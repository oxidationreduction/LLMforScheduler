# E0-E3 Paper Table Draft

This draft supersedes `experiments/aaai2026/e0_e1_paper_table_draft.md` for
E0-E3 paper-table preparation. It uses registered artifacts only and is handed
to `qa_repro_agent` for table-specific QA gate before any `paper_writer_agent`
use.

## Source Artifacts

| Experiment | Metrics | Registered summary paths |
|---|---|---|
| E0 existing timed_greedy | `experiments/aaai2026/metrics_timed_greedy_existing.json` | `results/raw_view/all_machine_capacity_dynamic_chunk25_20260626_tl120/summary.json` |
| E1 reproduced timed_greedy | `experiments/aaai2026/metrics_e1_full670_repro.json` | `results/raw_view/e1_full670_repro_20260703_232018/summary.json` |
| E2 fixed dispatching rules | `experiments/aaai2026/metrics_e2_dispatch_baselines_20260707_153730.json` | `results/raw_view/e2_dispatch_earliest_due_20260707_153730/summary.json`; `results/raw_view/e2_dispatch_round_robin_product_20260707_153730/summary.json`; `results/raw_view/e2_dispatch_largest_route_work_20260707_153730/summary.json`; `results/raw_view/e2_dispatch_smallest_route_work_20260707_153730/summary.json` |
| E3 chunked wavefront ablation | `experiments/aaai2026/metrics_e3_wavefront_ablation_20260707_153731.json` | `results/raw_view/e3_wavefront_chunk5_20260707_153731/summary.json`; `results/raw_view/e3_wavefront_chunk10_20260707_153731/summary.json`; `results/raw_view/e3_wavefront_chunk25_20260707_153731/summary.json` |

Split source for all rows: `experiments/aaai2026/split_manifest.json`.

## Main Table Draft

| Row | Metrics | Summary | Cases | Coverage | Status counts | Verify counts | OK | Infeasible | Unsolved | Invalid | Elapsed | Solve seconds p50/p90/p95/max |
|---|---|---|---:|---:|---|---|---:|---:|---:|---:|---:|---|
| E0 existing timed_greedy | `experiments/aaai2026/metrics_timed_greedy_existing.json` | `results/raw_view/all_machine_capacity_dynamic_chunk25_20260626_tl120/summary.json` | 670 | 1.0 | feasible 560, optimal 16, infeasible_proven 94 | ok 576, not_applicable 94 | 576 | 94 | 0 | 0 | 195.741s | 0.079 / 0.582 / 0.918 / 18.354 |
| E1 reproduced timed_greedy | `experiments/aaai2026/metrics_e1_full670_repro.json` | `results/raw_view/e1_full670_repro_20260703_232018/summary.json` | 670 | 1.0 | feasible 560, optimal 16, infeasible_proven 94 | ok 576, not_applicable 94 | 576 | 94 | 0 | 0 | 167.628s | 0.078 / 0.492 / 0.760 / 15.011 |
| E2 fixed dispatching: round_robin_product | `experiments/aaai2026/metrics_e2_dispatch_baselines_20260707_153730.json` | `results/raw_view/e2_dispatch_round_robin_product_20260707_153730/summary.json` | 670 | 1.0 | feasible 532, optimal 16, infeasible_proven 94, no_solution_found 28 | ok 548, not_applicable 122 | 548 | 94 | 28 | 0 | 139.882s | 0.079 / 0.387 / 0.621 / 6.508 |
| E2 fixed dispatching: largest_route_work | `experiments/aaai2026/metrics_e2_dispatch_baselines_20260707_153730.json` | `results/raw_view/e2_dispatch_largest_route_work_20260707_153730/summary.json` | 670 | 1.0 | feasible 532, optimal 16, infeasible_proven 94, no_solution_found 28 | ok 548, not_applicable 122 | 548 | 94 | 28 | 0 | 140.998s | 0.078 / 0.375 / 0.613 / 6.752 |
| E3 chunked_wavefront_25 | `experiments/aaai2026/metrics_e3_wavefront_ablation_20260707_153731.json` | `results/raw_view/e3_wavefront_chunk25_20260707_153731/summary.json` | 670 | 1.0 | feasible 560, optimal 16, infeasible_proven 94 | ok 576, not_applicable 94 | 576 | 94 | 0 | 0 | 172.358s | 0.085 / 0.502 / 0.861 / 7.446 |

Main-table note: E2 has a tie for best fixed dispatching rule. Keep both
`round_robin_product` and `largest_route_work` unless a later paper-layout pass
chooses to compress them with an explicit tie note.

## E2 Fixed Dispatching Rule Ablation

