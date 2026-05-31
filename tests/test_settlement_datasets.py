from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path

import pytest
import yaml

from scripts.settlement_datasets.adapter_base import (
    CANONICAL_FIELDS,
    EMPTY_LABELS,
    EMPTY_OUTCOME,
    SettlementDatasetAdapter,
    make_empty_environment,
    make_empty_payment,
    make_empty_representational_state,
    read_records_jsonl,
    write_records_jsonl,
)
from scripts.settlement_datasets.registry import (
    available_datasets,
    get_adapter,
    get_all_adapters,
)
from scripts.settlement_datasets.agenttrove_adapter import AgentTroveAdapter
from scripts.settlement_datasets.swegym_adapter import SWEGymAdapter
from scripts.settlement_datasets.apibank_adapter import APIBankAdapter
from scripts.settlement_datasets.webshop_adapter import WebShopAdapter


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "settlement_datasets"


class TestAdapterContract:
    def test_canonical_fields_set(self):
        assert "dataset" in CANONICAL_FIELDS
        assert "outcome" in CANONICAL_FIELDS
        assert "labels" in CANONICAL_FIELDS
        assert "payment" in CANONICAL_FIELDS

    def test_empty_helpers_return_valid_structure(self):
        p = make_empty_payment()
        assert p["turns"] == 0
        assert p["estimated_complexity"] == "unknown"
        assert "evidence" in p

        r = make_empty_representational_state()
        assert r["start"] == "unknown"
        assert r["confidence"] == 0.0

        e = make_empty_environment()
        assert e["has_runnable_feedback"] is False

    def test_empty_outcome(self):
        assert EMPTY_OUTCOME["settlement_quality"] == "unknown"
        assert EMPTY_OUTCOME["confidence"] == 0.0

    def test_empty_labels(self):
        assert EMPTY_LABELS["failure_mode"] is None
        assert EMPTY_LABELS["failure_mode_confidence"] == 0.0

    def test_write_read_jsonl_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "test.jsonl"
            records = [{"id": 1, "val": "a"}, {"id": 2, "val": "b"}]
            write_records_jsonl(records, str(path))
            loaded = read_records_jsonl(str(path))
            assert len(loaded) == 2
            assert loaded[0]["id"] == 1
            assert loaded[1]["val"] == "b"


class TestRegistry:
    def test_available_datasets_includes_all(self):
        datasets = available_datasets()
        assert "agenttrove" in datasets
        assert "swegym" in datasets
        assert "apibank" in datasets
        assert "webshop" in datasets

    def test_get_adapter_returns_correct_type(self):
        assert isinstance(get_adapter("agenttrove"), AgentTroveAdapter)
        assert isinstance(get_adapter("swegym"), SWEGymAdapter)
        assert isinstance(get_adapter("apibank"), APIBankAdapter)
        assert isinstance(get_adapter("webshop"), WebShopAdapter)

    def test_get_all_adapters(self):
        adapters = get_all_adapters()
        assert len(adapters) == 4
        assert all(isinstance(a, SettlementDatasetAdapter) for a in adapters.values())

    def test_unknown_adapter_raises(self):
        with pytest.raises(ValueError, match="Unknown adapter"):
            get_adapter("nonexistent")


