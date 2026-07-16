import pytest
import pandas as pd

from landscape_metrics.errors import ConfigurationError, SpatialMetadataError
from landscape_metrics.models import GridSpec, MetricResult, RunConfig


def test_grid_spec_rejects_non_positive_pixel_width() -> None:
    with pytest.raises(SpatialMetadataError, match="pixel_width must be positive"):
        GridSpec(width=2, height=2, pixel_width=0, pixel_height=30, crs="EPSG:6933")


def test_run_config_accepts_only_rook_or_queen_connectivity() -> None:
    with pytest.raises(ConfigurationError, match="connectivity must be 4 or 8"):
        RunConfig(connectivity=6)  # type: ignore[arg-type]


def test_metric_result_keeps_values_and_metadata_contract() -> None:
    values = pd.DataFrame({"total_area": [900.0]})
    metadata = {"connectivity": 8, "execution_path": "memory"}

    result = MetricResult(values=values, metadata=metadata)

    assert result.values.equals(values)
    assert result.metadata == metadata
