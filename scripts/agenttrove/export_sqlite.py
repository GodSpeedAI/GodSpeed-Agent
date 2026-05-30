from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS traces (
    trace_id TEXT PRIMARY KEY,
    source TEXT,
    teacher_model TEXT,
    task_id TEXT,
    reward REAL,
    turn_count INTEGER,
    tool_call_count INTEGER,
    command_count INTEGER,
    error_count INTEGER
);

CREATE TABLE IF NOT EXISTS turns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trace_id TEXT,
    turn_index INTEGER,
    role TEXT,
    content TEXT,
    tool_name TEXT,
    metadata_json TEXT
);

CREATE TABLE IF NOT EXISTS actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trace_id TEXT,
    turn_index INTEGER,
    action_type TEXT,
    content TEXT,
    settlement_status TEXT
);

CREATE TABLE IF NOT EXISTS settlements (
    trace_id TEXT PRIMARY KEY,
    settlement_quality TEXT,
    outcome_reward REAL,
    payment_pattern TEXT,
    path_shape TEXT,
    desired_direction_type TEXT
);

CREATE TABLE IF NOT EXISTS labels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trace_id TEXT,
    label_type TEXT,
    label_value TEXT,
    confidence REAL,
    evidence_json TEXT
);

CREATE TABLE IF NOT EXISTS failure_modes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trace_id TEXT,
    failure_mode TEXT,
    evidence_json TEXT
);

CREATE TABLE IF NOT EXISTS policy_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trace_id TEXT,
    signal_type TEXT,
    recommended_policy TEXT,
    evidence_json TEXT
);

CREATE TABLE IF NOT EXISTS eval_memberships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trace_id TEXT,
    eval_suite TEXT,
    reason TEXT
);

