from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.settlement_datasets.adapter_base import (
    read_records_jsonl,
    write_records_jsonl,
)
from scripts.settlement_datasets.live_shadow_policy_eval import (
    LiveShadowPolicyEvaluator,
    normalize_live_run_event,
    validate_live_run_event,
)
from godspeed_nav.trace_capture import read_trace_events, read_run_summary


EVALUATOR_POLICY_MAP = {
    "require_reflection_before_continuing_after_second_unresolved_error": {
        "require_reflection_after_repeated_errors",
        "require_explicit_settlement_for_failure",
    },
}

TRACE_TO_SHADOW_EVENT_TYPE = {
    "model_message": "model_message",
    "tool_call": "tool_call",
    "tool_result": "tool_result",
    "error": "error",
    "final_answer": "final_answer",
    "task_complete": "task_complete",
    "evaluator_result": "evaluator_result",
    "strategy_revision": "model_message",
    "file_edit": "tool_call",
    "command": "tool_call",
    "test_run": "tool_result",
}


def _map_trace_event_to_shadow(trace_event: dict[str, Any]) -> dict[str, Any]:
    raw_type = trace_event.get("event_type", "model_message")
    mapped_type = TRACE_TO_SHADOW_EVENT_TYPE.get(raw_type, "model_message")
    content = str(trace_event.get("content", ""))
    signals = dict(trace_event.get("settlement_signals", {}) or {})
    if raw_type == "strategy_revision":
        signals["strategy_revision_detected"] = True
    return {
        "run_id": trace_event.get("run_id", ""),
        "step_index": int(trace_event.get("step_index", 0)),
        "timestamp": trace_event.get("timestamp", ""),
        "event_type": mapped_type,
        "content": content,
        "tool_name": trace_event.get("tool_name"),
        "metadata": dict(trace_event.get("metadata", {}) or {}),
        "settlement_signals": signals,
    }


def _resolve_evaluator_policy_ids(target_policy: str | None) -> set[str]:
    if target_policy is None:
        return set()
    return EVALUATOR_POLICY_MAP.get(target_policy, {target_policy})


def _compute_trigger_before_settlement(
    fires: list[dict[str, Any]],
    events: list[dict[str, Any]],
) -> bool:
    if not fires:
        return False
    fire_steps = {int(f["step_index"]) for f in fires}
    settlement_steps = {
        int(e["step_index"])
        for e in events
        if e.get("event_type") in {"final_answer", "task_complete"}
    }
    if not settlement_steps:
        return True
    min_fire = min(fire_steps)
    min_settlement = min(settlement_steps)
    return min_fire < min_settlement


def _infer_uncertainty_reasons(
    trace_event: dict[str, Any],
    fires: list[dict[str, Any]],
) -> list[str]:
    reasons: list[str] = []
    signals = trace_event.get("settlement_signals", {}) or {}
    content = str(trace_event.get("content", "")).lower()
    if signals.get("error_detected") and signals.get("success_signal"):
        reasons.append("conflicting_error_and_success_signals")
    if signals.get("test_passed") and signals.get("test_failed"):
        reasons.append("conflicting_test_signals")
    if not fires and signals.get("error_detected"):
        reasons.append("error_without_policy_fire")
    if "timeout" in content:
        reasons.append("timeout_may_mask_root_cause")
    return reasons


def _infer_post_fire_outcome(
    fires: list[dict[str, Any]],
    summary: dict[str, Any] | None,
) -> str:
    if not fires:
        return "no_fire"
    outcome = (summary or {}).get("final_outcome", "unknown")
    if outcome == "success":
        return "succeeded_without_intervention"
    if outcome == "failure":
        return "failed"
    return "unknown"


def evaluate_run(
    run_dir: Path,
    target_policy_ids: set[str],
) -> dict[str, Any]:
    trace_events = read_trace_events(run_dir)
    summary = read_run_summary(run_dir)
    run_id = (summary or {}).get("run_id", run_dir.name)

    shadow_events = [_map_trace_event_to_shadow(e) for e in trace_events]

    evaluator = LiveShadowPolicyEvaluator(
        enabled=True,
        target_policy_ids=target_policy_ids,
        run_metadata={"run_id": run_id},
    )

    all_fires: list[dict[str, Any]] = []
    for shadow_event in shadow_events:
        normalized = normalize_live_run_event(shadow_event)
        errors = validate_live_run_event(normalized)
        if errors:
            continue
        fires = evaluator.record_event(normalized)
        all_fires.extend(fires)

    trigger_before_settlement = _compute_trigger_before_settlement(
        all_fires, shadow_events
    )

    results: list[dict[str, Any]] = []
    for fire in all_fires:
        fire_step = int(fire["step_index"])
        matching_trace = None
        for te in trace_events:
            if int(te.get("step_index", 0)) == fire_step:
                matching_trace = te
                break
        uncertainty = _infer_uncertainty_reasons(matching_trace or fire, [fire])
        results.append(
            {
                "policy_id": fire["policy_id"],
                "would_fire": fire["would_fire"],
                "fire_timing": fire["fire_timing"],
                "recovery_opportunity": fire["recovery_opportunity"],
                "uncertainty_reasons": uncertainty,
                "post_fire_outcome": _infer_post_fire_outcome([fire], summary),
                "trigger_before_settlement": trigger_before_settlement,
                "trigger_evidence": fire.get("trigger_evidence", []),
                "shadow_action": fire.get("shadow_action", ""),
                "activation_status": "shadow_only",
                "enforced": False,
            }
        )

    if not all_fires:
        results.append(
            {
                "policy_id": ",".join(sorted(target_policy_ids))
                if target_policy_ids
                else "none",
                "would_fire": False,
                "fire_timing": "no_fire",
                "recovery_opportunity": False,
                "uncertainty_reasons": [],
                "post_fire_outcome": "no_fire",
                "trigger_before_settlement": False,
                "trigger_evidence": [],
                "shadow_action": "",
                "activation_status": "shadow_only",
                "enforced": False,
            }
        )

    return {
        "run_id": run_id,
        "run_dir": str(run_dir),
        "results": results,
        "total_fires": len(all_fires),
        "trigger_before_settlement": trigger_before_settlement,
        "summary": summary,
    }


