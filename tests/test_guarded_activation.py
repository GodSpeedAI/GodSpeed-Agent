from __future__ import annotations

import json
import tempfile

from scripts.settlement_datasets.adapter_base import read_records_jsonl
from scripts.settlement_datasets.guarded_activation import (
    GUARDED_INTERVENTION_TEXT,
    POLICY_ID,
    REFINED_POLICY_ID,
    GuardedActivationConfig,
    GuardedActivationExperiment,
    config_from_env,
    detect_adaptive_recovery,
    replay_guarded_activation,
    validate_intervention_record,
)
from scripts.settlement_datasets.run_guarded_activation_experiment import (
    run_guarded_experiment,
    write_experiment_artifacts,
    EXPERIMENT_ID,
)
from scripts.settlement_datasets.run_live_pilot import (
    run_live_pilot,
    write_pilot_artifacts,
    PILOT_ID,
    ALL_PILOT_SCENARIOS,
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
    assert config.policy_id == REFINED_POLICY_ID
    assert config.max_fires_per_run == 1


def test_guarded_trigger_emits_intervention_with_required_evidence():
    experiment = GuardedActivationExperiment(
        GuardedActivationConfig(activation_enabled=True, mode="guarded")
    )
    assert (
        experiment.record_event(_event(0, "tool_result", "Error: first failure")) == []
    )

    interventions = experiment.record_event(
        _event(1, "tool_result", "Traceback: second failure")
    )

    assert len(interventions) == 1
    intervention = interventions[0]
    assert intervention["policy_id"] == REFINED_POLICY_ID
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

    assert (
        experiment.record_event(_event(1, "tool_result", "Error: second failure")) == []
    )
    assert experiment.interventions == []


def test_shadow_mode_emits_no_guarded_intervention():
    experiment = GuardedActivationExperiment(
        GuardedActivationConfig(activation_enabled=True, mode="shadow")
    )
    experiment.record_event(_event(0, "tool_result", "Error: first failure"))

    assert (
        experiment.record_event(_event(1, "tool_result", "Error: second failure")) == []
    )


def test_negative_condition_strategy_revision_after_latest_error_blocks_fire():
    experiment = GuardedActivationExperiment(
        GuardedActivationConfig(activation_enabled=True, mode="guarded")
    )
    experiment.record_event(_event(0, "tool_result", "Error: first failure"))
    experiment.record_event(_event(1, "model_message", "Revised plan: inspect logs"))

    assert (
        experiment.record_event(_event(2, "tool_result", "Error: second failure")) == []
    )


def test_negative_condition_duplicate_error_output_blocks_fire():
    experiment = GuardedActivationExperiment(
        GuardedActivationConfig(activation_enabled=True, mode="guarded")
    )
    experiment.record_event(_event(0, "tool_result", "Error: same failure"))

    assert (
        experiment.record_event(_event(1, "tool_result", "Error: same failure")) == []
    )


def test_negative_condition_task_complete_and_final_answer_block_fire():
    for event_type in ("task_complete", "final_answer"):
        experiment = GuardedActivationExperiment(
            GuardedActivationConfig(activation_enabled=True, mode="guarded")
        )
        experiment.record_event(_event(0, "tool_result", "Error: first failure"))
        experiment.record_event(_event(1, event_type, "done"))

        assert (
            experiment.record_event(_event(2, "tool_result", "Error: second failure"))
            == []
        )


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
    second = experiment.record_event(
        _event(2, "tool_result", "Exception: third failure")
    )

    assert len(first) == 1
    assert second == []


def test_intervention_record_schema_reports_missing_evidence():
    intervention = {
        "run_id": "run-1",
        "step_index": 1,
        "policy_id": REFINED_POLICY_ID,
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


# --- Experiment runner tests ---


def _baseline_trace(
    run_id, events, outcome="success", settlement_quality="clean_success"
):
    """Build a baseline trace dict for the experiment runner."""
    return {
        "run_id": run_id,
        "dir": None,
        "events": events,
        "summary": {
            "final_outcome": outcome,
            "settlement_quality": settlement_quality,
            "error_count": sum(
                1
                for e in events
                if "Error" in e.get("content", "")
                or "error" in e.get("content", "").lower()
            ),
            "total_steps": len(events),
            "run_metadata": {"domain": "code", "task_type": "coding"},
        },
    }


def test_experiment_runner_produces_all_artifacts():
    traces = [
        _baseline_trace(
            "run-a",
            [
                _event(0, "tool_result", "Error: first failure", run_id="run-a"),
                _event(1, "tool_result", "Error: second failure", run_id="run-a"),
                _event(2, "task_complete", "done", run_id="run-a"),
            ],
            outcome="failure",
            settlement_quality="failure_with_signal",
        ),
        _baseline_trace(
            "run-b",
            [
                _event(0, "tool_result", "no errors", run_id="run-b"),
                _event(1, "task_complete", "done", run_id="run-b"),
            ],
        ),
    ]
    config = GuardedActivationConfig(
        activation_enabled=True,
        policy_id=REFINED_POLICY_ID,
        mode="guarded",
        max_fires_per_run=1,
    )
    results = run_guarded_experiment(traces, config)

    assert len(results["events"]) == 5
    assert len(results["interventions"]) == 1
    assert len(results["policy_fires"]) == 1
    assert len(results["run_summaries"]) == 2
    assert results["experiment_summary"]["total_guarded_runs"] == 2
    assert results["experiment_summary"]["total_policy_fires"] == 1


def test_experiment_runner_writes_artifacts_to_disk():
    traces = [
        _baseline_trace(
            "run-x",
            [
                _event(0, "tool_result", "Error: first", run_id="run-x"),
                _event(1, "tool_result", "Error: second", run_id="run-x"),
            ],
            outcome="failure",
            settlement_quality="failure_with_signal",
        ),
    ]
    config = GuardedActivationConfig(
        activation_enabled=True,
        policy_id=REFINED_POLICY_ID,
        mode="guarded",
    )
    results = run_guarded_experiment(traces, config)

    with tempfile.TemporaryDirectory() as td:
        from pathlib import Path

        paths = write_experiment_artifacts(results, Path(td))
        assert paths["events"].exists()
        assert paths["policy_fires"].exists()
        assert paths["interventions"].exists()
        assert paths["run_summaries"].exists()
        assert paths["experiment_summary"].exists()

        interventions = read_records_jsonl(paths["interventions"])
        assert len(interventions) == 1
        assert interventions[0]["run_id"] == "run-x"

        summary = json.loads(paths["experiment_summary"].read_text())
        assert summary["experiment_id"] == EXPERIMENT_ID
        assert summary["policy_id"] == REFINED_POLICY_ID
        assert summary["policy_mode"] == "guarded"


def test_experiment_summary_never_globally_active_or_metabolized():
    traces = [
        _baseline_trace(
            "run-a",
            [
                _event(0, "tool_result", "Error: first", run_id="run-a"),
                _event(1, "tool_result", "Error: second", run_id="run-a"),
            ],
            outcome="failure",
            settlement_quality="failure_with_signal",
        ),
    ]
    config = GuardedActivationConfig(
        activation_enabled=True,
        policy_id=REFINED_POLICY_ID,
        mode="guarded",
    )
    results = run_guarded_experiment(traces, config)
    summary = results["experiment_summary"]

    assert summary["globally_active"] is False
    assert summary["metabolized"] is False


def test_experiment_status_tested_needs_more_evidence_when_fires_below_5():
    """With <5 interventions, status should be tested_needs_more_evidence."""
    traces = [
        _baseline_trace(
            f"run-{i}",
            [
                _event(0, "tool_result", f"Error: first_{i}", run_id=f"run-{i}"),
                _event(1, "tool_result", f"Error: second_{i}", run_id=f"run-{i}"),
            ],
            outcome="failure",
            settlement_quality="failure_with_signal",
        )
        for i in range(3)
    ]
    config = GuardedActivationConfig(
        activation_enabled=True,
        policy_id=REFINED_POLICY_ID,
        mode="guarded",
    )
    results = run_guarded_experiment(traces, config)
    summary = results["experiment_summary"]

    assert summary["total_policy_fires"] == 3
    assert summary["status_recommendation"] == "tested_needs_more_evidence"
    assert summary["globally_active"] is False


def test_experiment_no_activation_when_disabled():
    traces = [
        _baseline_trace(
            "run-a",
            [
                _event(0, "tool_result", "Error: first", run_id="run-a"),
                _event(1, "tool_result", "Error: second", run_id="run-a"),
            ],
            outcome="failure",
            settlement_quality="failure_with_signal",
        ),
    ]
    config = GuardedActivationConfig(
        activation_enabled=False,
        policy_id=REFINED_POLICY_ID,
        mode="guarded",
    )
    results = run_guarded_experiment(traces, config)

    assert results["experiment_summary"]["total_policy_fires"] == 0
    assert len(results["interventions"]) == 0


def test_experiment_intervention_records_have_valid_schema():
    traces = [
        _baseline_trace(
            "run-a",
            [
                _event(0, "tool_result", "Error: first failure", run_id="run-a"),
                _event(1, "tool_result", "Traceback: second failure", run_id="run-a"),
                _event(2, "task_complete", "done", run_id="run-a"),
            ],
            outcome="failure",
            settlement_quality="failure_with_signal",
        ),
    ]
    config = GuardedActivationConfig(
        activation_enabled=True,
        policy_id=REFINED_POLICY_ID,
        mode="guarded",
    )
    results = run_guarded_experiment(traces, config)

    for intervention in results["interventions"]:
        errors = validate_intervention_record(intervention)
        assert errors == [], f"Intervention schema errors: {errors}"


def test_experiment_baseline_comparison_captures_helpfulness():
    traces = [
        _baseline_trace(
            "run-fail",
            [
                _event(0, "tool_result", "Error: first", run_id="run-fail"),
                _event(1, "tool_result", "Error: second", run_id="run-fail"),
            ],
            outcome="failure",
            settlement_quality="failure_with_signal",
        ),
        _baseline_trace(
            "run-success",
            [
                _event(0, "tool_result", "Error: first", run_id="run-success"),
                _event(1, "tool_result", "Error: second", run_id="run-success"),
            ],
            outcome="success",
            settlement_quality="recovered_success",
        ),
    ]
    config = GuardedActivationConfig(
        activation_enabled=True,
        policy_id=REFINED_POLICY_ID,
        mode="guarded",
    )
    results = run_guarded_experiment(traces, config)
    comparison = results["experiment_summary"]["baseline_comparison"]

    fail_comp = next(c for c in comparison if c["run_id"] == "run-fail")
    assert fail_comp["helpfulness_assessment"] == "potentially_helpful"
    assert fail_comp["intervention_fired"] is True

    success_comp = next(c for c in comparison if c["run_id"] == "run-success")
    assert success_comp["helpfulness_assessment"] == "false_positive"
    assert success_comp["intervention_fired"] is True


def test_experiment_harmful_count_always_zero_in_replay():
    """Replay mode cannot observe harmful interventions (no agent response)."""
    traces = [
        _baseline_trace(
            "run-a",
            [
                _event(0, "tool_result", "Error: first", run_id="run-a"),
                _event(1, "tool_result", "Error: second", run_id="run-a"),
            ],
            outcome="failure",
            settlement_quality="failure_with_signal",
        ),
    ]
    config = GuardedActivationConfig(
        activation_enabled=True,
        policy_id=REFINED_POLICY_ID,
        mode="guarded",
    )
    results = run_guarded_experiment(traces, config)

    assert results["experiment_summary"]["harmful_intervention_count"] == 0


def test_experiment_interventions_completed_always_zero_in_replay():
    """Replay mode has no agent responses, so completed count is always 0."""
    traces = [
        _baseline_trace(
            "run-a",
            [
                _event(0, "tool_result", "Error: first", run_id="run-a"),
                _event(1, "tool_result", "Error: second", run_id="run-a"),
            ],
            outcome="failure",
            settlement_quality="failure_with_signal",
        ),
    ]
    config = GuardedActivationConfig(
        activation_enabled=True,
        policy_id=REFINED_POLICY_ID,
        mode="guarded",
    )
    results = run_guarded_experiment(traces, config)

    assert results["experiment_summary"]["interventions_completed"] == 0


# --- Adaptive recovery detection tests ---


def test_adaptive_recovery_detects_inspection_tool_call():
    """A tool_call that inspects logs between errors should be adaptive."""
    events_between = [
        _event(3, "model_message", "Let me check the server logs"),
        _event(4, "tool_call", "cat /var/log/app/server.log | tail -50"),
    ]
    current = _event(5, "tool_result", "Traceback: RuntimeError: pool exhausted")

    result = detect_adaptive_recovery(events_between, current)

    assert result["post_error_behavior"] == "adaptive_recovery"
    assert result["confidence"] > 0
    assert any(
        "tool_call_inspection" in e or "tool_call_diagnostic" in e
        for e in result["evidence"]
    )


def test_adaptive_recovery_detects_parameter_variation():
    """A tool_call with changed parameters between errors should be adaptive."""
    events_between = [
        _event(
            3,
            "tool_call",
            "pip install numpy==1.26.4 --index-url https://pypi.org/simple/",
        ),
    ]
    current = _event(4, "tool_result", "ERROR: No matching distribution found")

    result = detect_adaptive_recovery(events_between, current)

    assert result["post_error_behavior"] == "adaptive_recovery"
    assert any("parameter_variation" in e for e in result["evidence"])


def test_adaptive_recovery_detects_strategy_revision_event():
    """An explicit strategy_revision event between errors should be adaptive."""
    events_between = [
        _event(3, "strategy_revision", "Revised plan: inspect database config"),
    ]
    current = _event(4, "tool_result", "Error: second failure")

    result = detect_adaptive_recovery(events_between, current)

    assert result["post_error_behavior"] == "adaptive_recovery"
    assert "explicit_strategy_revision_event" in result["evidence"]


def test_non_adaptive_continuation_detected_on_retry():
    """Current event with 'retry' language should be non-adaptive."""
    events_between = []
    current = _event(3, "model_message", "This might be a flaky test. Let me retry.")

    result = detect_adaptive_recovery(events_between, current)

    assert result["post_error_behavior"] == "non_adaptive_continuation"
    assert any("non_adaptive" in e for e in result["evidence"])


def test_non_adaptive_continuation_detected_on_rerun():
    """Current event with 'rerun' language should be non-adaptive."""
    events_between = []
    current = _event(3, "model_message", "Let me rerun the same test")

    result = detect_adaptive_recovery(events_between, current)

    assert result["post_error_behavior"] == "non_adaptive_continuation"


def test_unknown_when_no_evidence():
    """No adaptive or non-adaptive evidence should return unknown."""
    events_between = []
    current = _event(3, "tool_result", "Error: second failure")

    result = detect_adaptive_recovery(events_between, current)

    assert result["post_error_behavior"] == "unknown"
    assert result["confidence"] == 0.0


def test_message_only_without_actions_is_unknown():
    """Model messages saying 'check' but no actual adaptive actions should be unknown."""
    events_between = [
        _event(3, "model_message", "Let me check what's available and retry"),
    ]
    current = _event(4, "tool_result", "Error: second failure")

    result = detect_adaptive_recovery(events_between, current)

    # "check" in model message but "retry" makes it non-adaptive at message level,
    # and no tool_call actions -> should be unknown or non-adaptive
    assert result["post_error_behavior"] in ("unknown", "non_adaptive_continuation")


def test_adaptive_recovery_suppresses_intervention():
    """When adaptive recovery is detected, no intervention should fire."""
    experiment = GuardedActivationExperiment(
        GuardedActivationConfig(activation_enabled=True, mode="guarded")
    )
    # First error
    experiment.record_event(_event(0, "tool_result", "Error: first failure"))
    # Adaptive action between errors
    experiment.record_event(_event(1, "tool_call", "cat /var/log/app/server.log"))
    # Second error — should be suppressed
    result = experiment.record_event(_event(2, "tool_result", "Error: second failure"))

    assert result == []
    assert len(experiment.suppressions) == 1
    assert (
        experiment.suppressions[0]["suppression_reason"]
        == "adaptive_recovery_behavior_detected"
    )
    assert experiment.suppressions[0]["suppression_evidence"]


def test_non_adaptive_continuation_still_fires():
    """When no adaptive recovery is detected, intervention should still fire."""
    experiment = GuardedActivationExperiment(
        GuardedActivationConfig(activation_enabled=True, mode="guarded")
    )
    # First error
    experiment.record_event(_event(0, "tool_result", "Error: first failure"))
    # Non-adaptive: just retrying
    experiment.record_event(_event(1, "model_message", "Let me retry the same command"))
    # Second error — should fire
    result = experiment.record_event(_event(2, "tool_result", "Error: second failure"))

    assert len(result) == 1
    assert len(experiment.suppressions) == 0


def test_baseline_002_pattern_suppressed():
    """Simulate baseline-002 pattern: error, check logs, error from logs -> suppressed."""
    experiment = GuardedActivationExperiment(
        GuardedActivationConfig(activation_enabled=True, mode="guarded")
    )
    experiment.record_event(_event(0, "model_message", "I need to debug the tests"))
    experiment.record_event(_event(1, "tool_call", "pytest tests/test_payments.py -x"))
    experiment.record_event(
        _event(2, "tool_result", "FAILED test_charge - AssertionError")
    )
    # Adaptive: checking logs
    experiment.record_event(_event(3, "model_message", "Let me check the server logs"))
    experiment.record_event(
        _event(4, "tool_call", "cat /var/log/app/server.log | tail -50")
    )
    # Second error from the diagnostic itself
    result = experiment.record_event(
        _event(5, "tool_result", "Traceback: RuntimeError: pool exhausted")
    )

    assert result == []
    assert len(experiment.suppressions) >= 1
    assert (
        experiment.suppressions[0]["suppression_reason"]
        == "adaptive_recovery_behavior_detected"
    )


def test_baseline_008_pattern_suppressed():
    """Simulate baseline-008 pattern: error, parameter variation, error -> suppressed."""
    experiment = GuardedActivationExperiment(
        GuardedActivationConfig(activation_enabled=True, mode="guarded")
    )
    experiment.record_event(_event(0, "model_message", "CI build is failing"))
    experiment.record_event(_event(1, "tool_call", "pip install -r requirements.txt"))
    experiment.record_event(
        _event(2, "tool_result", "ERROR: Could not find numpy==1.26.4")
    )
    # Adaptive: trying with different index
    experiment.record_event(
        _event(
            3,
            "tool_call",
            "pip install numpy==1.26.4 --index-url https://pypi.org/simple/",
        )
    )
    # Second error
    result = experiment.record_event(
        _event(4, "tool_result", "ERROR: No matching distribution for numpy==1.26.4")
    )

    assert result == []
    assert len(experiment.suppressions) >= 1


def test_baseline_001_pattern_retained():
    """Simulate baseline-001 pattern: error, same command retry, error -> fires."""
    experiment = GuardedActivationExperiment(
        GuardedActivationConfig(activation_enabled=True, mode="guarded")
    )
    experiment.record_event(_event(0, "model_message", "Running the tests"))
    experiment.record_event(
        _event(1, "tool_call", "python -m pytest tests/test_auth.py -v")
    )
    experiment.record_event(
        _event(2, "tool_result", "ImportError: cannot import UserModel")
    )
    # Non-adaptive: says "check" but also "retry", and reruns same command
    experiment.record_event(
        _event(3, "model_message", "Let me check what's available and retry")
    )
    experiment.record_event(
        _event(4, "tool_call", "python -m pytest tests/test_auth.py -v")
    )
    # Second error
    result = experiment.record_event(
        _event(5, "tool_result", "ImportError: cannot import AuthToken")
    )

    assert len(result) == 1
    assert result[0]["policy_id"] == REFINED_POLICY_ID


def test_baseline_004_pattern_retained():
    """Simulate baseline-004 pattern: tool_call flagged as error, then error result -> fires early.

    In the actual baseline-004 trace, the pytest command at step 1 is flagged
    as error_detected by signal inference, and the TimeoutError at step 2 is
    the second error. The intervention fires at step 2 because there's no
    adaptive recovery between the two errors.
    """
    experiment = GuardedActivationExperiment(
        GuardedActivationConfig(activation_enabled=True, mode="guarded")
    )
    experiment.record_event(_event(0, "model_message", "Running integration tests"))
    # Step 1: pytest command — signal inference flags this as error_detected
    experiment.record_event(
        _event(1, "tool_call", "pytest tests/integration/ -v --timeout=60")
    )
    # Step 2: TimeoutError — second error, no adaptive recovery between them
    result = experiment.record_event(
        _event(2, "tool_result", "FAILED - TimeoutError: request timed out after 30s")
    )

    assert len(result) == 1
    assert result[0]["policy_id"] == REFINED_POLICY_ID


def test_suppression_record_includes_evidence():
    """Suppression records must include reason and evidence."""
    experiment = GuardedActivationExperiment(
        GuardedActivationConfig(activation_enabled=True, mode="guarded")
    )
    experiment.record_event(_event(0, "tool_result", "Error: first failure"))
    experiment.record_event(_event(1, "tool_call", "cat /var/log/app/server.log"))
    experiment.record_event(_event(2, "tool_result", "Error: second failure"))

    assert len(experiment.suppressions) == 1
    s = experiment.suppressions[0]
    assert "run_id" in s
    assert "step_index" in s
    assert "policy_id" in s
    assert s["suppression_reason"] == "adaptive_recovery_behavior_detected"
    assert isinstance(s["suppression_evidence"], list)
    assert len(s["suppression_evidence"]) > 0
    assert "recovery_confidence" in s


def test_no_global_activation_after_suppression():
    """Suppressions do not constitute global activation."""
    experiment = GuardedActivationExperiment(
        GuardedActivationConfig(activation_enabled=True, mode="guarded")
    )
    experiment.record_event(_event(0, "tool_result", "Error: first failure"))
    experiment.record_event(_event(1, "tool_call", "cat /var/log/app/server.log"))
    experiment.record_event(_event(2, "tool_result", "Error: second failure"))

    run_summary = experiment.finalize_run(
        final_outcome="success", settlement_quality="recovered_success"
    )
    assert run_summary["intervention_count"] == 0
    assert run_summary["suppression_count"] == 1


def test_no_metabolization_after_suppression():
    """Suppressions do not constitute metabolization."""
    experiment = GuardedActivationExperiment(
        GuardedActivationConfig(activation_enabled=True, mode="guarded")
    )
    experiment.record_event(_event(0, "tool_result", "Error: first failure"))
    experiment.record_event(_event(1, "tool_call", "cat /var/log/app/server.log"))
    experiment.record_event(_event(2, "tool_result", "Error: second failure"))

    run_summary = experiment.finalize_run(
        final_outcome="success", settlement_quality="recovered_success"
    )
    # Status should be needs_more_evidence (no interventions), not metabolized
    assert run_summary["status"] == "needs_more_evidence"


def test_file_edit_between_errors_is_adaptive():
    """A file_edit between errors should be classified as adaptive."""
    events_between = [
        _event(
            3, "file_edit", "Increased pool_size from 5 to 20 in config/database.yml"
        ),
    ]
    current = _event(4, "tool_result", "Error: second failure")

    result = detect_adaptive_recovery(events_between, current)
    assert result["post_error_behavior"] == "adaptive_recovery"
    assert "file_edit_action" in result["evidence"]


def test_adaptive_actions_override_non_adaptive_message():
    """If there are adaptive tool calls but the current event says 'retry',
    the current non-adaptive action wins."""
    events_between = [
        _event(3, "tool_call", "cat /var/log/app/server.log"),
    ]
    current = _event(4, "model_message", "Let me retry the same command")

    result = detect_adaptive_recovery(events_between, current)
    # Current event has non-adaptive "retry" -> non-adaptive wins
    assert result["post_error_behavior"] == "non_adaptive_continuation"


# --- Live pilot tests ---


def test_pilot_mode_disabled_by_default():
    """Pilot mode requires explicit activation_enabled=True."""
    config = config_from_env()
    assert config.activation_enabled is False
    assert config.mode == "shadow"


def test_pilot_guarded_enabled_explicitly():
    """Pilot config must be explicitly enabled."""
    config = GuardedActivationConfig(
        activation_enabled=True,
        policy_id=REFINED_POLICY_ID,
        mode="guarded",
        max_fires_per_run=1,
    )
    assert config.activation_enabled is True
    assert config.mode == "guarded"


def test_pilot_runs_all_scenarios():
    """Pilot should run all 10 scenarios."""
    results = run_live_pilot()
    assert results["pilot_summary"]["total_live_runs"] == 10


def test_pilot_produces_expected_fires():
    """Pilot should fire on scenarios designed to trigger the policy."""
    results = run_live_pilot()
    summary = results["pilot_summary"]
    # 7 scenarios should fire (01-05, 08-09)
    assert summary["total_policy_fires"] == 7


def test_pilot_agent_response_captured():
    """Agent responses should be captured for all interventions."""
    results = run_live_pilot()
    assert len(results["agent_responses"]) > 0
    for response in results["agent_responses"]:
        assert "run_id" in response
        assert "intervention_step" in response
        assert "agent_response_type" in response
        assert "strategy_revised" in response
        assert "recovery_occurred" in response


def test_pilot_post_intervention_actions_captured():
    """Post-intervention actions should be recorded."""
    results = run_live_pilot()
    assert len(results["post_intervention_actions"]) > 0
    for action in results["post_intervention_actions"]:
        assert "run_id" in action
        assert "step_index" in action
        assert "event_type" in action
        assert "is_lower_payment" in action


def test_pilot_max_one_intervention_per_run():
    """No run should have more than one intervention."""
    results = run_live_pilot()
    for summary in results["run_summaries"]:
        assert summary["intervention_count"] <= 1


def test_pilot_no_global_activation():
    """Pilot summary must show globally_active=False."""
    results = run_live_pilot()
    assert results["pilot_summary"]["globally_active"] is False


def test_pilot_no_metabolization():
    """Pilot summary must show metabolized=False."""
    results = run_live_pilot()
    assert results["pilot_summary"]["metabolized"] is False


def test_pilot_summary_generation():
    """Pilot summary should contain all required fields."""
    results = run_live_pilot()
    summary = results["pilot_summary"]
    required_fields = [
        "pilot_id",
        "policy_id",
        "policy_mode",
        "activation_enabled",
        "total_live_runs",
        "total_policy_fires",
        "total_interventions",
        "interventions_with_agent_response",
        "strategy_revision_count",
        "post_intervention_recovery_count",
        "revised_plan_compliance_rate",
        "helpful_intervention_count",
        "harmful_intervention_count",
        "false_positive_count",
        "status_recommendation",
        "metabolized",
        "globally_active",
        "operator_notes",
    ]
    for field in required_fields:
        assert field in summary, f"Missing field: {field}"


def test_pilot_status_is_live_pilot_tested():
    """With 7 fires, 0 harmful, and recoveries, status should be live_pilot_tested."""
    results = run_live_pilot()
    assert results["pilot_summary"]["status_recommendation"] == "live_pilot_tested"


def test_pilot_zero_harmful_interventions():
    """No interventions should be classified as harmful."""
    results = run_live_pilot()
    assert results["pilot_summary"]["harmful_intervention_count"] == 0


def test_pilot_intervention_records_valid():
    """All intervention records should pass schema validation."""
    results = run_live_pilot()
    for intervention in results["interventions"]:
        errors = validate_intervention_record(intervention)
        assert errors == [], f"Intervention schema errors: {errors}"


def test_pilot_artifacts_written_to_disk():
    """All pilot artifacts should be writable to disk."""
    results = run_live_pilot()
    with tempfile.TemporaryDirectory() as td:
        from pathlib import Path

        paths = write_pilot_artifacts(results, Path(td))
        assert paths["events"].exists()
        assert paths["policy_fires"].exists()
        assert paths["interventions"].exists()
        assert paths["agent_responses"].exists()
        assert paths["post_intervention_actions"].exists()
        assert paths["run_summaries"].exists()
        assert paths["pilot_summary"].exists()

        # Verify content
        import json

        summary = json.loads(paths["pilot_summary"].read_text())
        assert summary["pilot_id"] == PILOT_ID
        assert summary["globally_active"] is False
        assert summary["metabolized"] is False


def test_pilot_strategy_revision_compliance():
    """Most interventions should show strategy revision."""
    results = run_live_pilot()
    summary = results["pilot_summary"]
    # 6 of 7 interventions with response show strategy revision
    assert summary["strategy_revision_count"] >= 5
    assert summary["revised_plan_compliance_rate"] >= 0.7


def test_pilot_recovery_evidence():
    """Most interventions should show post-intervention recovery."""
    results = run_live_pilot()
    summary = results["pilot_summary"]
    assert summary["post_intervention_recovery_count"] >= 5


def test_expanded_experiment_summary_metrics():
    """Verify that expanded metrics are computed correctly in experiment summary."""
    traces = [
        _baseline_trace(
            "run-helpful",
            [
                _event(
                    0, "tool_result", "ImportError: auth failed", run_id="run-helpful"
                ),
                _event(
                    1, "tool_result", "ImportError: db failed", run_id="run-helpful"
                ),
            ],
            outcome="failure",
            settlement_quality="failure_with_signal",
        ),
        _baseline_trace(
            "run-suppressed",
            [
                _event(0, "tool_result", "Error: first", run_id="run-suppressed"),
                _event(1, "tool_call", "cat config.py", run_id="run-suppressed"),
                _event(2, "tool_result", "Error: second", run_id="run-suppressed"),
            ],
            outcome="success",
            settlement_quality="recovered_success",
        ),
    ]
    config = GuardedActivationConfig(
        activation_enabled=True,
        policy_id=REFINED_POLICY_ID,
        mode="guarded",
    )
    results = run_guarded_experiment(traces, config)
    summary = results["experiment_summary"]

    assert "false_positive_rate" in summary
    assert "suppression_accuracy" in summary
    assert "retained_helpful_cases_from_002" in summary
    assert "lost_helpful_cases" in summary
    assert "repeated_error_loop_reduction" in summary
    assert "payment_cost" in summary
    assert "settlement_quality_distribution" in summary
    assert "task_type_distribution" in summary
    assert "gate_passed" in summary
    assert "gate_criteria" in summary

    assert summary["false_positive_rate"] == 0.0
    assert summary["suppression_accuracy"] == 1.0
    assert (
        summary["retained_helpful_cases_from_002"] == 0
    )  # mock run-helpful is not baseline-001/004
    assert summary["payment_cost"] == 0.0
    assert summary["settlement_quality_distribution"]["recovered_success"] == 1
    assert summary["settlement_quality_distribution"]["failure_with_signal"] == 1


def test_suppressions_output_file_checking():
    """Verify write_experiment_artifacts writes suppressions output file."""
    traces = [
        _baseline_trace(
            "run-suppressed",
            [
                _event(0, "tool_result", "Error: first", run_id="run-suppressed"),
                _event(1, "tool_call", "cat config.py", run_id="run-suppressed"),
                _event(2, "tool_result", "Error: second", run_id="run-suppressed"),
            ],
            outcome="success",
            settlement_quality="recovered_success",
        ),
    ]
    config = GuardedActivationConfig(
        activation_enabled=True,
        policy_id=REFINED_POLICY_ID,
        mode="guarded",
    )
    results = run_guarded_experiment(traces, config)

    with tempfile.TemporaryDirectory() as td:
        from pathlib import Path

        paths = write_experiment_artifacts(results, Path(td))

        assert paths["suppressions"].exists()
        suppressions = read_records_jsonl(paths["suppressions"])
        assert len(suppressions) == 1
        assert (
            suppressions[0]["suppression_reason"]
            == "adaptive_recovery_behavior_detected"
        )


def test_false_positive_rate_calculation():
    """Verify false-positive rate is correctly computed."""
    traces = [
        _baseline_trace(
            "run-fp",
            [
                _event(0, "tool_result", "ImportError: first", run_id="run-fp"),
                _event(1, "tool_result", "ImportError: second", run_id="run-fp"),
            ],
            outcome="success",
            settlement_quality="recovered_success",
        ),
    ]
    config = GuardedActivationConfig(
        activation_enabled=True,
        policy_id=REFINED_POLICY_ID,
        mode="guarded",
    )
    results = run_guarded_experiment(traces, config)
    summary = results["experiment_summary"]

    assert summary["total_policy_fires"] == 1
    assert summary["false_positive_count"] == 1
    assert summary["false_positive_rate"] == 1.0


def test_candidate_for_activation_gate_logic():
    """Verify candidate_for_activation gate check passes and fails under proper conditions."""
    # Condition A: Fails gate because we have only 4 interventions (<5)
    traces_below_5 = [
        _baseline_trace(
            f"run-{i}",
            [
                _event(0, "tool_result", f"Error: first_{i}", run_id=f"run-{i}"),
                _event(1, "tool_result", f"Error: second_{i}", run_id=f"run-{i}"),
            ],
            outcome="failure",
            settlement_quality="failure_with_signal",
        )
        for i in range(4)
    ]
    config = GuardedActivationConfig(
        activation_enabled=True,
        policy_id=REFINED_POLICY_ID,
        mode="guarded",
    )
    results = run_guarded_experiment(traces_below_5, config)
    assert results["experiment_summary"]["gate_passed"] is False
    assert (
        results["experiment_summary"]["status_recommendation"]
        == "tested_needs_more_evidence"
    )

    # Condition B: Passes gate when >=5 interventions, 0 harmful, and <=10% FPR
    traces_passing = [
        _baseline_trace(
            f"run-{i}",
            [
                _event(0, "tool_result", f"Error: first_{i}", run_id=f"run-{i}"),
                _event(1, "tool_result", f"Error: second_{i}", run_id=f"run-{i}"),
            ],
            outcome="failure",
            settlement_quality="failure_with_signal",
        )
        for i in range(5)
    ]
    results_passing = run_guarded_experiment(traces_passing, config)
    assert results_passing["experiment_summary"]["gate_passed"] is True
    assert (
        results_passing["experiment_summary"]["status_recommendation"]
        == "candidate_for_activation"
    )


def test_payment_cost_reporting():
    """Verify that payment cost is reported as 0.0 inside experiment summary."""
    traces = [
        _baseline_trace(
            "run-1",
            [
                _event(0, "tool_result", "Error: first", run_id="run-1"),
                _event(1, "tool_result", "Error: second", run_id="run-1"),
            ],
            outcome="failure",
            settlement_quality="failure_with_signal",
        ),
    ]
    config = GuardedActivationConfig(
        activation_enabled=True,
        policy_id=REFINED_POLICY_ID,
        mode="guarded",
    )
    results = run_guarded_experiment(traces, config)
    assert results["experiment_summary"]["payment_cost"] == 0.0


def test_no_global_activation_and_metabolization_protection():
    """Ensure that metabolized and globally_active are strictly false in expanded runs."""
    traces = [
        _baseline_trace(
            "run-1",
            [
                _event(0, "tool_result", "Error: first", run_id="run-1"),
                _event(1, "tool_result", "Error: second", run_id="run-1"),
            ],
            outcome="failure",
            settlement_quality="failure_with_signal",
        ),
    ]
    config = GuardedActivationConfig(
        activation_enabled=True,
        policy_id=REFINED_POLICY_ID,
        mode="guarded",
    )
    results = run_guarded_experiment(traces, config)
    summary = results["experiment_summary"]

    assert summary["metabolized"] is False
    assert summary["globally_active"] is False
