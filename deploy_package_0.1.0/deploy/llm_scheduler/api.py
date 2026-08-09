"""Stable, JSON-compatible in-memory API for the scheduling engine."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from typing import Any

from .core.schedule_solver import parse_order, solve_order
from .core.verify_schedule import verify_solution


SCHEMA_VERSION = "1.0"
ENGINE_VERSION = "0.1.0"
DEFAULT_TIME_LIMIT_SECONDS = 120.0
_SCHEDULE_STATUSES = {"feasible", "optimal"}
_LEGACY_KEYS = {
    "当前订单信息",
    "产品工序",
    "相关产品库存",
    "可使用设备信息",
    "每日可使用人员列表",
}
_UNSUPPORTED_CONSTRAINT_KEYS = {
    "fixed_tasks",
    "locked_tasks",
    "existing_schedule",
    "machine_downtime",
    "machine_downtime_days",
    "machine_availability",
    "固定任务",
    "不可移动任务",
    "已有排期",
    "设备停机日",
}


class InputValidationError(ValueError):
    """Raised internally for a request that does not meet the public contract."""


def _as_mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise InputValidationError(f"{path} must be an object")
    return value


def _as_list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise InputValidationError(f"{path} must be an array")
    return value


def _required_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InputValidationError(f"{path} must be a non-empty string")
    return value.strip()


def _integer(value: Any, path: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise InputValidationError(f"{path} must be an integer")
    if minimum is not None and value < minimum:
        raise InputValidationError(f"{path} must be at least {minimum}")
    return value


def _number(value: Any, path: str, *, minimum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InputValidationError(f"{path} must be a number")
    parsed = float(value)
    if not math.isfinite(parsed):
        raise InputValidationError(f"{path} must be finite")
    if minimum is not None and parsed < minimum:
        raise InputValidationError(f"{path} must be at least {minimum:g}")
    return parsed


def _reject_unknown_fields(payload: Mapping[str, Any], allowed: set[str], path: str) -> None:
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise InputValidationError(f"{path} contains unsupported fields: {', '.join(unknown)}")


def _reject_unsupported_constraints(payload: Mapping[str, Any]) -> None:
    for key in _UNSUPPORTED_CONSTRAINT_KEYS:
        if key in payload and payload[key]:
            raise InputValidationError(f"{key} is not supported by deployment API v{SCHEMA_VERSION}")


def _time_limit(value: Any) -> float:
    return _number(value, "options.time_limit_seconds", minimum=0.000001)


def _normalize_options(value: Any) -> float:
    if value is None:
        return DEFAULT_TIME_LIMIT_SECONDS
    options = _as_mapping(value, "options")
    _reject_unknown_fields(options, {"time_limit_seconds"}, "options")
    return _time_limit(options.get("time_limit_seconds", DEFAULT_TIME_LIMIT_SECONDS))


def _normalize_canonical_problem(value: Any) -> dict[str, Any]:
    problem = _as_mapping(value, "problem")
    _reject_unsupported_constraints(problem)
    allowed = {
        "orders",
        "processes",
        "inventory",
        "machines",
        "worker_availability",
        *_UNSUPPORTED_CONSTRAINT_KEYS,
    }
    _reject_unknown_fields(problem, allowed, "problem")

    for required in ("orders", "processes", "inventory", "machines", "worker_availability"):
        if required not in problem:
            raise InputValidationError(f"problem.{required} is required")

    legacy_orders: list[dict[str, Any]] = []
    for index, item in enumerate(_as_list(problem["orders"], "problem.orders")):
        row = _as_mapping(item, f"problem.orders[{index}]")
        _reject_unknown_fields(row, {"product_id", "quantity", "due_day"}, f"problem.orders[{index}]")
        legacy_orders.append(
            {
                "产品名称": _required_string(row.get("product_id"), f"problem.orders[{index}].product_id"),
                "需求量": _integer(row.get("quantity"), f"problem.orders[{index}].quantity", minimum=0),
                "期限": _integer(row.get("due_day"), f"problem.orders[{index}].due_day", minimum=1),
            }
        )

    raw_processes = _as_mapping(problem["processes"], "problem.processes")
    legacy_processes: dict[str, list[dict[str, Any]]] = {}
    for product_id, raw_steps in raw_processes.items():
        product_name = _required_string(product_id, "problem.processes product id")
        steps = _as_list(raw_steps, f"problem.processes.{product_name}")
        seen_indices: set[int] = set()
        legacy_steps: list[dict[str, Any]] = []
        for step_pos, raw_step in enumerate(steps):
            step = _as_mapping(raw_step, f"problem.processes.{product_name}[{step_pos}]")
            _reject_unknown_fields(
                step,
                {"step_index", "name", "equipment", "duration_minutes", "eligible_workers"},
                f"problem.processes.{product_name}[{step_pos}]",
            )
            step_index = _integer(step.get("step_index"), f"problem.processes.{product_name}[{step_pos}].step_index", minimum=1)
            if step_index in seen_indices:
                raise InputValidationError(f"problem.processes.{product_name} has duplicate step_index {step_index}")
            seen_indices.add(step_index)
            equipment = _as_list(step.get("equipment"), f"problem.processes.{product_name}[{step_pos}].equipment")
            machine_names = [
                _required_string(machine, f"problem.processes.{product_name}[{step_pos}].equipment[{machine_index}]")
                for machine_index, machine in enumerate(equipment)
            ]
            if len(machine_names) != len(set(machine_names)):
                raise InputValidationError(f"problem.processes.{product_name}[{step_pos}].equipment contains duplicates")
            workers = _as_list(step.get("eligible_workers"), f"problem.processes.{product_name}[{step_pos}].eligible_workers")
            worker_names = [
                _required_string(worker, f"problem.processes.{product_name}[{step_pos}].eligible_workers[{worker_index}]")
                for worker_index, worker in enumerate(workers)
            ]
            if not worker_names:
                raise InputValidationError(f"problem.processes.{product_name}[{step_pos}].eligible_workers cannot be empty")
            legacy_steps.append(
                {
                    "序号": step_index,
                    "工序": _required_string(step.get("name"), f"problem.processes.{product_name}[{step_pos}].name"),
                    "所用设备": machine_names or ["无"],
                    "耗时": _number(step.get("duration_minutes"), f"problem.processes.{product_name}[{step_pos}].duration_minutes", minimum=0.0),
                    "可选操作人员": worker_names,
                }
            )
        if seen_indices and seen_indices != set(range(1, len(seen_indices) + 1)):
            raise InputValidationError(f"problem.processes.{product_name}.step_index must be consecutive from 1")
        legacy_processes[f"{product_name}工艺信息"] = legacy_steps

    raw_inventory = _as_mapping(problem["inventory"], "problem.inventory")
    inventory = {
        _required_string(product_id, "problem.inventory product id"): _integer(quantity, f"problem.inventory.{product_id}", minimum=0)
        for product_id, quantity in raw_inventory.items()
    }

    seen_machines: set[str] = set()
    machines: list[dict[str, Any]] = []
    for index, raw_machine in enumerate(_as_list(problem["machines"], "problem.machines")):
        machine = _as_mapping(raw_machine, f"problem.machines[{index}]")
        _reject_unknown_fields(machine, {"name", "count"}, f"problem.machines[{index}]")
        name = _required_string(machine.get("name"), f"problem.machines[{index}].name")
        if name in seen_machines:
            raise InputValidationError(f"problem.machines has duplicate machine {name}")
        seen_machines.add(name)
        machines.append({"设备名称": name, "数量": _integer(machine.get("count"), f"problem.machines[{index}].count", minimum=0)})

    raw_workers = _as_mapping(problem["worker_availability"], "problem.worker_availability")
    workers: dict[str, list[int]] = {}
    for worker, raw_days in raw_workers.items():
        worker_name = _required_string(worker, "problem.worker_availability worker")
        days = [
            _integer(day, f"problem.worker_availability.{worker_name}[{index}]", minimum=1)
            for index, day in enumerate(_as_list(raw_days, f"problem.worker_availability.{worker_name}"))
        ]
        workers[worker_name] = sorted(set(days))

    return {
        "当前订单信息": legacy_orders,
        "产品工序": legacy_processes,
        "相关产品库存": inventory,
        "可使用设备信息": machines,
        "每日可使用人员列表": workers,
    }


def _normalize_legacy_problem(value: Any) -> dict[str, Any]:
    problem = _as_mapping(value, "problem")
    _reject_unsupported_constraints(problem)
    return dict(problem)


def _is_legacy_problem(problem: Mapping[str, Any]) -> bool:
    return bool(set(problem) & _LEGACY_KEYS)


def _error_response(
    *,
    status: str,
    errors: list[str],
    case_id: str | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "engine_version": ENGINE_VERSION,
        "request_id": request_id,
        "case_id": case_id,
        "schedule_accepted": False,
        "solution": {
            "status": status,
            "solver_method": None,
            "solve_seconds": 0.0,
            "objective_value": None,
            "strategy": {},
            "summary": {},
            "task_count": 0,
            "errors": errors,
            "plan": [],
        },
        "verification": {
            "status": "not_applicable",
            "task_count": 0,
            "error_count": 0,
            "machine_error_count": 0,
            "machine_concurrency_checked": False,
            "errors": [],
        },
    }


def _public_solution(solution: Mapping[str, Any]) -> dict[str, Any]:
    plan = solution.get("plan", [])
    if not isinstance(plan, list):
        plan = []
    summary = solution.get("summary", {})
    if not isinstance(summary, Mapping):
        summary = {}
    summary_fields = (
        "product_count",
        "net_required_total",
        "step_count",
        "total_work_minutes",
        "max_due_day",
        "worker_count",
        "worker_day_count",
        "complexity_score",
    )
    errors = solution.get("errors", [])
    if not isinstance(errors, list):
        errors = [str(errors)]
    strategy = solution.get("strategy", {})
    if not isinstance(strategy, Mapping):
        strategy = {}
    return {
        "status": str(solution.get("status", "failed")),
        "solver_method": solution.get("solver_method"),
        "solve_seconds": float(solution.get("solve_seconds", 0.0)),
        "objective_value": solution.get("objective_value"),
        "strategy": dict(strategy),
        "summary": {field: summary[field] for field in summary_fields if field in summary},
        "task_count": sum(len(day.get("tasks", [])) for day in plan if isinstance(day, Mapping)),
        "errors": [str(error) for error in errors],
        "plan": plan,
    }


def _public_verification(verification: Mapping[str, Any]) -> dict[str, Any]:
    errors = verification.get("errors", [])
    if not isinstance(errors, list):
        errors = [str(errors)]
    return {
        "status": str(verification.get("status", "invalid")),
        "task_count": int(verification.get("task_count", 0)),
        "error_count": int(verification.get("error_count", 0)),
        "machine_error_count": int(verification.get("machine_error_count", 0)),
        "machine_concurrency_checked": bool(verification.get("machine_concurrency_checked", False)),
        "errors": [str(error) for error in errors],
    }


def _solve_payload(
    *,
    case_id: str,
    request_id: str | None,
    payload: Mapping[str, Any],
    time_limit_seconds: float,
) -> dict[str, Any]:
    order = parse_order(payload, case_id=case_id)
    raw_solution = solve_order(order, time_limit_seconds=time_limit_seconds, method="timed")
    public_solution = _public_solution(raw_solution)
    if public_solution["status"] in _SCHEDULE_STATUSES:
        public_verification = _public_verification(verify_solution(order, raw_solution))
    else:
        public_verification = {
            "status": "not_applicable",
            "task_count": public_solution["task_count"],
            "error_count": 0,
            "machine_error_count": 0,
            "machine_concurrency_checked": False,
            "errors": [],
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "engine_version": ENGINE_VERSION,
        "request_id": request_id,
        "case_id": case_id,
        "schedule_accepted": public_solution["status"] in _SCHEDULE_STATUSES and public_verification["status"] == "ok",
        "solution": public_solution,
        "verification": public_verification,
    }


def solve(request: Mapping[str, Any]) -> dict[str, Any]:
    """Solve one canonical or legacy scheduling request and verify any schedule."""

    case_id: str | None = None
    request_id: str | None = None
    try:
        envelope = _as_mapping(request, "request")
        _reject_unsupported_constraints(envelope)
        _reject_unknown_fields(
            envelope,
            {"schema_version", "request_id", "case_id", "problem", "options", *_UNSUPPORTED_CONSTRAINT_KEYS},
            "request",
        )
        if envelope.get("schema_version") != SCHEMA_VERSION:
            raise InputValidationError(f"schema_version must be {SCHEMA_VERSION!r}")
        case_id = _required_string(envelope.get("case_id"), "case_id")
        if "request_id" in envelope and envelope["request_id"] is not None:
            request_id = _required_string(envelope["request_id"], "request_id")
        problem = _as_mapping(envelope.get("problem"), "problem")
        time_limit_seconds = _normalize_options(envelope.get("options"))
        payload = _normalize_legacy_problem(problem) if _is_legacy_problem(problem) else _normalize_canonical_problem(problem)
        return _solve_payload(
            case_id=case_id,
            request_id=request_id,
            payload=payload,
            time_limit_seconds=time_limit_seconds,
        )
    except InputValidationError as exc:
        return _error_response(status="invalid_input", errors=[str(exc)], case_id=case_id, request_id=request_id)
    except Exception:
        return _error_response(status="failed", errors=["internal scheduling error"], case_id=case_id, request_id=request_id)


def solve_legacy(
    order_payload: Mapping[str, Any],
    *,
    case_id: str,
    time_limit_seconds: float = DEFAULT_TIME_LIMIT_SECONDS,
) -> dict[str, Any]:
    """Solve an existing Chinese order payload without writing any files."""

    try:
        normalized_case_id = _required_string(case_id, "case_id")
        payload = _normalize_legacy_problem(order_payload)
        return _solve_payload(
            case_id=normalized_case_id,
            request_id=None,
            payload=payload,
            time_limit_seconds=_time_limit(time_limit_seconds),
        )
    except InputValidationError as exc:
        return _error_response(status="invalid_input", errors=[str(exc)], case_id=case_id if isinstance(case_id, str) else None)
    except Exception:
        return _error_response(status="failed", errors=["internal scheduling error"], case_id=case_id if isinstance(case_id, str) else None)


def solve_json(request_json: str) -> str:
    """JSON-string convenience wrapper for :func:`solve`."""

    try:
        parsed = json.loads(request_json)
    except (TypeError, json.JSONDecodeError):
        result = _error_response(status="invalid_input", errors=["request_json must be valid JSON"])
    else:
        result = solve(parsed)
    return json.dumps(result, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
