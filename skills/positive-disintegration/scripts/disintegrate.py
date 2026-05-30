from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from godspeed_nav.disintegration import review_positive_disintegration


def review_disintegration_case(payload: dict[str, Any]) -> dict[str, Any]:
    return review_positive_disintegration(
        structures=payload.get("structures", []),
        require_human_review=payload.get("require_human_review", True),
    )


def main() -> int:
    payload = json.loads(sys.stdin.read() or "{}")
    print(json.dumps(review_disintegration_case(payload), sort_keys=True))
    return 0


__all__ = ["review_disintegration_case"]


if __name__ == "__main__":
    raise SystemExit(main())
