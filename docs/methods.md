# Methods and reproducibility / 方法与可复现性

## Scope / 范围

Open Landscape Metrics is an independent MIT-licensed implementation for categorical LULC rasters. It derives the frozen v0.1 metric set from public definitions and the linked literature in [metrics.md](metrics.md). It does not invoke external landscape-metric software, read another project's files, or offer a compatibility layer.

Open Landscape Metrics 是面向分类 LULC 栅格的独立 MIT 实现。v0.1 指标以公开定义和 [metrics.md](metrics.md) 中链接的原始文献为依据；本库不调用外部景观格局软件、不读取其他项目的文件，也不提供兼容层。

## Inputs and categorical rules / 输入与分类规则

- Inputs are either a two-dimensional integer array with explicit pixel geometry or a single-band, integer, projected, north-up GeoTIFF. The library never silently reprojects, resamples, or recodes categories.
- NoData is excluded from valid area, class totals, side edges, and same-class adjacency. A background value such as `0` is an ordinary retained class unless it is declared as NoData.
- Patch connectivity is explicitly 4 or 8 neighbours. Perimeter and aggregation adjacency are a separate concept: they use only horizontal and vertical shared sides.
- Pixel width and height may differ. Area is computed from their product; vertical and horizontal sides use their corresponding physical lengths.

## Exact execution paths / 精确计算路径

The default GeoTIFF and array paths construct an in-memory topology. Supplying `tile_shape=(rows, cols)` to `Landscape.from_geotiff` instead selects the out-of-core path. Both paths produce the same v0.1 tables under the same connectivity, NoData, and boundary settings.

默认数组和 GeoTIFF 路径会构建内存拓扑。为 `Landscape.from_geotiff` 指定 `tile_shape=(rows, cols)` 则选择外存分块路径。在连接规则、NoData 和边界设置相同的条件下，两条路径产出一致的 v0.1 表格。

The tiled algorithm uses three disk-backed stages:

1. It labels each tile locally, records globally unique labels in a memory-mapped array, and resolves cross-tile contacts with a disk-backed union-find structure.
2. It writes a root-label map in bounded chunks.
3. It streams each source tile with a one-cell halo, groups only its central valid cells by root label, and upserts per-patch counts, moments, and side summaries once per tile into SQLite. The final tables are derived from those canonical summaries.

No full source band, full-grid mask, or full in-memory topology is created by this route. Before work begins, the library checks a conservative temporary budget of **48 bytes/像元** (48 bytes per pixel). It uses an automatically removed private working directory beneath `tempdir` (or the system temporary directory), including when calculation raises an error. The caller-owned input and `tempdir` are never removed.

For side edges, NoData neighbours are ignored. Landscape edge length counts each differing valid right/down side once, together with included raster exterior sides; patch and class perimeters retain the corresponding side totals. Patch output order is stable: `(class_value, first_row, first_col)`.

## Selecting columns / 选择指标列

Each result method accepts `metrics=None` by default, returning its full frozen table. Supplying a sequence validates every identifier against the packaged metric cards before selecting columns. The calculation and cached full result remain unchanged.

```python
from landscape_metrics import Landscape

landscape = Landscape.from_geotiff("lulc.tif", tile_shape=(2048, 2048))
patches = landscape.patch_metrics(metrics=["area", "perimeter"])
classes = landscape.class_metrics(metrics=["edge_density", "total_area"])
edge_density = landscape.metrics(metrics=["edge_density"])
```

Patch selection retains `patch_id` and `class_value`; class selection retains `class_value`; landscape selection has no identity column. Requested metric columns keep the caller's order. Unknown, duplicate, or wrong-level identifiers raise `ConfigurationError` and list the valid identifiers for that level. Every `MetricResult` keeps the same metadata, including CRS, pixel dimensions, connectivity, NoData policy, execution path, and tile shape.

## Reproducible benchmark / 可复现实验

`benchmarks/benchmark_chunked.py` runs the actual tiled path and prints one JSON record per requested tile shape. Without `--input`, it generates a deterministic categorical GeoTIFF using `numpy.random.default_rng(20260716)`. It records elapsed wall time, process peak RSS, the conservative temporary budget, and patch/class row counts. It reports measurements only; different disks, GeoTIFF compression, CPUs, and memory pressure mean no fixed speed threshold is scientifically meaningful.

```bash
python benchmarks/benchmark_chunked.py --height 4096 --width 4096 --classes 8 \
  --tile-shape 512 512 --tile-shape 2048 2048
```

Use `--input /path/to/lulc.tif` to benchmark an existing input. The input must satisfy the library's normal GeoTIFF validation rules.

## Current exclusions / 当前不包含的功能

v0.1 intentionally excludes CLI and GUI products, vector inputs, moving windows, temporal/zonal/buffer workflows, plots, Core Area, IIC, PC, Dask, GPU, and distributed execution. These are not implicit roadmap commitments.
