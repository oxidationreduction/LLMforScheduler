#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any

from schedule_solver import (
    WORKER_DAY_MINUTES,
    clean_text,
    due_requirements_by_product,
    is_no_machine,
    load_order,
    net_required_by_product,
    required_quantity_by_product,
)


NO_MACHINE_LABEL = "无设备"
PALETTE = (
    "#4e79a7",
    "#f28e2b",
    "#59a14f",
    "#e15759",
    "#76b7b2",
    "#edc948",
    "#b07aa1",
    "#ff9da7",
    "#9c755f",
    "#bab0ac",
    "#2f6f73",
    "#8c6d31",
)


@dataclass(frozen=True)
class VisualTask:
    index: int
    day: int
    start_minute: float
    end_minute: float
    product_id: str
    step_index: int | None
    process: str
    quantity: int
    worker: str
    machines: tuple[str, ...]
    machine_copy_labels: tuple[str, ...]
    duration_minutes: float

    @property
    def abs_start(self) -> float:
        return (self.day - 1) * WORKER_DAY_MINUTES + self.start_minute

    @property
    def abs_end(self) -> float:
        return (self.day - 1) * WORKER_DAY_MINUTES + self.end_minute


def _read_json(path: Path | None) -> Any:
    if path is None:
        return None
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _html(value: Any) -> str:
    return escape(str(value), quote=True)


def _fmt(value: Any, digits: int = 2) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if abs(number - round(number)) < 1e-9:
        return str(int(round(number)))
    return f"{number:.{digits}f}".rstrip("0").rstrip(".")


def _machine_list(task: dict[str, Any]) -> tuple[str, ...]:
    if isinstance(task.get("machines"), list):
        machines = tuple(clean_text(machine) for machine in task["machines"] if clean_text(machine))
        return tuple(machine for machine in machines if not is_no_machine(machine))
    machine_value = task.get("machine")
    if machine_value is None:
        return ()
    machine_text = clean_text(machine_value)
    if not machine_text or is_no_machine(machine_text):
        return ()
    if "+" in machine_text:
        return tuple(part.strip() for part in machine_text.split("+") if part.strip())
    return (machine_text,)


def _flatten_tasks(solution: dict[str, Any]) -> list[VisualTask]:
    plan = solution.get("plan", [])
    if not isinstance(plan, list):
        return []
    tasks: list[VisualTask] = []
    index = 0
    for day_block in plan:
        if not isinstance(day_block, dict):
            continue
        try:
            day = int(day_block.get("day", 0))
        except (TypeError, ValueError):
            continue
        raw_tasks = day_block.get("tasks", [])
        if not isinstance(raw_tasks, list):
            continue
        for task in raw_tasks:
            if not isinstance(task, dict):
                continue
            index += 1
            try:
                quantity = int(task.get("quantity", 0))
            except (TypeError, ValueError):
                quantity = 0
            raw_step_index = task.get("step_index", task.get("process_index"))
            try:
                step_index = int(raw_step_index)
            except (TypeError, ValueError):
                step_index = None
            try:
                start_minute = float(task.get("start_minute", 0.0))
                end_minute = float(task.get("end_minute", start_minute))
            except (TypeError, ValueError):
                start_minute = 0.0
                end_minute = 0.0
            try:
                duration = float(task.get("duration_minutes", end_minute - start_minute))
            except (TypeError, ValueError):
                duration = end_minute - start_minute
            tasks.append(
                VisualTask(
                    index=index,
                    day=day,
                    start_minute=start_minute,
                    end_minute=end_minute,
                    product_id=clean_text(task.get("material", task.get("product_id", ""))),
                    step_index=step_index,
                    process=clean_text(task.get("process", task.get("process_name", ""))),
                    quantity=quantity,
                    worker=clean_text(task.get("worker", "")),
                    machines=_machine_list(task),
                    machine_copy_labels=(),
                    duration_minutes=duration,
                )
            )
    return tasks


def _assign_machine_copies(tasks: list[VisualTask], machine_counts: dict[str, int]) -> list[VisualTask]:
    intervals: dict[tuple[str, int], list[list[tuple[float, float]]]] = {}
    assigned: list[VisualTask] = []
    for task in sorted(tasks, key=lambda item: (item.day, item.start_minute, item.end_minute, item.index)):
        copy_labels: list[str] = []
        for machine in task.machines:
            count = max(int(machine_counts.get(machine, 0)), 1)
            key = (machine, task.day)
            copies = intervals.setdefault(key, [[] for _ in range(count)])
            selected = 0
            for copy_index, used in enumerate(copies):
                if all(task.end_minute <= start or end <= task.start_minute for start, end in used):
                    selected = copy_index
                    break
            copies[selected].append((task.start_minute, task.end_minute))
            copies[selected].sort()
            copy_labels.append(f"{machine} #{selected + 1}")
        if not copy_labels:
            copy_labels = [NO_MACHINE_LABEL]
        assigned.append(
            VisualTask(
                index=task.index,
                day=task.day,
                start_minute=task.start_minute,
                end_minute=task.end_minute,
                product_id=task.product_id,
                step_index=task.step_index,
                process=task.process,
                quantity=task.quantity,
                worker=task.worker,
                machines=task.machines,
                machine_copy_labels=tuple(copy_labels),
                duration_minutes=task.duration_minutes,
            )
        )
    return sorted(assigned, key=lambda item: item.index)


def _color_maps(tasks: list[VisualTask]) -> tuple[dict[str, str], dict[str, str]]:
    processes = sorted({task.process or "未知工序" for task in tasks})
    machines = sorted({label.split(" #", 1)[0] for task in tasks for label in task.machine_copy_labels})
    process_colors = {name: PALETTE[index % len(PALETTE)] for index, name in enumerate(processes)}
    machine_colors = {name: PALETTE[index % len(PALETTE)] for index, name in enumerate(machines)}
    return process_colors, machine_colors


def _task_tooltip(task: VisualTask) -> str:
    step = "?" if task.step_index is None else str(task.step_index)
    machines = ", ".join(task.machine_copy_labels) if task.machine_copy_labels else NO_MACHINE_LABEL
    return "\n".join(
        [
            f"任务 #{task.index}",
            f"产品：{task.product_id}",
            f"工序：{step}. {task.process}",
            f"数量：{task.quantity}",
            f"工人：{task.worker or '未知'}",
            f"机器：{machines}",
            f"时间：Day {task.day} {_fmt(task.start_minute)}-{_fmt(task.end_minute)} min",
            f"总时长：{_fmt(task.duration_minutes)} min",
        ]
    )


def _render_task(task: VisualTask, *, left: float, width: float, top: float, process_color: str, machine_color: str) -> str:
    step = "?" if task.step_index is None else str(task.step_index)
    machines = ", ".join(task.machine_copy_labels) if task.machine_copy_labels else NO_MACHINE_LABEL
    tooltip = _html(_task_tooltip(task))
    label = _html(f"{step}. {task.process} x{task.quantity}")
    sub_label = _html(f"{task.product_id} · {machines}")
    return (
        f'<div class="task" data-tooltip="{tooltip}" '
        f'style="left:{left:.2f}px;width:{width:.2f}px;top:{top:.2f}px;'
        f'--proc:{process_color};--mach:{machine_color};">'
        f"<span>{label}</span><small>{sub_label}</small></div>"
    )


def _lane_stats(tasks: list[VisualTask]) -> str:
    duration = sum(max(task.end_minute - task.start_minute, 0.0) for task in tasks)
    return f"{len(tasks)} 项 / {_fmt(duration)} min"


