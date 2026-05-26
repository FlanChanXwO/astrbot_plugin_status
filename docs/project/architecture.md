# 架构说明

## 模块关系

```text
main.py
  -> core.ConfigManager
  -> core.HtmlRender
       -> core.SystemDataSource
       -> core.utils
       -> core.models.StatusPayload
       -> AstrBot html_render()
  -> core.StatusService
       -> AstrBot LLM provider
  -> core.logger
```

## `main.py`

`main.py` 保留插件入口职责：

- 初始化路径、`ConfigManager`、`HtmlRender` 和 `StatusService`
- 注册和注销 `astrbot_get_system_status`
- 将 `/status`、`/状态` 事件转发给 `StatusService`

不要把复杂采集、图片资源选择、CSS 内联或 payload 组装重新塞回 `main.py`。

## `core/status_service.py`

`StatusService` 负责路由和 LLM 分支：

- 处理 `/status`、`/状态` 的流程分支
- 处理 `astrbot_get_system_status` tool 的发送和返回
- 根据配置解析 provider，并区分配置缺失、模型超时和异常
- 调用 `HtmlRender` 获取状态图 URL 和文本摘要，但不直接拼接渲染数据

## `core/html_render.py`

`HtmlRender` 负责状态图渲染和数据拼接：

- 管理模板、CSS、默认 Banner 和角色图片资源路径
- 调用 `SystemDataSource` 采集状态指标
- 构建 `StatusPayload` 和 LLM tool 文本摘要
- 调用 AstrBot `html_render()` 生成图片 URL

## `core/data_source.py`

`SystemDataSource` 负责读取运行环境状态：

- CPU 百分比、频率、核心数和名称
- 内存、交换分区、磁盘
- 系统负载
- 网络瞬时上传/下载速度
- AstrBot 版本和已加载插件数
- 当前进程运行时间

网络速度是基于两次采样之间的差值计算的，因此首次调用通常返回 `0.0`。

`HtmlRender.build_render_data()` 负责把模板、CSS、图片资源和系统数据组装为：

- HTML 模板文本
- `StatusPayload`

它不负责发送消息；对外业务代码通过 `HtmlRender.render_status_image()` 和 `HtmlRender.build_status_text()` 使用渲染能力，不直接拼接状态图数据。

## `core/utils.py`

工具函数集中处理可复用边界：

- 字体资源内联
- 图片转 Data URI
- 随机选择用户 Banner、默认 Banner 或角色图片
- 本地路径范围检查
- 图片大小限制

路径安全是硬边界：用户路径必须限制在插件目录或插件数据目录内。

## `core/config_manager.py`

`ConfigManager` 负责集中加载、归一化和校验 `_conf_schema.json` 中的配置字段。入口和核心模块应读取已解析后的属性，不要在业务流程里散落直接调用 `config.get(...)`。

## `core/logger.py`

`core.logger` 负责集中包装 AstrBot logger，并为插件日志统一添加 `[astrbot_plugin_status]` 前缀。业务模块应使用 `from .logger import logger` 或 `get_logger()`，不要直接从 `astrbot.api` 导入原始 logger，也不要在消息文本中手写局部插件前缀。

## 渲染链路

1. 命令或 tool handler 进入 `StatusService`
2. `StatusService` 调用 `HtmlRender.render_status_image()`
3. `HtmlRender` 使用 `SystemDataSource` 拼接 HTML 与 payload
4. `HtmlRender` 调用 AstrBot `html_render()` 生成图片 URL
5. 命令路径返回图片；LLM tool 路径发送图片并通过 `HtmlRender.build_status_text()` 返回文本状态摘要

## 模板边界

`templates/main.html` 的背景 paw SVG 必须保留在 `.card` 内部，由 `.card { overflow: hidden; }` 负责裁剪。不要把这些绝对定位装饰元素移到 `.card` 外面，否则 AstrBot/T2I 的 full-page 截图会把它们计入页面滚动高度，导致状态卡片底部出现大块留白。

## LLM 分析链路

开启 `enable_llm_analysis` 后，`/status` 会：

1. 先发送状态图片
2. 使用 `vision_provider_id` 或全局图片描述模型识别图片
3. 使用 `comment_provider_id` 或当前会话模型生成文字总结
4. 视觉模型未配置、返回空结果或超时时，向用户返回明确提示

Provider 选择逻辑位于 `StatusService.resolve_provider()`。
