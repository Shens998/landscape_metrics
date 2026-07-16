"""Adapters from topology backends to common aggregate inputs."""

import numpy as np

from ..models import AggregateSummary
from ..topology import Topology


def summary_from_topology(topology: Topology) -> AggregateSummary:
    """Extract the aggregation inputs from an in-memory topology."""
    landscape_edge = 0.0
    for row, col in zip(*np.nonzero(topology.valid_mask), strict=True):
        value = topology.values[row, col]
        for row_delta, col_delta, length in (
            (0, 1, topology.grid.pixel_height),
            (1, 0, topology.grid.pixel_width),
        ):
            next_row, next_col = row + row_delta, col + col_delta
            if next_row >= topology.grid.height or next_col >= topology.grid.width:
                landscape_edge += length
            elif topology.valid_mask[next_row, next_col] and topology.values[next_row, next_col] != value:
                landscape_edge += length
        if row == 0:
            landscape_edge += topology.grid.pixel_width
        if col == 0:
            landscape_edge += topology.grid.pixel_height

    return AggregateSummary(
        grid=topology.grid,
        valid_cell_count=int(topology.valid_mask.sum()),
        class_cell_counts={
            class_value: int(np.count_nonzero(topology.valid_mask & (topology.values == class_value)))
            for class_value in topology.class_edge_by_class
        },
        same_adjacency_by_class=topology.same_adjacency_by_class,
        class_edge_by_class=topology.class_edge_by_class,
        landscape_edge=landscape_edge,
    )


def as_summary(value: Topology | AggregateSummary) -> AggregateSummary:
    """Normalize either supported backend representation to AggregateSummary."""
    return value if isinstance(value, AggregateSummary) else summary_from_topology(value)
