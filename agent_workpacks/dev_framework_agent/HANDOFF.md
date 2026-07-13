# dev_framework_agent Handoff

## 当前状态

已就绪。2026-07-11 后，主线开发任务从 LLM-agent/SFT/direct baseline tooling 调整为 H5 complexity/difficulty analysis 与 H6 verifier case-study extraction。已有 LLM harness 文件保留为暂停的附录候选，不继续扩展。

## 计划工作

1. 等待 `experiment_manager_agent` 给出 H5 分桶 schema。
2. 如现有 `aggregate_metrics.py` 不够，新增或扩展轻量分析工具，输出机器可读 `summary.json` 或 `metrics.json`。
3. 等待 H6 case-study 选择标准；如需要，提供从 summary/solution/verify 中提取 case evidence 的脚本。
4. 不新增 LLM/SFT/direct-generation 功能，除非 `project_manager_agent` 明确恢复 H8。

## 约束

- 默认只写新文件，除非获得批准。
- 保持依赖最小。
- 复用现有 solver/verifier import。
- 不启动长任务。

## 等待事项

- experiment_manager_agent 给出 H5/H6 的具体 schema 与输出路径。

## 2026-07-11 H5/H6 支援边界

项目主管已给出任务单：

- `experiments/aaai2026/h5_h6_next_phase_task_brief.md`

`dev_framework_agent` 只有在 `experiment_manager_agent` 判断现有 summary/manifest join 不足时才补代码。若补代码：

- 路径放在 `experiments/aaai2026/`。
- 输出必须是机器可读 JSON 或 markdown draft。
- 不修改 solver/verifier/checker 语义。
- 不启动长任务。
- 不扩展 E5/E6/E7。
