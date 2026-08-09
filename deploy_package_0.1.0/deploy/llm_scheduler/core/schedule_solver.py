#!/usr/bin/env python3
from __future__ import annotations

import bisect
import math
import os
import time
from dataclasses import dataclass
from itertools import combinations
from typing import Any


try:
    from ortools.sat.python import cp_model
except ImportError:  # pragma: no cover - exercised only when ortools is not installed.
    cp_model = None


NO_MACHINE_VALUES = {"", "无", "無", "none", "null", "n/a", "na", "?"}
NO_MACHINE_TOKENS = {value.lower() for value in NO_MACHINE_VALUES}
WORKER_DAY_MINUTES = 480.0
CP_SAT_DURATION_SCALE = 1000
DAY_TICKS = int(round(WORKER_DAY_MINUTES * CP_SAT_DURATION_SCALE))


@dataclass(frozen=True)
class OrderItem:
    product_id: str
    quantity: int
    due_day: int


@dataclass(frozen=True)
class ProcessStep:
    step_index: int
    name: str
    equipment: tuple[str, ...]
    duration_minutes: float
    eligible_workers: tuple[str, ...]


@dataclass(frozen=True)
class OrderData:
    case_id: str
    orders: tuple[OrderItem, ...]
    processes: dict[str, tuple[ProcessStep, ...]]
    initial_inventory: dict[str, int]
    machines: dict[str, int]
    workers: dict[str, tuple[int, ...]]
    schema_errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class TimedPlacement:
    day: int
    start_tick: int
    end_tick: int
    worker: str
    machine_resources: tuple[tuple[Any, ...], ...] = ()


class SolverInputError(ValueError):
    pass


def clean_text(value: Any) -> str:
    return str(value).strip()


def is_no_machine(value: Any) -> bool:
    return clean_text(value).lower() in NO_MACHINE_TOKENS


