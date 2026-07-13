#!/usr/bin/env python3
"""Build and independently recheck the H5 full-670 complexity analysis.

The tool deliberately reads only the registered split manifest, E1 summary,
and the raw order JSON files named by the manifest.  It does not run the
solver or verifier and never changes their semantics.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from common import REPO_ROOT, SCHEMA_VERSION, numeric_stats, read_json, relpath
from schedule_solver import (
    CP_SAT_DURATION_SCALE,
    DAY_TICKS,
    load_order,
    max_due_day,
    net_required_by_product,
    order_stats,
    real_equipment,
)


H5_SCHEMA_VERSION = "aaai2026.h5.v1"
FEATURE_ORDER = (
    "operation_count",
    "total_work_minutes",
    "machine_load_ratio",
    "worker_day_count",
)
BUCKET_NAMES = ("low", "medium", "high")
NOT_SOLVED_STATUSES = {
    "no_solution_found",
    "time_limit",
    "failed",
    "solver_unavailable",
}


def _case_rows(payload: dict[str, Any], label: str) -> list[dict[str, Any]]:
    rows = payload.get("cases")
    if not isinstance(rows, list):
        raise ValueError(f"{label}.cases must be a list")
    if payload.get("case_count") is not None and payload["case_count"] != len(rows):
        raise ValueError(f"{label}.case_count does not match cases length")
    result: list[dict[str, Any]] = []
    case_ids: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or not row.get("case_id"):
            raise ValueError(f"{label}.cases[{index}] has no case_id")
        case_id = str(row["case_id"])
        if case_id in case_ids:
            raise ValueError(f"duplicate {label} case_id: {case_id}")
        case_ids.add(case_id)
        result.append(row)
    return result


def _resolve_order_path(value: Any, manifest_path: Path) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError("manifest case has no order_path")
    path = Path(value)
    if path.is_absolute():
        return path
    repo_candidate = REPO_ROOT / path
    if repo_candidate.exists():
        return repo_candidate
    return manifest_path.parent / path


def operation_count(order) -> int:
    """Count net-required product units times their process-step count."""
    return sum(
        int(quantity) * len(order.processes.get(product_id, ()))
        for product_id, quantity in net_required_by_product(order).items()
        if quantity > 0
    )


def machine_load_ratio(order) -> float:
    """Mirror the solver's _max_machine_load_ratio capacity semantics."""
    horizon = max_due_day(order)
    if horizon <= 0:
        return 0.0
    machine_work_ticks: dict[str, int] = {}
    for product_id, quantity in net_required_by_product(order).items():
        if quantity <= 0:
            continue
        for step in order.processes.get(product_id, ()):
            step_ticks = int(round(float(step.duration_minutes) * CP_SAT_DURATION_SCALE)) * int(quantity)
            for machine in dict.fromkeys(real_equipment(step.equipment)):
                machine_work_ticks[machine] = machine_work_ticks.get(machine, 0) + step_ticks
    ratios = [
        demand_ticks / capacity_ticks
        for machine, demand_ticks in machine_work_ticks.items()
        if (capacity_ticks := max(int(order.machines.get(machine, 0)), 0) * horizon * DAY_TICKS) > 0
    ]
    return max(ratios, default=0.0)


def derive_features(order) -> dict[str, float | int]:
    stats = order_stats(order)
    return {
        "operation_count": operation_count(order),
        "total_work_minutes": stats["total_work_minutes"],
        "machine_load_ratio": machine_load_ratio(order),
        "worker_day_count": stats["worker_day_count"],
    }


