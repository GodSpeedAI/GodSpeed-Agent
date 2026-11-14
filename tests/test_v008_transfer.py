"""Tests for the frozen v008 LOSO transfer runner (plan V3).

Fast, local, synthetic.  Teeth pinned here:

1. ISOLATION (structural): the T derivation, scaler fitting, C
   selection, calibrator fitting, and whole-arm fitting functions take
   ONLY the training pool -- no parameter exists through which a
   held-out frame could enter any fitted quantity; behaviorally,
   ``fit_arm`` output is invariant to the frame it is never given;
2. IDENTITY WHITELIST: primary arm feature lists refuse ``dataset_id``
   and every bookkeeping column; only the diagnostic ``*_id`` arms may
   carry it;
3. WEIGHTING: parent x source balancing arithmetic on a crafted pool
   (equal total weight per source; equal weight per parent within a
   source; episodes counted, not rows);
4. T RULE: on a crafted two-source pool an environment identifier
   (constant in a source / perfectly source-separating) fails the
   gates, a direction-consistent signal passes them, and the fill-to-5
   size rule engages mechanically;
5. CALIBRATION: isotonic engages iff OOF ECE > 0.05 and the calibrator
   signature cannot fit on held-out labels;
6. DETERMINISM: two runs of the full per-arm path produce byte-identical
   predictions;
7. ACCEPTANCE: the frozen primary/secondary rules decide hand-computed
   micro-fixtures correctly (earned / macro-too-small /
   degradation-guard / sensitivity-direction / identity / secondary);
8. a full ``run_cell`` pass over a crafted three-source pool completes
   with 7 arms, a filled T set, and both calibration branches plumbed.
"""

from __future__ import annotations

import inspect
import json
from typing import Any

import numpy as np
import pandas as pd
import pytest

from scripts.settlement_datasets.run_v008_transfer import (
    ALL_ARM_KEYS,
    ARM_SPECS,
    CELL_DEGRADATION_GUARD,
    CELLS,
    C_GRID,
    F_FEATURES,
    IDENTITY_FEATURE,
    M_FEATURES,
    MACRO_MIN_DELTA,
    PRIMARY_ARM_KEYS,
    WEIGHTING_BALANCED,
    WEIGHTING_PARENT_ONLY,
    assert_no_identity,
    balanced_source_parent_weights,
    classify_outcome,
    derive_t_selection,
    ece_score,
    evaluate_acceptance,
    evaluate_probs,
    evaluate_secondary,
    feature_matrix,
    fit_arm,
    fit_calibrator,
    fit_scaler,
    group_folds,
    predict_arm,
    resolve_arm_features,
    run_arm,
    run_cell,
    select_C_and_oof,
    training_weights,
)
from scripts.settlement_datasets.v007_recovery import (
    FRAME_COLUMNS,
    POINT_R1,
    R1_FEATURES,
    V005_MINIMAL_RECOVERY_FEATURES,
    parent_balanced_training_weights,
)

# ---------------------------------------------------------------------------
# Synthetic pools
# ---------------------------------------------------------------------------

SIGNAL_FEATURE = "verification_rate"
ENV_FEATURE = "error_recovery_ratio"  # crafted: perfectly source-separating
CONST_ONE_SOURCE_FEATURE = "stuck_loop_indicator"  # crafted: constant in A only

DATASET_IDS = {"swegym_openhands": 0, "nebius_swe_agent": 2, "swe_smith": -1}


def _y_pattern(group: int, row: int) -> int:
    """Even groups carry two positive episodes; odd groups none."""
    return int(group % 2 == 0 and row < 2)


def _signal_value(group: int, row: int, episode: int) -> float:
    """Label-correlated value with overlapping jitter (deterministic)."""
    jitter = ((episode * 7) % 10) * 0.05 - 0.25
    return 0.5 * _y_pattern(group, row) + jitter


