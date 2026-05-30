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
- `computation.model_provider` should point at a local, explainable provider unless an operator has approved a different adapter.
- `computation.ml_event_threshold` and `computation.simulation_threshold` should be adjusted in `HARNESS.md`, not hard-coded in scripts.

## Validation

After editing `HARNESS.md`, run:

```bash
uv run pytest -q
uv run python -m godspeed_nav.cli validate --workspace-root . --storage-root .godspeed-harness/validation
```

Treat provider changes and predictive threshold changes as governed `HARNESS.md` edits so validation can confirm the new operating contract.
