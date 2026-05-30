from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from godspeed_nav.metrics import estimate_payment


def compute_affordance_assessment(candidate: dict[str, Any]) -> dict[str, Any]:
    pathway = candidate.get("pathway", "")
    if not pathway:
        return {
            "candidate_id": candidate.get("id"),
            "candidate_status": "potential",
            "reason": "missing_pathway",
            "payment": None,
        }

    payment = estimate_payment(
        candidate.get("costs", {}),
        candidate.get("weights", {}),
        candidate.get("capacities", {}),
    )
    status = "affordance" if payment["spendability"] == "affordable" else "possibility"
    return {
        "candidate_id": candidate.get("id"),
        "candidate_status": status,
        "payment": payment,
        "expected_horizon_delta": candidate.get("expected_horizon_delta", 0),
    }


def main() -> int:
    payload = json.loads(sys.stdin.read() or "{}")
    result = compute_affordance_assessment(payload.get("candidate", {}))
    print(json.dumps(result, sort_keys=True))
    return 0


__all__ = ["compute_affordance_assessment"]


if __name__ == "__main__":
    raise SystemExit(main())
