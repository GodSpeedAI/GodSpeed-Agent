from __future__ import annotations

import os
import tempfile
from pathlib import Path

from scripts.settlement_datasets.adapter_base import read_records_jsonl
from scripts.settlement_datasets.live_shadow_policy_eval import (
    LiveShadowPolicyEvaluator,
    event_from_trace_item,
    is_live_shadow_enabled,
    replay_records_to_live_shadow,
    validate_live_run_event,
)


def _event(
    step_index: int,
    event_type: str,
    content: str,
    run_id: str = "run-1",
    **kwargs,
):
    return {
        "run_id": run_id,
        "step_index": step_index,
        "timestamp": f"2026-05-31T00:00:0{step_index}Z",
        "event_type": event_type,
        "content": content,
        "tool_name": kwargs.get("tool_name"),
        "metadata": kwargs.get("metadata", {}),
        "settlement_signals": kwargs.get("settlement_signals", {}),
    }


def test_live_event_schema_validation_accepts_required_shape():
    event = _event(
        0,
        "tool_result",
        "pytest failed",
        settlement_signals={"test_failed": True, "error_detected": True},
    )

    assert validate_live_run_event(event) == []


def test_live_event_schema_validation_rejects_missing_fields():
    errors = validate_live_run_event({"run_id": "run-1", "event_type": "tool_call"})

    assert "missing_required_field:step_index" in errors
    assert "missing_required_field:settlement_signals" in errors


def test_reflection_policy_fires_on_second_unresolved_error_before_final():
    evaluator = LiveShadowPolicyEvaluator(enabled=True)

    assert evaluator.record_event(_event(0, "tool_call", "pytest tests")) == []
    assert evaluator.record_event(_event(1, "tool_result", "Error: first failure")) == []

    fires = evaluator.record_event(_event(2, "tool_result", "Traceback: second failure"))

    assert len(fires) == 1
    fire = fires[0]
    assert fire["policy_id"] == "require_reflection_after_repeated_errors"
    assert fire["would_fire"] is True
    assert fire["shadow_action"] == "would_require_reflection_or_revised_plan"
    assert fire["recovery_opportunity"] is True
    assert fire["activation_status"] == "shadow_only"
    assert fire["enforced"] is False


def test_strategy_revision_suppresses_repeated_error_reflection_fire():
    evaluator = LiveShadowPolicyEvaluator(enabled=True)
    evaluator.record_event(_event(0, "tool_result", "Error: first failure"))
    evaluator.record_event(_event(1, "model_message", "Revised plan: inspect the API schema"))

    fires = evaluator.record_event(_event(2, "tool_result", "Error: second failure"))

    assert fires == []


def test_task_completion_suppresses_shadow_fires():
    evaluator = LiveShadowPolicyEvaluator(enabled=True)
    evaluator.record_event(_event(0, "tool_result", "Error: first failure"))
    evaluator.record_event(_event(1, "task_complete", "task complete"))

    fires = evaluator.record_event(_event(2, "tool_result", "Error: second failure"))

    assert fires == []


def test_explicit_settlement_policy_fires_near_closure_without_settlement_evidence():
    evaluator = LiveShadowPolicyEvaluator(enabled=True)
    evaluator.record_event(_event(0, "tool_result", "Error: command failed"))

    fires = evaluator.record_event(
        _event(1, "model_message", "I cannot complete this, final answer: failed")
    )

    assert len(fires) == 1
    fire = fires[0]
    assert fire["policy_id"] == "require_explicit_settlement_for_failure"
    assert fire["shadow_action"] == "would_require_explicit_settlement_evidence"
    assert fire["recovery_opportunity"] is True


def test_explicit_settlement_policy_can_fire_on_final_answer_before_task_complete():
    evaluator = LiveShadowPolicyEvaluator(enabled=True)
    evaluator.record_event(_event(0, "tool_result", "Error: command failed"))

    fires = evaluator.record_event(_event(1, "final_answer", "Final answer: failed"))

    assert [f["policy_id"] for f in fires] == [
        "require_explicit_settlement_for_failure"
    ]
    assert fires[0]["fire_timing"] == "final_turn"


