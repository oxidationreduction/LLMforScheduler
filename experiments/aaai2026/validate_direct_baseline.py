#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from common import REPO_ROOT, SCHEMA_VERSION, read_json, relpath, write_json
from check_schedule import check_solution


def candidate_solution_paths(directory: Path, case_id: str) -> list[Path]:
    return [
        directory / f"{case_id}.solution.json",
        directory / f"{case_id}.json",
        directory / "solutions" / f"{case_id}.solution.json",
        directory / "solutions" / f"{case_id}.json",
    ]


def find_solution(directory: Path, case_id: str) -> Path | None:
    for path in candidate_solution_paths(directory, case_id):
        if path.exists():
            return path
    return None


def validate_one(case: dict[str, Any], llm_solutions: Path, sample_dir: Path, max_errors: int) -> dict[str, Any]:
    case_id = str(case["case_id"])
    raw_output_path = find_solution(llm_solutions, case_id)
    base = {
        "case_id": case_id,
        "split": case.get("split"),
        "raw_output_path": relpath(raw_output_path) if raw_output_path else None,
        "parsed_solution_path": relpath(raw_output_path) if raw_output_path else None,
    }
    if raw_output_path is None:
        return {
            **base,
            "parse_status": "missing",
            "checker_status": "invalid",
            "error_count": 1,
            "machine_error_count": 0,
            "task_count": 0,
            "plan_day_min": None,
            "plan_day_max": None,
            "solve_status": None,
            "errors": ["missing direct baseline output"],
        }
    try:
        json.loads(raw_output_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {
            **base,
            "parse_status": "parse_failed",
            "checker_status": "invalid",
            "error_count": 1,
            "machine_error_count": 0,
            "task_count": 0,
            "plan_day_min": None,
            "plan_day_max": None,
            "solve_status": None,
            "errors": [f"JSON parse failed: {exc}"],
        }
    order_path = sample_dir / f"{case_id}.json"
    row = check_solution(
        order_path,
        raw_output_path,
        max_errors=max_errors,
        require_feasible_status=True,
        check_machine_concurrency=True,
    )
    return {
        **base,
        "parse_status": "ok",
        "checker_status": row.get("checker_status"),
        "error_count": row.get("error_count"),
        "machine_error_count": row.get("machine_error_count"),
        "task_count": row.get("plan_task_count"),
        "plan_day_min": row.get("plan_day_min"),
        "plan_day_max": row.get("plan_day_max"),
        "solve_status": row.get("solve_status"),
        "errors": row.get("errors", []),
    }


def validate(manifest: dict[str, Any], llm_solutions: Path, sample_dir: Path, max_errors: int) -> dict[str, Any]:
    rows = [
        validate_one(case, llm_solutions, sample_dir, max_errors)
        for case in manifest.get("cases", [])
        if case.get("split") == "test" or "ood_recent" in case.get("eval_groups", [])
    ]
    status_counts: dict[str, int] = {}
    parse_counts: dict[str, int] = {}
    for row in rows:
        status = str(row.get("checker_status"))
        parse_status = str(row.get("parse_status"))
        status_counts[status] = status_counts.get(status, 0) + 1
        parse_counts[parse_status] = parse_counts.get(parse_status, 0) + 1
    return {
        "schema_version": SCHEMA_VERSION,
        "llm_solutions": relpath(llm_solutions),
        "sample_dir": relpath(sample_dir),
        "case_count": len(rows),
        "checker_status_counts": status_counts,
        "parse_status_counts": parse_counts,
        "cases": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate direct LLM schedule-generation baseline outputs.")
    parser.add_argument("--split-manifest", type=Path, required=True)
    parser.add_argument("--llm-solutions", type=Path, required=True)
    parser.add_argument("--sample-dir", type=Path, default=REPO_ROOT / "raw_orders")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--max-errors", type=int, default=20)
    args = parser.parse_args()

    payload = validate(read_json(args.split_manifest), args.llm_solutions, args.sample_dir, args.max_errors)
    write_json(args.out, payload)
    print(json.dumps({"out": str(args.out), "case_count": payload["case_count"], "checker_status_counts": payload["checker_status_counts"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
