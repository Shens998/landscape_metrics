"""Immutable configuration and result contracts."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pandas as pd

from .errors import ConfigurationError, SpatialMetadataError


@dataclass(frozen=True, slots=True)
class GridSpec:
    """Spatial shape and positive pixel dimensions for a categorical grid."""

    width: int
    height: int
    pixel_width: float
    pixel_height: float
    crs: str | None
    linear_unit_to_m: float | None = None

    def __post_init__(self) -> None:
        if self.width < 1 or self.height < 1:
            raise SpatialMetadataError("width and height must be positive")
        if self.pixel_width <= 0:
            raise SpatialMetadataError("pixel_width must be positive")
        if self.pixel_height <= 0:
            raise SpatialMetadataError("pixel_height must be positive")
        if self.linear_unit_to_m is not None and self.linear_unit_to_m <= 0:
            raise SpatialMetadataError("linear_unit_to_m must be positive when provided")


@dataclass(frozen=True, slots=True)
class RunConfig:
    """Explicit rules controlling connectivity and execution strategy."""

    connectivity: Literal[4, 8] = 8
    include_landscape_boundary: bool = True
    tile_shape: tuple[int, int] | None = None
    tempdir: Path | None = None

    def __post_init__(self) -> None:
        if self.connectivity not in (4, 8):
            raise ConfigurationError("connectivity must be 4 or 8")
        if self.tile_shape is not None and (self.tile_shape[0] < 1 or self.tile_shape[1] < 1):
            raise ConfigurationError("tile_shape dimensions must be positive")


@dataclass(frozen=True, slots=True)
class MetricResult:
    """Tabular metrics accompanied by reproducibility metadata."""

    values: pd.DataFrame
    metadata: dict[str, object]
