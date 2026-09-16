"""Tests for the v006 shared parent-trajectory corpus builder.

All tests run against local fixtures via ``input_path`` -- no network.
Corpus events must never carry raw trajectory text.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts.settlement_datasets.build_trajectory_corpus import (
    REASON_CONFIDENCE_BELOW_THRESHOLD,
    REASON_OUTCOME_UNDEFINED,
    _classify_cmd_family,
    _trajectory_content_hash,
    build_corpus,
    build_parent,
    load_corpus_config,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "settlement_datasets"

EXPECTED_EVENT_KEYS = {
    "i",
    "kind",
    "role",
    "content_len",
    "hash",
    "mentions_bash",
    "is_error",
    "cmd_family",
    "has_terminal_output",
    # Context-scoping annotation (v007 correction MAJOR-1): the number
    # of context messages strictly below the event's turn index.
    "ctx",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _rich_record() -> dict[str, Any]:
    return {
        "dataset": "test_ds",
        "domain": "code",
        "task_id": "task-1",
        "source_uri": "test/source",
        "desired_direction": {},
        "environment": {},
        "representational_state": {},
        "payment": {
            "turns": 2,
            "tool_calls": 2,
            "commands": 2,
            "page_actions": 0,
            "api_calls": 0,
            "elapsed_steps": 6,
            "error_count": 1,
            "estimated_complexity": "medium",
            "evidence": [],
        },
        "affordance_path": {
            "actions": [
                {
                    "turn_index": 2,
                    "role": "assistant",
                    "action_type": "message",
                    "content": "run bash to check git diff",
                },
                {
                    "turn_index": 4,
                    "role": "assistant",
                    "action_type": "message",
                    "content": "pip install pytest",
                },
            ],
            "observations": [
                {"turn_index": 3, "role": "tool", "content": "Error: tests failed"},
                {
                    "turn_index": 5,
                    "role": "tool",
                    "content": "New Terminal Output:\nok",
                },
            ],
            "recovery_events": [],
        },
        "outcome": {
            "success": True,
            "reward": 1.0,
            "score": 1.0,
            "settlement_quality": "clean_success",
            "confidence": 0.9,
            "evidence": ["resolved=True"],
        },
        "labels": {},
        "metadata": {"tool_names": ["execute_bash", "finish", ""]},
    }


def _write_test_config(tmp_path: Path, extra_datasets: list[dict[str, Any]]) -> Path:
    config = {
        "corpus_id": "v006-test",
        "min_confidence": 0.65,
        "settlement_classification": "external-proxy-settlement",
        "usability_rule": (
            "parent accepted iff terminal label defined (outcome.success is "
            "not None) AND outcome confidence >= 0.65"
        ),
        "datasets": extra_datasets,
    }
    config_path = tmp_path / "corpus.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return config_path


def _fixture_dataset(name: str, **overrides: Any) -> dict[str, Any]:
    entry = {
        "name": name,
        "source_uri": f"test/{name}",
        "adapter": name,
        "split": "train",
        "max_rows": 10,
        "revision_sha": f"rev-{name}",
        "license_status": f"test-license-{name}",
        "input_path": str(FIXTURES_DIR / name / "sample.jsonl"),
    }
    entry.update(overrides)
    return entry


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------


class TestCorpusConfig:
    def test_v006_config_loads_with_two_live_sources(self):
        config = load_corpus_config("configs/settlement_datasets/v006_corpus.yaml")

        names = [ds["name"] for ds in config["datasets"]]
        assert names == ["swegym_openhands", "nebius_swe_agent"]
        assert config["min_confidence"] == 0.65
        assert "outcome.success is not None" in config["usability_rule"]

        by_name = {ds["name"]: ds for ds in config["datasets"]}
        assert by_name["swegym_openhands"]["split"] == "train.raw"
        assert by_name["swegym_openhands"]["max_rows"] == 3000
        assert by_name["nebius_swe_agent"]["max_rows"] == 5000
        assert (
            by_name["swegym_openhands"]["revision_sha"]
            == "baf3a4e4bff514d48ddc08a93a2ade5c126212c7"
        )
        assert (
            by_name["nebius_swe_agent"]["revision_sha"]
            == "68195a1450865274106246d0d0296a1d6807b88e"
        )
        for ds in config["datasets"]:
            assert "cc-by-4.0" in ds["license_status"] or (
                "ambiguous" in ds["license_status"]
            )

    def test_agenttrove_rejection_is_documented_in_config(self):
        # AgentTrove is rejected for v006 (no verified terminal label in the
        # live revision); the config must record the rejection with evidence.
        config_text = Path(
            "configs/settlement_datasets/v006_corpus.yaml"
        ).read_text(encoding="utf-8")
        assert "REJECTED SOURCE" in config_text
        assert "agenttrove" in config_text
        assert "b395a4307a2bc9950a90dc899438f149e115fc60" in config_text
        assert "task_binary" in config_text

    def test_missing_required_key_raises(self, tmp_path):
        config_path = tmp_path / "bad.yaml"
        config_path.write_text("corpus_id: x\ndatasets: []\n", encoding="utf-8")
        with pytest.raises(ValueError, match="missing required keys"):
            load_corpus_config(config_path)

    def test_dataset_missing_revision_sha_raises(self, tmp_path):
        config_path = tmp_path / "bad.yaml"
        config_path.write_text(
            yaml.safe_dump(
                {
                    "corpus_id": "x",
                    "min_confidence": 0.65,
                    "usability_rule": "rule",
                    "datasets": [
                        {
                            "name": "agenttrove",
                            "source_uri": "open-thoughts/AgentTrove",
                            "adapter": "agenttrove",
                            "split": "train",
                            "max_rows": 5,
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="missing required key"):
            load_corpus_config(config_path)


# ---------------------------------------------------------------------------
# Event derivation
# ---------------------------------------------------------------------------


class TestCmdFamily:
    @pytest.mark.parametrize(
        "content,expected",
        [
            ("git commit -m 'fix'", "git"),
            ("git diff HEAD~1", "git"),
            ("pip install pytest", "install"),
            ("apt-get install -y postgresql", "install"),
            ("python -m pytest tests/", "test"),
            ("pytest test_foo.py", "test"),
            ("python script.py", "python"),
            ("python3 -c 'print(1)'", "python"),
            ("sed -i 's/a/b/' file.py", "edit"),
            ("use str_replace_editor to change it", "edit"),
            ("cat config.py", "inspect"),
            ("ls -la", "inspect"),
            ("now I will implement the feature", "other"),
            ("", None),
            ("   ", None),
        ],
    )
    def test_mapping(self, content, expected):
        assert _classify_cmd_family(content) == expected


class TestEventDerivation:
    @pytest.fixture
    def parent(self) -> dict[str, Any]:
        result, reason = build_parent(
            _rich_record(),
            revision_sha="rev-test",
            license_status="test-license",
            min_confidence=0.65,
        )
        assert reason is None
        return result

    def test_events_sorted_and_typed(self, parent):
        events = parent["events"]
        assert [ev["i"] for ev in events] == [2, 3, 4, 5]
        assert [ev["kind"] for ev in events] == [
            "action",
            "observation",
            "action",
            "observation",
        ]
        assert [ev["role"] for ev in events] == [
            "assistant",
            "tool",
            "assistant",
            "tool",
        ]

    def test_event_keys_exact(self, parent):
        for ev in parent["events"]:
            assert set(ev.keys()) == EXPECTED_EVENT_KEYS

    def test_hash_is_sha1_prefix(self, parent):
        first_action = _rich_record()["affordance_path"]["actions"][0]
        expected = hashlib.sha1(first_action["content"].encode("utf-8")).hexdigest()[:10]
        assert parent["events"][0]["hash"] == expected
        assert parent["events"][0]["content_len"] == len(first_action["content"])

    def test_action_markers(self, parent):
        bash_git = parent["events"][0]
        assert bash_git["mentions_bash"] is True
        assert bash_git["cmd_family"] == "git"
        assert bash_git["is_error"] is False
        assert bash_git["has_terminal_output"] is False

        install = parent["events"][2]
        assert install["mentions_bash"] is False
        assert install["cmd_family"] == "install"

    def test_observation_markers(self, parent):
        error_obs = parent["events"][1]
        assert error_obs["is_error"] is True
        assert error_obs["cmd_family"] is None
        assert error_obs["mentions_bash"] is False
        assert error_obs["has_terminal_output"] is False

        terminal_obs = parent["events"][3]
        assert terminal_obs["has_terminal_output"] is True
        assert terminal_obs["is_error"] is False

    def test_context_counting(self, parent):
        assert parent["total_messages"] == 6
        # 6 total messages - 2 actions - 2 observations = 2 context events.
        assert parent["n_context_events"] == 2

    def test_counts_copy_payment_verbatim(self, parent):
        payment = _rich_record()["payment"]
        assert parent["counts"] == {
            "turns": payment["turns"],
            "tool_calls": payment["tool_calls"],
            "commands": payment["commands"],
            "elapsed_steps": payment["elapsed_steps"],
            "error_count": payment["error_count"],
        }

    def test_tool_names_manifest_skips_empty(self, parent):
        assert parent["tool_names_manifest"] == ["execute_bash", "finish"]


# ---------------------------------------------------------------------------
# Label provenance and usability rule
# ---------------------------------------------------------------------------


class TestLabelProvenanceAndUsability:
    def test_label_comes_only_from_outcome_success(self):
        record = _rich_record()
        record["outcome"]["success"] = False
        record["outcome"]["settlement_quality"] = "failure_with_signal"
        parent, reason = build_parent(
            record, revision_sha="r", license_status="l", min_confidence=0.65
        )
        assert reason is None
        assert parent["label"] == 0
        assert parent["label_source"].startswith("success=False")

    def test_missing_outcome_rejects_with_reason(self):
        record = _rich_record()
        del record["outcome"]
        parent, reason = build_parent(
            record, revision_sha="r", license_status="l", min_confidence=0.65
        )
        assert parent is None
        assert reason == REASON_OUTCOME_UNDEFINED

    def test_undefined_success_rejects_with_reason(self):
        record = _rich_record()
        record["outcome"]["success"] = None
        parent, reason = build_parent(
            record, revision_sha="r", license_status="l", min_confidence=0.65
        )
        assert parent is None
        assert reason == REASON_OUTCOME_UNDEFINED

    def test_confidence_below_threshold_rejects(self):
        record = _rich_record()
        record["outcome"]["confidence"] = 0.6
        parent, reason = build_parent(
            record, revision_sha="r", license_status="l", min_confidence=0.65
        )
        assert parent is None
        assert reason == REASON_CONFIDENCE_BELOW_THRESHOLD

    def test_confidence_at_threshold_accepts(self):
        record = _rich_record()
        record["outcome"]["confidence"] = 0.65
        parent, reason = build_parent(
            record, revision_sha="r", license_status="l", min_confidence=0.65
        )
        assert reason is None
        assert parent["label"] == 1

    def test_label_source_drops_long_spaced_evidence(self):
        record = _rich_record()
        record["outcome"]["evidence"] = [
            "target=True",
            "eval_logs=" + "x" * 200,
            "eval_logs=FAIL AssertionError",
        ]
        parent, _ = build_parent(
            record, revision_sha="r", license_status="l", min_confidence=0.65
        )
        assert "target=True" in parent["label_source"]
        assert "x" * 200 not in parent["label_source"]
        # Entries with whitespace are raw-log-like and never stored.
        assert "FAIL AssertionError" not in parent["label_source"]


# ---------------------------------------------------------------------------
# parent identity: parent_id, group_key, run discriminator, dedup
# ---------------------------------------------------------------------------


class TestParentIdentity:
    def test_parent_id_embeds_dataset_instance_and_source_run_id(self):
        record = _rich_record()
        record["dataset"] = "swegym_openhands"
        record["task_id"] = "getmoto__moto-5321"
        record["metadata"]["source_run_id"] = "gpt-4o-run_1"
        parent, _ = build_parent(
            record, revision_sha="r", license_status="l", min_confidence=0.65
        )
        content_hash = _trajectory_content_hash(parent["events"], parent["label"])
        assert parent["parent_id"] == (
            f"swegym_openhands:getmoto__moto-5321:"
            f"gpt-4o-run_1-{content_hash[:10]}"
        )
        assert parent["group_key"] == "swegym_openhands:getmoto__moto-5321"

    def test_parent_id_is_stable_for_identical_records(self):
        parent_a, _ = build_parent(
            _rich_record(), revision_sha="r", license_status="l", min_confidence=0.65
        )
        parent_b, _ = build_parent(
            _rich_record(), revision_sha="r", license_status="l", min_confidence=0.65
        )
        assert parent_a["parent_id"] == parent_b["parent_id"]

    def test_fallback_parent_id_derives_from_trajectory_content_hash(self):
        record = _rich_record()
        record["task_id"] = ""
        parent, _ = build_parent(
            record, revision_sha="r", license_status="l", min_confidence=0.65
        )
        content_hash = _trajectory_content_hash(parent["events"], parent["label"])
        assert parent["parent_id"] == f"test_ds:{content_hash[:16]}:{content_hash[:10]}"
        assert parent["group_key"] == f"test_ds:{content_hash[:16]}"

    def test_different_runs_same_instance_get_different_parent_ids(self):
        run_a = _rich_record()
        run_b = _rich_record()
        # Distinct parent runs over the same instance: different trajectories,
        # no source-provided run id -> the content-hash discriminator must
        # keep the two parent_ids apart.
        run_b["affordance_path"]["actions"][0]["content"] = "cat setup.py"
        parent_a, _ = build_parent(
            run_a, revision_sha="r", license_status="l", min_confidence=0.65
        )
        parent_b, _ = build_parent(
            run_b, revision_sha="r", license_status="l", min_confidence=0.65
        )
        assert parent_a["parent_id"] != parent_b["parent_id"]
        assert parent_a["group_key"] == parent_b["group_key"]

    def test_repeated_source_run_id_across_distinct_runs_stays_distinct(self):
        # Live swegym data repeats source run ids (batch names) across
        # distinct runs of one instance; the content-hash component of the
        # discriminator must keep their parent_ids apart.
        run_a = _rich_record()
        run_b = _rich_record()
        for run in (run_a, run_b):
            run["metadata"]["source_run_id"] = "batch-t0-run_1"
        run_b["affordance_path"]["actions"][0]["content"] = "cat setup.py"
        parent_a, _ = build_parent(
            run_a, revision_sha="r", license_status="l", min_confidence=0.65
        )
        parent_b, _ = build_parent(
            run_b, revision_sha="r", license_status="l", min_confidence=0.65
        )
        assert parent_a["parent_id"] != parent_b["parent_id"]
        assert parent_a["parent_id"].startswith(
            "test_ds:task-1:batch-t0-run_1-"
        )
        assert parent_b["parent_id"].startswith(
            "test_ds:task-1:batch-t0-run_1-"
        )

    def test_dedup_drops_only_true_duplicates(self, tmp_path):
        # Two identical raw rows -> one parent, one duplicate counted.
        fixture = (FIXTURES_DIR / "swegym_openhands" / "sample.jsonl").read_text(
            encoding="utf-8"
        )
        first_line = fixture.splitlines()[0]
        dup_fixture = tmp_path / "dup_sample.jsonl"
        dup_fixture.write_text(first_line + "\n" + first_line + "\n", encoding="utf-8")

        config_path = _write_test_config(
            tmp_path,
            [_fixture_dataset("swegym_openhands", input_path=str(dup_fixture))],
        )
        summary = build_corpus(
            config_path=config_path,
            output_root=tmp_path / "corpora",
            summary_path=tmp_path / "corpus_summary.json",
        )

        ds = summary["datasets"]["swegym_openhands"]
        assert ds["scanned"] == 2
        assert ds["duplicates_dropped"] == 1
        assert ds["usable"] == 1

        parents = _read_jsonl(tmp_path / "corpora" / "swegym_openhands.jsonl")
        assert len(parents) == 1
        content_hash = _trajectory_content_hash(
            parents[0]["events"], parents[0]["label"]
        )
        assert parents[0]["parent_id"] == (
            f"swegym_openhands:getmoto__moto-5321:"
            f"gpt-4o-run_1-{content_hash[:10]}"
        )

    def test_different_runs_same_instance_both_survive(self, tmp_path):
        # Two distinct runs over one instance (distinct run_id and content)
        # must both survive: same-instance repeats are not duplicates.
        fixture = (FIXTURES_DIR / "swegym_openhands" / "sample.jsonl").read_text(
            encoding="utf-8"
        )
        first_row = json.loads(fixture.splitlines()[0])
        second_run = json.loads(json.dumps(first_row))
        second_run["run_id"] = "gpt-4o-run_2"
        second_run["messages"] = [
            m for m in first_row["messages"] if m["role"] != "system"
        ][:-1] + [
            {"role": "tool", "content": "pytest failed with AssertionError"},
            {"role": "assistant", "content": "different follow-up action"},
        ]
        second_run["resolved"] = False

        variant_fixture = tmp_path / "two_runs_sample.jsonl"
        variant_fixture.write_text(
            json.dumps(first_row) + "\n" + json.dumps(second_run) + "\n",
            encoding="utf-8",
        )

        config_path = _write_test_config(
            tmp_path,
            [_fixture_dataset("swegym_openhands", input_path=str(variant_fixture))],
        )
        summary = build_corpus(
            config_path=config_path,
            output_root=tmp_path / "corpora",
            summary_path=tmp_path / "corpus_summary.json",
        )

        ds = summary["datasets"]["swegym_openhands"]
        assert ds["scanned"] == 2
        assert ds["duplicates_dropped"] == 0
        assert ds["usable"] == 2

        parents = _read_jsonl(tmp_path / "corpora" / "swegym_openhands.jsonl")
        parent_ids = {p["parent_id"] for p in parents}
        group_keys = {p["group_key"] for p in parents}
        expected_ids = {
            f"swegym_openhands:getmoto__moto-5321:gpt-4o-run_{run}"
            f"-{_trajectory_content_hash(p['events'], p['label'])[:10]}"
            for p, run in zip(parents, ("1", "2"))
        }
        assert parent_ids == expected_ids
        assert len(parent_ids) == 2
        # Same instance -> one group_key across both runs.
        assert group_keys == {"swegym_openhands:getmoto__moto-5321"}


# ---------------------------------------------------------------------------
# End-to-end fixture build (no network)
# ---------------------------------------------------------------------------


class TestBuildCorpusFromFixtures:
    @pytest.fixture
    def build_result(self, tmp_path):
        config_path = _write_test_config(
            tmp_path,
            [
                _fixture_dataset("swegym_openhands", split="train.raw"),
                _fixture_dataset("agenttrove"),
                _fixture_dataset("nebius_swe_agent"),
            ],
        )
        return build_corpus(
            config_path=config_path,
            output_root=tmp_path / "corpora",
            summary_path=tmp_path / "corpus_summary.json",
        ), tmp_path

    def test_per_dataset_counts(self, build_result):
        summary, _ = build_result
        assert summary["datasets"]["swegym_openhands"]["usable"] == 2
        assert summary["datasets"]["agenttrove"]["usable"] == 5
        assert summary["datasets"]["nebius_swe_agent"]["usable"] == 2
        assert summary["total_usable_parents"] == 9
        # Fixture rows all normalize: scanned == usable, nothing rejected.
        for ds in summary["datasets"].values():
            assert ds["scanned"] == ds["usable"]
            assert ds["rejected"] == 0
            assert ds["adapter_errors"] == 0

    def test_label_balance(self, build_result):
        summary, _ = build_result
        assert summary["datasets"]["swegym_openhands"]["label_counts"] == {
            "success": 1,
            "failure": 1,
        }
        assert summary["datasets"]["agenttrove"]["label_counts"] == {
            "success": 3,
            "failure": 2,
        }
        assert summary["datasets"]["nebius_swe_agent"]["label_counts"] == {
            "success": 1,
            "failure": 1,
        }

    def test_corpus_files_one_parent_per_line(self, build_result):
        _, tmp_path = build_result
        corpus_dir = tmp_path / "corpora"
        for name, count in (
            ("swegym_openhands", 2),
            ("agenttrove", 5),
            ("nebius_swe_agent", 2),
        ):
            parents = _read_jsonl(corpus_dir / f"{name}.jsonl")
            assert len(parents) == count

    def test_agenttrove_events_are_actions_only(self, build_result):
        _, tmp_path = build_result
        parents = _read_jsonl(tmp_path / "corpora" / "agenttrove.jsonl")
        # The agenttrove settlement record carries affordance_path.actions
        # only, so every event is an action and terminal markers are False.
        for parent in parents:
            assert parent["events"]
            for ev in parent["events"]:
                assert ev["kind"] == "action"
                assert ev["has_terminal_output"] is False
                assert ev["is_error"] is False

    def test_swegym_parent_reproduces_v005_payment(self, build_result):
        _, tmp_path = build_result
        parents = _read_jsonl(tmp_path / "corpora" / "swegym_openhands.jsonl")
        first = parents[0]
        content_hash = _trajectory_content_hash(first["events"], first["label"])
        assert first["parent_id"] == (
            f"swegym_openhands:getmoto__moto-5321:"
            f"gpt-4o-run_1-{content_hash[:10]}"
        )
        assert first["group_key"] == "swegym_openhands:getmoto__moto-5321"
        assert first["label"] == 1
        assert "resolved=True" in first["label_source"]
        assert first["counts"] == {
            "turns": 2,
            "tool_calls": 2,
            "commands": 0,
            "elapsed_steps": 6,
            "error_count": 0,
        }
        assert first["total_messages"] == 6
        # system + user context messages are counted, not stored as events.
        assert first["n_context_events"] == 2
        assert "execute_bash" in first["tool_names_manifest"]

    def test_manifest_content(self, build_result):
        summary, tmp_path = build_result
        manifest_path = Path(summary["corpus_manifest_path"])
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        assert manifest["corpus_id"] == "v006-test"
        assert manifest["created_at"]
        assert "outcome.success is not None" in manifest["usability_rule"]
        assert manifest["min_confidence"] == 0.65
        assert "group_key" in manifest["identity_model"]
        assert "never straddle partitions" in manifest["identity_model"]["group_key"]

        for name, ds in manifest["datasets"].items():
            assert ds["revision_sha"] == f"rev-{name}"
            assert ds["license_status"] == f"test-license-{name}"
            for key in (
                "scanned",
                "normalized",
                "usable",
                "rejected",
                "duplicates_dropped",
                "label_counts",
                "top_rejection_reasons",
            ):
                assert key in ds
            # scanned == usable + rejected + duplicates
            assert ds["scanned"] == ds["usable"] + ds["rejected"] + ds["duplicates_dropped"]
            corpus_file = Path(ds["corpus_file"])
            assert corpus_file.exists()
            digest = hashlib.sha256(corpus_file.read_bytes()).hexdigest()
            assert ds["sha256"] == digest

    def test_summary_file_content(self, build_result):
        summary, tmp_path = build_result
        summary_file = tmp_path / "corpus_summary.json"
        written = json.loads(summary_file.read_text(encoding="utf-8"))

        assert written["corpus_manifest_path"]
        assert written["total_usable_parents"] == 9
        assert written["created_at"] == summary["created_at"]
        for name, ds in written["datasets"].items():
            assert ds["revision_sha"] == f"rev-{name}"
            assert ds["license_status"] == f"test-license-{name}"
            assert ds["sha256"]
            assert ds["corpus_file"]
            for key in ("scanned", "normalized", "usable", "rejected", "duplicates_dropped"):
                assert key in ds

    def test_no_raw_text_in_any_event(self, build_result):
        _, tmp_path = build_result
        corpus_dir = tmp_path / "corpora"
        for corpus_file in corpus_dir.glob("*.jsonl"):
            for parent in _read_jsonl(corpus_file):
                # Every parent carries both identity fields.
                assert parent["group_key"].startswith(f"{parent['dataset']}:")
                assert parent["parent_id"].startswith(f"{parent['group_key']}:")
                for ev in parent["events"]:
                    assert set(ev.keys()) == EXPECTED_EVENT_KEYS
                    for value in ev.values():
                        if isinstance(value, str):
                            assert len(value) <= 12, (
                                f"raw-text leak risk in event string: {value!r}"
                            )

    def test_rejection_reasons_recorded_not_silent(self, tmp_path):
        # A low-confidence raw row must surface as a counted rejection reason.
        config_path = _write_test_config(
            tmp_path,
            [
                _fixture_dataset(
                    "swegym_openhands",
                    min_confidence=0.99,
                )
            ],
        )
        # Patch config min_confidence to 0.99 so fixture rows (0.8/0.9) reject.
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        config["min_confidence"] = 0.99
        config_path.write_text(yaml.safe_dump(config), encoding="utf-8")

        summary = build_corpus(
            config_path=config_path,
            output_root=tmp_path / "corpora",
            summary_path=tmp_path / "corpus_summary.json",
        )
        ds = summary["datasets"]["swegym_openhands"]
        assert ds["usable"] == 0
        assert ds["rejected"] == 2
        reasons = {r["reason"]: r["count"] for r in ds["top_rejection_reasons"]}
        assert reasons.get(REASON_CONFIDENCE_BELOW_THRESHOLD) == 2


# ---------------------------------------------------------------------------
# v008 normalizations (N1/N2/N3)
# ---------------------------------------------------------------------------


class TestKindBasedMarkerGating:
    """N2: cmd_family/mentions_bash are gated on kind == "action" alone.

    The builder only emits kind="action" for adapter actions, which are
    the agent's own acts by construction; gating on the role string
    degenerated every nebius action (its harness carries role "ai").
    """

    def _ai_action_record(self) -> dict[str, Any]:
        record = _rich_record()
        record["dataset"] = "nebius_style_ds"
        record["affordance_path"] = {
            "actions": [
                {
                    "turn_index": 1,
                    "role": "ai",
                    "action_type": "message",
                    "content": "run bash: python -m pytest tests/",
                }
            ],
            "observations": [
                {"turn_index": 2, "role": "user", "content": "all ok"}
            ],
            "recovery_events": [],
        }
        return record

    def test_ai_roled_action_gets_markers(self):
        parent, reason = build_parent(
            self._ai_action_record(),
            revision_sha="rev-test",
            license_status="test-license",
            min_confidence=0.65,
        )
        assert reason is None
        action = parent["events"][0]
        assert action["kind"] == "action"
        assert action["role"] == "ai"
        assert action["mentions_bash"] is True
        assert action["cmd_family"] == "test"

    def test_observation_markers_unchanged(self):
        parent, _ = build_parent(
            self._ai_action_record(),
            revision_sha="rev-test",
            license_status="test-license",
            min_confidence=0.65,
        )
        observation = parent["events"][1]
        assert observation["kind"] == "observation"
        assert observation["cmd_family"] is None
        assert observation["mentions_bash"] is False


class TestSWEGymToolCallRendering:
    """N1: swegym assistant tool_calls are rendered into the action
    content so the corpus builder's cmd_family/mentions_bash derivation
    and action hashes are meaningful; messages without tool_calls are
    unchanged."""

    def _raw_with_tool_calls(self) -> dict[str, Any]:
        return {
            "instance_id": "pkg__repo-1",
            "run_id": "run_1",
            "resolved": True,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Fix the failing test."},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {
                                "name": "execute_bash",
                                "arguments": '{"command": "pytest -q tests/test_x.py"}',
                            },
                        }
                    ],
                },
                {"role": "tool", "content": "OBSERVATION:\n1 passed"},
                {"role": "assistant", "content": "plain prose reply"},
                {"role": "tool", "content": "OBSERVATION:\ndone"},
            ],
            "tools": [{"function": {"name": "execute_bash"}, "type": "function"}],
            "test_result": {"report": {"resolved": True}},
        }

    def test_tool_calls_rendered_into_action_content(self):
        from scripts.settlement_datasets.registry import get_adapter

        adapter = get_adapter("swegym_openhands")
        actions = adapter.extract_actions(self._raw_with_tool_calls())
        assert actions[0]["content"] == (
            'execute_bash {"command": "pytest -q tests/test_x.py"}'
        )

    def test_assistant_without_tool_calls_unchanged(self):
        from scripts.settlement_datasets.registry import get_adapter

        adapter = get_adapter("swegym_openhands")
        actions = adapter.extract_actions(self._raw_with_tool_calls())
        assert actions[1]["content"] == "plain prose reply"

    def test_rendering_is_null_safe(self):
        from scripts.settlement_datasets.registry import get_adapter

        adapter = get_adapter("swegym_openhands")
        raw = {
            "messages": [
                # Live-schema shape: null content, absent tool_calls.
                {"role": "assistant", "content": None},
                # Malformed tool_calls entries are skipped.
                {
                    "role": "assistant",
                    "content": "prose",
                    "tool_calls": ["nope", {"function": "nope"}, {}],
                },
            ]
        }
        actions = adapter.extract_actions(raw)
        assert [action["content"] for action in actions] == ["", "prose"]

    def test_rendered_content_drives_corpus_markers(self):
        from scripts.settlement_datasets.registry import get_adapter

        adapter = get_adapter("swegym_openhands")
        raw = self._raw_with_tool_calls()
        record = adapter.to_settlement_record(raw)
        parent, reason = build_parent(
            record,
            revision_sha="rev",
            license_status="l",
            min_confidence=0.65,
            context_positions=adapter.context_positions(raw),
        )
        assert reason is None
        by_i = {event["i"]: event for event in parent["events"]}
        # execute_bash(...) -> "bash" in the rendered tool name and
        # pytest in the arguments -> test family.
        assert by_i[2]["cmd_family"] == "test"
        assert by_i[2]["mentions_bash"] is True
        # Prose-only action keeps prose semantics.
        assert by_i[4]["mentions_bash"] is False
        assert by_i[4]["cmd_family"] == "other"
        # The empty-content hash degeneration is gone: the two actions
        # no longer share one hash.
        assert by_i[2]["hash"] != by_i[4]["hash"]


class TestNebiusLeadingIssueContext:
    """N3: nebius user entries before the first ai/assistant action are
    the task issue statement -- context, not observations."""

    def _raw(self) -> dict[str, Any]:
        return {
            "instance_id": "repo__issue-1",
            "model_name": "synthetic-model",
            "target": False,
            "trajectory": [
                {"role": "system", "content": "agent"},
                {
                    "role": "user",
                    "content": (
                        "We're currently solving the following issue.\n"
                        "TypeError: cannot concatenate str and int"
                    ),
                },
                {"role": "ai", "content": "run bash: git status"},
                {"role": "user", "content": "OBSERVATION: clean checkout"},
                {"role": "ai", "content": "pytest -q"},
                {"role": "user", "content": "OBSERVATION: 1 failed"},
                {"role": "ai", "content": "sed -i s/a/b/ src/x.py"},
                {"role": "user", "content": "OBSERVATION: all ok"},
            ],
            "exit_status": "submitted",
            "generated_patch": "diff --git a/x.py b/x.py",
            "eval_logs": "FAIL",
        }

    def test_issue_entry_is_context_not_observation(self):
        from scripts.settlement_datasets.registry import get_adapter

        adapter = get_adapter("nebius_swe_agent")
        raw = self._raw()
        assert [action["turn_index"] for action in adapter.extract_actions(raw)] == [
            2,
            4,
            6,
        ]
        assert [
            observation["turn_index"]
            for observation in adapter.extract_observations(raw)
        ] == [3, 5, 7]
        # Context = system role + pre-first-action user entries.
        assert adapter.context_positions(raw) == [0, 1]

    def test_issue_entry_not_among_events_and_counted_in_ctx(self):
        from scripts.settlement_datasets.registry import get_adapter

        adapter = get_adapter("nebius_swe_agent")
        raw = self._raw()
        record = adapter.to_settlement_record(raw)
        parent, reason = build_parent(
            record,
            revision_sha="rev",
            license_status="l",
            min_confidence=0.65,
            context_positions=adapter.context_positions(raw),
        )
        assert reason is None
        event_indices = [event["i"] for event in parent["events"]]
        assert 1 not in event_indices
        assert event_indices == [2, 3, 4, 5, 6, 7]
        # n_context_events = 8 total - 3 actions - 3 observations = 2,
        # and the first action has already witnessed both.
        assert parent["n_context_events"] == 2
        assert parent["trailing_context"] == 0
        assert parent["events"][0]["ctx"] == 2
        # The ai-roled actions carry real markers (N2 integration).
        assert parent["events"][0]["cmd_family"] == "git"
        assert parent["events"][2]["cmd_family"] == "test"

    def test_trajectory_without_actions_keeps_legacy_observations(self):
        from scripts.settlement_datasets.registry import get_adapter

        adapter = get_adapter("nebius_swe_agent")
        raw = {
            "trajectory": [
                {"role": "system", "content": "agent"},
                {"role": "user", "content": "issue statement"},
            ]
        }
        assert [
            observation["turn_index"]
            for observation in adapter.extract_observations(raw)
        ] == [1]
        assert adapter.context_positions(raw) == [0]
