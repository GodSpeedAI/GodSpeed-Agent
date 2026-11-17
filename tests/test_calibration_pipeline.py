"""Tests for the agentic calibration pipeline.

Proof classification: external-proxy-settlement records are valid for
calibration experiments and baseline comparison only.  They must not
promote local capabilities, metabolization, or enterprise readiness.
"""

from pathlib import Path

import yaml


# ---------------------------------------------------------------------------
# Task 1: Calibration source manifest
# ---------------------------------------------------------------------------


def test_calibration_sources_manifest_declares_priority_and_external_proxy_classification():
    path = Path("configs/settlement_datasets/calibration_sources.yaml")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))

    assert data["target_usable_settlements"] == 500
    assert data["settlement_classification"] == "external-proxy-settlement"
    assert data["min_confidence"] == 0.65

    names = [item["name"] for item in data["datasets"]]
    assert names[:3] == [
        "swegym_openhands",
        "agenttrove",
        "nebius_swe_agent",
    ]

    for source in data["datasets"]:
        assert source["source_uri"]
        assert source["adapter"]
        assert source["split"]
        assert source["max_rows"] > 0
        assert source["priority"] > 0


# ---------------------------------------------------------------------------
# Task 2: Hugging Face streaming helper
# ---------------------------------------------------------------------------


def test_iter_limited_stops_after_limit():
    from scripts.settlement_datasets.hf_stream import iter_limited

    rows = list(iter_limited(iter([{"id": 1}, {"id": 2}, {"id": 3}]), limit=2))
    assert rows == [{"id": 1}, {"id": 2}]


def test_load_hf_stream_is_lazy_and_patchable(monkeypatch):
    from scripts.settlement_datasets.hf_stream import load_hf_stream

    calls = []

    def fake_load_dataset(source_uri, split, streaming=True):
        calls.append((source_uri, split, streaming))
        return iter([{"id": "row-1"}])

    monkeypatch.setattr(
        "scripts.settlement_datasets.hf_stream.load_dataset", fake_load_dataset
    )

    stream = load_hf_stream("repo/name", split="train")
    assert list(stream) == [{"id": "row-1"}]
    assert calls == [("repo/name", "train", True)]


# ---------------------------------------------------------------------------
# Task 3: SWE-Gym OpenHands adapter
# ---------------------------------------------------------------------------


def test_swegym_openhands_adapter_registered_and_validates_fixture():
    from scripts.settlement_datasets.registry import available_datasets, get_adapter

    assert "swegym_openhands" in available_datasets()
    adapter = get_adapter("swegym_openhands")
    fixture = Path("tests/fixtures/settlement_datasets/swegym_openhands/sample.jsonl")

    records = [
        adapter.to_settlement_record(raw)
        for raw in adapter.stream(input_path=str(fixture))
    ]

    assert len(records) == 2
    assert records[0]["dataset"] == "swegym_openhands"
    assert records[0]["outcome"]["success"] is True
    assert records[1]["outcome"]["success"] is False
    assert all(adapter.validate_record(record) == [] for record in records)


def test_swegym_openhands_adapter_handles_hf_schema_with_none_content_and_nested_test_result():
    """Verify the adapter handles the real HF schema where:
    - message content can be None (assistant messages with tool calls)
    - test_result is nested: test_result.report.resolved (not test_result.passed)
    - tools are {'function': {'name': ...}, 'type': 'function'}
    """
    from scripts.settlement_datasets.registry import get_adapter

    adapter = get_adapter("swegym_openhands")
    fixture = Path("tests/fixtures/settlement_datasets/swegym_openhands/sample.jsonl")

    records = [
        adapter.to_settlement_record(raw)
        for raw in adapter.stream(input_path=str(fixture))
    ]

    assert len(records) == 2
    # Row 0: resolved=true via test_result.report.resolved
    assert records[0]["outcome"]["success"] is True
    assert records[0]["outcome"]["confidence"] >= 0.65
    # Row 1: resolved=false
    assert records[1]["outcome"]["success"] is False
    assert records[1]["outcome"]["confidence"] >= 0.65
    # Payment should handle None content without crashing
    assert records[0]["payment"]["turns"] >= 0
    assert records[1]["payment"]["turns"] >= 0
    # Tools should be extracted from nested function structure
    tool_names = records[0]["metadata"].get("tool_names", [])
    assert any("bash" in str(t).lower() for t in tool_names)
    assert all(adapter.validate_record(record) == [] for record in records)


