# Settlement Dataset SQLite Ledger

## Overview

The settlement ledger is a SQLite database that stores canonical settlement records from all datasets in a queryable, indexed format. It is produced by `scripts/settlement_datasets/export_ledger.py` and queried by `scripts/settlement_datasets/query_ledger.py`.

Default path: `data/settlement_datasets/settlement_ledger.sqlite`

## Tables

### datasets

Stores one row per dataset that has been imported.

| Column | Type | Description |
|---|---|---|
| `dataset` | TEXT PRIMARY KEY | Dataset name (agenttrove, swegym, apibank, webshop) |
| `domain` | TEXT | Domain category |
| `source_uri` | TEXT | Dataset source URI |
| `record_count` | INTEGER | Number of imported records |
| `avg_confidence` | REAL | Average outcome confidence across records |
| `imported_at` | TEXT | Import timestamp |

### tasks

Stores task-level metadata for each settlement record.

| Column | Type | Description |
|---|---|---|
| `task_id` | TEXT | Task identifier |
| `dataset` | TEXT | Source dataset |
| `domain` | TEXT | Domain category |
| `desired_direction_type` | TEXT | Task type (implementation, action, etc.) |
| `desired_direction_description` | TEXT | Task description |
| `environment_type` | TEXT | Environment type |
| `has_runnable_feedback` | INTEGER | Whether environment provides runnable feedback |
| `feedback_type` | TEXT | Feedback type |
| PRIMARY KEY | `(task_id, dataset)` | Composite primary key |

### traces

Stores representational state information for each trace.

| Column | Type | Description |
|---|---|---|
| `task_id` | TEXT | Task identifier |
| `dataset` | TEXT | Source dataset |
| `domain` | TEXT | Domain category |
| `source_uri` | TEXT | Dataset source URI |
| `path_shape` | TEXT | Representational path shape |
| `rep_state_start` | TEXT | Starting representational state |
| `rep_state_desired` | TEXT | Desired representational state |
| `rep_state_confidence` | REAL | Representational state confidence |
| PRIMARY KEY | `(task_id, dataset)` | Composite primary key |

### turns

Stores individual turns from trajectories.

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment ID |
| `task_id` | TEXT | Task identifier |
| `dataset` | TEXT | Source dataset |
| `turn_index` | INTEGER | Turn position in trajectory |
| `role` | TEXT | Turn role (assistant, tool, user) |
| `action_type` | TEXT | Action type |
| `content` | TEXT | Turn content (truncated to 2000 chars) |

### actions

Stores extracted actions from affordance paths.

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment ID |
| `task_id` | TEXT | Task identifier |
| `dataset` | TEXT | Source dataset |
| `turn_index` | INTEGER | Turn position |
| `action_type` | TEXT | Action type (command, analysis, api_call, search, click, buy, text) |
| `content` | TEXT | Action content (truncated to 2000 chars) |
| `tool_name` | TEXT | Tool name if applicable |

### observations

Stores extracted observations from affordance paths.

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment ID |
| `task_id` | TEXT | Task identifier |
| `dataset` | TEXT | Source dataset |
| `turn_index` | INTEGER | Turn position |
| `role` | TEXT | Observation role |
| `content` | TEXT | Observation content (truncated to 2000 chars) |

### settlements

Stores settlement quality and outcome information.

| Column | Type | Description |
|---|---|---|
| `task_id` | TEXT | Task identifier |
| `dataset` | TEXT | Source dataset |
| `success` | INTEGER | Success boolean (1/0/NULL) |
| `reward` | REAL | Numeric reward |
| `score` | REAL | Computed score |
| `settlement_quality` | TEXT | Settlement quality classification |
| `confidence` | REAL | Outcome confidence |
| PRIMARY KEY | `(task_id, dataset)` | Composite primary key |

### labels

Stores all label types for each record.

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment ID |
| `task_id` | TEXT | Task identifier |
| `dataset` | TEXT | Source dataset |
| `label_type` | TEXT | Label category (settlement_quality, failure_mode, etc.) |
| `label_value` | TEXT | Label value |
| `confidence` | REAL | Label confidence |
| `evidence_json` | TEXT | Evidence list as JSON array |

### failure_modes

