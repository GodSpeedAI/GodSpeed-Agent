from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Any


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


class DomainRuleError(ValueError):
    """Raised when a lifecycle transition violates the harness domain model."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class DesiredDirection:
    id: str
    label: str
    kind: str
    statement: str
    source: str | None
    horizon_id: str
    created_at: str = ""
    status: str = "active"
    pressure_notes: str | None = None
    success_criteria: list[str] | None = None
    death_criteria: list[str] | None = None
    needs_affordance_review: bool = False

    def __post_init__(self) -> None:
        if not self.created_at:
            object.__setattr__(self, "created_at", now_iso())
        object.__setattr__(self, "success_criteria", self.success_criteria or [])
        object.__setattr__(self, "death_criteria", self.death_criteria or [])

    def die(self, reason: str) -> DesiredDirection:
        return replace(
            self,
            status="dead",
            pressure_notes=reason,
            needs_affordance_review=True,
        )


@dataclass(frozen=True)
class Potential:
    id: str
    statement: str
    required_capabilities: list[str]
    missing_pathway_reason: str
    current_status: str = "potential"

    def to_affordance(self) -> None:
        raise DomainRuleError(
            "potential_cannot_execute",
            "Potential lacks a validated pathway and cannot be scheduled as affordance.",
        )


@dataclass(frozen=True)
class Possibility:
    id: str
    statement: str
    candidate_pathway: str
    unknowns: list[str]
    current_status: str = "possibility"

    def to_substrate(self) -> None:
        raise DomainRuleError(
            "possibility_cannot_metabolize",
            "Possibility has not settled repeatedly and cannot become substrate.",
        )


@dataclass(frozen=True)
class PaymentEstimate:
    id: str
    affordance_id: str
    dimensions: dict[str, float]
    burden: float
    capacity_norm: float = 0.0
    spendability: str = "unknown"
    dominant_cost: str | None = None


@dataclass(frozen=True)
class Affordance:
    id: str
    statement: str
    pathway: str
    payment_estimate: PaymentEstimate | None
    expected_horizon_delta: float
    current_status: str = "affordance"

    def __post_init__(self) -> None:
        if not self.pathway or self.payment_estimate is None:
            raise DomainRuleError(
                "affordance_requires_pathway_and_payment",
                "Affordance requires a validated pathway and payment estimate.",
            )


@dataclass(frozen=True)
class SettlementEvent:
    id: str
    affordance_id: str
    before_state: dict[str, Any]
    after_state: dict[str, Any]
    payment_actual: dict[str, float]
    score: float
    status: str
    evidence: list[str]
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            object.__setattr__(self, "created_at", now_iso())


@dataclass(frozen=True)
class Capability:
    id: str
    label: str
    settlement_event_ids: list[str]
    status: str = "capability"
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            object.__setattr__(self, "created_at", now_iso())

    @classmethod
    def from_settlements(
        cls,
        id: str,
        label: str,
        settlement_events: list[SettlementEvent],
        payment_estimate: PaymentEstimate | None = None,
    ) -> Capability:
        del payment_estimate
        successful = [event for event in settlement_events if event.status == "success" and event.score >= 0.7]
        if len(successful) < 2:
            raise DomainRuleError(
                "capability_requires_repeated_settlement",
                "Capability requires repeated successful settlement evidence.",
            )
        return cls(id=id, label=label, settlement_event_ids=[event.id for event in successful])


@dataclass(frozen=True)
class Substrate:
    id: str
    capability_id: str
    label: str
    metabolization_score: float
    evidence: list[str]
    status: str = "substrate"

    @classmethod
    def from_capability(
        cls,
        capability: Capability,
        metabolization_score: float,
        evidence: list[str],
    ) -> Substrate:
        if metabolization_score < 0.75 or len(evidence) < 2:
            raise DomainRuleError(
                "substrate_requires_metabolization",
                "Substrate requires metabolization evidence beyond operator declaration.",
            )
        return cls(
            id=f"sub-{capability.id}",
            capability_id=capability.id,
            label=capability.label,
            metabolization_score=metabolization_score,
            evidence=evidence,
        )
