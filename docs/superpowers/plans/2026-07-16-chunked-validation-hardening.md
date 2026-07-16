# Chunked Validation Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Prove that the exact tiled GeoTIFF path preserves v0.1 results under NoData, explicit-background, non-square-pixel, random-grid, and temporary-directory conditions.

**Architecture:** Extend tests/test_chunked.py around the existing public Landscape.from_geotiff API, comparing complete public result tables rather than implementation internals. Test fixtures write small projected GeoTIFFs; all tiled work is directed to pytest-owned temporary directories. No source change is authorized unless a new regression test exposes a concrete difference.

**Tech Stack:** Python 3.11+, NumPy, pandas, Rasterio, Hypothesis, pytest, Ruff, mypy.

## Global Constraints

- Do not add metrics, public API, CLI, new input formats, parallelism, auto tile sizing, or dependencies.
- Keep all 21 v0.1 metric IDs, result columns, NoData/background behavior, 4/8 connectivity, and side-edge semantics unchanged.
- Keep tiled execution out of core memory: no complete source-band read, full-grid topology, or per-cell SQLite writes.
- Only modify production code after a failing public-equivalence regression test identifies a root cause.
- Preserve caller-owned temporary directories and source GeoTIFFs; only private landscape-metrics-* work directories may be removed.

---

### Task 1: Deterministic rule-matrix and cleanup regressions

**Files:**

- Modify: tests/test_chunked.py

**Interfaces:**

- _write_grid(path, values, *, pixel_width=30, pixel_height=30, nodata=-1) -> None writes a projected categorical GeoTIFF with caller-selected spatial metadata.
- _assert_public_tables_equal(memory: Landscape, tiled: Landscape) -> None compares patch, class, and landscape result tables via pd.testing.assert_frame_equal.

- [ ] **Step 1: Write the rule-matrix regression**

~~~python
@pytest.mark.parametrize("connectivity", [4, 8])
@pytest.mark.parametrize("tile_shape", [(1, 2), (2, 1), (2, 2)])
def test_chunked_matches_memory_for_nodata_background_and_non_square_pixels(
    tmp_path, connectivity, tile_shape
) -> None:
    path = tmp_path / "rules.tif"
    _write_grid(
        path,
        np.array([[0, -1, 1], [0, 1, 1], [2, 2, -1]], dtype=np.int16),
        pixel_width=20,
        pixel_height=30,
    )
    memory = Landscape.from_geotiff(path, connectivity=connectivity)
    tiled = Landscape.from_geotiff(
        path, connectivity=connectivity, tile_shape=tile_shape, tempdir=tmp_path
    )
    _assert_public_tables_equal(memory, tiled)
~~~

- [ ] **Step 2: Write the successful-work-directory cleanup regression**

~~~python
def test_chunked_success_cleans_only_its_private_work_directory(tmp_path) -> None:
    path = tmp_path / "input.tif"
    _write_grid(path, np.array([[0, 1], [1, 0]], dtype=np.int16))
    tiled = Landscape.from_geotiff(path, tile_shape=(1, 1), tempdir=tmp_path)
    tiled.metrics()
    assert path.exists()
    assert not list(tmp_path.glob("landscape-metrics-*"))
~~~

- [ ] **Step 3: Run the deterministic validations**

Run: .venv/bin/python -m pytest tests/test_chunked.py -v

Expected: all existing and new deterministic cases PASS. If an equivalence case fails, stop this plan and use superpowers:systematic-debugging before editing production code.

- [ ] **Step 4: Commit deterministic coverage**

~~~bash
git add tests/test_chunked.py
git commit -m "test: cover chunked raster boundary rules"
~~~

### Task 2: Randomized public-equivalence property

**Files:**

- Modify: tests/test_chunked.py

**Interfaces:**

- Uses hypothesis.given only through the public GeoTIFF API.
- Generates values from [-1, 0, 1, 2], with -1 written as NoData and at least one valid cell.

- [ ] **Step 1: Write the random-grid property**

~~~python
@settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    data=st.data(),
    height=st.integers(min_value=1, max_value=5),
    width=st.integers(min_value=1, max_value=5),
    connectivity=st.sampled_from([4, 8]),
)
def test_chunked_matches_memory_for_random_small_categorical_grids(
    tmp_path, data, height, width, connectivity
) -> None:
    flat = data.draw(
        st.lists(st.sampled_from([-1, 0, 1, 2]), min_size=height * width, max_size=height * width)
    )
    values = np.array(flat, dtype=np.int16).reshape(height, width)
    assume(np.any(values != -1))
    tile_shape = (
        data.draw(st.integers(min_value=1, max_value=height)),
        data.draw(st.integers(min_value=1, max_value=width)),
    )
    path = tmp_path / "random.tif"
    _write_grid(path, values, pixel_width=20, pixel_height=30)
    memory = Landscape.from_geotiff(path, connectivity=connectivity)
    tiled = Landscape.from_geotiff(path, connectivity=connectivity, tile_shape=tile_shape, tempdir=tmp_path)
    _assert_public_tables_equal(memory, tiled)
~~~

- [ ] **Step 2: Run the property test**

Run: .venv/bin/python -m pytest tests/test_chunked.py::test_chunked_matches_memory_for_random_small_categorical_grids -v

Expected: PASS for all 20 generated examples. If it fails, preserve the Hypothesis example and use systematic debugging before implementation changes.

- [ ] **Step 3: Run full verification and commit**

Run:

~~~bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src tests tools benchmarks
.venv/bin/python -m mypy src
~~~

Commit:

~~~bash
git add tests/test_chunked.py
git commit -m "test: add chunked equivalence property coverage"
~~~

### Task 3: Record completed coverage

**Files:**

- Modify: docs/superpowers/progress/2026-07-16-v0-1-development-progress.md
- Create: docs/superpowers/specs/2026-07-16-chunked-validation-hardening.md
- Create: docs/superpowers/plans/2026-07-16-chunked-validation-hardening.md

**Interfaces:**

- Progress record names the completed rule matrix, randomized property, successful cleanup check, validation commands, and current branch/worktree without claiming new API or metric support.

- [ ] **Step 1: Update the progress record**

Replace its obsolete “next step” statement with the completed validation coverage, current command outputs, and the rule that any future production change starts from a failing public-equivalence test.

- [ ] **Step 2: Run documentation and test verification**

Run:

~~~bash
.venv/bin/python -m pytest tests/test_release_docs.py tests/test_chunked.py -v
.venv/bin/python -m ruff check src tests tools benchmarks
~~~

- [ ] **Step 3: Commit the durable record**

~~~bash
git add docs/superpowers/progress/2026-07-16-v0-1-development-progress.md docs/superpowers/specs/2026-07-16-chunked-validation-hardening.md docs/superpowers/plans/2026-07-16-chunked-validation-hardening.md
git commit -m "docs: record chunked validation coverage"
~~~
