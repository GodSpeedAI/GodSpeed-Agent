"""Tests for the frozen v006 experiment runner (plan task T05).

Fast, local, synthetic.  Teeth pinned here:

1. an ungrouped split is refused by the grouping guard;
2. label/identity columns entering the feature matrix are refused by the
   whitelist guard;
3. per-cut training frames carry exactly one row per parent per cut;
4. hyperparameter selection is structurally unable to see test groups (the
   selection function takes the train frame only, and partition disjointness
   is enforced);
5. the calibration path engages isotonic only when OOF ECE > 0.05 and its
   signature cannot fit on test labels;
6. two runs on fixed-seed synthetic data produce identical metric dicts;
7. the frozen acceptance rule is decided correctly on hand-computed
   fixtures (gain / no-gain / identity-dependent).
"""

from __future__ import annotations

import inspect
import zlib
from typing import Any

import numpy as np
import pandas as pd
import pytest

from scripts.settlement_datasets.run_v006_experiments import (
    ACCEPTANCE_MIN_CUTS_WON,
    ACCEPTANCE_MIN_DELTA,
    assert_no_label_columns,
    assert_partitions_grouped,
    ece_score,
    evaluate_acceptance,
    feature_matrix,
    group_labels_from_parents,
    maybe_calibrate,
    oof_train_predictions,
    run_arm_at_cut,
    select_hyperparameters,
    stratified_group_holdout,
)
from scripts.settlement_datasets.v006_features import (
    CANONICAL_CUT_KINDS,
    assert_grouped,
    build_prefix_frame,
)

# ---------------------------------------------------------------------------
# Synthetic parents
# ---------------------------------------------------------------------------

_HASH_SEQ = [f"{i:016x}"[:10] for i in range(64)]


