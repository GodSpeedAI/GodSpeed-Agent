from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from scripts.settlement_datasets.adapter_base import (
    read_records_jsonl,
    write_records_jsonl,
)


def update_metabolization_status(
    candidates_path: str,
    shadow_results_path: str | None = None,
    output_path: str = "data/settlement_datasets/metabolization_candidates/candidates_updated.jsonl",
) -> Path:
    candidates = read_records_jsonl(candidates_path)

    shadow_results = []
    if shadow_results_path:
        sp = Path(shadow_results_path)
        if sp.exists():
            shadow_results = read_records_jsonl(str(sp))

    helpful_policies: dict[str, int] = {}
    for r in shadow_results:
        if r.get("counterfactual_assessment") == "likely_helpful":
            pid = r.get("policy_id", "")
            helpful_policies[pid] = helpful_policies.get(pid, 0) + 1

    updated = []
    for cand in candidates:
        status = cand.get("metabolization_status", "candidate")
        trace_count = cand.get("supporting_trace_count", 0)

        if status == "candidate" and trace_count >= 3:
            status = "repeated"
            cand["status_change"] = (
                "candidate->repeated: cross-trace evidence supports repeated pattern"
            )
        elif status == "repeated":
            pattern_name = cand.get("pattern_name", "")
            pattern_helpful = any(
                pattern_name.replace("_", "") in pid.replace("_", "").lower()
                for pid in helpful_policies
            )
            if pattern_helpful and trace_count >= 5:
                status = "tested"
                cand["status_change"] = (
                    "repeated->tested: shadow-mode evaluation supports pattern"
                )
            elif trace_count >= 3:
                status = "repeated"
            else:
                status = "candidate"

        cand["metabolization_status"] = status
        if "metabolized" in cand.get("status_change", ""):
            cand["metabolization_status"] = status
            cand["status_change"] = (
                "blocked: metabolized requires live harness activation"
            )
        updated.append(cand)

    path = write_records_jsonl(updated, output_path)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Update metabolization candidate status"
    )
    parser.add_argument(
        "--candidates",
        default="data/settlement_datasets/metabolization_candidates/candidates.jsonl",
    )
    parser.add_argument(
        "--shadow-results",
        default="data/settlement_datasets/policy_shadow_eval/policy_shadow_results.jsonl",
    )
    parser.add_argument(
        "--output",
        default="data/settlement_datasets/metabolization_candidates/candidates_updated.jsonl",
    )

    args = parser.parse_args()

    path = update_metabolization_status(
        args.candidates, args.shadow_results, args.output
    )
    updated = read_records_jsonl(str(path))
    print(f"Updated {len(updated)} metabolization candidates -> {path}")
    for c in updated:
        change = c.get("status_change", "no change")
        print(f"  {c['pattern_name']}: {c['metabolization_status']} ({change})")


if __name__ == "__main__":
    main()
