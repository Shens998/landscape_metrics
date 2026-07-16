"""Pure patch-level metric formulas."""

import math
from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd

from ..topology import Topology
from ..models import GridSpec


def patch_shape_index(*, area: float, perimeter: float) -> float:
    """Return the perimeter-to-circle standardized shape index."""
    return perimeter / (2.0 * math.sqrt(math.pi * area))


def patch_fractal_dimension(*, area: float, perimeter: float, cell_count: int) -> float:
    """Return the perimeter-area fractal dimension for multi-cell patches."""
    if cell_count <= 1:
        return float("nan")
    return 2.0 * math.log(0.25 * perimeter) / math.log(area)


def patch_radius_of_gyration(
    *,
    rows: np.ndarray,
    cols: np.ndarray,
    pixel_width: float,
    pixel_height: float,
) -> float:
    """Return RMS distance of patch-cell centers from their centroid."""
    x = (cols.astype(float) + 0.5) * pixel_width
    y = (rows.astype(float) + 0.5) * pixel_height
    return float(math.sqrt(np.mean((x - x.mean()) ** 2 + (y - y.mean()) ** 2)))


def patch_metrics(topology: Topology) -> pd.DataFrame:
    """Calculate the frozen patch-level metrics for every labeled patch."""
    cell_area = topology.grid.pixel_width * topology.grid.pixel_height
    rows: list[dict[str, float | int]] = []
    for patch_id in sorted(topology.patch_class):
        patch_rows, patch_cols = np.nonzero(topology.labels == patch_id)
        cell_count = int(patch_rows.size)
        area = cell_count * cell_area
        perimeter = topology.perimeter_by_patch[patch_id]
        rows.append(
            {
                "patch_id": patch_id,
                "class_value": topology.patch_class[patch_id],
                "area": area,
                "perimeter": perimeter,
                "shape_index": patch_shape_index(area=area, perimeter=perimeter),
                "perimeter_area_ratio": perimeter / area,
                "fractal_dimension": patch_fractal_dimension(
                    area=area,
                    perimeter=perimeter,
                    cell_count=cell_count,
                ),
                "radius_of_gyration": patch_radius_of_gyration(
                    rows=patch_rows,
                    cols=patch_cols,
                    pixel_width=topology.grid.pixel_width,
                    pixel_height=topology.grid.pixel_height,
                ),
            }
        )
    return pd.DataFrame(rows)


def patch_metrics_from_summaries(
    records: Sequence[Mapping[str, float | int]],
    grid: GridSpec,
) -> pd.DataFrame:
    """Calculate patch metrics from streamed per-patch moments and edge summaries."""
    cell_area = grid.pixel_width * grid.pixel_height
    rows: list[dict[str, float | int]] = []
    for record in records:
        cell_count = int(record["cell_count"])
        area = cell_count * cell_area
        perimeter = float(record["perimeter"])
        mean_row = float(record["sum_row"]) / cell_count
        mean_col = float(record["sum_col"]) / cell_count
        row_variance = float(record["sum_row_sq"]) / cell_count - mean_row**2
        col_variance = float(record["sum_col_sq"]) / cell_count - mean_col**2
        radius = math.sqrt(
            max(0.0, row_variance * grid.pixel_height**2 + col_variance * grid.pixel_width**2)
        )
        rows.append(
            {
                "patch_id": int(record["patch_id"]),
                "class_value": int(record["class_value"]),
                "area": area,
                "perimeter": perimeter,
                "shape_index": patch_shape_index(area=area, perimeter=perimeter),
                "perimeter_area_ratio": perimeter / area,
                "fractal_dimension": patch_fractal_dimension(
                    area=area, perimeter=perimeter, cell_count=cell_count
                ),
                "radius_of_gyration": radius,
            }
        )
    return pd.DataFrame(rows)
