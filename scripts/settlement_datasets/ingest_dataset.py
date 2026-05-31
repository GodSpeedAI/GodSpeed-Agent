from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scripts.settlement_datasets.adapter_base import write_records_jsonl
from scripts.settlement_datasets.registry import (
    get_adapter,
    get_all_adapters,
    available_datasets,
)


def ingest_dataset(
    dataset: str,
    limit: int | None = None,
    input_path: str | None = None,
    output_path: str = "data/settlement_datasets/raw_samples/{dataset}.jsonl",
) -> Path:
    adapter = get_adapter(dataset)

    if input_path:
        stream_kwargs = {"input_path": input_path}
    else:
        fixture_default = f"tests/fixtures/settlement_datasets/{dataset}/sample.jsonl"
        data_default = f"data/{dataset}/raw_samples/sample.jsonl"
        if Path(fixture_default).exists():
            stream_kwargs = {"input_path": fixture_default}
        elif Path(data_default).exists():
            stream_kwargs = {"input_path": data_default}
        else:
            stream_kwargs = {}

    output_path = output_path.replace("{dataset}", dataset)

    records = []
    for raw in adapter.stream(limit=limit, **stream_kwargs):
        record = adapter.to_settlement_record(raw)
        records.append(record)

    path = write_records_jsonl(records, output_path)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest dataset into normalized settlement records"
    )
    parser.add_argument(
        "--dataset",
        required=True,
        choices=["agenttrove", "swegym", "apibank", "webshop", "all"],
        help="Dataset to ingest",
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Max records to process"
    )
    parser.add_argument(
        "--input", default=None, help="Input JSONL path (overrides default)"
    )
    parser.add_argument("--output", default=None, help="Output JSONL path")

    args = parser.parse_args()

    datasets = available_datasets() if args.dataset == "all" else [args.dataset]

    for ds in datasets:
        output = args.output or f"data/settlement_datasets/raw_samples/{ds}.jsonl"
        path = ingest_dataset(
            ds, limit=args.limit, input_path=args.input, output_path=output
        )
        print(f"Ingested {ds} -> {path}")


if __name__ == "__main__":
    main()
