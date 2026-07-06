#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from common import (
    REPO_ROOT,
    SCHEMA_VERSION,
    read_json,
    relpath,
    sha256_file,
    solution_path,
    verify_path,
    write_json,
)
from schedule_solver import load_order, order_stats


CASE_RE = re.compile(r"SO-(?P<year>\d{4})-(?P<month>\d{2})-")


def split_for_case(case_id: str) -> tuple[str, list[str]]:
    match = CASE_RE.match(case_id)
    if not match:
        return "unknown", []
    year = int(match.group("year"))
    month = int(match.group("month"))
    if year <= 2023:
        return "train", []
    if year == 2024 and month <= 6:
        return "dev", []
    if year == 2024 and month >= 7:
        return "test", []
    if year >= 2025:
        return "test", ["ood_recent"]
    return "unknown", []


def difficulty_buckets(rows: list[dict[str, Any]]) -> dict[str, str]:
    active = sorted(
        (row for row in rows if row.get("complexity_score") is not None),
        key=lambda row: (float(row["complexity_score"]), str(row["case_id"])),
    )
    buckets: dict[str, str] = {}
    count = len(active)
    for index, row in enumerate(active):
        fraction = index / max(count - 1, 1)
        if fraction < 1 / 3:
            bucket = "easy"
        elif fraction < 2 / 3:
            bucket = "medium"
        else:
            bucket = "hard"
        buckets[str(row["case_id"])] = bucket
    return buckets


def summary_rows(reference_results: Path) -> dict[str, dict[str, Any]]:
    summary_path = reference_results / "summary.json"
    if not summary_path.exists():
        return {}
    summary = read_json(summary_path)
    rows = summary.get("cases", [])
    if not isinstance(rows, list):
        return {}
    return {str(row.get("case_id")): row for row in rows if row.get("case_id")}


def build_manifest(raw_orders: Path, reference_results: Path, seed: int) -> dict[str, Any]:
    rows_by_case = summary_rows(reference_results)
    cases: list[dict[str, Any]] = []
    for order_path in sorted(raw_orders.glob("*.json")):
        order = load_order(order_path)
        stats = order_stats(order)
        case_id = order.case_id
        split, eval_groups = split_for_case(case_id)
        worker_capacity = float(stats["worker_day_count"]) * 480.0
        load_ratio = (
            float(stats["total_work_minutes"]) / worker_capacity
            if worker_capacity > 0
            else None
        )
        result_row = rows_by_case.get(case_id, {})
        solution = solution_path(reference_results, case_id)
        verify = verify_path(reference_results, case_id)
        cases.append(
            {
                "case_id": case_id,
                "split": split,
                "eval_groups": eval_groups,
                "order_path": relpath(order_path),
                "solution_path": relpath(solution) if solution.exists() else None,
                "verify_path": relpath(verify) if verify.exists() else None,
                "solve_status": result_row.get("status") or result_row.get("solve_status"),
                "verify_status": result_row.get("verify_status"),
                "product_count": stats["product_count"],
                "net_required_total": stats["net_required_total"],
                "step_count": stats["step_count"],
                "total_work_minutes": stats["total_work_minutes"],
                "max_due_day": stats["max_due_day"],
                "worker_count": stats["worker_count"],
                "worker_day_count": stats["worker_day_count"],
                "complexity_score": stats["complexity_score"],
                "load_ratio": load_ratio,
                "difficulty_bucket": None,
                "source_sha256": sha256_file(order_path),
            }
        )

    buckets = difficulty_buckets(cases)
    split_counts: dict[str, int] = {}
    eval_group_counts: dict[str, int] = {}
    for row in cases:
        row["difficulty_bucket"] = buckets.get(str(row["case_id"]), "unknown")
        split_counts[str(row["split"])] = split_counts.get(str(row["split"]), 0) + 1
        for group in row.get("eval_groups", []):
            eval_group_counts[str(group)] = eval_group_counts.get(str(group), 0) + 1

    return {
        "schema_version": SCHEMA_VERSION,
        "seed": seed,
        "raw_orders_dir": relpath(raw_orders),
        "reference_results_dir": relpath(reference_results),
        "case_count": len(cases),
        "split_counts": split_counts,
        "eval_group_counts": eval_group_counts,
        "stratification_policy": {
            "primary_split": "train=2020-2023; dev=2024H1; test=2024H2-2025",
            "ood_recent": "2025-only cases are tagged in eval_groups while retaining primary split=test",
            "difficulty_bucket": "tertiles by complexity_score over all cases",
        },
        "cases": cases,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the AAAI 2026 split manifest.")
    parser.add_argument("--raw-orders", type=Path, default=REPO_ROOT / "raw_orders")
    parser.add_argument(
        "--reference-results",
        type=Path,
        default=REPO_ROOT / "results/raw_view/all_machine_capacity_dynamic_chunk25_20260626_tl120",
    )
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260703)
    parser.add_argument("--train-ratio", type=float, default=None, help="Accepted for compatibility; split is date-based.")
    parser.add_argument("--dev-ratio", type=float, default=None, help="Accepted for compatibility; split is date-based.")
    parser.add_argument("--test-ratio", type=float, default=None, help="Accepted for compatibility; split is date-based.")
    args = parser.parse_args()

    manifest = build_manifest(args.raw_orders, args.reference_results, args.seed)
    write_json(args.out, manifest)
    print(json.dumps({"out": str(args.out), "case_count": manifest["case_count"], "split_counts": manifest["split_counts"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

