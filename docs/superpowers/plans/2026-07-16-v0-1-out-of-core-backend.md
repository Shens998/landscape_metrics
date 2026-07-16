# Open Landscape Metrics v0.1 Out-of-Core Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** 让单波段分类 GeoTIFF 在用户指定块大小时，以受控的单机内存精确计算 v0.1 的斑块、类别和景观指标，并与现有内存路径返回相同的表格。

**Architecture:** Landscape 在 tile_shape 存在时保留 GeoTIFF 路径，而不读取完整数组。chunked.py 顺次执行块内暂定标签、跨块磁盘并查集合并、根标签重写和带一像元 halo 的流式摘要聚合，直接产生三级 DataFrame。AggregateSummary 是内存与分块后端共用的基础量接口，使类别与景观公式只有一份实现。

**Tech Stack:** Python 3.11+, NumPy, SciPy ndimage.label（仅单块）, Rasterio windows, numpy.memmap, SQLite, pandas, pytest, Hypothesis, Ruff, mypy.

## Global Constraints

- 仅处理现有严格验证通过的单波段、二维整数、投影且北向上的分类 GeoTIFF；from_array 始终使用内存路径。
- tile_shape=(rows, cols) 明确选择分块路径；块大小必须为正整数，v0.1 不自动选择块大小，不使用 Dask、GPU、多进程或分布式调度。
- connectivity 仅决定 4/8 邻域斑块连通；周长、total_edge 和 aggregation_index 的同类邻接只使用共享边。
- NoData 排除面积、边和邻接；背景是显式类别。景观外边界按 include_landscape_boundary=True 计入，规则必须与 topology.build_topology 相同。
- 全图范围内不得调用 np.unique、ndimage.label 或创建全图布尔掩码；这些操作只允许在单块或一像元 halo 内。
- 分块路径不得构造 Topology、完整读取源 GeoTIFF，或逐像元写 SQLite；SQLite 写入必须按块分组、批量事务执行。
- 计算前用 shutil.disk_usage 对 tempdir 做 48 bytes/像元预检；空间不足抛出 TemporaryStorageError，且不创建临时文件。
- 临时文件格式版本为 v1；TemporaryDirectory 清理成功和异常退出的工作子目录。元数据记录 execution_path="chunked"、tile_shape、temporary_storage_format 和 temporary_storage_budget_bytes。
- 最终斑块按 (class_value, first_row, first_col) 排序，重编号为 patch_id=1..n；这复现内存路径按类别升序、每类行优先扫描标签的顺序。
- 所有实现步骤测试先行。每个任务在专用测试、Ruff、mypy 通过后独立提交。

## File Structure

~~~text
src/landscape_metrics/
  api.py                    # 后端调度和结果缓存
  chunked.py                # windows、memmap、并查集、SQLite、聚合
  io.py                     # 只读 GeoTIFF 元数据检查
  models.py                 # AggregateSummary、ChunkedResults
  metrics/patch.py          # 从斑块摘要创建固定 patch 表
  metrics/summary.py        # Topology 与 AggregateSummary 的单一适配器
  metrics/class_level.py    # 从 AggregateSummary 聚合 class 表
  metrics/landscape.py      # 从 AggregateSummary 聚合 landscape 表
tests/test_chunked.py       # 小块等价、连接、NoData、预检、清理
tests/test_properties.py    # 随机小栅格块大小等价
benchmarks/benchmark_chunked.py
docs/methods.md
~~~

---

### Task 1: Establish backend-neutral contracts and GeoTIFF dispatch

**Files:**
- Modify: src/landscape_metrics/models.py
- Modify: src/landscape_metrics/io.py
- Modify: src/landscape_metrics/api.py
- Modify: tests/test_models.py
- Modify: tests/test_io.py
- Modify: tests/test_api.py
- Modify: tests/test_chunked.py

