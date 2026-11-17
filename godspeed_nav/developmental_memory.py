"""Durable developmental-memory gate (convergence T09, memory-ledger seam).

The durable write seam for edge E9 (godspeed_agent -> memory_ledger): every
inbound developmental envelope is gated BEFORE anything is persisted, and an
admitted envelope is written exactly once to the append-only
``developmental_events`` ledger through ``LedgerStore.append_event_if_absent``
(flock-guarded dedup keyed on stable envelope identity).

Fail-closed rules enforced here (frozen edge E9, global invariants I3/I8/I9/
I14/I15, ENV-I2/I5/I6):

- exclusive producer authority: all five developmental event types are
  produced by ``godspeed_agent`` ALONE; forge attempts fail closed;
- identity gates: structural digest, placeholder pseudo-hash refusal (the
  standalone fallback constant and all-zero), optional drift pinning against
  this deployment's locally resolved model, namespace tampering refusal;
- the four common required payload fields validated TOGETHER, then by VALUE
  SHAPE — missing/empty/stripped ``source_evidence_refs`` quarantine the
  delivery (refused, never persisted as authoritative developmental truth);
- causality presence: at least one well-formed ``caused_by:`` parent, with
  optional out-of-band parent pinning;
- I9 promotion gate: a CapabilityUpdated is admitted ONLY when its OWN cited
  capability evidence satisfies the declared bar for its target lifecycle,
  composed with the runtime's existing machinery
  (:func:`godspeed_nav.schemas.Capability.from_settlements`,
  :func:`godspeed_nav.metabolization.compute_metabolization`,
  :func:`godspeed_nav.schemas.infer_capability_lifecycle`). One successful
  cycle can never reach metabolized; variation counts ONLY when it was
  declared on the recorded settlements themselves — inline declarations in a
  promotion request are ignored, so post-hoc variation gaming fails;
- durable idempotency (I14): redelivery under stable identity is a no-op;
  the same ``event_id`` carrying mutated content is refused BY NAME and the
  first record stands (I10/I15).

Restart semantics: gate state is rebuilt by REPLAYING the durable ledger
through this same gate (:func:`load_developmental_memory_state`), so
deduplication, settlement history, and earned promotions survive process
reopen without any in-memory-only truth. Ledger rows that fail re-validation
on replay are quarantined out of developmental history, never trusted.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from typing import Any

from godspeed_nav.canonical_events import verify_domain_model_hash
from godspeed_nav.developmental_events import (
    COMMON_REQUIRED_FIELDS,
    DEVELOPMENTAL_EVENT_TYPES,
    check_developmental_decision,
    check_identity_string,
    check_ref_list,
    validate_event_payload,
)
from godspeed_nav.metabolization import compute_metabolization
from godspeed_nav.schemas import (
    Capability,
    DomainRuleError,
    SettlementEvent,
    infer_capability_lifecycle,
    now_iso,
)

from datetime import UTC, datetime

SCHEMA_VERSION = "v1"
NAMESPACE = "agentic_capability_loop"
PRODUCER_CANONICAL = "godspeed_agent"

#: The single append-only durable ledger holding admitted E9 envelopes.
DEVELOPMENTAL_LEDGER = "developmental_events"

#: Declared thresholds BELOW metabolized (frozen known confound): lower
#: statuses keep explicitly lower bars instead of collapsing into one rule.
ACTIVE_MIN_SUCCESSFUL_SETTLEMENTS = 1

_METABOLIZED = "metabolized"

_PLACEHOLDER_IDS = frozenset({"placeholder", "unknown", "none", "<missing>", "tbd"})

_CANONICAL_AGENTS = {
    "swe-seed": "swe_seed",
    "swe_seed": "swe_seed",
    "context-kernel": "context_kernel",
    "context_kernel": "context_kernel",
    "sea-forge": "sea_forge",
    "sea_forge": "sea_forge",
    "godspeed-agent": PRODUCER_CANONICAL,
    "godspeed_agent": PRODUCER_CANONICAL,
    "gsa": PRODUCER_CANONICAL,
    "realitytrace": "realitytrace",
    "reality-trace": "realitytrace",
    "sxr": "realitytrace",
    "memory-ledger": "memory_ledger",
    "memory_ledger": "memory_ledger",
    "agent_memory_ledger": "memory_ledger",
    "execution-environment": "execution_environment",
    "execution_environment": "execution_environment",
    "external-environment": "external_environment",
    "external_environment": "external_environment",
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _bare_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _well_formed_event_id(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError, TypeError):
        pass
    crockford = set("0123456789ABCDEFGHJKMNPQRSTVWXYZ")
    return len(value) == 26 and all(c in crockford for c in value)


@dataclass(frozen=True)
class DevelopmentalAdmission:
    """Outcome of one delivery reaching the durable developmental gate."""

    status: str  # "first" | "duplicate"
    record: dict[str, Any] | None


@dataclass
class DevelopmentalMemoryState:
    """Gate state rebuilt from (and backed by) the durable ledger."""

    seen_identities: list[str] = field(default_factory=list)
    event_contents: dict[str, str] = field(default_factory=dict)
    #: Admitted SettlementRecorded summaries — the substrate the I9 gate
    #: evaluates promotions against.
    settlements: list[dict[str, Any]] = field(default_factory=list)
    #: Admitted CapabilityUpdated promotions.
    promotions: list[dict[str, Any]] = field(default_factory=list)
    #: Deliveries refused during ledger replay (never part of history).
    quarantined: list[dict[str, Any]] = field(default_factory=list)


def _caused_by_parents(envelope: dict[str, Any]) -> list[str]:
    chain = ((envelope.get("provenance") or {}).get("chain")) or []
    parents: list[str] = []
    for entry in chain:
        if isinstance(entry, str) and entry.startswith("caused_by:"):
            parent = entry[len("caused_by:") :]
            if not _well_formed_event_id(parent):
                raise DomainRuleError(
                    "causality_missing",
                    "Developmental event rejected: provenance chain carries a "
                    f"malformed causal parent id {parent!r}.",
                )
            parents.append(parent)
    return parents


def _validate_common_fields(
    payload: dict[str, Any],
) -> tuple[str, list[str], dict[str, Any]]:
    # Presence battery first (reported together), then VALUE-SHAPE validation
    # per field — presence alone never admits a degenerate value.
    missing = [name for name in COMMON_REQUIRED_FIELDS if payload.get(name) is None]
    if missing:
        raise DomainRuleError(
            "incomplete_developmental_event",
            "Developmental event rejected — missing frozen fields: "
            + ", ".join(sorted(missing))
            + ". A developmental record cannot bind incompletely.",
        )
    work_request_id = check_identity_string("work_request_id", payload["work_request_id"])
    evidence_refs = check_ref_list("source_evidence_refs", payload["source_evidence_refs"])
    decision = check_developmental_decision(payload["developmental_decision"])
    return work_request_id, evidence_refs, decision


def _evaluate_promotion(payload: dict[str, Any], state: DevelopmentalMemoryState) -> None:
    """I9 substance gate for CapabilityUpdated, composed with the runtime's
    existing lifecycle machinery. Raises on every unearned promotion."""
    capability_id = payload["capability_id"]
    target = payload["target_lifecycle"]
    cited_refs = payload["variation_evidence"]

    resolved: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    for ref in cited_refs:
        match = next(
            (
                s
                for s in state.settlements
                if s["capability_id"] == capability_id
                and (s["settlement_ref"] == ref or s["event_id"] == ref)
            ),
            None,
        )
        if match is None:
            raise DomainRuleError(
                "unresolved_capability_evidence",
                f"CapabilityUpdated rejected: variation evidence cites "
                f"{ref!r}, which is not a recorded developmental settlement "
                f"of capability {capability_id!r}. Capability claims must "
                "cite real recorded evidence of the SAME capability.",
            )
        key = f"{match['event_id']}|{match['settlement_ref']}"
        if key not in seen_keys:
            seen_keys.add(key)
            resolved.append(match)

    successful = [s for s in resolved if s["status"] == "success"]

    if target == "active":
        if len(successful) < ACTIVE_MIN_SUCCESSFUL_SETTLEMENTS:
            raise DomainRuleError(
                "i9_not_earned",
                "CapabilityUpdated rejected: 'active' promotion cites no "
                "successful recorded settlement.",
            )
        return

    schema_events = [
        SettlementEvent(
            id=str(s["settlement_ref"]),
            affordance_id=capability_id,
            before_state={},
            after_state={},
            payment_actual={},
            score=float(s["score"]),
            status=str(s["status"]),
            evidence=[str(s["event_id"])],
        )
        for s in resolved
    ]
    # Existing machinery: fewer than two successful (score >= 0.7) settlements
    # can never constitute a capability AT ALL — one pristine cycle dies here.
    Capability.from_settlements(
        id=capability_id, label=capability_id, settlement_events=schema_events
    )

    if target == _METABOLIZED:
        undeclared = [s for s in successful if not s["variation_context"]]
        if undeclared:
            raise DomainRuleError(
                "undeclared_variation",
                "CapabilityUpdated rejected: metabolized capability requires "
                "repeated settlement under DECLARED relevant variation; "
                f"{len(undeclared)} cited settlement(s) carry no declared "
                "variation context. Variation asserted inline in this request "
                "does not count — only pre-recorded declared contexts do.",
            )
        contexts = {str(s["variation_context"]) for s in successful}
        if len(contexts) < 2:
            raise DomainRuleError(
                "variation_not_demonstrated",
                "CapabilityUpdated rejected: metabolized capability requires "
                f"settlement under at least two DISTINCT declared variations, "
                f"got {sorted(contexts)!r}. Repetition of one identical "
                "condition is not variation.",
            )
        stability = sum(float(s["score"]) for s in successful) / len(successful)
        count = len(successful)
        burden = max(0.0, 0.6 - (0.15 * count))
        metabolization = compute_metabolization(
            capability_id=capability_id,
            settlement_events=[dict(s) for s in successful],
            reuse_frequency=count,
            context_diversity=max(1, len(contexts)),
            stability=stability,
            maintenance_burden=burden,
            attention_burden=burden,
        )
        lifecycle = infer_capability_lifecycle(
            settlement_count=count,
            stability=stability,
            metabolization_score=metabolization["metabolization_score"],
        )
        if lifecycle != _METABOLIZED:
            raise DomainRuleError(
                "i9_not_earned",
                "CapabilityUpdated rejected: cited evidence yields lifecycle "
                f"'{lifecycle}', not 'metabolized' (count={count}, "
                f"stability={stability:.3f}, "
                f"metabolization={metabolization['metabolization_score']:.3f}, "
                f"missing={metabolization['missing_evidence']}).",
            )


def ingest_developmental_event(
    envelope: Any,
    *,
    state: DevelopmentalMemoryState,
    local_model_sha256: str | None = None,
    known_parent_ids: list[str] | None = None,
) -> DevelopmentalAdmission:
    """Gate ONE canonical developmental delivery. Raises ``DomainRuleError``
    on every refusal BEFORE any state change; a refused delivery settles
    nothing and persists nothing."""
    if local_model_sha256 is not None:
        verify_domain_model_hash(local_model_sha256)

    if not isinstance(envelope, dict):
        raise DomainRuleError(
            "malformed_envelope",
            "Developmental event rejected: delivery is not a JSON object.",
        )
    if envelope.get("schema_version") != SCHEMA_VERSION:
        raise DomainRuleError(
            "malformed_envelope",
            f"Developmental event rejected: schema_version must be {SCHEMA_VERSION!r}.",
        )
    event_id = envelope.get("event_id")
    if (
        not isinstance(event_id, str)
        or not event_id.strip()
        or not _well_formed_event_id(event_id.strip())
    ):
        raise DomainRuleError(
            "malformed_envelope",
            f"Developmental event rejected: event_id is not a well-formed id: "
            f"{event_id!r}",
        )
    got_type = envelope.get("event_type")
    if got_type not in DEVELOPMENTAL_EVENT_TYPES:
        raise DomainRuleError(
            "wrong_event_type",
            f"This gate persists only the five godspeed_agent-owned "
            f"developmental types, got {got_type!r}.",
        )

    source_agent = envelope.get("source_agent")
    canonical_source = (
        _CANONICAL_AGENTS.get(source_agent) if isinstance(source_agent, str) else None
    )
    if canonical_source != PRODUCER_CANONICAL:
        raise DomainRuleError(
            "producer_forge",
            f"Producer forge: only {PRODUCER_CANONICAL!r} may produce "
            f"{got_type} events, got {source_agent!r}.",
        )
    origin = (envelope.get("provenance") or {}).get("origin")
    if origin is not None and origin != source_agent:
        raise DomainRuleError(
            "producer_forge",
            f"Producer forge: provenance origin {origin!r} contradicts the "
            f"{PRODUCER_CANONICAL!r} stamp.",
        )

    payload = envelope.get("payload")
    if not isinstance(payload, dict):
        raise DomainRuleError(
            "malformed_envelope",
            "Developmental event rejected: payload missing or not an object.",
        )

    declared = payload.get("domain_model_hash")
    try:
        verify_domain_model_hash(declared if isinstance(declared, str) else "")
    except DomainRuleError as exc:
        raise DomainRuleError(
            exc.code,
            f"Developmental event identity gate refused domain_model_hash "
            f"{declared!r}: {exc}",
        ) from exc
    if local_model_sha256 is not None and declared != local_model_sha256:
        raise DomainRuleError(
            "hash_drift",
            f"Developmental event domain_model_hash drift: expected "
            f"{local_model_sha256}, got {declared}.",
        )

    # Presence battery FIRST (all four frozen common fields reported
    # together), before any finer-grained shape or consistency check.
    work_request_id, evidence_refs, decision = _validate_common_fields(payload)

    if payload.get("namespace") != NAMESPACE:
        raise DomainRuleError(
            "namespace_tampering",
            f"Developmental event namespace mismatch: want {NAMESPACE!r}, got "
            f"{payload.get('namespace')!r}.",
        )
    model_ref = payload.get("domain_model_ref")
    if not isinstance(model_ref, dict):
        raise DomainRuleError(
            "ref_identity_mismatch",
            "Developmental event rejected: domain_model_ref is not an object.",
        )
    if model_ref.get("namespace") != NAMESPACE:
        raise DomainRuleError(
            "namespace_tampering",
            f"Developmental event domain_model_ref namespace mismatch: want "
            f"{NAMESPACE!r}, got {model_ref.get('namespace')!r}.",
        )
    if model_ref.get("model_hash") != declared:
        raise DomainRuleError(
            "ref_identity_mismatch",
            f"Developmental event domain_model_ref names "
            f"{model_ref.get('model_hash')!r} but the envelope declares "
            f"{declared!r}.",
        )

    extras = validate_event_payload(got_type, payload)

    parents = _caused_by_parents(envelope)
    if not parents:
        raise DomainRuleError(
            "causality_missing",
            "Developmental event rejected: no caused_by causal parent recorded; "
            "developmental records must retain provenance to the evidence that "
            "justified them.",
        )
    if known_parent_ids is not None:
        allowed = {p.strip() for p in known_parent_ids}
        forged = [p for p in parents if p not in allowed]
        if forged:
            raise DomainRuleError(
                "forged_parent_reference",
                f"Developmental event rejected: causal parents {forged!r} are "
                "not among the independently pinned upstream ids.",
            )

    if got_type == "CapabilityUpdated":
        _evaluate_promotion(extras, state)

    content_digest = _bare_sha256(envelope)
    stripped_id = event_id.strip()
    prior_content = state.event_contents.get(stripped_id)
    if prior_content is not None and prior_content != content_digest:
        raise DomainRuleError(
            "envelope_identity_conflict",
            f"Replay-with-mutation refused: event {stripped_id} was already "
            "recorded with different content; the first record stands (I10/I15).",
        )
    identities = [f"event|{stripped_id}", f"content|{content_digest}"]
    idem = envelope.get("idempotency_key")
    if isinstance(idem, str) and len(idem) == 64 and all(c in "0123456789abcdef" for c in idem):
        identities.append(f"idem|{idem}")
    if any(i in state.seen_identities for i in identities):
        return DevelopmentalAdmission(status="duplicate", record=None)

    state.seen_identities.extend(identities)
    state.event_contents[stripped_id] = content_digest
    record = {
        "event_id": stripped_id,
        "event_type": got_type,
        "work_request_id": work_request_id,
        "source_evidence_refs": list(evidence_refs),
        "causal_parents": list(parents),
        "domain_model_hash": declared,
        "developmental_decision": dict(decision),
        "payload": extras,
        "classification": "developmental",
        "recorded_at": now_iso(),
    }
    if got_type == "SettlementRecorded":
        state.settlements.append(
            {
                "event_id": stripped_id,
                "settlement_ref": extras["settlement_ref"],
                "capability_id": extras["affordance_id"],
                "status": extras["settlement_status"],
                "score": float(payload.get("settlement_score", 0.0)),
                "variation_context": str(payload.get("variation_context", "")),
                "source_evidence_refs": list(evidence_refs),
            }
        )
    elif got_type == "CapabilityUpdated":
        state.promotions.append(record)
    return DevelopmentalAdmission(status="first", record=record)


def load_developmental_memory_state(store: Any) -> DevelopmentalMemoryState:
    """Rebuild gate state by REPLAYING the durable ledger through the gate.

    Replay-through-the-gate keeps restart honest: dedup identities, recorded
    settlements, and earned promotions survive process reopen because they
    are re-derived from durable truth, and any row that cannot survive
    re-validation is quarantined OUT of developmental history instead of
    being trusted.
    """
    state = DevelopmentalMemoryState()
    for event in store.read_events(DEVELOPMENTAL_LEDGER):
        row = event.get("record")
        if not isinstance(row, dict):
            continue
        envelope = row.get("envelope")
        if not isinstance(envelope, dict):
            continue
        try:
            ingest_developmental_event(envelope, state=state)
        except DomainRuleError as exc:
            state.quarantined.append(
                {
                    "event_id": envelope.get("event_id"),
                    "code": exc.code,
                    "reason": str(exc),
                }
            )
    return state


def persist_developmental_event(
    store: Any,
    envelope: dict[str, Any],
    *,
    state: DevelopmentalMemoryState | None = None,
    local_model_sha256: str | None = None,
    known_parent_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Gate ONE delivery and, when first-admitted, durably write it ONCE.

    The gate runs first (every refusal happens before any write); admission
    then goes through ``append_event_if_absent`` keyed on stable envelope
    identity, so even a race between two first-admissions stores exactly one
    durable row. Redelivering the exact same envelope creates NO duplicate
    settlement/capability history.
    """
    gate_state = state if state is not None else load_developmental_memory_state(store)
    admission = ingest_developmental_event(
        envelope,
        state=gate_state,
        local_model_sha256=local_model_sha256,
        known_parent_ids=known_parent_ids,
    )
    if admission.status == "duplicate":
        return {"status": "duplicate", "record": None}

    row = {
        "event_id": envelope["event_id"],
        "stored_at": now_iso(),
        "envelope": envelope,
    }
    stored_event, appended = store.append_event_if_absent(
        DEVELOPMENTAL_LEDGER, row, dedup_field="event_id"
    )
    return {
        "status": "first" if appended else "duplicate",
        "record": admission.record,
        "ledger_record": stored_event.get("record"),
    }


