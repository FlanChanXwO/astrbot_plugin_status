# 贡献说明

## 贡献目标

优先做这些事情：

- 修复状态采集、渲染、图片资源和 LLM 分析回归
- 补充测试与最小回归用例
- 让 README、配置 schema 和 docs 保持一致
- 改善排障日志和错误可观测性

不建议直接上来做大而散的重构，除非先把行为边界讲清楚。

## 改动前先理解当前边界

改动前先确认自己触碰的是哪条边界，不在这里复制业务规则：

- 架构和渲染链路见 [`../project/architecture.md`](../project/architecture.md)
- 配置字段语义见 [`../project/configuration.md`](../project/configuration.md)
- 插件定位和能力边界见 [`../project/overview.md`](../project/overview.md)

如果准备做的事和这些边界冲突，需要先明确说明为什么。

## 推荐的贡献流程

1. 明确问题或目标
2. 先阅读相关代码与现有文档
3. 小步提交，单次改动尽量围绕一个目的
4. 先补或更新测试，再补文档
5. 通过 lint 与最小回归检查后再提交 PR

## 文档同步要求

文档同步细则统一维护在 [`maintenance.md`](./maintenance.md#文档同步)。贡献文档只强调一点：不要只改代码而让 README、docs、CHANGELOG 或 agent 入口说明失真。

## 代码风格

通用工程原则见 [`engineering-principles.md`](./engineering-principles.md)。贡献时优先沿用现有模式，不要为了局部问题顺手大改 unrelated 模块。

## PR 描述建议

新代码和修复改动的 PR 目标分支应为 `dev`，不要直接提交到主分支。

当前仓库若尚未创建 `dev` 分支，先和维护者确认目标分支或创建策略，再开 PR。

建议至少写清楚：

- 背景问题
- 改动范围
- 风险点
- 验证方式
