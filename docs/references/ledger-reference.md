# Ledger Reference

## Purpose

This document names the local ledgers that make the harness real at runtime. Payment and settlement ledgers are the truth surface. If a transformation is not recorded in a ledger or cannot survive ledger scrutiny, it has not settled.

## Controlling Surface

The ledger implementation lives in `godspeed_nav/storage.py` in `LedgerStore`.

Core methods:

- `append`: write a plain JSONL record.
- `read`: read plain JSONL records from a ledger.
- `append_event`: write an enveloped event record with sequence, timestamp, and checksum.
- `read_events`: read and verify enveloped event records.
- `read_event_by_record_id`: resolve an event through the ledger index.
- `query_developmental_memory`: answer lineage questions over the existing ledger truth.
- `export_backup`: export all ledger files plus `manifest.json`.
- `migration_status`: verify the storage manifest schema version.

## Event Envelope

When a caller uses `append_event`, the stored record includes these required fields:

- `schema_version`
- `sequence`
- `timestamp`
- `ledger`
- `record`
- `checksum`

`read_events` rejects corrupted lines and checksum mismatches into quarantine. That is part of the evidence contract, not bookkeeping decoration.

## Storage Layout

Default storage root: `.godspeed-harness`

Relevant subdirectories:

- `ledgers/`: JSONL ledger files.
- `indexes/`: per-ledger lookup files keyed by record id.
- `config/`: storage manifest metadata.
- `cache/quarantine/`: corrupt or checksum-invalid lines.

## Runtime Workflow Ledgers

These ledgers are written by the connected runtime in `NavigationRuntime`.

- `desired_directions`: active or historical directions created by `start-direction`.
- `horizons`: horizon state created with a direction.
- `horizon_reviews`: ranked affordance reviews created by `review-horizon`.
- `potentials`: candidate transformations lacking a spendable pathway.
- `possibilities`: candidates blocked by affordability or payment policy.
- `affordances`: spendable candidates accepted into the active horizon.
- `payments`: payment estimates recorded during horizon review.
- `settlements`: before/after consequence records from `record-settlement`.
- `trajectories`: Euler-style trajectory updates created after settlement.
- `capabilities`: capability or substrate-candidate records used by metabolization reporting.

## Event Adapter Ledgers

These ledgers are written by the public event adapter (`agentic_capability_loop`) and the runtime evidence boundary. They all use `append_event`.

- `execution_evidence`: provisional execution-evidence records persisted by `NavigationRuntime.ingest_execution_evidence()`. Software proof alone is never settlement; this ledger is provisional input for a later consequence-based settlement. Re-delivery by `event_id` is idempotent.
- `agentic_learning_proposals`: LearningProposalCreated events persisted through the canonical `LedgerStore` helper (`append_learning_proposal`). These share locking, checksum, redaction, index, backup, and migration behavior with every other canonical ledger; there is no second storage authority.
- `agentic_outbound_events`: a transport outbox. Outbound envelopes (e.g. SettlementRecorded, CapabilityUpdated, RepetitionPlanned) are buffered here for one-way drain. It stores transport envelopes only; `settlements`, `capabilities`, and `repetition_schedules` remain the canonical runtime authority.

Software hooks and traces are owned by SWE_SEED (F-08); host hook ledgers no longer exist in this runtime.

## Backup And Recovery Notes

- Use `export_backup` when you need a portable snapshot of local ledger state.
- Expect `manifest.json` in the backup root.
- Treat quarantine files as settlement warnings. They indicate evidence corruption, not harmless noise.

## Operational Reading Rules

- Read `payments` and `settlements` together when judging whether an affordance was truly affordable and truly settled.
- Read `horizon_reviews` and `trajectories` together when judging whether the system is expanding the horizon or rotating in place.
- Prefer `read_events` over raw line parsing for event ledgers because it enforces checksum validation.
- Use `query_developmental_memory` when the operator needs lineage answers such as what path was paid for, what failed to settle, which capabilities became substrate, or which critique findings were later revised.

## Model Calibration Fields

Settlement records now include a `model_calibration` object that captures the data needed for later calibration of the cognitive model burden, risk, and debt estimates. These fields support the calibration schedule described in the mathematical specification (Section 17).

Fields:

- `payment_predicted`: the payment dimensions recorded during horizon review, or `None` if no prediction was captured.
- `payment_actual`: the actual payment vector supplied at settlement time.
- `settlement_success`: boolean indicating whether the settlement scored as success.
- `settlement_score`: the continuous settlement score.
- `horizon_delta`: the horizon expansion recorded for this settlement.
- `risk_estimate`: the risk value from the matched affordance, or `None`.
- `debt_estimate`: the debt value from the matched affordance, or `None`.

These fields are **calibration data**, not proof of capability. They exist to support future weight fitting and threshold tuning after enough settlement history accumulates. Do not treat the presence of calibration fields as evidence that the model is calibrated or that predictions are accurate.
