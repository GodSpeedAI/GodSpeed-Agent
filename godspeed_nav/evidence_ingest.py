"""Canonical EvidenceRecorded ingestion gate (convergence plan T08).

Consumes the frozen E8 boundary (realitytrace -> godspeed_agent): GodSpeed-Agent
is the PROVISIONAL-ONLY consumer of EvidenceRecorded, never its producer. The
lawful promotion path remains an explicit, separate settlement action
(``NavigationRuntime.record_settlement``); nothing in this module can reach it.

Fail-closed rules mirrored from RealityTrace's own E8 emitter contract
(sxr-core ``evidence_emit``/``proof_ingest``, same v1 wire family):

- exclusive producer authority: only ``realitytrace`` may stamp
  EvidenceRecorded; forge attempts fail closed;
- canonical identity: structural sha256 digest, no placeholder pseudo-hash
  (the standalone fallback constant and the all-zero digest are refused),
  no drift against THIS deployment's locally resolved model;
- loop namespace on both the payload and ``domain_model_ref``;
- ALL NINE frozen required payload/envelope fields validated together;
- causality presence: at least one well-formed ``caused_by:`` parent; when the
  deployment pins upstream ids out-of-band (``known_parent_ids``), any chain
  citation outside that set is a forged-parent refusal;
- cryptographic comparison binding: ``difference.expected_sha256`` /
  ``difference.observed_sha256`` must recompute from the carried
  expected/observed values, so a mutated value cannot ride a stale difference
  (ENV-I10 probe detection);
- cross-wired work_request_id refusal against the tracked cycle;
- duplicate/replay idempotency under stable identity (event id, content
  digest, producer idempotency key), plus T07-style claim stability keyed by
  (work_request_id, proof_result_ref): a divergent resubmission of an
  already-recorded cycle is refused BY NAME and the first record stands.

Strictly provisional semantics: successful ingestion yields a
:class:`ProvisionalEvidence` value object — inert data with no promotion
method of any kind — and callers persisting it may only write the provisional
evidence ledger. No code path here creates SettlementRecorded,
CapabilityUpdated, or metabolized capability (frozen invariant I8).
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from typing import Any

from godspeed_nav.canonical_events import verify_domain_model_hash
from godspeed_nav.schemas import DomainRuleError
from godspeed_nav.world_ref import verify_world_ref

SCHEMA_VERSION = "v1"
NAMESPACE = "agentic_capability_loop"

#: The event type owned exclusively by ``realitytrace`` at edge E8.
EVENT_TYPE = "EvidenceRecorded"

#: The exclusive authoritative producer of EvidenceRecorded.
PRODUCER = "realitytrace"

#: The standalone fallback pseudo-hash: sha256("agentic_capability_loop").
FALLBACK_PSEUDO_HASH = (
    "dc144cbd71a483431301ca1bf32e95c014af4edba8dbcc525f505310e30a107e"
)

#: The all-zero digest, refused alongside the fallback pseudo-hash.
ZERO_HASH = "0" * 64

#: The frozen required fields of EvidenceRecorded (edge E8).
REQUIRED_FIELDS: tuple[str, ...] = (
    "event_id",
    "work_request_id",
    "affordance_id",
    "expected_outcome",
    "observed_outcome",
    "difference",
    "proof_result_ref",
    "operational_settlement_ref",
    "domain_model_ref",
)

_PLACEHOLDER_IDS = frozenset({"placeholder", "unknown", "none", "<missing>", "tbd"})

_CANONICAL_AGENTS = {
    "swe-seed": "swe_seed",
    "swe_seed": "swe_seed",
    "context-kernel": "context_kernel",
    "context_kernel": "context_kernel",
    "sea-forge": "sea_forge",
    "sea_forge": "sea_forge",
    "godspeed-agent": "godspeed_agent",
    "godspeed_agent": "godspeed_agent",
    "gsa": "godspeed_agent",
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
    """Sorted-key compact JSON — the same scheme sxr-core's emitter uses."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _bare_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _is_bare_digest(text: str) -> bool:
    return len(text) == 64 and all(c in "0123456789abcdef" for c in text)