def test_nebius_swe_agent_adapter_registered_and_validates_fixture():
    from scripts.settlement_datasets.registry import available_datasets, get_adapter

    assert "nebius_swe_agent" in available_datasets()
    adapter = get_adapter("nebius_swe_agent")
    fixture = Path("tests/fixtures/settlement_datasets/nebius_swe_agent/sample.jsonl")

    records = [
        adapter.to_settlement_record(raw)
        for raw in adapter.stream(input_path=str(fixture))
    ]

    assert len(records) == 2
    assert records[0]["outcome"]["success"] is True
    assert records[1]["outcome"]["success"] is False
    assert records[0]["payment"]["commands"] >= 0
    assert all(adapter.validate_record(record) == [] for record in records)


def test_swe_smith_adapter_registered_and_validates_fixture():
    from scripts.settlement_datasets.registry import available_datasets, get_adapter

    assert "swe_smith" in available_datasets()
    adapter = get_adapter("swe_smith")
    fixture = Path("tests/fixtures/settlement_datasets/swe_smith/sample.jsonl")

    records = [
        adapter.to_settlement_record(raw)
        for raw in adapter.stream(input_path=str(fixture))
    ]

    assert len(records) == 3
    assert records[0]["outcome"]["success"] is True
    assert records[1]["outcome"]["success"] is False
    assert records[1]["payment"]["error_count"] >= 1
    assert all(adapter.validate_record(record) == [] for record in records)


# ---------------------------------------------------------------------------
# Task 5: Calibration pipeline orchestrator
# ---------------------------------------------------------------------------


def test_load_calibration_manifest_orders_sources_by_priority():
    from scripts.settlement_datasets.run_calibration_pipeline import (
        load_calibration_manifest,
    )

    manifest = load_calibration_manifest(
        "configs/settlement_datasets/calibration_sources.yaml"
    )
    assert [source["name"] for source in manifest["datasets"]][:3] == [
        "swegym_openhands",
        "agenttrove",
        "nebius_swe_agent",
    ]


def test_should_stop_for_target_when_enough_usable_settlements():
    from scripts.settlement_datasets.run_calibration_pipeline import (
        CalibrationRunState,
        should_stop_for_target,
    )

    state = CalibrationRunState(target_usable_settlements=500)
    state.usable_settlements = 500
    assert should_stop_for_target(state) is True


# ---------------------------------------------------------------------------
# Task 6: Dataset iteration, filtering, and resumable outputs
# ---------------------------------------------------------------------------


def test_calibration_pipeline_processes_fixture_sources_until_target(tmp_path):
    from scripts.settlement_datasets.run_calibration_pipeline import run_pipeline

    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        """
target_usable_settlements: 2
min_confidence: 0.65
settlement_classification: external-proxy-settlement
datasets:
  - name: swegym_openhands
    source_uri: local-fixture
    adapter: swegym_openhands
    split: train
    input_path: tests/fixtures/settlement_datasets/swegym_openhands/sample.jsonl
    max_rows: 10
    priority: 1
    streaming: false
""",
        encoding="utf-8",
    )

    result = run_pipeline(
        manifest_path=str(manifest),
        run_id="fixture-calibration",
        output_run_dir=tmp_path / "run",
        target_usable_settlements=2,
        min_confidence=0.65,
        provider="disabled",
    )

    assert result["usable_settlements"] == 2
    assert (tmp_path / "run" / "settlements" / "swegym_openhands.jsonl").exists()
    assert (tmp_path / "run" / "summary.json").exists()


# ---------------------------------------------------------------------------
# Task 7: Calibration frame export and sklearn evaluation
# ---------------------------------------------------------------------------


