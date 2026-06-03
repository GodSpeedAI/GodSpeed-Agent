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
