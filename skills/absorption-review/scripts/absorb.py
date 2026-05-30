from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from godspeed_nav.absorption import review_absorbability


def review_absorption_case(payload: dict[str, Any]) -> dict[str, Any]:
    return review_absorbability(
        root_project_state=payload.get("root_project_state", {}),
        external_project_state=payload.get("external_project_state", {}),
        desired_direction=payload.get("desired_direction", {}),
        capability_delta=payload.get("capability_delta", []),
        license_summary=payload.get("license_summary", {}),
        pathway=payload.get("pathway"),
    )


def main() -> int:
    payload = json.loads(sys.stdin.read() or "{}")
    print(json.dumps(review_absorption_case(payload), sort_keys=True))
    return 0


__all__ = ["review_absorption_case"]


if __name__ == "__main__":
    raise SystemExit(main())
