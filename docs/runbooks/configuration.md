# Configuration Runbook

## Purpose

Configure local policy without breaking the horizon-centric invariants.

## Source

Configuration is read from `HARNESS.md` unless an explicit path is supplied by a caller. YAML front matter controls runtime behavior; markdown body documents local doctrine.

## Required Invariants

- `primary_metric` should remain `horizon_expansion`.
- `outcome_as_terminal` must stay false unless the operator explicitly documents why terminal outcome behavior is needed.
- Storage root should remain inside the workspace.
- Human review should remain enabled for absorption and positive disintegration in enterprise settings.

## Validation

After editing `HARNESS.md`, run:

```bash
uv run pytest -q
uv run python -m godspeed_nav.cli validate --workspace-root . --storage-root .godspeed-harness/validation
```

