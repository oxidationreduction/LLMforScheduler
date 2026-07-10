# project_manager_agent Handoff

## 当前状态

工作包已初始化。尚未启动任何实验。

## 下一步

1. 让 `experiment_manager_agent` 先冻结 split、metrics 和实验登记细节。
2. 让 `dev_framework_agent` 在 `experiments/aaai2026/` 下规划新增代码。
3. 让 `dev_runner_agent` 在任何长任务前先确定 tmux 安全运行约定。
4. 让 `paper_writer_agent` 在实验管理 agent 提供表格框架后再写结果段落。
5. 让 `qa_repro_agent` 在每批结果和每版论文 claim 进入正文前审计。

## 未决问题

- 本地 LLM 推理/SFT 具体使用哪个模型族。
- 14 天内 baseline 是跑 full 670 还是优先 test-only。

## E2/E3 结果报告与产物移交

更新时间：2026-07-09T14:34:14+08:00

E2/E3 已由 `dev_runner_agent` 完成并移交，scope 均为 full 670，未触发 test 133 降级。所有正式 run 均为 CPU-only，使用任务专属 tmux session 托管；smoke 临时目录已清理。共享登记已更新：

- `agent_workpacks/shared/EXPERIMENT_REGISTRY.md`
- `agent_workpacks/shared/ARTIFACTS.md`
- `agent_workpacks/dev_runner_agent/HANDOFF.md`
- `agent_workpacks/experiment_manager_agent/HANDOFF.md`

核心 metrics 产物：

- E2 dispatching-rule baselines：`experiments/aaai2026/metrics_e2_dispatch_baselines_20260707_153730.json`
- E3 chunked wavefront 消融：`experiments/aaai2026/metrics_e3_wavefront_ablation_20260707_153731.json`

E2 固定 dispatching-rule baselines：

| strategy | summary | verify ok | infeasible_proven | unsolved | verify invalid | runtime mean / p95 / max |
|---|---|---:|---:|---:|---:|---|
| earliest_due | `results/raw_view/e2_dispatch_earliest_due_20260707_153730/summary.json` | 546 | 94 | 30 | 0 | 0.208 / 0.672 / 7.709 |
| round_robin_product | `results/raw_view/e2_dispatch_round_robin_product_20260707_153730/summary.json` | 548 | 94 | 28 | 0 | 0.194 / 0.621 / 6.508 |
| largest_route_work | `results/raw_view/e2_dispatch_largest_route_work_20260707_153730/summary.json` | 548 | 94 | 28 | 0 | 0.195 / 0.613 / 6.752 |
| smallest_route_work | `results/raw_view/e2_dispatch_smallest_route_work_20260707_153730/summary.json` | 542 | 94 | 34 | 0 | 0.205 / 0.652 / 7.720 |

E3 chunked wavefront 消融：

| strategy | summary | verify ok | infeasible_proven | unsolved | verify invalid | runtime mean / p95 / max |
|---|---|---:|---:|---:|---:|---|
| chunked_wavefront_5 | `results/raw_view/e3_wavefront_chunk5_20260707_153731/summary.json` | 572 | 94 | 4 | 0 | 0.220 / 0.746 / 7.981 |
| chunked_wavefront_10 | `results/raw_view/e3_wavefront_chunk10_20260707_153731/summary.json` | 574 | 94 | 2 | 0 | 0.221 / 0.735 / 7.254 |
| chunked_wavefront_25 | `results/raw_view/e3_wavefront_chunk25_20260707_153731/summary.json` | 576 | 94 | 0 | 0 | 0.239 / 0.861 / 7.446 |

项目主管结论：

- E2 证明单一 dispatching rule 不足以覆盖 full 670：固定规则均有 28-34 个 unsolved，不能作为主方法。
- E3 支持当前 chunked wavefront 选择：`chunked_wavefront_25` 达到 576 verify ok / 94 infeasible_proven / 0 unsolved / 0 verify invalid，与 E1/existing baseline 的计数持平。
- E2/E3 是 deterministic solver strategy ablations，不应写成 LLM 结果、CP-SAT 结果或新算法主贡献。
- 后续 E8 表格只应从已登记 metrics/summary 取数；任何正文 claim 进入论文前交给 `qa_repro_agent` 审计。

建议下一步调度：

1. `experiment_manager_agent` 基于 E0-E3 生成论文主表草稿和消融表格。
2. `dev_runner_agent` 可继续 E4 CP-SAT 子集 baseline，按既定范围分层 50 单，120s/case 主表。
3. `dev_framework_agent` 在不改 verifier 的前提下推进 E5/E6 LLM tool-agent/SFT 相关 harness。
4. `qa_repro_agent` 对 E1-E3 的 artifact 路径、计数和 claim 边界做一次 gate。

