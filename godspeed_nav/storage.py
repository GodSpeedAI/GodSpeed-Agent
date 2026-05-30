from __future__ import annotations

import hashlib
import json
import os
import shutil
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
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
            handle.flush()
            os.fsync(handle.fileno())
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
            records.append(record)

        if corrupt:
            quarantine = self.root / "cache" / "quarantine" / f"{ledger_name}.corrupt.jsonl"
            with quarantine.open("a", encoding="utf-8") as handle:
                for line in corrupt:
                    handle.write(line + "\n")

        return records

    def append_event(self, ledger_name: str, record: dict[str, Any]) -> dict[str, Any]:
        existing = self.read_events(ledger_name)
        payload = self._redact(record) if self.redact_secrets else record
        envelope = {
            "schema_version": 1,
            "sequence": len(existing) + 1,
            "timestamp": now_iso(),
            "ledger": ledger_name,
            "record": payload,
        }
        envelope["checksum"] = self._checksum(envelope)
        path = self.ledger_path(ledger_name)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(envelope, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
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
        return json.loads(path.read_text(encoding="utf-8"))

    def _update_index(self, ledger_name: str, envelope: dict[str, Any]) -> None:
        index = self._read_index(ledger_name)
        record_id = envelope.get("record", {}).get("id")
        if record_id:
            index["records"][record_id] = {
                "sequence": envelope["sequence"],
                "timestamp": envelope["timestamp"],
                "checksum": envelope["checksum"],
            }
        index["updated_at"] = now_iso()
        path = self._index_path(ledger_name)
        path.write_text(json.dumps(index, indent=2, sort_keys=True), encoding="utf-8")

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
