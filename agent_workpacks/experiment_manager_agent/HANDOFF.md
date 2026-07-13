# experiment_manager_agent Handoff

## 当前状态

2026-07-11 更新：E0-E4 已被映射到 H-series 纯启发式主线。`experiments/aaai2026/h_series_heuristic_table_draft.md` 已通过 `qa_repro_agent` H-series table QA gate。

历史第一步已完成：split manifest 和现有 timed_greedy 基线 metrics 已冻结，并已登记到共享产物表。

关键产物：

- `experiments/aaai2026/split_manifest.json`
- `experiments/aaai2026/metrics_timed_greedy_existing.json`
- 参考 summary：`results/raw_view/all_machine_capacity_dynamic_chunk25_20260626_tl120/summary.json`

关键数字：

- split：train 473，dev 64，test 133。
- OOD/recent：2025-only，共 64，作为 test 内额外标签。
- existing timed_greedy：670 cases，576 verify ok，94 infeasible_proven，0 unsolved，0 verify invalid。

## 已完成任务

1. 审计已有全量结果 summary。
2. 定义 train/validation/test/OOD split：
   - Train：2020-2023。
   - Validation：2024H1。
   - Test：2024H2-2025。
   - OOD/recent：2025-only。
3. 定义指标：
   - verify ok rate；
   - infeasible_proven count；
   - unsolved rate；
   - verifier error count；
   - runtime mean/median/p90/p95/max；
   - task count；
   - makespan；
   - resource balance。
4. 将 split 和 metrics 产物登记到 `shared/ARTIFACTS.md`。
5. 将 E0 更新为 complete。

## 下一步

- 将 QA-passed `experiments/aaai2026/h_series_heuristic_table_draft.md` 交给 `paper_writer_agent` 使用，并保留 QA claim 边界。
- 设计 H5 complexity/difficulty metrics schema：operation_count、total_work_minutes、machine_load_ratio、worker_day_count；若特征不可用，显式标 `unavailable`。
- 设计 H6 verifier case-study selection：2 个复杂可行、1 个库存抵扣/零任务、1 个容量下界 infeasible。
- E5/E6/E7 暂停主线，不进入主表或主实验 claim。

## E2/E3 结果接收：dispatching-rule baselines 与 chunked wavefront 消融

dev_runner_agent 已完成 E2/E3，scope 均为 full 670，未降级 test 133。所有结果已登记到 `shared/ARTIFACTS.md` 和 `shared/EXPERIMENT_REGISTRY.md`。

可用于 E8 表格的 metrics：

- E2 dispatching-rule baselines：`experiments/aaai2026/metrics_e2_dispatch_baselines_20260707_153730.json`
- E3 chunked wavefront 消融：`experiments/aaai2026/metrics_e3_wavefront_ablation_20260707_153731.json`

E2 summary 路径和关键数字：

| strategy | summary | verify ok | infeasible_proven | unsolved | verify invalid |
|---|---|---:|---:|---:|---:|
| earliest_due | `results/raw_view/e2_dispatch_earliest_due_20260707_153730/summary.json` | 546 | 94 | 30 | 0 |
| round_robin_product | `results/raw_view/e2_dispatch_round_robin_product_20260707_153730/summary.json` | 548 | 94 | 28 | 0 |
| largest_route_work | `results/raw_view/e2_dispatch_largest_route_work_20260707_153730/summary.json` | 548 | 94 | 28 | 0 |
| smallest_route_work | `results/raw_view/e2_dispatch_smallest_route_work_20260707_153730/summary.json` | 542 | 94 | 34 | 0 |

E3 summary 路径和关键数字：

| strategy | summary | verify ok | infeasible_proven | unsolved | verify invalid |
|---|---|---:|---:|---:|---:|
| chunked_wavefront_5 | `results/raw_view/e3_wavefront_chunk5_20260707_153731/summary.json` | 572 | 94 | 4 | 0 |
| chunked_wavefront_10 | `results/raw_view/e3_wavefront_chunk10_20260707_153731/summary.json` | 574 | 94 | 2 | 0 |
| chunked_wavefront_25 | `results/raw_view/e3_wavefront_chunk25_20260707_153731/summary.json` | 576 | 94 | 0 | 0 |

论文表格建议：

- E2 可作为固定 dispatching rule 对照，展示单一规则会带来 28-34 个 unsolved，弱于多策略/chunk25。
- E3 可作为 wavefront chunk size 消融，`chunked_wavefront_25` 与 E1/existing baseline 的 576 verify ok、94 infeasible_proven、0 unsolved 持平。
- 不要把 E2/E3 写成 LLM 结果；它们是 deterministic solver strategy ablations。

## E0-E3 论文表格底稿：交给 QA gate

已生成 E0-E3 paper-ready 表格底稿：

- `experiments/aaai2026/e0_e3_paper_table_draft.md`

该底稿 supersedes `experiments/aaai2026/e0_e1_paper_table_draft.md` for E0-E3 table preparation，并只引用已登记 artifacts：

