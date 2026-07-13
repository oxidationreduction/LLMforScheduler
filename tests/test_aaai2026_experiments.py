from __future__ import annotations

import argparse
import json

import pytest

from aggregate_metrics import aggregate_run
from build_h5_complexity_difficulty import (
    _bucket_assignments,
    build_h5_payload,
    check_existing,
    derive_features,
    generate_outputs,
)
from build_sft_data import build_sft_rows
from build_split_manifest import build_manifest
from build_stratified_manifest import build_stratified_manifest
from common import write_json
from llm_tool_schema import parse_text
from run_llm_tool_agent import execute, prepare
from run_full_benchmark import run_benchmark
from validate_direct_baseline import validate


def test_h5_derives_inventory_aware_operation_and_machine_metrics(tmp_path, minimal_order, write_order):
    order_path = write_order(
        tmp_path,
        minimal_order(quantity=3, inventory=1, due_day=2, machine_counts={"M1": 2, "M2": 1}),
    )
    from schedule_solver import load_order

    features = derive_features(load_order(order_path))

    assert features["operation_count"] == 4
    assert features["total_work_minutes"] == 30.0
    assert features["machine_load_ratio"] == pytest.approx(20.0 / (2 * 2 * 480))
    assert features["worker_day_count"] == 2


def test_h5_tertiles_preserve_equal_values():
    rows = [
        {"case_id": f"C{index}", "features": {"worker_day_count": value}}
        for index, value in enumerate([1, 1, 2, 2, 2, 3])
    ]

    assignments, policy = _bucket_assignments(rows, "worker_day_count")

    assert assignments["C0"] == assignments["C1"] == "low"
    assert {assignments["C2"], assignments["C3"], assignments["C4"]} == {"medium"}
    assert assignments["C5"] == "high"
    assert policy["nominal_bucket_case_counts"] == {"low": 2, "medium": 2, "high": 2}


def test_h5_join_rejects_duplicate_and_missing_cases(tmp_path):
    manifest_path = tmp_path / "manifest.json"
    summary_path = tmp_path / "summary.json"
    duplicate_manifest = {"case_count": 2, "cases": [{"case_id": "A"}, {"case_id": "A"}]}
    summary = {"case_count": 1, "cases": [{"case_id": "A"}]}

    with pytest.raises(ValueError, match="duplicate split_manifest case_id"):
        build_h5_payload(duplicate_manifest, summary, split_manifest_path=manifest_path, summary_path=summary_path)

    manifest = {"case_count": 1, "cases": [{"case_id": "A", "order_path": "missing.json"}]}
    missing_summary = {"case_count": 1, "cases": [{"case_id": "B"}]}
    with pytest.raises(ValueError, match="case-id join mismatch"):
        build_h5_payload(manifest, missing_summary, split_manifest_path=manifest_path, summary_path=summary_path)


def test_h5_generation_refuses_overwrite_and_check_is_read_only(tmp_path, minimal_order, write_json, write_order):
    order_path = write_order(tmp_path, minimal_order(case_id="SO-2024-08-0001-2"))
    manifest_path = tmp_path / "manifest.json"
    summary_path = tmp_path / "summary.json"
    manifest = {
        "case_count": 1,
        "cases": [
            {
                "case_id": "SO-2024-08-0001-2",
                "split": "test",
                "difficulty_bucket": "easy",
                "order_path": str(order_path),
                "load_ratio": 0.1,
            }
        ],
    }
    summary = {
        "case_count": 1,
        "cases": [{"case_id": "SO-2024-08-0001-2", "status": "feasible", "verify_status": "ok", "solve_seconds": 0.1}],
    }
    write_json(manifest_path, manifest)
    write_json(summary_path, summary)
    payload = build_h5_payload(manifest, summary, split_manifest_path=manifest_path, summary_path=summary_path)
    out_json, out_md = tmp_path / "h5.json", tmp_path / "h5.md"

    generate_outputs(payload, out_json, out_md)
    before = (out_json.read_bytes(), out_md.read_bytes())
    check_existing(payload, out_json, out_md)

    assert before == (out_json.read_bytes(), out_md.read_bytes())
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        generate_outputs(payload, out_json, out_md)