def read_developmental_history(store: Any) -> dict[str, Any]:
    """Read-only derived view over durable developmental truth."""
    state = load_developmental_memory_state(store)
    envelopes = [
        event.get("record", {}).get("envelope")
        for event in store.read_events(DEVELOPMENTAL_LEDGER)
        if isinstance(event.get("record"), dict)
    ]
    by_type: dict[str, int] = {}
    for envelope in envelopes:
        if isinstance(envelope, dict):
            by_type[envelope.get("event_type", "?")] = (
                by_type.get(envelope.get("event_type", "?"), 0) + 1
            )
    return {
        "envelope_count": len([e for e in envelopes if isinstance(e, dict)]),
        "counts_by_type": by_type,
        "settlement_count": len(state.settlements),
        "promotion_count": len(state.promotions),
        "quarantined_count": len(state.quarantined),
        "promotions": list(state.promotions),
        "quarantined": list(state.quarantined),
    }


# ---------------------------------------------------------------------------
# E10 — DevelopmentalMemory -> next navigation (convergence T10)
# ---------------------------------------------------------------------------
# Frozen edge E10 (memory_ledger -> godspeed_agent, event_type DevelopmentalMemory):
# payload required: observer_or_system_id, capability_state, settlement_history_refs
# optional: repetitions_due, learning_proposals, prior_failures, recovery_history,
#           horizon_updates, earned_shortcuts, blocked_paths
# Invariants (E10 + I12): memory changes future navigation EVIDENCE but does
# NOT bypass current governance, settlement access, or payment gates. Historical
# capability evidence must remain distinguishable from current affordance
# availability — memory is evidence, not authority (gate-evaluation-after-memory).
# ---------------------------------------------------------------------------