def test_calibration_pipeline_writes_calibration_frame_and_model_metrics(tmp_path):
    from scripts.settlement_datasets.run_calibration_pipeline import run_pipeline

    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        """
target_usable_settlements: 2
min_confidence: 0.65
settlement_classification: external-proxy-settlement
datasets:
  - name: swegym_openhands
    source_uri: local-fixture
    adapter: swegym_openhands
    split: train
    input_path: tests/fixtures/settlement_datasets/swegym_openhands/sample.jsonl
    max_rows: 10
    priority: 1
    streaming: false
""",
        encoding="utf-8",
    )

    result = run_pipeline(
        manifest_path=str(manifest),
        run_id="fixture-calibration",
        output_run_dir=tmp_path / "run",
        target_usable_settlements=2,
        min_confidence=0.65,
        provider="disabled",
    )

    assert "calibration_frame_path" in result
    assert "model_evaluation" in result


# ---------------------------------------------------------------------------
# Task 8: CLI entry point and resume behavior
# ---------------------------------------------------------------------------


def test_calibration_pipeline_cli_runs_fixture_manifest(tmp_path):
    import subprocess

    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        """
target_usable_settlements: 1
min_confidence: 0.65
settlement_classification: external-proxy-settlement
datasets:
  - name: swegym_openhands
    source_uri: local-fixture
    adapter: swegym_openhands
    split: train
    input_path: tests/fixtures/settlement_datasets/swegym_openhands/sample.jsonl
    max_rows: 1
    priority: 1
    streaming: false
""",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            "uv",
            "run",
            "python",
            "-m",
            "scripts.settlement_datasets.run_calibration_pipeline",
            "--manifest",
            str(manifest),
            "--run-id",
            "cli-fixture",
            "--output-run-dir",
            str(tmp_path / "run"),
            "--target-usable-settlements",
            "1",
            "--provider",
            "disabled",
        ],
        check=True,
        text=True,
        capture_output=True,
    )

    assert "usable_settlements" in result.stdout


# ---------------------------------------------------------------------------
# Task 10: Evidence report generation
# ---------------------------------------------------------------------------


def test_calibration_pipeline_writes_docs_report(tmp_path):
    from scripts.settlement_datasets.run_calibration_pipeline import run_pipeline

    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        """
target_usable_settlements: 2
min_confidence: 0.65
settlement_classification: external-proxy-settlement
datasets:
  - name: swegym_openhands
    source_uri: local-fixture
    adapter: swegym_openhands
    split: train
    input_path: tests/fixtures/settlement_datasets/swegym_openhands/sample.jsonl
    max_rows: 10
    priority: 1
    streaming: false
""",
        encoding="utf-8",
    )

    result = run_pipeline(
        manifest_path=str(manifest),
        run_id="fixture-report",
        output_run_dir=tmp_path / "run",
        target_usable_settlements=2,
        min_confidence=0.65,
        provider="disabled",
        report_dir=tmp_path / "docs",
    )

    report_path = Path(result["report_path"])
    assert report_path.exists()
    text = report_path.read_text(encoding="utf-8")
    assert "external-proxy-settlement" in text
    assert "usable settlements" in text
    assert "Proof Classification" in text


# ---------------------------------------------------------------------------
# Label leakage fix: horizon_delta must not encode the target
# ---------------------------------------------------------------------------


