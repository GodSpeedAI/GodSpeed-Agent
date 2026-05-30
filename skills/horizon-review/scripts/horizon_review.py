from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from godspeed_nav.metrics import estimate_payment, rank_affordances


def review_horizon_candidates(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    affordances: list[dict[str, Any]] = []
    payments: dict[str, dict[str, Any]] = {}
    rejected: list[dict[str, str]] = []

    for candidate in candidates:
        candidate_id = candidate["id"]
        pathway = candidate.get("pathway", "")
        if not pathway:
            rejected.append({"id": candidate_id, "reason": "missing_pathway"})
            continue

        payment = estimate_payment(
            candidate.get("costs", {}),
            candidate.get("weights", {}),
            candidate.get("capacities", {}),
        )
        if payment["spendability"] != "affordable":
            rejected.append({"id": candidate_id, "reason": "unaffordable"})
            continue

        affordances.append(candidate)
        payments[candidate_id] = payment

    ranked = rank_affordances(affordances, payments)
    return {
        "ranked_affordances": ranked["ranked_affordances"],
        "next_affordance": ranked["next_recommended_affordance"],
        "rejected_candidates": rejected + ranked["rejected_candidates"],
    }


def main() -> int:
    payload = json.loads(sys.stdin.read() or "{}")
    result = review_horizon_candidates(payload.get("candidates", []))
    print(json.dumps(result, sort_keys=True))
    return 0


__all__ = ["review_horizon_candidates"]


if __name__ == "__main__":
    raise SystemExit(main())
