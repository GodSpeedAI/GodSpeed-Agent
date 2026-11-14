"""Tests for v007 recovery-prediction feature schemas.

Pins: (1) exact R0/R1 feature vectors (hand-computed on crafted
streams), (2) the frozen window closures (R0 at r0_k=e+1, R1 at r1_k),
(3) causal purity -- mutating every event strictly after a cut leaves
feature vectors bit-identical, (4) the v005_minimal_recovery@1
ablation schema and its pull-through from the v006 extractors, (5)
undefined-quantity conventions (0.0 + has_* indicators), (6) rounding
and finiteness, and (7) frame hygiene.
"""

from __future__ import annotations

import copy
import hashlib
from typing import Any

import pandas as pd
import pytest

from scripts.settlement_datasets.v006_features import (
    V005_FEATURES,
    V006_FEATURES,
    v005_prefix_compatible_features,
    v006_prefix_features,
)
from scripts.settlement_datasets.v007_recovery import (
    ABLATION_EXTRA_COLUMN,
    POINT_R0,
    POINT_R1,
    R0_EPISODE_FEATURES,
    R0_FEATURES,
    R1_ADDITIONS,
    R1_FEATURES,
    SCHEMA_VERSIONS,
    V005_MINIMAL_RECOVERY_FEATURES,
    V005_MINIMAL_RECOVERY_SCHEMA_VERSION,
    _current_streak_prior_nonerror,
    _r1_addition_features,
    _r1_cut,
    build_episode_frame,
    build_failure_episodes,
    select_ablation_features,
    v005_minimal_recovery_features,
)

from tests.test_v007_episodes import (
    _act,
    _err,
    _ok,
    _synthetic_parent,
)

FEATURE_COLUMNS = R0_FEATURES + R1_ADDITIONS + (ABLATION_EXTRA_COLUMN,)


# ---------------------------------------------------------------------------
# Crafted streams (hand-computed expectations)
# ---------------------------------------------------------------------------


def _repeat_stream() -> list[dict[str, Any]]:
    """Positions: 0 A(git hG) 1 O(ok) 2 O(errE e) 3 A(git hG) 4 O(errE)
    5 O(ok2).  Attempt repeats the prior action's hash; attempt result
    repeats the failure hash; escape at 5; r1_k = 6 (consecutive
    results at 4 and 5)."""
    return [
        _act("git commit -m fix", "git"),  # hG
        _ok(),
        _err("Error: traceback boom"),  # hE, e=2
        _act("git commit -m fix", "git"),  # same hash hG
        _err("Error: traceback boom"),  # result: same failure repeated
        _ok("fresh output"),  # second consecutive result; escape
    ]


def _family_change_stream() -> list[dict[str, Any]]:
    """Attempt switches family git -> python and does not repeat the
    hash; result is a fresh non-error observation; r1_k = 5."""
    return [
        _act("git commit -m fix", "git"),
        _ok(),
        _err(),  # e=2
        _act("python scripts/x.py", "python"),
        _ok("verification output is fresh"),  # novel hash after e
    ]


def _episode_at(parent: dict[str, Any], point: str) -> pd.Series:
    frame = build_episode_frame([parent])
    rows = frame[frame["point"] == point]
    assert len(rows) == 1
    return rows.iloc[0]


class TestSchemaConstants:
    def test_r0_schema_composition(self):
        assert R0_FEATURES == (
            V006_FEATURES
            + tuple(name for name in V005_FEATURES if name != "dataset_id")
            + R0_EPISODE_FEATURES
        )
        assert len(R0_FEATURES) == len(set(R0_FEATURES))
        assert R0_EPISODE_FEATURES == (
            "fail_event_index",
            "prior_episode_count",
            "prior_escape_count",
            "errors_opening_run_available_at_r0",
            "current_streak_prior_nonerror",
        )

    def test_r1_schema_composition(self):
        assert R1_FEATURES == R0_FEATURES + R1_ADDITIONS
        assert len(R1_ADDITIONS) == 10
        assert len(R1_FEATURES) == len(set(R1_FEATURES))

    def test_ablation_schema_and_version(self):
        assert V005_MINIMAL_RECOVERY_FEATURES == (
            "error_count_so_far",
            "consecutive_error_observations",
            "repeated_error_rate",
            "error_rate",
            "action_observation_ratio",
            "tool_diversity_count",
            "dataset_id",
        )
        assert V005_MINIMAL_RECOVERY_SCHEMA_VERSION == "v005_minimal_recovery@1"
        assert SCHEMA_VERSIONS["v005_minimal_recovery"] == (
            V005_MINIMAL_RECOVERY_SCHEMA_VERSION
        )


