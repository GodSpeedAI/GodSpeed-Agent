"""Execute the FROZEN v008 LOSO transfer matrix (plan godspeed-agent-v008-r1-transfer, V3).

The contract is the FROZEN preregistration
``.agents/reports/v008-transfer-preregistration.yaml`` (V2, committed at
HEAD): the held-out source EVALUATES the preregistered system, never
redesigns it.  This runner is a SEPARATE v008 module; v006/v007 files are
IMPORTED (never forked or modified): feature schemas and identity helpers
come from ``v007_recovery``.

Design (exactly per the prereg, section references inline):

- Leave-one-source-out over the three admitted sources; R1 rows only.
  Cell C: train pool = the other two sources; test ONCE on C.
- Representations: M = ``v005_minimal_recovery`` sans ``dataset_id`` (6
  features; ``error_count_so_far`` aliases the v006 ``error_count``
  column per ``select_ablation_features``), F = ``v007_r1@1`` complete
  (54 features), T = derived per held-out cell from that cell's training
  pool ONLY by the mechanical section-4 rule.  M/F/T are PRIMARY and
  identity-free.  Diagnostics: F+dataset_id, T+dataset_id (never
  primary).  Sensitivity: parent-only weighting (no source balancing)
  for M and T.
- T selection gates (all required, per training pool): univariate
  direction consistent across BOTH training sources in >= 4/5 folds;
  weighted-LR coefficient sign consistent in >= 4/5 folds; worst-case
  one-vs-rest source-identifiability AUC < 0.85; non-constant in both
  training sources.  Size rules: |T| < 5 -> fill to 5 by stability
  score (fold-consistency counts, ties lexicographic); |T| > 20 -> top
  20 by min(direction consistency, coefficient consistency).
- Weighting: primary = parent-balanced x source-balanced (each training
  source equal total weight; within a source each parent equal),
  implemented as ``sample_weight`` used in FIT ONLY (never in metrics).
  Sensitivity = ``v007_recovery.parent_balanced_training_weights``.
- Preprocessing: StandardScaler fit on the training pool's rows
  (weighted), applied to all splits of that cell.
- Estimator: ``LogisticRegression(class_weight='balanced',
  max_iter=1000, solver='lbfgs', random_state=42)``; C in
  {0.01, 0.1, 1.0} by GroupKFold(5) mean ROC-AUC inside the pool
  (tiebreak mean AP, then grid order).  No LightGBM anywhere.
- Calibration: isotonic on the selection folds' out-of-fold training
  predictions iff the selected model's OOF ECE(10 bin) > 0.05; applied
  to the held-out source; never fit on it.
- Metrics per cell and arm: ROC-AUC, AP, Brier, ECE(10 bin), balanced
  accuracy, precision/recall/F1 @0.5, confusion matrix (headline on raw
  probabilities; Brier/ECE also reported after calibration -- isotonic
  is monotone so ROC-AUC/AP are unchanged).  macro = unweighted mean
  over the three held-out cells of the primary arms' ROC-AUC; pooled =
  secondary context only.
- Acceptance is mechanical (frozen section 7): primary_T_earned,
  secondary_T_vs_F, descriptive F-vs-M and T-overlap, plus the frozen
  SETTLED_earned / PARTIAL / NOT_EARNED classification mapping.

Documented operationalizations (recorded in the experiment manifest):

- Direction consistency per fold counts only when BOTH training
  sources' univariate AUC signs are defined (both classes present and
  AUC != 0.5 within that source's fold-train rows) and equal.
- Coefficient-sign consistency = the majority sign's fold fraction
  (exactly-zero coefficients are consistent with neither sign).
- Source-identifiability AUC (per feature, once per pool): feature
  standardized by an (unweighted) scaler fit on the pool, then the
  frozen LR spec fit per GroupKFold(5) fold to predict the source from
  that single feature; the feature's statistic is max over folds of
  max(AUC_source0, 1 - AUC_source0) -- the worst case over folds and
  sources (with two sources, AUC for the second source is exactly
  1 - AUC for the first under the same scores).
- Non-constancy gate: per training source, computed once per pool on
  all of that source's rows (std > 0 in BOTH sources required).
- Stability score (fill rule) = direction folds + coefficient folds
  (counts out of 10); trim rule key = min(direction folds, coefficient
  folds); ties always broken lexicographically by feature name.
- Per-fold T measurements use the primary weights recomputed on the
  fold-train rows (the frozen parent x source balancing).
- PARTIAL uses v007's materiality margin: a primary arm is materially
  above chance at ROC-AUC >= 0.55; "most cells" = >= 2 of 3.

Isolation (tested): ``derive_t_selection``, ``fit_scaler``,
``select_C_and_oof``, ``fit_calibrator`` and ``fit_arm`` take ONLY the
training pool; there is no parameter through which held-out rows could
influence selection, scaling, tuning, or calibration.  The held-out
frame enters ``run_arm`` only after fitting, for the single evaluation.

Determinism: fixed seeds; no wall-clock fields in any artifact (runtime
is printed to stdout only) so the full matrix is byte-identical across
runs; ``run_matrix`` executes the matrix twice in-process, asserts the
six data artifacts byte-identical, and records their md5s in the
manifest.  Artifacts are JSON/CSV/JSONL only; no plots.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import sklearn
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

from scripts.settlement_datasets.v007_recovery import (
    FRAME_COLUMNS,
    POINT_R1,
    R1_FEATURES,
    V005_MINIMAL_RECOVERY_FEATURES,
    assert_no_label_features,
    parent_balanced_training_weights,
)

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
EPISODE_TABLE = (
    WORKSPACE_ROOT
    / "data"
    / "settlement_datasets"
    / "corpora"
    / "v008-episodes"
    / "episodes.jsonl"
)
RESULTS_ROOT = WORKSPACE_ROOT / "data" / "settlement_datasets" / "runs" / "v008-transfer"
PREREG_PATH = (
    WORKSPACE_ROOT / ".agents" / "reports" / "v008-transfer-preregistration.yaml"
)

SEED = 42
N_SPLITS = 5
C_GRID: tuple[float, ...] = (0.01, 0.1, 1.0)
ECE_BINS = 10
ECE_TRIGGER = 0.05
FIXED_THRESHOLD = 0.5
# v007's documented materiality margin above the 0.5 class-prior baseline,
# used ONLY by the frozen PARTIAL / NOT_EARNED classification step.
MATERIAL_AUC_MARGIN = 0.05

# Frozen T-rule constants (prereg section 4).
GATE_MIN_FOLDS = 4  # >= 80% of the 5 folds
IDENT_AUC_MAX = 0.85
MIN_T_SIZE = 5
MAX_T_SIZE = 20

# Frozen acceptance constants (prereg section 7).
MACRO_MIN_DELTA = 0.02
CELL_DEGRADATION_GUARD = 0.03
MIN_CELLS = 2

SOURCES: tuple[str, ...] = ("nebius_swe_agent", "swe_smith", "swegym_openhands")
CELLS: tuple[str, ...] = tuple(sorted(SOURCES))

IDENTITY_FEATURE = "dataset_id"
POINT = POINT_R1

# M: v005_minimal_recovery sans dataset_id (6 features).
M_FEATURES: tuple[str, ...] = tuple(
    name for name in V005_MINIMAL_RECOVERY_FEATURES if name != IDENTITY_FEATURE
)
# F: the complete v007_r1@1 schema (54 features; identity-free by construction).
F_FEATURES: tuple[str, ...] = tuple(R1_FEATURES)
# Schema-name -> frame-column alias (v007 ``select_ablation_features``
# convention; never a forked formula).
FEATURE_SOURCE_COLUMN: dict[str, str] = {"error_count_so_far": "error_count"}

# Arm keys: primary M/F/T, diagnostics *_id, sensitivity M/T under
# parent-only weights.
PRIMARY_ARM_KEYS: tuple[str, ...] = ("M", "F", "T")
DIAGNOSTIC_ARM_KEYS: tuple[str, ...] = ("F_id", "T_id")
SENSITIVITY_ARM_KEYS: tuple[str, ...] = ("M_parent_only", "T_parent_only")
ALL_ARM_KEYS: tuple[str, ...] = (
    PRIMARY_ARM_KEYS + DIAGNOSTIC_ARM_KEYS + SENSITIVITY_ARM_KEYS
)

WEIGHTING_BALANCED = "parent_x_source_balanced"
WEIGHTING_PARENT_ONLY = "parent_only"

# Identity/bookkeeping columns that must never enter a primary feature list
# (everything on the frame except the 54 R1 schema features and the
# ablation-only ``consecutive_error_observations`` carried by M).
NON_FEATURE_COLUMNS: frozenset[str] = frozenset(
    set(FRAME_COLUMNS) - set(R1_FEATURES) - set(M_FEATURES)
)

ARTIFACT_NAMES: tuple[str, ...] = (
    "results.json",
    "per_cell_results.csv",
    "test_predictions.jsonl",
    "t_selection.json",
    "calibration_summary.json",
    "error_analysis.json",
)


# ---------------------------------------------------------------------------
# Hashing and loading
# ---------------------------------------------------------------------------


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _md5_bytes(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()  # noqa: S324 - determinism fingerprint only


def _json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def git_head_commit(repo_root: Path = WORKSPACE_ROOT) -> str | None:
    """Current HEAD commit (provenance only; None when git is unavailable)."""
    try:
        return (
            subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
        )
    except (OSError, subprocess.CalledProcessError):
        return None


def load_r1_frame(table_path: Path = EPISODE_TABLE) -> tuple[pd.DataFrame, str]:
    """Load the episode table, keep R1 rows only; return (frame, sha256)."""
    loaded = pd.read_json(table_path, lines=True, dtype=False)
    if loaded.empty:
        raise RuntimeError(f"episode table is empty: {table_path}")
    missing = [c for c in FRAME_COLUMNS if c not in loaded.columns]
    if missing:
        raise RuntimeError(f"episode table lacks frame columns: {missing}")
    frame = loaded[loaded["point"] == POINT].copy()
    if frame.empty:
        raise RuntimeError(f"episode table has no {POINT} rows: {table_path}")
    return frame[list(FRAME_COLUMNS)], _sha256_file(table_path)


# ---------------------------------------------------------------------------
# Feature guards and matrices
# ---------------------------------------------------------------------------


def assert_no_identity(feature_names: list[str]) -> None:
    """Identity whitelist guard: ``dataset_id`` (and every bookkeeping
    column) must never enter a PRIMARY arm's feature list."""
    offenders = [c for c in feature_names if c in NON_FEATURE_COLUMNS]
    if offenders:
        raise ValueError(
            "Identity/bookkeeping columns must never enter a feature list: "
            f"{offenders}"
        )
    assert_no_label_features(feature_names)


