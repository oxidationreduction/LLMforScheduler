# H5/H6 Next Phase Task Brief

Status: assigned after H-series table QA PASS on 2026-07-11.

## Context

`qa_repro_agent` has passed the H-series heuristic-first table QA gate for:

- `experiments/aaai2026/h_series_heuristic_table_draft.md`

The paper can now use H1-H4 under the QA boundaries. The next experimental
evidence needed for the heuristic-first paper is:

- H5: complexity/difficulty bucket analysis.
- H6: verifier-backed case study.

Do not restart E5/E6/E7. LLM experiments remain paused and appendix-only unless
the project manager explicitly reopens them.

## H5 Owner And Output

Owner: `experiment_manager_agent`.

Use `dev_framework_agent` only if the existing scripts are insufficient.

Primary source artifacts:

- `experiments/aaai2026/split_manifest.json`
- `results/raw_view/e1_full670_repro_20260703_232018/summary.json`
- `experiments/aaai2026/metrics_e1_full670_repro.json`

Optional comparison sources:

- H2/E2: `experiments/aaai2026/metrics_e2_dispatch_baselines_20260707_153730.json`
- H3/E3: `experiments/aaai2026/metrics_e3_wavefront_ablation_20260707_153731.json`

Required outputs:

- `experiments/aaai2026/h5_complexity_difficulty_metrics.json`
- `experiments/aaai2026/h5_complexity_difficulty_table_draft.md`

Required bucket features:

- `operation_count`
- `total_work_minutes`
- `machine_load_ratio`
- `worker_day_count`

Feature handling rule:

- First produce a feature availability report.
- If a required feature is unavailable, mark it explicitly as `unavailable`.
- Do not silently substitute `load_ratio` for `machine_load_ratio`.
- If reporting the existing `load_ratio`, label it by its real source/meaning,
  not as machine load.

Each bucket must report:

- `case_count`
- `status_counts`
- `verify_counts`
- `verified_ok_count`
- `infeasible_proven_count`
- `unsolved_count`
- `verify_invalid_count`
- `solve_seconds` p50/p90/p95/max
- source artifact paths

Acceptance conditions:

- JSON is parseable.
- Case ids join cleanly between manifest and summary.
- H5 uses the same split/verifier semantics as H1.
- No H5 number enters the paper before `qa_repro_agent` gates the output.

## H6 Owner And Output

Owner: `experiment_manager_agent`.

QA support: `qa_repro_agent`.

Primary source artifacts:

- `experiments/aaai2026/split_manifest.json`
- `results/raw_view/e1_full670_repro_20260703_232018/summary.json`
- H1/E1 solution and verify files under
  `results/raw_view/e1_full670_repro_20260703_232018/solutions/`

Required outputs:

- `experiments/aaai2026/h6_verifier_case_study_manifest.json`
- `experiments/aaai2026/h6_verifier_case_study_draft.md`

Select exactly:

- 2 complex feasible cases with verifier `ok`.
- 1 inventory-deduction or zero-task/optimal case.
- 1 capacity-lower-bound infeasible case.

Each selected case must include:

- case id
- split and difficulty bucket
- order JSON path
- solution JSON path if available
- verify JSON path if available
- summary row source
- status and verify status
- why the case was selected
- exact claim allowed by the artifact

Acceptance conditions:

- No case-study claim extrapolates to global optimality.
- Infeasible case wording stays within current model/verifier assumptions.
- Every cited path exists.
- H6 does not use E5/E6/E7 or any LLM output.

## Direct Prompt For Experiment Manager

```text
请接手 H5/H6 下一阶段。

先阅读：
- experiments/aaai2026/h5_h6_next_phase_task_brief.md
- experiments/aaai2026/h_series_heuristic_table_draft.md
- agent_workpacks/qa_repro_agent/HANDOFF.md 中 2026-07-11 H-series table QA gate
- agent_workpacks/shared/EXPERIMENT_REGISTRY.md
- agent_workpacks/shared/ARTIFACTS.md

任务：
1. 生成 H5 complexity/difficulty metrics 和 table draft。
2. 生成 H6 verifier case-study manifest 和 draft。
3. 所有新产物登记到 shared/ARTIFACTS.md，并同步 EXPERIMENT_REGISTRY.md。
4. 若需要新脚本，先给 dev_framework_agent 明确最小需求；不得改 solver/verifier 语义。
5. 完成后交给 qa_repro_agent 做 H5/H6 QA gate。

硬约束：
- 不启动 E5/E6/E7。
- 不使用 LLM 输出进入主实验。
- machine_load_ratio 若不可用，必须显式标 unavailable；不得用 load_ratio 冒充。
- H6 每个案例必须指向真实 order/solution/verify 或 infeasibility artifact。
```