def _render_axis(min_day: int, max_day: int, width: float, scale: float) -> str:
    total_minutes = (max_day - min_day + 1) * WORKER_DAY_MINUTES
    ticks: list[str] = []
    day_count = max_day - min_day + 1
    for day_offset in range(day_count + 1):
        left = day_offset * WORKER_DAY_MINUTES * scale
        if left <= width + 1:
            label = f"D{min_day + day_offset}" if day_offset < day_count else ""
            ticks.append(f'<div class="tick dayline" style="left:{left:.2f}px"><span>{_html(label)}</span></div>')
    minor_step = 120.0
    current = 0.0
    while current <= total_minutes + 1e-9:
        left = current * scale
        minute_in_day = current % WORKER_DAY_MINUTES
        if minute_in_day:
            ticks.append(f'<div class="tick" style="left:{left:.2f}px"><span>{_fmt(minute_in_day, 0)}</span></div>')
        current += minor_step
    return "".join(ticks)


def _render_timeline(
    title: str,
    lane_title: str,
    lanes: list[tuple[str, list[VisualTask]]],
    *,
    min_day: int,
    max_day: int,
    width: float,
    scale: float,
    process_colors: dict[str, str],
    machine_colors: dict[str, str],
) -> str:
    base = (min_day - 1) * WORKER_DAY_MINUTES
    axis = _render_axis(min_day, max_day, width, scale)
    parts = [
        '<section>',
        f'<div class="toolbar"><h2>{_html(title)}</h2>'
        '<label>颜色 <select class="mode"><option value="process">按工序</option>'
        '<option value="machine">按机器</option></select></label></div>',
        '<div class="scroll">',
        f'<div class="timeline" style="--chart-width:{width:.0f}px">',
        f'<div class="axis-label">{_html(lane_title)}</div><div class="axis" style="width:{width:.0f}px">{axis}</div>',
    ]
    for lane_name, lane_tasks in lanes:
        sorted_tasks = sorted(lane_tasks, key=lambda item: (item.day, item.start_minute, item.end_minute, item.index))
        lane_levels: list[float] = []
        positioned_tasks: list[tuple[VisualTask, int]] = []
        for task in sorted_tasks:
            level = 0
            for idx, occupied_until in enumerate(lane_levels):
                if occupied_until <= task.abs_start:
                    level = idx
                    break
            else:
                level = len(lane_levels)
                lane_levels.append(float("-inf"))
            lane_levels[level] = task.abs_end
            positioned_tasks.append((task, level))
        lane_height = max(42.0, 8.0 + max(len(lane_levels), 1) * 32.0)
        parts.append(
            f'<div class="lane-label" style="height:{lane_height:.0f}px"><b>{_html(lane_name)}</b>'
            f"<span>{_html(_lane_stats(lane_tasks))}</span></div>"
        )
        parts.append(f'<div class="lane" style="width:{width:.0f}px;height:{lane_height:.0f}px">')
        for task, level in positioned_tasks:
            left = max((task.abs_start - base) * scale, 0.0)
            task_width = max((task.abs_end - task.abs_start) * scale, 5.0)
            top = 7.0 + level * 32.0
            machine_key = task.machine_copy_labels[0].split(" #", 1)[0] if task.machine_copy_labels else NO_MACHINE_LABEL
            parts.append(
                _render_task(
                    task,
                    left=left,
                    width=task_width,
                    top=top,
                    process_color=process_colors.get(task.process, PALETTE[0]),
                    machine_color=machine_colors.get(machine_key, PALETTE[1]),
                )
            )
        parts.append("</div>")
    parts.append("</div></div></section>")
    return "".join(parts)


def _build_worker_lanes(order_workers: list[str], tasks: list[VisualTask]) -> list[tuple[str, list[VisualTask]]]:
    by_worker: dict[str, list[VisualTask]] = defaultdict(list)
    for task in tasks:
        by_worker[task.worker or "未知工人"].append(task)
    lane_names = sorted(set(order_workers) | set(by_worker))
    return [(name, by_worker.get(name, [])) for name in lane_names]


def _build_machine_lanes(machine_counts: dict[str, int], tasks: list[VisualTask]) -> list[tuple[str, list[VisualTask]]]:
    by_machine: dict[str, list[VisualTask]] = defaultdict(list)
    for task in tasks:
        for label in task.machine_copy_labels or (NO_MACHINE_LABEL,):
            by_machine[label].append(task)
    lane_names: list[str] = []
    if NO_MACHINE_LABEL in by_machine:
        lane_names.append(NO_MACHINE_LABEL)
    for machine in sorted(machine_counts):
        for copy_index in range(max(int(machine_counts[machine]), 1)):
            lane_names.append(f"{machine} #{copy_index + 1}")
    for label in sorted(by_machine):
        if label not in lane_names:
            lane_names.append(label)
    return [(name, by_machine.get(name, [])) for name in lane_names]


def _render_cards(order: Any, solution: dict[str, Any], verify: dict[str, Any] | None, tasks: list[VisualTask]) -> str:
    days = sorted({task.day for task in tasks})
    max_finish = max((task.end_minute for task in tasks if task.day == max(days, default=0)), default=0.0)
    due_rows = due_requirements_by_product(order)
    max_due = max((due for rows in due_rows.values() for due, _qty in rows), default=0)
    required = required_quantity_by_product(order)
    net_required = net_required_by_product(order)
    demand_text = "；".join(
        f"{product}: 订单 {required.get(product, 0)} / 净需求 {net_required.get(product, 0)}"
        for product in sorted(required)
    ) or "无净需求"
    status = solution.get("status", "unknown")
    verify_status = (verify or {}).get("checker_status") or (verify or {}).get("status") or "未提供"
    machine_errors = (verify or {}).get("machine_error_count", "未提供")
    solver = solution.get("solver_method", "unknown")
    solve_seconds = solution.get("solve_seconds")
    day_text = f"Day {min(days)}-{max(days)}" if days else "无任务"
    rows = [
        ("Verify", verify_status, verify_status == "ok"),
        ("机器并发错误", machine_errors, machine_errors == 0),
        ("Solution", status, status in {"feasible", "optimal"}),
        ("任务数", len(tasks), False),
        ("排程范围", day_text, False),
        ("最大完成时间", f"Day {max(days)} {_fmt(max_finish)} min" if days else "无任务", False),
        ("订单期限", f"Day {max_due}" if max_due else "无期限", False),
        ("Solver", solver, False),
        ("耗时", f"{float(solve_seconds):.3f} s" if isinstance(solve_seconds, (int, float)) else "未提供", False),
        ("产品/需求", demand_text, False),
    ]
    return "<section class=\"cards\">" + "".join(
        f'<div class="card{" ok" if ok else ""}"><span>{_html(label)}</span><b>{_html(value)}</b></div>'
        for label, value, ok in rows
    ) + "</section>"


def _render_problem_summary(order: Any) -> str:
    required = required_quantity_by_product(order)
    net_required = net_required_by_product(order)
    inventory_rows = [
        f"{product}: 库存 {order.initial_inventory.get(product, 0)}，订单 {required.get(product, 0)}，净需求 {net_required.get(product, 0)}"
        for product in sorted(required)
    ]
    inventory_text = "；".join(inventory_rows) if inventory_rows else "无订单需求"
    parts = ['<section><h2>问题摘要</h2><div class="panel">', f"<p><b>库存抵扣：</b>{_html(inventory_text)}</p>"]
    for product in sorted(required):
        steps = order.processes.get(product, ())
        if not steps:
            continue
        parts.append(f"<h3>产品 {_html(product)}</h3><ol class=\"route\">")
        for step in steps:
            machines = ", ".join(step.equipment) if step.equipment else NO_MACHINE_LABEL
            workers = "、".join(step.eligible_workers)
            parts.append(
                "<li>"
                f"<b>{_html(step.step_index)}. {_html(step.name)}</b>："
                f"{_html(_fmt(step.duration_minutes))} min/件，"
                f"设备 {_html(machines)}，可选工人 {_html(workers)}"
                "</li>"
            )
        parts.append("</ol>")
    parts.append("</div></section>")
    return "".join(parts)


