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


def should_stop_for_target(
    state: CalibrationRunState,
    datasets_processed: int = 0,
    min_datasets: int = 0,
) -> bool:
    """Return True when the usable-settlement target has been reached.

    If ``min_datasets > 0``, the target stop is deferred until at least
    that many datasets have been fully processed.
    """
    if state.usable_settlements >= state.target_usable_settlements:
        if min_datasets <= 0 or datasets_processed >= min_datasets:
            return True
    return False


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

    **Label hygiene:** All features are derived from pre-outcome proxy
    signals (payment, affordance_path, metadata) -- never from
    ``outcome.success``, ``settlement_quality``, or ``settlement_score``.
    ``settlement_success`` and ``settlement_score`` are labels only.
    """
    payment = record.get("payment", {})
    outcome = record.get("outcome", {})
    affordance_path = record.get("affordance_path", {})
    metadata = record.get("metadata", {})

    elapsed_steps = max(payment.get("elapsed_steps", 1), 1)
    error_count = payment.get("error_count", 0)
    turns = payment.get("turns", 0)
    tool_calls = payment.get("tool_calls", 0)
    commands = payment.get("commands", 0)

    # Pre-outcome proxy signals only
    error_rate = error_count / elapsed_steps
    payment_efficiency = (turns + tool_calls + commands) / max(elapsed_steps, 1)
    inverse_risk = 1.0 - min(error_rate, 1.0)

    # horizon_delta: proxy for "how much perception-action space opened up"
    # based on payment signals, NOT outcome.success.
    raw_delta = (inverse_risk * 0.6) + (min(payment_efficiency, 1.0) * 0.4)
    horizon_delta = round(min(max(raw_delta, 0.0), 1.0), 4)

    risk_estimate = min(1.0, error_rate)

    # Debt estimate: proxy for unresolved payment burden
    debt_estimate = 0.0
    if turns > 0 and tool_calls == 0:
        debt_estimate = min(turns / 20.0, 1.0)

    # --- New pre-outcome features ---

    # 1. tool_diversity_count: distinct tool names used
    tool_names = metadata.get("tool_names", [])
    tool_diversity_count = len(set(t for t in tool_names if t))

    # 2. error_recovery_ratio: fraction of error observations followed
    #    by a non-error observation in a later turn.
    #    Pre-outcome: uses observation content only, not outcome labels.
    observations = affordance_path.get("observations", [])
    error_obs_indices: list[int] = []
    non_error_obs_indices: list[int] = []
    error_keywords = ("error", "fail", "traceback", "exception", "assertionerror")
    for obs in observations:
        content = obs.get("content", "") or ""
        idx = obs.get("turn_index", 0)
        if any(kw in content.lower() for kw in error_keywords):
            error_obs_indices.append(idx)
        else:
            non_error_obs_indices.append(idx)

    if error_obs_indices:
        recoveries = 0
        for eidx in error_obs_indices:
            if any(nidx > eidx for nidx in non_error_obs_indices):
                recoveries += 1
        error_recovery_ratio = round(recoveries / len(error_obs_indices), 4)
    else:
        error_recovery_ratio = 0.0

    # 3. action_observation_ratio: assistant actions / tool observations
    actions = affordance_path.get("actions", [])
    n_actions = len(actions)
    n_observations = len(observations)
    if n_observations > 0:
        action_observation_ratio = round(n_actions / n_observations, 4)
    else:
        action_observation_ratio = 0.0

    # 4. avg_actions_per_step: actions / elapsed_steps
    avg_actions_per_step = round(n_actions / max(elapsed_steps, 1), 4)

    # 5. dataset_id: numeric encoding of source dataset (pre-outcome metadata)
    dataset_name = record.get("dataset", "unknown")
    _DATASET_ID_MAP = {
        "swegym_openhands": 0,
        "agenttrove": 1,
        "nebius_swe_agent": 2,
    }
    dataset_id = _DATASET_ID_MAP.get(dataset_name, -1)

    return {
        "id": f"{record.get('dataset', 'unknown')}:{record.get('task_id', '')}",
        "model_calibration": {
            "payment_predicted": {"steps": payment.get("elapsed_steps", 0)},
            "payment_actual": {
                "turns": turns,
                "tool_calls": tool_calls,
                "commands": commands,
                "errors": error_count,
            },
            "settlement_success": bool(outcome.get("success")),
            "settlement_score": 1.0 if outcome.get("success") else 0.0,
            "horizon_delta": horizon_delta,
            "risk_estimate": risk_estimate,
            "debt_estimate": round(debt_estimate, 4),
            "tool_diversity_count": tool_diversity_count,
            "error_recovery_ratio": error_recovery_ratio,
            "action_observation_ratio": action_observation_ratio,
            "avg_actions_per_step": avg_actions_per_step,
            "dataset_id": dataset_id,
        },
        "metadata": {
            "settlement_classification": "external-proxy-settlement",
            "source_dataset": dataset_name,
        },
    }


# ---------------------------------------------------------------------------
# Held-out sklearn evaluation
# ---------------------------------------------------------------------------


def _evaluate_sklearn_held_out(
    cal_frame: "pd.DataFrame",
    leakage_audit: dict[str, Any],
    sampling_strategy: str,
) -> dict[str, Any]:
    """Evaluate a LogisticRegression model on a held-out test split.

    All sklearn imports are performed lazily so the module loads without
    sklearn installed.  Returns a dict with held-out metrics, baseline
    metrics, and comparison flags.
    """
    if leakage_audit.get("leakage_detected"):
        return {
            "sklearn_metrics_valid": False,
            "sklearn_invalid_reason": (
                f"Label leakage detected in features: "
                f"{leakage_audit['leaked_features']}. "
                f"sklearn predictions are not meaningful."
            ),
        }

    import numpy as np
    import pandas as pd
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import (
        average_precision_score,
        balanced_accuracy_score,
        brier_score_loss,
        confusion_matrix,
        f1_score,
        roc_auc_score,
    )
    from sklearn.model_selection import train_test_split

    label_col = "settlement_success"
    score_col = "settlement_score"
    exclude_cols = {label_col, score_col}

    feature_cols_all = [
        "payment_predicted_total",
        "payment_actual_total",
        "payment_error",
        "horizon_delta",
        "risk_estimate",
        "debt_estimate",
        "tool_diversity_count",
        "error_recovery_ratio",
        "action_observation_ratio",
        "avg_actions_per_step",
        "dataset_id",
    ]
    leaked = set(leakage_audit.get("leaked_features", []))
    feature_cols = [
        c
        for c in feature_cols_all
        if c in cal_frame.columns and c not in exclude_cols and c not in leaked
    ]

    y = cal_frame[label_col].astype(int)
    X = cal_frame[feature_cols].astype(float)

    if len(cal_frame) < 20:
        return {
            "sklearn_metrics_valid": False,
            "sklearn_skipped_reason": (
                f"insufficient_data: {len(cal_frame)} rows, need 20"
            ),
        }

    if y.nunique() < 2:
        return {
            "sklearn_metrics_valid": False,
            "sklearn_skipped_reason": (
                f"single_class_only: found class {int(y.iloc[0])}, need both 0 and 1"
            ),
        }

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    if sampling_strategy == "balanced":
        train_df = X_train.copy()
        train_df[label_col] = y_train.values
        class_counts = y_train.value_counts()
        minority_class = class_counts.idxmin()
        minority_size = int(class_counts.min())
        majority_class = class_counts.idxmax()

        minority_df = train_df[train_df[label_col] == minority_class]
        majority_df = train_df[train_df[label_col] == majority_class]
        majority_downsampled = majority_df.sample(
            n=minority_size,
            random_state=42,
        )
        balanced_train = (
            pd.concat([minority_df, majority_downsampled])
            .sample(frac=1, random_state=42)
            .reset_index(drop=True)
        )
        X_train = balanced_train[feature_cols]
        y_train = balanced_train[label_col].astype(int)

    clf = LogisticRegression(
        class_weight="balanced",
        max_iter=200,
        solver="lbfgs",
        random_state=42,
    )
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    y_prob = clf.predict_proba(X_test)[:, 1]

    both_classes_in_test = y_test.nunique() >= 2

    # sklearn metrics (all three families)
    sklearn_raw_accuracy = round(float((y_pred == y_test).mean()), 4)
    sklearn_balanced_accuracy = round(float(balanced_accuracy_score(y_test, y_pred)), 4)
    sklearn_f1 = round(float(f1_score(y_test, y_pred)), 4)

    held_out: dict[str, Any] = {
        "raw_accuracy": sklearn_raw_accuracy,
        "balanced_accuracy": sklearn_balanced_accuracy,
        "f1_score": sklearn_f1,
        "brier_score": round(float(brier_score_loss(y_test, y_prob)), 4),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
    }
    if both_classes_in_test:
        held_out["roc_auc"] = round(float(roc_auc_score(y_test, y_prob)), 4)
        held_out["average_precision"] = round(
            float(average_precision_score(y_test, y_prob)), 4
        )

    # Baseline predictors (matched metric families)
    train_success_rate = float(y_train.mean())
    majority_class = int(y_train.value_counts().idxmax())

    # Majority-class baseline: always predict the majority class
    majority_preds = np.full(len(y_test), majority_class)
    majority_raw_accuracy = round(float((majority_preds == y_test).mean()), 4)
    majority_balanced_accuracy = round(
        float(balanced_accuracy_score(y_test, majority_preds)), 4
    )
    majority_f1 = round(float(f1_score(y_test, majority_preds, zero_division=0.0)), 4)

    # Success-rate baseline: predict success when probability >= training rate
    success_rate_preds = (y_prob >= train_success_rate).astype(int)
    sr_raw_accuracy = round(float((success_rate_preds == y_test).mean()), 4)
    sr_balanced_accuracy = round(
        float(balanced_accuracy_score(y_test, success_rate_preds)), 4
    )
    sr_f1 = round(float(f1_score(y_test, success_rate_preds, zero_division=0.0)), 4)

    baseline: dict[str, Any] = {
        "majority_class_raw_accuracy": majority_raw_accuracy,
        "majority_class_balanced_accuracy": majority_balanced_accuracy,
        "majority_class_f1": majority_f1,
        "success_rate_raw_accuracy": sr_raw_accuracy,
        "success_rate_balanced_accuracy": sr_balanced_accuracy,
        "success_rate_f1": sr_f1,
    }

    return {
        "sklearn_metrics_valid": True,
        "train_size": int(len(X_train)),
        "test_size": int(len(X_test)),
        "train_success_rate": round(train_success_rate, 4),
        "test_success_rate": round(float(y_test.mean()), 4),
        "sampling_strategy": sampling_strategy,
        "class_weight": "balanced",
        "features_used": feature_cols,
        "held_out_metrics": held_out,
        "baseline_metrics": baseline,
        "sklearn_beats_majority_on_balanced_accuracy": bool(
            sklearn_balanced_accuracy > majority_balanced_accuracy
        ),
        "sklearn_beats_majority_on_f1": bool(sklearn_f1 > majority_f1),
        "sklearn_beats_majority_on_raw_accuracy": bool(
            sklearn_raw_accuracy > majority_raw_accuracy
        ),
        "sklearn_beats_success_rate_on_balanced_accuracy": bool(
            sklearn_balanced_accuracy > sr_balanced_accuracy
        ),
        "sklearn_beats_success_rate_on_f1": bool(sklearn_f1 > sr_f1),
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
    sampling_strategy: str = "natural",
    min_datasets: int = 0,
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
            "sampling_strategy": sampling_strategy,
            "min_datasets": min_datasets,
        },
    )

    # Ensure output sub-directories exist
    raw_dir = scope.root / "raw"
    normalized_dir = scope.root / "normalized"
    settlements_dir = scope.root / "settlements"
    for d in (raw_dir, normalized_dir, settlements_dir):
        d.mkdir(parents=True, exist_ok=True)

    datasets_processed: int = 0

    for source in manifest["datasets"]:
        if should_stop_for_target(state, datasets_processed, min_datasets):
            break

        ds_name = source["name"]
        adapter_name = source["adapter"]
        max_rows = source.get("max_rows")

        # In dry-run mode, skip datasets without a local input_path
        if dry_run and not source.get("input_path"):
            state.dataset_counts[ds_name] = {
                "scanned": 0,
                "normalized": 0,
                "usable": 0,
                "rejected": 0,
                "adapter_errors": 0,
                "skipped_reason": "dry_run_no_local_input",
            }
            datasets_processed += 1
            continue

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
            datasets_processed += 1
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
            datasets_processed += 1
            continue

        for raw in row_iter:
            if should_stop_for_target(state, datasets_processed, min_datasets):
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
        datasets_processed += 1

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

    # ------------------------------------------------------------------
    # Leakage audit: flag features with near-perfect correlation to label
    # ------------------------------------------------------------------
    leakage_audit: dict[str, Any] = {
        "feature_correlations": {},
        "leaked_features": [],
        "leakage_detected": False,
    }
    if len(cal_frame) > 1:
        feature_cols = [
            "payment_predicted_total",
            "payment_actual_total",
            "payment_error",
            "horizon_delta",
            "risk_estimate",
            "debt_estimate",
            "tool_diversity_count",
            "error_recovery_ratio",
            "action_observation_ratio",
            "avg_actions_per_step",
            "dataset_id",
        ]
        available_features = [c for c in feature_cols if c in cal_frame.columns]
        y = cal_frame["settlement_success"].astype(float)
        for col in available_features:
            series = cal_frame[col]
            if series.std() == 0:
                corr = 0.0
            else:
                corr = round(abs(float(series.corr(y))), 4)
            leakage_audit["feature_correlations"][col] = corr
            if corr >= 0.95:
                leakage_audit["leaked_features"].append(col)
        if leakage_audit["leaked_features"]:
            leakage_audit["leakage_detected"] = True
    model_evaluation["leakage_audit"] = leakage_audit

    # ------------------------------------------------------------------
    # Held-out sklearn evaluation
    # ------------------------------------------------------------------
    if provider == "sklearn" and len(cal_frame) >= 10:
        held_out_result = _evaluate_sklearn_held_out(
            cal_frame,
            leakage_audit,
            sampling_strategy,
        )
        model_evaluation["sklearn_held_out_evaluation"] = held_out_result

        # Keep the existing SklearnPredictiveModelAdapter as a secondary
        # candidate prediction evaluation.
        try:
            from godspeed_nav.ml import SklearnPredictiveModelAdapter

            sklearn_adapter = SklearnPredictiveModelAdapter()
            preds = sklearn_adapter.predict_affordances(
                settlement_history=calibration_records,
                candidates=[
                    {
                        "id": "eval_candidate",
                        "risk": 0.5,
                        "debt": 0.0,
                        "expected_horizon_delta": 0.7,
                    }
                ],
                payment_estimates={"eval_candidate": {"payment_burden": 1.0}},
            )
            model_evaluation["sklearn_candidate_prediction"] = preds
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
        "sampling_strategy": sampling_strategy,
        "min_datasets": min_datasets,
        "scanned": state.scanned,
        "normalized": state.normalized,
        "usable_settlements": state.usable_settlements,
        "rejected": state.rejected,
        "adapter_errors": state.adapter_errors,
        "dataset_counts": state.dataset_counts,
        "success_count": state.success_count,
        "failure_count": state.failure_count,
        "datasets_processed": datasets_processed,
        "calibration_frame_path": str(cal_frame_path),
        "model_evaluation": model_evaluation,
    }

    summary_path = scope.root / "summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    # ------------------------------------------------------------------
    # Evidence report
    # ------------------------------------------------------------------
    report_dir_resolved = Path(report_dir) if report_dir else scope.root / "docs"
    report_dir_resolved.mkdir(parents=True, exist_ok=True)
    report_path = report_dir_resolved / f"{run_id}-report.md"

    class_balance = ""
    if state.success_count + state.failure_count > 0:
        total = state.success_count + state.failure_count
        class_balance = (
            f"- Success: {state.success_count} ({state.success_count / total:.1%})\n"
            f"- Failure: {state.failure_count} ({state.failure_count / total:.1%})\n"
        )
    else:
        class_balance = "- No class data available\n"

    model_eval_summary = ""
    me = model_evaluation
    if me.get("provider") == "disabled":
        model_eval_summary = "- Provider: disabled (deterministic only)\n"
    elif me.get("sklearn_held_out_evaluation"):
        model_eval_summary = "- Provider: sklearn\n- Held-out evaluation available\n"
    elif me.get("sklearn_extra_required"):
        model_eval_summary = f"- Provider: sklearn (not installed)\n- Note: {me['sklearn_extra_required']}\n"
    elif me.get("sklearn_skipped_reason"):
        model_eval_summary = (
            f"- Provider: sklearn\n- Skipped: {me['sklearn_skipped_reason']}\n"
        )
    else:
        model_eval_summary = f"- Provider: {me.get('provider', 'unknown')}\n"

    # Held-out metrics report section
    held_out_section = ""
    h_eval = me.get("sklearn_held_out_evaluation")
    if h_eval:
        held_out_section = "## Held-Out Evaluation\n\n"
        if not h_eval.get("sklearn_metrics_valid"):
            reason = h_eval.get(
                "sklearn_invalid_reason",
                h_eval.get("sklearn_skipped_reason", "unknown"),
            )
            held_out_section += f"- **Status:** invalid\n- **Reason:** {reason}\n"
        else:
            held_out_section += (
                f"- **Train size:** {h_eval['train_size']}\n"
                f"- **Test size:** {h_eval['test_size']}\n"
                f"- **Train success rate:** {h_eval['train_success_rate']}\n"
                f"- **Test success rate:** {h_eval['test_success_rate']}\n"
                f"- **Sampling strategy:** {h_eval['sampling_strategy']}\n"
                f"- **Class weight:** {h_eval['class_weight']}\n"
                f"- **Features used:** {', '.join(h_eval['features_used'])}\n\n"
                "### Held-Out Metrics\n\n"
            )
            hm = h_eval["held_out_metrics"]
            for metric_name in (
                "raw_accuracy",
                "balanced_accuracy",
                "f1_score",
                "roc_auc",
                "average_precision",
                "brier_score",
            ):
                if metric_name in hm:
                    held_out_section += f"- **{metric_name}:** {hm[metric_name]}\n"
            if "confusion_matrix" in hm:
                held_out_section += (
                    f"- **confusion_matrix:** {hm['confusion_matrix']}\n"
                )

            held_out_section += "\n### Baseline Metrics (matched families)\n\n"
            bm = h_eval["baseline_metrics"]
            for bname, bval in bm.items():
                held_out_section += f"- **{bname}:** {bval}\n"

            held_out_section += "\n### Matched Baseline Comparison\n\n"
            held_out_section += (
                f"- **sklearn raw_accuracy vs majority raw_accuracy:**"
                f" {h_eval.get('sklearn_beats_majority_on_raw_accuracy', 'N/A')}\n"
                f"- **sklearn balanced_accuracy vs majority balanced_accuracy:**"
                f" {h_eval.get('sklearn_beats_majority_on_balanced_accuracy', 'N/A')}\n"
                f"- **sklearn f1 vs majority f1:**"
                f" {h_eval.get('sklearn_beats_majority_on_f1', 'N/A')}\n"
                f"- **sklearn balanced_accuracy vs success_rate balanced_accuracy:**"
                f" {h_eval.get('sklearn_beats_success_rate_on_balanced_accuracy', 'N/A')}\n"
                f"- **sklearn f1 vs success_rate f1:**"
                f" {h_eval.get('sklearn_beats_success_rate_on_f1', 'N/A')}\n"
            )

        # Leakage audit result
        held_out_section += (
            "\n### Leakage Audit\n\n"
            f"- **Leakage detected:** {leakage_audit['leakage_detected']}\n"
        )
        if leakage_audit["leaked_features"]:
            held_out_section += (
                f"- **Leaked features:**"
                f" {', '.join(leakage_audit['leaked_features'])}\n"
            )
        held_out_section += "\n"

    report_lines = [
        f"# Calibration Run Report: {run_id}",
        "",
        f"**Date:** {summary['created_at']}",
        f"**Manifest:** {str(manifest_path)}",
        "",
        "## Dataset Counts",
        "",
    ]
    for ds_name, counts in state.dataset_counts.items():
        report_lines.append(f"### {ds_name}")
        report_lines.append(f"- Scanned: {counts.get('scanned', 0)}")
        report_lines.append(f"- Normalized: {counts.get('normalized', 0)}")
        report_lines.append(f"- Usable: {counts.get('usable', 0)}")
        report_lines.append(f"- Rejected: {counts.get('rejected', 0)}")
        report_lines.append(f"- Adapter errors: {counts.get('adapter_errors', 0)}")
        report_lines.append("")

    report_lines.extend(
        [
            "## Summary",
            "",
            f"- Raw rows scanned: {state.scanned}",
            f"- Normalized records: {state.normalized}",
            f"- usable settlements: {state.usable_settlements}",
            f"- Rejected records: {state.rejected}",
            f"- Adapter errors: {state.adapter_errors}",
            f"- Datasets processed: {datasets_processed}",
            f"- Sampling strategy: {sampling_strategy}",
            f"- Min datasets: {min_datasets}",
            "",
            "## Class Balance",
            "",
            class_balance,
            f"## Calibration Frame",
            "",
            f"- Path: `{cal_frame_path}`",
            f"- Rows: {len(cal_frame)}",
            "",
            "## Model Evaluation",
            "",
            model_eval_summary,
        ]
    )

    if held_out_section:
        report_lines.append(held_out_section)

    report_lines.extend(
        [
            "## Proof Classification",
            "",
            "external-proxy-calibration",
            "",
            "All imported dataset records are classified as `external-proxy-settlement`.",
            "They are valid for calibration experiments, baseline comparison, and model",
            "warm-starting. They are not local Godspeed settlement evidence.",
            "",
            "## Non-Claims",
            "",
            "This report does not claim local capability, metabolization, enterprise readiness,",
            "or local settlement proof from external proxy data.",
            "",
            "## Next Move",
            "",
            "Run the fixture path first, then live HF only after local tests pass.",
            "",
        ]
    )

    report_path.write_text("\n".join(report_lines), encoding="utf-8")

    summary["report_path"] = str(report_path)

    # Re-write summary with report_path
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
    parser.add_argument(
        "--sampling-strategy",
        default="natural",
        choices=["natural", "balanced"],
        help="Sampling strategy for sklearn training data",
    )
    parser.add_argument(
        "--min-datasets",
        type=int,
        default=0,
        help="Minimum number of datasets to process before stopping for target",
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
        sampling_strategy=args.sampling_strategy,
        min_datasets=args.min_datasets,
    )

    # Print summary to stdout for CLI consumers
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
