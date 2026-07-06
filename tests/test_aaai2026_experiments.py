from __future__ import annotations

from aggregate_metrics import aggregate_run
from build_sft_data import build_sft_rows
from build_split_manifest import build_manifest
from common import write_json
from llm_tool_schema import parse_text
from validate_direct_baseline import validate


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
