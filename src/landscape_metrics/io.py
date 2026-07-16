"""Strict readers for categorical arrays and GeoTIFF metadata."""

from pathlib import Path

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.io import DatasetReader

from .errors import InvalidRasterError, SpatialMetadataError
from .models import GridSpec


def read_array(
    values: np.ndarray,
    *,
    pixel_width: float,
    pixel_height: float,
    crs: str,
    nodata: int | None,
) -> tuple[np.ndarray, GridSpec]:
    """Validate and copy a two-dimensional integer categorical array."""
    if values.ndim != 2 or not np.issubdtype(values.dtype, np.integer):
        raise InvalidRasterError("input must be a two-dimensional integer categorical array")

    parsed_crs = CRS.from_user_input(crs)
    if parsed_crs.is_geographic:
        raise SpatialMetadataError("a projected CRS is required")

    grid = GridSpec(
        width=values.shape[1],
        height=values.shape[0],
        pixel_width=pixel_width,
        pixel_height=pixel_height,
        crs=parsed_crs.to_string(),
    )
    return values.copy(), grid


def _grid_from_dataset(dataset: DatasetReader) -> GridSpec:
    if dataset.count != 1:
        raise InvalidRasterError("GeoTIFF input must contain exactly one band")
    if dataset.crs is None:
        raise SpatialMetadataError("GeoTIFF input must define a projected CRS")
    if dataset.crs.is_geographic:
        raise SpatialMetadataError("a projected CRS is required")

    transform = dataset.transform
    if transform.b != 0 or transform.d != 0 or transform.a <= 0 or transform.e >= 0:
        raise SpatialMetadataError("GeoTIFF transform must be north-up with no rotation or shear")

    return GridSpec(
        width=dataset.width,
        height=dataset.height,
        pixel_width=float(transform.a),
        pixel_height=float(abs(transform.e)),
        crs=dataset.crs.to_string(),
    )


def inspect_geotiff(path: Path | str) -> GridSpec:
    """Read only the structural metadata needed to validate a GeoTIFF."""
    grid, _ = inspect_geotiff_details(path)
    return grid


def inspect_geotiff_details(path: Path | str) -> tuple[GridSpec, int | None]:
    """Validate GeoTIFF metadata without reading the full raster band."""
    with rasterio.open(path) as dataset:
        grid = _grid_from_dataset(dataset)
        if not np.issubdtype(np.dtype(dataset.dtypes[0]), np.integer):
            raise InvalidRasterError("GeoTIFF input must contain integer categorical values")
        nodata_value = dataset.nodata

    if nodata_value is not None and not float(nodata_value).is_integer():
        raise InvalidRasterError("GeoTIFF NoData must be an integer for categorical input")
    return grid, None if nodata_value is None else int(nodata_value)


def read_geotiff(path: Path | str) -> tuple[np.ndarray, GridSpec, int | None]:
    """Read and validate a single-band integer categorical GeoTIFF."""
    with rasterio.open(path) as dataset:
        grid = _grid_from_dataset(dataset)
        values = dataset.read(1)
        nodata_value = dataset.nodata

    if nodata_value is not None and not float(nodata_value).is_integer():
        raise InvalidRasterError("GeoTIFF NoData must be an integer for categorical input")
    nodata = None if nodata_value is None else int(nodata_value)
    array, _ = read_array(
        values,
        pixel_width=grid.pixel_width,
        pixel_height=grid.pixel_height,
        crs=grid.crs or "",
        nodata=nodata,
    )
    return array, grid, nodata