**Interfaces:**
- Produces AggregateSummary(grid, valid_cell_count, class_cell_counts, same_adjacency_by_class, class_edge_by_class, landscape_edge).
- Produces ChunkedResults(patches: pd.DataFrame, classes: pd.DataFrame, landscape: pd.DataFrame).
- Produces inspect_geotiff_details(path) -> tuple[GridSpec, int | None] without reading band values.
- Extends Landscape.from_geotiff(path, *, connectivity=8, tile_shape=None, tempdir=None). With tile_shape, _array is None and _path is retained.

- [ ] **Step 1: Write failing constructor and contract tests**

~~~python
def test_chunked_constructor_keeps_path_without_reading_band(tmp_path, monkeypatch) -> None:
    path = _write_grid(tmp_path / "classes.tif", np.array([[1]], dtype=np.int16))
    monkeypatch.setattr(
        "landscape_metrics.io.read_geotiff",
        lambda _: (_ for _ in ()).throw(AssertionError("full read")),
    )
    landscape = Landscape.from_geotiff(path, tile_shape=(1, 1), tempdir=tmp_path)
    assert landscape._array is None
    assert landscape._path == path

def test_aggregate_summary_rejects_negative_cell_counts() -> None:
    with pytest.raises(ConfigurationError, match="valid_cell_count"):
        AggregateSummary(GRID, -1, {}, {}, {}, 0.0)
~~~

- [ ] **Step 2: Run the test to establish red state**

Run: .venv/bin/python -m pytest tests/test_models.py tests/test_io.py tests/test_api.py tests/test_chunked.py -v

Expected: FAIL because the summary contracts and tile constructor arguments do not exist.

- [ ] **Step 3: Add contracts and metadata-only inspection**

~~~python
@dataclass(frozen=True, slots=True)
class AggregateSummary:
    grid: GridSpec
    valid_cell_count: int
    class_cell_counts: dict[int, int]
    same_adjacency_by_class: dict[int, int]
    class_edge_by_class: dict[int, float]
    landscape_edge: float

    def __post_init__(self) -> None:
        if self.valid_cell_count < 0:
            raise ConfigurationError("valid_cell_count must be non-negative")

@dataclass(frozen=True, slots=True)
class ChunkedResults:
    patches: pd.DataFrame
    classes: pd.DataFrame
    landscape: pd.DataFrame

def inspect_geotiff_details(path: Path | str) -> tuple[GridSpec, int | None]:
    with rasterio.open(path) as dataset:
        grid = _grid_from_dataset(dataset)
        if not np.issubdtype(np.dtype(dataset.dtypes[0]), np.integer):
            raise InvalidRasterError("GeoTIFF input must contain integer categorical values")
        value = dataset.nodata
    if value is not None and not float(value).is_integer():
        raise InvalidRasterError("GeoTIFF NoData must be an integer for categorical input")
    return grid, None if value is None else int(value)
~~~

Keep inspect_geotiff(path) as a GridSpec wrapper. Make Landscape._array optional, add _path and _chunked_cache. from_geotiff calls read_geotiff only for memory mode; chunked mode calls inspect_geotiff_details. Its three public metric methods select cached compute_chunked results when tile_shape is present and return copied DataFrames plus metadata.

- [ ] **Step 4: Run focused validation**

Run:

~~~bash
.venv/bin/python -m pytest tests/test_models.py tests/test_io.py tests/test_api.py -v
.venv/bin/python -m ruff check src tests
.venv/bin/python -m mypy src
~~~

Expected: PASS. The metric-equivalence test in tests/test_chunked.py remains red until Task 3.

- [ ] **Step 5: Commit the dispatch boundary**

~~~bash
git add src/landscape_metrics/models.py src/landscape_metrics/io.py src/landscape_metrics/api.py tests/test_models.py tests/test_io.py tests/test_api.py
git commit -m "feat: add chunked GeoTIFF dispatch contracts"
~~~

### Task 2: Add preflight, local labels, and deterministic disk union-find

**Files:**
- Create: src/landscape_metrics/chunked.py
- Modify: tests/test_chunked.py

