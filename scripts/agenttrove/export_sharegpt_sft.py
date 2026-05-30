from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

DEFAULT_ALLOWED_QUALITIES = {"clean_success", "recovered_success"}
DEFAULT_EXCLUDED_FAILURE_MODES = {
    "brittle_success",
    "tool_thrashing",
    "premature_closure",
    "missing_affordance",
}


def export_sharegpt_sft(
    settlement_path: str | Path,
    raw_path: str | Path,
    output_path: str | Path = "data/agenttrove/sft/sharegpt_clean.jsonl",
    allowed_qualities: set[str] | None = None,
    excluded_failure_modes: set[str] | None = None,
    allow_brittle: bool = False,
) -> Path:
    if allowed_qualities is None:
        allowed_qualities = DEFAULT_ALLOWED_QUALITIES
    if not allow_brittle:
        allowed_qualities = allowed_qualities - {"brittle_success"}
    if excluded_failure_modes is None:
        excluded_failure_modes = DEFAULT_EXCLUDED_FAILURE_MODES

    settlement_path = Path(settlement_path)
    raw_path = Path(raw_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    settlements_by_id: dict[str, dict[str, Any]] = {}
    with settlement_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            s = json.loads(line)
            settlements_by_id[s.get("trace_id", "")] = s

    kept = 0
    excluded = 0
    with output_path.open("w", encoding="utf-8") as out_handle:
        with raw_path.open("r", encoding="utf-8") as in_handle:
            for line in in_handle:
                if not line.strip():
                    continue
                trace = json.loads(line)
                trace_id = trace.get("trace_id", "")
                settlement = settlements_by_id.get(trace_id)

                if not settlement:
                    excluded += 1
                    continue

                sq = settlement.get("outcome", {}).get("settlement_quality", "unknown")
                if sq not in allowed_qualities:
                    excluded += 1
                    continue

                fm = settlement.get("cognitive_os_labels", {}).get("failure_mode")
                modes = fm if isinstance(fm, list) else [fm] if fm else []
                if any(m in excluded_failure_modes for m in modes):
                    excluded += 1
                    continue

                messages = trace.get("messages", [])
                conv = [
                    {"from": m.get("role", "unknown"), "value": m.get("content", "")}
                    for m in messages
                    if m.get("content", "").strip()
                ]
                if len(conv) < 2:
                    excluded += 1
                    continue

                record = {
                    "conversations": conv,
                    "source": trace.get("source", ""),
                    "teacher": trace.get("teacher", ""),
                    "trace_id": trace_id,
                    "settlement_quality": sq,
                }
                out_handle.write(json.dumps(record, sort_keys=True) + "\n")
                kept += 1

    print(f"SFT export: kept {kept}, excluded {excluded}")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Export clean ShareGPT SFT traces.")
    parser.add_argument(
        "--settlements",
        type=str,
        default="data/agenttrove/settlements/settlement_traces.jsonl",
    )
    parser.add_argument(
        "--raw", type=str, default="data/agenttrove/raw_samples/sample.jsonl"
    )
    parser.add_argument(
        "--output", type=str, default="data/agenttrove/sft/sharegpt_clean.jsonl"
    )
    parser.add_argument(
        "--allow-brittle",
        action="store_true",
        default=False,
        help="Include brittle successes.",
    )
    args = parser.parse_args()

    path = export_sharegpt_sft(
        args.settlements, args.raw, args.output, allow_brittle=args.allow_brittle
    )
    print(f"Exported to {path}")


if __name__ == "__main__":
    main()
