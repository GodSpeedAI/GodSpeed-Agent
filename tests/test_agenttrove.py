from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

import pytest
import yaml

FIXTURES = Path(__file__).parent / "fixtures" / "agenttrove"


def _load_fixture(name: str) -> list[dict[str, Any]]:
    path = FIXTURES / name
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                records.append(json.loads(line))
    return records


class TestMessageNormalization:
    def test_normalize_turn_with_role_and_content(self):
        from scripts.agenttrove.ingest_agenttrove import normalize_turn

        result = normalize_turn({"role": "user", "content": "hello"})
        assert result["role"] == "user"
        assert result["content"] == "hello"

    def test_normalize_turn_with_from_field(self):
        from scripts.agenttrove.ingest_agenttrove import normalize_turn

        result = normalize_turn({"from": "assistant", "value": "response"})
        assert result["role"] == "assistant"
        assert result["content"] == "response"

    def test_normalize_turn_with_tool_name(self):
        from scripts.agenttrove.ingest_agenttrove import normalize_turn

        result = normalize_turn({"role": "tool", "content": "output", "name": "bash"})
        assert result["role"] == "tool"
        assert result["tool_name"] == "bash"

    def test_normalize_turn_preserves_metadata(self):
        from scripts.agenttrove.ingest_agenttrove import normalize_turn

        result = normalize_turn(
            {"role": "assistant", "content": "text", "custom_field": 42}
        )
        assert result["metadata"]["custom_field"] == 42

    def test_normalize_non_dict_turn(self):
        from scripts.agenttrove.ingest_agenttrove import normalize_turn

        result = normalize_turn("just a string")
        assert result["role"] == "unknown"
        assert result["content"] == "just a string"


class TestMetadataPreservation:
    def test_extract_metadata_preserves_known_fields(self):
        from scripts.agenttrove.ingest_agenttrove import extract_metadata

        row = {
            "original_source": "swesmith",
            "original_teacher": "gpt-4",
            "reward": 1.0,
            "messages": [],
        }
        meta = extract_metadata(row)
        assert meta["original_source"] == "swesmith"
        assert meta["original_teacher"] == "gpt-4"
        assert meta["reward"] == 1.0

    def test_extract_metadata_excludes_messages(self):
        from scripts.agenttrove.ingest_agenttrove import extract_metadata

        row = {
            "messages": [{"role": "user", "content": "hi"}],
            "original_source": "test",
        }
        meta = extract_metadata(row)
        assert "messages" not in meta

    def test_make_trace_id_deterministic(self):
        from scripts.agenttrove.ingest_agenttrove import make_trace_id

        row = {"task_id": "abc-123", "messages": []}
        id1 = make_trace_id(row, 0)
        id2 = make_trace_id(row, 0)
        assert id1 == id2
        assert id1.startswith("at-")


class TestCommandDetection:
    def test_detects_bash_command(self):
        from scripts.agenttrove.profile_traces import is_command_like

        assert is_command_like("```bash\npip install requests\n```")

    def test_detects_inline_command(self):
        from scripts.agenttrove.profile_traces import is_command_like

        assert is_command_like("run `pytest test_foo.py` to check")

    def test_detects_git_command(self):
        from scripts.agenttrove.profile_traces import is_command_like

        assert is_command_like("git commit -m 'fix'")

    def test_rejects_plain_text(self):
        from scripts.agenttrove.profile_traces import is_command_like

        assert not is_command_like("The function should return the sum of two numbers.")

    def test_rejects_empty(self):
        from scripts.agenttrove.profile_traces import is_command_like

        assert not is_command_like("")

    def test_detects_sudo(self):
        from scripts.agenttrove.profile_traces import is_command_like

        assert is_command_like("sudo apt update")

    def test_detects_docker(self):
        from scripts.agenttrove.profile_traces import is_command_like

        assert is_command_like("docker build -t myapp .")


