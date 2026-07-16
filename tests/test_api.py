import numpy as np
import rasterio
from rasterio.transform import from_origin

from landscape_metrics import Landscape


def test_landscape_api_returns_data_and_reproducibility_metadata() -> None:
    landscape = Landscape.from_array(
        np.array([[1, 1], [2, 2]], dtype=np.int16),
        pixel_width=30,
        pixel_height=30,
        crs="EPSG:6933",
        connectivity=4,
    )

    result = landscape.metrics()

    assert result.values.loc[0, "total_area"] == 3600.0
    assert result.metadata["connectivity"] == 4
    assert result.metadata["execution_path"] == "memory"
    assert result.metadata["nodata_policy"] == "excluded"


def test_landscape_api_exposes_each_frozen_metric_level() -> None:
    landscape = Landscape.from_array(
        np.array([[1, 1], [2, 2]], dtype=np.int16),
        pixel_width=30,
        pixel_height=30,
        crs="EPSG:6933",
    )

    assert set(landscape.patch_metrics().values["class_value"]) == {1, 2}
    assert set(landscape.class_metrics().values["class_value"]) == {1, 2}


def test_landscape_from_geotiff_uses_the_same_public_api(tmp_path) -> None:
    path = tmp_path / "classes.tif"
    values = np.array([[1, 1], [2, 2]], dtype=np.int16)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=2,
        width=2,
        count=1,
        dtype=values.dtype,
        crs="EPSG:6933",
        transform=from_origin(0, 60, 30, 30),
    ) as dataset:
        dataset.write(values, 1)

    result = Landscape.from_geotiff(path, connectivity=4).metrics()

    assert result.values.loc[0, "total_area"] == 3600.0
    assert result.metadata["execution_path"] == "memory"


def test_chunked_constructor_retains_path_without_reading_the_full_band(tmp_path, monkeypatch) -> None:
    path = tmp_path / "classes.tif"
    values = np.array([[1]], dtype=np.int16)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=1,
        width=1,
        count=1,
        dtype=values.dtype,
        crs="EPSG:6933",
        transform=from_origin(0, 30, 30, 30),
    ) as dataset:
        dataset.write(values, 1)

    monkeypatch.setattr(
        "landscape_metrics.io.read_geotiff",
        lambda _: (_ for _ in ()).throw(AssertionError("full raster read")),
    )

    landscape = Landscape.from_geotiff(path, tile_shape=(1, 1), tempdir=tmp_path)

    assert landscape._array is None
    assert landscape._path == path