def _render_task_table(tasks: list[VisualTask]) -> str:
    rows = []
    for task in sorted(tasks, key=lambda item: (item.day, item.start_minute, item.end_minute, item.index)):
        step = "" if task.step_index is None else str(task.step_index)
        rows.append(
            "<tr>"
            f"<td>{task.index}</td>"
            f"<td>Day {task.day}</td>"
            f"<td>{_html(_fmt(task.start_minute))}-{_html(_fmt(task.end_minute))}</td>"
            f"<td>{_html(task.product_id)}</td>"
            f"<td>{_html(step)}</td>"
            f"<td>{_html(task.process)}</td>"
            f"<td>{task.quantity}</td>"
            f"<td>{_html(task.worker)}</td>"
            f"<td>{_html(', '.join(task.machine_copy_labels))}</td>"
            f"<td>{_html(_fmt(task.duration_minutes))}</td>"
            "</tr>"
        )
    return (
        '<section><h2>任务明细</h2><div class="table-wrap"><table><thead><tr>'
        "<th>#</th><th>Day</th><th>时间</th><th>产品</th><th>Step</th><th>工序</th>"
        "<th>数量</th><th>工人</th><th>机器</th><th>时长</th>"
        "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div></section>"
    )


def _render_sources(order_path: Path, solution_path: Path, verify_path: Path | None) -> str:
    verify_text = str(verify_path) if verify_path else "未提供"
    return (
        '<section><h2>文件来源</h2><div class="panel source">'
        f"<b>问题</b><span>{_html(order_path)}</span>"
        f"<b>解</b><span>{_html(solution_path)}</span>"
        f"<b>Verify</b><span>{_html(verify_text)}</span>"
        "</div></section>"
    )


def _safe_script_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def _product_requirements(order: Any, tasks: list[VisualTask]) -> dict[str, dict[str, Any]]:
    required = required_quantity_by_product(order)
    net_required = net_required_by_product(order)
    due_rows = due_requirements_by_product(order)
    products = set(required) | set(order.initial_inventory) | {task.product_id for task in tasks if task.product_id}
    return {
        product: {
            "required": int(required.get(product, 0)),
            "net_required": int(net_required.get(product, 0)),
            "initial_inventory": int(order.initial_inventory.get(product, 0)),
            "due": [{"day": int(day), "quantity": int(qty)} for day, qty in due_rows.get(product, [])],
        }
        for product in sorted(products)
    }


def _inventory_by_day(order: Any, tasks: list[VisualTask], days: list[int]) -> dict[str, list[dict[str, Any]]]:
    requirements = _product_requirements(order, tasks)
    routes = {
        product: tuple(sorted(steps, key=lambda item: item.step_index))
        for product, steps in order.processes.items()
    }
    produced_by_step_day: dict[tuple[str, int, int], int] = defaultdict(int)
    for task in tasks:
        if task.step_index is None:
            continue
        produced_by_step_day[(task.product_id, task.step_index, task.day)] += task.quantity

    result: dict[str, list[dict[str, Any]]] = {}
    products = set(requirements) | set(routes) | {task.product_id for task in tasks if task.product_id}
    for day in days:
        rows: list[dict[str, Any]] = []
        for product in sorted(products):
            info = requirements.get(
                product,
                {"required": 0, "net_required": 0, "initial_inventory": int(order.initial_inventory.get(product, 0)), "due": []},
            )
            steps = routes.get(product, ())
            if not steps:
                initial_inventory = int(info["initial_inventory"])
                rows.append(
                    {
                        "product_id": product,
                        "artifact": "成品",
                        "step_index": None,
                        "process": "成品",
                        "is_final": True,
                        "initial_inventory": initial_inventory,
                        "start_inventory": initial_inventory,
                        "produced_today": 0,
                        "consumed_today": 0,
                        "end_inventory": initial_inventory,
                        "required": int(info["required"]),
                        "net_required": int(info["net_required"]),
                        "end_remaining": max(int(info["required"]) - initial_inventory, 0),
                        "due": info["due"],
                    }
                )
                continue
            step_indices = [step.step_index for step in steps]
            for position, step in enumerate(steps):
                next_step_index = step_indices[position + 1] if position + 1 < len(step_indices) else None
                produced_before = sum(
                    qty
                    for (pid, step_index, output_day), qty in produced_by_step_day.items()
                    if pid == product and step_index == step.step_index and output_day < day
                )
                produced_today = int(produced_by_step_day.get((product, step.step_index, day), 0))
                if next_step_index is None:
                    consumed_before = 0
                    consumed_today = 0
                else:
                    consumed_before = sum(
                        qty
                        for (pid, step_index, output_day), qty in produced_by_step_day.items()
                        if pid == product and step_index == next_step_index and output_day < day
                    )
                    consumed_today = int(produced_by_step_day.get((product, next_step_index, day), 0))
                is_final = next_step_index is None
                initial_inventory = int(info["initial_inventory"]) if is_final else 0
                start_inventory = initial_inventory + produced_before - consumed_before
                end_inventory = start_inventory + produced_today - consumed_today
                required = int(info["required"]) if is_final else 0
                rows.append(
                    {
                        "product_id": product,
                        "artifact": "成品" if is_final else f"Step {step.step_index}产物",
                        "step_index": step.step_index,
                        "process": step.name,
                        "is_final": is_final,
                        "initial_inventory": initial_inventory,
                        "start_inventory": start_inventory,
                        "produced_today": produced_today,
                        "consumed_today": consumed_today,
                        "end_inventory": end_inventory,
                        "required": required,
                        "net_required": int(info["net_required"]) if is_final else 0,
                        "end_remaining": max(required - end_inventory, 0) if is_final else None,
                        "due": info["due"] if is_final else [],
                    }
                )
        result[str(day)] = rows
    return result


def _task_payload(task: VisualTask) -> dict[str, Any]:
    return {
        "index": task.index,
        "day": task.day,
        "start_minute": task.start_minute,
        "end_minute": task.end_minute,
        "product_id": task.product_id,
        "step_index": task.step_index,
        "process": task.process,
        "quantity": task.quantity,
        "worker": task.worker,
        "machines": list(task.machines),
        "machine_copy_labels": list(task.machine_copy_labels or (NO_MACHINE_LABEL,)),
        "duration_minutes": task.duration_minutes,
    }


def _build_case_payload(order_path: Path, solution_path: Path, verify_path: Path | None = None) -> dict[str, Any]:
    order = load_order(order_path)
    solution = _read_json(solution_path)
    verify = _read_json(verify_path) if verify_path and verify_path.exists() else None
    tasks = _assign_machine_copies(_flatten_tasks(solution), order.machines)
    case_id = solution.get("case_id") or order.case_id or solution_path.stem.replace(".solution", "")
    task_days = sorted({task.day for task in tasks})
    days = task_days or [1]
    verify_status = (verify or {}).get("checker_status") or (verify or {}).get("status") or "未提供"
    machine_errors = (verify or {}).get("machine_error_count", "未提供")
    requirements = _product_requirements(order, tasks)
    max_due = max((item.due_day for item in order.orders), default=0)
    errors = solution.get("errors") or (solution.get("summary") or {}).get("errors") or []
    if not isinstance(errors, list):
        errors = [errors]

    return {
        "case_id": case_id,
        "status": solution.get("status", "unknown"),
        "verify_status": verify_status,
        "machine_error_count": machine_errors,
        "solver_method": solution.get("solver_method", "unknown"),
        "strategy": solution.get("strategy"),
        "solve_seconds": solution.get("solve_seconds"),
        "summary": solution.get("summary") or {},
        "errors": [str(item) for item in errors],
        "days": days,
        "max_due_day": max_due,
        "workers": sorted(order.workers),
        "machines": order.machines,
        "requirements": requirements,
        "inventory_by_day": _inventory_by_day(order, tasks, days),
        "tasks": [_task_payload(task) for task in tasks],
        "routes": {
            product: [
                {
                    "step_index": step.step_index,
                    "process": step.name,
                    "duration_minutes": step.duration_minutes,
                    "machines": list(step.equipment),
                    "workers": list(step.eligible_workers),
                }
                for step in steps
            ]
            for product, steps in sorted(order.processes.items())
        },
        "source": {
            "order": str(order_path),
            "solution": str(solution_path),
            "verify": str(verify_path) if verify_path else None,
        },
    }


