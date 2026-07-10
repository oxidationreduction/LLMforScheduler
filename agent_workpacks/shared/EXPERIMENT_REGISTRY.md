# 实验登记表

| ID | 负责人 | 实验 | 范围 | 状态 | 产物 |
|---|---|---|---|---|---|
| E0 | experiment_manager_agent | 已有 670 单结果审计与 split/metrics 冻结 | 只读已有 summary + date split | complete | `experiments/aaai2026/split_manifest.json`; `experiments/aaai2026/metrics_timed_greedy_existing.json`; `results/raw_view/all_machine_capacity_dynamic_chunk25_20260626_tl120/summary.json` |
| E1 | dev_runner_agent | 复现当前 full 670 solver | 全量 670 单 | complete | `results/raw_view/e1_full670_repro_20260703_232018/summary.json`; `experiments/aaai2026/metrics_e1_full670_repro.json`；670 单，576 verify ok / 94 infeasible_proven / 0 unsolved / 0 verify invalid |
| E2 | dev_runner_agent | Dispatching-rule baselines | full 670 | complete | `experiments/aaai2026/metrics_e2_dispatch_baselines_20260707_153730.json`; summaries: `results/raw_view/e2_dispatch_earliest_due_20260707_153730/summary.json`, `results/raw_view/e2_dispatch_round_robin_product_20260707_153730/summary.json`, `results/raw_view/e2_dispatch_largest_route_work_20260707_153730/summary.json`, `results/raw_view/e2_dispatch_smallest_route_work_20260707_153730/summary.json`; best verified ok 548, worst unsolved 34, verify invalid 0 |
| E3 | dev_runner_agent | Chunked wavefront 消融 | full 670 | complete | `experiments/aaai2026/metrics_e3_wavefront_ablation_20260707_153731.json`; summaries: `results/raw_view/e3_wavefront_chunk5_20260707_153731/summary.json`, `results/raw_view/e3_wavefront_chunk10_20260707_153731/summary.json`, `results/raw_view/e3_wavefront_chunk25_20260707_153731/summary.json`; chunk25 matched 576 verify ok / 94 infeasible_proven / 0 unsolved / 0 verify invalid |
| E4 | dev_runner_agent | CP-SAT 子集 baseline | 分层 50 单，120s/case 主表 | complete | `results/raw_view/e4_cpsat_stratified50_tl120_20260709_153557/summary.json`; `results/raw_view/e4_cpsat_stratified50_tl120_20260709_153557/metrics.json`; 50 单，44 verify ok / 6 infeasible_proven / 0 unsolved / 0 verify invalid；method_counts `{'timed_cpsat': 39, 'timed_cpsat_batched': 11}`；未启动 600s 附录版 |
| E5 | dev_runner_agent | LLM tool-agent harness | test 133 | running | prompts ready: `results/raw_view/e5_llm_tool_agent_test133_20260710_232523/prompts.jsonl`；仅 prompts，133 条 strict JSON tool-call prompts；pending model `responses.jsonl`, `parsed_tool_calls.jsonl`, `summary.json`, verifier metrics；未运行 direct LLM schedule generation |
| E6 | dev_framework_agent | LLM 策略选择 SFT 数据/LoRA | train/dev only for SFT，test 保留评估 | planned | `experiments/aaai2026/sft_strategy_data*.jsonl` + LoRA output |
| E7 | dev_runner_agent | Direct LLM 排班生成 baseline | 分层 30 单 | planned | `direct_baseline_validation.json` |
| E8 | experiment_manager_agent | 复杂度 scaling 和最终表格 | 所有已验证产物 | planned | TBD |
| E9 | paper_writer_agent | AAAI 论文草稿 | 论文各章节 | planned | TBD |

## 状态定义

- `planned`：已定义，未开始。
- `running`：tmux 或进程正在运行。
- `blocked`：需要项目主管决策或等待上游产物。
- `complete`：summary 和产物已经交付。
- `dropped`：项目主管明确取消。

## 冻结接口

- split manifest：`experiments/aaai2026/build_split_manifest.py --out experiments/aaai2026/split_manifest.json`
- metrics：`experiments/aaai2026/aggregate_metrics.py --split-manifest ... --run name=results_dir --out metrics.json`
- tool-call parser：`experiments/aaai2026/llm_tool_schema.py --parse llm_outputs.jsonl --out parsed_tool_calls.jsonl`
- SFT data：`experiments/aaai2026/build_sft_data.py --splits train dev ...`
- direct baseline QA：`experiments/aaai2026/validate_direct_baseline.py --llm-solutions direct_outputs ...`
