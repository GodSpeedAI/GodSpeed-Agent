"""Execute the frozen v006 two-family experiment matrix (plan task T05).

The contract is the FROZEN preregistration
``.agents/reports/v006-experiment-preregistration.yaml``: the final test
partition EVALUATES the preregistered system, never redesigns it.  This
runner materializes the group-level stratified holdout once, performs every
frozen choice (hyperparameter selection, out-of-fold calibration) on the
TRAIN partition only, and touches the test partition exactly once in the
final evaluation pass.

Structure (each piece is importable for tests):

- ``load_parents`` / ``group_labels_from_parents`` / ``stratified_group_holdout``
  -- corpus loading and the frozen split (group-level, test_size 0.20,
  random_state 42, stratified by group_label = max parent label in group).
- ``assert_partitions_grouped`` -- wraps ``v006_features.assert_grouped``;
  refuses any partition assignment under which one ``group_key`` straddles
  partitions.
- ``assert_no_label_columns`` -- whitelist guard: ``label`` /
  ``settlement_success`` / ``settlement_score`` (and every identity column)
  must never enter the feature matrix.
- ``select_hyperparameters`` -- STRUCTURAL guarantee that model selection
  never sees test groups: the function signature takes the TRAIN frame only.
- ``oof_train_predictions`` / ``ece_score`` / ``maybe_calibrate`` -- the
  frozen calibration procedure (OOF GroupKFold ECE 10 bins; isotonic on OOF
  iff OOF ECE > 0.05; never fit on test).
- ``evaluate_acceptance`` -- the frozen acceptance rule as a pure function.
- ``run_matrix`` / ``main`` -- the full preregistered matrix + artifacts.

Determinism: fixed seeds everywhere; LightGBM pinned with
``deterministic=True, force_col_wise=True, n_jobs=1`` (does not alter the
frozen hyperparameter space).  Artifacts are JSON/CSV only.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import platform
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import scipy.stats
import sklearn
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GroupKFold

from scripts.settlement_datasets.v006_features import (
    CANONICAL_CUT_KINDS,
    FAMILY_FEATURES,
    SCHEMA_VERSIONS,
    assert_grouped,
    assert_no_leaky_features,
    build_full_frame,
    build_prefix_frame,
)

try:
    from lightgbm import LGBMClassifier
except ImportError:  # pragma: no cover - T02 pins lightgbm in the ml extra
    LGBMClassifier = None

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
CORPUS_ROOT = WORKSPACE_ROOT / "data" / "settlement_datasets" / "corpora" / "v006-trajectories"
EVIDENCE_ROOT = WORKSPACE_ROOT / "data" / "settlement_datasets" / "runs" / "hf-calibration-006-experiments"
CORPUS_SUMMARY = EVIDENCE_ROOT / "corpus_summary.json"
PREREG_PATH = WORKSPACE_ROOT / ".agents" / "reports" / "v006-experiment-preregistration.yaml"

SEED = 42
TEST_SIZE = 0.20
N_CV_SPLITS = 5
MIN_TEST_PARENTS = 30
ECE_BINS = 10
ECE_CALIBRATION_TRIGGER = 0.05
ACCEPTANCE_MIN_DELTA = 0.02
ACCEPTANCE_MIN_CUTS_WON = 4
FIXED_THRESHOLD = 0.5

DATASETS = ("swegym_openhands", "nebius_swe_agent")

# Label columns must never enter X (frozen whitelist guard).
LABEL_COLUMNS = ("label", "settlement_success", "settlement_score")
# Identity columns are frame bookkeeping, also never features.
NON_FEATURE_COLUMNS = (
    "group_key",
    "parent_id",
    "dataset",
    "dataset_id",
    "prefix_kind",
    "k",
    "n_events_total",
    "weight_base",
) + LABEL_COLUMNS

FULL_PREFIX_KIND = "full"

PREFIX_ARMS: tuple[dict[str, str], ...] = (
    {"arm": "P-A", "family": "v005_prefix_compatible", "estimator": "logistic"},
    {"arm": "P-B", "family": "v006", "estimator": "logistic"},
    {"arm": "P-C", "family": "v005_prefix_compatible", "estimator": "lgbm"},
    {"arm": "P-D", "family": "v006", "estimator": "lgbm"},
)
FULL_ARMS: tuple[dict[str, str], ...] = (
    {"arm": "A-full", "family": "v005_full_semantics", "estimator": "logistic"},
    {"arm": "C-full", "family": "v005_full_semantics", "estimator": "lgbm"},
    {"arm": "B-full", "family": "v006", "estimator": "logistic"},
)

PROB_COLUMN_BY_ESTIMATOR = {"logistic": "p_logit", "lgbm": "p_lgbm"}


# ---------------------------------------------------------------------------
# Corpus loading and the frozen split
# ---------------------------------------------------------------------------


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_parents(corpus_root: Path = CORPUS_ROOT) -> list[dict[str, Any]]:
    """Load the local corpus parents from both dataset JSONL files."""
    parents: list[dict[str, Any]] = []
    for dataset in DATASETS:
        path = corpus_root / f"{dataset}.jsonl"
        if not path.exists():
            raise FileNotFoundError(f"corpus file missing: {path}")
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    parents.append(json.loads(line))
    return parents


def verify_corpus_integrity(corpus_root: Path = CORPUS_ROOT) -> dict[str, str]:
    """Recompute corpus sha256s and abort on mismatch with the frozen summary."""
    if not CORPUS_SUMMARY.exists():
        raise FileNotFoundError(f"frozen corpus summary missing: {CORPUS_SUMMARY}")
    summary = json.loads(CORPUS_SUMMARY.read_text(encoding="utf-8"))
    recorded: dict[str, str] = {}
    for dataset, block in summary.get("datasets", {}).items():
        recorded[Path(block["corpus_file"]).name] = block["sha256"]
    actual: dict[str, str] = {}
    for dataset in DATASETS:
        path = corpus_root / f"{dataset}.jsonl"
        digest = _sha256_file(path)
        actual[str(path)] = digest
        expected = recorded.get(path.name)
        if expected is None:
            raise RuntimeError(
                f"frozen corpus summary has no sha256 for {path.name}"
            )
        if expected != digest:
            raise RuntimeError(
                f"corpus file changed after preregistration freeze: {path} "
                f"(recorded {expected}, actual {digest})"
            )
    return actual


def group_labels_from_parents(parents: list[dict[str, Any]]) -> dict[str, int]:
    """group_label = max(parent label in group), per the frozen split rule."""
    labels: dict[str, int] = {}
    for parent in parents:
        key = parent["group_key"]
        labels[key] = max(labels.get(key, 0), int(parent["label"]))
    return labels


def stratified_group_holdout(
    group_labels: dict[str, int],
    test_size: float = TEST_SIZE,
    random_state: int = SEED,
) -> tuple[list[str], list[str]]:
    """Frozen stratified group-level holdout.

    Mechanical realization of the frozen split (see the preregistration):
    GroupShuffleSplit has no stratification support, so the frozen
    "stratified by group_label" quantity is realized by permuting each
    group_label stratum's sorted group keys with ``RandomState(random_state)``
    and holding out ``int(round(test_size * stratum_size))`` of them as test.
    Deterministic; test groups are disjoint from train groups.
    """
    rng = np.random.RandomState(random_state)
    train: list[str] = []
    test: list[str] = []
    for label in sorted(set(group_labels.values())):
        stratum = sorted(g for g, lab in group_labels.items() if lab == label)
        if len(stratum) < 2:
            raise ValueError(
                f"group_label stratum {label!r} has < 2 groups; stratified "
                "group holdout impossible"
            )
        perm = rng.permutation(len(stratum))
        n_test = int(round(test_size * len(stratum)))
        n_test = max(1, min(n_test, len(stratum) - 1))
        test.extend(stratum[i] for i in perm[:n_test])
        train.extend(stratum[i] for i in perm[n_test:])
    return sorted(train), sorted(test)


def assert_partitions_grouped(
    frame: pd.DataFrame, train_groups: set[str], test_groups: set[str]
) -> int:
    """Guard: no group_key straddles partitions; every group in exactly one."""
    if train_groups & test_groups:
        raise ValueError(
            f"{len(train_groups & test_groups)} group(s) assigned to both "
            "train and test partitions"
        )

    def split_fn(row: dict[str, Any]) -> str:
        return "test" if row["group_key"] in test_groups else "train"

    return assert_grouped(frame.to_dict("records"), split_fn)


# ---------------------------------------------------------------------------
# Feature matrix + guards
# ---------------------------------------------------------------------------


def assert_no_label_columns(columns: list[str]) -> None:
    """Whitelist guard: label columns (and identity columns) never enter X."""
    bad_labels = [c for c in columns if c in LABEL_COLUMNS]
    if bad_labels:
        raise ValueError(
            f"Label columns must never enter the feature matrix: {bad_labels}"
        )
    bad_identity = [c for c in columns if c in NON_FEATURE_COLUMNS]
    if bad_identity:
        raise ValueError(
            f"Identity/bookkeeping columns must never enter the feature "
            f"matrix: {bad_identity}"
        )


def feature_columns_for(family: str, use_dataset_id: bool) -> list[str]:
    cols = [c for c in FAMILY_FEATURES[family] if c != "dataset_id"]
    if use_dataset_id:
        cols = cols + ["dataset_id"]
    return cols


def feature_matrix(
    frame: pd.DataFrame, family: str, use_dataset_id: bool
) -> tuple[pd.DataFrame, pd.Series, pd.Series, pd.Series, pd.Series]:
    """X, y, groups, dataset, parent_id for one (family, identity variant).

    ``dataset_id`` is the single sanctioned identity feature (the PRIMARY
    variant mirrors the frozen v005 family); every other label/identity
    column is refused by the whitelist guard.
    """
    cols = feature_columns_for(family, use_dataset_id)
    assert_no_label_columns([c for c in cols if c != "dataset_id"])
    assert_no_leaky_features(cols)
    missing = [c for c in cols if c not in frame.columns]
    if missing:
        raise ValueError(f"frame lacks feature columns for {family}: {missing}")
    X = frame[cols].astype(float)
    values = X.to_numpy()
    if not np.isfinite(values).all():
        raise ValueError(f"non-finite feature values in {family} matrix")
    return (
        X,
        frame["label"].astype(int),
        frame["group_key"].astype(str),
        frame["dataset"].astype(str),
        frame["parent_id"].astype(str),
    )


# ---------------------------------------------------------------------------
# Estimators and hyperparameter grids (frozen)
# ---------------------------------------------------------------------------


def make_estimator(estimator_name: str, params: dict[str, Any]) -> Any:
    if estimator_name == "logistic":
        return LogisticRegression(
            class_weight="balanced",
            max_iter=1000,
            solver="lbfgs",
            random_state=SEED,
            **params,
        )
    if estimator_name == "lgbm":
        if LGBMClassifier is None:
            raise RuntimeError(
                "lightgbm is not importable; the frozen lgbm arms cannot run"
            )
        return LGBMClassifier(
            random_state=SEED,
            verbose=-1,
            subsample=0.9,
            colsample_bytree=0.9,
            reg_lambda=1.0,
            # Global determinism flags; not part of the tuned space.
            deterministic=True,
            force_col_wise=True,
            n_jobs=1,
            **params,
        )
    raise ValueError(f"unknown estimator: {estimator_name}")


def param_grid(estimator_name: str) -> list[dict[str, Any]]:
    """Frozen grids in deterministic candidate order (tiebreak: first wins)."""
    if estimator_name == "logistic":
        return [{"C": c} for c in (0.01, 0.1, 1.0)]
    if estimator_name == "lgbm":
        return [
            {
                "n_estimators": n,
                "num_leaves": leaves,
                "learning_rate": lr,
                "min_child_samples": mcs,
            }
            for n in (150, 400)
            for leaves in (15, 31)
            for lr in (0.05, 0.1)
            for mcs in (20, 50)
        ]
    raise ValueError(f"unknown estimator: {estimator_name}")


def _fit(est: Any, X: pd.DataFrame, y: pd.Series, w: np.ndarray) -> Any:
    return est.fit(X, y, sample_weight=w)


def _proba(est: Any, X: pd.DataFrame) -> np.ndarray:
    return est.predict_proba(X)[:, 1]


# ---------------------------------------------------------------------------
# Model selection (train partition only -- structural)
# ---------------------------------------------------------------------------


def _groupkfold(groups: pd.Series, n_splits: int = N_CV_SPLITS) -> list[tuple[np.ndarray, np.ndarray]]:
    n_groups = groups.nunique()
    if n_groups < n_splits:
        raise ValueError(
            f"GroupKFold({n_splits}) impossible with {n_groups} train groups"
        )
    gkf = GroupKFold(n_splits=n_splits, shuffle=False)
    dummy = np.zeros(len(groups))
    return list(gkf.split(dummy, dummy, groups))


def select_hyperparameters(
    train_frame: pd.DataFrame,
    family: str,
    estimator_name: str,
    use_dataset_id: bool,
    weights: np.ndarray | None = None,
    n_splits: int = N_CV_SPLITS,
) -> dict[str, Any]:
    """Frozen selection: mean GroupKFold ROC-AUC over TRAIN groups at this cut.

    STRUCTURAL GUARANTEE: this function takes the TRAIN frame only -- there
    is no parameter through which test rows could enter selection.
    """
    X, y, groups, _, _ = feature_matrix(train_frame, family, use_dataset_id)
    if weights is None:
        weights = np.ones(len(y))
    else:
        weights = np.asarray(weights, dtype=float)
    folds = _groupkfold(groups, n_splits)
    cv_rows: list[dict[str, Any]] = []
    for params in param_grid(estimator_name):
        fold_aucs: list[float] = []
        fold_aps: list[float] = []
        for tr, va in folds:
            y_va = y.iloc[va]
            if y_va.nunique() < 2:
                continue
            est = make_estimator(estimator_name, params)
            _fit(est, X.iloc[tr], y.iloc[tr], weights[tr])
            p = _proba(est, X.iloc[va])
            fold_aucs.append(float(roc_auc_score(y_va, p)))
            fold_aps.append(float(average_precision_score(y_va, p)))
        if not fold_aucs:
            raise RuntimeError(
                f"no evaluable CV folds for {estimator_name} {params}: "
                "every fold single-class"
            )
        cv_rows.append(
            {
                "params": params,
                "mean_roc_auc": float(np.mean(fold_aucs)),
                "mean_ap": float(np.mean(fold_aps)),
                "n_folds_scored": len(fold_aucs),
            }
        )
    best = max(cv_rows, key=lambda r: (r["mean_roc_auc"], r["mean_ap"]))
    return {
        "best_params": best["params"],
        "best_mean_roc_auc": best["mean_roc_auc"],
        "best_mean_ap": best["mean_ap"],
        "cv_table": cv_rows,
        "n_train_rows": int(len(y)),
        "n_train_groups": int(groups.nunique()),
        "n_train_positives": int(y.sum()),
    }


def oof_train_predictions(
    train_frame: pd.DataFrame,
    family: str,
    estimator_name: str,
    params: dict[str, Any],
    use_dataset_id: bool,
    weights: np.ndarray | None = None,
    n_splits: int = N_CV_SPLITS,
) -> np.ndarray:
    """Out-of-fold TRAIN predictions for the selected model (calibration input)."""
    X, y, groups, _, _ = feature_matrix(train_frame, family, use_dataset_id)
    if weights is None:
        weights = np.ones(len(y))
    oof = np.full(len(y), np.nan)
    for tr, va in _groupkfold(groups, n_splits):
        est = make_estimator(estimator_name, params)
        _fit(est, X.iloc[tr], y.iloc[tr], np.asarray(weights)[tr])
        oof[va] = _proba(est, X.iloc[va])
    if np.isnan(oof).any():
        raise RuntimeError("OOF prediction left unfilled positions")
    return oof


# ---------------------------------------------------------------------------
# Metrics and calibration
# ---------------------------------------------------------------------------


def ece_score(probs: np.ndarray, y: np.ndarray, n_bins: int = ECE_BINS) -> float:
    """Equal-width 10-bin expected calibration error."""
    probs = np.asarray(probs, dtype=float)
    y = np.asarray(y, dtype=int)
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    bin_ids = np.clip(np.digitize(probs, edges[1:-1], right=False), 0, n_bins - 1)
    ece = 0.0
    for b in range(n_bins):
        mask = bin_ids == b
        n_b = int(mask.sum())
        if n_b == 0:
            continue
        conf = float(probs[mask].mean())
        acc = float(y[mask].mean())
        ece += (n_b / len(y)) * abs(acc - conf)
    return float(ece)


def reliability_bins(
    probs: np.ndarray, y: np.ndarray, n_bins: int = ECE_BINS
) -> list[dict[str, float]]:
    probs = np.asarray(probs, dtype=float)
    y = np.asarray(y, dtype=int)
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    bin_ids = np.clip(np.digitize(probs, edges[1:-1], right=False), 0, n_bins - 1)
    out: list[dict[str, float]] = []
    for b in range(n_bins):
        mask = bin_ids == b
        n_b = int(mask.sum())
        out.append(
            {
                "bin_lower": float(edges[b]),
                "bin_upper": float(edges[b + 1]),
                "n": float(n_b),
                "mean_predicted": float(probs[mask].mean()) if n_b else None,
                "fraction_positive": float(y[mask].mean()) if n_b else None,
            }
        )
    return out


def maybe_calibrate(
    oof_probs: np.ndarray,
    y_train: np.ndarray,
    test_probs: np.ndarray,
    trigger: float = ECE_CALIBRATION_TRIGGER,
) -> dict[str, Any]:
    """Frozen calibration path; isotonic is fit on OOF TRAIN predictions only.

    STRUCTURAL GUARANTEE: the signature accepts no test labels -- the
    calibration transform cannot be fit on test in any calling pattern.
    """
    oof_probs = np.asarray(oof_probs, dtype=float)
    y_train = np.asarray(y_train, dtype=int)
    test_probs = np.asarray(test_probs, dtype=float)
    oof_ece = ece_score(oof_probs, y_train)
    result: dict[str, Any] = {
        "oof_ece": oof_ece,
        "trigger": trigger,
        "applied": False,
        "reliability_oof": reliability_bins(oof_probs, y_train),
    }
    if oof_ece > trigger:
        iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        iso.fit(oof_probs, y_train)
        result["applied"] = True
        result["test_probs_calibrated"] = np.asarray(iso.predict(test_probs), dtype=float)
    else:
        result["test_probs_calibrated"] = test_probs
    return result


def evaluate_probs(y_true: np.ndarray, probs: np.ndarray) -> dict[str, Any]:
    """Per-cut metric block; underpowered cuts are flagged, never hidden."""
    y = np.asarray(y_true, dtype=int)
    p = np.asarray(probs, dtype=float)
    n = int(len(y))
    n_pos = int(y.sum())
    n_neg = n - n_pos
    underpowered = n < MIN_TEST_PARENTS or n_pos == 0 or n_neg == 0
    pred = (p >= FIXED_THRESHOLD).astype(int)
    metrics: dict[str, Any] = {
        "n_test_parents": n,
        "n_test_positives": n_pos,
        "n_test_negatives": n_neg,
        "class_balance": float(n_pos / n) if n else None,
        "roc_auc": None,
        "ap": None,
        "brier": float(brier_score_loss(y, p)) if n else None,
        "balanced_accuracy": float(balanced_accuracy_score(y, pred)) if n else None,
        "precision": float(precision_score(y, pred, zero_division=0)) if n else None,
        "recall": float(recall_score(y, pred, zero_division=0)) if n else None,
        "f1": float(f1_score(y, pred, zero_division=0)) if n else None,
        "ece": ece_score(p, y) if n else None,
        "threshold": FIXED_THRESHOLD,
        "underpowered": bool(underpowered),
    }
    if n_pos > 0 and n_neg > 0:
        metrics["roc_auc"] = float(roc_auc_score(y, p))
        metrics["ap"] = float(average_precision_score(y, p))
    return metrics


def per_source_metrics(
    y: pd.Series, probs: np.ndarray, datasets: pd.Series
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    y_arr = np.asarray(y, dtype=int)
    for dataset in sorted(datasets.unique()):
        mask = (datasets == dataset).to_numpy()
        block = evaluate_probs(y_arr[mask], np.asarray(probs)[mask])
        block["macro_eligible"] = block["roc_auc"] is not None
        out[str(dataset)] = block
    aucs = [b["roc_auc"] for b in out.values() if b["roc_auc"] is not None]
    out["_macro_roc_auc"] = float(np.mean(aucs)) if aucs else None  # type: ignore[assignment]
    return out


# ---------------------------------------------------------------------------
# One (arm, cut) run: selection -> fit -> OOF calibration -> single test eval
# ---------------------------------------------------------------------------


def source_balance_weights(train_frame: pd.DataFrame) -> np.ndarray:
    """Frozen sensitivity weights: w_s = 0.5 / n_train_parents_of_source."""
    counts = train_frame["dataset"].value_counts()
    return train_frame["dataset"].map(lambda d: 0.5 / float(counts[d])).to_numpy(dtype=float)


def run_arm_at_cut(
    train_frame: pd.DataFrame,
    test_frame: pd.DataFrame,
    family: str,
    estimator_name: str,
    use_dataset_id: bool,
    weighting: str = "natural",
    n_splits: int = N_CV_SPLITS,
) -> dict[str, Any]:
    """Full preregistered path for one (arm, cut, identity variant).

    Everything except the last line operates on the train partition; the
    single ``evaluate_probs`` + ``per_source_metrics`` calls at the end are
    the one touch of test data.
    """
    if weighting not in ("natural", "source_balanced"):
        raise ValueError(f"unknown weighting: {weighting}")
    weights = (
        source_balance_weights(train_frame) if weighting == "source_balanced" else None
    )
    selection = select_hyperparameters(
        train_frame, family, estimator_name, use_dataset_id, weights=weights, n_splits=n_splits
    )
    X_tr, y_tr, _, _, _ = feature_matrix(train_frame, family, use_dataset_id)
    X_te, y_te, g_te, ds_te, pid_te = feature_matrix(test_frame, family, use_dataset_id)
    w_tr = (
        source_balance_weights(train_frame) if weighting == "source_balanced" else np.ones(len(y_tr))
    )

    est = make_estimator(estimator_name, selection["best_params"])
    _fit(est, X_tr, y_tr, w_tr)
    p_test = _proba(est, X_te)

    oof = oof_train_predictions(
        train_frame, family, estimator_name, selection["best_params"],
        use_dataset_id, weights=w_tr, n_splits=n_splits,
    )
    cal = maybe_calibrate(oof, y_tr.to_numpy(), p_test)

    before = evaluate_probs(y_te.to_numpy(), p_test)
    before["per_source"] = per_source_metrics(y_te, p_test, ds_te)
    after = evaluate_probs(y_te.to_numpy(), cal["test_probs_calibrated"])
    before["brier_after_calibration"] = after["brier"]
    before["ece_after_calibration"] = after["ece"]

    return {
        "selection": selection,
        "oof_ece": cal["oof_ece"],
        "calibration_applied": cal["applied"],
        "reliability_oof": cal["reliability_oof"],
        "metrics": before,
        "test_predictions": {
            "parent_id": pid_te.tolist(),
            "group_key": g_te.tolist(),
            "dataset": ds_te.tolist(),
            "y": y_te.astype(int).tolist(),
            "p": [float(v) for v in p_test],
            "p_calibrated": [float(v) for v in cal["test_probs_calibrated"]],
            "calibration_applied": bool(cal["applied"]),
        },
    }


# ---------------------------------------------------------------------------
# Acceptance rule (pure; hand-fixture-tested)
# ---------------------------------------------------------------------------


def macro_roc_auc(per_cut: dict[str, dict[str, Any]]) -> tuple[float | None, list[str]]:
    """Mean per-cut ROC-AUC over cuts with reliable metrics only."""
    reliable = sorted(
        cut
        for cut, m in per_cut.items()
        if not m.get("underpowered", False) and m.get("roc_auc") is not None
    )
    if not reliable:
        return None, []
    return float(np.mean([per_cut[c]["roc_auc"] for c in reliable])), reliable


def evaluate_acceptance(
    baseline_cuts: dict[str, dict[str, Any]],
    treatment_cuts: dict[str, dict[str, Any]],
    robustness_baseline_cuts: dict[str, dict[str, Any]],
    robustness_treatment_cuts: dict[str, dict[str, Any]],
    min_delta: float = ACCEPTANCE_MIN_DELTA,
    min_cuts_won: int = ACCEPTANCE_MIN_CUTS_WON,
) -> dict[str, Any]:
    """Frozen acceptance rule, mechanically applied.

    ``*_cuts`` map cut kind -> metrics block (needs ``roc_auc`` and
    ``underpowered``).  Reliability is identical across variants (same test
    parents); the reliable cut set is taken from the primary comparison.
    """
    delta_primary, reliable = macro_roc_auc_pair(baseline_cuts, treatment_cuts)
    delta_robust, _ = macro_roc_auc_pair(
        robustness_baseline_cuts, robustness_treatment_cuts, restrict_to=reliable
    )
    if delta_primary is None:
        return {
            "verdict": "NOT EARNED (no cut with reliable metrics)",
            "reliable_cuts": reliable,
            "delta_primary": None,
            "delta_robustness": delta_robust,
            "cuts_won": 0,
            "identity_dependent": False,
        }
    won = sum(
        1
        for c in reliable
        if treatment_cuts[c]["roc_auc"] >= baseline_cuts[c]["roc_auc"]
    )
    gain = (delta_primary >= min_delta) and (won >= min_cuts_won)
    reversal = False
    if delta_robust is not None:
        reversal = (delta_primary > 0 and delta_robust < 0) or (
            delta_primary < 0 and delta_robust > 0
        )
    identity_dependent = bool(gain and reversal)
    if gain and not identity_dependent:
        verdict = "EARNED (identity-robust)"
    elif gain and identity_dependent:
        verdict = "NOT EARNED -- identity-dependent (adoption blocked)"
    else:
        verdict = "NOT EARNED"
    return {
        "verdict": verdict,
        "reliable_cuts": reliable,
        "delta_primary": delta_primary,
        "delta_robustness": delta_robust,
        "cuts_won": won,
        "cuts_won_required": min_cuts_won,
        "min_delta": min_delta,
        "identity_dependent": identity_dependent,
        "per_cut_direction": {
            c: bool(treatment_cuts[c]["roc_auc"] >= baseline_cuts[c]["roc_auc"])
            for c in reliable
        },
    }


def macro_roc_auc_pair(
    baseline_cuts: dict[str, dict[str, Any]],
    treatment_cuts: dict[str, dict[str, Any]],
    restrict_to: list[str] | None = None,
) -> tuple[float | None, list[str]]:
    base_macro, base_reliable = macro_roc_auc(baseline_cuts)
    treat_macro, treat_reliable = macro_roc_auc(treatment_cuts)
    reliable = sorted(set(base_reliable) & set(treat_reliable))
    if restrict_to is not None:
        reliable = [c for c in reliable if c in restrict_to]
    if base_macro is None or treat_macro is None or not reliable:
        return None, reliable
    delta = treat_macro - base_macro
    # Recompute the delta strictly over the shared reliable cut set.
    base_mean = float(np.mean([baseline_cuts[c]["roc_auc"] for c in reliable]))
    treat_mean = float(np.mean([treatment_cuts[c]["roc_auc"] for c in reliable]))
    return float(treat_mean - base_mean), reliable


# ---------------------------------------------------------------------------
# Matrix orchestration
# ---------------------------------------------------------------------------


def _cut_frame(frame: pd.DataFrame, cut: str) -> pd.DataFrame:
    sub = frame[frame["prefix_kind"] == cut]
    if sub.empty:
        raise RuntimeError(f"cut {cut!r} has no rows")
    return sub


def _per_cut_yields(frame: pd.DataFrame) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for cut in CANONICAL_CUT_KINDS:
        sub = frame[frame["prefix_kind"] == cut]
        by_ds = sub.groupby("dataset")["parent_id"].nunique().to_dict()
        out[cut] = {
            "parents_with_cut": int(sub["parent_id"].nunique()),
            "rows": int(len(sub)),
            "by_dataset": {k: int(v) for k, v in sorted(by_ds.items())},
        }
    return out


def run_identity_variant(
    train_frame_by_cut: dict[str, pd.DataFrame],
    test_frame_by_cut: dict[str, pd.DataFrame],
    arms: list[dict[str, str]],
    use_dataset_id: bool,
    log: bool = True,
) -> dict[str, dict[str, dict[str, Any]]]:
    results: dict[str, dict[str, dict[str, Any]]] = {}
    for spec in arms:
        arm, family, est_name = spec["arm"], spec["family"], spec["estimator"]
        results[arm] = {}
        for cut in CANONICAL_CUT_KINDS:
            t0 = time.time()
            block = run_arm_at_cut(
                train_frame_by_cut[cut],
                test_frame_by_cut[cut],
                family,
                est_name,
                use_dataset_id,
            )
            results[arm][cut] = block
            if log:
                auc = block["metrics"]["roc_auc"]
                print(
                    f"  {arm} variant={'with' if use_dataset_id else 'without'}_dataset_id "
                    f"cut={cut:<20} auc={auc if auc is not None else 'n/a'} "
                    f"({time.time() - t0:.1f}s)",
                    flush=True,
                )
    return results


def collect_cut_aucs(variant_results: dict[str, dict[str, dict[str, Any]]], arm: str) -> dict[str, dict[str, Any]]:
    return {cut: block["metrics"] for cut, block in variant_results[arm].items()}


def run_full_family(
    full_train: pd.DataFrame,
    full_test: pd.DataFrame,
    use_dataset_id: bool,
    weighting: str = "natural",
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for spec in FULL_ARMS:
        t0 = time.time()
        block = run_arm_at_cut(
            full_train,
            full_test,
            spec["family"],
            spec["estimator"],
            use_dataset_id,
            weighting=weighting,
        )
        out[spec["arm"]] = block
        auc = block["metrics"]["roc_auc"]
        print(
            f"  {spec['arm']} variant={'with' if use_dataset_id else 'without'}_dataset_id "
            f"auc={auc if auc is not None else 'n/a'} ({time.time() - t0:.1f}s)",
            flush=True,
        )
    return out


def run_lodo(
    prefix_frame: pd.DataFrame,
    train_groups: list[str],
    test_groups_unused: set[str],
) -> dict[str, Any]:
    """LODO for P-A vs P-B per cut; dataset_id omitted (structural inertness).

    WEAK evidence by construction: two folds, unequal sizes.
    """
    del test_groups_unused  # LODO uses whole sources, not the holdout.
    out: dict[str, Any] = {"note": "WEAK evidence: two folds, unequal sizes; dataset_id omitted (constant within a LODO train partition)", "folds": {}}
    sources = ("swegym_openhands", "nebius_swe_agent")
    for train_source, eval_source in itertools.permutations(sources, 2):
        train_src = prefix_frame[prefix_frame["dataset"] == train_source]
        eval_src = prefix_frame[prefix_frame["dataset"] == eval_source]
        # LODO selection groups stay within the LODO train source.
        use_dataset_id = False
        for spec_name, family, est_name in (("P-A", "v005_prefix_compatible", "logistic"), ("P-B", "v006", "logistic")):
            for cut in CANONICAL_CUT_KINDS:
                fold_key = f"train={train_source}->eval={eval_source}"
                out["folds"].setdefault(fold_key, {}).setdefault(spec_name, {})
                try:
                    tr = _cut_frame(train_src, cut)
                    te = _cut_frame(eval_src, cut)
                    block = run_arm_at_cut(
                        tr, te, family, est_name, use_dataset_id
                    )
                except (ValueError, RuntimeError) as exc:
                    # e.g. single-source cut where the train source has no
                    # rows (nebius at the failure/recovery cuts).
                    out["folds"][fold_key][spec_name][cut] = {
                        "not_defined": True,
                        "reason": str(exc),
                    }
                    continue
                out["folds"][fold_key][spec_name][cut] = {
                    "roc_auc": block["metrics"]["roc_auc"],
                    "ap": block["metrics"]["ap"],
                    "n_eval_parents": block["metrics"]["n_test_parents"],
                    "n_train_parents": block["selection"]["n_train_rows"],
                    "best_params": block["selection"]["best_params"],
                }
    return out


def run_disagreement(
    variant_with: dict[str, dict[str, dict[str, Any]]],
    test_frame_by_cut: dict[str, pd.DataFrame],
) -> dict[str, Any]:
    """|p_logit - p_lgbm| on the v006 feature set per cut (P-B vs P-D)."""
    out: dict[str, Any] = {}
    for cut in CANONICAL_CUT_KINDS:
        pb = variant_with["P-B"][cut]["test_predictions"]
        pd_ = variant_with["P-D"][cut]["test_predictions"]
        assert pb["parent_id"] == pd_["parent_id"], "P-B/P-D test populations differ"
        p_logit = np.asarray(pb["p"], dtype=float)
        p_lgbm = np.asarray(pd_["p"], dtype=float)
        y = np.asarray(pb["y"], dtype=int)
        d = np.abs(p_logit - p_lgbm)
        err_lr = np.abs(p_logit - y)
        err_lgbm = np.abs(p_lgbm - y)
        block: dict[str, Any] = {
            "n_test_parents": int(len(d)),
            "mean": float(d.mean()),
            "median": float(np.median(d)),
            "p90": float(np.percentile(d, 90)),
            "frac_gt_0.2": float((d > 0.2).mean()),
            "corr_pearson_disagreement_vs_err_logit": float(scipy.stats.pearsonr(d, err_lr)[0]) if len(d) > 2 and np.std(d) > 0 else None,
            "corr_pearson_disagreement_vs_err_lgbm": float(scipy.stats.pearsonr(d, err_lgbm)[0]) if len(d) > 2 and np.std(d) > 0 else None,
            "corr_spearman_disagreement_vs_err_logit": float(scipy.stats.spearmanr(d, err_lr)[0]) if len(d) > 2 and np.std(d) > 0 else None,
            "corr_spearman_disagreement_vs_err_lgbm": float(scipy.stats.spearmanr(d, err_lgbm)[0]) if len(d) > 2 and np.std(d) > 0 else None,
        }
        out[cut] = block
    return out


def summarize_calibration(
    variant_results: dict[str, dict[str, dict[str, Any]]],
    full_results: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Per-feature-family calibration verdict (frozen)."""
    family_of_arm = {
        "P-A": "v005_prefix_compatible",
        "P-C": "v005_prefix_compatible",
        "P-B": "v006",
        "P-D": "v006",
        "A-full": "v005_full_semantics",
        "C-full": "v005_full_semantics",
        "B-full": "v006-full (diagnostic)",
    }
    per_family: dict[str, dict[str, Any]] = {}
    blocks: list[tuple[str, str, dict[str, Any]]] = []
    for arm, cuts in variant_results.items():
        for cut, block in cuts.items():
            blocks.append((family_of_arm[arm], f"{arm}@{cut}", block))
    for arm, block in full_results.items():
        blocks.append((family_of_arm[arm], f"{arm}@full", block))
    for family in sorted(set(family_of_arm.values())):
        items = [(name, b) for fam, name, b in blocks if fam == family]
        if not items:
            continue
        n_triggered = sum(1 for _, b in items if b["calibration_applied"])
        briers_before = [b["metrics"]["brier"] for _, b in items if b["metrics"]["brier"] is not None]
        briers_after = [
            b["metrics"]["brier_after_calibration"]
            for _, b in items
            if b["metrics"].get("brier_after_calibration") is not None
        ]
        eces_before = [b["metrics"]["ece"] for _, b in items if b["metrics"]["ece"] is not None]
        eces_after = [
            b["metrics"]["ece_after_calibration"]
            for _, b in items
            if b["metrics"].get("ece_after_calibration") is not None
        ]
        improved = (
            bool(briers_after) and bool(briers_before)
            and float(np.mean(briers_after)) < float(np.mean(briers_before))
        )
        per_family[family] = {
            "n_models": len(items),
            "n_triggered": int(n_triggered),
            "mean_oof_ece": float(np.mean([b["oof_ece"] for _, b in items])),
            "mean_test_brier_before": float(np.mean(briers_before)) if briers_before else None,
            "mean_test_brier_after": float(np.mean(briers_after)) if briers_after else None,
            "mean_test_ece_before": float(np.mean(eces_before)) if eces_before else None,
            "mean_test_ece_after": float(np.mean(eces_after)) if eces_after else None,
            "isotonic_improved_mean_test_brier": improved,
            "calibration_required": bool(n_triggered > 0),
        }
    return per_family


