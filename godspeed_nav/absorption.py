from __future__ import annotations

from typing import Any

from godspeed_nav.policies import enforce_absorption_review


def review_absorbability(
    root_project_state: dict[str, Any],
    external_project_state: dict[str, Any],
    desired_direction: dict[str, Any],
    capability_delta: list[str],
    license_summary: dict[str, Any],
    pathway: str | None,
) -> dict[str, Any]:
    missing_pathway = pathway is None or not pathway.strip()
    license_ok = bool(license_summary.get("compatible", False))
    blocking_reasons: list[str] = []

    if missing_pathway:
        blocking_reasons.append("missing_pathway")
        status = "potential"
    elif not license_ok:
        blocking_reasons.append("incompatible_license")
        status = "blocked"
    else:
        status = "absorbable"

    policy_gate = enforce_absorption_review(
        proposal={
            "pathway": pathway,
            "capability_delta": capability_delta,
            "root_project_state": root_project_state,
            "external_project_state": external_project_state,
        }
    )
    required_human_review = policy_gate.decision == "requires_review"

    return {
        "absorbability_status": status,
        "missing_pathway": missing_pathway,
        "blocking_reasons": blocking_reasons,
        "policy_gate": policy_gate.to_dict(),
        "required_human_review": required_human_review,
        "payment_estimate": {
            "payment_burden": max(1, len(capability_delta) * 2),
            "dominant_cost": "integration",
        },
        "settlement_plan": [
            f"Prove {desired_direction.get('statement', 'desired direction')} with local tests",
            "Record before/after settlement evidence",
            "Document the local pathway and review decision before absorption",
        ],
        "proposed_worktree_plan": {
            "enabled": status == "absorbable",
            "branch": "absorb/external-capability",
        },
    }