def make_parent(
    parent_id: str,
    group_key: str,
    dataset: str,
    label: int,
    n_events: int = 12,
    n_errors: int = 1,
    n_context_events: int = 2,
) -> dict[str, Any]:
    rng = np.random.RandomState(zlib.crc32(parent_id.encode("utf-8")))
    events: list[dict[str, Any]] = []
    i = n_context_events
    errors_left = n_errors
    for pos in range(n_events):
        kind = "action" if pos % 2 == 0 else "observation"
        is_error = bool(errors_left > 0 and kind == "observation" and pos >= 3)
        if is_error:
            errors_left -= 1
        events.append(
            {
                "kind": kind,
                "is_error": is_error,
                "cmd_family": ("test" if pos % 6 == 0 else "git") if kind == "action" else None,
                "hash": _HASH_SEQ[(pos + int(label) * 3) % len(_HASH_SEQ)],
                "i": i,
                "mentions_bash": kind == "action" and pos % 5 == 0,
                "has_terminal_output": kind == "observation",
                "content_len": int(rng.randint(0, 200)),
                "role": "assistant" if kind == "action" else "tool",
            }
        )
        i += 1
    n_actions = sum(1 for e in events if e["kind"] == "action")
    n_obs = len(events) - n_actions
    return {
        "parent_id": parent_id,
        "group_key": group_key,
        "dataset": dataset,
        "label": int(label),
        "events": events,
        "n_context_events": n_context_events,
        "tool_names_manifest": ["bash", "edit"] if dataset == "swegym_openhands" else [],
        "counts": {
            "elapsed_steps": n_context_events + len(events),
            "turns": n_actions,
            "tool_calls": n_obs,
            "commands": int(n_events // 5),
            "error_count": n_errors,
        },
        "total_messages": n_context_events + len(events) + 1,
    }


def synthetic_parents(n_groups: int = 12, runs_per_group: int = 2) -> list[dict[str, Any]]:
    parents: list[dict[str, Any]] = []
    for g in range(n_groups):
        for r in range(runs_per_group):
            label = int(g % 2 and r == 0)
            parents.append(
                make_parent(
                    parent_id=f"ds{g % 2}:inst{g}:run{r}",
                    group_key=f"ds{g % 2}:inst{g}",
                    dataset="swegym_openhands" if g % 2 == 0 else "nebius_swe_agent",
                    label=label,
                    n_events=10 + (g * 3 + r) % 25,
                    n_errors=(g + r) % 3,
                )
            )
    return parents


def synthetic_frames() -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    parents = synthetic_parents()
    frame = build_prefix_frame(parents, families=("v005_prefix_compatible", "v006"))
    by_cut = {cut: frame[frame["prefix_kind"] == cut] for cut in CANONICAL_CUT_KINDS}
    return frame, by_cut


# ---------------------------------------------------------------------------
# 1. Ungrouped splits are refused
# ---------------------------------------------------------------------------


def test_ungrouped_split_is_refused_by_grouping_guard() -> None:
    frame, _ = synthetic_frames()
    # Deliberately ungrouped assignment: every other ROW goes to test, so any
    # group with multiple rows straddles partitions.
    counter = {"i": 0}

    def split_fn(row: dict[str, Any]) -> str:
        i = counter["i"]
        counter["i"] += 1
        return "test" if i % 2 == 0 else "train"

    with pytest.raises(ValueError, match="straddles partitions"):
        assert_grouped(frame.to_dict("records"), split_fn)


def test_overlapping_partitions_are_refused() -> None:
    frame, _ = synthetic_frames()
    some_groups = set(sorted(frame["group_key"].unique())[:3])
    with pytest.raises(ValueError, match="both"):
        assert_partitions_grouped(frame, some_groups, set(some_groups))


def test_frozen_holdout_groups_are_disjoint_deterministic_and_stratified() -> None:
    parents = synthetic_parents()
    group_labels = group_labels_from_parents(parents)
    train_groups, test_groups = stratified_group_holdout(group_labels)
    assert set(train_groups).isdisjoint(test_groups)
    assert set(train_groups) | set(test_groups) == set(group_labels)
    # Stratification: the test partition contains both group labels.
    assert {group_labels[g] for g in test_groups} == {0, 1}
    again = stratified_group_holdout(group_labels)
    assert (train_groups, test_groups) == again


# ---------------------------------------------------------------------------
# 2. Label/identity columns in X are refused
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "poison", ["label", "settlement_success", "settlement_score"]
)
def test_label_columns_are_refused(poison: str) -> None:
    with pytest.raises(ValueError, match="Label columns must never enter"):
        assert_no_label_columns(["n_events", poison])


def test_identity_columns_are_refused_as_features() -> None:
    with pytest.raises(ValueError, match="Identity/bookkeeping"):
        assert_no_label_columns(["n_events", "group_key", "weight_base"])


def test_feature_matrix_never_carries_label_or_identity_columns() -> None:
    frame, _ = synthetic_frames()
    X, y, groups, _ds, pid = feature_matrix(frame, "v006", use_dataset_id=True)
    for col in (
        "label",
        "settlement_success",
        "settlement_score",
        "group_key",
        "parent_id",
        "dataset",
        "prefix_kind",
        "weight_base",
    ):
        assert col not in X.columns
    assert "dataset_id" in X.columns  # PRIMARY identity variant
    X_rob, _, _, _, _ = feature_matrix(frame, "v006", use_dataset_id=False)
    assert "dataset_id" not in X_rob.columns
    assert (y.values == frame["label"].values).all()
    assert (pid.values == frame["parent_id"].values).all()


# ---------------------------------------------------------------------------
# 3. Exactly one row per parent per cut
# ---------------------------------------------------------------------------


def test_one_row_per_parent_per_cut() -> None:
    _, by_cut = synthetic_frames()
    for cut in CANONICAL_CUT_KINDS:
        sub = by_cut[cut]
        counts = sub.groupby("parent_id").size()
        assert (counts == 1).all(), f"cut {cut} has duplicated parents"
        assert sub["parent_id"].is_unique


# ---------------------------------------------------------------------------
# 4. Selection never sees test groups (structural)
# ---------------------------------------------------------------------------


