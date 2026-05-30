from __future__ import annotations

import hashlib
import json
import os
import shutil
import fcntl
from pathlib import Path
from typing import Any

from godspeed_nav.schemas import now_iso


SECRET_KEYS = {
    "api_key",
    "apikey",
    "authorization",
    "password",
    "secret",
    "token",
}

STORAGE_SCHEMA_VERSION = 1


class StorageError(ValueError):
    """Typed storage error for operator-visible failure surfaces."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class LedgerStore:
    """Append-only JSONL developmental memory store."""

    def __init__(self, root: str | Path, redact_secrets: bool = True):
        self.root = Path(root)
        self.redact_secrets = redact_secrets
        (self.root / "ledgers").mkdir(parents=True, exist_ok=True)
        (self.root / "indexes").mkdir(parents=True, exist_ok=True)
        (self.root / "config").mkdir(parents=True, exist_ok=True)
        (self.root / "cache" / "quarantine").mkdir(parents=True, exist_ok=True)
        self._ensure_storage_manifest()

    def ledger_path(self, ledger_name: str) -> Path:
        if not ledger_name.replace("_", "").replace("-", "").isalnum():
            raise StorageError("unsafe_ledger_name", f"Unsafe ledger name: {ledger_name}")
        return self.root / "ledgers" / f"{ledger_name}.jsonl"

    def append(self, ledger_name: str, record: dict[str, Any]) -> Path:
        path = self.ledger_path(ledger_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = self._redact(record) if self.redact_secrets else record
        line = json.dumps(payload, sort_keys=True)
        with path.open("a+", encoding="utf-8") as handle:
            self._lock_handle(handle)
            try:
                handle.seek(0, os.SEEK_END)
                handle.write(line + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            finally:
                self._unlock_handle(handle)
        return path

    def read(self, ledger_name: str) -> list[dict[str, Any]]:
        path = self.ledger_path(ledger_name)
        if not path.exists():
            return []

        records: list[dict[str, Any]] = []
        corrupt: list[str] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                corrupt.append(line)
                continue
            if self._is_event_envelope(record):
                if record.get("checksum") != self._checksum(record):
                    corrupt.append(
                        json.dumps(
                            {"reason": "checksum_mismatch", "line": line},
                            sort_keys=True,
                        )
                    )
                    continue
                payload = record.get("record")
                if isinstance(payload, dict):
                    records.append(payload)
                    continue
            records.append(record)

        if corrupt:
            self._write_quarantine(ledger_name, corrupt)

        return records

    def append_event(self, ledger_name: str, record: dict[str, Any]) -> dict[str, Any]:
        path = self.ledger_path(ledger_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = self._redact(record) if self.redact_secrets else record
        with path.open("a+", encoding="utf-8") as handle:
            self._lock_handle(handle)
            try:
                sequence = self._next_event_sequence(handle)
                envelope = {
                    "schema_version": 1,
                    "sequence": sequence,
                    "timestamp": now_iso(),
                    "ledger": ledger_name,
                    "record": payload,
                }
                envelope["checksum"] = self._checksum(envelope)
                handle.seek(0, os.SEEK_END)
                handle.write(json.dumps(envelope, sort_keys=True) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            finally:
                self._unlock_handle(handle)
        self._update_index(ledger_name, envelope)
        return envelope

    def read_events(self, ledger_name: str) -> list[dict[str, Any]]:
        path = self.ledger_path(ledger_name)
        if not path.exists():
            return []

        events: list[dict[str, Any]] = []
        corrupt: list[str] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                corrupt.append(line)
                continue
            if event.get("checksum") != self._checksum(event):
                corrupt.append(json.dumps({"reason": "checksum_mismatch", "line": line}, sort_keys=True))
                continue
            events.append(event)

        if corrupt:
            self._write_quarantine(ledger_name, corrupt)
        return events

    def export_backup(self, destination: str | Path) -> Path:
        destination = Path(destination)
        if destination.exists():
            shutil.rmtree(destination)
        (destination / "ledgers").mkdir(parents=True, exist_ok=True)

        ledger_files = sorted((self.root / "ledgers").glob("*.jsonl"))
        for path in ledger_files:
            shutil.copy2(path, destination / "ledgers" / path.name)

        manifest = {
            "created_at": now_iso(),
            "source_root": str(self.root),
            "ledger_count": len(ledger_files),
            "ledgers": [path.name for path in ledger_files],
        }
        (destination / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        return destination

    def read_event_by_record_id(self, ledger_name: str, record_id: str) -> dict[str, Any] | None:
        index = self._read_index(ledger_name)
        entry = index.get("records", {}).get(record_id)
        if not entry:
            return None
        for event in self.read_events(ledger_name):
            if event.get("sequence") == entry["sequence"]:
                return event
        return None

    def migration_status(self) -> dict[str, Any]:
        manifest = self._read_storage_manifest()
        version = manifest.get("schema_version")
        if version != STORAGE_SCHEMA_VERSION:
            raise StorageError(
                "storage_migration_required",
                f"Storage schema {version} must be migrated to {STORAGE_SCHEMA_VERSION}.",
            )
        return {**manifest, "status": "current"}

    def query_developmental_memory(self) -> dict[str, Any]:
        payments = self.read("payments")
        settlements = self.read("settlements")
        capabilities = self.read("capabilities")
        critique_findings = self.read("critique_findings")

        paid_paths = [
            record.get("affordance_id")
            for record in payments
            if record.get("affordance_id")
        ]
        failed_settlements = [
            record.get("id")
            for record in settlements
            if record.get("status") == "failed" and record.get("id")
        ]
        substrate_capabilities = [
            record.get("id")
            for record in capabilities
            if record.get("lifecycle_state") == "metabolized" and record.get("id")
        ]
        revised_critique_findings = [
            {"id": record.get("id"), "revised_by": record.get("revised_by")}
            for record in critique_findings
            if record.get("id") and record.get("revised_by")
        ]
        return {
            "paid_paths": paid_paths,
            "failed_settlements": failed_settlements,
            "substrate_capabilities": substrate_capabilities,
            "revised_critique_findings": revised_critique_findings,
        }

    def _redact(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: "[REDACTED]" if key.lower() in SECRET_KEYS else self._redact(nested)
                for key, nested in value.items()
            }
        if isinstance(value, list):
            return [self._redact(item) for item in value]
        return value

    def _write_quarantine(self, ledger_name: str, lines: list[str]) -> None:
        quarantine = self.root / "cache" / "quarantine" / f"{ledger_name}.corrupt.jsonl"
        with quarantine.open("a", encoding="utf-8") as handle:
            for line in lines:
                handle.write(line + "\n")

    def _checksum(self, envelope: dict[str, Any]) -> str:
        payload = {key: value for key, value in envelope.items() if key != "checksum"}
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def _index_path(self, ledger_name: str) -> Path:
        self.ledger_path(ledger_name)
        return self.root / "indexes" / f"{ledger_name}.index.json"

    def _read_index(self, ledger_name: str) -> dict[str, Any]:
        path = self._index_path(ledger_name)
        if not path.exists():
            return {
                "schema_version": STORAGE_SCHEMA_VERSION,
                "ledger": ledger_name,
                "updated_at": now_iso(),
                "records": {},
            }
        text = path.read_text(encoding="utf-8")
        if not text.strip():
            return {
                "schema_version": STORAGE_SCHEMA_VERSION,
                "ledger": ledger_name,
                "updated_at": now_iso(),
                "records": {},
            }
        return json.loads(text)

    def _update_index(self, ledger_name: str, envelope: dict[str, Any]) -> None:
        path = self._index_path(ledger_name)
        with path.open("a+", encoding="utf-8") as handle:
            self._lock_handle(handle)
            try:
                handle.seek(0)
                raw = handle.read()
                index = (
                    json.loads(raw)
                    if raw.strip()
                    else {
                        "schema_version": STORAGE_SCHEMA_VERSION,
                        "ledger": ledger_name,
                        "updated_at": now_iso(),
                        "records": {},
                    }
                )
                record_id = envelope.get("record", {}).get("id")
                if record_id:
                    index["records"][record_id] = {
                        "sequence": envelope["sequence"],
                        "timestamp": envelope["timestamp"],
                        "checksum": envelope["checksum"],
                    }
                index["updated_at"] = now_iso()
                handle.seek(0)
                handle.truncate()
                handle.write(json.dumps(index, indent=2, sort_keys=True))
                handle.flush()
                os.fsync(handle.fileno())
            finally:
                self._unlock_handle(handle)

    def _manifest_path(self) -> Path:
        return self.root / "config" / "storage_manifest.json"

    def _ensure_storage_manifest(self) -> None:
        path = self._manifest_path()
        if path.exists():
            return
        manifest = {
            "schema_version": STORAGE_SCHEMA_VERSION,
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "storage_root": str(self.root),
        }
        path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    def _read_storage_manifest(self) -> dict[str, Any]:
        return json.loads(self._manifest_path().read_text(encoding="utf-8"))

    def _is_event_envelope(self, record: dict[str, Any]) -> bool:
        return {"schema_version", "sequence", "timestamp", "ledger", "record", "checksum"} <= set(record)

    def _next_event_sequence(self, handle: Any) -> int:
        handle.seek(0)
        sequence = 0
        for line in handle.read().splitlines():
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict) or not self._is_event_envelope(event):
                continue
            if event.get("checksum") != self._checksum(event):
                continue
            sequence = max(sequence, int(event.get("sequence", 0)))
        return sequence + 1

    def _lock_handle(self, handle: Any) -> None:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)

    def _unlock_handle(self, handle: Any) -> None:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