CREATE INDEX IF NOT EXISTS idx_traces_source ON traces(source);
CREATE INDEX IF NOT EXISTS idx_traces_reward ON traces(reward);
CREATE INDEX IF NOT EXISTS idx_settlements_quality ON settlements(settlement_quality);
CREATE INDEX IF NOT EXISTS idx_failure_modes_mode ON failure_modes(failure_mode);
CREATE INDEX IF NOT EXISTS idx_settlements_path_shape ON settlements(path_shape);
CREATE INDEX IF NOT EXISTS idx_settlements_direction_type ON settlements(desired_direction_type);
CREATE INDEX IF NOT EXISTS idx_labels_trace ON labels(trace_id);
CREATE INDEX IF NOT EXISTS idx_labels_type ON labels(label_type);
"""


def create_database(db_path: str | Path) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    return conn


def export_to_sqlite(
    settlement_path: str | Path,
    raw_path: str | Path | None = None,
    db_path: str | Path = "data/agenttrove/settlement_ledger.sqlite",
) -> Path:
    settlement_path = Path(settlement_path)
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    if db_path.exists():
        db_path.unlink()

    conn = create_database(db_path)

    raw_traces: dict[str, dict[str, Any]] = {}
    if raw_path:
        raw_path = Path(raw_path)
        if raw_path.exists():
            with raw_path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    trace = json.loads(line)
                    raw_traces[trace.get("trace_id", "")] = trace

    with settlement_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            settlement = json.loads(line)
            _insert_settlement(
                conn, settlement, raw_traces.get(settlement.get("trace_id", ""))
            )

    conn.commit()
    conn.close()
    return db_path


def _insert_settlement(
    conn: sqlite3.Connection,
    s: dict[str, Any],
    raw_trace: dict[str, Any] | None,
) -> None:
    trace_id = s.get("trace_id", "")
    payment = s.get("payment", {})
    outcome = s.get("outcome", {})
    labels = s.get("cognitive_os_labels", {})
    rep_state = s.get("representational_state", {})
    desired = s.get("desired_direction", {})

    conn.execute(
        "INSERT OR REPLACE INTO traces VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            trace_id,
            s.get("source", ""),
            s.get("teacher_model", ""),
            s.get("task_id", ""),
            _to_float(outcome.get("reward")),
            payment.get("turn_count", 0),
            payment.get("tool_call_count", 0),
            payment.get("command_count", 0),
            payment.get("error_count", 0),
        ),
    )

    conn.execute(
        "INSERT OR REPLACE INTO settlements VALUES (?, ?, ?, ?, ?, ?)",
        (
            trace_id,
            outcome.get("settlement_quality", "unknown"),
            _to_float(outcome.get("reward")),
            payment.get("estimated_complexity", "unknown"),
            rep_state.get("path_shape", "unknown"),
            desired.get("type", "unknown"),
        ),
    )

    if raw_trace:
        for i, msg in enumerate(raw_trace.get("messages", [])):
            conn.execute(
                "INSERT INTO turns (trace_id, turn_index, role, content, tool_name, metadata_json) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    trace_id,
                    i,
                    msg.get("role", ""),
                    msg.get("content", "")[:5000],
                    msg.get("tool_name"),
                    json.dumps(msg.get("metadata", {}), sort_keys=True)
                    if msg.get("metadata")
                    else None,
                ),
            )

    affordance = s.get("affordance_path", {})
    for action in affordance.get("actions", []):
        conn.execute(
            "INSERT INTO actions (trace_id, turn_index, action_type, content, settlement_status) VALUES (?, ?, ?, ?, ?)",
            (
                trace_id,
                action.get("turn_index", 0),
                action.get("role", ""),
                json.dumps(action, sort_keys=True),
                outcome.get("settlement_quality", "unknown"),
            ),
        )

    for recovery in affordance.get("recovery_events", []):
        conn.execute(
            "INSERT INTO actions (trace_id, turn_index, action_type, content, settlement_status) VALUES (?, ?, ?, ?, ?)",
            (
                trace_id,
                recovery.get("error_turn", 0),
                "recovery_event",
                json.dumps(recovery, sort_keys=True),
                "recovered" if recovery.get("recovered") else "unrecovered",
            ),
        )

    fm = labels.get("failure_mode")
    if fm:
        modes = fm if isinstance(fm, list) else [fm]
        for mode in modes:
            conn.execute(
                "INSERT INTO failure_modes (trace_id, failure_mode, evidence_json) VALUES (?, ?, ?)",
                (
                    trace_id,
                    mode,
                    json.dumps(
                        {"payment": payment, "path_shape": rep_state.get("path_shape")},
                        sort_keys=True,
                    ),
                ),
            )

    if labels.get("harness_policy_signal"):
        conn.execute(
            "INSERT INTO policy_signals (trace_id, signal_type, recommended_policy, evidence_json) VALUES (?, ?, ?, ?)",
            (
                trace_id,
                labels["harness_policy_signal"],
                labels["harness_policy_signal"],
                json.dumps({"failure_modes": fm}, sort_keys=True),
            ),
        )

    if labels.get("metabolization_candidate"):
        conn.execute(
            "INSERT INTO labels (trace_id, label_type, label_value, confidence, evidence_json) VALUES (?, ?, ?, ?, ?)",
            (
                trace_id,
                "metabolization_candidate",
                labels["metabolization_candidate"],
                0.8,
                json.dumps(
                    {"settlement_quality": outcome.get("settlement_quality")},
                    sort_keys=True,
                ),
            ),
        )

    conn.execute(
        "INSERT INTO labels (trace_id, label_type, label_value, confidence, evidence_json) VALUES (?, ?, ?, ?, ?)",
        (
            trace_id,
            "settlement_quality",
            outcome.get("settlement_quality", "unknown"),
            1.0,
            json.dumps({"reward": outcome.get("reward")}, sort_keys=True),
        ),
    )


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Export settlement traces to SQLite.")
    parser.add_argument(
        "--input",
        type=str,
        default="data/agenttrove/settlements/settlement_traces.jsonl",
    )
    parser.add_argument(
        "--raw", type=str, default=None, help="Optional raw JSONL for turn data."
    )
    parser.add_argument(
        "--output", type=str, default="data/agenttrove/settlement_ledger.sqlite"
    )
    args = parser.parse_args()

    path = export_to_sqlite(args.input, args.raw, args.output)
    print(f"Exported to {path}")


if __name__ == "__main__":
    main()