def _index_case_metadata(case_payload: dict[str, Any], output_path: Path) -> dict[str, Any]:
    task_count = len(case_payload["tasks"])
    return {
        "case_id": case_payload["case_id"],
        "status": case_payload["status"],
        "verify_status": case_payload["verify_status"],
        "task_count": task_count,
        "day_count": len(case_payload["days"]),
        "max_due_day": case_payload["max_due_day"],
        "html": output_path.name,
    }


def render_solution_html(order_path: Path, solution_path: Path, output_path: Path, verify_path: Path | None = None) -> dict[str, Any]:
    case_payload = _build_case_payload(order_path, solution_path, verify_path)
    case_id = case_payload["case_id"]
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    day_text = f"Day {min(case_payload['days'])}-{max(case_payload['days'])}" if case_payload["tasks"] else "无任务"

    css = """
:root{--bg:#f7f7f4;--paper:#fff;--ink:#222821;--muted:#667064;--line:#d9ded2;--strong:#b7c0b0;--ok:#25784a;--bad:#a23b3b;--focus:#315f83}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif}
header{padding:18px 24px 14px;background:#fbfbf8;border-bottom:1px solid var(--line)}
h1{margin:0 0 8px;font-size:24px;letter-spacing:0}
h2{font-size:18px;margin:0 0 10px}
h3{font-size:15px;margin:14px 0 6px}
.meta{display:flex;gap:8px 16px;flex-wrap:wrap;color:var(--muted);font-size:13px}
.explain{margin-top:12px;max-width:1180px;border-left:4px solid var(--focus);background:#eef3f4;padding:10px 12px;border-radius:6px;color:#27322e}
.explain b{margin-right:4px}
main{padding:16px 24px 28px}
.controls{display:flex;gap:10px;align-items:end;flex-wrap:wrap;margin-bottom:14px}
.control{display:grid;gap:5px;color:var(--muted);font-size:12px}
.control select{min-width:120px}
.cards{display:grid;grid-template-columns:repeat(6,minmax(130px,1fr));gap:10px;margin-bottom:14px}
.card{background:var(--paper);border:1px solid var(--line);border-radius:8px;padding:12px;min-height:70px}
.card span{display:block;color:var(--muted);font-size:12px;margin-bottom:7px}
.card b{display:block;font-size:17px;overflow-wrap:anywhere}
.ok b{color:var(--ok)}
section{margin:0 0 24px}
.panel{background:var(--paper);border:1px solid var(--line);border-radius:8px;padding:14px;overflow:hidden}
.scroll{overflow:auto;border:1px solid var(--line);border-radius:8px;background:#fff}
.timeline{display:grid;grid-template-columns:190px var(--chart-width);min-width:calc(190px + var(--chart-width))}
.axis-label,.lane-label{position:sticky;left:0;z-index:5;background:#f1f3ed;border-right:1px solid var(--strong)}
.axis-label{height:48px;padding:14px 12px;font-weight:700;color:var(--muted);border-bottom:1px solid var(--line)}
.axis{position:relative;height:48px;background:#fbfbf8;border-bottom:1px solid var(--line)}
.tick{position:absolute;top:0;bottom:0;border-left:1px solid #edf0e8;color:#687064;font-size:11px}
.tick.dayline{border-left-color:#aeb9a6}
.tick span{position:absolute;top:6px;left:4px;white-space:nowrap}
.lane-label{padding:7px 10px;border-bottom:1px solid var(--line);overflow:hidden}
.lane-label b{display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.lane-label span{display:block;color:var(--muted);font-size:12px;white-space:nowrap}
.lane{position:relative;border-bottom:1px solid var(--line);background-image:linear-gradient(to right,rgba(30,40,30,.06) 1px,transparent 1px);background-size:100px 100%}
.task{position:absolute;height:28px;border-radius:6px;border:1px solid color-mix(in srgb,var(--proc),#222 28%);border-left:5px solid var(--proc);background:color-mix(in srgb,var(--proc),white 78%);padding:2px 5px;overflow:hidden;white-space:nowrap;box-shadow:0 1px 1px rgba(0,0,0,.08);cursor:default}
.task:hover{outline:2px solid rgba(34,40,33,.28);outline-offset:2px;z-index:20}
body[data-color="machine"] .task{border-color:color-mix(in srgb,var(--mach),#222 28%);border-left-color:var(--mach);background:color-mix(in srgb,var(--mach),white 78%)}
.task span{display:block;font-size:11px;font-weight:700;line-height:1.1;overflow:hidden;text-overflow:ellipsis}
.task small{display:block;font-size:10px;color:#4f574d;overflow:hidden;text-overflow:ellipsis}
.toolbar{display:flex;justify-content:space-between;gap:12px;align-items:center;margin-bottom:10px}
.toolbar label{color:var(--muted)}
select{height:30px;border:1px solid var(--strong);border-radius:6px;background:white;padding:0 8px}
.empty{padding:18px;color:var(--muted);background:white;border:1px solid var(--line);border-radius:8px}
.route{margin:0 0 6px 18px;padding:0}
.route li{margin:4px 0}
.table-wrap{overflow:auto;border:1px solid var(--line);border-radius:8px}
table{border-collapse:separate;border-spacing:0;width:100%;min-width:980px;background:white}
th,td{padding:7px 9px;border-bottom:1px solid var(--line);text-align:left;white-space:nowrap}
th{position:sticky;top:0;background:#eef1e9;color:#475044;font-size:12px}
.inventory table{min-width:1260px}
.info-grid{display:grid;grid-template-columns:minmax(360px,.8fr) minmax(520px,1.2fr);gap:12px}
.info-grid h3{margin:0 0 8px}
.info-grid table{min-width:720px}
.source{display:grid;grid-template-columns:90px 1fr;gap:6px 10px;color:var(--muted);font-size:12px;overflow-wrap:anywhere}
.task-tooltip{position:fixed;z-index:9999;display:none;max-width:360px;padding:10px 12px;border:1px solid #9ea995;border-radius:8px;background:rgba(255,255,252,.98);box-shadow:0 12px 30px rgba(32,40,28,.18);color:#222821;font-size:13px;line-height:1.45;white-space:pre-line;pointer-events:none}
.task-tooltip b{display:block;margin-bottom:5px;font-size:14px}
@media(max-width:1100px){main,header{padding-left:16px;padding-right:16px}.cards{grid-template-columns:repeat(2,minmax(130px,1fr))}.info-grid{grid-template-columns:1fr}}
"""
    script = f"""
const CASE={_safe_script_json(case_payload)};
const WORKER_DAY_MINUTES={WORKER_DAY_MINUTES};
const NO_MACHINE_LABEL={_safe_script_json(NO_MACHINE_LABEL)};
const PALETTE={_safe_script_json(PALETTE)};
const body=document.body;
const daySelect=document.getElementById('daySelect');
const colorSelect=document.getElementById('colorSelect');
const taskTooltip=document.createElement('div');
taskTooltip.className='task-tooltip';
document.body.appendChild(taskTooltip);
function escapeHtml(value){{
  return String(value ?? '').replace(/[&<>"']/g, ch=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[ch]));
}}
function fmt(value,digits=2){{
  const number=Number(value);
  if(!Number.isFinite(number)) return String(value ?? '');
  if(Math.abs(number-Math.round(number))<1e-9) return String(Math.round(number));
  return number.toFixed(digits).replace(/\\.0+$/,'').replace(/(\\.\\d*?)0+$/,'$1');
}}
function colorMap(values){{
  const names=[...new Set(values.filter(Boolean))].sort();
  const map={{}};
  names.forEach((name,index)=>{{map[name]=PALETTE[index%PALETTE.length];}});
  return map;
}}
const processColors=colorMap(CASE.tasks.map(task=>task.process || '未知工序'));
const machineColors=colorMap(CASE.tasks.flatMap(task=>(task.machine_copy_labels || [NO_MACHINE_LABEL]).map(label=>label.split(' #')[0])));
function taskTooltipText(task){{
  const step=task.step_index ?? '?';
  const machines=(task.machine_copy_labels && task.machine_copy_labels.length ? task.machine_copy_labels : [NO_MACHINE_LABEL]).join(', ');
  const rows=[
    `任务 #${{task.index}}`,
    task.flow_lane ? `生产流：${{task.flow_lane}}` : null,
    `产品：${{task.product_id}}`,
    `工序：${{step}}. ${{task.process}}`,
    `数量：${{task.quantity}}`,
    `工人：${{task.worker || '未知'}}`,
    `机器：${{machines}}`,
    `时间：Day ${{task.day}} ${{fmt(task.start_minute)}}-${{fmt(task.end_minute)}} min`,
    `总时长：${{fmt(task.duration_minutes)}} min`
  ];
  return rows.filter(Boolean).join('\\n');
}}
function placeTaskTooltip(event){{
  const pad=14;
  taskTooltip.style.display='block';
  const rect=taskTooltip.getBoundingClientRect();
  let left=event.clientX+pad;
  let top=event.clientY+pad;
  if(left+rect.width>window.innerWidth-8) left=event.clientX-rect.width-pad;
  if(top+rect.height>window.innerHeight-8) top=event.clientY-rect.height-pad;
  taskTooltip.style.left=Math.max(8,left)+'px';
  taskTooltip.style.top=Math.max(8,top)+'px';
}}
function attachTooltip(element,task){{
  element.addEventListener('mouseenter',event=>{{
    const title=document.createElement('b');
    title.textContent='任务详情';
    const content=document.createElement('div');
    content.textContent=taskTooltipText(task);
    taskTooltip.textContent='';
    taskTooltip.append(title,content);
    placeTaskTooltip(event);
  }});
  element.addEventListener('mousemove',placeTaskTooltip);
  element.addEventListener('mouseleave',()=>{{taskTooltip.style.display='none';}});
}}
function laneStats(tasks){{
  const duration=tasks.reduce((total,task)=>total+Math.max(Number(task.end_minute)-Number(task.start_minute),0),0);
  return `${{tasks.length}} 项 / ${{fmt(duration)}} min`;
}}
function dayTasks(){{
  const day=Number(daySelect.value || CASE.days[0] || 1);
  return CASE.tasks.filter(task=>Number(task.day)===day).sort((a,b)=>a.start_minute-b.start_minute || a.end_minute-b.end_minute || a.index-b.index);
}}
function buildWorkerLanes(tasks){{
  const grouped=new Map();
  tasks.forEach(task=>{{
    const key=task.worker || '未知工人';
    if(!grouped.has(key)) grouped.set(key,[]);
    grouped.get(key).push(task);
  }});
  const names=[...grouped.keys()].sort((a,b)=>a.localeCompare(b,'zh-CN'));
  return names.map(name=>[name,grouped.get(name) || []]);
}}
function buildMachineLanes(tasks){{
  const grouped=new Map();
  tasks.forEach(task=>{{
    const labels=task.machine_copy_labels && task.machine_copy_labels.length ? task.machine_copy_labels : [NO_MACHINE_LABEL];
    labels.forEach(label=>{{
      if(!grouped.has(label)) grouped.set(label,[]);
      grouped.get(label).push(task);
    }});
  }});
  const names=[...grouped.keys()].sort((a,b)=>{{
    if(a===NO_MACHINE_LABEL) return -1;
    if(b===NO_MACHINE_LABEL) return 1;
    return a.localeCompare(b,'zh-CN');
  }});
  return names.map(name=>[name,grouped.get(name) || []]);
}}
function absStart(task){{
  return (Number(task.day)-1)*WORKER_DAY_MINUTES + Number(task.start_minute);
}}
function absEnd(task){{
  return (Number(task.day)-1)*WORKER_DAY_MINUTES + Number(task.end_minute);
}}
function compareTasks(a,b){{
  return absStart(a)-absStart(b)
    || Number(a.step_index ?? 0)-Number(b.step_index ?? 0)
    || absEnd(a)-absEnd(b)
    || Number(a.index)-Number(b.index);
}}
function assignFlowLanes(){{
  const grouped=new Map();
  CASE.tasks.forEach(task=>{{
    const product=task.product_id || '未知产品';
    if(!grouped.has(product)) grouped.set(product,[]);
    grouped.get(product).push(task);
  }});
  grouped.forEach((productTasks,product)=>{{
    const flows=[];
    [...productTasks].sort(compareTasks).forEach(task=>{{
      const step=Number(task.step_index);
      const start=absStart(task);
      let selected=null;
      if(Number.isFinite(step) && step>1){{
        const candidates=flows
          .filter(flow=>flow.lastStep===step-1 && flow.lastEnd<=start+1e-6)
          .sort((a,b)=>b.lastEnd-a.lastEnd || a.id-b.id);
        selected=candidates[0] || null;
      }}
      if(!selected){{
        selected={{id:flows.length+1,lastStep:0,lastEnd:-Infinity,tasks:[]}};
        flows.push(selected);
      }}
      selected.tasks.push(task);
      if(Number.isFinite(step)) selected.lastStep=step;
      selected.lastEnd=Math.max(selected.lastEnd,absEnd(task));
      task.flow_index=selected.id;
      task.flow_lane=`${{product}} #${{String(selected.id).padStart(2,'0')}}`;
    }});
  }});
}}
function buildTaskLanes(tasks){{
  const grouped=new Map();
  tasks.forEach(task=>{{
    const key=task.flow_lane || task.product_id || '未知产品';
    if(!grouped.has(key)) grouped.set(key,[]);
    grouped.get(key).push(task);
  }});
  const names=[...grouped.keys()].sort((a,b)=>{{
    const at=(grouped.get(a) || [{{}}])[0];
    const bt=(grouped.get(b) || [{{}}])[0];
    return String(at.product_id || '').localeCompare(String(bt.product_id || ''),'zh-CN')
      || Number(at.flow_index || 0)-Number(bt.flow_index || 0)
      || a.localeCompare(b,'zh-CN');
  }});
  return names.map(name=>[name,grouped.get(name) || []]);
}}
function axisHtml(width){{
  const scale=width/WORKER_DAY_MINUTES;
  let html='';
  for(let minute=0;minute<=WORKER_DAY_MINUTES;minute+=60){{
    html+=`<div class="tick ${{minute===0?'dayline':''}}" style="left:${{(minute*scale).toFixed(2)}}px"><span>${{minute}}</span></div>`;
  }}
  return html;
}}
function renderTask(task,left,width,top){{
  const step=task.step_index ?? '?';
  const machines=(task.machine_copy_labels && task.machine_copy_labels.length ? task.machine_copy_labels : [NO_MACHINE_LABEL]).join(', ');
  const machineKey=(task.machine_copy_labels && task.machine_copy_labels[0] ? task.machine_copy_labels[0].split(' #')[0] : NO_MACHINE_LABEL);
  const el=document.createElement('div');
  el.className='task';
  el.style.left=`${{left.toFixed(2)}}px`;
  el.style.width=`${{width.toFixed(2)}}px`;
  el.style.top=`${{top.toFixed(2)}}px`;
  el.style.setProperty('--proc',processColors[task.process || '未知工序'] || PALETTE[0]);
  el.style.setProperty('--mach',machineColors[machineKey] || PALETTE[1]);
  el.innerHTML=`<span>${{escapeHtml(`${{step}}. ${{task.process}} x${{task.quantity}}`)}}</span><small>${{escapeHtml(`${{task.product_id}} · ${{machines}}`)}}</small>`;
  attachTooltip(el,task);
  return el;
}}
function viewLanes(view,tasks){{
  if(view==='machine') return {{lanes:buildMachineLanes(tasks), laneTitle:'机器'}};
  if(view==='task') return {{lanes:buildTaskLanes(tasks), laneTitle:'生产流'}};
  return {{lanes:buildWorkerLanes(tasks), laneTitle:'工人'}};
}}
function renderTimeline(view,targetId){{
  const tasks=dayTasks();
  const {{lanes,laneTitle}}=viewLanes(view,tasks);
  const chart=document.getElementById(targetId);
  const width=1440;
  const scale=width/WORKER_DAY_MINUTES;
  if(tasks.length===0){{
    chart.innerHTML='<div class="empty">无排班任务</div>';
    return;
  }}
  chart.innerHTML=`<div class="scroll"><div class="timeline" style="--chart-width:${{width}}px"><div class="axis-label">${{laneTitle}}</div><div class="axis" style="width:${{width}}px">${{axisHtml(width)}}</div></div></div>`;
  const timeline=chart.querySelector('.timeline');
  lanes.forEach(([laneName,laneTasks])=>{{
    const sorted=[...laneTasks].sort((a,b)=>a.start_minute-b.start_minute || a.end_minute-b.end_minute || a.index-b.index);
    let positioned=[];
    let laneHeight=42;
    if(view==='task'){{
      positioned=sorted.map(task=>[task,0]);
    }} else {{
      const levels=[];
      sorted.forEach(task=>{{
        let level=levels.findIndex(until=>until<=task.start_minute);
        if(level<0){{level=levels.length;levels.push(-Infinity);}}
        levels[level]=task.end_minute;
        positioned.push([task,level]);
      }});
      laneHeight=Math.max(42,8+Math.max(levels.length,1)*32);
    }}
    const label=document.createElement('div');
    label.className='lane-label';
    label.style.height=`${{laneHeight}}px`;
    label.innerHTML=`<b>${{escapeHtml(laneName)}}</b><span>${{escapeHtml(laneStats(laneTasks))}}</span>`;
    const lane=document.createElement('div');
    lane.className='lane';
    lane.style.width=`${{width}}px`;
    lane.style.height=`${{laneHeight}}px`;
    positioned.forEach(([task,level])=>{{
      const left=Math.max(Number(task.start_minute)*scale,0);
      const taskWidth=Math.max((Number(task.end_minute)-Number(task.start_minute))*scale,5);
      lane.appendChild(renderTask(task,left,taskWidth,7+level*32));
    }});
    timeline.append(label,lane);
  }});
}}
function renderStaticCards(){{
  const cards=[
    ['Solution',CASE.status,CASE.status==='feasible' || CASE.status==='optimal'],
    ['Verify',CASE.verify_status,CASE.verify_status==='ok'],
    ['机器并发错误',CASE.machine_error_count,CASE.machine_error_count===0],
    ['总任务数',CASE.tasks.length,false],
    ['排程天数',CASE.days.length,false],
    ['订单期限',CASE.max_due_day ? `Day ${{CASE.max_due_day}}` : '无期限',false],
    ['Solver',CASE.solver_method || 'unknown',false],
    ['耗时',Number.isFinite(Number(CASE.solve_seconds)) ? `${{Number(CASE.solve_seconds).toFixed(3)}} s` : '未提供',false]
  ];
  document.getElementById('staticCards').innerHTML=cards.map(([label,value,ok])=>`<div class="card ${{ok?'ok':''}}"><span>${{escapeHtml(label)}}</span><b>${{escapeHtml(value)}}</b></div>`).join('');
}}
function renderDayCards(){{
  const day=String(daySelect.value || CASE.days[0] || 1);
  const tasks=dayTasks();
  const rows=CASE.inventory_by_day[day] || [];
  const finalRows=rows.filter(row=>row.is_final);
  const startRemaining=finalRows.reduce((total,row)=>total+Math.max(Number(row.required)-Number(row.start_inventory),0),0);
  const endRemaining=finalRows.reduce((total,row)=>total+Number(row.end_remaining || 0),0);
  const finalOutput=finalRows.reduce((total,row)=>total+Number(row.produced_today || 0),0);
  const wipEnd=rows.filter(row=>!row.is_final).reduce((total,row)=>total+Number(row.end_inventory || 0),0);
  const workers=new Set(tasks.map(task=>task.worker).filter(Boolean));
  const machines=new Set(tasks.flatMap(task=>task.machine_copy_labels || []).filter(label=>label && label!==NO_MACHINE_LABEL));
  const cards=[
    ['当前 Day',`Day ${{day}}`,false],
    ['当天任务',tasks.length,false],
    ['Day开始成品剩余',startRemaining,false],
    ['当天完成成品',finalOutput,false],
    ['Day结束成品剩余',endRemaining,false],
    ['Day结束在制品',wipEnd,false],
    ['当天工人',workers.size,false],
    ['当天机器',machines.size,false]
  ];
  document.getElementById('dayCards').innerHTML=cards.map(([label,value,ok])=>`<div class="card ${{ok?'ok':''}}"><span>${{escapeHtml(label)}}</span><b>${{escapeHtml(value)}}</b></div>`).join('');
}}
function dueText(items){{
  return (items || []).map(item=>`Day ${{item.day}} x${{item.quantity}}`).join('；');
}}
function renderProblemInfo(){{
  const target=document.getElementById('problemInfo');
  const requirementRows=Object.keys(CASE.requirements || {{}}).sort().map(product=>{{
    const row=CASE.requirements[product] || {{}};
    return `<tr><td>${{escapeHtml(product)}}</td><td>${{row.required ?? 0}}</td><td>${{row.initial_inventory ?? 0}}</td><td>${{row.net_required ?? 0}}</td><td>${{escapeHtml(dueText(row.due))}}</td></tr>`;
  }}).join('');
  const routeRows=Object.keys(CASE.routes || {{}}).sort().flatMap(product=>
    (CASE.routes[product] || []).map(step=>{{
      const artifact=step.step_index === (CASE.routes[product] || [])[((CASE.routes[product] || []).length)-1]?.step_index ? '成品' : `Step ${{step.step_index}}产物`;
      const machines=(step.machines || []).join('、') || NO_MACHINE_LABEL;
      const workers=(step.workers || []).join('、') || '未提供';
      return `<tr><td>${{escapeHtml(product)}}</td><td>${{escapeHtml(artifact)}}</td><td>${{escapeHtml(step.step_index)}}</td><td>${{escapeHtml(step.process)}}</td><td>${{fmt(step.duration_minutes)}} min/件</td><td>${{escapeHtml(machines)}}</td><td>${{escapeHtml(workers)}}</td></tr>`;
    }})
  ).join('');
  target.innerHTML=`<div class="info-grid">
    <div><h3>订单需求</h3><div class="table-wrap"><table><thead><tr><th>产品</th><th>订单需求</th><th>初始成品库存</th><th>净需求</th><th>交期</th></tr></thead><tbody>${{requirementRows || '<tr><td colspan="5">无订单需求</td></tr>'}}</tbody></table></div></div>
    <div><h3>工艺路线和资源</h3><div class="table-wrap"><table><thead><tr><th>产品</th><th>生成产物</th><th>Step</th><th>工序</th><th>单件耗时</th><th>机器</th><th>可选工人</th></tr></thead><tbody>${{routeRows || '<tr><td colspan="7">无工艺路线</td></tr>'}}</tbody></table></div></div>
  </div>`;
}}
function renderInventory(){{
  const day=String(daySelect.value || CASE.days[0] || 1);
  const rows=CASE.inventory_by_day[day] || [];
  const target=document.getElementById('inventory');
  if(rows.length===0){{target.innerHTML='<div class="empty">无订单需求</div>';return;}}
  target.innerHTML=`<div class="table-wrap"><table><thead><tr><th>产品</th><th>工序产物</th><th>Step</th><th>工序</th><th>初始库存</th><th>Day开始库存</th><th>当天生成</th><th>当天被下一工序消耗</th><th>Day结束库存</th><th>订单需求</th><th>净需求</th><th>成品订单剩余</th><th>交期</th></tr></thead><tbody>${{rows.map(row=>`<tr><td>${{escapeHtml(row.product_id)}}</td><td>${{escapeHtml(row.artifact)}}</td><td>${{escapeHtml(row.step_index ?? '')}}</td><td>${{escapeHtml(row.process)}}</td><td>${{row.initial_inventory}}</td><td>${{row.start_inventory}}</td><td>${{row.produced_today}}</td><td>${{row.consumed_today}}</td><td>${{row.end_inventory}}</td><td>${{row.is_final ? row.required : ''}}</td><td>${{row.is_final ? row.net_required : ''}}</td><td>${{row.is_final ? row.end_remaining : ''}}</td><td>${{escapeHtml(dueText(row.due))}}</td></tr>`).join('')}}</tbody></table></div>`;
}}
function renderTaskTable(){{
  const tasks=dayTasks();
  const target=document.getElementById('taskTable');
  if(tasks.length===0){{target.innerHTML='<div class="empty">无任务明细</div>';return;}}
  target.innerHTML=`<div class="table-wrap"><table><thead><tr><th>#</th><th>生产流</th><th>Day</th><th>时间</th><th>产品</th><th>Step</th><th>工序</th><th>数量</th><th>工人</th><th>机器</th><th>时长</th></tr></thead><tbody>${{tasks.map(task=>`<tr><td>${{task.index}}</td><td>${{escapeHtml(task.flow_lane || '')}}</td><td>Day ${{task.day}}</td><td>${{fmt(task.start_minute)}}-${{fmt(task.end_minute)}}</td><td>${{escapeHtml(task.product_id)}}</td><td>${{escapeHtml(task.step_index ?? '')}}</td><td>${{escapeHtml(task.process)}}</td><td>${{task.quantity}}</td><td>${{escapeHtml(task.worker)}}</td><td>${{escapeHtml((task.machine_copy_labels || []).join(', '))}}</td><td>${{fmt(task.duration_minutes)}}</td></tr>`).join('')}}</tbody></table></div>`;
}}
function renderErrors(){{
  const target=document.getElementById('errors');
  const errors=CASE.errors || [];
  if(!errors.length){{target.innerHTML='';return;}}
  target.innerHTML=`<section><h2>不可行/错误信息</h2><div class="panel">${{errors.map(error=>`<p>${{escapeHtml(error)}}</p>`).join('')}}</div></section>`;
}}
function renderAll(){{
  body.dataset.color=colorSelect.value;
  renderStaticCards();
  renderProblemInfo();
  renderDayCards();
  renderInventory();
  renderTimeline('worker','workerChart');
  renderTimeline('machine','machineChart');
  renderTimeline('task','taskChart');
  renderTaskTable();
  renderErrors();
}}
CASE.days.forEach(day=>{{
  const option=document.createElement('option');
  option.value=day;
  option.textContent=`Day ${{day}}`;
  daySelect.appendChild(option);
}});
daySelect.addEventListener('change',renderAll);
colorSelect.addEventListener('change',renderAll);
assignFlowLanes();
renderAll();
"""
    html_text = (
        "<!doctype html>\n"
        '<html lang="zh-CN"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{_html(case_id)} 排班可视化</title><style>{css}</style></head>\n"
        '<body data-color="process">'
        f"<header><h1>{_html(case_id)} 排班可视化</h1>"
        '<div class="meta">'
        f"<span>生成时间：{_html(generated_at)}</span>"
        f"<span>solution：{_html(case_payload['status'])}</span>"
        f"<span>verify：{_html(case_payload['verify_status'])}</span>"
        f"<span>机器并发错误：{_html(case_payload['machine_error_count'])}</span>"
        f"<span>排程：{_html(day_text)}</span>"
        "</div>"
        '<div class="explain"><b>说明：</b>每个色块是一道排产任务，长度表示加工时间；页面会同时展示工人、机器、生产流三张甘特图，分别用于检查人员占用、设备占用和工序顺序；甘特图下方的库存表显示每道工序产物在当天开始和结束时的余量。</div>'
        "</header><main>"
        '<section id="staticCards" class="cards"></section>'
        '<section><h2>任务和工艺信息</h2><div id="problemInfo"></div></section>'
        '<section class="controls">'
        '<label class="control">Day<select id="daySelect"></select></label>'
        '<label class="control">颜色<select id="colorSelect"><option value="process">按工序</option><option value="machine">按机器</option></select></label>'
        "</section>"
        '<section id="dayCards" class="cards"></section>'
        '<section><div class="toolbar"><h2>按工人看排程</h2></div><div id="workerChart"></div></section>'
        '<section><div class="toolbar"><h2>按机器看排程</h2></div><div id="machineChart"></div></section>'
        '<section><div class="toolbar"><h2>按生产流/工序看排程</h2></div><div id="taskChart"></div></section>'
        '<section class="inventory"><h2>工序产物库存</h2><div id="inventory"></div></section>'
        '<section><h2>当天任务顺序</h2><div id="taskTable"></div></section>'
        '<div id="errors"></div>'
        + _render_sources(order_path, solution_path, verify_path)
        + f"</main><script>{script}</script></body></html>\n"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_text, encoding="utf-8")
    return _index_case_metadata(case_payload, output_path)


