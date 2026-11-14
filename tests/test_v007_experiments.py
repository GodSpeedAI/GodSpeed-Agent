"""Tests for the frozen v007 experiment runner (plan task T03).

Fast, local, synthetic.  Teeth pinned here:

1. the feature whitelist refuses leakage/identity columns -- including
   escape-derived names and ``recovery_success`` / ``audit_bucket`` /
   ``parent_label`` -- while admitting the single documented causal
   exception ``prior_escape_count`` and handling ``dataset_id`` per the
   frozen identity-variant rule;
2. the grouping guard refuses any split under which one ``split_group``
   straddles partitions, and the frozen holdout is disjoint, complete,
   deterministic, and stratified;
3. parent-balanced training weights equal 1/(episodes of that parent),
   counting episode_ids rather than rows;
4. hyperparameter selection is structurally unable to see test groups;
5. the calibration path engages isotonic only when OOF ECE > 0.05 and its
   signature cannot fit on test labels;
6. two runs of the full per-cell path produce identical metrics;
7. the frozen acceptance and classification rules are decided correctly
   on hand-computed micro-fixtures (earned / not-earned /
   identity-reversed), and the co-reported metric helpers match hand
   computations.
"""

from __future__ import annotations

import inspect
from typing import Any

import numpy as np
import pandas as pd
import pytest

from scripts.settlement_datasets.run_v007_experiments import (
    ACCEPTANCE_MIN_DELTA,
    ARM_BY_ESTIMATOR,
    NON_FEATURE_COLUMNS,
    SCHEMA_ABLATION,
    SCHEMA_R0,
    SCHEMA_R1,
    assert_feature_columns,
    assert_partitions_grouped,
    classify_outcome,
    delta_of,
    ece_score,
    evaluate_acceptance,
    evaluate_probs,
    feature_columns_for,
    feature_matrix,
    group_labels_from_frame,
    maybe_calibrate,
    parent_aggregated_auc,
    per_source_direction,
    representative_examples,
    run_cell,
    select_hyperparameters,
    stratified_group_holdout,
)
from scripts.settlement_datasets.v007_recovery import (
    CAUSAL_ESCAPE_FEATURE_EXCEPTION,
    FRAME_COLUMNS,
    POINT_R0,
    R0_FEATURES,
    R1_FEATURES,
    V005_MINIMAL_RECOVERY_FEATURES,
    assert_grouped_by_split_group,
    assert_recovery_schemas_clean,
    parent_balanced_training_weights,
)

# ---------------------------------------------------------------------------
# Synthetic episode frame
# ---------------------------------------------------------------------------


def synthetic_episode_frame(
    n_groups: int = 24,
    rows_per_group: int = 8,
    seed: int = 7,
    point: str = POINT_R0,
) -> pd.DataFrame:
    """Episode-table-shaped frame with label-correlated features.

    Labels follow a deterministic pattern (even g -> two positive episodes;
    odd g -> none) so that every (dataset, group_label) holdout stratum
    has >= 2 groups and both episode classes appear across folds; the
    frame carries every FRAME_COLUMNS key so the whitelist guard and the
    feature matrix see the full identity surface.
    """
    rng = np.random.RandomState(seed)
    records: list[dict[str, Any]] = []
    for g in range(n_groups):
        for r in range(rows_per_group):
            episode = g * rows_per_group + r
            y = int(g % 2 == 0 and r < 2)
            row: dict[str, Any] = {c: 0.0 for c in FRAME_COLUMNS}
            dataset = ("swegym_openhands", "nebius_swe_agent", "swe_smith")[g % 3]
            row.update(
                {
                    "episode_id": f"p{episode}:ep0",
                    "episode_index": 0,
                    "parent_id": f"p{episode}",
                    "group_key": f"ds{g % 2}:inst{g}",
                    "split_group": f"ds{g % 2}:repo{g}",
                    "dataset": dataset,
                    "dataset_id": {"swegym_openhands": 0, "nebius_swe_agent": 2,
                                   "swe_smith": -1}[dataset],
                    "point": point,
                    "e": 5,
                    "r0_k": 6,
                    "r1_k": 9,
                    "n_events_total": 20,
                    "parent_label": y,
                    "recovery_success": y,
                    "audit_bucket": (
                        "escape_with_settlement" if y else "escape_no_settlement"
                    ),
                    "n_parent_episodes": 1,
                    "weight_base": 1.0,
                    # Label-correlated causal signal + noise features.
                    "verification_rate": rng.rand() + (0.6 if y else 0.0),
                    "error_count": float(rng.randint(0, 5)),
                    "error_rate": rng.rand(),
                    "prior_escape_count": float(episode % 3),
                }
            )
            records.append(row)
    return pd.DataFrame(records)


