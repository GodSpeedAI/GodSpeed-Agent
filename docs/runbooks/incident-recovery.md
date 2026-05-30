# Incident Recovery Runbook

## Common Incidents

## Corrupt Ledger Record

Symptom: report or read operation skips records and writes a file under `cache/quarantine`.

Recovery:

1. Inspect the quarantine file.
2. Compare the corrupt line with the source event.
3. Reconstruct only from authoritative evidence.
4. Re-run validation.

## Storage Migration Required

Symptom: `storage_migration_required` from `migration_status`.

Recovery:

1. Stop runtime writes.
2. Back up the storage root.
3. Run the appropriate migration for the stored schema version.
4. Re-run `uv run python -m godspeed_nav.cli validate --workspace-root . --storage-root <root>`.

## Hook Failure

Hook failures should not corrupt ledgers. Capture stdin payload, command output, and the affected storage root, then replay in a temporary storage root before retrying production writes.

