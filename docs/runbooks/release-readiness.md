# Release Readiness Runbook

## Release gates

Every release candidate must pass:

```bash
uv run pytest -q
uv run python -m godspeed_nav.cli validate --workspace-root . --storage-root .godspeed-harness/release-validation
```

If the package entry point is installed, the equivalent command is `godspeed-nav validate`.

## Checklist

- Plugin manifest exists and identity metadata is correct.
- Skills include front matter descriptions and focused instructions.
- Runtime workflow can start a direction, review horizon, record settlement, and produce a snapshot.
- Storage manifest is current and backup export produces `manifest.json`.
- Hooks return structured JSON.
- MCP exposes deterministic tools plus runtime snapshot and developmental report.
- `CURRENT_STATE.md` includes the latest meaningful milestone and verification evidence.

## Release Decision

Ship only when the release gates pass, no known critical gaps remain in `CURRENT_STATE.md`, and backup/restore plus incident recovery runbooks are current.
