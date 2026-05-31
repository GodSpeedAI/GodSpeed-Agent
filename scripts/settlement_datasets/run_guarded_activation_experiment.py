"""Guarded Activation Experiment Runner.

Replays the 13 baseline live harness traces through the guarded activation
experiment for the refined reflection policy, compares guarded vs baseline
results, and writes experiment artifacts.

Usage:
    PYTHONPATH=. uv run python scripts/settlement_datasets/run_guarded_activation_experiment.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.settlement_datasets.adapter_base import (
    read_records_jsonl,
    write_records_jsonl,
)
from scripts.settlement_datasets.guarded_activation import (
    REFINED_POLICY_ID,
    GUARDED_INTERVENTION_TEXT,
    GuardedActivationConfig,
    GuardedActivationExperiment,
    validate_intervention_record,
)
from godspeed_nav.trace_capture import read_trace_events, read_run_summary


EXPERIMENT_ID = "reflection-guarded-002"
BASELINE_DIR = Path("data/settlement_datasets/live_harness_traces")
OUTPUT_DIR = (
    Path("data/settlement_datasets/guarded_activation_experiment") / EXPERIMENT_ID
)


def load_baseline_traces(baseline_dir: Path) -> list[dict[str, Any]]:
    """Load all baseline trace directories."""
    traces = []
    for child in sorted(baseline_dir.iterdir()):
        if (
            child.is_dir()
            and child.name.startswith("baseline-")
            and (child / "events.jsonl").exists()
        ):
            events = read_trace_events(child)
            summary = read_run_summary(child)
            traces.append(
                {
                    "run_id": child.name,
                    "dir": child,
                    "events": events,
                    "summary": summary or {},
                }
            )
    return traces


def run_guarded_experiment(
    baseline_traces: list[dict[str, Any]],
    config: GuardedActivationConfig,
    experiment_id: str = EXPERIMENT_ID,
) -> dict[str, Any]:
    """Run guarded activation experiment over baseline traces."""
    all_events: list[dict[str, Any]] = []
    all_policy_fires: list[dict[str, Any]] = []
    all_interventions: list[dict[str, Any]] = []
    all_suppressions: list[dict[str, Any]] = []
    run_summaries: list[dict[str, Any]] = []
    baseline_comparison: list[dict[str, Any]] = []

    for trace_info in baseline_traces:
        run_id = trace_info["run_id"]
        events = trace_info["events"]
        baseline_summary = trace_info["summary"]

        experiment = GuardedActivationExperiment(
            config,
            run_metadata={
                "run_id": run_id,
                "task_id": run_id,
                "domain": baseline_summary.get("run_metadata", {}).get(
                    "domain", "harness"
                ),
                "task_type": baseline_summary.get("run_metadata", {}).get(
                    "task_type", "unknown"
                ),
                "experiment_id": experiment_id,
            },
        )

        run_interventions = []
        for event in events:
            interventions = experiment.record_event(event)
            run_interventions.extend(interventions)

        final_outcome = baseline_summary.get("final_outcome", "unknown")
        settlement_quality = baseline_summary.get("settlement_quality", "unknown")

        run_summary = experiment.finalize_run(
            final_outcome=final_outcome,
            settlement_quality=settlement_quality,
        )

        all_events.extend(events)
        all_policy_fires.extend(experiment.policy_fires)
        all_interventions.extend(run_interventions)
        all_suppressions.extend(experiment.suppressions)
        run_summaries.append(run_summary)

        # Build baseline comparison
        baseline_error_count = baseline_summary.get("error_count", 0)
        baseline_total_steps = baseline_summary.get("total_steps", 0)
        guarded_error_count = sum(
            1
            for e in experiment.events
            if e.get("settlement_signals", {}).get("error_detected")
        )
        guarded_tool_calls = sum(
            1 for e in experiment.events if e.get("event_type") == "tool_call"
        )
        baseline_tool_calls = sum(
            1 for e in events if e.get("event_type") == "tool_call"
        )

        comparison = {
            "run_id": run_id,
            "baseline_outcome": final_outcome,
            "baseline_settlement_quality": settlement_quality,
            "baseline_error_count": baseline_error_count,
            "baseline_total_steps": baseline_total_steps,
            "baseline_tool_calls": baseline_tool_calls,
            "guarded_intervention_count": len(run_interventions),
            "guarded_suppression_count": len(experiment.suppressions),
            "guarded_error_count": guarded_error_count,
            "guarded_tool_calls": guarded_tool_calls,
            "guarded_total_steps": len(experiment.events),
            "tool_call_delta": guarded_tool_calls - baseline_tool_calls,
            "error_count_delta": guarded_error_count - baseline_error_count,
            "intervention_fired": len(run_interventions) > 0,
            "suppression_fired": len(experiment.suppressions) > 0,
        }

        if run_interventions:
            intervention = run_interventions[0]
            comparison["intervention_step"] = intervention["step_index"]
            comparison["intervention_text"] = intervention["intervention_text"]
            comparison["trigger_evidence"] = intervention["trigger_evidence"]
            comparison["helpfulness_assessment"] = intervention[
                "helpfulness_assessment"
            ]

            # Assess helpfulness based on outcome
            if final_outcome == "failure" and baseline_error_count >= 2:
                comparison["helpfulness_assessment"] = "potentially_helpful"
                comparison["assessment_evidence"] = [
                    "agent_failed_after_repeated_errors",
                    "no_strategy_revision_detected",
                    "same_path_continuation_observed",
                ]
            elif final_outcome == "success":
                comparison["helpfulness_assessment"] = "false_positive"
                comparison["assessment_evidence"] = [
                    "agent_recovered_without_intervention",
                    f"settlement_quality={settlement_quality}",
                ]
            else:
                comparison["helpfulness_assessment"] = "uncertain"
                comparison["assessment_evidence"] = [
                    "outcome_unclear",
                ]

        if experiment.suppressions:
            comparison["suppression_reason"] = experiment.suppressions[0][
                "suppression_reason"
            ]
            comparison["suppression_evidence"] = experiment.suppressions[0][
                "suppression_evidence"
            ]

        baseline_comparison.append(comparison)

    # Build experiment summary
    total_runs = len(baseline_traces)
    total_fires = len(all_interventions)
    fires_before_settlement = sum(
        1
        for comp in baseline_comparison
        if comp["intervention_fired"]
        and comp.get("intervention_step", 999) < comp["baseline_total_steps"]
    )
    false_positive_count = sum(
        1
        for comp in baseline_comparison
        if comp.get("helpfulness_assessment") == "false_positive"
    )
    potentially_helpful_count = sum(
        1
        for comp in baseline_comparison
        if comp.get("helpfulness_assessment") == "potentially_helpful"
    )
    uncertain_count = sum(
        1
        for comp in baseline_comparison
        if comp.get("helpfulness_assessment") == "uncertain"
    )

    # Determine status recommendation
    if (
        total_fires >= 5
        and false_positive_count / max(total_fires, 1) <= 0.10
        and potentially_helpful_count >= 2
    ):
        status_recommendation = "candidate_for_activation"
    elif total_fires >= 5 and potentially_helpful_count >= 1:
        status_recommendation = "tested_needs_more_evidence"
    elif total_fires >= 1:
        status_recommendation = "tested_needs_more_evidence"
    else:
        status_recommendation = "needs_more_evidence"

    experiment_summary = {
        "experiment_id": experiment_id,
        "policy_id": REFINED_POLICY_ID,
        "policy_mode": "guarded",
        "activation_enabled": config.activation_enabled,
        "max_fires_per_run": config.max_fires_per_run,
        "total_guarded_runs": total_runs,
        "total_policy_fires": total_fires,
        "total_interventions": total_fires,
        "total_suppressions": len(all_suppressions),
        "interventions_completed": 0,  # replay mode, no agent response
        "fires_before_settlement": fires_before_settlement,
        "post_intervention_recovery_count": 0,  # replay mode
        "false_positive_count": false_positive_count,
        "potentially_helpful_count": potentially_helpful_count,
        "harmful_intervention_count": 0,
        "uncertain_count": uncertain_count,
        "neutral_count": total_runs - total_fires - len(all_suppressions),
        "suppressed_count": sum(
            1 for comp in baseline_comparison if comp.get("suppression_fired")
        ),
        "tool_call_delta_total": sum(
            comp["tool_call_delta"] for comp in baseline_comparison
        ),
        "error_count_delta_total": sum(
            comp["error_count_delta"] for comp in baseline_comparison
        ),
        "payment_increase": None,
        "status_recommendation": status_recommendation,
        "metabolized": False,
        "globally_active": False,
        "baseline_comparison": baseline_comparison,
    }

    return {
        "events": all_events,
        "policy_fires": all_policy_fires,
        "interventions": all_interventions,
        "suppressions": all_suppressions,
        "run_summaries": run_summaries,
        "experiment_summary": experiment_summary,
    }


def write_experiment_artifacts(
    results: dict[str, Any],
    output_dir: Path,
) -> dict[str, Path]:
    """Write all experiment artifacts to disk."""
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "events": output_dir / "events.jsonl",
        "policy_fires": output_dir / "policy_fires.jsonl",
        "interventions": output_dir / "interventions.jsonl",
        "suppressions": output_dir / "suppressions.jsonl",
        "run_summaries": output_dir / "run_summaries.jsonl",
        "experiment_summary": output_dir / "experiment_summary.json",
    }
    write_records_jsonl(results["events"], paths["events"])
    write_records_jsonl(results["policy_fires"], paths["policy_fires"])
    write_records_jsonl(results["interventions"], paths["interventions"])
    write_records_jsonl(results.get("suppressions", []), paths["suppressions"])
    write_records_jsonl(results["run_summaries"], paths["run_summaries"])
    paths["experiment_summary"].write_text(
        json.dumps(results["experiment_summary"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run guarded activation experiment over baseline traces"
    )
    parser.add_argument(
        "--baseline-dir",
        default=str(BASELINE_DIR),
        help="Directory containing baseline trace directories",
    )
    parser.add_argument(
        "--output-dir",
        default=str(OUTPUT_DIR),
        help="Output directory for experiment artifacts",
    )
    args = parser.parse_args()

    baseline_dir = Path(args.baseline_dir)
    output_dir = Path(args.output_dir)

    print(f"Loading baseline traces from {baseline_dir}")
    baseline_traces = load_baseline_traces(baseline_dir)
    print(f"Loaded {len(baseline_traces)} baseline traces")

    config = GuardedActivationConfig(
        activation_enabled=True,
        policy_id=REFINED_POLICY_ID,
        mode="guarded",
        max_fires_per_run=1,
        max_experiment_runs=20,
    )
    print(f"Policy: {config.policy_id}")
    print(f"Mode: {config.mode}")
    print(f"Max fires per run: {config.max_fires_per_run}")
    print()

    results = run_guarded_experiment(baseline_traces, config)
    paths = write_experiment_artifacts(results, output_dir)

    summary = results["experiment_summary"]
    print(f"Total guarded runs: {summary['total_guarded_runs']}")
    print(f"Total policy fires: {summary['total_policy_fires']}")
    print(f"Fires before settlement: {summary['fires_before_settlement']}")
    print(f"False positives: {summary['false_positive_count']}")
    print(f"Potentially helpful: {summary['potentially_helpful_count']}")
    print(f"Uncertain: {summary['uncertain_count']}")
    print(f"Suppressed: {summary['suppressed_count']}")
    print(f"Status recommendation: {summary['status_recommendation']}")
    print()
    print(f"Events -> {paths['events']}")
    print(f"Policy fires -> {paths['policy_fires']}")
    print(f"Interventions -> {paths['interventions']}")
    print(f"Suppressions -> {paths['suppressions']}")
    print(f"Run summaries -> {paths['run_summaries']}")
    print(f"Experiment summary -> {paths['experiment_summary']}")


if __name__ == "__main__":
    main()
