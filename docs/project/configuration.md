# 配置说明

配置真源是根目录 `_conf_schema.json`。修改配置字段时必须同步更新 README、本文档和相关测试。

## 字段

| 字段 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `auto_use_current_name` | `bool` | `true` | 自动使用事件发送者名称；取不到时使用平台 ID，再取不到时使用 `bot_name`。 |
| `bot_name` | `string` | `AstrBot` | 显示在状态卡片上的机器人名称。 |
| `banner_image` | `file` | `[]` | 自定义状态背景图，可上传多张随机展示。 |
| `enable_llm_analysis` | `bool` | `false` | `/状态` 返回图片后是否调用 LLM 分析。 |
| `vision_provider_id` | `string` | 空字符串 | 识图模型 provider。留空时优先使用 AstrBot 全局图片描述模型，再回退到当前会话模型。 |
| `comment_provider_id` | `string` | 空字符串 | 文本转述 provider。留空时使用当前会话模型。 |
| `vision_prompt` | `string` | `把图片中各种指标用文字描述出来` | 发送给视觉模型的提示词。 |
| `comment_prompt` | `string` | 见 schema | 发送给文本模型的提示词，使用 `{description}` 表示识图结果占位符。 |

## 配置维护规则

- README 中的配置表必须和 `_conf_schema.json` 保持一致。
- 运行时代码通过 `core.config_manager.ConfigManager` 读取配置，业务流程不要直接散落调用 `config.get(...)`。
- 删除、重命名或改变字段类型时，必须说明兼容影响。
- Provider 字段使用 AstrBot 的 `select_provider` 特殊选择器。
- `banner_image` 是用户文件路径入口，读取时必须保留路径范围检查。
- `comment_prompt` 修改时必须保留 `{description}` 语义，或同步修改代码中的替换逻辑。