# ---------------------------------------------------------------------------
# Window closures: the frame cuts exactly where the frozen rules say
# ---------------------------------------------------------------------------


class TestWindowClosures:
    def test_r0_features_equal_extractors_at_e_plus_one(self):
        parent = _synthetic_parent(_repeat_stream(), label=1)
        record = build_failure_episodes(parent)[0]
        row = _episode_at(parent, POINT_R0)
        k = record["r0_k"]
        assert k == record["e"] + 1 == 3
        v006 = v006_prefix_features(parent, k)
        v005 = v005_prefix_compatible_features(parent, k)
        for name, value in v006.items():
            assert row[name] == value
        for name, value in v005.items():
            if name == "dataset_id":
                continue
            assert row[name] == value

    def test_r1_features_equal_extractors_at_r1_k(self):
        parent = _synthetic_parent(_repeat_stream(), label=1)
        record = build_failure_episodes(parent)[0]
        row = _episode_at(parent, POINT_R1)
        k = record["r1_k"]
        assert k == 6
        v006 = v006_prefix_features(parent, k)
        for name, value in v006.items():
            assert row[name] == value

    def test_r0_cut_is_failure_inclusive(self):
        parent = _synthetic_parent(_repeat_stream())
        record = build_failure_episodes(parent)[0]
        row = _episode_at(parent, POINT_R0)
        # The failure observation itself is inside the R0 window: the
        # error run ending at the cut counts it.
        assert row["consecutive_error_observations"] == 1.0
        assert row["error_count"] == 1.0
        assert row["n_events"] == 3.0

    def test_r1_cut_includes_attempt_and_consecutive_results(self):
        parent = _synthetic_parent(_repeat_stream())
        row = _episode_at(parent, POINT_R1)
        # events[:6]: n_events 6 = attempt(3) + results(4,5).
        assert row["n_events"] == 6.0
        assert row["n_actions"] == 2.0
        assert row["n_observations"] == 4.0


# ---------------------------------------------------------------------------
# Hand-computed R1 addition values
# ---------------------------------------------------------------------------


class TestR1AdditionValues:
    def test_repeat_stream_values(self):
        parent = _synthetic_parent(_repeat_stream(), label=1)
        row = _episode_at(parent, POINT_R1)
        assert row["recovery_attempt_present"] == 1.0
        assert row["has_prior_action"] == 1.0
        assert row["attempt_repeats_prior_action"] == 1.0
        assert row["has_pre_failure_action"] == 1.0
        assert row["attempt_family_change"] == 0.0  # git -> git
        assert row["obs_between_failure_and_attempt"] == 0.0
        # Novel observations after e and before/at k1: only "fresh
        # output" at position 5 (hE repeated at 4; hashes before e seen).
        assert row["new_obs_between_failure_and_attempt"] == 1.0
        assert row["has_attempt_result"] == 1.0
        assert row["attempt_result_is_error"] == 1.0
        assert row["attempt_result_same_hash_as_failure"] == 1.0

    def test_family_change_stream_values(self):
        parent = _synthetic_parent(_family_change_stream())
        row = _episode_at(parent, POINT_R1)
        assert row["recovery_attempt_present"] == 1.0
        assert row["attempt_repeats_prior_action"] == 0.0
        assert row["attempt_family_change"] == 1.0  # git -> python
        assert row["obs_between_failure_and_attempt"] == 0.0
        assert row["has_attempt_result"] == 1.0
        assert row["attempt_result_is_error"] == 0.0
        assert row["attempt_result_same_hash_as_failure"] == 0.0
        assert row["new_obs_between_failure_and_attempt"] == 1.0

    def test_no_prior_action_indicators(self):
        events = [
            _ok(),  # 0 (non-error observation precedes the run)
            _err(),  # 1 e
            _act("python scripts/x.py", "python"),  # 2 attempt
            _ok("fresh result payload"),  # 3 result, novel hash
        ]
        parent = _synthetic_parent(events)
        row = _episode_at(parent, POINT_R1)
        assert row["has_prior_action"] == 0.0
        assert row["attempt_repeats_prior_action"] == 0.0
        assert row["has_pre_failure_action"] == 0.0
        assert row["attempt_family_change"] == 0.0
        assert row["obs_between_failure_and_attempt"] == 0.0
        assert row["has_attempt_result"] == 1.0
        assert row["new_obs_between_failure_and_attempt"] == 1.0

    def test_observations_between_failure_and_attempt_counted(self):
        events = [
            _ok(),  # 0
            _err(),  # 1 e
            _err(),  # 2 between (run continues)
            _act("git status", "git"),  # 3 attempt
            _ok(),  # 4 result
        ]
        parent = _synthetic_parent(events)
        row = _episode_at(parent, POINT_R1)
        assert row["obs_between_failure_and_attempt"] == 1.0
        # Novel after e: position 2 repeats the failure hash -> not
        # novel; position 4 ("all ok") repeats position 0's hash? No --
        # ok() at 0 has the same content hash as ok() at 4 -> not novel.
        assert row["new_obs_between_failure_and_attempt"] == 0.0

    def test_new_obs_counts_first_occurrences_including_between(self):
        events = [
            _ok("intermediate output A"),  # 0
            _err(),  # 1 e
            _ok("post-failure fresh"),  # 2 between, novel after e
            _act("git status", "git"),  # 3 attempt
            _ok("post-failure fresh"),  # 4 result, repeat hash
        ]
        parent = _synthetic_parent(events)
        row = _episode_at(parent, POINT_R1)
        assert row["obs_between_failure_and_attempt"] == 1.0
        assert row["new_obs_between_failure_and_attempt"] == 1.0

    def test_r0_rows_carry_zeroed_r1_additions(self):
        parent = _synthetic_parent(_repeat_stream(), label=1)
        row = _episode_at(parent, POINT_R0)
        for name in R1_ADDITIONS:
            assert row[name] == 0.0, name

    def test_r1_addition_features_direct_function(self):
        parent = _synthetic_parent(_repeat_stream())
        record = build_failure_episodes(parent)[0]
        feats = _r1_addition_features(parent, record)
        assert set(feats) == set(R1_ADDITIONS)
        assert all(isinstance(value, float) for value in feats.values())
        with pytest.raises(AssertionError):
            _r1_addition_features(parent, {**record, "r1_k": None})