- E0：`experiments/aaai2026/metrics_timed_greedy_existing.json`
- E1：`experiments/aaai2026/metrics_e1_full670_repro.json`
- E2：`experiments/aaai2026/metrics_e2_dispatch_baselines_20260707_153730.json`
- E3：`experiments/aaai2026/metrics_e3_wavefront_ablation_20260707_153731.json`

状态：已交给 `qa_repro_agent` 做 table-specific QA gate；在 QA 明确通过该表格底稿前，不交给 `paper_writer_agent` 作为正文可引用结果。

QA 重点：

- 所有表格行必须能追溯到 metrics 和 summary。
- 不得混入未登记旧目录。
- E2/E3 只能写成 deterministic solver strategy ablations。
- 不得写 LLM、CP-SAT、新算法优越性、全局最优、完备现实不可行或 runtime speedup claim。

## E0-E3 表格底稿 QA gate 结果

更新时间：2026-07-09T15:36:44+08:00

`qa_repro_agent` 已完成 `experiments/aaai2026/e0_e3_paper_table_draft.md` 的 table-specific QA gate，结论：PASS。所有检查均为轻量只读检查；未启动长任务，未生成或保留临时文件。

数字核对结果：

- 底稿 12 个表格数据行均可追溯到 E0/E1/E2/E3 metrics 和对应 summary。
- E0：670 cases，coverage 1.0，576 ok，94 infeasible_proven，0 unsolved，0 invalid。
- E1：670 cases，coverage 1.0，576 ok，94 infeasible_proven，0 unsolved，0 invalid。
- E2 fixed dispatching rules：full 670 上留下 28-34 个 unsolved；该结论仅限固定单一 dispatching rule 消融。
- E3 `chunked_wavefront_25`：576 ok，94 infeasible_proven，0 unsolved，0 invalid；该结论仅限 aggregate counts 与 E0/E1 持平。

Claim 边界：

- E2/E3 只能写成 deterministic solver strategy ablations。
- `chunked_wavefront_25` 的结果不能扩写为质量等价、全局最优或泛化能力证明。
- E2/E3 不得写成 LLM 结果、CP-SAT 结果、新算法优越性、工业 KPI 提升或 runtime speedup。

状态：该表格底稿可以进入 `paper_writer_agent`，但正文 claim 必须继续遵守上述边界。

## E4 结果接收：CP-SAT stratified-50 baseline

更新时间：2026-07-09T15:43:00+08:00

dev_runner_agent 已完成 E4 120s/case 主表版本，未启动 600s/case 附录版。

可用于 E8 表格的产物：

- summary：`results/raw_view/e4_cpsat_stratified50_tl120_20260709_153557/summary.json`
- metrics：`results/raw_view/e4_cpsat_stratified50_tl120_20260709_153557/metrics.json`
- manifest：`experiments/aaai2026/e4_cpsat_stratified50_manifest.json`

关键数字：

- scope：stratified 50，不是 full 670。
- time limit：120s/case。
- case_count：50，coverage_rate：1.0。
- status_counts：`{'feasible': 42, 'infeasible_proven': 6, 'optimal': 2}`。
- verify_counts：`{'ok': 44, 'not_applicable': 6}`。
- method_counts：`{'timed_cpsat': 39, 'timed_cpsat_batched': 11}`；无 `timed_greedy`。
- not_solved_count：0。
- verify_invalid_count：0。
- solve_seconds：mean 5.305，median 2.395，p90 13.952，p95 19.366，max 38.795。

论文表格口径：

- E4 只能写作 `CP-SAT stratified-50 baseline, 120s/case`。
- 不要把 E4 与 E0-E3 full-670 结果直接按 case_count 等价比较；主表需要显式标注 subset size 50。
- `optimal` 仍需遵守项目 claim 边界，不要扩写为现实工厂全局最优。
- E4 已登记到 `shared/ARTIFACTS.md` 和 `shared/EXPERIMENT_REGISTRY.md`；建议交给 `qa_repro_agent` 做 E4 artifact QA gate 后再进入 paper table。

## E4 artifact QA gate 结果

更新时间：2026-07-09T16:22:27+08:00

`qa_repro_agent` 已完成 E4 artifact QA gate，结论：PASS。检查为轻量只读，不启动长任务，不保留临时文件。

数字核对：

- manifest：50 cases，train 35 / dev 5 / test 10，easy 17 / medium 17 / hard 16。
- summary / metrics：50 cases，coverage 1.0，44 verify ok，6 infeasible_proven，0 unsolved，0 verify invalid。
- status_counts：`{'feasible': 42, 'infeasible_proven': 6, 'optimal': 2}`。
- verify_counts：`{'ok': 44, 'not_applicable': 6}`。
- method_counts：`{'timed_cpsat': 39, 'timed_cpsat_batched': 11}`，无 `timed_greedy`。
- elapsed_seconds：265.9068440308329。

Gate 结论：

- E4 case id 与 manifest 完全一致，无缺失、额外或重复。
- 非可验证状态均为 `not_applicable`。
- registry / artifacts 与 summary / metrics 数字一致。

Claim 边界：

