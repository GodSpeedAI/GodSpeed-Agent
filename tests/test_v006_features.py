"""Tests for v006 prefix-trajectory feature extraction.

All tests run against local fixtures and synthetic parents -- no network.
The suite pins: (1) exact v005 equivalence, (2) prefix purity against
future-event mutations, (3) final-length leakage exclusion, (4) group_key
split guarding, (5) parent-balancing weight_base, (6) cut semantics, and
(7) deterministic extraction.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from godspeed_nav.cognitive_model import build_calibration_frame
from scripts.settlement_datasets.build_trajectory_corpus import build_parent
from scripts.settlement_datasets.run_calibration_pipeline import (
    external_record_to_model_calibration,
)
from scripts.settlement_datasets.v006_features import (
    CANONICAL_CUT_KINDS,
    LEAKY_FEATURE_PATTERNS,
    SCHEMA_VERSIONS,
    V005_FEATURES,
    V006_FEATURES,
    assert_grouped,
    assert_no_leaky_features,
    build_full_frame,
    build_prefix_frame,
    generate_prefixes,
    plan_prefix_cuts,
    v005_full_semantics_features,
    v005_prefix_compatible_features,
    v006_prefix_features,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "settlement_datasets"

_ADAPTER_DATASETS = (
    "swegym_openhands",
    "agenttrove",
    "nebius_swe_agent",
    "swegym",
    "apibank",
    "webshop",
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _fixture_records() -> list[dict[str, Any]]:
    """Every fixture record + its corpus parent (skips unusable rows)."""
    from scripts.settlement_datasets.registry import get_adapter

    out: list[dict[str, Any]] = []
    for name in _ADAPTER_DATASETS:
        adapter = get_adapter(name)
        sample = FIXTURES_DIR / name / "sample.jsonl"
        for raw in _read_jsonl(sample):
            record = adapter.to_settlement_record(raw)
            parent, reason = build_parent(
                record, revision_sha="rev", license_status="l", min_confidence=0.65
            )
            out.append(
                {
                    "dataset": name,
                    "record": record,
                    "parent": parent,
                    "reason": reason,
                }
            )
    return out


def _fixture_parents() -> list[dict[str, Any]]:
    return [item["parent"] for item in _fixture_records() if item["parent"]]


def _event(
    kind: str,
    content: str,
    *,
    role: str | None = None,
    cmd_family: str | None = None,
    is_error: bool = False,
    mentions_bash: bool = False,
    has_terminal_output: bool = False,
) -> dict[str, Any]:
    is_action = kind == "action"
    return {
        "i": 0,
        "kind": kind,
        "role": role or ("assistant" if is_action else "tool"),
        "content_len": len(content),
        "hash": hashlib.sha1(content.encode("utf-8")).hexdigest()[:10],
        "mentions_bash": is_action and mentions_bash,
        "is_error": kind == "observation" and is_error,
        "cmd_family": cmd_family if is_action else None,
        "has_terminal_output": kind == "observation" and has_terminal_output,
    }


def _synthetic_parent(
    events: list[dict[str, Any]], **overrides: Any
) -> dict[str, Any]:
    parent: dict[str, Any] = {
        "parent_id": "synthetic:task-1:run-a",
        "group_key": "synthetic:task-1",
        "dataset": "synthetic_ds",
        "revision_sha": "rev",
        "license_status": "test-license",
        "label": 0,
        "label_source": "success=False",
        "outcome_confidence": 0.9,
        "n_context_events": 2,
        "total_messages": 2 + len(events),
        "tool_names_manifest": ["execute_bash"],
        "counts": {
            "turns": sum(1 for ev in events if ev["kind"] == "action"),
            "tool_calls": sum(1 for ev in events if ev["kind"] == "observation"),
            "commands": 0,
            "elapsed_steps": 2 + len(events),
            "error_count": sum(1 for ev in events if ev["is_error"]),
        },
        "events": copy.deepcopy(events),
    }
    parent.update(overrides)
    for i, ev in enumerate(parent["events"]):
        ev["i"] = i
    return parent


def _rich_stream() -> list[dict[str, Any]]:
    """12-event stream exercising every v006 feature family theme.

    Positions: 0 A(git) 1 O(err e1) 2 A(test) 3 O(ok) 4 A(edit h3)
    5 A(edit h3) 6 O(err e1) 7 A(edit h3) 8 O(err e1) 9 O(new e3)
    10 A(test) 11 O(ok)
    """
    return [
        _event("action", "git commit -m fix", cmd_family="git"),
        _event("observation", "Error: traceback boom", is_error=True),
        _event("action", "pytest -q tests/", cmd_family="test"),
        _event("observation", "all ok"),
        _event("action", "sed -i s/a/b/ file.py", cmd_family="edit"),
        _event("action", "sed -i s/a/b/ file.py", cmd_family="edit"),
        _event("observation", "Error: traceback boom", is_error=True),
        _event("action", "sed -i s/a/b/ file.py", cmd_family="edit"),
        _event("observation", "Error: traceback boom", is_error=True),
        _event("observation", "fresh output data"),
        _event("action", "pytest -q tests/", cmd_family="test"),
        _event("observation", "all ok"),
    ]


# ---------------------------------------------------------------------------
# 1. EQUIVALENCE: v005_full_semantics == H pipeline on every fixture record
# ---------------------------------------------------------------------------


class TestV005FullSemanticsEquivalence:
    @pytest.fixture
    def records(self) -> list[dict[str, Any]]:
        return _fixture_records()

    def test_every_fixture_record_equivalent_to_h_pipeline(self, records):
        compared = 0
        for item in records:
            parent = item["parent"]
            if parent is None:
                continue
            h_record = external_record_to_model_calibration(item["record"])
            h_frame = build_calibration_frame([h_record])
            assert len(h_frame) == 1
            h_row = h_frame.iloc[0]

            mine = v005_full_semantics_features(parent)
            assert set(mine) == set(V005_FEATURES)
            for column in V005_FEATURES:
                h_value = h_row[column]
                my_value = mine[column]
                if isinstance(h_value, float) or isinstance(my_value, float):
                    # Exact bit-level equality, same rounding as H.
                    assert float(h_value) == float(my_value), (
                        f"{item['dataset']} column {column}: "
                        f"H={h_value!r} mine={my_value!r}"
                    )
                else:
                    assert h_value == my_value, (
                        f"{item['dataset']} column {column}: "
                        f"H={h_value!r} mine={my_value!r}"
                    )
            compared += 1
        # The three corpus adapters + swegym/apibank/webshop fixtures.
        assert compared >= 15

    def test_h_dtypes_reproduced(self, records):
        for item in records:
            parent = item["parent"]
            if parent is None:
                continue
            mine = v005_full_semantics_features(parent)
            assert isinstance(mine["tool_diversity_count"], int)
            assert isinstance(mine["dataset_id"], int)
            for name in V005_FEATURES:
                if name not in ("tool_diversity_count", "dataset_id"):
                    assert isinstance(mine[name], float)
                    assert mine[name] == mine[name]  # finite, not NaN

    def test_payment_error_is_unrounded_absolute_gap(self):
        parent = _synthetic_parent(
            _rich_stream(),
            counts={
                "turns": 3,
                "tool_calls": 0,
                "commands": 0,
                "elapsed_steps": 7,
                "error_count": 0,
            },
        )
        mine = v005_full_semantics_features(parent)
        assert mine["payment_predicted_total"] == 7.0
        assert mine["payment_actual_total"] == 3.0
        assert mine["payment_error"] == 4.0
        # H debt rule: turns>0 and tool_calls==0 -> min(turns/20, 1).
        assert mine["debt_estimate"] == round(3 / 20, 4)
        # Unknown dataset maps to -1.
        assert mine["dataset_id"] == -1

    def test_error_recovery_ratio_uses_turn_index_not_list_order(self):
        # Error observation with a LATER turn index than every non-error
        # observation: not recovered, even though it appears first in the
        # sorted event list.
        events = [
            _event("action", "git status", cmd_family="git"),
            _event("observation", "Error: fail", is_error=True),
            _event("observation", "fine"),
        ]
        events[1]["i"] = 9
        events[2]["i"] = 1
        parent = _synthetic_parent(events)
        # _synthetic_parent renumbers positions; restore the custom
        # turn indices under test (H compares turn_index, not position).
        parent["events"][1]["i"] = 9
        parent["events"][2]["i"] = 1
        # Mirror the H computation on a raw settlement record.
        record = {
            "dataset": "synthetic_ds",
            "task_id": "task-1",
            "payment": {
                "turns": 1,
                "tool_calls": 2,
                "commands": 0,
                "elapsed_steps": 5,
                "error_count": 0,
            },
            "affordance_path": {
                "actions": [],
                "observations": [
                    {"turn_index": 9, "role": "tool", "content": "Error: fail"},
                    {"turn_index": 1, "role": "tool", "content": "fine"},
                ],
            },
            "metadata": {"tool_names": []},
            "outcome": {"success": False, "confidence": 0.9},
        }
        expected = build_calibration_frame(
            [external_record_to_model_calibration(record)]
        ).iloc[0]["error_recovery_ratio"]
        mine = v005_full_semantics_features(parent)
        assert mine["error_recovery_ratio"] == expected == 0.0


# ---------------------------------------------------------------------------
# 2. PURITY: features never see events after the cut
# ---------------------------------------------------------------------------


def _mutate_future(parent: dict[str, Any], k: int) -> dict[str, Any]:
    """Deep-copy ``parent`` and violently mutate everything after k."""
    mutant = copy.deepcopy(parent)
    for ev in mutant["events"][k:]:
        ev["hash"] = "ffffffff" if ev["hash"] != "ffffffff" else "00000000"
        ev["is_error"] = not ev["is_error"]
        ev["role"] = "mutated"
        ev["content_len"] = ev["content_len"] + 100
        ev["mentions_bash"] = not ev["mentions_bash"]
        ev["has_terminal_output"] = not ev["has_terminal_output"]
        if ev["cmd_family"] is not None:
            ev["cmd_family"] = "git" if ev["cmd_family"] != "git" else "edit"
    mutant["events"].append(
        _event("action", "pip install pytest", cmd_family="install")
    )
    mutant["events"].append(_event("observation", "Error: traceback", is_error=True))
    return mutant


class TestPrefixPurity:
    @pytest.mark.parametrize("family", ["v005_prefix_compatible", "v006"])
    def test_future_mutations_keep_features_bit_identical(self, family):
        checked = 0
        for parent in _fixture_parents():
            for kind, k in generate_prefixes(parent):
                before = v006_prefix_features(parent, k) if family == "v006" else (
                    v005_prefix_compatible_features(parent, k)
                )
                after = (
                    v006_prefix_features(_mutate_future(parent, k), k)
                    if family == "v006"
                    else v005_prefix_compatible_features(
                        _mutate_future(parent, k), k
                    )
                )
                assert before == after, (
                    f"{parent['parent_id']} cut {kind}(k={k}): future events "
                    "changed prefix features"
                )
                checked += 1
        assert checked >= 20

    def test_synthethic_stream_purity_at_every_cut(self):
        parent = _synthetic_parent(_rich_stream())
        for kind, k in generate_prefixes(parent):
            before = v006_prefix_features(parent, k)
            after = v006_prefix_features(_mutate_future(parent, k), k)
            assert before == after


# ---------------------------------------------------------------------------
# 3. FUTURE-FRACTION EXCLUSION: no final-length features anywhere
# ---------------------------------------------------------------------------


class TestLeakageExclusion:
    def test_v006_schema_contains_no_final_fraction_features(self):
        for name in V006_FEATURES:
            for pattern in LEAKY_FEATURE_PATTERNS:
                assert pattern not in name

    def test_row_schema_contains_no_final_fraction_features(self):
        frame = build_prefix_frame(
            _fixture_parents()[:3], ["v005_prefix_compatible", "v006"]
        )
        for column in frame.columns:
            for pattern in LEAKY_FEATURE_PATTERNS:
                assert pattern not in column

    def test_n_events_total_is_metadata_only(self):
        # The final length lives in an identity column for provenance, and
        # never enters the feature families themselves.
        assert "n_events_total" not in V006_FEATURES
        assert "n_events_total" not in V005_FEATURES

    def test_leaky_helper_is_rejected(self):
        assert_no_leaky_features(V006_FEATURES)  # does not raise
        assert_no_leaky_features(["n_events", "error_rate"])
        with pytest.raises(ValueError, match="prefix_fraction"):
            assert_no_leaky_features(["n_events", "prefix_fraction"])
        with pytest.raises(ValueError, match="fraction_of_final"):
            assert_no_leaky_features(["fraction_of_final_length"])
        with pytest.raises(ValueError, match="pct_of_total_length"):
            assert_no_leaky_features(["pct_of_total_length_used"])

    def test_prefix_features_do_not_vary_with_final_length(self):
        # Same prefix, different final trajectories -> identical vectors
        # (strengthens purity with a final-length-only change).
        events = _rich_stream()
        short = _synthetic_parent(events)
        longer = _synthetic_parent(
            events + [_event("action", "cat log.txt", cmd_family="inspect")]
        )
        assert len(short["events"]) != len(longer["events"])
        for k in (2, 5, 9):
            assert v006_prefix_features(short, k) == v006_prefix_features(longer, k)
            assert v005_prefix_compatible_features(short, k) == (
                v005_prefix_compatible_features(longer, k)
            )


# ---------------------------------------------------------------------------
# 4. GROUPING: prefix rows of one parent share group_key; guard raises
# ---------------------------------------------------------------------------


class TestGroupingGuard:
    @pytest.fixture
    def frame(self) -> pd.DataFrame:
        return build_prefix_frame(
            _fixture_parents(), ["v005_prefix_compatible", "v006"]
        )

    def test_all_rows_of_a_parent_share_group_key(self, frame):
        assert not frame.empty
        per_parent = frame.groupby("parent_id")["group_key"].nunique()
        assert (per_parent == 1).all()

    def test_assert_grouped_passes_on_real_rows(self, frame):
        rows = frame.to_dict("records")
        groups = assert_grouped(rows, lambda row: row["parent_id"])
        assert groups == frame["group_key"].nunique()

    def test_assert_grouped_raises_on_deliberately_ungrouped_split(self, frame):
        rows = frame.to_dict("records")
        first_same_group = [
            row
            for row in rows
            if row["group_key"] == rows[0]["group_key"]
        ]
        assert len(first_same_group) >= 2
        victim_a, victim_b = first_same_group[0], first_same_group[1]
        with pytest.raises(ValueError, match="straddles partitions"):
            assert_grouped(
                [victim_a, victim_b], lambda row: 0 if row is victim_a else 1
            )

    def test_split_by_parent_id_never_violates_grouping(self, frame):
        rows = frame.to_dict("records")
        # Any partition keyed on parent_id is group-safe by construction.
        assert_grouped(rows, lambda row: hash(row["parent_id"]) % 7)


# ---------------------------------------------------------------------------
# 5. WEIGHTS: weight_base = 1/count per parent
# ---------------------------------------------------------------------------


class TestWeightBase:
    def test_hand_computed_weight_on_swegym_fixture_parent(self):
        parents = [
            p for p in _fixture_parents() if p["dataset"] == "swegym_openhands"
        ]
        parent = parents[0]
        prefixes = generate_prefixes(parent)
        # n=4 events: early=2, pct25=1, pct50 dup(early), pre_terminal=3;
        # no error observations -> failure/recovery cuts undefined.
        assert prefixes == [("early", 2), ("pct25", 1), ("pre_terminal", 3)]

        frame = build_prefix_frame([parent], ["v006"])
        assert len(frame) == 3
        assert ((frame["weight_base"] - 1.0 / 3.0).abs() < 1e-12).all()
        assert frame["weight_base"].sum() == pytest.approx(1.0)

    def test_weights_sum_to_one_per_parent(self):
        frame = build_prefix_frame(_fixture_parents(), ["v006"])
        sums = frame.groupby("parent_id")["weight_base"].sum()
        assert all(abs(total - 1.0) < 1e-12 for total in sums)

    def test_full_frame_rows_carry_unit_weight(self):
        frame = build_full_frame(_fixture_parents()[:4], ["v005_full_semantics"])
        assert (frame["weight_base"] == 1.0).all()
        assert (frame["prefix_kind"] == "full").all()
        assert (frame["k"] == frame["n_events_total"]).all()


# ---------------------------------------------------------------------------
# 6. CUT SEMANTICS on crafted synthetic parents
# ---------------------------------------------------------------------------


class TestCutSemantics:
    def test_failure_and_recovery_cuts_point_at_their_events(self):
        events = [
            _event("action", "git status", cmd_family="git"),  # 0
            _event("observation", "Error: boom", is_error=True),  # 1 first failure
            _event("action", "pytest -q", cmd_family="test"),  # 2 first recovery
            _event("observation", "ok"),  # 3
            _event("action", "git diff", cmd_family="git"),  # 4
            _event("observation", "fine"),  # 5
            _event("action", "python x.py", cmd_family="python"),  # 6
            _event("observation", "Error: boom", is_error=True),  # 7
            _event("observation", "dead"),  # 8
        ]
        parent = _synthetic_parent(events)
        plan = plan_prefix_cuts(parent)

        assert plan["yields"]["after_first_failure"] == 2
        assert parent["events"][1]["is_error"]  # k=2 ends at first error obs
        assert plan["yields"]["after_first_recovery"] == 3
        assert parent["events"][2]["kind"] == "action"  # k=3 ends at post-failure action
        assert plan["yields"]["pre_terminal"] == 8

        # n=9: early=2, pct25=3, pct50=5 -> failure/recovery cuts dedup.
        assert plan["prefixes"] == [
            ("early", 2),
            ("pct25", 3),
            ("pct50", 5),
            ("pre_terminal", 8),
        ]
        assert plan["dropped_aliases"] == {
            "after_first_failure": "early",
            "after_first_recovery": "pct25",
        }

    def test_early_cut_floor_semantics(self):
        # n=20: floor(0.10*20)=2 -> early=2; n=100 -> capped at 8.
        small = _synthetic_parent(
            [
                _event("action", f"cmd {i}", cmd_family="other")
                for i in range(20)
            ]
        )
        big = _synthetic_parent(
            [
                _event("action", f"cmd {i}", cmd_family="other")
                for i in range(100)
            ]
        )
        assert plan_prefix_cuts(small, ["early"])["prefixes"] == [("early", 2)]
        assert plan_prefix_cuts(big, ["early"])["prefixes"] == [("early", 8)]

    def test_single_event_parent_clamps_and_drops_pre_terminal(self):
        parent = _synthetic_parent([_event("action", "only", cmd_family="other")])
        plan = plan_prefix_cuts(parent)
        assert plan["prefixes"] == [("early", 1)]
        assert plan["yields"] == {
            "early": 1,
            "pct25": 1,
            "pct50": 1,
            "after_first_failure": None,
            "after_first_recovery": None,
            "pre_terminal": None,
        }
        assert set(plan["dropped_aliases"]) == {"pct25", "pct50"}

    def test_empty_event_stream_yields_no_prefixes(self):
        parent = _synthetic_parent([])
        plan = plan_prefix_cuts(parent)
        assert plan["prefixes"] == []
        assert all(value is None for value in plan["yields"].values())

    def test_undefined_cuts_absent_from_frame_but_recorded_in_yields(self):
        no_failure = _synthetic_parent(
            [
                _event("action", "git commit -m fix", cmd_family="git"),
                _event("observation", "all ok"),
                _event("action", "pytest -q tests/", cmd_family="test"),
            ]
        )
        frame = build_prefix_frame([no_failure], ["v006"])
        kinds = set(frame["prefix_kind"])
        assert "after_first_failure" not in kinds
        assert "after_first_recovery" not in kinds
        plan = plan_prefix_cuts(no_failure)
        assert plan["yields"]["after_first_failure"] is None
        assert plan["yields"]["after_first_recovery"] is None

    def test_generate_prefixes_matches_plan(self):
        parent = _synthetic_parent(_rich_stream())
        assert generate_prefixes(parent, CANONICAL_CUT_KINDS) == (
            plan_prefix_cuts(parent, CANONICAL_CUT_KINDS)["prefixes"]
        )

    def test_unknown_cut_kind_raises(self):
        parent = _synthetic_parent(_rich_stream())
        with pytest.raises(ValueError, match="Unknown cut kinds"):
            plan_prefix_cuts(parent, ["pct90"])
        with pytest.raises(ValueError, match="Unknown cut kinds"):
            generate_prefixes(parent, ["pct90"])

    def test_all_six_canonical_kinds_are_documented(self):
        assert CANONICAL_CUT_KINDS == (
            "early",
            "pct25",
            "pct50",
            "after_first_failure",
            "after_first_recovery",
            "pre_terminal",
        )


# ---------------------------------------------------------------------------
# v006 feature values pinned on a hand-computed stream
# ---------------------------------------------------------------------------


class TestV006FeatureValues:
    @pytest.fixture
    def features(self) -> dict[str, Any]:
        return v006_prefix_features(_synthetic_parent(_rich_stream()), 12)

    def test_depth(self, features):
        assert features["n_events"] == 12.0
        assert features["n_actions"] == 6.0
        assert features["n_observations"] == 6.0

    def test_closure(self, features):
        # Every action has a later observation.
        assert features["unresolved_action_rate"] == 0.0
        assert features["action_observation_closure_ratio"] == 1.0

    def test_tool_dynamics(self, features):
        families = ["git", "test", "edit", "edit", "edit", "test"]
        switches = sum(
            1 for a, b in zip(families, families[1:]) if a != b
        )
        assert features["used_family_diversity"] == 3.0
        assert features["tool_switch_rate"] == round(switches / 5, 4)  # 0.6
        assert features["repeated_action_rate"] == round(2 / 6, 4)  # 0.3333
        assert features["max_repeated_action_run"] == 3.0

    def test_errors(self, features):
        assert features["error_count"] == 3.0
        assert features["error_rate"] == round(3 / 12, 4)  # 0.25
        assert features["distinct_error_count"] == 1.0
        assert features["repeated_error_rate"] == round(2 / 3, 4)  # 0.6667

    def test_recovery(self, features):
        # Errors at 1, 6, 8; attempts at 2 and 7.
        assert features["recovery_attempt_count"] == 2.0
        assert features["recovery_rate"] == round(2 / 3, 4)
        # Latencies: 3-1=2, 9-6=3, 9-8=1 -> mean 2.0; first = 2.0.
        assert features["recovery_latency_mean"] == 2.0
        assert features["first_recovery_latency"] == 2.0
        # git (pre) -> test (post) differs.
        assert features["strategy_change_after_first_failure"] == 1.0

    def test_verification(self, features):
        assert features["verification_action_count"] == 2.0
        assert features["verification_rate"] == round(2 / 6, 4)
        # pytest at 10 follows an edit-family action (4/5/7).
        assert features["verification_after_edit_count"] == 1.0
        # pytest at 10 follows error@1 plus intervening recovery action@2.
        assert features["verification_after_recovery_count"] == 1.0

    def test_evidence(self, features):
        # Observation hashes in order: e1, ok, e1, e1, fresh, ok ->
        # 3 first-seen of 6.
        assert features["observation_novelty_rate"] == round(3 / 6, 4)  # 0.5
        # Prefix ends with an observation.
        assert features["actions_since_last_observation"] == 0.0
        # Only action@7 sees a duplicate of the preceding observation (e1).
        assert features["actions_without_observation_rate"] == round(1 / 6, 4)

    def test_stuck_loop(self, features):
        # (edit h3 -> err e1) at (5,6) and (7,8): consecutive identical pair.
        assert features["stuck_cycle_max"] == 2.0
        assert features["stuck_loop_indicator"] == 1.0

    def test_indicators(self, features):
        assert features["has_failure"] == 1.0
        assert features["has_recovery"] == 1.0

    def test_undefined_quantities_are_zero_with_indicators(self):
        # Failure-free open stream: A(git) O(ok) A(test) -- the trailing
        # action has no observation after it.
        clean = _synthetic_parent(
            [
                _event("action", "git commit -m fix", cmd_family="git"),
                _event("observation", "all ok"),
                _event("action", "pytest -q tests/", cmd_family="test"),
            ]
        )
        feats = v006_prefix_features(clean, 3)
        assert feats["error_count"] == 0.0
        assert feats["has_failure"] == 0.0
        assert feats["has_recovery"] == 0.0
        assert feats["recovery_rate"] == 0.0
        assert feats["recovery_latency_mean"] == 0.0
        assert feats["first_recovery_latency"] == 0.0
        assert feats["strategy_change_after_first_failure"] == 0.0
        assert feats["stuck_cycle_max"] == 0.0
        assert feats["stuck_loop_indicator"] == 0.0
        assert feats["repeated_error_rate"] == 0.0
        # Unresolved open streak: no observation after the last action.
        assert feats["unresolved_action_rate"] == 0.5
        assert feats["actions_since_last_observation"] == 1.0

    def test_all_features_finite_rounded_floats(self):
        for parent in _fixture_parents():
            for _, k in generate_prefixes(parent):
                feats = v006_prefix_features(parent, k)
                assert set(feats) == set(V006_FEATURES)
                for name, value in feats.items():
                    assert isinstance(value, float)
                    assert value == value and abs(value) != float("inf")
                    assert value == round(value, 4)


# ---------------------------------------------------------------------------
# 7. DETERMINISM: seed-free, identical frames on repeated extraction
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_prefix_frame_identical_across_extractions(self):
        parents = _fixture_parents()
        first = build_prefix_frame(
            parents, ["v005_prefix_compatible", "v006"]
        )
        second = build_prefix_frame(
            parents, ["v005_prefix_compatible", "v006"]
        )
        pd.testing.assert_frame_equal(first, second)

    def test_family_order_does_not_change_the_frame(self):
        parents = _fixture_parents()
        canonical = build_prefix_frame(
            parents, ["v005_prefix_compatible", "v006"]
        )
        shuffled = build_prefix_frame(
            parents, ["v006", "v005_prefix_compatible"]
        )
        pd.testing.assert_frame_equal(canonical, shuffled)

    def test_full_frame_identical_across_extractions(self):
        parents = _fixture_parents()
        first = build_full_frame(parents, ["v005_full_semantics"])
        second = build_full_frame(parents, ["v005_full_semantics"])
        pd.testing.assert_frame_equal(first, second)
        # Full frame rows match the direct full-semantics extraction.
        for _, row in first.iterrows():
            direct = v005_full_semantics_features(
                next(p for p in parents if p["parent_id"] == row["parent_id"])
            )
            for name, value in direct.items():
                if name == "dataset_id":
                    assert row[name] == value
                else:
                    assert row[name] == value

    def test_unknown_family_raises(self):
        with pytest.raises(ValueError, match="Unknown feature families"):
            build_prefix_frame(_fixture_parents()[:1], ["v006", "nope"])

    def test_schema_versions_are_the_three_normative_tags(self):
        assert SCHEMA_VERSIONS == {
            "v005_full_semantics": "v005_full_semantics@1",
            "v005_prefix_compatible": "v005_prefix_compatible@1",
            "v006": "v006@1",
        }