def test_horizon_delta_does_not_leak_success_label():
    """horizon_delta must be derived from pre-outcome proxy signals,
    not from outcome.success or settlement_success."""
    from scripts.settlement_datasets.run_calibration_pipeline import (
        external_record_to_model_calibration,
    )

    # A failure record with low error rate and moderate payment
    failure_record = {
        "dataset": "test",
        "task_id": "leak-check-fail",
        "payment": {
            "turns": 3,
            "tool_calls": 2,
            "commands": 3,
            "elapsed_steps": 10,
            "error_count": 1,
        },
        "outcome": {"success": False, "confidence": 0.8},
    }

    # A success record with high error rate and high payment
    success_record = {
        "dataset": "test",
        "task_id": "leak-check-success",
        "payment": {
            "turns": 8,
            "tool_calls": 7,
            "commands": 8,
            "elapsed_steps": 20,
            "error_count": 5,
        },
        "outcome": {"success": True, "confidence": 0.9},
    }

    fail_cal = external_record_to_model_calibration(failure_record)
    succ_cal = external_record_to_model_calibration(success_record)

    fail_hd = fail_cal["model_calibration"]["horizon_delta"]
    succ_hd = succ_cal["model_calibration"]["horizon_delta"]

    # Labels must remain correct
    assert fail_cal["model_calibration"]["settlement_success"] is False
    assert succ_cal["model_calibration"]["settlement_success"] is True

    # horizon_delta must NOT be a perfect function of success.
    # If success=False -> 0.0 and success=True -> 1.0, that is leakage.
    assert not (fail_hd == 0.0 and succ_hd == 1.0), (
        "horizon_delta directly encodes settlement_success (label leakage)"
    )

    # horizon_delta must be non-negative
    assert fail_hd >= 0.0
    assert succ_hd >= 0.0


def test_leakage_audit_flags_perfect_correlation(tmp_path):
    """The pipeline must detect and flag features that perfectly correlate
    with settlement_success."""
    from scripts.settlement_datasets.run_calibration_pipeline import (
        run_pipeline,
    )

    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        """
target_usable_settlements: 2
min_confidence: 0.65
settlement_classification: external-proxy-settlement
datasets:
  - name: swegym_openhands
    source_uri: local-fixture
    adapter: swegym_openhands
    split: train
    input_path: tests/fixtures/settlement_datasets/swegym_openhands/sample.jsonl
    max_rows: 10
    priority: 1
    streaming: false
""",
        encoding="utf-8",
    )

    result = run_pipeline(
        manifest_path=str(manifest),
        run_id="leakage-audit-test",
        output_run_dir=tmp_path / "run",
        target_usable_settlements=2,
        min_confidence=0.65,
        provider="disabled",
    )

    model_eval = result["model_evaluation"]
    assert "leakage_audit" in model_eval
    audit = model_eval["leakage_audit"]
    assert "feature_correlations" in audit
    assert "leaked_features" in audit


# ---------------------------------------------------------------------------
# Task: Held-out evaluation, balanced class_weight, sampling strategy, min-datasets
# ---------------------------------------------------------------------------


def test_held_out_evaluation_with_sklearn(tmp_path):
    """Pipeline with sklearn provider must produce held-out metrics
    when sufficient data exists and leakage is not detected."""
    from scripts.settlement_datasets.run_calibration_pipeline import (
        _evaluate_sklearn_held_out,
    )
    import pandas as pd
    import numpy as np

    np.random.seed(42)
    n = 100
    df = pd.DataFrame(
        {
            "settlement_id": [f"id-{i}" for i in range(n)],
            "payment_predicted_total": np.random.uniform(10, 60, n),
            "payment_actual_total": np.random.uniform(5, 50, n),
            "payment_error": np.random.uniform(0, 20, n),
            "settlement_success": np.random.choice([True, False], n, p=[0.3, 0.7]),
            "settlement_score": np.random.uniform(0, 1, n),
            "horizon_delta": np.random.uniform(0.5, 1.0, n),
            "risk_estimate": np.random.uniform(0, 0.5, n),
            "debt_estimate": np.random.uniform(0, 0.3, n),
        }
    )

    leakage_audit = {
        "feature_correlations": {"horizon_delta": 0.1, "risk_estimate": 0.2},
        "leaked_features": [],
        "leakage_detected": False,
    }

    result = _evaluate_sklearn_held_out(df, leakage_audit, "natural")
    assert result["sklearn_metrics_valid"] is True
    assert "held_out_metrics" in result
    assert "baseline_metrics" in result
    assert result["class_weight"] == "balanced"
    assert result["train_size"] > 0
    assert result["test_size"] > 0
    assert "roc_auc" in result["held_out_metrics"]
    assert "balanced_accuracy" in result["held_out_metrics"]
    assert "raw_accuracy" in result["held_out_metrics"]
    assert "f1_score" in result["held_out_metrics"]
    assert "brier_score" in result["held_out_metrics"]
    # Matched baseline metrics
    assert "majority_class_raw_accuracy" in result["baseline_metrics"]
    assert "majority_class_balanced_accuracy" in result["baseline_metrics"]
    assert "majority_class_f1" in result["baseline_metrics"]
    assert "success_rate_raw_accuracy" in result["baseline_metrics"]
    assert "success_rate_balanced_accuracy" in result["baseline_metrics"]
    assert "success_rate_f1" in result["baseline_metrics"]
    # Matched comparison flags
    assert "sklearn_beats_majority_on_balanced_accuracy" in result
    assert "sklearn_beats_majority_on_f1" in result
    assert "sklearn_beats_majority_on_raw_accuracy" in result