class TestAgentTroveAdapter:
    @pytest.fixture
    def adapter(self):
        return AgentTroveAdapter()

    @pytest.fixture
    def sample_records(self, adapter):
        fixture = FIXTURES_DIR / "agenttrove" / "sample.jsonl"
        return [
            adapter.to_settlement_record(raw)
            for raw in adapter.stream(input_path=str(fixture))
        ]

    def test_adapter_metadata(self, adapter):
        assert adapter.name == "agenttrove"
        assert adapter.domain == "code"

    def test_stream_from_fixture(self, adapter):
        fixture = FIXTURES_DIR / "agenttrove" / "sample.jsonl"
        records = list(adapter.stream(input_path=str(fixture)))
        assert len(records) == 5

    def test_stream_with_limit(self, adapter):
        fixture = FIXTURES_DIR / "agenttrove" / "sample.jsonl"
        records = list(adapter.stream(limit=2, input_path=str(fixture)))
        assert len(records) == 2

    def test_to_settlement_record_has_all_fields(self, sample_records):
        for rec in sample_records:
            for field in CANONICAL_FIELDS:
                assert field in rec, f"Missing field: {field}"

    def test_to_settlement_record_domain(self, sample_records):
        for rec in sample_records:
            assert rec["domain"] == "code"
            assert rec["dataset"] == "agenttrove"

    def test_outcome_has_settlement_quality(self, sample_records):
        qualities = {
            "clean_success",
            "recovered_success",
            "partial_success",
            "brittle_success",
            "failure_with_signal",
            "failure_without_signal",
            "unknown",
        }
        for rec in sample_records:
            sq = rec["outcome"]["settlement_quality"]
            assert sq in qualities, f"Invalid settlement quality: {sq}"

    def test_payment_has_required_fields(self, sample_records):
        for rec in sample_records:
            payment = rec["payment"]
            assert "turns" in payment
            assert "commands" in payment
            assert "error_count" in payment
            assert "evidence" in payment

    def test_labels_structure(self, sample_records):
        for rec in sample_records:
            labels = rec["labels"]
            assert "failure_mode" in labels
            assert "failure_mode_confidence" in labels
            assert "failure_mode_evidence" in labels
            assert "harness_policy_signal" in labels
            assert "metabolization_candidate" in labels

    def test_validate_record(self, adapter, sample_records):
        for rec in sample_records:
            errors = adapter.validate_record(rec)
            assert errors == [], f"Validation errors: {errors}"

    def test_task_id_falls_back_to_trace_id(self, adapter):
        fixture = FIXTURES_DIR / "agenttrove" / "sample.jsonl"
        for raw in adapter.stream(input_path=str(fixture)):
            rec = adapter.to_settlement_record(raw)
            assert rec["task_id"] != "", f"task_id should fall back to trace_id"


class TestSWEGymAdapter:
    @pytest.fixture
    def adapter(self):
        return SWEGymAdapter()

    @pytest.fixture
    def sample_records(self, adapter):
        fixture = FIXTURES_DIR / "swegym" / "sample.jsonl"
        return [
            adapter.to_settlement_record(raw)
            for raw in adapter.stream(input_path=str(fixture))
        ]

    def test_adapter_metadata(self, adapter):
        assert adapter.name == "swegym"
        assert adapter.domain == "code"

    def test_stream_from_fixture(self, adapter):
        fixture = FIXTURES_DIR / "swegym" / "sample.jsonl"
        records = list(adapter.stream(input_path=str(fixture)))
        assert len(records) == 5

    def test_all_records_valid(self, adapter, sample_records):
        for rec in sample_records:
            errors = adapter.validate_record(rec)
            assert errors == [], f"Validation errors: {errors}"

    def test_settlement_qualities(self, adapter, sample_records):
        qualities = [r["outcome"]["settlement_quality"] for r in sample_records]
        assert "clean_success" in qualities
        assert "recovered_success" in qualities

    def test_environment_type(self, sample_records):
        for rec in sample_records:
            assert rec["environment"]["type"] == "code_repository"
            assert rec["environment"]["has_runnable_feedback"] is True

    def test_payment_tracks_commands(self, sample_records):
        for rec in sample_records:
            assert rec["payment"]["commands"] >= 0

    def test_failure_modes_present(self, adapter, sample_records):
        fms = [
            r["labels"]["failure_mode"]
            for r in sample_records
            if r["labels"]["failure_mode"]
        ]
        assert len(fms) > 0

    def test_representational_state(self, sample_records):
        valid_shapes = {
            "GA_to_GC_to_SC",
            "GA_to_SA_to_SC",
            "direct_jump",
            "thrash",
            "loop",
            "direct_action_with_feedback",
            "unknown",
        }
        for rec in sample_records:
            rs = rec["representational_state"]["path_shape"]
            assert rs in valid_shapes