# ---------------------------------------------------------------------------
# Episode-positional features
# ---------------------------------------------------------------------------


class TestPositionalFeatures:
    def test_values_on_two_episode_parent(self):
        events = [
            _act("git commit -m fix", "git"),  # 0
            _ok(),  # 1
            _err(),  # 2 ep0
            _act("pytest -q", "test"),  # 3
            _ok(),  # 4 escape ep0
            _act("git diff", "git"),  # 5
            _err(),  # 6 ep1
            _act("pytest -q", "test"),  # 7
            _ok(),  # 8 escape ep1
        ]
        parent = _synthetic_parent(events, label=1)
        frame = build_episode_frame([parent])
        ep0_r0 = frame[
            (frame["episode_index"] == 0) & (frame["point"] == POINT_R0)
        ].iloc[0]
        ep1_r0 = frame[
            (frame["episode_index"] == 1) & (frame["point"] == POINT_R0)
        ].iloc[0]
        ep1_r1 = frame[
            (frame["episode_index"] == 1) & (frame["point"] == POINT_R1)
        ].iloc[0]
        for row in (ep0_r0, ep1_r0, ep1_r1):
            assert row["errors_opening_run_available_at_r0"] == 1.0
        assert ep0_r0["fail_event_index"] == 2.0
        assert ep0_r0["prior_episode_count"] == 0.0
        assert ep0_r0["prior_escape_count"] == 0.0
        # Streak before e=2: one non-error observation at position 1.
        assert ep0_r0["current_streak_prior_nonerror"] == 1.0
        assert ep1_r0["fail_event_index"] == 6.0
        assert ep1_r0["prior_episode_count"] == 1.0
        assert ep1_r0["prior_escape_count"] == 1.0
        assert ep1_r1["fail_event_index"] == 6.0
        assert ep1_r1["prior_episode_count"] == 1.0

    def test_streak_spans_actions_transparently(self):
        events = [
            _ok(),  # 0
            _act("git status", "git"),  # 1 (transparent for the streak)
            _ok(),  # 2
            _err(),  # 3 e
            _act("pytest -q", "test"),  # 4
            _ok(),  # 5
        ]
        parent = _synthetic_parent(events)
        assert _current_streak_prior_nonerror(parent, 3) == 2

    def test_consecutive_error_observations_at_cuts(self):
        parent = _synthetic_parent(_repeat_stream())
        frame = build_episode_frame([parent])
        r0 = frame[frame["point"] == POINT_R0].iloc[0]
        r1 = frame[frame["point"] == POINT_R1].iloc[0]
        # At r0_k=3 the window ends on the opening error observation.
        assert r0["consecutive_error_observations"] == 1.0
        # At r1_k=6 the window ends on a non-error observation.
        assert r1["consecutive_error_observations"] == 0.0


