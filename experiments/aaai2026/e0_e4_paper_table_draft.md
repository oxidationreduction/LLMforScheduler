# E0-E4 Paper Table Draft

This draft combines the QA-passed E0-E3 full-670 table material with the
QA-passed E4 CP-SAT stratified-50 baseline. E4 is separated from E0-E3 because
it uses a 50-case stratified subset rather than the full 670-case set.

## QA Status

| Scope | QA record | Status |
|---|---|---|
| E0-E3 full-670 tables | `agent_workpacks/qa_repro_agent/HANDOFF.md` section `2026-07-09 E0-E3 table-specific QA gate` | PASS |
| E4 CP-SAT artifact | `agent_workpacks/qa_repro_agent/HANDOFF.md` section `2026-07-09 E4 artifact QA gate` | PASS |

## Source Artifacts

| Experiment | Metrics | Summary or manifest |
|---|---|---|
| E0 existing timed_greedy | `experiments/aaai2026/metrics_timed_greedy_existing.json` | `results/raw_view/all_machine_capacity_dynamic_chunk25_20260626_tl120/summary.json` |
| E1 reproduced timed_greedy | `experiments/aaai2026/metrics_e1_full670_repro.json` | `results/raw_view/e1_full670_repro_20260703_232018/summary.json` |
| E2 fixed dispatching rules | `experiments/aaai2026/metrics_e2_dispatch_baselines_20260707_153730.json` | summaries under `results/raw_view/e2_dispatch_*_20260707_153730/` |
| E3 chunked wavefront ablation | `experiments/aaai2026/metrics_e3_wavefront_ablation_20260707_153731.json` | summaries under `results/raw_view/e3_wavefront_chunk*_20260707_153731/` |
| E4 CP-SAT stratified-50 | `results/raw_view/e4_cpsat_stratified50_tl120_20260709_153557/metrics.json` | `results/raw_view/e4_cpsat_stratified50_tl120_20260709_153557/summary.json`; `experiments/aaai2026/e4_cpsat_stratified50_manifest.json` |

## Main Full-670 Table Draft

| Row | Metrics | Summary | Cases | Coverage | Status counts | Verify counts | OK | Infeasible | Unsolved | Invalid | Elapsed | Solve seconds p50/p90/p95/max |
|---|---|---|---:|---:|---|---|---:|---:|---:|---:|---:|---|
| E0 existing timed_greedy | `experiments/aaai2026/metrics_timed_greedy_existing.json` | `results/raw_view/all_machine_capacity_dynamic_chunk25_20260626_tl120/summary.json` | 670 | 1.0 | feasible 560, optimal 16, infeasible_proven 94 | ok 576, not_applicable 94 | 576 | 94 | 0 | 0 | 195.741s | 0.079 / 0.582 / 0.918 / 18.354 |
| E1 reproduced timed_greedy | `experiments/aaai2026/metrics_e1_full670_repro.json` | `results/raw_view/e1_full670_repro_20260703_232018/summary.json` | 670 | 1.0 | feasible 560, optimal 16, infeasible_proven 94 | ok 576, not_applicable 94 | 576 | 94 | 0 | 0 | 167.628s | 0.078 / 0.492 / 0.760 / 15.011 |
| E2 fixed dispatching: round_robin_product | `experiments/aaai2026/metrics_e2_dispatch_baselines_20260707_153730.json` | `results/raw_view/e2_dispatch_round_robin_product_20260707_153730/summary.json` | 670 | 1.0 | feasible 532, optimal 16, infeasible_proven 94, no_solution_found 28 | ok 548, not_applicable 122 | 548 | 94 | 28 | 0 | 139.882s | 0.079 / 0.387 / 0.621 / 6.508 |
| E2 fixed dispatching: largest_route_work | `experiments/aaai2026/metrics_e2_dispatch_baselines_20260707_153730.json` | `results/raw_view/e2_dispatch_largest_route_work_20260707_153730/summary.json` | 670 | 1.0 | feasible 532, optimal 16, infeasible_proven 94, no_solution_found 28 | ok 548, not_applicable 122 | 548 | 94 | 28 | 0 | 140.998s | 0.078 / 0.375 / 0.613 / 6.752 |
| E3 chunked_wavefront_25 | `experiments/aaai2026/metrics_e3_wavefront_ablation_20260707_153731.json` | `results/raw_view/e3_wavefront_chunk25_20260707_153731/summary.json` | 670 | 1.0 | feasible 560, optimal 16, infeasible_proven 94 | ok 576, not_applicable 94 | 576 | 94 | 0 | 0 | 172.358s | 0.085 / 0.502 / 0.861 / 7.446 |

## CP-SAT Stratified-50 Baseline

Do not compare this section to the full-670 rows by equal case count. E4 uses a
stratified 50-case subset sampled from the same 670-case parent manifest.

| Row | Metrics | Summary | Manifest | Scope | Time limit | Cases | Coverage | Status counts | Verify counts | OK | Infeasible | Unsolved | Invalid | Method counts | Elapsed | Solve seconds mean/p50/p90/p95/max |
|---|---|---|---|---|---:|---:|---:|---|---|---:|---:|---:|---:|---|---:|---|
| E4 CP-SAT stratified-50 baseline | `results/raw_view/e4_cpsat_stratified50_tl120_20260709_153557/metrics.json` | `results/raw_view/e4_cpsat_stratified50_tl120_20260709_153557/summary.json` | `experiments/aaai2026/e4_cpsat_stratified50_manifest.json` | stratified 50 subset | 120s/case | 50 | 1.0 | feasible 42, optimal 2, infeasible_proven 6 | ok 44, not_applicable 6 | 44 | 6 | 0 | 0 | timed_cpsat 39, timed_cpsat_batched 11 | 265.907s | 5.305 / 2.395 / 13.952 / 19.366 / 38.795 |

E4 manifest scope:

- Parent manifest: `experiments/aaai2026/split_manifest.json`.
- Source case count: 670.
- Split counts: train 35, dev 5, test 10.
- Difficulty counts: easy 17, medium 17, hard 16.
- OOD/recent count: 4.
- No 600s appendix run is included.

## Claim Boundaries

Allowed claims:

- E0-E3 full-670 rows use the registered 670-case split and verifier-backed metrics.
- E2 fixed single dispatching rules leave 28-34 unsolved cases on the full 670-case set.
- E3 `chunked_wavefront_25` matches E0/E1 aggregate counts: 576 verifier-ok schedules, 94 infeasible_proven cases, 0 unsolved cases, and 0 verify-invalid cases.
- E4 is a `CP-SAT stratified-50 baseline, 120s/case`.
- E4 achieved 44 verifier-ok schedules and 6 infeasible_proven cases on the stratified-50 subset.

Forbidden claims:

- Do not present E2/E3/E4 as LLM tool-agent results.
- Do not present E4 as a full-670 result or main method result.
- Do not make case-count-equivalent comparisons between E4 and E0-E3.
- Do not claim global optimality for feasible schedules.
- Do not claim complete real-world infeasibility beyond the current scheduling model, constraints, and verifier assumptions.
- Do not claim industrial KPI evidence or runtime speedup beyond observed run records.
