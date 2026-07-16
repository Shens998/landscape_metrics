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
from .metrics.class_level import class_metrics
from .metrics.landscape import landscape_metrics
from .metrics.patch import patch_metrics_from_summaries
from .models import AggregateSummary, ChunkedResults, GridSpec, RunConfig
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
    """Compute exact metric tables with disk-backed labels and patch summaries."""
    if config.tile_shape is None:
        raise ValueError("chunked execution requires tile_shape")
    work_parent = preflight_temporary_storage(config.tempdir, grid)
    with tempfile.TemporaryDirectory(prefix="landscape-metrics-", dir=work_parent) as name:
        workdir = Path(name)
        roots = build_root_labels(path, grid=grid, nodata=nodata, config=config, workdir=workdir)
        database = sqlite3.connect(workdir / "patches.sqlite")
        database.execute(
            "CREATE TABLE patches (root_label INTEGER PRIMARY KEY, class_value INTEGER NOT NULL, "
            "cell_count INTEGER NOT NULL, perimeter REAL NOT NULL, same_adjacency INTEGER NOT NULL, "
            "sum_row REAL NOT NULL, sum_col REAL NOT NULL, sum_row_sq REAL NOT NULL, "
            "sum_col_sq REAL NOT NULL, first_row INTEGER NOT NULL, first_col INTEGER NOT NULL)"
        )
        summary = _aggregate_windows(path, roots, grid, nodata, config, database)
        records = _read_patch_records(database)
        database.close()
        patches = patch_metrics_from_summaries(records, grid)
        classes = class_metrics(patches, summary)
        return ChunkedResults(patches, classes, landscape_metrics(classes, patches, summary))