def _mini_split(
    frame: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, int]]:
    labels = group_labels_from_frame(frame)
    train_groups, test_groups = stratified_group_holdout(labels)
    train = frame[frame["split_group"].isin(set(train_groups))]
    test = frame[frame["split_group"].isin(set(test_groups))]
    return train, test, labels


# ---------------------------------------------------------------------------
# 1. Feature whitelist refuses leakage and identity columns
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "poison",
    [
        "recovery_success",
        "audit_bucket",
        "parent_label",
        "episode_id",
        "episode_index",
        "parent_id",
        "group_key",
        "split_group",
        "dataset",
        "point",
        "e",
        "r0_k",
        "r1_k",
        "n_events_total",
        "n_parent_episodes",
        "weight_base",
        "escape_observed",
        "escape_index",
        "first_escape_position",
        "settlement_bucket",
    ],
)
def test_whitelist_refuses_leakage_and_identity_columns(poison: str) -> None:
    with pytest.raises(ValueError):
        assert_feature_columns([poison], allow_dataset_id=True)
    with pytest.raises(ValueError):
        assert_feature_columns([poison], allow_dataset_id=False)


@pytest.mark.parametrize(
    "label_feature",
    ["recovery_success", "audit_bucket", "parent_label", "escape_position"],
)
def test_whitelist_refuses_label_columns_in_real_schemas(
    label_feature: str,
) -> None:
    for schema_cols in (R0_FEATURES, R1_FEATURES, V005_MINIMAL_RECOVERY_FEATURES):
        with pytest.raises(ValueError):
            assert_feature_columns([*schema_cols, label_feature], allow_dataset_id=True)


def test_prior_escape_count_is_the_single_documented_exception() -> None:
    # The causal prior-escape feature is admitted; a sibling escape-derived
    # name is not.
    assert_feature_columns(["prior_escape_count"], allow_dataset_id=False)
    assert CAUSAL_ESCAPE_FEATURE_EXCEPTION == "prior_escape_count"
    with pytest.raises(ValueError, match="escape"):
        assert_feature_columns(["own_escape_observed"], allow_dataset_id=False)


def test_dataset_id_follows_the_identity_variant_rule() -> None:
    # Refused by default...
    with pytest.raises(ValueError, match="dataset_id"):
        assert_feature_columns(["error_rate", "dataset_id"], allow_dataset_id=False)
    # ...admitted only in the with-identity variant.
    assert_feature_columns(["error_rate", "dataset_id"], allow_dataset_id=True)
    # v007_r0: 44 base features + dataset_id appended for the primary variant.
    assert feature_columns_for(SCHEMA_R0, True) == [*R0_FEATURES, "dataset_id"]
    assert feature_columns_for(SCHEMA_R0, False) == list(R0_FEATURES)
    # v007_r1: 54 base features + dataset_id appended / dropped.
    assert len(feature_columns_for(SCHEMA_R1, True)) == 55
    assert len(feature_columns_for(SCHEMA_R1, False)) == 54
    # The ablation schema ships dataset_id inside it: with-identity keeps it,
    # without-identity strips it.
    assert feature_columns_for(SCHEMA_ABLATION, True) == list(
        V005_MINIMAL_RECOVERY_FEATURES
    )
    assert "dataset_id" not in feature_columns_for(SCHEMA_ABLATION, False)
    assert len(feature_columns_for(SCHEMA_ABLATION, False)) == 6


