# PyLandStats 启发的 v0.1 改进设计

> 状态：已获用户口头确认，待书面审阅。
>
> 日期：2026-07-16

## 目标

在不复制 PyLandStats 的代码、API 命名、文档文字或兼容性承诺的前提下，借鉴其易用性与结果组织方式，完善 Open Landscape Metrics 的 v0.1。优先完成超大 LULC GeoTIFF 的精确、单机内存受控计算，再改善公开 Python API 和研究文档。

## 保持不变的边界

- 本库是 MIT 许可的独立实现；不调用 FRAGSTATS 或 PyLandStats，不读取其工程格式，也不声称结果或 API 兼容。
- 输入仍限于二维整数数组和严格验证的单波段、投影、北向上 GeoTIFF。
- v0.1 的 21 个冻结指标、NoData 与显式背景规则、4/8 连通规则、共享边规则和输出列语义不变。
- v0.1 仍不加入 CLI、GUI、矢量输入、移动窗口、时序/分区/缓冲区分析、绘图、Core Area、IIC、PC、Dask、GPU 或分布式调度。

## 改进 1：完成精确外存分块后端

分块 GeoTIFF 路径继续采用已确认的三阶段算法：块内标签、跨块磁盘并查集合并、带一像元 halo 的流式聚合。它直接生成 patch/class/landscape 三个 DataFrame 与运行元数据，不构造内存 `Topology`，不读取完整源栅格，也不逐像元写 SQLite。

块大小由调用者以 `tile_shape=(rows, cols)` 明确指定。计算前按 48 bytes/像元进行临时空间预检；临时目录成功或异常退出都清理。分块与内存路径在所有支持指标上必须严格一致，且 patch ID 按 `(class_value, first_row, first_col)` 稳定排序。

## 改进 2：借鉴易用性，但不复制 API

完成分块后端后，公开 `Landscape` API 增加可选的指标列筛选参数：`metrics: Sequence[str] | None`。`None` 返回当前冻结层级的全部列；指定序列返回 `patch_id`/`class_value` 标识列（适用时）以及请求的指标列，按用户请求顺序排列。未知、跨层级或重复指标在计算前抛出 `ConfigurationError`，并列出可选标识。

三种返回方法仍是 `.patch_metrics()`、`.class_metrics()`、`.metrics()`，始终返回 `MetricResult`。筛选只改变返回列，不改变计算规则、元数据、行排序或缓存的完整结果。API 不采用 PyLandStats 的类方法名称，也不模仿其调用签名。

## 改进 3：研究可复现性文档

README 和方法文档为中英文读者明确说明：输入约束、NoData 与背景的区别、连接与边的区别、内存/分块执行路径、临时磁盘预算、结果元数据和当前 v0.1 排除项。示例只使用本库公开 API；指标卡继续将原始来源与定义性参考区分标记。

## 验收

1. 4/8 邻域、至少三种 `tile_shape` 下，内存与分块的三张 DataFrame 完全一致。
2. 测试覆盖跨块边界、四块交点对角、NoData、显式背景、非方形像元、临时磁盘不足与清理。
3. 指标筛选测试覆盖完整列、用户指定顺序、标识列、未知标识和跨层级标识。
4. 基准记录块大小、耗时、RSS、临时磁盘预算和结果行数；不以某一设备的固定速度作为验收阈值。
5. 文档不包含 FRAGSTATS-compatible 或 PyLandStats-compatible 等兼容性声称。
