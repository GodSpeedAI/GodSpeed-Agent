"""GodSpeed-Agent event adapters for the agentic_capability_loop domain.

GodSpeed-Agent emits:
  - SettlementRecorded
  - CapabilityUpdated
  - RepetitionPlanned
  - TwinUpdated
  - CoherenceBreakDetected
  - LearningProposalCreated

GodSpeed-Agent consumes:
  - EvidenceRecorded (from SEA-Forge)
  - ProofCompleted (from SWE_SEED, via SEA-Forge evidence chain)
"""
from __future__ import annotations

import datetime
import hashlib
import json
import uuid
import warnings
from pathlib import Path
from typing import Any

NAMESPACE = "agentic_capability_loop"

_MANIFEST = (
    Path(__file__).resolve().parents[2]
    / "SEA"
    / "docs"
    / "specs"
    / "domains"
    / "agentic_capability_loop"
    / "agentic_capability_loop.manifest.json"
)


def _load_hash() -> str:
    if _MANIFEST.exists():
        m = json.loads(_MANIFEST.read_text(encoding="utf-8"))
        h = (m.get("meta") or {}).get("sea_file_hash")
        if h:
            return h
    warnings.warn(
        "agentic_capability_loop manifest not found or missing sea_file_hash; "
        "using namespace hash as fallback. Complete Phase 1 to fix this.",
        stacklevel=2,
    )
    return hashlib.sha256(NAMESPACE.encode("utf-8")).hexdigest()