def test_selection_takes_train_frame_only() -> None:
    """Structural: the selection API has no channel for test data."""
    sig = inspect.signature(select_hyperparameters)
    param_names = list(sig.parameters)
    assert param_names[0] == "train_frame"
    for forbidden in ("test_frame", "test", "test_groups", "full_frame", "frame"):
        assert forbidden not in param_names
    sig_oof = inspect.signature(oof_train_predictions)
    for forbidden in ("test_frame", "test_probs", "test_groups"):
        assert forbidden not in sig_oof.parameters


def test_selection_runs_on_train_partition_only() -> None:
    parents = synthetic_parents(n_groups=14, runs_per_group=2)
    frame = build_prefix_frame(parents, families=("v005_prefix_compatible", "v006"))
    sub = frame[frame["prefix_kind"] == "pct50"]
    group_labels = group_labels_from_parents(parents)
    train_groups, test_groups = stratified_group_holdout(group_labels)
    train_set, test_set = set(train_groups), set(test_groups)
    # Grouped-guard accepts the clean split (every group in one partition).
    n_checked = assert_partitions_grouped(frame, train_set, test_set)
    assert n_checked == len(group_labels)

    train_frame = sub[sub["group_key"].isin(train_set)]
    assert train_frame["group_key"].nunique() >= 5
    selection = select_hyperparameters(
        train_frame, "v005_prefix_compatible", "logistic", use_dataset_id=True
    )
    assert selection["best_params"]["C"] in (0.01, 0.1, 1.0)
    assert selection["n_train_groups"] == train_frame["group_key"].nunique()
    assert selection["n_train_rows"] == len(train_frame)
    # Whatever the selection consumed is disjoint from the test partition.
    assert set(train_frame["group_key"]).isdisjoint(test_set)


# ---------------------------------------------------------------------------
# 5. Calibration path
# ---------------------------------------------------------------------------


