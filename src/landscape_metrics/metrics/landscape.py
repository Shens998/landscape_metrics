"""Landscape-level aggregations of class, patch, and topology metrics."""

import math

import numpy as np
import pandas as pd

from ..topology import Topology
from .class_level import max_g_ii


def _landscape_edge(topology: Topology, *, include_landscape_boundary: bool = True) -> float:
    total = 0.0
    for row, col in zip(*np.nonzero(topology.valid_mask), strict=True):
        class_value = topology.values[row, col]
        for row_delta, col_delta, length in (
            (0, 1, topology.grid.pixel_height),
            (1, 0, topology.grid.pixel_width),
        ):
            next_row, next_col = row + row_delta, col + col_delta
            if next_row >= topology.grid.height or next_col >= topology.grid.width:
                if include_landscape_boundary:
                    total += length
            elif topology.valid_mask[next_row, next_col] and topology.values[next_row, next_col] != class_value:
                total += length
        if include_landscape_boundary and row == 0:
            total += topology.grid.pixel_width
        if include_landscape_boundary and col == 0:
            total += topology.grid.pixel_height
    return total


def landscape_metrics(
    classes: pd.DataFrame,
    patches: pd.DataFrame,
    topology: Topology,
) -> pd.DataFrame:
    """Aggregate frozen landscape metrics to one one-row DataFrame."""
    cell_area = topology.grid.pixel_width * topology.grid.pixel_height
    valid_area = float(topology.valid_mask.sum()) * cell_area
    valid_area_hectares = valid_area / 10_000.0
    proportions = classes["total_area"].to_numpy(dtype=float) / valid_area
    shannon = float(-(proportions[proportions > 0] * np.log(proportions[proportions > 0])).sum())
    class_count = int(proportions.size)
    total_same = sum(topology.same_adjacency_by_class.values())
    total_max = sum(
        max_g_ii(int(np.count_nonzero(topology.valid_mask & (topology.values == class_value))))
        for class_value in topology.class_edge_by_class
    )

    return pd.DataFrame(
        [
            {
                "total_area": valid_area,
                "number_of_patches": int(patches.shape[0]),
                "patch_density": patches.shape[0] / valid_area_hectares * 100.0,
                "edge_density": _landscape_edge(topology) / valid_area_hectares,
                "largest_patch_index": 100.0 * float(patches["area"].max()) / valid_area,
                "shannon_diversity": shannon,
                "shannon_evenness": 0.0 if class_count == 1 else shannon / math.log(class_count),
                "simpson_diversity": float(1.0 - np.square(proportions).sum()),
                "aggregation_index": 0.0 if total_max == 0 else 100.0 * total_same / total_max,
            }
        ]
    )