def test_split_manifest_is_date_based_and_tags_ood(tmp_path, minimal_order, valid_solution, write_json, write_order, write_solution):
    raw_orders = tmp_path / "raw_orders"
    results = tmp_path / "results"
    rows = []
    for case_id in ["SO-2023-01-0001-2", "SO-2024-03-0001-2", "SO-2024-08-0001-2", "SO-2025-01-0001-2"]:
        payload = minimal_order(case_id=case_id)
        write_order(raw_orders, payload)
        solution = valid_solution(case_id=case_id)
        solution_path = results / "solutions" / f"{case_id}.solution.json"
        verify_path = results / "solutions" / f"{case_id}.verify.json"
        write_json(solution_path, solution)
        write_json(verify_path, {"status": "ok"})
        rows.append({"case_id": case_id, "status": "feasible", "verify_status": "ok", "strategy": solution["strategy"], "solve_seconds": 0.1, "task_count": 2})
    write_json(results / "summary.json", {"case_count": 4, "cases": rows})

    manifest = build_manifest(raw_orders, results, seed=20260703)

    assert manifest["split_counts"] == {"train": 1, "dev": 1, "test": 2}
    ood = [case for case in manifest["cases"] if case["case_id"].startswith("SO-2025")]
    assert ood[0]["eval_groups"] == ["ood_recent"]


def test_aggregate_metrics_reads_existing_summary(tmp_path):
    manifest = {
        "cases": [
            {"case_id": "A", "split": "train", "difficulty_bucket": "easy"},
            {"case_id": "B", "split": "test", "difficulty_bucket": "hard"},
        ]
    }
    run_dir = tmp_path / "run"
    write_json(
        run_dir / "summary.json",
        {
            "case_count": 2,
            "cases": [
                {"case_id": "A", "status": "feasible", "verify_status": "ok", "solve_seconds": 1, "task_count": 2},
                {"case_id": "B", "status": "infeasible_proven", "verify_status": "not_applicable", "solve_seconds": 2, "task_count": 0},
            ],
        },
    )

    result = aggregate_run("timed_greedy", run_dir, manifest)

    assert result["overall"]["case_count"] == 2
    assert result["overall"]["verified_ok_count"] == 1
    assert result["overall"]["infeasible_proven_count"] == 1


def test_full_benchmark_runner_records_single_strategy_and_aggregates(tmp_path, minimal_order, write_json, write_order):
    order_path = write_order(tmp_path, minimal_order(case_id="SO-2025-01-0001-2"))
    manifest_path = tmp_path / "manifest.json"
    manifest = {
        "cases": [
            {
                "case_id": "SO-2025-01-0001-2",
                "split": "test",
                "difficulty_bucket": "easy",
                "order_path": str(order_path),
            }
        ]
    }
    write_json(manifest_path, manifest)
    output_dir = tmp_path / "run"

    summary = run_benchmark(
        manifest_path=manifest_path,
        output_dir=output_dir,
        time_limit_seconds=2,
        method="timed",
        unit_strategy="earliest_due",
        worker_strategy="least_used",
        day_strategy="forward",
        case_ids=None,
        split="test",
        limit=1,
    )

    assert summary["case_count"] == 1
    assert summary["strategy"] == {
        "unit_strategy": "earliest_due",
        "worker_strategy": "least_used",
        "day_strategy": "forward",
    }
    assert summary["cases"][0]["strategy"] == summary["strategy"]
    assert summary["verify_counts"] == {"ok": 1}

    result = aggregate_run("e2_smoke", output_dir, manifest)

    assert result["overall"]["case_count"] == 1
    assert result["overall"]["verified_ok_count"] == 1


