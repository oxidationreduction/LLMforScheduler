# Experiments

This section evaluates the verifier-backed heuristic scheduling engine on the
registered 670-case manifest. The main results use H1--H3, which are
paper-ready full-670 evaluations. H4 is reported separately because it is a
CP-SAT baseline on a stratified 50-case subset with a 120-second per-case time
limit. Consequently, H4 is not a case-count-equivalent comparison to H1--H3.

## Evaluation Protocol

All H1--H3 rows use the same 670-case split manifest and the same
verifier-backed reporting schema. A schedule contributes to the accepted count
only when its verifier record is `ok`. A result recorded as
`infeasible_proven` is a model-specific lower-bound outcome; it is not a claim
about complete infeasibility outside the modeled constraints and certificate.
We report `no_solution_found` separately from verifier-invalid output.

The H1--H4 values below are taken only from the paper-ready H-series evidence:
`experiments/aaai2026/h_series_heuristic_table_draft.md`. H1 is the portfolio
timed heuristic. H2 isolates fixed single dispatching rules, and H3 isolates
the chunked-wavefront setting. These comparisons study strategy coverage under
the registered evaluation protocol; they do not establish global optimality or
industrial KPI improvements.

## Full-670 Heuristic Evaluation

Table 1 reports H1--H3 on the full 670-case set. The portfolio timed heuristic
(H1) produced 576 verifier-accepted schedules, 94 model-specific
`infeasible_proven` outcomes, no unsolved cases, and no verifier-invalid
records. The two strongest fixed-rule H2 configurations each left 28 cases
without a solution, whereas H3 chunk size 25 recovered the H1 aggregate
coverage. The table presents observed run records, not an algorithmic runtime
speedup claim.

| Setting | H ID | Cases | Verifier `ok` | `infeasible_proven` | `no_solution_found` | Verifier invalid | Elapsed |
|---|---|---:|---:|---:|---:|---:|---:|
| Portfolio timed heuristic | H1 | 670 | 576 | 94 | 0 | 0 | 167.628 s |
| Fixed rule: `round_robin_product` | H2 | 670 | 548 | 94 | 28 | 0 | 139.882 s |
| Fixed rule: `largest_route_work` | H2 | 670 | 548 | 94 | 28 | 0 | 140.998 s |
| Chunked wavefront, chunk 5 | H3 | 670 | 572 | 94 | 4 | 0 | 157.910 s |
| Chunked wavefront, chunk 10 | H3 | 670 | 574 | 94 | 2 | 0 | 160.155 s |
| Chunked wavefront, chunk 25 | H3 | 670 | 576 | 94 | 0 | 0 | 172.358 s |

For the complete H2 ablation, the four fixed rules yield 546, 548, 548, and
542 verifier-accepted schedules for `earliest_due`,
`round_robin_product`, `largest_route_work`, and `smallest_route_work`,
respectively. Their unresolved-case counts range from 28 to 34. For H3, the
chunk sizes 5, 10, and 25 yield 572, 574, and 576 verifier-accepted schedules,
respectively. This ablation indicates that the portfolio/chunking choices
affect coverage in this evaluation; it makes no claim that a feasible schedule
is globally optimal.

## CP-SAT Stratified-50 Baseline

H4 is deliberately isolated from Table 1. It runs the CP-SAT
stratified-50 baseline on a stratified 50-case subset sampled from the same
670-case parent manifest, with a 120-second limit per case. On this subset,
H4 records 44 verifier-accepted schedules and 6 model-specific
`infeasible_proven` outcomes, with no unsolved or verifier-invalid records.
These results characterize the baseline on its stated subset only; they are
not compared to the full-670 rows by equal case count and are not a main-method
result.

| Setting | H ID | Evaluation scope | Time limit | Cases | Verifier `ok` | `infeasible_proven` | `no_solution_found` | Verifier invalid |
|---|---|---|---:|---:|---:|---:|---:|---:|
| CP-SAT stratified-50 baseline | H4 | Stratified subset of the 670-case parent manifest | 120 s/case | 50 | 44 | 6 | 0 | 0 |

## Audited Complexity, Case-Study, and Appendix Material

### H5 Complexity and Difficulty Analysis

The H5 artifact QA gate passed for an audit of the E1 full-670 reproduction:
the split manifest and E1 summary join on 670 unique case IDs with no missing
or extra IDs. Table 3 reports empirical-tertile summaries from
[`h5_complexity_difficulty_metrics.json`](h5_complexity_difficulty_metrics.json).
`operation_count` and `machine_load_ratio` are derived from raw orders using
the scheduler's operation and capacity semantics; `total_work_minutes` and
`worker_day_count` are available raw-order statistics. The manifest's
`load_ratio` remains explicitly `available_not_a_substitute`: it is a
worker-capacity metric and is not substituted for `machine_load_ratio`.

