"""Validation and column selection for the public metric tables."""

from collections.abc import Sequence
from typing import Literal

import pandas as pd

from .errors import ConfigurationError
from .metrics import load_metric_cards


MetricLevel = Literal["patch", "class", "landscape"]

IDENTITY_COLUMNS: dict[MetricLevel, tuple[str, ...]] = {
    "patch": ("patch_id", "class_value"),
    "class": ("class_value",),
    "landscape": (),
}


def select_metric_columns(
    values: pd.DataFrame,
    *,
    level: MetricLevel,
    requested: Sequence[str] | None,
) -> pd.DataFrame:
    """Return identity columns and requested metric IDs in the caller's order."""
    if requested is None:
        return values.copy()

    metric_ids = tuple(requested)
    if len(set(metric_ids)) != len(metric_ids):
        raise ConfigurationError("metric selection cannot contain duplicates")

    cards = load_metric_cards()
    available = tuple(metric_id for metric_id, card in cards.items() if level in card["level"])
    for metric_id in metric_ids:
        if metric_id not in cards:
            raise ConfigurationError(
                f"unknown metric '{metric_id}'; available at {level} level: {', '.join(available)}"
            )
        if level not in cards[metric_id]["level"]:
            raise ConfigurationError(
                f"metric '{metric_id}' is not available at {level} level; "
                f"available: {', '.join(available)}"
            )

    return values.loc[:, [*IDENTITY_COLUMNS[level], *metric_ids]].copy()
