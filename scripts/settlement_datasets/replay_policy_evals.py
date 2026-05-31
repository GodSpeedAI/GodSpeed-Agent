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
from scripts.settlement_datasets.action_ontology import (
    compare_normalized_actions,
    load_action_ontology,
    normalize_eval_behavior,
    normalize_policy_action,
)
from scripts.settlement_datasets.run_scoped_paths import (
    add_run_scope_arguments,
    ensure_run_surface,
)


def _match_policy_to_eval(
    policy: dict[str, Any],
    eval_item: dict[str, Any],
) -> tuple[bool, str]:
    policy_fms = policy.get("evidence", {}).get("observed_failure_patterns", [])
    eval_fm = eval_item.get("observed_failure_mode", "")

    if eval_fm and eval_fm in policy_fms:
        return True, f"Policy targets '{eval_fm}' which matches eval failure mode."

    return False, "No match between policy and eval context."


def _raw_match(policy_action: dict[str, Any], expected: str) -> bool:
    require = str(policy_action.get("require_operator", "")).lower()
    return bool(require and require in expected.lower())


def replay_evals(
    policies: list[dict[str, Any]],
    eval_dir: str = "data/settlement_datasets/evals/",
    min_confidence: float = 0.65,
    ontology_path: str = "configs/settlement_datasets/harness_action_ontology.yaml",
) -> list[dict[str, Any]]:
    results = []
    eval_path = Path(eval_dir)
    ontology = load_action_ontology(ontology_path)

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
                normalized_policy = normalize_policy_action(policy_action, ontology)
                normalized_eval = normalize_eval_behavior(expected, ontology)
                semantic_result = compare_normalized_actions(
                    normalized_policy,
                    normalized_eval,
                )
                raw_match = _raw_match(policy_action, expected)

                results.append(
                    {
                        "policy_id": policy.get("id", ""),
                        "eval_id": item.get("trace_id", ""),
                        "eval_suite": suite_name,
                        "trace_id": item.get("trace_id", ""),
                        "dataset": item.get("dataset", ""),
                        "domain": item.get("domain", ""),
                        "observed_failure_mode": item.get("observed_failure_mode", ""),
                        "eval_raw_expected_behavior": expected,
                        "policy_raw_action": policy_action,
                        "policy_canonical_action": normalized_policy.get("canonical_action"),
                        "eval_canonical_action": normalized_eval.get("canonical_action"),
                        "raw_match": raw_match,
                        "match_result": semantic_result["match_category"],
                        "semantic_match": semantic_result["semantic_match"],
                        "match_confidence": semantic_result["match_confidence"],
                        "match_evidence": semantic_result["match_evidence"],
                        "mismatch_reason": semantic_result["mismatch_reason"],
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
                "raw_match": 0,
                "exact_semantic_match": 0,
                "partial_semantic_match": 0,
                "mismatch": 0,
                "unknown_policy_action": 0,
                "unknown_eval_behavior": 0,
                "insufficient_evidence": 0,
                "total": 0,
            }
        policy_stats[pid]["total"] += 1
        if r.get("raw_match"):
            policy_stats[pid]["raw_match"] += 1
        mr = r["match_result"]
        if mr in policy_stats[pid]:
            policy_stats[pid][mr] += 1

    summary = []
    for pid, stats in sorted(policy_stats.items()):
        excluded_unknown = stats["unknown_policy_action"] + stats["unknown_eval_behavior"]
        eligible_total = max(0, stats["total"] - excluded_unknown)
        semantic_score = stats["exact_semantic_match"] + (0.5 * stats["partial_semantic_match"])
        summary.append(
            {
                "policy_id": pid,
                **stats,
                "raw_match_rate": round(stats["raw_match"] / stats["total"], 3)
                if stats["total"]
                else 0.0,
                "semantic_match_rate": round(semantic_score / eligible_total, 3)
                if eligible_total
                else 0.0,
                "partial_match_rate": round(
                    stats["partial_semantic_match"] / eligible_total,
                    3,
                )
                if eligible_total
                else 0.0,
                "unknown_policy_action_count": stats["unknown_policy_action"],
                "unknown_eval_behavior_count": stats["unknown_eval_behavior"],
                "mismatch_count": stats["mismatch"],
                "excluded_unknown_count": excluded_unknown,
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

    policies_path = (
        str(scope.named_path("policies", "policies.yaml", input_surface=True))
        if scope is not None
        else args.policies
    )
    with open(policies_path) as f:
        policy_data = yaml.safe_load(f)
    policies = policy_data.get("policies", [])

    print(f"Loaded {len(policies)} policies")
    results = replay_evals(
        policies, eval_dir=args.eval_dir, min_confidence=args.min_confidence
    )

    output_dir = scope.replay_dir if scope is not None else Path(args.output)
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
                "raw_match",
                "exact_semantic_match",
                "partial_semantic_match",
                "mismatch",
                "unknown_policy_action",
                "unknown_eval_behavior",
                "insufficient_evidence",
                "raw_match_rate",
                "semantic_match_rate",
                "partial_match_rate",
                "unknown_policy_action_count",
                "unknown_eval_behavior_count",
                "mismatch_count",
                "excluded_unknown_count",
            ],
        )
        writer.writeheader()
        for s in summary:
            writer.writerow(s)
    print(f"Wrote eval replay summary -> {summary_path}")

    for s in summary:
        print(
            f"  {s['policy_id']}: {s['total']} evals, raw={s['raw_match_rate']:.1%}, "
            f"semantic={s['semantic_match_rate']:.1%}, partial={s['partial_match_rate']:.1%}, "
            f"unknown={s['excluded_unknown_count']}"
        )


if __name__ == "__main__":
    main()
