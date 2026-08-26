"""Canonical E9 developmental-event projection (convergence T09).

Projects EXPLICIT GodSpeed-Agent developmental decisions into the canonical
v1 envelope family shared with the T03/T08 convergence surfaces
(``godspeed_nav.canonical_events``, ``godspeed_nav.evidence_ingest``):

- SettlementRecorded
- CapabilityUpdated
- RepetitionPlanned
- LearningProposalCreated
- CoherenceBreakDetected

``godspeed_agent`` is the EXCLUSIVE authoritative producer of ALL FIVE event
types (frozen ``event_ownership``). Every envelope carries the four common
required payload fields — ``work_request_id``, ``source_evidence_refs``,
``developmental_decision``, ``domain_model_ref`` — and cites the justifying
EvidenceRecorded / provisional-evidence ids through ``caused_by:``
provenance-chain entries (E9 invariant: developmental records retain
provenance to the evidence that justified them).

Fail-closed rules (frozen edge E9, ENV-I2/I4):

- canonical identity only: a structural 64-hex lowercase sha256 digest; the
  standalone fallback pseudo-hash (sha256("agentic_capability_loop")) and the
  all-zero digest are refused;
- provenance value shapes are validated, not just presence: empty lists,
  blank strings, whitespace-only strings, and placeholder tokens are
  degenerate values and REFUSED before any envelope exists;
- at least one well-formed ``caused_by:`` parent id is REQUIRED.

This module is STATELESS projection only. Whether a decision is SUBSTANTIVELY
earned (in particular I9 capability promotion) is enforced by the durable
memory gate in :mod:`godspeed_nav.developmental_memory`, which is the single
authority seam for what enters durable developmental history.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from godspeed_nav.canonical_events import (
    NAMESPACE,
    SCHEMA_VERSION,
    idempotency_key,
    verify_domain_model_hash,
)
from godspeed_nav.schemas import DomainRuleError

#: Wire stamp of the exclusive authoritative producer of all five E9 types.
PRODUCER = "godspeed-agent"

FALLBACK_PSEUDO_HASH = (
    "dc144cbd71a483431301ca1bf32e95c014af4edba8dbcc525f505310e30a107e"
)
ZERO_HASH = "0" * 64

#: The five frozen E9 event types, ALL owned exclusively by godspeed_agent.
DEVELOPMENTAL_EVENT_TYPES: tuple[str, ...] = (
    "SettlementRecorded",
    "CapabilityUpdated",
    "RepetitionPlanned",
    "LearningProposalCreated",
    "CoherenceBreakDetected",
)

#: The four common required payload fields of every E9 envelope.
COMMON_REQUIRED_FIELDS: tuple[str, ...] = (
    "work_request_id",
    "source_evidence_refs",
    "developmental_decision",
    "domain_model_ref",
)

#: Lifecycle states a CapabilityUpdated may PROMOTE to. Statuses below
#: metabolized keep their explicitly declared lower thresholds (frozen known
#: confound); they are preserved here rather than collapsed into one bar.
PROMOTION_TARGETS: tuple[str, ...] = ("active", "repeated", "metabolized")

#: Event-appropriate required payload fields per type (on top of the common four).
EVENT_PAYLOAD_REQUIREMENTS: dict[str, tuple[str, ...]] = {
    "SettlementRecorded": ("affordance_id", "settlement_ref", "settlement_status"),
    "CapabilityUpdated": ("capability_id", "target_lifecycle", "variation_evidence"),
    "RepetitionPlanned": ("affordance_id", "repetition_count"),
    "LearningProposalCreated": ("learning_proposal_id", "domain_area", "status"),
    "CoherenceBreakDetected": ("break_reason",),
}

_PLACEHOLDER_IDS = frozenset({"placeholder", "unknown", "none", "<missing>", "tbd"})


def _well_formed_event_id(value: str) -> bool:
    try:
        UUID(value)
        return True
    except (ValueError, AttributeError, TypeError):
        pass
    crockford = set("0123456789ABCDEFGHJKMNPQRSTVWXYZ")
    return len(value) == 26 and all(c in crockford for c in value)


def _is_degenerate_text(value: Any) -> bool:
    if not isinstance(value, str):
        return True
    trimmed = value.strip()
    return not trimmed or trimmed.lower() in _PLACEHOLDER_IDS


def check_identity_string(field_name: str, value: Any) -> str:
    """Return the trimmed value when it is a non-placeholder identity string."""
    if _is_degenerate_text(value):
        raise DomainRuleError(
            "degenerate_field_value",
            f"Developmental event rejected: '{field_name}' is missing, blank, "
            f"or a placeholder identity, got {value!r}.",
        )
    return str(value).strip()


def check_ref_list(field_name: str, value: Any) -> list[str]:
    """Validate a provenance reference LIST by VALUE SHAPE.

    Refuses: non-lists, EMPTY lists, blank/whitespace entries, placeholder
    tokens. This is the tooth that keeps stripped or degenerate provenance
    from ever entering canonical history.
    """
    if not isinstance(value, (list, tuple)) or not value:
        raise DomainRuleError(
            "provenance_stripped",
            f"Developmental event rejected: '{field_name}' must be a "
            f"non-empty list of evidence references, got {value!r}.",
        )
    refs: list[str] = []
    for item in value:
        if _is_degenerate_text(item):
            raise DomainRuleError(
                "provenance_stripped",
                f"Developmental event rejected: '{field_name}' carries a "
                f"stripped/degenerate reference {item!r}; developmental records "
                "cannot be detached from their justifying evidence.",
            )
        refs.append(str(item).strip())
    return refs


def check_developmental_decision(value: Any) -> dict[str, Any]:
    """The independent GSA decision itself: a non-empty string-keyed mapping."""
    if not isinstance(value, dict) or not value:
        raise DomainRuleError(
            "degenerate_developmental_decision",
            f"Developmental event rejected: 'developmental_decision' must be a "
            f"non-empty object carrying GSA's independent evaluation, got "
            f"{value!r}.",
        )
    for key in value:
        if not isinstance(key, str) or not key.strip():
            raise DomainRuleError(
                "degenerate_developmental_decision",
                "Developmental event rejected: 'developmental_decision' keys "
                f"must be non-empty strings, got {key!r}.",
            )
    return dict(value)


def validate_event_payload(event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the event-appropriate required extras for one E9 type."""
    projected = {
        key: value
        for key, value in (payload or {}).items()
        if key not in COMMON_REQUIRED_FIELDS
        and key not in ("domain_model_hash", "namespace")
    }
    for field_name in EVENT_PAYLOAD_REQUIREMENTS[event_type]:
        value = projected.get(field_name)
        if field_name == "repetition_count":
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise DomainRuleError(
                    "degenerate_field_value",
                    f"RepetitionPlanned rejected: 'repetition_count' must be a "
                    f"positive integer, got {value!r}.",
                )
        elif field_name == "variation_evidence":
            projected[field_name] = check_ref_list(field_name, value)
        elif field_name == "target_lifecycle":
            if value not in PROMOTION_TARGETS:
                raise DomainRuleError(
                    "invalid_promotion_target",
                    f"CapabilityUpdated rejected: 'target_lifecycle' must be "
                    f"one of {list(PROMOTION_TARGETS)}, got {value!r}. Retired "
                    "and brittle are degradation states, not promotion targets.",
                )
        else:
            projected[field_name] = check_identity_string(field_name, value)
    if "settlement_score" in projected:
        score = projected["settlement_score"]
        if (
            isinstance(score, bool)
            or not isinstance(score, (int, float))
            or not 0.0 <= float(score) <= 1.0
        ):
            raise DomainRuleError(
                "degenerate_field_value",
                f"{event_type} rejected: 'settlement_score' must be a number "
                f"in [0, 1], got {score!r}.",
            )
    return projected