def _is_sha256_ref(text: Any) -> bool:
    if not isinstance(text, str) or not text.startswith("sha256:"):
        return False
    return _is_bare_digest(text[len("sha256:") :])


def _well_formed_event_id(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError, TypeError):
        pass
    # ULID shape: 26 Crockford base32 characters.
    crockford = set("0123456789ABCDEFGHJKMNPQRSTVWXYZ")
    return len(value) == 26 and all(c in crockford for c in value)


def _check_identity_string(field_name: str, value: Any) -> str:
    if not isinstance(value, str):
        raise DomainRuleError(
            "incomplete_evidence_recorded",
            f"EvidenceRecorded rejected: required field '{field_name}' is "
            "missing or not a string.",
        )
    trimmed = value.strip()
    if not trimmed or trimmed.lower() in _PLACEHOLDER_IDS:
        raise DomainRuleError(
            "placeholder_field",
            f"EvidenceRecorded rejected: '{field_name}' is blank or a "
            "placeholder identity.",
        )
    return trimmed


def _validate_sha256_ref(field_name: str, value: Any) -> str:
    if not _is_sha256_ref(value):
        raise DomainRuleError(
            "invalid_ref",
            f"EvidenceRecorded rejected: '{field_name}' must be a "
            f"content-addressed sha256 reference, got {value!r}.",
        )
    return value


# --- Provisional value object ------------------------------------------------------


@dataclass(frozen=True)
class ProvisionalEvidence:
    """Inert, strictly-provisional developmental evidence (I8).

    Plain frozen data ONLY: this type deliberately exposes no promotion,
    settlement, capability, or emit method of any kind. Promotion remains an
    explicit, separate GodSpeed-Agent settlement action outside ingestion.
    """

    event_id: str
    work_request_id: str
    affordance_id: str
    expected_outcome: Any
    observed_outcome: Any
    difference: dict[str, Any]
    proof_result_ref: str
    operational_settlement_ref: str
    domain_model_hash: str
    verdict: str
    classification: str = "provisional"
    #: Semantic world the evidence declares, when the producer carried one.
    world_ref: str | None = None
    #: "bound" = declared world equals this deployment's pinned world;
    #: "unbound" = the producer carried no world_ref, so the evidence says
    #: nothing about which world it is relative to (unknown, never assumed).
    world_binding: str = "unbound"

    def to_ledger_record(self, created_at: str) -> dict[str, Any]:
        """Project into a plain JSON-safe ledger record (still provisional)."""
        return {
            "evidence_event_id": self.event_id,
            "work_request_id": self.work_request_id,
            "affordance_id": self.affordance_id,
            "expected_outcome": self.expected_outcome,
            "observed_outcome": self.observed_outcome,
            "difference": dict(self.difference),
            "proof_result_ref": self.proof_result_ref,
            "operational_settlement_ref": self.operational_settlement_ref,
            "domain_model_hash": self.domain_model_hash,
            "verdict": self.verdict,
            "classification": self.classification,
            "world_ref": self.world_ref,
            "world_binding": self.world_binding,
            "source_event_type": EVENT_TYPE,
            "source_producer": PRODUCER,
            "created_at": created_at,
        }


@dataclass(frozen=True)
class EvidenceAdmission:
    """Outcome of one delivery reaching the canonical evidence gate."""

    status: str  # "first" | "duplicate"
    record: ProvisionalEvidence | None


@dataclass
class EvidenceIngestState:
    """Explicitly threaded gate state (durability is the caller's concern)."""

    seen_identities: list[str] = field(default_factory=list)
    claims: list[dict[str, Any]] = field(default_factory=list)


def _caused_by_parents(envelope: dict[str, Any]) -> list[str]:
    chain = ((envelope.get("provenance") or {}).get("chain")) or []
    parents: list[str] = []
    for entry in chain:
        if isinstance(entry, str) and entry.startswith("caused_by:"):
            parent = entry[len("caused_by:") :]
            if not _well_formed_event_id(parent):
                raise DomainRuleError(
                    "causality_missing",
                    "EvidenceRecorded rejected: provenance chain carries a "
                    f"malformed causal parent id {parent!r}.",
                )
            parents.append(parent)
    return parents


