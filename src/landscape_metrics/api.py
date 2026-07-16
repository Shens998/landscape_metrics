"""Public object-oriented API for in-memory landscape metric computation."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import numpy as np

from .metadata import METADATA_SCHEMA_VERSION
from .metrics.class_level import class_metrics as compute_class_metrics
from .metrics.landscape import landscape_metrics as compute_landscape_metrics
from .metrics.patch import patch_metrics as compute_patch_metrics
from .models import ChunkedResults, GridSpec, MetricResult, RunConfig
from .topology import Topology, build_topology


@dataclass(slots=True)
class Landscape:
    """A validated categorical landscape plus explicit calculation rules."""

    _array: np.ndarray | None
    _grid: GridSpec
    _nodata: int | None
    _config: RunConfig
    _path: Path | None = None
    _topology_cache: Topology | None = field(default=None, init=False, repr=False)
    _chunked_cache: ChunkedResults | None = field(default=None, init=False, repr=False)

    @classmethod
    def from_array(
        cls,
        values: np.ndarray,
        *,
        pixel_width: float,
        pixel_height: float,
        crs: str,
        nodata: int | None = None,
        connectivity: Literal[4, 8] = 8,
    ) -> "Landscape":
        """Create an in-memory landscape after strict categorical input validation."""
        from .io import read_array

        array, grid = read_array(
            values,
            pixel_width=pixel_width,
            pixel_height=pixel_height,
            crs=crs,
            nodata=nodata,
        )
        return cls(array, grid, nodata, RunConfig(connectivity=connectivity))

    @classmethod
    def from_geotiff(
        cls,
        path: Path | str,
        *,
        connectivity: Literal[4, 8] = 8,
        tile_shape: tuple[int, int] | None = None,
        tempdir: Path | str | None = None,
    ) -> "Landscape":
        """Create an in-memory or chunked landscape from a validated GeoTIFF."""
        configuration = RunConfig(
            connectivity=connectivity,
            tile_shape=tile_shape,
            tempdir=None if tempdir is None else Path(tempdir),
        )
        source_path = Path(path)

        if tile_shape is not None:
            from .io import inspect_geotiff_details

            grid, nodata = inspect_geotiff_details(source_path)
            return cls(None, grid, nodata, configuration, source_path)

        from .io import read_geotiff

        array, grid, nodata = read_geotiff(source_path)
        return cls(array, grid, nodata, configuration, source_path)

    def _topology(self) -> Topology:
        if self._array is None:
            raise RuntimeError("chunked landscapes do not construct in-memory topology")
        if self._topology_cache is None:
            self._topology_cache = build_topology(
                self._array,
                nodata=self._nodata,
                grid=self._grid,
                connectivity=self._config.connectivity,
                include_landscape_boundary=self._config.include_landscape_boundary,
            )
        return self._topology_cache

    def _chunked(self) -> ChunkedResults:
        if self._path is None:
            raise RuntimeError("chunked execution requires a GeoTIFF source path")
        if self._chunked_cache is None:
            from .chunked import compute_chunked

            self._chunked_cache = compute_chunked(
                self._path,
                grid=self._grid,
                nodata=self._nodata,
                config=self._config,
            )
        return self._chunked_cache

    def _metadata(self) -> dict[str, object]:
        return {
            "metadata_schema_version": METADATA_SCHEMA_VERSION,
            "input_shape": [self._grid.height, self._grid.width],
            "input_dtype": None if self._array is None else str(self._array.dtype),
            "crs": self._grid.crs,
            "pixel_width": self._grid.pixel_width,
            "pixel_height": self._grid.pixel_height,
            "nodata": self._nodata,
            "nodata_policy": "excluded",
            "connectivity": self._config.connectivity,
            "include_landscape_boundary": self._config.include_landscape_boundary,
            "execution_path": "chunked" if self._config.tile_shape is not None else "memory",
            "tile_shape": None if self._config.tile_shape is None else list(self._config.tile_shape),
            "metric_version": "v0.1",
        }

    def patch_metrics(self) -> MetricResult:
        """Return one row per patch and reproducibility metadata."""
        if self._config.tile_shape is not None:
            return MetricResult(self._chunked().patches.copy(), self._metadata())
        return MetricResult(compute_patch_metrics(self._topology()), self._metadata())

    def class_metrics(self) -> MetricResult:
        """Return one row per explicit class and reproducibility metadata."""
        if self._config.tile_shape is not None:
            return MetricResult(self._chunked().classes.copy(), self._metadata())
        topology = self._topology()
        patches = compute_patch_metrics(topology)
        return MetricResult(compute_class_metrics(patches, topology), self._metadata())

    def metrics(self) -> MetricResult:
        """Return the one-row frozen landscape metric set and reproducibility metadata."""
        if self._config.tile_shape is not None:
            return MetricResult(self._chunked().landscape.copy(), self._metadata())
        topology = self._topology()
        patches = compute_patch_metrics(topology)
        classes = compute_class_metrics(patches, topology)
        return MetricResult(compute_landscape_metrics(classes, patches, topology), self._metadata())
