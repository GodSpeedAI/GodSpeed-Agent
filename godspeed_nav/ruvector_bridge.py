from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


class RuVectorBridgeError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def search_documents(
    *,
    repo_root: str | Path,
    documents: list[dict[str, Any]],
    query: str,
    limit: int = 5,
) -> dict[str, Any]:
    helper_dir = Path(repo_root) / "tools" / "ruvector"
    helper_script = helper_dir / "search_memory.cjs"

    if shutil.which("node") is None:
        raise RuVectorBridgeError("ruvector_node_missing", "Node.js is required for the RuVector bridge.")
    if not helper_script.exists():
        raise RuVectorBridgeError(
            "ruvector_bridge_missing",
            f"RuVector bridge script not found at {helper_script}",
        )
    if not (helper_dir / "node_modules" / "ruvector").exists():
        raise RuVectorBridgeError(
            "ruvector_not_installed",
            "RuVector is not installed. Run 'npm install' in tools/ruvector.",
        )

    payload = {
        "query": query,
        "limit": limit,
        "documents": documents,
    }
    result = subprocess.run(
        ["node", str(helper_script)],
        cwd=helper_dir,
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "RuVector bridge failed"
        raise RuVectorBridgeError("ruvector_search_failed", message)

    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuVectorBridgeError("ruvector_invalid_response", f"Invalid RuVector response: {exc}") from exc

    parsed.setdefault("provider", "ruvector")
    parsed.setdefault("result_count", len(parsed.get("results", [])))
    return parsed