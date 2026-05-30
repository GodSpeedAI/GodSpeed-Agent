from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from godspeed_nav.metabolization import compute_metabolization


def review_metabolization_case(payload: dict[str, Any]) -> dict[str, Any]:
    return compute_metabolization(
        capability_id=payload["capability_id"],
        settlement_events=payload.get("settlement_events", []),
        reuse_frequency=payload.get("reuse_frequency", 0),
        context_diversity=payload.get("context_diversity", 0),
        stability=payload.get("stability", 0.0),
        maintenance_burden=payload.get("maintenance_burden", 1.0),
        attention_burden=payload.get("attention_burden", 1.0),
    )


def main() -> int:
    payload = json.loads(sys.stdin.read() or "{}")
    print(json.dumps(review_metabolization_case(payload), sort_keys=True))
    return 0


__all__ = ["review_metabolization_case"]


if __name__ == "__main__":
    raise SystemExit(main())
