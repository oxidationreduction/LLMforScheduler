# E0/E1 Paper Table Draft

Generated from registered artifacts only. Do not mix unregistered legacy result
directories into paper main tables.

## Source Artifacts

| Run | Summary | Metrics |
|---|---|---|
| E0 existing timed_greedy | `results/raw_view/all_machine_capacity_dynamic_chunk25_20260626_tl120/summary.json` | `experiments/aaai2026/metrics_timed_greedy_existing.json` |
| E1 reproduced timed_greedy | `results/raw_view/e1_full670_repro_20260703_232018/summary.json` | `experiments/aaai2026/metrics_e1_full670_repro.json` |

Split source: `experiments/aaai2026/split_manifest.json`.

Recalculation method:

```bash
python3 experiments/aaai2026/aggregate_metrics.py \
  --split-manifest experiments/aaai2026/split_manifest.json \
  --run e1_full670_repro=results/raw_view/e1_full670_repro_20260703_232018 \
  --run timed_greedy=results/raw_view/all_machine_capacity_dynamic_chunk25_20260626_tl120 \
  --out <temporary_metrics_json>
```

Audit result:

- E1 stored metrics match recomputed metrics.
- E0 stored metrics match recomputed metrics.
- E0 vs E1 case-level comparison: `missing=0`, `extra=0`, `status_diffs=0`, `verify_diffs=0`.
- No unregistered legacy directory is included in the table draft.

## Overall Table Draft

| Run | Cases | Status counts | Verify counts | Unsolved | Verify invalid | Elapsed | Solve seconds p50/p90/p95/max | Artifact |
|---|---:|---|---|---:|---:|---:|---|---|
| E0 existing timed_greedy | 670 | feasible 560, optimal 16, infeasible_proven 94 | ok 576, not_applicable 94 | 0 | 0 | 195.741s | 0.079 / 0.582 / 0.918 / 18.354 | `experiments/aaai2026/metrics_timed_greedy_existing.json` |
| E1 reproduced timed_greedy | 670 | feasible 560, optimal 16, infeasible_proven 94 | ok 576, not_applicable 94 | 0 | 0 | 167.628s | 0.078 / 0.492 / 0.760 / 15.011 | `experiments/aaai2026/metrics_e1_full670_repro.json` |

## E1 Split And Difficulty Draft

| Group | Cases | Verify ok | Infeasible proven | Success rate verified | Solve seconds p50/p90/p95/max |
|---|---:|---:|---:|---:|---|
| train | 473 | 398 | 75 | 0.8414 | 0.076 / 0.458 / 0.839 / 15.011 |
| dev | 64 | 58 | 6 | 0.9063 | 0.071 / 0.246 / 0.507 / 0.712 |
| test | 133 | 120 | 13 | 0.9023 | 0.085 / 0.603 / 0.796 / 7.287 |
| easy | 223 | 223 | 0 | 1.0000 | 0.033 / 0.083 / 0.117 / 1.784 |
| medium | 223 | 223 | 0 | 1.0000 | 0.088 / 0.366 / 0.703 / 6.072 |
| hard | 224 | 130 | 94 | 0.5804 | 0.147 / 0.838 / 1.296 / 15.011 |

## Registry Audit

`agent_workpacks/shared/EXPERIMENT_REGISTRY.md` and
`agent_workpacks/shared/ARTIFACTS.md` accurately register E1 status, paths, and
key numbers. No mandatory project_manager update is required.

Optional project_manager follow-up: register a separate E0/E1 case-level
comparison artifact if the paper audit trail needs a durable diff artifact.

## Claim Boundaries

Claims that can be written:

- E1 fully reproduces the current timed_greedy solver on the full 670-case set.
- E1 has 576 verifier-ok schedules, 94 infeasible_proven cases, 0 unsolved cases, and 0 verify-invalid cases.
- E1 test split result is 120 verifier-ok and 13 infeasible_proven cases.
- E1 and the existing timed_greedy baseline have identical case-level status and verify_status outcomes.

Claims that must not be written:

- Do not present E1 as an LLM tool-agent result, CP-SAT result, or new algorithmic improvement.
- Do not present the elapsed difference between E0 and E1 as algorithmic speedup; it is only a run record.
- Do not state that every feasible case is globally optimal.
- Do not state that 576/670 cases are all feasible; 94 cases are infeasible_proven under the current model/verifier.
- Do not generalize infeasible_proven beyond the current scheduling model, constraints, and verifier assumptions.
