"""Execute the FROZEN v007 recovery-prediction experiment matrix (plan T03).

The contract is the FROZEN preregistration
``.agents/reports/v007-experiment-preregistration.yaml``: the final test
partition EVALUATES the preregistered system, never redesigns it.  This
runner is a SEPARATE v007 module (v006 files are imported where a shared
formula exists -- via ``v007_recovery`` -- and never modified).  It
materializes the stratum-grouped holdout once over ``split_group``, performs
every frozen choice (hyperparameter selection, out-of-fold calibration) on
the TRAIN partition only, and touches the test partition exactly once in
the final evaluation pass.

Structure (each piece is importable for tests):

- ``load_episode_table`` / ``verify_episode_table`` -- local episode-table
  loading with sha256 verification against the frozen build manifest.
- ``group_labels_from_frame`` / ``stratified_group_holdout`` /
  ``assert_partitions_grouped`` -- the frozen split per AMENDMENT 1
  (2026-09-15, pre-round-2): strata are ``(dataset, group_label)`` where
  group_label = 1 iff ANY episode of the ``split_group`` has
  ``recovery_success == 1`` (split stratification ONLY; row labels are
  never changed), test_size 0.20, random_state 42, so each source
  contributes ~20% of its groups to test.  A stratum holding a single
  group is assigned to test deterministically (no RNG), maximizing test
  coverage of rare strata.  The grouping guard delegates to
  ``v007_recovery.assert_grouped_by_split_group`` and refuses any
  assignment under which one split_group straddles partitions.
  Round-1 (strata on group_label alone) drew all 11 swegym groups into
  train, leaving the frozen swegym per-source test cells empty; its
  artifacts are preserved at ``runs/v007-recovery/round1-stratum-defect/``.
- ``assert_feature_columns`` / ``feature_columns_for`` / ``feature_matrix``
  -- the whitelist guard: identity/label columns (``recovery_success``,
  ``audit_bucket``, ``parent_label``, every id/bookkeeping column, and all
  escape-derived names except the documented CAUSAL_ESCAPE_FEATURE_EXCEPTION
  ``prior_escape_count``) must never enter X; ``dataset_id`` joins X only in
  the with-identity variant per the frozen identity-variant rule.
- ``select_hyperparameters`` -- STRUCTURAL guarantee that selection never
  sees test groups: the function signature takes the TRAIN frame only.
- ``parent_balanced_training_weights`` (imported from ``v007_recovery``) --
  1/(training episodes of that parent) on TRAIN rows only; never used in
  metric computation.
- ``oof_train_predictions`` / ``ece_score`` / ``maybe_calibrate`` -- the
  frozen calibration path (OOF GroupKFold ECE 10 bins; isotonic on OOF iff
  OOF ECE > 0.05; the signature cannot fit on test).
- ``evaluate_probs`` / ``parent_aggregated_auc`` / ``per_source_metrics`` --
  episode-level metrics plus the multiplicity-inflation co-reports.
- ``run_loso`` -- leave-one-source-out (3 folds) reusing the globally
  selected hyperparameters, performed INSIDE the train partition only so
  the test partition is still touched exactly once.
- ``evaluate_acceptance`` / ``classify_outcome`` -- the frozen acceptance
  rules as pure functions.
- ``run_matrix`` / ``main`` -- the full preregistered matrix + artifacts.

Documented operationalizations (recorded in the experiment manifest):

- group_label (prereg: "max parent label in group"): parents hold MULTIPLE
  episodes with potentially different labels, so group_label is defined as
  1 iff ANY episode of the group has recovery_success == 1.
- parent-aggregated AUC labels each parent by max(recovery_success) over
  its test episodes (the same ANY-episode convention); probabilities are
  averaged per parent before scoring.
- LOSO trains on train-partition rows of two sources and evaluates on the
  train-partition rows of the held-out source (the test partition stays
  untouched; no re-tuning -- the globally selected hyperparameters are
  reused; weights recomputed on the LOSO train frame per the frozen
  weight definition).

Determinism: fixed seeds everywhere; LightGBM pinned with
``deterministic=True, force_col_wise=True, n_jobs=1`` (not part of the
frozen hyperparameter space).  Artifacts are JSON/CSV/JSONL only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
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

from scripts.settlement_datasets.v007_recovery import (
    ABLATION_EXTRA_COLUMN,
    FRAME_COLUMNS,
    POINT_R0,
    POINT_R1,
    R0_FEATURES,
    R1_FEATURES,
    SCHEMA_VERSIONS,
    V005_MINIMAL_RECOVERY_FEATURES,
    assert_grouped_by_split_group,
    assert_no_label_features,
    parent_balanced_training_weights,
)

try:
    from lightgbm import LGBMClassifier
except ImportError:  # pragma: no cover - T02 pins lightgbm in the ml extra
    LGBMClassifier = None

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
EPISODE_TABLE = (
    WORKSPACE_ROOT
    / "data"
    / "settlement_datasets"
    / "corpora"
    / "v007-episodes"
    / "episodes.jsonl"
)
EPISODE_TABLE_MANIFEST = EPISODE_TABLE.parent / "manifest.json"
CORPUS_ROOT = WORKSPACE_ROOT / "data" / "settlement_datasets" / "corpora" / "v007-trajectories"
RESULTS_ROOT = WORKSPACE_ROOT / "data" / "settlement_datasets" / "runs" / "v007-recovery"
PREREG_PATH = (
    WORKSPACE_ROOT / ".agents" / "reports" / "v007-experiment-preregistration.yaml"
)

SEED = 42
TEST_SIZE = 0.20
N_CV_SPLITS = 5
ECE_BINS = 10
ECE_CALIBRATION_TRIGGER = 0.05
ACCEPTANCE_MIN_DELTA = 0.02
ACCEPTANCE_MIN_SOURCES = 2
FIXED_THRESHOLD = 0.5
# Documented materiality margin above the 0.5 class-prior ROC-AUC baseline
# used only by the prereg's PARTIAL / NOT EARNED classification step.
MATERIAL_AUC_MARGIN = 0.05
# Per-source blocks below this many rows are flagged underpowered (a flag
# for readers; it gates nothing in the frozen verdicts).
MIN_EVAL_ROWS = 200

CORPUS_FILES = (
    "nebius_swe_agent.jsonl",
    "swe_smith.jsonl",
    "swegym_openhands.jsonl",
)
SOURCES = ("nebius_swe_agent", "swe_smith", "swegym_openhands")

VARIANT_WITH = "with_identity"
VARIANT_WITHOUT = "without_identity"

SCHEMA_R0 = "v007_r0"
SCHEMA_R1 = "v007_r1"
SCHEMA_ABLATION = "v005_minimal_recovery"

SCHEMA_BY_POINT = {POINT_R0: SCHEMA_R0, POINT_R1: SCHEMA_R1}
SCHEMA_FEATURES: dict[str, tuple[str, ...]] = {
    SCHEMA_R0: tuple(R0_FEATURES),
    SCHEMA_R1: tuple(R1_FEATURES),
    SCHEMA_ABLATION: tuple(V005_MINIMAL_RECOVERY_FEATURES),
}

# Frame-column aliases for schema names (``select_ablation_features``
# convention: ``error_count_so_far`` is the v006 ``error_count`` column at
# the row's cut, never a forked formula).
SCHEMA_SOURCE_COLUMN: dict[str, str] = {"error_count_so_far": "error_count"}

ARM_LR = "R_LR"
ARM_LGBM = "R_LGBM"
ESTIMATOR_BY_ARM = {ARM_LR: "logistic", ARM_LGBM: "lgbm"}

# The frozen matrix: per prediction point, both estimators on the v007
# schema (primary identity variant + preregistered without-identity
# robustness variant) and the representation-ablation R_LR arm on
# v005_minimal_recovery (both identity variants).
CELLS: tuple[dict[str, Any], ...] = tuple(
    {
        "point": point,
        "schema": SCHEMA_BY_POINT[point],
        "arm": arm,
        "variant": variant,
    }
    for point in (POINT_R0, POINT_R1)
    for arm in (ARM_LR, ARM_LGBM)
    for variant in (VARIANT_WITH, VARIANT_WITHOUT)
) + tuple(
    {
        "point": point,
        "schema": SCHEMA_ABLATION,
        "arm": ARM_LR,
        "variant": variant,
    }
    for point in (POINT_R0, POINT_R1)
    for variant in (VARIANT_WITH, VARIANT_WITHOUT)
)

# Identity/bookkeeping columns are everything on the frame that is not a
# schema feature name (dataset_id included -- it is handled by the
# identity-variant rule, refused by default).
_SCHEMA_FEATURE_NAME_SET = (
    set(R0_FEATURES) | set(R1_FEATURES) | {ABLATION_EXTRA_COLUMN}
)
NON_FEATURE_COLUMNS: tuple[str, ...] = tuple(
    sorted(set(FRAME_COLUMNS) - _SCHEMA_FEATURE_NAME_SET)
)


# ---------------------------------------------------------------------------
# Hashing and loading
# ---------------------------------------------------------------------------


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_episode_table(
    table_path: Path = EPISODE_TABLE,
    manifest_path: Path | None = None,
) -> str:
    """Abort unless the realized episode table matches its frozen manifest.

    The build manifest is expected next to the table (the v007 episode CLI
    writes them as a pair), so an alternate table carries its own manifest.
    """
    if manifest_path is None:
        manifest_path = table_path.parent / "manifest.json"
    if not table_path.exists():
        raise FileNotFoundError(f"episode table missing: {table_path}")
    if not manifest_path.exists():
        raise FileNotFoundError(f"episode-table manifest missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    digest = _sha256_file(table_path)
    expected = manifest.get("episode_table_sha256")
    if expected is None:
        raise RuntimeError("episode-table manifest records no episode_table_sha256")
    if expected != digest:
        raise RuntimeError(
            f"episode table changed after its manifest was written: {table_path} "
            f"(recorded {expected}, actual {digest})"
        )
    return digest


def load_episode_table(table_path: Path = EPISODE_TABLE) -> pd.DataFrame:
    """Load the realized episode table (one row per episode per point)."""
    frame = pd.read_json(table_path, lines=True, dtype=False)
    if frame.empty:
        raise RuntimeError(f"episode table is empty: {table_path}")
    missing = [c for c in FRAME_COLUMNS if c not in frame.columns]
    if missing:
        raise RuntimeError(f"episode table lacks frame columns: {missing}")
    return frame[list(FRAME_COLUMNS)]


# ---------------------------------------------------------------------------
# The frozen split (stratum-grouped holdout over split_group)
# ---------------------------------------------------------------------------


def group_labels_from_frame(frame: pd.DataFrame) -> dict[str, tuple[str, int]]:
    """Stratum label per split_group: ``(dataset, group_label)``.

    AMENDMENT 1 (2026-09-15, pre-round-2): holdout strata are
    (dataset, group_label) so each source contributes ~20% of its groups
    to test.  ``group_label`` = 1 iff ANY episode of the split_group has
    ``recovery_success == 1`` (operationalization of the frozen "max
    parent label in group"; parents hold multiple episodes with
    potentially different labels; ``recovery_success`` is constant within
    an episode, so a max over rows equals a max over episodes).  This is
    split STRATIFICATION only; row labels are never changed.
    """
    labels = frame.groupby(["dataset", "split_group"], sort=False)[
        "recovery_success"
    ].max()
    return {
        str(split_group): (str(dataset), int(value))
        for (dataset, split_group), value in labels.items()
    }


def stratified_group_holdout(
    group_labels: dict[str, tuple[str, int]],
    test_size: float = TEST_SIZE,
    random_state: int = SEED,
) -> tuple[list[str], list[str]]:
    """Frozen stratified group-level holdout (GroupShuffleSplit-equivalent).

    GroupShuffleSplit has no stratification support, so the frozen
    "per stratum" quantity (AMENDMENT 1: strata are ``(dataset,
    group_label)``) is realized by permuting each stratum's sorted group
    keys with ``RandomState(random_state)`` and holding out
    ``int(round(test_size * stratum_size))`` of them as test.
    A stratum holding a SINGLE group is assigned to test
    deterministically (no RNG consumed) so rare strata are never entirely
    absent from the evaluation partition.  Deterministic; test groups are
    disjoint from train groups.
    """
    rng = np.random.RandomState(random_state)
    train: list[str] = []
    test: list[str] = []
    for label in sorted(set(group_labels.values())):
        stratum = sorted(g for g, lab in group_labels.items() if lab == label)
        if len(stratum) == 1:
            test.append(stratum[0])
            continue
        if len(stratum) < 2:
            raise ValueError(
                f"stratum {label!r} has < 2 groups; stratified group "
                "holdout impossible"
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
    """Guard: no split_group straddles partitions; every group in exactly one.

    Delegates to the v007 grouping guard so the same invariant is enforced
    here as at build time.
    """
    if train_groups & test_groups:
        raise ValueError(
            f"{len(train_groups & test_groups)} split_group(s) assigned to "
            "both train and test partitions"
        )

    def split_fn(row: dict[str, Any]) -> str:
        return "test" if row["split_group"] in test_groups else "train"

    return assert_grouped_by_split_group(frame.to_dict("records"), split_fn)


# ---------------------------------------------------------------------------
# Feature matrix + guards
# ---------------------------------------------------------------------------


def assert_feature_columns(columns: list[str], *, allow_dataset_id: bool) -> None:
    """Whitelist guard: identity/label columns never enter X.

    Refuses every identity/bookkeeping column (episode ids, ``point``,
    ``e``, cut columns, ``parent_label``, ``recovery_success``,
    ``audit_bucket``, ``split_group``, ``dataset``, ``weight_base``, ...),
    every escape-derived name except the documented causal exception
    ``prior_escape_count``, and -- unless ``allow_dataset_id`` -- the
    ``dataset_id`` identity column itself.
    """
    checked = [c for c in columns if not (c == "dataset_id" and allow_dataset_id)]
    bad_identity = [c for c in checked if c in NON_FEATURE_COLUMNS]
    if bad_identity:
        raise ValueError(
            "Identity/label columns must never enter the feature matrix: "
            f"{bad_identity}"
        )
    assert_no_label_features(columns)


def feature_columns_for(schema: str, use_dataset_id: bool) -> list[str]:
    """Frozen schema columns for one (schema, identity variant).

    ``dataset_id`` is appended ONLY in the with-identity variant (it is
    already part of the ``v005_minimal_recovery@1`` schema, where the
    without-identity variant drops it instead).
    """
    if schema not in SCHEMA_FEATURES:
        raise ValueError(f"unknown schema: {schema}")
    base = list(SCHEMA_FEATURES[schema])
    if use_dataset_id:
        if "dataset_id" not in base:
            base = base + ["dataset_id"]
    else:
        base = [c for c in base if c != "dataset_id"]
    assert_feature_columns(base, allow_dataset_id=use_dataset_id)
    return base


def feature_matrix(
    frame: pd.DataFrame, schema: str, use_dataset_id: bool
) -> tuple[pd.DataFrame, pd.Series, pd.Series, pd.Series, pd.Series, pd.Series]:
    """X, y, groups(split_group), dataset, parent_id, episode_id for a cell."""
    points = set(frame["point"].unique())
    expected_point = POINT_R0 if schema == SCHEMA_R0 else (
        POINT_R1 if schema == SCHEMA_R1 else None
    )
    if expected_point is not None and points != {expected_point}:
        raise ValueError(
            f"schema {schema} requires point={expected_point}, frame has {points}"
        )
    cols = feature_columns_for(schema, use_dataset_id)
    source_cols = [SCHEMA_SOURCE_COLUMN.get(c, c) for c in cols]
    missing = [c for c in source_cols if c not in frame.columns]
    if missing:
        raise ValueError(f"frame lacks feature columns for {schema}: {missing}")
    X = frame[source_cols].astype(float)
    X.columns = cols  # schema names (aliases applied)
    values = X.to_numpy()
    if not np.isfinite(values).all():
        raise ValueError(f"non-finite feature values in {schema} matrix")
    return (
        X,
        frame["recovery_success"].astype(int),
        frame["split_group"].astype(str),
        frame["dataset"].astype(str),
        frame["parent_id"].astype(str),
        frame["episode_id"].astype(str),
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


def _groupkfold(
    groups: pd.Series, n_splits: int = N_CV_SPLITS
) -> list[tuple[np.ndarray, np.ndarray]]:
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
    schema: str,
    estimator_name: str,
    use_dataset_id: bool,
    weights: np.ndarray | None = None,
    n_splits: int = N_CV_SPLITS,
) -> dict[str, Any]:
    """Frozen selection: mean GroupKFold(5) train ROC-AUC, tiebreak mean AP.

    STRUCTURAL GUARANTEE: this function takes the TRAIN frame only -- there
    is no parameter through which test rows could enter selection.
    """
    X, y, groups, _, _, _ = feature_matrix(train_frame, schema, use_dataset_id)
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
    schema: str,
    estimator_name: str,
    params: dict[str, Any],
    use_dataset_id: bool,
    weights: np.ndarray | None = None,
    n_splits: int = N_CV_SPLITS,
) -> np.ndarray:
    """Out-of-fold TRAIN predictions for the selected model (calibration input)."""
    X, y, groups, _, _, _ = feature_matrix(train_frame, schema, use_dataset_id)
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
    }
    if oof_ece > trigger:
        iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        iso.fit(oof_probs, y_train)
        result["applied"] = True
        result["test_probs_calibrated"] = np.asarray(
            iso.predict(test_probs), dtype=float
        )
    else:
        result["test_probs_calibrated"] = test_probs
    return result


def evaluate_probs(y_true: np.ndarray, probs: np.ndarray) -> dict[str, Any]:
    """Episode-level metric block for one cell (fixed 0.5 threshold)."""
    y = np.asarray(y_true, dtype=int)
    p = np.asarray(probs, dtype=float)
    n = int(len(y))
    n_pos = int(y.sum())
    n_neg = n - n_pos
    underpowered = n < MIN_EVAL_ROWS or n_pos == 0 or n_neg == 0
    pred = (p >= FIXED_THRESHOLD).astype(int)
    tn, fp, fn, tp = (
        (int(v) for v in confusion_matrix(y, pred, labels=[0, 1]).ravel())
        if n
        else (0, 0, 0, 0)
    )
    metrics: dict[str, Any] = {
        "n_test_rows": n,
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
        "confusion_matrix": {"tn": tn, "fp": fp, "fn": fn, "tp": tp},
        "underpowered": bool(underpowered),
    }
    if n_pos > 0 and n_neg > 0:
        metrics["roc_auc"] = float(roc_auc_score(y, p))
        metrics["ap"] = float(average_precision_score(y, p))
    return metrics


def parent_aggregated_auc(
    y: pd.Series, probs: np.ndarray, parent_id: pd.Series
) -> float | None:
    """Multiplicity-inflation check: AUC over parents after within-parent
    probability averaging.

    A parent is labeled 1 iff ANY of its episodes in the evaluation set has
    ``recovery_success == 1`` (the same ANY-episode convention as the split
    strata); raw model probabilities are averaged per parent.
    """
    y = np.asarray(y, dtype=int)
    p = np.asarray(probs, dtype=float)
    parents = np.asarray(parent_id, dtype=str)
    means: dict[str, list[float]] = {}
    labels: dict[str, int] = {}
    for pid, prob, label in zip(parents, p, y):
        means.setdefault(pid, []).append(float(prob))
        labels[pid] = max(labels.get(pid, 0), int(label))
    p_parent = np.array([float(np.mean(means[pid])) for pid in sorted(means)])
    y_parent = np.array([labels[pid] for pid in sorted(means)], dtype=int)
    if y_parent.max() == 0 or y_parent.min() == 1:
        return None
    return float(roc_auc_score(y_parent, p_parent))


def per_source_metrics(
    y: pd.Series, probs: np.ndarray, datasets: pd.Series
) -> dict[str, Any]:
    """Per-source metric blocks + macro-source (unweighted mean over the
    three sources)."""
    out: dict[str, Any] = {}
    y_arr = np.asarray(y, dtype=int)
    for dataset in SOURCES:
        mask = (datasets == dataset).to_numpy()
        block = evaluate_probs(y_arr[mask], np.asarray(probs)[mask])
        block["macro_eligible"] = (
            block["roc_auc"] is not None and not block["underpowered"]
        )
        out[dataset] = block
    aucs = [
        b["roc_auc"]
        for b in out.values()
        if isinstance(b, dict) and b.get("roc_auc") is not None
    ]
    eligible = [b for b in out.values() if isinstance(b, dict) and b["macro_eligible"]]
    out["_macro_roc_auc"] = (
        float(np.mean([b["roc_auc"] for b in eligible])) if eligible else None
    )
    out["_macro_over_all_sources"] = bool(len(eligible) == len(SOURCES))
    out["_n_sources_with_auc"] = len(aucs)  # type: ignore[assignment]
    return out


def feature_importance(
    est: Any,
    estimator_name: str,
    columns: list[str],
    X_train: pd.DataFrame,
    top_k: int = 15,
) -> list[dict[str, Any]]:
    """Top-k importance: LR |std-coef| (|coef| x train-std); LGBM gain."""
    if estimator_name == "logistic":
        coef = np.asarray(est.coef_[0], dtype=float)
        std = X_train.std(ddof=0).to_numpy(dtype=float)
        score = np.abs(coef) * std
    elif estimator_name == "lgbm":
        score = np.asarray(
            est.booster_.feature_importance(importance_type="gain"), dtype=float
        )
    else:
        raise ValueError(f"unknown estimator: {estimator_name}")
    order = np.argsort(-score)[:top_k]
    return [
        {"feature": str(columns[i]), "importance": float(score[i])}
        for i in order
    ]


# ---------------------------------------------------------------------------
# One frozen cell: selection -> fit -> OOF calibration -> single test eval
# ---------------------------------------------------------------------------


def run_cell(
    train_frame: pd.DataFrame,
    test_frame: pd.DataFrame,
    schema: str,
    estimator_name: str,
    use_dataset_id: bool,
    n_splits: int = N_CV_SPLITS,
) -> dict[str, Any]:
    """Full frozen path for one (point, schema, arm, identity variant).

    Everything except the ``evaluate_probs`` / ``per_source_metrics`` calls
    at the end operates on the train partition; those final calls are the
    one touch of test data for this cell.
    """
    weights = parent_balanced_training_weights(train_frame).to_numpy(dtype=float)
    selection = select_hyperparameters(
        train_frame, schema, estimator_name, use_dataset_id,
        weights=weights, n_splits=n_splits,
    )
    X_tr, y_tr, _, _, _, _ = feature_matrix(train_frame, schema, use_dataset_id)
    X_te, y_te, g_te, ds_te, pid_te, eid_te = feature_matrix(
        test_frame, schema, use_dataset_id
    )

    est = make_estimator(estimator_name, selection["best_params"])
    _fit(est, X_tr, y_tr, weights)
    p_test = _proba(est, X_te)

    oof = oof_train_predictions(
        train_frame, schema, estimator_name, selection["best_params"],
        use_dataset_id, weights=weights, n_splits=n_splits,
    )
    cal = maybe_calibrate(oof, y_tr.to_numpy(), p_test)

    metrics = evaluate_probs(y_te.to_numpy(), p_test)
    calibrated = evaluate_probs(y_te.to_numpy(), cal["test_probs_calibrated"])
    metrics["brier_after_calibration"] = calibrated["brier"]
    metrics["ece_after_calibration"] = calibrated["ece"]
    metrics["per_source"] = per_source_metrics(y_te, p_test, ds_te)
    metrics["parent_aggregated_auc"] = parent_aggregated_auc(y_te, p_test, pid_te)
    metrics["parent_aggregated_auc_calibrated"] = parent_aggregated_auc(
        y_te, cal["test_probs_calibrated"], pid_te
    )

    return {
        "point": str(test_frame["point"].iloc[0]),
        "schema": schema,
        "estimator": estimator_name,
        "identity_variant": VARIANT_WITH if use_dataset_id else VARIANT_WITHOUT,
        "selection": selection,
        "oof_ece": cal["oof_ece"],
        "calibration_applied": bool(cal["applied"]),
        "metrics": metrics,
        "importance": feature_importance(est, estimator_name, list(X_tr.columns), X_tr),
        "test_predictions": {
            "episode_id": eid_te.tolist(),
            "parent_id": pid_te.tolist(),
            "split_group": g_te.tolist(),
            "dataset": ds_te.tolist(),
            "y": y_te.astype(int).tolist(),
            "p_raw": [float(v) for v in p_test],
            "p_calibrated": [
                float(v) for v in cal["test_probs_calibrated"]
            ],
            "calibration_applied": bool(cal["applied"]),
        },
    }


# ---------------------------------------------------------------------------
# Leave-one-source-out (co-reporting; train partition only)
# ---------------------------------------------------------------------------


def run_loso(
    train_point_frame: pd.DataFrame,
    schema: str,
    estimator_name: str,
    best_params: dict[str, Any],
    use_dataset_id: bool = True,
) -> dict[str, Any]:
    """3-fold LOSO over the three sources, INSIDE the train partition.

    Fold s: train on the other two sources' train rows, evaluate on source
    s's train rows.  No re-tuning -- the globally selected hyperparameters
    of the owning cell are reused; the frozen parent-balanced weights are
    recomputed on each LOSO train frame.  The test partition is never
    touched here, preserving the frozen single-touch rule.
    """
    folds: dict[str, Any] = {}
    for held_out in SOURCES:
        tr = train_point_frame[train_point_frame["dataset"] != held_out]
        ev = train_point_frame[train_point_frame["dataset"] == held_out]
        if tr.empty or ev.empty:
            folds[held_out] = {"not_defined": True, "reason": "empty fold partition"}
            continue
        if ev["recovery_success"].nunique() < 2:
            folds[held_out] = {
                "not_defined": True,
                "reason": "held-out source single-class in train partition",
            }
            continue
        w = parent_balanced_training_weights(tr).to_numpy(dtype=float)
        X_tr, y_tr, _, _, _, _ = feature_matrix(tr, schema, use_dataset_id)
        X_ev, y_ev, _, _, _, _ = feature_matrix(ev, schema, use_dataset_id)
        est = make_estimator(estimator_name, best_params)
        _fit(est, X_tr, y_tr, w)
        p = _proba(est, X_ev)
        folds[held_out] = {
            "roc_auc": float(roc_auc_score(y_ev, p)),
            "ap": float(average_precision_score(y_ev, p)),
            "n_eval_rows": int(len(y_ev)),
            "n_eval_positives": int(y_ev.sum()),
            "n_train_rows": int(len(y_tr)),
        }
    return {
        "note": (
            "train-without-source -> held-out-source evaluation inside the "
            "TRAIN partition (test untouched); globally selected "
            "hyperparameters reused (no re-tuning); parent-balanced weights "
            "recomputed per fold"
        ),
        "folds": folds,
    }


# ---------------------------------------------------------------------------
# Acceptance rules (pure; hand-fixture-tested)
# ---------------------------------------------------------------------------


def evaluate_acceptance(
    delta_primary: float | None,
    per_source_direction: dict[str, bool | None],
    delta_without_identity: float | None,
    min_delta: float = ACCEPTANCE_MIN_DELTA,
    min_sources: int = ACCEPTANCE_MIN_SOURCES,
) -> dict[str, Any]:
    """Frozen acceptance rule for one hypothesis at one prediction point.

    ``delta_primary`` is treatment-minus-baseline episode-level test
    ROC-AUC in the primary (with-identity) variant; ``per_source_direction``
    records whether the treatment beats the baseline in each per-source
    cell (strictly greater); ``delta_without_identity`` is the same delta
    in the preregistered without-identity variant.

    EARNED iff delta_primary >= min_delta AND >= min_sources sources hold
    the direction AND the without-identity delta does not reverse sign.
    """
    held = sum(1 for v in per_source_direction.values() if v is True)
    gain = delta_primary is not None and delta_primary >= min_delta
    identity_reversed = bool(
        gain
        and delta_without_identity is not None
        and delta_without_identity < 0
    )
    earned = bool(gain and held >= min_sources and not identity_reversed)
    if earned:
        verdict = "EARNED"
    elif gain and identity_reversed:
        verdict = "NOT EARNED (identity-reversed)"
    else:
        verdict = "NOT EARNED"
    return {
        "earned": earned,
        "verdict": verdict,
        "delta_primary": delta_primary,
        "delta_without_identity": delta_without_identity,
        "per_source_direction": per_source_direction,
        "sources_held": held,
        "sources_required": min_sources,
        "min_delta": min_delta,
        "identity_reversed": identity_reversed,
    }


def classify_outcome(
    primary_by_point: dict[str, dict[str, Any]],
    secondary_by_point: dict[str, dict[str, Any]],
    best_point_auc: dict[str, float | None],
    material_margin: float = MATERIAL_AUC_MARGIN,
) -> dict[str, Any]:
    """Mechanical SETTLED-earned / PARTIAL / NOT EARNED classification.

    SETTLED-earned when the primary hypothesis is earned at any point;
    otherwise PARTIAL when at least one point clears the class-prior
    baseline materially (ROC-AUC >= 0.5 + margin) or the secondary
    hypothesis is earned; otherwise NOT EARNED.  BLOCKED is reserved for
    an unconstructible experiment and is never returned by a completed run.
    """
    primary_earned = [p for p, r in primary_by_point.items() if r["earned"]]
    secondary_earned = [p for p, r in secondary_by_point.items() if r["earned"]]
    materially_above = sorted(
        p
        for p, auc in best_point_auc.items()
        if auc is not None and auc >= 0.5 + material_margin
    )
    if primary_earned:
        verdict = "SETTLED-earned"
    elif materially_above or secondary_earned:
        verdict = "PARTIAL"
    else:
        verdict = "NOT EARNED"
    return {
        "classification": verdict,
        "primary_earned_points": sorted(primary_earned),
        "secondary_earned_points": sorted(secondary_earned),
        "points_materially_above_prior": materially_above,
        "material_margin": material_margin,
        "class_prior_baseline_roc_auc": 0.5,
    }


def delta_of(treatment: dict[str, Any], baseline: dict[str, Any]) -> float | None:
    """Treatment-minus-baseline episode-level ROC-AUC (None if unevaluable)."""
    t = treatment["metrics"]["roc_auc"]
    b = baseline["metrics"]["roc_auc"]
    if t is None or b is None:
        return None
    return float(t) - float(b)


def per_source_direction(
    treatment: dict[str, Any], baseline: dict[str, Any]
) -> dict[str, bool | None]:
    """Whether the treatment beats the baseline in each per-source cell."""
    out: dict[str, bool | None] = {}
    t_src = treatment["metrics"]["per_source"]
    b_src = baseline["metrics"]["per_source"]
    for source in SOURCES:
        t_auc = t_src[source]["roc_auc"]
        b_auc = b_src[source]["roc_auc"]
        if t_auc is None or b_auc is None:
            out[source] = None
        else:
            out[source] = bool(t_auc > b_auc)
    return out


# ---------------------------------------------------------------------------
# Representative predictions
# ---------------------------------------------------------------------------


def representative_examples(
    block: dict[str, Any],
    test_frame: pd.DataFrame,
    top_k_features: int = 5,
    n_each: int = 3,
) -> dict[str, Any]:
    """3 highest-confidence correct + 3 incorrect rows for one cell.

    Confidence of a correct prediction is p toward the true label
    (p if y == 1 else 1 - p); of an incorrect prediction, confidence in the
    wrong direction.  Each example carries the arm's top-k important
    feature values from the episode's row.
    """
    preds = block["test_predictions"]
    top = [entry["feature"] for entry in block["importance"][:top_k_features]]
    lookup = test_frame.set_index("episode_id")
    rows: list[dict[str, Any]] = []
    for i, eid in enumerate(preds["episode_id"]):
        y, p = preds["y"][i], preds["p_raw"][i]
        correct = (p >= FIXED_THRESHOLD) == bool(y)
        confidence = p if y == 1 else 1.0 - p
        if not correct:
            confidence = 1.0 - confidence
        row = {
            "episode_id": eid,
            "parent_id": preds["parent_id"][i],
            "split_group": preds["split_group"][i],
            "dataset": preds["dataset"][i],
            "y": int(y),
            "p_raw": float(p),
            "correct": bool(correct),
            "confidence": float(confidence),
        }
        if eid in lookup.index:
            record = lookup.loc[eid]
            if isinstance(record, pd.DataFrame):  # duplicate ids would be a bug
                record = record.iloc[0]
            row["feature_values"] = {
                feature: float(record[feature]) for feature in top
            }
        rows.append(row)
    correct_rows = sorted(
        (r for r in rows if r["correct"]),
        key=lambda r: r["confidence"],
        reverse=True,
    )[:n_each]
    incorrect_rows = sorted(
        (r for r in rows if not r["correct"]),
        key=lambda r: r["confidence"],
        reverse=True,
    )[:n_each]
    return {
        "point": block["point"],
        "arm": ARM_BY_ESTIMATOR[block["estimator"]],
        "schema": block["schema"],
        "identity_variant": block["identity_variant"],
        "top_features": top,
        "highest_confidence_correct": correct_rows,
        "highest_confidence_incorrect": incorrect_rows,
    }


ARM_BY_ESTIMATOR = {v: k for k, v in ESTIMATOR_BY_ARM.items()}


# ---------------------------------------------------------------------------
# Matrix orchestration
# ---------------------------------------------------------------------------


def _point_frame(frame: pd.DataFrame, point: str) -> pd.DataFrame:
    sub = frame[frame["point"] == point]
    if sub.empty:
        raise RuntimeError(f"point {point!r} has no rows")
    return sub


def _cell_id(cell: dict[str, Any]) -> str:
    return f"{cell['point']}|{cell['arm']}|{cell['schema']}|{cell['variant']}"


def run_matrix(
    episode_table: Path = EPISODE_TABLE,
    results_root: Path = RESULTS_ROOT,
    corpus_root: Path = CORPUS_ROOT,
    log: bool = True,
) -> dict[str, Any]:
    t_start = time.time()
    table_sha = verify_episode_table(episode_table)
    build_manifest_path = episode_table.parent / "manifest.json"
    build_manifest = json.loads(build_manifest_path.read_text(encoding="utf-8"))
    prereg_sha = _sha256_file(PREREG_PATH)
    # corpus_root is CLI-selectable (C3 round-3 rerun consumes the corrected
    # v007c-trajectories corpus so manifest provenance matches the table);
    # the frozen design (cells, seeds, splits, grids) is untouched.
    corpus_shas = {name: _sha256_file(corpus_root / name) for name in CORPUS_FILES}

    frame = load_episode_table(episode_table)
    n_episodes = int(frame["episode_id"].nunique())
    if log:
        print(f"loaded episode table: {len(frame)} rows, {n_episodes} episodes")

    group_labels = group_labels_from_frame(frame)
    train_groups, test_groups = stratified_group_holdout(group_labels)
    train_set, test_set = set(train_groups), set(test_groups)
    n_checked = assert_partitions_grouped(frame, train_set, test_set)
    if log:
        print(
            f"holdout: {len(train_groups)} train / {len(test_groups)} test "
            f"split_groups ({n_checked} checked); "
            f"strata {sorted({group_labels[g] for g in test_groups})}"
        )

    split_frame = frame.copy()
    split_frame["_partition"] = np.where(
        split_frame["split_group"].isin(test_set), "test", "train"
    )

    cells_results: dict[str, dict[str, Any]] = {}
    for cell in CELLS:
        point, schema, arm, variant = (
            cell["point"], cell["schema"], cell["arm"], cell["variant"]
        )
        use_dataset_id = variant == VARIANT_WITH
        point_rows = _point_frame(split_frame, point)
        train = point_rows[point_rows["_partition"] == "train"]
        test = point_rows[point_rows["_partition"] == "test"]
        t0 = time.time()
        block = run_cell(
            train, test, schema, ESTIMATOR_BY_ARM[arm], use_dataset_id
        )
        block["cell_id"] = _cell_id(cell)
        cells_results[block["cell_id"]] = block
        auc = block["metrics"]["roc_auc"]
        if log:
            print(
                f"  {block['cell_id']}: auc={auc if auc is not None else 'n/a'} "
                f"ap={block['metrics']['ap']} "
                f"oof_ece={block['oof_ece']:.4f} "
                f"calibrated={block['calibration_applied']} "
                f"({time.time() - t0:.1f}s)",
                flush=True,
            )

    # ---- co-reported LOSO for the with-identity cells ----------------------
    loso_results: dict[str, Any] = {}
    for cell in CELLS:
        if cell["variant"] != VARIANT_WITH:
            continue
        point, schema = cell["point"], cell["schema"]
        cell_key = _cell_id(cell)
        block = cells_results[cell_key]
        point_rows = _point_frame(split_frame, point)
        loso_results[cell_key] = run_loso(
            point_rows[point_rows["_partition"] == "train"],
            schema,
            block["estimator"],
            block["selection"]["best_params"],
        )
        if log:
            aucs = {
                s: f.get("roc_auc")
                for s, f in loso_results[cell_key]["folds"].items()
                if isinstance(f, dict)
            }
            print(f"  LOSO {cell_key}: {aucs}", flush=True)

    # ---- frozen acceptance, mechanically applied ---------------------------
    def cell_key_for(point: str, arm: str, variant: str, schema: str) -> str:
        return f"{point}|{arm}|{schema}|{variant}"

    acceptance: dict[str, Any] = {"primary": {}, "secondary": {}}
    for point in (POINT_R0, POINT_R1):
        schema = SCHEMA_BY_POINT[point]
        lgbm = cells_results[cell_key_for(point, ARM_LGBM, VARIANT_WITH, schema)]
        lr = cells_results[cell_key_for(point, ARM_LR, VARIANT_WITH, schema)]
        lgbm_wo = cells_results[cell_key_for(point, ARM_LGBM, VARIANT_WITHOUT, schema)]
        lr_wo = cells_results[cell_key_for(point, ARM_LR, VARIANT_WITHOUT, schema)]
        acceptance["primary"][point] = evaluate_acceptance(
            delta_of(lgbm, lr),
            per_source_direction(lgbm, lr),
            delta_of(lgbm_wo, lr_wo),
        )
        abl = cells_results[cell_key_for(point, ARM_LR, VARIANT_WITH, SCHEMA_ABLATION)]
        acceptance["secondary"][point] = evaluate_acceptance(
            delta_of(lr, abl),
            per_source_direction(lr, abl),
            None,  # prereg gates the secondary hypothesis on per-source
                   # direction only; no identity-reversal clause
        )

    def best_with_identity_auc(point: str) -> float | None:
        aucs = [
            cells_results[cell_key_for(point, arm, VARIANT_WITH, schema)][
                "metrics"
            ]["roc_auc"]
            for arm, schema in (
                (ARM_LR, SCHEMA_BY_POINT[point]),
                (ARM_LGBM, SCHEMA_BY_POINT[point]),
                (ARM_LR, SCHEMA_ABLATION),
            )
        ]
        scored = [a for a in aucs if a is not None]
        return max(scored) if scored else None

    best_point_auc = {
        point: best_with_identity_auc(point) for point in (POINT_R0, POINT_R1)
    }
    classification = classify_outcome(
        acceptance["primary"], acceptance["secondary"], best_point_auc
    )

    # ---- representative predictions for the best arm per point -------------
    representatives: dict[str, Any] = {}
    for point in (POINT_R0, POINT_R1):
        schema = SCHEMA_BY_POINT[point]
        candidates = [
            cells_results[cell_key_for(point, arm, VARIANT_WITH, schema)]
            for arm in (ARM_LR, ARM_LGBM)
        ] + [
            cells_results[cell_key_for(point, ARM_LR, VARIANT_WITH, SCHEMA_ABLATION)]
        ]
        best = max(
            candidates,
            key=lambda b: (
                b["metrics"]["roc_auc"] is not None,
                b["metrics"]["roc_auc"] or -1.0,
            ),
        )
        point_rows = _point_frame(split_frame, point)
        representatives[point] = representative_examples(
            best, point_rows[point_rows["_partition"] == "test"]
        )

    # ---- calibration summary ----------------------------------------------
    calibration_summary = {
        "rule": "OOF GroupKFold isotonic on the selected model iff OOF ECE > 0.05; never fit on test",
        "trigger": ECE_CALIBRATION_TRIGGER,
        "cells": {
            key: {
                "point": b["point"],
                "arm": ARM_BY_ESTIMATOR[b["estimator"]],
                "schema": b["schema"],
                "identity_variant": b["identity_variant"],
                "oof_ece": b["oof_ece"],
                "applied": b["calibration_applied"],
                "test_brier_raw": b["metrics"]["brier"],
                "test_brier_calibrated": b["metrics"]["brier_after_calibration"],
                "test_ece_raw": b["metrics"]["ece"],
                "test_ece_calibrated": b["metrics"]["ece_after_calibration"],
                "brier_improved": (
                    b["metrics"]["brier_after_calibration"] < b["metrics"]["brier"]
                    if b["metrics"]["brier"] is not None
                    and b["metrics"]["brier_after_calibration"] is not None
                    else None
                ),
            }
            for key, b in cells_results.items()
        },
    }
    applied = [v for v in calibration_summary["cells"].values() if v["applied"]]
    calibration_summary["n_cells"] = len(calibration_summary["cells"])
    calibration_summary["n_triggered"] = len(applied)
    calibration_summary["isotonic_improved_mean_test_brier"] = (
        bool(applied)
        and float(np.mean([v["test_brier_calibrated"] for v in applied]))
        < float(np.mean([v["test_brier_raw"] for v in applied]))
    )

    # ---- artifacts ---------------------------------------------------------
    results_root.mkdir(parents=True, exist_ok=True)
    per_cell_sizes = {
        key: {
            "point": b["point"],
            "schema": b["schema"],
            "arm": ARM_BY_ESTIMATOR[b["estimator"]],
            "identity_variant": b["identity_variant"],
            "n_train_rows": b["selection"]["n_train_rows"],
            "n_train_groups": b["selection"]["n_train_groups"],
            "n_train_positives": b["selection"]["n_train_positives"],
            "n_test_rows": b["metrics"]["n_test_rows"],
            "n_test_positives": b["metrics"]["n_test_positives"],
        }
        for key, b in cells_results.items()
    }

    manifest = {
        "plan": "godspeed-agent-v007-recovery-prediction",
        "task": "T03",
        "preregistration_id": "v007-recovery",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "runtime_seconds": time.time() - t_start,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "versions": {
            "scikit-learn": sklearn.__version__,
            "lightgbm": __import__("lightgbm").__version__
            if LGBMClassifier is not None
            else None,
            "pandas": pd.__version__,
            "numpy": np.__version__,
        },
        "seeds": {
            "random_state": SEED,
            "test_size": TEST_SIZE,
            "cv_splits": N_CV_SPLITS,
        },
        "determinism_flags": {
            "lgbm": ["deterministic=True", "force_col_wise=True", "n_jobs=1"]
        },
        "preregistration": {
            "path": str(PREREG_PATH),
            "sha256": prereg_sha,
            "frozen_at": "2026-09-15",
        },
        "episode_table": {
            "path": str(episode_table),
            "sha256": table_sha,
            "build_manifest_path": str(build_manifest_path),
            "build_manifest_sha256": _sha256_file(build_manifest_path),
            "episodes_id": build_manifest.get("episodes_id"),
            "rows": int(len(frame)),
            "episodes": n_episodes,
            "rows_by_point": {
                str(k): int(v)
                for k, v in frame["point"].value_counts().items()
            },
        },
        "corpus": {
            "root": str(corpus_root),
            "sha256_by_file": corpus_shas,
        },
        "group_label_definition": (
            "split stratification ONLY (AMENDMENT 1: strata are "
            "(dataset, group_label)): group_label = 1 iff ANY episode of "
            "the split_group has recovery_success == 1 (operationalization "
            "of the frozen 'max parent label in group'; parents hold "
            "multiple episodes with potentially different labels). Row "
            "labels are never changed."
        ),
        "weights_definition": (
            "sample_weight = 1/(number of TRAINING episodes of that parent) "
            "per episode row (parent_balanced_training_weights; episodes "
            "counted as distinct episode_id per parent, per point); applied "
            "to fit only, never to metric computation"
        ),
        "parent_aggregated_definition": (
            "parents labeled 1 iff ANY of their evaluation episodes has "
            "recovery_success == 1; raw predicted probabilities averaged "
            "per parent before AUC"
        ),
        "headline_probability": (
            "headline episode-level metrics are computed on RAW model "
            "probabilities; calibration changes Brier/ECE only (isotonic is "
            "monotone)"
        ),
        "loso_scope": (
            "with-identity cells; train-without-source -> held-out-source "
            "inside the TRAIN partition; no re-tuning; test untouched"
        ),
        "split": {
            "strategy": (
                "AMENDMENT 1 (2026-09-15, pre-round-2): stratum-grouped "
                "holdout over split_group with strata (dataset, group_label); "
                "each source contributes ~20% of its groups to test (a "
                "single-group stratum is assigned to test deterministically). "
                "group_label = 1 iff ANY episode of the split_group has "
                "recovery_success == 1; split stratification only, row "
                "labels unchanged. Round-1 (strata on group_label alone) "
                "produced a test partition with zero swegym rows and is "
                "preserved at runs/v007-recovery/round1-stratum-defect/."
            ),
            "train_groups": len(train_groups),
            "test_groups": len(test_groups),
            "train_rows": int((split_frame["_partition"] == "train").sum()),
            "test_rows": int((split_frame["_partition"] == "test").sum()),
            "test_positives": int(
                split_frame.loc[
                    split_frame["_partition"] == "test", "recovery_success"
                ].sum()
            ),
            "composition_by_source": {
                source: {
                    "train_groups": int(
                        split_frame.loc[
                            (split_frame["dataset"] == source)
                            & (split_frame["_partition"] == "train"),
                            "split_group",
                        ].nunique()
                    ),
                    "test_groups": int(
                        split_frame.loc[
                            (split_frame["dataset"] == source)
                            & (split_frame["_partition"] == "test"),
                            "split_group",
                        ].nunique()
                    ),
                    "train_rows": int(
                        (
                            (split_frame["dataset"] == source)
                            & (split_frame["_partition"] == "train")
                        ).sum()
                    ),
                    "test_rows": int(
                        (
                            (split_frame["dataset"] == source)
                            & (split_frame["_partition"] == "test")
                        ).sum()
                    ),
                    "test_positives": int(
                        split_frame.loc[
                            (split_frame["dataset"] == source)
                            & (split_frame["_partition"] == "test"),
                            "recovery_success",
                        ].sum()
                    ),
                }
                for source in SOURCES
            },
        },
        "per_cell_sizes": per_cell_sizes,
        "schema_versions": dict(SCHEMA_VERSIONS),
        "matrix": [
            {"cell_id": _cell_id(cell), **cell} for cell in CELLS
        ],
        "artifacts_written_at": time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
        ),
    }

    results_payload = {
        "preregistration_sha256": prereg_sha,
        "episode_table_sha256": table_sha,
        "split": manifest["split"],
        "cells": {
            key: {
                "cell_id": b["cell_id"],
                "point": b["point"],
                "schema": b["schema"],
                "estimator": b["estimator"],
                "identity_variant": b["identity_variant"],
                "selection": b["selection"],
                "oof_ece": b["oof_ece"],
                "calibration_applied": b["calibration_applied"],
                "metrics": b["metrics"],
            }
            for key, b in cells_results.items()
        },
        "loso": loso_results,
        "acceptance": acceptance,
        "classification": classification,
        "representatives_note": "see representative_examples.json",
    }

    # results.json
    results_path = results_root / "results.json"
    results_path.write_text(
        json.dumps(results_payload, indent=2, default=str), encoding="utf-8"
    )
    # experiment_manifest.json
    manifest_path = results_root / "experiment_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, default=str), encoding="utf-8"
    )
    # calibration_summary.json
    calibration_path = results_root / "calibration_summary.json"
    calibration_path.write_text(
        json.dumps(calibration_summary, indent=2, default=str), encoding="utf-8"
    )
    # feature_importance.json
    importance_payload = {
        key: {
            "point": b["point"],
            "arm": ARM_BY_ESTIMATOR[b["estimator"]],
            "schema": b["schema"],
            "identity_variant": b["identity_variant"],
            "importance": b["importance"],
        }
        for key, b in cells_results.items()
    }
    importance_path = results_root / "feature_importance.json"
    importance_path.write_text(
        json.dumps(importance_payload, indent=2, default=str), encoding="utf-8"
    )
    # representative_examples.json
    examples_path = results_root / "representative_examples.json"
    examples_path.write_text(
        json.dumps(representatives, indent=2, default=str), encoding="utf-8"
    )
    # per_point_results.csv
    csv_rows = []
    for key, b in cells_results.items():
        m = b["metrics"]
        csv_rows.append(
            {
                "cell_id": b["cell_id"],
                "point": b["point"],
                "arm": ARM_BY_ESTIMATOR[b["estimator"]],
                "schema": b["schema"],
                "identity_variant": b["identity_variant"],
                "n_train_rows": b["selection"]["n_train_rows"],
                "n_test_rows": m["n_test_rows"],
                "n_test_positives": m["n_test_positives"],
                "class_balance": m["class_balance"],
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
                "parent_aggregated_auc": m["parent_aggregated_auc"],
                "macro_source_roc_auc": m["per_source"]["_macro_roc_auc"],
                "oof_ece": b["oof_ece"],
                "calibration_applied": b["calibration_applied"],
                "brier_after_calibration": m["brier_after_calibration"],
                "ece_after_calibration": m["ece_after_calibration"],
                "best_params": json.dumps(
                    b["selection"]["best_params"], sort_keys=True
                ),
            }
        )
    csv_path = results_root / "per_point_results.csv"
    pd.DataFrame(csv_rows).to_csv(csv_path, index=False)
    # test_predictions.jsonl
    pred_path = results_root / "test_predictions.jsonl"
    with pred_path.open("w", encoding="utf-8") as f:
        for key, b in cells_results.items():
            tp = b["test_predictions"]
            for i, eid in enumerate(tp["episode_id"]):
                f.write(
                    json.dumps(
                        {
                            "point": b["point"],
                            "arm": ARM_BY_ESTIMATOR[b["estimator"]],
                            "schema": b["schema"],
                            "variant": b["identity_variant"],
                            "episode_id": eid,
                            "parent_id": tp["parent_id"][i],
                            "split_group": tp["split_group"][i],
                            "dataset": tp["dataset"][i],
                            "y": tp["y"][i],
                            "p_raw": tp["p_raw"][i],
                            "p_calibrated": (
                                tp["p_calibrated"][i]
                                if tp["calibration_applied"]
                                else None
                            ),
                        }
                    )
                    + "\n"
                )

    if log:
        print("\n=== HEADLINE (episode-level test ROC-AUC, raw probs) ===")
        for point in (POINT_R0, POINT_R1):
            for arm in (ARM_LR, ARM_LGBM):
                for variant in (VARIANT_WITH, VARIANT_WITHOUT):
                    key = cell_key_for(
                        point, arm, variant, SCHEMA_BY_POINT[point]
                    )
                    auc = cells_results[key]["metrics"]["roc_auc"]
                    print(
                        f"{point} {arm:<6} {variant:<17} auc="
                        f"{auc if auc is not None else 'n/a'}"
                    )
            key = cell_key_for(point, ARM_LR, VARIANT_WITH, SCHEMA_ABLATION)
            auc = cells_results[key]["metrics"]["roc_auc"]
            print(f"{point} R_LR   {SCHEMA_ABLATION:<17} auc={auc}")
        print("\n=== PREREGISTERED ACCEPTANCE ===")
        for hypothesis, by_point in acceptance.items():
            for point, verdict in by_point.items():
                print(
                    f"{hypothesis}@{point}: {verdict['verdict']} "
                    f"(delta={verdict['delta_primary']}, "
                    f"without_identity={verdict['delta_without_identity']}, "
                    f"sources_held={verdict['sources_held']})"
                )
        print(f"classification: {classification['classification']}")
        print(f"\nartifacts under {results_root}")
        print(f"total runtime {time.time() - t_start:.1f}s")

    return {
        "manifest": manifest,
        "results": results_payload,
        "classification": classification,
        "paths": {
            "results": str(results_path),
            "manifest": str(manifest_path),
            "calibration_summary": str(calibration_path),
            "feature_importance": str(importance_path),
            "representative_examples": str(examples_path),
            "per_point_results_csv": str(csv_path),
            "test_predictions_jsonl": str(pred_path),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the frozen v007 recovery-prediction experiment matrix (T03)."
    )
    parser.add_argument(
        "--episode-table", type=Path, default=EPISODE_TABLE,
        help="Path to the realized v007 episode table (episodes.jsonl)",
    )
    parser.add_argument(
        "--results-root", type=Path, default=RESULTS_ROOT,
        help="Directory under which experiment artifacts are written",
    )
    parser.add_argument(
        "--corpus-root", type=Path, default=CORPUS_ROOT,
        help=(
            "Trajectory-corpus directory recorded for provenance sha256s "
            "(C3: pass the corrected v007c-trajectories corpus when "
            "--episode-table points at v007c-episodes)"
        ),
    )
    args = parser.parse_args(argv)
    run_matrix(
        episode_table=args.episode_table,
        results_root=args.results_root,
        corpus_root=args.corpus_root,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