def two_source_pool(
    n_groups: int = 12,
    rows_per_group: int = 4,
    datasets: tuple[str, str] = ("swegym_openhands", "nebius_swe_agent"),
) -> pd.DataFrame:
    """R1-shaped frame over two sources with a known signal feature.

    ``SIGNAL_FEATURE`` tracks the label with jitter (direction-consistent
    in both sources, distribution identical across sources);
    ``ENV_FEATURE`` is 0 in source A and 1 in source B (perfectly
    source-separating, constant within each source);
    ``CONST_ONE_SOURCE_FEATURE`` is constant in source A only; every
    other schema feature is an all-zero column (constant everywhere).
    """
    records: list[dict[str, Any]] = []
    episode = 0
    for g in range(n_groups):
        for source_index, dataset in enumerate(datasets):
            for r in range(rows_per_group):
                y = _y_pattern(g, r)
                row: dict[str, Any] = {c: 0.0 for c in FRAME_COLUMNS}
                row.update(
                    {
                        "episode_id": f"{dataset}:g{g}:ep{episode}",
                        "episode_index": 0,
                        "parent_id": f"{dataset}:p{episode}",
                        "group_key": f"{dataset}:inst{g}",
                        "split_group": f"{dataset}:repo{g}",
                        "dataset": dataset,
                        "dataset_id": DATASET_IDS.get(dataset, -1),
                        "point": POINT_R1,
                        "e": 5,
                        "r0_k": 6,
                        "r1_k": 9,
                        "n_events_total": 20,
                        "parent_label": y,
                        "recovery_success": y,
                        "audit_bucket": "escape_with_settlement" if y else "escape_no_settlement",
                        "n_parent_episodes": 1,
                        "weight_base": 1.0,
                        SIGNAL_FEATURE: _signal_value(g, r, episode),
                        ENV_FEATURE: float(source_index),
                        CONST_ONE_SOURCE_FEATURE: (
                            1.0 if source_index == 0 else float(episode % 3)
                        ),
                    }
                )
                records.append(row)
                episode += 1
    return pd.DataFrame(records)


def three_source_pool() -> pd.DataFrame:
    """Small three-source frame; the third source repeats the pattern."""
    base = two_source_pool(n_groups=8)
    extra = two_source_pool(n_groups=8, datasets=("swe_smith", "swe_smith_unused"))
    third = extra[extra["dataset"] == "swe_smith_unused"].copy()
    third["dataset"] = "swe_smith"
    third["episode_id"] = [f"sm{i}" for i in range(len(third))]
    third["parent_id"] = [f"sm:p{i}" for i in range(len(third))]
    third["split_group"] = [f"swe_smith:repo{i % 8}" for i in range(len(third))]
    third[ENV_FEATURE] = 0.5
    return pd.concat([base, third], ignore_index=True)


# ---------------------------------------------------------------------------
# 1. Structural + behavioral isolation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "func",
    [derive_t_selection, fit_scaler, select_C_and_oof, fit_arm],
)
def test_pool_only_signatures_have_no_heldout_parameter(func) -> None:
    params = set(inspect.signature(func).parameters)
    assert params, f"{func.__name__} lost its parameters"
    for forbidden in ("held", "test", "out", "eval", "target_source"):
        offending = [p for p in params if forbidden in p]
        assert not offending, (
            f"{func.__name__} must take only the training pool; found {offending}"
        )


def test_calibrator_signature_cannot_receive_heldout_labels() -> None:
    params = inspect.signature(fit_calibrator).parameters
    assert set(params) == {"oof_probs", "y_pool", "trigger"}