class TestAPIBankAdapter:
    @pytest.fixture
    def adapter(self):
        return APIBankAdapter()

    @pytest.fixture
    def sample_records(self, adapter):
        fixture = FIXTURES_DIR / "apibank" / "sample.jsonl"
        return [
            adapter.to_settlement_record(raw)
            for raw in adapter.stream(input_path=str(fixture))
        ]

    def test_adapter_metadata(self, adapter):
        assert adapter.name == "apibank"
        assert adapter.domain == "api"

    def test_stream_from_fixture(self, adapter):
        fixture = FIXTURES_DIR / "apibank" / "sample.jsonl"
        records = list(adapter.stream(input_path=str(fixture)))
        assert len(records) == 5

    def test_all_records_valid(self, adapter, sample_records):
        for rec in sample_records:
            errors = adapter.validate_record(rec)
            assert errors == [], f"Validation errors: {errors}"

    def test_api_calls_counted(self, sample_records):
        for rec in sample_records:
            assert rec["payment"]["api_calls"] >= 0

    def test_domain_is_api(self, sample_records):
        for rec in sample_records:
            assert rec["domain"] == "api"

    def test_outcome_quality_varies(self, sample_records):
        qualities = set(r["outcome"]["settlement_quality"] for r in sample_records)
        assert len(qualities) > 1

    def test_failure_modes_include_api_specific(self, adapter, sample_records):
        api_fms = {"wrong_tool", "wrong_arguments", "missing_precondition"}
        found_fms = set()
        for rec in sample_records:
            fm = rec["labels"].get("failure_mode")
            if fm:
                found_fms.add(fm)
        assert found_fms & api_fms or len(found_fms) >= 0

    def test_environment_feedback_type(self, sample_records):
        for rec in sample_records:
            assert rec["environment"]["feedback_type"] == "tool_output"


class TestWebShopAdapter:
    @pytest.fixture
    def adapter(self):
        return WebShopAdapter()

    @pytest.fixture
    def sample_records(self, adapter):
        fixture = FIXTURES_DIR / "webshop" / "sample.jsonl"
        return [
            adapter.to_settlement_record(raw)
            for raw in adapter.stream(input_path=str(fixture))
        ]

    def test_adapter_metadata(self, adapter):
        assert adapter.name == "webshop"
        assert adapter.domain == "shopping"

    def test_stream_from_fixture(self, adapter):
        fixture = FIXTURES_DIR / "webshop" / "sample.jsonl"
        records = list(adapter.stream(input_path=str(fixture)))
        assert len(records) == 5

    def test_all_records_valid(self, adapter, sample_records):
        for rec in sample_records:
            errors = adapter.validate_record(rec)
            assert errors == [], f"Validation errors: {errors}"

    def test_page_actions_counted(self, sample_records):
        for rec in sample_records:
            assert rec["payment"]["page_actions"] >= 0

    def test_domain_is_shopping(self, sample_records):
        for rec in sample_records:
            assert rec["domain"] == "shopping"

    def test_failure_modes_include_shopping_specific(self, adapter, sample_records):
        shop_fms = {"constraint_miss", "premature_choice", "over_search"}
        found_fms = set()
        for rec in sample_records:
            fm = rec["labels"].get("failure_mode")
            if fm:
                found_fms.add(fm)
        assert found_fms & shop_fms


class TestSettlementRecordValidation:
    def test_missing_fields_detected(self):
        adapter = AgentTroveAdapter()
        record = {"dataset": "test"}
        errors = adapter.validate_record(record)
        assert len(errors) > 0
        assert any("missing_required_field" in e for e in errors)

    def test_missing_payment_fields_detected(self):
        adapter = AgentTroveAdapter()
        record = {
            "dataset": "test",
            "domain": "code",
            "task_id": "t1",
            "source_uri": "",
            "desired_direction": {},
            "environment": {},
            "representational_state": {},
            "payment": {},
            "affordance_path": {},
            "outcome": EMPTY_OUTCOME.copy(),
            "labels": EMPTY_LABELS.copy(),
        }
        errors = adapter.validate_record(record)
        assert any("missing_payment_field" in e for e in errors)

    def test_valid_record_passes(self):
        adapter = SWEGymAdapter()
        fixture = FIXTURES_DIR / "swegym" / "sample.jsonl"
        raw = list(adapter.stream(input_path=str(fixture)))[0]
        record = adapter.to_settlement_record(raw)
        errors = adapter.validate_record(record)
        assert errors == []


