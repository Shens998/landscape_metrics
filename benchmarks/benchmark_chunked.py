"""Record reproducible resource measurements for exact tiled GeoTIFF calculations."""

from __future__ import annotations

import argparse
import json
import resource
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

from landscape_metrics import Landscape
from landscape_metrics.chunked import required_temporary_bytes
from landscape_metrics.io import inspect_geotiff_details


DEFAULT_SEED = 20_260_716


def parse_args() -> argparse.Namespace:
    """Parse an existing input or deterministic synthetic-raster parameters."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="existing categorical GeoTIFF")
    parser.add_argument("--height", type=int, default=4096)
    parser.add_argument("--width", type=int, default=4096)
    parser.add_argument("--classes", type=int, default=8)
    parser.add_argument("--tile-shape", nargs=2, type=int, action="append")
    parser.add_argument("--tempdir", type=Path, help="parent directory for temporary work files")
    arguments = parser.parse_args()
    arguments.tile_shape = arguments.tile_shape or [(1024, 1024)]
    return arguments


def write_synthetic_raster(path: Path, *, height: int, width: int, classes: int) -> None:
    """Write a deterministic explicit-background categorical GeoTIFF."""
    if height < 1 or width < 1 or classes < 1:
        raise ValueError("height, width, and classes must be positive")
    values = np.random.default_rng(DEFAULT_SEED).integers(
        0, classes, size=(height, width), dtype=np.int16
    )
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype=values.dtype,
        crs="EPSG:6933",
        transform=from_origin(0, height * 30, 30, 30),
    ) as dataset:
        dataset.write(values, 1)


def peak_rss_bytes() -> int:
    """Return the platform-normalized peak resident set size for this process."""
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(peak if sys.platform == "darwin" else peak * 1024)


def benchmark(path: Path, *, tile_shape: tuple[int, int], tempdir: Path | None) -> dict[str, object]:
    """Run the public tiled API once and return a machine-readable measurement."""
    grid, _ = inspect_geotiff_details(path)
    start = time.perf_counter()
    landscape = Landscape.from_geotiff(path, tile_shape=tile_shape, tempdir=tempdir)
    patches = landscape.patch_metrics().values
    classes = landscape.class_metrics().values
    elapsed = time.perf_counter() - start
    return {
        "input": str(path),
        "tile_shape": list(tile_shape),
        "elapsed_seconds": elapsed,
        "peak_rss_bytes": peak_rss_bytes(),
        "temporary_budget_bytes": required_temporary_bytes(grid),
        "patch_rows": int(patches.shape[0]),
        "class_rows": int(classes.shape[0]),
    }


def main() -> None:
    """Benchmark a supplied GeoTIFF or a private deterministic temporary one."""
    args = parse_args()
    if args.input is not None:
        for shape in args.tile_shape:
            print(json.dumps(benchmark(args.input, tile_shape=tuple(shape), tempdir=args.tempdir)))
        return

    with tempfile.TemporaryDirectory(prefix="landscape-metrics-benchmark-") as name:
        path = Path(name) / "synthetic.tif"
        write_synthetic_raster(path, height=args.height, width=args.width, classes=args.classes)
        for shape in args.tile_shape:
            print(json.dumps(benchmark(path, tile_shape=tuple(shape), tempdir=args.tempdir)))


if __name__ == "__main__":
    main()
