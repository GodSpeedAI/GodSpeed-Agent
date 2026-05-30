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
