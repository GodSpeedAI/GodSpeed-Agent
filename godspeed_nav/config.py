from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

SUPPORTED_STORAGE_FORMATS = {"jsonl", "sqlite", "duckdb", "parquet"}


class ConfigError(ValueError):
    """Typed configuration error surfaced to operators and gates."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class HarnessSettings:
    mode: str = "local"
    primary_metric: str = "horizon_expansion"
    allow_outcome_language: bool = True
    outcome_as_terminal: bool = False


@dataclass(frozen=True)
class StorageSettings:
    root: Path
    format: str = "jsonl"
    retain_raw_events: bool = True
    redact_secrets: bool = True


@dataclass(frozen=True)
class ComputationSettings:
    engine: str = "python"
    use_pandas: bool = True
    use_numpy: bool = True
    use_sklearn: bool | str = "auto"
    model_provider: str = "heuristic"
    ml_event_threshold: int = 200
    simulation_threshold: int = 1000


@dataclass(frozen=True)
class ExperimentSettings:
    enabled: bool = True
    root: Path | None = None
    use_git_worktrees: bool = True
    max_parallel_experiments: int = 1
    cleanup_failed_experiments: bool = False


@dataclass(frozen=True)
class AbsorptionSettings:
    enabled: bool = True
    ingest_root: Path | None = None
    require_license_check: bool = True
    require_pathway: bool = True
    require_settlement_plan: bool = True


@dataclass(frozen=True)
class SafetySettings:
    block_unaffordable_actions: bool = False
    warn_unaffordable_actions: bool = True
    max_payment_burden: float = 100.0
    require_human_review_for_absorption: bool = True
    require_human_review_for_disintegration: bool = True


@dataclass(frozen=True)
class HarnessConfig:
    workspace_root: Path
    harness: HarnessSettings
    storage: StorageSettings
    computation: ComputationSettings
    experiments: ExperimentSettings
    absorption: AbsorptionSettings
    safety: SafetySettings
    policy_body: str = ""


def load_config(
    workspace_root: str | Path, explicit_path: str | Path | None = None
) -> HarnessConfig:
    root = Path(workspace_root).resolve()
    config_path = (
        Path(explicit_path).resolve() if explicit_path else root / "HARNESS.md"
    )
    frontmatter: dict[str, Any] = {}
    body = ""

    if config_path.exists():
        frontmatter, body = _read_harness_file(config_path)

    storage_data = _section(frontmatter, "storage")
    storage_root = _resolve_workspace_path(
        root, storage_data.get("root", ".godspeed-harness")
    )
    storage_format = storage_data.get("format", "jsonl")
    if storage_format not in SUPPORTED_STORAGE_FORMATS:
        raise ConfigError(
            "unsupported_storage_format",
            f"Unsupported storage format: {storage_format}",
        )

    harness_data = _section(frontmatter, "harness")
    primary_metric = harness_data.get("primary_metric", "horizon_expansion")
    if primary_metric == "goal_completion":
        raise ConfigError(
            "invalid_primary_metric",
            "primary_metric MUST NOT default to goal_completion",
        )

    experiments_data = _section(frontmatter, "experiments")
    experiments_root = _resolve_workspace_path(
        root,
        experiments_data.get("root", ".godspeed-harness/experiments"),
    )

    absorption_data = _section(frontmatter, "absorption")
    ingest_root = _resolve_workspace_path(
        root, absorption_data.get("ingest_root", "ingest/")
    )

    computation_data = _section(frontmatter, "computation")
    safety_data = _section(frontmatter, "safety")

    return HarnessConfig(
        workspace_root=root,
        harness=HarnessSettings(
            mode=harness_data.get("mode", "local"),
            primary_metric=primary_metric,
            allow_outcome_language=bool(
                harness_data.get("allow_outcome_language", True)
            ),
            outcome_as_terminal=bool(harness_data.get("outcome_as_terminal", False)),
        ),
        storage=StorageSettings(
            root=storage_root,
            format=storage_format,
            retain_raw_events=bool(storage_data.get("retain_raw_events", True)),
            redact_secrets=bool(storage_data.get("redact_secrets", True)),
        ),
        computation=ComputationSettings(
            engine=computation_data.get("engine", "python"),
            use_pandas=bool(computation_data.get("use_pandas", True)),
            use_numpy=bool(computation_data.get("use_numpy", True)),
            use_sklearn=computation_data.get("use_sklearn", "auto"),
            model_provider=str(computation_data.get("model_provider", "heuristic")),
            ml_event_threshold=int(computation_data.get("ml_event_threshold", 200)),
            simulation_threshold=int(
                computation_data.get("simulation_threshold", 1000)
            ),
        ),
        experiments=ExperimentSettings(
            enabled=bool(experiments_data.get("enabled", True)),
            root=experiments_root,
            use_git_worktrees=bool(experiments_data.get("use_git_worktrees", True)),
            max_parallel_experiments=int(
                experiments_data.get("max_parallel_experiments", 1)
            ),
            cleanup_failed_experiments=bool(
                experiments_data.get("cleanup_failed_experiments", False)
            ),
        ),
        absorption=AbsorptionSettings(
            enabled=bool(absorption_data.get("enabled", True)),
            ingest_root=ingest_root,
            require_license_check=bool(
                absorption_data.get("require_license_check", True)
            ),
            require_pathway=bool(absorption_data.get("require_pathway", True)),
            require_settlement_plan=bool(
                absorption_data.get("require_settlement_plan", True)
            ),
        ),
        safety=SafetySettings(
            block_unaffordable_actions=bool(
                safety_data.get("block_unaffordable_actions", False)
            ),
            warn_unaffordable_actions=bool(
                safety_data.get("warn_unaffordable_actions", True)
            ),
            max_payment_burden=float(safety_data.get("max_payment_burden", 100.0)),
            require_human_review_for_absorption=bool(
                safety_data.get("require_human_review_for_absorption", True)
            ),
            require_human_review_for_disintegration=bool(
                safety_data.get("require_human_review_for_disintegration", True)
            ),
        ),
        policy_body=body.strip(),
    )


def _read_harness_file(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}, text

    try:
        _, raw_frontmatter, body = text.split("---", 2)
        parsed = yaml.safe_load(raw_frontmatter) if raw_frontmatter.strip() else {}
    except (ValueError, yaml.YAMLError) as exc:
        raise ConfigError(
            "harness_parse_error", f"Could not parse HARNESS.md frontmatter: {exc}"
        ) from exc

    if not isinstance(parsed, dict):
        raise ConfigError(
            "harness_front_matter_not_a_map",
            "HARNESS.md frontmatter must decode to a map",
        )

    return parsed, body


def _section(frontmatter: dict[str, Any], key: str) -> dict[str, Any]:
    value = frontmatter.get(key, {})
    return value if isinstance(value, dict) else {}


def _resolve_workspace_path(workspace_root: Path, value: str | Path) -> Path:
    raw = Path(value)
    if raw.is_absolute() or ".." in raw.parts:
        raise ConfigError(
            "invalid_storage_root", f"Path must remain inside workspace: {value}"
        )
    resolved = (workspace_root / raw).resolve()
    try:
        resolved.relative_to(workspace_root)
    except ValueError as exc:
        raise ConfigError(
            "invalid_storage_root", f"Path must remain inside workspace: {value}"
        ) from exc
    return resolved
