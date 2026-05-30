# Backup And Restore Runbook

## Purpose

Protect local developmental memory ledgers from accidental loss or corruption.

## Backup

Use `LedgerStore.export_backup(destination)` or a wrapper command that calls `export_backup`. A valid backup contains copied ledger files and a `manifest.json` with creation time, source root, ledger count, and ledger names.

## Restore

1. Stop hook or runtime processes that may write ledgers.
2. Copy the backup `ledgers/*.jsonl` files into the target storage root.
3. Preserve `manifest.json` with the incident record.
4. Run `uv run python -m godspeed_nav.cli validate --workspace-root . --storage-root <restored-root>`.

## Verification

Read a developmental report after restore and confirm expected settlement, payment, and trajectory counts.