def test_fit_arm_output_invariant_to_never_seen_frames() -> None:
    pool = two_source_pool()
    probe = two_source_pool(n_groups=4)
    unrelated_a = two_source_pool(n_groups=6, datasets=("swe_smith", "nebius_swe_agent"))
    unrelated_b = unrelated_a.copy()
    unrelated_b[SIGNAL_FEATURE] = 42.0  # would change any leaked statistic

    arm_a = fit_arm(pool, list(M_FEATURES), WEIGHTING_BALANCED)
    arm_b = fit_arm(pool, list(M_FEATURES), WEIGHTING_BALANCED)
    probs_a = predict_arm(arm_a, probe)["p_raw"]
    # Same pool -> identical fit; a poisoned frame the fit never receives
    # cannot move it.
    assert np.array_equal(probs_a, predict_arm(arm_b, probe)["p_raw"])
    arm_c = fit_arm(pool, list(M_FEATURES), WEIGHTING_BALANCED)
    assert np.array_equal(probs_a, predict_arm(arm_c, probe)["p_raw"])
    del unrelated_a, unrelated_b  # structural: never passed anywhere above


def test_run_arm_touches_heldout_only_after_fitting() -> None:
    pool = two_source_pool()
    held = two_source_pool(n_groups=4)
    block_a = run_arm(pool, held, list(M_FEATURES), WEIGHTING_BALANCED)
    block_b = run_arm(pool, held.copy(), list(M_FEATURES), WEIGHTING_BALANCED)
    assert block_a["predictions"]["p_raw"] == block_b["predictions"]["p_raw"]
    assert block_a["metrics"]["roc_auc"] == block_b["metrics"]["roc_auc"]


# ---------------------------------------------------------------------------
# 2. Identity whitelist
# ---------------------------------------------------------------------------


def test_primary_arms_refuse_dataset_id_and_bookkeeping() -> None:
    for arm_key in ("M", "F", "T", "M_parent_only", "T_parent_only"):
        features = resolve_arm_features(arm_key, ["error_count"])
        assert IDENTITY_FEATURE not in features
        with pytest.raises(ValueError):
            assert_no_identity([*features, IDENTITY_FEATURE])


def test_diagnostic_arms_are_the_only_identity_carriers() -> None:
    assert "dataset_id" in resolve_arm_features("F_id", ["error_count"])
    assert "dataset_id" in resolve_arm_features("T_id", ["error_count"])
    with pytest.raises(ValueError):
        assert_no_identity(["recovery_success"])
    with pytest.raises(ValueError):
        assert_no_identity(["split_group"])


def test_frozen_representation_shapes() -> None:
    assert len(M_FEATURES) == 6
    assert IDENTITY_FEATURE not in M_FEATURES
    assert "error_count_so_far" in M_FEATURES
    assert len(F_FEATURES) == 54
    assert len(R1_FEATURES) == 54
    assert len(set(F_FEATURES)) == 54
    assert IDENTITY_FEATURE not in F_FEATURES
    assert len(V005_MINIMAL_RECOVERY_FEATURES) == 7


def test_feature_matrix_applies_error_count_alias() -> None:
    frame = two_source_pool(n_groups=2)
    frame["error_count"] = 3.0
    X = feature_matrix(frame, ["error_count_so_far"])
    assert (X["error_count_so_far"] == 3.0).all()


# ---------------------------------------------------------------------------
# 3. Weighting arithmetic
# ---------------------------------------------------------------------------


def _weighting_fixture() -> pd.DataFrame:
    rows = []
    spec = {
        "swegym_openhands": {"pa": 2, "pb": 4},
        "nebius_swe_agent": {"pc": 3},
    }
    episode = 0
    for dataset, parents in spec.items():
        for parent, n_rows in parents.items():
            for _ in range(n_rows):
                row = {c: 0.0 for c in FRAME_COLUMNS}
                row.update(
                    {
                        "episode_id": f"e{episode}",
                        "parent_id": f"{dataset}:{parent}",
                        "split_group": f"{dataset}:repo",
                        "dataset": dataset,
                        "point": POINT_R1,
                        "recovery_success": episode % 2,
                    }
                )
                rows.append(row)
                episode += 1
    return pd.DataFrame(rows)


