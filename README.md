# Open Landscape Metrics / 开放景观格局指标

Open Landscape Metrics is an open-science Python library for calculating a focused set of reproducible landscape metrics from categorical land-use and land-cover (LULC) rasters. It is an independent implementation built from public metric definitions and cited literature.

## 中文简介

**Open Landscape Metrics** 是一个面向开放科学研究的 Python 库，用于从土地利用／土地覆被（LULC）分类栅格中计算基础景观格局指标。它优先支持单波段、整数分类、具有投影坐标参考系的 GeoTIFF，也支持二维整数数组。

本项目独立实现公开可追溯的指标定义，记录公式、规则和文献来源；不调用 FRAGSTATS，不读取其工程格式，也不宣称与任何专有软件逐项兼容。NoData 被明确排除，背景值是普通的显式类别；4/8 邻域连通与共享边邻接分别定义。

当前 alpha 版本提供斑块、类别和景观三级的常用基础指标。对于超大 GeoTIFF，可用 `tile_shape` 启动经过验证的精确、单机内存受控分块路径；它不构造完整内存拓扑，也不会读取完整源波段。详细规则见[方法说明](docs/methods.md)。

## English overview

**Open Landscape Metrics** is an open-science Python library for a focused, reproducible set of landscape metrics from categorical land-use/land-cover (LULC) rasters. It supports single-band integer GeoTIFFs with a projected CRS and two-dimensional integer arrays.

The project is independently implemented from public, citable definitions. It does not call FRAGSTATS, read FRAGSTATS project files, or claim one-to-one compatibility with proprietary software. NoData is excluded from area, edge, and adjacency calculations, while a background value is an ordinary explicit class. Patch connectivity (4 or 8 neighbours) is intentionally separate from side-based edge adjacency.

The current alpha provides common patch-, class-, and landscape-level metrics. For very large GeoTIFFs, `tile_shape` enables a verified exact, memory-bounded tiled path; it constructs neither a full in-memory topology nor a full source-band read. See the [methods note](docs/methods.md) for the calculation rules.

## Quick start / 快速开始

```python
from landscape_metrics import Landscape

landscape = Landscape.from_geotiff("lulc.tif", connectivity=8)

patches = landscape.patch_metrics().values
classes = landscape.class_metrics().values
landscape_metrics = landscape.metrics().values

print(classes)
```

Request only the columns needed for a table while keeping identity columns and metadata:

```python
classes = landscape.class_metrics(metrics=["edge_density", "total_area"])
edge_density = landscape.metrics(metrics=["edge_density"])
```

For a large GeoTIFF, select an explicit tile size and a location with sufficient temporary disk space:

```python
large = Landscape.from_geotiff(
    "large_lulc.tif",
    connectivity=8,
    tile_shape=(2048, 2048),
    tempdir="/path/to/temporary-storage",
)
classes = large.class_metrics(metrics=["total_area", "number_of_patches"])
```

Input rasters must be single-band integer categories with a projected, north-up, unrotated GeoTIFF transform. The library does not silently reproject, resample, or recode data.

## Scope / 当前范围

- Patch connectivity: 4 or 8 neighbours; perimeter and adjacency always use shared sides only.
- NoData is excluded; explicit background categories are retained.
- Pixel width and height may differ; areas and side lengths use the input grid geometry.
- Tiled execution is exact for the current metric set. Before it starts, the library reserves a conservative temporary-storage budget of 48 bytes/像元 (48 bytes per pixel); its working files are automatically cleaned after success or failure.
- Metric cards, formulas, assumptions, and original/definition references are available in [docs/metrics.md](docs/metrics.md).
- Algorithmic rules, reproducibility metadata, and the benchmark procedure are in [docs/methods.md](docs/methods.md).
- The library currently has no CLI, GUI, vector-input, moving-window, Core Area, IIC, or PC support.

## Project status / 项目状态

This repository is under active alpha development. APIs and metric contracts are documented as they are validated, and all numerical changes are expected to carry regression tests.

本仓库处于积极开发的 alpha 阶段。API 与指标契约会随验证结果同步记录；任何数值规则变更都应附带回归测试。

## Contributing and citation / 参与贡献与引用

Bug reports, reproducible examples, documentation improvements, and scientifically transparent metric discussions are welcome. Please cite the software version and the metric sources relevant to your analysis. The repository is released under the [MIT License](LICENSE).