def resolve_arm_features(arm_key: str, t_features: list[str]) -> list[str]:
    """Frozen feature list for one arm key (identity guard enforced).

    Diagnostics arms (``F_id`` / ``T_id``) are the ONLY arms that may
    carry ``dataset_id``, per the frozen identity-variant rule.
    """
    if arm_key == "M":
        features = list(M_FEATURES)
    elif arm_key == "F":
        features = list(F_FEATURES)
    elif arm_key == "T":
        features = list(t_features)
    elif arm_key == "F_id":
        features = list(F_FEATURES) + [IDENTITY_FEATURE]
    elif arm_key == "T_id":
        features = list(t_features) + [IDENTITY_FEATURE]
    elif arm_key in ("M_parent_only", "T_parent_only"):
        features = resolve_arm_features(
            "M" if arm_key == "M_parent_only" else "T", t_features
        )
    else:
        raise ValueError(f"unknown arm key: {arm_key}")
    if arm_key not in ("F_id", "T_id"):
        assert_no_identity(features)
    return features


def feature_matrix(frame: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    """Float feature matrix for the given schema names (aliases applied)."""
    source_cols = [FEATURE_SOURCE_COLUMN.get(c, c) for c in features]
    missing = [c for c in source_cols if c not in frame.columns]
    if missing:
        raise ValueError(f"frame lacks feature columns: {missing}")
    X = frame[source_cols].astype(float)
    X.columns = list(features)
    values = X.to_numpy()
    if not np.isfinite(values).all():
        raise ValueError("non-finite feature values in feature matrix")
    return X


# ---------------------------------------------------------------------------
# Weights (fit only, never metrics)
# ---------------------------------------------------------------------------


def balanced_source_parent_weights(pool: pd.DataFrame) -> np.ndarray:
    """FROZEN primary weight: parent-balanced x source-balanced.

    Per row: ``1/(training episodes of that parent)`` (episodes counted
    as distinct ``episode_id`` per parent), normalized per source so
    every training source contributes equal total weight and, within a
    source, every parent contributes equal weight: a source holding n
    parents contributes total ``1/n_sources``; each of its parents
    carries ``1/(n_sources * n_parents_of_that_source)``.
    """
    if pool.empty:
        return np.zeros(0)
    base = parent_balanced_training_weights(pool).to_numpy(dtype=float)
    datasets = pool["dataset"].astype(str).to_numpy()
    totals: dict[str, float] = {
        str(dataset): float(base[datasets == dataset].sum())
        for dataset in np.unique(datasets)
    }
    n_sources = len(totals)
    weights = np.array(
        [base[i] / (n_sources * totals[str(dataset)]) for i, dataset in enumerate(datasets)],
        dtype=float,
    )
    if not np.isfinite(weights).all() or weights.min() <= 0:
        raise RuntimeError("non-positive or non-finite training weights")
    return weights


def training_weights(pool: pd.DataFrame, weighting: str) -> np.ndarray:
    """Dispatch the frozen weighting scheme (used in fit only)."""
    if weighting == WEIGHTING_BALANCED:
        return balanced_source_parent_weights(pool)
    if weighting == WEIGHTING_PARENT_ONLY:
        return parent_balanced_training_weights(pool).to_numpy(dtype=float)
    raise ValueError(f"unknown weighting scheme: {weighting}")


# ---------------------------------------------------------------------------
# Group folds
# ---------------------------------------------------------------------------


def group_folds(pool: pd.DataFrame) -> list[tuple[np.ndarray, np.ndarray]]:
    """Deterministic GroupKFold(5) over the pool's ``split_group``."""
    groups = pool["split_group"].astype(str)
    n_groups = int(groups.nunique())
    if n_groups < N_SPLITS:
        raise ValueError(
            f"GroupKFold({N_SPLITS}) impossible with {n_groups} split groups"
        )
    gkf = GroupKFold(n_splits=N_SPLITS)
    dummy = np.zeros(len(pool))
    return list(gkf.split(dummy, dummy, groups))


# ---------------------------------------------------------------------------
# Estimator (frozen spec; no LightGBM anywhere)
# ---------------------------------------------------------------------------


def make_lr(c_value: float) -> LogisticRegression:
    return LogisticRegression(
        class_weight="balanced",
        max_iter=1000,
        solver="lbfgs",
        random_state=SEED,
        C=c_value,
    )


# ---------------------------------------------------------------------------
# T selection (training pool ONLY -- structural isolation)
# ---------------------------------------------------------------------------


def _univariate_sign(values: np.ndarray, y: np.ndarray) -> int:
    """sign(AUC - 0.5) for one source's fold-train rows; 0 when undefined."""
    if len(np.unique(y)) < 2:
        return 0
    auc = float(roc_auc_score(y, values))
    if auc > 0.5:
        return 1
    if auc < 0.5:
        return -1
    return 0


def identifiability_auc(pool: pd.DataFrame, feature: str) -> float:
    """Worst-case one-vs-rest source-identifiability AUC for one feature.

    Computed ONCE per pool: the feature is standardized by an unweighted
    scaler fit on the pool, then the frozen LR spec predicts the source
    under GroupKFold(5); the statistic is max over folds of
    max(AUC(source0), 1 - AUC(source0)).
    """
    column = feature_matrix(pool, [feature]).to_numpy(dtype=float).reshape(-1, 1)
    column = StandardScaler().fit(column).transform(column)
    sources = pool["dataset"].astype(str).to_numpy()
    classes = sorted(str(s) for s in np.unique(sources))
    if len(classes) != 2:
        raise ValueError(
            "source identifiability is defined for exactly two training "
            f"sources; pool has {classes}"
        )
    worst = 0.5
    for tr, va in group_folds(pool):
        if len(np.unique(sources[va])) < 2:
            continue
        est = make_lr(1.0)
        est.fit(column[tr], sources[tr] == classes[0])
        prob = est.predict_proba(column[va])[:, 1]
        auc0 = float(roc_auc_score(sources[va] == classes[0], prob))
        worst = max(worst, auc0, 1.0 - auc0)
    return float(worst)


def derive_t_selection(pool: pd.DataFrame) -> dict[str, Any]:
    """FROZEN mechanical T rule (prereg section 4) on the training pool.

    Returns the full per-feature gate table and the selected set.  This
    function takes ONLY the training pool: there is no parameter through
    which held-out-source rows could influence the selected set.
    """
    features = list(F_FEATURES)
    X = feature_matrix(pool, features)
    y = pool["recovery_success"].astype(int).to_numpy()
    datasets = pool["dataset"].astype(str).to_numpy()
    training_sources = sorted(str(s) for s in np.unique(datasets))
    if len(training_sources) != 2:
        raise ValueError(
            "a transfer cell trains on exactly two sources; pool has "
            f"{training_sources}"
        )

    # Pool-level non-constancy per source (gate 4).
    constant_in: dict[str, set[str]] = {}
    for source in training_sources:
        sub = X[datasets == source]
        constant_in[source] = {
            name
            for name, std in sub.std(ddof=0).items()
            if float(std) == 0.0
        }

    # Pool-level identifiability (gate 3), once per feature.
    ident = {feature: identifiability_auc(pool, feature) for feature in features}

    # Per-fold measurements (frozen LR spec + primary weights on fold-train).
    dir_folds = {f: 0 for f in features}
    coef_folds = {f: 0 for f in features}
    for tr, _va in group_folds(pool):
        fold_train = pool.iloc[tr]
        fold_weights = balanced_source_parent_weights(fold_train)
        X_tr = feature_matrix(fold_train, features)
        scaler = StandardScaler().fit(X_tr, sample_weight=fold_weights)
        y_tr = fold_train["recovery_success"].astype(int).to_numpy()
        est = make_lr(1.0)
        est.fit(scaler.transform(X_tr), y_tr, sample_weight=fold_weights)
        coefs = np.asarray(est.coef_[0], dtype=float)

        ds_tr = fold_train["dataset"].astype(str).to_numpy()
        for j, feature in enumerate(features):
            if coefs[j] > 0:
                coef_folds[feature] += 1
            elif coefs[j] < 0:
                coef_folds[feature] -= 1
            signs = [
                _univariate_sign(
                    X_tr.iloc[np.flatnonzero(ds_tr == source), j].to_numpy(dtype=float),
                    y_tr[ds_tr == source],
                )
                for source in training_sources
            ]
            if signs[0] != 0 and signs[0] == signs[1]:
                dir_folds[feature] += 1

    gate_table: list[dict[str, Any]] = []
    selected: list[str] = []
    for feature in features:
        dir_count = int(dir_folds[feature])
        coef_signed = int(coef_folds[feature])
        coef_count = abs(coef_signed)
        coef_sign = 1 if coef_signed > 0 else (-1 if coef_signed < 0 else 0)
        const_flags = {
            source: feature in constant_in[source] for source in training_sources
        }
        gates = {
            "direction_consistent": dir_count >= GATE_MIN_FOLDS,
            "coefficient_consistent": coef_count >= GATE_MIN_FOLDS,
            "not_source_identifying": ident[feature] < IDENT_AUC_MAX,
            "non_constant_both_sources": not any(const_flags.values()),
        }
        row = {
            "feature": feature,
            "direction_folds": dir_count,
            "coefficient_folds": coef_count,
            "coefficient_sign": coef_sign,
            "identifiability_auc": ident[feature],
            "constant_in_source": {
                source: bool(const_flags[source]) for source in training_sources
            },
            "gates": gates,
            "passes_all_gates": all(gates.values()),
            "stability_score": dir_count + coef_count,
            "min_consistency": min(dir_count, coef_count),
            "selected": False,
            "fill": False,
        }
        gate_table.append(row)
        if row["passes_all_gates"]:
            selected.append(feature)
            row["selected"] = True

    fill_applied = False
    trim_applied = False
    if len(selected) < MIN_T_SIZE:
        fill_applied = True
        chosen = set(selected)
        remaining = sorted(
            (r for r in gate_table if r["feature"] not in chosen),
            key=lambda r: (-r["stability_score"], r["feature"]),
        )
        for row in remaining[: MIN_T_SIZE - len(selected)]:
            row["fill"] = True
            selected.append(row["feature"])
    elif len(selected) > MAX_T_SIZE:
        trim_applied = True
        passing = sorted(
            (r for r in gate_table if r["passes_all_gates"]),
            key=lambda r: (-r["min_consistency"], r["feature"]),
        )
        keep = {r["feature"] for r in passing[:MAX_T_SIZE]}
        for row in gate_table:
            if row["passes_all_gates"] and row["feature"] not in keep:
                row["selected"] = False
        selected = sorted(keep)

    selected = sorted(selected)
    return {
        "training_sources": training_sources,
        "gate_table": gate_table,
        "selected": selected,
        "n_passing_gates_untrimmed": sum(
            1 for r in gate_table if r["passes_all_gates"]
        ),
        "fill_applied": fill_applied,
        "trim_applied": trim_applied,
    }


# ---------------------------------------------------------------------------
# Scaler, C selection + OOF, calibration (training pool ONLY)
# ---------------------------------------------------------------------------


def fit_scaler(
    pool: pd.DataFrame, features: list[str], weighting: str
) -> StandardScaler:
    """Weighted StandardScaler fit on the training pool's rows only."""
    X = feature_matrix(pool, features)
    return StandardScaler().fit(X, sample_weight=training_weights(pool, weighting))


def select_C_and_oof(
    pool: pd.DataFrame,
    features: list[str],
    weighting: str,
) -> dict[str, Any]:
    """Frozen C selection + out-of-fold predictions on the training pool.

    GroupKFold(5) mean ROC-AUC inside the pool (tiebreak mean AP, then
    frozen grid order).  Returns the selected C, its OOF predictions
    (the calibration input), and the full CV table.  Takes ONLY the
    training pool: held-out rows cannot enter selection.
    """
    X = feature_matrix(pool, features)
    y = pool["recovery_success"].astype(int).to_numpy()
    weights = training_weights(pool, weighting)
    folds = group_folds(pool)
    cv_rows: list[dict[str, Any]] = []
    oof_by_c: dict[float, np.ndarray] = {}
    for c_value in C_GRID:
        oof = np.full(len(y), np.nan)
        fold_aucs: list[float] = []
        fold_aps: list[float] = []
        for tr, va in folds:
            if len(np.unique(y[va])) < 2:
                continue
            scaler = StandardScaler().fit(X.iloc[tr], sample_weight=weights[tr])
            est = make_lr(c_value)
            est.fit(scaler.transform(X.iloc[tr]), y[tr], sample_weight=weights[tr])
            prob = est.predict_proba(scaler.transform(X.iloc[va]))[:, 1]
            fold_aucs.append(float(roc_auc_score(y[va], prob)))
            fold_aps.append(float(average_precision_score(y[va], prob)))
            oof[va] = prob
        if not fold_aucs or np.isnan(oof).any():
            raise RuntimeError(
                f"no evaluable CV folds for C={c_value} (single-class folds)"
            )
        cv_rows.append(
            {
                "C": c_value,
                "mean_roc_auc": float(np.mean(fold_aucs)),
                "mean_ap": float(np.mean(fold_aps)),
                "n_folds_scored": len(fold_aucs),
            }
        )
        oof_by_c[c_value] = oof
    best = max(cv_rows, key=lambda r: (r["mean_roc_auc"], r["mean_ap"]))
    best_c = float(best["C"])
    return {
        "best_C": best_c,
        "cv_table": cv_rows,
        "oof_probs": oof_by_c[best_c],
        "n_pool_rows": int(len(y)),
        "n_pool_groups": int(pool["split_group"].astype(str).nunique()),
        "n_pool_positives": int(y.sum()),
    }


def fit_calibrator(
    oof_probs: np.ndarray,
    y_pool: np.ndarray,
    trigger: float = ECE_TRIGGER,
) -> dict[str, Any]:
    """Frozen calibration path: isotonic on OOF pool predictions iff
    OOF ECE(10 bin) > trigger.

    STRUCTURAL GUARANTEE: the signature accepts no held-out labels -- a
    calibrator cannot be fit on the held-out source in any calling
    pattern.
    """
    oof = np.asarray(oof_probs, dtype=float)
    y = np.asarray(y_pool, dtype=int)
    oof_ece = ece_score(oof, y)
    result: dict[str, Any] = {"oof_ece": oof_ece, "trigger": trigger, "applied": False}
    if oof_ece > trigger:
        iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        iso.fit(oof, y)
        result["applied"] = True
        result["isotonic"] = iso
    return result


def fit_arm(
    pool: pd.DataFrame,
    features: list[str],
    weighting: str,
) -> dict[str, Any]:
    """Frozen per-(cell, arm) fitting path on the training pool ONLY.

    Selection, scaling statistics, hyperparameter choice, final fit, and
    calibration all consume the pool; the returned artifact carries the
    fitted scaler/model/calibrator and provenance.
    """
    if pool.empty:
        raise RuntimeError("empty training pool")
    selection = select_C_and_oof(pool, features, weighting)
    scaler = fit_scaler(pool, features, weighting)
    X = feature_matrix(pool, features)
    y = pool["recovery_success"].astype(int).to_numpy()
    weights = training_weights(pool, weighting)
    model = make_lr(selection["best_C"])
    model.fit(scaler.transform(X), y, sample_weight=weights)
    calibration = fit_calibrator(selection["oof_probs"], y)
    return {
        "features": list(features),
        "weighting": weighting,
        "scaler": scaler,
        "model": model,
        "calibration": calibration,
        "selection": {
            "best_C": selection["best_C"],
            "cv_table": selection["cv_table"],
            "n_pool_rows": selection["n_pool_rows"],
            "n_pool_groups": selection["n_pool_groups"],
            "n_pool_positives": selection["n_pool_positives"],
        },
    }


def predict_arm(arm: dict[str, Any], frame: pd.DataFrame) -> dict[str, np.ndarray]:
    """Raw + calibrated probabilities for rows of any frame (single touch)."""
    X = feature_matrix(frame, arm["features"])
    p_raw = arm["model"].predict_proba(arm["scaler"].transform(X))[:, 1]
    if arm["calibration"]["applied"]:
        p_cal = np.asarray(arm["calibration"]["isotonic"].predict(p_raw), dtype=float)
    else:
        p_cal = p_raw.copy()
    return {"p_raw": p_raw, "p_cal": p_cal}


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def ece_score(probs: np.ndarray, y: np.ndarray, n_bins: int = ECE_BINS) -> float:
    """Equal-width 10-bin expected calibration error."""
    probs = np.asarray(probs, dtype=float)
    y = np.asarray(y, dtype=int)
    if len(y) == 0:
        return 0.0
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    bin_ids = np.clip(np.digitize(probs, edges[1:-1], right=False), 0, n_bins - 1)
    ece = 0.0
    for b in range(n_bins):
        mask = bin_ids == b
        n_b = int(mask.sum())
        if n_b == 0:
            continue
        ece += (n_b / len(y)) * abs(float(y[mask].mean()) - float(probs[mask].mean()))
    return float(ece)


def evaluate_probs(y_true: np.ndarray, probs: np.ndarray) -> dict[str, Any]:
    """Frozen per-cell metric block (fixed 0.5 threshold)."""
    y = np.asarray(y_true, dtype=int)
    p = np.asarray(probs, dtype=float)
    n = int(len(y))
    n_pos = int(y.sum())
    pred = (p >= FIXED_THRESHOLD).astype(int)
    tn, fp, fn, tp = (
        (int(v) for v in confusion_matrix(y, pred, labels=[0, 1]).ravel())
        if n
        else (0, 0, 0, 0)
    )
    metrics: dict[str, Any] = {
        "n_test_rows": n,
        "n_test_positives": n_pos,
        "n_test_negatives": n - n_pos,
        "class_balance": float(n_pos / n) if n else None,
        "roc_auc": None,
        "ap": None,
        "brier": float(brier_score_loss(y, p)) if n else None,
        "ece": ece_score(p, y),
        "balanced_accuracy": float(balanced_accuracy_score(y, pred)) if n else None,
        "precision": float(precision_score(y, pred, zero_division=0)) if n else None,
        "recall": float(recall_score(y, pred, zero_division=0)) if n else None,
        "f1": float(f1_score(y, pred, zero_division=0)) if n else None,
        "threshold": FIXED_THRESHOLD,
        "confusion_matrix": {"tn": tn, "fp": fp, "fn": fn, "tp": tp},
    }
    if 0 < n_pos < n:
        metrics["roc_auc"] = float(roc_auc_score(y, p))
        metrics["ap"] = float(average_precision_score(y, p))
    return metrics


# ---------------------------------------------------------------------------
# One cell arm: fit on pool -> single held-out evaluation
# ---------------------------------------------------------------------------


def run_arm(
    pool: pd.DataFrame,
    held_out: pd.DataFrame,
    features: list[str],
    weighting: str,
) -> dict[str, Any]:
    """Fit on the training pool, then test ONCE on the held-out source.

    ``fit_arm`` receives only ``pool``; ``held_out`` is touched first in
    ``predict_arm``/``evaluate_probs`` below -- after every fitted
    quantity (T set, scaler, C, model, calibrator) is already frozen.
    """
    arm = fit_arm(pool, features, weighting)
    y_te = held_out["recovery_success"].astype(int).to_numpy()
    probs = predict_arm(arm, held_out)
    metrics = evaluate_probs(y_te, probs["p_raw"])
    calibrated = evaluate_probs(y_te, probs["p_cal"])
    metrics["brier_after_calibration"] = calibrated["brier"]
    metrics["ece_after_calibration"] = calibrated["ece"]
    return {
        "features": arm["features"],
        "weighting": weighting,
        "scaler": arm["scaler"],
        "model": arm["model"],
        "selection": arm["selection"],
        "oof_ece": arm["calibration"]["oof_ece"],
        "calibration_applied": bool(arm["calibration"]["applied"]),
        "metrics": metrics,
        "predictions": {
            "episode_id": held_out["episode_id"].astype(str).tolist(),
            "parent_id": held_out["parent_id"].astype(str).tolist(),
            "split_group": held_out["split_group"].astype(str).tolist(),
            "dataset": held_out["dataset"].astype(str).tolist(),
            "y": y_te.astype(int).tolist(),
            "p_raw": [float(v) for v in probs["p_raw"]],
            "p_calibrated": [float(v) for v in probs["p_cal"]],
        },
    }


# ---------------------------------------------------------------------------
# Acceptance rules (pure; hand-fixture-tested)
# ---------------------------------------------------------------------------


def evaluate_acceptance(
    cell_deltas: dict[str, float | None],
    sensitivity_delta: float | None,
    identity_clean: bool,
    min_delta: float = MACRO_MIN_DELTA,
    degradation_guard: float = CELL_DEGRADATION_GUARD,
    min_cells: int = MIN_CELLS,
) -> dict[str, Any]:
    """FROZEN primary_T_earned rule, mechanically applied.

    ``cell_deltas``: held-out-cell T-minus-M test ROC-AUC (raw).
    Earned iff EVERY condition holds:
      (1) macro delta >= +min_delta;
      (2) T >= M in >= min_cells cells;
      (3) no cell with T < M - degradation_guard;
      (4) parent-only sensitivity preserves the macro direction
          (sensitivity delta > 0, matching the positive primary macro
          delta required by (1));
      (5) schema audit: no identity column in any primary arm.
    """
    scored = [v for v in cell_deltas.values() if v is not None]
    macro_delta = float(np.mean(scored)) if scored else None
    t_ge_m = {cell: (v is not None and v >= 0) for cell, v in cell_deltas.items()}
    n_held = sum(1 for v in t_ge_m.values() if v)
    worst = min(scored) if scored else None
    conditions = {
        "macro_delta_at_least_min": (
            macro_delta is not None and macro_delta >= min_delta
        ),
        "t_ge_m_in_enough_cells": n_held >= min_cells,
        "no_cell_below_degradation_guard": (
            worst is not None and worst >= -degradation_guard
        ),
        "sensitivity_preserves_direction": (
            sensitivity_delta is not None and sensitivity_delta > 0
        ),
        "no_identity_in_primary_arms": bool(identity_clean),
    }
    return {
        "earned": all(conditions.values()),
        "conditions": conditions,
        "macro_delta": macro_delta,
        "cell_deltas": dict(cell_deltas),
        "t_ge_m_per_cell": t_ge_m,
        "cells_held": n_held,
        "worst_cell_delta": worst,
        "sensitivity_delta": sensitivity_delta,
        "min_delta": min_delta,
        "degradation_guard": degradation_guard,
        "min_cells": min_cells,
    }


def evaluate_secondary(
    cell_deltas: dict[str, float | None],
    min_delta: float = MACRO_MIN_DELTA,
    min_cells: int = MIN_CELLS,
) -> dict[str, Any]:
    """FROZEN secondary T-vs-F rule (macro delta and per-cell direction)."""
    scored = [v for v in cell_deltas.values() if v is not None]
    macro_delta = float(np.mean(scored)) if scored else None
    t_ge_f = {cell: (v is not None and v >= 0) for cell, v in cell_deltas.items()}
    n_held = sum(1 for v in t_ge_f.values() if v)
    conditions = {
        "macro_delta_at_least_min": (
            macro_delta is not None and macro_delta >= min_delta
        ),
        "t_ge_f_in_enough_cells": n_held >= min_cells,
    }
    return {
        "earned": all(conditions.values()),
        "conditions": conditions,
        "macro_delta": macro_delta,
        "cell_deltas": dict(cell_deltas),
        "t_ge_f_per_cell": t_ge_f,
        "cells_held": n_held,
    }


def classify_outcome(
    primary_earned: bool,
    cells_materially_above_chance: int,
    total_cells: int = len(CELLS),
    min_cells: int = MIN_CELLS,
    material_margin: float = MATERIAL_AUC_MARGIN,
) -> str:
    """Frozen SETTLED_earned / PARTIAL / NOT_EARNED mapping.

    PARTIAL when the primary gate is not met but a primary
    representation clears the class-prior baseline materially
    (ROC-AUC >= 0.5 + material_margin) in most cells (>= min_cells).
    BLOCKED is reserved for an unconstructible evaluation and is never
    returned by a completed run.
    """
    if primary_earned:
        return "SETTLED_earned"
    if cells_materially_above_chance >= min_cells:
        return "PARTIAL"
    _ = total_cells
    return "NOT_EARNED"


# ---------------------------------------------------------------------------
# Error analysis (T arm, primary weighting)
# ---------------------------------------------------------------------------

ERROR_ANALYSIS_TOP_K = 5
ERROR_ANALYSIS_PER_QUADRANT = 3
QUADRANTS: tuple[str, ...] = ("TP", "TN", "FP", "FN")


def _quadrant_episodes(
    y: np.ndarray, p: np.ndarray, episode_ids: list[str]
) -> dict[str, list[int]]:
    """3 episodes per quadrant by error-side confidence (deterministic)."""
    pred = (p >= FIXED_THRESHOLD).astype(int)
    error_conf = np.where(pred == 1, p, 1.0 - p)
    buckets: dict[str, list[int]] = {}
    targets: dict[str, tuple[int, int]] = {
        "TP": (1, 1),
        "TN": (0, 0),
        "FP": (0, 1),
        "FN": (1, 0),
    }
    for quadrant in QUADRANTS:
        want_y, want_pred = targets[quadrant]
        mask = np.flatnonzero((y == want_y) & (pred == want_pred))
        order = sorted(mask, key=lambda i: (-error_conf[i], episode_ids[i]))
        buckets[quadrant] = order[:ERROR_ANALYSIS_PER_QUADRANT]
    return buckets


def error_analysis_for_cell(
    pool: pd.DataFrame,
    held_out: pd.DataFrame,
    arm: dict[str, Any],
) -> dict[str, Any]:
    """TP/TN/FP/FN exemplars (T arm) with feature-z evidence.

    For each exemplar: the top features by |coef x z_pool| contribution,
    the episode's standardized value under the training-pool scaler
    (``z_pool``) and under a scaler fit on the held-out source only
    (``z_source``), the raw value, and the source's raw mean -- the
    context needed to distinguish feature-scaling from representation /
    label / dynamics causes.  Tentative per-quadrant cause hypotheses
    use the transparent priority recorded in ``cause_rule``; they are
    heuristic annotations, never settlement evidence.
    """
    features = arm["features"]
    scaler_pool: StandardScaler = arm["scaler"]
    coefs = np.asarray(arm["model"].coef_[0], dtype=float)

    X_held = feature_matrix(held_out, features)
    z_pool = scaler_pool.transform(X_held)
    z_source = StandardScaler().fit(X_held).transform(X_held)
    source_means = X_held.mean()
    X_pool = feature_matrix(pool, features)
    pool_min = X_pool.min()
    pool_max = X_pool.max()

    preds = arm["predictions"]
    y = np.asarray(preds["y"], dtype=int)
    p = np.asarray(preds["p_raw"], dtype=float)
    episode_ids = preds["episode_id"]
    buckets = _quadrant_episodes(y, p, episode_ids)

    pool_pos_rate = float(np.mean(pool["recovery_success"].astype(int).to_numpy()))
    held_pos_rate = float(np.mean(y))

    quadrants: dict[str, Any] = {}
    for quadrant in QUADRANTS:
        exemplars: list[dict[str, Any]] = []
        divergent: list[float] = []
        outside: list[float] = []
        for index in buckets[quadrant]:
            contributions = np.abs(coefs * z_pool[index])
            top = sorted(
                np.argsort(-contributions, kind="stable")[:ERROR_ANALYSIS_TOP_K],
                key=lambda j: (-contributions[j], features[j]),
            )
            snippet: list[dict[str, Any]] = []
            for j in top:
                name = features[j]
                z_p = float(z_pool[index, j])
                z_s = float(z_source[index, j])
                raw = float(X_held.iloc[index, j])
                divergent.append(abs(z_p - z_s))
                outside.append(
                    1.0 if (raw < float(pool_min.iloc[j]) or raw > float(pool_max.iloc[j])) else 0.0
                )
                snippet.append(
                    {
                        "feature": name,
                        "coef": float(coefs[j]),
                        "z_pool": z_p,
                        "z_source": z_s,
                        "abs_contribution": float(contributions[j]),
                        "raw_value": raw,
                        "heldout_source_mean": float(source_means.iloc[j]),
                    }
                )
            exemplars.append(
                {
                    "episode_id": episode_ids[index],
                    "parent_id": preds["parent_id"][index],
                    "split_group": preds["split_group"][index],
                    "dataset": preds["dataset"][index],
                    "y": int(y[index]),
                    "p_raw": float(p[index]),
                    "top_features": snippet,
                }
            )
        n_flags = len(divergent)
        scaling_share = (
            sum(1 for d in divergent if d >= 1.0) / n_flags if n_flags else 0.0
        )
        range_share = sum(outside) / n_flags if n_flags else 0.0
        if scaling_share >= 0.5:
            cause = "feature_scaling"
            rationale = (
                f"{scaling_share:.0%} of top-feature readings diverge >= 1.0 "
                "between pool-scaled and source-scaled z"
            )
        elif range_share >= 0.5:
            cause = "representation_mismatch"
            rationale = (
                f"{range_share:.0%} of top-feature readings fall outside the "
                "training pool's raw range"
            )
        elif abs(held_pos_rate - pool_pos_rate) >= 0.15:
            cause = "label_semantics"
            rationale = (
                f"held-out positive rate {held_pos_rate:.3f} vs pool "
                f"{pool_pos_rate:.3f} (>= 0.15 divergence)"
            )
        else:
            cause = "genuinely_different_recovery_dynamics"
            rationale = (
                "no scaling/range/label-prior flag; residual hypothesis "
                "(adapter-semantics and environment-policy causes are not "
                "mechanically separable from this evidence surface)"
            )
        quadrants[quadrant] = {
            "n_available": len(buckets[quadrant]),
            "exemplars": exemplars,
            "tentative_cause": cause,
            "cause_rationale": rationale,
            "diagnostics": {
                "share_top_feature_z_divergence_ge_1": scaling_share,
                "share_top_feature_outside_train_range": range_share,
            },
        }
    return {
        "arm": "T",
        "weighting": WEIGHTING_BALANCED,
        "top_k": ERROR_ANALYSIS_TOP_K,
        "per_quadrant": ERROR_ANALYSIS_PER_QUADRANT,
        "pool_positive_rate": pool_pos_rate,
        "heldout_positive_rate": held_pos_rate,
        "cause_rule": (
            "tentative heuristic, priority: feature_scaling (>= half of "
            "top-feature readings with |z_pool - z_source| >= 1) > "
            "representation_mismatch (>= half of top-feature readings "
            "outside the pool's raw range) > label_semantics (|held-out "
            "positive rate - pool positive rate| >= 0.15) > "
            "genuinely_different_recovery_dynamics; annotations are "
            "evidence-cited heuristics, never settlement claims"
        ),
        "quadrants": quadrants,
    }


# ---------------------------------------------------------------------------
# Matrix orchestration
# ---------------------------------------------------------------------------

ARM_SPECS: tuple[dict[str, str], ...] = (
    {"key": "M", "arm": "M", "variant": "primary", "weighting": WEIGHTING_BALANCED},
    {"key": "F", "arm": "F", "variant": "primary", "weighting": WEIGHTING_BALANCED},
    {"key": "T", "arm": "T", "variant": "primary", "weighting": WEIGHTING_BALANCED},
    {
        "key": "F_id",
        "arm": "F_id",
        "variant": "diagnostic",
        "weighting": WEIGHTING_BALANCED,
    },
    {
        "key": "T_id",
        "arm": "T_id",
        "variant": "diagnostic",
        "weighting": WEIGHTING_BALANCED,
    },
    {
        "key": "M_parent_only",
        "arm": "M",
        "variant": "sensitivity",
        "weighting": WEIGHTING_PARENT_ONLY,
    },
    {
        "key": "T_parent_only",
        "arm": "T",
        "variant": "sensitivity",
        "weighting": WEIGHTING_PARENT_ONLY,
    },
)


def run_cell(frame: pd.DataFrame, held_out_source: str) -> dict[str, Any]:
    """One LOSO cell: T derivation on the pool + the 7 arm runs."""
    pool = frame[frame["dataset"] != held_out_source]
    held_out = frame[frame["dataset"] == held_out_source]
    if pool.empty or held_out.empty:
        raise RuntimeError(f"cell {held_out_source}: empty pool or held-out frame")

    t_selection = derive_t_selection(pool)
    t_features = t_selection["selected"]

    arms: dict[str, Any] = {}
    for spec in ARM_SPECS:
        features = resolve_arm_features(spec["arm"], t_features)
        block = run_arm(pool, held_out, features, spec["weighting"])
        block["variant"] = spec["variant"]
        block["arm"] = spec["arm"]
        arms[spec["key"]] = block

    error_analysis = error_analysis_for_cell(pool, held_out, arms["T"])

    return {
        "held_out_source": held_out_source,
        "pool_sources": sorted(str(s) for s in pool["dataset"].astype(str).unique()),
        "n_pool_rows": int(len(pool)),
        "n_pool_split_groups": int(pool["split_group"].astype(str).nunique()),
        "n_pool_positives": int(pool["recovery_success"].astype(int).sum()),
        "n_heldout_rows": int(len(held_out)),
        "n_heldout_positives": int(held_out["recovery_success"].astype(int).sum()),
        "t_selection": t_selection,
        "t_features": t_features,
        "arms": arms,
        "error_analysis": error_analysis,
    }


def macro_over_cells(cells: dict[str, dict[str, Any]], arm_key: str) -> dict[str, Any]:
    """Unweighted mean over cells of the arm's ROC-AUC and AP."""
    aucs = [
        cells[c]["arms"][arm_key]["metrics"]["roc_auc"]
        for c in CELLS
        if cells[c]["arms"][arm_key]["metrics"]["roc_auc"] is not None
    ]
    aps = [
        cells[c]["arms"][arm_key]["metrics"]["ap"]
        for c in CELLS
        if cells[c]["arms"][arm_key]["metrics"]["ap"] is not None
    ]
    return {
        "roc_auc": float(np.mean(aucs)) if len(aucs) == len(CELLS) else None,
        "ap": float(np.mean(aps)) if len(aps) == len(CELLS) else None,
        "n_cells_scored": len(aucs),
    }


def pooled_over_cells(cells: dict[str, dict[str, Any]], arm_key: str) -> dict[str, Any]:
    """Pooled predictions across the three cells (secondary context only)."""
    y_all: list[int] = []
    p_all: list[float] = []
    for cell in CELLS:
        preds = cells[cell]["arms"][arm_key]["predictions"]
        y_all.extend(preds["y"])
        p_all.extend(preds["p_raw"])
    y = np.asarray(y_all, dtype=int)
    p = np.asarray(p_all, dtype=float)
    metrics = evaluate_probs(y, p)
    return {
        "roc_auc": metrics["roc_auc"],
        "ap": metrics["ap"],
        "brier": metrics["brier"],
        "ece": metrics["ece"],
        "n_rows": int(len(y)),
        "note": "secondary context only; never an adoption criterion",
    }


def _cell_deltas(
    cells: dict[str, dict[str, Any]], treatment: str, baseline: str
) -> dict[str, float | None]:
    out: dict[str, float | None] = {}
    for cell in CELLS:
        t_auc = cells[cell]["arms"][treatment]["metrics"]["roc_auc"]
        b_auc = cells[cell]["arms"][baseline]["metrics"]["roc_auc"]
        out[cell] = (
            float(t_auc) - float(b_auc)
            if t_auc is not None and b_auc is not None
            else None
        )
    return out


def evaluate_full_acceptance(cells: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Mechanical frozen acceptance over the completed matrix."""
    identity_clean = True
    for cell in CELLS:
        for arm_key in PRIMARY_ARM_KEYS:
            features = cells[cell]["arms"][arm_key]["features"]
            if IDENTITY_FEATURE in features or any(
                f in NON_FEATURE_COLUMNS for f in features
            ):
                identity_clean = False

    primary_deltas = _cell_deltas(cells, "T", "M")
    sens_deltas = _cell_deltas(cells, "T_parent_only", "M_parent_only")
    scored_sens = [v for v in sens_deltas.values() if v is not None]
    sens_macro = float(np.mean(scored_sens)) if scored_sens else None
    primary = evaluate_acceptance(
        primary_deltas, sens_macro, identity_clean=identity_clean
    )

    secondary_deltas = _cell_deltas(cells, "T", "F")
    secondary = evaluate_secondary(secondary_deltas)

    f_vs_m = _cell_deltas(cells, "F", "M")
    scored_f = [v for v in f_vs_m.values() if v is not None]

    overlap: dict[str, Any] = {}
    for i, a in enumerate(CELLS):
        for b in CELLS[i + 1 :]:
            set_a = set(cells[a]["t_features"])
            set_b = set(cells[b]["t_features"])
            intersection = sorted(set_a & set_b)
            union = sorted(set_a | set_b)
            overlap[f"{a}|{b}"] = {
                "intersection": intersection,
                "n_intersection": len(intersection),
                "n_union": len(union),
                "jaccard": len(intersection) / len(union) if union else None,
            }
    all_three = sorted(
        set(cells[CELLS[0]]["t_features"])
        & set(cells[CELLS[1]]["t_features"])
        & set(cells[CELLS[2]]["t_features"])
    )

    materially_above = 0
    for cell in CELLS:
        aucs = [
            cells[cell]["arms"][key]["metrics"]["roc_auc"] for key in PRIMARY_ARM_KEYS
        ]
        if any(
            auc is not None and auc >= 0.5 + MATERIAL_AUC_MARGIN for auc in aucs
        ):
            materially_above += 1
    classification = classify_outcome(primary["earned"], materially_above)

    return {
        "primary_T_earned": primary,
        "secondary_T_vs_F": secondary,
        "descriptive": {
            "F_vs_M_macro_delta": float(np.mean(scored_f)) if scored_f else None,
            "F_vs_M_cell_deltas": f_vs_m,
            "t_set_pairwise_overlap": overlap,
            "t_set_common_to_all_cells": all_three,
            "t_set_sizes": {c: len(cells[c]["t_features"]) for c in CELLS},
        },
        "classification": classification,
        "classification_mapping": {
            "SETTLED_earned": "primary_T_earned fully met",
            "PARTIAL": (
                "recovery signal persists held-out (T and/or F materially "
                "above chance in most cells) but the frozen T-gate is not "
                "fully met"
            ),
            "NOT_EARNED": (
                "no representation demonstrates held-out transfer above the "
                "degradation-guarded bar"
            ),
            "BLOCKED": "trustworthy transfer evaluation could not be completed",
        },
    }


# ---------------------------------------------------------------------------
# Artifact construction (deterministic; no wall-clock fields)
# ---------------------------------------------------------------------------


def build_matrix(frame: pd.DataFrame) -> dict[str, Any]:
    """Run the full frozen matrix once; return cells + summary blocks."""
    per_source = {
        source: {
            "rows": int((frame["dataset"] == source).sum()),
            "positives": int(
                frame.loc[frame["dataset"] == source, "recovery_success"]
                .astype(int)
                .sum()
            ),
            "split_groups": int(
                frame.loc[frame["dataset"] == source, "split_group"]
                .astype(str)
                .nunique()
            ),
            "parents": int(
                frame.loc[frame["dataset"] == source, "parent_id"]
                .astype(str)
                .nunique()
            ),
        }
        for source in SOURCES
    }
    cells: dict[str, dict[str, Any]] = {
        held_out: run_cell(frame, held_out) for held_out in CELLS
    }
    macro = {arm_key: macro_over_cells(cells, arm_key) for arm_key in ALL_ARM_KEYS}
    pooled = {arm_key: pooled_over_cells(cells, arm_key) for arm_key in ALL_ARM_KEYS}
    acceptance = evaluate_full_acceptance(cells)
    return {
        "cells": cells,
        "macro": macro,
        "pooled": pooled,
        "acceptance": acceptance,
        "per_source": per_source,
    }


def serialize_artifacts(matrix: dict[str, Any], table_sha: str) -> dict[str, bytes]:
    """Serialize the six data artifacts to bytes (fully deterministic)."""
    cells: dict[str, dict[str, Any]] = matrix["cells"]
    macro: dict[str, Any] = matrix["macro"]
    acceptance: dict[str, Any] = matrix["acceptance"]

    # ---- results.json ------------------------------------------------------
    results_payload: dict[str, Any] = {
        "preregistration_id": "v008-r1-transfer",
        "episode_table_sha256": table_sha,
        "point": POINT,
        "representations": {
            "M": list(M_FEATURES),
            "F": list(F_FEATURES),
            "T_by_cell": {c: cells[c]["t_features"] for c in CELLS},
        },
        "per_source_composition": matrix["per_source"],
        "cells": {
            cell: {
                "held_out_source": cells[cell]["held_out_source"],
                "pool_sources": cells[cell]["pool_sources"],
                "n_pool_rows": cells[cell]["n_pool_rows"],
                "n_pool_split_groups": cells[cell]["n_pool_split_groups"],
                "n_pool_positives": cells[cell]["n_pool_positives"],
                "n_heldout_rows": cells[cell]["n_heldout_rows"],
                "n_heldout_positives": cells[cell]["n_heldout_positives"],
                "t_features": cells[cell]["t_features"],
                "arms": {
                    key: {
                        "arm": block["arm"],
                        "variant": block["variant"],
                        "weighting": block["weighting"],
                        "n_features": len(block["features"]),
                        "features": block["features"],
                        "best_C": block["selection"]["best_C"],
                        "cv_table": block["selection"]["cv_table"],
                        "n_pool_rows": block["selection"]["n_pool_rows"],
                        "n_pool_groups": block["selection"]["n_pool_groups"],
                        "oof_ece": block["oof_ece"],
                        "calibration_applied": block["calibration_applied"],
                        "metrics": block["metrics"],
                    }
                    for key, block in cells[cell]["arms"].items()
                },
            }
            for cell in CELLS
        },
        "macro": macro,
        "pooled": matrix["pooled"],
        "acceptance": acceptance,
        "seeds": {
            "random_state": SEED,
            "n_cv_splits": N_SPLITS,
            "c_grid": list(C_GRID),
            "ece_trigger": ECE_TRIGGER,
        },
    }

    # ---- per_cell_results.csv ---------------------------------------------
    csv_rows: list[dict[str, Any]] = []
    for cell in CELLS:
        for key, block in cells[cell]["arms"].items():
            m = block["metrics"]
            csv_rows.append(
                {
                    "cell": cell,
                    "arm_key": key,
                    "arm": block["arm"],
                    "variant": block["variant"],
                    "weighting": block["weighting"],
                    "n_features": len(block["features"]),
                    "best_C": block["selection"]["best_C"],
                    "oof_ece": block["oof_ece"],
                    "calibration_applied": block["calibration_applied"],
                    "roc_auc": m["roc_auc"],
                    "ap": m["ap"],
                    "brier": m["brier"],
                    "ece": m["ece"],
                    "balanced_accuracy": m["balanced_accuracy"],
                    "precision": m["precision"],
                    "recall": m["recall"],
                    "f1": m["f1"],
                    "tn": m["confusion_matrix"]["tn"],
                    "fp": m["confusion_matrix"]["fp"],
                    "fn": m["confusion_matrix"]["fn"],
                    "tp": m["confusion_matrix"]["tp"],
                    "brier_after_calibration": m["brier_after_calibration"],
                    "ece_after_calibration": m["ece_after_calibration"],
                    "macro_roc_auc": macro[key]["roc_auc"],
                }
            )
    csv_bytes = pd.DataFrame(csv_rows).to_csv(index=False).encode("utf-8")

    # ---- test_predictions.jsonl -------------------------------------------
    pred_lines: list[str] = []
    for cell in CELLS:
        for key in ALL_ARM_KEYS:
            block = cells[cell]["arms"][key]
            preds = block["predictions"]
            for i, eid in enumerate(preds["episode_id"]):
                pred_lines.append(
                    json.dumps(
                        {
                            "cell": cell,
                            "arm": block["arm"],
                            "arm_key": key,
                            "variant": block["variant"],
                            "weighting": block["weighting"],
                            "episode_id": eid,
                            "parent_id": preds["parent_id"][i],
                            "split_group": preds["split_group"][i],
                            "dataset": preds["dataset"][i],
                            "y": preds["y"][i],
                            "p_raw": preds["p_raw"][i],
                            "p_calibrated": preds["p_calibrated"][i],
                        },
                        sort_keys=True,
                    )
                )
    predictions_bytes = ("\n".join(pred_lines) + "\n").encode("utf-8")

    # ---- t_selection.json ---------------------------------------------------
    t_selection_payload = {
        "rule": (
            "FROZEN prereg section 4: GroupKFold(5) over the training pool's "
            "split_group; per fold weighted-LR coefficient sign (frozen LR "
            "spec, C=1.0) and per-source univariate AUC sign; gates: "
            "direction consistent across BOTH sources in >= 4/5 folds, "
            "coefficient sign consistent in >= 4/5 folds, worst-case "
            "one-vs-rest source-identifiability AUC < 0.85, non-constant in "
            "both training sources; fill to 5 by stability score (ties "
            "lexicographic), trim to 20 by min(direction, coefficient) folds"
        ),
        "cells": {
            cell: {
                "training_sources": cells[cell]["t_selection"]["training_sources"],
                "selected": cells[cell]["t_selection"]["selected"],
                "n_passing_gates_untrimmed": cells[cell]["t_selection"][
                    "n_passing_gates_untrimmed"
                ],
                "fill_applied": cells[cell]["t_selection"]["fill_applied"],
                "trim_applied": cells[cell]["t_selection"]["trim_applied"],
                "gate_table": cells[cell]["t_selection"]["gate_table"],
            }
            for cell in CELLS
        },
        "pairwise_overlap": acceptance["descriptive"]["t_set_pairwise_overlap"],
        "common_to_all_cells": acceptance["descriptive"][
            "t_set_common_to_all_cells"
        ],
    }

    # ---- calibration_summary.json ------------------------------------------
    calibration_rows: dict[str, Any] = {}
    for cell in CELLS:
        for key, block in cells[cell]["arms"].items():
            m = block["metrics"]
            calibration_rows[f"{cell}|{key}"] = {
                "cell": cell,
                "arm": block["arm"],
                "variant": block["variant"],
                "weighting": block["weighting"],
                "best_C": block["selection"]["best_C"],
                "oof_ece": block["oof_ece"],
                "trigger": ECE_TRIGGER,
                "applied": block["calibration_applied"],
                "test_brier_raw": m["brier"],
                "test_brier_calibrated": m["brier_after_calibration"],
                "test_ece_raw": m["ece"],
                "test_ece_calibrated": m["ece_after_calibration"],
            }
    applied = [v for v in calibration_rows.values() if v["applied"]]
    calibration_payload = {
        "rule": (
            "isotonic on the selection folds' out-of-fold training-pool "
            "predictions iff selected-model OOF ECE(10 bin) > 0.05; applied "
            "to the held-out source; never fit on it"
        ),
        "trigger": ECE_TRIGGER,
        "n_arm_cells": len(calibration_rows),
        "n_triggered": len(applied),
        "cells": calibration_rows,
    }

    # ---- error_analysis.json ------------------------------------------------
    error_payload = {
        "note": (
            "T arm, primary weighting; 3 TP / 3 TN / 3 FP / 3 FN per cell "
            "by prediction confidence; z_pool uses the training-pool "
            "scaler, z_source a scaler fit on the held-out source only; "
            "tentative causes are heuristic annotations"
        ),
        "cells": {cell: cells[cell]["error_analysis"] for cell in CELLS},
    }

    return {
        "results.json": _json_bytes(results_payload),
        "per_cell_results.csv": csv_bytes,
        "test_predictions.jsonl": predictions_bytes,
        "t_selection.json": _json_bytes(t_selection_payload),
        "calibration_summary.json": _json_bytes(calibration_payload),
        "error_analysis.json": _json_bytes(error_payload),
    }


# ---------------------------------------------------------------------------
# Entry point: run twice, assert byte-identical, persist
# ---------------------------------------------------------------------------


def run_matrix(
    episode_table: Path = EPISODE_TABLE,
    results_root: Path = RESULTS_ROOT,
    log: bool = True,
) -> dict[str, Any]:
    """Execute the frozen matrix TWICE, assert byte-identical artifacts,
    persist them, and write the experiment manifest."""
    t_start = time.time()
    frame, table_sha = load_r1_frame(episode_table)
    n_positives = int(frame["recovery_success"].astype(int).sum())
    if log:
        print(
            f"loaded episode table: {len(frame)} {POINT} rows, "
            f"{n_positives} positives, sha256={table_sha[:12]}...",
            flush=True,
        )

    prereg_sha = _sha256_file(PREREG_PATH)
    head_commit = git_head_commit()

    if log:
        print("matrix run 1/2 ...", flush=True)
    first = build_matrix(frame)
    artifacts = serialize_artifacts(first, table_sha)
    if log:
        print("matrix run 2/2 ...", flush=True)
    second = serialize_artifacts(build_matrix(frame), table_sha)

    md5s = {name: _md5_bytes(artifacts[name]) for name in ARTIFACT_NAMES}
    identical = all(artifacts[name] == second[name] for name in ARTIFACT_NAMES)
    if not identical:
        differing = [name for name in ARTIFACT_NAMES if artifacts[name] != second[name]]
        raise RuntimeError(
            f"determinism failure: artifacts differ between runs: {differing}"
        )

    # ---- experiment_manifest.json (deterministic; no wall-clock fields) ----
    cells = first["cells"]
    manifest = {
        "plan": "godspeed-agent-v008-r1-transfer",
        "task": "V3",
        "round_label": "v008-round1",
        "preregistration_id": "v008-r1-transfer",
        "preregistration": {
            "path": str(PREREG_PATH),
            "sha256": prereg_sha,
            "frozen_at": "2026-09-15",
            "git_head_commit": head_commit,
        },
        "episode_table": {
            "path": str(episode_table),
            "sha256": table_sha,
            "rows_used": int(len(frame)),
            "point": POINT,
            "positives": int(frame["recovery_success"].astype(int).sum()),
        },
        "weights_definition": {
            WEIGHTING_BALANCED: (
                "parent-balanced x source-balanced: each training source "
                "equal total weight; within a source each parent equal "
                "(1/(training episodes of that parent), normalized per "
                "source); implemented as sample_weight, fit only"
            ),
            WEIGHTING_PARENT_ONLY: (
                "parent-balanced only (v007 "
                "parent_balanced_training_weights); preregistered "
                "sensitivity"
            ),
        },
        "scaler_provenance": (
            "StandardScaler fit on the training pool's rows (weighted), "
            "applied to all splits of that cell; held-out statistics never "
            "enter any fitted quantity"
        ),
        "calibration_provenance": (
            "isotonic on the selection folds' OOF training-pool predictions "
            "iff selected-model OOF ECE > 0.05; never fit on the held-out "
            "source"
        ),
        "operationalizations": {
            "direction_consistency": (
                "a fold counts only when both training sources' univariate "
                "AUC signs are defined (both classes present, AUC != 0.5) "
                "and equal"
            ),
            "coefficient_consistency": (
                "majority sign's fold fraction; exactly-zero coefficients "
                "count for neither sign"
            ),
            "identifiability": (
                "per feature, once per pool: unweighted pool scaler, frozen "
                "LR spec per GroupKFold(5) fold predicting the source from "
                "the single standardized feature; statistic = max over "
                "folds of max(AUC_s0, 1 - AUC_s0); gate < 0.85"
            ),
            "non_constancy": (
                "pool-level per training source (std > 0 required in both)"
            ),
            "size_rules": (
                "fill to 5 by stability score = direction folds + "
                "coefficient folds (ties lexicographic); trim to 20 by "
                "min(direction, coefficient) folds (ties lexicographic)"
            ),
            "headline_probability": (
                "headline metrics use RAW probabilities; calibration moves "
                "Brier/ECE only (isotonic is monotone)"
            ),
            "acceptance_sensitivity_direction": (
                "sensitivity preserves direction iff the parent-only macro "
                "T-minus-M delta is > 0, matching the positive primary "
                "macro delta required by condition (1)"
            ),
            "classification": (
                "PARTIAL uses the v007 materiality margin: a primary arm "
                "materially above chance at ROC-AUC >= 0.55 in >= 2 of 3 "
                "cells"
            ),
        },
        "seeds": {
            "random_state": SEED,
            "n_cv_splits": N_SPLITS,
            "c_grid": list(C_GRID),
        },
        "determinism": {
            "runs": 2,
            "byte_identical": identical,
            "artifact_md5": md5s,
            "note": (
                "no wall-clock fields in any artifact by design; runtime is "
                "printed to stdout only"
            ),
        },
        "t_selection_by_cell": {
            cell: {
                "training_sources": cells[cell]["t_selection"]["training_sources"],
                "selected": cells[cell]["t_features"],
                "n_passing_gates_untrimmed": cells[cell]["t_selection"][
                    "n_passing_gates_untrimmed"
                ],
                "fill_applied": cells[cell]["t_selection"]["fill_applied"],
                "trim_applied": cells[cell]["t_selection"]["trim_applied"],
                "gate_table": [
                    {
                        "feature": row["feature"],
                        "direction_folds": row["direction_folds"],
                        "coefficient_folds": row["coefficient_folds"],
                        "coefficient_sign": row["coefficient_sign"],
                        "identifiability_auc": row["identifiability_auc"],
                        "constant_in_source": row["constant_in_source"],
                        "passes_all_gates": row["passes_all_gates"],
                        "selected": row["selected"],
                        "fill": row["fill"],
                    }
                    for row in cells[cell]["t_selection"]["gate_table"]
                ],
            }
            for cell in CELLS
        },
        "versions": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "scikit-learn": sklearn.__version__,
            "pandas": pd.__version__,
            "numpy": np.__version__,
        },
    }

    all_artifacts = dict(artifacts)
    all_artifacts["experiment_manifest.json"] = _json_bytes(manifest)

    results_root.mkdir(parents=True, exist_ok=True)
    for name, payload in all_artifacts.items():
        (results_root / name).write_bytes(payload)

    if log:
        print("\n=== HEADLINE (per-cell test ROC-AUC, raw probs, primary arms) ===")
        for cell in CELLS:
            row = [
                f"{arm}={cells[cell]['arms'][arm]['metrics']['roc_auc']:.4f}"
                for arm in PRIMARY_ARM_KEYS
            ]
            print(f"  held_out={cell}: " + "  ".join(row))
        for arm in PRIMARY_ARM_KEYS:
            print(f"  macro {arm}: {first['macro'][arm]['roc_auc']:.4f}")
        print("\n=== FROZEN ACCEPTANCE ===")
        print(
            "primary_T_earned:",
            first["acceptance"]["primary_T_earned"]["earned"],
        )
        print(
            "secondary_T_vs_F:",
            first["acceptance"]["secondary_T_vs_F"]["earned"],
        )
        print("classification:", first["acceptance"]["classification"])
        print(f"\nartifacts under {results_root}")
        print(f"total runtime {time.time() - t_start:.1f}s")

    return {
        "artifacts": all_artifacts,
        "md5s": md5s,
        "byte_identical": identical,
        "matrix": first,
        "results_root": str(results_root),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the FROZEN v008 LOSO transfer matrix "
            "(plan godspeed-agent-v008-r1-transfer, V3)."
        )
    )
    parser.add_argument(
        "--episode-table", type=Path, default=EPISODE_TABLE,
        help="Path to the v008 episode table (episodes.jsonl)",
    )
    parser.add_argument(
        "--results-root", type=Path, default=RESULTS_ROOT,
        help="Directory under which experiment artifacts are written",
    )
    args = parser.parse_args(argv)
    run_matrix(episode_table=args.episode_table, results_root=args.results_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
