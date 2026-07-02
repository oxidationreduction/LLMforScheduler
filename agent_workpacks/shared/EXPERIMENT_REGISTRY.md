# 实验登记表

| ID | 负责人 | 实验 | 范围 | 状态 | 产物 |
|---|---|---|---|---|---|
| E0 | experiment_manager_agent | 已有 670 单结果审计 | 只读已有 summary | ready | `results/raw_view/all_machine_capacity_dynamic_chunk25_20260626_tl120/summary.json` |
| E1 | dev_runner_agent | 复现当前 full 670 solver | 全量 670 单 | planned | TBD |
| E2 | dev_runner_agent | Dispatching-rule baselines | 全量 670 或 test 133 | planned | TBD |
| E3 | dev_runner_agent | Chunked wavefront 消融 | 全量 670 或 test 133 | planned | TBD |
| E4 | dev_runner_agent | CP-SAT 子集 baseline | 分层 50 单 | planned | TBD |
| E5 | dev_framework_agent | LLM tool-agent harness | test 133 | planned | TBD |
| E6 | dev_framework_agent | LLM 策略选择 SFT 数据/LoRA | train/dev/test split | planned | TBD |
| E7 | dev_runner_agent | Direct LLM 排班生成 baseline | 分层 30 单 | planned | TBD |
| E8 | experiment_manager_agent | 复杂度 scaling 和最终表格 | 所有已验证产物 | planned | TBD |
| E9 | paper_writer_agent | AAAI 论文草稿 | 论文各章节 | planned | TBD |

## 状态定义

- `planned`：已定义，未开始。
- `running`：tmux 或进程正在运行。
- `blocked`：需要项目主管决策或等待上游产物。
- `complete`：summary 和产物已经交付。
- `dropped`：项目主管明确取消。
