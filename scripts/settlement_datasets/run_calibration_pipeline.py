"""Calibration pipeline orchestrator.

Streams external agent trajectory datasets, normalises them into proxy
settlement records, and stops once the configured usable-settlement
target is reached.  All records are classified as
``external-proxy-settlement``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from scripts.settlement_datasets.run_scoped_paths import (
    RunScope,
    ensure_run_surface,
    utc_now_iso,
    write_run_manifest,
)


# ---------------------------------------------------------------------------
# Run state
# ---------------------------------------------------------------------------


@dataclass
class CalibrationRunState:
    """Mutable accumulator for a single calibration run."""

    target_usable_settlements: int
    min_confidence: float = 0.65
    scanned: int = 0
    normalized: int = 0
    usable_settlements: int = 0
    rejected: int = 0
    adapter_errors: int = 0
    dataset_counts: dict[str, dict[str, int]] = field(default_factory=dict)
    success_count: int = 0
    failure_count: int = 0


# ---------------------------------------------------------------------------
# Manifest loading
# ---------------------------------------------------------------------------


def load_calibration_manifest(path: str | Path) -> dict[str, Any]:
    """Load and validate a calibration source manifest.

    Datasets are sorted by ``priority`` (ascending).
    """
    with Path(path).open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    required_keys = {
        "target_usable_settlements",
        "settlement_classification",
        "datasets",
    }
    missing = required_keys - set(data.keys())
    if missing:
        raise ValueError(f"Manifest missing required keys: {missing}")

    datasets = data.get("datasets", [])
    for ds in datasets:
        for key in ("name", "source_uri", "adapter", "split", "max_rows", "priority"):
            if key not in ds:
                raise ValueError(f"Dataset entry missing required key: {key}")

    data["datasets"] = sorted(datasets, key=lambda d: d["priority"])
    return data


# ---------------------------------------------------------------------------
# Stop conditions
# ---------------------------------------------------------------------------


def should_stop_for_target(state: CalibrationRunState) -> bool:
    """Return True when the usable-settlement target has been reached."""
    return state.usable_settlements >= state.target_usable_settlements


# ---------------------------------------------------------------------------
# Pipeline runner (skeleton — full processing in Task 6)
# ---------------------------------------------------------------------------


def run_pipeline(
    *,
    manifest_path: str | Path,
    run_id: str,
    output_run_dir: str | Path | None = None,
    target_usable_settlements: int = 500,
    min_confidence: float = 0.65,
    provider: str = "disabled",
    dry_run: bool = False,
    report_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Execute the calibration pipeline from manifest to summary.

    Returns a summary dict with counts and artifact paths.
    """
    manifest = load_calibration_manifest(manifest_path)

    scope = ensure_run_surface(
        run_id=run_id,
        output_run_dir=output_run_dir,
    )

    state = CalibrationRunState(
        target_usable_settlements=target_usable_settlements,
        min_confidence=min_confidence,
    )

    write_run_manifest(
        scope,
        {
            "run_id": run_id,
            "manifest_path": str(manifest_path),
            "created_at": utc_now_iso(),
            "target_usable_settlements": target_usable_settlements,
            "min_confidence": min_confidence,
            "provider": provider,
            "dry_run": dry_run,
        },
    )

    summary = {
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "manifest_path": str(manifest_path),
        "target_usable_settlements": target_usable_settlements,
        "min_confidence": min_confidence,
        "provider": provider,
        "scanned": state.scanned,
        "normalized": state.normalized,
        "usable_settlements": state.usable_settlements,
        "rejected": state.rejected,
        "adapter_errors": state.adapter_errors,
        "dataset_counts": state.dataset_counts,
        "success_count": state.success_count,
        "failure_count": state.failure_count,
    }

    summary_path = scope.root / "summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    return summary
