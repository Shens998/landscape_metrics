# Open Landscape Metrics｜v0.1 开发进展与交接记录

> 更新日期：2026-07-16
>
> 工作分支：`v0.1-raster-api`
>
> 隔离工作区：`.worktrees/v0.1-raster-api`

## 当前目标

交付一个公开、独立实现的 Python 库，用于土地利用/覆被分类栅格的基础景观格局指标。项目不调用 FRAGSTATS；指标来源、公式和规则由仓库内机器可读指标卡公开记录。

## 已确认的科学与工程规则

- 输入：单波段整数分类 GeoTIFF 或二维整数数组；拒绝连续浮点表面。
- 空间：要求投影 CRS、北向上、无旋转/剪切；NoData 排除，背景是显式类别。
- 斑块：`connectivity` 仅为 4 或 8；周长/边邻接只使用共享边，不将对角接触算为边。
- 边界：默认计入景观外框；NoData 邻边不计为边。
- 指标：v0.1 固定 21 个指标标识；卡片位于 `src/landscape_metrics/metric_cards.yaml`，文献见 `docs/references.bib`。
- 大数据：用户已确认优先级是“有限单机内存受控处理超大文件”，而不是多核最大吞吐。

## 已完成提交

| 提交 | 内容 | 验证 |
|---|---|---|
| `96b07a5` | 包骨架、异常、配置契约 | 模型测试与 Ruff |
| `f7dfd04` | 21 张指标卡、参考文献与生成式指标页 | 指标卡测试与 Ruff |
| `bbb02c7` | 数组/GeoTIFF 输入验证 | 输入测试、Ruff、mypy |
| `50242c9` | 内存斑块标签、边和邻接拓扑 | 拓扑测试、Ruff、mypy |
| `b625380` | 斑块级指标 | 斑块测试、Ruff、mypy |
| `20bfc18` | 类别级与景观级指标 | 聚合测试、Ruff、mypy |
| `cf2af7e` | 公开 `Landscape` API 与运行元数据 | API 测试、Ruff、mypy |

## 当前验证状态

截至 `cf2af7e`，在工作区 `.venv` 中运行：

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src tests tools
.venv/bin/python -m mypy src
```

结果为 **21 项测试通过**，Ruff 与 mypy 无诊断。

Python 运行环境为 3.13.5；项目声明支持 Python 3.11+。为了规避 Rasterio 1.5 与 NumPy 2.5 的弃用警告，`pyproject.toml` 约束为 `numpy>=2.0,<2.5`。第三方库缺少类型桩的情况在 mypy 配置中显式忽略，不放宽项目源码检查。

## 当前未提交状态

`tests/test_chunked.py` 已创建且故意保持红色。它要求：

- `Landscape.from_geotiff(..., tile_shape=..., tempdir=...)`；
- 4/8 邻域、三种块大小下，分块与内存的 patch/class/landscape 结果完全一致；
- 分块结果元数据为 `execution_path="chunked"`。

该测试尚未提交，因为先前计划把分块结果错误地建模为内存 `Topology`。用户已确认改用外存流式聚合设计；请先更新计划，再实现并提交该测试与后端。

## 已识别的架构修订

分块后端设计已确认并记录在：

`docs/superpowers/specs/2026-07-16-out-of-core-backend-design.md`

核心变更：分块路径直接产出三级表格和元数据，不构造完整 `Topology`。算法使用窗口局部标签、磁盘映射标签与父指针、跨块并查集、SQLite 聚合和窗口内向量化统计。临时磁盘预检按 48 bytes/像元保守估算。

## 下一步（严格顺序）

1. 由 `writing-plans` 更新 Task 8 的接口和实现步骤，替换 `compute_chunked(...) -> Topology` 假设。
2. 用户审阅更新后的计划。
3. 实现分块后端；先让 `tests/test_chunked.py` 转绿，再添加临时空间不足、NoData、对角跨块和非方形像元测试。
4. 实现性质测试、基准、方法文档、CI、发布文件。
5. 全量验证、分支审查、合并与推送。

## 风险与注意事项

- 不要通过“读取完整数组后复用内存后端”伪装分块支持；这违反已确认的资源目标。
- 不要在分块路径逐像元执行 SQLite 写入；必须按窗口向量化并批量事务写入。
- 不要让不同块大小改变类别顺序、patch ID 排序、指标值或元数据定义。
- 不要把工作分支直接合并到 `main`，直到用户审查完成、所有测试通过并运行分支完成流程。