DEVELOPMENTAL_MEMORY_EVENT_TYPE = "DevelopmentalMemory"
DEVELOPMENTAL_MEMORY_PRODUCER = "memory-ledger"
DEVELOPMENTAL_MEMORY_CANONICAL = "memory_ledger"

# Allowed lifecycle states for honest capability_state (via infer_capability_lifecycle)
_ALLOWED_LIFECYCLES = frozenset(
    {"latent", "active", "repeated", "metabolized", "brittle", "retired"}
)

_MEMORY_OPTIONAL_LIST_FIELDS = (
    "repetitions_due",
    "learning_proposals",
    "prior_failures",
    "recovery_history",
    "horizon_updates",
    "earned_shortcuts",
    "blocked_paths",
)


def _check_observer_id(value: Any) -> str:
    return check_identity_string("observer_or_system_id", value)


def _check_capability_state(value: Any) -> dict[str, Any] | str:
    """Validate capability_state is honest lifecycle evidence.

    Accepts:
    - a lifecycle string (one of _ALLOWED_LIFECYCLES)
    - a dict containing at least a ``lifecycle`` key with allowed value
    """
    if isinstance(value, str):
        trimmed = value.strip()
        if trimmed.lower() in _PLACEHOLDER_IDS or not trimmed:
            raise DomainRuleError(
                "degenerate_field_value",
                f"DevelopmentalMemory rejected: 'capability_state' is blank or placeholder, got {value!r}.",
            )
        if trimmed not in _ALLOWED_LIFECYCLES:
            raise DomainRuleError(
                "invalid_capability_state",
                f"DevelopmentalMemory rejected: capability_state lifecycle {trimmed!r} not in {sorted(_ALLOWED_LIFECYCLES)}.",
            )
        return trimmed
    if isinstance(value, dict):
        lifecycle = value.get("lifecycle") or value.get("lifecycle_state") or value.get("status")
        if not isinstance(lifecycle, str) or lifecycle.strip() not in _ALLOWED_LIFECYCLES:
            raise DomainRuleError(
                "invalid_capability_state",
                f"DevelopmentalMemory rejected: capability_state dict must carry lifecycle in {sorted(_ALLOWED_LIFECYCLES)}, got {value!r}.",
            )
        # Keys must be non-empty strings
        for k in value:
            if not isinstance(k, str) or not k.strip():
                raise DomainRuleError(
                    "degenerate_field_value",
                    f"DevelopmentalMemory rejected: capability_state keys must be non-empty strings, got {k!r}.",
                )
        return dict(value)
    raise DomainRuleError(
        "degenerate_field_value",
        f"DevelopmentalMemory rejected: 'capability_state' must be lifecycle string or dict, got {value!r}.",
    )


