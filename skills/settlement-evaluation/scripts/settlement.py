from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from godspeed_nav.metrics import score_settlement


def evaluate_settlement_case(payload: dict[str, Any]) -> dict[str, Any]:
    return score_settlement(
        before_state=payload.get("before_state", {}),
        after_state=payload.get("after_state", {}),
        desired_direction=payload.get("desired_direction", {}),
        payment_actual=payload.get("payment_actual", {}),
        evaluator_config={"evidence": payload.get("evidence", [])},
    )


def main() -> int:
    payload = json.loads(sys.stdin.read() or "{}")
    print(json.dumps(evaluate_settlement_case(payload), sort_keys=True))
    return 0


__all__ = ["evaluate_settlement_case"]


if __name__ == "__main__":
    raise SystemExit(main())