def _aggregate_windows(
    path: Path,
    roots: np.memmap,
    grid: GridSpec,
    nodata: int | None,
    config: RunConfig,
    database: sqlite3.Connection,
) -> AggregateSummary:
    """Aggregate root labels one window at a time into a SQLite patch table."""
    valid_count = 0
    class_counts: dict[int, int] = {}
    same_counts: dict[int, int] = {}
    landscape_edge = 0.0
    with rasterio.open(path) as dataset:
        for window in iter_windows(grid, config.tile_shape or (grid.height, grid.width)):
            r0, c0 = int(window.row_off), int(window.col_off)
            r1, c1 = r0 + int(window.height), c0 + int(window.width)
            er0, ec0 = max(0, r0 - 1), max(0, c0 - 1)
            er1, ec1 = min(grid.height, r1 + 1), min(grid.width, c1 + 1)
            expanded = Window(ec0, er0, ec1 - ec0, er1 - er0)
            values = dataset.read(1, window=expanded)
            root_values = roots[er0:er1, ec0:ec1]
            rr0, cc0 = r0 - er0, c0 - ec0
            central = values[rr0 : rr0 + (r1 - r0), cc0 : cc0 + (c1 - c0)]
            labels = root_values[rr0 : rr0 + (r1 - r0), cc0 : cc0 + (c1 - c0)]
            valid = labels > 0
            if not np.any(valid):
                continue
            flat_labels = labels[valid]
            unique, inverse = np.unique(flat_labels, return_inverse=True)
            counts = np.bincount(inverse)
            rows, cols = np.nonzero(valid)
            global_rows, global_cols = rows + r0, cols + c0
            sum_row = np.bincount(inverse, weights=global_rows)
            sum_col = np.bincount(inverse, weights=global_cols)
            sum_row_sq = np.bincount(inverse, weights=global_rows.astype(float) ** 2)
            sum_col_sq = np.bincount(inverse, weights=global_cols.astype(float) ** 2)
            first_row = np.full(unique.size, grid.height, dtype=int)
            first_col = np.full(unique.size, grid.width, dtype=int)
            np.minimum.at(first_row, inverse, global_rows)
            np.minimum.at(first_col, inverse, global_cols)
            first_index = np.full(unique.size, central.size, dtype=int)
            np.minimum.at(first_index, inverse, np.flatnonzero(valid))
            classes = central.ravel()[first_index]
            perimeter = np.zeros(unique.size, dtype=float)
            same = np.zeros(unique.size, dtype=int)
            global_row_grid = np.arange(r0, r1)[:, np.newaxis]
            global_col_grid = np.arange(c0, c1)[np.newaxis, :]
            padded_roots = np.pad(root_values, 1)
            padded_values = np.pad(values, 1)
            cr0, cc0p = rr0 + 1, cc0 + 1
            for dr, dc, length, count_same in ((-1, 0, grid.pixel_width, False), (1, 0, grid.pixel_width, True), (0, -1, grid.pixel_height, False), (0, 1, grid.pixel_height, True)):
                neighbor_roots = padded_roots[cr0 + dr : cr0 + dr + labels.shape[0], cc0p + dc : cc0p + dc + labels.shape[1]]
                neighbor_values = padded_values[
                    cr0 + dr : cr0 + dr + labels.shape[0],
                    cc0p + dc : cc0p + dc + labels.shape[1],
                ]
                boundary = valid & (neighbor_roots > 0) & (neighbor_values != central)
                outside = valid & (
                    (global_row_grid + dr < 0)
                    | (global_row_grid + dr >= grid.height)
                    | (global_col_grid + dc < 0)
                    | (global_col_grid + dc >= grid.width)
                )
                perimeter += np.bincount(inverse, weights=(boundary[valid] | outside[valid]) * length, minlength=unique.size)
                if count_same:
                    landscape_edge += float(boundary.sum() + outside.sum()) * length
                    equal = valid & (neighbor_roots > 0) & (neighbor_values == central)
                    same += np.bincount(inverse, weights=equal[valid], minlength=unique.size).astype(int)
            landscape_edge += float((valid & (global_row_grid == 0)).sum()) * grid.pixel_width
            landscape_edge += float((valid & (global_col_grid == 0)).sum()) * grid.pixel_height
            database.executemany(
                "INSERT INTO patches VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(root_label) DO UPDATE SET cell_count=cell_count+excluded.cell_count, perimeter=perimeter+excluded.perimeter, same_adjacency=same_adjacency+excluded.same_adjacency, sum_row=sum_row+excluded.sum_row, sum_col=sum_col+excluded.sum_col, sum_row_sq=sum_row_sq+excluded.sum_row_sq, sum_col_sq=sum_col_sq+excluded.sum_col_sq, first_row=MIN(first_row, excluded.first_row), first_col=MIN(first_col, excluded.first_col)",
                [(int(unique[i]), int(classes[i]), int(counts[i]), float(perimeter[i]), int(same[i]), float(sum_row[i]), float(sum_col[i]), float(sum_row_sq[i]), float(sum_col_sq[i]), int(first_row[i]), int(first_col[i])) for i in range(unique.size)],
            )
            valid_count += int(valid.sum())
            for value in np.unique(central[valid]):
                mask = valid & (central == value)
                class_counts[int(value)] = class_counts.get(int(value), 0) + int(mask.sum())
                same_counts[int(value)] = same_counts.get(int(value), 0) + int(same[classes == value].sum())
    database.commit()
    edges = {int(value): float(edge) for value, edge in database.execute("SELECT class_value, SUM(perimeter) FROM patches GROUP BY class_value")}
    return AggregateSummary(grid, valid_count, class_counts, same_counts, edges, landscape_edge)


def _read_patch_records(database: sqlite3.Connection) -> list[dict[str, int | float]]:
    columns = ["root_label", "class_value", "cell_count", "perimeter", "same_adjacency", "sum_row", "sum_col", "sum_row_sq", "sum_col_sq", "first_row", "first_col"]
    rows = database.execute("SELECT " + ", ".join(columns) + " FROM patches ORDER BY class_value, first_row, first_col")
    return [{"patch_id": index, **dict(zip(columns, row, strict=True))} for index, row in enumerate(rows, 1)]
