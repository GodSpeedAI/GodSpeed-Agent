from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.settlement_datasets.adapter_base import read_records_jsonl
from scripts.settlement_datasets.registry import available_datasets


def profile_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        return {"count": 0}

    dataset = records[0].get("dataset", "unknown")
    domain = records[0].get("domain", "unknown")

    settlement_qualities = Counter()
    failure_modes = Counter()
    domains = Counter()

    total_payment = {
        "turns": 0,
        "tool_calls": 0,
        "commands": 0,
        "page_actions": 0,
        "api_calls": 0,
        "error_count": 0,
    }
    total_confidence = 0.0
    high_confidence = 0

    for rec in records:
        outcome = rec.get("outcome", {})
        sq = outcome.get("settlement_quality", "unknown")
        settlement_qualities[sq] += 1

        conf = outcome.get("confidence", 0.0)
        total_confidence += conf
        if conf >= 0.65:
            high_confidence += 1

        labels = rec.get("labels", {})
        fm = labels.get("failure_mode")
        if fm:
            failure_modes[fm] += 1

        domains[rec.get("domain", "unknown")] += 1

        payment = rec.get("payment", {})
        for k in total_payment:
            total_payment[k] += payment.get(k, 0)

    count = len(records)
    avg_confidence = total_confidence / count if count else 0.0

    return {
        "dataset": dataset,
        "domain": domain,
        "count": count,
        "avg_confidence": round(avg_confidence, 3),
        "high_confidence_count": high_confidence,
        "settlement_quality_distribution": dict(settlement_qualities),
        "failure_mode_distribution": dict(failure_modes),
        "payment_summary": {k: round(v / count, 2) for k, v in total_payment.items()},
    }


def profile_dataset(
    dataset: str,
    input_path: str | None = None,
    output_dir: str = "data/settlement_datasets/profiles/",
) -> dict[str, Path]:
    if input_path is None:
        input_path = f"data/settlement_datasets/raw_samples/{dataset}.jsonl"

    records = read_records_jsonl(input_path)
    profile = profile_records(records)

    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)

    profile_path = output_dir_path / f"{dataset}_profile.json"
    with profile_path.open("w") as f:
        json.dump(profile, f, indent=2, sort_keys=True)

    return {"profile": profile_path}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Profile settlement records for a dataset"
    )
    parser.add_argument(
        "--dataset",
        required=True,
        choices=["agenttrove", "swegym", "apibank", "webshop", "all"],
    )
    parser.add_argument("--input", default=None)
    parser.add_argument("--output", default="data/settlement_datasets/profiles/")

    args = parser.parse_args()
    datasets = available_datasets() if args.dataset == "all" else [args.dataset]

    summary_rows = []
    for ds in datasets:
        result = profile_dataset(ds, input_path=args.input, output_dir=args.output)
        profile_path = result["profile"]

        from scripts.settlement_datasets.adapter_base import read_records_jsonl

        profile_data = json.loads(profile_path.read_text())
        print(
            f"Profiled {ds}: {profile_data['count']} records, avg_conf={profile_data['avg_confidence']}"
        )
        summary_rows.append(profile_data)

    if len(summary_rows) > 1:
        summary_path = Path(args.output) / "all_datasets_summary.csv"
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        with summary_path.open("w", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "dataset",
                    "domain",
                    "count",
                    "avg_confidence",
                    "high_confidence_count",
                ],
            )
            writer.writeheader()
            for row in summary_rows:
                writer.writerow({k: row.get(k, "") for k in writer.fieldnames})
        print(f"Wrote summary to {summary_path}")


if __name__ == "__main__":
    main()