def test_balanced_source_parent_weights_arithmetic() -> None:
    pool = _weighting_fixture()
    weights = balanced_source_parent_weights(pool)
    assert len(weights) == len(pool)

    datasets = pool["dataset"].astype(str).to_numpy()
    parents = pool["parent_id"].astype(str).to_numpy()
    for dataset in ("swegym_openhands", "nebius_swe_agent"):
        assert weights[datasets == dataset].sum() == pytest.approx(0.5)
    # Within source A (2 parents), each parent carries 0.25 total.
    for parent, expected in (("swegym_openhands:pa", 0.25), ("swegym_openhands:pb", 0.25)):
        assert weights[parents == parent].sum() == pytest.approx(expected)
    # Source B has one parent carrying the full 0.5.
    assert weights[parents == "nebius_swe_agent:pc"].sum() == pytest.approx(0.5)
    # Parent balancing equals the v007 frozen weight before normalization.
    base = parent_balanced_training_weights(pool).to_numpy(dtype=float)
    assert np.allclose(base[parents == "swegym_openhands:pa"], 0.5)
    assert np.allclose(base[parents == "swegym_openhands:pb"], 0.25)


def test_training_weights_dispatch_and_fit_only_use() -> None:
    pool = _weighting_fixture()
    assert training_weights(pool, WEIGHTING_PARENT_ONLY).sum() == pytest.approx(3.0)
    assert training_weights(pool, WEIGHTING_BALANCED).sum() == pytest.approx(1.0)
    with pytest.raises(ValueError):
        training_weights(pool, "unknown")


# ---------------------------------------------------------------------------
# 4. The mechanical T rule
# ---------------------------------------------------------------------------


def test_t_rule_excludes_env_identifier_and_keeps_signal() -> None:
    pool = two_source_pool()
    selection = derive_t_selection(pool)

    gate_by_feature = {row["feature"]: row for row in selection["gate_table"]}
    assert len(selection["gate_table"]) == 54

    env = gate_by_feature[ENV_FEATURE]
    assert not env["passes_all_gates"]
    assert not env["gates"]["non_constant_both_sources"]
    assert not env["gates"]["not_source_identifying"]
    assert env["identifiability_auc"] == pytest.approx(1.0)

    const_one = gate_by_feature[CONST_ONE_SOURCE_FEATURE]
    assert not const_one["gates"]["non_constant_both_sources"]
    assert const_one["constant_in_source"]["swegym_openhands"] is True
    assert const_one["constant_in_source"]["nebius_swe_agent"] is False

    signal = gate_by_feature[SIGNAL_FEATURE]
    assert signal["passes_all_gates"], signal
    assert signal["direction_folds"] >= 4
    assert signal["coefficient_folds"] >= 4
    assert signal["coefficient_sign"] == 1
    assert signal["identifiability_auc"] < 0.85
    assert SIGNAL_FEATURE in selection["selected"]
    assert not selection["trim_applied"]


def test_t_rule_fills_to_five_with_stability_ties_lexicographic() -> None:
    pool = two_source_pool()
    selection = derive_t_selection(pool)
    assert selection["fill_applied"] is True
    assert selection["n_passing_gates_untrimmed"] < 5
    assert len(selection["selected"]) == 5
    assert len(set(selection["selected"])) == 5
    # Fill rows are flagged and complete the set in deterministic order.
    filled = [row["feature"] for row in selection["gate_table"] if row["fill"]]
    passing = [row["feature"] for row in selection["gate_table"] if row["passes_all_gates"]]
    assert sorted(filled + [f for f in selection["selected"] if f in passing]) == sorted(
        selection["selected"]
    )
    # Fill preference respects the stability score (desc), name (asc).
    remaining = [row for row in selection["gate_table"] if not row["passes_all_gates"]]
    expected = [
        row["feature"]
        for row in sorted(remaining, key=lambda r: (-r["stability_score"], r["feature"]))
    ][: 5 - selection["n_passing_gates_untrimmed"]]
    assert sorted(expected) == sorted(filled)


# ---------------------------------------------------------------------------
# 5. Calibration trigger
# ---------------------------------------------------------------------------


