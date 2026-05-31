from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import yaml

from scripts.settlement_datasets.adapter_base import (
    read_records_jsonl,
    write_records_jsonl,
)


def _match_policy_to_eval(
    policy: dict[str, Any],
    eval_item: dict[str, Any],
) -> tuple[bool, str]:
    policy_fms = policy.get("evidence", {}).get("observed_failure_patterns", [])
    eval_fm = eval_item.get("observed_failure_mode", "")

    if eval_fm and eval_fm in policy_fms:
        return True, f"Policy targets '{eval_fm}' which matches eval failure mode."

    expected = eval_item.get("expected_harness_behavior", "").lower()
    action = policy.get("action", {})
    require = action.get("require_operator", "")
    if require and require in expected:
        return True, f"Policy action '{require}' matches expected behavior."

    return False, "No match between policy and eval context."


def replay_evals(
    policies: list[dict[str, Any]],
    eval_dir: str = "data/settlement_datasets/evals/",
    min_confidence: float = 0.65,
) -> list[dict[str, Any]]:
    results = []
    eval_path = Path(eval_dir)

    for suite_file in sorted(eval_path.glob("*.jsonl")):
        suite_name = suite_file.stem
        items = read_records_jsonl(str(suite_file))

        for item in items:
            item_conf = item.get("confidence", 0.0)
            if item_conf < min_confidence:
                continue

            for policy in policies:
                matched, match_rationale = _match_policy_to_eval(policy, item)
                if not matched:
                    continue

                expected = item.get("expected_harness_behavior", "")
                policy_action = policy.get("action", {})
                require = policy_action.get("require_operator", "")

                action_match = "uncertain"
                if require and require.lower() in expected.lower():
                    action_match = "match"
                elif expected and require:
                    action_match = "mismatch"
                elif not expected:
                    action_match = "no_expected_behavior"

                results.append(
                    {
                        "policy_id": policy.get("id", ""),
                        "eval_suite": suite_name,
                        "trace_id": item.get("trace_id", ""),
                        "dataset": item.get("dataset", ""),
                        "domain": item.get("domain", ""),
                        "observed_failure_mode": item.get("observed_failure_mode", ""),
                        "expected_behavior": expected,
                        "policy_action": require,
                        "match_result": action_match,
                        "match_rationale": match_rationale,
                        "eval_confidence": item_conf,
                    }
                )

    return results


def compute_replay_summary(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    policy_stats: dict[str, dict[str, Any]] = {}
    for r in results:
        pid = r["policy_id"]
        if pid not in policy_stats:
            policy_stats[pid] = {
                "match": 0,
                "mismatch": 0,
                "uncertain": 0,
                "no_expected_behavior": 0,
                "total": 0,
            }
        policy_stats[pid]["total"] += 1
        mr = r["match_result"]
        if mr in policy_stats[pid]:
            policy_stats[pid][mr] += 1

    summary = []
    for pid, stats in sorted(policy_stats.items()):
        summary.append(
            {
                "policy_id": pid,
                **stats,
                "match_rate": round(stats["match"] / stats["total"], 3)
                if stats["total"]
                else 0.0,
            }
        )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Replay eval items against proposed policies"
    )
    parser.add_argument("--policies", default="data/settlement_datasets/policies.yaml")
    parser.add_argument("--eval-dir", default="data/settlement_datasets/evals/")
    parser.add_argument(
        "--output", default="data/settlement_datasets/policy_shadow_eval"
    )
    parser.add_argument("--min-confidence", type=float, default=0.0)

    args = parser.parse_args()

    with open(args.policies) as f:
        policy_data = yaml.safe_load(f)
    policies = policy_data.get("policies", [])

    print(f"Loaded {len(policies)} policies")
    results = replay_evals(
        policies, eval_dir=args.eval_dir, min_confidence=args.min_confidence
    )

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    results_path = output_dir / "eval_replay_results.jsonl"
    write_records_jsonl(results, str(results_path))
    print(f"Wrote {len(results)} eval replay results -> {results_path}")

    summary = compute_replay_summary(results)
    summary_path = output_dir / "eval_replay_summary.csv"
    with summary_path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "policy_id",
                "total",
                "match",
                "mismatch",
                "uncertain",
                "no_expected_behavior",
                "match_rate",
            ],
        )
        writer.writeheader()
        for s in summary:
            writer.writerow(s)
    print(f"Wrote eval replay summary -> {summary_path}")

    for s in summary:
        print(
            f"  {s['policy_id']}: {s['total']} evals, match={s['match']}, "
            f"mismatch={s['mismatch']}, rate={s['match_rate']:.1%}"
        )


if __name__ == "__main__":
    main()
