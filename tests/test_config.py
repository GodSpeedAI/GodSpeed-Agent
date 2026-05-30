from pathlib import Path

import pytest

from godspeed_nav.config import ConfigError, load_config


def test_missing_harness_file_uses_horizon_defaults(tmp_path: Path):
    config = load_config(tmp_path)

    assert config.harness.mode == "local"
    assert config.harness.primary_metric == "horizon_expansion"
    assert config.harness.allow_outcome_language is True
    assert config.harness.outcome_as_terminal is False
    assert config.storage.root == tmp_path / ".godspeed-harness"
    assert config.storage.format == "jsonl"
    assert config.storage.retain_raw_events is True
    assert config.storage.redact_secrets is True


def test_invalid_yaml_reports_typed_error(tmp_path: Path):
    (tmp_path / "HARNESS.md").write_text("---\nharness: [\n---\n", encoding="utf-8")

    with pytest.raises(ConfigError) as error:
        load_config(tmp_path)

    assert error.value.code == "harness_parse_error"


def test_frontmatter_must_be_a_map(tmp_path: Path):
    (tmp_path / "HARNESS.md").write_text("---\n- local\n---\nbody\n", encoding="utf-8")

    with pytest.raises(ConfigError) as error:
        load_config(tmp_path)

    assert error.value.code == "harness_front_matter_not_a_map"


def test_unknown_keys_are_ignored_and_markdown_body_is_preserved(tmp_path: Path):
    (tmp_path / "HARNESS.md").write_text(
        "---\n"
        "unknown: kept for future\n"
        "harness:\n"
        "  mode: workspace\n"
        "storage:\n"
        "  root: .local-ledgers\n"
        "---\n"
        "# Local Doctrine\n\nPrefer small settlement loops.\n",
        encoding="utf-8",
    )

    config = load_config(tmp_path)

    assert config.harness.mode == "workspace"
    assert config.storage.root == tmp_path / ".local-ledgers"
    assert "Prefer small settlement loops." in config.policy_body


def test_storage_root_path_traversal_is_rejected(tmp_path: Path):
    (tmp_path / "HARNESS.md").write_text(
        "---\nstorage:\n  root: ../outside\n---\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError) as error:
        load_config(tmp_path)

    assert error.value.code == "invalid_storage_root"


def test_goal_completion_cannot_be_default_primary_metric(tmp_path: Path):
    (tmp_path / "HARNESS.md").write_text(
        "---\nharness:\n  primary_metric: goal_completion\n---\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError) as error:
        load_config(tmp_path)

    assert error.value.code == "invalid_primary_metric"


def test_invalid_storage_format_is_rejected(tmp_path: Path):
    (tmp_path / "HARNESS.md").write_text(
        "---\nstorage:\n  format: xml\n---\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError) as error:
        load_config(tmp_path)

    assert error.value.code == "unsupported_storage_format"


def test_computation_settings_allow_provider_and_threshold_overrides(tmp_path: Path):
    (tmp_path / "HARNESS.md").write_text(
        "---\n"
        "computation:\n"
        "  model_provider: testing\n"
        "  ml_event_threshold: 250\n"
        "  simulation_threshold: 1250\n"
        "---\n",
        encoding="utf-8",
    )

    config = load_config(tmp_path)

    assert config.computation.model_provider == "testing"
    assert config.computation.ml_event_threshold == 250
    assert config.computation.simulation_threshold == 1250