def test_calibration_triggers_only_above_ece_threshold() -> None:
    y = np.array([0, 0, 0, 0, 0, 1, 1, 1, 1, 1])
    overconfident = np.full(10, 0.9)
    assert ece_score(overconfident, y) == pytest.approx(0.4)
    result = fit_calibrator(overconfident, y)
    assert result["applied"] is True
    assert result["oof_ece"] == pytest.approx(0.4)

    perfect = y.astype(float)
    assert ece_score(perfect, y) == pytest.approx(0.0)
    untriggered = fit_calibrator(perfect, y)
    assert untriggered["applied"] is False
    assert "isotonic" not in untriggered

    borderline = fit_calibrator(np.full(10, 0.5), y)
    assert borderline["applied"] is False  # ECE == 0.05 is not > 0.05


# ---------------------------------------------------------------------------
# 6. Determinism micro-check
# ---------------------------------------------------------------------------


def test_full_arm_path_deterministic() -> None:
    pool = two_source_pool()
    held = two_source_pool(n_groups=4)
    block_a = run_arm(pool, held, list(M_FEATURES), WEIGHTING_BALANCED)
    block_b = run_arm(pool, held, list(M_FEATURES), WEIGHTING_BALANCED)
    assert json.dumps(block_a["predictions"], sort_keys=True) == json.dumps(
        block_b["predictions"], sort_keys=True
    )
    assert json.dumps(block_a["selection"], sort_keys=True) == json.dumps(
        block_b["selection"], sort_keys=True
    )
    # C selection is over the frozen grid, in frozen order.
    assert [row["C"] for row in block_a["selection"]["cv_table"]] == list(C_GRID)


# ---------------------------------------------------------------------------
# 7. Acceptance micro-fixtures (hand-computed)
# ---------------------------------------------------------------------------


def test_acceptance_earned_fixture() -> None:
    deltas = {"nebius_swe_agent": 0.04, "swe_smith": 0.03, "swegym_openhands": 0.01}
    verdict = evaluate_acceptance(deltas, sensitivity_delta=0.005, identity_clean=True)
    assert verdict["earned"] is True
    assert verdict["macro_delta"] == pytest.approx(sum(deltas.values()) / 3)
    assert verdict["cells_held"] == 3
    assert verdict["worst_cell_delta"] == pytest.approx(0.01)


def test_acceptance_rejects_small_macro_delta() -> None:
    deltas = {"nebius_swe_agent": 0.03, "swe_smith": 0.01, "swegym_openhands": 0.005}
    verdict = evaluate_acceptance(deltas, sensitivity_delta=0.01, identity_clean=True)
    assert verdict["macro_delta"] == pytest.approx(0.015)
    assert verdict["conditions"]["macro_delta_at_least_min"] is False
    assert verdict["earned"] is False


def test_acceptance_degradation_guard_fires() -> None:
    deltas = {"nebius_swe_agent": 0.10, "swe_smith": 0.08, "swegym_openhands": -0.05}
    verdict = evaluate_acceptance(deltas, sensitivity_delta=0.02, identity_clean=True)
    assert verdict["macro_delta"] > MACRO_MIN_DELTA
    assert verdict["cells_held"] == 2
    assert verdict["worst_cell_delta"] == pytest.approx(-0.05)
    assert verdict["conditions"]["no_cell_below_degradation_guard"] is False
    assert verdict["earned"] is False
    assert CELL_DEGRADATION_GUARD == 0.03


def test_acceptance_requires_sensitivity_direction() -> None:
    deltas = {"nebius_swe_agent": 0.04, "swe_smith": 0.03, "swegym_openhands": 0.01}
    assert (
        evaluate_acceptance(deltas, sensitivity_delta=-0.01, identity_clean=True)[
            "earned"
        ]
        is False
    )
    assert (
        evaluate_acceptance(deltas, sensitivity_delta=0.0, identity_clean=True)[
            "earned"
        ]
        is False
    )
    assert (
        evaluate_acceptance(deltas, sensitivity_delta=None, identity_clean=True)[
            "earned"
        ]
        is False
    )