def test_shipped_schemas_pass_all_hygiene_guards() -> None:
    assert_recovery_schemas_clean()


def test_non_feature_columns_carry_the_full_identity_surface() -> None:
    for column in (
        "recovery_success",
        "audit_bucket",
        "parent_label",
        "episode_id",
        "split_group",
        "dataset_id",
        "weight_base",
        "point",
    ):
        assert column in NON_FEATURE_COLUMNS


def test_feature_matrix_returns_aligned_columns() -> None:
    frame = synthetic_episode_frame()
    X, y, groups, datasets, parents, eids = feature_matrix(
        frame, SCHEMA_R0, use_dataset_id=True
    )
    assert list(X.columns) == [*R0_FEATURES, "dataset_id"]
    assert y.tolist() == frame["recovery_success"].tolist()
    assert len(X) == len(y) == len(groups) == len(parents) == len(eids)
    assert np.isfinite(X.to_numpy()).all()


# ---------------------------------------------------------------------------
# 2. Grouping guard + frozen holdout
# ---------------------------------------------------------------------------


def test_grouping_guard_refuses_within_split_group_splits() -> None:
    frame = synthetic_episode_frame(n_groups=4, rows_per_group=4)
    # Every other ROW goes to test: multi-row split_groups straddle.
    counter = {"i": 0}

    def split_fn(row: dict[str, Any]) -> str:
        i = counter["i"]
        counter["i"] += 1
        return "test" if i % 2 == 0 else "train"

    with pytest.raises(ValueError, match="straddles partitions"):
        assert_grouped_by_split_group(frame.to_dict("records"), split_fn)
    # The wrapper assigns per split_group, so within-group splits are
    # structurally impossible there; instead an overlap is refused.
    some = set(sorted(frame["split_group"].unique())[:2])
    with pytest.raises(ValueError, match="both"):
        assert_partitions_grouped(frame, some, set(some))


def test_overlapping_partitions_are_refused() -> None:
    frame = synthetic_episode_frame(n_groups=6, rows_per_group=4)
    some_groups = set(sorted(frame["split_group"].unique())[:3])
    with pytest.raises(ValueError, match="both"):
        assert_partitions_grouped(frame, some_groups, set(some_groups))


def test_frozen_holdout_is_disjoint_deterministic_and_stratified() -> None:
    frame = synthetic_episode_frame()
    labels = group_labels_from_frame(frame)
    train_groups, test_groups = stratified_group_holdout(labels)
    assert set(train_groups).isdisjoint(test_groups)
    assert set(train_groups) | set(test_groups) == set(labels)
    # Stratification: every (dataset, group_label) stratum reaches test.
    strata = {labels[g] for g in labels}
    assert {labels[g] for g in test_groups} == strata
    # Amendment-1 defect regression: EVERY source reaches the test draw.
    assert {labels[g][0] for g in test_groups} == {
        "swegym_openhands",
        "nebius_swe_agent",
        "swe_smith",
    }
    # Small per-strata counts make the exact 20% lumpy; stay in range.
    assert 0.15 <= len(test_groups) / len(labels) <= 0.40
    again = stratified_group_holdout(labels)
    assert (train_groups, test_groups) == again
    # The clean split passes the grouping guard.
    n_checked = assert_partitions_grouped(frame, set(train_groups), set(test_groups))
    assert n_checked == len(labels)


