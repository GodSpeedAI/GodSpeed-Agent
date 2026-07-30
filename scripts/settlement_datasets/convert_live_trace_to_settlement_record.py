from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from scripts.settlement_datasets.adapter_base import (
    CANONICAL_FIELDS,
    EMPTY_LABELS,
    EMPTY_OUTCOME,
    make_empty_environment,
    make_empty_payment,
    make_empty_representational_state,
    read_records_jsonl,
    write_records_jsonl,
)

from godspeed_nav.trace_capture import (
    read_run_summary,
    read_trace_events,
    detect_duplicate_errors,
    detect_same_path_continuation,
    detect_low_cost_inspection_after_error,
)

from scripts.settlement_datasets.swe_seed_trace_reader import (
    read_swe_seed_hook_events,
    read_swe_seed_trace_record,
    to_trace_analysis_record,
)

ACTION_EVENT_TYPES = {
    "tool_call",
    "command",
    "file_edit",
    "model_message",
    "strategy_revision",
}

OBSERVATION_EVENT_TYPES = {
    "tool_result",
    "error",
    "test_run",
    "evaluator_result",
}


def validate_record(record: dict[str, Any]) -> list[str]:
    from scripts.settlement_datasets.adapter_base import (
        REQUIRED_LABELS_FIELDS,
        REQUIRED_OUTCOME_FIELDS,
        REQUIRED_PAYMENT_FIELDS,
        SettlementDatasetAdapter,
    )

    errors: list[str] = []
    for field in CANONICAL_FIELDS:
        if field not in record:
            errors.append(f"missing_required_field:{field}")

    payment = record.get("payment", {})
    for pf in REQUIRED_PAYMENT_FIELDS:
        if pf not in payment:
            errors.append(f"missing_payment_field:{pf}")

    outcome = record.get("outcome", {})
    for of_ in REQUIRED_OUTCOME_FIELDS:
        if of_ not in outcome:
            errors.append(f"missing_outcome_field:{of_}")

    labels = record.get("labels", {})
    for lf in REQUIRED_LABELS_FIELDS:
        if lf not in labels:
            errors.append(f"missing_labels_field:{lf}")

    return errors


