# Changelog

## [1.0.3] - 2026-04-10

### Fixed

- 修复运行时间显示为系统启动时间而非 AstrBot 进程运行时间的问题，改用 `psutil.Process(os.getpid()).create_time()` (data_source.py:34)

### Changed

- **T2I 渲染性能优化**：通过将 Google Fonts 内联为 base64 Data URI 消除外部网络依赖，移除渲染时的 CDN 请求
- **图片优化**：将所有横幅和角色图片转换为 WebP 格式以减小文件体积
- **字体优化**：
  - `baotu.ttf`：压缩一半的字体大小，以确保常用的字体都可以使用
  - 其他字体 (`DingTalk-JinBuTi.ttf`, `Ma-Shan-Zheng-Regular.ttf`, `Noto-Sans-SC-*.ttf`, `Spicy-Rice-Regular.ttf`, `ADLaM-Display-Regular.ttf`)：通过子集化优化减小体积

### Added

- 在 `get_image_data_uri()` 函数中添加 WebP MIME 类型支持 (utils.py:113-114)

## [1.0.2] - 2026-03-11

### Removed

- 移除了不必要的模块导入

## [1.0.1] - 2026-03-08

### Changed

- 在所有模块中使用 `astrbot.api` 导入日志记录器
- 优化获取系统信息时的性能
- 使用 StarTools 改进数据存储位置的获取

### Added

- 为图片提供默认的 base64 透明占位符

## [1.0.0] - 2026-03-08

### Added

- astrbot_plugin_status 初始版本发布
- 系统状态卡片渲染，包含 CPU、RAM、SWAP、DISK 和 LOAD 指标
- HTML 转图片 (T2I) 渲染支持
- LLM 工具集成，供 Agent 获取状态图片
- 可通过配置自定义机器人名称和横幅图片
- 网络速度监控（上传/下载）
- 插件数量显示
- 跨平台支持（Windows、Linux）
