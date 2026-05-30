from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))


def reconstruction_prompt(failed_doctrine: str) -> str:
    return f"Reconstruct this doctrine from settlement evidence, not preference: {failed_doctrine}"


def build_reconstruction_packet(payload: dict[str, Any]) -> dict[str, Any]:
    invariants = payload.get("preserve_invariants", [])
    evidence = payload.get("evidence", [])
    failed_doctrine = payload.get("failed_doctrine", "")
    return {
        "reconstruction_prompt": reconstruction_prompt(failed_doctrine),
        "preserved_invariants": invariants,
        "failure_evidence": evidence,
        "recommended_experiments": [
            "state the falsified rule explicitly",
            "write the smallest revised doctrine that preserves valid invariants",
            "define the next settlement surface for the revision",
        ],
    }


def main() -> int:
    payload = json.loads(sys.stdin.read() or "{}")
    print(json.dumps(build_reconstruction_packet(payload), sort_keys=True))
    return 0


__all__ = ["reconstruction_prompt", "build_reconstruction_packet"]


if __name__ == "__main__":
    raise SystemExit(main())
