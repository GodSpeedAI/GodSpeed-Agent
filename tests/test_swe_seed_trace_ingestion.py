from __future__ import annotations

# Tests for the read-only SWE_SEED trace ingestion adapter
# (scripts/settlement_datasets/swe_seed_trace_reader.py). They live here because
# the existing pytest testpaths collection includes tests/, and they exercise
# the adapter in isolation with inline pathlib/json fixtures.

import json
from pathlib import Path

import pytest

from scripts.settlement_datasets import swe_seed_trace_reader as reader
from scripts.settlement_datasets.swe_seed_trace_reader import (
    read_swe_seed_hook_events,
    read_swe_seed_trace_record,
    to_trace_analysis_record,
)


def _trace_record(trace_id: str = "trace-abc") -> dict:
    return {
        "trace_id": trace_id,
        "created_at": "2026-07-29T00:00:00Z",
        "task": "fix the login bug",
        "route_decision_record": ".agent-harness/traces/route-decisions/trace-abc.json",
        "route": {
            "job_type": "bugfix",
            "route_card": ".agent-harness/routes/bugfix.json",
            "confidence": "medium",
            "assumption": None,
            "required_context": [],
            "required_skills": [],
            "work_loop": [],
            "required_artifacts": [],
            "proof": [],
            "done_when": [],
            "next_action": "reproduce",
        },
        "events": [],
        "verification": [{"type": "test_run", "status": "passed"}],
        "unresolved_risks": ["flaky-ci"],
        "completion_claim": {"at": "2026-07-29T00:01:00Z", "claim": "fixed"},
    }


def _records_dir(trace_root: Path) -> Path:
    d = trace_root / ".agent-harness" / "traces" / "records"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _write_record(trace_root: Path, record: dict) -> Path:
    p = _records_dir(trace_root) / f"{record['trace_id']}.json"
    p.write_text(json.dumps(record), encoding="utf-8")
    return p


def test_read_returns_record_and_analysis_is_provisional(tmp_path):
    trace_root = tmp_path / "repo"
    p = _write_record(trace_root, _trace_record())

    got = read_swe_seed_trace_record(trace_root, p)
    assert got["trace_id"] == "trace-abc"

    analysis = to_trace_analysis_record(got, [])
    assert analysis["trace_source"] == "swe_seed_export"
    assert analysis["classification"] == "provisional"
    assert analysis["route"] == got["route"]
    assert analysis["route_decision_record"] == got["route_decision_record"]
    assert analysis["verification"] == got["verification"]
    assert analysis["unresolved_risks"] == got["unresolved_risks"]
    assert analysis["completion_claim"] == got["completion_claim"]
    assert analysis["hook_event_count"] == 0
    assert analysis["hook_events"] == []
    for forbidden in (
        "affordance_id",
        "work_request_id",
        "proof_result_id",
        "expected_result",
        "observed_result",
    ):
        assert forbidden not in analysis


def test_hook_events_filter_by_trace_id_and_redact(tmp_path):
    hook_dir = tmp_path / "hooks"
    hook_dir.mkdir()
    lines = [
        json.dumps(
            {
                "event_id": "e1",
                "event": "tool_call",
                "status": "ok",
                "timestamp": "t1",
                "trace_id": "trace-abc",
                "attributes": {
                    "api_key": "sk-1",
                    "nested": {"token": "tok-1"},
                    "safe": "keep",
                },
            }
        ),
        json.dumps(
            {
                "event_id": "e2",
                "event": "tool_result",
                "status": "ok",
                "timestamp": "t2",
                "trace_id": "trace-xyz",
                "attributes": {},
            }
        ),
        "this line is not json",
        json.dumps(
            {
                "event_id": "e3",
                "event": "checkpoint",
                "status": "ok",
                "timestamp": "t3",
                "attributes": {"trace_id": "trace-abc"},
            }
        ),
    ]
    (hook_dir / "events-2026-07-29.jsonl").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )

    events = read_swe_seed_hook_events(hook_dir, "trace-abc")

    assert len(events) == 2
    assert [e["event"] for e in events] == ["tool_call", "checkpoint"]

    e1 = events[0]
    assert set(e1.keys()) == {"event", "status", "timestamp", "attributes"}
    assert e1["attributes"]["api_key"] == "[REDACTED]"
    assert e1["attributes"]["nested"]["token"] == "[REDACTED]"
    assert e1["attributes"]["safe"] == "keep"


def test_hook_events_missing_dir_returns_empty(tmp_path):
    assert read_swe_seed_hook_events(tmp_path / "nope", "trace-abc") == []


def test_missing_required_field_raises(tmp_path):
    trace_root = tmp_path / "repo"
    record = _trace_record()
    del record["task"]
    p = _write_record(trace_root, record)

    with pytest.raises(ValueError, match="task"):
        read_swe_seed_trace_record(trace_root, p)


def test_trace_path_outside_records_dir_rejected(tmp_path):
    trace_root = tmp_path / "repo"
    _records_dir(trace_root)

    outside = tmp_path / "evil.json"
    outside.write_text(json.dumps(_trace_record()), encoding="utf-8")
    with pytest.raises(ValueError):
        read_swe_seed_trace_record(trace_root, outside)

    inside_but_wrong = (
        trace_root / ".agent-harness" / "traces" / "route-decisions"
    )
    inside_but_wrong.mkdir(parents=True, exist_ok=True)
    stray = inside_but_wrong / "trace-abc.json"
    stray.write_text(json.dumps(_trace_record()), encoding="utf-8")
    with pytest.raises(ValueError):
        read_swe_seed_trace_record(trace_root, stray)


def test_symlink_trace_path_rejected(tmp_path):
    trace_root = tmp_path / "repo"
    real = _write_record(trace_root, _trace_record())
    link = _records_dir(trace_root) / "link.json"
    link.symlink_to(real)

    with pytest.raises(ValueError, match="symlink"):
        read_swe_seed_trace_record(trace_root, link)


def test_reader_exposes_no_writing_callables():
    forbidden_substrings = ("write", "append", "create", "finalize", "save")
    bad = [
        name
        for name in dir(reader)
        if callable(getattr(reader, name))
        and any(s in name.lower() for s in forbidden_substrings)
    ]
    assert bad == []
