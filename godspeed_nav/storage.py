from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


SECRET_KEYS = {
    "api_key",
    "apikey",
    "authorization",
    "password",
    "secret",
    "token",
}


class LedgerStore:
    """Append-only JSONL developmental memory store."""

    def __init__(self, root: str | Path, redact_secrets: bool = True):
        self.root = Path(root)
        self.redact_secrets = redact_secrets
        (self.root / "ledgers").mkdir(parents=True, exist_ok=True)
        (self.root / "cache" / "quarantine").mkdir(parents=True, exist_ok=True)

    def ledger_path(self, ledger_name: str) -> Path:
        safe_name = ledger_name.replace("/", "_").replace("..", "_")
        return self.root / "ledgers" / f"{safe_name}.jsonl"

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

    def _redact(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: "[REDACTED]" if key.lower() in SECRET_KEYS else self._redact(nested)
                for key, nested in value.items()
            }
        if isinstance(value, list):
            return [self._redact(item) for item in value]
        return value

