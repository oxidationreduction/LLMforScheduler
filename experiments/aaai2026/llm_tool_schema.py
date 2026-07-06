#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from common import SCHEMA_VERSION, jsonl_rows, write_json, write_jsonl


ALLOWED_TOOLS = {"summarize_order", "select_solver_strategy", "solve_order", "verify_solution"}
REQUIRED_ARGUMENTS = {
    "select_solver_strategy": {"strategy"},
    "solve_order": {"case_id", "time_limit_seconds"},
    "verify_solution": {"case_id"},
    "summarize_order": {"case_id"},
}
FENCED_JSON_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)


TOOL_CALL_SCHEMA: dict[str, Any] = {
    "schema_version": SCHEMA_VERSION,
    "type": "object",
    "required": ["tool_name", "arguments"],
    "properties": {
        "tool_name": {"enum": sorted(ALLOWED_TOOLS)},
        "case_id": {"type": "string"},
        "arguments": {"type": "object"},
        "strategy": {
            "type": "object",
            "required": ["unit_strategy", "worker_strategy", "day_strategy"],
        },
        "time_limit_seconds": {"type": "number"},
        "reason": {"type": "string"},
        "retry_of": {"type": ["string", "null"]},
    },
}


def raw_text_from_row(row: Any) -> str:
    if isinstance(row, dict):
        for key in ("raw_text", "text", "output", "content", "response"):
            if key in row:
                return str(row[key])
        if "tool_name" in row:
            return json.dumps(row, ensure_ascii=False)
    return str(row)


def extract_json_object(raw_text: str) -> tuple[dict[str, Any] | None, str | None, list[str]]:
    text = raw_text.strip()
    candidates: list[tuple[str, str]] = []
    if text.startswith("{") and text.endswith("}"):
        candidates.append((text, "full"))
    match = FENCED_JSON_RE.search(text)
    if match:
        candidates.append((match.group(1), "fenced"))
    errors: list[str] = []
    for candidate, span in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError as exc:
            errors.append(f"{span} JSON decode failed: {exc}")
            continue
        if isinstance(parsed, dict):
            return parsed, span, errors
        errors.append(f"{span} JSON is {type(parsed).__name__}, expected object")
    if not errors:
        errors.append("no strict JSON object or fenced JSON object found")
    return None, None, errors


def normalize_call(call: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    tool_name = call.get("tool_name")
    if tool_name not in ALLOWED_TOOLS:
        errors.append(f"tool_name must be one of {sorted(ALLOWED_TOOLS)}, got {tool_name!r}")
    arguments = call.get("arguments")
    if not isinstance(arguments, dict):
        errors.append("arguments must be an object")
        arguments = {}
    case_id = call.get("case_id") or arguments.get("case_id")
    if not case_id:
        errors.append("case_id is required at top level or in arguments")
    required = REQUIRED_ARGUMENTS.get(str(tool_name), set())
    missing = sorted(key for key in required if key not in arguments and key not in call)
    if missing:
        errors.append(f"missing required fields for {tool_name}: {missing}")
    if tool_name == "select_solver_strategy":
        strategy = call.get("strategy") or arguments.get("strategy")
        if not isinstance(strategy, dict):
            errors.append("select_solver_strategy requires strategy object")
        else:
            for key in ("unit_strategy", "worker_strategy", "day_strategy"):
                if not strategy.get(key):
                    errors.append(f"strategy.{key} is required")
            arguments = dict(arguments)
            arguments["strategy"] = strategy
    if errors:
        return None, errors
    normalized = {
        "tool_name": tool_name,
        "case_id": str(case_id),
        "arguments": arguments,
    }
    for optional in ("reason", "retry_of", "time_limit_seconds"):
        if optional in call:
            normalized[optional] = call[optional]
    return normalized, []


def parse_text(raw_text: str) -> dict[str, Any]:
    call, span, errors = extract_json_object(raw_text)
    if call is None:
        return {
            "case_id": None,
            "raw_text": raw_text,
            "parse_status": "parse_failed",
            "tool_name": None,
            "arguments": None,
            "errors": errors,
            "json_span": span,
            "normalized_call": None,
        }
    normalized, validation_errors = normalize_call(call)
    all_errors = errors + validation_errors
    return {
        "case_id": (normalized or call).get("case_id") or (call.get("arguments") or {}).get("case_id"),
        "raw_text": raw_text,
        "parse_status": "ok" if normalized is not None else "invalid",
        "tool_name": call.get("tool_name"),
        "arguments": call.get("arguments"),
        "errors": all_errors,
        "json_span": span,
        "normalized_call": normalized,
    }


def parse_file(path: Path) -> list[dict[str, Any]]:
    return [parse_text(raw_text_from_row(row)) for row in jsonl_rows(path)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Print or parse the AAAI LLM tool-call schema.")
    parser.add_argument("--print-schema", action="store_true")
    parser.add_argument("--parse", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    if args.print_schema:
        if args.out:
            write_json(args.out, TOOL_CALL_SCHEMA)
        print(json.dumps(TOOL_CALL_SCHEMA, ensure_ascii=False, indent=2))
        return
    if args.parse:
        rows = parse_file(args.parse)
        if args.out:
            write_jsonl(args.out, rows)
        else:
            for row in rows:
                print(json.dumps(row, ensure_ascii=False))
        return
    parser.error("provide --print-schema or --parse")


if __name__ == "__main__":
    main()

