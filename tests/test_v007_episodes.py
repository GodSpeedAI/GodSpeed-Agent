"""Tests for v007 failure-episode construction (frozen definition).

All tests run against local fixtures and crafted synthetic parents --
no network.  The suite pins: (1) the frozen episode definition
(leading context errors, maximal runs with intervening actions,
trailing-error exclusion, R0-only episodes), (2) the recovery_success
target and label-audit buckets, (3) episode-record invariants, (4) the
dataset:repository split grouping and its refusal guard, (5) parent
episode weights (1/training-episodes-per-parent, episodes not rows),
(6) determinism, (7) schema hygiene (no leaky/label-side feature
names), and (8) the CLI materialization over a temp config.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
import yaml

from scripts.settlement_datasets.adapter_base import write_records_jsonl
from scripts.settlement_datasets.build_trajectory_corpus import build_parent
from scripts.settlement_datasets.v006_features import assert_no_leaky_features
from scripts.settlement_datasets.v007_recovery import (
    ABLATION_EXTRA_COLUMN,
    AUDIT_BUCKETS,
    AUDIT_ESCAPE_NO_SETTLEMENT,
    AUDIT_ESCAPE_WITH_SETTLEMENT,
    AUDIT_NO_ESCAPE_NO_SETTLEMENT,
    AUDIT_NO_ESCAPE_WITH_SETTLEMENT,
    EXCLUSION_FAILURE_IS_FINAL_EVENT,
    FRAME_COLUMNS,
    POINT_R0,
    POINT_R1,
    R0_FEATURES,
    R1_ADDITIONS,
    V005_MINIMAL_RECOVERY_FEATURES,
    assert_grouped_by_split_group,
    assert_no_label_features,
    assert_recovery_schemas_clean,
    build_episode_frame,
    build_episode_table,
    build_failure_episodes,
    build_failure_scan,
    main,
    parent_balanced_training_weights,
    parse_repository,
    split_group_for_parent,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "settlement_datasets"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _swegym_fixture_parents() -> list[dict[str, Any]]:
    """Fixture rows through the real v006 corpus builder (build_parent)."""
    from scripts.settlement_datasets.registry import get_adapter

    adapter = get_adapter("swegym_openhands")
    out: list[dict[str, Any]] = []
    for raw in _read_jsonl(FIXTURES_DIR / "swegym_openhands" / "sample.jsonl"):
        record = adapter.to_settlement_record(raw)
        parent, reason = build_parent(
            record, revision_sha="rev", license_status="l", min_confidence=0.65
        )
        assert parent is not None, reason
        out.append(parent)
    return out


def _event(
    kind: str,
    content: str,
    *,
    cmd_family: str | None = None,
    is_error: bool = False,
) -> dict[str, Any]:
    is_action = kind == "action"
    return {
        "i": 0,
        "kind": kind,
        "role": "assistant" if is_action else "tool",
        "content_len": len(content),
        "hash": hashlib.sha1(content.encode("utf-8")).hexdigest()[:10],
        "mentions_bash": False,
        "is_error": kind == "observation" and is_error,
        "cmd_family": cmd_family if is_action else None,
        "has_terminal_output": False,
    }


def _act(content: str, cmd_family: str) -> dict[str, Any]:
    return _event("action", content, cmd_family=cmd_family)


def _err(content: str = "Error: traceback boom") -> dict[str, Any]:
    return _event("observation", content, is_error=True)


def _ok(content: str = "all ok") -> dict[str, Any]:
    return _event("observation", content)


def _synthetic_parent(
    events: list[dict[str, Any]],
    *,
    label: int = 0,
    group_key: str = "synthetic:repoa__pkg-1",
    parent_id: str | None = None,
) -> dict[str, Any]:
    if parent_id is None:
        parent_id = group_key + ":run-a"
    parent: dict[str, Any] = {
        "parent_id": parent_id,
        "group_key": group_key,
        "dataset": "synthetic_ds",
        "revision_sha": "rev",
        "license_status": "test-license",
        "label": label,
        "label_source": f"success={bool(label)}",
        "outcome_confidence": 0.9,
        "n_context_events": 1,
        "total_messages": 1 + len(events),
        "tool_names_manifest": ["execute_bash"],
        "counts": {
            "turns": sum(1 for ev in events if ev["kind"] == "action"),
            "tool_calls": sum(1 for ev in events if ev["kind"] == "observation"),
            "commands": 0,
            "elapsed_steps": 1 + len(events),
            "error_count": sum(
                1 for ev in events if ev["kind"] == "observation" and ev["is_error"]
            ),
        },
        "events": copy.deepcopy(events),
    }
    for i, ev in enumerate(parent["events"]):
        ev["i"] = i
    return parent


def _single_episode_stream() -> list[dict[str, Any]]:
    """Positions: 0 A(git) 1 O(ok) 2 O(err e) 3 A(git) 4 O(err) 5 A(edit)
    6 O(err) 7 O(ok) -- one maximal error run (2,4,6) with intervening
    actions; escape at 7."""
    return [
        _act("git commit -m fix", "git"),
        _ok(),
        _err(),
        _act("git commit -m fix", "git"),
        _err(),
        _act("sed -i s/a/b/ f.py", "edit"),
        _err(),
        _ok(),
    ]


# ---------------------------------------------------------------------------
# 1. EPISODE DEFINITION edge cases
# ---------------------------------------------------------------------------


class TestEpisodeDefinition:
    def test_leading_context_errors_never_open_episodes(self):
        parent = _synthetic_parent([_err(), _err(), _act("ls", "inspect"), _ok()])
        episodes = build_failure_episodes(parent)
        assert episodes == []
        scan = build_failure_scan(parent)
        assert scan["leading_error_runs"] == 1
        assert scan["exclusions"] == []

    def test_leading_run_then_later_valid_episode(self):
        events = [
            _err(),  # 0 leading run (never opens)
            _act("ls", "inspect"),  # 1
            _ok(),  # 2
            _err(),  # 3 episode opens here
            _act("pytest -q", "test"),  # 4
            _ok(),  # 5 escape
        ]
        parent = _synthetic_parent(events)
        episodes = build_failure_episodes(parent)
        assert [ep["e"] for ep in episodes] == [3]
        assert episodes[0]["r0_k"] == 4
        # Attempt at 4; its result observation at 5 is included, so the
        # window closes at 6 (= n: the result is the final event).
        assert episodes[0]["r1_k"] == 6
        scan = build_failure_scan(parent)
        assert scan["leading_error_runs"] == 1
        assert scan["escape_positions"] == [5]

    def test_consecutive_error_run_with_intervening_actions_is_one_episode(self):
        parent = _synthetic_parent(_single_episode_stream())
        episodes = build_failure_episodes(parent)
        assert len(episodes) == 1
        record = episodes[0]
        assert record["e"] == 2
        assert record["r0_k"] == 3
        # First post-failure action at 3; consecutive result obs at 4.
        assert record["r1_k"] == 5
        scan = build_failure_scan(parent)
        assert scan["escape_positions"] == [7]

    def test_trailing_error_final_event_is_excluded_and_counted(self):
        parent = _synthetic_parent(
            [_act("git status", "git"), _ok(), _act("pytest -q", "test"), _err()]
        )
        episodes = build_failure_episodes(parent)
        assert episodes == []
        scan = build_failure_scan(parent)
        assert scan["exclusions"] == [
            {"e": 3, "bucket": EXCLUSION_FAILURE_IS_FINAL_EVENT}
        ]

    def test_no_post_failure_action_is_r0_only(self):
        parent = _synthetic_parent([_act("git status", "git"), _ok(), _err(), _err(), _ok()])
        episodes = build_failure_episodes(parent)
        assert len(episodes) == 1
        assert episodes[0]["r1_k"] is None
        frame = build_episode_frame([parent])
        assert list(frame["point"]) == [POINT_R0]

    def test_r1_closes_at_action_when_action_is_final_event(self):
        parent = _synthetic_parent([_ok(), _err(), _act("pytest -q", "test")])
        episodes = build_failure_episodes(parent)
        assert len(episodes) == 1
        # Attempt at position 2 is the final event: R1 closes at it.
        assert episodes[0]["r1_k"] == 3
        assert episodes[0]["n_events_total"] == 3
        frame = build_episode_frame([parent])
        r1 = frame[frame["point"] == POINT_R1]
        assert len(r1) == 1
        # No result observation: undefined quantities stay 0.0.
        assert r1.iloc[0]["has_attempt_result"] == 0.0
        assert r1.iloc[0]["attempt_result_is_error"] == 0.0

    def test_parent_without_errors_yields_nothing(self):
        parent = _synthetic_parent([_act("git status", "git"), _ok()])
        scan = build_failure_scan(parent)
        assert scan == {
            "episodes": [],
            "escape_positions": [],
            "exclusions": [],
            "leading_error_runs": 0,
        }

    def test_r1_window_includes_only_consecutive_results(self):
        # Attempt at 2; results at 3 and 4 (consecutive); the NEXT action
        # at 5 stops the window: r1_k = 5.
        events = [
            _ok(),  # 0
            _err(),  # 1 e
            _act("pytest -q", "test"),  # 2 attempt
            _err(),  # 3 result (same failure immediately repeated)
            _ok(),  # 4 result (also the escape)
            _act("git diff", "git"),  # 5 next action
            _ok(),  # 6 outside the R1 window
        ]
        parent = _synthetic_parent(events)
        episodes = build_failure_episodes(parent)
        assert episodes[0]["r1_k"] == 5
        frame = build_episode_frame([parent])
        r1 = frame[frame["point"] == POINT_R1].iloc[0]
        assert r1["obs_between_failure_and_attempt"] == 0.0
        # Result at 3 repeats the failure hash -> error, same hash.
        assert r1["attempt_result_is_error"] == 1.0
        assert r1["attempt_result_same_hash_as_failure"] == 1.0
        # The attempt's non-error result at 4 is the escape (label-side):
        # with parent label 0 this is escape without settlement.
        assert episodes[0]["audit_bucket"] == AUDIT_ESCAPE_NO_SETTLEMENT


# ---------------------------------------------------------------------------
# 2. TARGET + LABEL AUDIT BUCKETS
# ---------------------------------------------------------------------------


class TestLabelsAndBuckets:
    def test_escape_with_settlement_is_positive(self):
        parent = _synthetic_parent(
            [_ok(), _err(), _act("pytest -q", "test"), _ok()], label=1
        )
        record = build_failure_episodes(parent)[0]
        assert record["recovery_success"] == 1
        assert record["audit_bucket"] == AUDIT_ESCAPE_WITH_SETTLEMENT

    def test_escape_without_settlement_is_not_recovery(self):
        parent = _synthetic_parent(
            [_ok(), _err(), _act("pytest -q", "test"), _ok()], label=0
        )
        record = build_failure_episodes(parent)[0]
        assert record["recovery_success"] == 0
        assert record["audit_bucket"] == AUDIT_ESCAPE_NO_SETTLEMENT

    def test_no_escape_with_settlement_is_trailing_error_edge(self):
        parent = _synthetic_parent(
            [_ok(), _err(), _act("pytest -q", "test"), _err()], label=1
        )
        episodes = build_failure_episodes(parent)
        assert len(episodes) == 1  # e=1 is not the final event
        record = episodes[0]
        assert record["recovery_success"] == 0
        assert record["audit_bucket"] == AUDIT_NO_ESCAPE_WITH_SETTLEMENT

    def test_no_escape_no_settlement(self):
        parent = _synthetic_parent(
            [_ok(), _err(), _act("pytest -q", "test"), _err()], label=0
        )
        record = build_failure_episodes(parent)[0]
        assert record["recovery_success"] == 0
        assert record["audit_bucket"] == AUDIT_NO_ESCAPE_NO_SETTLEMENT

    def test_escape_alone_never_suffices_mirror_pair(self):
        events = [_ok(), _err(), _act("pytest -q", "test"), _ok()]
        negative = build_failure_episodes(_synthetic_parent(events, label=0))[0]
        positive = build_failure_episodes(_synthetic_parent(events, label=1))[0]
        assert negative["recovery_success"] == 0
        assert positive["recovery_success"] == 1

    def test_audit_buckets_partition_the_frame(self):
        parents = [
            _synthetic_parent([_ok(), _err(), _act("pytest -q", "test"), _ok()], label=1),
            _synthetic_parent([_ok(), _err(), _act("pytest -q", "test"), _ok()], label=0),
            _synthetic_parent([_ok(), _err(), _act("pytest -q", "test"), _err()], label=1),
            _synthetic_parent([_ok(), _err(), _act("pytest -q", "test"), _err()], label=0),
        ]
        frame = build_episode_frame(parents)
        assert set(frame["audit_bucket"]) == set(AUDIT_BUCKETS)
        positives = frame["recovery_success"] == 1
        assert (frame.loc[positives, "audit_bucket"] == AUDIT_ESCAPE_WITH_SETTLEMENT).all()
        assert (frame.loc[~positives, "audit_bucket"] != AUDIT_ESCAPE_WITH_SETTLEMENT).all()
        assert set(frame["recovery_success"].unique()) <= {0, 1}


# ---------------------------------------------------------------------------
# 3. EPISODE RECORD invariants
# ---------------------------------------------------------------------------


class TestEpisodeRecords:
    def test_running_ids_and_multi_episode_fields(self):
        events = [
            _act("git commit -m fix", "git"),  # 0
            _ok(),  # 1
            _err("Error: e1"),  # 2 episode 0
            _act("pytest -q", "test"),  # 3
            _ok(),  # 4 escape of episode 0
            _act("git diff", "git"),  # 5
            _err("Error: e2"),  # 6 episode 1
            _act("pytest -q", "test"),  # 7
            _ok(),  # 8 escape of episode 1
        ]
        parent = _synthetic_parent(events, label=1)
        episodes = build_failure_episodes(parent)
        assert [ep["episode_id"] for ep in episodes] == [
            f"{parent['parent_id']}:ep0",
            f"{parent['parent_id']}:ep1",
        ]
        assert [ep["episode_index"] for ep in episodes] == [0, 1]
        assert [ep["e"] for ep in episodes] == [2, 6]
        assert [ep["r0_k"] for ep in episodes] == [3, 7]
        scan = build_failure_scan(parent)
        assert scan["escape_positions"] == [4, 8]
        # Frozen record fields all present.
        expected_keys = {
            "episode_id",
            "episode_index",
            "parent_id",
            "group_key",
            "split_group",
            "dataset",
            "parent_label",
            "e",
            "r0_k",
            "r1_k",
            "recovery_success",
            "audit_bucket",
            "n_events_total",
        }
        assert set(episodes[0]) == expected_keys

    def test_scan_invariants_hold_on_crafted_multi_episode_parent(self):
        events = [
            _act("git commit -m fix", "git"),
            _ok(),
            _err(),
            _act("pytest -q", "test"),
            _ok(),
            _act("git diff", "git"),
            _err(),
            _act("pytest -q", "test"),
            _ok(),
            _err(),
        ]  # last error run is trailing-final -> excluded
        parent = _synthetic_parent(events)
        scan = build_failure_scan(parent)
        episodes = scan["episodes"]
        for record in episodes:
            assert record["r0_k"] == record["e"] + 1
            assert record["e"] < record["n_events_total"] - 1
        # Every episode's streak of prior non-error observations >= 1 and
        # prior escapes equal prior episodes (maximality argument).
        from scripts.settlement_datasets.v007_recovery import (
            _current_streak_prior_nonerror,
        )

        frame = build_episode_frame([parent])
        for record in episodes:
            streak = _current_streak_prior_nonerror(parent, record["e"])
            assert streak >= 1
            row = frame[frame["episode_index"] == record["episode_index"]].iloc[0]
            assert row["current_streak_prior_nonerror"] == float(streak)
            assert row["prior_escape_count"] == row["prior_episode_count"]
            assert row["prior_escape_count"] == float(record["episode_index"])
        assert scan["exclusions"] == [
            {"e": 9, "bucket": EXCLUSION_FAILURE_IS_FINAL_EVENT}
        ]


# ---------------------------------------------------------------------------
# 4. GROUPING: dataset:repository split keys + refusal guard
# ---------------------------------------------------------------------------


class TestGrouping:
    def test_parse_repository_strips_version_tags(self):
        assert parse_repository("django__django-4.2") == "django__django"
        assert parse_repository("getmoto__moto-5321") == "getmoto__moto"
        assert parse_repository("scikit-learn__scikit-learn-1.4") == (
            "scikit-learn__scikit-learn"
        )
        assert parse_repository("plain__repo") == "plain__repo"
        assert parse_repository("pandas-dev__pandas-57121") == "pandas-dev__pandas"

    def test_split_group_is_dataset_colon_repository(self):
        parent = _synthetic_parent(
            [_ok(), _err(), _act("pytest -q", "test"), _ok()],
            group_key="swegym_openhands:getmoto__moto-5321",
        )
        assert split_group_for_parent(parent) == "swegym_openhands:getmoto__moto"
        episodes = build_failure_episodes(parent)
        assert episodes[0]["split_group"] == "swegym_openhands:getmoto__moto"
        assert episodes[0]["group_key"] == "swegym_openhands:getmoto__moto-5321"

    def _repo_pair(self) -> list[dict[str, Any]]:
        return [
            _synthetic_parent(
                [_ok(), _err(), _act("pytest -q", "test"), _ok()],
                group_key="ds:repoa__pkg-1",
                parent_id="ds:repoa__pkg-1:run-a",
            ),
            _synthetic_parent(
                [_ok(), _err(), _act("pytest -q", "test"), _ok()],
                group_key="ds:repoa__pkg-2",
                parent_id="ds:repoa__pkg-2:run-b",
            ),
        ]

    def test_frame_rows_carry_split_group(self):
        frame = build_episode_frame(self._repo_pair())
        # "repoa__pkg-1" / "repoa__pkg-2" both parse to repo "repoa__pkg".
        assert set(frame["split_group"]) == {"ds:repoa__pkg"}
        assert frame["group_key"].nunique() == 2

    def test_guard_passes_when_partitions_keyed_on_split_group(self):
        frame = build_episode_frame(self._repo_pair())
        rows = frame.to_dict("records")
        checked = assert_grouped_by_split_group(
            rows, lambda row: row["split_group"]
        )
        assert checked == 1
    def test_guard_refuses_split_within_a_repository(self):
        frame = build_episode_frame(self._repo_pair())
        rows = frame.to_dict("records")
        # A partition boundary drawn between the two same-repo parents
        # must be refused.
        with pytest.raises(ValueError, match="straddles partitions"):
            assert_grouped_by_split_group(
                rows,
                lambda row: row["parent_id"],  # type: ignore[arg-type, return-value]
            )


# ---------------------------------------------------------------------------
# 5. WEIGHTS: 1/training-episodes-per-parent
# ---------------------------------------------------------------------------


class TestWeights:
    def _two_parent_frame(self) -> pd.DataFrame:
        parent_a = _synthetic_parent(
            [
                _ok(),
                _err(),
                _act("pytest -q", "test"),
                _ok(),
                _act("git diff", "git"),
                _err(),
                _act("pytest -q", "test"),
                _ok(),
            ],
            group_key="ds:repoa__pkg-1",
        )  # two episodes
        parent_b = _synthetic_parent(
            [_ok(), _err(), _act("pytest -q", "test"), _ok()],
            group_key="ds:repob__pkg-1",
            parent_id="ds:repob__pkg-1:run-b",
        )  # one episode
        return build_episode_frame([parent_a, parent_b])

    def test_weight_base_is_inverse_total_episode_count(self):
        frame = self._two_parent_frame()
        a = frame[frame["parent_id"].str.contains("repoa")]
        b = frame[frame["parent_id"].str.contains("repob")]
        assert (a["weight_base"] == 0.5).all()
        assert (b["weight_base"] == 1.0).all()
        assert (a["n_parent_episodes"] == 2).all()
        assert (b["n_parent_episodes"] == 1).all()

    def test_training_weights_count_episodes_never_rows(self):
        # One parent, ONE episode that has both an R0 and an R1 row:
        # the pooled frame has 2 rows but 1 training episode.
        parent = _synthetic_parent(
            [_ok(), _err(), _act("pytest -q", "test"), _ok()]
        )
        frame = build_episode_frame([parent])
        assert len(frame) == 2
        weights = parent_balanced_training_weights(frame)
        assert weights.tolist() == [1.0, 1.0]

    def test_training_weights_on_single_point_frame(self):
        frame = self._two_parent_frame()
        r0 = frame[frame["point"] == POINT_R0]
        weights = parent_balanced_training_weights(r0)
        expected = [0.5, 0.5, 1.0]
        assert weights.tolist() == expected
        # Weights sum to the parent count (balanced).
        assert weights.sum() == pytest.approx(2.0)

    def test_training_weights_empty_frame(self):
        empty = pd.DataFrame(columns=list(FRAME_COLUMNS))
        assert parent_balanced_training_weights(empty).empty


# ---------------------------------------------------------------------------
# 6. DETERMINISM + fixture integration
# ---------------------------------------------------------------------------


class TestDeterminismAndFixtures:
    def test_scan_and_frame_are_deterministic(self):
        parents = [
            _synthetic_parent(_single_episode_stream(), label=1),
            _synthetic_parent(
                [_ok(), _err(), _act("pytest -q", "test"), _ok()],
                group_key="ds:repob__pkg-1",
            ),
        ]
        first_frame = build_episode_frame(parents)
        second_frame = build_episode_frame(parents)
        pd.testing.assert_frame_equal(first_frame, second_frame)
        first_scans = [build_failure_scan(p) for p in parents]
        second_scans = [build_failure_scan(p) for p in parents]
        assert first_scans == second_scans

    def test_swegym_fixture_parent_excludes_final_event_error(self):
        parents = _swegym_fixture_parents()
        assert len(parents) == 2
        # Fixture row 2 ("pytest failed with AssertionError ...") ends on
        # its error observation: excluded with the frozen bucket.
        scans = [build_failure_scan(p) for p in parents]
        total_episodes = sum(len(scan["episodes"]) for scan in scans)
        total_exclusions = sum(len(scan["exclusions"]) for scan in scans)
        assert total_episodes == 0
        assert total_exclusions == 1
        assert scans[1]["exclusions"][0]["bucket"] == EXCLUSION_FAILURE_IS_FINAL_EVENT
        frame = build_episode_frame(parents)
        assert frame.empty
        assert list(frame.columns) == list(FRAME_COLUMNS)

    def test_zero_episode_sources_are_graceful_in_the_table(self, tmp_path):
        corpus = tmp_path / "no_errors.jsonl"
        write_records_jsonl(
            [_synthetic_parent([_act("git status", "git"), _ok()])], corpus
        )
        config = {
            "episodes_id": "v007-episodes-test",
            "sources": [
                {"name": "no_errors_ds", "corpus_path": str(corpus)},
            ],
            "episode_definition": {"opening": "frozen"},
            "audit_buckets": list(AUDIT_BUCKETS),
            "exclusion_buckets": [EXCLUSION_FAILURE_IS_FINAL_EVENT],
            "feature_schemas": {"r0": {}, "r1": {}, "ablation": {}},
            "output": {
                "root": str(tmp_path / "out"),
                "episode_table": str(tmp_path / "out" / "episodes.jsonl"),
                "manifest": str(tmp_path / "out" / "manifest.json"),
            },
        }
        built = build_episode_table(config)
        manifest = built["manifest"]
        assert manifest["totals"]["episodes"] == 0
        assert manifest["sources"]["no_errors_ds"]["episodes"] == 0
        assert manifest["sources"]["no_errors_ds"]["parents_scanned"] == 1
        assert built["frame"].empty


# ---------------------------------------------------------------------------
# 7. CLI materialization over a temp config
# ---------------------------------------------------------------------------


class TestCliMain:
    def test_main_writes_table_and_manifest(self, tmp_path, monkeypatch, capsys):
        corpus = tmp_path / "swegym_openhands.jsonl"
        parents = [
            _synthetic_parent(
                [_ok(), _err(), _act("pytest -q", "test"), _ok()], label=1
            ),
            _synthetic_parent(
                [
                    _ok(),
                    _err(),
                    _act("pytest -q", "test"),
                    _ok(),
                    _act("git diff", "git"),
                    _err(),
                    _act("pytest -q", "test"),
                    _ok(),
                ],
                label=0,
                group_key="synthetic:repob__pkg-1",
            ),
        ]
        write_records_jsonl(parents, corpus)
        config = {
            "episodes_id": "v007-episodes-test",
            "sources": [{"name": "swegym_openhands", "corpus_path": str(corpus)}],
            "episode_definition": {"opening": "frozen"},
            "audit_buckets": list(AUDIT_BUCKETS),
            "exclusion_buckets": [EXCLUSION_FAILURE_IS_FINAL_EVENT],
            "feature_schemas": {"r0": {}, "r1": {}, "ablation": {}},
            "output": {
                "root": str(tmp_path / "out"),
                "episode_table": str(tmp_path / "out" / "episodes.jsonl"),
                "manifest": str(tmp_path / "out" / "manifest.json"),
            },
        }
        config_path = tmp_path / "v007_episodes.yaml"
        config_path.write_text(yaml.safe_dump(config), encoding="utf-8")

        monkeypatch.setattr("sys.argv", ["v007_recovery.py", "--config", str(config_path)])
        main()

        manifest = json.loads((tmp_path / "out" / "manifest.json").read_text())
        table = _read_jsonl(tmp_path / "out" / "episodes.jsonl")
        # 3 episodes: one with R1 + two with R1... parent A: 1 episode w/
        # R1; parent B: 2 episodes w/ R1 -> 3 episodes, 6 rows.
        assert manifest["totals"]["episodes"] == 3
        assert manifest["totals"]["rows_total"] == len(table) == 6
        assert manifest["totals"]["rows_r0"] == 3
        assert manifest["totals"]["rows_r1"] == 3
        assert manifest["totals"]["recovery_success_1"] == 1
        assert manifest["episodes_per_parent"]["mean"] == 1.5
        assert manifest["episode_table_sha256"] == hashlib.sha256(
            (tmp_path / "out" / "episodes.jsonl").read_bytes()
        ).hexdigest()
        assert "v007" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# 8. SCHEMA HYGIENE guards
# ---------------------------------------------------------------------------


class TestSchemaHygiene:
    def test_all_schemas_pass_leak_and_label_guards(self):
        assert_recovery_schemas_clean()  # does not raise
        assert_no_leaky_features(R0_FEATURES)
        assert_no_leaky_features(R0_FEATURES + R1_ADDITIONS)
        assert_no_leaky_features(V005_MINIMAL_RECOVERY_FEATURES)

    @pytest.mark.parametrize(
        "token",
        ["escape", "recovery_success", "label", "settlement"],
    )
    def test_label_side_names_are_rejected(self, token):
        with pytest.raises(ValueError, match="forbidden"):
            assert_no_label_features([f"legit_feature", f"sneaky_{token}_count"])

    def test_frame_has_no_duplicate_or_extra_columns(self):
        parent = _synthetic_parent(_single_episode_stream())
        frame = build_episode_frame([parent])
        assert list(frame.columns) == list(FRAME_COLUMNS)
        assert len(set(frame.columns)) == len(frame.columns)