def render_batch_index_html(output_path: Path, cases: list[dict[str, Any]], results_dir: Path) -> None:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    css = """
:root{--bg:#f7f7f4;--paper:#fff;--ink:#222821;--muted:#667064;--line:#d9ded2;--strong:#b7c0b0;--focus:#315f83;--ok:#25784a}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif}
header{padding:18px 24px 14px;background:#fbfbf8;border-bottom:1px solid var(--line)}
h1{margin:0 0 8px;font-size:24px}
.meta{display:flex;gap:8px 16px;flex-wrap:wrap;color:var(--muted);font-size:13px}
main{height:calc(100vh - 88px);display:grid;grid-template-rows:auto 1fr;gap:12px;padding:14px 18px 18px}
.controls{display:flex;gap:10px;align-items:end;flex-wrap:wrap;background:var(--paper);border:1px solid var(--line);border-radius:8px;padding:12px}
label{display:grid;gap:5px;color:var(--muted);font-size:12px}
input,select{height:32px;border:1px solid var(--strong);border-radius:6px;background:white;padding:0 9px;color:var(--ink)}
#caseSearch{width:260px}
#caseSelect{width:min(560px,70vw)}
.stat{min-width:96px;color:var(--muted);font-size:12px}
.stat b{display:block;color:var(--ink);font-size:16px}
iframe{width:100%;height:100%;border:1px solid var(--line);border-radius:8px;background:white}
@media(max-width:900px){main{height:auto;min-height:calc(100vh - 88px)}#caseSearch,#caseSelect{width:100%}.controls{display:grid;grid-template-columns:1fr}.stat{display:inline-block;margin-right:14px}iframe{height:78vh}}
"""
    script = f"""
const CASES={_safe_script_json(cases)};
const caseSearch=document.getElementById('caseSearch');
const statusFilter=document.getElementById('statusFilter');
const caseSelect=document.getElementById('caseSelect');
const frame=document.getElementById('caseFrame');
function escapeHtml(value){{
  return String(value ?? '').replace(/[&<>"']/g, ch=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[ch]));
}}
function filteredCases(){{
  const query=caseSearch.value.trim().toLowerCase();
  const status=statusFilter.value;
  return CASES.filter(item=>(!status || item.status===status) && (!query || item.case_id.toLowerCase().includes(query)));
}}
function renderOptions(preferred){{
  const rows=filteredCases();
  caseSelect.innerHTML=rows.map(item=>`<option value="${{escapeHtml(item.case_id)}}">${{escapeHtml(item.case_id)}} · ${{escapeHtml(item.status)}} · ${{item.task_count}} tasks · ${{item.day_count}} days</option>`).join('');
  const target=preferred && rows.some(item=>item.case_id===preferred) ? preferred : (rows.find(item=>item.task_count>0 && (item.status==='feasible' || item.status==='optimal')) || rows[0] || {{}}).case_id;
  if(target) caseSelect.value=target;
  document.getElementById('shownCount').textContent=rows.length;
  loadSelected();
}}
function loadSelected(){{
  const selected=CASES.find(item=>item.case_id===caseSelect.value);
  if(!selected){{frame.removeAttribute('src');return;}}
  document.getElementById('selectedStatus').textContent=selected.status;
  document.getElementById('selectedVerify').textContent=selected.verify_status;
  document.getElementById('selectedTasks').textContent=selected.task_count;
  frame.src=selected.html;
}}
caseSearch.addEventListener('input',()=>renderOptions(caseSelect.value));
statusFilter.addEventListener('change',()=>renderOptions(caseSelect.value));
caseSelect.addEventListener('change',loadSelected);
renderOptions();
"""
    statuses = sorted({str(case["status"]) for case in cases})
    status_options = '<option value="">全部</option>' + "".join(
        f'<option value="{_html(status)}">{_html(status)}</option>' for status in statuses
    )
    feasible_count = sum(1 for case in cases if case["status"] in {"feasible", "optimal"})
    verify_ok_count = sum(1 for case in cases if case["verify_status"] == "ok")
    html_text = (
        "<!doctype html>\n"
        '<html lang="zh-CN"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>排班结果浏览</title><style>{css}</style></head>"
        "<body><header><h1>排班结果浏览</h1><div class=\"meta\">"
        f"<span>生成时间：{_html(generated_at)}</span>"
        f"<span>结果目录：{_html(results_dir)}</span>"
        f"<span>订单数：{len(cases)}</span>"
        f"<span>可行/最优：{feasible_count}</span>"
        f"<span>verify ok：{verify_ok_count}</span>"
        "</div></header><main>"
        '<section class="controls">'
        '<label>搜索订单<input id="caseSearch" type="search" autocomplete="off"></label>'
        f'<label>状态<select id="statusFilter">{status_options}</select></label>'
        '<label>订单<select id="caseSelect"></select></label>'
        '<div class="stat"><span>显示</span><b id="shownCount">0</b></div>'
        '<div class="stat"><span>状态</span><b id="selectedStatus">-</b></div>'
        '<div class="stat"><span>Verify</span><b id="selectedVerify">-</b></div>'
        '<div class="stat"><span>任务</span><b id="selectedTasks">-</b></div>'
        "</section>"
        '<iframe id="caseFrame" title="排班可视化"></iframe>'
        f"</main><script>{script}</script></body></html>\n"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_text, encoding="utf-8")


