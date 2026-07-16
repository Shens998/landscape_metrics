"""Class-level aggregations of frozen patch and topology metrics."""

import math

import numpy as np
import pandas as pd

from ..topology import Topology


def max_g_ii(cell_count: int) -> int:
    """Return the maximum number of rook-adjacent pairs for n grid cells."""
    return 0 if cell_count <= 1 else 2 * cell_count - math.ceil(2 * math.sqrt(cell_count))


def class_metrics(patches: pd.DataFrame, topology: Topology) -> pd.DataFrame:
    """Aggregate patch metrics to one row per explicit valid class."""
    cell_area = topology.grid.pixel_width * topology.grid.pixel_height
    valid_area = float(topology.valid_mask.sum()) * cell_area
    valid_area_hectares = valid_area / 10_000.0
    records: list[dict[str, float | int]] = []

    for class_value in sorted(topology.class_edge_by_class):
        class_patches = patches.loc[patches["class_value"] == class_value]
        areas = class_patches["area"].to_numpy(dtype=float)
        cell_count = int(np.count_nonzero(topology.valid_mask & (topology.values == class_value)))
        count = int(areas.size)
        total_area = float(areas.sum())
        area_sd = float(np.std(areas, ddof=1)) if count > 1 else float("nan")
        denominator = max_g_ii(cell_count)
        aggregation = (
            0.0
            if denominator == 0
            else 100.0 * topology.same_adjacency_by_class[class_value] / denominator
        )
        records.append(
            {
                "class_value": class_value,
                "total_area": total_area,
                "proportion_of_landscape": 100.0 * total_area / valid_area,
                "number_of_patches": count,
                "patch_density": count / valid_area_hectares * 100.0,
                "largest_patch_index": 100.0 * float(areas.max()) / valid_area,
                "total_edge": topology.class_edge_by_class[class_value],
                "edge_density": topology.class_edge_by_class[class_value] / valid_area_hectares,
                "area_mean": float(areas.mean()),
                "area_sd": area_sd,
                "area_cv": float("nan") if count < 2 else 100.0 * area_sd / float(areas.mean()),
                "shape_index_mean": float(class_patches["shape_index"].mean()),
                "aggregation_index": aggregation,
            }
        )
    return pd.DataFrame(records)