**Interfaces:**
- Produces required_temporary_bytes(grid: GridSpec) -> int, exactly 48 * width * height.
- Produces preflight_temporary_storage(tempdir: Path | None, grid: GridSpec) -> Path.
- Produces compute_chunked(path: Path, *, grid: GridSpec, nodata: int | None, config: RunConfig) -> ChunkedResults.
- Internal DiskUnionFind uses parent.memmap and makes the smaller root the parent.

- [ ] **Step 1: Write failing preflight and diagonal-crossing tests**

~~~python
def test_chunked_preflight_fails_before_creating_work_directory(tmp_path, monkeypatch) -> None:
    grid = GridSpec(width=10, height=10, pixel_width=30, pixel_height=30, crs="EPSG:6933")
    usage = namedtuple("Usage", "total used free")(0, 0, 4_799)
    monkeypatch.setattr(shutil, "disk_usage", lambda _: usage)
    with pytest.raises(TemporaryStorageError, match="4800.*4799"):
        preflight_temporary_storage(tmp_path, grid)
    assert list(tmp_path.iterdir()) == []

@pytest.mark.parametrize("connectivity, patch_count", [(4, 4), (8, 2)])
def test_chunked_joins_diagonal_components_across_four_tile_corner(tmp_path, connectivity, patch_count) -> None:
    path = _write_grid(tmp_path / "diagonal.tif", np.array([[1, 0], [0, 1]], dtype=np.int16))
    result = Landscape.from_geotiff(path, connectivity=connectivity, tile_shape=(1, 1), tempdir=tmp_path)
    assert len(result.patch_metrics().values) == patch_count
~~~

- [ ] **Step 2: Run the focused red test**

Run: .venv/bin/python -m pytest tests/test_chunked.py -v

Expected: FAIL because preflight, disk labels, and compute_chunked are absent.

- [ ] **Step 3: Implement preflight and window iterator**

~~~python
def required_temporary_bytes(grid: GridSpec) -> int:
    return 48 * grid.width * grid.height

def preflight_temporary_storage(tempdir: Path | None, grid: GridSpec) -> Path:
    directory = Path(tempdir) if tempdir is not None else Path(tempfile.gettempdir())
    if not directory.is_dir():
        raise TemporaryStorageError(f"temporary directory does not exist: {directory}")
    required = required_temporary_bytes(grid)
    free = shutil.disk_usage(directory).free
    if free < required:
        raise TemporaryStorageError(
            f"temporary storage requires {required} bytes but {free} bytes are free; choose another tempdir"
        )
    return directory

def iter_windows(grid: GridSpec, tile_shape: tuple[int, int]) -> Iterator[Window]:
    for row_off in range(0, grid.height, tile_shape[0]):
        for col_off in range(0, grid.width, tile_shape[1]):
            yield Window(col_off, row_off, min(tile_shape[1], grid.width - col_off), min(tile_shape[0], grid.height - row_off))
~~~

The preflight runs before TemporaryDirectory. Every Rasterio read uses a window.

- [ ] **Step 4: Implement first pass and boundary-only union**

For each window, run label_patches only on that tile, add a monotonic int64 offset to positive labels, and write labels.memmap. Initialise parent.memmap in tile-sized ranges, never with a full-grid np.arange. Batch-insert provisional components once per tile:

~~~sql
CREATE TABLE provisional_components (
    provisional_label INTEGER PRIMARY KEY,
    class_value INTEGER NOT NULL,
    cell_count INTEGER NOT NULL
);
~~~

Compare one-column strips across vertical tile boundaries and one-row strips across horizontal boundaries. Only union nonzero labels with matching categorical values. With 8 connectivity, also compare each strip with +1 and -1 shifts along its long axis; those comparisons cover four-tile-corner diagonals. De-duplicate pairs on that boundary before union. With 4 connectivity, compare only directly opposing cells.

- [ ] **Step 5: Flatten roots in bounded strips**

