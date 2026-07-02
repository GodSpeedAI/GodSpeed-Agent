"""LearningProposalLedger — queryable store for LearningProposalCreated events.

Learning proposals are written here by GodSpeed-Agent when a coherence break
occurs. Context Kernel reads from this ledger when serving ContextRequired
events for the 'learning-proposals' corpus.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


LEDGER_NAME = "agentic_learning_proposals"


class LearningProposalLedger:
    """Append-only JSONL ledger for LearningProposalCreated events.

    Args:
        storage_root: Root directory where ledger files are written.
            Each ledger is a file named ``<ledger_name>.jsonl``.
    """

    def __init__(self, storage_root: Path) -> None:
        self._path = storage_root / f"{LEDGER_NAME}.jsonl"
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, learning_proposal_event: dict[str, Any]) -> dict[str, Any]:
        """Append a LearningProposalCreated event to the ledger.

        Validates that the event type is correct and the payload contains
        required fields before writing.

        Returns the event unchanged (for chaining).
        Raises ValueError if required fields are absent.
        """
        if learning_proposal_event.get("event_type") != "LearningProposalCreated":
            raise ValueError(
                f"Expected LearningProposalCreated, got {learning_proposal_event.get('event_type')!r}"
            )
        payload = learning_proposal_event.get("payload", {})
        for required in ("learning_proposal_id", "work_request_id", "domain_area", "status"):
            if not payload.get(required):
                raise ValueError(f"LearningProposalCreated payload missing required field: {required!r}")

        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(learning_proposal_event, ensure_ascii=False) + "\n")
        return learning_proposal_event

    def read_all(self) -> list[dict[str, Any]]:
        """Return all records in insertion order."""
        if not self._path.exists():
            return []
        records = []
        for line in self._path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                records.append(json.loads(line))
        return records

    def query_by_domain_area(self, domain_area: str) -> list[dict[str, Any]]:
        """Return all proposals whose payload.domain_area matches.

        Returns an empty list if no matches — never raises.
        """
        return [
            r for r in self.read_all()
            if r.get("payload", {}).get("domain_area") == domain_area
        ]

    def query_open(self) -> list[dict[str, Any]]:
        """Return all proposals with status 'open'."""
        return [
            r for r in self.read_all()
            if r.get("payload", {}).get("status") == "open"
        ]