def _bucket_assignments(rows: list[dict[str, Any]], feature: str) -> tuple[dict[str, str], dict[str, Any]]:
    ordered = sorted(rows, key=lambda row: (float(row["features"][feature]), str(row["case_id"])))
    if not ordered:
        raise ValueError("cannot bucket an empty case set")
    first_target = max(1, len(ordered) // 3)
    second_target = min(len(ordered), max(first_target + 1, (2 * len(ordered)) // 3))
    first_cut_index = first_target - 1
    second_cut_index = second_target - 1
    # For 670 rows this deliberately selects sorted positions 222 and 445,
    # giving nominal 223/223/224 targets before whole-value tie preservation.
    first_cut = float(ordered[first_cut_index]["features"][feature])
    second_cut = float(ordered[second_cut_index]["features"][feature])
    assignments: dict[str, str] = {}
    for row in ordered:
        value = float(row["features"][feature])
        assignments[str(row["case_id"])] = "low" if value <= first_cut else "medium" if value <= second_cut else "high"
    nominal_counts = [first_target, second_target - first_target, len(ordered) - second_target]
    return assignments, {
        "method": "empirical_tertiles; boundaries are sorted nominal tertile values; equal feature values remain in one bucket",
        "nominal_bucket_case_counts": dict(zip(BUCKET_NAMES, nominal_counts)),
        "cutoffs": {"low_max": first_cut, "medium_max": second_cut},
    }


def _counts(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    return dict(sorted(Counter(str(row[key]) for row in rows if row.get(key) is not None).items()))


def _runtime_stats(rows: list[dict[str, Any]]) -> dict[str, float | int | None]:
    stats = numeric_stats([row.get("solve_seconds", row.get("wall_seconds")) for row in rows])
    return {"count": stats["count"], "p50": stats["median"], "p90": stats["p90"], "p95": stats["p95"], "max": stats["max"]}


def _bucket_metrics(rows: list[dict[str, Any]], source_paths: dict[str, str]) -> dict[str, Any]:
    status_counts = _counts(rows, "status")
    verify_counts = _counts(rows, "verify_status")
    return {
        "case_count": len(rows),
        "status_counts": status_counts,
        "verify_counts": verify_counts,
        "verified_ok_count": verify_counts.get("ok", 0),
        "infeasible_proven_count": status_counts.get("infeasible_proven", 0),
        "unsolved_count": sum(status_counts.get(status, 0) for status in NOT_SOLVED_STATUSES),
        "verify_invalid_count": sum(count for status, count in verify_counts.items() if status not in {"ok", "not_applicable"}),
        "solve_seconds": _runtime_stats(rows),
        "case_ids": sorted(str(row["case_id"]) for row in rows),
        "source_paths": source_paths,
    }


def build_h5_payload(
    manifest: dict[str, Any],
    summary: dict[str, Any],
    *,
    split_manifest_path: Path,
    summary_path: Path,
) -> dict[str, Any]:
    manifest_rows = _case_rows(manifest, "split_manifest")
    summary_rows = _case_rows(summary, "summary")
    manifest_by_case = {str(row["case_id"]): row for row in manifest_rows}
    summary_by_case = {str(row["case_id"]): row for row in summary_rows}
    manifest_ids, summary_ids = set(manifest_by_case), set(summary_by_case)
    if manifest_ids != summary_ids:
        missing_summary = sorted(manifest_ids - summary_ids)
        missing_manifest = sorted(summary_ids - manifest_ids)
        raise ValueError(f"case-id join mismatch: manifest_only={missing_summary}; summary_only={missing_manifest}")

    source_paths = {"split_manifest": relpath(split_manifest_path), "e1_summary": relpath(summary_path)}
    cases: list[dict[str, Any]] = []
    for manifest_row in manifest_rows:
        case_id = str(manifest_row["case_id"])
        order_path = _resolve_order_path(manifest_row.get("order_path"), split_manifest_path)
        if not order_path.exists():
            raise FileNotFoundError(f"order JSON not found for {case_id}: {order_path}")
        order = load_order(order_path)
        if order.case_id != case_id:
            raise ValueError(f"order path case_id mismatch: expected {case_id}, got {order.case_id}")
        if order.schema_errors:
            raise ValueError(f"order schema errors for {case_id}: {'; '.join(order.schema_errors)}")
        summary_row = summary_by_case[case_id]
        cases.append(
            {
                "case_id": case_id,
                "split": manifest_row.get("split"),
                "difficulty_bucket": manifest_row.get("difficulty_bucket"),
                "order_path": relpath(order_path),
                "summary_row_source": {"summary_path": source_paths["e1_summary"], "case_id": case_id},
                "status": summary_row.get("status", summary_row.get("solve_status")),
                "verify_status": summary_row.get("verify_status"),
                "solve_seconds": summary_row.get("solve_seconds", summary_row.get("wall_seconds")),
                "features": derive_features(order),
                "non_substitute_metrics": {
                    "load_ratio": {
                        "value": manifest_row.get("load_ratio"),
                        "availability": "available_not_a_substitute",
                        "meaning": "manifest worker total-work / worker-day capacity; not machine_load_ratio",
                    }
                },
            }
        )

    availability = {
        "operation_count": {
            "availability": "derived",
            "source": "raw order JSON via schedule_solver.net_required_by_product and process-step counts",
            "formula": "sum(net_required_quantity(product) * process_step_count(product))",
        },
        "total_work_minutes": {
            "availability": "available",
            "source": "raw order JSON via schedule_solver.order_stats",
            "formula": "sum(net_required_quantity(product) * process_step.duration_minutes)",
        },
        "machine_load_ratio": {
            "availability": "derived",
            "source": "raw order JSON via schedule_solver capacity semantics",
            "formula": "max_machine(machine_demand_ticks / (machine_count * max_due_day * DAY_TICKS))",
        },
        "worker_day_count": {
            "availability": "available",
            "source": "raw order JSON via schedule_solver.order_stats",
            "formula": "sum(len(available_days) for each worker)",
        },
        "load_ratio": {
            "availability": "available_not_a_substitute",
            "source": "split manifest",
            "meaning": "worker total-work / worker-day capacity; never substituted for machine_load_ratio",
        },
    }
    bucket_features: dict[str, Any] = {}
    for feature in FEATURE_ORDER:
        assignments, policy = _bucket_assignments(cases, feature)
        buckets = {}
        for bucket in BUCKET_NAMES:
            bucket_rows = [row for row in cases if assignments[row["case_id"]] == bucket]
            buckets[bucket] = _bucket_metrics(bucket_rows, source_paths)
        bucket_features[feature] = {**policy, "buckets": buckets}

    return {
        "schema_version": H5_SCHEMA_VERSION,
        "source_artifacts": source_paths,
        "join_audit": {
            "manifest_case_count": len(manifest_rows),
            "summary_case_count": len(summary_rows),
            "manifest_unique_case_count": len(manifest_ids),
            "summary_unique_case_count": len(summary_ids),
            "case_id_sets_match": True,
            "manifest_only_case_ids": [],
            "summary_only_case_ids": [],
        },
        "feature_availability_and_provenance": availability,
        "case_count": len(cases),
        "cases": cases,
        "feature_buckets": bucket_features,
        "claim_boundaries": [
            "H5 summarizes the registered E1 full-670 run only; it is not an H2/H3 comparison.",
            "Counts retain E1 summary status and verifier semantics; no solver or verifier was rerun.",
            "load_ratio is retained only as a named non-substitute worker-capacity metric.",
            "This QA-pending artifact must not be used as a paper result before qa_repro_agent gates it.",
        ],
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# H5 Complexity/Difficulty Metrics Draft",
        "",
        "Status: `qa_pending`. This draft summarizes the registered E1 full-670 artifact only; it is not an H2/H3 comparison and must not enter the paper before the H5/H6 artifact QA gate.",
        "",
        "## Feature availability and provenance",
        "",
        "| Feature | Availability | Source / definition |",
        "| --- | --- | --- |",
    ]
    for feature in (*FEATURE_ORDER, "load_ratio"):
        item = payload["feature_availability_and_provenance"][feature]
        definition = item.get("formula", item.get("meaning", ""))
        lines.append(f"| `{feature}` | `{item['availability']}` | {item['source']}; {definition} |")
    lines.extend(
        [
            "",
            "`load_ratio` is the manifest's worker total-work / worker-day capacity metric. It is `available_not_a_substitute` and is never used as `machine_load_ratio`.",
            "",
            "## Empirical-tertile bucket results",
            "",
            "| Feature | Bucket | Cases | Verify ok | Infeasible proven | Unsolved | Verify invalid | Runtime p50 | p90 | p95 | max |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for feature in FEATURE_ORDER:
        for bucket in BUCKET_NAMES:
            metrics = payload["feature_buckets"][feature]["buckets"][bucket]
            runtime = metrics["solve_seconds"]
            formatted_runtime = ["—" if value is None else f"{value:.6f}" for value in (runtime["p50"], runtime["p90"], runtime["p95"], runtime["max"])]
            lines.append(
                f"| `{feature}` | {bucket} | {metrics['case_count']} | {metrics['verified_ok_count']} | "
                f"{metrics['infeasible_proven_count']} | {metrics['unsolved_count']} | {metrics['verify_invalid_count']} | "
                f"{' | '.join(formatted_runtime)} |"
            )
    lines.extend(["", "## Claim boundaries", ""])
    lines.extend(f"- {claim}" for claim in payload["claim_boundaries"])
    lines.extend(["", "## Source artifacts", ""])
    for label, path in payload["source_artifacts"].items():
        lines.append(f"- `{label}`: `{path}`")
    return "\n".join(lines) + "\n"


def generate_outputs(payload: dict[str, Any], out_json: Path, out_md: Path) -> None:
    existing = [path for path in (out_json, out_md) if path.exists()]
    if existing:
        raise FileExistsError("refusing to overwrite existing output(s): " + ", ".join(map(str, existing)))
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_md.write_text(render_markdown(payload), encoding="utf-8")


def check_existing(payload: dict[str, Any], existing_json: Path, existing_md: Path) -> None:
    if read_json(existing_json) != payload:
        raise ValueError(f"existing JSON does not match recomputed payload: {existing_json}")
    if existing_md.read_text(encoding="utf-8") != render_markdown(payload):
        raise ValueError(f"existing Markdown does not match recomputed payload: {existing_md}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build or independently recheck the H5 full-670 complexity/difficulty artifact.")
    parser.add_argument("--split-manifest", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--out-json", type=Path)
    parser.add_argument("--out-md", type=Path)
    parser.add_argument("--check-existing-json", type=Path)
    parser.add_argument("--check-existing-md", type=Path)
    args = parser.parse_args()
    generating = args.out_json is not None or args.out_md is not None
    checking = args.check_existing_json is not None or args.check_existing_md is not None
    if generating == checking or (generating and (args.out_json is None or args.out_md is None)) or (checking and (args.check_existing_json is None or args.check_existing_md is None)):
        parser.error("supply exactly one complete pair: --out-json/--out-md or --check-existing-json/--check-existing-md")

    payload = build_h5_payload(
        read_json(args.split_manifest),
        read_json(args.summary),
        split_manifest_path=args.split_manifest,
        summary_path=args.summary,
    )
    if generating:
        generate_outputs(payload, args.out_json, args.out_md)
        print(json.dumps({"out_json": str(args.out_json), "out_md": str(args.out_md), "case_count": payload["case_count"]}, ensure_ascii=False))
    else:
        check_existing(payload, args.check_existing_json, args.check_existing_md)
        print(json.dumps({"check": "ok", "case_count": payload["case_count"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
