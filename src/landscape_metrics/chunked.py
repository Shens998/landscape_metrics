"""Out-of-core backend entry point; implementation follows in the next task."""

from pathlib import Path
import shutil
import sqlite3
import tempfile
from collections.abc import Iterator

import numpy as np
import rasterio
from rasterio.windows import Window

from .errors import TemporaryStorageError
from .models import ChunkedResults, GridSpec, RunConfig
from .topology import label_patches


def required_temporary_bytes(grid: GridSpec) -> int:
    """Return the conservative v0.1 temporary-storage budget."""
    return 48 * grid.width * grid.height


def preflight_temporary_storage(tempdir: Path | None, grid: GridSpec) -> Path:
    """Validate temporary capacity before creating a chunked work directory."""
    directory = Path(tempdir) if tempdir is not None else Path(tempfile.gettempdir())
    if not directory.is_dir():
        raise TemporaryStorageError(f"temporary directory does not exist: {directory}")

    required = required_temporary_bytes(grid)
    available = shutil.disk_usage(directory).free
    if available < required:
        raise TemporaryStorageError(
            f"temporary storage requires {required} bytes but {available} bytes are free; "
            "choose another tempdir"
        )
    return directory


class DiskUnionFind:
    """Deterministic union-find backed by an int64 memmap parent array."""

    def __init__(self, parent: np.memmap) -> None:
        self._parent = parent

    def find(self, label: int) -> int:
        """Return the root and compress the traversed parent chain."""
        root = label
        while int(self._parent[root]) != root:
            root = int(self._parent[root])

        while label != root:
            parent = int(self._parent[label])
            self._parent[label] = root
            label = parent
        return root

    def union(self, left: int, right: int) -> int:
        """Merge two labels with the smaller root chosen deterministically."""
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root == right_root:
            return left_root
        root, child = sorted((left_root, right_root))
        self._parent[child] = root
        return root


def iter_windows(grid: GridSpec, tile_shape: tuple[int, int]) -> Iterator[Window]:
    """Yield row-major windows constrained by the requested tile shape."""
    tile_rows, tile_cols = tile_shape
    for row_off in range(0, grid.height, tile_rows):
        for col_off in range(0, grid.width, tile_cols):
            yield Window(
                col_off=col_off,
                row_off=row_off,
                width=min(tile_cols, grid.width - col_off),
                height=min(tile_rows, grid.height - row_off),
            )


def _initialize_parent(parent: np.memmap, chunk_cells: int) -> None:
    for start in range(0, parent.size, chunk_cells):
        stop = min(start + chunk_cells, parent.size)
        parent[start:stop] = np.arange(start, stop, dtype=np.int64)


def _union_boundary(
    first_labels: np.ndarray,
    second_labels: np.ndarray,
    first_values: np.ndarray,
    second_values: np.ndarray,
    *,
    connectivity: int,
    union_find: DiskUnionFind,
) -> None:
    shifts = (0,) if connectivity == 4 else (-1, 0, 1)
    for shift in shifts:
        if shift >= 0:
            first_slice = slice(shift, None)
            second_slice = slice(None, -shift or None)
        else:
            first_slice = slice(None, shift)
            second_slice = slice(-shift, None)

        labels_a = first_labels[first_slice]
        labels_b = second_labels[second_slice]
        values_a = first_values[first_slice]
        values_b = second_values[second_slice]
        matching = (labels_a > 0) & (labels_b > 0) & (values_a == values_b)
        if not np.any(matching):
            continue

        pairs = np.unique(np.column_stack((labels_a[matching], labels_b[matching])), axis=0)
        for left, right in pairs:
            union_find.union(int(left), int(right))


def _union_pair(
    first_label: int,
    second_label: int,
    first_value: int,
    second_value: int,
    union_find: DiskUnionFind,
) -> None:
    if first_label > 0 and second_label > 0 and first_value == second_value:
        union_find.union(first_label, second_label)


def _component_rows(values: np.ndarray, labels: np.ndarray, offset: int) -> list[tuple[int, int, int]]:
    count = int(labels.max())
    if count == 0:
        return []

    flat_labels = labels.ravel()
    counts = np.bincount(flat_labels, minlength=count + 1)[1:]
    first_indices = np.full(count + 1, labels.size, dtype=np.int64)
    np.minimum.at(first_indices, flat_labels, np.arange(labels.size))
    class_values = values.ravel()[first_indices[1:]]
    return [
        (offset + local_label, int(class_value), int(cell_count))
        for local_label, class_value, cell_count in zip(
            range(1, count + 1), class_values, counts, strict=True
        )
    ]


