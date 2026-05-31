from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

from scripts.settlement_datasets.run_evidence_pipeline import run_evidence_pipeline
from scripts.settlement_datasets.run_scoped_paths import (
    ensure_run_surface,
    load_target_profile,
    resolve_run_scope,
    write_run_manifest,
)
from scripts.settlement_datasets.target_profile_filtering import (
    apply_target_profile,
)


ROOT = Path(__file__).resolve().parents[1]


def _target_record(
    task_id: str,
    *,
    confidence: float = 0.8,
    second_error: bool = True,
    continuation_after_second_error: bool = True,
    strategy_revision_after_error: bool = False,
    duplicate_error_only: bool = False,
    task_complete: bool = True,
):
    observations = [
        {"turn_index": 1, "role": "user", "content": "New Terminal Output: Error: first failure"},
    ]
    if second_error:
        second_error_text = "New Terminal Output: Error: first failure" if duplicate_error_only else "New Terminal Output: Traceback: second failure"
        observations.append({"turn_index": 3, "role": "user", "content": second_error_text})

    actions = [
        {"turn_index": 0, "role": "assistant", "action_type": "command", "content": "pytest tests/test_example.py"},
    ]
    if continuation_after_second_error:
        if strategy_revision_after_error:
            actions.append(
                {
                    "turn_index": 4,
                    "role": "assistant",
                    "action_type": "text",
                    "content": "Revised plan: inspect the failing command before retrying",
                }
            )
        actions.append(
            {
                "turn_index": 5,
                "role": "assistant",
                "action_type": "command",
                "content": "pytest tests/test_example.py -k focused_case",
            }
        )
    if task_complete:
        actions.append(
            {
                "turn_index": 7,
                "role": "assistant",
                "action_type": "text",
                "content": "Final answer: task complete",
            }
        )

    return {
        "task_id": task_id,
        "dataset": "agenttrove",
        "domain": "code",
        "environment": {
            "type": "simulated_terminal",
            "has_runnable_feedback": True,
            "feedback_type": "tool_output",
        },
        "metadata": {"trace_id": task_id},
        "desired_direction": {"type": "action", "description": "debug the failing command"},
        "payment": {
            "turns": 8,
            "tool_calls": 0,
            "commands": 2 if continuation_after_second_error else 1,
            "page_actions": 0,
            "api_calls": 0,
            "elapsed_steps": 8,
            "error_count": 2 if second_error else 1,
            "estimated_complexity": "medium",
            "evidence": [],
        },
        "affordance_path": {"actions": actions, "observations": observations, "recovery_events": []},
        "labels": {
            "failure_mode": "failed_recovery",
            "failure_mode_confidence": 0.8,
            "failure_mode_evidence": [],
            "harness_policy_signal": None,
            "harness_policy_signal_confidence": 0.0,
            "harness_policy_signal_evidence": [],
            "metabolization_candidate": None,
            "metabolization_candidate_confidence": 0.0,
            "metabolization_candidate_evidence": [],
        },
        "outcome": {
            "success": False,
            "reward": None,
            "score": None,
            "settlement_quality": "failure_with_signal",
            "confidence": confidence,
            "evidence": ["task_complete:True:assistant_json"] if task_complete else [],
        },
        "representational_state": {
            "start": "unknown",
            "desired": "unknown",
            "path_shape": "unknown",
            "confidence": 0.0,
            "evidence": [],
        },
        "source_uri": "fixture://target-profile",
    }


def test_run_surface_creates_expected_directories(tmp_path: Path):
    scope = ensure_run_surface(run_id="smoke", output_run_dir=tmp_path / "smoke")

    assert scope.run_id == "smoke"
    for path in (
        scope.root,
        scope.raw_dir,
        scope.normalized_dir,
        scope.profiles_dir,
        scope.settlements_dir,
        scope.ledger_dir,
        scope.policies_dir,
        scope.shadow_dir,
        scope.replay_dir,
        scope.adjudication_dir,
        scope.metabolization_dir,
        scope.summaries_dir,
    ):
        assert path.exists()
        assert path.is_dir()


def test_resolve_run_scope_prefers_explicit_input_and_output_dirs(tmp_path: Path):
    input_dir = tmp_path / "input-run"
    output_dir = tmp_path / "output-run"
    input_dir.mkdir()

    scope = resolve_run_scope(
        run_id="ignored-by-output",
        input_run_dir=input_dir,
        output_run_dir=output_dir,
    )

    assert scope.root == output_dir
    assert scope.input_root == input_dir
    assert scope.run_id == "output-run"


def test_write_run_manifest_writes_required_fields(tmp_path: Path):
    scope = ensure_run_surface(run_id="manifest-run", output_run_dir=tmp_path / "manifest-run")
    manifest = {
        "run_id": scope.run_id,
        "created_at": "2026-05-31T00:00:00Z",
        "commands": [],
        "datasets": ["agenttrove"],
        "limits": {"limit": 10},
        "min_confidence": 0.65,
        "input_paths": {},
        "output_paths": {},
        "artifact_counts": {},
        "policy_counts": {},
        "eval_counts": {},
        "test_status": None,
    }

    path = write_run_manifest(scope, manifest)
    loaded = json.loads(path.read_text(encoding="utf-8"))

    assert loaded == manifest


def test_load_target_profile_reads_reflection_query():
    profile = load_target_profile("reflection_second_unresolved_error")

    assert profile["dataset"] == "agenttrove"
    assert "tool_or_environment_error" in profile["signals"]["require"]
    assert "multiple_error_events" in profile["signals"]["prefer"]
    assert "duplicate_error_only" in profile["signals"]["exclude"]
    assert "command_or_action_trace" in profile["signals"]["prefer"]
    assert "final_turn_only_error" in profile["signals"]["exclude"]


