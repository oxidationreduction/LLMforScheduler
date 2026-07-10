# qa_repro_agent Handoff

## 当前状态

E4 artifact QA gate 已完成，结论为 PASS。E0-E3 table-specific QA gate 与 E1-E3 artifact QA gate PASS 记录继续保留。

## 初始 checklist

- 确认所有 JSON 文件可解析。
- 确认已有全量结果 summary 的关键数字。
- split manifest 出现后检查 split 泄漏。
- 确认每张论文表格都有来源 artifact。
- 确认所有 claim 都不超过证据边界。

## Claim 红线

- 不写全局最优 claim。
- 不写完备不可行证明 claim。
- LLM 实验完成前，不写 LLM 优越性 claim。
- 没有部署或用户研究证据时，不写工业 KPI claim。

## 2026-07-09 E1-E3 QA gate 记录

检查对象：

- E1: `experiments/aaai2026/metrics_e1_full670_repro.json`
- E2: `experiments/aaai2026/metrics_e2_dispatch_baselines_20260707_153730.json`
- E3: `experiments/aaai2026/metrics_e3_wavefront_ablation_20260707_153731.json`
- Registry: `agent_workpacks/shared/EXPERIMENT_REGISTRY.md`
- Artifacts: `agent_workpacks/shared/ARTIFACTS.md`

Gate 结论：PASS。

已完成只读检查，未修改实验结果，未生成临时文件。E1-E3 的 JSON 均可解析；metrics 中引用的 `split_manifest`、run path、summary path 均存在；从 summary cases 重新计数后，与 metrics 的 `overall` / `source_summary` 关键数字一致；所有 run 的 `verify_invalid_count=0`。

关键数字：

| Run | Cases | Verified ok | Infeasible proven | Unsolved | Verify invalid |
|---|---:|---:|---:|---:|---:|
| E1 full670 | 670 | 576 | 94 | 0 | 0 |
| E2 earliest_due | 670 | 546 | 94 | 30 | 0 |
| E2 round_robin_product | 670 | 548 | 94 | 28 | 0 |
| E2 largest_route_work | 670 | 548 | 94 | 28 | 0 |
| E2 smallest_route_work | 670 | 542 | 94 | 34 | 0 |
| E3 chunk5 | 670 | 572 | 94 | 4 | 0 |
| E3 chunk10 | 670 | 574 | 94 | 2 | 0 |
| E3 chunk25 | 670 | 576 | 94 | 0 | 0 |

Split / coverage：

- `experiments/aaai2026/split_manifest.json` 含 670 个 unique case/order path。
- split 分布为 train 473 / dev 64 / test 133，三者两两无交集。
- `ood_recent=64`，均在 test split。
- E1/E2/E3 每个 run 都覆盖 manifest 全 670：missing 0、extra 0、duplicate 0。
- E2/E3 应表述为 full 670 with split breakdown，不是 split-only 实验。

Registry / artifacts：

- `agent_workpacks/shared/EXPERIMENT_REGISTRY.md` 中 E1/E2/E3 的路径存在，关键数字与 metrics 一致。
- `agent_workpacks/shared/ARTIFACTS.md` 中 E1 和各 E2/E3 summary/metrics 路径存在，关键数字与 summary/metrics 一致。

Claim 边界：

- 未发现明确越界 claim。
- E2/E3 当前登记为 dispatching-rule baselines / chunked wavefront ablation，未写成 LLM 或 CP-SAT 结果。
- 允许使用 verified feasible、capacity-lower-bound infeasible、runtime、scale、strategy ablation。
- 不允许写全局最优、完备不可行证明、工业 KPI 提升、LLM 全面优越。
- 论文正文中不要把 E2/E3 写成 LLM 结果或 CP-SAT 结果。

措辞注意点：

- `README.md` 中 `infeasible_proven` 有“容量下界或精确模型证明不可行”的说明；论文里建议只写 `capacity-lower-bound infeasible under current model/verifier`。
- `README.md` 中 “optimal 16” 单独摘用容易被读成全局最优；论文里应说明这些主要是零任务/库存抵消 case。
- `ARTIFACTS.md` 中 E2 metrics 的“无 test133 降级”有歧义：若指覆盖率则成立；若指相对 E1 的 test verified-ok/unsolved，则 E2 test 是 114 ok / 6 unsolved，低于 E1 test 的 120 ok / 0 unsolved。

## 2026-07-09 E0-E3 表格底稿 QA gate 请求

表格底稿：

- `experiments/aaai2026/e0_e3_paper_table_draft.md`

必须审计的 metrics：

- E0：`experiments/aaai2026/metrics_timed_greedy_existing.json`
- E1：`experiments/aaai2026/metrics_e1_full670_repro.json`
- E2：`experiments/aaai2026/metrics_e2_dispatch_baselines_20260707_153730.json`
- E3：`experiments/aaai2026/metrics_e3_wavefront_ablation_20260707_153731.json`

split manifest：

- `experiments/aaai2026/split_manifest.json`

