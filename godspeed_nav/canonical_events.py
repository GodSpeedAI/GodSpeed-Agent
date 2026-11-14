"""Canonical event projection for the GodSpeed convergence boundary (T03).

Projects GodSpeed-Agent's existing navigation outputs into the canonical
`GodSpeedSemanticEnvelope` wire family (schema_version ``v1``) shared with
SWE_SEED's federation module:

- E0: a DesiredDirection becomes a canonical ``DesiredDirection`` envelope
  stamped by its authoritative producer (``external_environment``).
- E1: a selected, executable affordance becomes a canonical ``WorkRequested``
  envelope stamped by its exclusive producer (``godspeed_agent``).

Fail-closed rules (frozen preregistration ENV-I1/I2, E0/E1):

- A destination-only input (no validated pathway / no payment estimate) can
  never be projected as a canonical WorkRequested event.
- Settlement criteria are required; an empty set is rejected rather than
  silently defaulted.
- Fallback/placeholder pseudo-identities (the standalone constant, all-zero)
  are refused as domain identity.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from godspeed_nav.schemas import DomainRuleError
from godspeed_nav.world_ref import verify_world_ref

SCHEMA_VERSION = "v1"
NAMESPACE = "agentic_capability_loop"

GODSPEED_AGENT = "godspeed-agent"
EXTERNAL_ENVIRONMENT = "external-environment"

# sha256("agentic_capability_loop") — the standalone fallback pseudo-hash the
# frozen contract forbids as canonical identity.
FALLBACK_PSEUDO_HASH = (
    "dc144cbd71a483431301ca1bf32e95c014af4edba8dbcc525f505310e30a107e"
)


def verify_domain_model_hash(domain_model_hash: str) -> str:
    """Return the digest when it is admissible canonical identity; else raise."""
    if len(domain_model_hash) != 64 or any(
        c not in "0123456789abcdef" for c in domain_model_hash
    ):
        raise DomainRuleError(
            "malformed_domain_identity",
            "domain_model_hash must be a 64-char lowercase sha256 digest",
        )
    if domain_model_hash == FALLBACK_PSEUDO_HASH or set(domain_model_hash) == {"0"}:
        raise DomainRuleError(
            "fallback_domain_hash_forbidden",
            "fallback/placeholder pseudo-hashes cannot masquerade as canonical "
            "domain identity",
        )
    return domain_model_hash


def _canonical_payload_json(payload: dict[str, Any]) -> str:
    def sorted_without_signature(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: sorted_without_signature(value[key])
                for key in sorted(value)
                if key != "signature"
            }
        if isinstance(value, list):
            return [sorted_without_signature(item) for item in value]
        return value

    return json.dumps(sorted_without_signature(payload), separators=(",", ":"))


def idempotency_key(
    event_type: str, payload: dict[str, Any], correlation_id: str | None = None
) -> str:
    content = f"{correlation_id or ''}|{event_type}|{_canonical_payload_json(payload)}"
    return hashlib.sha256(content.encode()).hexdigest()


def _envelope(
    event_type: str,
    source_agent: str,
    payload: dict[str, Any],
    domain_model_hash: str,
    world_ref: str,
    parent_event_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Build one canonical v1 envelope (wire-compatible with SWE_SEED).

    ``world_ref`` pins the semantic-world revision. It rides next to the legacy
    ``domain_model_hash`` and is never derived from it.
    """
    verify_domain_model_hash(domain_model_hash)
    full_payload: dict[str, Any] = {
        "domain_model_hash": verify_domain_model_hash(domain_model_hash),
        "world_ref": verify_world_ref(world_ref),
        "namespace": NAMESPACE,
    }
    full_payload.update(payload)
    chain = [f"domain_model_hash:{domain_model_hash}", f"world_ref:{world_ref}"]
    chain.extend(f"caused_by:{parent}" for parent in parent_event_ids or [])
    correlation = full_payload.get("work_request_id")
    return {
        "schema_version": SCHEMA_VERSION,
        "event_id": str(uuid.uuid4()),
        "source_agent": source_agent,
        "event_type": event_type,
        "occurred_at": datetime.now(UTC).isoformat(),
        "idempotency_key": idempotency_key(
            event_type,
            full_payload,
            correlation_id=correlation if isinstance(correlation, str) else None,
        ),
        "payload": full_payload,
        "provenance": {"origin": source_agent, "chain": chain},
    }


