# H-Series Heuristic Paper Table Draft

Status: draft for `qa_repro_agent` gate.

This draft restates the QA-passed E0-E4 evidence under the new heuristic-first
paper strategy. It does not introduce new experiment results.

## Source Artifacts

| H ID | Evidence source | Metrics | Summary or manifest |
|---|---|---|---|
| H1 | E0 existing + E1 reproduction | `experiments/aaai2026/metrics_timed_greedy_existing.json`; `experiments/aaai2026/metrics_e1_full670_repro.json` | `results/raw_view/all_machine_capacity_dynamic_chunk25_20260626_tl120/summary.json`; `results/raw_view/e1_full670_repro_20260703_232018/summary.json` |
| H2 | E2 fixed dispatching rules | `experiments/aaai2026/metrics_e2_dispatch_baselines_20260707_153730.json` | summaries under `results/raw_view/e2_dispatch_*_20260707_153730/` |
| H3 | E3 chunked wavefront ablation | `experiments/aaai2026/metrics_e3_wavefront_ablation_20260707_153731.json` | summaries under `results/raw_view/e3_wavefront_chunk*_20260707_153731/` |
| H4 | E4 CP-SAT stratified-50 | `results/raw_view/e4_cpsat_stratified50_tl120_20260709_153557/metrics.json` | `results/raw_view/e4_cpsat_stratified50_tl120_20260709_153557/summary.json`; `experiments/aaai2026/e4_cpsat_stratified50_manifest.json` |

## Main Full-670 Heuristic Table

Use H1 as the main method row. E0 can be cited as the existing archived run, but
E1 is the preferred reproducible row for the paper table.

| Row label | H ID | Source | Scope | Cases | Coverage | Status counts | Verify counts | OK | Infeasible | Unsolved | Invalid | Elapsed | Solve seconds p50/p90/p95/max |
|---|---|---|---|---:|---:|---|---|---:|---:|---:|---:|---:|---|
| portfolio timed heuristic | H1 | E1 reproduced timed_greedy | full 670 | 670 | 1.0 | feasible 560, optimal 16, infeasible_proven 94 | ok 576, not_applicable 94 | 576 | 94 | 0 | 0 | 167.628s | 0.078 / 0.492 / 0.760 / 15.011 |
| fixed dispatching rule: round_robin_product | H2 | E2 dispatch baseline | full 670 | 670 | 1.0 | feasible 532, optimal 16, infeasible_proven 94, no_solution_found 28 | ok 548, not_applicable 122 | 548 | 94 | 28 | 0 | 139.882s | 0.079 / 0.387 / 0.621 / 6.508 |
| fixed dispatching rule: largest_route_work | H2 | E2 dispatch baseline | full 670 | 670 | 1.0 | feasible 532, optimal 16, infeasible_proven 94, no_solution_found 28 | ok 548, not_applicable 122 | 548 | 94 | 28 | 0 | 140.998s | 0.078 / 0.375 / 0.613 / 6.752 |
| chunked wavefront: chunk25 | H3 | E3 wavefront ablation | full 670 | 670 | 1.0 | feasible 560, optimal 16, infeasible_proven 94 | ok 576, not_applicable 94 | 576 | 94 | 0 | 0 | 172.358s | 0.085 / 0.502 / 0.861 / 7.446 |

## H2 Fixed Dispatching-Rule Ablation

| Strategy | Scope | Cases | OK | Infeasible | Unsolved | Invalid | Elapsed | Solve seconds p50/p90/p95/max |
|---|---|---:|---:|---:|---:|---:|---:|---|
| earliest_due | full 670 | 670 | 546 | 94 | 30 | 0 | 149.063s | 0.078 / 0.421 / 0.672 / 7.709 |
| round_robin_product | full 670 | 670 | 548 | 94 | 28 | 0 | 139.882s | 0.079 / 0.387 / 0.621 / 6.508 |
| largest_route_work | full 670 | 670 | 548 | 94 | 28 | 0 | 140.998s | 0.078 / 0.375 / 0.613 / 6.752 |
| smallest_route_work | full 670 | 670 | 542 | 94 | 34 | 0 | 147.854s | 0.079 / 0.396 / 0.652 / 7.720 |

## H3 Chunked Wavefront Ablation

| Strategy | Scope | Cases | OK | Infeasible | Unsolved | Invalid | Elapsed | Solve seconds p50/p90/p95/max |
|---|---|---:|---:|---:|---:|---:|---:|---|
| chunked_wavefront_5 | full 670 | 670 | 572 | 94 | 4 | 0 | 157.910s | 0.079 / 0.447 / 0.746 / 7.981 |
| chunked_wavefront_10 | full 670 | 670 | 574 | 94 | 2 | 0 | 160.155s | 0.081 / 0.453 / 0.735 / 7.254 |
| chunked_wavefront_25 | full 670 | 670 | 576 | 94 | 0 | 0 | 172.358s | 0.085 / 0.502 / 0.861 / 7.446 |

## H4 CP-SAT Stratified-50 Baseline

Do not compare this row to H1-H3 by equal case count. H4 uses a stratified
50-case subset from the parent 670-case manifest.

| Row label | H ID | Scope | Time limit | Cases | Coverage | Status counts | Verify counts | OK | Infeasible | Unsolved | Invalid | Method counts | Elapsed | Solve seconds mean/p50/p90/p95/max |
|---|---|---|---:|---:|---:|---|---|---:|---:|---:|---:|---|---:|---|
| CP-SAT stratified-50 baseline, 120s/case | H4 | stratified 50 subset | 120s/case | 50 | 1.0 | feasible 42, optimal 2, infeasible_proven 6 | ok 44, not_applicable 6 | 44 | 6 | 0 | 0 | timed_cpsat 39, timed_cpsat_batched 11 | 265.907s | 5.305 / 2.395 / 13.952 / 19.366 / 38.795 |

## Pending H5/H6 Tables

H5 and H6 are not yet paper-ready.

- H5 must produce a machine-readable complexity/difficulty `summary.json` or
  `metrics.json` before it enters this draft.
- H6 must produce a case-study note with order/solution/verify or infeasibility
  artifact links before it enters this draft.

## Claim Boundaries

Allowed:

- H1 reports verified feasible and capacity-lower-bound infeasible counts for
  the full-670 portfolio timed heuristic.
- H2 reports that fixed single dispatching rules leave 28-34 unsolved cases on
  the full-670 set.
- H3 reports that chunk size changes coverage, with chunk25 reaching the same
  aggregate counts as H1/E1.
- H4 reports CP-SAT behavior on a stratified 50-case subset under 120s/case.

Forbidden:

- Do not describe H1-H4 as LLM results.
- Do not describe H4 as full-670 or as the main method.
- Do not claim global optimality for feasible schedules.
- Do not claim complete real-world infeasibility.
- Do not claim industrial KPI improvement.
- Do not claim runtime speedup beyond observed run records.
