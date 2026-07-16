# PyLandStats-Informed v0.1 Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Complete exact memory-bounded GeoTIFF execution, then add an independent, explicit metric-column selection API.

**Architecture:** The chunked backend emits canonical patch rows and AggregateSummary from window-level SQLite aggregation; existing patch, class, and landscape formula functions consume those summaries. A thin public selector validates requested metric IDs against metric_cards.yaml and filters cached full tables without changing computations or metadata.

**Tech Stack:** Python 3.11+, NumPy, Rasterio windows, numpy.memmap, SQLite, pandas, pytest, Hypothesis, Ruff, mypy.

## Global Constraints

- Keep the library an independent MIT implementation: do not copy PyLandStats/FRAGSTATS code, API names, wording, project formats, or compatibility claims.
- Keep frozen v0.1 metric semantics, input validation, NoData, explicit-background, 4/8 connectivity, side-edge, output-order, and metadata rules unchanged.
- Chunked execution may not create a full Topology, read the full source band, create full-grid masks, or write SQLite per cell.
- Window-local NumPy grouping and one SQLite transaction per window are required; temporary storage preflight remains 48 bytes/pixel.
- Metric selection changes result columns only; it may not alter numeric calculation, row ordering, cached complete results, or metadata.
- Do not add temporal, zonal, buffer, plotting, vector, Dask, GPU, CLI, GUI, or extra v0.1 metrics.

---

### Task 1: Materialize exact chunked tables from window summaries

**Files:**
- Modify: src/landscape_metrics/chunked.py
- Modify: tests/test_chunked.py

**Interfaces:**
- Produces _aggregate_windows(path, roots, grid, nodata, config, database) -> AggregateSummary.
- Produces _read_patch_records(database) -> list[dict[str, int | float]].
- Completes compute_chunked(path, *, grid, nodata, config) -> ChunkedResults.

- [ ] **Step 1: Extend the red public-equivalence fixture**

~~~python
def test_chunked_results_match_memory_for_cross_boundary_and_diagonal_patches(...):
    ...
    pd.testing.assert_frame_equal(memory.patch_metrics().values, chunked.patch_metrics().values)
    pd.testing.assert_frame_equal(memory.class_metrics().values, chunked.class_metrics().values)
    pd.testing.assert_frame_equal(memory.metrics().values, chunked.metrics().values)
    assert chunked.metrics().metadata["execution_path"] == "chunked"
~~~

Retain the existing six combinations: connectivity 4/8 and tile shapes (1, 2), (2, 1), (2, 2).

- [ ] **Step 2: Verify the red state**

Run: .venv/bin/python -m pytest tests/test_chunked.py::test_chunked_results_match_memory_for_cross_boundary_and_diagonal_patches -v

Expected: FAIL because compute_chunked raises NotImplementedError.

- [ ] **Step 3: Add a transaction-backed patch summary schema**

~~~sql
CREATE TABLE patches (
    root_label INTEGER PRIMARY KEY,
    class_value INTEGER NOT NULL,
    cell_count INTEGER NOT NULL,
    perimeter REAL NOT NULL,
    same_adjacency INTEGER NOT NULL,
    sum_row REAL NOT NULL,
    sum_col REAL NOT NULL,
    sum_row_sq REAL NOT NULL,
    sum_col_sq REAL NOT NULL,
    first_row INTEGER NOT NULL,
    first_col INTEGER NOT NULL
);
~~~

For each central window read source and root-label data with a clipped one-cell halo. Restrict labels, masks, coordinate arrays, np.unique, and np.bincount to the central window. Group valid central cells by root label and use one executemany UPSERT per window.

- [ ] **Step 4: Count edges and moments exactly**

For every valid central cell, count per-patch perimeter for each side whose neighbour is a different valid class, or outside the raster with boundary inclusion true. Ignore NoData neighbours. Count equal-class right/down pairs once. Accumulate valid-cell count, class cell counts, same adjacency, and landscape edge; landscape edge is right/down differing valid sides plus included exterior sides. Use global row/column indices for sum_row, sum_col, sum_row_sq, and sum_col_sq.

- [ ] **Step 5: Return canonical results and always clean temporary files**

~~~python
with tempfile.TemporaryDirectory(prefix="landscape-metrics-", dir=work_parent) as name:
    workdir = Path(name)
    roots = build_root_labels(path, grid=grid, nodata=nodata, config=config, workdir=workdir)
    # aggregate roots into SQLite, query canonical rows, and build ChunkedResults
~~~

Query patch rows with ORDER BY class_value, first_row, first_col; enumerate patch_id from 1. Call patch_metrics_from_summaries(records, grid), class_metrics(patches, summary), and landscape_metrics(classes, patches, summary). Do not remove caller-owned files.

- [ ] **Step 6: Verify and commit**

