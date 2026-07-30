import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_SKILLS = [
    "horizon-review",
    "affordance-accounting",
    "settlement-evaluation",
    "metabolization-review",
    "positive-disintegration",
    "absorption-review",
    "framework-reconstruction",
]


def _skill_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path} must start with YAML frontmatter"
    _, frontmatter, body = text.split("---", 2)
    data = yaml.safe_load(frontmatter)
    assert isinstance(data, dict), f"{path} frontmatter must be a map"
    assert body.strip(), f"{path} must include markdown instructions"
    return data


def test_plugin_manifest_has_required_identity_metadata():
    manifest_path = ROOT / ".claude-plugin" / "plugin.json"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["name"] == "godspeed-agent-harness"
    assert "horizon-centric" in manifest["description"].lower()
    assert manifest["version"]
    assert manifest["author"]["name"] == "Godspeed AI"


def test_required_skills_live_at_plugin_root_with_descriptions():
    for skill_name in REQUIRED_SKILLS:
        skill_path = ROOT / "skills" / skill_name / "SKILL.md"

        frontmatter = _skill_frontmatter(skill_path)

        description = frontmatter.get("description", "")
        assert "use" in description.lower()
        assert len(description) >= 80


def test_plugin_components_are_not_nested_inside_manifest_directory():
    plugin_dir = ROOT / ".claude-plugin"

    forbidden = [
        "skills",
        "agents",
        "hooks",
        "monitors",
        "bin",
        "settings.json",
        ".mcp.json",
    ]

    for name in forbidden:
        assert not (plugin_dir / name).exists()


def test_plugin_has_no_host_hook_registration():
    """SWE_SEED owns software hooks; GodSpeed-Agent registers none."""
    assert not (ROOT / "hooks").exists(), "hooks/ directory must not exist"


def test_runtime_trace_capture_module_is_absent():
    """Live trace capture lives in SWE_SEED; the runtime recorder is removed."""
    assert not (ROOT / "godspeed_nav" / "trace_capture.py").exists()
    import importlib

    with __import__("pytest").raises(ModuleNotFoundError):
        importlib.import_module("godspeed_nav.trace_capture")
