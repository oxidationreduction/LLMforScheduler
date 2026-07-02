# dev_framework_agent Handoff

## 当前状态

已就绪。尚未编写代码。

## 计划工作

1. 创建 split manifest 工具。
2. 创建 metrics aggregation 工具。
3. 创建 LLM tool-call schema 和 parser。
4. 从现有 solver 结果构造 SFT 数据。
5. 创建 direct LLM baseline 输出验证工具。

## 约束

- 默认只写新文件，除非获得批准。
- 保持依赖最小。
- 复用现有 solver/verifier import。
- 不启动长任务。

## 等待事项

- 实验管理 agent 给出 split 和指标 schema。
