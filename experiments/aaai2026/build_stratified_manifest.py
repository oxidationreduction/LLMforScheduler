#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from common import SCHEMA_VERSION, read_json, relpath, write_json


def stable_key(seed: int, case_id: str) -> tuple[str, str]:
    digest = hashlib.sha256(f"{seed}:{case_id}".encode("utf-8")).hexdigest()
    return digest, case_id


def largest_remainder_quotas(stratum_sizes: dict[tuple[str, str], int], sample_size: int) -> dict[tuple[str, str], int]:
    total = sum(stratum_sizes.values())
    if sample_size <= 0:
        raise ValueError("--sample-size must be positive")
    if sample_size > total:
        raise ValueError(f"--sample-size {sample_size} exceeds source case count {total}")

    rows = []
    base_total = 0
    for key, size in sorted(stratum_sizes.items()):
        raw = size * sample_size / total
        base = math.floor(raw)
        base_total += base
        rows.append((key, size, base, raw - base))

    quotas = {key: base for key, _size, base, _remainder in rows}
    remaining = sample_size - base_total
    ranked = sorted(rows, key=lambda row: (-row[3], -row[1], row[0]))
    for key, _size, _base, _remainder in ranked[:remaining]:
        quotas[key] += 1
    return quotas


def build_stratified_manifest(source: dict[str, Any], sample_size: int, seed: int) -> dict[str, Any]:
    strata: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for case in source.get("cases", []):
        split = str(case.get("split", "unknown"))
        difficulty = str(case.get("difficulty_bucket", "unknown"))
        strata[(split, difficulty)].append(case)

    quotas = largest_remainder_quotas({key: len(rows) for key, rows in strata.items()}, sample_size)
    selected: list[dict[str, Any]] = []
    stratum_counts: dict[str, dict[str, int]] = {}
    for key in sorted(strata):
        rows = sorted(strata[key], key=lambda case: stable_key(seed, str(case["case_id"])))
        sample_count = quotas[key]
        selected.extend(rows[:sample_count])
        stratum_counts[f"{key[0]}/{key[1]}"] = {
            "source_count": len(rows),
            "sample_count": sample_count,
        }

    split_counts = Counter(str(case.get("split", "unknown")) for case in selected)
    eval_group_counts = Counter(
        str(group)
        for case in selected
        for group in case.get("eval_groups", [])
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "parent_manifest": source.get("parent_manifest") or source.get("source_manifest") or None,
        "source_case_count": source.get("case_count", len(source.get("cases", []))),
        "seed": seed,
        "sample_size": sample_size,
        "case_count": len(selected),
        "split_counts": dict(sorted(split_counts.items())),
        "eval_group_counts": dict(sorted(eval_group_counts.items())),
        "raw_orders_dir": source.get("raw_orders_dir"),
        "reference_results_dir": source.get("reference_results_dir"),
        "sampling_policy": {
            "source": "full split manifest",
            "strata": ["split", "difficulty_bucket"],
            "quota": "largest_remainder",
            "within_stratum_order": "sha256(seed:case_id)",
        },
        "stratum_counts": stratum_counts,
        "stratification_policy": source.get("stratification_policy"),
        "cases": selected,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a deterministic stratified subset manifest.")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--sample-size", type=int, required=True)
    parser.add_argument("--seed", type=int, default=20260703)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    source = read_json(args.source)
    manifest = build_stratified_manifest(source, args.sample_size, args.seed)
    manifest["parent_manifest"] = relpath(args.source)
    write_json(args.out, manifest)
    print(
        json.dumps(
            {
                "out": str(args.out),
                "case_count": manifest["case_count"],
                "split_counts": manifest["split_counts"],
                "stratum_counts": manifest["stratum_counts"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