Table-specific QA checklist：

- 解析所有 listed metrics 和 metrics 内引用的 summary JSON。
- 确认每个表格行都能追溯到已登记 metrics 和 summary path。
- 用 `experiments/aaai2026/aggregate_metrics.py` 复算到临时路径，对比 stored metrics，完成后删除临时文件。
- 检查所有 E0-E3 rows 都是 `case_count=670`、`coverage_rate=1.0`、`verify_invalid_count=0`。
- 确认 E2/E3 没有 test 133 降级，也没有混入未登记旧目录。
- 确认底稿把 E2/E3 明确写成 deterministic solver strategy ablations。
- 可选运行现有 lightweight pytest gate；不要启动 solver benchmark、全量 verifier replay 或任何长任务。

Claim 边界：

- 允许写 E2 固定单一 dispatching rule 在 full 670 上留下 28-34 个 unsolved。
- 允许写 E3 `chunked_wavefront_25` 与 E0/E1 聚合计数持平：576 verify ok、94 infeasible_proven、0 unsolved、0 verify invalid。
- 允许写 E2/E3 是 full-670 deterministic solver strategy ablations。
- 禁止写 E2/E3 是 LLM 结果、CP-SAT 结果或新算法主贡献。
- 禁止把 runtime 差异写成算法加速；目前只能写 observed run records。
- 禁止写 feasible 等于全局最优，或 infeasible_proven 等于现实工厂绝对不可行。

QA 输出请报告给 `project_manager_agent` 和 `experiment_manager_agent`。

## 2026-07-09 E0-E3 table-specific QA gate

Gate 结论：PASS。

检查对象：

- 表格底稿：`experiments/aaai2026/e0_e3_paper_table_draft.md`
- E0 metrics：`experiments/aaai2026/metrics_timed_greedy_existing.json`
- E1 metrics：`experiments/aaai2026/metrics_e1_full670_repro.json`
- E2 metrics：`experiments/aaai2026/metrics_e2_dispatch_baselines_20260707_153730.json`
- E3 metrics：`experiments/aaai2026/metrics_e3_wavefront_ablation_20260707_153731.json`

执行方式：轻量只读 QA。未启动 solver benchmark、全量 verifier replay 或其他长任务；未生成或保留临时文件；未修改 metrics、summary 或表格底稿。

表格数字核对：

- 已核对 `experiments/aaai2026/e0_e3_paper_table_draft.md` 的 12 个表格数据行。
- Main table：E0、E1、E2 `round_robin_product`、E2 `largest_route_work`、E3 `chunked_wavefront_25`。
- E2 ablation：4 个 fixed dispatching rules。
- E3 ablation：3 个 chunked wavefront runs。
- `case_count`、`coverage`、`verified ok`、`infeasible_proven`、`unsolved`、`verify invalid`、`elapsed`、`solve seconds p50/p90/p95/max` 均可追溯到对应 metrics / summary。
- `status_counts` / `verify_counts` 与 metrics / summary 一致；展示顺序差异不构成数值差异。

关键 evidence：

| Run | Cases | Coverage | Verified ok | Infeasible proven | Unsolved | Verify invalid |
|---|---:|---:|---:|---:|---:|---:|
| E0 timed_greedy | 670 | 1.0 | 576 | 94 | 0 | 0 |
| E1 reproduced timed_greedy | 670 | 1.0 | 576 | 94 | 0 | 0 |
| E2 earliest_due | 670 | 1.0 | 546 | 94 | 30 | 0 |
| E2 round_robin_product | 670 | 1.0 | 548 | 94 | 28 | 0 |
| E2 largest_route_work | 670 | 1.0 | 548 | 94 | 28 | 0 |
| E2 smallest_route_work | 670 | 1.0 | 542 | 94 | 34 | 0 |
| E3 chunked_wavefront_5 | 670 | 1.0 | 572 | 94 | 4 | 0 |
| E3 chunked_wavefront_10 | 670 | 1.0 | 574 | 94 | 2 | 0 |
| E3 chunked_wavefront_25 | 670 | 1.0 | 576 | 94 | 0 | 0 |

Claim boundary：

- PASS：E2/E3 在表格底稿中写成 full-670 deterministic solver strategy ablations。
- PASS：forbidden claims 只出现在禁止清单中，没有出现在正向结论中。
- E2 fixed dispatching rules 只能写为 full 670 上留下 28-34 个 unsolved，不能扩写为整体最优或方法优越。
- E3 `chunked_wavefront_25` 只能写为 aggregate counts 与 E0/E1 持平，不能扩写为质量等价、全局最优或泛化能力证明。
- `best fixed dispatching rule` 只能解释为 E2 固定规则组内并列最好。

已报告给：

- `agent_workpacks/project_manager_agent/HANDOFF.md`
- `agent_workpacks/experiment_manager_agent/HANDOFF.md`

## 2026-07-09 E4 artifact QA gate 请求

E4 CP-SAT stratified-50 baseline 已完成，需做 artifact QA gate 后再进入论文 E8 表格。

