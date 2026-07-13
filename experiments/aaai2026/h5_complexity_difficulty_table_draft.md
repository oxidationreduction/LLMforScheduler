# H5 Complexity/Difficulty Metrics Draft

Status: `qa_pending`. This draft summarizes the registered E1 full-670 artifact only; it is not an H2/H3 comparison and must not enter the paper before the H5/H6 artifact QA gate.

## Feature availability and provenance

| Feature | Availability | Source / definition |
| --- | --- | --- |
| `operation_count` | `derived` | raw order JSON via schedule_solver.net_required_by_product and process-step counts; sum(net_required_quantity(product) * process_step_count(product)) |
| `total_work_minutes` | `available` | raw order JSON via schedule_solver.order_stats; sum(net_required_quantity(product) * process_step.duration_minutes) |
| `machine_load_ratio` | `derived` | raw order JSON via schedule_solver capacity semantics; max_machine(machine_demand_ticks / (machine_count * max_due_day * DAY_TICKS)) |
| `worker_day_count` | `available` | raw order JSON via schedule_solver.order_stats; sum(len(available_days) for each worker) |
| `load_ratio` | `available_not_a_substitute` | split manifest; worker total-work / worker-day capacity; never substituted for machine_load_ratio |

`load_ratio` is the manifest's worker total-work / worker-day capacity metric. It is `available_not_a_substitute` and is never used as `machine_load_ratio`.

## Empirical-tertile bucket results

| Feature | Bucket | Cases | Verify ok | Infeasible proven | Unsolved | Verify invalid | Runtime p50 | p90 | p95 | max |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `operation_count` | low | 223 | 223 | 0 | 0 | 0 | 0.031868 | 0.063419 | 0.072736 | 0.144295 |
| `operation_count` | medium | 223 | 223 | 0 | 0 | 0 | 0.094511 | 0.186777 | 0.248393 | 1.783712 |
| `operation_count` | high | 224 | 130 | 94 | 0 | 0 | 0.203162 | 1.007872 | 1.610563 | 15.010929 |
| `total_work_minutes` | low | 223 | 223 | 0 | 0 | 0 | 0.033855 | 0.085654 | 0.117366 | 0.421597 |
| `total_work_minutes` | medium | 223 | 223 | 0 | 0 | 0 | 0.087523 | 0.323075 | 0.698607 | 6.071807 |
| `total_work_minutes` | high | 224 | 130 | 94 | 0 | 0 | 0.155387 | 0.877643 | 1.414055 | 15.010929 |
| `machine_load_ratio` | low | 223 | 223 | 0 | 0 | 0 | 0.039601 | 0.111268 | 0.148070 | 0.369842 |
| `machine_load_ratio` | medium | 223 | 223 | 0 | 0 | 0 | 0.086385 | 0.612119 | 0.751888 | 7.287242 |
| `machine_load_ratio` | high | 224 | 130 | 94 | 0 | 0 | 0.115530 | 0.800058 | 1.296316 | 15.010929 |
| `worker_day_count` | low | 233 | 192 | 41 | 0 | 0 | 0.064884 | 0.305267 | 0.501414 | 3.416349 |
| `worker_day_count` | medium | 214 | 182 | 32 | 0 | 0 | 0.077228 | 0.367530 | 0.688019 | 2.661473 |
| `worker_day_count` | high | 223 | 202 | 21 | 0 | 0 | 0.097268 | 0.720739 | 1.014046 | 15.010929 |

## Claim boundaries

- H5 summarizes the registered E1 full-670 run only; it is not an H2/H3 comparison.
- Counts retain E1 summary status and verifier semantics; no solver or verifier was rerun.
- load_ratio is retained only as a named non-substitute worker-capacity metric.
- This QA-pending artifact must not be used as a paper result before qa_repro_agent gates it.

## Source artifacts

- `split_manifest`: `experiments/aaai2026/split_manifest.json`
- `e1_summary`: `results/raw_view/e1_full670_repro_20260703_232018/summary.json`
