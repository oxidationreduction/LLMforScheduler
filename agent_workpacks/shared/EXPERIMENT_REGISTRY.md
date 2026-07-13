# 实验登记表

| ID | 负责人 | 实验 | 范围 | 状态 | 产物 |
|---|---|---|---|---|---|
| E0 | experiment_manager_agent | 已有 670 单结果审计与 split/metrics 冻结 | 只读已有 summary + date split | complete | `experiments/aaai2026/split_manifest.json`; `experiments/aaai2026/metrics_timed_greedy_existing.json`; `results/raw_view/all_machine_capacity_dynamic_chunk25_20260626_tl120/summary.json` |
| E1 | dev_runner_agent | 复现当前 full 670 solver | 全量 670 单 | complete | `results/raw_view/e1_full670_repro_20260703_232018/summary.json`; `experiments/aaai2026/metrics_e1_full670_repro.json`；670 单，576 verify ok / 94 infeasible_proven / 0 unsolved / 0 verify invalid |
| E2 | dev_runner_agent | Dispatching-rule baselines | full 670 | complete | `experiments/aaai2026/metrics_e2_dispatch_baselines_20260707_153730.json`; summaries: `results/raw_view/e2_dispatch_earliest_due_20260707_153730/summary.json`, `results/raw_view/e2_dispatch_round_robin_product_20260707_153730/summary.json`, `results/raw_view/e2_dispatch_largest_route_work_20260707_153730/summary.json`, `results/raw_view/e2_dispatch_smallest_route_work_20260707_153730/summary.json`; best verified ok 548, worst unsolved 34, verify invalid 0 |
| E3 | dev_runner_agent | Chunked wavefront 消融 | full 670 | complete | `experiments/aaai2026/metrics_e3_wavefront_ablation_20260707_153731.json`; summaries: `results/raw_view/e3_wavefront_chunk5_20260707_153731/summary.json`, `results/raw_view/e3_wavefront_chunk10_20260707_153731/summary.json`, `results/raw_view/e3_wavefront_chunk25_20260707_153731/summary.json`; chunk25 matched 576 verify ok / 94 infeasible_proven / 0 unsolved / 0 verify invalid |
| E4 | dev_runner_agent | CP-SAT 子集 baseline | 分层 50 单，120s/case 主表 | complete | `results/raw_view/e4_cpsat_stratified50_tl120_20260709_153557/summary.json`; `results/raw_view/e4_cpsat_stratified50_tl120_20260709_153557/metrics.json`; 50 单，44 verify ok / 6 infeasible_proven / 0 unsolved / 0 verify invalid；method_counts `{'timed_cpsat': 39, 'timed_cpsat_batched': 11}`；未启动 600s 附录版 |
| E5 | dev_runner_agent | LLM tool-agent harness | test 133 | paused | prompts ready: `results/raw_view/e5_llm_tool_agent_test133_20260710_232523/prompts.jsonl`；仅 prompts，133 条 strict JSON tool-call prompts；尚无 `responses.jsonl`, `parsed_tool_calls.jsonl`, `summary.json` 或 verifier metrics；纯启发式重规划后暂停主线，仅 appendix/motivation candidate |
| E6 | dev_framework_agent | LLM 策略选择 SFT 数据/LoRA | train/dev only for SFT，test 保留评估 | paused | 纯启发式重规划后暂停；除非项目主管明确恢复，否则不启动 LoRA/SFT |
| E7 | dev_runner_agent | Direct LLM 排班生成 baseline | 分层 30 单 | paused | 纯启发式重规划后暂停；只可作为可选 LLM appendix/motivation |
| E8 | experiment_manager_agent | 复杂度 scaling 和最终表格 | 所有已验证产物 | superseded | 由 H5/H6/H-series paper strategy 承接 |
| E9 | paper_writer_agent | AAAI 论文草稿 | 论文各章节 | planned | 按 H-series 纯启发式主线撰写 |

## H-series 主动实验轨道

