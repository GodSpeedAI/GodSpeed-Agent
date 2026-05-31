from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


EVAL_SUITES = {
    "premature_closure": {
        "failure_mode": "premature_closure",
        "expected_harness_behavior": "require reflection",
        "settlement_criteria": "Agent must show settlement evidence before providing final answer.",
    },
    "tool_thrashing": {
        "failure_mode": "tool_thrashing",
        "expected_harness_behavior": "require revised plan",
        "settlement_criteria": "Agent must break tool loop and propose alternative approach.",
    },
    "failed_recovery": {
        "failure_mode": "failed_recovery",
        "expected_harness_behavior": "require reflection",
        "settlement_criteria": "Agent must adjust strategy after error, not repeat same action.",
    },
    "direct_jump_failures": {
        "failure_mode": "representation_jump",
        "expected_harness_behavior": "route through intermediate representational state",
        "settlement_criteria": "Agent must pass through intermediate representational state before concrete action.",
    },
    "payment_spirals": {
        "failure_mode": "payment_spiral",
        "expected_harness_behavior": "reset plan",
        "settlement_criteria": "Agent must recognize unproductive payment and trigger positive disintegration.",
    },
    "brittle_successes": {
        "failure_mode": "brittle_success",
        "expected_harness_behavior": "require settlement evidence",
        "settlement_criteria": "Success must be verified as metabolized, not fragile coincidence.",
    },
    "successful_recovery_patterns": {
        "failure_mode": None,
        "settlement_quality": "recovered_success",
        "expected_harness_behavior": "record recovery pattern as metabolization candidate",
        "settlement_criteria": "Successful recovery from error demonstrates adaptive capability.",
    },
}


def build_eval_suites(
    settlement_path: str | Path,
    output_dir: str | Path = "evals/agenttrove",
    min_confidence: float = 0.65,
) -> dict[str, Path]:
    settlement_path = Path(settlement_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    settlements: list[dict[str, Any]] = []
    with settlement_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            settlements.append(json.loads(line))

    written: dict[str, Path] = {}

    for suite_name, suite_config in EVAL_SUITES.items():
        items: list[dict[str, Any]] = []
        target_failure_mode = suite_config.get("failure_mode")
        target_quality = suite_config.get("settlement_quality")

        for s in settlements:
            confidence = s.get("outcome", {}).get("confidence", 0.0)
            if confidence < min_confidence:
                continue

            fm = s.get("cognitive_os_labels", {}).get("failure_mode")
            modes = fm if isinstance(fm, list) else [fm] if fm else []
            sq = s.get("outcome", {}).get("settlement_quality", "")

            if target_failure_mode and target_failure_mode in modes:
                pass
            elif target_quality and sq == target_quality:
                pass
            else:
                continue

            messages_summary = _summarize_messages(s)
            items.append(
                {
                    "trace_id": s.get("trace_id", ""),
                    "source": s.get("source", ""),
                    "input_context": messages_summary[:500],
                    "observed_failure_mode": target_failure_mode or sq,
                    "expected_harness_behavior": suite_config[
                        "expected_harness_behavior"
                    ],
                    "settlement_criteria": suite_config["settlement_criteria"],
                    "confidence": confidence,
                    "evidence": {
                        "settlement_quality": sq,
                        "failure_modes": modes,
                        "payment": s.get("payment", {}),
                        "path_shape": s.get("representational_state", {}).get(
                            "path_shape", ""
                        ),
                        "label_evidence": s.get("label_evidence", {}),
                    },
                }
            )

        output_path = output_dir / f"{suite_name}.jsonl"
        with output_path.open("w", encoding="utf-8") as handle:
            for item in items:
                handle.write(json.dumps(item, sort_keys=True) + "\n")
        written[suite_name] = output_path

    return written


def _summarize_messages(s: dict[str, Any]) -> str:
    actions = s.get("affordance_path", {}).get("actions", [])
    parts: list[str] = []
    for a in actions[:5]:
        role = a.get("role", "")
        is_cmd = a.get("is_command", False)
        parts.append(f"[{role}] {'(cmd)' if is_cmd else '(text)'}")
    return " | ".join(parts) if parts else "No actions recorded."


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build eval suites from settlement traces."
    )
    parser.add_argument(
        "--input",
        type=str,
        default="data/agenttrove/settlements/settlement_traces.jsonl",
    )
    parser.add_argument("--output-dir", type=str, default="evals/agenttrove")
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.65,
        help="Minimum label confidence to include in eval suites.",
    )
    args = parser.parse_args()

    written = build_eval_suites(args.input, args.output_dir, args.min_confidence)
    for name, path in sorted(written.items()):
        count = sum(1 for _ in path.open("r"))
        print(f"  {name}: {count} items -> {path}")


if __name__ == "__main__":
    main()
