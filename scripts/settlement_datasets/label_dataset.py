from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.settlement_datasets.adapter_base import (
    read_records_jsonl,
    write_records_jsonl,
)
from scripts.settlement_datasets.registry import get_adapter, available_datasets


def label_records(
    records: list[dict],
    min_confidence: float = 0.0,
) -> list[dict]:
    labeled = []
    for rec in records:
        outcome_conf = rec.get("outcome", {}).get("confidence", 0.0)
        if outcome_conf >= min_confidence:
            labeled.append(rec)
    return labeled


def label_dataset(
    dataset: str,
    input_path: str | None = None,
    output_path: str | None = None,
    min_confidence: float = 0.0,
) -> Path:
    if input_path is None:
        input_path = f"data/settlement_datasets/raw_samples/{dataset}.jsonl"
    if output_path is None:
        output_path = f"data/settlement_datasets/settlements/{dataset}.jsonl"

    records = read_records_jsonl(input_path)
    labeled = label_records(records, min_confidence=min_confidence)

    path = write_records_jsonl(labeled, output_path)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Label and filter settlement records")
    parser.add_argument(
        "--dataset",
        required=True,
        choices=["agenttrove", "swegym", "apibank", "webshop", "all"],
    )
    parser.add_argument("--input", default=None)
    parser.add_argument("--output", default=None)
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.0,
        help="Minimum confidence to include",
    )

    args = parser.parse_args()
    datasets = available_datasets() if args.dataset == "all" else [args.dataset]

    for ds in datasets:
        path = label_dataset(
            ds,
            input_path=args.input,
            output_path=args.output,
            min_confidence=args.min_confidence,
        )
        records = read_records_jsonl(str(path))
        print(f"Labeled {ds}: {len(records)} records -> {path}")


if __name__ == "__main__":
    main()
