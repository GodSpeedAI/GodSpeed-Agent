"""Tests for the Adjusted-Format Real Agent Pilot Expansion (reflection-real-agent-002).

Validates:
- Adjusted checkpoint text is used (not original questions-only)
- Pilot artifacts are produced correctly
- No global activation
- No metabolization
- Pilot summary generation
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from scripts.settlement_datasets.guarded_activation import REFINED_POLICY_ID

# The adjusted checkpoint text used in pilot-002
ADJUSTED_CHECKPOINT = (
    "Repeated unresolved errors detected. Before continuing, briefly consider:\n"
    "1. What failed?\n"
    "2. What assumption may be wrong?\n"
    "3. What lower-payment action should happen next?\n"
    "4. What evidence would show the next step worked?\n"
    "\n"
    "Now continue fixing the code. Implement your fix and re-run the tests."
)

# The original questions-only checkpoint (must NOT be used in pilot-002)
ORIGINAL_CHECKPOINT = (
    "Repeated unresolved errors detected.\n\n"
    "Before continuing, revise the plan using the latest settlement feedback:\n\n"
    "1. What failed?\n"
    "2. What assumption may be wrong?\n"
    "3. What lower-payment action should happen next?\n"
    "4. What evidence would show the next step worked?"
)

PILOT_002_DIR = Path(
    "data/settlement_datasets/real_agent_pilot/reflection-real-agent-002"
)


def test_adjusted_checkpoint_has_continuation_directive():
    """The adjusted checkpoint must include a continuation directive."""
    assert "Now continue" in ADJUSTED_CHECKPOINT
    assert "Implement your fix" in ADJUSTED_CHECKPOINT


def test_adjusted_checkpoint_preserves_reflection_questions():
    """The adjusted checkpoint must still include all 4 reflection questions."""
    assert "What failed?" in ADJUSTED_CHECKPOINT
    assert "What assumption may be wrong?" in ADJUSTED_CHECKPOINT
    assert "What lower-payment action" in ADJUSTED_CHECKPOINT
    assert "What evidence would show" in ADJUSTED_CHECKPOINT


def test_original_checkpoint_lacks_continuation_directive():
    """The original checkpoint must NOT have the continuation directive."""
    assert "Now continue" not in ORIGINAL_CHECKPOINT
    assert "Implement your fix" not in ORIGINAL_CHECKPOINT


def test_adjusted_differs_from_original():
    """Adjusted and original checkpoints must be different texts."""
    assert ADJUSTED_CHECKPOINT != ORIGINAL_CHECKPOINT


def test_pilot_002_dir_exists():
    """The pilot-002 artifact directory must exist."""
    assert PILOT_002_DIR.is_dir(), f"Pilot-002 directory not found: {PILOT_002_DIR}"


def test_pilot_002_uses_refined_policy_id():
    """Pilot-002 must test the refined policy, not the original."""
    assert REFINED_POLICY_ID == (
        "require_reflection_before_continuing_after_second_unresolved_error"
    )


def test_no_global_activation_in_pilot_config():
    """Pilot-002 must not enable global activation."""
    from scripts.settlement_datasets.guarded_activation import config_from_env

    config = config_from_env({})
    assert config.activation_enabled is False
    assert config.mode == "shadow"


def test_no_metabolization_allowed():
    """Pilot-002 must not claim metabolization."""
    # This is a contract test — the pilot summary must set metabolized=False
    # The actual check runs against the pilot_summary.json after completion
    pass  # validated in test_pilot_summary_no_metabolization


def test_pilot_summary_schema():
    """Validate pilot summary has required fields."""
    summary_path = PILOT_002_DIR / "pilot_summary.json"
    if not summary_path.exists():
        # Pilot hasn't run yet — skip
        return

    with open(summary_path) as f:
        summary = json.load(f)

    required_fields = {
        "pilot_id",
        "policy_id",
        "total_runs",
        "baseline_runs",
        "guarded_runs",
        "status_recommendation",
        "metabolized",
        "globally_active",
    }
    missing = required_fields - set(summary.keys())
    assert not missing, f"Missing fields in pilot_summary: {missing}"


def test_pilot_summary_no_metabolization():
    """Pilot summary must not claim metabolization."""
    summary_path = PILOT_002_DIR / "pilot_summary.json"
    if not summary_path.exists():
        return

    with open(summary_path) as f:
        summary = json.load(f)

    assert summary.get("metabolized") is False, "Metabolization not allowed from pilot"
    assert summary.get("globally_active") is False, (
        "Global activation not allowed from pilot"
    )


def test_pilot_summary_allowed_status():
    """Pilot summary status must be from the allowed set."""
    summary_path = PILOT_002_DIR / "pilot_summary.json"
    if not summary_path.exists():
        return

    with open(summary_path) as f:
        summary = json.load(f)

    allowed = {"needs_more_evidence", "candidate_for_activation", "refine", "reject"}
    forbidden = {"globally_active", "metabolized"}
    status = summary.get("status_recommendation", "")
    assert status in allowed, f"Status '{status}' not in allowed set {allowed}"
    assert status not in forbidden, f"Forbidden status: {status}"


def test_intervention_records_use_adjusted_format():
    """All intervention records in pilot-002 must use the adjusted format."""
    interventions_path = PILOT_002_DIR / "interventions.jsonl"
    if not interventions_path.exists():
        return

    with open(interventions_path) as f:
        for line in f:
            if not line.strip():
                continue
            record = json.loads(line)
            text = record.get("intervention_text", "")
            # Must have continuation directive
            assert "Now continue" in text or "adjusted" in text.lower(), (
                f"Intervention in run {record.get('run_id')} does not use adjusted format: {text[:100]}"
            )
            # Must NOT be the original questions-only format
            if text == ORIGINAL_CHECKPOINT:
                raise AssertionError(
                    f"Run {record.get('run_id')} uses original format, not adjusted"
                )


def test_run_summaries_have_condition_field():
    """Run summaries must record baseline/guarded condition."""
    summaries_path = PILOT_002_DIR / "run_summaries.jsonl"
    if not summaries_path.exists():
        return

    with open(summaries_path) as f:
        for line in f:
            if not line.strip():
                continue
            record = json.loads(line)
            assert "condition" in record, (
                f"Missing condition in run summary: {record.get('run_id')}"
            )
            assert record["condition"] in ("baseline", "guarded")


def test_task_traps_fire():
    """Verify all 5 task traps produce test failures."""
    import subprocess
    import sys

    tasks = {
        "task_d": "test_inventory.py",
        "task_e": "test_csv_parser.py",
        "task_f": "test_build.py",
        "task_g": "test_config.py",
        "task_h": "test_http_client.py",
    }

    for task_dir, test_file in tasks.items():
        task_path = Path("tmp/pilot_tasks") / task_dir
        if not task_path.is_dir():
            continue
        result = subprocess.run(
            [sys.executable, test_file],
            capture_output=True,
            text=True,
            cwd=str(task_path),
            timeout=30,
        )
        assert result.returncode != 0, (
            f"{task_dir}/{test_file} should fail (trap not set). Output: {result.stdout}{result.stderr}"
        )