class TestErrorDetection:
    def test_detects_error_keyword(self):
        from scripts.agenttrove.profile_traces import is_error_like

        assert is_error_like("Error: module not found")

    def test_detects_traceback(self):
        from scripts.agenttrove.profile_traces import is_error_like

        assert is_error_like("Traceback (most recent call last):\n  File ...")

    def test_detects_exception(self):
        from scripts.agenttrove.profile_traces import is_error_like

        assert is_error_like("Exception: connection refused")

    def test_rejects_success_message(self):
        from scripts.agenttrove.profile_traces import is_error_like

        assert not is_error_like("Successfully installed requests")

    def test_rejects_empty(self):
        from scripts.agenttrove.profile_traces import is_error_like

        assert not is_error_like("")

    def test_detects_permission_denied(self):
        from scripts.agenttrove.profile_traces import is_error_like

        assert is_error_like("Permission denied: cannot write to /etc/config")

    def test_detects_timeout(self):
        from scripts.agenttrove.profile_traces import is_error_like

        assert is_error_like("operation timeout waiting for response")


class TestProfileGeneration:
    def test_profile_clean_trace(self):
        from scripts.agenttrove.profile_traces import profile_trace

        traces = _load_fixture("test_traces.jsonl")
        clean = traces[0]
        profile = profile_trace(clean)
        assert profile["trace_id"] == "at-test-clean-001"
        assert profile["turn_count"] == 4
        assert profile["user_turn_count"] == 1
        assert profile["assistant_turn_count"] == 2
        assert profile["error_like_output_count"] == 0
        assert profile["has_final_answer"] is True

    def test_profile_thrashing_trace(self):
        from scripts.agenttrove.profile_traces import profile_trace

        traces = _load_fixture("test_traces.jsonl")
        thrash = traces[2]
        profile = profile_trace(thrash)
        assert profile["trace_id"] == "at-test-thrash-003"
        assert profile["error_like_output_count"] >= 3
        assert profile["command_like_action_count"] >= 5

    def test_profile_final_answer_detection(self):
        from scripts.agenttrove.profile_traces import profile_trace

        traces = _load_fixture("test_traces.jsonl")
        clean = traces[0]
        profile = profile_trace(clean)
        assert profile["has_final_answer"] is True

    def test_write_profiles(self):
        from scripts.agenttrove.profile_traces import profile_traces

        with tempfile.TemporaryDirectory() as tmpdir:
            fixture_path = FIXTURES / "test_traces.jsonl"
            output_dir = Path(tmpdir)
            paths = profile_traces(str(fixture_path), str(output_dir))
            assert paths["profiles"].exists()
            assert paths["summary"].exists()

            profiles = []
            with paths["profiles"].open("r") as f:
                for line in f:
                    if line.strip():
                        profiles.append(json.loads(line))
            assert len(profiles) == 7

            with paths["summary"].open("r") as f:
                content = f.read()
            assert "test_source" in content


class TestYAMLRuleLoading:
    def test_load_rules(self):
        from scripts.agenttrove.label_settlements import load_rules

        rules = load_rules("configs/agenttrove/settlement_label_rules.yaml")
        assert "desired_direction_keywords" in rules
        assert "failure_mode_rules" in rules
        assert "settlement_quality_rules" in rules

    def test_rules_have_implementation_keywords(self):
        from scripts.agenttrove.label_settlements import load_rules

        rules = load_rules("configs/agenttrove/settlement_label_rules.yaml")
        impl_kw = rules["desired_direction_keywords"]["implementation"]
        assert "implement" in impl_kw
        assert "build" in impl_kw

    def test_rules_have_all_failure_modes(self):
        from scripts.agenttrove.label_settlements import load_rules

        rules = load_rules("configs/agenttrove/settlement_label_rules.yaml")
        expected_modes = [
            "premature_closure",
            "tool_thrashing",
            "failed_recovery",
            "representation_jump",
            "payment_spiral",
            "context_loss",
            "over_abstraction",
            "premature_concretion",
            "missing_affordance",
            "brittle_success",
        ]
        for mode in expected_modes:
            assert mode in rules["failure_mode_rules"], f"Missing failure mode: {mode}"