Run:
~~~bash
.venv/bin/python -m pytest tests/test_chunked.py tests/test_patch_metrics.py tests/test_class_metrics.py tests/test_landscape_metrics.py tests/test_api.py -v
.venv/bin/python -m ruff check src tests
.venv/bin/python -m mypy src
~~~

Expected: all listed tests PASS, including six memory/chunked equivalence cases.

~~~bash
git add src/landscape_metrics/chunked.py tests/test_chunked.py
git commit -m "feat: compute exact chunked metric tables"
~~~

### Task 2: Add explicit metric-column selection

**Files:**
- Modify: src/landscape_metrics/api.py
- Modify: src/landscape_metrics/metrics/__init__.py
- Create: src/landscape_metrics/selection.py
- Modify: tests/test_api.py

**Interfaces:**
- Adds metrics: Sequence[str] | None = None to patch_metrics, class_metrics, and metrics.
- Produces select_metric_columns(values: pd.DataFrame, *, level: Literal["patch", "class", "landscape"], requested: Sequence[str] | None) -> pd.DataFrame.
- Uses load_metric_cards() as the sole metric-ID registry.

- [ ] **Step 1: Write red selector tests**

~~~python
def test_class_metric_selection_keeps_identity_and_requested_order() -> None:
    result = Landscape.from_array(...).class_metrics(metrics=["edge_density", "total_area"])
    assert result.values.columns.tolist() == ["class_value", "edge_density", "total_area"]

def test_metric_selection_rejects_unknown_and_cross_level_ids() -> None:
    landscape = Landscape.from_array(...)
    with pytest.raises(ConfigurationError, match="unknown metric"):
        landscape.metrics(metrics=["not_a_metric"])
    with pytest.raises(ConfigurationError, match="not available at landscape level"):
        landscape.metrics(metrics=["perimeter"])
~~~

- [ ] **Step 2: Verify the red state**

Run: .venv/bin/python -m pytest tests/test_api.py -v

Expected: FAIL because public methods do not accept metrics.

- [ ] **Step 3: Implement registry-based validation and filtering**

~~~python
IDENTITY_COLUMNS = {"patch": ("patch_id", "class_value"), "class": ("class_value",), "landscape": ()}

def select_metric_columns(values, *, level, requested):
    if requested is None:
        return values.copy()
    requested = tuple(requested)
    if len(set(requested)) != len(requested):
        raise ConfigurationError("metric selection cannot contain duplicates")
    # validate every ID exists and declares level, then select identity columns + requested
    return values.loc[:, [*IDENTITY_COLUMNS[level], *requested]].copy()
~~~

Use the YAML card loader to validate IDs and levels. Error messages include available metric identifiers for the requested level.

- [ ] **Step 4: Verify selection and both execution paths**

Run:
~~~bash
.venv/bin/python -m pytest tests/test_api.py tests/test_chunked.py -v
.venv/bin/python -m ruff check src tests
.venv/bin/python -m mypy src
~~~

Expected: PASS; selection produces identical values to the full cached table subset for memory and chunked landscapes.

- [ ] **Step 5: Commit**

~~~bash
git add src/landscape_metrics/api.py src/landscape_metrics/metrics/__init__.py src/landscape_metrics/selection.py tests/test_api.py
git commit -m "feat: add explicit metric column selection"
~~~

### Task 3: Document non-compatibility and validate research-facing behavior

**Files:**
- Modify: README.md
- Create: docs/methods.md
- Modify: tests/test_release_docs.py
- Create: benchmarks/benchmark_chunked.py

- [ ] **Step 1: Write red documentation checks**

~~~python
def test_public_docs_describe_selection_and_exact_chunking_without_compatibility_claims() -> None:
    text = Path("README.md").read_text(encoding="utf-8") + Path("docs/methods.md").read_text(encoding="utf-8")
    assert "metrics=[\"edge_density\"]" in text
    assert "48 bytes/像元" in text
    assert "FRAGSTATS-compatible" not in text
    assert "PyLandStats-compatible" not in text
~~~

- [ ] **Step 2: Write documentation and reproducible benchmark**

Document metric selection, full versus chunked metadata, exact tile passes, NoData and adjacency rules, 48 bytes/pixel budget, and exclusions. The benchmark uses np.random.default_rng(20260716), accepts tile sizes, and reports wall time, peak RSS, temporary budget, patch rows, and class rows without fixed performance thresholds.

- [ ] **Step 3: Run final checks and commit**

Run:
~~~bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src tests tools benchmarks
.venv/bin/python -m mypy src
~~~

Expected: PASS with no warnings or diagnostics.

~~~bash
git add README.md docs/methods.md tests/test_release_docs.py benchmarks/benchmark_chunked.py
git commit -m "docs: explain exact chunking and metric selection"
~~~
