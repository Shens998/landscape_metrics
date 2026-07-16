# 发布工程化设计

> 状态：用户已确认
>
> 日期：2026-07-16

## 目标

为 Open Landscape Metrics 的公开 alpha Python 库补齐可复现的持续集成、可引用软件元数据和最小贡献文档，使每次提交与 Pull Request 都能自动验证安装、测试、静态检查和发行包构建。

## 范围

- 新增 GitHub Actions 工作流，在 Ubuntu 上使用 Python 3.11 与 3.12 运行完整测试、Ruff 和 mypy。
- 单独构建 sdist 与 wheel，不上传 PyPI、不创建 GitHub Release、不生成 DOI。
- 新增 CITATION.cff，作者显示为 Shi Shen，版本保持 0.1.0a0，许可证为 MIT，仓库为 Shens998/landscape_metrics。
- 新增贡献指南和 Keep a Changelog 风格的初始变更记录。
- 将 build 添加为开发依赖，使本地与 CI 使用同一构建入口。

## 不变量

- 不改变 21 个指标、公开计算 API、分块算法或任何数值结果。
- 不添加 CLI、在线服务、遥测、用户数据上传或新的运行时依赖。
- CI 不访问私有数据，不上传用户栅格，不保存密钥；工作流仅具有只读仓库权限。
- 文档不声称与 FRAGSTATS 或 PyLandStats 兼容。

## 验收

1. GitHub Actions 在 push 和 pull_request 时，针对 Python 3.11/3.12 安装项目并运行 pytest、Ruff、mypy。
2. 构建步骤生成 sdist 与 wheel，并检查其元数据包含项目名称、版本和 MIT 许可证声明。
3. CITATION.cff 可由 YAML 读取，含 Shi Shen、仓库 URL、版本和 MIT 许可证。
4. CONTRIBUTING.md 和 CHANGELOG.md 说明贡献与 alpha 变更边界。
5. 本地完整测试、Ruff、mypy 与 build 都通过。
