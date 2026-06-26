#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path
from typing import Any

from schedule_solver import load_order, order_stats, solve_order
from verify_schedule import verify_solution


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_ORDERS_DIR = PROJECT_ROOT / "raw_orders"
SAMPLED_ORDER_DIR = Path(__file__).resolve().parent / "sampled_order"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "results" / "minute_sample_benchmark"

DEFAULT_SAMPLE_CASES = [
    ("easy", "SO-2022-04-0040-2.json"),
    ("easy", "SO-2023-05-0001-2.json"),
    ("easy", "SO-2021-11-0122-2.json"),
    ("medium", "SO-2023-06-0009-2.json"),
    ("medium", "SO-2021-02-0018-2.json"),
    ("medium", "SO-2022-02-0019-2.json"),
    ("hard", "SO-2025-04-0007-2.json"),
    ("hard", "SO-2022-06-0002-2.json"),
    ("hard", "SO-2021-04-0015-2.json"),
]

NON_VERIFIABLE_STATUSES = {
    "infeasible",
    "infeasible_proven",
    "invalid_input",
    "model_invalid",
    "no_solution_found",
    "time_limit",
    "solver_unavailable",
}


def ensure_default_samples() -> list[dict[str, str]]:
    SAMPLED_ORDER_DIR.mkdir(parents=True, exist_ok=True)
    copied: list[dict[str, str]] = []
    for level, filename in DEFAULT_SAMPLE_CASES:
        source = RAW_ORDERS_DIR / filename
        target = SAMPLED_ORDER_DIR / filename
        if not source.exists():
            raise FileNotFoundError(f"默认样本不存在: {source}")
        if not target.exists():
            shutil.copy2(source, target)
            copied.append({"level": level, "source": str(source), "target": str(target)})
    return copied


def sample_level_by_name() -> dict[str, str]:
    return {filename: level for level, filename in DEFAULT_SAMPLE_CASES}


def discover_samples(*, create_default_samples: bool) -> list[Path]:
    if create_default_samples:
        ensure_default_samples()
    samples = sorted(SAMPLED_ORDER_DIR.glob("*.json"))
    if samples:
        return samples
    return [RAW_ORDERS_DIR / filename for _level, filename in DEFAULT_SAMPLE_CASES]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def run_benchmark(
    *,
    output_dir: Path,
    time_limit_seconds: float,
    method: str,
    create_default_samples: bool,
) -> dict[str, Any]:
    copied_samples = ensure_default_samples() if create_default_samples else []
    selected_samples = discover_samples(create_default_samples=False)
    level_map = sample_level_by_name()
    solutions_dir = output_dir / "solutions"
    summary_rows: list[dict[str, Any]] = []

    benchmark_start = time.perf_counter()
    for sample_path in selected_samples:
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
        summary_rows.append(
            {
                "case_id": sample_path.stem,
                "level": level_map.get(sample_path.name, "custom"),
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
                "error_count": verify_result.get("error_count"),
            }
        )

    total_seconds = time.perf_counter() - benchmark_start
    solve_status_counts: dict[str, int] = {}
    verify_status_counts: dict[str, int] = {}
    for row in summary_rows:
        solve_status = str(row["solve_status"])
        verify_status = str(row["verify_status"])
        solve_status_counts[solve_status] = solve_status_counts.get(solve_status, 0) + 1
        verify_status_counts[verify_status] = verify_status_counts.get(verify_status, 0) + 1

    summary = {
        "sample_dir": str(SAMPLED_ORDER_DIR),
        "output_dir": str(output_dir),
        "time_limit_seconds": time_limit_seconds,
        "method": method,
        "total_seconds": total_seconds,
        "copied_samples": copied_samples,
        "solve_status_counts": solve_status_counts,
        "verify_status_counts": verify_status_counts,
        "cases": summary_rows,
    }
    write_json(output_dir / "summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the solver on 9 selected sampled orders.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--time-limit", type=float, default=600.0)
    parser.add_argument("--method", choices=["timed"], default="timed")
    parser.add_argument(
        "--create-default-samples",
        action="store_true",
        help="Copy the 9 selected raw_orders into solver/sampled_order before running.",
    )
    args = parser.parse_args()

    summary = run_benchmark(
        output_dir=args.output_dir,
        time_limit_seconds=args.time_limit,
        method=args.method,
        create_default_samples=args.create_default_samples,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
