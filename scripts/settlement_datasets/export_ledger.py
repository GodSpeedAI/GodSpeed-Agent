from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any

from scripts.settlement_datasets.adapter_base import read_records_jsonl
from scripts.settlement_datasets.registry import available_datasets
from scripts.settlement_datasets.run_scoped_paths import (
    add_run_scope_arguments,
    ensure_run_surface,
)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS datasets (
    dataset TEXT PRIMARY KEY,
    domain TEXT,
    source_uri TEXT,
    record_count INTEGER DEFAULT 0,
    avg_confidence REAL DEFAULT 0.0,
    imported_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS tasks (
    task_id TEXT,
    dataset TEXT,
    domain TEXT,
    desired_direction_type TEXT,
    desired_direction_description TEXT,
    environment_type TEXT,
    has_runnable_feedback INTEGER DEFAULT 0,
    feedback_type TEXT,
    PRIMARY KEY (task_id, dataset)
);

CREATE TABLE IF NOT EXISTS traces (
    task_id TEXT,
    dataset TEXT,
    domain TEXT,
    source_uri TEXT,
    path_shape TEXT,
    rep_state_start TEXT,
    rep_state_desired TEXT,
    rep_state_confidence REAL,
    PRIMARY KEY (task_id, dataset)
);

CREATE TABLE IF NOT EXISTS turns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT,
    dataset TEXT,
    turn_index INTEGER,
    role TEXT,
    action_type TEXT,
    content TEXT
);

CREATE TABLE IF NOT EXISTS actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT,
    dataset TEXT,
    turn_index INTEGER,
    action_type TEXT,
    content TEXT,
    tool_name TEXT
);

CREATE TABLE IF NOT EXISTS observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT,
    dataset TEXT,
    turn_index INTEGER,
    role TEXT,
    content TEXT
);

CREATE TABLE IF NOT EXISTS settlements (
    task_id TEXT,
    dataset TEXT,
    success INTEGER,
    reward REAL,
    score REAL,
    settlement_quality TEXT,
    confidence REAL,
    PRIMARY KEY (task_id, dataset)
);

CREATE TABLE IF NOT EXISTS labels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT,
    dataset TEXT,
    label_type TEXT,
    label_value TEXT,
    confidence REAL,
    evidence_json TEXT
);

CREATE TABLE IF NOT EXISTS failure_modes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT,
    dataset TEXT,
    failure_mode TEXT,
    confidence REAL,
    evidence_json TEXT
);

CREATE TABLE IF NOT EXISTS policy_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT,
    dataset TEXT,
    signal_type TEXT,
    confidence REAL,
    evidence_json TEXT
);

CREATE TABLE IF NOT EXISTS metabolization_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT,
    dataset TEXT,
    candidate_name TEXT,
    confidence REAL,
    evidence_json TEXT
);

CREATE TABLE IF NOT EXISTS eval_memberships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT,
    dataset TEXT,
    eval_suite TEXT,
    reason TEXT
);

