# dev_runner_agent Handoff

## 当前状态

E1 full 670 solver 复现实验已完成并验收通过。当前没有本任务遗留 tmux session 或运行中进程。

## 运行规则

- 所有长任务都用 tmux。
- 使用唯一 session 名，例如 `llm_sched_e1_full670`。
- 日志和 summary 写入新结果目录。
- 长任务需要提供 watcher/status 文件。
- smoke 测试后删除临时文件，除非它们是必要 artifact。

## E1 任务单：复现 full 670 solver

### 目标

复现当前 full 670 timed_greedy solver 结果，验证主线 solver/verifier 在当前仓库路径下仍能得到同量级证据。

验收目标：

- case_count：670。
- verify ok：目标 576。
- infeasible_proven：目标 94。
- unsolved：目标 0。
- verify invalid：目标 0。

参考基线：

- split manifest：`experiments/aaai2026/split_manifest.json`
- existing metrics：`experiments/aaai2026/metrics_timed_greedy_existing.json`
- existing summary：`results/raw_view/all_machine_capacity_dynamic_chunk25_20260626_tl120/summary.json`

### 输出要求

- 新结果目录必须写入 `results/raw_view/e1_full670_repro_<YYYYMMDD_HHMMSS>/`。
- 不得覆盖 `results/raw_view/all_machine_capacity_dynamic_chunk25_20260626_tl120/` 或其它既有结果目录。
- 结果目录至少包含：
  - `summary.json`
  - `solutions/*.solution.json`
  - `solutions/*.verify.json`
  - `run.log` 或等价日志
  - `status.json` 或等价 watcher/status 文件
- 完成后用 `experiments/aaai2026/aggregate_metrics.py` 生成对应 metrics，例如：

```bash
python3 experiments/aaai2026/aggregate_metrics.py \
  --split-manifest experiments/aaai2026/split_manifest.json \
  --run e1_full670_repro=<E1_RESULT_DIR> \
  --out experiments/aaai2026/metrics_e1_full670_repro.json
```

### 启动规则

- tmux session 名称：`llm_sched_e1_full670`。
- 仅使用 CPU；不要占用 GPU。
- 启动前检查是否已有同名 tmux session；如存在，先确认它是否属于本任务，严禁误杀其它 session。
- 先做短 smoke：任选 1-3 个 `raw_orders/*.json`，确认 solver 和 verifier 能写入临时目录；smoke 临时目录完成后删除。
- smoke 通过后再启动 full 670 长任务。

### 执行注意

- 仓库没有专门的 full-670 runner 时，优先复用现有 `solver/schedule_solver.py`、`solver/verify_schedule.py`、`checker/check_schedule.py` 的 import/API 组合；如需新增 runner，先把最小脚本交给 `dev_framework_agent` 或项目主管确认。
- summary 字段需要兼容 `experiments/aaai2026/aggregate_metrics.py`，至少包含 `case_count`、`cases`，每个 case 包含 `case_id`、`status`/`solve_status`、`verify_status`、`solve_seconds`、`task_count`。
- `infeasible_proven`、`time_limit`、`no_solution_found` 等非可验证状态应写入 solution 和 summary；不可强行调用 verifier 当成 ok。
- 若结果偏离基线，先保留完整 artifact，并在 handoff 中报告偏离 case 列表和可能原因，不要覆盖重跑。

### 完成后交付

- tmux session 名称和最终状态。
- E1 结果目录路径。
- E1 metrics 路径。
- 与 existing baseline 的关键差异：
  - verify ok
  - infeasible_proven
  - unsolved
  - verify invalid
  - total elapsed/runtime 分位
- 更新 `shared/ARTIFACTS.md` 和 `shared/EXPERIMENT_REGISTRY.md`，或把精确路径交给 `experiment_manager_agent` 登记。

## 等待事项

- E1 已完成；等待后续 E2/E3/E4 等实验指挥。
- E0/E1 论文表格底稿已保存：`experiments/aaai2026/e0_e1_paper_table_draft.md`。后续 dev-agent 使用该底稿时，不要混入未登记旧目录；E1 只能作为 `Timed greedy solver (E1 reproduction)` 主表行，不能写成 LLM/CP-SAT/新算法结果。

## E1 完成记录：full 670 solver reproduction

- tmux session：`llm_sched_e1_full670`，full run 完成后自然退出。
- runner：新增 `solver/run_full_benchmark.py`，复用现有 `schedule_solver`/`verify_schedule` API；未修改 solver/verifier 核心逻辑。
- CPU-only：full run 使用 `CUDA_VISIBLE_DEVICES=""`，未占用 GPU。
- smoke：`SO-2020-10-0002-2` + `SO-2020-11-0001-2` 通过，临时目录已删除。
- 结果目录：`results/raw_view/e1_full670_repro_20260703_232018/`
- summary：`results/raw_view/e1_full670_repro_20260703_232018/summary.json`
- status/watcher：`results/raw_view/e1_full670_repro_20260703_232018/status.json`
- 日志：`results/raw_view/e1_full670_repro_20260703_232018/run.log`
- metrics：`experiments/aaai2026/metrics_e1_full670_repro.json`