def extract_actions(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for e in events:
        if e.get("event_type") in ACTION_EVENT_TYPES:
            actions.append(
                {
                    "action_type": e["event_type"],
                    "content": e.get("content", ""),
                    "turn_index": e.get("step_index", 0),
                    "tool_name": e.get("tool_name"),
                }
            )
    return actions


def extract_observations(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    for e in events:
        if e.get("event_type") in OBSERVATION_EVENT_TYPES:
            observations.append(
                {
                    "content": e.get("content", ""),
                    "turn_index": e.get("step_index", 0),
                    "tool_name": e.get("tool_name"),
                }
            )
    return observations


def extract_payment(events: list[dict[str, Any]]) -> dict[str, Any]:
    payment = make_empty_payment()
    payment["turns"] = len(events)
    payment["tool_calls"] = sum(1 for e in events if e.get("event_type") == "tool_call")
    payment["commands"] = sum(1 for e in events if e.get("event_type") == "command")
    payment["elapsed_steps"] = len(events)
    payment["error_count"] = sum(
        1
        for e in events
        if e.get("settlement_signals", {}).get("error_detected", False)
    )
    return payment


def extract_outcome(
    events: list[dict[str, Any]],
    summary: dict[str, Any] | None,
) -> dict[str, Any]:
    outcome: dict[str, Any] = dict(EMPTY_OUTCOME)

    if summary:
        final = summary.get("final_outcome", "unknown")
        outcome["success"] = final == "success"
        outcome["settlement_quality"] = summary.get("settlement_quality", "unknown")

    if not events:
        return outcome

    last = events[-1]
    last_signals = last.get("settlement_signals", {})
    if last_signals.get("task_complete"):
        if outcome["settlement_quality"] == "unknown":
            outcome["settlement_quality"] = "complete"
    if last_signals.get("success_signal"):
        outcome["success"] = True
        if outcome["settlement_quality"] == "unknown":
            outcome["settlement_quality"] = "high"
    if last_signals.get("failure_signal"):
        outcome["success"] = False
        if outcome["settlement_quality"] == "unknown":
            outcome["settlement_quality"] = "low"

    return outcome


def build_metadata(
    events: list[dict[str, Any]],
    summary: dict[str, Any] | None,
) -> dict[str, Any]:
    error_steps = sorted(
        e["step_index"]
        for e in events
        if e.get("settlement_signals", {}).get("error_detected")
    )
    strategy_revision_steps = sorted(
        e["step_index"]
        for e in events
        if e.get("settlement_signals", {}).get("strategy_revision_detected")
    )
    test_passed_steps = sorted(
        e["step_index"]
        for e in events
        if e.get("settlement_signals", {}).get("test_passed")
    )
    test_failed_steps = sorted(
        e["step_index"]
        for e in events
        if e.get("settlement_signals", {}).get("test_failed")
    )
    task_complete_steps = sorted(
        e["step_index"]
        for e in events
        if e.get("settlement_signals", {}).get("task_complete")
    )

    metadata: dict[str, Any] = {
        "trace_source": "live_harness_trace",
        "error_steps": error_steps,
        "strategy_revision_steps": strategy_revision_steps,
        "test_passed_steps": test_passed_steps,
        "test_failed_steps": test_failed_steps,
        "task_complete_steps": task_complete_steps,
        "same_path_continuation_after_second_error": detect_same_path_continuation(
            events
        ),
        "duplicate_errors": detect_duplicate_errors(events),
        "low_cost_inspection_after_error": detect_low_cost_inspection_after_error(
            events
        ),
    }

    if summary and summary.get("run_metadata"):
        metadata["run_metadata"] = summary["run_metadata"]

    return metadata


def convert_run(run_dir: Path) -> dict[str, Any]:
    events = read_trace_events(run_dir)
    summary = read_run_summary(run_dir)

    run_id = run_dir.name
    if summary:
        run_id = summary.get("run_id", run_id)

    domain = "harness"
    task_id = run_id
    desired_direction_statement = ""
    if summary and summary.get("run_metadata"):
        rm = summary["run_metadata"]
        domain = rm.get("domain", domain)
        task_id = rm.get("task_id", task_id)
        desired_direction_statement = rm.get("desired_direction", "")

    environment = make_empty_environment()
    environment["type"] = "harness"
    environment["has_runnable_feedback"] = True
    environment["feedback_type"] = "tool_output"

    record: dict[str, Any] = {
        "dataset": "live_harness_trace",
        "domain": domain,
        "task_id": task_id,
        "source_uri": f"live_harness_trace://{run_id}",
        "desired_direction": {
            "statement": desired_direction_statement,
            "source": "live_capture",
        },
        "environment": environment,
        "representational_state": make_empty_representational_state(),
        "payment": extract_payment(events),
        "affordance_path": {
            "actions": extract_actions(events),
            "observations": extract_observations(events),
        },
        "outcome": extract_outcome(events, summary),
        "labels": dict(EMPTY_LABELS),
        "metadata": build_metadata(events, summary),
    }

    return record


def convert_swe_seed_trace(
    trace_root: Path,
    trace_path: Path,
    hook_log_dir: Path | None,
    output_path: Path,
) -> None:
    record = read_swe_seed_trace_record(trace_root, trace_path)
    hook_events = (
        read_swe_seed_hook_events(hook_log_dir, record["trace_id"])
        if hook_log_dir is not None
        else []
    )
    analysis = to_trace_analysis_record(record, hook_events)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(analysis, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert a captured live harness trace into a canonical settlement record"
    )
    parser.add_argument(
        "--run-dir",
        default=None,
        help="Path to a live harness trace directory (e.g., data/settlement_datasets/live_harness_traces/<run_id>/)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output path for settlement_record.json (defaults to <run-dir>/settlement_record.json)",
    )
    parser.add_argument(
        "--swe-seed-trace-root",
        default=None,
        help="Repo root whose .agent-harness/traces/records/ holds an SWE_SEED trace export",
    )
    parser.add_argument(
        "--swe-seed-trace-path",
        default=None,
        help="Path to a single SWE_SEED TraceRecord JSON inside the canonical records dir",
    )
    parser.add_argument(
        "--swe-seed-hook-log-dir",
        default=None,
        help="Directory of SWE_SEED events-*.jsonl hook logs to correlate with the trace",
    )
    args = parser.parse_args()

    if args.swe_seed_trace_path:
        if not args.swe_seed_trace_root or not args.output:
            parser.error(
                "--swe-seed-trace-path requires --swe-seed-trace-root and --output"
            )
        convert_swe_seed_trace(
            Path(args.swe_seed_trace_root),
            Path(args.swe_seed_trace_path),
            Path(args.swe_seed_hook_log_dir) if args.swe_seed_hook_log_dir else None,
            Path(args.output),
        )
        print(f"Wrote SWE_SEED provisional analysis record -> {args.output}")
        return

    if not args.run_dir:
        parser.error("--run-dir is required (or use the SWE_SEED trace flags)")

    run_dir = Path(args.run_dir)
    if not run_dir.is_dir():
        print(f"Error: run-dir is not a directory: {run_dir}", file=sys.stderr)
        sys.exit(1)

    events_path = run_dir / "events.jsonl"
    if not events_path.exists():
        print(f"Error: events.jsonl not found in {run_dir}", file=sys.stderr)
        sys.exit(1)

    record = convert_run(run_dir)

    validation_errors = validate_record(record)
    if validation_errors:
        print(
            f"Validation errors in converted record: {validation_errors}",
            file=sys.stderr,
        )
        sys.exit(1)

    output_path = (
        Path(args.output) if args.output else run_dir / "settlement_record.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(record, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(f"Wrote settlement record -> {output_path}")


if __name__ == "__main__":
    main()
