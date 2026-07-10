from __future__ import annotations

import pytest

from check_schedule import check_solution
from schedule_solver import load_order, net_required_by_product, solve_order, validate_order_static
from verify_schedule import verify_solution


def test_net_required_subtracts_initial_finished_inventory(tmp_path, minimal_order, write_order):
    order_path = write_order(tmp_path, minimal_order(quantity=3, inventory=2))
    order = load_order(order_path)

    assert net_required_by_product(order) == {"P1": 1}


def test_validate_order_static_rejects_unknown_machine(tmp_path, minimal_order, write_order):
    payload = minimal_order(equipment=["M9"])
    order_path = write_order(tmp_path, payload)
    order = load_order(order_path)

    assert any("未知设备" in error for error in validate_order_static(order))


def test_solve_order_zero_net_demand_returns_optimal_empty_plan(tmp_path, minimal_order, write_order):
    order_path = write_order(tmp_path, minimal_order(quantity=2, inventory=2))
    result = solve_order(load_order(order_path), time_limit_seconds=1)

    assert result["status"] == "optimal"
    assert result["plan"] == []


def test_solve_order_simple_two_step_case_verifies_ok(tmp_path, minimal_order, write_order, write_solution):
    order_path = write_order(tmp_path, minimal_order())
    result = solve_order(load_order(order_path), time_limit_seconds=2)
    solution_path = write_solution(tmp_path, result)

    verify = verify_solution(order_path, solution_path)

    assert result["status"] in {"feasible", "optimal"}
    assert verify["status"] == "ok"


def test_solve_order_single_dispatch_strategy_is_fixed(tmp_path, minimal_order, write_order):
    order_path = write_order(tmp_path, minimal_order())

    result = solve_order(
        load_order(order_path),
        time_limit_seconds=2,
        unit_strategy="round_robin_product",
        worker_strategy="name",
        day_strategy="forward",
    )

    assert result["status"] == "feasible"
    assert result["attempt_count"] == 1
    assert result["strategy"] == {
        "unit_strategy": "round_robin_product",
        "worker_strategy": "name",
        "day_strategy": "forward",
    }
    assert "greedy_failed_attempts" not in result


def test_solve_order_single_chunked_wavefront_records_chunk_size(tmp_path, minimal_order, write_order):
    order_path = write_order(tmp_path, minimal_order(quantity=2, due_day=2, worker_days={"W1": [1, 2], "W2": [1, 2]}))

    result = solve_order(
        load_order(order_path),
        time_limit_seconds=2,
        unit_strategy="chunked_wavefront_5",
    )

    assert result["status"] == "feasible"
    assert result["attempt_count"] == 1
    assert result["strategy"] == {
        "unit_strategy": "chunked_wavefront_5",
        "worker_strategy": "least_used",
        "day_strategy": "forward",
        "chunk_size": 5,
    }


def test_solve_order_cpsat_public_method_does_not_use_greedy(tmp_path, minimal_order, write_order):
    order_path = write_order(tmp_path, minimal_order())

    result = solve_order(load_order(order_path), time_limit_seconds=2, method="cpsat")

    assert result["status"] in {"feasible", "optimal"}
    assert result["solver_method"] in {"timed_cpsat", "timed_cpsat_batched"}
    assert result["solver_method"] != "timed_greedy"
    assert "greedy_failed_attempts" not in result


def test_solve_order_cpsat_rejects_greedy_strategy_override(tmp_path, minimal_order, write_order):
    order_path = write_order(tmp_path, minimal_order())

    with pytest.raises(ValueError, match="does not accept"):
        solve_order(load_order(order_path), time_limit_seconds=2, method="cpsat", unit_strategy="earliest_due")


def test_check_solution_rejects_failed_solver_status_before_verify(tmp_path, minimal_order, valid_solution, write_order, write_solution):
    order_path = write_order(tmp_path, minimal_order())
    solution = valid_solution()
    solution["status"] = "time_limit"
    solution_path = write_solution(tmp_path, solution)

    row = check_solution(
        order_path,
        solution_path,
        max_errors=10,
        require_feasible_status=True,
        check_machine_concurrency=True,
    )

    assert row["checker_status"] == "invalid"
    assert row["errors"] == ["solution status is not feasible: time_limit"]