def _solution_files_from_results_dir(results_dir: Path) -> list[Path]:
    solution_dir = results_dir / "solutions"
    if solution_dir.exists():
        return sorted(solution_dir.glob("*.solution.json"))
    return sorted(results_dir.glob("*.solution.json"))


def _default_output_dir(results_dir: Path) -> Path:
    if results_dir.parent.name == "raw_view" and results_dir.parent.parent.name == "results":
        return results_dir.parent.parent / "html_view" / results_dir.name
    return results_dir / "visualizations"


def _case_id_from_solution_path(path: Path) -> str:
    name = path.name
    if name.endswith(".solution.json"):
        return name[: -len(".solution.json")]
    return path.stem


def _resolve_order_path(solution: dict[str, Any], solution_path: Path, sample_dir: Path | None) -> Path:
    raw = solution.get("input_path") or solution.get("order_path")
    candidates: list[Path] = []
    if raw:
        path = Path(str(raw))
        if path.is_absolute():
            candidates.append(path)
        candidates.extend([Path.cwd() / path, solution_path.parent / path])
    case_id = solution.get("case_id") or _case_id_from_solution_path(solution_path)
    if sample_dir is not None:
        candidates.append(sample_dir / f"{case_id}.json")
    candidates.append(Path.cwd() / "raw_orders" / f"{case_id}.json")
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    raise FileNotFoundError(f"cannot resolve order JSON for {solution_path}")


