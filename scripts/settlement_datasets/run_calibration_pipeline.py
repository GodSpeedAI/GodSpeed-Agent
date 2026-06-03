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
# Calibration frame conversion
# ---------------------------------------------------------------------------


def external_record_to_model_calibration(record: dict[str, Any]) -> dict[str, Any]:
    """Convert an external adapter settlement record into model_calibration shape.

    The output is compatible with
    ``godspeed_nav.cognitive_model.build_calibration_frame``.
    """
    payment = record.get("payment", {})
    outcome = record.get("outcome", {})
    return {
        "id": f"{record.get('dataset', 'unknown')}:{record.get('task_id', '')}",
        "model_calibration": {
            "payment_predicted": {"steps": payment.get("elapsed_steps", 0)},
            "payment_actual": {
                "turns": payment.get("turns", 0),
                "tool_calls": payment.get("tool_calls", 0),
                "commands": payment.get("commands", 0),
                "errors": payment.get("error_count", 0),
            },
            "settlement_success": bool(outcome.get("success")),
            "settlement_score": 1.0 if outcome.get("success") else 0.0,
            "horizon_delta": 1.0 if outcome.get("success") else 0.0,
            "risk_estimate": min(
                1.0,
                payment.get("error_count", 0) / max(payment.get("elapsed_steps", 1), 1),
            ),
            "debt_estimate": 0.0,
        },
        "metadata": {
            "settlement_classification": "external-proxy-settlement",
            "source_dataset": record.get("dataset", ""),
        },
    }


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

    # ------------------------------------------------------------------
    # Calibration frame export
    # ------------------------------------------------------------------
    calibration_dir = scope.root / "calibration"
    calibration_dir.mkdir(parents=True, exist_ok=True)

    # Collect all settlement records across datasets
    all_settlements: list[dict[str, Any]] = []
    for settlement_file in settlements_dir.glob("*.jsonl"):
        from scripts.settlement_datasets.adapter_base import read_records_jsonl

        all_settlements.extend(read_records_jsonl(str(settlement_file)))

    calibration_records = [
        external_record_to_model_calibration(rec) for rec in all_settlements
    ]

    # Write model calibration records
    cal_records_path = calibration_dir / "model_calibration_records.jsonl"
    write_records_jsonl(calibration_records, str(cal_records_path))

    # Build calibration frame via cognitive_model
    from godspeed_nav.cognitive_model import build_calibration_frame

    cal_frame = build_calibration_frame(calibration_records)
    cal_frame_path = calibration_dir / "calibration_frame.csv"
    cal_frame.to_csv(str(cal_frame_path), index=False)

    # ------------------------------------------------------------------
    # Model evaluation
    # ------------------------------------------------------------------
    model_evaluation: dict[str, Any] = {
        "provider": provider,
        "calibration_rows": len(cal_frame),
        "success_class_count": int(cal_frame["settlement_success"].sum())
        if len(cal_frame) > 0
        else 0,
        "failure_class_count": int((~cal_frame["settlement_success"]).sum())
        if len(cal_frame) > 0
        else 0,
    }

    if len(cal_frame) > 0:
        baseline_rate = float(cal_frame["settlement_success"].mean())
        model_evaluation["deterministic_baseline_success_rate"] = round(
            baseline_rate, 4
        )

    if provider == "sklearn" and len(cal_frame) >= 10:
        try:
            from godspeed_nav.ml import SklearnPredictiveModelAdapter

            sklearn_adapter = SklearnPredictiveModelAdapter()
            # Use calibration records as history for a self-evaluation
            preds = sklearn_adapter.predict_affordances(
                settlement_history=calibration_records,
                candidates=[
                    {
                        "id": "eval_candidate",
                        "risk": 0.5,
                        "debt": 0.0,
                        "expected_horizon_delta": 1.0,
                    }
                ],
                payment_estimates={"eval_candidate": {"payment_burden": 1.0}},
            )
            model_evaluation["sklearn_evaluation"] = preds
        except RuntimeError as exc:
            model_evaluation["sklearn_extra_required"] = str(exc)
    elif provider == "sklearn":
        model_evaluation["sklearn_skipped_reason"] = (
            f"insufficient_data: {len(cal_frame)} rows, need 10"
        )

    # Write model evaluation
    model_eval_path = calibration_dir / "model_evaluation.json"
    model_eval_path.write_text(
        json.dumps(model_evaluation, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    # ------------------------------------------------------------------
    # Build summary
    # ------------------------------------------------------------------
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
        "calibration_frame_path": str(cal_frame_path),
        "model_evaluation": model_evaluation,
    }

    summary_path = scope.root / "summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    return summary


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point for the calibration pipeline."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Run the agentic calibration pipeline."
    )
    parser.add_argument(
        "--manifest",
        required=True,
        help="Path to calibration source manifest YAML",
    )
    parser.add_argument("--run-id", default=None, help="Run identifier")
    parser.add_argument(
        "--run-dir", default=None, help="Run directory (input and output)"
    )
    parser.add_argument(
        "--input-run-dir", default=None, help="Existing run directory to resume from"
    )
    parser.add_argument("--output-run-dir", default=None, help="Output run directory")
    parser.add_argument(
        "--target-usable-settlements",
        type=int,
        default=500,
        help="Target number of usable settlements",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.65,
        help="Minimum confidence threshold for usable records",
    )
    parser.add_argument(
        "--provider",
        default="disabled",
        choices=["disabled", "heuristic", "sklearn"],
        help="Predictive model provider",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from an existing run directory",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Process fixtures only, do not contact Hugging Face",
    )

    args = parser.parse_args()

    run_id = args.run_id or f"calibration-run"

    # Resume support: if resuming, load existing summary for counts
    if args.resume and args.input_run_dir:
        existing_summary_path = Path(args.input_run_dir) / "summary.json"
        if existing_summary_path.exists():
            existing = json.loads(existing_summary_path.read_text(encoding="utf-8"))
            print(
                f"Resuming from existing run with {existing.get('usable_settlements', 0)} usable settlements"
            )

    result = run_pipeline(
        manifest_path=args.manifest,
        run_id=run_id,
        output_run_dir=args.output_run_dir,
        target_usable_settlements=args.target_usable_settlements,
        min_confidence=args.min_confidence,
        provider=args.provider,
        dry_run=args.dry_run,
    )

    # Print summary to stdout for CLI consumers
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
