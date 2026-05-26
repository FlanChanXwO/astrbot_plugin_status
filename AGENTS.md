# AGENTS.md - astrbot_plugin_status

本文件只保留协作 agent 的入口规则。项目细节按需阅读 `docs/project/`，开发维护规则优先阅读 `docs/dev/maintenance.md`。

## 沟通语言

- 与用户沟通必须使用中文。

## 项目形态

- 这是一个 AstrBot 系统状态插件，负责采集主机指标并渲染状态卡片。
- 插件入口是根目录 `main.py`；可复用逻辑放在 `core/`。
- 静态 HTML/CSS、字体和默认图片资源放在 `templates/`。

主要目录：

- `main.py`: 插件生命周期、命令入口、LLM tool 注册和 LLM 分析编排。
- `core/`: 数据采集、渲染 payload、模型和通用工具。
- `templates/`: T2I 渲染模板、样式、字体和默认图片资源。
- `assets/`: README 预览图。
- `tests/`: 测试入口，当前只有占位包。

## 阅读入口

- 任何改动前先看：`docs/dev/maintenance.md`
- 需要项目背景时看：`docs/project/README.md`
- 修改状态指标、渲染 payload、图片资源或 LLM 分析时看：`docs/project/architecture.md`
- 修改配置项时同步核对：`_conf_schema.json`、`README.md`、`docs/project/configuration.md`
- 修改测试、lint、贡献流程或工程约束时看：`docs/dev/testing.md`、`docs/dev/contributing.md`、`docs/dev/engineering-principles.md`

## 硬约束

- 不要把复杂采集、资源处理或渲染组装重新塞回 `main.py`。
- 不要在插件目录创建或依赖 `<plugin>/data` 作为运行态目录；插件数据目录使用 AstrBot 提供的 `StarTools.get_data_dir()`。
- 用户上传的图片路径必须限制在插件目录或插件数据目录内，不要绕过 `core.utils` 的路径安全检查。
- 状态卡片渲染依赖 AstrBot 的 HTML/T2I 能力；不要把本插件改成独立 Web 服务。
- 其他指标语义、配置边界和维护规则不要写进本文件，放到 `docs/project/` 或 `docs/dev/` 对应章节。

## 文档纪律

- 文档不是可选收尾。行为、边界、入口、配置、流程、架构或维护约定变化时，必须同步更新对应 `docs/`。
- 命令行为、配置项、LLM provider 选择、渲染资源、安全边界、测试或 lint 流程变化时，通常需要更新文档。
- 如果修改 repo-wide 维护规则或 agent 入口约定，同步更新 `AGENTS.md` 和 `CLAUDE.md`。

## 测试与检查命令

从 AstrBot 项目根目录运行检查：

```bash
uv run ruff format data/plugins/astrbot_plugin_status
uv run ruff check data/plugins/astrbot_plugin_status
```

从插件目录运行语法与测试检查：

```bash
python3 -m compileall main.py core
pytest tests/ -v
```

本地集成验证通常需要运行上层 AstrBot 入口：

```bash
cd /Users/flanchan/Development/SourceCode/GithubProjects/AstrbotPluginDev
uv run main.py
```

## 更新策略

当架构、命令面、配置路径、渲染流程、LLM 分析或测试 / lint 流程变化时，同步更新 `CLAUDE.md` 和 `AGENTS.md`。

## 篇幅约束

`AGENTS.md` 和 `CLAUDE.md` 均不得超过 100 行；内容过长时拆入 `docs/dev/` 或 `docs/project/`。