# ---------------------------------------------------------------------------
# CAUSAL PURITY: future-event mutation invariance (teeth)
# ---------------------------------------------------------------------------


def _mutate_from(parent: dict[str, Any], start: int) -> dict[str, Any]:
    """Deep-copy and violently mutate every event at index >= start,
    then append new tail events (structure change)."""
    mutant = copy.deepcopy(parent)
    for ev in mutant["events"][start:]:
        ev["hash"] = "ffffffff" if ev["hash"] != "ffffffff" else "00000000"
        ev["is_error"] = not ev["is_error"]
        ev["role"] = "mutated"
        ev["content_len"] = ev["content_len"] + 100
        ev["mentions_bash"] = not ev["mentions_bash"]
        ev["has_terminal_output"] = not ev["has_terminal_output"]
        if ev["cmd_family"] is not None:
            ev["cmd_family"] = "git" if ev["cmd_family"] != "git" else "edit"
    mutant["events"].append(_act("pip install pytest", "install"))
    mutant["events"].append(_err())
    return mutant


class TestMutationInvariance:
    def test_feature_vectors_bit_identical_under_future_mutations(self):
        events = [
            _act("git commit -m fix", "git"),  # 0
            _ok(),  # 1
            _err(),  # 2 ep0 (R0 cut 3; attempt 3; r1 cut 5)
            _act("pytest -q", "test"),  # 3
            _ok(),  # 4
            _act("git diff", "git"),  # 5
            _err(),  # 6 ep1 (R0 cut 7; attempt 7; r1 cut 9)
            _act("pytest -q", "test"),  # 7
            _ok(),  # 8
        ]
        parent = _synthetic_parent(events, label=1)
        base_frame = build_episode_frame([parent])
        n = len(events)
        for start in range(1, n + 1):
            mutant = _mutate_from(parent, start)
            mutant_frame = build_episode_frame([mutant])
            # Rows whose ENTIRE feature window closed at or before the
            # mutation start must be bit-identical.
            for _, row in base_frame.iterrows():
                cut = row["r0_k"] if row["point"] == POINT_R0 else row["r1_k"]
                if cut > start:
                    continue
                match = mutant_frame[
                    (mutant_frame["episode_id"] == row["episode_id"])
                    & (mutant_frame["point"] == row["point"])
                ]
                assert len(match) == 1, (start, row["episode_id"], row["point"])
                mutant_row = match.iloc[0]
                for name in FEATURE_COLUMNS:
                    assert mutant_row[name] == row[name], (
                        f"mutation at {start} changed {name} for "
                        f"{row['episode_id']}({row['point']}, cut={cut})"
                    )

    def test_extractor_purity_at_episode_cuts(self):
        parent = _synthetic_parent(_repeat_stream())
        record = build_failure_episodes(parent)[0]
        for k in (record["r0_k"], record["r1_k"]):
            assert k is not None
            before_v006 = v006_prefix_features(parent, k)
            before_v005 = v005_prefix_compatible_features(parent, k)
            mutant = _mutate_from(parent, k)
            assert v006_prefix_features(mutant, k) == before_v006
            assert v005_prefix_compatible_features(mutant, k) == before_v005
            assert v005_minimal_recovery_features(parent, k) == (
                v005_minimal_recovery_features(mutant, k)
            )


# ---------------------------------------------------------------------------
# Ablation schema
# ---------------------------------------------------------------------------


