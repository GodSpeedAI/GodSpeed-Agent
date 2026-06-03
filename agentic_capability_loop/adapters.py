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
import uuid
from typing import Any

NAMESPACE = "agentic_capability_loop"
DOMAIN_MODEL_HASH = hashlib.sha256(NAMESPACE.encode("utf-8")).hexdigest()


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _event(event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Build a canonical event envelope."""
    payload = {"domain_model_hash": DOMAIN_MODEL_HASH, **payload}
    return {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "namespace": NAMESPACE,
        "occurred_at": _now_iso(),
        "payload": payload,
    }


def handle_evidence_recorded(
    event: dict[str, Any],
) -> dict[str, Any]:
    """Consume EvidenceRecorded event and emit SettlementRecorded.
    
    Validates that the event references a known work request, compares
    observed_result vs expected_result, and classifies the settlement
    outcome as 'usable' | 'partial' | 'unusable'.
    
    Args:
        event: EvidenceRecorded canonical event envelope.
    
    Returns:
        SettlementRecorded canonical event envelope.
    
    Raises:
        ValueError: If event type does not match or required fields missing.
    """
    if event.get("event_type") != "EvidenceRecorded":
        raise ValueError(
            f"Expected EvidenceRecorded event, got '{event.get('event_type')}'"
        )
    payload = event.get("payload", {})
    observed = payload.get("observed_result", "")
    expected = payload.get("expected_result", "")
    work_request_id = payload.get("work_request_id", "")
    proof_result_id = payload.get("proof_result_id", "")
    context_packet_id = payload.get("context_packet_id")
    
    if not work_request_id:
        raise ValueError("EvidenceRecorded payload missing 'work_request_id'")
    
    # Classify settlement outcome from evidence comparison
    if observed == expected:
        outcome = "usable"
        outcome_reason = "Observed result matches expected result"
    elif observed and expected and observed.strip() and expected.strip():
        # Partial match — some output but not exactly what was expected
        outcome = "partial"
        outcome_reason = f"Observed result differs from expected: got '{observed[:100]}'"
    else:
        outcome = "unusable"
        outcome_reason = "Observed result is empty or expected result not specified"
    
    return emit_settlement_recorded(
        work_request_id=work_request_id,
        proof_result_id=proof_result_id,
        evidence_event_id=event.get("event_id", ""),
        outcome=outcome,
        outcome_reason=outcome_reason,
        context_packet_id=context_packet_id,
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


def update_capability_ledger(
    settlement_event: dict[str, Any],
    capability_name: str,
    *,
    capability_id: str | None = None,
    settlement_count: int = 1,
) -> dict[str, Any]:
    """Emit CapabilityUpdated event after recording a settlement.
    
    Links the settlement to a named capability and advances its lifecycle.
    Capabilities remain active_evidence until at least three usable settlements.
    
    Args:
        settlement_event: SettlementRecorded event envelope (or payload dict).
        capability_name: Human-readable name for the capability being tracked.
        capability_id: Optional stable ID; auto-generated if not provided.
    
    Returns:
        Canonical CapabilityUpdated event envelope.
    """
    payload = settlement_event.get("payload", settlement_event)
    outcome = payload.get("outcome", "unusable")
    capability_id = capability_id or str(uuid.uuid4())
    
    if outcome not in ("usable", "partial"):
        status = "latent"
    elif settlement_count >= 3:
        status = "metabolized"
    else:
        status = "active_evidence"
    
    return _event(
        "CapabilityUpdated",
        {
            "capability_id": capability_id,
            "capability_name": capability_name,
            "work_request_id": payload.get("work_request_id", ""),
            "settlement_event_id": settlement_event.get("event_id", ""),
            "context_packet_id": payload.get("context_packet_id"),
            "status": status,
            "outcome": outcome,
            "settlement_count": settlement_count,
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
) -> dict[str, Any]:
    """Persist agentic loop events to real GodSpeed JSONL ledgers."""
    settlement_envelope = ledger_store.append_event("agentic_settlements", settlement_event)
    capability_envelope = ledger_store.append_event("agentic_capabilities", capability_event)
    repetition_envelope = ledger_store.append_event("agentic_repetitions", repetition_event)
    return {
        "settlement": settlement_envelope,
        "capability": capability_envelope,
        "repetition": repetition_envelope,
    }


def detect_coherence_break(
    reason: str,
    work_request_id: str,
    *,
    missing_phase: str | None = None,
    trigger_event_id: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Detect a coherence break and emit CoherenceBreakDetected + LearningProposalCreated.
    
    A coherence break occurs when the agentic capability loop cannot complete:
    e.g., missing context packet, unauthorized corpus, missing evidence.
    
    Args:
        reason: Human-readable explanation of why coherence broke.
        work_request_id: ID of the work request where the break occurred.
        missing_phase: Optional name of the phase that was skipped or failed.
        trigger_event_id: Optional ID of the event that triggered the detection.
    
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
            "priority": "high" if "missing" in reason.lower() else "medium",
            "created_at": _now_iso(),
        },
    )
    
    return coherence_break_event, learning_proposal_event