def project_developmental_event(
    event_type: str,
    *,
    work_request_id: str,
    source_evidence_refs: list[str],
    developmental_decision: dict[str, Any],
    domain_model_hash: str,
    parent_evidence_ids: list[str],
    payload: dict[str, Any] | None = None,
    event_id: str | None = None,
    occurred_at: str | None = None,
) -> dict[str, Any]:
    """Project ONE explicit developmental decision into a canonical E9 envelope.

    All gates run BEFORE any envelope exists; a refused decision produces
    nothing. ``event_id``/``occurred_at`` may be injected for deterministic
    golden-fixture regeneration.
    """
    if event_type not in DEVELOPMENTAL_EVENT_TYPES:
        raise DomainRuleError(
            "wrong_event_type",
            f"E9 projection refused: {event_type!r} is not one of the five "
            f"developmental event types {list(DEVELOPMENTAL_EVENT_TYPES)}.",
        )
    resolved_hash = verify_domain_model_hash(domain_model_hash)
    work_request_id = check_identity_string("work_request_id", work_request_id)
    evidence_refs = check_ref_list("source_evidence_refs", source_evidence_refs)
    decision = check_developmental_decision(developmental_decision)

    parents = list(parent_evidence_ids or [])
    if not parents:
        raise DomainRuleError(
            "causality_missing",
            "E9 projection refused: no caused_by parent recorded. A "
            "developmental record MUST cite the EvidenceRecorded/provisional "
            "ids that justify it.",
        )
    for parent in parents:
        if not _well_formed_event_id(parent):
            raise DomainRuleError(
                "malformed_parent_reference",
                f"E9 projection refused: causal parent id {parent!r} is not a "
                "well-formed event id.",
            )

    extras = validate_event_payload(event_type, payload or {})
    full_payload: dict[str, Any] = {
        "domain_model_hash": resolved_hash,
        "namespace": NAMESPACE,
        "work_request_id": work_request_id,
        "source_evidence_refs": evidence_refs,
        "developmental_decision": decision,
        "domain_model_ref": {"namespace": NAMESPACE, "model_hash": resolved_hash},
        **extras,
    }
    chain = [f"domain_model_hash:{resolved_hash}"]
    chain.extend(f"caused_by:{parent}" for parent in parents)
    return {
        "schema_version": SCHEMA_VERSION,
        "event_id": event_id or str(uuid4()),
        "source_agent": PRODUCER,
        "event_type": event_type,
        "occurred_at": occurred_at or datetime.now(UTC).isoformat(),
        "idempotency_key": idempotency_key(
            event_type, full_payload, correlation_id=work_request_id
        ),
        "payload": full_payload,
        "provenance": {"origin": PRODUCER, "chain": chain},
    }