def test_isotonic_engaged_only_when_oof_ece_above_trigger() -> None:
    rng = np.random.RandomState(0)
    n = 400
    y = np.concatenate([np.zeros(n // 2), np.ones(n // 2)]).astype(int)
    # Badly calibrated: failures predicted at 0.7-0.9, successes at 0.9-1.0.
    bad_probs = np.where(y == 1, rng.uniform(0.9, 1.0, n), rng.uniform(0.7, 0.9, n))
    bad = maybe_calibrate(bad_probs, y, np.array([0.9, 0.8, 0.3]))
    assert bad["oof_ece"] > 0.05
    assert bad["applied"] is True
    assert len(bad["reliability_oof"]) == 10
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
# 6. Determinism of the full per-cut path
# ---------------------------------------------------------------------------


def _mini_split(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    labels = frame.groupby("group_key")["label"].max()
    train_groups, test_groups = stratified_group_holdout(labels.astype(int).to_dict())
    train = frame[frame["group_key"].isin(set(train_groups))]
    test = frame[frame["group_key"].isin(set(test_groups))]
    return train, test


def test_two_runs_produce_identical_metrics() -> None:
    _, by_cut = synthetic_frames()
    train, test = _mini_split(by_cut["pct50"])
    lgbm_runs = [
        run_arm_at_cut(train, test, "v006", "lgbm", use_dataset_id=True)["metrics"]
        for _ in range(2)
    ]
    assert lgbm_runs[0] == lgbm_runs[1]
    lr_runs = [
        run_arm_at_cut(train, test, "v005_prefix_compatible", "logistic", use_dataset_id=True)["metrics"]
        for _ in range(2)
    ]
    assert lr_runs[0] == lr_runs[1]


# ---------------------------------------------------------------------------
# 7. Acceptance rule on hand-computed fixtures
# ---------------------------------------------------------------------------


def _cuts(aucs: list[float]) -> dict[str, dict[str, Any]]:
    names = list(CANONICAL_CUT_KINDS)
    assert len(aucs) == len(names)
    return {
        name: {"roc_auc": auc, "underpowered": False, "n_test_parents": 50}
        for name, auc in zip(names, aucs)
    }


BASE = [0.60, 0.58, 0.62, 0.55, 0.61, 0.57]


def test_acceptance_gain_identity_robust() -> None:
    base = _cuts(BASE)
    treat = _cuts([a + 0.03 for a in BASE])  # delta +0.03 >= 0.02, 6/6 won
    rob_treat = _cuts([a + 0.025 for a in BASE])  # robustness also positive
    verdict = evaluate_acceptance(base, treat, base, rob_treat)
    assert verdict["verdict"] == "EARNED (identity-robust)"
    assert verdict["delta_primary"] == pytest.approx(0.03)
    assert verdict["cuts_won"] == 6
    assert verdict["identity_dependent"] is False


def test_acceptance_no_gain_when_delta_below_threshold() -> None:
    base = _cuts(BASE)
    treat = _cuts([a + 0.01 for a in BASE])  # delta < 0.02 -> not earned
    verdict = evaluate_acceptance(base, treat, base, treat)
    assert verdict["verdict"] == "NOT EARNED"
    assert verdict["identity_dependent"] is False
    assert verdict["delta_primary"] == pytest.approx(0.01)


def test_acceptance_direction_gate() -> None:
    base = _cuts(BASE)
    # Macro delta >= +0.02 with exactly 4/6 cuts won -> passes the >= 4 gate.
    aucs = [a + 0.10 for a in BASE]
    aucs[0] = BASE[0] - 0.05
    aucs[1] = BASE[1] - 0.05
    treat = _cuts(aucs)
    macro_delta = float(np.mean(aucs) - np.mean(BASE))
    assert macro_delta >= ACCEPTANCE_MIN_DELTA
    verdict = evaluate_acceptance(base, treat, base, treat)
    assert verdict["cuts_won"] == 4
    assert verdict["cuts_won"] >= ACCEPTANCE_MIN_CUTS_WON
    assert verdict["verdict"] == "EARNED (identity-robust)"
    # Only 3/6 cuts won -> NOT EARNED despite macro delta >= +0.02.
    aucs2 = [a + 0.10 for a in BASE]
    for i in range(3):
        aucs2[i] = BASE[i] - 0.05
    verdict2 = evaluate_acceptance(base, _cuts(aucs2), base, _cuts(aucs2))
    assert verdict2["cuts_won"] == 3
    assert verdict2["verdict"] == "NOT EARNED"


def test_acceptance_identity_dependent_blocks_adoption() -> None:
    base = _cuts(BASE)
    treat = _cuts([a + 0.03 for a in BASE])
    rob_treat = _cuts([a - 0.02 for a in BASE])  # sign reverses without dataset_id
    verdict = evaluate_acceptance(base, treat, base, rob_treat)
    assert verdict["identity_dependent"] is True
    assert verdict["verdict"] == "NOT EARNED -- identity-dependent (adoption blocked)"


def test_acceptance_ignores_unreliable_cuts() -> None:
    base = _cuts(BASE)
    base["pct50"] = {"roc_auc": None, "underpowered": True, "n_test_parents": 5}
    treat = _cuts([a + 0.03 for a in BASE])
    treat["pct50"] = {"roc_auc": 0.99, "underpowered": True, "n_test_parents": 5}
    verdict = evaluate_acceptance(base, treat, base, treat)
    assert "pct50" not in verdict["reliable_cuts"]
    assert len(verdict["reliable_cuts"]) == 5
    assert verdict["verdict"] == "EARNED (identity-robust)"


def test_ece_matches_hand_computation() -> None:
    y = np.array([0, 1, 0, 1])
    p = np.array([0.05, 0.85, 0.15, 0.55])
    # bins: .05->|0-.05|, .15->|0-.15|, .55->|1-.55|, .85->|1-.85|
    expected = (0.05 + 0.15 + 0.45 + 0.15) / 4
    assert ece_score(p, y) == pytest.approx(expected)
