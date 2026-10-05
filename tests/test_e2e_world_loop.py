"""End-to-end world loop, GodSpeed-Agent's two hops (driven by sea-rs `scripts/e2e-world-loop.sh`).

The loop is E1 (here) -> Context Kernel -> SWE_SEED (E4) -> SEA-Forge (E5/E6) -> SWE_SEED (E7) ->
RealityTrace (E8) -> E8 consumed here. Every hop reads the previous hop's real output from
``E2E_DIR`` and writes its own, all pinned to ONE ``E2E_WORLD_REF``. Skipped unless the driver sets
``E2E_DIR``, so a normal ``pytest`` run is unaffected.
"""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path

import pytest

from godspeed_nav.canonical_events import project_work_requested
from godspeed_nav.evidence_ingest import EvidenceIngestState, ingest_evidence_recorded
from godspeed_nav.schemas import DomainRuleError

from tests.test_canonical_events import direction, executable_affordance

E2E_DIR = os.environ.get("E2E_DIR")
pytestmark = pytest.mark.skipif(not E2E_DIR, reason="set E2E_DIR via scripts/e2e-world-loop.sh")


def _env(name: str) -> str:
    return os.environ[name]


def _read(name: str) -> dict:
    return json.loads((Path(E2E_DIR) / name).read_text(encoding="utf-8"))


def test_hop_1_emit_work_requested():
    event = project_work_requested(
        executable_affordance(),
        work_request_id=_env("E2E_WORK_REQUEST_ID"),
        domain_model_hash=_env("E2E_DOMAIN_HASH"),
        direction=direction(),
        parent_direction_event_id="33333333-3333-4333-8333-555555555555",
        world_ref=_env("E2E_WORLD_REF"),
    )
    assert event["payload"]["world_ref"] == _env("E2E_WORLD_REF")
    (Path(E2E_DIR) / "e1_work_requested.json").write_text(
        json.dumps(event, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _gate(envelope: dict, *, world: str | None, parents: list[str]):
    return ingest_evidence_recorded(
        envelope,
        local_model_sha256=_env("E2E_DOMAIN_HASH"),
        expected_work_request_id=_env("E2E_WORK_REQUEST_ID"),
        state=EvidenceIngestState(),
        known_parent_ids=parents,
        local_world_ref=world,
    )


def test_hop_6_ingest_evidence_recorded():
    envelope = _read("e8_evidence_recorded.json")
    parents = [_read("e6_operational_settlement.json")["event_id"], _read("e7_proof_completed.json")["event_id"]]
    world = _env("E2E_WORLD_REF")

    admission = _gate(envelope, world=world, parents=parents)
    record = admission.record
    assert admission.status == "first"
    # Evidence is provisional and bound to the same world the work started in.
    assert record.classification == "provisional"
    assert record.world_binding == "bound"
    assert record.world_ref == world
    assert record.work_request_id == _env("E2E_WORK_REQUEST_ID")

    # The loop is one world end to end: every artifact in the exchange dir names it.
    for name in sorted(p.name for p in Path(E2E_DIR).glob("e*.json")):
        text = (Path(E2E_DIR) / name).read_text(encoding="utf-8")
        assert world in text, f"{name} does not carry the pinned world"
        assert "world:" not in text.replace(world, ""), f"{name} names a second world"


def test_hop_6_refuses_evidence_from_another_world():
    envelope = _read("e8_evidence_recorded.json")
    parents = [_read("e6_operational_settlement.json")["event_id"], _read("e7_proof_completed.json")["event_id"]]
    other = "world:other@sha256:" + "d" * 64
    with pytest.raises(DomainRuleError) as err:
        _gate(envelope, world=other, parents=parents)
    assert err.value.code == "world_ref_drift"

    stripped = copy.deepcopy(envelope)
    stripped["payload"].pop("world_ref")
    with pytest.raises(DomainRuleError) as err:
        _gate(stripped, world=_env("E2E_WORLD_REF"), parents=parents)
    assert err.value.code == "world_ref_missing"