关键数字：

- case_count：670。
- verify ok：576。
- infeasible_proven：94。
- unsolved：0。
- verify invalid：0。
- coverage_rate：1.0。
- elapsed_seconds：167.6277772031026。
- solve_seconds：mean 0.2331358470，median 0.0775131771，p90 0.4924942168，p95 0.7600731058，max 15.0109289760。

与 existing baseline 的差异：

- baseline ok 但 E1 非 ok：0。
- baseline infeasible 但 E1 非 infeasible：0。
- E1 新增 infeasible：0。
- E1 新增 ok：0。
- manifest missing cases：0。
- manifest extra cases：0。

## E2/E3 完成记录：dispatching-rule baselines 与 chunked wavefront 消融

- CPU-only：所有正式 run 使用 `CUDA_VISIBLE_DEVICES=""`，未占用 GPU。
- smoke：`earliest_due` 与 `chunked_wavefront_5` 各跑 manifest 前 2 单，确认策略字段可区分、summary/solution/verify 正常；临时目录已删除。
- tmux session：
  - `llm_sched_e2_dispatch_baseline`：完成后停在 shell prompt，已确认 `E2_DONE 2026-07-07T15:47:12+08:00`，随后关闭该本任务空 session。
  - `llm_sched_e3_wavefront_ablation`：完成后停在 shell prompt，已确认 `E3_DONE 2026-07-07T15:45:44+08:00`，随后关闭该本任务空 session。
- scope：均为 full 670；未降级 test 133。
- runner：`solver/run_full_benchmark.py` 新增 `--unit-strategy`、`--worker-strategy`、`--day-strategy` 和 `--split`；不传策略时保留 E1 多策略 timed 行为。
- metrics：
  - E2：`experiments/aaai2026/metrics_e2_dispatch_baselines_20260707_153730.json`
  - E3：`experiments/aaai2026/metrics_e3_wavefront_ablation_20260707_153731.json`

E2 fixed dispatching-rule summaries：

| strategy | summary | status_counts | verify_counts | unsolved | verify invalid | elapsed / solve_seconds mean, median, p90, p95, max |
|---|---|---|---|---:|---:|---|
| earliest_due | `results/raw_view/e2_dispatch_earliest_due_20260707_153730/summary.json` | `{'infeasible_proven': 94, 'feasible': 530, 'no_solution_found': 30, 'optimal': 16}` | `{'not_applicable': 124, 'ok': 546}` | 30 | 0 | 149.063s / 0.208, 0.078, 0.421, 0.672, 7.709 |
| round_robin_product | `results/raw_view/e2_dispatch_round_robin_product_20260707_153730/summary.json` | `{'infeasible_proven': 94, 'feasible': 532, 'no_solution_found': 28, 'optimal': 16}` | `{'not_applicable': 122, 'ok': 548}` | 28 | 0 | 139.882s / 0.194, 0.079, 0.387, 0.621, 6.508 |
| largest_route_work | `results/raw_view/e2_dispatch_largest_route_work_20260707_153730/summary.json` | `{'infeasible_proven': 94, 'feasible': 532, 'no_solution_found': 28, 'optimal': 16}` | `{'not_applicable': 122, 'ok': 548}` | 28 | 0 | 140.998s / 0.195, 0.078, 0.375, 0.613, 6.752 |
| smallest_route_work | `results/raw_view/e2_dispatch_smallest_route_work_20260707_153730/summary.json` | `{'infeasible_proven': 94, 'feasible': 526, 'no_solution_found': 34, 'optimal': 16}` | `{'not_applicable': 128, 'ok': 542}` | 34 | 0 | 147.854s / 0.205, 0.079, 0.396, 0.652, 7.720 |

E3 chunked wavefront summaries：

| strategy | summary | status_counts | verify_counts | unsolved | verify invalid | elapsed / solve_seconds mean, median, p90, p95, max |
|---|---|---|---|---:|---:|---|
| chunked_wavefront_5 | `results/raw_view/e3_wavefront_chunk5_20260707_153731/summary.json` | `{'infeasible_proven': 94, 'feasible': 556, 'optimal': 16, 'no_solution_found': 4}` | `{'not_applicable': 98, 'ok': 572}` | 4 | 0 | 157.910s / 0.220, 0.079, 0.447, 0.746, 7.981 |
| chunked_wavefront_10 | `results/raw_view/e3_wavefront_chunk10_20260707_153731/summary.json` | `{'infeasible_proven': 94, 'feasible': 558, 'optimal': 16, 'no_solution_found': 2}` | `{'not_applicable': 96, 'ok': 574}` | 2 | 0 | 160.155s / 0.221, 0.081, 0.453, 0.735, 7.254 |
| chunked_wavefront_25 | `results/raw_view/e3_wavefront_chunk25_20260707_153731/summary.json` | `{'infeasible_proven': 94, 'feasible': 560, 'optimal': 16}` | `{'not_applicable': 94, 'ok': 576}` | 0 | 0 | 172.358s / 0.239, 0.085, 0.502, 0.861, 7.446 |

