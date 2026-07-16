import math
import importlib

import numpy as np
import pandas as pd
import pytest

from landscape_metrics.metrics.class_level import class_metrics
from landscape_metrics.metrics.patch import patch_metrics
from landscape_metrics.models import GridSpec
from landscape_metrics.topology import build_topology


def test_class_metrics_use_valid_landscape_area_as_denominator() -> None:
    topology = build_topology(
        np.array([[1, 1], [2, 2]], dtype=np.int16),
        nodata=None,
        grid=GridSpec(width=2, height=2, pixel_width=30, pixel_height=30, crs="EPSG:6933"),
        connectivity=4,
    )

    result = class_metrics(patch_metrics(topology), topology).set_index("class_value")
    row = result.loc[1]

    assert row["total_area"] == 1800.0
    assert row["proportion_of_landscape"] == 50.0
    assert row["number_of_patches"] == 1
    assert row["patch_density"] == pytest.approx(100 / 0.36)
    assert row["largest_patch_index"] == 50.0
    assert row["total_edge"] == 180.0
    assert row["edge_density"] == 500.0
    assert row["area_mean"] == 1800.0
    assert math.isnan(row["area_sd"])
    assert math.isnan(row["area_cv"])
    assert row["shape_index_mean"] == row["shape_index_mean"]
    assert row["aggregation_index"] == 100.0


def test_class_metrics_accepts_a_backend_neutral_summary() -> None:
    topology = build_topology(
        np.array([[1, 1], [2, 2]], dtype=np.int16),
        nodata=None,
        grid=GridSpec(width=2, height=2, pixel_width=30, pixel_height=30, crs="EPSG:6933"),
        connectivity=4,
    )
    patches = patch_metrics(topology)
    summary = importlib.import_module("landscape_metrics.metrics.summary")

    pd.testing.assert_frame_equal(
        class_metrics(patches, topology),
        class_metrics(patches, summary.summary_from_topology(topology)),
    )