def build_cross_run_summary(run_results: list[dict[str, Any]]) -> dict[str, Any]:
    total_runs = len(run_results)
    total_fires = sum(r["total_fires"] for r in run_results)
    fires_by_timing: dict[str, int] = {}
    fires_with_recovery = 0
    fires_before_settlement = 0

    for run in run_results:
        for result in run["results"]:
            if not result["would_fire"]:
                continue
            timing = result["fire_timing"]
            fires_by_timing[timing] = fires_by_timing.get(timing, 0) + 1
            if result["recovery_opportunity"]:
                fires_with_recovery += 1
        if run["trigger_before_settlement"]:
            fires_before_settlement += 1

    return {
        "total_runs": total_runs,
        "total_fires": total_fires,
        "fires_by_timing": fires_by_timing,
        "fires_with_recovery_opportunity": fires_with_recovery,
        "fires_before_settlement": fires_before_settlement,
        "policy_activation_count": 0,
    }


def discover_run_dirs(trace_dir: Path | None, traces_root: Path | None) -> list[Path]:
    dirs: list[Path] = []
    if trace_dir is not None:
        trace_path = Path(trace_dir)
        if trace_path.is_dir():
            dirs.append(trace_path)
    if traces_root is not None:
        root_path = Path(traces_root)
        if root_path.is_dir():
            for child in sorted(root_path.iterdir()):
                if child.is_dir() and (child / "events.jsonl").exists():
                    if trace_dir is None or child != Path(trace_dir):
                        dirs.append(child)
    return dirs


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run live shadow evaluation over captured live harness traces"
    )
    parser.add_argument(
        "--trace-dir",
        default=None,
        help="Path to a single live harness trace directory",
    )
    parser.add_argument(
        "--traces-root",
        default=None,
        help="Path to parent directory containing multiple run directories",
    )
    parser.add_argument(
        "--target-policy",
        default="require_reflection_before_continuing_after_second_unresolved_error",
        help="Target policy ID to evaluate (default: require_reflection_before_continuing_after_second_unresolved_error)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output path for shadow_policy_results.jsonl (default: write in trace dir)",
    )
    args = parser.parse_args()

    if args.trace_dir is None and args.traces_root is None:
        parser.error("At least one of --trace-dir or --traces-root is required")

    target_policy_ids = _resolve_evaluator_policy_ids(args.target_policy)
    run_dirs = discover_run_dirs(
        Path(args.trace_dir) if args.trace_dir else None,
        Path(args.traces_root) if args.traces_root else None,
    )

    if not run_dirs:
        print("No trace directories found")
        return

    all_run_results: list[dict[str, Any]] = []
    all_flat_results: list[dict[str, Any]] = []

    for run_dir in run_dirs:
        run_result = evaluate_run(run_dir, target_policy_ids)
        all_run_results.append(run_result)

        output_path = (
            Path(args.output)
            if args.output
            else run_dir / "shadow_policy_results.jsonl"
        )
        write_records_jsonl(run_result["results"], output_path)

        all_flat_results.extend(run_result["results"])
        fire_count = run_result["total_fires"]
        print(
            f"Run {run_result['run_id']}: {fire_count} policy fire(s) -> {output_path}"
        )

    summary = build_cross_run_summary(all_run_results)
    summary_path = (
        Path(args.output).parent / "shadow_policy_summary.json" if args.output else None
    )
    if args.traces_root and summary_path is None:
        summary_path = Path(args.traces_root) / "shadow_policy_summary.json"
    if summary_path is not None:
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(
            json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
        )
        print(f"Summary -> {summary_path}")

    print(
        f"Total runs: {summary['total_runs']}, "
        f"Total fires: {summary['total_fires']}, "
        f"Fires before settlement: {summary['fires_before_settlement']}"
    )


if __name__ == "__main__":
    main()
