from __future__ import annotations

from typing import Any


def review_absorbability(
    root_project_state: dict[str, Any],
    external_project_state: dict[str, Any],
    desired_direction: dict[str, Any],
    capability_delta: list[str],
    license_summary: dict[str, Any],
    pathway: str | None,
) -> dict[str, Any]:
    del root_project_state, external_project_state
    missing_pathway = pathway is None or not pathway.strip()
    license_ok = bool(license_summary.get("compatible", False))
    if missing_pathway:
        status = "potential"
    elif not license_ok:
        status = "blocked"
    else:
        status = "absorbable"
    return {
        "absorbability_status": status,
        "missing_pathway": missing_pathway,
        "payment_estimate": {
            "payment_burden": max(1, len(capability_delta) * 2),
            "dominant_cost": "integration",
        },
        "settlement_plan": [
            f"Prove {desired_direction.get('statement', 'desired direction')} with local tests",
            "Record before/after settlement evidence",
        ],
        "proposed_worktree_plan": {
            "enabled": status == "absorbable",
            "branch": "absorb/external-capability",
        },
    }