~~~python
for start in range(0, grid.width * grid.height, chunk_cells):
    stop = min(start + chunk_cells, grid.width * grid.height)
    labels = label_memmap.reshape(-1)[start:stop]
    roots = np.fromiter((uf.find(int(label)) if label else 0 for label in labels), dtype=np.int64)
    root_memmap.reshape(-1)[start:stop] = roots
~~~

Set chunk_cells to max(1, tile_shape[0] * tile_shape[1]), flush both memmaps, and use root labels only after flattening finishes.

- [ ] **Step 6: Run labels/preflight checks and commit**

Run:

~~~bash
.venv/bin/python -m pytest tests/test_chunked.py -v
.venv/bin/python -m ruff check src tests
.venv/bin/python -m mypy src
~~~

Expected: quota and diagonal-connectivity tests PASS. Full metric-equivalence tests can remain red until Task 3.

~~~bash
git add src/landscape_metrics/chunked.py tests/test_chunked.py
git commit -m "feat: add disk-backed tile labeling and union"
~~~

### Task 3: Stream patch summaries and reuse formula aggregations

**Files:**
- Modify: src/landscape_metrics/chunked.py
- Modify: src/landscape_metrics/metrics/patch.py
- Create: src/landscape_metrics/metrics/summary.py
- Modify: src/landscape_metrics/metrics/class_level.py
- Modify: src/landscape_metrics/metrics/landscape.py
- Modify: src/landscape_metrics/api.py
- Modify: tests/test_chunked.py
- Modify: tests/test_class_metrics.py
- Modify: tests/test_landscape_metrics.py

**Interfaces:**
- Produces patch_metrics_from_summaries(records, grid) -> pd.DataFrame.
- Produces patch_radius_of_gyration_from_moments(..., grid) -> float.
- class_metrics and landscape_metrics accept Topology or AggregateSummary and preserve their existing columns and formulas.
- compute_chunked returns ChunkedResults entirely from summaries, never a Topology.

- [ ] **Step 1: Write red tests for NoData, non-square pixels, and formula reuse**

~~~python
@pytest.mark.parametrize("tile_shape", [(1, 2), (2, 1), (2, 2)])
def test_chunked_matches_memory_for_nodata_background_and_non_square_pixels(tmp_path, tile_shape) -> None:
    values = np.array([[0, -1, 1], [0, 1, 1], [2, 2, -1]], dtype=np.int16)
    path = _write_grid(tmp_path / "rules.tif", values, pixel_width=20, pixel_height=30, nodata=-1)
    memory = Landscape.from_geotiff(path, connectivity=8)
    tiled = Landscape.from_geotiff(path, connectivity=8, tile_shape=tile_shape, tempdir=tmp_path)
    for method in ("patch_metrics", "class_metrics", "metrics"):
        pd.testing.assert_frame_equal(getattr(memory, method)().values, getattr(tiled, method)().values)

def test_summary_path_preserves_class_columns() -> None:
    topology = build_topology(
        np.array([[1, 1], [2, 2]], dtype=np.int16),
        nodata=None, grid=GRID, connectivity=4,
    )
    patches = patch_metrics(topology)
    assert class_metrics(patches, summary_from_topology(topology)).columns.tolist() == class_metrics(patches, topology).columns.tolist()
~~~

- [ ] **Step 2: Run aggregation tests to verify red state**

Run: .venv/bin/python -m pytest tests/test_chunked.py tests/test_class_metrics.py tests/test_landscape_metrics.py -v

Expected: FAIL because streamed aggregation and summary adapters are absent.

- [ ] **Step 3: Implement halo aggregation and batch SQLite upserts**

Use this temporary table:

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

For each central window, read a clipped one-cell source and root-label halo. Restrict masks, np.unique, np.bincount, and coordinate arrays to the central tile. Each valid central cell contributes a perimeter side when its side neighbour is a different valid category, or when it is outside the raster and boundary inclusion is enabled. A NoData neighbour contributes nothing. Count equal-category right/down side pairs once. Group by root label in NumPy and issue one executemany UPSERT per tile. Independently accumulate landscape edge as right/down different-valid sides plus each included exterior side, matching _landscape_edge.