def real_equipment(equipment: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(machine for machine in equipment if not is_no_machine(machine))


def product_id_from_process_key(key: Any) -> str:
    text = clean_text(key)
    if text.endswith("工艺信息"):
        return text[: -len("工艺信息")]
    return text


def _list_field(errors: list[str], path: str, value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    errors.append(f"{path} 必须是列表，实际为 {type(value).__name__}")
    return []


def _dict_field(errors: list[str], path: str, value: Any) -> dict[Any, Any]:
    if isinstance(value, dict):
        return value
    errors.append(f"{path} 必须是对象，实际为 {type(value).__name__}")
    return {}


def _parse_int_field(
    errors: list[str],
    path: str,
    value: Any,
    *,
    minimum: int | None = None,
) -> int:
    if isinstance(value, bool):
        errors.append(f"{path} 必须是整数，实际为布尔值")
        return 0
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        errors.append(f"{path} 必须是整数，实际为 {value!r}")
        return 0
    if minimum is not None and parsed < minimum:
        errors.append(f"{path} 必须大于等于 {minimum}，实际为 {parsed}")
    return parsed


def _parse_float_field(
    errors: list[str],
    path: str,
    value: Any,
    *,
    minimum: float | None = None,
) -> float:
    if isinstance(value, bool):
        errors.append(f"{path} 必须是数字，实际为布尔值")
        return 0.0
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        errors.append(f"{path} 必须是数字，实际为 {value!r}")
        return 0.0
    if not math.isfinite(parsed):
        errors.append(f"{path} 必须是有限数字，实际为 {value!r}")
        return 0.0
    if minimum is not None and parsed < minimum:
        errors.append(f"{path} 必须大于等于 {minimum:g}，实际为 {parsed:g}")
    return parsed


def _string_list_field(errors: list[str], path: str, value: Any) -> tuple[str, ...]:
    items = _list_field(errors, path, value)
    result = tuple(clean_text(item) for item in items if clean_text(item))
    if not result:
        errors.append(f"{path} 不能为空")
    return result


def parse_order(raw_json: Any, *, case_id: str) -> OrderData:
    errors: list[str] = []
    if not isinstance(raw_json, dict):
        return OrderData(
            case_id=case_id,
            orders=(),
            processes={},
            initial_inventory={},
            machines={},
            workers={},
            schema_errors=(f"顶层 JSON 必须是对象，实际为 {type(raw_json).__name__}",),
        )
    raw = raw_json

    order_rows: list[OrderItem] = []
    for row_index, row in enumerate(_list_field(errors, "当前订单信息", raw.get("当前订单信息"))):
        if not isinstance(row, dict):
            errors.append(f"当前订单信息[{row_index}] 必须是对象")
            continue
        product_id = clean_text(row.get("产品名称", ""))
        if not product_id:
            errors.append(f"当前订单信息[{row_index}].产品名称 不能为空")
            continue
        order_rows.append(
            OrderItem(
                product_id=product_id,
                quantity=_parse_int_field(errors, f"当前订单信息[{row_index}].需求量", row.get("需求量"), minimum=0),
                due_day=_parse_int_field(errors, f"当前订单信息[{row_index}].期限", row.get("期限"), minimum=1),
            )
        )
    orders = tuple(order_rows)

    processes: dict[str, tuple[ProcessStep, ...]] = {}
    for raw_product_id, raw_steps in _dict_field(errors, "产品工序", raw.get("产品工序")).items():
        product_id = product_id_from_process_key(raw_product_id)
        if not product_id:
            errors.append("产品工序 包含空产品 ID")
            continue
        steps = []
        for step_index, raw_step in enumerate(_list_field(errors, f"产品工序[{product_id}]", raw_steps)):
            if not isinstance(raw_step, dict):
                errors.append(f"产品工序[{product_id}][{step_index}] 必须是对象")
                continue
            step_name = clean_text(raw_step.get("工序", ""))
            if not step_name:
                errors.append(f"产品工序[{product_id}][{step_index}].工序 不能为空")
            steps.append(
                ProcessStep(
                    step_index=_parse_int_field(
                        errors,
                        f"产品工序[{product_id}][{step_index}].序号",
                        raw_step.get("序号"),
                        minimum=1,
                    ),
                    name=step_name,
                    equipment=_string_list_field(errors, f"产品工序[{product_id}][{step_index}].所用设备", raw_step.get("所用设备")),
                    duration_minutes=_parse_float_field(
                        errors,
                        f"产品工序[{product_id}][{step_index}].耗时",
                        raw_step.get("耗时"),
                        minimum=0.0,
                    ),
                    eligible_workers=_string_list_field(
                        errors,
                        f"产品工序[{product_id}][{step_index}].可选操作人员",
                        raw_step.get("可选操作人员"),
                    ),
                )
            )
        processes[product_id] = tuple(sorted(steps, key=lambda step: step.step_index))

    inventory = {
        clean_text(product_id): _parse_int_field(errors, f"相关产品库存[{clean_text(product_id)}]", quantity, minimum=0)
        for product_id, quantity in _dict_field(errors, "相关产品库存", raw.get("相关产品库存")).items()
        if clean_text(product_id)
    }
    machines: dict[str, int] = {}
    for row_index, row in enumerate(_list_field(errors, "可使用设备信息", raw.get("可使用设备信息"))):
        if not isinstance(row, dict):
            errors.append(f"可使用设备信息[{row_index}] 必须是对象")
            continue
        machine_name = clean_text(row.get("设备名称", ""))
        if not machine_name:
            errors.append(f"可使用设备信息[{row_index}].设备名称 不能为空")
            continue
        machines[machine_name] = _parse_int_field(
            errors,
            f"可使用设备信息[{row_index}].数量",
            row.get("数量"),
            minimum=0,
        )

    workers: dict[str, tuple[int, ...]] = {}
    for worker, raw_days in _dict_field(errors, "每日可使用人员列表", raw.get("每日可使用人员列表")).items():
        worker_name = clean_text(worker)
        if not worker_name:
            errors.append("每日可使用人员列表 包含空工人姓名")
            continue
        days = []
        for day_index, day in enumerate(_list_field(errors, f"每日可使用人员列表[{worker_name}]", raw_days)):
            days.append(
                _parse_int_field(
                    errors,
                    f"每日可使用人员列表[{worker_name}][{day_index}]",
                    day,
                    minimum=1,
                )
            )
        workers[worker_name] = tuple(days)

    return OrderData(
        case_id=case_id,
        orders=orders,
        processes=processes,
        initial_inventory=inventory,
        machines=machines,
        workers=workers,
        schema_errors=tuple(errors),
    )


def required_quantity_by_product(order: OrderData) -> dict[str, int]:
    required: dict[str, int] = {}
    for item in order.orders:
        required[item.product_id] = required.get(item.product_id, 0) + item.quantity
    return required


def net_required_by_product(order: OrderData) -> dict[str, int]:
    required = required_quantity_by_product(order)
    return {
        product_id: max(quantity - max(order.initial_inventory.get(product_id, 0), 0), 0)
        for product_id, quantity in required.items()
    }


def due_requirements_by_product(order: OrderData) -> dict[str, list[tuple[int, int]]]:
    by_product: dict[str, dict[int, int]] = {}
    for item in order.orders:
        due_map = by_product.setdefault(item.product_id, {})
        due_map[item.due_day] = due_map.get(item.due_day, 0) + item.quantity

    result: dict[str, list[tuple[int, int]]] = {}
    for product_id, due_map in by_product.items():
        initial_ready = max(order.initial_inventory.get(product_id, 0), 0)
        cumulative = 0
        rows = []
        for due_day in sorted(due_map):
            cumulative += due_map[due_day]
            rows.append((due_day, max(cumulative - initial_ready, 0)))
        result[product_id] = rows
    return result


def max_due_day(order: OrderData) -> int:
    return max((item.due_day for item in order.orders), default=0)


def validate_order_static(order: OrderData) -> list[str]:
    errors: list[str] = list(order.schema_errors)
    if errors:
        return errors
    known_machines = {name for name, count in order.machines.items() if count > 0}
    known_workers = set(order.workers)
    for product_id, net_required in net_required_by_product(order).items():
        if net_required <= 0:
            continue
        steps = order.processes.get(product_id)
        if not steps:
            errors.append(f"产品 {product_id} 缺少工序定义")
            continue
        for step in steps:
            if step.duration_minutes < 0:
                errors.append(f"产品 {product_id} 工序 {step.step_index} 耗时为负数")
            for machine in real_equipment(step.equipment):
                if machine not in known_machines:
                    errors.append(f"产品 {product_id} 工序 {step.step_index} 需要未知设备 {machine}")
            if not step.eligible_workers:
                errors.append(f"产品 {product_id} 工序 {step.step_index} 缺少可选操作人员")
            for worker in step.eligible_workers:
                if worker not in known_workers:
                    errors.append(f"产品 {product_id} 工序 {step.step_index} 引用未知工人 {worker}")
    return errors


def order_stats(order: OrderData) -> dict[str, Any]:
    net_required = net_required_by_product(order)
    active_products = [product for product, quantity in net_required.items() if quantity > 0]
    step_count = sum(len(order.processes.get(product, ())) for product in active_products)
    total_work = 0.0
    for product in active_products:
        for step in order.processes.get(product, ()):
            total_work += step.duration_minutes * net_required[product]
    worker_days = sum(len(days) for days in order.workers.values())
    return {
        "case_id": order.case_id,
        "product_count": len(active_products),
        "net_required_total": sum(net_required[product] for product in active_products),
        "step_count": step_count,
        "total_work_minutes": total_work,
        "max_due_day": max_due_day(order),
        "worker_count": len(order.workers),
        "worker_day_count": worker_days,
        "complexity_score": total_work + 250.0 * step_count + 100.0 * len(active_products),
    }


def _duration_ticks(minutes: float) -> int:
    return int(round(float(minutes) * CP_SAT_DURATION_SCALE))


def _ticks_to_minutes(ticks: int) -> float:
    return round(float(ticks) / CP_SAT_DURATION_SCALE, 6)


def _absolute_tick(day: int, tick_in_day: int) -> int:
    return (int(day) - 1) * DAY_TICKS + int(tick_in_day)


def _day_from_absolute_tick(absolute_tick: int) -> int:
    return int(absolute_tick) // DAY_TICKS + 1


def _tick_in_day(absolute_tick: int) -> int:
    return int(absolute_tick) % DAY_TICKS


def _resource_worker(worker: str) -> tuple[str, str]:
    return ("worker", worker)


def _resource_machine(machine: str, copy_index: int) -> tuple[str, str, int]:
    return ("machine", machine, int(copy_index))


def _required_machines(step: ProcessStep) -> tuple[str, ...]:
    return tuple(dict.fromkeys(real_equipment(step.equipment)))


def _machine_resource_options(order: OrderData, step: ProcessStep) -> tuple[tuple[tuple[Any, ...], ...], ...] | None:
    options: list[tuple[tuple[Any, ...], ...]] = []
    for machine in _required_machines(step):
        count = max(int(order.machines.get(machine, 0)), 0)
        if count <= 0:
            return None
        options.append(tuple(_resource_machine(machine, copy_index) for copy_index in range(count)))
    return tuple(options)


def _machine_resource_combinations(
    options: tuple[tuple[tuple[Any, ...], ...], ...],
) -> list[tuple[tuple[Any, ...], ...]]:
    if not options:
        return [()]
    combinations_by_machine: list[tuple[tuple[Any, ...], ...]] = [()]
    for machine_options in options:
        combinations_by_machine = [
            (*prefix, machine_resource)
            for prefix in combinations_by_machine
            for machine_resource in machine_options
        ]
    return combinations_by_machine


def _first_overlap_end(intervals: list[tuple[int, int]], start: int, end: int) -> int | None:
    if start >= end:
        return None
    probe = bisect.bisect_right(intervals, (start, math.inf)) - 1
    if probe >= 0 and intervals[probe][1] > start:
        return intervals[probe][1]
    probe += 1
    if probe < len(intervals) and intervals[probe][0] < end:
        return intervals[probe][1]
    return None


def _find_common_slot(
    calendars: dict[tuple[Any, ...], dict[int, list[tuple[int, int]]]],
    resources: tuple[tuple[Any, ...], ...],
    *,
    day: int,
    earliest_tick: int,
    duration_ticks: int,
) -> int | None:
    earliest_tick = max(0, int(earliest_tick))
    duration_ticks = max(0, int(duration_ticks))
    if duration_ticks == 0:
        return earliest_tick if earliest_tick <= DAY_TICKS else None
    start = earliest_tick
    while start + duration_ticks <= DAY_TICKS:
        end = start + duration_ticks
        bumped_to: int | None = None
        for resource in resources:
            intervals = calendars.get(resource, {}).get(day, [])
            overlap_end = _first_overlap_end(intervals, start, end)
            if overlap_end is not None:
                bumped_to = max(bumped_to or overlap_end, overlap_end)
        if bumped_to is None:
            return start
        if bumped_to <= start:
            bumped_to = start + 1
        start = bumped_to
    return None


def _insert_interval(
    calendars: dict[tuple[Any, ...], dict[int, list[tuple[int, int]]]],
    resource: tuple[Any, ...],
    day: int,
    start_tick: int,
    end_tick: int,
) -> None:
    if start_tick >= end_tick:
        return
    intervals = calendars.setdefault(resource, {}).setdefault(day, [])
    bisect.insort(intervals, (int(start_tick), int(end_tick)))


def _find_timed_placement(
    order: OrderData,
    calendars: dict[tuple[Any, ...], dict[int, list[tuple[int, int]]]],
    worker_usage: dict[tuple[str, int], int],
    *,
    product_id: str,
    step_pos: int,
    ready_abs_tick: int,
    due_day: int,
    worker_strategy: str = "least_used",
    day_strategy: str = "forward",
    latest_end_abs_tick: int | None = None,
) -> TimedPlacement | None:
    step = order.processes[product_id][step_pos]
    duration_ticks = _duration_ticks(step.duration_minutes)
    if duration_ticks > DAY_TICKS:
        return None

    first_day = max(1, _day_from_absolute_tick(ready_abs_tick))
    due_day = max(1, int(due_day))
    latest_end = int(latest_end_abs_tick) if latest_end_abs_tick is not None else due_day * DAY_TICKS
    if ready_abs_tick + duration_ticks > latest_end:
        return None
    worker_available_days = {worker: set(order.workers.get(worker, ())) for worker in step.eligible_workers}
    machine_options = _machine_resource_options(order, step)
    if machine_options is None:
        return None
    machine_combinations = _machine_resource_combinations(machine_options)

    best: tuple[int, int, str, tuple[tuple[Any, ...], ...]] | None = None
    day_range: list[int]
    if day_strategy == "backward":
        day_range = list(range(due_day, first_day - 1, -1))
    else:
        day_range = list(range(first_day, due_day + 1))

    for day in day_range:
        day_start_abs = (day - 1) * DAY_TICKS
        earliest_tick = max(0, ready_abs_tick - day_start_abs)
        latest_tick = min(DAY_TICKS, latest_end - day_start_abs)
        if duration_ticks > 0 and earliest_tick >= DAY_TICKS:
            continue
        if duration_ticks == 0 and earliest_tick > DAY_TICKS:
            continue
        if earliest_tick + duration_ticks > latest_tick:
            continue

        workers = [
            worker
            for worker in step.eligible_workers
            if day in worker_available_days.get(worker, set())
        ]
        if worker_strategy == "most_used":
            workers.sort(key=lambda worker: (-worker_usage.get((worker, day), 0), worker))
        elif worker_strategy == "name":
            workers.sort()
        else:
            workers.sort(key=lambda worker: (worker_usage.get((worker, day), 0), worker))
        for worker in workers:
            worker_resource = _resource_worker(worker)
            for machine_resources in machine_combinations:
                start_tick = _find_common_slot(
                    calendars,
                    (worker_resource, *machine_resources),
                    day=day,
                    earliest_tick=earliest_tick,
                    duration_ticks=duration_ticks,
                )
                if start_tick is None:
                    continue
                absolute_start = _absolute_tick(day, start_tick)
                if absolute_start + duration_ticks > latest_end:
                    continue
                candidate = (
                    absolute_start,
                    worker_usage.get((worker, day), 0),
                    worker,
                    machine_resources,
                )
                if best is None or candidate < best:
                    best = candidate
        if best is not None and _day_from_absolute_tick(best[0]) == day:
            break

    if best is None:
        return None
    absolute_start, _usage, worker, machine_resources = best
    day = _day_from_absolute_tick(absolute_start)
    start_tick = _tick_in_day(absolute_start)
    end_tick = start_tick + duration_ticks
    return TimedPlacement(
        day=day,
        start_tick=start_tick,
        end_tick=end_tick,
        worker=worker,
        machine_resources=machine_resources,
    )


def _reserve_timed_placement(
    calendars: dict[tuple[Any, ...], dict[int, list[tuple[int, int]]]],
    worker_usage: dict[tuple[str, int], int],
    placement: TimedPlacement,
    *,
    duration_ticks: int,
) -> None:
    worker_resource = _resource_worker(placement.worker)
    _insert_interval(calendars, worker_resource, placement.day, placement.start_tick, placement.end_tick)
    for machine_resource in placement.machine_resources:
        _insert_interval(calendars, machine_resource, placement.day, placement.start_tick, placement.end_tick)
    worker_usage[(placement.worker, placement.day)] = worker_usage.get((placement.worker, placement.day), 0) + duration_ticks


def _timed_records_to_plan(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not records:
        return []

    records = sorted(
        records,
        key=lambda item: (
            int(item["day"]),
            int(item["start_tick"]),
            int(item["end_tick"]),
            str(item["material"]),
            int(item["step_index"]),
            str(item["worker"]),
            tuple(item["machines"]),
        ),
    )
    merged: list[dict[str, Any]] = []
    for record in records:
        key = (
            record["day"],
            record["worker"],
            tuple(record["machines"]),
            record["material"],
            record["process"],
            record["step_index"],
            record["unit_duration_ticks"],
        )
        previous = merged[-1] if merged else None
        if previous is not None:
            previous_key = (
                previous["day"],
                previous["worker"],
                tuple(previous["machines"]),
                previous["material"],
                previous["process"],
                previous["step_index"],
                previous["unit_duration_ticks"],
            )
            contiguous = (
                record["unit_duration_ticks"] == 0
                and previous["start_tick"] == record["start_tick"]
                and previous["end_tick"] == record["end_tick"]
            ) or (
                record["unit_duration_ticks"] > 0
                and previous["end_tick"] == record["start_tick"]
            )
            if previous_key == key and contiguous:
                previous["end_tick"] = record["end_tick"]
                previous["quantity"] += int(record["quantity"])
                previous["duration_ticks"] += record["duration_ticks"]
                continue
        merged.append(dict(record))

    tasks_by_day: dict[int, list[dict[str, Any]]] = {}
    for item in merged:
        machines = list(item["machines"])
        task = {
            "start_minute": _ticks_to_minutes(int(item["start_tick"])),
            "end_minute": _ticks_to_minutes(int(item["end_tick"])),
            "worker": item["worker"],
            "machines": machines,
            "machine": "无" if not machines else "+".join(machines),
            "material": item["material"],
            "process": item["process"],
            "step_index": int(item["step_index"]),
            "quantity": int(item["quantity"]),
            "unit_duration_minutes": item["unit_duration_minutes"],
            "duration_minutes": _ticks_to_minutes(int(item["duration_ticks"])),
        }
        tasks_by_day.setdefault(int(item["day"]), []).append(task)

    return [
        {
            "day": day,
            "tasks": sorted(
                tasks,
                key=lambda item: (
                    float(item["start_minute"]),
                    float(item["end_minute"]),
                    str(item["material"]),
                    int(item["step_index"]),
                    str(item["worker"]),
                ),
            ),
        }
        for day, tasks in sorted(tasks_by_day.items())
    ]


def _net_due_batches(order: OrderData) -> list[tuple[str, int, int]]:
    batches: list[tuple[str, int, int]] = []
    for product_id, due_rows in due_requirements_by_product(order).items():
        previous_required = 0
        for due_day, cumulative_required in due_rows:
            quantity = max(int(cumulative_required) - previous_required, 0)
            previous_required = int(cumulative_required)
            if quantity > 0:
                batches.append((product_id, int(due_day), quantity))
    return batches


def _worker_capacity_until(order: OrderData, workers: frozenset[str], absolute_tick: int) -> int:
    if absolute_tick <= 0:
        return 0
    day = absolute_tick // DAY_TICKS + 1
    tick = absolute_tick % DAY_TICKS
    capacity = 0
    for worker in workers:
        for available_day in order.workers.get(worker, ()):
            if available_day < day:
                capacity += DAY_TICKS
            elif available_day == day:
                capacity += tick
    return capacity


def _worker_subset_capacity_errors(order: OrderData, *, max_errors: int = 10) -> list[str]:
    workers = tuple(sorted(order.workers))
    if not workers:
        return []

    items: list[tuple[frozenset[str], int, int, str, int, str]] = []
    errors: list[str] = []
    for product_id, due_day, quantity in _net_due_batches(order):
        steps = order.processes.get(product_id, ())
        for step_pos, step in enumerate(steps):
            duration_ticks = _duration_ticks(step.duration_minutes)
            if duration_ticks <= 0:
                continue
            eligible_workers = frozenset(worker for worker in step.eligible_workers if worker in order.workers)
            if not eligible_workers:
                continue
            remaining_after_ticks = _remaining_route_ticks(order, product_id, step_pos + 1)
            latest_end = int(due_day) * DAY_TICKS - remaining_after_ticks
            demand_ticks = int(quantity) * duration_ticks
            if latest_end < duration_ticks:
                errors.append(
                    f"产品 {product_id} 第 {step.step_index} 道工序 {step.name} "
                    "无法在期限前为后续工序留出最短加工时间"
                )
                if len(errors) >= max_errors:
                    return errors
                continue
            items.append((eligible_workers, latest_end, demand_ticks, product_id, step.step_index, step.name))

    if len(workers) <= 16:
        worker_subsets = [
            frozenset(subset)
            for subset_size in range(1, len(workers) + 1)
            for subset in combinations(workers, subset_size)
        ]
    else:
        worker_subsets = sorted({item[0] for item in items}, key=lambda subset: (len(subset), tuple(sorted(subset))))

    violations: list[tuple[int, int, frozenset[str], int]] = []
    for worker_subset in worker_subsets:
        relevant = [item for item in items if item[0].issubset(worker_subset)]
        if not relevant:
            continue
        for latest_end in sorted({item[1] for item in relevant}):
            demand_ticks = sum(item[2] for item in relevant if item[1] <= latest_end)
            capacity_ticks = _worker_capacity_until(order, worker_subset, latest_end)
            if demand_ticks > capacity_ticks:
                violations.append((demand_ticks - capacity_ticks, demand_ticks, worker_subset, latest_end))
                break

    for shortage_ticks, demand_ticks, worker_subset, latest_end in sorted(violations, reverse=True)[:max_errors]:
        errors.append(
            "人员集合时间窗容量不足："
            f"[{', '.join(sorted(worker_subset))}] 在第 {_day_from_absolute_tick(latest_end)} 天 "
            f"{_ticks_to_minutes(_tick_in_day(latest_end)):.3f} 分钟前可用 "
            f"{_ticks_to_minutes(demand_ticks - shortage_ticks):.3f} 分钟，"
            f"但必须完成 {_ticks_to_minutes(demand_ticks):.3f} 分钟，"
            f"缺口 {_ticks_to_minutes(shortage_ticks):.3f} 分钟"
        )
    return errors


def _basic_capacity_errors(order: OrderData) -> list[str]:
    horizon = max_due_day(order)
    if horizon <= 0:
        return []
    net_required = net_required_by_product(order)
    total_work_ticks = 0
    machine_work_ticks: dict[str, int] = {}
    errors: list[str] = []
    for product_id, quantity in net_required.items():
        if quantity <= 0:
            continue
        for step in order.processes.get(product_id, ()):
            step_ticks = _duration_ticks(step.duration_minutes) * int(quantity)
            total_work_ticks += step_ticks
            for machine in _required_machines(step):
                machine_work_ticks[machine] = machine_work_ticks.get(machine, 0) + step_ticks
            if _duration_ticks(step.duration_minutes) > DAY_TICKS:
                errors.append(
                    f"产品 {product_id} 第 {step.step_index} 道工序单件耗时超过工人单日 480 分钟"
                )

    worker_capacity_ticks = 0
    for days in order.workers.values():
        worker_capacity_ticks += sum(1 for day in days if 1 <= day <= horizon) * DAY_TICKS

    if total_work_ticks > worker_capacity_ticks:
        errors.append(
            "总工时超过全部可用工人工时："
            f"{_ticks_to_minutes(total_work_ticks):.6f} > {_ticks_to_minutes(worker_capacity_ticks):.6f}"
        )
    for machine, demand_ticks in sorted(machine_work_ticks.items()):
        capacity_ticks = max(int(order.machines.get(machine, 0)), 0) * horizon * DAY_TICKS
        if demand_ticks > capacity_ticks:
            errors.append(
                f"设备 {machine} 总工时超过可用容量："
                f"{_ticks_to_minutes(demand_ticks):.6f} > {_ticks_to_minutes(capacity_ticks):.6f}"
            )
    errors.extend(_worker_subset_capacity_errors(order))
    return errors


def _max_machine_load_ratio(order: OrderData) -> float:
    horizon = max_due_day(order)
    if horizon <= 0:
        return 0.0
    machine_work_ticks: dict[str, int] = {}
    for product_id, quantity in net_required_by_product(order).items():
        if quantity <= 0:
            continue
        for step in order.processes.get(product_id, ()):
            step_ticks = _duration_ticks(step.duration_minutes) * int(quantity)
            for machine in _required_machines(step):
                machine_work_ticks[machine] = machine_work_ticks.get(machine, 0) + step_ticks
    max_ratio = 0.0
    for machine, demand_ticks in machine_work_ticks.items():
        capacity_ticks = max(int(order.machines.get(machine, 0)), 0) * horizon * DAY_TICKS
        if capacity_ticks > 0:
            max_ratio = max(max_ratio, demand_ticks / capacity_ticks)
    return max_ratio


def _empty_solution(
    order: OrderData,
    status: str,
    start_time: float,
    errors: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "case_id": order.case_id,
        "status": status,
        "solve_seconds": time.perf_counter() - start_time,
        "objective_value": None,
        "summary": order_stats(order),
        "errors": list(errors or []),
        "plan": [],
    }


def _strategy_config(unit_strategy: str, worker_strategy: str, day_strategy: str) -> dict[str, Any]:
    strategy: dict[str, Any] = {
        "unit_strategy": unit_strategy,
        "worker_strategy": worker_strategy,
        "day_strategy": day_strategy,
    }
    if unit_strategy.startswith("chunked_wavefront_"):
        strategy["chunk_size"] = _parse_chunked_wavefront_strategy(unit_strategy)
    return strategy


def _validate_timed_strategy(unit_strategy: str, worker_strategy: str, day_strategy: str) -> None:
    known_units = {
        "earliest_due",
        "round_robin_product",
        "largest_route_work",
        "smallest_route_work",
        "interleaved_slack",
        "interleaved_ready",
        "interleaved_depth",
    }
    if unit_strategy not in known_units and not unit_strategy.startswith("chunked_wavefront_"):
        raise ValueError(f"unknown unit_strategy: {unit_strategy}")
    if worker_strategy not in {"least_used", "most_used", "name"}:
        raise ValueError(f"unknown worker_strategy: {worker_strategy}")
    if day_strategy not in {"forward", "backward"}:
        raise ValueError(f"unknown day_strategy: {day_strategy}")


def _unit_specs_for_strategy(order: OrderData, strategy: str) -> list[tuple[int, str, int]]:
    unit_specs: list[tuple[int, str, int]] = []
    for product_id, due_rows in due_requirements_by_product(order).items():
        previous_required = 0
        unit_index = 0
        for due_day, cumulative_required in due_rows:
            batch_quantity = max(int(cumulative_required) - previous_required, 0)
            previous_required = int(cumulative_required)
            for _ in range(batch_quantity):
                unit_index += 1
                unit_specs.append((int(due_day), str(product_id), unit_index))
    if strategy == "round_robin_product":
        by_group: dict[tuple[int, str], list[tuple[int, str, int]]] = {}
        for item in unit_specs:
            by_group.setdefault((item[0], item[1]), []).append(item)
        reordered: list[tuple[int, str, int]] = []
        for due_day in sorted({item[0] for item in unit_specs}):
            groups = [
                items
                for (group_due, _product_id), items in sorted(by_group.items())
                if group_due == due_day
            ]
            max_len = max((len(items) for items in groups), default=0)
            for index in range(max_len):
                for items in groups:
                    if index < len(items):
                        reordered.append(items[index])
        return reordered

    route_work = {
        product_id: sum(step.duration_minutes for step in order.processes.get(product_id, ()))
        for _due_day, product_id, _unit_index in unit_specs
    }
    if strategy == "largest_route_work":
        unit_specs.sort(key=lambda item: (item[0], -route_work.get(item[1], 0.0), item[1], item[2]))
    elif strategy == "smallest_route_work":
        unit_specs.sort(key=lambda item: (item[0], route_work.get(item[1], 0.0), item[1], item[2]))
    else:
        unit_specs.sort(key=lambda item: (item[0], item[1], item[2]))
    return unit_specs


def _remaining_route_ticks(order: OrderData, product_id: str, step_pos: int) -> int:
    return sum(_duration_ticks(step.duration_minutes) for step in order.processes.get(product_id, ())[step_pos:])


def _chunked_unit_specs(order: OrderData, chunk_size: int) -> list[list[tuple[int, str, int]]]:
    unit_specs = _unit_specs_for_strategy(order, "earliest_due")
    chunk_size = max(1, int(chunk_size))
    return [unit_specs[index : index + chunk_size] for index in range(0, len(unit_specs), chunk_size)]


def _parse_chunked_wavefront_strategy(unit_strategy: str) -> int:
    prefix = "chunked_wavefront_"
    if not unit_strategy.startswith(prefix):
        raise ValueError(f"unknown chunked wavefront strategy: {unit_strategy}")
    try:
        return max(1, int(unit_strategy[len(prefix) :]))
    except ValueError:
        return 10


def _interleaved_state_key(
    order: OrderData,
    state: dict[str, int | str],
    strategy: str,
) -> tuple[Any, ...]:
    due_day = int(state["due_day"])
    product_id = str(state["product_id"])
    unit_index = int(state["unit_index"])
    step_pos = int(state["step_pos"])
    ready_abs_tick = int(state["ready_abs_tick"])
    due_abs_tick = due_day * DAY_TICKS
    remaining_ticks = _remaining_route_ticks(order, product_id, step_pos)
    slack_ticks = due_abs_tick - ready_abs_tick - remaining_ticks
    if strategy == "interleaved_ready":
        return (ready_abs_tick, due_day, step_pos, product_id, unit_index)
    if strategy == "interleaved_depth":
        return (due_day, -step_pos, ready_abs_tick, product_id, unit_index)
    return (slack_ticks, due_day, ready_abs_tick, step_pos, product_id, unit_index)


def _attempt_interleaved_timed_schedule(
    order: OrderData,
    *,
    start_time: float,
    deadline: float,
    unit_strategy: str,
    worker_strategy: str,
    day_strategy: str,
) -> dict[str, Any]:
    calendars: dict[tuple[Any, ...], dict[int, list[tuple[int, int]]]] = {}
    worker_usage: dict[tuple[str, int], int] = {}
    records: list[dict[str, Any]] = []
    states: list[dict[str, int | str]] = [
        {
            "due_day": due_day,
            "product_id": product_id,
            "unit_index": unit_index,
            "step_pos": 0,
            "ready_abs_tick": 0,
        }
        for due_day, product_id, unit_index in _unit_specs_for_strategy(order, "earliest_due")
    ]

    scheduled_operations = 0
    while states:
        if time.perf_counter() > deadline:
            solution = _empty_solution(order, "time_limit", start_time, ["分钟级交错贪心排程超过时间限制"])
            solution["solver_method"] = "timed_greedy"
            solution["scheduled_operations"] = scheduled_operations
            return solution

        states.sort(key=lambda item: _interleaved_state_key(order, item, unit_strategy))
        state = states.pop(0)
        due_day = int(state["due_day"])
        product_id = str(state["product_id"])
        unit_index = int(state["unit_index"])
        step_pos = int(state["step_pos"])
        ready_abs_tick = int(state["ready_abs_tick"])
        steps = order.processes.get(product_id, ())
        if not steps:
            solution = _empty_solution(order, "invalid_input", start_time, [f"产品 {product_id} 缺少工序定义"])
            solution["solver_method"] = "timed_greedy"
            return solution
        step = steps[step_pos]
        duration_ticks = _duration_ticks(step.duration_minutes)
        placement = _find_timed_placement(
            order,
            calendars,
            worker_usage,
            product_id=product_id,
            step_pos=step_pos,
            ready_abs_tick=ready_abs_tick,
            due_day=due_day,
            worker_strategy=worker_strategy,
            day_strategy=day_strategy,
            latest_end_abs_tick=due_day * DAY_TICKS - _remaining_route_ticks(order, product_id, step_pos + 1),
        )
        if placement is None:
            solution = _empty_solution(
                order,
                "no_solution_found",
                start_time,
                [
                    f"无法在第 {due_day} 天前安排产品 {product_id} "
                    f"第 {step.step_index} 道工序 {step.name}"
                ],
            )
            solution["solver_method"] = "timed_greedy"
            solution["scheduled_operations"] = scheduled_operations
            solution["strategy"] = {
                "unit_strategy": unit_strategy,
                "worker_strategy": worker_strategy,
                "day_strategy": day_strategy,
            }
            return solution

        _reserve_timed_placement(calendars, worker_usage, placement, duration_ticks=duration_ticks)
        equipment = list(real_equipment(step.equipment))
        records.append(
            {
                "day": placement.day,
                "start_tick": placement.start_tick,
                "end_tick": placement.end_tick,
                "worker": placement.worker,
                "machines": equipment,
                "material": product_id,
                "process": step.name,
                "step_index": step.step_index,
                "quantity": 1,
                "unit_duration_minutes": step.duration_minutes,
                "unit_duration_ticks": duration_ticks,
                "duration_ticks": duration_ticks,
            }
        )
        scheduled_operations += 1
        ready_abs_tick = _absolute_tick(placement.day, placement.end_tick)
        if ready_abs_tick > due_day * DAY_TICKS:
            solution = _empty_solution(
                order,
                "no_solution_found",
                start_time,
                [f"产品 {product_id} 单件完工时间超过第 {due_day} 天"],
            )
            solution["solver_method"] = "timed_greedy"
            solution["scheduled_operations"] = scheduled_operations
            solution["strategy"] = {
                "unit_strategy": unit_strategy,
                "worker_strategy": worker_strategy,
                "day_strategy": day_strategy,
            }
            return solution
        if step_pos + 1 < len(steps):
            states.append(
                {
                    "due_day": due_day,
                    "product_id": product_id,
                    "unit_index": unit_index,
                    "step_pos": step_pos + 1,
                    "ready_abs_tick": ready_abs_tick,
                }
            )

    plan = _timed_records_to_plan(records)
    return {
        "case_id": order.case_id,
        "status": "feasible",
        "solver_method": "timed_greedy",
        "solve_seconds": time.perf_counter() - start_time,
        "objective_value": None,
        "summary": order_stats(order),
        "scheduled_operations": scheduled_operations,
        "task_count_before_merge": len(records),
        "task_count_after_merge": sum(len(day["tasks"]) for day in plan),
        "strategy": {
            "unit_strategy": unit_strategy,
            "worker_strategy": worker_strategy,
            "day_strategy": day_strategy,
        },
        "plan": plan,
    }


def _attempt_chunked_wavefront_timed_schedule(
    order: OrderData,
    *,
    start_time: float,
    deadline: float,
    unit_strategy: str,
    worker_strategy: str,
    day_strategy: str,
) -> dict[str, Any]:
    chunk_size = _parse_chunked_wavefront_strategy(unit_strategy)
    calendars: dict[tuple[Any, ...], dict[int, list[tuple[int, int]]]] = {}
    worker_usage: dict[tuple[str, int], int] = {}
    records: list[dict[str, Any]] = []
    chunks = _chunked_unit_specs(order, chunk_size)
    unit_ready: dict[tuple[int, str, int], int] = {
        spec: 0
        for chunk in chunks
        for spec in chunk
    }

    scheduled_operations = 0
    for chunk in chunks:
        max_steps = max((len(order.processes.get(product_id, ())) for _due_day, product_id, _unit_index in chunk), default=0)
        for step_pos in range(max_steps):
            if time.perf_counter() > deadline:
                solution = _empty_solution(order, "time_limit", start_time, ["分钟级分块分层贪心排程超过时间限制"])
                solution["solver_method"] = "timed_greedy"
                solution["scheduled_operations"] = scheduled_operations
                return solution

            operations: list[tuple[int, int, int, str, int]] = []
            for due_day, product_id, unit_index in chunk:
                steps = order.processes.get(product_id, ())
                if not steps:
                    solution = _empty_solution(order, "invalid_input", start_time, [f"产品 {product_id} 缺少工序定义"])
                    solution["solver_method"] = "timed_greedy"
                    return solution
                if step_pos >= len(steps):
                    continue
                ready_abs_tick = unit_ready[(due_day, product_id, unit_index)]
                slack_ticks = due_day * DAY_TICKS - ready_abs_tick - _remaining_route_ticks(order, product_id, step_pos)
                operations.append((slack_ticks, ready_abs_tick, due_day, product_id, unit_index))
            operations.sort()

            for _slack_ticks, ready_abs_tick, due_day, product_id, unit_index in operations:
                if time.perf_counter() > deadline:
                    solution = _empty_solution(order, "time_limit", start_time, ["分钟级分块分层贪心排程超过时间限制"])
                    solution["solver_method"] = "timed_greedy"
                    solution["scheduled_operations"] = scheduled_operations
                    return solution

                step = order.processes[product_id][step_pos]
                duration_ticks = _duration_ticks(step.duration_minutes)
                placement = _find_timed_placement(
                    order,
                    calendars,
                    worker_usage,
                    product_id=product_id,
                    step_pos=step_pos,
                    ready_abs_tick=ready_abs_tick,
                    due_day=due_day,
                    worker_strategy=worker_strategy,
                    day_strategy=day_strategy,
                    latest_end_abs_tick=due_day * DAY_TICKS - _remaining_route_ticks(order, product_id, step_pos + 1),
                )
                if placement is None:
                    solution = _empty_solution(
                        order,
                        "no_solution_found",
                        start_time,
                        [
                            f"无法在第 {due_day} 天前安排产品 {product_id} "
                            f"第 {step.step_index} 道工序 {step.name}"
                        ],
                    )
                    solution["solver_method"] = "timed_greedy"
                    solution["scheduled_operations"] = scheduled_operations
                    solution["strategy"] = {
                        "unit_strategy": unit_strategy,
                        "worker_strategy": worker_strategy,
                        "day_strategy": day_strategy,
                        "chunk_size": chunk_size,
                    }
                    return solution

                _reserve_timed_placement(calendars, worker_usage, placement, duration_ticks=duration_ticks)
                equipment = list(real_equipment(step.equipment))
                records.append(
                    {
                        "day": placement.day,
                        "start_tick": placement.start_tick,
                        "end_tick": placement.end_tick,
                        "worker": placement.worker,
                        "machines": equipment,
                        "material": product_id,
                        "process": step.name,
                        "step_index": step.step_index,
                        "quantity": 1,
                        "unit_duration_minutes": step.duration_minutes,
                        "unit_duration_ticks": duration_ticks,
                        "duration_ticks": duration_ticks,
                    }
                )
                scheduled_operations += 1
                ready_abs_tick = _absolute_tick(placement.day, placement.end_tick)
                unit_ready[(due_day, product_id, unit_index)] = ready_abs_tick
                if ready_abs_tick > due_day * DAY_TICKS:
                    solution = _empty_solution(
                        order,
                        "no_solution_found",
                        start_time,
                        [f"产品 {product_id} 单件完工时间超过第 {due_day} 天"],
                    )
                    solution["solver_method"] = "timed_greedy"
                    solution["scheduled_operations"] = scheduled_operations
                    solution["strategy"] = {
                        "unit_strategy": unit_strategy,
                        "worker_strategy": worker_strategy,
                        "day_strategy": day_strategy,
                        "chunk_size": chunk_size,
                    }
                    return solution

    plan = _timed_records_to_plan(records)
    return {
        "case_id": order.case_id,
        "status": "feasible",
        "solver_method": "timed_greedy",
        "solve_seconds": time.perf_counter() - start_time,
        "objective_value": None,
        "summary": order_stats(order),
        "scheduled_operations": scheduled_operations,
        "task_count_before_merge": len(records),
        "task_count_after_merge": sum(len(day["tasks"]) for day in plan),
        "strategy": {
            "unit_strategy": unit_strategy,
            "worker_strategy": worker_strategy,
            "day_strategy": day_strategy,
            "chunk_size": chunk_size,
        },
        "plan": plan,
    }


def _attempt_timed_schedule(
    order: OrderData,
    *,
    start_time: float,
    deadline: float,
    unit_strategy: str,
    worker_strategy: str,
    day_strategy: str,
) -> dict[str, Any]:
    if unit_strategy.startswith("interleaved_"):
        return _attempt_interleaved_timed_schedule(
            order,
            start_time=start_time,
            deadline=deadline,
            unit_strategy=unit_strategy,
            worker_strategy=worker_strategy,
            day_strategy=day_strategy,
        )
    if unit_strategy.startswith("chunked_wavefront_"):
        return _attempt_chunked_wavefront_timed_schedule(
            order,
            start_time=start_time,
            deadline=deadline,
            unit_strategy=unit_strategy,
            worker_strategy=worker_strategy,
            day_strategy=day_strategy,
        )

    calendars: dict[tuple[Any, ...], dict[int, list[tuple[int, int]]]] = {}
    worker_usage: dict[tuple[str, int], int] = {}
    records: list[dict[str, Any]] = []
    unit_specs = _unit_specs_for_strategy(order, unit_strategy)

    scheduled_operations = 0
    for due_day, product_id, _unit_index in unit_specs:
        if time.perf_counter() > deadline:
            solution = _empty_solution(order, "time_limit", start_time, ["分钟级贪心排程超过时间限制"])
            solution["solver_method"] = "timed_greedy"
            solution["scheduled_operations"] = scheduled_operations
            return solution

        ready_abs_tick = 0
        steps = order.processes.get(product_id, ())
        if not steps:
            solution = _empty_solution(order, "invalid_input", start_time, [f"产品 {product_id} 缺少工序定义"])
            solution["solver_method"] = "timed_greedy"
            return solution
        for step_pos, step in enumerate(steps):
            duration_ticks = _duration_ticks(step.duration_minutes)
            placement = _find_timed_placement(
                order,
                calendars,
                worker_usage,
                product_id=product_id,
                step_pos=step_pos,
                ready_abs_tick=ready_abs_tick,
                due_day=due_day,
                worker_strategy=worker_strategy,
                day_strategy=day_strategy,
                latest_end_abs_tick=due_day * DAY_TICKS - _remaining_route_ticks(order, product_id, step_pos + 1),
            )
            if placement is None:
                solution = _empty_solution(
                    order,
                    "no_solution_found",
                    start_time,
                    [
                        f"无法在第 {due_day} 天前安排产品 {product_id} "
                        f"第 {step.step_index} 道工序 {step.name}"
                    ],
                )
                solution["solver_method"] = "timed_greedy"
                solution["scheduled_operations"] = scheduled_operations
                solution["strategy"] = {
                    "unit_strategy": unit_strategy,
                    "worker_strategy": worker_strategy,
                    "day_strategy": day_strategy,
                }
                return solution

            _reserve_timed_placement(calendars, worker_usage, placement, duration_ticks=duration_ticks)
            equipment = list(real_equipment(step.equipment))
            records.append(
                {
                    "day": placement.day,
                    "start_tick": placement.start_tick,
                    "end_tick": placement.end_tick,
                    "worker": placement.worker,
                    "machines": equipment,
                    "material": product_id,
                    "process": step.name,
                    "step_index": step.step_index,
                    "quantity": 1,
                    "unit_duration_minutes": step.duration_minutes,
                    "unit_duration_ticks": duration_ticks,
                    "duration_ticks": duration_ticks,
                }
            )
            scheduled_operations += 1
            ready_abs_tick = _absolute_tick(placement.day, placement.end_tick)

            if ready_abs_tick > due_day * DAY_TICKS:
                solution = _empty_solution(
                    order,
                    "no_solution_found",
                    start_time,
                    [f"产品 {product_id} 单件完工时间超过第 {due_day} 天"],
                )
                solution["solver_method"] = "timed_greedy"
                solution["scheduled_operations"] = scheduled_operations
                solution["strategy"] = {
                    "unit_strategy": unit_strategy,
                    "worker_strategy": worker_strategy,
                    "day_strategy": day_strategy,
                }
                return solution

    plan = _timed_records_to_plan(records)
    return {
        "case_id": order.case_id,
        "status": "feasible",
        "solver_method": "timed_greedy",
        "solve_seconds": time.perf_counter() - start_time,
        "objective_value": None,
        "summary": order_stats(order),
        "scheduled_operations": scheduled_operations,
        "task_count_before_merge": len(records),
        "task_count_after_merge": sum(len(day["tasks"]) for day in plan),
        "strategy": {
            "unit_strategy": unit_strategy,
            "worker_strategy": worker_strategy,
            "day_strategy": day_strategy,
        },
        "plan": plan,
    }


def _operation_count(order: OrderData) -> int:
    total = 0
    for product_id, quantity in net_required_by_product(order).items():
        if quantity > 0:
            total += int(quantity) * len(order.processes.get(product_id, ()))
    return total


def _max_batch_quantity_for_product(order: OrderData, product_id: str) -> int:
    max_quantity = math.inf
    for step in order.processes.get(product_id, ()):
        duration_ticks = _duration_ticks(step.duration_minutes)
        if duration_ticks <= 0:
            continue
        max_quantity = min(max_quantity, DAY_TICKS // duration_ticks)
    if math.isinf(max_quantity):
        return 10_000
    return max(1, int(max_quantity))


def _batch_specs_for_cpsat(
    order: OrderData,
    *,
    operation_count: int,
    target_operations: int = 2500,
) -> list[tuple[int, int, str, int]]:
    target_batch_quantity = max(1, int(math.ceil(max(operation_count, 1) / max(target_operations, 1))))
    specs: list[tuple[int, int, str, int]] = []
    batch_id = 0
    for product_id, due_day, quantity in _net_due_batches(order):
        max_batch_quantity = _max_batch_quantity_for_product(order, product_id)
        batch_quantity = max(1, min(target_batch_quantity, max_batch_quantity))
        remaining = int(quantity)
        while remaining > 0:
            current_quantity = min(batch_quantity, remaining)
            specs.append((batch_id, int(due_day), product_id, current_quantity))
            batch_id += 1
            remaining -= current_quantity
    return specs


def _worker_start_domain(
    order: OrderData,
    worker: str,
    *,
    due_day: int,
    duration_ticks: int,
    max_start_abs: int | None = None,
):
    return _start_domain_for_workers(
        order,
        (worker,),
        due_day=due_day,
        duration_ticks=duration_ticks,
        max_start_abs=max_start_abs,
    )


def _start_domain_for_workers(
    order: OrderData,
    workers: tuple[str, ...] | list[str],
    *,
    due_day: int,
    duration_ticks: int,
    max_start_abs: int | None = None,
):
    intervals: list[list[int]] = []
    for worker in workers:
        for day in sorted(order.workers.get(worker, ())):
            if not (1 <= day <= due_day):
                continue
            day_start = (day - 1) * DAY_TICKS
            if duration_ticks == 0:
                latest_start = day_start + DAY_TICKS - 1
            else:
                latest_start = day_start + DAY_TICKS - duration_ticks
            if max_start_abs is not None:
                latest_start = min(latest_start, int(max_start_abs))
            if latest_start >= day_start:
                intervals.append([day_start, latest_start])
    if not intervals:
        return None
    intervals.sort()
    merged: list[list[int]] = []
    for start, end in intervals:
        if merged and start <= merged[-1][1] + 1:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return cp_model.Domain.FromIntervals(merged)


def _eligible_workers_for_step(order: OrderData, step: ProcessStep) -> list[str]:
    return [worker for worker in dict.fromkeys(step.eligible_workers) if worker in order.workers]


def _solve_order_timed_cpsat_batched(
    order: OrderData,
    *,
    start_time: float,
    deadline: float,
    operation_count: int,
    target_operations: int = 2500,
) -> dict[str, Any]:
    batch_specs = _batch_specs_for_cpsat(
        order,
        operation_count=operation_count,
        target_operations=target_operations,
    )
    batched_operation_count = sum(
        len(order.processes.get(product_id, ()))
        for _batch_id, _due_day, product_id, _quantity in batch_specs
    )
    batched_model_exact = all(quantity == 1 for _batch_id, _due_day, _product_id, quantity in batch_specs)
    if not batch_specs:
        solution = _empty_solution(order, "optimal", start_time)
        solution["solver_method"] = "timed_cpsat_batched"
        solution["operation_count"] = operation_count
        solution["batched_operation_count"] = 0
        solution["batch_count"] = 0
        solution["target_operations"] = target_operations
        solution["batched_model_exact"] = True
        return solution

    model = cp_model.CpModel()
    worker_intervals: dict[str, list[Any]] = {}
    machine_intervals: dict[str, list[Any]] = {}
    start_vars: dict[tuple[int, int], Any] = {}
    end_vars: dict[tuple[int, int], Any] = {}
    worker_choices: dict[tuple[int, int], list[tuple[str, Any]]] = {}
    op_meta: dict[tuple[int, int], tuple[int, str, int, int, ProcessStep]] = {}
    presence_vars: list[Any] = []

    errors: list[str] = []
    for batch_id, due_day, product_id, quantity in batch_specs:
        steps = order.processes.get(product_id, ())
        if not steps:
            errors.append(f"产品 {product_id} 缺少工序定义")
            continue
        for step_pos, step in enumerate(steps):
            unit_duration_ticks = _duration_ticks(step.duration_minutes)
            duration_ticks = unit_duration_ticks * int(quantity)
            if duration_ticks > DAY_TICKS:
                errors.append(
                    f"产品 {product_id} 第 {step.step_index} 道工序批量 {quantity} 件耗时超过一天"
                )
                continue
            remaining_after_ticks = int(quantity) * _remaining_route_ticks(order, product_id, step_pos + 1)
            latest_end = int(due_day) * DAY_TICKS - remaining_after_ticks
            if latest_end < duration_ticks:
                errors.append(
                    f"产品 {product_id} 第 {step.step_index} 道工序批量 {quantity} 件无法为后续工序留出最短加工时间"
                )
                continue
            latest_start = max(0, latest_end - duration_ticks)
            eligible_workers = _eligible_workers_for_step(order, step)
            start_domain = _start_domain_for_workers(
                order,
                eligible_workers,
                due_day=due_day,
                duration_ticks=duration_ticks,
                max_start_abs=latest_start,
            )
            if start_domain is None:
                errors.append(
                    f"产品 {product_id} 第 {step.step_index} 道工序批量 {quantity} 件没有可用工人日期"
                )
                continue
            op_key = (batch_id, step_pos)
            start_var = model.NewIntVarFromDomain(start_domain, f"bs_{batch_id}_{step_pos}")
            end_var = model.NewIntVar(0, latest_end, f"be_{batch_id}_{step_pos}")
            model.Add(end_var == start_var + duration_ticks)
            start_vars[op_key] = start_var
            end_vars[op_key] = end_var
            op_meta[op_key] = (due_day, product_id, batch_id, int(quantity), step)
            for machine in _required_machines(step):
                if max(int(order.machines.get(machine, 0)), 0) <= 0:
                    errors.append(
                        f"产品 {product_id} 第 {step.step_index} 道工序需要不可用设备 {machine}"
                    )
                    continue
                if duration_ticks > 0:
                    machine_interval = model.NewIntervalVar(
                        start_var,
                        duration_ticks,
                        end_var,
                        f"bim_{batch_id}_{step_pos}_{machine}",
                    )
                    machine_intervals.setdefault(machine, []).append(machine_interval)

            choices: list[tuple[str, Any]] = []
            for worker in eligible_workers:
                domain = _worker_start_domain(
                    order,
                    worker,
                    due_day=due_day,
                    duration_ticks=duration_ticks,
                    max_start_abs=latest_start,
                )
                if domain is None:
                    continue
                presence = model.NewBoolVar(f"bw_{batch_id}_{step_pos}_{worker}")
                interval = model.NewOptionalIntervalVar(
                    start_var,
                    duration_ticks,
                    end_var,
                    presence,
                    f"biw_{batch_id}_{step_pos}_{worker}",
                )
                model.AddLinearExpressionInDomain(start_var, domain).OnlyEnforceIf(presence)
                worker_intervals.setdefault(worker, []).append(interval)
                choices.append((worker, presence))
                presence_vars.append(presence)
            if not choices:
                errors.append(
                    f"产品 {product_id} 第 {step.step_index} 道工序批量 {quantity} 件没有可用工人日期"
                )
                continue
            model.AddExactlyOne(presence for _worker, presence in choices)
            worker_choices[op_key] = choices

        for step_pos in range(1, len(steps)):
            previous_key = (batch_id, step_pos - 1)
            current_key = (batch_id, step_pos)
            if previous_key in end_vars and current_key in start_vars:
                model.Add(start_vars[current_key] >= end_vars[previous_key])

    if errors:
        status = "infeasible_proven" if batched_model_exact else "no_solution_found"
        solution = _empty_solution(order, status, start_time, errors[:10])
        solution["solver_method"] = "timed_cpsat_batched"
        solution["operation_count"] = operation_count
        solution["batched_operation_count"] = batched_operation_count
        solution["batch_count"] = len(batch_specs)
        solution["target_operations"] = target_operations
        solution["batched_model_exact"] = batched_model_exact
        return solution

    for worker, intervals in worker_intervals.items():
        if intervals:
            model.AddNoOverlap(intervals)
    for machine, intervals in machine_intervals.items():
        if not intervals:
            continue
        count = max(int(order.machines.get(machine, 0)), 0)
        if count <= 1:
            model.AddNoOverlap(intervals)
        else:
            model.AddCumulative(intervals, [1] * len(intervals), count)
    if start_vars:
        model.AddDecisionStrategy(
            list(start_vars.values()),
            cp_model.CHOOSE_LOWEST_MIN,
            cp_model.SELECT_MIN_VALUE,
        )
    if presence_vars:
        model.AddDecisionStrategy(
            presence_vars,
            cp_model.CHOOSE_FIRST,
            cp_model.SELECT_MAX_VALUE,
        )

    solver = cp_model.CpSolver()
    remaining_seconds = max(0.001, deadline - time.perf_counter())
    solver.parameters.max_time_in_seconds = remaining_seconds
    solver.parameters.num_search_workers = min(max(os.cpu_count() or 1, 1), 8)
    solver.parameters.random_seed = 1
    solver.parameters.stop_after_first_solution = True

    status_code = solver.Solve(model)
    status_name = solver.StatusName(status_code)
    if status_code not in {cp_model.OPTIMAL, cp_model.FEASIBLE}:
        if status_code == cp_model.INFEASIBLE and not batched_model_exact:
            status = "no_solution_found"
        else:
            status = {
                cp_model.INFEASIBLE: "infeasible_proven",
                cp_model.MODEL_INVALID: "model_invalid",
                cp_model.UNKNOWN: "time_limit",
            }.get(status_code, "failed")
        solution = _empty_solution(
            order,
            status,
            start_time,
            [f"CP-SAT batched minute model status: {status_name}"],
        )
        solution["solver_method"] = "timed_cpsat_batched"
        solution["cp_sat_status"] = status_name
        solution["operation_count"] = operation_count
        solution["batched_operation_count"] = batched_operation_count
        solution["batch_count"] = len(batch_specs)
        solution["target_operations"] = target_operations
        solution["batched_model_exact"] = batched_model_exact
        return solution

    records: list[dict[str, Any]] = []
    for op_key, (due_day, product_id, _batch_id, quantity, step) in op_meta.items():
        start_abs = int(solver.Value(start_vars[op_key]))
        end_abs = int(solver.Value(end_vars[op_key]))
        chosen_worker = ""
        for worker, presence in worker_choices.get(op_key, []):
            if int(solver.Value(presence)):
                chosen_worker = worker
                break
        day = _day_from_absolute_tick(start_abs)
        start_tick = _tick_in_day(start_abs)
        end_tick = end_abs - (day - 1) * DAY_TICKS
        unit_duration_ticks = _duration_ticks(step.duration_minutes)
        duration_ticks = unit_duration_ticks * int(quantity)
        equipment = list(real_equipment(step.equipment))
        records.append(
            {
                "day": day,
                "start_tick": start_tick,
                "end_tick": end_tick,
                "worker": chosen_worker,
                "machines": equipment,
                "material": product_id,
                "process": step.name,
                "step_index": step.step_index,
                "quantity": int(quantity),
                "unit_duration_minutes": step.duration_minutes,
                "unit_duration_ticks": unit_duration_ticks,
                "duration_ticks": duration_ticks,
            }
        )

    plan = _timed_records_to_plan(records)
    return {
        "case_id": order.case_id,
        "status": "feasible",
        "solver_method": "timed_cpsat_batched",
        "cp_sat_status": status_name,
        "solve_seconds": time.perf_counter() - start_time,
        "objective_value": None,
        "summary": order_stats(order),
        "operation_count": operation_count,
        "batched_operation_count": batched_operation_count,
        "batch_count": len(batch_specs),
        "target_operations": target_operations,
        "batched_model_exact": batched_model_exact,
        "task_count_before_merge": len(records),
        "task_count_after_merge": sum(len(day["tasks"]) for day in plan),
        "plan": plan,
    }


def _batched_attempt_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "target_operations": result.get("target_operations"),
        "status": result.get("status"),
        "cp_sat_status": result.get("cp_sat_status"),
        "batched_operation_count": result.get("batched_operation_count"),
        "batch_count": result.get("batch_count"),
        "solve_seconds": result.get("solve_seconds"),
        "errors": result.get("errors", [])[:3],
    }


def _solve_order_timed_cpsat_batched_staged(
    order: OrderData,
    *,
    start_time: float,
    deadline: float,
    operation_count: int,
) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    last_result: dict[str, Any] | None = None
    stages: tuple[tuple[int, float | None], ...] = (
        (300, 90.0),
        (800, 120.0),
        (2500, None),
    )
    for target_operations, max_stage_seconds in stages:
        now = time.perf_counter()
        if now >= deadline:
            break
        stage_deadline = deadline
        if max_stage_seconds is not None:
            stage_deadline = min(deadline, now + max_stage_seconds)
        result = _solve_order_timed_cpsat_batched(
            order,
            start_time=start_time,
            deadline=stage_deadline,
            operation_count=operation_count,
            target_operations=target_operations,
        )
        last_result = result
        summary = _batched_attempt_summary(result)
        attempts.append(summary)
        if result.get("status") == "feasible":
            result["batched_attempts"] = attempts
            return result
        if result.get("status") in {"model_invalid", "solver_unavailable"}:
            result["batched_attempts"] = attempts
            return result
        if result.get("batched_model_exact") and result.get("status") == "infeasible_proven":
            result["batched_attempts"] = attempts
            return result

    if last_result is None:
        last_result = _empty_solution(
            order,
            "time_limit",
            start_time,
            ["CP-SAT batched staged model had no remaining time"],
        )
        last_result["solver_method"] = "timed_cpsat_batched"
        last_result["operation_count"] = operation_count
    last_result["batched_attempts"] = attempts
    return last_result


def _solve_order_timed_cpsat(
    order: OrderData,
    *,
    start_time: float,
    deadline: float,
    max_operations: int = 1000,
) -> dict[str, Any] | None:
    if cp_model is None:
        solution = _empty_solution(
            order,
            "solver_unavailable",
            start_time,
            ["ortools is not installed; install it with `python -m pip install --user ortools`"],
        )
        solution["solver_method"] = "timed_cpsat"
        return solution
    operation_count = _operation_count(order)
    if operation_count > max_operations:
        return _solve_order_timed_cpsat_batched_staged(
            order,
            start_time=start_time,
            deadline=deadline,
            operation_count=operation_count,
        )

    model = cp_model.CpModel()
    worker_intervals: dict[str, list[Any]] = {}
    machine_intervals: dict[str, list[Any]] = {}
    start_vars: dict[tuple[int, int], Any] = {}
    end_vars: dict[tuple[int, int], Any] = {}
    worker_choices: dict[tuple[int, int], list[tuple[str, Any]]] = {}
    op_meta: dict[tuple[int, int], tuple[int, str, int, ProcessStep]] = {}
    presence_vars: list[Any] = []

    unit_specs = _unit_specs_for_strategy(order, "earliest_due")
    errors: list[str] = []
    for unit_id, (due_day, product_id, _unit_index) in enumerate(unit_specs):
        steps = order.processes.get(product_id, ())
        if not steps:
            errors.append(f"产品 {product_id} 缺少工序定义")
            continue
        for step_pos, step in enumerate(steps):
            duration_ticks = _duration_ticks(step.duration_minutes)
            if duration_ticks > DAY_TICKS:
                errors.append(
                    f"产品 {product_id} 第 {step.step_index} 道工序单件耗时超过一天"
                )
                continue
            remaining_after_ticks = _remaining_route_ticks(order, product_id, step_pos + 1)
            latest_end = int(due_day) * DAY_TICKS - remaining_after_ticks
            if latest_end < duration_ticks:
                errors.append(
                    f"产品 {product_id} 第 {step.step_index} 道工序无法为后续工序留出最短加工时间"
                )
                continue
            latest_start = max(0, latest_end - duration_ticks)
            eligible_workers = _eligible_workers_for_step(order, step)
            start_domain = _start_domain_for_workers(
                order,
                eligible_workers,
                due_day=due_day,
                duration_ticks=duration_ticks,
                max_start_abs=latest_start,
            )
            if start_domain is None:
                errors.append(
                    f"产品 {product_id} 第 {step.step_index} 道工序没有可用工人日期"
                )
                continue
            op_key = (unit_id, step_pos)
            start_var = model.NewIntVarFromDomain(start_domain, f"s_{unit_id}_{step_pos}")
            end_var = model.NewIntVar(0, latest_end, f"e_{unit_id}_{step_pos}")
            model.Add(end_var == start_var + duration_ticks)
            start_vars[op_key] = start_var
            end_vars[op_key] = end_var
            op_meta[op_key] = (due_day, product_id, unit_id, step)
            for machine in _required_machines(step):
                if max(int(order.machines.get(machine, 0)), 0) <= 0:
                    errors.append(
                        f"产品 {product_id} 第 {step.step_index} 道工序需要不可用设备 {machine}"
                    )
                    continue
                if duration_ticks > 0:
                    machine_interval = model.NewIntervalVar(
                        start_var,
                        duration_ticks,
                        end_var,
                        f"im_{unit_id}_{step_pos}_{machine}",
                    )
                    machine_intervals.setdefault(machine, []).append(machine_interval)

            choices: list[tuple[str, Any]] = []
            for worker in eligible_workers:
                domain = _worker_start_domain(
                    order,
                    worker,
                    due_day=due_day,
                    duration_ticks=duration_ticks,
                    max_start_abs=latest_start,
                )
                if domain is None:
                    continue
                presence = model.NewBoolVar(f"w_{unit_id}_{step_pos}_{worker}")
                interval = model.NewOptionalIntervalVar(
                    start_var,
                    duration_ticks,
                    end_var,
                    presence,
                    f"iw_{unit_id}_{step_pos}_{worker}",
                )
                model.AddLinearExpressionInDomain(start_var, domain).OnlyEnforceIf(presence)
                worker_intervals.setdefault(worker, []).append(interval)
                choices.append((worker, presence))
                presence_vars.append(presence)
            if not choices:
                errors.append(
                    f"产品 {product_id} 第 {step.step_index} 道工序没有可用工人日期"
                )
                continue
            model.AddExactlyOne(presence for _worker, presence in choices)
            worker_choices[op_key] = choices

        for step_pos in range(1, len(steps)):
            previous_key = (unit_id, step_pos - 1)
            current_key = (unit_id, step_pos)
            if previous_key in end_vars and current_key in start_vars:
                model.Add(start_vars[current_key] >= end_vars[previous_key])

    if errors:
        solution = _empty_solution(order, "infeasible_proven", start_time, errors[:10])
        solution["solver_method"] = "timed_cpsat"
        solution["operation_count"] = operation_count
        return solution

    for worker, intervals in worker_intervals.items():
        if intervals:
            model.AddNoOverlap(intervals)
    for machine, intervals in machine_intervals.items():
        if not intervals:
            continue
        count = max(int(order.machines.get(machine, 0)), 0)
        if count <= 1:
            model.AddNoOverlap(intervals)
        else:
            model.AddCumulative(intervals, [1] * len(intervals), count)
    if start_vars:
        model.AddDecisionStrategy(
            list(start_vars.values()),
            cp_model.CHOOSE_LOWEST_MIN,
            cp_model.SELECT_MIN_VALUE,
        )
    if presence_vars:
        model.AddDecisionStrategy(
            presence_vars,
            cp_model.CHOOSE_FIRST,
            cp_model.SELECT_MAX_VALUE,
        )

    solver = cp_model.CpSolver()
    remaining_seconds = max(0.001, deadline - time.perf_counter())
    solver.parameters.max_time_in_seconds = remaining_seconds
    solver.parameters.num_search_workers = min(max(os.cpu_count() or 1, 1), 8)
    solver.parameters.random_seed = 1
    solver.parameters.stop_after_first_solution = True

    status_code = solver.Solve(model)
    status_name = solver.StatusName(status_code)
    if status_code not in {cp_model.OPTIMAL, cp_model.FEASIBLE}:
        status = {
            cp_model.INFEASIBLE: "infeasible_proven",
            cp_model.MODEL_INVALID: "model_invalid",
            cp_model.UNKNOWN: "time_limit",
        }.get(status_code, "failed")
        solution = _empty_solution(
            order,
            status,
            start_time,
            [f"CP-SAT minute model status: {status_name}"],
        )
        solution["solver_method"] = "timed_cpsat"
        solution["cp_sat_status"] = status_name
        solution["operation_count"] = operation_count
        return solution

    records: list[dict[str, Any]] = []
    for op_key, (due_day, product_id, _unit_id, step) in op_meta.items():
        start_abs = int(solver.Value(start_vars[op_key]))
        end_abs = int(solver.Value(end_vars[op_key]))
        chosen_worker = ""
        for worker, presence in worker_choices.get(op_key, []):
            if int(solver.Value(presence)):
                chosen_worker = worker
                break
        day = _day_from_absolute_tick(start_abs)
        start_tick = _tick_in_day(start_abs)
        end_tick = end_abs - (day - 1) * DAY_TICKS
        equipment = list(real_equipment(step.equipment))
        records.append(
            {
                "day": day,
                "start_tick": start_tick,
                "end_tick": end_tick,
                "worker": chosen_worker,
                "machines": equipment,
                "material": product_id,
                "process": step.name,
                "step_index": step.step_index,
                "quantity": 1,
                "unit_duration_minutes": step.duration_minutes,
                "unit_duration_ticks": _duration_ticks(step.duration_minutes),
                "duration_ticks": _duration_ticks(step.duration_minutes),
            }
        )

    plan = _timed_records_to_plan(records)
    return {
        "case_id": order.case_id,
        "status": "feasible",
        "solver_method": "timed_cpsat",
        "cp_sat_status": status_name,
        "solve_seconds": time.perf_counter() - start_time,
        "objective_value": None,
        "summary": order_stats(order),
        "operation_count": operation_count,
        "task_count_before_merge": len(records),
        "task_count_after_merge": sum(len(day["tasks"]) for day in plan),
        "plan": plan,
    }


def solve_order_timed(order: OrderData, *, time_limit_seconds: float = 600.0) -> dict[str, Any]:
    start_time = time.perf_counter()
    deadline = start_time + float(time_limit_seconds)
    static_errors = validate_order_static(order)
    if static_errors:
        return _empty_solution(order, "invalid_input", start_time, static_errors)

    horizon = max_due_day(order)
    net_required = net_required_by_product(order)
    active_products = [product for product, quantity in sorted(net_required.items()) if quantity > 0]
    if not active_products:
        solution = _empty_solution(order, "optimal", start_time)
        solution["solver_method"] = "timed_greedy"
        return solution
    if horizon <= 0:
        return _empty_solution(order, "invalid_input", start_time, ["存在净需求但没有有效期限"])

    capacity_errors = _basic_capacity_errors(order)
    if capacity_errors:
        solution = _empty_solution(order, "infeasible_proven", start_time, capacity_errors)
        solution["solver_method"] = "timed_greedy"
        return solution

    chunked_strategies = [
        ("chunked_wavefront_5", "least_used", "forward"),
        ("chunked_wavefront_10", "least_used", "forward"),
        ("chunked_wavefront_25", "least_used", "forward"),
    ]
    standard_strategies = [
        ("earliest_due", "least_used", "forward"),
        ("round_robin_product", "least_used", "forward"),
        ("largest_route_work", "least_used", "forward"),
        ("smallest_route_work", "least_used", "forward"),
        ("earliest_due", "name", "forward"),
        ("round_robin_product", "name", "forward"),
        ("largest_route_work", "name", "forward"),
        ("earliest_due", "most_used", "forward"),
        ("interleaved_slack", "least_used", "forward"),
        ("interleaved_ready", "least_used", "forward"),
        ("interleaved_depth", "least_used", "forward"),
        ("interleaved_slack", "name", "forward"),
        ("interleaved_ready", "name", "forward"),
        ("interleaved_slack", "most_used", "forward"),
    ]
    if _operation_count(order) >= 1000 and _max_machine_load_ratio(order) >= 0.75:
        strategies = [*chunked_strategies, *standard_strategies]
    else:
        strategies = [*standard_strategies[:4], *chunked_strategies, *standard_strategies[4:]]
    failures: list[dict[str, Any]] = []
    for unit_strategy, worker_strategy, day_strategy in strategies:
        if time.perf_counter() > deadline:
            break
        result = _attempt_timed_schedule(
            order,
            start_time=start_time,
            deadline=deadline,
            unit_strategy=unit_strategy,
            worker_strategy=worker_strategy,
            day_strategy=day_strategy,
        )
        if result.get("status") == "feasible":
            result["attempt_count"] = len(failures) + 1
            return result
        failures.append(
            {
                "strategy": result.get("strategy"),
                "status": result.get("status"),
                "errors": result.get("errors", [])[:3],
                "scheduled_operations": result.get("scheduled_operations"),
            }
        )
        if result.get("status") == "time_limit":
            break

    if time.perf_counter() < deadline:
        cpsat_result = _solve_order_timed_cpsat(order, start_time=start_time, deadline=deadline)
        if cpsat_result is not None:
            cpsat_result["greedy_failed_attempts"] = failures
            if cpsat_result.get("status") == "feasible":
                cpsat_result["attempt_count"] = len(failures) + 1
                return cpsat_result
            if cpsat_result.get("status") in {
                "infeasible_proven",
                "model_invalid",
                "time_limit",
                "solver_unavailable",
                "no_solution_found",
            }:
                return cpsat_result

    final_status = "time_limit" if failures and failures[-1].get("status") == "time_limit" else "no_solution_found"
    solution = _empty_solution(
        order,
        final_status,
        start_time,
        [
            "分钟级多策略排程未找到可行方案",
            *[
                f"{failure.get('strategy')}: {failure.get('errors')}"
                for failure in failures[:5]
            ],
        ],
    )
    solution["solver_method"] = "timed_greedy"
    solution["attempt_count"] = len(failures)
    solution["failed_attempts"] = failures
    return solution


def solve_order_timed_single(
    order: OrderData,
    *,
    time_limit_seconds: float = 600.0,
    unit_strategy: str,
    worker_strategy: str = "least_used",
    day_strategy: str = "forward",
) -> dict[str, Any]:
    _validate_timed_strategy(unit_strategy, worker_strategy, day_strategy)
    start_time = time.perf_counter()
    deadline = start_time + float(time_limit_seconds)
    strategy = _strategy_config(unit_strategy, worker_strategy, day_strategy)
    static_errors = validate_order_static(order)
    if static_errors:
        solution = _empty_solution(order, "invalid_input", start_time, static_errors)
        solution["solver_method"] = "timed_greedy"
        solution["strategy"] = strategy
        solution["attempt_count"] = 0
        return solution

    horizon = max_due_day(order)
    net_required = net_required_by_product(order)
    active_products = [product for product, quantity in sorted(net_required.items()) if quantity > 0]
    if not active_products:
        solution = _empty_solution(order, "optimal", start_time)
        solution["solver_method"] = "timed_greedy"
        solution["strategy"] = strategy
        solution["attempt_count"] = 0
        return solution
    if horizon <= 0:
        solution = _empty_solution(order, "invalid_input", start_time, ["存在净需求但没有有效期限"])
        solution["solver_method"] = "timed_greedy"
        solution["strategy"] = strategy
        solution["attempt_count"] = 0
        return solution

    capacity_errors = _basic_capacity_errors(order)
    if capacity_errors:
        solution = _empty_solution(order, "infeasible_proven", start_time, capacity_errors)
        solution["solver_method"] = "timed_greedy"
        solution["strategy"] = strategy
        solution["attempt_count"] = 0
        return solution

    result = _attempt_timed_schedule(
        order,
        start_time=start_time,
        deadline=deadline,
        unit_strategy=unit_strategy,
        worker_strategy=worker_strategy,
        day_strategy=day_strategy,
    )
    result["solver_method"] = "timed_greedy"
    result["strategy"] = result.get("strategy") or strategy
    result["attempt_count"] = 1
    return result


def solve_order_cpsat(order: OrderData, *, time_limit_seconds: float = 600.0) -> dict[str, Any]:
    start_time = time.perf_counter()
    deadline = start_time + float(time_limit_seconds)
    static_errors = validate_order_static(order)
    if static_errors:
        solution = _empty_solution(order, "invalid_input", start_time, static_errors)
        solution["solver_method"] = "timed_cpsat"
        return solution

    horizon = max_due_day(order)
    net_required = net_required_by_product(order)
    active_products = [product for product, quantity in sorted(net_required.items()) if quantity > 0]
    if not active_products:
        solution = _empty_solution(order, "optimal", start_time)
        solution["solver_method"] = "timed_cpsat"
        return solution
    if horizon <= 0:
        solution = _empty_solution(order, "invalid_input", start_time, ["存在净需求但没有有效期限"])
        solution["solver_method"] = "timed_cpsat"
        return solution

    capacity_errors = _basic_capacity_errors(order)
    if capacity_errors:
        solution = _empty_solution(order, "infeasible_proven", start_time, capacity_errors)
        solution["solver_method"] = "timed_cpsat"
        return solution

    result = _solve_order_timed_cpsat(order, start_time=start_time, deadline=deadline)
    if result is None:
        result = _empty_solution(order, "solver_unavailable", start_time, ["CP-SAT solver did not return a result"])
        result["solver_method"] = "timed_cpsat"
    return result


def solve_order(
    order: OrderData,
    *,
    time_limit_seconds: float = 600.0,
    method: str = "timed",
    unit_strategy: str | None = None,
    worker_strategy: str = "least_used",
    day_strategy: str = "forward",
) -> dict[str, Any]:
    if method == "cpsat":
        if unit_strategy is not None:
            raise ValueError("method='cpsat' does not accept timed greedy strategy overrides")
        return solve_order_cpsat(order, time_limit_seconds=time_limit_seconds)
    if method != "timed":
        raise ValueError("method must be one of: timed, cpsat")
    if unit_strategy is not None:
        return solve_order_timed_single(
            order,
            time_limit_seconds=time_limit_seconds,
            unit_strategy=unit_strategy,
            worker_strategy=worker_strategy,
            day_strategy=day_strategy,
        )
    return solve_order_timed(order, time_limit_seconds=time_limit_seconds)