检查对象：

- E4 manifest：`experiments/aaai2026/e4_cpsat_stratified50_manifest.json`
- E4 summary：`results/raw_view/e4_cpsat_stratified50_tl120_20260709_153557/summary.json`
- E4 metrics：`results/raw_view/e4_cpsat_stratified50_tl120_20260709_153557/metrics.json`
- Registry：`agent_workpacks/shared/EXPERIMENT_REGISTRY.md`
- Artifacts：`agent_workpacks/shared/ARTIFACTS.md`

必须检查：

- JSON 均可解析。
- manifest case_count 为 50，split 为 train 35 / dev 5 / test 10，difficulty 为 easy 17 / medium 17 / hard 16。
- summary/metrics coverage 为 1.0，missing/extra/duplicate case 均为 0。
- `method_counts` 不含 `timed_greedy`，只允许 CP-SAT 路径，例如 `timed_cpsat` / `timed_cpsat_batched`。
- `verify_invalid_count=0`，非可验证状态均为 `verify_status=not_applicable`。
- summary/metrics/registry/artifacts 的关键数字一致：50 cases，44 verify ok，6 infeasible_proven，0 unsolved，0 verify invalid。
- 结果目录是 `results/raw_view/e4_cpsat_stratified50_tl120_20260709_153557/`，不要混入 600s 附录版或其它结果目录。

Claim 边界：

- E4 只能写为 `CP-SAT stratified-50 baseline, 120s/case`。
- 禁止写成 full-670、LLM 结果、新算法主贡献、全局最优、完备现实不可行或工业 KPI 提升。

## 2026-07-09 E4 artifact QA gate

Gate 结论：PASS。

检查对象：

- Manifest：`experiments/aaai2026/e4_cpsat_stratified50_manifest.json`
- Summary：`results/raw_view/e4_cpsat_stratified50_tl120_20260709_153557/summary.json`
- Metrics：`results/raw_view/e4_cpsat_stratified50_tl120_20260709_153557/metrics.json`
- Registry：`agent_workpacks/shared/EXPERIMENT_REGISTRY.md`
- Artifacts：`agent_workpacks/shared/ARTIFACTS.md`

执行方式：轻量只读 artifact QA。未启动 solver benchmark、verifier replay 或其他长任务；未生成或保留临时文件；未修改 E4 manifest、summary、metrics 或共享登记。

JSON / artifact path：

- manifest、summary、metrics 均可解析。
- metrics run key 为 `e4_cpsat_stratified50_tl120`。
- metrics `split_manifest` 指向 `experiments/aaai2026/e4_cpsat_stratified50_manifest.json`。
- metrics `summary_path` 指向 `results/raw_view/e4_cpsat_stratified50_tl120_20260709_153557/summary.json`。

Coverage / manifest：

- manifest `case_count=50`，`sample_size=50`。
- split 为 train 35 / dev 5 / test 10。
- difficulty 汇总为 easy 17 / medium 17 / hard 16。
- summary 覆盖 manifest 全部 50 个 case：missing 0、extra 0、duplicate 0。
- summary case `input_path` 与 manifest `order_path` 无 mismatch。

数字核对：

| Field | Value |
|---|---|
| case_count | 50 |
| expected_case_count | 50 |
| coverage_rate | 1.0 |
| status_counts | `{'feasible': 42, 'infeasible_proven': 6, 'optimal': 2}` |
| verify_counts | `{'ok': 44, 'not_applicable': 6}` |
| method_counts | `{'timed_cpsat': 39, 'timed_cpsat_batched': 11}` |
| verified_ok_count | 44 |
| infeasible_proven_count | 6 |
| not_solved_count | 0 |
| verify_invalid_count | 0 |
| elapsed_seconds | 265.9068440308329 |
| time_limit_seconds | 120.0 |

Consistency：

- summary 逐 case 复算与 summary top-level counts 一致。
- metrics `overall` 与 summary counts 一致。
- registry E4 行与 summary/metrics 数字一致。
- artifacts E4 summary / metrics 行与 summary/metrics 数字一致。

Method / verifier rules：

- `method_counts` 不含 `timed_greedy`。
- 允许方法仅为 `timed_cpsat` 和 `timed_cpsat_batched`。
- 非可验证状态均为 `infeasible_proven` + `not_applicable`，数量 6。
- 可验证状态均为 `ok`，数量 44。

Claim boundary：

- PASS：E4 只能写为 `CP-SAT stratified-50 baseline, 120s/case`。
- PASS：登记文本没有把 E4 写成 full-670、LLM 结果、新算法主贡献、全局最优或完备现实不可行证明。
- `optimal` 只能作为 CP-SAT / 当前模型输出状态引用，不能扩写为现实工厂全局最优。
- `infeasible_proven` 只按当前模型/verifier 口径使用，不能写成现实绝对不可行。

已报告给：

- `agent_workpacks/project_manager_agent/HANDOFF.md`
- `agent_workpacks/experiment_manager_agent/HANDOFF.md`