def test_stratified_manifest_uses_largest_remainder_and_stable_hash():
    source_cases = []
    for split, difficulty, count in [
        ("train", "easy", 5),
        ("train", "hard", 3),
        ("test", "easy", 2),
    ]:
        for index in range(count):
            case_id = f"{split}-{difficulty}-{index}"
            source_cases.append(
                {
                    "case_id": case_id,
                    "split": split,
                    "difficulty_bucket": difficulty,
                    "order_path": f"raw_orders/{case_id}.json",
                }
            )
    source = {"case_count": len(source_cases), "cases": source_cases}

    manifest = build_stratified_manifest(source, sample_size=5, seed=20260703)

    assert manifest["case_count"] == 5
    assert manifest["stratum_counts"]["train/easy"]["sample_count"] == 3
    assert manifest["stratum_counts"]["train/hard"]["sample_count"] == 1
    assert manifest["stratum_counts"]["test/easy"]["sample_count"] == 1
    assert [case["case_id"] for case in manifest["cases"]] == [
        "test-easy-1",
        "train-easy-4",
        "train-easy-0",
        "train-easy-1",
        "train-hard-2",
    ]


def test_full_benchmark_runner_cpsat_aggregates_with_subset_manifest(tmp_path, minimal_order, write_json, write_order):
    order_path = write_order(tmp_path, minimal_order(case_id="SO-2025-01-0001-2"))
    manifest_path = tmp_path / "manifest.json"
    manifest = {
        "cases": [
            {
                "case_id": "SO-2025-01-0001-2",
                "split": "test",
                "difficulty_bucket": "easy",
                "order_path": str(order_path),
            }
        ]
    }
    write_json(manifest_path, manifest)
    output_dir = tmp_path / "run"

    summary = run_benchmark(
        manifest_path=manifest_path,
        output_dir=output_dir,
        time_limit_seconds=2,
        method="cpsat",
        unit_strategy=None,
        worker_strategy="least_used",
        day_strategy="forward",
        case_ids=None,
        split=None,
        limit=None,
    )

    assert summary["method"] == "cpsat"
    assert summary["case_count"] == 1
    assert summary["cases"][0]["solver_method"] != "timed_greedy"

    result = aggregate_run("e4_smoke", output_dir, manifest)

    assert result["overall"]["coverage_rate"] == 1.0
    assert result["overall"]["verify_invalid_count"] == 0


def test_tool_parser_accepts_strict_and_fenced_json():
    raw = """```json
{"tool_name":"select_solver_strategy","case_id":"SO-1","arguments":{"strategy":{"unit_strategy":"earliest_due","worker_strategy":"least_used","day_strategy":"forward"}}}
```"""

    row = parse_text(raw)

    assert row["parse_status"] == "ok"
    assert row["normalized_call"]["tool_name"] == "select_solver_strategy"


def test_tool_parser_rejects_prose_without_json():
    row = parse_text("I would use the solver now.")

    assert row["parse_status"] == "parse_failed"


def test_sft_builder_uses_train_dev_only(tmp_path, minimal_order, valid_solution, write_json, write_order):
    raw_orders = tmp_path / "raw_orders"
    source = tmp_path / "source"
    train_order = write_order(raw_orders, minimal_order(case_id="SO-2023-01-0001-2"))
    test_order = write_order(raw_orders, minimal_order(case_id="SO-2025-01-0001-2"))
    train_solution = valid_solution(case_id="SO-2023-01-0001-2")
    test_solution = valid_solution(case_id="SO-2025-01-0001-2")
    write_json(source / "summary.json", {"cases": [
        {"case_id": "SO-2023-01-0001-2", "status": "feasible", "verify_status": "ok", "strategy": train_solution["strategy"]},
        {"case_id": "SO-2025-01-0001-2", "status": "feasible", "verify_status": "ok", "strategy": test_solution["strategy"]},
    ]})
    manifest = {"cases": [
        {"case_id": "SO-2023-01-0001-2", "split": "train", "order_path": str(train_order)},
        {"case_id": "SO-2025-01-0001-2", "split": "test", "order_path": str(test_order)},
    ]}

    rows = build_sft_rows(manifest, source, {"train", "dev"})

    assert [row["case_id"] for row in rows] == ["SO-2023-01-0001-2"]
    assert rows[0]["target_tool_call"]["tool_name"] == "select_solver_strategy"


