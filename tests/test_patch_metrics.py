import math

import numpy as np
import pytest

from landscape_metrics.metrics.patch import (
    patch_metrics,
    patch_fractal_dimension,
    patch_radius_of_gyration,
    patch_shape_index,
)
from landscape_metrics.models import GridSpec
from landscape_metrics.topology import build_topology


def test_square_patch_shape_and_fractal_metrics() -> None:
    assert patch_shape_index(area=3600.0, perimeter=240.0) == pytest.approx(
        240.0 / (2 * math.sqrt(math.pi * 3600.0))
    )
    assert patch_fractal_dimension(area=3600.0, perimeter=240.0, cell_count=4) == pytest.approx(
        1.0
    )
    assert math.isnan(patch_fractal_dimension(area=900.0, perimeter=120.0, cell_count=1))


def test_two_horizontal_cells_have_radius_of_gyration_half_a_cell_width() -> None:
    result = patch_radius_of_gyration(
        rows=np.array([0, 0]),
        cols=np.array([0, 1]),
        pixel_width=30,
        pixel_height=30,
    )

    assert result == pytest.approx(15.0)


def test_patch_metrics_returns_one_row_per_nonzero_patch_label() -> None:
    topology = build_topology(
        np.array([[1, 1], [2, 2]], dtype=np.int16),
        nodata=None,
        grid=GridSpec(width=2, height=2, pixel_width=30, pixel_height=30, crs="EPSG:6933"),
        connectivity=4,
    )

    result = patch_metrics(topology)

    assert result[["patch_id", "class_value"]].to_dict("records") == [
        {"patch_id": 1, "class_value": 1},
        {"patch_id": 2, "class_value": 2},
    ]
    assert result["area"].tolist() == [1800.0, 1800.0]
    assert result["perimeter"].tolist() == [180.0, 180.0]
