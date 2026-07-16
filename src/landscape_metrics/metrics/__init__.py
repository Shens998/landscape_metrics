"""Metric-card metadata and metric functions."""

from importlib.resources import files
from typing import Any

import yaml


def load_metric_cards() -> dict[str, dict[str, Any]]:
    """Load the versioned metric definitions shipped with this package."""
    text = files("landscape_metrics").joinpath("metric_cards.yaml").read_text(encoding="utf-8")
    return yaml.safe_load(text)["metrics"]
