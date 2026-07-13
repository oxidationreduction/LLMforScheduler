# 产物登记表

所有长期保留的实验和论文产物都要登记在这里。smoke 测试临时文件清理后不要登记。

| 产物 | 生产者 | 路径 | 状态 | 备注 |
|---|---|---|---|---|
| 已有全量结果 summary | 既有结果 | `results/raw_view/all_machine_capacity_dynamic_chunk25_20260626_tl120/summary.json` | available | 670 单，576 verify ok，94 infeasible_proven |
| 已有全量 HTML index | 既有结果 | `results/html_view/all_machine_capacity_dynamic_chunk25_20260626_tl120/index.html` | available | 可视化 case 浏览入口 |
| 旧版 solver summary | 既有结果 | `results/raw_view/all_machine_capacity_dynamic_20260626_tl120/summary.json` | available | 旧对照，1 个 time_limit |
| AAAI 2026 实验框架 | dev_framework_agent | `experiments/aaai2026/` | available | 主线为 split、metrics、stratified manifest、H-series planning/table drafts；LLM tool schema、SFT data、direct baseline validator 仅保留为暂停的附录候选接口 |
| AAAI 2026 split manifest | experiment_manager_agent | `experiments/aaai2026/split_manifest.json` | available | 670 单；train 473，dev 64，test 133；2025-only OOD/recent 64 |
| 现有 timed_greedy 基线 metrics | experiment_manager_agent | `experiments/aaai2026/metrics_timed_greedy_existing.json` | available | 670 单；576 verify ok，94 infeasible_proven，0 unsolved，0 verify invalid |
| E1 full 670 复现 summary | dev_runner_agent | `results/raw_view/e1_full670_repro_20260703_232018/summary.json` | available | 670 单；576 verify ok，94 infeasible_proven，0 unsolved，0 verify invalid；elapsed 167.628s |
| E1 full 670 复现 metrics | dev_runner_agent | `experiments/aaai2026/metrics_e1_full670_repro.json` | available | 与 existing baseline case-level 状态一致；coverage 1.0 |
| E0/E1 论文表格底稿 | experiment_manager_agent | `experiments/aaai2026/e0_e1_paper_table_draft.md` | available | 只使用已登记 E0/E1 artifacts；含 claim 边界和 dev-agent 交接说明 |
| E2 dispatch earliest_due summary | dev_runner_agent | `results/raw_view/e2_dispatch_earliest_due_20260707_153730/summary.json` | available | full 670；546 verify ok，94 infeasible_proven，30 unsolved，0 verify invalid；elapsed 149.063s |
| E2 dispatch round_robin_product summary | dev_runner_agent | `results/raw_view/e2_dispatch_round_robin_product_20260707_153730/summary.json` | available | full 670；548 verify ok，94 infeasible_proven，28 unsolved，0 verify invalid；elapsed 139.882s |
| E2 dispatch largest_route_work summary | dev_runner_agent | `results/raw_view/e2_dispatch_largest_route_work_20260707_153730/summary.json` | available | full 670；548 verify ok，94 infeasible_proven，28 unsolved，0 verify invalid；elapsed 140.998s |
| E2 dispatch smallest_route_work summary | dev_runner_agent | `results/raw_view/e2_dispatch_smallest_route_work_20260707_153730/summary.json` | available | full 670；542 verify ok，94 infeasible_proven，34 unsolved，0 verify invalid；elapsed 147.854s |
| E2 dispatch metrics | dev_runner_agent | `experiments/aaai2026/metrics_e2_dispatch_baselines_20260707_153730.json` | available | 4 个 full-670 fixed dispatching rules；coverage 1.0；无 test133 降级 |
| E3 wavefront chunk5 summary | dev_runner_agent | `results/raw_view/e3_wavefront_chunk5_20260707_153731/summary.json` | available | full 670；572 verify ok，94 infeasible_proven，4 unsolved，0 verify invalid；elapsed 157.910s |
| E3 wavefront chunk10 summary | dev_runner_agent | `results/raw_view/e3_wavefront_chunk10_20260707_153731/summary.json` | available | full 670；574 verify ok，94 infeasible_proven，2 unsolved，0 verify invalid；elapsed 160.155s |
| E3 wavefront chunk25 summary | dev_runner_agent | `results/raw_view/e3_wavefront_chunk25_20260707_153731/summary.json` | available | full 670；576 verify ok，94 infeasible_proven，0 unsolved，0 verify invalid；elapsed 172.358s |
| E3 wavefront metrics | dev_runner_agent | `experiments/aaai2026/metrics_e3_wavefront_ablation_20260707_153731.json` | available | 3 个 full-670 chunked_wavefront 消融；chunk25 与 E1 status/verify counts 持平；无 test133 降级 |
| E1-E3 QA gate 记录 | qa_repro_agent | `agent_workpacks/qa_repro_agent/HANDOFF.md` | available | 2026-07-09 QA gate PASS；JSON/path/split/summary/verify/claim 边界已核对；含措辞注意点 |
| E0-E3 论文表格底稿 | experiment_manager_agent | `experiments/aaai2026/e0_e3_paper_table_draft.md` | available | 基于已登记 E0/E1/E2/E3 metrics；含主表、E2/E3 消融表和 claim 边界；已交给 qa_repro_agent 做 table-specific QA gate |
| E4 CP-SAT stratified-50 summary | dev_runner_agent | `results/raw_view/e4_cpsat_stratified50_tl120_20260709_153557/summary.json` | available | 分层 50 单；120s/case；CPU-only；44 verify ok，6 infeasible_proven，0 unsolved，0 verify invalid；未启动 600s 附录版 |
| E4 CP-SAT stratified-50 metrics | dev_runner_agent | `results/raw_view/e4_cpsat_stratified50_tl120_20260709_153557/metrics.json` | available | coverage 1.0；method_counts `timed_cpsat=39, timed_cpsat_batched=11`；无 `timed_greedy`；elapsed 265.907s |
| E4 CP-SAT stratified-50 表格候选 | experiment_manager_agent | `experiments/aaai2026/e4_cpsat_stratified50_table_candidate.md` | available | E8 候选记录；E4 artifact QA PASS 已满足；由 `experiments/aaai2026/e0_e4_paper_table_draft.md` 承接为 paper-ready draft |
| E0-E4 论文表格底稿 | experiment_manager_agent | `experiments/aaai2026/e0_e4_paper_table_draft.md` | available | E0-E3 full-670 与 E4 CP-SAT stratified-50 分区呈现；E4 artifact QA PASS 后生成；禁止 case_count 等价比较 |
| 纯启发式重规划策略 | project_manager_agent | `experiments/aaai2026/heuristic_replan_experiment_plan.md` | active | H0-H8 主动轨道；论文主线改为 verifier-backed industrial heuristic scheduling engine；E5/E6/E7 暂停主线 |
| H-series 启发式论文表格底稿 | experiment_manager_agent | `experiments/aaai2026/h_series_heuristic_table_draft.md` | qa_passed | 复用 E0-E4 QA 通过证据并改写为 H1-H4 启发式主线；2026-07-11 H-series table QA gate PASS；H5/H6 尚未进入表格 |
| H5/H6 下一阶段任务单 | project_manager_agent | `experiments/aaai2026/h5_h6_next_phase_task_brief.md` | assigned | 交给 experiment_manager_agent：生成 H5 complexity/difficulty metrics 与 H6 verifier case-study artifacts；E5/E6/E7 继续暂停 |
| H5 complexity/difficulty 构建工具 | dev_framework_agent | `experiments/aaai2026/build_h5_complexity_difficulty.py` | available | 只读 full-670 manifest、E1 summary 和 order JSON；支持拒绝覆盖生成及无写入复核；不读取 LLM 产物 |
| H5 complexity/difficulty metrics | experiment_manager_agent | `experiments/aaai2026/h5_complexity_difficulty_metrics.json` | qa_pending | E1 full-670；operation_count 与 machine_load_ratio 由现有 solver 语义派生，load_ratio 明确为非替代指标 |
| H5 complexity/difficulty table draft | experiment_manager_agent | `experiments/aaai2026/h5_complexity_difficulty_table_draft.md` | qa_pending | 与 H5 metrics 同源生成；12 个 feature-bucket 行；不得在 QA PASS 前进入论文主表 |
| H6 verifier case-study manifest | experiment_manager_agent | `experiments/aaai2026/h6_verifier_case_study_manifest.json` | qa_pending | 4 个 E1 anchored cases；solution/verify 路径来自 E1 summary，不使用 split manifest 旧路径 |
| H6 verifier case-study draft | experiment_manager_agent | `experiments/aaai2026/h6_verifier_case_study_draft.md` | qa_pending | 2 complex feasible、1 inventory zero-task、1 capacity-lower-bound infeasible；claim boundaries 已写明 |
| E5 LLM tool-agent test-133 prompts | dev_runner_agent | `results/raw_view/e5_llm_tool_agent_test133_20260710_232523/prompts.jsonl` | appendix_candidate | 仅 prompts；test 133 条；strict JSON tool-call prompts；尚无 responses、parsed tool calls、run summary 或 verifier metrics；E5 暂停主线，未运行 direct LLM schedule generation |

## 产物规则

- 新实验必须写入新结果目录。
- 不得覆盖已有结果。
- 每个实验输出应包含机器可读的 `summary.json` 或 `metrics.json`。
- 长任务日志只有在复现或解释结果需要时才保留。
