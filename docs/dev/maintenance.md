# 维护规则

本文面向维护者和协作 agent，记录开发时需要遵守的仓库级规则。业务细节不要继续塞进 `AGENTS.md` 或 `CLAUDE.md`，应拆到 `docs/project/` 的对应主题文档。

## 文档同步

- 文档不是可选收尾。
- 行为、边界、入口、配置、流程、架构或维护约定变化时，必须同步更新对应文档。
- 下列变化默认需要更新文档：
  - 命令行为或参数变化
  - 配置项、默认值或兼容规则变化
  - 状态指标语义或展示格式变化
  - 渲染模板、资源路径、T2I 依赖或安全边界变化
  - LLM provider 选择、prompt 语义或分析流程变化
  - 测试、lint 或本地验证流程变化
- 修改 repo-wide 维护规则或 agent 入口约定时，同步更新 `AGENTS.md` 和 `CLAUDE.md`。

## 入口与模块边界

入口与模块事实统一维护在 [`../project/architecture.md`](../project/architecture.md)。本文件只记录维护要求：不要把复杂采集、资源处理或渲染组装重新塞回 `main.py`。

## 本地路径

- 插件数据目录由 AstrBot `StarTools.get_data_dir(self.name)` 提供。
- 不要在插件目录创建或依赖 `<plugin>/data` 作为运行态目录。
- 用户上传图片路径必须限制在插件目录或插件数据目录内，具体边界见 [`../project/architecture.md`](../project/architecture.md#coreutilspy)。

## 配置维护

- 配置字段语义见 [`../project/configuration.md`](../project/configuration.md)。
- `_conf_schema.json` 字段新增、删除、重命名或类型变化时，必须同步 README、配置文档和相关回归测试。
- 不在维护文档里复制完整配置表。

## 测试与检查

常用命令见 [`testing.md`](./testing.md)。涉及下列行为时，优先补回归测试：

- 图片路径安全
- 图片大小限制
- CSS 字体内联
- `StatusPayload` 字段
- LLM provider 选择优先级
- `_conf_schema.json` 字段兼容

## 已移除或不属于本插件的能力

本插件不维护独立使用文档目录、不提供 Plugin Pages、不提供独立 Web 服务、不存储历史指标。修改相关入口前先确认是否真的属于本插件职责。