class TestAblation:
    def test_minimal_features_pull_from_v006_extractor_outputs(self):
        parent = _synthetic_parent(_repeat_stream())
        for k in (2, 3, 6):
            v006 = v006_prefix_features(parent, k)
            v005 = v005_prefix_compatible_features(parent, k)
            minimal = v005_minimal_recovery_features(parent, k)
            assert minimal["error_count_so_far"] == v006["error_count"]
            assert minimal["repeated_error_rate"] == v006["repeated_error_rate"]
            assert minimal["error_rate"] == v006["error_rate"]
            assert minimal["action_observation_ratio"] == v005["action_observation_ratio"]
            assert minimal["tool_diversity_count"] == v005["tool_diversity_count"]
            assert minimal["dataset_id"] == v005["dataset_id"]
            assert isinstance(minimal["tool_diversity_count"], int)
            assert isinstance(minimal["dataset_id"], int)

    def test_consecutive_error_observations_matches_local_rule(self):
        parent = _synthetic_parent(_repeat_stream())
        from scripts.settlement_datasets.v007_recovery import (
            _consecutive_error_observations,
        )

        for k in (2, 3, 4, 6):
            minimal = v005_minimal_recovery_features(parent, k)
            assert minimal["consecutive_error_observations"] == _r4_like(
                _consecutive_error_observations(parent, k)
            )

    def test_select_ablation_features_materializes_named_schema(self):
        parent = _synthetic_parent(_repeat_stream(), label=1)
        frame = build_episode_frame([parent])
        subset = select_ablation_features(frame)
        assert list(subset.columns) == list(V005_MINIMAL_RECOVERY_FEATURES)
        for _, row in frame.iterrows():
            cut = row["r0_k"] if row["point"] == POINT_R0 else row["r1_k"]
            direct = v005_minimal_recovery_features(parent, cut)
            named = subset.loc[
                (frame["episode_id"] == row["episode_id"])
                & (frame["point"] == row["point"])
            ].iloc[0]
            for name in V005_MINIMAL_RECOVERY_FEATURES:
                assert named[name] == direct[name]

    def test_select_ablation_features_missing_column_raises(self):
        frame = pd.DataFrame({"error_count": [1.0]})
        with pytest.raises(ValueError, match="missing required ablation column"):
            select_ablation_features(frame)


def _r4_like(value: int) -> float:
    return round(float(value), 4) + 0.0


# ---------------------------------------------------------------------------
# Frame hygiene: rounding, finiteness, identity
# ---------------------------------------------------------------------------


class TestFrameHygiene:
    def test_all_feature_values_are_finite(self):
        parents = [
            _synthetic_parent(_repeat_stream(), label=1),
            _synthetic_parent(_family_change_stream()),
        ]
        frame = build_episode_frame(parents)
        for name in FEATURE_COLUMNS:
            for value in frame[name]:
                # H's int dtypes (tool_diversity_count, dataset_id) are
                # preserved by the import-never-fork rule.
                assert isinstance(value, (int, float)) and not isinstance(value, bool)
                assert value == value and abs(value) != float("inf")

    def test_v007_added_features_are_r4_rounded(self):
        # The v007-added columns are rounded like v006 (_r4).  The
        # v005-prefix family columns keep H's native precision by the
        # import-never-fork rule (v006 leaves error_rate/risk_estimate/
        # payment_* unrounded exactly as H computes them).
        parents = [
            _synthetic_parent(_repeat_stream(), label=1),
            _synthetic_parent(_family_change_stream()),
        ]
        frame = build_episode_frame(parents)
        added = R0_EPISODE_FEATURES + R1_ADDITIONS + (ABLATION_EXTRA_COLUMN,)
        for name in added:
            for value in frame[name]:
                assert value == round(value, 4), name

    def test_identity_columns_are_stable(self):
        parent = _synthetic_parent(_repeat_stream(), label=1)
        frame = build_episode_frame([parent])
        assert set(frame["point"]) == {POINT_R0, POINT_R1}
        assert (frame["parent_label"] == 1).all()
        assert (frame["recovery_success"] == 1).all()
        assert (frame["e"] == 2).all()
        assert (frame["r0_k"] == 3).all()
        assert (frame.loc[frame["point"] == POINT_R1, "r1_k"] == 6).all()
        assert (frame["n_events_total"] == 6).all()
        assert (frame["dataset_id"] == -1).all()  # unknown synthetic dataset
        assert frame["episode_id"].nunique() == 1

    def test_r1_cut_helper_direct(self):
        events = _repeat_stream()
        parent = _synthetic_parent(events)
        assert _r1_cut(parent["events"], 2) == 6
        # No action after e=2 variant.
        no_action = _synthetic_parent([_ok(), _err(), _err()])
        assert _r1_cut(no_action["events"], 1) is None
        # Action is the final event.
        tail_action = _synthetic_parent([_ok(), _err(), _act("ls", "inspect")])
        assert _r1_cut(tail_action["events"], 1) == 3
