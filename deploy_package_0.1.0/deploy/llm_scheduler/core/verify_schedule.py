#!/usr/bin/env python3
from __future__ import annotations

import bisect
import math
from collections import defaultdict
from collections.abc import Mapping
from typing import Any

from .schedule_solver import (
    CP_SAT_DURATION_SCALE,
    DAY_TICKS,
    WORKER_DAY_MINUTES,
    OrderData,
    clean_text,
    due_requirements_by_product,
    is_no_machine,
    net_required_by_product,
    real_equipment,
    required_quantity_by_product,
    validate_order_static,
)


def _minute_to_tick(value: Any) -> int | None:
    try:
        return int(round(float(value) * CP_SAT_DURATION_SCALE))
    except (TypeError, ValueError):
        return None


def _absolute_tick(day: int, tick_in_day: int) -> int:
    return (int(day) - 1) * DAY_TICKS + int(tick_in_day)


def _insert_or_report_overlap(
    intervals: list[tuple[int, int, str]],
    start_tick: int,
    end_tick: int,
    label: str,
    *,
    commit: bool = True,
) -> str | None:
    if start_tick >= end_tick:
        return None
    probe = bisect.bisect_right(intervals, (start_tick, math.inf, "")) - 1
    if probe >= 0 and intervals[probe][1] > start_tick:
        return f"{label} 与 {intervals[probe][2]} 时间重叠"
    probe += 1
    if probe < len(intervals) and intervals[probe][0] < end_tick:
        return f"{label} 与 {intervals[probe][2]} 时间重叠"
    if commit:
        bisect.insort(intervals, (start_tick, end_tick, label))
    return None


def _insert_interval_on_any_copy(
    intervals_by_copy: list[list[tuple[int, int, str]]],
    start_tick: int,
    end_tick: int,
    label: str,
) -> str | None:
    if start_tick >= end_tick:
        return None
    for intervals in intervals_by_copy:
        overlap = _insert_or_report_overlap(intervals, start_tick, end_tick, label)
        if overlap is None:
            return None
    examples: list[str] = []
    for intervals in intervals_by_copy[:2]:
        for prev_start, prev_end, prev_label in intervals:
            if prev_start < end_tick and start_tick < prev_end:
                examples.append(
                    f"{prev_label} [{prev_start / CP_SAT_DURATION_SCALE:.3f}, "
                    f"{prev_end / CP_SAT_DURATION_SCALE:.3f}]"
                )
                break
    detail = "；".join(examples) if examples else "所有设备副本都被占用"
    return (
        f"{label} [{start_tick / CP_SAT_DURATION_SCALE:.3f}, "
        f"{end_tick / CP_SAT_DURATION_SCALE:.3f}] 与已有设备占用重叠：{detail}"
    )


def _machine_list(task: dict[str, Any]) -> list[str]:
    if isinstance(task.get("machines"), list):
        return [clean_text(machine) for machine in task["machines"] if clean_text(machine)]
    machine_value = task.get("machine")
    if machine_value is None:
        return []
    machine_text = clean_text(machine_value)
    if not machine_text or is_no_machine(machine_text):
        return []
    if "+" in machine_text:
        return [part.strip() for part in machine_text.split("+") if part.strip()]
    return [machine_text]


def _find_step(order: OrderData, product_id: str, task: dict[str, Any]):
    steps = order.processes.get(product_id, ())
    raw_step_index = task.get("step_index", task.get("process_index"))
    if raw_step_index not in (None, ""):
        try:
            step_index = int(raw_step_index)
        except (TypeError, ValueError):
            step_index = None
        if step_index is not None:
            for pos, step in enumerate(steps):
                if step.step_index == step_index:
                    return pos, step
    process_name = clean_text(task.get("process", task.get("process_name", "")))
    for pos, step in enumerate(steps):
        if step.name == process_name:
            return pos, step
    return None, None


