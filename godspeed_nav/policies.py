from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class PolicyDecision:
    decision: str
    code: str
    reason: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def enforce_payment_policy(
    payment: dict[str, Any],
    policy: dict[str, Any] | None = None,
) -> PolicyDecision:
    policy = policy or {}
    if payment.get("spendability") != "unaffordable":
        return PolicyDecision("allow", "affordable", "Payment is within configured capacity.")

    if policy.get("block_unaffordable_actions", False):
        return PolicyDecision(
            "block",
            "unaffordable_action",
            "Payment exceeds capacity and blocking is enabled.",
        )

    if policy.get("warn_unaffordable_actions", True):
        return PolicyDecision(
            "warn",
            "unaffordable_action",
            "Payment exceeds capacity; candidate should remain a possibility.",
        )

    return PolicyDecision("allow", "unaffordable_warning_disabled", "Un affordable warning is disabled.")


def enforce_absorption_review(
    proposal: dict[str, Any],
    policy: dict[str, Any] | None = None,
) -> PolicyDecision:
    del proposal
    policy = policy or {}
    if policy.get("require_human_review_for_absorption", True):
        return PolicyDecision(
            "requires_review",
            "human_review_required",
            "Absorption requires human review before execution.",
        )
    return PolicyDecision("allow", "human_review_not_required", "Absorption review gate is disabled.")


def enforce_disintegration_review(
    candidate: dict[str, Any],
    policy: dict[str, Any] | None = None,
) -> PolicyDecision:
    del candidate
    policy = policy or {}
    if policy.get("require_human_review_for_disintegration", True):
        return PolicyDecision(
            "requires_review",
            "human_review_required",
            "Disintegration requires human review before execution.",
        )
    return PolicyDecision("allow", "human_review_not_required", "Disintegration review gate is disabled.")


def enforce_representational_transition_policy(
    transition: dict[str, Any],
    policy: dict[str, Any] | None = None,
) -> PolicyDecision:
    del policy
    if transition.get("status") == "blocked":
        return PolicyDecision(
            "block",
            str(transition.get("code", "blocked_transition")),
            "Representational transition is not currently spendable.",
        )
    return PolicyDecision(
        "allow",
        str(transition.get("code", "affordable_transition")),
        "Representational transition is currently spendable.",
    )