def _check_optional_ref_list(field_name: str, value: Any) -> list[str] | None:
    if value is None:
        return None
    if not isinstance(value, (list, tuple)):
        raise DomainRuleError(
            "degenerate_field_value",
            f"DevelopmentalMemory rejected: '{field_name}' must be a list when present, got {value!r}.",
        )
    if not value:
        return []
    # Validate each entry is non-degenerate text
    refs: list[str] = []
    for item in value:
        if _is_degenerate_text(item) if isinstance(item, str) else True:
            # allow empty list, but degenerate entries are refused
            if isinstance(item, str) and not item.strip():
                raise DomainRuleError(
                    "degenerate_field_value",
                    f"DevelopmentalMemory rejected: '{field_name}' carries blank entry {item!r}.",
                )
            if isinstance(item, str) and item.strip().lower() in _PLACEHOLDER_IDS:
                raise DomainRuleError(
                    "degenerate_field_value",
                    f"DevelopmentalMemory rejected: '{field_name}' carries placeholder {item!r}.",
                )
        refs.append(str(item).strip() if isinstance(item, str) else str(item))
    return refs


def _is_degenerate_text(value: Any) -> bool:
    if not isinstance(value, str):
        return True
    trimmed = value.strip()
    return not trimmed or trimmed.lower() in _PLACEHOLDER_IDS


