#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Any, Iterable


NO_MACHINE_VALUES = {"", "无", "無", "none", "null", "n/a", "na", "?"}
NO_MACHINE_TOKENS = {value.lower() for value in NO_MACHINE_VALUES}


def clean_text(value: Any) -> str:
    return str(value).strip()


def is_no_machine(value: Any) -> bool:
    return clean_text(value).lower() in NO_MACHINE_TOKENS


def product_id_from_process_key(key: Any) -> str:
    text = clean_text(key)
    if text.endswith("工艺信息"):
        return text[: -len("工艺信息")]
    return text


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def numeric_summary(values: Iterable[float]) -> dict[str, float | int | None]:
    series = sorted(float(value) for value in values)
    if not series:
        return {
            "count": 0,
            "mean": None,
            "median": None,
            "min": None,
            "max": None,
            "p90": None,
        }
    p90_index = min(len(series) - 1, int(0.9 * (len(series) - 1)))
    return {
        "count": len(series),
        "mean": mean(series),
        "median": median(series),
        "min": series[0],
        "max": series[-1],
        "p90": series[p90_index],
    }


def compact_counter(counter: Counter[tuple[Any, ...]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key, count in counter.items():
        if count <= 1:
            continue
        rows.append({"key": list(key), "count": count})
    rows.sort(key=lambda row: (-int(row["count"]), row["key"]))
    return rows


def duplicate_values(values: Iterable[Any]) -> list[dict[str, Any]]:
    counter = Counter(clean_text(value) for value in values)
    rows = [{"value": key, "count": count} for key, count in counter.items() if count > 1]
    rows.sort(key=lambda row: (-int(row["count"]), row["value"]))
    return rows


def canonical_hash(data: Any) -> str:
    payload = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def analyze_one(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    order_rows = as_list(raw.get("当前订单信息"))
    processes = raw.get("产品工序") if isinstance(raw.get("产品工序"), dict) else {}
    inventory = raw.get("相关产品库存") if isinstance(raw.get("相关产品库存"), dict) else {}
    machines = as_list(raw.get("可使用设备信息"))
    workers = raw.get("每日可使用人员列表") if isinstance(raw.get("每日可使用人员列表"), dict) else {}

    order_counter: Counter[tuple[Any, ...]] = Counter()
    ordered_product_counter: Counter[str] = Counter()
    for row in order_rows:
        if not isinstance(row, dict):
            continue
        product_id = clean_text(row.get("产品名称"))
        order_counter[(product_id, row.get("需求量"), row.get("期限"))] += 1
        ordered_product_counter[product_id] += 1

    listed_machine_counter: Counter[str] = Counter()
    non_positive_machines: list[dict[str, Any]] = []
    for row in machines:
        if not isinstance(row, dict):
            continue
        machine_name = clean_text(row.get("设备名称"))
        if not machine_name:
            continue
        listed_machine_counter[machine_name] += 1
        try:
            count = int(row.get("数量", 0))
        except (TypeError, ValueError):
            count = 0
        if count <= 0:
            non_positive_machines.append({"machine": machine_name, "count": row.get("数量")})

    listed_machines = set(listed_machine_counter)
    listed_workers = {clean_text(worker) for worker in workers if clean_text(worker)}

    duplicate_worker_days: list[dict[str, Any]] = []
    empty_worker_schedules: list[str] = []
    for worker_name, days in workers.items():
        worker = clean_text(worker_name)
        day_values = as_list(days)
        if not day_values:
            empty_worker_schedules.append(worker)
        repeated_days = duplicate_values(day_values)
        if repeated_days:
            duplicate_worker_days.append({"worker": worker, "duplicate_days": repeated_days})

    required_machines: set[str] = set()
    required_workers: set[str] = set()
    missing_machine_refs: list[dict[str, Any]] = []
    missing_worker_refs: list[dict[str, Any]] = []
    empty_process_products: list[str] = []
    duplicate_process_rows: list[dict[str, Any]] = []
    duplicate_step_indexes: list[dict[str, Any]] = []
    duplicate_step_names: list[dict[str, Any]] = []
    steps_per_product: list[int] = []
    eligible_workers_per_step: list[int] = []
    real_machines_per_step: list[int] = []

    for process_key, raw_steps in processes.items():
        product_id = product_id_from_process_key(process_key)
        steps = as_list(raw_steps)
        steps_per_product.append(len(steps))
        if not steps:
            empty_process_products.append(product_id)
            continue

        row_identity_counter: Counter[tuple[Any, ...]] = Counter()
        index_counter: Counter[str] = Counter()
        name_counter: Counter[str] = Counter()
        for step in steps:
            if not isinstance(step, dict):
                continue
            step_index = clean_text(step.get("序号"))
            process_name = clean_text(step.get("工序"))
            index_counter[step_index] += 1
            name_counter[process_name] += 1
            row_identity_counter[(step_index, process_name)] += 1

            machines_needed = [
                clean_text(machine)
                for machine in as_list(step.get("所用设备"))
                if clean_text(machine)
            ]
            real_machines = [machine for machine in machines_needed if not is_no_machine(machine)]
            real_machines_per_step.append(len(set(real_machines)))
            for machine in set(real_machines):
                required_machines.add(machine)
                if machine not in listed_machines:
                    missing_machine_refs.append(
                        {
                            "product": product_id,
                            "step_index": step_index,
                            "process": process_name,
                            "machine": machine,
                        }
                    )

            eligible_workers = [
                clean_text(worker)
                for worker in as_list(step.get("可选操作人员"))
                if clean_text(worker)
            ]
            eligible_workers_per_step.append(len(set(eligible_workers)))
            for worker in set(eligible_workers):
                required_workers.add(worker)
                if worker not in listed_workers:
                    missing_worker_refs.append(
                        {
                            "product": product_id,
                            "step_index": step_index,
                            "process": process_name,
                            "worker": worker,
                        }
                    )

        for row in compact_counter(row_identity_counter):
            duplicate_process_rows.append({"product": product_id, **row})
        for row in compact_counter(Counter((key,) for key, count in index_counter.items() for _ in range(count))):
            duplicate_step_indexes.append({"product": product_id, **row})
        for row in compact_counter(Counter((key,) for key, count in name_counter.items() for _ in range(count))):
            duplicate_step_names.append({"product": product_id, **row})

    inventory_products = {clean_text(product_id) for product_id in inventory if clean_text(product_id)}
    ordered_products = {clean_text(product_id) for product_id in ordered_product_counter}
    process_products = {product_id_from_process_key(key) for key in processes}

    return {
        "file": str(path),
        "sha256_canonical_json": canonical_hash(raw),
        "order_row_count": len(order_rows),
        "unique_ordered_product_count": len(ordered_products),
        "process_product_count": len(process_products),
        "process_step_count": sum(steps_per_product),
        "inventory_product_count": len(inventory_products),
        "listed_machine_count": len(listed_machines),
        "listed_worker_count": len(listed_workers),
        "has_empty_order_rows": len(order_rows) == 0,
        "has_empty_processes": len(processes) == 0,
        "steps_per_product": steps_per_product,
        "eligible_workers_per_step": eligible_workers_per_step,
        "real_machines_per_step": real_machines_per_step,
        "duplicate_order_rows": compact_counter(order_counter),
        "repeated_ordered_products": [
            {"product": key, "count": count}
            for key, count in sorted(ordered_product_counter.items())
            if count > 1
        ],
        "duplicate_machine_rows": [
            {"machine": key, "count": count}
            for key, count in sorted(listed_machine_counter.items())
            if count > 1
        ],
        "duplicate_worker_days": duplicate_worker_days,
        "duplicate_process_rows": duplicate_process_rows,
        "duplicate_step_indexes": duplicate_step_indexes,
        "duplicate_step_names": duplicate_step_names,
        "empty_process_products": sorted(empty_process_products),
        "empty_worker_schedules": sorted(empty_worker_schedules),
        "non_positive_machines": non_positive_machines,
        "missing_machine_refs": missing_machine_refs,
        "missing_worker_refs": missing_worker_refs,
        "unused_listed_machines": sorted(listed_machines - required_machines),
        "unused_listed_workers": sorted(listed_workers - required_workers),
        "ordered_products_without_process": sorted(ordered_products - process_products),
        "process_products_without_order": sorted(process_products - ordered_products),
        "ordered_products_without_inventory": sorted(ordered_products - inventory_products),
        "inventory_products_without_order": sorted(inventory_products - ordered_products),
    }


def collect_report(raw_orders_dir: Path) -> dict[str, Any]:
    files = sorted(raw_orders_dir.glob("*.json"))
    records: list[dict[str, Any]] = []
    parse_errors: list[dict[str, str]] = []

    for path in files:
        try:
            records.append(analyze_one(path))
        except Exception as exc:  # Keep scanning other orders and report the bad file.
            parse_errors.append({"file": str(path), "error": f"{type(exc).__name__}: {exc}"})

    hash_groups: dict[str, list[str]] = defaultdict(list)
    for record in records:
        hash_groups[str(record["sha256_canonical_json"])].append(str(record["file"]))
    duplicate_content_groups = [
        {"sha256_canonical_json": digest, "files": paths}
        for digest, paths in sorted(hash_groups.items())
        if len(paths) > 1
    ]

    def files_with(key: str) -> list[str]:
        return [str(record["file"]) for record in records if record.get(key)]

    def flatten(key: str) -> list[Any]:
        rows: list[Any] = []
        for record in records:
            rows.extend(record.get(key, []))
        return rows

    all_steps_per_product: list[int] = []
    all_workers_per_step: list[int] = []
    all_machines_per_step: list[int] = []
    products_per_schedule: list[int] = []
    process_products_per_schedule: list[int] = []
    steps_per_schedule: list[int] = []
    for record in records:
        products_per_schedule.append(int(record["unique_ordered_product_count"]))
        process_products_per_schedule.append(int(record["process_product_count"]))
        steps_per_schedule.append(int(record["process_step_count"]))
        all_steps_per_product.extend(int(value) for value in record["steps_per_product"])
        all_workers_per_step.extend(int(value) for value in record["eligible_workers_per_step"])
        all_machines_per_step.extend(int(value) for value in record["real_machines_per_step"])

    missing_machine_counter = Counter(
        row["machine"] for row in flatten("missing_machine_refs") if isinstance(row, dict)
    )
    missing_worker_counter = Counter(
        row["worker"] for row in flatten("missing_worker_refs") if isinstance(row, dict)
    )

    return {
        "input_dir": str(raw_orders_dir),
        "file_count": len(files),
        "parsed_file_count": len(records),
        "parse_errors": parse_errors,
        "duplicate_content_groups": duplicate_content_groups,
        "shape_checks": {
            "files_with_empty_order_rows": files_with("has_empty_order_rows"),
            "files_with_empty_processes": files_with("has_empty_processes"),
        },
        "duplicate_checks": {
            "files_with_duplicate_order_rows": files_with("duplicate_order_rows"),
            "files_with_repeated_ordered_products": files_with("repeated_ordered_products"),
            "files_with_duplicate_machine_rows": files_with("duplicate_machine_rows"),
            "files_with_duplicate_worker_days": files_with("duplicate_worker_days"),
            "files_with_duplicate_process_rows": files_with("duplicate_process_rows"),
            "files_with_duplicate_step_indexes": files_with("duplicate_step_indexes"),
            "files_with_duplicate_step_names": files_with("duplicate_step_names"),
        },
        "resource_checks": {
            "files_with_missing_machine_refs": files_with("missing_machine_refs"),
            "files_with_missing_worker_refs": files_with("missing_worker_refs"),
            "missing_machine_ref_count": len(flatten("missing_machine_refs")),
            "missing_worker_ref_count": len(flatten("missing_worker_refs")),
            "missing_machines": [
                {"machine": key, "ref_count": count}
                for key, count in missing_machine_counter.most_common()
            ],
            "missing_workers": [
                {"worker": key, "ref_count": count}
                for key, count in missing_worker_counter.most_common()
            ],
            "files_with_ordered_products_without_process": files_with("ordered_products_without_process"),
            "files_with_ordered_products_without_inventory": files_with("ordered_products_without_inventory"),
            "files_with_non_positive_machines": files_with("non_positive_machines"),
            "files_with_empty_worker_schedules": files_with("empty_worker_schedules"),
        },
        "stats": {
            "products_per_schedule": numeric_summary(products_per_schedule),
            "process_products_per_schedule": numeric_summary(process_products_per_schedule),
            "steps_per_schedule": numeric_summary(steps_per_schedule),
            "steps_per_product": numeric_summary(all_steps_per_product),
            "eligible_workers_per_step": numeric_summary(all_workers_per_step),
            "real_machines_per_step": numeric_summary(all_machines_per_step),
        },
        "per_file": records,
    }


def format_num(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def sample_list(values: list[Any], max_items: int) -> list[Any]:
    return values[:max(0, max_items)]


def print_summary(report: dict[str, Any], max_examples: int) -> None:
    stats = report["stats"]
    shape_checks = report["shape_checks"]
    duplicate_checks = report["duplicate_checks"]
    resource_checks = report["resource_checks"]

    print("# Raw Order Data Analysis")
    print(f"Input directory: {report['input_dir']}")
    print(f"JSON files: {report['file_count']}; parsed: {report['parsed_file_count']}")
    print(f"Parse errors: {len(report['parse_errors'])}")
    if report["parse_errors"]:
        for row in sample_list(report["parse_errors"], max_examples):
            print(f"  - {row['file']}: {row['error']}")

    duplicate_content_groups = report["duplicate_content_groups"]
    duplicate_content_file_count = sum(len(group["files"]) for group in duplicate_content_groups)
    print("\n## Shape Checks")
    for label, key in [
        ("Files with empty order rows", "files_with_empty_order_rows"),
        ("Files with empty process definitions", "files_with_empty_processes"),
    ]:
        values = shape_checks[key]
        print(f"{label}: {len(values)}")
        for value in sample_list(values, max_examples):
            print(f"  - {value}")

    print("\n## Duplicate Checks")
    print(f"Canonical duplicate content groups: {len(duplicate_content_groups)}")
    print(f"Files in canonical duplicate content groups: {duplicate_content_file_count}")
    for group in sample_list(duplicate_content_groups, max_examples):
        print(f"  - {group['sha256_canonical_json'][:12]}: {', '.join(group['files'])}")
    for label, key in [
        ("Files with duplicate order rows", "files_with_duplicate_order_rows"),
        ("Files with repeated ordered products", "files_with_repeated_ordered_products"),
        ("Files with duplicate machine rows", "files_with_duplicate_machine_rows"),
        ("Files with duplicate worker schedule days", "files_with_duplicate_worker_days"),
        ("Files with duplicate process rows", "files_with_duplicate_process_rows"),
        ("Files with duplicate process step indexes", "files_with_duplicate_step_indexes"),
        ("Files with duplicate process step names", "files_with_duplicate_step_names"),
    ]:
        values = duplicate_checks[key]
        print(f"{label}: {len(values)}")
        for value in sample_list(values, max_examples):
            print(f"  - {value}")

    print("\n## Resource Reference Checks")
    print(f"Missing machine references: {resource_checks['missing_machine_ref_count']}")
    print(f"Files with missing machine references: {len(resource_checks['files_with_missing_machine_refs'])}")
    for row in sample_list(resource_checks["missing_machines"], max_examples):
        print(f"  - {row['machine']}: {row['ref_count']}")
    print(f"Missing worker references: {resource_checks['missing_worker_ref_count']}")
    print(f"Files with missing worker references: {len(resource_checks['files_with_missing_worker_refs'])}")
    for row in sample_list(resource_checks["missing_workers"], max_examples):
        print(f"  - {row['worker']}: {row['ref_count']}")
    for label, key in [
        ("Files with ordered products missing process definitions", "files_with_ordered_products_without_process"),
        ("Files with ordered products missing inventory entries", "files_with_ordered_products_without_inventory"),
        ("Files with non-positive machine counts", "files_with_non_positive_machines"),
        ("Files with empty worker schedules", "files_with_empty_worker_schedules"),
    ]:
        values = resource_checks[key]
        print(f"{label}: {len(values)}")
        for value in sample_list(values, max_examples):
            print(f"  - {value}")

    print("\n## Aggregate Stats")
    for label, key in [
        ("Products per schedule/order file", "products_per_schedule"),
        ("Process-defined products per schedule/order file", "process_products_per_schedule"),
        ("Process steps per schedule/order file", "steps_per_schedule"),
        ("Process steps per product", "steps_per_product"),
        ("Eligible workers per process step", "eligible_workers_per_step"),
        ("Real machines per process step, excluding '无'", "real_machines_per_step"),
    ]:
        row = stats[key]
        print(
            f"{label}: count={row['count']}, mean={format_num(row['mean'])}, "
            f"median={format_num(row['median'])}, min={format_num(row['min'])}, "
            f"p90={format_num(row['p90'])}, max={format_num(row['max'])}"
        )


def resolve_default_raw_orders_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "raw_orders"


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze raw TianjinLLM order JSON files.")
    parser.add_argument(
        "--raw-orders-dir",
        type=Path,
        default=resolve_default_raw_orders_dir(),
        help="Directory containing raw order JSON files. Defaults to project raw_orders/.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=None,
        help="Optional path for the full machine-readable report.",
    )
    parser.add_argument(
        "--max-examples",
        type=int,
        default=20,
        help="Maximum number of examples printed for each issue type.",
    )
    args = parser.parse_args()

    raw_orders_dir = args.raw_orders_dir.resolve()
    report = collect_report(raw_orders_dir)
    print_summary(report, max_examples=args.max_examples)

    if args.output_json:
        output_path = args.output_json.resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nFull JSON report written to: {output_path}")


if __name__ == "__main__":
    main()
