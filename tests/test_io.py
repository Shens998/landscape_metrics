import numpy as np
import pytest
import rasterio
from landscape_metrics import io as landscape_io
from affine import Affine
from rasterio.crs import CRS
from rasterio.transform import from_origin

from landscape_metrics.errors import InvalidRasterError, SpatialMetadataError
from landscape_metrics.io import inspect_geotiff, read_array, read_geotiff


def test_array_requires_two_dimensional_integer_categories() -> None:
    with pytest.raises(InvalidRasterError, match="two-dimensional integer"):
        read_array(
            np.array([[1.0, 2.0]]),
            pixel_width=30,
            pixel_height=30,
            crs="EPSG:6933",
            nodata=None,
        )


def test_array_rejects_geographic_crs_without_explicit_meter_scale() -> None:
    with pytest.raises(SpatialMetadataError, match="projected CRS"):
        read_array(
            np.array([[1]], dtype=np.int16),
            pixel_width=0.01,
            pixel_height=0.01,
            crs="EPSG:4326",
            nodata=None,
        )


def test_array_preserves_explicit_background_while_recording_nodata() -> None:
    values = np.array([[1, -9999], [0, 1]], dtype=np.int16)

    array, grid = read_array(
        values,
        pixel_width=30,
        pixel_height=30,
        crs=CRS.from_epsg(6933).to_string(),
        nodata=-9999,
    )

    assert array[1, 0] == 0
    assert array[0, 1] == -9999
    assert grid.width == 2
    assert grid.height == 2


def test_geotiff_reader_returns_single_band_array_and_grid(tmp_path) -> None:
    path = tmp_path / "categorical.tif"
    values = np.array([[1, -9999], [0, 1]], dtype=np.int16)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=2,
        width=2,
        count=1,
        dtype=values.dtype,
        crs="EPSG:6933",
        transform=from_origin(100, 200, 30, 30),
        nodata=-9999,
    ) as dataset:
        dataset.write(values, 1)

    array, grid, nodata = read_geotiff(path)

    assert array.tolist() == values.tolist()
    assert nodata == -9999
    assert grid.pixel_width == 30
    assert grid.pixel_height == 30
    assert inspect_geotiff(path) == grid
    assert landscape_io.inspect_geotiff_details(path) == (grid, -9999)


def test_geotiff_reader_rejects_rotated_transform(tmp_path) -> None:
    path = tmp_path / "rotated.tif"
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=1,
        width=1,
        count=1,
        dtype="int16",
        crs="EPSG:6933",
        transform=Affine(30, 1, 0, 0, -30, 0),
    ) as dataset:
        dataset.write(np.array([[1]], dtype=np.int16), 1)

    with pytest.raises(SpatialMetadataError, match="north-up"):
        read_geotiff(path)


def test_geotiff_reader_rejects_multiband_input(tmp_path) -> None:
    path = tmp_path / "multiband.tif"
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=1,
        width=1,
        count=2,
        dtype="int16",
        crs="EPSG:6933",
        transform=from_origin(0, 30, 30, 30),
    ) as dataset:
        dataset.write(np.array([[1]], dtype=np.int16), 1)
        dataset.write(np.array([[2]], dtype=np.int16), 2)

    with pytest.raises(InvalidRasterError, match="exactly one band"):
        inspect_geotiff(path)
