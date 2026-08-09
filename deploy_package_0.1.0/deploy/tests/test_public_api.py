from __future__ import annotations

import importlib
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest


DEPLOY_ROOT = Path(__file__).resolve().parents[1]
if str(DEPLOY_ROOT) not in sys.path:
    sys.path.insert(0, str(DEPLOY_ROOT))


@pytest.fixture
def api():
    module = importlib.import_module("llm_scheduler")
    for name in ("solve", "solve_json", "solve_legacy"):
        assert callable(getattr(module, name, None)), f"llm_scheduler.{name} must be public"
    return module


def english_request(
    *,
    quantity: int = 1,
    inventory: int = 0,
    duration_minutes: int = 10,
    equipment: list[str] | None = None,
    worker_days: list[int] | None = None,
    two_steps: bool = False,
) -> dict[str, Any]:
    steps = [
        {
            "step_index": 1,
            "name": "cut",
            "equipment": equipment or ["M1"],
            "duration_minutes": duration_minutes,
            "eligible_workers": ["W1"],
        }
    ]
    if two_steps:
        steps.append(
            {
                "step_index": 2,
                "name": "inspect",
                "equipment": [],
                "duration_minutes": 5,
                "eligible_workers": ["W1"],
            }
        )
    machine_names = sorted({machine for step in steps for machine in step["equipment"]})
    return {
        "schema_version": "1.0",
        "request_id": "request-1",
        "case_id": "english-small-case",
        "problem": {
            "orders": [{"product_id": "P1", "quantity": quantity, "due_day": 1}],
            "processes": {"P1": steps},
            "inventory": {"P1": inventory},
            "machines": [{"name": machine, "count": 1} for machine in machine_names],
            "worker_availability": {"W1": [1] if worker_days is None else worker_days},
        },
        "options": {"time_limit_seconds": 2},
    }


def chinese_payload(*, quantity: Any = 1, inventory: Any = 0) -> dict[str, Any]:
    return {
        "当前订单信息": [{"产品名称": "P1", "需求量": quantity, "期限": "1"}],
        "产品工序": {
            "P1工艺信息": [
                {
                    "序号": "1",
                    "工序": "cut",
                    "所用设备": ["M1"],
                    "耗时": "10",
                    "可选操作人员": ["W1"],
                }
            ]
        },
        "相关产品库存": {"P1": inventory},
        "可使用设备信息": [{"设备名称": "M1", "数量": "1"}],
        "每日可使用人员列表": {"W1": ["1"]},
    }


def assert_public_result(result: Mapping[str, Any]) -> None:
    assert isinstance(result, Mapping)
    assert result["schema_version"] == "1.0"
    assert "solution" in result
    assert "verification" in result
    assert json.dumps(result, allow_nan=False)

    def assert_no_path_keys(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                assert "path" not in str(key).lower()
                assert_no_path_keys(child)
        elif isinstance(value, list):
            for child in value:
                assert_no_path_keys(child)

    assert_no_path_keys(result)


def task_quantity(result: Mapping[str, Any]) -> int:
    return sum(
        task["quantity"]
        for day in result["solution"]["plan"]
        for task in day["tasks"]
    )


def test_solve_accepts_english_request_and_verifies_schedule(api):
    result = api.solve(english_request())

    assert_public_result(result)
    assert result["solution"]["status"] == "feasible"
    assert result["verification"]["status"] == "ok"
    assert result["schedule_accepted"] is True
    assert task_quantity(result) == 1


def test_solve_accepts_chinese_problem_and_solve_legacy_keeps_numeric_string_compatibility(api):
    payload = chinese_payload()
    wrapped = {
        "schema_version": "1.0",
        "case_id": "chinese-case",
        "problem": payload,
        "options": {"time_limit_seconds": 2},
    }

    for result in (api.solve(wrapped), api.solve_legacy(payload, case_id="legacy-case", time_limit_seconds=2)):
        assert_public_result(result)
        assert result["solution"]["status"] == "feasible"
        assert result["verification"]["status"] == "ok"


def test_inventory_deducts_finished_stock_before_scheduling(api):
    result = api.solve(english_request(quantity=3, inventory=2))

    assert_public_result(result)
    assert result["solution"]["status"] == "feasible"
    assert task_quantity(result) == 1


def test_zero_net_demand_returns_an_empty_verified_optimal_plan(api):
    result = api.solve(english_request(quantity=2, inventory=2))

    assert_public_result(result)
    assert result["solution"]["status"] == "optimal"
    assert result["solution"]["plan"] == []
    assert result["verification"]["status"] == "ok"
    assert result["schedule_accepted"] is True


def test_capacity_lower_bound_is_proven_infeasible(api):
    result = api.solve(english_request(quantity=2, duration_minutes=480))

    assert_public_result(result)
    assert result["solution"]["status"] == "infeasible_proven"
    assert result["solution"]["plan"] == []
    assert result["verification"]["status"] == "not_applicable"


def test_multi_machine_and_process_precedence_are_verified(api):
    result = api.solve(english_request(equipment=["M1", "M2"], two_steps=True))

    assert_public_result(result)
    assert result["verification"]["status"] == "ok"
    tasks = result["solution"]["plan"][0]["tasks"]
    assert tasks[0]["machines"] == ["M1", "M2"]
    assert tasks[1]["start_minute"] >= tasks[0]["end_minute"]


def test_unavailable_worker_has_no_accepted_schedule(api):
    result = api.solve(english_request(worker_days=[]))

    assert_public_result(result)
    assert result["solution"]["status"] in {"infeasible_proven", "no_solution_found"}
    assert result["schedule_accepted"] is False


def test_solve_json_rejects_malformed_json_and_non_finite_numbers(api):
    request = english_request()
    request["problem"]["processes"]["P1"][0]["duration_minutes"] = float("nan")
    for request_json in ("{", json.dumps(request, allow_nan=True)):
        result = json.loads(api.solve_json(request_json))
        assert_public_result(result)
        assert result["solution"]["status"] == "invalid_input"


@pytest.mark.parametrize("fixed_tasks", [[{"day": 1}], "not-a-list"])
def test_solve_rejects_nonempty_fixed_tasks(api, fixed_tasks):
    request = english_request()
    request["problem"]["fixed_tasks"] = fixed_tasks

    result = api.solve(request)

    assert_public_result(result)
    assert result["solution"]["status"] == "invalid_input"