- [ ] **Step 4: Convert moments to canonical patch rows and adapt formulas**

~~~python
def patch_radius_of_gyration_from_moments(
    *, cell_count: int, sum_row: float, sum_col: float,
    sum_row_sq: float, sum_col_sq: float, grid: GridSpec,
) -> float:
    mean_row = sum_row / cell_count
    mean_col = sum_col / cell_count
    row_variance = (sum_row_sq / cell_count - mean_row**2) * grid.pixel_height**2
    col_variance = (sum_col_sq / cell_count - mean_col**2) * grid.pixel_width**2
    return math.sqrt(max(0.0, row_variance + col_variance))
~~~

Read the final patch table with ORDER BY class_value, first_row, first_col and enumerate patch_id from one. Derive class edge from the sum of patch perimeters by class. Build AggregateSummary with class cell counts, same-side counts, class edges and the separately accumulated landscape edge.

Create metrics/summary.py with summary_from_topology(topology) -> AggregateSummary. At the beginning of class_metrics and landscape_metrics, normalize Topology through that one adapter; subsequently use only AggregateSummary fields. Retain function names and output order.

- [ ] **Step 5: Run equivalence and quality checks**

Run:

~~~bash
.venv/bin/python -m pytest tests/test_chunked.py tests/test_patch_metrics.py tests/test_class_metrics.py tests/test_landscape_metrics.py tests/test_api.py -v
.venv/bin/python -m ruff check src tests
.venv/bin/python -m mypy src
~~~

Expected: PASS for 4/8 connectivity and all declared tile shapes. Patch, class and landscape tables equal memory results, and metadata contains execution_path == "chunked".

- [ ] **Step 6: Commit the exact result path**

~~~bash
git add src/landscape_metrics/chunked.py src/landscape_metrics/metrics src/landscape_metrics/api.py tests/test_chunked.py tests/test_patch_metrics.py tests/test_class_metrics.py tests/test_landscape_metrics.py tests/test_api.py
git commit -m "feat: compute exact metrics from streamed patch summaries"
~~~

### Task 4: Verify cleanup, ordering, and randomized equivalence

**Files:**
- Modify: src/landscape_metrics/chunked.py
- Modify: tests/test_chunked.py
- Create: tests/test_properties.py

**Interfaces:**
- A fresh TemporaryDirectory(prefix="landscape-metrics-", dir=preflight_directory) surrounds every uncached chunked calculation.
- The property suite uses categorical values {-1, 0, 1, 2}, reserves -1 as NoData, and checks all legal tile modes against memory mode.

- [ ] **Step 1: Write red cleanup/order/property tests**

~~~python
def test_chunked_patch_ids_are_independent_of_tile_shape(tmp_path) -> None:
    path = _write_grid(tmp_path / "order.tif", np.array([[2, 1, 1], [2, 2, 1]], dtype=np.int16))
    first = Landscape.from_geotiff(path, tile_shape=(1, 1), tempdir=tmp_path).patch_metrics().values
    second = Landscape.from_geotiff(path, tile_shape=(2, 2), tempdir=tmp_path).patch_metrics().values
    pd.testing.assert_frame_equal(first, second)

def test_chunked_removes_work_directory_after_failure(tmp_path, monkeypatch) -> None:
    path = _write_grid(tmp_path / "failure.tif", np.array([[1]], dtype=np.int16))
    monkeypatch.setattr("landscape_metrics.chunked._aggregate_windows", lambda **_: (_ for _ in ()).throw(RuntimeError("boom")))
    with pytest.raises(RuntimeError, match="boom"):
        Landscape.from_geotiff(path, tile_shape=(1, 1), tempdir=tmp_path).metrics()
    assert not list(tmp_path.glob("landscape-metrics-*"))
