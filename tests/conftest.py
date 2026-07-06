from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SOLVER_DIR = REPO_ROOT / "solver"
CHECKER_DIR = REPO_ROOT / "checker"
EXPERIMENT_DIR = REPO_ROOT / "experiments" / "aaai2026"
for path in (SOLVER_DIR, CHECKER_DIR, EXPERIMENT_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


@pytest.fixture
def write_json():
    def _write_json(path: Path, payload: Any) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    return _write_json


def _write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


@pytest.fixture
def minimal_order():
    def _minimal_order(
        *,
        case_id: str = "SO-2024-08-0001-2",
        quantity: int = 1,
        due_day: int = 1,
        inventory: int = 0,
        equipment: list[str] | None = None,
        machine_counts: dict[str, int] | None = None,
        worker_days: dict[str, list[int]] | None = None,
    ) -> dict[str, Any]:
        equipment_value = equipment or ["M1"]
        machine_counts_value = machine_counts or {"M1": 1, "M2": 1}
        worker_days_value = worker_days or {"W1": [1], "W2": [1]}
        return {
            "当前订单信息": [{"产品名称": "P1", "需求量": quantity, "期限": due_day}],
            "产品工序": {
                "P1工艺信息": [
                    {"序号": 1, "工序": "cut", "所用设备": equipment_value, "耗时": 10, "可选操作人员": ["W1", "W2"]},
                    {"序号": 2, "工序": "inspect", "所用设备": ["无"], "耗时": 5, "可选操作人员": ["W1", "W2"]},
                ]
            },
            "相关产品库存": {"P1": inventory},
            "可使用设备信息": [{"设备名称": name, "数量": count} for name, count in machine_counts_value.items()],
            "每日可使用人员列表": worker_days_value,
            "_case_id": case_id,
        }

    return _minimal_order


@pytest.fixture
def write_order():
    def _write_order(tmp_path: Path, payload: dict[str, Any]) -> Path:
        case_id = str(payload.pop("_case_id", "SO-2024-08-0001-2"))
        return _write_json(tmp_path / f"{case_id}.json", payload)

    return _write_order


@pytest.fixture
def valid_solution():
    return _valid_solution


@pytest.fixture
def write_solution():
    def _write_solution(tmp_path: Path, payload: dict[str, Any]) -> Path:
        case_id = str(payload.get("case_id", "SO-2024-08-0001-2"))
        return _write_json(tmp_path / f"{case_id}.solution.json", payload)

    return _write_solution


def _valid_solution(case_id: str = "SO-2024-08-0001-2", *, machines: list[str] | None = None) -> dict[str, Any]:
    machines = machines or ["M1"]
    return {
        "case_id": case_id,
        "status": "feasible",
        "solver_method": "timed_greedy",
        "solve_seconds": 0.01,
        "strategy": {"unit_strategy": "earliest_due", "worker_strategy": "least_used", "day_strategy": "forward"},
        "plan": [
            {
                "day": 1,
                "tasks": [
                    {
                        "start_minute": 0,
                        "end_minute": 10,
                        "worker": "W1",
                        "machines": machines,
                        "machine": "+".join(machines),
                        "material": "P1",
                        "process": "cut",
                        "step_index": 1,
                        "quantity": 1,
                        "unit_duration_minutes": 10,
                        "duration_minutes": 10,
                    },
                    {
                        "start_minute": 10,
                        "end_minute": 15,
                        "worker": "W2",
                        "machines": [],
                        "machine": "无",
                        "material": "P1",
                        "process": "inspect",
                        "step_index": 2,
                        "quantity": 1,
                        "unit_duration_minutes": 5,
                        "duration_minutes": 5,
                    },
                ],
            }
        ],
    }