def test_target_profile_filtering_matches_only_qualifying_reflection_traces():
    profile = load_target_profile("reflection_second_unresolved_error")
    records = [
        _target_record("match-trace"),
        _target_record("duplicate-only", duplicate_error_only=True),
        _target_record("strategy-revision", strategy_revision_after_error=True),
        _target_record("no-continuation", continuation_after_second_error=False),
    ]

    matched, diagnostics = apply_target_profile(
        records,
        profile_name="reflection_second_unresolved_error",
        profile=profile,
        min_confidence=0.65,
    )

    assert [record["task_id"] for record in matched] == ["match-trace"]
    assert diagnostics["sampled_count"] == 4
    assert diagnostics["matched_count"] == 1
    assert diagnostics["high_confidence_count"] == 4
    assert diagnostics["signal_counts"]["two_or_more_unresolved_errors"] == 4
    assert diagnostics["signal_counts"]["same_path_continuation_after_second_error"] == 2
    assert diagnostics["signal_counts"]["no_strategy_revision_after_latest_error"] == 3
    assert diagnostics["signal_counts"]["recovery_opportunity_remaining"] == 3
    assert diagnostics["exclude_reason_counts"]["duplicate_error_only"] == 1
    assert diagnostics["exclude_reason_counts"]["strategy_revision_after_latest_error"] == 1
    assert diagnostics["exclude_reason_counts"]["no_action_after_error"] == 2


def test_pipeline_dry_run_writes_manifest_and_summary(tmp_path: Path):
    result = run_evidence_pipeline(
        run_id="smoke-run",
        dataset="agenttrove",
        limit=10,
        min_confidence=0.65,
        output_run_dir=tmp_path / "smoke-run",
        target_profile="reflection_second_unresolved_error",
        dry_run=True,
    )

    manifest = json.loads(result["manifest"].read_text(encoding="utf-8"))
    summary = json.loads(result["summary_json"].read_text(encoding="utf-8"))

    assert manifest["run_id"] == "smoke-run"
    assert manifest["datasets"] == ["agenttrove"]
    assert manifest["limits"]["limit"] == 10
    assert manifest["min_confidence"] == 0.65
    assert manifest["test_status"] is None
    assert result["summary_md"].exists()
    assert (tmp_path / "smoke-run" / "summary.json").exists()
    assert (tmp_path / "smoke-run" / "summary.md").exists()
    assert summary["trace_counts"]["ingested"] == 0
    assert summary["policy_fire_counts"]["total"] == 0
    assert summary["metabolization_candidate_status_counts"].get("metabolized", 0) == 0
    assert summary["policy_activation_count"] == 0
    assert "recommended_next_move" in summary


def test_scripts_help_includes_run_scoped_flags():
    modules = [
        "scripts.settlement_datasets.ingest_dataset",
        "scripts.settlement_datasets.profile_dataset",
        "scripts.settlement_datasets.label_dataset",
        "scripts.settlement_datasets.export_ledger",
        "scripts.settlement_datasets.mine_policies",
        "scripts.settlement_datasets.evaluate_policies_shadow",
        "scripts.settlement_datasets.replay_policy_evals",
        "scripts.settlement_datasets.update_policy_status",
        "scripts.settlement_datasets.update_metabolization_status",
        "scripts.settlement_datasets.mine_metabolization_candidates",
        "scripts.settlement_datasets.replay_live_shadow_from_traces",
    ]

    for module_name in modules:
        completed = subprocess.run(
            [sys.executable, "-m", module_name, "--help"],
            check=True,
            capture_output=True,
            text=True,
            cwd=ROOT,
        )
        stdout = completed.stdout
        assert "--run-id" in stdout
        assert "--run-dir" in stdout
        assert "--input-run-dir" in stdout
        assert "--output-run-dir" in stdout


def test_pipeline_dry_run_keeps_policy_activation_off(tmp_path: Path):
    result = run_evidence_pipeline(
        run_id="safety-run",
        dataset="agenttrove",
        limit=5,
        min_confidence=0.65,
        output_run_dir=tmp_path / "safety-run",
        dry_run=True,
    )

    summary = json.loads(result["summary_json"].read_text(encoding="utf-8"))
    manifest = json.loads(result["manifest"].read_text(encoding="utf-8"))

    assert summary["policy_activation_count"] == 0
    assert summary["metabolization_candidate_status_counts"].get("metabolized", 0) == 0
    assert manifest["artifact_counts"]["policy_fires"] == 0


def test_pipeline_targeted_execution_writes_target_match_counts(tmp_path: Path):
    input_path = ROOT / "tests" / "fixtures" / "settlement_datasets" / "agenttrove" / "sample.jsonl"

    result = run_evidence_pipeline(
        run_id="targeted-run",
        dataset="agenttrove",
        limit=5,
        min_confidence=0.65,
        input_path=str(input_path),
        output_run_dir=tmp_path / "targeted-run",
        target_profile="reflection_second_unresolved_error",
        include_live_shadow=True,
    )

    summary = json.loads(result["summary_json"].read_text(encoding="utf-8"))

    assert "target_profile_match_counts" in summary
    assert summary["policy_activation_count"] == 0
    assert summary["metabolization_candidate_status_counts"].get("metabolized", 0) == 0
    assert summary["target_profile_match_counts"]["sampled_count"] == 5
    assert summary["target_profile_match_counts"]["matched_count"] <= 5


def test_target_query_config_is_valid_yaml():
    config_path = ROOT / "configs" / "settlement_datasets" / "targeted_trace_queries.yaml"
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    assert "reflection_second_unresolved_error" in data
    assert data["reflection_second_unresolved_error"]["dataset"] == "agenttrove"
