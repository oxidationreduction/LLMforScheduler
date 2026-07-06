#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import statistics
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
SOLVER_DIR = REPO_ROOT / "solver"
CHECKER_DIR = REPO_ROOT / "checker"
for path in (SOLVER_DIR, CHECKER_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


SCHEMA_VERSION = "aaai2026.v1"
NON_VERIFIABLE_STATUSES = {
    "infeasible",
    "infeasible_proven",
    "invalid_input",
    "model_invalid",
    "no_solution_found",
    "time_limit",
    "solver_unavailable",
    "failed",
}


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def jsonl_rows(path: Path) -> list[Any]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                rows.append(json.loads(text))
            except json.JSONDecodeError as exc:
                rows.append({"raw_text": text, "_jsonl_error": f"line {line_no}: {exc}"})
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def relpath(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def case_id_from_path(path: Path) -> str:
    name = path.name
    for suffix in (".solution.json", ".verify.json", ".json"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return path.stem


def solution_path(results_dir: Path, case_id: str) -> Path:
    return results_dir / "solutions" / f"{case_id}.solution.json"


def verify_path(results_dir: Path, case_id: str) -> Path:
    return results_dir / "solutions" / f"{case_id}.verify.json"


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * q
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def numeric_stats(values: list[Any]) -> dict[str, float | int | None]:
    clean: list[float] = []
    for value in values:
        if value is None:
            continue
        try:
            clean.append(float(value))
        except (TypeError, ValueError):
            continue
    if not clean:
        return {"count": 0, "mean": None, "median": None, "p90": None, "p95": None, "max": None}
    return {
        "count": len(clean),
        "mean": statistics.fmean(clean),
        "median": statistics.median(clean),
        "p90": percentile(clean, 0.90),
        "p95": percentile(clean, 0.95),
        "max": max(clean),
    }