CREATE INDEX IF NOT EXISTS idx_tasks_dataset ON tasks(dataset);
CREATE INDEX IF NOT EXISTS idx_traces_dataset ON traces(dataset);
CREATE INDEX IF NOT EXISTS idx_settlements_quality ON settlements(settlement_quality);
CREATE INDEX IF NOT EXISTS idx_settlements_dataset ON settlements(dataset);
CREATE INDEX IF NOT EXISTS idx_failure_modes_mode ON failure_modes(failure_mode);
CREATE INDEX IF NOT EXISTS idx_failure_modes_dataset ON failure_modes(dataset);
CREATE INDEX IF NOT EXISTS idx_labels_dataset ON labels(dataset);
CREATE INDEX IF NOT EXISTS idx_policy_signals_dataset ON policy_signals(dataset);
CREATE INDEX IF NOT EXISTS idx_metab_dataset ON metabolization_candidates(dataset);
"""


def create_database(db_path: str | Path) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(str(db_path))
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    return conn


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _insert_record(conn: sqlite3.Connection, record: dict[str, Any]) -> None:
    dataset = record.get("dataset", "unknown")
    task_id = record.get("task_id", "")
    domain = record.get("domain", "unknown")

    conn.execute(
        "INSERT OR IGNORE INTO datasets (dataset, domain, source_uri) VALUES (?, ?, ?)",
        (dataset, domain, record.get("source_uri", "")),
    )

    dd = record.get("desired_direction", {})
    env = record.get("environment", {})
    conn.execute(
        "INSERT OR IGNORE INTO tasks (task_id, dataset, domain, desired_direction_type, desired_direction_description, environment_type, has_runnable_feedback, feedback_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            task_id,
            dataset,
            domain,
            dd.get("type", "unknown"),
            dd.get("description", ""),
            env.get("type", "unknown"),
            int(env.get("has_runnable_feedback", False)),
            env.get("feedback_type", "unknown"),
        ),
    )

    rs = record.get("representational_state", {})
    conn.execute(
        "INSERT OR IGNORE INTO traces (task_id, dataset, domain, source_uri, path_shape, rep_state_start, rep_state_desired, rep_state_confidence) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            task_id,
            dataset,
            domain,
            record.get("source_uri", ""),
            rs.get("path_shape", "unknown"),
            rs.get("start", "unknown"),
            rs.get("desired", "unknown"),
            rs.get("confidence", 0.0),
        ),
    )

    for i, action in enumerate(
        record.get("affordance_path", {}).get("actions", [])[:20]
    ):
        conn.execute(
            "INSERT INTO actions (task_id, dataset, turn_index, action_type, content, tool_name) VALUES (?, ?, ?, ?, ?, ?)",
            (
                task_id,
                dataset,
                action.get("turn_index", i),
                action.get("action_type", ""),
                str(action.get("content", ""))[:2000],
                action.get("tool_name"),
            ),
        )

    for i, obs in enumerate(
        record.get("affordance_path", {}).get("observations", [])[:20]
    ):
        conn.execute(
            "INSERT INTO observations (task_id, dataset, turn_index, role, content) VALUES (?, ?, ?, ?, ?)",
            (
                task_id,
                dataset,
                obs.get("turn_index", i),
                obs.get("role", ""),
                str(obs.get("content", ""))[:2000],
            ),
        )

    outcome = record.get("outcome", {})
    success_val = outcome.get("success")
    conn.execute(
        "INSERT INTO settlements (task_id, dataset, success, reward, score, settlement_quality, confidence) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            task_id,
            dataset,
            int(success_val) if success_val is not None else None,
            _to_float(outcome.get("reward")),
            _to_float(outcome.get("score")),
            outcome.get("settlement_quality", "unknown"),
            outcome.get("confidence", 0.0),
        ),
    )

    labels = record.get("labels", {})

    if labels.get("failure_mode"):
        conn.execute(
            "INSERT INTO failure_modes (task_id, dataset, failure_mode, confidence, evidence_json) VALUES (?, ?, ?, ?, ?)",
            (
                task_id,
                dataset,
                labels.get("failure_mode"),
                labels.get("failure_mode_confidence", 0.0),
                json.dumps(labels.get("failure_mode_evidence", [])),
            ),
        )

    if labels.get("harness_policy_signal"):
        conn.execute(
            "INSERT INTO policy_signals (task_id, dataset, signal_type, confidence, evidence_json) VALUES (?, ?, ?, ?, ?)",
            (
                task_id,
                dataset,
                labels.get("harness_policy_signal"),
                labels.get("harness_policy_signal_confidence", 0.0),
                json.dumps(labels.get("harness_policy_signal_evidence", [])),
            ),
        )

    if labels.get("metabolization_candidate"):
        conn.execute(
            "INSERT INTO metabolization_candidates (task_id, dataset, candidate_name, confidence, evidence_json) VALUES (?, ?, ?, ?, ?)",
            (
                task_id,
                dataset,
                labels.get("metabolization_candidate"),
                labels.get("metabolization_candidate_confidence", 0.0),
                json.dumps(labels.get("metabolization_candidate_evidence", [])),
            ),
        )

    conn.execute(
        "INSERT INTO labels (task_id, dataset, label_type, label_value, confidence, evidence_json) VALUES (?, ?, ?, ?, ?, ?)",
        (
            task_id,
            dataset,
            "settlement_quality",
            outcome.get("settlement_quality", "unknown"),
            outcome.get("confidence", 0.0),
            json.dumps(outcome.get("evidence", [])),
        ),
    )


def export_ledger(
    dataset: str | None = None,
    input_dir: str = "data/settlement_datasets/settlements/",
    output_path: str = "data/settlement_datasets/settlement_ledger.sqlite",
) -> Path:
    conn = create_database(output_path)

    datasets = [dataset] if dataset and dataset != "all" else available_datasets()

    total = 0
    for ds in datasets:
        input_path = Path(input_dir) / f"{ds}.jsonl"
        if not input_path.exists():
            input_path = (
                Path(input_dir.replace("settlements", "raw_samples")) / f"{ds}.jsonl"
            )
        if not input_path.exists():
            continue

        records = read_records_jsonl(str(input_path))
        for rec in records:
            _insert_record(conn, rec)
            total += 1

    for ds in datasets:
        count = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE dataset = ?", (ds,)
        ).fetchone()[0]
        conn.execute(
            "UPDATE datasets SET record_count = ? WHERE dataset = ?", (count, ds)
        )

    conn.commit()
    conn.close()
    return Path(output_path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export settlement records to SQLite ledger"
    )
    parser.add_argument(
        "--dataset",
        default="all",
        choices=["agenttrove", "swegym", "apibank", "webshop", "all"],
    )
    parser.add_argument("--input", default="data/settlement_datasets/settlements/")
    parser.add_argument(
        "--output", default="data/settlement_datasets/settlement_ledger.sqlite"
    )
    add_run_scope_arguments(parser)

    args = parser.parse_args()
    scope = None
    if any([args.run_id, args.run_dir, args.input_run_dir, args.output_run_dir]):
        scope = ensure_run_surface(
            run_id=args.run_id,
            run_dir=args.run_dir,
            input_run_dir=args.input_run_dir,
            output_run_dir=args.output_run_dir,
        )
    path = export_ledger(
        dataset=args.dataset,
        input_dir=str(scope.stage_dir("settlements", input_surface=True)) if scope is not None else args.input,
        output_path=str(scope.named_path("ledger", "settlement_ledger.sqlite")) if scope is not None else args.output,
    )
    print(f"Exported to {path}")


if __name__ == "__main__":
    main()
