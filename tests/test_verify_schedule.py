from __future__ import annotations

from verify_schedule import verify_solution


def test_verify_accepts_valid_two_step_plan(tmp_path, minimal_order, valid_solution, write_order, write_solution):
    order_path = write_order(tmp_path, minimal_order())
    solution_path = write_solution(tmp_path, valid_solution())

    result = verify_solution(order_path, solution_path)

    assert result["status"] == "ok"
    assert result["error_count"] == 0


def test_verify_rejects_missing_required_simultaneous_machine(tmp_path, minimal_order, valid_solution, write_order, write_solution):
    order_path = write_order(tmp_path, minimal_order(equipment=["M1", "M2"]))
    solution_path = write_solution(tmp_path, valid_solution(machines=["M1"]))

    result = verify_solution(order_path, solution_path)

    assert result["status"] == "invalid"
    assert any("设备不匹配" in error for error in result["errors"])


def test_verify_rejects_step2_before_step1_output_ready(tmp_path, minimal_order, valid_solution, write_order, write_solution):
    order_path = write_order(tmp_path, minimal_order())
    solution = valid_solution()
    solution["plan"][0]["tasks"][1]["start_minute"] = 5
    solution["plan"][0]["tasks"][1]["end_minute"] = 10
    solution_path = write_solution(tmp_path, solution)

    result = verify_solution(order_path, solution_path)

    assert result["status"] == "invalid"
    assert any("超过前序已完成" in error or "时间重叠" in error for error in result["errors"])


def test_verify_rejects_machine_capacity_overlap(tmp_path, minimal_order, valid_solution, write_order, write_solution):
    order_path = write_order(tmp_path, minimal_order(quantity=2))
    solution = valid_solution()
    first_task = dict(solution["plan"][0]["tasks"][0])
    first_task["worker"] = "W2"
    solution["plan"][0]["tasks"].insert(1, first_task)
    solution["plan"][0]["tasks"][2]["quantity"] = 2
    solution["plan"][0]["tasks"][2]["start_minute"] = 10
    solution["plan"][0]["tasks"][2]["end_minute"] = 20
    solution["plan"][0]["tasks"][2]["duration_minutes"] = 10
    solution_path = write_solution(tmp_path, solution)

    result = verify_solution(order_path, solution_path)

    assert result["status"] == "invalid"
    assert result["machine_error_count"] >= 1