## E4/E5 最小接口实现报告

更新时间：2026-07-09T15:21:06+08:00

`dev_framework_agent` 已完成 E4 CP-SAT stratified-50 baseline 的最小实验接口，以及 E5 LLM tool-agent JSONL runner 设计实现。未启动 E4 正式长任务；只做了短 smoke 和 CLI 验证，所有临时目录与 pytest cache 已清理。

本次新增/修改的核心代码：

- E4 分层清单生成器：`experiments/aaai2026/build_stratified_manifest.py`
- E4 固定 50 单 manifest：`experiments/aaai2026/e4_cpsat_stratified50_manifest.json`
- E5 tool-agent harness：`experiments/aaai2026/run_llm_tool_agent.py`
- CP-SAT-only 公共入口：`solver/schedule_solver.py` 支持 `method="cpsat"`
- 批量 runner：`solver/run_full_benchmark.py` 支持 `--method cpsat`，并拒绝 CP-SAT 下传入 greedy strategy override
- 测试：`tests/test_aaai2026_experiments.py`、`tests/test_solver_and_checker_gate.py`

E4 manifest 状态：

- `case_count=50`
- split 分布：train 35 / dev 5 / test 10
- 分层配额：train/easy 12, train/medium 11, train/hard 12, dev/easy 2, dev/medium 2, dev/hard 1, test/easy 3, test/medium 4, test/hard 3
- case list 已核对，和项目计划中列出的 50 个 case ID 完全一致

验证结果：

- `pytest -q`：24 passed
- E4 smoke：`--method cpsat --time-limit 5 --limit 2`，2/2 verifier `ok`，`method_counts={'timed_cpsat': 2}`，无 `timed_greedy`
- E5 CLI smoke：`prepare` + `execute` 在 1 个真实 test case 上通过，verifier `ok`，`tool_call_ok_count=1`

给项目主管的建议：

1. 下一步优先把 E4 正式 120s/case 交给 `dev_runner_agent` 跑，tmux session 建议 `llm_sched_e4_cpsat_strat50`，CPU-only，禁止启动 600s 附录版。
2. E4 完成后必须通过 QA gate：`coverage_rate=1.0`、无 `timed_greedy`、`verify_invalid_count=0`、非可验证状态均为 `not_applicable`、结果目录未覆盖旧产物。
3. E5 当前只应先生成 test-133 prompts 或交给模型推理 agent 产出 `responses.jsonl`；runner 已保证 LLM 直排 `plan` 不会被采纳为最终结果。
4. E4 正式结果产出后，再更新 `shared/EXPERIMENT_REGISTRY.md` 和 `shared/ARTIFACTS.md`；当前接口实现本身可登记为 framework readiness，但不要写成 E4 实验完成。

可直接转交 `dev_runner_agent` 的 E4 正式命令：

```bash
tmux new-session -d -s llm_sched_e4_cpsat_strat50 'cd /wenyu/media-wenyu-data/LLMforScheduler && set -euo pipefail && export CUDA_VISIBLE_DEVICES="" && ts=$(date +%Y%m%d_%H%M%S) && out=results/raw_view/e4_cpsat_stratified50_tl120_${ts} && python3 solver/run_full_benchmark.py --manifest experiments/aaai2026/e4_cpsat_stratified50_manifest.json --output-dir "$out" --time-limit 120 --method cpsat && python3 experiments/aaai2026/aggregate_metrics.py --split-manifest experiments/aaai2026/e4_cpsat_stratified50_manifest.json --run e4_cpsat_stratified50_tl120="$out" --out "$out/metrics.json"'
```

可直接准备 E5 prompts 的命令：

```bash
ts=$(date +%Y%m%d_%H%M%S)
out=results/raw_view/e5_llm_tool_agent_test133_${ts}
mkdir -p "$out"
CUDA_VISIBLE_DEVICES="" python3 experiments/aaai2026/run_llm_tool_agent.py prepare \
  --split-manifest experiments/aaai2026/split_manifest.json \
  --split test \
  --out "$out/prompts.jsonl"
```

## E4 正式运行完成报告

更新时间：2026-07-09T15:43:00+08:00

`dev_runner_agent` 已完成 E4 CP-SAT stratified-50 baseline 的 120s/case 主表版本。未启动 600s/case 附录版。