def build_root_labels(
    path: Path,
    *,
    grid: GridSpec,
    nodata: int | None,
    config: RunConfig,
    workdir: Path,
) -> np.memmap:
    """Label tiles, union matching boundary components, and write root labels."""
    if config.tile_shape is None:
        raise ValueError("chunked root labels require tile_shape")

    labels = np.memmap(workdir / "labels.memmap", dtype=np.int64, mode="w+", shape=(grid.height, grid.width))
    labels[:] = 0
    parent = np.memmap(
        workdir / "parent.memmap",
        dtype=np.int64,
        mode="w+",
        shape=(grid.height * grid.width + 1,),
    )
    chunk_cells = max(1, config.tile_shape[0] * config.tile_shape[1])
    _initialize_parent(parent, chunk_cells)
    windows = list(iter_windows(grid, config.tile_shape))

    database = sqlite3.connect(workdir / "components.sqlite")
    database.execute(
        "CREATE TABLE provisional_components ("
        "provisional_label INTEGER PRIMARY KEY, class_value INTEGER NOT NULL, cell_count INTEGER NOT NULL)"
    )
    offset = 0
    with rasterio.open(path) as dataset:
        for window in windows:
            values = dataset.read(1, window=window)
            local_labels = label_patches(values, nodata=nodata, connectivity=config.connectivity)
            count = int(local_labels.max())
            row_start, col_start = int(window.row_off), int(window.col_off)
            row_stop, col_stop = row_start + int(window.height), col_start + int(window.width)
            target = labels[row_start:row_stop, col_start:col_stop]
            occupied = local_labels > 0
            target[occupied] = local_labels[occupied] + offset
            database.executemany(
                "INSERT INTO provisional_components VALUES (?, ?, ?)",
                _component_rows(values, local_labels, offset),
            )
            offset += count
        database.commit()

        union_find = DiskUnionFind(parent)
        for window in windows:
            row_start, col_start = int(window.row_off), int(window.col_off)
            row_stop, col_stop = row_start + int(window.height), col_start + int(window.width)
            if col_stop < grid.width:
                left_window = Window(col_stop - 1, row_start, 1, int(window.height))
                right_window = Window(col_stop, row_start, 1, int(window.height))
                _union_boundary(
                    labels[row_start:row_stop, col_stop - 1],
                    labels[row_start:row_stop, col_stop],
                    dataset.read(1, window=left_window).reshape(-1),
                    dataset.read(1, window=right_window).reshape(-1),
                    connectivity=config.connectivity,
                    union_find=union_find,
                )
            if row_stop < grid.height:
                top_window = Window(col_start, row_stop - 1, int(window.width), 1)
                bottom_window = Window(col_start, row_stop, int(window.width), 1)
                _union_boundary(
                    labels[row_stop - 1, col_start:col_stop],
                    labels[row_stop, col_start:col_stop],
                    dataset.read(1, window=top_window).reshape(-1),
                    dataset.read(1, window=bottom_window).reshape(-1),
                    connectivity=config.connectivity,
                    union_find=union_find,
                )
            if config.connectivity == 8 and row_stop < grid.height and col_stop < grid.width:
                corner_values = dataset.read(
                    1,
                    window=Window(col_stop - 1, row_stop - 1, 2, 2),
                )
                _union_pair(
                    int(labels[row_stop - 1, col_stop - 1]),
                    int(labels[row_stop, col_stop]),
                    int(corner_values[0, 0]),
                    int(corner_values[1, 1]),
                    union_find,
                )
                _union_pair(
                    int(labels[row_stop - 1, col_stop]),
                    int(labels[row_stop, col_stop - 1]),
                    int(corner_values[0, 1]),
                    int(corner_values[1, 0]),
                    union_find,
                )
    database.close()

    roots = np.memmap(workdir / "root_labels.memmap", dtype=np.int64, mode="w+", shape=labels.shape)
    flat_labels = labels.reshape(-1)
    flat_roots = roots.reshape(-1)
    union_find = DiskUnionFind(parent)
    for start in range(0, flat_labels.size, chunk_cells):
        stop = min(start + chunk_cells, flat_labels.size)
        flat_roots[start:stop] = np.fromiter(
            (union_find.find(int(label)) if label else 0 for label in flat_labels[start:stop]),
            dtype=np.int64,
            count=stop - start,
        )
    parent.flush()
    labels.flush()
    roots.flush()
    return roots


def compute_chunked(
    path: Path,
    *,
    grid: GridSpec,
    nodata: int | None,
    config: RunConfig,
) -> ChunkedResults:
    """Reserve the stable chunked-backend interface before its implementation."""
    del path, grid, nodata, config
    raise NotImplementedError("the chunked backend has not been implemented yet")
