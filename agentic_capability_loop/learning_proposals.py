"""Canonical LearningProposalCreated storage through LedgerStore.

Learning proposals are persisted through the single LedgerStore authority so
they receive locking, sequencing, checksum envelopes, secret redaction, index,
quarantine, backup, and migration behavior. Domain validation and query
helpers live here but open no files directly.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from godspeed_nav.storage import LedgerStore

LEDGER_NAME = "agentic_learning_proposals"
_REQUIRED_PAYLOAD_FIELDS = (
    "learning_proposal_id",
    "work_request_id",
    "domain_area",
    "status",
)


def _validate(event: dict[str, Any]) -> None:
    if event.get("event_type") != "LearningProposalCreated":
        raise ValueError(
            f"Expected LearningProposalCreated, got {event.get('event_type')!r}"
        )
    payload = event.get("payload", {})
    for field in _REQUIRED_PAYLOAD_FIELDS:
        if not payload.get(field):
            raise ValueError(
                f"LearningProposalCreated payload missing required field: {field!r}"
            )


def append_learning_proposal(
    store: "LedgerStore", event: dict[str, Any]
) -> dict[str, Any]:
    """Validate and append a LearningProposalCreated event to canonical storage.

    Re-delivery of the same ``event_id`` is idempotent: the dedup scan and
    append run under one ``flock`` so concurrent re-delivery stores exactly one
    record and the existing record is returned.
    """
    _validate(event)
    envelope, _appended = store.append_event_if_absent(
        LEDGER_NAME, event, dedup_field="event_id"
    )
    return envelope["record"]


def query_learning_proposals(
    store: "LedgerStore",
    *,
    domain_area: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    """Return proposal events filtered by payload domain_area and/or status."""
    results: list[dict[str, Any]] = []
    for record in store.read(LEDGER_NAME):
        payload = record.get("payload", {})
        if domain_area is not None and payload.get("domain_area") != domain_area:
            continue
        if status is not None and payload.get("status") != status:
            continue
        results.append(record)
    return results


def migrate_legacy_learning_proposals(
    store: "LedgerStore",
) -> dict[str, int]:
    """Migrate the legacy root-level JSONL into canonical enveloped records.

    Idempotent: unique valid records migrate once (deduplicated by event_id),
    already-canonical records are skipped, and the legacy file is archived under
    ``cache/migrations/`` only after all lines verify. Malformed or invalid
    input blocks archival so nothing is lost without inspection.
    """
    legacy = Path(store.root) / f"{LEDGER_NAME}.jsonl"
    result = {"migrated": 0, "skipped_duplicates": 0, "archived": 0, "malformed": 0}
    if not legacy.exists():
        return result

    existing_ids = {r.get("event_id") for r in query_learning_proposals(store)}
    pending_ids = set[str]()
    valid: list[dict[str, Any]] = []
    malformed = 0

    for line in legacy.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            malformed += 1
            continue
        try:
            _validate(record)
        except ValueError:
            malformed += 1
            continue
        event_id = record.get("event_id")
        if event_id in existing_ids or event_id in pending_ids:
            result["skipped_duplicates"] += 1
            continue
        pending_ids.add(event_id)
        valid.append(record)

    for record in valid:
        store.append_event(LEDGER_NAME, record)
        result["migrated"] += 1

    if malformed == 0:
        archive_dir = Path(store.root) / "cache" / "migrations"
        archive_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(legacy), str(archive_dir / legacy.name))
        result["archived"] = 1
    else:
        result["malformed"] = malformed

    return result
