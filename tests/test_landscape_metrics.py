import math

import numpy as np
import pytest

from landscape_metrics.metrics.class_level import class_metrics
from landscape_metrics.metrics.landscape import landscape_metrics
from landscape_metrics.metrics.patch import patch_metrics
from landscape_metrics.models import GridSpec
from landscape_metrics.topology import build_topology


def test_landscape_metrics_for_two_equal_contiguous_classes() -> None:
    topology = build_topology(
        np.array([[1, 1], [2, 2]], dtype=np.int16),
        nodata=None,
        grid=GridSpec(width=2, height=2, pixel_width=30, pixel_height=30, crs="EPSG:6933"),
        connectivity=4,
    )
    patches = patch_metrics(topology)
    classes = class_metrics(patches, topology)

    result = landscape_metrics(classes, patches, topology).iloc[0]

    assert result["total_area"] == 3600.0
    assert result["number_of_patches"] == 2
    assert result["patch_density"] == pytest.approx(200 / 0.36)
    assert result["largest_patch_index"] == 50.0
    assert result["shannon_diversity"] == pytest.approx(math.log(2))
    assert result["shannon_evenness"] == 1.0
    assert result["simpson_diversity"] == 0.5
    assert result["aggregation_index"] == 100.0