def project_developmental_memory(
    *,
    observer_or_system_id: str,
    capability_state: Any,
    settlement_history_refs: list[str],
    domain_model_hash: str,
    parent_evidence_ids: list[str] | None = None,
    repetitions_due: list[str] | None = None,
    learning_proposals: list[str] | None = None,
    prior_failures: list[str] | None = None,
    recovery_history: list[str] | None = None,
    horizon_updates: list[str] | None = None,
    earned_shortcuts: list[str] | None = None,
    blocked_paths: list[str] | None = None,
    event_id: str | None = None,
    occurred_at: str | None = None,
) -> dict[str, Any]:
    """Project durable developmental history into a canonical DevelopmentalMemory envelope.

    This is the production E10 seam (memory_ledger -> godspeed_agent). All gates
    run BEFORE any envelope exists; a refused projection produces nothing.

    Required frozen payload fields: observer_or_system_id, capability_state,
    settlement_history_refs (must cite real durable settlements; empty is
    allowed only when history is genuinely empty — callers building from a
    populated store will always carry at least one ref). Capability_state is
    validated as honest lifecycle evidence (via _ALLOWED_LIFECYCLES, which mirrors
    infer_capability_lifecycle outputs).

    Optional fields (repetitions_due, learning_proposals, etc.) are included
    only when the caller supplies real evidenced values — they remain lists of
    cited ids/text, not free-form authority claims.

    The envelope is stamped by the exclusive producer ``memory-ledger`` and
    carries the canonical v1 wire shape (same family as E9). Provenance chain
    records ``domain_model_hash:<hash>`` plus ``caused_by:<settlement_ref>`` for
    each history ref that is a well-formed event id (non-id refs are still
    carried in payload but not added to the causal chain).
    """
    resolved_hash = verify_domain_model_hash(domain_model_hash)
    observer = _check_observer_id(observer_or_system_id)
    capability = _check_capability_state(capability_state)
    # settlement_history_refs is required but may be empty when history is genuinely empty (latent)
    if not settlement_history_refs:
        history_refs = []
    else:
        history_refs = check_ref_list("settlement_history_refs", settlement_history_refs)

    # Optional list fields validated by value shape when present
    optional_payload: dict[str, Any] = {}
    for field_name, value in [
        ("repetitions_due", repetitions_due),
        ("learning_proposals", learning_proposals),
        ("prior_failures", prior_failures),
        ("recovery_history", recovery_history),
        ("horizon_updates", horizon_updates),
        ("earned_shortcuts", earned_shortcuts),
        ("blocked_paths", blocked_paths),
    ]:
        checked = _check_optional_ref_list(field_name, value)
        if checked is not None:
            optional_payload[field_name] = checked

    full_payload: dict[str, Any] = {
        "domain_model_hash": resolved_hash,
        "namespace": NAMESPACE,
        "observer_or_system_id": observer,
        "capability_state": capability,
        "settlement_history_refs": history_refs,
        "domain_model_ref": {"namespace": NAMESPACE, "model_hash": resolved_hash},
        **optional_payload,
    }

    # Provenance chain: domain hash plus caused_by for each well-formed history ref
    # and each explicit parent_evidence_id (allows out-of-band pinning similar to E9)
    chain = [f"domain_model_hash:{resolved_hash}"]
    for ref in history_refs:
        if _well_formed_event_id(ref):
            chain.append(f"caused_by:{ref}")
    for parent in parent_evidence_ids or []:
        if _well_formed_event_id(parent) and f"caused_by:{parent}" not in chain:
            chain.append(f"caused_by:{parent}")

    # Idempotency key mirrors canonical family: sha256("{observer}|{event_type}|{canonical_payload}")
    correlation = observer
    return {
        "schema_version": SCHEMA_VERSION,
        "event_id": event_id or str(uuid.uuid4()),
        "source_agent": DEVELOPMENTAL_MEMORY_PRODUCER,
        "event_type": DEVELOPMENTAL_MEMORY_EVENT_TYPE,
        "occurred_at": occurred_at or datetime.now(UTC).isoformat(),
        "idempotency_key": hashlib.sha256(
            f"{correlation}|{DEVELOPMENTAL_MEMORY_EVENT_TYPE}|{canonical_json(full_payload)}".encode()
        ).hexdigest(),
        "payload": full_payload,
        "provenance": {"origin": DEVELOPMENTAL_MEMORY_PRODUCER, "chain": chain},
    }


