# Open Landscape Metrics｜v0.1 开发进展与交接记录

> 更新日期：2026-07-16
>
> 当前分支：v0-1-chunked-validation
>
> 隔离工作区：.worktrees/v0-1-chunked-validation
>
> 基线：main 的合并提交 03dafa5

## 当前目标

交付一个公开、独立实现的 Python 库，用于土地利用／土地覆被分类栅格的基础景观格局指标。项目不调用 FRAGSTATS；所有指标定义、展示名称、LaTeX 公式、规则和文献来源均由机器可读指标卡记录。

## 已冻结的科学与工程规则

- 输入为单波段整数分类 GeoTIFF 或二维整数数组；必须是投影、北向上、无旋转／剪切的空间参考。
- NoData 排除面积、边和邻接；背景是显式有效类别。
- patch connectivity 仅支持 4 或 8 邻域；周长、边缘和聚集度的邻接均仅使用共享边。
- 默认计入景观外边界；NoData 邻边不计为边。
- v0.1 固定 21 个指标稳定 ID；展示用标准英文名、缩写、中文名和 LaTeX 公式位于 src/landscape_metrics/metric_cards.yaml，渲染文档为 docs/metrics.md。
- 大数据优先级是有限单机内存受控处理超大 GeoTIFF，而不是多核最大吞吐。

## 已完成能力

1. 严格数组／GeoTIFF 输入验证、内存拓扑和 patch/class/landscape 三级指标。
2. 公开 Landscape API、结果元数据和指标列筛选。
3. 精确外存分块路径：块内标签、跨块磁盘并查集、根标签映射、带一像元 halo 的流式聚合、SQLite 按块汇总与自动临时文件清理。
4. 48 bytes/像元的临时磁盘预检、双语 README／方法文档和可复现实验基准。
5. 已合并并推送 main 的标准指标名称、缩写与 LaTeX 公式文档。

## 当前验证覆盖

- 已有跨水平／垂直块边界和四块交点对角连接对照，覆盖 4/8 连通与三种块大小。
- 新增规则矩阵：NoData -1、显式背景 0、多个有效类别、20 m × 30 m 非方形像元，覆盖 4/8 连通和 (1, 2)、(2, 1)、(2, 2) 块大小。
- 新增成功路径清理检查：调用者输入 GeoTIFF 保留，调用者临时目录不残留 landscape-metrics-* 私有工作目录。
- 新增 Hypothesis 小栅格性质测试：20 个包含 -1、0、1、2 的随机案例，随机合法块大小与 4/8 连通；三个公共结果表必须与内存路径严格一致。

验证命令：

~~~bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src tests tools benchmarks
.venv/bin/python -m mypy src
~~~

最近一次结果：53 项测试通过，Ruff 与 mypy 无诊断。Python 环境为 3.13.5；项目声明支持 Python 3.11+。

## 后续规则

若后续扩展分块后端，必须先用公开 API 写出失败的内存／分块等价回归测试；仅在该测试确认真实差异后，按系统调试流程进行最小生产代码修复。不得以完整栅格读取、全局内存拓扑或逐像元 SQLite 写入规避内存上界。
