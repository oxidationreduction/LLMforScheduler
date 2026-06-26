#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path
from typing import Any

from run_sample_benchmark import DEFAULT_SAMPLE_CASES, NON_VERIFIABLE_STATUSES, RAW_ORDERS_DIR, write_json
from schedule_solver import load_order, order_stats, solve_order, validate_order_static
from verify_schedule import verify_solution


EXTRA_SAMPLE_DIR = Path(__file__).resolve().parent / "extra_sampled_order"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "results" / "minute_extra50_benchmark"


def existing_default_case_ids() -> set[str]:
    return {Path(filename).stem for _level, filename in DEFAULT_SAMPLE_CASES}


def difficulty_label(rank: int, count: int) -> str:
    if count <= 0:
        return "custom"
    fraction = rank / max(count - 1, 1)
    if fraction < 1 / 3:
        return "easy_extra"
    if fraction < 2 / 3:
        return "medium_extra"
    return "hard_extra"


def select_extra_samples(sample_count: int) -> list[dict[str, Any]]:
    excluded = existing_default_case_ids()
    candidates: list[dict[str, Any]] = []

    for path in sorted(RAW_ORDERS_DIR.glob("*.json")):
        order = load_order(path)
        if order.case_id in excluded:
            continue
        if validate_order_static(order):
            continue
        stats = order_stats(order)
        if stats["product_count"] <= 0 or stats["net_required_total"] <= 0:
            continue
        worker_capacity = float(stats["worker_day_count"]) * 480.0
        load_ratio = float(stats["total_work_minutes"]) / worker_capacity if worker_capacity > 0 else float("inf")
        row = {
            "case_id": order.case_id,
            "filename": path.name,
            "source_path": str(path),
            **stats,
            "worker_capacity_minutes": worker_capacity,
            "load_ratio": load_ratio,
        }
        candidates.append(row)

    if sample_count <= 0:
        return []
    if not candidates:
        return []

    candidates.sort(key=lambda row: (float(row["complexity_score"]), str(row["case_id"])))
    if sample_count >= len(candidates):
        selected = list(candidates)
    else:
        selected_indices: list[int] = []
        seen: set[int] = set()
        for offset in range(sample_count):
            index = round(offset * (len(candidates) - 1) / (sample_count - 1))
            while index in seen and index + 1 < len(candidates):
                index += 1
            while index in seen and index > 0:
                index -= 1
            seen.add(index)
            selected_indices.append(index)
        selected = [candidates[index] for index in sorted(selected_indices)]

    for rank, row in enumerate(selected):
        row["level"] = difficulty_label(rank, len(selected))
        row["selection_rank"] = rank + 1
    return selected


def materialize_extra_samples(selected: list[dict[str, Any]]) -> list[dict[str, str]]:
    EXTRA_SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    selected_names = {str(row["filename"]) for row in selected}
    for existing in EXTRA_SAMPLE_DIR.glob("*.json"):
        if existing.name not in selected_names:
            existing.unlink()

    copied: list[dict[str, str]] = []
    for row in selected:
        source = Path(str(row["source_path"]))
        target = EXTRA_SAMPLE_DIR / str(row["filename"])
        if not target.exists():
            shutil.copy2(source, target)
            copied.append({"source": str(source), "target": str(target)})
    return copied


def run_extra_benchmark(
    *,
    sample_count: int,
    output_dir: Path,
    time_limit_seconds: float,
    method: str,
) -> dict[str, Any]:
    selected = select_extra_samples(sample_count)
    copied = materialize_extra_samples(selected)
    level_by_case = {str(row["case_id"]): str(row["level"]) for row in selected}

    solutions_dir = output_dir / "solutions"
    write_json(output_dir / "selected_samples.json", selected)

    rows: list[dict[str, Any]] = []
    start = time.perf_counter()
    for sample_path in sorted(EXTRA_SAMPLE_DIR.glob("*.json")):
        order = load_order(sample_path)
        solve_result = solve_order(order, time_limit_seconds=time_limit_seconds, method=method)
        solution_path = solutions_dir / f"{sample_path.stem}.solution.json"
        write_json(solution_path, solve_result)

        if solve_result.get("status") in NON_VERIFIABLE_STATUSES:
            verify_result = {
                "status": "not_applicable",
                "case_id": order.case_id,
                "input_path": str(sample_path),
                "solution_path": str(solution_path),
                "task_count": 0,
                "error_count": 0,
                "errors": [],
                "reason": f"no feasible solution to verify; solve_status={solve_result.get('status')}",
            }
        else:
            verify_result = verify_solution(sample_path, solution_path)
        verify_path = solutions_dir / f"{sample_path.stem}.verify.json"
        write_json(verify_path, verify_result)

        stats = order_stats(order)
        rows.append(
            {
                "case_id": sample_path.stem,
                "level": level_by_case.get(sample_path.stem, "extra"),
                "input_path": str(sample_path),
                "solution_path": str(solution_path),
                "verify_path": str(verify_path),
                "solve_status": solve_result.get("status"),
                "solver_method": solve_result.get("solver_method"),
                "cp_sat_status": solve_result.get("cp_sat_status"),
                "verify_status": verify_result.get("status"),
                "solve_seconds": solve_result.get("solve_seconds"),
                "task_count": sum(len(day.get("tasks", [])) for day in solve_result.get("plan", [])),
                "product_count": stats["product_count"],
                "net_required_total": stats["net_required_total"],
                "step_count": stats["step_count"],
                "total_work_minutes": stats["total_work_minutes"],
                "max_due_day": stats["max_due_day"],
                "worker_day_count": stats["worker_day_count"],
                "load_ratio": (
                    float(stats["total_work_minutes"]) / (float(stats["worker_day_count"]) * 480.0)
                    if stats["worker_day_count"]
                    else None
                ),
                "error_count": verify_result.get("error_count"),
            }
        )

    total_seconds = time.perf_counter() - start
    status_counts: dict[str, int] = {}
    verify_counts: dict[str, int] = {}
    for row in rows:
        status_counts[str(row["solve_status"])] = status_counts.get(str(row["solve_status"]), 0) + 1
        verify_counts[str(row["verify_status"])] = verify_counts.get(str(row["verify_status"]), 0) + 1

    summary = {
        "sample_dir": str(EXTRA_SAMPLE_DIR),
        "output_dir": str(output_dir),
        "sample_count": len(selected),
        "time_limit_seconds": time_limit_seconds,
        "method": method,
        "total_seconds": total_seconds,
        "copied_samples": copied,
        "solve_status_counts": status_counts,
        "verify_status_counts": verify_counts,
        "cases": rows,
    }
    write_json(output_dir / "summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run minute-level benchmark on 50 extra raw_orders samples.")
    parser.add_argument("--sample-count", type=int, default=50)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--time-limit", type=float, default=600.0)
    parser.add_argument("--method", choices=["timed"], default="timed")
    args = parser.parse_args()

    summary = run_extra_benchmark(
        sample_count=args.sample_count,
        output_dir=args.output_dir,
        time_limit_seconds=args.time_limit,
        method=args.method,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
