# 项目文档

本目录用于说明插件是什么、为什么这样设计、配置语义是什么，以及维护者触碰某条链路时该看哪里。

## 目录

- [`overview.md`](./overview.md): 项目定位、能力边界和当前入口
- [`architecture.md`](./architecture.md): 模块关系、渲染链路、数据采集和安全边界
- [`configuration.md`](./configuration.md): `_conf_schema.json` 字段语义、默认值和文档同步要求

## 适合谁看

- 第一次接手这个插件的维护者
- 准备修改指标、渲染、配置或 LLM 分析的人
- 需要确认 README、schema 和代码是否一致的人

## 推荐阅读顺序

1. [`overview.md`](./overview.md)
2. [`architecture.md`](./architecture.md)
3. [`configuration.md`](./configuration.md)