def build_leaderboard(
    prefix_with: dict[str, dict[str, dict[str, Any]]],
    prefix_without: dict[str, dict[str, dict[str, Any]]],
    full_with: dict[str, dict[str, Any]],
    full_without: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    board: dict[str, Any] = {}
    for arm in ("P-A", "P-B", "P-C", "P-D"):
        for variant, results in (("with_dataset_id", prefix_with), ("without_dataset_id", prefix_without)):
            cuts = collect_cut_aucs(results, arm)
            macro, reliable = macro_roc_auc(cuts)
            board.setdefault(arm, {})[variant] = {
                "macro_roc_auc": macro,
                "reliable_cuts": reliable,
                "per_cut_roc_auc": {c: cuts[c]["roc_auc"] for c in CANONICAL_CUT_KINDS},
            }
    for arm in ("A-full", "C-full", "B-full"):
        for variant, results in (("with_dataset_id", full_with), ("without_dataset_id", full_without)):
            m = results[arm]["metrics"]
            board.setdefault(arm, {})[variant] = {
                "roc_auc": m["roc_auc"],
                "ap": m["ap"],
                "brier": m["brier"],
                "balanced_accuracy": m["balanced_accuracy"],
                "f1": m["f1"],
            }
    return board


def print_leaderboard(board: dict[str, Any], acceptance: dict[str, Any]) -> None:
    print("\n=== LEADERBOARD (macro ROC-AUC over reliable cuts) ===")
    for arm in ("P-A", "P-B", "P-C", "P-D"):
        for variant in ("with_dataset_id", "without_dataset_id"):
            b = board[arm][variant]
            macro = b["macro_roc_auc"]
            macro_str = f"{macro:.4f}" if macro is not None else "n/a"
            per_cut = " ".join(
                f"{c[:2]}={b['per_cut_roc_auc'][c]:.4f}" if b["per_cut_roc_auc"][c] is not None else f"{c[:2]}=n/a"
                for c in CANONICAL_CUT_KINDS
            )
            print(f"{arm:<5} {variant:<19} macro={macro_str}  {per_cut}")
    for arm in ("A-full", "C-full", "B-full"):
        for variant in ("with_dataset_id", "without_dataset_id"):
            b = board[arm][variant]
            print(f"{arm:<7} {variant:<19} auc={b['roc_auc']:.4f} ap={b['ap']:.4f}")
    print("\n=== PREREGISTERED ACCEPTANCE VERDICTS ===")
    for name, verdict in acceptance.items():
        print(f"{name}: {verdict['verdict']}  (delta={verdict['delta_primary']}, robust_delta={verdict['delta_robustness']}, cuts_won={verdict['cuts_won']})")


# ---------------------------------------------------------------------------
# Artifacts
# ---------------------------------------------------------------------------


def _prereg_fingerprint() -> dict[str, Any]:
    stat = PREREG_PATH.stat()
    return {
        "path": str(PREREG_PATH),
        "sha256": _sha256_file(PREREG_PATH),
        "mtime_epoch": stat.st_mtime,
        "mtime_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(stat.st_mtime)),
    }


def write_artifacts(
    evidence_root: Path,
    manifest: dict[str, Any],
    results: dict[str, Any],
    calibration_summary: dict[str, Any],
    disagreement_summary: dict[str, Any],
    prediction_records: list[dict[str, Any]],
) -> dict[str, str]:
    evidence_root.mkdir(parents=True, exist_ok=True)
    paths: dict[str, str] = {}
    files = {
        "experiment_manifest.json": manifest,
        "results.json": results,
        "calibration_summary.json": calibration_summary,
        "disagreement_summary.json": disagreement_summary,
    }
    for name, payload in files.items():
        path = evidence_root / name
        path.write_text(json.dumps(payload, indent=2, sort_keys=False, default=str), encoding="utf-8")
        paths[name] = str(path)
    pred_path = evidence_root / "test_predictions.jsonl"
    with pred_path.open("w", encoding="utf-8") as f:
        for record in prediction_records:
            f.write(json.dumps(record, default=str) + "\n")
    paths["test_predictions.jsonl"] = str(pred_path)

    rows: list[dict[str, Any]] = []
    for arm, cuts in results["prefix_family"]["with_dataset_id"].items():
        for cut, block in cuts.items():
            rows.append(_per_cut_csv_row(arm, "with_dataset_id", cut, block))
    for arm, cuts in results["prefix_family"]["without_dataset_id"].items():
        for cut, block in cuts.items():
            rows.append(_per_cut_csv_row(arm, "without_dataset_id", cut, block))
    for arm, block in results["full_family"]["with_dataset_id"].items():
        rows.append(_per_cut_csv_row(arm, "with_dataset_id", "full", block))
    for arm, block in results["full_family"]["without_dataset_id"].items():
        rows.append(_per_cut_csv_row(arm, "without_dataset_id", "full", block))
    csv_path = evidence_root / "per_cut_results.csv"
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    paths["per_cut_results.csv"] = str(csv_path)
    return paths


def _per_cut_csv_row(arm: str, variant: str, cut: str, block: dict[str, Any]) -> dict[str, Any]:
    m = block["metrics"]
    return {
        "arm": arm,
        "identity_variant": variant,
        "prefix_kind": cut,
        "n_test_parents": m["n_test_parents"],
        "n_test_positives": m["n_test_positives"],
        "class_balance": m["class_balance"],
        "underpowered": m["underpowered"],
        "roc_auc": m["roc_auc"],
        "ap": m["ap"],
        "brier": m["brier"],
        "balanced_accuracy": m["balanced_accuracy"],
        "precision": m["precision"],
        "recall": m["recall"],
        "f1": m["f1"],
        "ece": m["ece"],
        "oof_ece": block["oof_ece"],
        "calibration_applied": block["calibration_applied"],
        "brier_after_calibration": m.get("brier_after_calibration"),
        "ece_after_calibration": m.get("ece_after_calibration"),
        "best_params": json.dumps(block["selection"]["best_params"], sort_keys=True),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run_matrix(
    corpus_root: Path = CORPUS_ROOT,
    evidence_root: Path = EVIDENCE_ROOT,
    log: bool = True,
) -> dict[str, Any]:
    t_start = time.time()
    corpus_sha = verify_corpus_integrity(corpus_root)
    prereg_fp = _prereg_fingerprint()
    parents = load_parents(corpus_root)
    if log:
        print(f"loaded {len(parents)} parents", flush=True)

    group_labels = group_labels_from_parents(parents)
    train_groups, test_groups = stratified_group_holdout(group_labels)
    train_set, test_set = set(train_groups), set(test_groups)
    if log:
        n_train_pos = sum(1 for p in parents if p["group_key"] in train_set and p["label"] == 1)
        n_test_pos = sum(1 for p in parents if p["group_key"] in test_set and p["label"] == 1)
        print(
            f"holdout: {len(train_groups)} train groups / {len(test_groups)} test groups; "
            f"test positives {n_test_pos}",
            flush=True,
        )

    # Frames: one prefix frame over both prefix families (identical rows for
    # every prefix arm); one full frame over all three families.
    prefix_frame = build_prefix_frame(parents, families=("v005_prefix_compatible", "v006"))
    full_frame = build_full_frame(parents, families=("v005_full_semantics", "v006"))
    for frame in (prefix_frame, full_frame):
        assert_partitions_grouped(frame, train_set, test_set)
    prefix_train = prefix_frame[prefix_frame["group_key"].isin(train_set)]
    prefix_test = prefix_frame[prefix_frame["group_key"].isin(test_set)]
    full_train = full_frame[full_frame["group_key"].isin(train_set)]
    full_test = full_frame[full_frame["group_key"].isin(test_set)]

    train_by_cut = {cut: _cut_frame(prefix_train, cut) for cut in CANONICAL_CUT_KINDS}
    test_by_cut = {cut: _cut_frame(prefix_test, cut) for cut in CANONICAL_CUT_KINDS}

    per_cut_sizes = {
        cut: {
            "train_parents": int(f["parent_id"].nunique()),
            "train_rows": int(len(f)),
            "train_positives": int(f["label"].sum()),
            "test_parents": int(test_by_cut[cut]["parent_id"].nunique()),
            "test_rows": int(len(test_by_cut[cut])),
            "test_positives": int(test_by_cut[cut]["label"].sum()),
        }
        for cut, f in train_by_cut.items()
    }
    per_cut_yields = _per_cut_yields(prefix_frame)

    print("PRIMARY identity variant (with dataset_id):", flush=True)
    prefix_with = run_identity_variant(train_by_cut, test_by_cut, list(PREFIX_ARMS), True)
    print("ROBUSTNESS identity variant (without dataset_id):", flush=True)
    prefix_without = run_identity_variant(train_by_cut, test_by_cut, list(PREFIX_ARMS), False)
    print("FULL family (with dataset_id):", flush=True)
    full_with = run_full_family(full_train, full_test, True)
    print("FULL family (without dataset_id):", flush=True)
    full_without = run_full_family(full_train, full_test, False)

    # Frozen acceptance, mechanically applied.
    acceptance = {
        "representation_gain_P-B_vs_P-A": evaluate_acceptance(
            collect_cut_aucs(prefix_with, "P-A"), collect_cut_aucs(prefix_with, "P-B"),
            collect_cut_aucs(prefix_without, "P-A"), collect_cut_aucs(prefix_without, "P-B"),
        ),
        "estimator_gain_P-C_vs_P-A": evaluate_acceptance(
            collect_cut_aucs(prefix_with, "P-A"), collect_cut_aucs(prefix_with, "P-C"),
            collect_cut_aucs(prefix_without, "P-A"), collect_cut_aucs(prefix_without, "P-C"),
        ),
        "combined_gain_P-D_vs_P-A": evaluate_acceptance(
            collect_cut_aucs(prefix_with, "P-A"), collect_cut_aucs(prefix_with, "P-D"),
            collect_cut_aucs(prefix_without, "P-A"), collect_cut_aucs(prefix_without, "P-D"),
        ),
    }

    print("LODO (weak evidence):", flush=True)
    lodo = run_lodo(prefix_frame, train_groups, test_set)
    print("Source-balanced sensitivity arm:", flush=True)
    sensitivity = {
        "note": (
            "preregistered trigger met (1574/225 > 3); w_s = 0.5 / "
            "n_train_parents_of_source within each cut's train partition; "
            "PRIMARY identity variant; sensitivity only"
        ),
        "with_source_weights": {},
    }
    sens_arms = ("P-A", "P-B", "P-D")
    sens_results: dict[str, dict[str, dict[str, Any]]] = {arm: {} for arm in sens_arms}
    for spec in PREFIX_ARMS:
        if spec["arm"] not in sens_arms:
            continue
        for cut in CANONICAL_CUT_KINDS:
            block = run_arm_at_cut(
                train_by_cut[cut], test_by_cut[cut], spec["family"], spec["estimator"],
                True, weighting="source_balanced",
            )
            sens_results[spec["arm"]][cut] = block
    for treat in ("P-B", "P-D"):
        verdict = evaluate_acceptance(
            collect_cut_aucs(sens_results, "P-A"), collect_cut_aucs(sens_results, treat),
            collect_cut_aucs(sens_results, "P-A"), collect_cut_aucs(sens_results, treat),
        )
        sensitivity["with_source_weights"][f"{treat}_vs_P-A"] = {
            "macro_delta": verdict["delta_primary"],
            "cuts_won": verdict["cuts_won"],
            "reliable_cuts": verdict["reliable_cuts"],
        }
    sensitivity["per_cut"] = {
        arm: {cut: {"roc_auc": b["metrics"]["roc_auc"], "ap": b["metrics"]["ap"]} for cut, b in cuts.items()}
        for arm, cuts in sens_results.items()
    }

    calibration_summary = summarize_calibration(prefix_with, full_with)
    disagreement_summary = run_disagreement(prefix_with, test_by_cut)

    board = build_leaderboard(prefix_with, prefix_without, full_with, full_without)
    print_leaderboard(board, acceptance)

    # ---- artifacts --------------------------------------------------------
    n_train_pos = int(full_train["label"].sum())
    n_test_pos = int(full_test["label"].sum())
    manifest = {
        "plan": "godspeed-agent-v006-dual-model",
        "task": "T05",
        "preregistration": prereg_fp,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "runtime_seconds": time.time() - t_start,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "versions": {
            "scikit-learn": sklearn.__version__,
            "lightgbm": __import__("lightgbm").__version__ if LGBMClassifier is not None else None,
            "pandas": pd.__version__,
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
        "seeds": {"random_state": SEED, "test_size": TEST_SIZE, "cv_splits": N_CV_SPLITS},
        "determinism_flags": {"lgbm": ["deterministic=True", "force_col_wise=True", "n_jobs=1"]},
        "schema_versions": SCHEMA_VERSIONS,
        "corpus": {
            "root": str(corpus_root),
            "sha256_by_file": corpus_sha,
            "parents": len(parents),
            "datasets": {
                "swegym_openhands": {"revision_sha": "baf3a4e4bff514d48ddc08a93a2ade5c126212c7", "license": "ambiguous-recorded", "parents": 1574},
                "nebius_swe_agent": {"revision_sha": "68195a1450865274106246d0d0296a1d6807b88e", "license": "cc-by-4.0", "parents": 225},
                "agenttrove": "rejected (label columns null at live revision; agent self-report only)",
            },
            "known_structural_confound": "nebius_swe_agent has ZERO is_error events; error/recovery features are swegym-supported only; after_first_failure/after_first_recovery cuts contain swegym parents only",
        },
        "split": {
            "strategy": "frozen stratified group-level holdout (see preregistration)",
            "train_groups": len(train_groups),
            "test_groups": len(test_groups),
            "train_parents": int(full_train["parent_id"].nunique()),
            "test_parents": int(full_test["parent_id"].nunique()),
            "train_positives": n_train_pos,
            "test_positives": n_test_pos,
        },
        "per_cut_sizes": per_cut_sizes,
        "per_cut_yields": per_cut_yields,
        "weighting": {
            "primary": "natural mixture (no source weights)",
            "within_cut_parent_balance": "structural (one row per parent per cut)",
            "weight_base_use": "carried; no pooled training exists in the frozen matrix",
            "sensitivity": "w_s = 0.5 / n_train_parents_of_source (per cut train partition)",
        },
        "artifacts_written_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    prediction_records: list[dict[str, Any]] = []
    for family_results, arm_specs in (
        (prefix_with, PREFIX_ARMS),
    ):
        for spec in arm_specs:
            arm = spec["arm"]
            prob_col = PROB_COLUMN_BY_ESTIMATOR[spec["estimator"]]
            for cut, block in family_results[arm].items():
                tp = block["test_predictions"]
                for i, pid in enumerate(tp["parent_id"]):
                    prediction_records.append(
                        {
                            "arm": arm,
                            "identity_variant": "with_dataset_id",
                            "prefix_kind": cut,
                            "parent_id": pid,
                            "group_key": tp["group_key"][i],
                            "dataset": tp["dataset"][i],
                            "y": tp["y"][i],
                            prob_col: tp["p"][i],
                            "p_calibrated": tp["p_calibrated"][i] if tp["calibration_applied"] else None,
                        }
                    )
    # Robustness variant records.
    for spec in PREFIX_ARMS:
        arm = spec["arm"]
        prob_col = PROB_COLUMN_BY_ESTIMATOR[spec["estimator"]]
        for cut, block in prefix_without[arm].items():
            tp = block["test_predictions"]
            for i, pid in enumerate(tp["parent_id"]):
                prediction_records.append(
                    {
                        "arm": arm,
                        "identity_variant": "without_dataset_id",
                        "prefix_kind": cut,
                        "parent_id": pid,
                        "group_key": tp["group_key"][i],
                        "dataset": tp["dataset"][i],
                        "y": tp["y"][i],
                        prob_col: tp["p"][i],
                        "p_calibrated": tp["p_calibrated"][i] if tp["calibration_applied"] else None,
                    }
                )
    # Full-family records.
    for full_results, tag in ((full_with, "with_dataset_id"), (full_without, "without_dataset_id")):
        for spec in FULL_ARMS:
            arm = spec["arm"]
            prob_col = PROB_COLUMN_BY_ESTIMATOR[spec["estimator"]]
            tp = full_results[arm]["test_predictions"]
            for i, pid in enumerate(tp["parent_id"]):
                prediction_records.append(
                    {
                        "arm": arm,
                        "identity_variant": tag,
                        "prefix_kind": "full",
                        "parent_id": pid,
                        "group_key": tp["group_key"][i],
                        "dataset": tp["dataset"][i],
                        "y": tp["y"][i],
                        prob_col: tp["p"][i],
                        "p_calibrated": tp["p_calibrated"][i] if tp["calibration_applied"] else None,
                    }
                )

    results_payload = {
        "preregistration_sha256": prereg_fp["sha256"],
        "split": manifest["split"],
        "per_cut_sizes": per_cut_sizes,
        "per_cut_yields": per_cut_yields,
        "prefix_family": {
            "with_dataset_id": prefix_with,
            "without_dataset_id": prefix_without,
        },
        "full_family": {"with_dataset_id": full_with, "without_dataset_id": full_without},
        "leaderboard": board,
        "acceptance": acceptance,
        "lodo": lodo,
        "sensitivity": sensitivity,
        "per_source_note": "per-source metrics embedded in every cut block under metrics.per_source",
    }

    paths = write_artifacts(
        evidence_root, manifest, results_payload, calibration_summary, disagreement_summary, prediction_records
    )
    if log:
        print(f"\nartifacts written under {evidence_root}:")
        for name, path in paths.items():
            print(f"  {name}: {path}")
        print(f"total runtime {time.time() - t_start:.1f}s")
    return {"manifest": manifest, "results": results_payload, "paths": paths}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the frozen v006 two-family experiment matrix (T05)."
    )
    parser.add_argument("--corpus-root", type=Path, default=CORPUS_ROOT)
    parser.add_argument("--evidence-root", type=Path, default=EVIDENCE_ROOT)
    args = parser.parse_args(argv)
    run_matrix(corpus_root=args.corpus_root, evidence_root=args.evidence_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