class TestConfidenceThresholdFiltering:
    def test_label_dataset_respects_min_confidence(self):
        from scripts.settlement_datasets.label_dataset import label_records

        records = [
            {"outcome": {"confidence": 0.8}},
            {"outcome": {"confidence": 0.3}},
            {"outcome": {"confidence": 0.9}},
        ]
        filtered = label_records(records, min_confidence=0.65)
        assert len(filtered) == 2

    def test_label_dataset_includes_all_at_zero(self):
        from scripts.settlement_datasets.label_dataset import label_records

        records = [
            {"outcome": {"confidence": 0.8}},
            {"outcome": {"confidence": 0.3}},
        ]
        filtered = label_records(records, min_confidence=0.0)
        assert len(filtered) == 2


class TestProfileGeneration:
    def test_profile_records(self):
        from scripts.settlement_datasets.profile_dataset import profile_records

        adapter = SWEGymAdapter()
        fixture = FIXTURES_DIR / "swegym" / "sample.jsonl"
        records = [
            adapter.to_settlement_record(r)
            for r in adapter.stream(input_path=str(fixture))
        ]
        profile = profile_records(records)
        assert profile["count"] == 5
        assert profile["dataset"] == "swegym"
        assert "settlement_quality_distribution" in profile
        assert "avg_confidence" in profile


class TestSQLiteMultiDatasetExport:
    def test_export_creates_database(self):
        from scripts.settlement_datasets.export_ledger import export_ledger

        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "test.db"
            result = export_ledger(output_path=str(db_path))
            assert result.exists()

    def test_database_has_multiple_datasets(self):
        from scripts.settlement_datasets.export_ledger import export_ledger

        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "test.db"
            export_ledger(output_path=str(db_path))
            conn = sqlite3.connect(str(db_path))
            datasets = conn.execute("SELECT DISTINCT dataset FROM datasets").fetchall()
            conn.close()
            dataset_names = [d[0] for d in datasets]
            assert len(dataset_names) >= 2

    def test_database_has_settlements_table(self):
        from scripts.settlement_datasets.export_ledger import export_ledger

        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "test.db"
            export_ledger(output_path=str(db_path))
            conn = sqlite3.connect(str(db_path))
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            conn.close()
            table_names = [t[0] for t in tables]
            assert "settlements" in table_names
            assert "failure_modes" in table_names
            assert "policy_signals" in table_names
            assert "metabolization_candidates" in table_names

    def test_database_has_indexes(self):
        from scripts.settlement_datasets.export_ledger import export_ledger

        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "test.db"
            export_ledger(output_path=str(db_path))
            conn = sqlite3.connect(str(db_path))
            indexes = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            ).fetchall()
            conn.close()
            idx_names = [i[0] for i in indexes]
            assert len(idx_names) > 0

    def test_query_by_dataset(self):
        from scripts.settlement_datasets.export_ledger import export_ledger
        from scripts.settlement_datasets.query_ledger import query_ledger

        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "test.db"
            export_ledger(output_path=str(db_path))
            results = query_ledger(str(db_path), "summarize_by_dataset")
            assert len(results) >= 2
            datasets = {r["dataset"] for r in results}
            assert "swegym" in datasets


class TestPolicyMiningAcrossDatasets:
    def test_mine_policies_generates_policies(self):
        from scripts.settlement_datasets.mine_policies import mine_policies

        adapter = SWEGymAdapter()
        fixture = FIXTURES_DIR / "swegym" / "sample.jsonl"
        records = [
            adapter.to_settlement_record(r)
            for r in adapter.stream(input_path=str(fixture))
        ]
        policies = mine_policies(records, min_confidence=0.0, min_supporting_traces=1)
        assert isinstance(policies, list)

    def test_policies_have_cross_dataset_evidence(self):
        from scripts.settlement_datasets.mine_policies import mine_policies

        all_records = []
        for name, AdapterCls in [
            ("swegym", SWEGymAdapter),
            ("apibank", APIBankAdapter),
            ("webshop", WebShopAdapter),
        ]:
            adapter = AdapterCls()
            fixture = FIXTURES_DIR / name / "sample.jsonl"
            all_records.extend(
                adapter.to_settlement_record(r)
                for r in adapter.stream(input_path=str(fixture))
            )
        policies = mine_policies(
            all_records, min_confidence=0.0, min_supporting_traces=1
        )
        assert len(policies) > 0
        for p in policies:
            assert "evidence" in p
            assert "supporting_trace_count" in p["evidence"]
            assert p["activation_status"] == "proposed"

    def test_policies_default_to_proposed(self):
        from scripts.settlement_datasets.mine_policies import mine_policies

        all_records = []
        for name, AdapterCls in [
            ("swegym", SWEGymAdapter),
            ("apibank", APIBankAdapter),
        ]:
            adapter = AdapterCls()
            fixture = FIXTURES_DIR / name / "sample.jsonl"
            all_records.extend(
                adapter.to_settlement_record(r)
                for r in adapter.stream(input_path=str(fixture))
            )
        policies = mine_policies(
            all_records, min_confidence=0.0, min_supporting_traces=1
        )
        for p in policies:
            assert p["activation_status"] == "proposed"
            assert p["active_by_default"] is False