Stores failure mode labels extracted from records.

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment ID |
| `task_id` | TEXT | Task identifier |
| `dataset` | TEXT | Source dataset |
| `failure_mode` | TEXT | Failure mode value |
| `confidence` | REAL | Failure mode confidence |
| `evidence_json` | TEXT | Evidence list as JSON array |

### policy_signals

Stores harness policy signal labels.

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment ID |
| `task_id` | TEXT | Task identifier |
| `dataset` | TEXT | Source dataset |
| `signal_type` | TEXT | Policy signal value |
| `confidence` | REAL | Signal confidence |
| `evidence_json` | TEXT | Evidence list as JSON array |

### metabolization_candidates

Stores metabolization candidate labels.

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment ID |
| `task_id` | TEXT | Task identifier |
| `dataset` | TEXT | Source dataset |
| `candidate_name` | TEXT | Candidate pattern name |
| `confidence` | REAL | Candidate confidence |
| `evidence_json` | TEXT | Evidence list as JSON array |

### eval_memberships

Stores eval suite membership for records.

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment ID |
| `task_id` | TEXT | Task identifier |
| `dataset` | TEXT | Source dataset |
| `eval_suite` | TEXT | Eval suite name |
| `reason` | TEXT | Membership reason |

## Indexes

| Index Name | Table | Column(s) | Purpose |
|---|---|---|---|
| `idx_tasks_dataset` | tasks | dataset | Filter by dataset |
| `idx_traces_dataset` | traces | dataset | Filter by dataset |
| `idx_settlements_quality` | settlements | settlement_quality | Filter by quality |
| `idx_settlements_dataset` | settlements | dataset | Filter by dataset |
| `idx_failure_modes_mode` | failure_modes | failure_mode | Filter by failure mode |
| `idx_failure_modes_dataset` | failure_modes | dataset | Filter by dataset |
| `idx_labels_dataset` | labels | dataset | Filter by dataset |
| `idx_policy_signals_dataset` | policy_signals | dataset | Filter by dataset |
| `idx_metab_dataset` | metabolization_candidates | dataset | Filter by dataset |

## Available Queries

The query ledger tool provides 10 predefined queries:

| Query | Returns |
|---|---|
| `summarize_by_dataset` | Record count and average confidence per dataset |
| `summarize_by_settlement_quality` | Record count per settlement quality and dataset |
| `summarize_by_failure_mode` | Record count per failure mode and dataset |
| `summarize_by_domain` | Record count per domain and dataset |
| `summarize_by_path_shape` | Record count per path shape and dataset |
| `high_confidence_records` | Records with confidence >= 0.65 |
| `low_confidence_records` | Records with confidence < 0.65 |
| `cross_dataset_failure_modes` | Failure modes appearing across multiple datasets |
| `policy_signal_summary` | Policy signal counts by type and dataset |
| `metabolization_summary` | Metabolization candidate counts by name and dataset |

Usage:

```bash
uv run python -m scripts.settlement_datasets.query_ledger --query summarize_by_dataset --format json
uv run python -m scripts.settlement_datasets.query_ledger --query cross_dataset_failure_modes --format table
```

## How to Extend for New Tables

To add a new table:

1. Add the `CREATE TABLE IF NOT EXISTS` statement to the `SCHEMA_SQL` string in `scripts/settlement_datasets/export_ledger.py`.
2. Add any `CREATE INDEX IF NOT EXISTS` statements to the same string.
3. Add insertion logic in the `_insert_record()` function that extracts the relevant data from the canonical record.
4. Add any new predefined queries to the `QUERIES` dict in `scripts/settlement_datasets/query_ledger.py`.
5. Update tests in `tests/test_settlement_datasets.py`.

## RuVector Extension Point (Future)

The ledger includes a future extension point for RuVector-based semantic search over settlement summaries. When activated:

- Settlement summaries (not raw traces) would be embedded and indexed.
- The `LedgerStore.search_developmental_memory()` method would query the vector index.
- Results would be filtered by settlement quality, confidence, and dataset before returning.

RuVector is not required for the current phase. See `docs/settlement-dataset-ruvector-extension.md` for details.

## Rebuilding the Ledger

```bash
rm data/settlement_datasets/settlement_ledger.sqlite
uv run python -m scripts.settlement_datasets.export_ledger --dataset all
```

The ledger is always rebuilt from the settlement record JSONL files. It is a derived artifact, not a source of truth.