| ID | 负责人 | 实验 | 范围 | 状态 | 产物 |
|---|---|---|---|---|---|
| H0 | project_manager_agent + experiment_manager_agent | 纯启发式叙事、登记、claim 和 agent 规则重写 | workpacks + paper plan | complete | `experiments/aaai2026/heuristic_replan_experiment_plan.md`; `experiments/aaai2026/h_series_heuristic_table_draft.md`; `agent_workpacks/shared/DECISIONS.md`; `agent_workpacks/shared/RISKS.md` |
| H1 | experiment_manager_agent | 主方法：portfolio timed heuristic | full 670，复用 E0/E1 | paper_ready | `experiments/aaai2026/metrics_timed_greedy_existing.json`; `experiments/aaai2026/metrics_e1_full670_repro.json`; label `portfolio timed heuristic`；670 单，576 verify ok / 94 infeasible_proven / 0 unsolved / 0 verify invalid；H-series table QA PASS |
| H2 | experiment_manager_agent | 固定 dispatching-rule baseline | full 670，复用 E2 | paper_ready | `experiments/aaai2026/metrics_e2_dispatch_baselines_20260707_153730.json`; fixed rules 留下 28-34 unsolved；0 verify invalid；H-series table QA PASS |
| H3 | experiment_manager_agent | chunked wavefront 消融 | full 670，复用 E3 | paper_ready | `experiments/aaai2026/metrics_e3_wavefront_ablation_20260707_153731.json`; chunk5/10/25 分别 4/2/0 unsolved；chunk25 为 576 ok / 94 infeasible / 0 invalid；H-series table QA PASS |
| H4 | experiment_manager_agent | CP-SAT 子集 baseline | stratified 50，120s/case，复用 E4 | paper_ready | `results/raw_view/e4_cpsat_stratified50_tl120_20260709_153557/metrics.json`; label 必须为 `CP-SAT stratified-50 baseline, 120s/case`；不得与 full-670 rows 按 case_count 等价比较；H-series table QA PASS |
| H5 | experiment_manager_agent + dev_framework_agent | 规模/难度分桶分析 | full-670 registered artifacts | assigned | 任务单：`experiments/aaai2026/h5_h6_next_phase_task_brief.md`；输出 `summary.json` 或 `metrics.json`；按 operation_count、total_work_minutes、machine_load_ratio、worker_day_count 分桶；缺失特征必须显式标 `unavailable` |
| H6 | experiment_manager_agent + qa_repro_agent | verifier case study | 4 个代表 case | assigned | 任务单：`experiments/aaai2026/h5_h6_next_phase_task_brief.md`；2 个复杂可行、1 个库存抵扣/零任务、1 个容量下界 infeasible；每个 case 指向 order/solution/verify 或 infeasibility artifact |
| H7 | dev_runner_agent | 可选 CP-SAT 600s 附录 | stratified 50，600s/case | optional | 仅在项目主管明确启动时运行；必须新目录、tmux、CPU-only |
| H8 | dev_runner_agent | 可选 LLM appendix/motivation | 小规模，非主表 | paused | 可复用 E5 prompts 或 direct LLM 分层 30；不得进入主实验比较 |

## 状态定义

- `planned`：已定义，未开始。
- `running`：tmux 或进程正在运行。
- `blocked`：需要项目主管决策或等待上游产物。
- `paused`：项目主管重规划后暂停，不在主动主线推进。
- `evidence_ready`：已有已登记证据可用于后续表格/QA，但未必已生成 H-series 专用底稿。
- `in_progress`：当前正在更新或整合。
- `assigned`：任务单已交付给负责人，但尚未产出正式 artifact。
- `paper_ready`：表格/数字已通过 QA gate，可在遵守 claim 边界时交给论文写手使用。
- `optional`：仅在项目主管明确启动时执行。
- `superseded`：由新的登记项承接，历史记录保留。
- `complete`：summary 和产物已经交付。
- `dropped`：项目主管明确取消。

## 冻结接口

- split manifest：`experiments/aaai2026/build_split_manifest.py --out experiments/aaai2026/split_manifest.json`
- metrics：`experiments/aaai2026/aggregate_metrics.py --split-manifest ... --run name=results_dir --out metrics.json`
- H-series plan：`experiments/aaai2026/heuristic_replan_experiment_plan.md`
- H-series table draft：`experiments/aaai2026/h_series_heuristic_table_draft.md`
- LLM appendix-only parser：`experiments/aaai2026/llm_tool_schema.py --parse llm_outputs.jsonl --out parsed_tool_calls.jsonl`
- Paused SFT data：`experiments/aaai2026/build_sft_data.py --splits train dev ...`
- Paused direct baseline QA：`experiments/aaai2026/validate_direct_baseline.py --llm-solutions direct_outputs ...`