DOMAIN_MODEL_HASH: str = _load_hash()


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _idempotency_key(
    event_type: str,
    payload: dict[str, Any],
    *,
    correlation_id: str | None = None,
) -> str:
    """Content-derived dedup key (matches SEA's v1 derivation, F-10).

    A replay (same logical content) carries the same key with a fresh
    `event_id`, so the ledger can dedup redeliveries. Covers correlation_id +
    event_type + canonical payload — not event_id/occurred_at.
    """
    content = "{cid}|{etype}|{payload}".format(
        cid=correlation_id or "",
        etype=event_type,
        payload=json.dumps(payload, sort_keys=True, separators=(",", ":")),
    )
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _provenance(
    *,
    domain_model_hash: str | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    """CEP-0008 SS15 provenance record (F-06): producer (origin) + lineage
    refs (chain). The v1 schema's provenance allows only `origin` + `chain`."""
    chain: list[str] = []
    if domain_model_hash:
        chain.append(f"domain_model_hash:{domain_model_hash}")
    if correlation_id:
        chain.append(f"correlation_id:{correlation_id}")
    return {"origin": "godspeed-agent", "chain": chain}


def _event(
    event_type: str,
    payload: dict[str, Any],
    *,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    """Build a v1-conformant envelope (`sea.agent.event.v1.json`).

    `namespace` rides inside `payload` because v1's `additionalProperties:false`
    rejects a top-level `namespace`. Family-A callers see no difference.
    """
    payload = {"domain_model_hash": DOMAIN_MODEL_HASH, "namespace": NAMESPACE, **payload}
    event: dict[str, Any] = {
        "schema_version": "v1",
        "event_id": str(uuid.uuid4()),
        "source_agent": "godspeed-agent",
        "event_type": event_type,
        "occurred_at": _now_iso(),
        "idempotency_key": _idempotency_key(
            event_type, payload, correlation_id=correlation_id
        ),
        "payload": payload,
        "provenance": _provenance(
            domain_model_hash=DOMAIN_MODEL_HASH, correlation_id=correlation_id
        ),
    }
    if correlation_id:
        event["correlation_id"] = correlation_id
    return event


def handle_evidence_recorded(
    event: dict[str, Any],
    runtime: Any,
) -> dict[str, Any]:
    """Consume an EvidenceRecorded event as provisional execution evidence.

    Translates the event into the runtime's canonical
    ``ingest_execution_evidence()`` boundary. Software proof alone is never
    settlement: a complete event yields a provisional ``ExecutionEvidenceIngested``
    envelope that preserves the match/mismatch fact; missing required evidence
    or an unknown affordance raises a typed error and emits nothing. A later
    canonical ``record_settlement()`` is the only promotion path.

    Args:
        event: EvidenceRecorded canonical event envelope.
        runtime: NavigationRuntime owning evidence ingestion and persistence.

    Raises:
        ValueError: If the event type does not match.
        DomainRuleError: If evidence is incomplete or the affordance is unknown.
    """
    if event.get("event_type") != "EvidenceRecorded":
        raise ValueError(
            f"Expected EvidenceRecorded event, got '{event.get('event_type')}'"
        )
    ingested = runtime.ingest_execution_evidence(event)
    return emit_execution_evidence_ingested(ingested, event)


def emit_execution_evidence_ingested(
    ingested: dict[str, Any],
    source_event: dict[str, Any],
) -> dict[str, Any]:
    """Emit an ExecutionEvidenceIngested envelope from a provisional record."""
    payload = source_event.get("payload", {})
    return _event(
        "ExecutionEvidenceIngested",
        {
            "evidence_event_id": ingested.get("evidence_event_id", source_event.get("event_id", "")),
            "affordance_id": ingested.get("affordance_id", payload.get("affordance_id", "")),
            "work_request_id": ingested.get("work_request_id", payload.get("work_request_id", "")),
            "proof_result_id": ingested.get("proof_result_id", payload.get("proof_result_id", "")),
            "classification": ingested.get("classification", "provisional"),
            "proof_match": ingested.get("proof_match"),
            "ingested_at": _now_iso(),
        },
    )


def emit_settlement_recorded(
    work_request_id: str,
    proof_result_id: str,
    evidence_event_id: str,
    outcome: str,
    outcome_reason: str,
    *,
    context_packet_id: str | None = None,
) -> dict[str, Any]:
    """Emit SettlementRecorded event.
    
    Args:
        work_request_id: ID of the originating work request.
        proof_result_id: ID of the proof result that generated the evidence.
        evidence_event_id: ID of the EvidenceRecorded event.
        outcome: 'usable' | 'partial' | 'unusable'.
        outcome_reason: Human-readable explanation of the outcome.
    
    Returns:
        Canonical SettlementRecorded event envelope.
    """
    return _event(
        "SettlementRecorded",
        {
            "work_request_id": work_request_id,
            "proof_result_id": proof_result_id,
            "evidence_event_id": evidence_event_id,
            "outcome": outcome,
            "outcome_reason": outcome_reason,
            "context_packet_id": context_packet_id,
            "settled_at": _now_iso(),
        },
    )


def emit_capability_updated(
    capability_record: dict[str, Any],
    settlement_event: dict[str, Any],
    *,
    capability_name: str | None = None,
) -> dict[str, Any]:
    """Emit a CapabilityUpdated envelope translating a canonical capability record.

    Pure translation: status and settlement_count come from the persisted
    canonical capability record, never from caller-supplied counts or from
    classifying a string match as settlement. ``settlement_event`` is the
    canonical SettlementRecorded envelope (or payload dict) being annotated.

    Args:
        capability_record: Canonical capability record from the runtime.
        settlement_event: Canonical SettlementRecorded envelope.
        capability_name: Optional human-readable name override.

    Returns:
        Canonical CapabilityUpdated event envelope.
    """
    payload = settlement_event.get("payload", settlement_event)
    capability_id = capability_record.get("id") or str(uuid.uuid4())
    return _event(
        "CapabilityUpdated",
        {
            "capability_id": capability_id,
            "capability_name": capability_name or capability_record.get("label", capability_id),
            "work_request_id": payload.get("work_request_id", ""),
            "settlement_event_id": settlement_event.get("event_id", ""),
            "context_packet_id": payload.get("context_packet_id"),
            "status": capability_record.get("status", ""),
            "settlement_count": capability_record.get("settlement_count", 0),
            "outcome": payload.get("outcome"),
            "updated_at": _now_iso(),
        },
    )


def schedule_repetition(
    capability_id: str,
    *,
    variation_type: str = "context",
    due_after_days: int = 7,
) -> dict[str, Any]:
    """Emit RepetitionPlanned event to schedule a repetition cycle.
    
    Capabilities must survive repeated, varied settlement before being
    counted as metabolized. This event schedules the next repetition.
    
    Args:
        capability_id: ID of the capability to repeat.
        variation_type: 'context' | 'operand' | 'combination' — which axis to vary.
        due_after_days: Number of days until this repetition is due.
    
    Returns:
        Canonical RepetitionPlanned event envelope.
    """
    due_at = (
        datetime.datetime.now(datetime.timezone.utc)
        + datetime.timedelta(days=due_after_days)
    ).isoformat()
    
    return _event(
        "RepetitionPlanned",
        {
            "repetition_plan_id": str(uuid.uuid4()),
            "capability_id": capability_id,
            "variation_type": variation_type,
            "due_at": due_at,
            "planned_at": _now_iso(),
        },
    )


def emit_twin_update(
    settlement_event: dict[str, Any],
    capability_event: dict[str, Any],
    *,
    context_id: str | None = None,
    context_health: str = "unknown",
    policy_adherence: str = "unknown",
) -> dict[str, Any]:
    """Emit TwinUpdated event to reflect the settlement in the organization twin.
    
    The organizational twin tracks the cumulative developmental state of the
    agent system. A TwinUpdated event means reality has acknowledged the change.
    
    Args:
        settlement_event: SettlementRecorded event envelope.
        capability_event: CapabilityUpdated event envelope.
        context_id: Optional context/session ID.
    
    Returns:
        Canonical TwinUpdated event envelope.
    """
    settlement_payload = settlement_event.get("payload", settlement_event)
    capability_payload = capability_event.get("payload", capability_event)
    
    return _event(
        "TwinUpdated",
        {
            "twin_update_id": str(uuid.uuid4()),
            "work_request_id": settlement_payload.get("work_request_id", ""),
            "settlement_event_id": settlement_event.get("event_id", ""),
            "capability_id": capability_payload.get("capability_id", ""),
            "capability_name": capability_payload.get("capability_name", ""),
            "outcome": settlement_payload.get("outcome", ""),
            "context_id": context_id,
            "context_health": context_health,
            "policy_adherence": policy_adherence,
            "capability_delta": {
                "status": capability_payload.get("status"),
                "settlement_count": capability_payload.get("settlement_count", 0),
                "outcome": capability_payload.get("outcome"),
            },
            "updated_at": _now_iso(),
        },
    )


def persist_to_ledger(
    settlement_event: dict[str, Any],
    capability_event: dict[str, Any],
    repetition_event: dict[str, Any],
    ledger_store: Any,
    *,
    learning_proposal_event: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Persist agentic loop outbound envelopes to the transport outbox.

    Outbound envelopes are written to one ``agentic_outbound_events`` outbox
    ledger; ``settlements``, ``capabilities``, and ``repetition_schedules``
    remain the canonical runtime authority. Learning proposals route through
    the canonical ``append_learning_proposal`` helper.
    """
    from agentic_capability_loop.learning_proposals import append_learning_proposal  # noqa: PLC0415

    outbox: list[dict[str, Any]] = []
    for envelope in (settlement_event, capability_event, repetition_event):
        if envelope is not None:
            outbox.append(ledger_store.append_event("agentic_outbound_events", envelope))

    result: dict[str, Any] = {
        "outbox": outbox,
        "learning_proposal": None,
    }

    if learning_proposal_event is not None:
        append_learning_proposal(ledger_store, learning_proposal_event)
        result["learning_proposal"] = {"event_id": learning_proposal_event["event_id"]}

    # WP-3 (F-02): best-effort one-way drain of the outbox to NATS when
    # configured. The JSONL outbox is the source of truth; this never raises —
    # a transport failure leaves events buffered for the next drain.
    try:
        from agentic_capability_loop.publisher import drain_persisted_to_nats  # noqa: PLC0415

        result["nats_drain"] = drain_persisted_to_nats(
            ledger_store,
            ("agentic_outbound_events",),
        )
    except Exception:  # noqa: BLE001 — transport must not break persistence
        result["nats_drain"] = {}

    return result


def detect_coherence_break(
    reason: str,
    work_request_id: str,
    *,
    missing_phase: str | None = None,
    trigger_event_id: str | None = None,
    domain_area: str = "agentic_capability_loop",
    evidence_ref: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Detect a coherence break and emit CoherenceBreakDetected + LearningProposalCreated.
    
    A coherence break occurs when the agentic capability loop cannot complete:
    e.g., missing context packet, unauthorized corpus, missing evidence.
    
    Args:
        reason: Human-readable explanation of why coherence broke.
        work_request_id: ID of the work request where the break occurred.
        missing_phase: Optional name of the phase that was skipped or failed.
        trigger_event_id: Optional ID of the event that triggered the detection.
        domain_area: Domain area for the learning proposal.
        evidence_ref: Optional reference to evidence that triggered the break.
    
    Returns:
        Tuple of (CoherenceBreakDetected event, LearningProposalCreated event).
    """
    coherence_break_id = str(uuid.uuid4())
    
    coherence_break_event = _event(
        "CoherenceBreakDetected",
        {
            "coherence_break_id": coherence_break_id,
            "work_request_id": work_request_id,
            "reason": reason,
            "missing_phase": missing_phase,
            "trigger_event_id": trigger_event_id,
            "detected_at": _now_iso(),
        },
    )
    
    learning_proposal_event = _event(
        "LearningProposalCreated",
        {
            "learning_proposal_id": str(uuid.uuid4()),
            "coherence_break_id": coherence_break_id,
            "work_request_id": work_request_id,
            "proposal": f"Investigate and resolve: {reason}",
            "domain_area": domain_area,
            "evidence_ref": evidence_ref,
            "priority": "high" if "missing" in reason.lower() else "medium",
            "status": "open",
            "created_at": _now_iso(),
        },
    )
    
    return coherence_break_event, learning_proposal_event
