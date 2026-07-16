"""Class-level aggregations of frozen patch and topology metrics."""

import math

import numpy as np
import pandas as pd

from ..models import AggregateSummary
from ..topology import Topology
from .summary import as_summary


def max_g_ii(cell_count: int) -> int:
    """Return the maximum number of rook-adjacent pairs for n grid cells."""
    return 0 if cell_count <= 1 else 2 * cell_count - math.ceil(2 * math.sqrt(cell_count))


def class_metrics(patches: pd.DataFrame, topology: Topology | AggregateSummary) -> pd.DataFrame:
    """Aggregate patch metrics to one row per explicit valid class."""
    summary = as_summary(topology)
    cell_area = summary.grid.pixel_width * summary.grid.pixel_height
    valid_area = float(summary.valid_cell_count) * cell_area
    valid_area_hectares = valid_area / 10_000.0
    records: list[dict[str, float | int]] = []

    for class_value in sorted(summary.class_edge_by_class):
        class_patches = patches.loc[patches["class_value"] == class_value]
        areas = class_patches["area"].to_numpy(dtype=float)
        cell_count = summary.class_cell_counts[class_value]
        count = int(areas.size)
        total_area = float(areas.sum())
        area_sd = float(np.std(areas, ddof=1)) if count > 1 else float("nan")
        denominator = max_g_ii(cell_count)
        aggregation = (
            0.0
            if denominator == 0
            else 100.0 * summary.same_adjacency_by_class[class_value] / denominator
        )
        records.append(
            {
                "class_value": class_value,
                "total_area": total_area,
                "proportion_of_landscape": 100.0 * total_area / valid_area,
                "number_of_patches": count,
                "patch_density": count / valid_area_hectares * 100.0,
                "largest_patch_index": 100.0 * float(areas.max()) / valid_area,
                "total_edge": summary.class_edge_by_class[class_value],
                "edge_density": summary.class_edge_by_class[class_value] / valid_area_hectares,
                "area_mean": float(areas.mean()),
                "area_sd": area_sd,
                "area_cv": float("nan") if count < 2 else 100.0 * area_sd / float(areas.mean()),
                "shape_index_mean": float(class_patches["shape_index"].mean()),
                "aggregation_index": aggregation,
            }
        )
    return pd.DataFrame(records)
