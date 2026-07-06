#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from common import REPO_ROOT, SCHEMA_VERSION, read_json, relpath, solution_path, write_jsonl
from schedule_solver import load_order, net_required_by_product, order_stats


def route_lengths(order) -> dict[str, int]:
    return {product: len(steps) for product, steps in order.processes.items()}


def order_summary(order_path: Path) -> dict[str, Any]:
    order = load_order(order_path)
    stats = order_stats(order)
    return {
        "orders": [
            {"product_id": item.product_id, "quantity": item.quantity, "due_day": item.due_day}
            for item in order.orders
        ],
        "net_required_by_product": net_required_by_product(order),
        "route_lengths": route_lengths(order),
        "machine_counts": order.machines,
        "worker_count": stats["worker_count"],
        "worker_day_count": stats["worker_day_count"],
        "max_due_day": stats["max_due_day"],
        "complexity_score": stats["complexity_score"],
    }


def rows_by_case(source_results: Path) -> dict[str, dict[str, Any]]:
    summary = read_json(source_results / "summary.json")
    rows = summary.get("cases", [])
    return {str(row.get("case_id")): row for row in rows if row.get("case_id")}


def build_sft_rows(manifest: dict[str, Any], source_results: Path, splits: set[str]) -> list[dict[str, Any]]:
    source_rows = rows_by_case(source_results)
    output_rows: list[dict[str, Any]] = []
    for case in manifest.get("cases", []):
        split = str(case.get("split"))
        if split not in splits:
            continue
        case_id = str(case["case_id"])
        source_row = source_rows.get(case_id, {})
        strategy = source_row.get("strategy")
        verify_status = source_row.get("verify_status")
        if not isinstance(strategy, dict) or verify_status != "ok":
            continue
        order_path = REPO_ROOT / str(case["order_path"])
        summary = order_summary(order_path)
        target_tool_call = {
            "tool_name": "select_solver_strategy",
            "case_id": case_id,
            "arguments": {
                "case_id": case_id,
                "strategy": {
                    "unit_strategy": strategy.get("unit_strategy"),
                    "worker_strategy": strategy.get("worker_strategy"),
                    "day_strategy": strategy.get("day_strategy"),
                },
                "time_limit_seconds": 120,
                "expected_status": source_row.get("status"),
            },
        }
        output_rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "id": f"{case_id}:strategy",
                "case_id": case_id,
                "split": split,
                "messages": [
                    {
                        "role": "system",
                        "content": "Select a scheduling tool strategy. Return only one strict JSON tool call.",
                    },
                    {
                        "role": "user",
                        "content": json.dumps({"case_id": case_id, "order_summary": summary}, ensure_ascii=False),
                    },
                    {
                        "role": "assistant",
                        "content": json.dumps(target_tool_call, ensure_ascii=False),
                    },
                ],
                "target_tool_call": target_tool_call,
                "source_solution_path": relpath(solution_path(source_results, case_id)),
                "verify_status": verify_status,
                "strategy": strategy,
                "order_summary": summary,
            }
        )
    return output_rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Build SFT data for AAAI strategy-selection tool calls.")
    parser.add_argument("--split-manifest", type=Path, required=True)
    parser.add_argument("--source-results", type=Path, required=True)
    parser.add_argument("--splits", nargs="+", default=["train", "dev"])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    manifest = read_json(args.split_manifest)
    rows = build_sft_rows(manifest, args.source_results, set(args.splits))
    write_jsonl(args.out, rows)
    print(json.dumps({"out": str(args.out), "rows": len(rows), "splits": args.splits}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