def test_explicit_settlement_policy_does_not_fire_when_test_evidence_exists():
    evaluator = LiveShadowPolicyEvaluator(enabled=True)
    evaluator.record_event(_event(0, "tool_result", "Error: command failed"))
    evaluator.record_event(_event(1, "tool_result", "2 tests failed, 1 passed"))
    evaluator.record_event(_event(2, "tool_result", "3 passed"))

    fires = evaluator.record_event(_event(3, "model_message", "final answer"))

    assert fires == []


def test_run_summary_counts_pre_final_shadow_fires():
    evaluator = LiveShadowPolicyEvaluator(enabled=True, run_metadata={"task_id": "task-1", "domain": "code"})
    evaluator.record_event(_event(0, "tool_result", "Error: first failure"))
    evaluator.record_event(_event(1, "tool_result", "Error: second failure"))
    evaluator.record_event(_event(2, "model_message", "try another command"))

    summary = evaluator.finalize_run(final_outcome="failure", settlement_quality="failure_with_signal")

    assert summary["run_id"] == "run-1"
    assert summary["task_id"] == "task-1"
    assert summary["total_steps"] == 3
    assert summary["first_shadow_fire_step"] == 1
    assert summary["fires_before_final"] == 1
    assert summary["fires_with_recovery_opportunity"] == 1
    assert summary["post_fire_outcome"] == "failed"
    assert summary["policy_activation_recommendations"] == []


def test_config_defaults_off_and_env_enables(monkeypatch):
    monkeypatch.delenv("SHADOW_POLICY_EVAL_ENABLED", raising=False)
    assert is_live_shadow_enabled() is False

    monkeypatch.setenv("SHADOW_POLICY_EVAL_ENABLED", "true")
    assert is_live_shadow_enabled() is True


def test_disabled_evaluator_records_no_fire_and_no_enforcement():
    evaluator = LiveShadowPolicyEvaluator(enabled=False)
    evaluator.record_event(_event(0, "tool_result", "Error: first failure"))

    assert evaluator.record_event(_event(1, "tool_result", "Error: second failure")) == []
    assert evaluator.policy_fires == []


def test_event_from_trace_item_maps_actions_and_observations():
    action_event = event_from_trace_item(
        {"action_type": "command", "content": "pytest", "turn_index": 2},
        run_id="run-2",
    )
    observation_event = event_from_trace_item(
        {"content": "Traceback: failure", "turn_index": 3},
        run_id="run-2",
        item_kind="observation",
    )

    assert action_event["event_type"] == "tool_call"
    assert observation_event["event_type"] == "tool_result"
    assert observation_event["settlement_signals"]["error_detected"] is True


def test_replay_records_to_live_shadow_writes_outputs():
    records = [
        {
            "task_id": "trace-1",
            "domain": "code",
            "outcome": {"settlement_quality": "failure_with_signal"},
            "affordance_path": {
                "actions": [
                    {"action_type": "command", "content": "pytest", "turn_index": 0},
                    {"action_type": "command", "content": "retry pytest", "turn_index": 2},
                ],
                "observations": [
                    {"content": "Error: first failure", "turn_index": 1},
                    {"content": "Error: second failure", "turn_index": 3},
                ],
            },
        }
    ]
    with tempfile.TemporaryDirectory() as td:
        outputs = replay_records_to_live_shadow(records, output_dir=td, enabled=True)

        events = read_records_jsonl(outputs["events"])
        fires = read_records_jsonl(outputs["policy_fires"])
        summaries = read_records_jsonl(outputs["run_summaries"])

    assert len(events) == 4
    assert any(f["policy_id"] == "require_reflection_after_repeated_errors" for f in fires)
    assert summaries[0]["run_id"] == "trace-1"
    assert summaries[0]["fires_with_recovery_opportunity"] >= 1