| Strategy | Metrics | Summary | Cases | Coverage | Status counts | Verify counts | OK | Infeasible | Unsolved | Invalid | Elapsed | Solve seconds p50/p90/p95/max |
|---|---|---|---:|---:|---|---|---:|---:|---:|---:|---:|---|
| earliest_due | `experiments/aaai2026/metrics_e2_dispatch_baselines_20260707_153730.json` | `results/raw_view/e2_dispatch_earliest_due_20260707_153730/summary.json` | 670 | 1.0 | feasible 530, optimal 16, infeasible_proven 94, no_solution_found 30 | ok 546, not_applicable 124 | 546 | 94 | 30 | 0 | 149.063s | 0.078 / 0.421 / 0.672 / 7.709 |
| round_robin_product | `experiments/aaai2026/metrics_e2_dispatch_baselines_20260707_153730.json` | `results/raw_view/e2_dispatch_round_robin_product_20260707_153730/summary.json` | 670 | 1.0 | feasible 532, optimal 16, infeasible_proven 94, no_solution_found 28 | ok 548, not_applicable 122 | 548 | 94 | 28 | 0 | 139.882s | 0.079 / 0.387 / 0.621 / 6.508 |
| largest_route_work | `experiments/aaai2026/metrics_e2_dispatch_baselines_20260707_153730.json` | `results/raw_view/e2_dispatch_largest_route_work_20260707_153730/summary.json` | 670 | 1.0 | feasible 532, optimal 16, infeasible_proven 94, no_solution_found 28 | ok 548, not_applicable 122 | 548 | 94 | 28 | 0 | 140.998s | 0.078 / 0.375 / 0.613 / 6.752 |
| smallest_route_work | `experiments/aaai2026/metrics_e2_dispatch_baselines_20260707_153730.json` | `results/raw_view/e2_dispatch_smallest_route_work_20260707_153730/summary.json` | 670 | 1.0 | feasible 526, optimal 16, infeasible_proven 94, no_solution_found 34 | ok 542, not_applicable 128 | 542 | 94 | 34 | 0 | 147.854s | 0.079 / 0.396 / 0.652 / 7.720 |

## E3 Chunked Wavefront Ablation

| Strategy | Metrics | Summary | Cases | Coverage | Status counts | Verify counts | OK | Infeasible | Unsolved | Invalid | Elapsed | Solve seconds p50/p90/p95/max |
|---|---|---|---:|---:|---|---|---:|---:|---:|---:|---:|---|
| chunked_wavefront_5 | `experiments/aaai2026/metrics_e3_wavefront_ablation_20260707_153731.json` | `results/raw_view/e3_wavefront_chunk5_20260707_153731/summary.json` | 670 | 1.0 | feasible 556, optimal 16, infeasible_proven 94, no_solution_found 4 | ok 572, not_applicable 98 | 572 | 94 | 4 | 0 | 157.910s | 0.079 / 0.447 / 0.746 / 7.981 |
| chunked_wavefront_10 | `experiments/aaai2026/metrics_e3_wavefront_ablation_20260707_153731.json` | `results/raw_view/e3_wavefront_chunk10_20260707_153731/summary.json` | 670 | 1.0 | feasible 558, optimal 16, infeasible_proven 94, no_solution_found 2 | ok 574, not_applicable 96 | 574 | 94 | 2 | 0 | 160.155s | 0.081 / 0.453 / 0.735 / 7.254 |
| chunked_wavefront_25 | `experiments/aaai2026/metrics_e3_wavefront_ablation_20260707_153731.json` | `results/raw_view/e3_wavefront_chunk25_20260707_153731/summary.json` | 670 | 1.0 | feasible 560, optimal 16, infeasible_proven 94 | ok 576, not_applicable 94 | 576 | 94 | 0 | 0 | 172.358s | 0.085 / 0.502 / 0.861 / 7.446 |

## Claim Boundaries

Allowed claims:

- E2 fixed single dispatching rules leave 28-34 unsolved cases on the full 670-case set.
- E3 `chunked_wavefront_25` matches E0/E1 aggregate counts: 576 verifier-ok schedules, 94 infeasible_proven cases, 0 unsolved cases, and 0 verify-invalid cases.
- E2/E3 are full-670 deterministic solver strategy ablations under the registered split and verifier-backed metrics schema.

Forbidden claims:

- Do not present E2/E3 as LLM tool-agent results.
- Do not present E2/E3 as CP-SAT results.
- Do not present E2/E3 as a new algorithmic superiority claim.
- Do not claim global optimality for `feasible` schedules.
- Do not claim complete real-world infeasibility beyond the current scheduling model, constraints, and verifier assumptions.
- Do not claim runtime speedup beyond observed run records.

## QA Gate Handoff

This draft is ready for `qa_repro_agent` to gate. QA should parse the listed
metrics and summaries, recompute metrics into a temporary path with
`aggregate_metrics.py`, compare against stored metrics, delete the temporary
file, and report findings back to `project_manager_agent` and
`experiment_manager_agent`.