| Scale feature | Provenance | Low / medium / high cases | Verifier `ok` (low / medium / high) | `infeasible_proven` (low / medium / high) | Solve-time p50, s (low / medium / high) |
|---|---|---:|---:|---:|---:|
| `operation_count` | derived | 223 / 223 / 224 | 223 / 223 / 130 | 0 / 0 / 94 | 0.032 / 0.095 / 0.203 |
| `total_work_minutes` | available | 223 / 223 / 224 | 223 / 223 / 130 | 0 / 0 / 94 | 0.034 / 0.088 / 0.155 |
| `machine_load_ratio` | derived | 223 / 223 / 224 | 223 / 223 / 130 | 0 / 0 / 94 | 0.040 / 0.086 / 0.116 |
| `worker_day_count` | available | 233 / 214 / 223 | 192 / 182 / 202 | 41 / 32 / 21 | 0.065 / 0.077 / 0.097 |

Each feature's buckets cover all 670 cases and record zero unsolved and zero
verifier-invalid outputs. The concentration of the 94 model-specific
`infeasible_proven` outcomes in the high operation-count, work-minute, and
machine-load tertiles is a descriptive property of this E1 run, not a causal
difficulty claim or a comparison with H2/H3. H5 does not rerun the solver or
verifier, establish global optimality, or establish complete infeasibility.

### H6 Verifier Case Study

The H6 artifact QA gate also passed for the four-case evidence index in
[`h6_verifier_case_study_manifest.json`](h6_verifier_case_study_manifest.json)
and its companion
[`h6_verifier_case_study_draft.md`](h6_verifier_case_study_draft.md). All
order, solution, and verifier references resolve to E1 full-670 summary rows;
the study is illustrative case evidence, not an aggregate benchmark claim.

| Category | Case and audited evidence | E1 status / verifier boundary |
|---|---|---|
| Complex feasible | `SO-2025-04-0022-2`: the largest observed E1-feasible total work (46,138.88 min) and complexity score; 7,046 scheduled operations and 6,947 merged tasks in the E1 summary/verifier record. | `feasible`; verifier `ok` |
| Complex feasible | `SO-2022-12-0019-2`: the largest observed E1-feasible merged task count (9,129) and solve time (15.010928976 s); 9,280 scheduled operations. | `feasible`; verifier `ok` |
| Inventory deduction / zero task | `SO-2024-10-0032-2`: requested quantity 5 and inventory quantity 5 yield an empty plan with zero E1-summary and verifier tasks. | current-model `optimal`; verifier `ok` |
| Capacity lower-bound infeasible | `SO-2025-05-0003-2`: CMM CONTURA 10/16/6 requires `10701.610000 > 10080.000000` under the recorded capacity lower bound. | `infeasible_proven`; verifier `not_applicable` because no schedule was emitted |

The two feasible rows show only that their cited E1 schedules were verifier
`ok`. The inventory row is an audited zero-task observation, and its
current-model `optimal` status is not a global-optimality claim. The capacity
row is only a model-specific lower-bound observation: `not_applicable` means
that there was no emitted schedule to verify, not a verifier pass, a verifier
failure, or a complete real-world infeasibility result. H6 excludes E5/E6/E7
and LLM output.

**H7 appendix-only 600-second extension.** H7 is the
`CP-SAT stratified-50 baseline, 600s/case appendix`: on 50 cases it records
44 verifier `ok`, 6 `infeasible_proven`, 0 unsolved, and 0 verifier-invalid
outputs. It remains appendix material only and must not be treated as directly
equivalent to E4 at 120s/case or to the full-670 evaluations.

## Scope Statement

The study centers on a verifier-backed heuristic scheduler. It does not use
LLM systems as the main method or comparison. The reported evidence does not
claim global optimality, complete infeasibility in a broader real-world sense,
or industrial KPI improvement.

## Evidence References

- H1--H4 paper-ready source: `experiments/aaai2026/h_series_heuristic_table_draft.md`.
- H1 reproduced full-670 run: `experiments/aaai2026/metrics_e1_full670_repro.json`.
- H2 fixed-rule ablation: `experiments/aaai2026/metrics_e2_dispatch_baselines_20260707_153730.json`.
- H3 wavefront ablation: `experiments/aaai2026/metrics_e3_wavefront_ablation_20260707_153731.json`.
- H4 subset baseline: `results/raw_view/e4_cpsat_stratified50_tl120_20260709_153557/metrics.json`.
