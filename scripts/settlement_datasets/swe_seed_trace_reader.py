from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SECRET_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "authorization",
        "password",
        "secret",
        "token",
    }
)


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            k: (
                "[REDACTED]"
                if isinstance(k, str) and k.lower() in SECRET_KEYS
                else _redact(v)
            )
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_redact(v) for v in value]
    return value


def _canonical_records_dir(trace_root: Path) -> Path:
    return (trace_root / ".agent-harness" / "traces" / "records").resolve()


def read_swe_seed_trace_record(
    trace_root: Path, trace_path: Path
) -> dict[str, Any]:
    # Trace capture/mutation is owned by SWE_SEED. This reader only ingests
    # exports: reject symlinks and confine reads to the canonical records dir.
    if trace_path.is_symlink():
        raise ValueError(f"trace_path must not be a symlink: {trace_path}")
    canonical = _canonical_records_dir(trace_root)
    resolved = trace_path.resolve()
    try:
        resolved.relative_to(canonical)
    except ValueError:
        raise ValueError(
            f"trace_path must resolve under canonical records dir "
            f"{canonical}: {trace_path}"
        )
    data = json.loads(resolved.read_text(encoding="utf-8"))
    for field in ("trace_id", "created_at", "task", "route_decision_record"):
        if not data.get(field):
            raise ValueError(f"missing required field: {field}")
    return data


def read_swe_seed_hook_events(
    hook_log_dir: Path, trace_id: str
) -> list[dict[str, Any]]:
    if not hook_log_dir.is_dir():
        return []
    matched: list[dict[str, Any]] = []
    for log_path in sorted(hook_log_dir.glob("events-*.jsonl")):
        for line in log_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                envelope = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(envelope, dict):
                continue
            attrs = envelope.get("attributes")
            tid = envelope.get("trace_id") or (
                attrs.get("trace_id") if isinstance(attrs, dict) else None
            )
            if tid != trace_id:
                continue
            matched.append(
                {
                    "event": envelope.get("event"),
                    "status": envelope.get("status"),
                    "timestamp": envelope.get("timestamp"),
                    "attributes": _redact(envelope.get("attributes", {})),
                }
            )
    return matched


def to_trace_analysis_record(
    record: dict[str, Any], hook_events: list[dict[str, Any]]
) -> dict[str, Any]:
    return {
        "trace_source": "swe_seed_export",
        "classification": "provisional",
        "trace_id": record.get("trace_id"),
        "created_at": record.get("created_at"),
        "task": record.get("task"),
        "route": record.get("route", {}),
        "route_decision_record": record.get("route_decision_record"),
        "verification": record.get("verification", []),
        "unresolved_risks": record.get("unresolved_risks", []),
        "completion_claim": record.get("completion_claim"),
        "hook_event_count": len(hook_events),
        "hook_events": hook_events,
    }