def test_single_group_stratum_is_assigned_to_test() -> None:
    """A stratum with one group goes to test deterministically.

    This is the round-1 failure mode guard: a source must never vanish
    from the evaluation partition merely because its stratum is tiny.
    """
    labels = {
        "swegym:lonely": ("swegym_openhands", 0),  # single-group stratum
        "swegym:a": ("swegym_openhands", 1),
        "swegym:b": ("swegym_openhands", 1),
        "swegym:c": ("swegym_openhands", 1),
        "swegym:d": ("swegym_openhands", 1),
        "nebius:a": ("nebius_swe_agent", 1),
        "nebius:b": ("nebius_swe_agent", 1),
        "nebius:c": ("nebius_swe_agent", 0),
        "nebius:d": ("nebius_swe_agent", 0),
    }
    train, test = stratified_group_holdout(labels)
    assert "swegym:lonely" in test
    assert set(train).isdisjoint(test)
    assert set(train) | set(test) == set(labels)
    again = stratified_group_holdout(labels)
    assert (train, test) == again


def test_group_label_is_any_episode_recovered_and_rows_unaffected() -> None:
    frame = synthetic_episode_frame()
    # Craft a group with mixed episode labels: its stratum label is 1.
    mixed = frame[frame["split_group"] == sorted(frame["split_group"].unique())[0]]
    mixed = mixed.copy()
    mixed.loc[mixed.index[:2], "recovery_success"] = 0
    mixed.loc[mixed.index[2:], "recovery_success"] = 1
    labels = group_labels_from_frame(mixed)
    assert labels[mixed["split_group"].iloc[0]][1] == 1
    # Row labels are untouched by label derivation.
    assert group_labels_from_frame(frame) == group_labels_from_frame(frame.copy())


# ---------------------------------------------------------------------------
# 3. Parent-balanced training weights
# ---------------------------------------------------------------------------


def test_parent_weights_equal_one_over_episodes_of_parent() -> None:
    rows = []
    for parent, episodes in (("pA", 2), ("pB", 1), ("pC", 3)):
        for ep in range(episodes):
            rows.append(
                {"parent_id": parent, "episode_id": f"{parent}:ep{ep}"}
            )
    frame = pd.DataFrame(rows)
    weights = parent_balanced_training_weights(frame)
    assert weights.tolist() == pytest.approx([0.5, 0.5, 1.0, 1 / 3, 1 / 3, 1 / 3])


def test_parent_weights_count_episode_ids_not_rows() -> None:
    # Parent pA has TWO episodes, but ep0 contributes two rows (R0 + R1):
    # every pA row carries 1/2.  pB has one episode -> 1.0.  The count is
    # distinct episode_ids per parent, never rows.
    frame = pd.DataFrame(
        [
            {"parent_id": "pA", "episode_id": "pA:ep0", "point": "R0"},
            {"parent_id": "pA", "episode_id": "pA:ep0", "point": "R1"},
            {"parent_id": "pA", "episode_id": "pA:ep1", "point": "R0"},
            {"parent_id": "pB", "episode_id": "pB:ep0", "point": "R0"},
        ]
    )
    weights = parent_balanced_training_weights(frame)
    assert weights.tolist() == pytest.approx([0.5, 0.5, 0.5, 1.0])


def test_run_cell_applies_train_weights_not_test_weights() -> None:
    """Structural: weights are computed inside run_cell from the train frame.

    A parent with many training episodes gets weight 1/n regardless of its
    test-side multiplicity (the test frame cannot influence the weight).
    """
    train, test, _ = _mini_split(synthetic_episode_frame())
    counts = train.groupby("parent_id")["episode_id"].nunique()
    expected = train["parent_id"].map(1.0 / counts).to_numpy()
    computed = parent_balanced_training_weights(train).to_numpy()
    assert np.allclose(computed, expected)


# ---------------------------------------------------------------------------
# 4. Selection never sees test groups (structural + behavioral)
# ---------------------------------------------------------------------------


def test_selection_takes_train_frame_only() -> None:
    sig = inspect.signature(select_hyperparameters)
    param_names = list(sig.parameters)
    assert param_names[0] == "train_frame"
    for forbidden in ("test_frame", "test", "test_groups", "full_frame", "frame"):
        assert forbidden not in param_names


