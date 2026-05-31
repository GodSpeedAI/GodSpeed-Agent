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
from scripts.settlement_datasets.run_scoped_paths import (
    add_run_scope_arguments,
    ensure_run_surface,
)


def ingest_dataset(
    dataset: str,
    limit: int | None = None,
    input_path: str | None = None,
    output_path: str = "data/settlement_datasets/raw_samples/{dataset}.jsonl",
    raw_output_path: str | None = None,
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

    raw_records = []
    records = []
    for raw in adapter.stream(limit=limit, **stream_kwargs):
        raw_records.append(raw)
        record = adapter.to_settlement_record(raw)
        records.append(record)

    if raw_output_path is not None:
        write_records_jsonl(raw_records, raw_output_path.replace("{dataset}", dataset))
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
    parser.add_argument(
        "--raw-output",
        default=None,
        help="Optional raw trace JSONL path for run-scoped capture",
    )
    add_run_scope_arguments(parser, include_target_profile=True)

    args = parser.parse_args()
    scope = None
    if any([args.run_id, args.run_dir, args.input_run_dir, args.output_run_dir]):
        scope = ensure_run_surface(
            run_id=args.run_id,
            run_dir=args.run_dir,
            input_run_dir=args.input_run_dir,
            output_run_dir=args.output_run_dir,
        )

    datasets = available_datasets() if args.dataset == "all" else [args.dataset]

    for ds in datasets:
        output = args.output or (
            str(scope.dataset_jsonl_path("normalized", ds))
            if scope is not None
            else f"data/settlement_datasets/raw_samples/{ds}.jsonl"
        )
        raw_output = args.raw_output or (
            str(scope.dataset_jsonl_path("raw", ds)) if scope is not None else None
        )
        path = ingest_dataset(
            ds,
            limit=args.limit,
            input_path=args.input,
            output_path=output,
            raw_output_path=raw_output,
        )
        print(f"Ingested {ds} -> {path}")


if __name__ == "__main__":
    main()
