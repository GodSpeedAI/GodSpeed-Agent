"""Tests for the agentic calibration pipeline.

Proof classification: external-proxy-settlement records are valid for
calibration experiments and baseline comparison only.  They must not
promote local capabilities, metabolization, or enterprise readiness.
"""

from pathlib import Path

import yaml


# ---------------------------------------------------------------------------
# Task 1: Calibration source manifest
# ---------------------------------------------------------------------------


def test_calibration_sources_manifest_declares_priority_and_external_proxy_classification():
    path = Path("configs/settlement_datasets/calibration_sources.yaml")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))

    assert data["target_usable_settlements"] == 500
    assert data["settlement_classification"] == "external-proxy-settlement"
    assert data["min_confidence"] == 0.65

    names = [item["name"] for item in data["datasets"]]
    assert names[:3] == [
        "swegym_openhands",
        "agenttrove",
        "nebius_swe_agent",
    ]

    for source in data["datasets"]:
        assert source["source_uri"]
        assert source["adapter"]
        assert source["split"]
        assert source["max_rows"] > 0
        assert source["priority"] > 0


# ---------------------------------------------------------------------------
# Task 2: Hugging Face streaming helper
# ---------------------------------------------------------------------------


def test_iter_limited_stops_after_limit():
    from scripts.settlement_datasets.hf_stream import iter_limited

    rows = list(iter_limited(iter([{"id": 1}, {"id": 2}, {"id": 3}]), limit=2))
    assert rows == [{"id": 1}, {"id": 2}]


def test_load_hf_stream_is_lazy_and_patchable(monkeypatch):
    from scripts.settlement_datasets.hf_stream import load_hf_stream

    calls = []

    def fake_load_dataset(source_uri, split, streaming=True):
        calls.append((source_uri, split, streaming))
        return iter([{"id": "row-1"}])

    monkeypatch.setattr(
        "scripts.settlement_datasets.hf_stream.load_dataset", fake_load_dataset
    )

    stream = load_hf_stream("repo/name", split="train")
    assert list(stream) == [{"id": "row-1"}]
    assert calls == [("repo/name", "train", True)]


# ---------------------------------------------------------------------------
# Task 3: SWE-Gym OpenHands adapter
# ---------------------------------------------------------------------------


def test_swegym_openhands_adapter_registered_and_validates_fixture():
    from scripts.settlement_datasets.registry import available_datasets, get_adapter

    assert "swegym_openhands" in available_datasets()
    adapter = get_adapter("swegym_openhands")
    fixture = Path("tests/fixtures/settlement_datasets/swegym_openhands/sample.jsonl")

    records = [
        adapter.to_settlement_record(raw)
        for raw in adapter.stream(input_path=str(fixture))
    ]

    assert len(records) == 2
    assert records[0]["dataset"] == "swegym_openhands"
    assert records[0]["outcome"]["success"] is True
    assert records[1]["outcome"]["success"] is False
    assert all(adapter.validate_record(record) == [] for record in records)


# ---------------------------------------------------------------------------
# Task 4: Nebius SWE-Agent adapter
# ---------------------------------------------------------------------------


def test_nebius_swe_agent_adapter_registered_and_validates_fixture():
    from scripts.settlement_datasets.registry import available_datasets, get_adapter

    assert "nebius_swe_agent" in available_datasets()
    adapter = get_adapter("nebius_swe_agent")
    fixture = Path("tests/fixtures/settlement_datasets/nebius_swe_agent/sample.jsonl")

    records = [
        adapter.to_settlement_record(raw)
        for raw in adapter.stream(input_path=str(fixture))
    ]

    assert len(records) == 2
    assert records[0]["outcome"]["success"] is True
    assert records[1]["outcome"]["success"] is False
    assert records[0]["payment"]["commands"] >= 0
    assert all(adapter.validate_record(record) == [] for record in records)


# ---------------------------------------------------------------------------
# Task 5: Calibration pipeline orchestrator
# ---------------------------------------------------------------------------


def test_load_calibration_manifest_orders_sources_by_priority():
    from scripts.settlement_datasets.run_calibration_pipeline import (
        load_calibration_manifest,
    )

    manifest = load_calibration_manifest(
        "configs/settlement_datasets/calibration_sources.yaml"
    )
    assert [source["name"] for source in manifest["datasets"]][:3] == [
        "swegym_openhands",
        "agenttrove",
        "nebius_swe_agent",
    ]


def test_should_stop_for_target_when_enough_usable_settlements():
    from scripts.settlement_datasets.run_calibration_pipeline import (
        CalibrationRunState,
        should_stop_for_target,
    )

    state = CalibrationRunState(target_usable_settlements=500)
    state.usable_settlements = 500
    assert should_stop_for_target(state) is True


# ---------------------------------------------------------------------------
# Task 6: Dataset iteration, filtering, and resumable outputs
# ---------------------------------------------------------------------------


def test_calibration_pipeline_processes_fixture_sources_until_target(tmp_path):
    from scripts.settlement_datasets.run_calibration_pipeline import run_pipeline

    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        """
target_usable_settlements: 2
min_confidence: 0.65
settlement_classification: external-proxy-settlement
datasets:
  - name: swegym_openhands
    source_uri: local-fixture
    adapter: swegym_openhands
    split: train
    input_path: tests/fixtures/settlement_datasets/swegym_openhands/sample.jsonl
    max_rows: 10
    priority: 1
    streaming: false
""",
        encoding="utf-8",
    )

    result = run_pipeline(
        manifest_path=str(manifest),
        run_id="fixture-calibration",
        output_run_dir=tmp_path / "run",
        target_usable_settlements=2,
        min_confidence=0.65,
        provider="disabled",
    )

    assert result["usable_settlements"] == 2
    assert (tmp_path / "run" / "settlements" / "swegym_openhands.jsonl").exists()
    assert (tmp_path / "run" / "summary.json").exists()