class TestSettlementLabeling:
    @pytest.fixture()
    def rules(self):
        from scripts.agenttrove.label_settlements import load_rules

        return load_rules("configs/agenttrove/settlement_label_rules.yaml")

    @pytest.fixture()
    def traces(self):
        return _load_fixture("test_traces.jsonl")

    def test_label_clean_success(self, rules, traces):
        from scripts.agenttrove.label_settlements import label_trace
        from scripts.agenttrove.profile_traces import profile_trace

        profile = profile_trace(traces[0])
        settlement = label_trace(traces[0], profile, rules)
        assert settlement["outcome"]["settlement_quality"] == "clean_success"
        assert settlement["desired_direction"]["type"] == "implementation"

    def test_label_recovered_success(self, rules, traces):
        from scripts.agenttrove.label_settlements import label_trace
        from scripts.agenttrove.profile_traces import profile_trace

        profile = profile_trace(traces[1])
        settlement = label_trace(traces[1], profile, rules)
        assert settlement["outcome"]["settlement_quality"] == "recovered_success"
        assert len(settlement["affordance_path"]["recovery_events"]) >= 1

    def test_label_tool_thrashing(self, rules, traces):
        from scripts.agenttrove.label_settlements import label_trace
        from scripts.agenttrove.profile_traces import profile_trace

        profile = profile_trace(traces[2])
        settlement = label_trace(traces[2], profile, rules)
        fm = settlement["cognitive_os_labels"]["failure_mode"]
        modes = fm if isinstance(fm, list) else [fm]
        assert "tool_thrashing" in modes

    def test_label_premature_closure(self, rules, traces):
        from scripts.agenttrove.label_settlements import label_trace
        from scripts.agenttrove.profile_traces import profile_trace

        profile = profile_trace(traces[3])
        settlement = label_trace(traces[3], profile, rules)
        fm = settlement["cognitive_os_labels"]["failure_mode"]
        modes = fm if isinstance(fm, list) else [fm]
        assert "premature_closure" in modes

    def test_label_representation_jump(self, rules, traces):
        from scripts.agenttrove.label_settlements import label_trace
        from scripts.agenttrove.profile_traces import profile_trace

        profile = profile_trace(traces[4])
        settlement = label_trace(traces[4], profile, rules)
        fm = settlement["cognitive_os_labels"]["failure_mode"]
        modes = fm if isinstance(fm, list) else [fm]
        assert "representation_jump" in modes

    def test_label_over_abstraction(self, rules, traces):
        from scripts.agenttrove.label_settlements import label_trace
        from scripts.agenttrove.profile_traces import profile_trace

        profile = profile_trace(traces[5])
        settlement = label_trace(traces[5], profile, rules)
        fm = settlement["cognitive_os_labels"]["failure_mode"]
        modes = fm if isinstance(fm, list) else [fm]
        assert "over_abstraction" in modes

    def test_label_brittle_success(self, rules, traces):
        from scripts.agenttrove.label_settlements import label_trace
        from scripts.agenttrove.profile_traces import profile_trace

        profile = profile_trace(traces[6])
        settlement = label_trace(traces[6], profile, rules)
        assert settlement["outcome"]["settlement_quality"] in (
            "recovered_success",
            "brittle_success",
        )
        fm = settlement["cognitive_os_labels"]["failure_mode"]
        modes = fm if isinstance(fm, list) else [fm]
        assert "brittle_success" in modes

    def test_label_traces_produces_jsonl(self, rules, traces):
        from scripts.agenttrove.label_settlements import label_traces

        with tempfile.TemporaryDirectory() as tmpdir:
            fixture_path = FIXTURES / "test_traces.jsonl"
            output = Path(tmpdir) / "settlements.jsonl"
            result = label_traces(str(fixture_path), output_path=str(output))
            assert result.exists()
            with result.open("r") as f:
                records = [json.loads(line) for line in f if line.strip()]
            assert len(records) == 7
            for r in records:
                assert "trace_id" in r
                assert "outcome" in r
                assert "desired_direction" in r
                assert "payment" in r