def verify_solution(
    order: OrderData,
    solution: Mapping[str, Any],
    *,
    check_machine_concurrency: bool = True,
) -> dict[str, Any]:
    plan = solution.get("plan", solution)
    errors: list[str] = []
    machine_errors: list[str] = []

    static_errors = validate_order_static(order)
    errors.extend(static_errors)
    if not isinstance(plan, list):
        return {
            "status": "invalid",
            "case_id": order.case_id,
            "error_count": len(errors) + 1,
            "errors": errors + ["plan 必须是列表"],
        }

    net_required = net_required_by_product(order)
    required_by_product = required_quantity_by_product(order)
    known_machines = {machine for machine, count in order.machines.items() if count > 0}
    worker_usage: dict[tuple[str, int], float] = defaultdict(float)
    output_by_day: dict[str, dict[int, dict[int, int]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    final_output_by_day: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    total_by_product_step: dict[tuple[str, int], int] = defaultdict(int)
    produced_events: dict[tuple[str, int], list[tuple[int, int]]] = defaultdict(list)
    consumed_events: dict[tuple[str, int], list[tuple[int, int]]] = defaultdict(list)
    worker_intervals: dict[tuple[str, int], list[tuple[int, int, str]]] = defaultdict(list)
    machine_intervals: dict[tuple[str, int], list[tuple[int, int, str]]] = defaultdict(list)
    task_count = 0

    for day_block in plan:
        if not isinstance(day_block, dict):
            errors.append(f"day block 不是对象: {day_block!r}")
            continue
        try:
            day = int(day_block.get("day", 0))
        except (TypeError, ValueError):
            errors.append(f"day 不是整数: {day_block.get('day')!r}")
            continue
        if day < 1:
            errors.append(f"day 必须大于等于 1: {day}")
            continue
        tasks = day_block.get("tasks", [])
        if not isinstance(tasks, list):
            errors.append(f"第 {day} 天 tasks 必须是列表")
            continue
        previous_sort_key: tuple[int, int, int] | None = None

        for task_index, task in enumerate(tasks):
            task_count += 1
            if not isinstance(task, dict):
                errors.append(f"第 {day} 天第 {task_index} 个 task 不是对象")
                continue
            product_id = clean_text(task.get("material", task.get("product_id", "")))
            if not product_id:
                errors.append(f"第 {day} 天第 {task_index} 个 task 缺少 material/product_id")
                continue
            if product_id not in required_by_product:
                errors.append(f"第 {day} 天产品 {product_id} 不在订单需求中")
            step_pos, step = _find_step(order, product_id, task)
            if step is None or step_pos is None:
                errors.append(f"第 {day} 天产品 {product_id} 找不到工序 {task.get('process')!r}")
                continue
            try:
                quantity = int(task.get("quantity", 0))
            except (TypeError, ValueError):
                quantity = 0
            if quantity <= 0:
                errors.append(f"第 {day} 天产品 {product_id} 工序 {step.name} quantity 必须大于 0")
                continue

            start_tick = _minute_to_tick(task.get("start_minute"))
            end_tick = _minute_to_tick(task.get("end_minute"))
            if start_tick is None or end_tick is None:
                errors.append(f"第 {day} 天产品 {product_id} 工序 {step.name} 缺少合法 start_minute/end_minute")
                continue
            if start_tick < 0 or end_tick > DAY_TICKS:
                errors.append(
                    f"第 {day} 天产品 {product_id} 工序 {step.name} 时间不在 0-480 分钟内："
                    f"{task.get('start_minute')} -> {task.get('end_minute')}"
                )
            expected_duration_ticks = _minute_to_tick(step.duration_minutes * quantity)
            if expected_duration_ticks is None:
                expected_duration_ticks = -1
            if expected_duration_ticks > 0 and start_tick >= end_tick:
                errors.append(f"第 {day} 天产品 {product_id} 工序 {step.name} 非零耗时任务必须 start < end")
            if expected_duration_ticks == 0 and start_tick != end_tick:
                errors.append(f"第 {day} 天产品 {product_id} 工序 {step.name} 零耗时任务必须 start == end")
            sort_key = (start_tick, end_tick, task_index)
            if previous_sort_key is not None and sort_key < previous_sort_key:
                errors.append(f"第 {day} 天 tasks 未按 start_minute/end_minute 升序排列")
            previous_sort_key = sort_key

            worker = clean_text(task.get("worker", ""))
            if not worker:
                errors.append(f"第 {day} 天产品 {product_id} 工序 {step.name} 缺少 worker")
            elif worker not in step.eligible_workers:
                errors.append(f"第 {day} 天工人 {worker} 不能执行产品 {product_id} 工序 {step.name}")
            elif day not in set(order.workers.get(worker, ())):
                errors.append(f"第 {day} 天工人 {worker} 不可用")

            expected_machines = set(real_equipment(step.equipment))
            actual_machines = set(_machine_list(task))
            if actual_machines != expected_machines:
                errors.append(
                    f"第 {day} 天产品 {product_id} 工序 {step.name} 设备不匹配："
                    f"应同时占用 {sorted(expected_machines)}，实际 {sorted(actual_machines)}"
                )
            for machine in actual_machines:
                if machine not in known_machines:
                    errors.append(f"第 {day} 天使用未知设备 {machine}")

            expected_duration = step.duration_minutes * quantity
            duration = task.get("duration_minutes", expected_duration)
            try:
                duration_float = float(duration)
            except (TypeError, ValueError):
                duration_float = -1.0
            if not math.isclose(duration_float, expected_duration, rel_tol=1e-9, abs_tol=1e-6):
                errors.append(
                    f"第 {day} 天产品 {product_id} 工序 {step.name} 总工时不正确："
                    f"应为 {expected_duration:.6f}，实际 {duration}"
                )
            duration_ticks = end_tick - start_tick
            if duration_ticks != expected_duration_ticks:
                errors.append(
                    f"第 {day} 天产品 {product_id} 工序 {step.name} 起止时间跨度不正确："
                    f"应为 {expected_duration_ticks / CP_SAT_DURATION_SCALE:.6f} 分钟，"
                    f"实际 {duration_ticks / CP_SAT_DURATION_SCALE:.6f} 分钟"
                )

            label = f"第{day}天#{task_index} {product_id}/{step.name}/{worker}"
            if worker and expected_duration_ticks > 0:
                overlap = _insert_or_report_overlap(
                    worker_intervals[(worker, day)],
                    start_tick,
                    end_tick,
                    label,
                )
                if overlap:
                    errors.append(f"第 {day} 天工人 {worker} {overlap}")
            if check_machine_concurrency and expected_duration_ticks > 0:
                for machine in actual_machines:
                    if machine in known_machines:
                        machine_intervals[(machine, day)].append((start_tick, end_tick, label))

            if worker:
                worker_usage[(worker, day)] += expected_duration
            output_by_day[product_id][step_pos][day] += quantity
            total_by_product_step[(product_id, step_pos)] += quantity
            start_abs = _absolute_tick(day, start_tick)
            unit_duration_ticks = _minute_to_tick(step.duration_minutes)
            if unit_duration_ticks is None:
                unit_duration_ticks = expected_duration_ticks // quantity if quantity else 0
            if unit_duration_ticks == 0:
                produced_events[(product_id, step_pos)].append((start_abs, quantity))
                if step_pos > 0:
                    consumed_events[(product_id, step_pos)].append((start_abs, quantity))
            else:
                for unit_offset in range(quantity):
                    unit_start_abs = start_abs + unit_offset * unit_duration_ticks
                    unit_finish_abs = unit_start_abs + unit_duration_ticks
                    produced_events[(product_id, step_pos)].append((unit_finish_abs, 1))
                    if step_pos > 0:
                        consumed_events[(product_id, step_pos)].append((unit_start_abs, 1))
            if step_pos == len(order.processes.get(product_id, ())) - 1:
                final_output_by_day[product_id][day] += quantity

    for (worker, day), used_minutes in sorted(worker_usage.items()):
        if used_minutes > WORKER_DAY_MINUTES + 1e-6:
            errors.append(
                f"第 {day} 天工人 {worker} 超出 480 分钟：{used_minutes:.6f}"
            )

    if check_machine_concurrency:
        for (machine, day), intervals in sorted(machine_intervals.items()):
            count = max(int(order.machines.get(machine, 0)), 0)
            if count <= 0:
                continue
            intervals_by_copy: list[list[tuple[int, int, str]]] = [[] for _ in range(count)]
            for start_tick, end_tick, label in sorted(intervals):
                overlap = _insert_interval_on_any_copy(intervals_by_copy, start_tick, end_tick, label)
                if overlap:
                    machine_errors.append(f"第 {day} 天设备 {machine} 超出 {count} 台并发容量：{overlap}")

    for product_id, required_quantity in sorted(net_required.items()):
        if required_quantity <= 0:
            continue
        steps = order.processes.get(product_id, ())
        for step_pos, _step in enumerate(steps):
            total = total_by_product_step.get((product_id, step_pos), 0)
            if total != required_quantity:
                errors.append(
                    f"产品 {product_id} 第 {step_pos + 1} 道工序总量不等于净需求："
                    f"{total} != {required_quantity}"
                )

        for step_pos in range(1, len(steps)):
            prev_events = sorted(produced_events.get((product_id, step_pos - 1), []))
            current_consumes = sorted(consumed_events.get((product_id, step_pos), []))
            prev_index = 0
            cumulative_prev = 0
            cumulative_consumed = 0
            for consume_time, consume_quantity in current_consumes:
                while prev_index < len(prev_events) and prev_events[prev_index][0] <= consume_time:
                    cumulative_prev += prev_events[prev_index][1]
                    prev_index += 1
                cumulative_consumed += consume_quantity
                if cumulative_consumed > cumulative_prev:
                    consume_day = consume_time // DAY_TICKS + 1
                    consume_minute = (consume_time % DAY_TICKS) / CP_SAT_DURATION_SCALE
                    errors.append(
                        f"产品 {product_id} 第 {step_pos + 1} 道工序在第 {consume_day} 天 "
                        f"{consume_minute:.6f} 分钟累计消耗 {cumulative_consumed}，"
                        f"超过前序已完成 {cumulative_prev}"
                    )

    for product_id, due_rows in due_requirements_by_product(order).items():
        cumulative_final = 0
        completed_items = sorted(final_output_by_day.get(product_id, {}).items())
        completed_index = 0
        for due_day, required_by_due in due_rows:
            while completed_index < len(completed_items) and completed_items[completed_index][0] <= due_day:
                cumulative_final += completed_items[completed_index][1]
                completed_index += 1
            if cumulative_final < required_by_due:
                errors.append(
                    f"产品 {product_id} 截止第 {due_day} 天净完成 {cumulative_final}，"
                    f"净需求 {required_by_due}"
                )

    errors.extend(machine_errors)
    return {
        "status": "ok" if not errors else "invalid",
        "case_id": order.case_id,
        "task_count": task_count,
        "error_count": len(errors),
        "machine_error_count": len(machine_errors),
        "machine_concurrency_checked": check_machine_concurrency,
        "errors": errors,
    }
