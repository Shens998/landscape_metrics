"""Behavior checks for the reproducible chunked benchmark entry point."""

import sys

from benchmarks.benchmark_chunked import parse_args


def test_explicit_tile_shape_replaces_the_default(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["benchmark_chunked.py", "--tile-shape", "2", "3"])

    arguments = parse_args()

    assert arguments.tile_shape == [[2, 3]]