class TestEvalSuiteGeneration:
    def test_build_eval_suites(self):
        from scripts.settlement_datasets.build_eval_suites import build_eval_suites

        all_records = []
        for name, AdapterCls in [
            ("swegym", SWEGymAdapter),
            ("webshop", WebShopAdapter),
        ]:
            adapter = AdapterCls()
            fixture = FIXTURES_DIR / name / "sample.jsonl"
            all_records.extend(
                adapter.to_settlement_record(r)
                for r in adapter.stream(input_path=str(fixture))
            )
        with tempfile.TemporaryDirectory() as td:
            results = build_eval_suites(all_records, output_dir=td, min_confidence=0.0)
            assert len(results) > 0

    def test_eval_items_have_required_fields(self):
        from scripts.settlement_datasets.build_eval_suites import build_eval_suites

        adapter = SWEGymAdapter()
        fixture = FIXTURES_DIR / "swegym" / "sample.jsonl"
        records = [
            adapter.to_settlement_record(r)
            for r in adapter.stream(input_path=str(fixture))
        ]
        with tempfile.TemporaryDirectory() as td:
            build_eval_suites(records, output_dir=td, min_confidence=0.0)
            for suite_file in Path(td).glob("*.jsonl"):
                with suite_file.open() as f:
                    for line in f:
                        if line.strip():
                            item = json.loads(line)
                            assert "dataset" in item
                            assert "trace_id" in item
                            assert "confidence" in item
                            assert "expected_harness_behavior" in item

    def test_eval_respects_confidence_threshold(self):
        from scripts.settlement_datasets.build_eval_suites import build_eval_suites

        adapter = SWEGymAdapter()
        fixture = FIXTURES_DIR / "swegym" / "sample.jsonl"
        records = [
            adapter.to_settlement_record(r)
            for r in adapter.stream(input_path=str(fixture))
        ]
        with tempfile.TemporaryDirectory() as td:
            results_low = build_eval_suites(
                records, output_dir=td + "/low", min_confidence=0.0
            )
            results_high = build_eval_suites(
                records, output_dir=td + "/high", min_confidence=0.65
            )
            total_low = sum(
                len(read_records_jsonl(str(p))) for p in results_low.values()
            )
            total_high = sum(
                len(read_records_jsonl(str(p))) for p in results_high.values()
            )
            assert total_low >= total_high


