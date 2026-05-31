from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


RUNS_ROOT = Path("data/settlement_datasets/runs")
TARGET_PROFILE_CONFIG = Path("configs/settlement_datasets/targeted_trace_queries.yaml")
STAGE_DIRS = {
    "raw": "raw",
    "normalized": "normalized",
    "profiles": "profiles",
    "settlements": "settlements",
    "ledger": "ledger",
    "policies": "policies",
    "shadow": "shadow",
    "replay": "replay",
    "adjudication": "adjudication",
    "metabolization": "metabolization",
    "summaries": "summaries",
}


@dataclass(frozen=True)
class RunScope:
    run_id: str
    root: Path
    input_root: Path

    @property
    def raw_dir(self) -> Path:
        return self.root / STAGE_DIRS["raw"]

    @property
    def normalized_dir(self) -> Path:
        return self.root / STAGE_DIRS["normalized"]

    @property
    def profiles_dir(self) -> Path:
        return self.root / STAGE_DIRS["profiles"]

    @property
    def settlements_dir(self) -> Path:
        return self.root / STAGE_DIRS["settlements"]

    @property
    def ledger_dir(self) -> Path:
        return self.root / STAGE_DIRS["ledger"]

    @property
    def policies_dir(self) -> Path:
        return self.root / STAGE_DIRS["policies"]

    @property
    def shadow_dir(self) -> Path:
        return self.root / STAGE_DIRS["shadow"]

    @property
    def replay_dir(self) -> Path:
        return self.root / STAGE_DIRS["replay"]

    @property
    def adjudication_dir(self) -> Path:
        return self.root / STAGE_DIRS["adjudication"]

    @property
    def metabolization_dir(self) -> Path:
        return self.root / STAGE_DIRS["metabolization"]

    @property
    def summaries_dir(self) -> Path:
        return self.root / STAGE_DIRS["summaries"]

    def stage_dir(self, stage: str, *, input_surface: bool = False) -> Path:
        base = self.input_root if input_surface else self.root
        return base / STAGE_DIRS[stage]

    def dataset_jsonl_path(
        self,
        stage: str,
        dataset: str,
        *,
        input_surface: bool = False,
    ) -> Path:
        return self.stage_dir(stage, input_surface=input_surface) / f"{dataset}.jsonl"

    def profile_path(self, dataset: str, *, input_surface: bool = False) -> Path:
        return self.stage_dir("profiles", input_surface=input_surface) / f"{dataset}_profile.json"

    def named_path(
        self,
        stage: str,
        filename: str,
        *,
        input_surface: bool = False,
    ) -> Path:
        return self.stage_dir(stage, input_surface=input_surface) / filename


def add_run_scope_arguments(
    parser: argparse.ArgumentParser,
    *,
    include_target_profile: bool = False,
) -> argparse.ArgumentParser:
    parser.add_argument("--run-id", default=None, help="Run id for a run-scoped evidence surface")
    parser.add_argument("--run-dir", default=None, help="Run directory to use for both input and output")
    parser.add_argument("--input-run-dir", default=None, help="Existing run directory to consume as input")
    parser.add_argument("--output-run-dir", default=None, help="Run directory to write as output")
    if include_target_profile:
        parser.add_argument(
            "--target-profile",
            default=None,
            help="Named targeted trace query profile for this run",
        )
        parser.add_argument(
            "--target-profile-config",
            default=str(TARGET_PROFILE_CONFIG),
            help="Targeted trace query config file",
        )
    return parser


def resolve_run_scope(
    *,
    run_id: str | None = None,
    run_dir: str | Path | None = None,
    input_run_dir: str | Path | None = None,
    output_run_dir: str | Path | None = None,
) -> RunScope:
    if run_dir is not None:
        root = Path(run_dir)
        input_root = root
    else:
        root = Path(output_run_dir) if output_run_dir is not None else RUNS_ROOT / (run_id or "default-run")
        input_root = Path(input_run_dir) if input_run_dir is not None else root

    resolved_run_id = root.name if output_run_dir is not None or run_dir is not None else (run_id or root.name)
    return RunScope(run_id=resolved_run_id, root=root, input_root=input_root)


def ensure_run_surface(
    *,
    run_id: str | None = None,
    run_dir: str | Path | None = None,
    input_run_dir: str | Path | None = None,
    output_run_dir: str | Path | None = None,
) -> RunScope:
    scope = resolve_run_scope(
        run_id=run_id,
        run_dir=run_dir,
        input_run_dir=input_run_dir,
        output_run_dir=output_run_dir,
    )
    scope.root.mkdir(parents=True, exist_ok=True)
    for stage in STAGE_DIRS:
        scope.stage_dir(stage).mkdir(parents=True, exist_ok=True)
    return scope


def load_target_profile(
    profile_name: str,
    config_path: str | Path = TARGET_PROFILE_CONFIG,
) -> dict[str, Any]:
    with Path(config_path).open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}
    if profile_name not in config:
        raise KeyError(f"Unknown target profile: {profile_name}")
    return config[profile_name]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_run_manifest(scope: RunScope, manifest: dict[str, Any]) -> Path:
    path = scope.root / "run_manifest.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return path


def write_summary_files(scope: RunScope, summary: dict[str, Any]) -> dict[str, Path]:
    summary_json = scope.summaries_dir / "summary.json"
    summary_md = scope.summaries_dir / "summary.md"
    root_summary_json = scope.root / "summary.json"
    root_summary_md = scope.root / "summary.md"
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    root_summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    md_lines = [
        f"# Run Summary: {scope.run_id}",
        "",
        f"- Created at: {summary.get('created_at', '')}",
        f"- Dataset: {summary.get('dataset', '')}",
        f"- Min confidence: {summary.get('min_confidence', 0.0)}",
        f"- Policy activation count: {summary.get('policy_activation_count', 0)}",
        "",
        "## Trace Counts",
        "",
    ]
    for key, value in summary.get("trace_counts", {}).items():
        md_lines.append(f"- {key}: {value}")
    md_lines.extend(["", "## Policy Fires", ""])
    for key, value in summary.get("policy_fire_counts", {}).items():
        md_lines.append(f"- {key}: {value}")
    md_lines.extend(["", "## Recommended Next Move", "", summary.get("recommended_next_move", "No recommendation recorded.")])
    rendered = "\n".join(md_lines) + "\n"
    summary_md.write_text(rendered, encoding="utf-8")
    root_summary_md.write_text(rendered, encoding="utf-8")
    return {"summary_json": summary_json, "summary_md": summary_md}
