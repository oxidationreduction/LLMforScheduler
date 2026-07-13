# Heuristic Replan Experiment Plan

Status: active from 2026-07-11.

## Summary

The paper track is now `verifier-backed industrial heuristic scheduling engine`.
LLM direct generation and LLM tool-agent experiments are not primary baselines.
They may be kept only as appendix/motivation evidence if the project manager
explicitly asks for them later.

The main evidence chain is:

- H1: `portfolio timed heuristic` on full 670 cases, reusing E0/E1.
- H2: fixed dispatching-rule baselines on full 670 cases, reusing E2.
- H3: chunked wavefront ablation on full 670 cases, reusing E3.
- H4: `CP-SAT stratified-50 baseline, 120s/case`, reusing E4.
- H5: complexity/difficulty analysis over verified registered artifacts.
- H6: verifier case studies grounded in solution/verify/infeasible artifacts.
- H7: optional CP-SAT stratified-50 600s/case appendix.
- H8: optional LLM appendix/motivation only.

## Rationale

Dispatching and priority rules are standard real-time heuristic baselines for
complex manufacturing scheduling. CP-SAT is an exact/constraint-programming
baseline suitable for job-shop-style scheduling models. Standard JSSP/FJSP
benchmarks such as JSPLib/FJSPLib are useful related-work anchors, but they do
not include this project's inventory deduction, worker availability, machine
copies, and due-date acceptance semantics. Recent LLM scheduling work targets
related but different standard scheduling settings and should not be the main
comparison for a pure heuristic industrial scheduler.

Reference anchors:

- NIST dispatching-rule survey: https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=821200
- OR-Tools CP-SAT docs: https://developers.google.com/optimization/cp/cp_solver
- OR-Tools scheduling docs: https://developers.google.com/optimization/cp
- JSPLib benchmark index: https://scheduleopt.github.io/benchmarks/jsplib/
- Starjob: https://arxiv.org/html/2503.01877v1
- Natural Plan: https://arxiv.org/abs/2406.04520

## Active H-Series Registry

| ID | Owner | Scope | Status | Required Output |
|---|---|---|---|---|
| H0 | project_manager_agent + experiment_manager_agent | Rewrite registry, decisions, risks, agent rules, and paper claim boundaries around heuristic scheduler story. | in progress | Updated workpacks and this plan. |
| H1 | experiment_manager_agent | Reuse E0/E1 full-670 main method evidence. | evidence ready | Paper row label: `portfolio timed heuristic`; 670 cases; 576 verify ok; 94 infeasible_proven; 0 unsolved; 0 verify invalid. |
| H2 | experiment_manager_agent | Reuse E2 full-670 fixed dispatching-rule baselines. | evidence ready | Table/ablation showing fixed rules leave 28-34 unsolved. |
| H3 | experiment_manager_agent | Reuse E3 full-670 chunked wavefront ablation. | evidence ready | Table/ablation showing chunk5/chunk10/chunk25 coverage differences. |
| H4 | experiment_manager_agent | Reuse E4 CP-SAT stratified-50 120s/case. | evidence ready | Separate CP-SAT subsection; never compare as full-670. |
| H5 | experiment_manager_agent + dev_framework_agent if needed | Complexity/difficulty bucket analysis. | next | `summary.json` or `metrics.json` plus paper table draft. |
| H6 | experiment_manager_agent + qa_repro_agent | Verifier case study. | next | Case-study note with artifact links and QA-safe claim wording. |
| H7 | dev_runner_agent | Optional CP-SAT stratified-50 600s/case appendix. | optional | New result directory and metrics, only if explicitly launched. |
| H8 | dev_runner_agent | Optional LLM appendix/motivation. | paused | E5 prompts may be reused; no main-table claim. |

## Evidence Labels

Use these exact labels unless project manager revises them:

- H1/E0/E1: `portfolio timed heuristic`.
- H2/E2: `fixed dispatching rule`.
- H3/E3: `chunked wavefront ablation`.
- H4/E4: `CP-SAT stratified-50 baseline, 120s/case`.
- H7: `CP-SAT stratified-50 baseline, 600s/case appendix`.
- H8: `LLM appendix/motivation only`.

## H5 Complexity/Difficulty Analysis

The preferred H5 output is a machine-readable metrics file derived from already
registered full-670 artifacts, with buckets by:

- operation_count;
- total_work_minutes;
- machine_load_ratio;
- worker_day_count.

Each bucket should report:

- case_count;
- status_counts;
- verify_counts;
- verified_ok_count;
- infeasible_proven_count;
- unsolved_count;
- verify_invalid_count;
- runtime p50/p90/p95/max;
- artifact source paths.

If a required difficulty feature is unavailable, the output must mark it as
`unavailable` instead of silently substituting a different metric.

## H6 Verifier Case Study

Select:

- 2 complex feasible cases with nontrivial operation and resource structure;
- 1 inventory-deduction or zero-task/optimal case;
- 1 capacity-lower-bound infeasible case.

Each selected case must point to concrete artifacts:

- order JSON;
- solution JSON when available;
- verify JSON when available;
- summary row or infeasibility artifact;
- verifier/checker outcome.

Case-study claims must say only what the artifact proves. Do not extrapolate a
case into global optimality, complete infeasibility proof, or industrial KPI
improvement.

## Paused LLM Track

E5 currently has prompts only:

- `results/raw_view/e5_llm_tool_agent_test133_20260710_232523/prompts.jsonl`

There is no `responses.jsonl`, parsed tool-call file, summary, or verifier
metrics. E5/E6/E7 must not be used in the main experiment comparison unless the
project manager explicitly reopens the LLM route.

## QA Gate

Before paper use, every H-series table or case study must pass:

- JSON is parseable.
- Case coverage is traceable to a manifest or explicit subset.
- Split has no leakage.
- `verify_invalid_count=0` for reported scheduling results.
- Table numbers can be recomputed from registered artifacts.
- Paper claim does not exceed artifact evidence.

Regression semantics to preserve:

- inventory deduction;
- multiple machine copies/concurrency;
- worker unavailable days;
- operation order;
- due-date failure;
- zero-task optimal cases;
- capacity-lower-bound infeasible cases.

## Paper Strategy

Recommended structure:

1. Introduction
2. Related Work
3. Problem Formulation
4. Verifier-Backed Heuristic Scheduling Framework
5. Scheduling Engine
6. Verifier
7. Experimental Setup
8. Results
9. Case Study
10. Limitations
11. Conclusion

Primary contributions:

- industrial scheduling framework with a deterministic heuristic portfolio;
- independent verifier as the acceptance boundary for hard constraints;
- 670-case empirical evidence with strategy ablations and a CP-SAT subset
  baseline.

Limitations to state proactively:

- not a global optimality proof system;
- not a complete real-world infeasibility proof system;
- external standard benchmarks are not the main evidence because they omit key
  industrial constraints in this dataset;
- LLM experiments are not the main scheduling method.
