"""In-memory topology primitives for categorical raster landscapes."""

from dataclasses import dataclass

import numpy as np
from scipy import ndimage

from .errors import ConfigurationError, InvalidRasterError
from .models import GridSpec


@dataclass(frozen=True, slots=True)
class Topology:
    """Reusable patch labels and edge summaries for one categorical grid."""

    labels: np.ndarray
    values: np.ndarray
    valid_mask: np.ndarray
    patch_class: dict[int, int]
    grid: GridSpec
    perimeter_by_patch: dict[int, float]
    same_adjacency_by_class: dict[int, int]
    class_edge_by_class: dict[int, float]


def _structure(connectivity: int) -> np.ndarray:
    if connectivity == 4:
        return np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], dtype=np.uint8)
    if connectivity == 8:
        return np.ones((3, 3), dtype=np.uint8)
    raise ConfigurationError("connectivity must be 4 or 8")


def _valid_mask(values: np.ndarray, nodata: int | None) -> np.ndarray:
    return np.ones(values.shape, dtype=bool) if nodata is None else values != nodata


def label_patches(values: np.ndarray, *, nodata: int | None, connectivity: int) -> np.ndarray:
    """Assign positive, globally unique patch labels; zero denotes excluded cells."""
    if values.ndim != 2:
        raise InvalidRasterError("input must be a two-dimensional integer categorical array")

    valid = _valid_mask(values, nodata)
    labels = np.zeros(values.shape, dtype=np.int64)
    offset = 0
    for class_value in np.unique(values[valid]):
        local_labels, count = ndimage.label(values == class_value, structure=_structure(connectivity))
        occupied = local_labels > 0
        labels[occupied] = local_labels[occupied] + offset
        offset += int(count)
    return labels


def build_topology(
    values: np.ndarray,
    *,
    nodata: int | None,
    grid: GridSpec,
    connectivity: int,
    include_landscape_boundary: bool = True,
) -> Topology:
    """Build labels and exact side-based edge summaries for an in-memory grid."""
    if values.shape != (grid.height, grid.width):
        raise InvalidRasterError("array shape must match GridSpec height and width")

    valid = _valid_mask(values, nodata)
    labels = label_patches(values, nodata=nodata, connectivity=connectivity)
    classes = [int(value) for value in np.unique(values[valid])]
    patch_class = {
        int(label): int(values[row, col])
        for row, col in zip(*np.nonzero(labels), strict=True)
        for label in [labels[row, col]]
    }
    perimeter_by_patch = {patch_id: 0.0 for patch_id in patch_class}
    same_adjacency_by_class = {class_value: 0 for class_value in classes}
    class_edge_by_class = {class_value: 0.0 for class_value in classes}

    directions = (
        (-1, 0, grid.pixel_width),
        (1, 0, grid.pixel_width),
        (0, -1, grid.pixel_height),
        (0, 1, grid.pixel_height),
    )
    for row, col in zip(*np.nonzero(valid), strict=True):
        class_value = int(values[row, col])
        patch_id = int(labels[row, col])
        for row_delta, col_delta, edge_length in directions:
            neighbor_row = row + row_delta
            neighbor_col = col + col_delta
            if not (0 <= neighbor_row < grid.height and 0 <= neighbor_col < grid.width):
                if include_landscape_boundary:
                    perimeter_by_patch[patch_id] += edge_length
                    class_edge_by_class[class_value] += edge_length
                continue
            if not valid[neighbor_row, neighbor_col]:
                continue
            neighbor_class = int(values[neighbor_row, neighbor_col])
            if neighbor_class != class_value:
                perimeter_by_patch[patch_id] += edge_length
                class_edge_by_class[class_value] += edge_length
            elif row_delta > 0 or col_delta > 0:
                same_adjacency_by_class[class_value] += 1

    return Topology(
        labels=labels,
        values=values.copy(),
        valid_mask=valid,
        patch_class=patch_class,
        grid=grid,
        perimeter_by_patch=perimeter_by_patch,
        same_adjacency_by_class=same_adjacency_by_class,
        class_edge_by_class=class_edge_by_class,
    )
