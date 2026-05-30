import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SKILLS = [
    "horizon-review",
    "affordance-accounting",
    "settlement-evaluation",
    "metabolization-review",
    "positive-disintegration",
    "absorption-review",
    "framework-reconstruction",
]
AGENTS = ["navigator", "evaluator", "metabolizer", "absorber", "disintegrator"]


def test_skill_descriptions_include_trigger_context_and_task_purpose():
    for skill in SKILLS:
        text = (ROOT / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
        frontmatter = yaml.safe_load(text.split("---", 2)[1])
        description = frontmatter["description"].lower()
        assert "use this skill when" in description
        assert any(term in description for term in ["horizon", "payment", "settlement", "substrate", "absorb"])


def test_skill_bodies_include_operational_sections():
    required_sections = [
        "## Overview",
        "## When To Use",
        "## Inputs",
        "## Workflow",
        "## Output",
        "## Common Failure Modes",
    ]

    for skill in SKILLS:
        text = (ROOT / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
        for section in required_sections:
            assert section in text, f"{skill} is missing {section}"


def test_each_skill_has_reference_and_script_material():
    for skill in SKILLS:
        skill_root = ROOT / "skills" / skill
        assert list((skill_root / "references").glob("*.md"))
        assert list((skill_root / "scripts").glob("*.py"))


def test_agent_role_files_exist_with_role_contracts():
    for agent in AGENTS:
        text = (ROOT / "agents" / f"{agent}.md").read_text(encoding="utf-8")
        assert f"# {agent.title()}" in text
        assert "## Role" in text
        assert "## Output" in text


def test_evaluator_agent_includes_enterprise_settlement_contract():
    text = (ROOT / "agents" / "evaluator.md").read_text(encoding="utf-8")

    assert "## Inputs" in text
    assert "## Workflow" in text
    assert "## Failure Modes" in text
    assert "before_state" in text
    assert "after_state" in text
    assert "evidence" in text


def test_skill_evals_include_trigger_and_non_trigger_cases():
    evals = json.loads((ROOT / "evals" / "evals.json").read_text(encoding="utf-8"))

    for skill in SKILLS:
        cases = [case for case in evals["cases"] if case["skill"] == skill]
        assert any(case["should_trigger"] is True for case in cases)
        assert any(case["should_trigger"] is False for case in cases)


def test_readme_documents_implementation_defined_behavior_and_local_first_boundary():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "Implementation-defined" in readme
    assert "No external API calls by default" in readme
    assert "outcome completion is not terminal" in readme.lower()
    assert "## Self-Critique" in readme


def test_understanding_doc_distinguishes_verified_and_remaining_gaps():
    text = (
        ROOT / "docs" / "understanding" / "2026-05-29-cognitive-operating-systems.md"
    ).read_text(encoding="utf-8")

    assert "## Verified Gap Status" in text
    assert "Mostly resolved" in text
    assert "Still a gap" in text or "still a gap" in text


def test_understanding_doc_explicitly_bridges_current_harness_to_target_state_spec():
    text = (
        ROOT / "docs" / "understanding" / "2026-05-29-cognitive-operating-systems.md"
    ).read_text(encoding="utf-8")

    assert "current harness substrate" in text.lower()
    assert "target-state cognitive operating system spec" in text.lower()
    assert "representational state" in text.lower()
    assert "representational transition" in text.lower()
    assert "developmental memory" in text.lower()
    assert "self-critique" in text.lower()


def test_operator_reference_docs_exist_and_use_normalized_directory():
    reference_dir = ROOT / "docs" / "references"
    odd_reference_dir = ROOT / "docs" / "references "

    assert reference_dir.exists()
    assert not odd_reference_dir.exists()

    required_docs = {
        "ledger-reference.md": ["LedgerStore", "append_event", "read_events"],
        "schema-index.md": ["schemas/", "desired_direction.schema.json", "settlement.schema.json"],
        "cli-reference.md": ["start-direction", "developmental-report", "predictive-extensions"],
        "policy-reference.md": ["HARNESS.md", "block_unaffordable_actions", "require_human_review_for_absorption"],
        "report-interpretation.md": ["partial", "unaffordable", "circular_motion"],
        "runtime-workflow-example.md": ["start-direction", "review-horizon", "record-settlement"],
    }

    for filename, terms in required_docs.items():
        text = (reference_dir / filename).read_text(encoding="utf-8")
        for term in terms:
            assert term in text


def test_runtime_workflow_doc_distinguishes_visible_destinations_from_spendable_paths():
    text = (ROOT / "docs" / "references" / "runtime-workflow-example.md").read_text(encoding="utf-8")

    assert "visible destination" in text.lower()
    assert "spendable path" in text.lower()
    assert "transition sequence" in text.lower()


def test_report_interpretation_doc_covers_capability_lifecycle_and_identity_state():
    text = (ROOT / "docs" / "references" / "report-interpretation.md").read_text(encoding="utf-8")

    for term in ["latent", "active", "repeated", "metabolized", "brittle", "retired", "identity state"]:
        assert term in text.lower()


def test_policy_and_evaluator_docs_cover_self_critique_and_simulation_limits():
    policy = (ROOT / "docs" / "references" / "policy-reference.md").read_text(encoding="utf-8")
    evaluator = (ROOT / "agents" / "evaluator.md").read_text(encoding="utf-8")

    assert "self-critique" in policy.lower()
    assert "simulation is not settlement" in policy.lower() or "simulation is not capability evidence" in policy.lower()
    assert "intent-only" in evaluator.lower()
    assert "simulation" in evaluator.lower()


def test_absorber_and_disintegrator_docs_describe_review_artifacts():
    absorber = (ROOT / "agents" / "absorber.md").read_text(encoding="utf-8")
    disintegrator = (ROOT / "agents" / "disintegrator.md").read_text(encoding="utf-8")
    configuration = (ROOT / "docs" / "runbooks" / "configuration.md").read_text(encoding="utf-8")

    assert "human review" in absorber.lower()
    assert "settlement plan" in absorber.lower()
    assert "salvage" in disintegrator.lower()
    assert "positive disintegration" in configuration.lower()