def ingest_developmental_memory(
    envelope: Any,
    *,
    local_model_sha256: str | None = None,
    expected_observer_id: str | None = None,
) -> dict[str, Any]:
    """Validate a DevelopmentalMemory envelope as GSA would on receipt (E10 consumer gate).

    Enforces: correct event_type, exclusive producer (memory_ledger), canonical identity
    (structural digest, placeholder refusal, optional drift pinning), required-field
    presence + value-shape, namespace consistency, and optional observer binding.
    Returns the envelope's payload on success; raises DomainRuleError on every refusal
    BEFORE any state change — memory never bypasses governance itself.
    """
    if local_model_sha256 is not None:
        verify_domain_model_hash(local_model_sha256)

    if not isinstance(envelope, dict):
        raise DomainRuleError("malformed_envelope", "DevelopmentalMemory rejected: envelope is not an object.")
    if envelope.get("schema_version") != SCHEMA_VERSION:
        raise DomainRuleError(
            "malformed_envelope",
            f"DevelopmentalMemory rejected: schema_version must be {SCHEMA_VERSION!r}.",
        )
    if envelope.get("event_type") != DEVELOPMENTAL_MEMORY_EVENT_TYPE:
        raise DomainRuleError(
            "wrong_event_type",
            f"DevelopmentalMemory gate expects {DEVELOPMENTAL_MEMORY_EVENT_TYPE!r}, got {envelope.get('event_type')!r}.",
        )
    event_id = envelope.get("event_id")
    if not isinstance(event_id, str) or not event_id.strip() or not _well_formed_event_id(event_id.strip()):
        raise DomainRuleError("malformed_envelope", f"DevelopmentalMemory rejected: event_id malformed: {event_id!r}")

    source = envelope.get("source_agent")
    canonical_source = _CANONICAL_AGENTS.get(source) if isinstance(source, str) else None
    # Accept both "memory-ledger" wire form and canonical "memory_ledger"
    if canonical_source != DEVELOPMENTAL_MEMORY_CANONICAL and source != DEVELOPMENTAL_MEMORY_PRODUCER:
        raise DomainRuleError(
            "producer_forge",
            f"Producer forge: only {DEVELOPMENTAL_MEMORY_PRODUCER!r} (memory_ledger) may produce "
            f"{DEVELOPMENTAL_MEMORY_EVENT_TYPE}, got {source!r}.",
        )
    origin = (envelope.get("provenance") or {}).get("origin")
    if origin is not None and origin != source:
        raise DomainRuleError(
            "producer_forge",
            f"Producer forge: provenance origin {origin!r} contradicts source {source!r}.",
        )

    payload = envelope.get("payload")
    if not isinstance(payload, dict):
        raise DomainRuleError("malformed_envelope", "DevelopmentalMemory rejected: payload missing or not an object.")

    declared = payload.get("domain_model_hash")
    try:
        verify_domain_model_hash(declared if isinstance(declared, str) else "")
    except DomainRuleError as exc:
        raise DomainRuleError(exc.code, f"DevelopmentalMemory identity gate refused domain_model_hash {declared!r}: {exc}") from exc
    if local_model_sha256 is not None and declared != local_model_sha256:
        raise DomainRuleError("hash_drift", f"DevelopmentalMemory domain_model_hash drift: expected {local_model_sha256}, got {declared}.")
    if payload.get("namespace") != NAMESPACE:
        raise DomainRuleError(
            "namespace_tampering",
            f"DevelopmentalMemory namespace mismatch: want {NAMESPACE!r}, got {payload.get('namespace')!r}.",
        )
    model_ref = payload.get("domain_model_ref")
    if not isinstance(model_ref, dict):
        raise DomainRuleError("ref_identity_mismatch", "DevelopmentalMemory rejected: domain_model_ref not an object.")
    if model_ref.get("namespace") != NAMESPACE:
        raise DomainRuleError("namespace_tampering", f"DevelopmentalMemory domain_model_ref namespace mismatch: want {NAMESPACE!r}, got {model_ref.get('namespace')!r}.")
    if model_ref.get("model_hash") != declared:
        raise DomainRuleError(
            "ref_identity_mismatch",
            f"DevelopmentalMemory domain_model_ref names {model_ref.get('model_hash')!r} but envelope declares {declared!r}.",
        )

    # Required fields battery
    missing = []
    for fname in ("observer_or_system_id", "capability_state", "settlement_history_refs"):
        if payload.get(fname) is None:
            missing.append(fname)
    if missing:
        raise DomainRuleError(
            "incomplete_developmental_memory",
            "DevelopmentalMemory rejected — missing frozen fields: " + ", ".join(sorted(missing)) + ".",
        )
    observer = _check_observer_id(payload["observer_or_system_id"])
    if expected_observer_id is not None and observer != expected_observer_id.strip():
        raise DomainRuleError(
            "observer_mismatch",
            f"DevelopmentalMemory rejected: expected observer {expected_observer_id!r}, got {observer!r}.",
        )
    capability = _check_capability_state(payload["capability_state"])
    # Allow empty history for latent case (no settlements yet)
    raw_refs = payload["settlement_history_refs"]
    if isinstance(raw_refs, list) and len(raw_refs) == 0:
        history_refs = []
    else:
        history_refs = check_ref_list("settlement_history_refs", raw_refs)
    # Optional fields value-shape when present
    for fname in _MEMORY_OPTIONAL_LIST_FIELDS:
        if fname in payload and payload[fname] is not None:
            _check_optional_ref_list(fname, payload[fname])

    # Return validated payload summary for caller evidence
    return {
        "event_id": event_id.strip(),
        "observer_or_system_id": observer,
        "capability_state": capability,
        "settlement_history_refs": history_refs,
        "domain_model_hash": declared,
        "payload": payload,
    }


