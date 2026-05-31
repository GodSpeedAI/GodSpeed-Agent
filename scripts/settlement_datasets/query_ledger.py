from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


QUERIES = {
    "summarize_by_dataset": "SELECT dataset, COUNT(*) as count, AVG(confidence) as avg_confidence FROM settlements GROUP BY dataset",
    "summarize_by_settlement_quality": "SELECT settlement_quality, dataset, COUNT(*) as count FROM settlements GROUP BY settlement_quality, dataset ORDER BY count DESC",
    "summarize_by_failure_mode": "SELECT failure_mode, dataset, COUNT(*) as count FROM failure_modes GROUP BY failure_mode, dataset ORDER BY count DESC",
    "summarize_by_domain": "SELECT domain, dataset, COUNT(*) as count FROM traces GROUP BY domain, dataset",
    "summarize_by_path_shape": "SELECT path_shape, dataset, COUNT(*) as count FROM traces GROUP BY path_shape, dataset ORDER BY count DESC",
    "high_confidence_records": "SELECT task_id, dataset, settlement_quality, confidence FROM settlements WHERE confidence >= 0.65 ORDER BY confidence DESC",
    "low_confidence_records": "SELECT task_id, dataset, settlement_quality, confidence FROM settlements WHERE confidence < 0.65 ORDER BY confidence ASC",
    "cross_dataset_failure_modes": "SELECT fm.failure_mode, GROUP_CONCAT(DISTINCT fm.dataset) as datasets, COUNT(*) as total FROM failure_modes fm GROUP BY fm.failure_mode ORDER BY total DESC",
    "policy_signal_summary": "SELECT signal_type, dataset, COUNT(*) as count FROM policy_signals GROUP BY signal_type, dataset ORDER BY count DESC",
    "metabolization_summary": "SELECT candidate_name, dataset, COUNT(*) as count FROM metabolization_candidates GROUP BY candidate_name, dataset",
}


def query_ledger(db_path: str | Path, query_type: str) -> list[dict]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    sql = QUERIES.get(query_type)
    if not sql:
        conn.close()
        raise ValueError(
            f"Unknown query: {query_type}. Available: {list(QUERIES.keys())}"
        )
    rows = conn.execute(sql).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def main() -> None:
    parser = argparse.ArgumentParser(description="Query settlement ledger")
    parser.add_argument(
        "--db", default="data/settlement_datasets/settlement_ledger.sqlite"
    )
    parser.add_argument("--query", required=True, choices=list(QUERIES.keys()))
    parser.add_argument("--format", choices=["table", "json"], default="table")

    args = parser.parse_args()
    results = query_ledger(args.db, args.query)

    if args.format == "json":
        print(json.dumps(results, indent=2))
    else:
        if results:
            headers = list(results[0].keys())
            print("\t".join(headers))
            for row in results:
                print("\t".join(str(row.get(h, "")) for h in headers))


if __name__ == "__main__":
    main()
