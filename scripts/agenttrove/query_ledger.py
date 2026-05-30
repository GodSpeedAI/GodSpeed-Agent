from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any


def query_ledger(db_path: str | Path, query_type: str) -> list[dict[str, Any]]:
    db_path = Path(db_path)
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    queries: dict[str, str] = {
        "summarize_by_source": """
            SELECT source, COUNT(*) as count,
                   AVG(turn_count) as avg_turns,
                   AVG(command_count) as avg_commands,
                   AVG(error_count) as avg_errors
            FROM traces GROUP BY source ORDER BY count DESC
        """,
        "summarize_by_failure_mode": """
            SELECT failure_mode, COUNT(*) as count
            FROM failure_modes GROUP BY failure_mode ORDER BY count DESC
        """,
        "summarize_by_reward": """
            SELECT CASE
                WHEN reward >= 1.0 THEN 'high'
                WHEN reward > 0 AND reward < 1.0 THEN 'partial'
                WHEN reward IS NULL THEN 'null'
                ELSE 'low'
            END as reward_bucket, COUNT(*) as count
            FROM traces GROUP BY reward_bucket ORDER BY count DESC
        """,
        "high_payment_failures": """
            SELECT t.trace_id, t.source, t.turn_count, t.command_count, t.error_count,
                   s.settlement_quality, s.outcome_reward
            FROM traces t JOIN settlements s ON t.trace_id = s.trace_id
            WHERE t.turn_count > 10 AND (s.outcome_reward IS NULL OR s.outcome_reward <= 0)
            ORDER BY t.turn_count DESC LIMIT 50
        """,
        "recovered_successes": """
            SELECT t.trace_id, t.source, t.turn_count, t.error_count,
                   s.settlement_quality, s.outcome_reward
            FROM traces t JOIN settlements s ON t.trace_id = s.trace_id
            WHERE s.settlement_quality = 'recovered_success'
            ORDER BY t.error_count DESC LIMIT 50
        """,
        "premature_closures": """
            SELECT t.trace_id, t.source, t.turn_count
            FROM traces t JOIN failure_modes f ON t.trace_id = f.trace_id
            WHERE f.failure_mode = 'premature_closure'
            LIMIT 50
        """,
        "brittle_successes": """
            SELECT t.trace_id, t.source, t.turn_count, t.error_count, t.command_count,
                   s.settlement_quality
            FROM traces t JOIN settlements s ON t.trace_id = s.trace_id
            WHERE s.settlement_quality = 'brittle_success'
            ORDER BY t.turn_count DESC LIMIT 50
        """,
        "summarize_by_settlement_quality": """
            SELECT settlement_quality, COUNT(*) as count
            FROM settlements GROUP BY settlement_quality ORDER BY count DESC
        """,
        "summarize_by_path_shape": """
            SELECT path_shape, COUNT(*) as count
            FROM settlements GROUP BY path_shape ORDER BY count DESC
        """,
        "policy_signal_summary": """
            SELECT signal_type, recommended_policy, COUNT(*) as count
            FROM policy_signals GROUP BY signal_type ORDER BY count DESC
        """,
    }

    sql = queries.get(query_type)
    if not sql:
        available = ", ".join(sorted(queries.keys()))
        raise ValueError(f"Unknown query type '{query_type}'. Available: {available}")

    cursor = conn.execute(sql)
    columns = [desc[0] for desc in cursor.description]
    results = [dict(zip(columns, row)) for row in cursor.fetchall()]
    conn.close()
    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Query the AgentTrove settlement ledger."
    )
    parser.add_argument(
        "--db", type=str, default="data/agenttrove/settlement_ledger.sqlite"
    )
    parser.add_argument(
        "--query",
        type=str,
        default="summarize_by_source",
        choices=[
            "summarize_by_source",
            "summarize_by_failure_mode",
            "summarize_by_reward",
            "summarize_by_settlement_quality",
            "summarize_by_path_shape",
            "high_payment_failures",
            "recovered_successes",
            "premature_closures",
            "brittle_successes",
            "policy_signal_summary",
        ],
    )
    parser.add_argument(
        "--format", type=str, default="table", choices=["table", "json"]
    )
    args = parser.parse_args()

    results = query_ledger(args.db, args.query)

    if args.format == "json":
        print(json.dumps(results, indent=2))
    else:
        if not results:
            print("No results.")
            return
        headers = list(results[0].keys())
        col_widths = [
            max(len(str(h)), max((len(str(r.get(h, ""))) for r in results), default=0))
            for h in headers
        ]
        header_line = " | ".join(h.ljust(w) for h, w in zip(headers, col_widths))
        print(header_line)
        print("-" * len(header_line))
        for row in results:
            print(
                " | ".join(
                    str(row.get(h, "")).ljust(w) for h, w in zip(headers, col_widths)
                )
            )


if __name__ == "__main__":
    main()
