# H6 — Verifier-backed four-case study

**Status:** `paper_ready`; independent H5/H6 artifact QA passed on 2026-07-15. This case study remains separate from the aggregate main table and retains the claim limits below.

This case study is anchored to the E1 full-670 reproduction only. It does not read or use E5/E6/E7 artifacts, does not use LLM output, and does not make an aggregate benchmark claim. The paths below are the E1 summary-row paths; the split manifest is used only for split, evaluation-group, and difficulty labels.

| Category | Case | Split / evaluation / difficulty | E1 status and verifier | Selected evidence |
| --- | --- | --- | --- | --- |
| Complex feasible | [`SO-2025-04-0022-2`](../../raw_orders/SO-2025-04-0022-2.json) | test / `ood_recent` / hard | `feasible`; verify `ok` | Largest observed E1-feasible total work (46,138.88 min) and complexity score; solution: 7,046 scheduled operations; E1 summary: 6,947 tasks after merge. |
| Complex feasible | [`SO-2022-12-0019-2`](../../raw_orders/SO-2022-12-0019-2.json) | train / — / hard | `feasible`; verify `ok` | Largest observed E1-feasible task count (9,129 after merge, E1 summary) and solve time (15.010928976 s); solution: 9,280 scheduled operations. |
| Inventory deduction / zero task | [`SO-2024-10-0032-2`](../../raw_orders/SO-2024-10-0032-2.json) | test / — / easy | `optimal`; verify `ok` | Requested quantity 5 and inventory quantity 5; solution plan `[]`; E1 summary and verifier task count 0. |
| Capacity lower-bound infeasible | [`SO-2025-05-0003-2`](../../raw_orders/SO-2025-05-0003-2.json) | test / `ood_recent` / hard | `infeasible_proven`; verify `not_applicable` | E1 records CMM CONTURA 10/16/6 required capacity `10701.610000 > 10080.000000`; no schedule exists to verify. |

## Evidence links

| Case | E1 solution | E1 verifier | E1 summary row |
| --- | --- | --- | --- |
| SO-2025-04-0022-2 | [solution](../../results/raw_view/e1_full670_repro_20260703_232018/solutions/SO-2025-04-0022-2.solution.json) | [verify](../../results/raw_view/e1_full670_repro_20260703_232018/solutions/SO-2025-04-0022-2.verify.json) | [`summary.json#cases[case_id=SO-2025-04-0022-2]`](../../results/raw_view/e1_full670_repro_20260703_232018/summary.json) |
| SO-2022-12-0019-2 | [solution](../../results/raw_view/e1_full670_repro_20260703_232018/solutions/SO-2022-12-0019-2.solution.json) | [verify](../../results/raw_view/e1_full670_repro_20260703_232018/solutions/SO-2022-12-0019-2.verify.json) | [`summary.json#cases[case_id=SO-2022-12-0019-2]`](../../results/raw_view/e1_full670_repro_20260703_232018/summary.json) |
| SO-2024-10-0032-2 | [solution](../../results/raw_view/e1_full670_repro_20260703_232018/solutions/SO-2024-10-0032-2.solution.json) | [verify](../../results/raw_view/e1_full670_repro_20260703_232018/solutions/SO-2024-10-0032-2.verify.json) | [`summary.json#cases[case_id=SO-2024-10-0032-2]`](../../results/raw_view/e1_full670_repro_20260703_232018/summary.json) |
| SO-2025-05-0003-2 | [solution / lower-bound certificate](../../results/raw_view/e1_full670_repro_20260703_232018/solutions/SO-2025-05-0003-2.solution.json) | [verify record (`not_applicable`)](../../results/raw_view/e1_full670_repro_20260703_232018/solutions/SO-2025-05-0003-2.verify.json) | [`summary.json#cases[case_id=SO-2025-05-0003-2]`](../../results/raw_view/e1_full670_repro_20260703_232018/summary.json) |

The machine-readable companion is [`h6_verifier_case_study_manifest.json`](h6_verifier_case_study_manifest.json). The split and difficulty labels are sourced from [`split_manifest.json`](split_manifest.json), while all solution/verify links above are deliberately taken from the E1 summary rather than the split manifest's legacy solution paths.

## Safe claims and claim limits

- The two feasible cases support only the narrow claim that their cited E1 timed-greedy schedules were recorded as verifier `ok` with zero reported errors.
- The inventory case supports only the cited order-level observation: demand 5 and inventory 5 produced an empty, zero-task E1 plan whose verifier record is `ok`.
- The capacity case supports only the cited lower-bound observation: CMM CONTURA 10/16/6 requires `10701.610000 > 10080.000000`; its verifier status must remain `not_applicable` because no schedule was emitted.
- Do not claim optimality for the feasible cases, universal runtime or quality, OOD generalization from one order, full-benchmark performance from four cases, or that `not_applicable` is a verifier pass/fail result.
- Use this draft only with its cited E1 evidence and the claim limits above.

## QA commands

```bash
python3 -m json.tool experiments/aaai2026/h6_verifier_case_study_manifest.json >/dev/null
jq -e '.status == "paper_ready" and .paper_ready == true and .selection_policy.category_count.total == 4' experiments/aaai2026/h6_verifier_case_study_manifest.json >/dev/null
jq -e '.cases | length == 4 and ([.[].case_id] | sort) == ["SO-2022-12-0019-2","SO-2024-10-0032-2","SO-2025-04-0022-2","SO-2025-05-0003-2"]' experiments/aaai2026/h6_verifier_case_study_manifest.json >/dev/null
jq -e '.cases[] | select(.case_id == "SO-2025-05-0003-2") | .status.verify_status == "not_applicable" and .observed_metrics.machine_capacity_lower_bound.comparison == "10701.610000 > 10080.000000"' experiments/aaai2026/h6_verifier_case_study_manifest.json >/dev/null
git diff --check -- experiments/aaai2026/h6_verifier_case_study_manifest.json experiments/aaai2026/h6_verifier_case_study_draft.md
```
