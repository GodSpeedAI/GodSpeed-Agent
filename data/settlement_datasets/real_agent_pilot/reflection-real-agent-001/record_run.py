"""Real Agent Pilot Recording Helper.

Usage by the human operator:
    PYTHONPATH=. uv run python data/settlement_datasets/real_agent_pilot/reflection-real-agent-001/record_run.py \
        --run-id run-01 \
        --condition baseline \
        --task-dir tmp/pilot_tasks/task_a \
        --task-description "Fix the failing tests in tmp/pilot_tasks/task_a/"

This creates the artifact directory and provides a template for recording events.
The operator fills in events as the agent works, then finalizes the run.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PILOT_DIR = Path("data/settlement_datasets/real_agent_pilot/reflection-real-agent-001")

REFLECTION_CHECKPOINT = (
    "Repeated unresolved errors detected.\n\n"
    "Before continuing, revise the plan using the latest settlement feedback:\n\n"
    "1. What failed?\n"
    "2. What assumption may be wrong?\n"
    "3. What lower-payment action should happen next?\n"
    "4. What evidence would show the next step worked?"
)


def new_event(
    run_id: str,
    step_index: int,
    event_type: str,
    content: str,
    tool_name: str | None = None,
    is_error: bool = False,
) -> dict[str, Any]:
    """Create a new event record."""
    return {
        "run_id": run_id,
        "step_index": step_index,
        "timestamp": datetime.now(UTC).isoformat(),
        "event_type": event_type,
        "content": content,
        "tool_name": tool_name,
        "is_error": is_error,
        "metadata": {},
    }


def new_policy_fire(
    run_id: str,
    step_index: int,
    error_count: int,
    error_summaries: list[str],
    same_path_evidence: str,
) -> dict[str, Any]:
    """Create a policy fire record."""
    return {
        "run_id": run_id,
        "step_index": step_index,
        "timestamp": datetime.now(UTC).isoformat(),
        "policy_id": "require_reflection_before_continuing_after_second_unresolved_error",
        "fire_reason": "second_unresolved_error_with_same_path_continuation",
        "error_count": error_count,
        "error_summaries": error_summaries,
        "same_path_evidence": same_path_evidence,
        "intervention_delivered": True,
    }


def new_intervention(
    run_id: str,
    step_index: int,
    intervention_text: str,
) -> dict[str, Any]:
    """Create an intervention record."""
    return {
        "run_id": run_id,
        "step_index": step_index,
        "timestamp": datetime.now(UTC).isoformat(),
        "intervention_text": intervention_text,
        "agent_response": None,  # filled after agent responds
        "response_step_index": None,
    }


def new_run_summary(
    run_id: str,
    condition: str,
    task_dir: str,
    task_description: str,
    total_steps: int,
    error_count: int,
    outcome: str,
    settlement_quality: str,
    policy_fired: bool,
    agent_revised_strategy: bool,
    notes: str = "",
) -> dict[str, Any]:
    """Create a run summary record."""
    return {
        "run_id": run_id,
        "condition": condition,  # "baseline" or "guarded" — REMOVED before giving to evaluator
        "task_dir": task_dir,
        "task_description": task_description,
        "total_steps": total_steps,
        "error_count": error_count,
        "outcome": outcome,  # "success" or "failure"
        "settlement_quality": settlement_quality,
        "policy_fired": policy_fired,
        "agent_revised_strategy": agent_revised_strategy,
        "notes": notes,
        "timestamp": datetime.now(UTC).isoformat(),
    }


def append_jsonl(record: dict[str, Any], path: Path) -> None:
    """Append a record to a JSONL file."""
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def init_run(run_id: str, condition: str, task_dir: str, task_description: str) -> None:
    """Initialize the artifact files for a new run."""
    PILOT_DIR.mkdir(parents=True, exist_ok=True)

    # Write run metadata
    metadata = {
        "run_id": run_id,
        "condition": condition,
        "task_dir": task_dir,
        "task_description": task_description,
        "started_at": datetime.now(UTC).isoformat(),
    }
    metadata_path = PILOT_DIR / f"{run_id}_metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Initialized run {run_id}")
    print(f"  Condition: {condition}")
    print(f"  Task dir: {task_dir}")
    print(f"  Metadata: {metadata_path}")
    print()
    print("Recording instructions:")
    print("  1. Watch the agent work in VS Code")
    print("  2. After each agent action, record it using the event schema")
    print("  3. For guarded runs: when the agent hits 2+ unresolved errors")
    print("     AND continues same-path, paste this reflection checkpoint:")
    print()
    print(REFLECTION_CHECKPOINT)
    print()
    print("  4. Record the policy fire and intervention")
    print("  5. When the agent finishes, finalize the run")


def finalize_run(
    run_id: str,
    condition: str,
    task_dir: str,
    task_description: str,
    total_steps: int,
    error_count: int,
    outcome: str,
    settlement_quality: str,
    policy_fired: bool,
    agent_revised_strategy: bool,
    notes: str = "",
) -> None:
    """Finalize a run by writing the run summary."""
    summary = new_run_summary(
        run_id=run_id,
        condition=condition,
        task_dir=task_dir,
        task_description=task_description,
        total_steps=total_steps,
        error_count=error_count,
        outcome=outcome,
        settlement_quality=settlement_quality,
        policy_fired=policy_fired,
        agent_revised_strategy=agent_revised_strategy,
        notes=notes,
    )
    append_jsonl(summary, PILOT_DIR / "run_summaries.jsonl")
    print(f"Finalized run {run_id}: {outcome} ({settlement_quality})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Real Agent Pilot Recording Helper")
    sub = parser.add_subparsers(dest="command")

    init = sub.add_parser("init", help="Initialize a new run")
    init.add_argument("--run-id", required=True)
    init.add_argument("--condition", required=True, choices=["baseline", "guarded"])
    init.add_argument("--task-dir", required=True)
    init.add_argument("--task-description", required=True)

    finalize = sub.add_parser("finalize", help="Finalize a completed run")
    finalize.add_argument("--run-id", required=True)
    finalize.add_argument("--condition", required=True, choices=["baseline", "guarded"])
    finalize.add_argument("--task-dir", required=True)
    finalize.add_argument("--task-description", required=True)
    finalize.add_argument("--total-steps", type=int, required=True)
    finalize.add_argument("--error-count", type=int, required=True)
    finalize.add_argument("--outcome", required=True, choices=["success", "failure"])
    finalize.add_argument("--settlement-quality", required=True)
    finalize.add_argument("--policy-fired", type=bool, default=False)
    finalize.add_argument("--agent-revised-strategy", type=bool, default=False)
    finalize.add_argument("--notes", default="")

    args = parser.parse_args()

    if args.command == "init":
        init_run(args.run_id, args.condition, args.task_dir, args.task_description)
    elif args.command == "finalize":
        finalize_run(
            run_id=args.run_id,
            condition=args.condition,
            task_dir=args.task_dir,
            task_description=args.task_description,
            total_steps=args.total_steps,
            error_count=args.error_count,
            outcome=args.outcome,
            settlement_quality=args.settlement_quality,
            policy_fired=args.policy_fired,
            agent_revised_strategy=args.agent_revised_strategy,
            notes=args.notes,
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
