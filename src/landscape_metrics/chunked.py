"""Out-of-core backend entry point; implementation follows in the next task."""

from pathlib import Path

from .models import ChunkedResults, GridSpec, RunConfig


def compute_chunked(
    path: Path,
    *,
    grid: GridSpec,
    nodata: int | None,
    config: RunConfig,
) -> ChunkedResults:
    """Reserve the stable chunked-backend interface before its implementation."""
    del path, grid, nodata, config
    raise NotImplementedError("the chunked backend has not been implemented yet")
