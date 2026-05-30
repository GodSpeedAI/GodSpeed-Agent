from __future__ import annotations

import json
import sys
from typing import Any

from godspeed_nav.config import load_config, resolve_storage_root, runtime_policy
from godspeed_nav.runtime import NavigationRuntime
from godspeed_nav.storage import LedgerStore


def read_stdin_json() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("Hook input must be a JSON object")
    return parsed


def write_stdout_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, sort_keys=True))


def get_storage(event: dict[str, Any]) -> LedgerStore:
    workspace_root = event.get("workspace_root", ".")
    storage_root = resolve_storage_root(workspace_root, event.get("storage_root"))
    return LedgerStore(storage_root)


def get_runtime(event: dict[str, Any]) -> NavigationRuntime:
    workspace_root = event.get("workspace_root", ".")
    config = load_config(workspace_root)
    storage_root = resolve_storage_root(workspace_root, event.get("storage_root"))
    return NavigationRuntime(storage_root, policy=runtime_policy(config))


def get_policy(event: dict[str, Any]) -> dict[str, Any]:
    workspace_root = event.get("workspace_root", ".")
    return runtime_policy(load_config(workspace_root))


def get_session_context(
    event: dict[str, Any],
    desired_direction_id: str | None = None,
) -> dict[str, Any]:
    derived_direction_id = desired_direction_id or event.get("desired_direction_id")
    if not derived_direction_id:
        desired_direction = event.get("desired_direction")
        if isinstance(desired_direction, dict):
            derived_direction_id = desired_direction.get("id")

    return {
        "session_id": event.get("session_id"),
        "desired_direction_id": derived_direction_id,
    }

