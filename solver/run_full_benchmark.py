#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from schedule_solver import load_order, order_stats, solve_order
from verify_schedule import verify_solution


PROJECT_ROOT = Path(__file__).resolve().parents[1]
NON_VERIFIABLE_STATUSES = {
    "infeasible",
    "infeasible_proven",
    "invalid_input",
    "model_invalid",
    "no_solution_found",
    "time_limit",
    "solver_unavailable",
    "failed",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def relpath(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def resolve_path(path: Path) -> Path:
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def select_cases(manifest: dict[str, Any], case_ids: list[str] | None, limit: int | None) -> list[dict[str, Any]]:
    cases = list(manifest.get("cases", []))
    if case_ids:
        wanted = set(case_ids)
        cases = [case for case in cases if str(case.get("case_id")) in wanted]
        found = {str(case.get("case_id")) for case in cases}
        missing = sorted(wanted - found)
        if missing:
            raise ValueError(f"case_id not found in manifest: {missing}")
    if limit is not None:
        if limit <= 0:
            raise ValueError("--limit must be positive")
        cases = cases[:limit]
    return cases


def task_count(solution: dict[str, Any]) -> int:
    return sum(len(day.get("tasks", [])) for day in solution.get("plan", []) if isinstance(day, dict))


def non_verifiable_result(case_id: str, order_path: Path, solution_path: Path, solve_status: str) -> dict[str, Any]:
    return {
        "status": "not_applicable",
        "case_id": case_id,
        "input_path": relpath(order_path),
        "solution_path": relpath(solution_path),
        "task_count": 0,
        "error_count": 0,
        "machine_error_count": 0,
        "errors": [],
        "reason": f"no feasible solution to verify; solve_status={solve_status}",
    }


def count_by(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = row.get(key)
        if value is None:
            continue
        text = str(value)
        counts[text] = counts.get(text, 0) + 1
    return counts


def open_log(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    return path.open("a", encoding="utf-8")


def append_log(log_fh, message: str) -> None:
    log_fh.write(f"{now_iso()} {message}\n")
    log_fh.flush()


def ensure_new_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing output directory: {output_dir}")
    output_dir.mkdir(parents=True)


def write_status(output_dir: Path, payload: dict[str, Any]) -> None:
    payload["updated_at"] = now_iso()
    write_json(output_dir / "status.json", payload)


def run_benchmark(
    *,
    manifest_path: Path,
    output_dir: Path,
    time_limit_seconds: float,
    method: str,
    case_ids: list[str] | None,
    limit: int | None,
) -> dict[str, Any]:
    manifest = read_json(manifest_path)
    cases = select_cases(manifest, case_ids, limit)
    ensure_new_output_dir(output_dir)

    solutions_dir = output_dir / "solutions"
    run_manifest = {
        "source_manifest": relpath(manifest_path),
        "output_dir": relpath(output_dir),
        "time_limit_seconds": time_limit_seconds,
        "method": method,
        "case_count": len(cases),
        "case_ids": [str(case["case_id"]) for case in cases],
        "started_at": now_iso(),
    }
    write_json(output_dir / "manifest.json", run_manifest)

    status = {
        "state": "running",
        "output_dir": relpath(output_dir),
        "manifest": relpath(manifest_path),
        "case_count": len(cases),
        "completed_count": 0,
        "failed_count": 0,
        "started_at": run_manifest["started_at"],
        "current_case_id": None,
    }
    write_status(output_dir, status)

    rows: list[dict[str, Any]] = []
    started = time.perf_counter()
    log_path = output_dir / "run.log"
    with open_log(log_path) as log_fh:
        append_log(log_fh, f"start case_count={len(cases)} output_dir={relpath(output_dir)}")
        for index, case in enumerate(cases, start=1):
            case_id = str(case["case_id"])
            order_path = resolve_path(Path(str(case["order_path"])))
            solution_path = solutions_dir / f"{case_id}.solution.json"
            verify_path = solutions_dir / f"{case_id}.verify.json"
            case_started = time.perf_counter()

            status["current_case_id"] = case_id
            status["completed_count"] = index - 1
            write_status(output_dir, status)
            append_log(log_fh, f"case_start index={index}/{len(cases)} case_id={case_id}")

            try:
                order = load_order(order_path)
                stats = order_stats(order)
                solution = solve_order(order, time_limit_seconds=time_limit_seconds, method=method)
            except Exception as exc:  # pragma: no cover - defensive long-run guard.
                stats = {}
                solution = {
                    "case_id": case_id,
                    "input_path": relpath(order_path),
                    "status": "failed",
                    "solver_method": method,
                    "solve_seconds": time.perf_counter() - case_started,
                    "objective_value": None,
                    "summary": {},
                    "errors": [f"{type(exc).__name__}: {exc}"],
                    "plan": [],
                }

            write_json(solution_path, solution)
            solve_status = str(solution.get("status"))
            if solve_status in NON_VERIFIABLE_STATUSES:
                verify = non_verifiable_result(case_id, order_path, solution_path, solve_status)
            else:
                try:
                    verify = verify_solution(order_path, solution_path)
                except Exception as exc:  # pragma: no cover - defensive long-run guard.
                    verify = {
                        "status": "invalid",
                        "case_id": case_id,
                        "input_path": relpath(order_path),
                        "solution_path": relpath(solution_path),
                        "task_count": task_count(solution),
                        "error_count": 1,
                        "machine_error_count": 0,
                        "errors": [f"{type(exc).__name__}: {exc}"],
                    }
            write_json(verify_path, verify)

            row = {
                "case_id": case_id,
                "status": solve_status,
                "solve_status": solve_status,
                "method": solution.get("solver_method", method),
                "solver_method": solution.get("solver_method", method),
                "strategy": solution.get("strategy"),
                "attempt_count": solution.get("attempt_count"),
                "cp_sat_status": solution.get("cp_sat_status"),
                "solve_seconds": solution.get("solve_seconds"),
                "wall_seconds": time.perf_counter() - case_started,
                "task_count": task_count(solution),
                "operation_count": solution.get("operation_count"),
                "batched_operation_count": solution.get("batched_operation_count"),
                "batch_count": solution.get("batch_count"),
                "input_path": relpath(order_path),
                "solution_path": relpath(solution_path),
                "verify_path": relpath(verify_path),
                "verify_status": verify.get("status"),
                "verify_error_count": verify.get("error_count"),
                "machine_error_count": verify.get("machine_error_count"),
                "errors": list(solution.get("errors", []))[:5],
                "verify_errors": list(verify.get("errors", []))[:5],
                "product_count": stats.get("product_count"),
                "net_required_total": stats.get("net_required_total"),
                "step_count": stats.get("step_count"),
                "total_work_minutes": stats.get("total_work_minutes"),
                "max_due_day": stats.get("max_due_day"),
                "worker_count": stats.get("worker_count"),
                "worker_day_count": stats.get("worker_day_count"),
            }
            rows.append(row)

            status["completed_count"] = index
            status["failed_count"] = sum(1 for item in rows if item.get("status") == "failed")
            status["status_counts"] = count_by(rows, "status")
            status["verify_counts"] = count_by(rows, "verify_status")
            write_status(output_dir, status)
            append_log(
                log_fh,
                "case_done "
                f"index={index}/{len(cases)} case_id={case_id} "
                f"status={row['status']} verify={row['verify_status']} "
                f"wall_seconds={row['wall_seconds']:.6f}",
            )

        elapsed_seconds = time.perf_counter() - started
        status_counts = count_by(rows, "status")
        verify_counts = count_by(rows, "verify_status")
        not_solved_cases = [
            row["case_id"]
            for row in rows
            if row.get("status") in {"no_solution_found", "time_limit", "failed", "solver_unavailable"}
        ]
        infeasible_cases = [row["case_id"] for row in rows if row.get("status") == "infeasible_proven"]
        slowest_cases = sorted(
            (
                {
                    "case_id": row["case_id"],
                    "solve_seconds": row.get("solve_seconds"),
                    "wall_seconds": row.get("wall_seconds"),
                    "status": row.get("status"),
                    "verify_status": row.get("verify_status"),
                }
                for row in rows
            ),
            key=lambda row: float(row.get("wall_seconds") or 0.0),
            reverse=True,
        )[:20]
        summary = {
            "schema_version": "full_benchmark.v1",
            "source_manifest": relpath(manifest_path),
            "output_dir": relpath(output_dir),
            "case_count": len(rows),
            "expected_case_count": len(cases),
            "time_limit_seconds": time_limit_seconds,
            "method": method,
            "elapsed_seconds": elapsed_seconds,
            "status_counts": status_counts,
            "method_counts": count_by(rows, "method"),
            "verify_counts": verify_counts,
            "solved_and_verified_ok": verify_counts.get("ok", 0),
            "not_solved_cases": not_solved_cases,
            "infeasible_proven_cases": infeasible_cases,
            "slowest_cases": slowest_cases,
            "cases": rows,
        }
        write_json(output_dir / "summary.json", summary)

        status["state"] = "complete"
        status["completed_count"] = len(rows)
        status["finished_at"] = now_iso()
        status["elapsed_seconds"] = elapsed_seconds
        status["summary_path"] = relpath(output_dir / "summary.json")
        status["current_case_id"] = None
        write_status(output_dir, status)
        append_log(log_fh, f"complete elapsed_seconds={elapsed_seconds:.6f}")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the timed solver over manifest-listed raw orders.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--time-limit", type=float, default=120.0)
    parser.add_argument("--method", choices=["timed"], default="timed")
    parser.add_argument("--case-id", action="append", default=None, help="Restrict to one case; repeatable.")
    parser.add_argument("--limit", type=int, default=None, help="Run only the first N selected manifest cases.")
    args = parser.parse_args()

    summary = run_benchmark(
        manifest_path=resolve_path(args.manifest),
        output_dir=resolve_path(args.output_dir),
        time_limit_seconds=args.time_limit,
        method=args.method,
        case_ids=args.case_id,
        limit=args.limit,
    )
    print(
        json.dumps(
            {
                "output_dir": summary["output_dir"],
                "case_count": summary["case_count"],
                "status_counts": summary["status_counts"],
                "verify_counts": summary["verify_counts"],
                "elapsed_seconds": summary["elapsed_seconds"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"run_full_benchmark failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
