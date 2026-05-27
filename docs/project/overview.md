# 项目概览

## 插件定位

`astrbot_plugin_status` 是一个面向 AstrBot 的系统状态展示插件。它的核心职责是：

- 采集当前运行环境的 CPU、内存、交换分区、磁盘、负载、网络速度、运行时间等状态
- 使用 AstrBot HTML/T2I 能力把状态数据渲染成图片卡片
- 支持自定义 Banner 图片和默认角色/背景资源
- 可选调用视觉模型和文本模型，对状态图片生成文字分析
- 为 AstrBot Agent 注册 `astrbot_get_system_status` 工具，供会话中主动查询系统状态

## 当前入口

用户入口：

- `/status`
- `/状态`

Agent tool 入口：

- `astrbot_get_system_status`

运行入口：

- 插件自身入口是本仓库根目录 `main.py`
- 本地集成验证通常运行上层 AstrBot 工程入口 `/Users/flanchan/Development/SourceCode/GithubProjects/AstrbotPluginDev/main.py`

## 当前能力边界

插件负责：

- 系统指标采集与展示格式化
- HTML/CSS 渲染 payload 构造
- 图片资源读取、内联和安全检查
- LLM provider 选择和两段式图片分析编排
- AstrBot 命令和 LLM tool 注册

插件不负责：

- 提供独立 Web 服务
- 替代 AstrBot T2I 服务
- 长期存储历史指标
- 监控告警、阈值规则或定时推送
- 跨机器采集远端指标

## 对维护者最重要的事实

- `main.py` 是入口和编排层，不应重新堆放渲染细节。
- `core/data_source.py` 是系统指标采集层。
- `core/html_render.py` 是 HTML 模板和 `StatusPayload` 的组装层。
- `core/utils.py` 是图片、字体和路径安全相关工具层。
- `_conf_schema.json` 是配置字段真源；README 和 docs 必须跟它同步。
- 用户上传图片路径必须经过安全检查，避免路径穿越。
