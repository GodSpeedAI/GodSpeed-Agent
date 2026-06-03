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

from scripts.settlement_datasets.adapter_base import write_records_jsonl
from scripts.settlement_datasets.hf_stream import iter_limited
from scripts.settlement_datasets.registry import get_adapter
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
# Record filtering
# ---------------------------------------------------------------------------


def _is_usable(record: dict[str, Any], min_confidence: float) -> bool:
    """A record is usable when it has a defined success label and sufficient confidence."""
    outcome = record.get("outcome", {})
    success = outcome.get("success")
    confidence = outcome.get("confidence", 0.0)
    return success is not None and confidence >= min_confidence


# ---------------------------------------------------------------------------
# Pipeline runner
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

    # Ensure output sub-directories exist
    raw_dir = scope.root / "raw"
    normalized_dir = scope.root / "normalized"
    settlements_dir = scope.root / "settlements"
    for d in (raw_dir, normalized_dir, settlements_dir):
        d.mkdir(parents=True, exist_ok=True)

    for source in manifest["datasets"]:
        if should_stop_for_target(state):
            break

        ds_name = source["name"]
        adapter_name = source["adapter"]
        max_rows = source.get("max_rows")

        ds_counts: dict[str, int] = {
            "scanned": 0,
            "normalized": 0,
            "usable": 0,
            "rejected": 0,
            "adapter_errors": 0,
        }

        try:
            adapter = get_adapter(adapter_name)
        except ValueError:
            state.adapter_errors += 1
            ds_counts["adapter_errors"] = 1
            state.dataset_counts[ds_name] = ds_counts
            continue

        raw_records: list[dict[str, Any]] = []
        normalized_records: list[dict[str, Any]] = []
        settlement_records: list[dict[str, Any]] = []

        # Build stream kwargs
        stream_kwargs: dict[str, Any] = {}
        if source.get("input_path"):
            stream_kwargs["input_path"] = source["input_path"]
        else:
            stream_kwargs["source_uri"] = source.get("source_uri", adapter.source_uri)
            stream_kwargs["split"] = source.get("split", "train")

        try:
            row_iter = adapter.stream(limit=max_rows, **stream_kwargs)
        except Exception:
            state.adapter_errors += 1
            ds_counts["adapter_errors"] = 1
            state.dataset_counts[ds_name] = ds_counts
            continue

        for raw in row_iter:
            if should_stop_for_target(state):
                break

            state.scanned += 1
            ds_counts["scanned"] += 1
            raw_records.append(raw)

            try:
                record = adapter.to_settlement_record(raw)
            except Exception:
                state.adapter_errors += 1
                ds_counts["adapter_errors"] += 1
                continue

            # Enforce external-proxy-settlement classification
            metadata = record.get("metadata", {})
            metadata["settlement_classification"] = "external-proxy-settlement"
            record["metadata"] = metadata

            state.normalized += 1
            ds_counts["normalized"] += 1
            normalized_records.append(record)

            if _is_usable(record, min_confidence):
                state.usable_settlements += 1
                ds_counts["usable"] += 1
                settlement_records.append(record)

                outcome = record.get("outcome", {})
                if outcome.get("success") is True:
                    state.success_count += 1
                elif outcome.get("success") is False:
                    state.failure_count += 1
            else:
                state.rejected += 1
                ds_counts["rejected"] += 1

        # Write per-dataset artifacts
        if raw_records:
            write_records_jsonl(raw_records, str(raw_dir / f"{ds_name}.jsonl"))
        if normalized_records:
            write_records_jsonl(
                normalized_records, str(normalized_dir / f"{ds_name}.jsonl")
            )
        if settlement_records:
            write_records_jsonl(
                settlement_records, str(settlements_dir / f"{ds_name}.jsonl")
            )

        state.dataset_counts[ds_name] = ds_counts

    # Build summary
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
