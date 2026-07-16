from collections import namedtuple
import shutil

import numpy as np
import pandas as pd
import pytest
import rasterio
from rasterio.transform import from_origin

from landscape_metrics import Landscape
from landscape_metrics import chunked
from landscape_metrics.errors import TemporaryStorageError
from landscape_metrics.models import GridSpec, RunConfig


def _write_grid(path, values: np.ndarray) -> None:
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=values.shape[0],
        width=values.shape[1],
        count=1,
        dtype=values.dtype,
        crs="EPSG:6933",
        transform=from_origin(0, values.shape[0] * 30, 30, 30),
        nodata=-1,
    ) as dataset:
        dataset.write(values, 1)


@pytest.mark.parametrize("connectivity", [4, 8])
@pytest.mark.parametrize("tile_shape", [(1, 2), (2, 1), (2, 2)])
def test_chunked_results_match_memory_for_cross_boundary_and_diagonal_patches(
    tmp_path,
    connectivity,
    tile_shape,
) -> None:
    path = tmp_path / "grid.tif"
    _write_grid(
        path,
        np.array([[1, 0, 1], [0, 1, 0], [2, 2, 2]], dtype=np.int16),
    )

    memory = Landscape.from_geotiff(path, connectivity=connectivity)
    chunked = Landscape.from_geotiff(
        path,
        connectivity=connectivity,
        tile_shape=tile_shape,
        tempdir=tmp_path,
    )

    pd.testing.assert_frame_equal(memory.patch_metrics().values, chunked.patch_metrics().values)
    pd.testing.assert_frame_equal(memory.class_metrics().values, chunked.class_metrics().values)
    pd.testing.assert_frame_equal(memory.metrics().values, chunked.metrics().values)
    assert chunked.metrics().metadata["execution_path"] == "chunked"


def test_chunked_preflight_fails_before_creating_a_work_directory(tmp_path, monkeypatch) -> None:
    grid = GridSpec(width=10, height=10, pixel_width=30, pixel_height=30, crs="EPSG:6933")
    usage = namedtuple("Usage", "total used free")(0, 0, 4_799)
    monkeypatch.setattr(shutil, "disk_usage", lambda _: usage)

    with pytest.raises(TemporaryStorageError, match="4800.*4799"):
        chunked.preflight_temporary_storage(tmp_path, grid)

    assert list(tmp_path.iterdir()) == []


def test_disk_union_find_keeps_the_smallest_root(tmp_path) -> None:
    parent = np.memmap(tmp_path / "parent.memmap", dtype=np.int64, mode="w+", shape=(10,))
    parent[:] = np.arange(10)
    union_find = chunked.DiskUnionFind(parent)

    union_find.union(9, 4)
    union_find.union(4, 3)

    assert union_find.find(9) == 3
    assert union_find.find(4) == 3


@pytest.mark.parametrize("connectivity, joins_diagonals", [(4, False), (8, True)])
def test_root_labels_apply_the_requested_cross_tile_connectivity(
    tmp_path,
    connectivity,
    joins_diagonals,
) -> None:
    path = tmp_path / "diagonal.tif"
    values = np.array([[1, 0], [0, 1]], dtype=np.int16)
    _write_grid(path, values)
    grid = GridSpec(width=2, height=2, pixel_width=30, pixel_height=30, crs="EPSG:6933")
    workdir = tmp_path / "work"
    workdir.mkdir()

    roots = chunked.build_root_labels(
        path,
        grid=grid,
        nodata=-1,
        config=RunConfig(connectivity=connectivity, tile_shape=(1, 1)),
        workdir=workdir,
    )

    assert bool(roots[0, 0] == roots[1, 1]) is joins_diagonals
    assert bool(roots[0, 1] == roots[1, 0]) is joins_diagonals