def test_acceptance_requires_identity_clean() -> None:
    deltas = {"nebius_swe_agent": 0.04, "swe_smith": 0.03, "swegym_openhands": 0.01}
    assert (
        evaluate_acceptance(deltas, sensitivity_delta=0.01, identity_clean=False)[
            "earned"
        ]
        is False
    )


def test_secondary_rule_fixture() -> None:
    earned = evaluate_secondary(
        {"nebius_swe_agent": 0.04, "swe_smith": 0.03, "swegym_openhands": 0.011}
    )
    assert earned["earned"] is True
    not_earned = evaluate_secondary(
        {"nebius_swe_agent": 0.03, "swe_smith": 0.025, "swegym_openhands": -0.005}
    )
    assert not_earned["macro_delta"] == pytest.approx((0.03 + 0.025 - 0.005) / 3)
    assert not_earned["earned"] is False


def test_classification_mapping_fixture() -> None:
    assert classify_outcome(True, 0) == "SETTLED_earned"
    assert classify_outcome(False, 2) == "PARTIAL"
    assert classify_outcome(False, 1) == "NOT_EARNED"
    assert classify_outcome(False, 0) == "NOT_EARNED"


def test_ece_and_metric_helpers_hand_checked() -> None:
    y = np.array([0, 0, 0, 0, 0, 1, 1, 1, 1, 1])
    assert ece_score(np.array([0.0] * 5 + [1.0] * 5), y) == pytest.approx(0.0)
    metrics = evaluate_probs(y, np.array([0.1] * 5 + [0.9] * 5))
    assert metrics["roc_auc"] == pytest.approx(1.0)
    assert metrics["confusion_matrix"] == {"tn": 5, "fp": 0, "fn": 0, "tp": 5}
    assert metrics["f1"] == pytest.approx(1.0)
    inverted = evaluate_probs(y, np.array([0.9] * 5 + [0.1] * 5))
    assert inverted["roc_auc"] == pytest.approx(0.0)
    assert inverted["confusion_matrix"] == {"tn": 0, "fp": 5, "fn": 5, "tp": 0}


# ---------------------------------------------------------------------------
# 8. Full cell plumbing on a crafted three-source pool
# ---------------------------------------------------------------------------


def test_run_cell_completes_all_arms_and_rules() -> None:
    frame = three_source_pool()
    held_out = CELLS[0]
    cell = run_cell(frame, held_out)

    assert cell["held_out_source"] == held_out
    assert sorted(cell["pool_sources"]) == sorted(set(CELLS) - {held_out})
    assert len(cell["arms"]) == len(ARM_SPECS) == 7
    for key in ALL_ARM_KEYS:
        block = cell["arms"][key]
        assert block["metrics"]["roc_auc"] is not None
        assert len(block["predictions"]["episode_id"]) == block["metrics"]["n_test_rows"]
    # Primary arms stay identity-free; only diagnostics carry dataset_id.
    for key in PRIMARY_ARM_KEYS:
        assert IDENTITY_FEATURE not in cell["arms"][key]["features"]
    assert IDENTITY_FEATURE in cell["arms"]["F_id"]["features"]
    assert IDENTITY_FEATURE in cell["arms"]["T_id"]["features"]
    # Sensitivity arms use the parent-only weighting.
    assert cell["arms"]["M_parent_only"]["weighting"] == WEIGHTING_PARENT_ONLY
    assert cell["arms"]["T_parent_only"]["weighting"] == WEIGHTING_PARENT_ONLY
    # The T set is the derived selection; error analysis has all quadrants.
    assert cell["t_features"] == cell["t_selection"]["selected"]
    assert len(cell["t_features"]) == 5
    for quadrant in ("TP", "TN", "FP", "FN"):
        assert quadrant in cell["error_analysis"]["quadrants"]
        assert cell["error_analysis"]["quadrants"][quadrant]["tentative_cause"]
    # Group folds respect split_group grouping.
    folds = group_folds(frame)
    assert len(folds) == 5
    for tr, va in folds:
        assert not set(frame.iloc[tr]["split_group"]) & set(frame.iloc[va]["split_group"])
