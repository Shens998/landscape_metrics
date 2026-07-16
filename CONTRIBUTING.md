# Contributing

Thank you for contributing to Open Landscape Metrics.

## Scope

This is an alpha research library for reproducible metrics from categorical LULC rasters. Contributions must preserve the independent implementation boundary: do not copy code, project formats, or compatibility claims from other landscape-metric software.

## Before opening a Pull Request

1. Describe the scientific rule, input assumptions, and expected result.
2. Add a regression test before changing calculation code.
3. Keep NoData, explicit background, 4/8 connectivity, and shared-side rules explicit.
4. Run the local checks:

~~~bash
python -m pytest -q
python -m ruff check src tests tools benchmarks
python -m mypy src
python -m build
~~~

Please avoid committing generated local files, test rasters, credentials, or user data.
