# 测试与回归检查

## 基础命令

| 场景 | 工作目录 | 命令 |
| --- | --- | --- |
| Python 格式化 | AstrBot 根目录 | `uv run ruff format data/plugins/astrbot_plugin_status` |
| Python lint | AstrBot 根目录 | `uv run ruff check data/plugins/astrbot_plugin_status` |
| 语法检查 | 插件目录 | `python3 -m compileall main.py core` |
| pytest | 插件目录 | `pytest tests/ -v` |

> [!TIP]
> 这些是测试与检查命令，不是插件的独立运行命令。实际集成验证入口见 [`setup.md`](./setup.md#本地集成验证)。

## 分层验证矩阵

| 改动类型 | 最小检查 | 建议额外回归 | 关注点 |
| --- | --- | --- | --- |
| Python 业务逻辑 | `ruff check`、语法检查、相关测试 | 命令路径和 tool handler 路径 | 不要只跑被改函数附近的测试。 |
| 渲染模板 / 资源 | `ruff check`、语法检查 | `/status` 或 `/状态` 手工生成图片 | 关注 T2I、字体内联、默认图片缺失。 |
| 配置 schema | `ruff check`、相关配置测试 | README 与配置文档同步核对 | 旧配置是否还能被容忍。 |
| LLM 分析 | `ruff check`、相关测试 | 视觉模型缺失、转述模型缺失、prompt 替换 | provider fallback 要可观测。 |

## 高风险改动清单

| 改动 | 风险 | 建议 |
| --- | --- | --- |
| 用户图片路径逻辑 | 路径穿越或读取任意文件 | 补路径安全测试。 |
| `StatusPayload` 字段 | 模板渲染失败 | 同步模板和回归测试。 |
| HTML/CSS 变量名 | 图片或角色资源不显示 | 手工验证 T2I 输出。 |
| 网络速度采样 | 首次速度、差值或单位异常 | 覆盖首次采样和连续采样。 |
| provider fallback | 分析误用模型或静默失败 | 覆盖配置优先级和缺失提示。 |

## T2I 回归

`tests/test_status_rendering.py` 会在 `localhost:8999` 可访问时调用本地 T2I 服务，检查输出图底部不再出现大块白色留白。若普通沙箱网络访问不到 Docker 服务，该测试会跳过；需要真实验证时用宿主机网络环境运行对应测试。