def test_sampling_strategy_balanced_option(tmp_path):
    """Pipeline accepts sampling_strategy='balanced' without error."""
    from scripts.settlement_datasets.run_calibration_pipeline import run_pipeline

    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        """
target_usable_settlements: 2
min_confidence: 0.65
settlement_classification: external-proxy-settlement
datasets:
  - name: swegym_openhands
    source_uri: local-fixture
    adapter: swegym_openhands
    split: train
    input_path: tests/fixtures/settlement_datasets/swegym_openhands/sample.jsonl
    max_rows: 10
    priority: 1
    streaming: false
""",
        encoding="utf-8",
    )

    result = run_pipeline(
        manifest_path=str(manifest),
        run_id="balanced-test",
        output_run_dir=tmp_path / "run",
        target_usable_settlements=2,
        min_confidence=0.65,
        provider="sklearn",
        sampling_strategy="balanced",
    )

    model_eval = result["model_evaluation"]
    if "held_out_evaluation" in model_eval:
        assert model_eval["held_out_evaluation"]["sampling_strategy"] == "balanced"


def test_min_datasets_processes_multiple_sources(tmp_path):
    """With min_datasets=2, pipeline must process at least 2 datasets
    even if target is reached from the first."""
    from scripts.settlement_datasets.run_calibration_pipeline import run_pipeline

    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        """
target_usable_settlements: 1
min_confidence: 0.65
settlement_classification: external-proxy-settlement
datasets:
  - name: swegym_openhands
    source_uri: local-fixture
    adapter: swegym_openhands
    split: train
    input_path: tests/fixtures/settlement_datasets/swegym_openhands/sample.jsonl
    max_rows: 10
    priority: 1
    streaming: false
  - name: nebius_swe_agent
    source_uri: local-fixture
    adapter: nebius_swe_agent
    split: train
    input_path: tests/fixtures/settlement_datasets/nebius_swe_agent/sample.jsonl
    max_rows: 10
    priority: 2
    streaming: false
""",
        encoding="utf-8",
    )

    result = run_pipeline(
        manifest_path=str(manifest),
        run_id="min-ds-test",
        output_run_dir=tmp_path / "run",
        target_usable_settlements=1,
        min_confidence=0.65,
        provider="disabled",
        min_datasets=2,
    )

    # Both datasets must appear in dataset_counts
    assert "swegym_openhands" in result["dataset_counts"]
    assert "nebius_swe_agent" in result["dataset_counts"]
    # Both must have been scanned
    assert result["dataset_counts"]["nebius_swe_agent"]["scanned"] > 0


# ---------------------------------------------------------------------------
# Richer pre-outcome features
# ---------------------------------------------------------------------------