class TestSQLiteExport:
    def test_export_creates_database(self):
        from scripts.agenttrove.export_sqlite import export_to_sqlite

        with tempfile.TemporaryDirectory() as tmpdir:
            fixture_path = FIXTURES / "test_traces.jsonl"
            settlement_path = Path(tmpdir) / "settlements.jsonl"

            from scripts.agenttrove.label_settlements import label_traces

            label_traces(str(fixture_path), output_path=str(settlement_path))

            db_path = Path(tmpdir) / "test.sqlite"
            result = export_to_sqlite(
                str(settlement_path), str(fixture_path), str(db_path)
            )
            assert result.exists()

            conn = sqlite3.connect(str(result))
            tables = [
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            ]
            assert "traces" in tables
            assert "turns" in tables
            assert "settlements" in tables
            assert "failure_modes" in tables
            assert "policy_signals" in tables
            assert "labels" in tables

            trace_count = conn.execute("SELECT COUNT(*) FROM traces").fetchone()[0]
            assert trace_count == 7

            turns_count = conn.execute("SELECT COUNT(*) FROM turns").fetchone()[0]
            assert turns_count > 0

            conn.close()

    def test_database_has_indexes(self):
        from scripts.agenttrove.export_sqlite import export_to_sqlite

        with tempfile.TemporaryDirectory() as tmpdir:
            fixture_path = FIXTURES / "test_traces.jsonl"
            settlement_path = Path(tmpdir) / "settlements.jsonl"

            from scripts.agenttrove.label_settlements import label_traces

            label_traces(str(fixture_path), output_path=str(settlement_path))

            db_path = Path(tmpdir) / "test.sqlite"
            export_to_sqlite(str(settlement_path), str(fixture_path), str(db_path))

            conn = sqlite3.connect(str(db_path))
            indexes = [
                row[1]
                for row in conn.execute(
                    "SELECT * FROM sqlite_master WHERE type='index'"
                ).fetchall()
            ]
            assert any("source" in idx for idx in indexes)
            assert any("reward" in idx for idx in indexes)
            assert any("quality" in idx for idx in indexes)
            conn.close()

    def test_query_summarize_by_source(self):
        from scripts.agenttrove.export_sqlite import export_to_sqlite
        from scripts.agenttrove.query_ledger import query_ledger

        with tempfile.TemporaryDirectory() as tmpdir:
            fixture_path = FIXTURES / "test_traces.jsonl"
            settlement_path = Path(tmpdir) / "settlements.jsonl"

            from scripts.agenttrove.label_settlements import label_traces

            label_traces(str(fixture_path), output_path=str(settlement_path))

            db_path = Path(tmpdir) / "test.sqlite"
            export_to_sqlite(str(settlement_path), str(fixture_path), str(db_path))

            results = query_ledger(str(db_path), "summarize_by_source")
            assert len(results) >= 1
            assert results[0]["source"] == "test_source"

    def test_query_failure_modes(self):
        from scripts.agenttrove.export_sqlite import export_to_sqlite
        from scripts.agenttrove.query_ledger import query_ledger

        with tempfile.TemporaryDirectory() as tmpdir:
            fixture_path = FIXTURES / "test_traces.jsonl"
            settlement_path = Path(tmpdir) / "settlements.jsonl"

            from scripts.agenttrove.label_settlements import label_traces

            label_traces(str(fixture_path), output_path=str(settlement_path))

            db_path = Path(tmpdir) / "test.sqlite"
            export_to_sqlite(str(settlement_path), str(fixture_path), str(db_path))

            results = query_ledger(str(db_path), "summarize_by_failure_mode")
            failure_modes = [r["failure_mode"] for r in results]
            assert len(failure_modes) >= 1