~~~

Use Hypothesis rectangular 1..5 row/column matrices, at least one valid cell, 30 examples, 4/8 connectivity, and tile shapes (1,1), (1,width), (height,1), and (height,width).

- [ ] **Step 2: Run the red tests**

Run: .venv/bin/python -m pytest tests/test_chunked.py tests/test_properties.py -v

Expected: FAIL until cleanup is exception-safe and property generators exist.

- [ ] **Step 3: Implement cleanup and property fixtures**

Wrap all memmap allocation, SQLite work, and aggregation in TemporaryDirectory; close SQLite and flush/delete memmap handles before the context exits. Do not remove caller-owned paths. Each property example creates an isolated child temporary directory and asserts the patch, class and landscape DataFrames equal memory mode.

- [ ] **Step 4: Run regressions and commit**

Run:

~~~bash
.venv/bin/python -m pytest tests/test_chunked.py tests/test_properties.py -v
.venv/bin/python -m ruff check src tests
.venv/bin/python -m mypy src
~~~

Expected: PASS with no landscape-metrics-* directory remaining in the caller-supplied temp root.

~~~bash
git add src/landscape_metrics/chunked.py tests/test_chunked.py tests/test_properties.py
git commit -m "test: cover chunked cleanup and tile invariants"
~~~

### Task 5: Add benchmark and public method documentation

**Files:**
- Create: benchmarks/benchmark_chunked.py
- Create: docs/methods.md
- Modify: README.md
- Create: tests/test_release_docs.py

**Interfaces:**
- Benchmark accepts --tile-rows and --tile-cols, makes a deterministic 4096x4096 synthetic GeoTIFF, and reports wall time, peak RSS, temporary-budget bytes, and output row counts.
- Documentation describes the exact algorithm and does not claim FRAGSTATS compatibility.

- [ ] **Step 1: Write failing documentation check**

~~~python
def test_methods_document_states_exact_storage_policy() -> None:
    text = Path("docs/methods.md").read_text(encoding="utf-8")
    assert "48 bytes/像元" in text
    assert "精确" in text
    assert "FRAGSTATS-compatible" not in text
~~~

- [ ] **Step 2: Run the red documentation check**

Run: .venv/bin/python -m pytest tests/test_release_docs.py -v

Expected: FAIL until docs/methods.md and the test module assertion exist.

- [ ] **Step 3: Add reproducible benchmark and methods content**

Benchmark uses np.random.default_rng(20260716), time.perf_counter, resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, and required_temporary_bytes(grid). It reports observations but contains no machine-specific time/RSS threshold.

Methods documentation states input constraints; connectivity versus side adjacency; NoData and exterior rules; local labels, boundary union and halo aggregation; canonical patch ordering; 48 bytes/像元 preflight; cleanup; exact-not-sampled status; and v0.1 exclusions (Dask, GPU, vector, moving window, global distance/graph metrics). README links to this document and includes tile_shape=(2048, 2048).

- [ ] **Step 4: Run final backend checks and commit**

Run:

~~~bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src tests tools benchmarks
.venv/bin/python -m mypy src
~~~

Expected: PASS with a fresh test count and zero Ruff/mypy diagnostics.

~~~bash
git add benchmarks/benchmark_chunked.py docs/methods.md README.md tests/test_release_docs.py
git commit -m "docs: document and benchmark exact chunked metrics"
~~~

## Final Verification and Handoff

- [ ] Run .venv/bin/python benchmarks/benchmark_chunked.py --tile-rows 512 --tile-cols 512 on a scratch directory with at least the printed 48 bytes/像元 budget; record wall time, peak RSS, budget and patch/class rows without treating one machine as a release threshold.
- [ ] Run git diff --check and git status --short; only intentional release work may remain.
- [ ] Confirm no source or document claims FRAGSTATS compatibility, and both memory and chunked metadata include frozen rules plus execution-path-specific fields.