def test_new_features_are_pre_outcome_and_present():
    """New features must be derived from payment/affordance_path/metadata
    only, never from outcome.success or settlement labels."""
    from scripts.settlement_datasets.run_calibration_pipeline import (
        external_record_to_model_calibration,
    )

    # A record with rich affordance_path data
    record = {
        "dataset": "swegym_openhands",
        "task_id": "feat-test-1",
        "payment": {
            "turns": 5,
            "tool_calls": 4,
            "commands": 5,
            "elapsed_steps": 12,
            "error_count": 2,
        },
        "outcome": {"success": True, "confidence": 0.9},
        "affordance_path": {
            "actions": [
                {
                    "turn_index": 0,
                    "role": "assistant",
                    "action_type": "message",
                    "content": "edit file",
                },
                {
                    "turn_index": 2,
                    "role": "assistant",
                    "action_type": "message",
                    "content": "run tests",
                },
                {
                    "turn_index": 4,
                    "role": "assistant",
                    "action_type": "message",
                    "content": "fix error",
                },
                {
                    "turn_index": 6,
                    "role": "assistant",
                    "action_type": "message",
                    "content": "run tests again",
                },
                {
                    "turn_index": 8,
                    "role": "assistant",
                    "action_type": "message",
                    "content": "done",
                },
            ],
            "observations": [
                {"turn_index": 1, "role": "tool", "content": "file edited"},
                {"turn_index": 3, "role": "tool", "content": "test failed with error"},
                {"turn_index": 5, "role": "tool", "content": "fix applied"},
                {"turn_index": 7, "role": "tool", "content": "all tests passed"},
            ],
            "recovery_events": [],
        },
        "metadata": {
            "tool_names": ["execute_bash", "str_replace_editor", "finish"],
            "settlement_classification": "external-proxy-settlement",
        },
    }

    cal = external_record_to_model_calibration(record)
    mc = cal["model_calibration"]

    # New features must exist
    assert "tool_diversity_count" in mc
    assert "error_recovery_ratio" in mc
    assert "action_observation_ratio" in mc
    assert "avg_actions_per_step" in mc
    assert "dataset_id" in mc

    # tool_diversity_count: count of distinct tools
    assert mc["tool_diversity_count"] == 3  # execute_bash, str_replace_editor, finish

    # error_recovery_ratio: must be between 0 and 1
    assert 0.0 <= mc["error_recovery_ratio"] <= 1.0

    # action_observation_ratio: actions / observations
    assert mc["action_observation_ratio"] > 0.0

    # avg_actions_per_step: actions / elapsed_steps
    assert mc["avg_actions_per_step"] > 0.0


def test_new_features_do_not_leak_labels():
    """New features must not change when outcome.success flips."""
    from scripts.settlement_datasets.run_calibration_pipeline import (
        external_record_to_model_calibration,
    )

    base = {
        "dataset": "test",
        "task_id": "leak-check",
        "payment": {
            "turns": 3,
            "tool_calls": 2,
            "commands": 3,
            "elapsed_steps": 10,
            "error_count": 1,
        },
        "affordance_path": {
            "actions": [
                {"turn_index": 0, "role": "assistant", "content": "a"},
                {"turn_index": 2, "role": "assistant", "content": "b"},
            ],
            "observations": [
                {"turn_index": 1, "role": "tool", "content": "error in test"},
                {"turn_index": 3, "role": "tool", "content": "ok"},
            ],
            "recovery_events": [],
        },
        "metadata": {"tool_names": ["bash", "edit"]},
    }

    success_rec = {**base, "outcome": {"success": True, "confidence": 0.9}}
    failure_rec = {**base, "outcome": {"success": False, "confidence": 0.8}}

    s_cal = external_record_to_model_calibration(success_rec)["model_calibration"]
    f_cal = external_record_to_model_calibration(failure_rec)["model_calibration"]

    # All new features must be identical regardless of outcome
    for feat in [
        "tool_diversity_count",
        "error_recovery_ratio",
        "action_observation_ratio",
        "avg_actions_per_step",
        "horizon_delta",
        "risk_estimate",
        "debt_estimate",
    ]:
        assert s_cal[feat] == f_cal[feat], (
            f"Feature {feat} differs between success and failure: "
            f"{s_cal[feat]} vs {f_cal[feat]}"
        )

    # Labels must differ
    assert s_cal["settlement_success"] is True
    assert f_cal["settlement_success"] is False
