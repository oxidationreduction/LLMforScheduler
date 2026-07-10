#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aggregate_metrics import aggregate_run
from build_sft_data import order_summary
from common import NON_VERIFIABLE_STATUSES, REPO_ROOT, SCHEMA_VERSION, jsonl_rows, read_json, relpath, write_json, write_jsonl
from llm_tool_schema import TOOL_CALL_SCHEMA, parse_text, raw_text_from_row
from schedule_solver import load_order, order_stats, solve_order
from verify_schedule import verify_solution


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def selected_cases(manifest: dict[str, Any], split: str) -> list[dict[str, Any]]:
    return [case for case in manifest.get("cases", []) if str(case.get("split")) == split]


def count_by(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = row.get(key)
        if value is None:
            continue
        text = str(value)
        counts[text] = counts.get(text, 0) + 1
    return counts


def task_count(solution: dict[str, Any]) -> int:
    return sum(len(day.get("tasks", [])) for day in solution.get("plan", []) if isinstance(day, dict))


def write_status(output_dir: Path, payload: dict[str, Any]) -> None:
    payload["updated_at"] = now_iso()
    write_json(output_dir / "status.json", payload)


def append_log(output_dir: Path, message: str) -> None:
    with (output_dir / "run.log").open("a", encoding="utf-8") as f:
        f.write(f"{now_iso()} {message}\n")


def ensure_prepare_out(out: Path) -> None:
    if out.exists():
        raise FileExistsError(f"refusing to overwrite existing prompts file: {out}")


def ensure_execute_output_dir(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    blocked = [
        output_dir / "summary.json",
        output_dir / "metrics.json",
        output_dir / "parsed_tool_calls.jsonl",
        output_dir / "status.json",
        output_dir / "solutions",
    ]
    existing = [path for path in blocked if path.exists()]
    if existing:
        raise FileExistsError(f"refusing to overwrite existing E5 artifacts: {[str(path) for path in existing]}")


def make_prompt_row(case: dict[str, Any]) -> dict[str, Any]:
    case_id = str(case["case_id"])
    order_path = resolve_path(Path(str(case["order_path"])))
    payload = {
        "case_id": case_id,
        "order_summary": order_summary(order_path),
        "allowed_tools": TOOL_CALL_SCHEMA,
        "policy": {
            "return_only": "one strict JSON tool call",
            "final_schedule_source": "repository solver/verifier tools only",
            "forbidden": "do not output a schedule plan as the final answer",
        },
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "id": f"{case_id}:tool_agent",
        "case_id": case_id,
        "split": case.get("split"),
        "eval_groups": case.get("eval_groups", []),
        "messages": [
            {
                "role": "system",
                "content": "You are a verifier-backed scheduling tool agent. Return only one strict JSON tool call.",
            },
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
    }


def prepare(args: argparse.Namespace) -> None:
    manifest = read_json(args.split_manifest)
    cases = selected_cases(manifest, args.split)
    rows = [make_prompt_row(case) for case in cases]
    ensure_prepare_out(args.out)
    write_jsonl(args.out, rows)
    print(json.dumps({"out": str(args.out), "case_count": len(rows), "split": args.split}, ensure_ascii=False, indent=2))


def responses_by_case(path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for raw_row in jsonl_rows(path):
        parsed = parse_text(raw_text_from_row(raw_row))
        case_id = parsed.get("case_id")
        if isinstance(raw_row, dict) and raw_row.get("case_id"):
            case_id = raw_row["case_id"]
            parsed["case_id"] = str(case_id)
        if case_id:
            rows[str(case_id)] = {"raw_row": raw_row, "parsed": parsed}
    return rows


def non_verifiable_result(case_id: str, order_path: Path, solution_path: Path | None, solve_status: str) -> dict[str, Any]:
    return {
        "status": "not_applicable",
        "case_id": case_id,
        "input_path": relpath(order_path),
        "solution_path": relpath(solution_path) if solution_path else None,
        "task_count": 0,
        "error_count": 0,
        "machine_error_count": 0,
        "errors": [],
        "reason": f"no feasible solution to verify; solve_status={solve_status}",
    }


def no_final_schedule_row(
    case: dict[str, Any],
    parsed: dict[str, Any],
    *,
    reason: str,
    output_dir: Path,
) -> dict[str, Any]:
    case_id = str(case["case_id"])
    order_path = resolve_path(Path(str(case["order_path"])))
    return {
        "case_id": case_id,
        "split": case.get("split"),
        "eval_groups": case.get("eval_groups", []),
        "parse_status": parsed.get("parse_status"),
        "tool_call_ok": parsed.get("parse_status") == "ok",
        "tool_name": parsed.get("tool_name"),
        "selected_strategy": None,
        "llm_reason": None,
        "repair_attempt_count": 0,
        "repair_action": None,
        "status": "no_solution_found",
        "solve_status": "no_solution_found",
        "solver_method": None,
        "verify_status": "not_applicable",
        "solve_seconds": 0.0,
        "wall_seconds": 0.0,
        "task_count": 0,
        "input_path": relpath(order_path),
        "solution_path": None,
        "verify_path": None,
        "errors": [reason],
        "verify_errors": [],
    }


def execute_tool_call(
    case: dict[str, Any],
    parsed: dict[str, Any],
    *,
    output_dir: Path,
    time_limit_seconds: float,
) -> dict[str, Any]:
    case_id = str(case["case_id"])
    normalized = parsed.get("normalized_call")
    if parsed.get("parse_status") != "ok" or not isinstance(normalized, dict):
        return no_final_schedule_row(case, parsed, reason="LLM response is not a valid strict tool call", output_dir=output_dir)

    tool_name = str(normalized.get("tool_name"))
    arguments = normalized.get("arguments") if isinstance(normalized.get("arguments"), dict) else {}
    if tool_name in {"summarize_order", "verify_solution"}:
        return no_final_schedule_row(case, parsed, reason=f"{tool_name} did not request a final solver run", output_dir=output_dir)

    order_path = resolve_path(Path(str(case["order_path"])))
    solution_path = output_dir / "solutions" / f"{case_id}.solution.json"
    verify_path = output_dir / "solutions" / f"{case_id}.verify.json"
    case_started = time.perf_counter()
    selected_strategy = None
    try:
        order = load_order(order_path)
        stats = order_stats(order)
        if tool_name == "select_solver_strategy":
            selected_strategy = arguments.get("strategy")
            if not isinstance(selected_strategy, dict):
                raise ValueError("select_solver_strategy requires arguments.strategy")
            solution = solve_order(
                order,
                time_limit_seconds=time_limit_seconds,
                method="timed",
                unit_strategy=str(selected_strategy.get("unit_strategy")),
                worker_strategy=str(selected_strategy.get("worker_strategy", "least_used")),
                day_strategy=str(selected_strategy.get("day_strategy", "forward")),
            )
        elif tool_name == "solve_order":
            selected_strategy = arguments.get("strategy") if isinstance(arguments.get("strategy"), dict) else None
            solution = solve_order(
                order,
                time_limit_seconds=float(arguments.get("time_limit_seconds", time_limit_seconds)),
                method="timed",
                unit_strategy=selected_strategy.get("unit_strategy") if selected_strategy else None,
                worker_strategy=selected_strategy.get("worker_strategy", "least_used") if selected_strategy else "least_used",
                day_strategy=selected_strategy.get("day_strategy", "forward") if selected_strategy else "forward",
            )
        else:
            return no_final_schedule_row(case, parsed, reason=f"unsupported tool call: {tool_name}", output_dir=output_dir)
    except Exception as exc:  # pragma: no cover - defensive long-run guard.
        stats = {}
        solution = {
            "case_id": case_id,
            "input_path": relpath(order_path),
            "status": "failed",
            "solver_method": "tool_agent",
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

    repair_action = arguments.get("repair_action") or arguments.get("verifier_repair_action")
    return {
        "case_id": case_id,
        "split": case.get("split"),
        "eval_groups": case.get("eval_groups", []),
        "parse_status": parsed.get("parse_status"),
        "tool_call_ok": True,
        "tool_name": tool_name,
        "selected_strategy": selected_strategy,
        "llm_reason": normalized.get("reason") or arguments.get("reason"),
        "repair_attempt_count": 1 if normalized.get("retry_of") or repair_action else 0,
        "repair_action": repair_action,
        "status": solve_status,
        "solve_status": solve_status,
        "solver_method": solution.get("solver_method"),
        "verify_status": verify.get("status"),
        "solve_seconds": solution.get("solve_seconds"),
        "wall_seconds": time.perf_counter() - case_started,
        "task_count": task_count(solution),
        "input_path": relpath(order_path),
        "solution_path": relpath(solution_path),
        "verify_path": relpath(verify_path),
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


def execute(args: argparse.Namespace) -> None:
    manifest = read_json(args.split_manifest)
    cases = selected_cases(manifest, args.split)
    output_dir = resolve_path(args.output_dir)
    ensure_execute_output_dir(output_dir)
    started_at = now_iso()
    status = {
        "state": "running",
        "output_dir": relpath(output_dir),
        "split_manifest": relpath(args.split_manifest),
        "responses": relpath(args.responses),
        "split": args.split,
        "case_count": len(cases),
        "completed_count": 0,
        "failed_count": 0,
        "started_at": started_at,
        "current_case_id": None,
    }
    write_status(output_dir, status)
    append_log(output_dir, f"start case_count={len(cases)} responses={relpath(args.responses)}")

    response_rows = responses_by_case(args.responses)
    parsed_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    started = time.perf_counter()
    for index, case in enumerate(cases, start=1):
        case_id = str(case["case_id"])
        status["current_case_id"] = case_id
        status["completed_count"] = index - 1
        write_status(output_dir, status)
        parsed = response_rows.get(case_id, {}).get("parsed") or {
            "case_id": case_id,
            "raw_text": "",
            "parse_status": "missing",
            "tool_name": None,
            "arguments": None,
            "errors": ["missing LLM response"],
            "json_span": None,
            "normalized_call": None,
        }
        parsed_rows.append(parsed)
        row = execute_tool_call(case, parsed, output_dir=output_dir, time_limit_seconds=args.time_limit)
        summary_rows.append(row)
        status["completed_count"] = index
        status["failed_count"] = sum(1 for item in summary_rows if item.get("status") == "failed")
        status["status_counts"] = count_by(summary_rows, "status")
        status["verify_counts"] = count_by(summary_rows, "verify_status")
        write_status(output_dir, status)
        append_log(output_dir, f"case_done index={index}/{len(cases)} case_id={case_id} status={row['status']} verify={row['verify_status']}")

    elapsed_seconds = time.perf_counter() - started
    verify_counts = count_by(summary_rows, "verify_status")
    status_counts = count_by(summary_rows, "status")
    summary = {
        "schema_version": "llm_tool_agent.v1",
        "source_manifest": relpath(args.split_manifest),
        "responses": relpath(args.responses),
        "output_dir": relpath(output_dir),
        "case_count": len(summary_rows),
        "expected_case_count": len(cases),
        "time_limit_seconds": args.time_limit,
        "method": "llm_tool_agent",
        "split": args.split,
        "elapsed_seconds": elapsed_seconds,
        "status_counts": status_counts,
        "method_counts": count_by(summary_rows, "solver_method"),
        "verify_counts": verify_counts,
        "parse_status_counts": count_by(summary_rows, "parse_status"),
        "tool_call_ok_count": sum(1 for row in summary_rows if row.get("tool_call_ok") is True),
        "solved_and_verified_ok": verify_counts.get("ok", 0),
        "not_solved_cases": [
            row["case_id"]
            for row in summary_rows
            if row.get("status") in {"no_solution_found", "time_limit", "failed", "solver_unavailable"}
        ],
        "infeasible_proven_cases": [row["case_id"] for row in summary_rows if row.get("status") == "infeasible_proven"],
        "cases": summary_rows,
    }
    write_json(output_dir / "summary.json", summary)
    write_jsonl(output_dir / "parsed_tool_calls.jsonl", parsed_rows)
    metrics = {
        "schema_version": SCHEMA_VERSION,
        "split_manifest": relpath(args.split_manifest),
        "runs": {"e5_llm_tool_agent": aggregate_run("e5_llm_tool_agent", output_dir, manifest)},
    }
    write_json(output_dir / "metrics.json", metrics)

    status["state"] = "complete"
    status["completed_count"] = len(summary_rows)
    status["finished_at"] = now_iso()
    status["elapsed_seconds"] = elapsed_seconds
    status["summary_path"] = relpath(output_dir / "summary.json")
    status["metrics_path"] = relpath(output_dir / "metrics.json")
    status["current_case_id"] = None
    write_status(output_dir, status)
    append_log(output_dir, f"complete elapsed_seconds={elapsed_seconds:.6f}")
    print(json.dumps({"output_dir": relpath(output_dir), "case_count": len(summary_rows), "verify_counts": verify_counts}, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare or execute the AAAI LLM tool-agent JSONL harness.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--split-manifest", type=Path, required=True)
    prepare_parser.add_argument("--split", default="test")
    prepare_parser.add_argument("--out", type=Path, required=True)
    prepare_parser.set_defaults(func=prepare)

    execute_parser = subparsers.add_parser("execute")
    execute_parser.add_argument("--split-manifest", type=Path, required=True)
    execute_parser.add_argument("--responses", type=Path, required=True)
    execute_parser.add_argument("--output-dir", type=Path, required=True)
    execute_parser.add_argument("--split", default="test")
    execute_parser.add_argument("--time-limit", type=float, default=120.0)
    execute_parser.set_defaults(func=execute)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