- E4 只能写为 `CP-SAT stratified-50 baseline, 120s/case`。
- E4 不是 full-670，不是 LLM 结果，不是新算法主贡献。
- `optimal` 不得扩写为现实工厂全局最优。
- `infeasible_proven` 不得扩写为完备现实不可行证明。

## E4 E8 表格候选与 E0-E4 底稿

更新时间：2026-07-09T16:25:01+08:00

已生成 E4 E8 table candidate note：

- `experiments/aaai2026/e4_cpsat_stratified50_table_candidate.md`

随后检测到 `qa_repro_agent` 已记录 E4 artifact QA PASS，因此已生成 E0-E4 paper-ready draft：

- `experiments/aaai2026/e0_e4_paper_table_draft.md`

QA evidence：

- E0-E3 table-specific QA PASS：`agent_workpacks/qa_repro_agent/HANDOFF.md`
- E4 artifact QA PASS：`agent_workpacks/qa_repro_agent/HANDOFF.md`

纳入 E8 的口径：

- Label 必须是 `CP-SAT stratified-50 baseline, 120s/case`。
- E4 是 stratified 50 subset，不是 full 670。
- E4 不得与 E0-E3 full-670 rows 按 case_count 等价比较。
- E4 不是 LLM 结果、主方法结果、全局最优证据或现实完备不可行证明。

底稿结构：

- E0-E3 full-670 table group 保持在一起。
- E4 放入单独 CP-SAT stratified-50 section。
- 表格明确警告 E4 不能与 E0-E3 按 case_count 等价比较。

## 2026-07-11 H-series 纯启发式表格底稿

已生成 H-series heuristic-first paper table draft：

- `experiments/aaai2026/h_series_heuristic_table_draft.md`

该底稿复用已 QA 通过的 E0-E4 证据，不新增实验结果：

- H1：E1 reproduced timed_greedy，主表标签 `portfolio timed heuristic`，full 670，576 verify ok / 94 infeasible_proven / 0 unsolved / 0 invalid。
- H2：E2 fixed dispatching-rule baselines，full 670，固定单一规则留下 28-34 unsolved。
- H3：E3 chunked wavefront ablation，full 670，chunk5/10/25 分别 4/2/0 unsolved。
- H4：E4 `CP-SAT stratified-50 baseline, 120s/case`，50-case subset，44 verify ok / 6 infeasible_proven / 0 unsolved / 0 invalid。

交给 QA 的重点：

- H1-H3 是 full-670 deterministic heuristic / strategy ablation。
- H4 是 CP-SAT stratified-50 subset，不得与 H1-H3 做 case-count-equivalent 比较。
- E5/E6/E7 不得进入主实验比较。
- H5/H6 在没有机器可读 metrics 或 case-study artifact 前不得写入正文结果。

下一步由 experiment_manager_agent 负责：

1. 生成 H5 schema 与所需特征可用性检查。
2. 提出 H6 候选 case list，附 order/solution/verify 或 infeasibility artifact 路径。
3. 将通过 QA 的 H-series table 和 H5/H6 结果交给 `paper_writer_agent`。

## 2026-07-11 H-series table QA gate 结果

更新时间：2026-07-11T04:45:46+08:00

`qa_repro_agent` 已完成 H-series heuristic-first paper table draft QA gate，结论：PASS。

状态：

- `experiments/aaai2026/h_series_heuristic_table_draft.md` 可交给 `paper_writer_agent` 使用。
- H1-H3 保持 full-670 heuristic / strategy ablation 口径。
- H4 保持 `CP-SAT stratified-50 baseline, 120s/case` 口径，不与 H1-H3 做等 case_count 比较。
- H5/H6 仍需新增机器可读 metrics / case-study artifacts 后才能进入正文结果。
- E5/E6/E7 继续暂停主线，不进入主实验比较。

下一步由 experiment_manager_agent 负责：

1. 生成 H5 schema 与特征可用性检查。
2. 提出 H6 候选 case list，附 order/solution/verify 或 infeasibility artifact 路径。
3. 将 QA-passed H-series table 和后续 H5/H6 结果交给 `paper_writer_agent`。

## 2026-07-11 H5/H6 任务单接收

任务单路径：

- `experiments/aaai2026/h5_h6_next_phase_task_brief.md`

必须产出：

- `experiments/aaai2026/h5_complexity_difficulty_metrics.json`
- `experiments/aaai2026/h5_complexity_difficulty_table_draft.md`
- `experiments/aaai2026/h6_verifier_case_study_manifest.json`
- `experiments/aaai2026/h6_verifier_case_study_draft.md`

H5 注意：

- 先做特征可用性报告。
- `operation_count`、`total_work_minutes`、`worker_day_count` 可从 E1 summary / split manifest join 检查。
- `machine_load_ratio` 若没有可靠来源，必须标 `unavailable`。
- 不得把 `load_ratio` 静默改名为 `machine_load_ratio`。

H6 注意：

- 选择 2 个复杂可行 verifier-ok case。
- 选择 1 个库存抵扣/零任务/optimal case。
- 选择 1 个容量下界 infeasible case。
- 每个 case 必须有真实 order/solution/verify 或 infeasibility artifact 路径。

完成后交给 `qa_repro_agent` 做 H5/H6 QA gate。