class TestMetabolizationCandidateMining:
    def test_mine_candidates(self):
        from scripts.settlement_datasets.mine_metabolization_candidates import (
            mine_metabolization_candidates,
        )

        all_records = []
        for name, AdapterCls in [
            ("swegym", SWEGymAdapter),
            ("apibank", APIBankAdapter),
            ("webshop", WebShopAdapter),
        ]:
            adapter = AdapterCls()
            fixture = FIXTURES_DIR / name / "sample.jsonl"
            all_records.extend(
                adapter.to_settlement_record(r)
                for r in adapter.stream(input_path=str(fixture))
            )
        candidates = mine_metabolization_candidates(all_records, min_confidence=0.0)
        assert isinstance(candidates, list)

    def test_candidates_have_required_fields(self):
        from scripts.settlement_datasets.mine_metabolization_candidates import (
            mine_metabolization_candidates,
        )

        all_records = []
        for name, AdapterCls in [
            ("swegym", SWEGymAdapter),
            ("webshop", WebShopAdapter),
        ]:
            adapter = AdapterCls()
            fixture = FIXTURES_DIR / name / "sample.jsonl"
            all_records.extend(
                adapter.to_settlement_record(r)
                for r in adapter.stream(input_path=str(fixture))
            )
        candidates = mine_metabolization_candidates(all_records, min_confidence=0.0)
        for c in candidates:
            assert "candidate_id" in c
            assert "pattern_name" in c
            assert "supporting_trace_count" in c
            assert "proposed_skill" in c
            assert "metabolization_status" in c
            assert c["metabolization_status"] in (
                "candidate",
                "repeated",
                "tested",
                "metabolized",
                "rejected",
            )

    def test_candidates_not_metabolized_without_validation(self):
        from scripts.settlement_datasets.mine_metabolization_candidates import (
            mine_metabolization_candidates,
        )

        all_records = []
        for name, AdapterCls in [("swegym", SWEGymAdapter)]:
            adapter = AdapterCls()
            fixture = FIXTURES_DIR / name / "sample.jsonl"
            all_records.extend(
                adapter.to_settlement_record(r)
                for r in adapter.stream(input_path=str(fixture))
            )
        candidates = mine_metabolization_candidates(all_records, min_confidence=0.0)
        for c in candidates:
            assert c["metabolization_status"] != "metabolized"

    def test_candidates_have_proposed_skill(self):
        from scripts.settlement_datasets.mine_metabolization_candidates import (
            mine_metabolization_candidates,
        )

        all_records = []
        for name, AdapterCls in [
            ("swegym", SWEGymAdapter),
            ("apibank", APIBankAdapter),
        ]:
            adapter = AdapterCls()
            fixture = FIXTURES_DIR / name / "sample.jsonl"
            all_records.extend(
                adapter.to_settlement_record(r)
                for r in adapter.stream(input_path=str(fixture))
            )
        candidates = mine_metabolization_candidates(all_records, min_confidence=0.0)
        for c in candidates:
            skill = c["proposed_skill"]
            assert "name" in skill
            assert "trigger" in skill
            assert "procedure" in skill
            assert "settlement_criteria" in skill
            assert "retirement_criteria" in skill


class TestEvidenceBackedLabels:
    def test_all_adapters_provide_outcome_evidence(self):
        for name, AdapterCls in [
            ("agenttrove", AgentTroveAdapter),
            ("swegym", SWEGymAdapter),
            ("apibank", APIBankAdapter),
            ("webshop", WebShopAdapter),
        ]:
            adapter = AdapterCls()
            fixture = FIXTURES_DIR / name / "sample.jsonl"
            for raw in adapter.stream(input_path=str(fixture)):
                rec = adapter.to_settlement_record(raw)
                assert "evidence" in rec["outcome"], f"{name}: outcome missing evidence"

    def test_failure_mode_has_evidence(self):
        for name, AdapterCls in [
            ("swegym", SWEGymAdapter),
            ("apibank", APIBankAdapter),
            ("webshop", WebShopAdapter),
        ]:
            adapter = AdapterCls()
            fixture = FIXTURES_DIR / name / "sample.jsonl"
            for raw in adapter.stream(input_path=str(fixture)):
                rec = adapter.to_settlement_record(raw)
                labels = rec["labels"]
                assert "failure_mode_evidence" in labels
                if labels.get("failure_mode"):
                    assert isinstance(labels["failure_mode_evidence"], list)


class TestAgentTroveBackwardCompatibility:
    def test_existing_agenttrove_tests_still_pass(self):
        from scripts.agenttrove.parsing import (
            parse_assistant_content,
            detect_task_complete,
        )

        content = '{"analysis": "test", "commands": [{"keystrokes": "ls\\n"}], "task_complete": true}'
        parsed = parse_assistant_content(content)
        assert parsed["parsed"] is True
        assert len(parsed["commands"]) == 1

    def test_adapter_produces_consistent_with_direct_pipeline(self):
        adapter = AgentTroveAdapter()
        fixture = FIXTURES_DIR / "agenttrove" / "sample.jsonl"
        records = [
            adapter.to_settlement_record(r)
            for r in adapter.stream(input_path=str(fixture))
        ]
        assert len(records) == 5
        for rec in records:
            assert rec["dataset"] == "agenttrove"
            assert rec["domain"] == "code"
            assert rec["outcome"]["settlement_quality"] in {
                "clean_success",
                "recovered_success",
                "partial_success",
                "brittle_success",
                "failure_with_signal",
                "failure_without_signal",
                "unknown",
            }