def test_direct_validator_reports_parse_failed(tmp_path):
    case_id = "SO-2025-01-0001-2"
    manifest = {"cases": [{"case_id": case_id, "split": "test", "eval_groups": []}]}
    direct = tmp_path / "direct"
    direct.mkdir()
    (direct / f"{case_id}.json").write_text("not json", encoding="utf-8")

    result = validate(manifest, direct, tmp_path, max_errors=5)

    assert result["parse_status_counts"] == {"parse_failed": 1}
    assert result["checker_status_counts"] == {"invalid": 1}


def test_llm_tool_agent_prepare_writes_test_prompts(tmp_path, minimal_order, write_json, write_order):
    order_path = write_order(tmp_path, minimal_order(case_id="SO-2025-01-0001-2"))
    manifest_path = tmp_path / "manifest.json"
    write_json(
        manifest_path,
        {
            "cases": [
                {
                    "case_id": "SO-2025-01-0001-2",
                    "split": "test",
                    "eval_groups": ["ood_recent"],
                    "order_path": str(order_path),
                },
                {
                    "case_id": "SO-2024-01-0001-2",
                    "split": "dev",
                    "eval_groups": [],
                    "order_path": str(order_path),
                },
            ]
        },
    )
    out = tmp_path / "prompts.jsonl"

    prepare(argparse.Namespace(split_manifest=manifest_path, split="test", out=out))

    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert [row["case_id"] for row in rows] == ["SO-2025-01-0001-2"]
    assert "messages" in rows[0]


def test_llm_tool_agent_execute_rejects_direct_schedule_and_aggregates(tmp_path, minimal_order, write_json, write_order):
    order_path = write_order(tmp_path, minimal_order(case_id="SO-2025-01-0001-2"))
    manifest_path = tmp_path / "manifest.json"
    manifest = {
        "cases": [
            {
                "case_id": "SO-2025-01-0001-2",
                "split": "test",
                "difficulty_bucket": "easy",
                "eval_groups": [],
                "order_path": str(order_path),
            },
            {
                "case_id": "SO-2025-01-0002-2",
                "split": "test",
                "difficulty_bucket": "easy",
                "eval_groups": [],
                "order_path": str(order_path),
            },
        ]
    }
    write_json(manifest_path, manifest)
    responses = tmp_path / "responses.jsonl"
    responses.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "case_id": "SO-2025-01-0001-2",
                        "raw_text": json.dumps(
                            {
                                "tool_name": "select_solver_strategy",
                                "case_id": "SO-2025-01-0001-2",
                                "arguments": {
                                    "case_id": "SO-2025-01-0001-2",
                                    "strategy": {
                                        "unit_strategy": "earliest_due",
                                        "worker_strategy": "least_used",
                                        "day_strategy": "forward",
                                    },
                                },
                                "reason": "small case",
                            },
                            ensure_ascii=False,
                        ),
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "case_id": "SO-2025-01-0002-2",
                        "raw_text": json.dumps(
                            {
                                "case_id": "SO-2025-01-0002-2",
                                "status": "feasible",
                                "plan": [],
                            },
                            ensure_ascii=False,
                        ),
                    },
                    ensure_ascii=False,
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    output_dir = tmp_path / "e5"

    execute(
        argparse.Namespace(
            split_manifest=manifest_path,
            responses=responses,
            output_dir=output_dir,
            split="test",
            time_limit=2,
        )
    )

    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    metrics = json.loads((output_dir / "metrics.json").read_text(encoding="utf-8"))

    assert summary["case_count"] == 2
    assert summary["tool_call_ok_count"] == 1
    direct_row = next(row for row in summary["cases"] if row["case_id"] == "SO-2025-01-0002-2")
    assert direct_row["status"] == "no_solution_found"
    assert direct_row["solution_path"] is None
    overall = metrics["runs"]["e5_llm_tool_agent"]["overall"]
    assert overall["parse_ok_count"] == 1
    assert overall["tool_call_ok_count"] == 1
