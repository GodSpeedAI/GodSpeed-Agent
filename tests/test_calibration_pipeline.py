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
