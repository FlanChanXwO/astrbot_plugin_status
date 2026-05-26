# 开发环境与本地调试

## 前置要求

- Python 3.10+
- AstrBotPluginDev 本地开发环境
- 推荐使用 `uv`

## 本地代码位置

插件通常位于：

```text
AstrbotPluginDev/data/plugins/astrbot_plugin_status
```

## 常用目录

```text
core/       # 数据采集、渲染 payload、模型和通用工具
templates/  # T2I HTML/CSS、字体和默认图片资源
assets/     # README 预览图
tests/      # 测试入口，当前只有占位包
docs/       # 项目和开发文档
```

## 运行与调试原则

### 本地集成验证

项目运行通常启动 AstrBotPluginDev 顶层入口，而不是直接运行插件目录内的文件。

本地工作区常见入口：

```bash
python /Users/flanchan/Development/SourceCode/GithubProjects/AstrbotPluginDev/main.py
```

如果工作区路径不同，就在 AstrBotPluginDev 根目录运行对应的顶层 `main.py`。

### 数据目录

不要把运行时数据写回插件仓库下的 `data/`。

本插件通过 AstrBot 提供的 `StarTools.get_data_dir(self.name)` 取得插件数据目录。

### 启动结构

入口和渲染链路见 [`../project/architecture.md`](../project/architecture.md)。本地调试时不要把复杂采集、资源处理或渲染组装塞回 `main.py`。

## 测试与检查命令

命令清单统一维护在 [`testing.md`](./testing.md)，本文件不重复列出。
