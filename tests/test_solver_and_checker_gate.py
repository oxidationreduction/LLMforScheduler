from __future__ import annotations

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