class TestPolicyMining:
    def test_mine_generates_policies(self):
        from scripts.agenttrove.mine_harness_policies import (
            mine_policies,
            load_settlements,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            fixture_path = FIXTURES / "test_traces.jsonl"
            settlement_path = Path(tmpdir) / "settlements.jsonl"

            from scripts.agenttrove.label_settlements import label_traces

            label_traces(str(fixture_path), output_path=str(settlement_path))

            settlements = load_settlements(str(settlement_path))
            policies = mine_policies(settlements)
            assert len(policies) >= 10

            policy_ids = [p["id"] for p in policies]
            assert "require_reflection_after_repeated_tool_errors" in policy_ids
            assert "block_premature_final_answer" in policy_ids
            assert "payment_spiral_reset" in policy_ids

    def test_policies_have_evidence(self):
        from scripts.agenttrove.mine_harness_policies import (
            mine_policies,
            load_settlements,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            fixture_path = FIXTURES / "test_traces.jsonl"
            settlement_path = Path(tmpdir) / "settlements.jsonl"

            from scripts.agenttrove.label_settlements import label_traces

            label_traces(str(fixture_path), output_path=str(settlement_path))

            settlements = load_settlements(str(settlement_path))
            policies = mine_policies(settlements)

            for policy in policies:
                assert "evidence" in policy
                assert "supporting_trace_count" in policy["evidence"]
                assert "total_traces_analyzed" in policy["evidence"]
                assert "example_trace_ids" in policy["evidence"]
                assert policy["active_by_default"] is False

    def test_write_policies_yaml(self):
        from scripts.agenttrove.mine_harness_policies import (
            mine_policies,
            load_settlements,
            write_policies,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            fixture_path = FIXTURES / "test_traces.jsonl"
            settlement_path = Path(tmpdir) / "settlements.jsonl"

            from scripts.agenttrove.label_settlements import label_traces

            label_traces(str(fixture_path), output_path=str(settlement_path))

            settlements = load_settlements(str(settlement_path))
            policies = mine_policies(settlements)
            output = Path(tmpdir) / "policies.yaml"
            write_policies(policies, str(output))

            assert output.exists()
            loaded = yaml.safe_load(output.read_text(encoding="utf-8"))
            assert "policies" in loaded
            assert len(loaded["policies"]) >= 10


class TestEvalSuites:
    def test_build_eval_suites(self):
        from scripts.agenttrove.build_eval_suites import build_eval_suites

        with tempfile.TemporaryDirectory() as tmpdir:
            fixture_path = FIXTURES / "test_traces.jsonl"
            settlement_path = Path(tmpdir) / "settlements.jsonl"

            from scripts.agenttrove.label_settlements import label_traces

            label_traces(str(fixture_path), output_path=str(settlement_path))

            output_dir = Path(tmpdir) / "evals"
            written = build_eval_suites(str(settlement_path), str(output_dir))

            assert len(written) >= 5
            for name, path in written.items():
                assert path.exists()
                with path.open("r") as f:
                    items = [json.loads(line) for line in f if line.strip()]
                for item in items:
                    assert "trace_id" in item
                    assert "expected_harness_behavior" in item
                    assert "settlement_criteria" in item

    def test_eval_suites_cover_failure_modes(self):
        from scripts.agenttrove.build_eval_suites import build_eval_suites

        with tempfile.TemporaryDirectory() as tmpdir:
            fixture_path = FIXTURES / "test_traces.jsonl"
            settlement_path = Path(tmpdir) / "settlements.jsonl"

            from scripts.agenttrove.label_settlements import label_traces

            label_traces(str(fixture_path), output_path=str(settlement_path))

            output_dir = Path(tmpdir) / "evals"
            written = build_eval_suites(str(settlement_path), str(output_dir))

            suite_names = set(written.keys())
            assert "premature_closure" in suite_names
            assert "tool_thrashing" in suite_names
            assert "brittle_successes" in suite_names


class TestSFTExport:
    def test_sft_export_filters_bad_traces(self):
        from scripts.agenttrove.export_sharegpt_sft import export_sharegpt_sft

        with tempfile.TemporaryDirectory() as tmpdir:
            fixture_path = FIXTURES / "test_traces.jsonl"
            settlement_path = Path(tmpdir) / "settlements.jsonl"

            from scripts.agenttrove.label_settlements import label_traces

            label_traces(str(fixture_path), output_path=str(settlement_path))

            output = Path(tmpdir) / "sft.jsonl"
            export_sharegpt_sft(str(settlement_path), str(fixture_path), str(output))

            with output.open("r") as f:
                items = [json.loads(line) for line in f if line.strip()]

            for item in items:
                assert item["settlement_quality"] in (
                    "clean_success",
                    "recovered_success",
                )

    def test_sft_export_excludes_brittle_by_default(self):
        from scripts.agenttrove.export_sharegpt_sft import export_sharegpt_sft

        with tempfile.TemporaryDirectory() as tmpdir:
            fixture_path = FIXTURES / "test_traces.jsonl"
            settlement_path = Path(tmpdir) / "settlements.jsonl"

            from scripts.agenttrove.label_settlements import label_traces

            label_traces(str(fixture_path), output_path=str(settlement_path))

            output = Path(tmpdir) / "sft.jsonl"
            export_sharegpt_sft(str(settlement_path), str(fixture_path), str(output))

            with output.open("r") as f:
                items = [json.loads(line) for line in f if line.strip()]

            for item in items:
                assert item["settlement_quality"] != "brittle_success"

    def test_sft_export_conversation_format(self):
        from scripts.agenttrove.export_sharegpt_sft import export_sharegpt_sft

        with tempfile.TemporaryDirectory() as tmpdir:
            fixture_path = FIXTURES / "test_traces.jsonl"
            settlement_path = Path(tmpdir) / "settlements.jsonl"

            from scripts.agenttrove.label_settlements import label_traces

            label_traces(str(fixture_path), output_path=str(settlement_path))

            output = Path(tmpdir) / "sft.jsonl"
            export_sharegpt_sft(str(settlement_path), str(fixture_path), str(output))

            with output.open("r") as f:
                for line in f:
                    if not line.strip():
                        continue
                    item = json.loads(line)
                    assert "conversations" in item
                    assert isinstance(item["conversations"], list)
                    for conv in item["conversations"]:
                        assert "from" in conv
                        assert "value" in conv


CORRECTION_FIXTURES = FIXTURES / "correction_traces.jsonl"


def _load_correction_traces() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with CORRECTION_FIXTURES.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                records.append(json.loads(line))
    return records


class TestJSONCommandParsing:
    def test_single_json_command(self):
        from scripts.agenttrove.parsing import parse_assistant_content

        content = '{"commands": [{"keystrokes": "ls -la\\n"}], "task_complete": false}'
        result = parse_assistant_content(content)
        assert result["parsed"] is True
        assert len(result["commands"]) == 1
        assert result["commands"][0]["content"] == "ls -la\n"

    def test_multiple_json_commands(self):
        from scripts.agenttrove.parsing import parse_assistant_content

        content = '{"commands": [{"keystrokes": "python test.py\\n"}, {"keystrokes": "cat output.txt\\n"}]}'
        result = parse_assistant_content(content)
        assert result["parsed"] is True
        assert len(result["commands"]) == 2

    def test_empty_commands_array(self):
        from scripts.agenttrove.parsing import parse_assistant_content

        content = '{"commands": [], "task_complete": true}'
        result = parse_assistant_content(content)
        assert result["parsed"] is True
        assert len(result["commands"]) == 0
        assert result["task_complete"] is True

    def test_malformed_json_falls_back(self):
        from scripts.agenttrove.parsing import parse_assistant_content

        content = "I'll run that command for you.\n```bash\nls -la\n```"
        result = parse_assistant_content(content)
        assert result["parsed"] is False
        assert result["source"] == "regex_fallback"


class TestTaskCompletionDetection:
    def test_task_complete_true(self):
        from scripts.agenttrove.parsing import detect_task_complete

        messages = [
            {"role": "user", "content": "Do something"},
            {"role": "assistant", "content": '{"commands": [], "task_complete": true}'},
        ]
        result = detect_task_complete(messages)
        assert result["has_marker"] is True
        assert result["value"] is True
        assert result["source"] == "assistant_json"

    def test_task_complete_false(self):
        from scripts.agenttrove.parsing import detect_task_complete

        messages = [
            {"role": "user", "content": "Do something"},
            {
                "role": "assistant",
                "content": '{"commands": [], "task_complete": false}',
            },
        ]
        result = detect_task_complete(messages)
        assert result["has_marker"] is True
        assert result["value"] is False

    def test_prose_final_answer(self):
        from scripts.agenttrove.parsing import detect_task_complete

        messages = [
            {"role": "user", "content": "What is 2+2?"},
            {"role": "assistant", "content": "The answer is 4."},
        ]
        result = detect_task_complete(messages)
        assert result["has_marker"] is True
        assert result["value"] is True
        assert result["source"] == "prose"


class TestCorrectedProfiles:
    def test_json_command_count(self):
        from scripts.agenttrove.profile_traces import profile_trace

        traces = _load_correction_traces()
        trace = traces[0]
        profile = profile_trace(trace)
        assert profile["json_command_count"] == 2
        assert profile["command_like_action_count"] >= 2
        assert profile["has_task_complete_marker"] is True
        assert profile["task_complete_value"] is True

    def test_multi_command_count(self):
        from scripts.agenttrove.profile_traces import profile_trace

        traces = _load_correction_traces()
        trace = traces[1]
        profile = profile_trace(trace)
        assert profile["json_command_count"] == 3

    def test_task_complete_profile_fields(self):
        from scripts.agenttrove.profile_traces import profile_trace

        traces = _load_correction_traces()
        true_trace = traces[2]
        false_trace = traces[3]
        true_profile = profile_trace(true_trace)
        false_profile = profile_trace(false_trace)
        assert true_profile["has_task_complete_marker"] is True
        assert true_profile["task_complete_value"] is True
        assert false_profile["has_task_complete_marker"] is True
        assert false_profile["task_complete_value"] is False

    def test_malformed_json_uses_regex(self):
        from scripts.agenttrove.profile_traces import profile_trace

        traces = _load_correction_traces()
        trace = traces[8]
        profile = profile_trace(trace)
        assert profile["regex_command_like_action_count"] >= 1


class TestCorrectedSettlementLabels:
    @pytest.fixture()
    def rules(self):
        from scripts.agenttrove.label_settlements import load_rules

        return load_rules("configs/agenttrove/settlement_label_rules.yaml")

    @pytest.fixture()
    def correction_traces(self):
        return _load_correction_traces()

    def test_null_reward_with_task_complete_true(self, rules, correction_traces):
        from scripts.agenttrove.label_settlements import label_trace
        from scripts.agenttrove.profile_traces import profile_trace

        profile = profile_trace(correction_traces[4])
        settlement = label_trace(correction_traces[4], profile, rules)
        assert settlement["outcome"]["settlement_quality"] == "clean_success"
        assert settlement["outcome"]["confidence"] >= 0.6

    def test_null_reward_with_unresolved_error(self, rules, correction_traces):
        from scripts.agenttrove.label_settlements import label_trace
        from scripts.agenttrove.profile_traces import profile_trace

        profile = profile_trace(correction_traces[5])
        settlement = label_trace(correction_traces[5], profile, rules)
        assert settlement["outcome"]["settlement_quality"] in (
            "failure_with_signal",
            "failure_without_signal",
        )

    def test_boilerplate_no_context_loss(self, rules, correction_traces):
        from scripts.agenttrove.label_settlements import label_trace
        from scripts.agenttrove.profile_traces import profile_trace

        profile = profile_trace(correction_traces[6])
        settlement = label_trace(correction_traces[6], profile, rules)
        fm = settlement["cognitive_os_labels"]["failure_mode"]
        modes = fm if isinstance(fm, list) else [fm]
        assert "context_loss" not in modes

    def test_real_context_loss_detected(self, rules, correction_traces):
        from scripts.agenttrove.label_settlements import label_trace
        from scripts.agenttrove.profile_traces import profile_trace

        profile = profile_trace(correction_traces[7])
        settlement = label_trace(correction_traces[7], profile, rules)
        fm = settlement["cognitive_os_labels"]["failure_mode"]
        modes = fm if isinstance(fm, list) else [fm]
        assert "context_loss" in modes

    def test_evidence_attached_to_labels(self, rules, correction_traces):
        from scripts.agenttrove.label_settlements import label_trace
        from scripts.agenttrove.profile_traces import profile_trace

        profile = profile_trace(correction_traces[0])
        settlement = label_trace(correction_traces[0], profile, rules)
        assert "label_evidence" in settlement
        assert "settlement_quality" in settlement["label_evidence"]
        assert len(settlement["label_evidence"]["settlement_quality"]) > 0

    def test_confidence_score_present(self, rules, correction_traces):
        from scripts.agenttrove.label_settlements import label_trace
        from scripts.agenttrove.profile_traces import profile_trace

        for i, trace in enumerate(correction_traces[:5]):
            profile = profile_trace(trace)
            settlement = label_trace(trace, profile, rules)
            assert "confidence" in settlement["outcome"], (
                f"Trace {i} missing confidence"
            )
            assert 0.0 <= settlement["outcome"]["confidence"] <= 1.0, (
                f"Trace {i} bad confidence"
            )

    def test_json_commands_in_payment(self, rules, correction_traces):
        from scripts.agenttrove.label_settlements import label_trace
        from scripts.agenttrove.profile_traces import profile_trace

        profile = profile_trace(correction_traces[0])
        settlement = label_trace(correction_traces[0], profile, rules)
        assert settlement["payment"]["json_command_count"] == 2

    def test_malformed_json_settlement(self, rules, correction_traces):
        from scripts.agenttrove.label_settlements import label_trace
        from scripts.agenttrove.profile_traces import profile_trace

        profile = profile_trace(correction_traces[8])
        settlement = label_trace(correction_traces[8], profile, rules)
        assert settlement["outcome"]["settlement_quality"] in (
            "clean_success",
            "unknown",
        )


class TestSystemPromptBoilerplate:
    def test_detects_boilerplate(self):
        from scripts.agenttrove.parsing import is_system_prompt_boilerplate

        assert is_system_prompt_boilerplate(
            "You are an AI assistant tasked with solving command-line tasks in a Linux environment."
        )
        assert is_system_prompt_boilerplate("You are a helpful assistant.")
        assert not is_system_prompt_boilerplate("Check if the file exists in /tmp.")


class TestStructuralSettlement:
    def test_structural_inference_success(self):
        from scripts.agenttrove.parsing import infer_settlement_from_structure

        messages = [
            {"role": "user", "content": "Do something"},
            {
                "role": "assistant",
                "content": '{"commands": [{"keystrokes": "echo done\\n"}], "task_complete": false}',
            },
            {"role": "user", "content": "New Terminal Output:\necho done"},
            {"role": "assistant", "content": '{"commands": [], "task_complete": true}'},
        ]
        profile = {"json_command_count": 1, "error_like_output_count": 0}
        result = infer_settlement_from_structure(messages, profile)
        assert result["settlement_quality"] == "clean_success"
        assert result["confidence"] >= 0.6
        assert len(result["evidence"]) > 0

    def test_structural_inference_failure(self):
        from scripts.agenttrove.parsing import infer_settlement_from_structure

        messages = [
            {"role": "user", "content": "Do something"},
            {
                "role": "assistant",
                "content": '{"commands": [{"keystrokes": "python broken.py\\n"}], "task_complete": false}',
            },
            {
                "role": "user",
                "content": "New Terminal Output:\nError: module not found",
            },
            {
                "role": "assistant",
                "content": '{"commands": [], "task_complete": false}',
            },
        ]
        profile = {"json_command_count": 1, "error_like_output_count": 1}
        result = infer_settlement_from_structure(messages, profile)
        assert result["settlement_quality"] in (
            "failure_with_signal",
            "failure_without_signal",
        )