产物：

- summary：`results/raw_view/e4_cpsat_stratified50_tl120_20260709_153557/summary.json`
- metrics：`results/raw_view/e4_cpsat_stratified50_tl120_20260709_153557/metrics.json`
- status：`results/raw_view/e4_cpsat_stratified50_tl120_20260709_153557/status.json`
- run log：`results/raw_view/e4_cpsat_stratified50_tl120_20260709_153557/run.log`

关键数字：

- scope：stratified 50，120s/case。
- status_counts：`{'feasible': 42, 'infeasible_proven': 6, 'optimal': 2}`。
- verify_counts：`{'ok': 44, 'not_applicable': 6}`。
- method_counts：`{'timed_cpsat': 39, 'timed_cpsat_batched': 11}`；无 `timed_greedy`。
- not_solved_count：0。
- verify_invalid_count：0。
- elapsed_seconds：265.9068440308329。
- solve_seconds：mean 5.305，median 2.395，p90 13.952，p95 19.366，max 38.795。

登记与交接：

- `shared/EXPERIMENT_REGISTRY.md` 已将 E4 更新为 complete。
- `shared/ARTIFACTS.md` 已登记 E4 summary 和 metrics。
- `experiment_manager_agent` 已接收 E4 结果。
- `qa_repro_agent` 已收到 E4 artifact QA gate 请求。

项目主管注意：

- E4 只能作为 `CP-SAT stratified-50 baseline, 120s/case` 使用。
- E4 不是 full-670 结果，不能与 E0-E3 full-670 结果按 case_count 等价比较。
- 不得把 E4 写成 LLM 结果、新算法主贡献、全局最优或完备现实不可行证明。

## E4 artifact QA gate 通过

更新时间：2026-07-09T16:22:27+08:00

`qa_repro_agent` 已完成 E4 CP-SAT stratified-50 baseline 的 artifact QA gate，结论：PASS。该 gate 为轻量只读 QA，未启动长任务，未生成或保留临时文件，未修改 manifest、summary、metrics 或共享登记。

检查对象：

- `experiments/aaai2026/e4_cpsat_stratified50_manifest.json`
- `results/raw_view/e4_cpsat_stratified50_tl120_20260709_153557/summary.json`
- `results/raw_view/e4_cpsat_stratified50_tl120_20260709_153557/metrics.json`
- `agent_workpacks/shared/EXPERIMENT_REGISTRY.md`
- `agent_workpacks/shared/ARTIFACTS.md`

QA 结论：

- JSON 均可解析。
- summary / metrics / registry / artifacts 数字一致。
- case id 与 E4 manifest 完全一致：missing 0、extra 0、duplicate 0。
- `method_counts={'timed_cpsat': 39, 'timed_cpsat_batched': 11}`，不含 `timed_greedy`。
- 非可验证状态均为 `infeasible_proven` + `not_applicable`。
- E4 只能写为 `CP-SAT stratified-50 baseline, 120s/case`；不得写成 full-670、LLM 结果、新算法主贡献、全局最优或完备现实不可行证明。

## E0-E3 表格底稿 QA gate 通过

更新时间：2026-07-09T15:36:44+08:00

`qa_repro_agent` 已完成 `experiments/aaai2026/e0_e3_paper_table_draft.md` 的 table-specific QA gate，结论：PASS。该 gate 为轻量只读 QA，未启动长任务，未生成或保留临时文件，未修改 metrics、summary 或表格底稿。

检查对象：

- E0：`experiments/aaai2026/metrics_timed_greedy_existing.json`
- E1：`experiments/aaai2026/metrics_e1_full670_repro.json`
- E2：`experiments/aaai2026/metrics_e2_dispatch_baselines_20260707_153730.json`
- E3：`experiments/aaai2026/metrics_e3_wavefront_ablation_20260707_153731.json`

QA 结论：

- 底稿 12 个表格数据行全部可追溯到指定 metrics / summary。
- `case_count`、`coverage`、`verified ok`、`infeasible_proven`、`unsolved`、`verify invalid`、`elapsed`、`solve seconds p50/p90/p95/max` 全部通过核对。
- E2/E3 在底稿中只写成 full-670 deterministic solver strategy ablations。
- forbidden claims 只出现在禁止清单中，没有出现在正向结论中。

后续可将该底稿交给 `paper_writer_agent` 使用，但正文只能引用已登记 metrics/summary。不得扩写成 LLM 结果、CP-SAT 结果、新算法优越、全局最优、工业 KPI 提升或现实完备不可行 claim。
