from __future__ import annotations

import tempfile

from scripts.settlement_datasets.adapter_base import read_records_jsonl
from scripts.settlement_datasets.guarded_activation import (
    GUARDED_INTERVENTION_TEXT,
    GuardedActivationConfig,
    GuardedActivationExperiment,
    config_from_env,
    replay_guarded_activation,
    validate_intervention_record,
)


def _event(step_index: int, event_type: str, content: str, run_id: str = "run-1"):
    return {
        "run_id": run_id,
        "step_index": step_index,
        "timestamp": f"2026-05-31T00:00:0{step_index}Z",
        "event_type": event_type,
        "content": content,
        "tool_name": None,
        "metadata": {},
        "settlement_signals": {},
    }


def test_guarded_config_safe_defaults(monkeypatch):
    monkeypatch.delenv("HARNESS_POLICY_ACTIVATION_ENABLED", raising=False)
    monkeypatch.delenv("HARNESS_POLICY_EXPERIMENT", raising=False)
    monkeypatch.delenv("HARNESS_POLICY_MODE", raising=False)

    config = config_from_env()

    assert config.activation_enabled is False
    assert config.mode == "shadow"
    assert config.policy_id == "require_reflection_after_repeated_errors"
    assert config.max_fires_per_run == 1


def test_guarded_trigger_emits_intervention_with_required_evidence():
    experiment = GuardedActivationExperiment(
        GuardedActivationConfig(activation_enabled=True, mode="guarded")
    )
    assert experiment.record_event(_event(0, "tool_result", "Error: first failure")) == []

    interventions = experiment.record_event(
        _event(1, "tool_result", "Traceback: second failure")
    )

    assert len(interventions) == 1
    intervention = interventions[0]
    assert intervention["policy_id"] == "require_reflection_after_repeated_errors"
    assert intervention["activation_mode"] == "guarded"
    assert intervention["intervention_text"] == GUARDED_INTERVENTION_TEXT
    assert intervention["agent_response_to_intervention"] is None
    assert intervention["payment_delta_estimate"] is None
    assert intervention["helpfulness_assessment"] == "uncertain"
    assert validate_intervention_record(intervention) == []
    assert intervention["trigger_evidence"]["error_events"]
    assert intervention["trigger_evidence"]["continued_same_path_evidence"]
    assert intervention["trigger_evidence"]["missing_revision_evidence"]
    assert intervention["trigger_evidence"]["recovery_opportunity_evidence"]


def test_guarded_activation_disabled_emits_no_intervention():
    experiment = GuardedActivationExperiment(
        GuardedActivationConfig(activation_enabled=False, mode="guarded")
    )
    experiment.record_event(_event(0, "tool_result", "Error: first failure"))

    assert experiment.record_event(_event(1, "tool_result", "Error: second failure")) == []
    assert experiment.interventions == []


def test_shadow_mode_emits_no_guarded_intervention():
    experiment = GuardedActivationExperiment(
        GuardedActivationConfig(activation_enabled=True, mode="shadow")
    )
    experiment.record_event(_event(0, "tool_result", "Error: first failure"))

    assert experiment.record_event(_event(1, "tool_result", "Error: second failure")) == []


def test_negative_condition_strategy_revision_after_latest_error_blocks_fire():
    experiment = GuardedActivationExperiment(
        GuardedActivationConfig(activation_enabled=True, mode="guarded")
    )
    experiment.record_event(_event(0, "tool_result", "Error: first failure"))
    experiment.record_event(_event(1, "model_message", "Revised plan: inspect logs"))

    assert experiment.record_event(_event(2, "tool_result", "Error: second failure")) == []


def test_negative_condition_duplicate_error_output_blocks_fire():
    experiment = GuardedActivationExperiment(
        GuardedActivationConfig(activation_enabled=True, mode="guarded")
    )
    experiment.record_event(_event(0, "tool_result", "Error: same failure"))

    assert experiment.record_event(_event(1, "tool_result", "Error: same failure")) == []


def test_negative_condition_task_complete_and_final_answer_block_fire():
    for event_type in ("task_complete", "final_answer"):
        experiment = GuardedActivationExperiment(
            GuardedActivationConfig(activation_enabled=True, mode="guarded")
        )
        experiment.record_event(_event(0, "tool_result", "Error: first failure"))
        experiment.record_event(_event(1, event_type, "done"))

        assert experiment.record_event(_event(2, "tool_result", "Error: second failure")) == []


def test_negative_condition_low_cost_inspection_blocks_fire():
    experiment = GuardedActivationExperiment(
        GuardedActivationConfig(activation_enabled=True, mode="guarded")
    )
    experiment.record_event(_event(0, "tool_result", "Error: first failure"))

    assert experiment.record_event(_event(1, "tool_call", "cat app.py")) == []


def test_max_one_intervention_per_run():
    experiment = GuardedActivationExperiment(
        GuardedActivationConfig(
            activation_enabled=True,
            mode="guarded",
            max_fires_per_run=1,
        )
    )
    experiment.record_event(_event(0, "tool_result", "Error: first failure"))
    first = experiment.record_event(_event(1, "tool_result", "Error: second failure"))
    second = experiment.record_event(_event(2, "tool_result", "Exception: third failure"))

    assert len(first) == 1
    assert second == []


def test_intervention_record_schema_reports_missing_evidence():
    intervention = {
        "run_id": "run-1",
        "step_index": 1,
        "policy_id": "require_reflection_after_repeated_errors",
        "activation_mode": "guarded",
        "intervention_text": GUARDED_INTERVENTION_TEXT,
        "trigger_evidence": {},
        "agent_response_to_intervention": None,
        "post_intervention_actions": [],
        "final_outcome": "unknown",
        "settlement_quality": "unknown",
        "payment_delta_estimate": None,
        "helpfulness_assessment": "uncertain",
        "assessment_evidence": [],
    }

    errors = validate_intervention_record(intervention)

    assert "missing_trigger_evidence:error_events" in errors


def test_replay_guarded_activation_writes_outputs_and_summary():
    events = [
        _event(0, "tool_result", "Error: first failure", run_id="run-a"),
        _event(1, "tool_result", "Error: second failure", run_id="run-a"),
        _event(2, "model_message", "continue", run_id="run-a"),
        _event(0, "tool_result", "Error: only failure", run_id="run-b"),
        _event(1, "task_complete", "task complete", run_id="run-b"),
    ]

    with tempfile.TemporaryDirectory() as td:
        outputs = replay_guarded_activation(events, output_dir=td)
        interventions = read_records_jsonl(outputs["interventions"])
        summary = outputs["experiment_summary"].read_text()

    assert len(interventions) == 1
    assert interventions[0]["run_id"] == "run-a"
    assert '"fires": 1' in summary
    assert '"interventions_completed": 0' in summary


def test_replay_guarded_activation_uses_baseline_run_outcomes():
    events = [
        _event(0, "tool_result", "Error: first failure", run_id="run-a"),
        _event(1, "tool_result", "Error: second failure", run_id="run-a"),
    ]
    baseline = {
        "run-a": {
            "final_outcome": "success",
            "settlement_quality": "recovered_success",
        }
    }

    with tempfile.TemporaryDirectory() as td:
        outputs = replay_guarded_activation(
            events,
            output_dir=td,
            baseline_summaries=baseline,
        )
        interventions = read_records_jsonl(outputs["interventions"])
        summary = outputs["experiment_summary"].read_text()

    assert interventions[0]["final_outcome"] == "success"
    assert interventions[0]["settlement_quality"] == "recovered_success"
    assert '"false_positive_count": 1' in summary