def project_desired_direction(
    direction: dict[str, Any], domain_model_hash: str, *, world_ref: str
) -> dict[str, Any]:
    """E0: project an operator direction into its canonical envelope.

    The direction itself is NOT executable; this event only carries it to
    GodSpeed-Agent's evaluation. Required frozen fields: ``direction_id``,
    ``direction_type``, ``desired_state``. Production authority is the
    external environment — never GodSpeed-Agent itself.
    """
    direction_id = direction.get("id") or ""
    direction_type = direction.get("kind") or ""
    desired_state = direction.get("statement") or ""
    if not (direction_id and direction_type and desired_state):
        raise DomainRuleError(
            "direction_incomplete",
            "DesiredDirection requires direction_id, direction_type, and "
            "desired_state.",
        )
    return _envelope(
        "DesiredDirection",
        EXTERNAL_ENVIRONMENT,
        {
            "direction_id": direction_id,
            "direction_type": direction_type,
            "desired_state": desired_state,
        },
        domain_model_hash=domain_model_hash,
        world_ref=world_ref,
    )


def project_work_requested(
    affordance: dict[str, Any],
    work_request_id: str,
    domain_model_hash: str,
    direction: dict[str, Any] | None = None,
    parent_direction_event_id: str | None = None,
    settlement_criteria: list[str] | None = None,
    *,
    world_ref: str,
) -> dict[str, Any]:
    """E1: project a SELECTED EXECUTABLE affordance into WorkRequested.

    Fail-closed against the frozen falsifier: a bare destination with no
    validated pathway, payment estimate, or settlement criteria can never be
    emitted as a canonical WorkRequested event. ``godspeed_agent`` is the
    exclusive authoritative producer of WorkRequested. The event is a request
    pinned to ``world_ref``; it carries no authority grant, which only
    SEA-Forge issues.
    """
    if not work_request_id:
        raise DomainRuleError(
            "work_request_id_required",
            "WorkRequested requires an explicit work_request_id correlation.",
        )

    pathway = affordance.get("pathway") or ""
    payment_estimate = affordance.get("payment_estimate")
    if not pathway or payment_estimate is None:
        raise DomainRuleError(
            "destination_only_not_spendable",
            f"Affordance '{affordance.get('id')}' has no validated pathway "
            "and/or payment estimate; a destination-only input cannot enter "
            "SWE_SEED as a canonical WorkRequested event.",
        )

    criteria = list(settlement_criteria or [])
    if not criteria:
        criteria = list((direction or {}).get("success_criteria") or [])
    if not criteria:
        raise DomainRuleError(
            "settlement_criteria_required",
            "WorkRequested requires observable settlement criteria; refusing "
            "to emit an ungrounded objective.",
        )

    affordance_id = affordance.get("id") or ""
    desired_outcome = affordance.get("statement") or ""
    if not (affordance_id and desired_outcome):
        raise DomainRuleError(
            "work_contract_incomplete",
            "WorkRequested requires both affordance_id and desired_outcome.",
        )

    parents = [parent_direction_event_id] if parent_direction_event_id else []
    return _envelope(
        "WorkRequested",
        GODSPEED_AGENT,
        {
            "work_request_id": work_request_id,
            "affordance_id": affordance_id,
            "desired_outcome": desired_outcome,
            "settlement_criteria": criteria,
        },
        domain_model_hash=domain_model_hash,
        world_ref=world_ref,
        parent_event_ids=parents,
    )
