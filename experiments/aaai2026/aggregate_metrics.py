#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from common import SCHEMA_VERSION, numeric_stats, read_json, relpath, write_json


def parse_run(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("--run must be NAME=PATH")
    name, raw_path = value.split("=", 1)
    if not name.strip():
        raise argparse.ArgumentTypeError("run NAME cannot be empty")
    return name.strip(), Path(raw_path)


def load_run_cases(run_path: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    summary_path = run_path / "summary.json" if run_path.is_dir() else run_path
    summary = read_json(summary_path)
    cases = summary.get("cases", [])
    if not isinstance(cases, list):
        cases = []
    by_case = {str(row.get("case_id")): row for row in cases if row.get("case_id")}
    return summary, by_case


def status_value(row: dict[str, Any]) -> str | None:
    value = row.get("status", row.get("solve_status"))
    return str(value) if value is not None else None


def verify_value(row: dict[str, Any]) -> str | None:
    value = row.get("verify_status", row.get("checker_status"))
    return str(value) if value is not None else None


def count_by(rows: list[dict[str, Any]], getter) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = getter(row)
        if value is None:
            continue
        counts[value] = counts.get(value, 0) + 1
    return counts


def aggregate_rows(rows: list[dict[str, Any]], expected_count: int) -> dict[str, Any]:
    status_counts = count_by(rows, status_value)
    verify_counts = count_by(rows, verify_value)
    verified_ok = verify_counts.get("ok", 0)
    infeasible = status_counts.get("infeasible_proven", 0)
    not_solved = sum(status_counts.get(status, 0) for status in ("no_solution_found", "time_limit", "failed", "solver_unavailable"))
    verify_invalid = sum(count for status, count in verify_counts.items() if status not in {"ok", "not_applicable"})
    parse_ok = sum(1 for row in rows if row.get("parse_status") in {"ok", "parsed"})
    tool_call_ok = sum(1 for row in rows if row.get("tool_call_ok") is True)
    return {
        "case_count": len(rows),
        "expected_case_count": expected_count,
        "coverage_rate": len(rows) / expected_count if expected_count else None,
        "solved_count": sum(count for status, count in status_counts.items() if status in {"feasible", "optimal"}),
        "verified_ok_count": verified_ok,
        "infeasible_proven_count": infeasible,
        "not_solved_count": not_solved,
        "verify_invalid_count": verify_invalid,
        "parse_ok_count": parse_ok,
        "tool_call_ok_count": tool_call_ok,
        "success_rate_verified": verified_ok / len(rows) if rows else None,
        "status_counts": status_counts,
        "verify_counts": verify_counts,
        "solve_seconds": numeric_stats([row.get("solve_seconds", row.get("wall_seconds")) for row in rows]),
        "task_count": numeric_stats([row.get("task_count", row.get("plan_task_count")) for row in rows]),
    }


def group_rows(manifest_cases: list[dict[str, Any]], run_rows: dict[str, dict[str, Any]], key: str) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for case in manifest_cases:
        case_id = str(case["case_id"])
        row = run_rows.get(case_id)
        if row is None:
            continue
        group = str(case.get(key, "unknown"))
        groups.setdefault(group, []).append(row)
    return groups


def aggregate_run(name: str, run_path: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    summary, run_rows = load_run_cases(run_path)
    manifest_cases = manifest.get("cases", [])
    expected_case_ids = {str(case["case_id"]) for case in manifest_cases}
    rows = [row for case_id, row in run_rows.items() if not expected_case_ids or case_id in expected_case_ids]
    by_split = {
        split: aggregate_rows(group, len([case for case in manifest_cases if case.get("split") == split]))
        for split, group in group_rows(manifest_cases, run_rows, "split").items()
    }
    by_difficulty = {
        bucket: aggregate_rows(group, len([case for case in manifest_cases if case.get("difficulty_bucket") == bucket]))
        for bucket, group in group_rows(manifest_cases, run_rows, "difficulty_bucket").items()
    }
    return {
        "name": name,
        "path": relpath(run_path),
        "summary_path": relpath(run_path / "summary.json" if run_path.is_dir() else run_path),
        "source_summary": {
            "case_count": summary.get("case_count"),
            "elapsed_seconds": summary.get("elapsed_seconds", summary.get("total_seconds")),
            "status_counts": summary.get("status_counts", summary.get("solve_status_counts")),
            "verify_counts": summary.get("verify_counts", summary.get("verify_status_counts")),
        },
        "overall": aggregate_rows(rows, len(manifest_cases)),
        "by_split": by_split,
        "by_difficulty": by_difficulty,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate AAAI 2026 experiment metrics.")
    parser.add_argument("--split-manifest", type=Path, required=True)
    parser.add_argument("--run", action="append", type=parse_run, required=True, help="NAME=RESULT_DIR_OR_SUMMARY_JSON")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    manifest = read_json(args.split_manifest)
    runs = {name: aggregate_run(name, path, manifest) for name, path in args.run}
    payload = {
        "schema_version": SCHEMA_VERSION,
        "split_manifest": relpath(args.split_manifest),
        "runs": runs,
    }
    write_json(args.out, payload)
    print(json.dumps({"out": str(args.out), "runs": list(runs)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

