from __future__ import annotations

import argparse

from scripts.settlement_datasets.adapter_base import read_records_jsonl
from scripts.settlement_datasets.live_shadow_policy_eval import replay_records_to_live_shadow
from scripts.settlement_datasets.run_scoped_paths import (
    add_run_scope_arguments,
    ensure_run_surface,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Replay live shadow policy evaluation from settlement traces"
    )
    parser.add_argument("--dataset", default="agenttrove")
    parser.add_argument("--input", default=None)
    parser.add_argument("--output", default="data/settlement_datasets/live_shadow")
    parser.add_argument("--disabled", action="store_true")
    add_run_scope_arguments(parser)
    args = parser.parse_args()

    scope = None
    if any([args.run_id, args.run_dir, args.input_run_dir, args.output_run_dir]):
        scope = ensure_run_surface(
            run_id=args.run_id,
            run_dir=args.run_dir,
            input_run_dir=args.input_run_dir,
            output_run_dir=args.output_run_dir,
        )

    input_path = args.input or (
        str(scope.dataset_jsonl_path("settlements", args.dataset, input_surface=True))
        if scope is not None
        else "data/settlement_datasets/evidence_accumulation_run/settlements/agenttrove.jsonl"
    )
    output_dir = (
        scope.shadow_dir / "live_shadow" if scope is not None else args.output
    )

    records = read_records_jsonl(input_path)
    paths = replay_records_to_live_shadow(
        records,
        output_dir=output_dir,
        enabled=not args.disabled,
    )
    print(f"Wrote live shadow events -> {paths['events']}")
    print(f"Wrote live shadow policy fires -> {paths['policy_fires']}")
    print(f"Wrote live shadow run summaries -> {paths['run_summaries']}")


if __name__ == "__main__":
    main()