异常说明：

- E2 固定 dispatching-rule baselines 均低于 E1/chunk25 的 576 verify ok，出现 28-34 个 `no_solution_found`；这是单策略消融结果，artifact 已保留，未覆盖重跑。
- E3 `chunked_wavefront_25` 与 E1/full existing baseline 的 status/verify counts 持平；`chunked_wavefront_5/10` 分别有 4/2 个 `no_solution_found`。

## E4 完成记录：CP-SAT stratified-50 baseline

更新时间：2026-07-09T15:43:00+08:00

- tmux session：`llm_sched_e4_cpsat_strat50`，正式 run 完成后自然退出，当前无残留 tmux session。
- 启动命令：使用项目主管转交的 120s/case 主表命令，`CUDA_VISIBLE_DEVICES=""`，未启动 600s/case 附录版。
- scope：`experiments/aaai2026/e4_cpsat_stratified50_manifest.json`，分层 50 单。
- 结果目录：`results/raw_view/e4_cpsat_stratified50_tl120_20260709_153557/`
- summary：`results/raw_view/e4_cpsat_stratified50_tl120_20260709_153557/summary.json`
- metrics：`results/raw_view/e4_cpsat_stratified50_tl120_20260709_153557/metrics.json`
- status/watcher：`results/raw_view/e4_cpsat_stratified50_tl120_20260709_153557/status.json`
- 日志：`results/raw_view/e4_cpsat_stratified50_tl120_20260709_153557/run.log`

关键数字：

- case_count：50。
- expected_case_count：50。
- coverage_rate：1.0。
- status_counts：`{'feasible': 42, 'infeasible_proven': 6, 'optimal': 2}`。
- verify_counts：`{'ok': 44, 'not_applicable': 6}`。
- method_counts：`{'timed_cpsat': 39, 'timed_cpsat_batched': 11}`；无 `timed_greedy`。
- not_solved_count：0。
- verify_invalid_count：0。
- elapsed_seconds：265.9068440308329。
- solve_seconds：mean 5.3049399915，median 2.3945699481，p90 13.9520238571，p95 19.3658396501，max 38.7951691588。

验收记录：

- `summary.json`、`status.json`、`run.log`、`manifest.json`、`metrics.json` 均存在。
- `solutions/*.solution.json` 50 个，`solutions/*.verify.json` 50 个。
- 非可验证状态均为 `verify_status=not_applicable`。
- `metrics.json` 中 run 名为 `e4_cpsat_stratified50_tl120`，overall coverage 1.0。
- 结果目录为新目录，未覆盖 E0-E3 或 smoke 产物。

## E5 第一阶段记录：LLM tool-agent test-133 prompts

更新时间：2026-07-10T23:25:23+08:00

- 执行身份：dev_runner_agent。
- 命令：`CUDA_VISIBLE_DEVICES="" python3 experiments/aaai2026/run_llm_tool_agent.py prepare --split-manifest experiments/aaai2026/split_manifest.json --split test --out results/raw_view/e5_llm_tool_agent_test133_20260710_232523/prompts.jsonl`
- 输出：`results/raw_view/e5_llm_tool_agent_test133_20260710_232523/prompts.jsonl`
- scope：test split，133 条 prompts。
- 校验：JSONL 133 行；所有行 `split=test`；system prompt 与 user policy 均要求 strict JSON tool call。
- 边界：仅生成 prompts；未运行 direct LLM schedule generation；尚无 `responses.jsonl`、parsed tool calls、run summary 或 verifier metrics。
- 2026-07-11 更新：E5/E6/E7 已暂停主线。不要把 E5 继续交给模型推理 agent，除非项目主管明确恢复 H8 LLM appendix/motivation。
- 登记：已更新 `agent_workpacks/shared/ARTIFACTS.md` 与 `agent_workpacks/shared/EXPERIMENT_REGISTRY.md`。
- 旧模型推理指令已因 2026-07-11 纯启发式重规划失效；不要从历史对话或旧 handoff 中恢复执行。

## 2026-07-11 H-series runner 规则

- 不启动 E5 模型推理、E6 SFT/LoRA 或 E7 direct generation。
- 若收到 H5/H6 相关任务，优先使用轻量 CPU-only 分析；长任务仍必须用 tmux。
- 若项目主管明确启动 H7，使用新结果目录运行 CP-SAT stratified-50 600s/case appendix，不覆盖 E4 120s/case 目录。
- 所有新产物必须输出 `summary.json` 或 `metrics.json` 并登记到 `shared/ARTIFACTS.md`。