def _infer_verify_path(solution_path: Path, results_dir: Path | None, explicit_verify: Path | None) -> Path | None:
    if explicit_verify is not None:
        return explicit_verify
    case_id = _case_id_from_solution_path(solution_path)
    candidates: list[Path] = []
    if results_dir is not None:
        candidates.extend(
            [
                results_dir / "verify" / f"{case_id}.verify.json",
                results_dir / "solutions" / f"{case_id}.verify.json",
            ]
        )
    candidates.extend(
        [
            solution_path.with_name(f"{case_id}.verify.json"),
            solution_path.with_suffix("").with_suffix(".verify.json"),
        ]
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert TianjinLLM solver solution JSON files into standalone HTML Gantt visualizations."
    )
    parser.add_argument("order_json", nargs="?", type=Path, help="Raw order JSON for single-case mode.")
    parser.add_argument("solution_json", nargs="?", type=Path, help="Solution JSON for single-case mode.")
    parser.add_argument("--verify-json", type=Path, help="Optional checker verify JSON for single-case mode.")
    parser.add_argument("-o", "--output", type=Path, help="Output HTML path for single-case mode.")
    parser.add_argument("--results-dir", type=Path, help="Batch mode: result directory containing solutions/*.solution.json.")
    parser.add_argument("--sample-dir", type=Path, help="Batch mode fallback directory for raw order JSON files.")
    parser.add_argument("--output-dir", type=Path, help="Batch mode output directory. Defaults to RESULTS_DIR/visualizations.")
    args = parser.parse_args()

    if args.results_dir:
        results_dir = args.results_dir.resolve()
        output_dir = args.output_dir or _default_output_dir(results_dir)
        solution_paths = _solution_files_from_results_dir(results_dir)
        if not solution_paths:
            raise FileNotFoundError(f"no *.solution.json files under {results_dir}")
        written = []
        index_cases = []
        for solution_path in solution_paths:
            solution = _read_json(solution_path)
            order_path = _resolve_order_path(solution, solution_path, args.sample_dir)
            verify_path = _infer_verify_path(solution_path, results_dir, None)
            case_id = solution.get("case_id") or _case_id_from_solution_path(solution_path)
            output_path = output_dir / f"{case_id}.html"
            index_cases.append(render_solution_html(order_path, solution_path, output_path, verify_path))
            written.append(output_path)
        index_path = output_dir / "index.html"
        render_batch_index_html(index_path, index_cases, results_dir)
        print(
            json.dumps(
                {"count": len(written), "output_dir": str(output_dir), "index": str(index_path)},
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    if args.order_json is None or args.solution_json is None:
        parser.error("provide order_json and solution_json, or use --results-dir")
    output_path = args.output or args.solution_json.with_suffix("").with_suffix(".html")
    render_solution_html(args.order_json, args.solution_json, output_path, args.verify_json)
    print(json.dumps({"output": str(output_path)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