def ingest_evidence_recorded(
    envelope: Any,
    *,
    local_model_sha256: str,
    expected_work_request_id: str,
    state: EvidenceIngestState,
    known_parent_ids: list[str] | None = None,
    local_world_ref: str | None = None,
) -> EvidenceAdmission:
    """Gate ONE canonical EvidenceRecorded delivery.

    Returns an :class:`EvidenceAdmission`; raises ``DomainRuleError`` on every
    refusal. Every refusal happens BEFORE any state change — a refused
    delivery settles nothing and records nothing.
    """
    verify_domain_model_hash(local_model_sha256)

    # 1. Structural wire shape.
    if not isinstance(envelope, dict):
        raise DomainRuleError(
            "malformed_envelope", "EvidenceRecorded rejected: delivery is not a JSON object."
        )
    if envelope.get("schema_version") != SCHEMA_VERSION:
        raise DomainRuleError(
            "malformed_envelope",
            f"EvidenceRecorded rejected: schema_version must be {SCHEMA_VERSION!r}.",
        )
    got_type = envelope.get("event_type")
    if got_type != EVENT_TYPE:
        raise DomainRuleError(
            "wrong_event_type",
            f"This gate ingests only {EVENT_TYPE} events, got {got_type!r}. "
            "SettlementRecorded/CapabilityUpdated are godspeed_agent's own "
            "outbound events and can never be ingested here.",
        )
    event_id = envelope.get("event_id")
    if (
        not isinstance(event_id, str)
        or not event_id.strip()
        or not _well_formed_event_id(event_id.strip())
    ):
        raise DomainRuleError(
            "malformed_envelope",
            f"EvidenceRecorded rejected: event_id is not a well-formed id: {event_id!r}",
        )

    # 2. Exclusive producer authority: realitytrace, nobody else.
    source_agent = envelope.get("source_agent")
    canonical_source = _CANONICAL_AGENTS.get(source_agent) if isinstance(source_agent, str) else None
    if canonical_source != PRODUCER:
        raise DomainRuleError(
            "producer_forge",
            f"Producer forge: only {PRODUCER!r} may produce EvidenceRecorded, "
            f"got {source_agent!r}.",
        )
    origin = (envelope.get("provenance") or {}).get("origin")
    if origin is not None and origin != source_agent:
        raise DomainRuleError(
            "producer_forge",
            f"Producer forge: provenance origin {origin!r} contradicts the "
            f"{PRODUCER!r} stamp.",
        )

    payload = envelope.get("payload")
    if not isinstance(payload, dict):
        raise DomainRuleError(
            "malformed_envelope", "EvidenceRecorded rejected: payload missing or not an object."
        )

    # 3. Canonical identity: structural, non-placeholder, no drift.
    declared = payload.get("domain_model_hash")
    try:
        verify_domain_model_hash(declared if isinstance(declared, str) else "")
    except DomainRuleError as exc:
        raise DomainRuleError(
            exc.code,
            f"EvidenceRecorded identity gate refused domain_model_hash {declared!r}: {exc}",
        ) from exc
    if declared != local_model_sha256:
        raise DomainRuleError(
            "hash_drift",
            f"EvidenceRecorded domain_model_hash drift: expected "
            f"{local_model_sha256}, got {declared}.",
        )

    # 3b. Semantic world (CEP-0008 world_ref). Syntax and equality only; the
    # digest is verified by SEA-Forge, not here. A declared world must match
    # the deployment's pinned one; an absent world leaves the evidence
    # "unbound" (unknown) only when this deployment pins no world; once a world
    # is pinned, evidence that names none is refused (RealityTrace now stamps it).
    world_ref = payload.get("world_ref")
    world_binding = "unbound"
    if world_ref is None and local_world_ref is not None:
        raise DomainRuleError(
            "world_ref_missing",
            "EvidenceRecorded carries no world_ref but this deployment pins "
            f"{local_world_ref}; evidence for an unknown world is refused.",
        )
    if world_ref is not None:
        verify_world_ref(world_ref)
        if local_world_ref is None:
            raise DomainRuleError(
                "world_ref_unpinned",
                "EvidenceRecorded declares a world_ref but this deployment pins "
                "none; the evidence cannot be compared and is refused.",
            )
        if world_ref != verify_world_ref(local_world_ref):
            raise DomainRuleError(
                "world_ref_drift",
                f"EvidenceRecorded world_ref drift: expected {local_world_ref}, "
                f"got {world_ref}.",
            )
        world_binding = "bound"

    # 4. Namespace / schema tampering (payload level).
    if payload.get("namespace") != NAMESPACE:
        raise DomainRuleError(
            "namespace_tampering",
            f"EvidenceRecorded namespace mismatch: want {NAMESPACE!r}, "
            f"got {payload.get('namespace')!r}.",
        )

    # 5. Required-field battery — ALL NINE frozen fields reported together.
    missing: list[str] = []
    if not (isinstance(event_id, str) and event_id.strip()):
        missing.append("event_id")
    for fname in REQUIRED_FIELDS[1:]:
        value = payload.get(fname)
        present = bool(value) if isinstance(value, str) else value is not None
        if not present:
            missing.append(fname)
    if missing:
        raise DomainRuleError(
            "incomplete_evidence_recorded",
            "EvidenceRecorded rejected — missing/empty frozen fields: "
            + ", ".join(sorted(missing))
            + ". Expected-vs-observed evidence cannot bind incompletely.",
        )

    # 6. Typed validation of each projected field.
    model_ref = payload["domain_model_ref"]
    if not isinstance(model_ref, dict):
        raise DomainRuleError(
            "ref_identity_mismatch",
            "EvidenceRecorded rejected: domain_model_ref is not an object.",
        )
    if model_ref.get("namespace") != NAMESPACE:
        raise DomainRuleError(
            "namespace_tampering",
            f"EvidenceRecorded domain_model_ref namespace mismatch: want "
            f"{NAMESPACE!r}, got {model_ref.get('namespace')!r}.",
        )
    if model_ref.get("model_hash") != declared:
        raise DomainRuleError(
            "ref_identity_mismatch",
            f"EvidenceRecorded domain_model_ref names {model_ref.get('model_hash')!r} "
            f"but the envelope declares {declared!r}.",
        )

    work_request_id = _check_identity_string("work_request_id", payload["work_request_id"])
    affordance_id = _check_identity_string("affordance_id", payload["affordance_id"])
    proof_result_ref = _validate_sha256_ref("proof_result_ref", payload["proof_result_ref"])
    operational_settlement_ref = _validate_sha256_ref(
        "operational_settlement_ref", payload["operational_settlement_ref"]
    )
    expected_outcome = payload["expected_outcome"]
    observed_outcome = payload["observed_outcome"]

    difference = payload["difference"]
    if not isinstance(difference, dict) or set(difference) < {
        "verdict",
        "expected_sha256",
        "observed_sha256",
    }:
        raise DomainRuleError(
            "invalid_ref",
            "EvidenceRecorded rejected: 'difference' must carry verdict, "
            "expected_sha256, and observed_sha256.",
        )
    for digest_field in ("expected_sha256", "observed_sha256"):
        if not _is_bare_digest(difference.get(digest_field) or ""):
            raise DomainRuleError(
                "invalid_ref",
                f"EvidenceRecorded rejected: difference.{digest_field} is not a "
                f"bare 64-hex sha256 digest: {difference.get(digest_field)!r}.",
            )
    if difference.get("verdict") not in ("equivalent", "divergent"):
        raise DomainRuleError(
            "invalid_ref",
            "EvidenceRecorded rejected: difference.verdict must be 'equivalent' "
            f"or 'divergent', got {difference.get('verdict')!r}.",
        )

    # 7. Cryptographic comparison binding (I10 probe detection): the recorded
    #    digests must recompute from the CARRIED values — a mutated
    #    expectation/observation cannot ride a stale difference.
    recomputed_expected = _bare_sha256(expected_outcome)
    recomputed_observed = _bare_sha256(observed_outcome)
    divergent_bindings: list[str] = []
    if difference["expected_sha256"] != recomputed_expected:
        divergent_bindings.append("expected_sha256")
    if difference["observed_sha256"] != recomputed_observed:
        divergent_bindings.append("observed_sha256")
    correct_verdict = (
        "equivalent" if recomputed_expected == recomputed_observed else "divergent"
    )
    if difference["verdict"] != correct_verdict:
        divergent_bindings.append("verdict")
    if divergent_bindings:
        raise DomainRuleError(
            "difference_binding_mismatch",
            "EvidenceRecorded rejected: 'difference' does not match the carried "
            "comparison values (diverged: "
            + ", ".join(divergent_bindings)
            + "). Upstream semantic facts cannot be silently rewritten.",
        )

    # 8. Causality presence (and optional out-of-band parent pinning).
    parents = _caused_by_parents(envelope)
    if not parents:
        raise DomainRuleError(
            "causality_missing",
            "EvidenceRecorded rejected: no caused_by causal parent recorded "
            "(ENV-I2/I4).",
        )
    if known_parent_ids is not None:
        allowed = {p.strip() for p in known_parent_ids}
        forged = [p for p in parents if p not in allowed]
        if forged:
            raise DomainRuleError(
                "forged_parent_reference",
                f"EvidenceRecorded rejected: causal parents {forged!r} are not "
                "among the independently pinned upstream ids.",
            )

    # 9. Correlation binding to the tracked cycle.
    if work_request_id != expected_work_request_id.strip():
        raise DomainRuleError(
            "cross_wired_work_request",
            f"Cross-wired delivery: tracked work_request_id "
            f"{expected_work_request_id!r}, envelope carries {work_request_id!r}.",
        )

    # 10. Duplicate recognition BEFORE any consequence: stable envelope
    #     identity, content identity, and producer idempotency key.
    identities = [
        f"event|{event_id.strip()}",
        f"content|{_bare_sha256(envelope)}",
    ]
    idem = envelope.get("idempotency_key")
    if isinstance(idem, str) and _is_bare_digest(idem):
        identities.append(f"idem|{idem}")
    if any(i in state.seen_identities for i in identities):
        return EvidenceAdmission(status="duplicate", record=None)

    # 11. Cycle-claim stability (T07 ClaimMismatch mirror): a FRESH envelope
    #     re-claiming an ALREADY-recorded (cycle, proof result) with divergent
    #     facts is refused BY NAME — the first record stands.
    claim = {
        "affordance_id": affordance_id,
        "operational_settlement_ref": operational_settlement_ref,
        "expected_canonical": canonical_json(expected_outcome),
        "observed_canonical": canonical_json(observed_outcome),
        "difference_canonical": canonical_json(difference),
        "model_hash": declared,
    }
    for prior in state.claims:
        prior_key = prior["claim_key"]
        if prior_key == f"{work_request_id}|{proof_result_ref}":
            diverged = [
                name for name, value in claim.items() if prior["claim"][name] != value
            ]
            if diverged:
                raise DomainRuleError(
                    "claim_mismatch",
                    "Resubmission contradicts the already-recorded cycle claims "
                    "(first claim stands); diverged fields: "
                    + ", ".join(sorted(diverged))
                    + ".",
                )
            return EvidenceAdmission(status="duplicate", record=None)

    # 12. Admit — identities then claim, atomically over the threaded state.
    state.seen_identities.extend(identities)
    state.claims.append(
        {
            "claim_key": f"{work_request_id}|{proof_result_ref}",
            "claim": claim,
        }
    )
    return EvidenceAdmission(
        status="first",
        record=ProvisionalEvidence(
            event_id=event_id.strip(),
            work_request_id=work_request_id,
            affordance_id=affordance_id,
            expected_outcome=expected_outcome,
            observed_outcome=observed_outcome,
            difference=dict(difference),
            proof_result_ref=proof_result_ref,
            operational_settlement_ref=operational_settlement_ref,
            domain_model_hash=declared,
            verdict=difference["verdict"],
            world_ref=world_ref,
            world_binding=world_binding,
        ),
    )