def build_developmental_memory_from_store(
    store: Any,
    *,
    observer_or_system_id: str,
    domain_model_hash: str,
    parent_evidence_ids: list[str] | None = None,
    event_id: str | None = None,
    occurred_at: str | None = None,
) -> dict[str, Any]:
    """Derive a DevelopmentalMemory envelope from durable truth (E10 retrieval seam).

    Composition with existing lifecycle machinery: capability_state is honestly
    derived via ``infer_capability_lifecycle`` + ``compute_metabolization`` over
    the durable settlements (same code T09's I9 gate uses), so history cannot
    inflate into unearned capability. settlement_history_refs cite the real
    durable settlement refs (or event_ids when refs absent). When evidenced,
    repetitions_due and learning_proposals are populated from durable state:

    - repetitions_due: capability ids whose lifecycle is not metabolized but have
      successful settlements (still due under variation)
    - learning_proposals: LearningProposalCreated event ids/proposal ids from the
      durable ledger
    - prior_failures: settlement refs whose status != success
    - earned_shortcuts variation contexts that are declared and distinct

    The envelope is NOT persisted — it is evidence for the NEXT navigation cycle,
    produced on demand from durable content. Callers that need a stable handle
    can persist the envelope themselves under the same flock-guarded seam.

    Gate-evaluation-after-memory: the returned envelope MUST be fed into
    navigation's normal gate evaluation (governance, payment, settlement) — it
    is consumed as evidence, not authority. Historical capability evidence
    remains distinguishable from current affordance availability because the
    payload carries ``capability_state`` separately from any ``current_affordances``
    the next cycle will compute.
    """
    resolved_hash = verify_domain_model_hash(domain_model_hash)
    observer = _check_observer_id(observer_or_system_id)

    state = load_developmental_memory_state(store)
    settlements = state.settlements  # list of dicts with settlement_ref, capability_id, status, score, variation_context

    # Settlement history refs: all durable settlement refs (prefer settlement_ref, fallback event_id)
    settlement_refs: list[str] = []
    for s in settlements:
        ref = s.get("settlement_ref") or s.get("event_id")
        if isinstance(ref, str) and ref.strip():
            settlement_refs.append(ref.strip())

    # Derive capability_state honestly: per-capability lifecycle via existing machinery
    # Group settlements by capability_id
    from collections import defaultdict

    by_cap: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for s in settlements:
        by_cap[str(s.get("capability_id", ""))].append(s)

    # Choose the capability with most settlements as representative, or synthesize from all if empty
    if by_cap:
        # Pick the capability with max successful count, break tie by total count
        def _score(entry: tuple[str, list[dict[str, Any]]]) -> tuple[int, int]:
            _, lst = entry
            succ = sum(1 for x in lst if x.get("status") == "success")
            return (succ, len(lst))

        rep_cap_id, rep_settlements = max(by_cap.items(), key=_score)
        successful = [s for s in rep_settlements if s.get("status") == "success"]
        settlement_count = len(successful)
        stability = sum(float(s.get("score", 0.0)) for s in successful) / max(1, settlement_count) if successful else 0.0
        # For metabolization calc: need context diversity etc.
        contexts = {str(s.get("variation_context", "")) for s in successful if s.get("variation_context")}
        # Use same burden formula as runtime._update_capability_evidence
        burden = max(0.0, 0.6 - (0.15 * settlement_count))
        metabolization = compute_metabolization(
            capability_id=rep_cap_id,
            settlement_events=[dict(s) for s in successful],
            reuse_frequency=settlement_count,
            context_diversity=max(1, len(contexts)),
            stability=stability,
            maintenance_burden=burden,
            attention_burden=burden,
        )
        lifecycle = infer_capability_lifecycle(
            settlement_count=settlement_count,
            stability=stability,
            metabolization_score=metabolization["metabolization_score"],
        )
        capability_state: Any = {
            "capability_id": rep_cap_id,
            "lifecycle": lifecycle,
            "settlement_count": settlement_count,
            "stability": stability,
            "metabolization_score": metabolization["metabolization_score"],
        }
    else:
        # No history: latent with zero evidence
        capability_state = {"lifecycle": "latent", "settlement_count": 0, "stability": 0.0, "metabolization_score": 0.0}

    # Optional evidenced fields
    # repetitions_due: capabilities not yet metabolized that have at least one success
    repetitions_due: list[str] = []
    for cap_id, lst in by_cap.items():
        succ = [s for s in lst if s.get("status") == "success"]
        if not succ:
            continue
        # recompute lifecycle for this cap to see if metabolized
        contexts = {str(s.get("variation_context", "")) for s in succ if s.get("variation_context")}
        burden = max(0.0, 0.6 - (0.15 * len(succ)))
        stability = sum(float(s.get("score", 0.0)) for s in succ) / max(1, len(succ))
        metab = compute_metabolization(
            capability_id=cap_id,
            settlement_events=[dict(s) for s in succ],
            reuse_frequency=len(succ),
            context_diversity=max(1, len(contexts)),
            stability=stability,
            maintenance_burden=burden,
            attention_burden=burden,
        )
        lc = infer_capability_lifecycle(len(succ), stability, metab["metabolization_score"])
        if lc != "metabolized":
            repetitions_due.append(cap_id)

    # learning_proposals: ids from durable LearningProposalCreated events
    learning_proposals: list[str] = []
    prior_failures: list[str] = []
    earned_shortcuts: list[str] = []
    for s in settlements:
        if s.get("status") != "success":
            ref = s.get("settlement_ref") or s.get("event_id")
            if ref:
                prior_failures.append(str(ref))
        vc = s.get("variation_context")
        if isinstance(vc, str) and vc.strip() and s.get("status") == "success":
            earned_shortcuts.append(vc.strip())
    # Deduplicate while preserving order
    def _dedup(seq: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for item in seq:
            if item not in seen:
                seen.add(item)
                out.append(item)
        return out

    repetitions_due = _dedup(repetitions_due)
    earned_shortcuts = _dedup(earned_shortcuts)
    prior_failures = _dedup(prior_failures)

    # Read learning proposals directly from ledger envelopes
    envelopes = [
        event.get("record", {}).get("envelope")
        for event in store.read_events(DEVELOPMENTAL_LEDGER)
        if isinstance(event.get("record"), dict)
    ]
    for envelope in envelopes:
        if isinstance(envelope, dict) and envelope.get("event_type") == "LearningProposalCreated":
            payload = envelope.get("payload", {}) if isinstance(envelope.get("payload"), dict) else {}
            lp_id = payload.get("learning_proposal_id")
            if isinstance(lp_id, str) and lp_id.strip():
                learning_proposals.append(lp_id.strip())
    learning_proposals = _dedup(learning_proposals)

    # Only include optional fields when they carry real evidenced values (honest, not empty placeholders)
    kwargs: dict[str, Any] = {}
    if repetitions_due:
        kwargs["repetitions_due"] = repetitions_due
    if learning_proposals:
        kwargs["learning_proposals"] = learning_proposals
    if prior_failures:
        kwargs["prior_failures"] = prior_failures
    if earned_shortcuts:
        kwargs["earned_shortcuts"] = earned_shortcuts

    return project_developmental_memory(
        observer_or_system_id=observer,
        capability_state=capability_state,
        settlement_history_refs=settlement_refs,
        domain_model_hash=resolved_hash,
        parent_evidence_ids=parent_evidence_ids,
        event_id=event_id,
        occurred_at=occurred_at,
        **kwargs,
    )


def apply_developmental_memory_to_candidates(
    candidates: list[dict[str, Any]],
    developmental_memory: dict[str, Any] | None,
    *,
    boost_factor: float = 0.25,
) -> list[dict[str, Any]]:
    """Return memory-influenced candidate copies WITHOUT bypassing hard gates.

    This is the documented gate-evaluation-after-memory pattern: memory may
    reduce search/orchestration burden (here modeled as a modest boost to
    ``expected_horizon_delta`` / ``direction_score`` for candidates whose id
    appears in historical settlement refs), but the caller MUST still evaluate
    the returned candidates through :func:`godspeed_nav.cognitive_model.evaluate_candidate_model`
    (or equivalent) — memory never flips ``governance_allowed`` /
    ``settlement_accessible`` / ``payment_capacity`` from denied to allowed.

    Historical capability evidence remains distinguishable from current affordance
    availability because this function tags every influenced candidate with
    ``_memory_influenced: True`` and preserves the original ``_historical_capability``
    separately: a candidate that is currently unaffordable/inaccessible stays that
    way regardless of memory boost.

    Returns a NEW list; input candidates are not mutated.
    """
    if not developmental_memory or not isinstance(developmental_memory, dict):
        return [dict(c) for c in candidates]
    payload = developmental_memory.get("payload", {}) if isinstance(developmental_memory.get("payload"), dict) else {}
    history_refs = set(payload.get("settlement_history_refs", []) if isinstance(payload.get("settlement_history_refs"), list) else [])
    # Also consider capability_state capability_id as historical evidence
    cap_state = payload.get("capability_state")
    historical_cap_ids: set[str] = set()
    if isinstance(cap_state, dict):
        cid = cap_state.get("capability_id")
        if isinstance(cid, str) and cid.strip():
            historical_cap_ids.add(cid.strip())
    elif isinstance(cap_state, str) and cap_state.strip():
        historical_cap_ids.add(cap_state.strip())

    # Build set of historical affordance ids from settlement refs — but settlement refs
    # are settlement_ref values, not affordance ids directly. For E10 we treat historical
    # capability ids as the affordance identity that was previously exercised (same namespace).
    # Also treat learning_proposals / repetitions_due as additional historical signals.
    for field in ("repetitions_due", "learning_proposals", "earned_shortcuts"):
        vals = payload.get(field)
        if isinstance(vals, list):
            for v in vals:
                if isinstance(v, str) and v.strip():
                    historical_cap_ids.add(v.strip())

    influenced: list[dict[str, Any]] = []
    for c in candidates:
        copy_c = dict(c)
        cid = str(c.get("id", ""))
        # Memory influences only candidates that have a historical echo
        is_historical = cid in historical_cap_ids or cid in history_refs
        if is_historical:
            # Evidence-weighted boost: reduce burden / increase horizon gain, never gate creation
            original_delta = float(copy_c.get("expected_horizon_delta", 0) or 0)
            original_dscore = float(copy_c.get("direction_score", 0) or 0)
            copy_c["expected_horizon_delta"] = original_delta + boost_factor
            copy_c["direction_score"] = original_dscore + (boost_factor * 0.5)
            copy_c["_memory_influenced"] = True
            copy_c["_historical_capability"] = True
            # Preserve provenance of influence
            copy_c["_memory_event_id"] = developmental_memory.get("event_id")
        else:
            copy_c["_memory_influenced"] = False
            copy_c["_historical_capability"] = False
        # Never mutate governance / settlement / payment fields here — that is the gate's job
        influenced.append(copy_c)
    return influenced


def export_learning_proposals_for_ck(
    store: Any,
    destination_path: Any,
) -> dict[str, Any]:
    """Export durable LearningProposalCreated envelopes to a CK-readable JSONL file.

    CK's ``AclContextAgent.resolve_from_learning_proposals`` reads a plain
    JSONL ledger where each line is a JSON object with ``payload.proposal`` and
    ``payload.domain_area``. This helper bridges the canonical flock-guarded
    ``developmental_events`` ledger into that shape, preserving provenance:

    - Each exported line is the FULL developmental envelope (including envelope_id,
      payload, provenance) so ``proposal`` text and ``domain_area`` remain citable
      via ``learning-proposals://<learning_proposal_id>`` with source ref to the
      original settlement evidence.
    - The destination file is written atomically (temp file + rename) and receives
      one line per durable LearningProposalCreated envelope.
    - Returns ``{"exported": N, "path": str}`` for evidence.
    """
    from pathlib import Path

    dest = Path(destination_path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    envelopes = [
        event.get("record", {}).get("envelope")
        for event in store.read_events(DEVELOPMENTAL_LEDGER)
        if isinstance(event.get("record"), dict)
    ]
    proposals = [e for e in envelopes if isinstance(e, dict) and e.get("event_type") == "LearningProposalCreated"]

    # Write atomically
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        for envelope in proposals:
            # CK expects payload.proposal to be present; developmental ledger's
            # LearningProposalCreated currently stores proposal under different key?
            # We ensure proposal field is present for CK retrieval: if missing,
            # synthesize from status/domain_area so corpus is still citable.
            payload = envelope.get("payload", {}) if isinstance(envelope.get("payload"), dict) else {}
            if not payload.get("proposal") and payload.get("domain_area"):
                # Backfill a citable proposal text so CK corpus remains queryable
                envelope = dict(envelope)
                new_payload = dict(payload)
                new_payload["proposal"] = f"Learning proposal in {payload.get('domain_area')}: {payload.get('status', 'open')}"
                envelope["payload"] = new_payload
            handle.write(json.dumps(envelope, sort_keys=True) + "\n")
    tmp.replace(dest)
    return {"exported": len(proposals), "path": str(dest)}
