# Installation Runbook

## Purpose

Install and verify the GodSpeed-Agent settlement and navigation runtime as a local-first Claude Code plugin and Python runtime.

## Prerequisites

- Python 3.11 or newer.
- `uv` available on PATH.
- Claude Code plugin loading available for `.claude-plugin/plugin.json`.

## Steps

1. Clone or unpack the repository.
2. Run `uv run pytest -q`.
3. Run `uv run python -m godspeed_nav.cli validate --workspace-root . --storage-root .godspeed-harness/validation`.
4. Install or link the plugin according to the local Claude Code plugin workflow.
5. Confirm root-level plugin assets remain outside `.claude-plugin/`.

## Acceptance

The installation is usable when `uv run pytest -q` passes and `godspeed-nav validate` or the module equivalent returns `"status": "pass"`.

