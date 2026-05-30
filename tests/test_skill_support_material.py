import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REFERENCE_FILES = [
    ROOT / "skills" / "horizon-review" / "references" / "glossary.md",
    ROOT
    / "skills"
    / "affordance-accounting"
    / "references"
    / "payment-and-settlement.md",
    ROOT / "skills" / "settlement-evaluation" / "references" / "settlement-evidence.md",
    ROOT / "skills" / "metabolization-review" / "references" / "metabolization.md",
    ROOT / "skills" / "positive-disintegration" / "references" / "disintegration.md",
    ROOT / "skills" / "absorption-review" / "references" / "absorption.md",
    ROOT
    / "skills"
    / "framework-reconstruction"
    / "references"
    / "framework-invariants.md",
]


def run_script(script_path: Path, payload: dict) -> dict:
    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=ROOT,
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(result.stdout)


def test_reference_docs_include_enterprise_decision_sections():
    required_sections = [
        "## Purpose",
        "## Decision Rules",
        "## Enterprise Notes",
        "## Failure Modes",
    ]

    for reference_path in REFERENCE_FILES:
        text = reference_path.read_text(encoding="utf-8")
        for section in required_sections:
            assert section in text, f"{reference_path.name} is missing {section}"


def test_horizon_review_script_outputs_ranked_affordances(tmp_path: Path):
    output = run_script(
        ROOT / "skills" / "horizon-review" / "scripts" / "horizon_review.py",
        {
            "candidates": [
                {
                    "id": "aff-1",
                    "statement": "Take the next affordable step",
                    "pathway": "local implementation",
                    "costs": {"time": 1},
                    "capacities": {"time": 5},
                    "expected_horizon_delta": 3,
                    "risk": 0,
                },
                {
                    "id": "pot-1",
                    "statement": "Imaginary platform leap",
                    "pathway": "",
                    "costs": {"time": 10},
                    "capacities": {"time": 1},
                    "expected_horizon_delta": 10,
                    "risk": 4,
                },
            ]
        },
    )

    assert output["next_affordance"]["id"] == "aff-1"
    assert output["rejected_candidates"][0]["reason"] == "missing_pathway"


def test_affordance_accounting_script_outputs_candidate_status():
    output = run_script(
        ROOT / "skills" / "affordance-accounting" / "scripts" / "compute_affordance.py",
        {
            "candidate": {
                "id": "aff-1",
                "pathway": "local step",
                "costs": {"time": 2, "risk": 1},
                "capacities": {"time": 5, "risk": 5},
                "expected_horizon_delta": 3,
                "risk": 1,
            }
        },
    )

    assert output["candidate_status"] == "affordance"
    assert output["payment"]["spendability"] == "affordable"


def test_settlement_script_reports_missing_observable_change():
    output = run_script(
        ROOT / "skills" / "settlement-evaluation" / "scripts" / "settlement.py",
        {
            "before_state": {"tests": 1},
            "after_state": {"tests": 1},
            "desired_direction": {"statement": "Improve tests"},
            "payment_actual": {"time": 1},
            "evidence": ["command ran"],
        },
    )

    assert output["status"] == "failed"
    assert output["missing_evidence"] == ["observable_change"]


def test_metabolization_script_returns_review_summary():
    output = run_script(
        ROOT / "skills" / "metabolization-review" / "scripts" / "metabolization.py",
        {
            "capability_id": "cap-1",
            "settlement_events": [{"id": "s1"}, {"id": "s2"}, {"id": "s3"}],
            "reuse_frequency": 3,
            "context_diversity": 1,
            "stability": 0.8,
            "maintenance_burden": 0.2,
            "attention_burden": 0.2,
        },
    )

    assert output["status_recommendation"] == "not_metabolized"
    assert "context_diversity" in output["missing_evidence"]


def test_positive_disintegration_script_returns_actionable_split():
    output = run_script(
        ROOT / "skills" / "positive-disintegration" / "scripts" / "disintegrate.py",
        {
            "structures": [
                {"id": "old-flow", "settlement_score": 0.1, "risk": "low"},
                {
                    "id": "good-flow",
                    "settlement_score": 0.95,
                    "attention_burden": 0.1,
                    "repetitions": 4,
                },
            ]
        },
    )

    assert output["dissolution_candidates"][0]["id"] == "old-flow"
    assert output["metabolization_candidates"][0]["id"] == "good-flow"


def test_absorption_script_reports_blockers_and_plan():
    output = run_script(
        ROOT / "skills" / "absorption-review" / "scripts" / "absorb.py",
        {
            "root_project_state": {"capabilities": ["python"]},
            "external_project_state": {"capabilities": ["mcp"]},
            "desired_direction": {"statement": "Absorb MCP support"},
            "capability_delta": ["mcp"],
            "license_summary": {"compatible": True},
            "pathway": "implement local wrapper",
        },
    )

    assert output["absorbability_status"] == "absorbable"
    assert output["proposed_worktree_plan"]["enabled"] is True


def test_framework_reconstruction_script_outputs_reconstruction_packet():
    output = run_script(
        ROOT / "skills" / "framework-reconstruction" / "scripts" / "reconstruct.py",
        {
            "failed_doctrine": "Treat outcomes as terminal completion.",
            "evidence": [
                "Desired directions stopped generating new affordances after closure."
            ],
            "preserve_invariants": ["settlement over intent", "horizon over arrival"],
        },
    )

    assert "Reconstruct this doctrine" in output["reconstruction_prompt"]
    assert output["preserved_invariants"][0] == "settlement over intent"
