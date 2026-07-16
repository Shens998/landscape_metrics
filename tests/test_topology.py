import numpy as np

from landscape_metrics.models import GridSpec
from landscape_metrics.topology import build_topology, label_patches


GRID = GridSpec(width=2, height=2, pixel_width=30, pixel_height=30, crs="EPSG:6933")


def test_connectivity_changes_diagonal_patch_count() -> None:
    values = np.array([[1, 0], [0, 1]], dtype=np.int16)

    assert label_patches(values, nodata=None, connectivity=4).max() == 4
    assert label_patches(values, nodata=None, connectivity=8).max() == 2


def test_nodata_does_not_create_an_edge() -> None:
    values = np.array([[1, -9999]], dtype=np.int16)

    topology = build_topology(
        values,
        nodata=-9999,
        grid=GridSpec(width=2, height=1, pixel_width=30, pixel_height=30, crs="EPSG:6933"),
        connectivity=4,
        include_landscape_boundary=True,
    )

    assert topology.perimeter_by_patch[1] == 90.0


def test_square_patch_and_class_interfaces_have_auditable_lengths() -> None:
    solid = build_topology(np.ones((2, 2), dtype=np.int16), nodata=None, grid=GRID, connectivity=4)
    assert solid.perimeter_by_patch[1] == 240.0
    assert solid.same_adjacency_by_class[1] == 4

    split = build_topology(
        np.array([[1, 2]], dtype=np.int16),
        nodata=None,
        grid=GridSpec(width=2, height=1, pixel_width=30, pixel_height=30, crs="EPSG:6933"),
        connectivity=4,
    )
    assert split.class_edge_by_class == {1: 120.0, 2: 120.0}
    assert split.same_adjacency_by_class == {1: 0, 2: 0}