def test_selection_consumes_train_groups_only() -> None:
    train, test, labels = _mini_split(synthetic_episode_frame())
    assert set(train["split_group"]).isdisjoint(test["split_group"])
    selection = select_hyperparameters(
        train, SCHEMA_R0, "logistic", use_dataset_id=True
    )
    assert selection["best_params"]["C"] in (0.01, 0.1, 1.0)
    assert selection["n_train_groups"] == train["split_group"].nunique()
    assert selection["n_train_rows"] == len(train)
    assert selection["n_train_positives"] == int(train["recovery_success"].sum())
    # Whatever the selection consumed is disjoint from the held-out partition.
    assert set(train["split_group"]).isdisjoint(set(test["split_group"]))


# ---------------------------------------------------------------------------
# 5. Calibration path
# ---------------------------------------------------------------------------


def test_isotonic_engages_only_when_oof_ece_above_trigger() -> None:
    rng = np.random.RandomState(0)
    n = 400
    y = np.concatenate([np.zeros(n // 2), np.ones(n // 2)]).astype(int)
    # Badly calibrated: failures predicted at 0.7-0.9, successes at 0.9-1.0.
    bad_probs = np.where(y == 1, rng.uniform(0.9, 1.0, n), rng.uniform(0.7, 0.9, n))
    bad = maybe_calibrate(bad_probs, y, np.array([0.9, 0.8, 0.3]))
    assert bad["oof_ece"] > 0.05
    assert bad["applied"] is True
    # Isotonic (monotone) pushes the mid-range prob down toward 0.
    assert bad["test_probs_calibrated"][2] <= 0.3 + 1e-9

    # Perfectly calibrated by construction: p equals the label.
    good_probs = y.astype(float)
    good = maybe_calibrate(good_probs, y, np.array([0.9, 0.3]))
    assert good["oof_ece"] == pytest.approx(0.0)
    assert good["applied"] is False
    # Without the trigger, test probabilities pass through unchanged.
    assert list(good["test_probs_calibrated"]) == [0.9, 0.3]


def test_calibration_never_fits_on_test() -> None:
    """Structural: the calibration entry point takes no test labels."""
    params = inspect.signature(maybe_calibrate).parameters
    for name in params:
        assert name in {"oof_probs", "y_train", "test_probs", "trigger"}


# ---------------------------------------------------------------------------
# 6. Determinism of the full per-cell path
# ---------------------------------------------------------------------------


def test_two_runs_produce_identical_metrics() -> None:
    frame = synthetic_episode_frame()
    train, test, _ = _mini_split(frame)
    runs = [
        run_cell(train, test, SCHEMA_R0, "logistic", use_dataset_id=True)["metrics"]
        for _ in range(2)
    ]
    assert runs[0] == runs[1]
    # 12 groups keep every (dataset, group_label) stratum at 2 groups while
    # staying fast for the 16-candidate LightGBM grid; the full
    # selection -> fit -> OOF calibration -> test path is exercised.
    small = synthetic_episode_frame(n_groups=12, rows_per_group=8, seed=11)
    small_train, small_test, _ = _mini_split(small)
    lgbm_runs = [
        run_cell(small_train, small_test, SCHEMA_R0, "lgbm", use_dataset_id=True)[
            "metrics"
        ]
        for _ in range(2)
    ]
    assert lgbm_runs[0] == lgbm_runs[1]


def test_run_cell_reports_required_metric_surface() -> None:
    train, test, _ = _mini_split(synthetic_episode_frame())
    block = run_cell(train, test, SCHEMA_R0, "logistic", use_dataset_id=True)
    metrics = block["metrics"]
    for key in (
        "roc_auc",
        "ap",
        "brier",
        "ece",
        "balanced_accuracy",
        "precision",
        "recall",
        "f1",
        "confusion_matrix",
        "parent_aggregated_auc",
        "per_source",
        "brier_after_calibration",
        "ece_after_calibration",
    ):
        assert key in metrics
    assert block["oof_ece"] >= 0.0
    assert block["identity_variant"] == "with_identity"
    preds = block["test_predictions"]
    assert len(preds["p_raw"]) == len(test)
    assert preds["episode_id"] == test["episode_id"].tolist()


# ---------------------------------------------------------------------------
# 7. Acceptance rules + metric helpers on hand-computed fixtures
# ---------------------------------------------------------------------------


def test_acceptance_earned() -> None:
    verdict = evaluate_acceptance(
        delta_primary=0.03,
        per_source_direction={"a": True, "b": True, "c": False},
        delta_without_identity=0.01,
    )
    assert verdict["earned"] is True
    assert verdict["verdict"] == "EARNED"
    assert verdict["sources_held"] == 2
    assert verdict["identity_reversed"] is False


def test_acceptance_not_earned_below_delta() -> None:
    verdict = evaluate_acceptance(
        delta_primary=ACCEPTANCE_MIN_DELTA - 0.005,
        per_source_direction={"a": True, "b": True, "c": True},
        delta_without_identity=0.0,
    )
    assert verdict["earned"] is False
    assert verdict["verdict"] == "NOT EARNED"


def test_acceptance_not_earned_on_direction_gate() -> None:
    verdict = evaluate_acceptance(
        delta_primary=0.05,
        per_source_direction={"a": True, "b": False, "c": None},
        delta_without_identity=0.02,
    )
    assert verdict["earned"] is False
    assert verdict["sources_held"] == 1


def test_acceptance_identity_reversed_blocks() -> None:
    verdict = evaluate_acceptance(
        delta_primary=0.04,
        per_source_direction={"a": True, "b": True, "c": True},
        delta_without_identity=-0.01,
    )
    assert verdict["earned"] is False
    assert verdict["verdict"] == "NOT EARNED (identity-reversed)"
    assert verdict["identity_reversed"] is True


def test_classification_settled_partial_not_earned() -> None:
    earned = evaluate_acceptance(
        0.03, {"a": True, "b": True, "c": False}, 0.01
    )
    not_earned = evaluate_acceptance(0.001, {"a": False, "b": True, "c": False}, 0.0)
    # Primary earned at R1 -> SETTLED-earned.
    assert classify_outcome(
        {"R0": not_earned, "R1": earned},
        {"R0": not_earned, "R1": not_earned},
        {"R0": 0.52, "R1": 0.66},
    )["classification"] == "SETTLED-earned"
    # No primary win, but a point materially above the prior -> PARTIAL.
    assert classify_outcome(
        {"R0": not_earned, "R1": not_earned},
        {"R0": not_earned, "R1": not_earned},
        {"R0": 0.58, "R1": 0.53},
    )["classification"] == "PARTIAL"
    # Secondary earned still leaves at least PARTIAL.
    assert classify_outcome(
        {"R0": not_earned, "R1": not_earned},
        {"R0": not_earned, "R1": earned},
        {"R0": 0.51, "R1": 0.52},
    )["classification"] == "PARTIAL"
    # Nothing anywhere -> NOT EARNED.
    assert classify_outcome(
        {"R0": not_earned, "R1": not_earned},
        {"R0": not_earned, "R1": not_earned},
        {"R0": 0.50, "R1": 0.52},
    )["classification"] == "NOT EARNED"


def test_ece_matches_hand_computation() -> None:
    probs = np.array([0.1, 0.4, 0.6, 0.9])
    y = np.array([0, 0, 1, 1])
    # One row per populated 10-bin: |acc - conf| averaged over rows.
    assert ece_score(probs, y) == pytest.approx(0.25 * (0.1 + 0.4 + 0.4 + 0.1))


def test_evaluate_probs_hand_confusion_and_auc() -> None:
    y = np.array([0, 1, 1, 0])
    p = np.array([0.2, 0.9, 0.4, 0.6])
    m = evaluate_probs(y, p)
    assert m["confusion_matrix"] == {"tn": 1, "fp": 1, "fn": 1, "tp": 1}
    assert m["roc_auc"] == pytest.approx(0.75)
    assert m["precision"] == pytest.approx(0.5)
    assert m["recall"] == pytest.approx(0.5)


def test_parent_aggregated_auc_labels_by_any_episode() -> None:
    y = pd.Series([1, 0, 0, 1])
    p = np.array([0.9, 0.1, 0.2, 0.8])
    parents = pd.Series(["p1", "p1", "p2", "p3"])
    # p1: mean prob 0.5, label 1 (ANY episode recovered); p2: 0.2/0; p3: 0.8/1.
    # Parent pairs are fully concordant -> AUC 1.0.
    assert parent_aggregated_auc(y, p, parents) == pytest.approx(1.0)
    # Flip p1's mean below p2's and the ordering breaks accordingly:
    # p1 (label 1, mean 0.125) ranks below p2 (label 0, 0.2); p3 ranks
    # above -> AUC 0.5.
    assert parent_aggregated_auc(
        y, np.array([0.1, 0.15, 0.2, 0.8]), parents
    ) == pytest.approx(0.5)


def test_per_source_direction_strictly_greater() -> None:
    a, b, c = "swegym_openhands", "nebius_swe_agent", "swe_smith"
    treatment = {
        "metrics": {
            "roc_auc": 0.68,
            "per_source": {
                a: {"roc_auc": 0.7},
                b: {"roc_auc": 0.6},
                c: {"roc_auc": None},
            },
        }
    }
    baseline = {
        "metrics": {
            "roc_auc": 0.6,
            "per_source": {
                a: {"roc_auc": 0.69},
                b: {"roc_auc": 0.6},
                c: {"roc_auc": 0.55},
            },
        }
    }
    direction = per_source_direction(treatment, baseline)
    assert direction == {a: True, b: False, c: None}
    assert delta_of(treatment, baseline) == pytest.approx(0.08)


def test_representative_examples_picks_confidence_extremes() -> None:
    block = {
        "point": POINT_R0,
        "estimator": "logistic",
        "schema": SCHEMA_R0,
        "identity_variant": "with_identity",
        "importance": [
            {"feature": "verification_rate", "importance": 1.0},
            {"feature": "error_rate", "importance": 0.5},
        ],
        "test_predictions": {
            "episode_id": [f"e{i}" for i in range(6)],
            "parent_id": [f"p{i}" for i in range(6)],
            "split_group": ["g"] * 6,
            "dataset": ["d"] * 6,
            "y": [1, 1, 0, 0, 1, 0],
            "p_raw": [0.95, 0.55, 0.9, 0.05, 0.52, 0.7],
            "p_calibrated": [0.95, 0.55, 0.9, 0.05, 0.52, 0.7],
            "calibration_applied": False,
        },
    }
    test_frame = pd.DataFrame(
        {
            "episode_id": [f"e{i}" for i in range(6)],
            "verification_rate": [0.9, 0.5, 0.1, 0.2, 0.3, 0.7],
            "error_rate": [1.0, 0.8, 0.6, 0.4, 0.2, 0.0],
        }
    )
    out = representative_examples(block, test_frame)
    assert ARM_BY_ESTIMATOR["logistic"] == "R_LR"
    assert [r["episode_id"] for r in out["highest_confidence_correct"]] == [
        "e0",
        "e3",
        "e1",
    ]  # confidences 0.95, 0.95, 0.55
    assert [r["episode_id"] for r in out["highest_confidence_incorrect"]] == [
        "e2",
        "e5",
    ]  # wrong-direction confidences 0.9, 0.7
    assert out["highest_confidence_correct"][0]["feature_values"] == {
        "verification_rate": 0.9,
        "error_rate": 1.0,
    }
    assert all(r["correct"] for r in out["highest_confidence_correct"])
    assert not any(r["correct"] for r in out["highest_confidence_incorrect"])
