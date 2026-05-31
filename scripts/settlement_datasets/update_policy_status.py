from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from scripts.settlement_datasets.adapter_base import read_records_jsonl


def update_policy_status(
    shadow_results_path: str,
    policies_path: str,
    output_path: str = "policies/review/policy_status_recommendations.yaml",
) -> Path:
    shadow_results = read_records_jsonl(shadow_results_path)

    with open(policies_path) as f:
        policy_data = yaml.safe_load(f)
    policies = policy_data.get("policies", [])

    from scripts.settlement_datasets.evaluate_policies_shadow import (
        compute_promotion_scores,
    )

    scores = compute_promotion_scores(shadow_results, policies)

    status_records = []
    for policy in policies:
        pid = policy.get("id", "")
        score = next((s for s in scores if s["policy_id"] == pid), None)

        if score is None:
            status_records.append(
                {
                    "policy_id": pid,
                    "current_status": "proposed",
                    "recommended_status": "needs_more_evidence",
                    "rationale": "No shadow evaluation results found.",
                    "evidence": {},
                }
            )
            continue

        status_records.append(
            {
                "policy_id": pid,
                "current_status": "proposed",
                "recommended_status": score["recommendation"],
                "rationale": score["recommendation_rationale"],
                "evidence": {
                    "would_fire_count": score["would_fire_count"],
                    "likely_helpful_count": score["likely_helpful_count"],
                    "likely_harmful_count": score["likely_harmful_count"],
                    "uncertain_count": score["uncertain_count"],
                    "false_positive_rate_estimate": score[
                        "false_positive_rate_estimate"
                    ],
                    "payment_risk_distribution": score["payment_risk_distribution"],
                    "domains_observed": score["domains_observed"],
                    "datasets_observed": score["datasets_observed"],
                },
            }
        )

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w") as f:
        yaml.dump(
            {"policy_status_recommendations": status_records},
            f,
            default_flow_style=False,
            sort_keys=False,
        )

    return output


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Update policy status based on shadow evaluation"
    )
    parser.add_argument(
        "--shadow-results",
        default="data/settlement_datasets/policy_shadow_eval/policy_shadow_results.jsonl",
    )
    parser.add_argument("--policies", default="data/settlement_datasets/policies.yaml")
    parser.add_argument(
        "--output", default="policies/review/policy_status_recommendations.yaml"
    )

    args = parser.parse_args()

    path = update_policy_status(args.shadow_results, args.policies, args.output)
    print(f"Wrote policy status recommendations -> {path}")

    with open(path) as f:
        data = yaml.safe_load(f)
    for rec in data.get("policy_status_recommendations", []):
        print(
            f"  {rec['policy_id']}: {rec['recommended_status']} — {rec['rationale'][:80]}"
        )


if __name__ == "__main__":
    main()
