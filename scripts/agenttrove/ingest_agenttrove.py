from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import random
import sys
from pathlib import Path
from typing import Any


def find_trace_key(row: dict[str, Any]) -> str:
    for cand in ("messages", "conversations"):
        if cand in row and isinstance(row[cand], list):
            return cand
    for key, value in row.items():
        if isinstance(value, list) and value and isinstance(value[0], dict):
            if "content" in value[0] or "role" in value[0] or "value" in value[0]:
                return key
    raise KeyError("No conversation-like column found in dataset row.")


def normalize_turn(raw_turn: dict[str, Any] | Any) -> dict[str, Any]:
    if not isinstance(raw_turn, dict):
        return {"role": "unknown", "content": str(raw_turn)}
    role = str(raw_turn.get("role") or raw_turn.get("from") or "unknown")
    content = raw_turn.get("content")
    if content is None:
        content = raw_turn.get("value", "")
    content = "" if content is None else str(content)
    tool_name = raw_turn.get("tool_name") or raw_turn.get("name") or None
    metadata: dict[str, Any] = {}
    for key in raw_turn:
        if key not in ("role", "from", "content", "value", "tool_name", "name"):
            metadata[key] = raw_turn[key]
    result: dict[str, Any] = {"role": role, "content": content}
    if tool_name:
        result["tool_name"] = tool_name
    if metadata:
        result["metadata"] = metadata
    return result


def extract_metadata(row: dict[str, Any]) -> dict[str, Any]:
    meta_fields = [
        "original_source",
        "original_teacher",
        "model",
        "model_provider",
        "task",
        "task_id",
        "episode",
        "trajectory_id",
        "sandbox_id",
        "result",
    ]
    metadata: dict[str, Any] = {}
    for field in meta_fields:
        if field in row and row[field] is not None:
            metadata[field] = row[field]
    extra_keys = [
        k
        for k in row
        if k not in meta_fields and k not in ("messages", "conversations")
    ]
    for key in extra_keys:
        value = row[key]
        if not isinstance(value, (list, dict)):
            metadata[key] = value
    return metadata


def make_trace_id(row: dict[str, Any], index: int) -> str:
    for field in ("trajectory_id", "task_id", "id"):
        if field in row and row[field] is not None:
            raw = str(row[field])
            return f"at-{hashlib.sha256(raw.encode()).hexdigest()[:12]}"
    content_hash = hashlib.sha256(
        json.dumps(
            row.get("messages", row.get("conversations", [])), sort_keys=True
        ).encode()
    ).hexdigest()[:12]
    return f"at-{content_hash}"


def stream_traces(
    source: str = "open-thoughts/AgentTrove",
    split: str = "train",
    max_traces: int | None = None,
    source_filter: str | None = None,
    seed: int = 0,
) -> list[dict[str, Any]]:
    from datasets import load_dataset

    ds = load_dataset(source, split=split, streaming=True)
    rng = random.Random(seed)
    traces: list[dict[str, Any]] = []
    collected_for_filter: list[
        tuple[int, dict[str, Any], list[Any], dict[str, Any]]
    ] = []

    for index, row in enumerate(ds):
        if max_traces is not None and len(traces) >= max_traces and not source_filter:
            break

        try:
            trace_key = find_trace_key(row)
        except KeyError:
            continue

        raw_messages = row[trace_key]
        if not isinstance(raw_messages, list):
            continue

        metadata = extract_metadata(row)

        if source_filter:
            row_source = metadata.get("original_source", "")
            if row_source != source_filter:
                collected_for_filter.append((index, row, raw_messages, metadata))
                if (
                    len(collected_for_filter) > max_traces * 5
                    if max_traces
                    else len(collected_for_filter) > 10000
                ):
                    break
                continue

        normalized = [normalize_turn(t) for t in raw_messages]
        trace_id = make_trace_id(row, index)

        trace_record = {
            "trace_id": trace_id,
            "source": metadata.get("original_source", ""),
            "teacher": metadata.get("original_teacher", ""),
            "task_id": metadata.get("task_id", metadata.get("task", "")),
            "reward": row.get("reward"),
            "metadata": metadata,
            "messages": normalized,
        }
        traces.append(trace_record)

    if source_filter and max_traces:
        rng.shuffle(collected_for_filter)
        for index, row, raw_messages, metadata in collected_for_filter[:max_traces]:
            normalized = [normalize_turn(t) for t in raw_messages]
            trace_id = make_trace_id(row, index)
            traces.append(
                {
                    "trace_id": trace_id,
                    "source": metadata.get("original_source", ""),
                    "teacher": metadata.get("original_teacher", ""),
                    "task_id": metadata.get("task_id", metadata.get("task", "")),
                    "reward": row.get("reward"),
                    "metadata": metadata,
                    "messages": normalized,
                }
            )

    return traces


def write_jsonl(traces: list[dict[str, Any]], output_path: str | Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for trace in traces:
            handle.write(json.dumps(trace, sort_keys=True) + "\n")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest AgentTrove traces via streaming."
    )
    parser.add_argument(
        "--max-traces",
        type=int,
        default=100,
        help="Maximum number of traces to sample.",
    )
    parser.add_argument(
        "--source",
        type=str,
        default="open-thoughts/AgentTrove",
        help="HuggingFace dataset source.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/agenttrove/raw_samples/sample.jsonl",
        help="Output JSONL path.",
    )
    parser.add_argument("--seed", type=int, default=0, help="Random seed for sampling.")
    parser.add_argument(
        "--split", type=str, default="train", help="Dataset split to stream from."
    )
    parser.add_argument(
        "--source-filter",
        type=str,
        default=None,
        help="Filter by original_source field value.",
    )
    args = parser.parse_args()

    print(
        f"Streaming from {args.source} (split={args.split}, max_traces={args.max_traces})..."
    )
    traces = stream_traces(
        source=args.source,
        split=args.split,
        max_traces=args.max_traces,
        source_filter=args.source_filter,
        seed=args.seed,
    )
    path = write_jsonl(traces, args.output)
    print(f"Wrote {len(traces)} traces to {path}")


if __name__ == "__main__":
    main()
