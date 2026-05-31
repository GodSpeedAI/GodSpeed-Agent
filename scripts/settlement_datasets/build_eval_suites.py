from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.settlement_datasets.adapter_base import read_records_jsonl
from scripts.settlement_datasets.registry import available_datasets


EVAL_SUITES = {
    "premature_closure": {
        "failure_mode": "premature_closure",
        "settlement_quality": None,
    },
    "tool_thrashing": {"failure_mode": "tool_thrashing", "settlement_quality": None},
    "failed_recovery": {"failure_mode": "failed_recovery", "settlement_quality": None},
    "direct_jump_failures": {
        "failure_mode": "representation_jump",
        "settlement_quality": None,
    },
    "payment_spirals": {"failure_mode": "payment_spiral", "settlement_quality": None},
    "brittle_successes": {
        "failure_mode": "brittle_success",
        "settlement_quality": None,
    },
    "successful_recovery_patterns": {
        "failure_mode": None,
        "settlement_quality": "recovered_success",
    },
    "metabolization_candidates": {
        "failure_mode": None,
        "settlement_quality": None,
        "has_metab_candidate": True,
    },
}


def _summarize_context(record: dict[str, Any]) -> str:
    actions = record.get("affordance_path", {}).get("actions", [])[:5]
    parts = []
    for a in actions:
        content = str(a.get("content", ""))[:100]
        parts.append(f"{a.get('action_type', 'action')}: {content}")
    return "; ".join(parts)[:500]


def _expected_behavior(failure_mode: str | None, suite_name: str) -> str:
    behaviors = {
        "premature_closure": "Agent must verify answer before submitting.",
        "tool_thrashing": "Agent must break tool loop and propose alternative approach.",
        "failed_recovery": "Agent must recognize failed recovery and escalate or reset.",
        "direct_jump_failures": "Agent must use intermediate representation before action.",
        "payment_spirals": "Agent must recognize unproductive payment and trigger positive disintegration.",
        "brittle_successes": "Agent must verify result robustness, not just surface correctness.",
        "successful_recovery_patterns": "Agent should apply similar recovery strategy when facing errors.",
        "metabolization_candidates": "Agent should recognize reusable pattern and apply it.",
    }
    return behaviors.get(
        suite_name, "Agent must demonstrate improved settlement behavior."
    )


def build_eval_suites(
    records: list[dict[str, Any]],
    output_dir: str = "data/settlement_datasets/evals/",
    min_confidence: float = 0.65,
) -> dict[str, Path]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    results = {}
    for suite_name, criteria in EVAL_SUITES.items():
        items = []
        for rec in records:
            conf = rec.get("outcome", {}).get("confidence", 0.0)
            if conf < min_confidence:
                continue

            labels = rec.get("labels", {})
            fm = labels.get("failure_mode")
            sq = rec.get("outcome", {}).get("settlement_quality")
            has_metab = labels.get("metabolization_candidate") is not None

            if criteria.get("has_metab_candidate") and not has_metab:
                continue

            fm_match = (
                criteria.get("failure_mode") is None or fm == criteria["failure_mode"]
            )
            sq_match = (
                criteria.get("settlement_quality") is None
                or sq == criteria["settlement_quality"]
            )

            if fm_match and sq_match:
                items.append(
                    {
                        "dataset": rec.get("dataset", ""),
                        "trace_id": rec.get("task_id", ""),
                        "domain": rec.get("domain", ""),
                        "input_context": _summarize_context(rec),
                        "observed_failure_mode": fm or "none",
                        "expected_harness_behavior": _expected_behavior(fm, suite_name),
                        "settlement_criteria": f"Settlement quality: {sq or 'unknown'}, confidence: {conf}",
                        "confidence": conf,
                        "evidence": {
                            "settlement_quality": sq,
                            "failure_modes": [fm] if fm else [],
                            "payment": rec.get("payment", {}),
                            "path_shape": rec.get("representational_state", {}).get(
                                "path_shape", "unknown"
                            ),
                        },
                    }
                )

        suite_path = output_path / f"{suite_name}.jsonl"
        with suite_path.open("w") as f:
            for item in items:
                f.write(json.dumps(item, sort_keys=True) + "\n")

        results[suite_name] = suite_path
        print(f"  {suite_name}: {len(items)} items -> {suite_path}")

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Build eval suites across datasets")
    parser.add_argument(
        "--dataset",
        default="all",
        choices=["agenttrove", "swegym", "apibank", "webshop", "all"],
    )
    parser.add_argument("--input", default=None)
    parser.add_argument("--output", default="data/settlement_datasets/evals/")
    parser.add_argument("--min-confidence", type=float, default=0.65)

    args = parser.parse_args()
    datasets = available_datasets() if args.dataset == "all" else [args.dataset]

    all_records = []
    for ds in datasets:
        input_path = args.input or f"data/settlement_datasets/settlements/{ds}.jsonl"
        p = Path(input_path)
        if p.exists():
            all_records.extend(read_records_jsonl(str(p)))

    print(f"Building eval suites from {len(all_records)} records")
    build_eval_suites(
        all_records, output_dir=args.output, min_confidence=args.min_confidence
    )


if __name__ == "__main__":
    main()
