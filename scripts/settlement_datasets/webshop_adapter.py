from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

from scripts.settlement_datasets.adapter_base import (
    EMPTY_LABELS,
    EMPTY_OUTCOME,
    SettlementDatasetAdapter,
    make_empty_environment,
    make_empty_payment,
    make_empty_representational_state,
)

_DEFAULT_FIXTURE = (
    Path(__file__).resolve().parent.parent.parent
    / "tests"
    / "fixtures"
    / "settlement_datasets"
    / "webshop"
    / "sample.jsonl"
)


class WebShopAdapter(SettlementDatasetAdapter):
    name = "webshop"
    domain = "shopping"
    source_uri = "fixture:webshop_style"

    def stream(
        self, limit: int | None = None, **kwargs: Any
    ) -> Iterator[dict[str, Any]]:
        input_path = Path(kwargs.get("input_path", str(_DEFAULT_FIXTURE)))
        count = 0
        with input_path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                yield json.loads(line)
                count += 1
                if limit is not None and count >= limit:
                    return

    def normalize_task(self, raw: dict[str, Any]) -> dict[str, Any]:
        return {
            "type": "action",
            "description": raw.get("instruction", ""),
            "settlement_target": "find_product_matching_all_constraints",
        }

    def extract_actions(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        actions: list[dict[str, Any]] = []
        trajectory = raw.get("trajectory", [])
        for turn_index, step in enumerate(trajectory):
            if step.get("role") != "assistant":
                continue
            action: dict[str, Any] = {
                "turn_index": turn_index,
                "role": "assistant",
                "action_type": step.get("action_type", "unknown"),
                "content": step.get("content", ""),
            }
            if step.get("action_type") == "search":
                action["query"] = step.get("query", "")
            if step.get("action_type") == "click":
                action["item_index"] = step.get("item_index")
            actions.append(action)
        return actions

    def extract_observations(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        observations: list[dict[str, Any]] = []
        trajectory = raw.get("trajectory", [])
        for turn_index, step in enumerate(trajectory):
            if step.get("role") != "tool":
                continue
            if step.get("action_type") != "observation":
                continue
            observations.append(
                {
                    "turn_index": turn_index,
                    "role": "tool",
                    "content": step.get("content", ""),
                }
            )
        return observations

    def extract_outcome(self, raw: dict[str, Any]) -> dict[str, Any]:
        reward = raw.get("reward", 0.0)
        chosen_item = raw.get("chosen_item")
        constraints = raw.get("constraints", [])
        success = reward >= 1.0 and chosen_item is not None

        evidence: list[str] = []
        if chosen_item is not None:
            evidence.append(f"chosen_item:{chosen_item.get('name', 'unknown')}")
        evidence.append(f"reward:{reward}")
        if constraints:
            evidence.append(f"constraint_count:{len(constraints)}")

        if success and chosen_item is not None:
            all_met = _check_constraints(chosen_item, constraints)
            if not all_met:
                success = False
                evidence.append("constraint_mismatch_detected")

        return {
            "success": success,
            "reward": reward,
            "score": reward,
            "settlement_quality": "success" if success else "failure",
            "confidence": 1.0 if reward in (0.0, 1.0) else 0.7,
            "evidence": evidence,
        }

    def extract_payment(self, raw: dict[str, Any]) -> dict[str, Any]:
        actions = self.extract_actions(raw)
        searches = sum(1 for a in actions if a["action_type"] == "search")
        clicks = sum(1 for a in actions if a["action_type"] == "click")
        buys = sum(1 for a in actions if a["action_type"] == "buy")
        total_steps = len(raw.get("trajectory", []))

        return {
            "turns": len(actions),
            "tool_calls": 0,
            "commands": searches,
            "page_actions": clicks + buys,
            "api_calls": 0,
            "elapsed_steps": total_steps,
            "error_count": 0,
            "estimated_complexity": _estimate_complexity(searches, clicks),
            "evidence": [
                f"searches:{searches}",
                f"clicks:{clicks}",
                f"buys:{buys}",
                f"total_steps:{total_steps}",
            ],
        }

    def infer_settlement_quality(
        self, raw: dict[str, Any], extracted: dict[str, Any]
    ) -> dict[str, Any]:
        reward = raw.get("reward", 0.0)
        actions = self.extract_actions(raw)
        searches = sum(1 for a in actions if a["action_type"] == "search")
        total = len(actions)

        if reward == 1.0 and searches >= 2:
            return {
                "settlement_quality": "recovered_success",
                "confidence": 0.8,
                "evidence": [f"reward:{reward}", f"searches:{searches}"],
            }
        if reward == 1.0 and total <= 4:
            return {
                "settlement_quality": "clean_success",
                "confidence": 0.9,
                "evidence": [f"reward:{reward}", f"steps:{total}"],
            }
        if 0.3 <= reward <= 0.7:
            return {
                "settlement_quality": "partial_success",
                "confidence": 0.6,
                "evidence": [f"reward:{reward}"],
            }
        if reward == 0.0 and searches >= 3:
            return {
                "settlement_quality": "failure_with_signal",
                "confidence": 0.7,
                "evidence": [f"reward:{reward}", f"searches:{searches}"],
            }
        if reward == 0.0 and total <= 2:
            return {
                "settlement_quality": "premature_closure",
                "confidence": 0.5,
                "evidence": [f"reward:{reward}", f"steps:{total}"],
            }
        return {
            "settlement_quality": "unknown",
            "confidence": 0.1,
            "evidence": [f"reward:{reward}"],
        }

    def to_settlement_record(self, raw: dict[str, Any]) -> dict[str, Any]:
        actions = self.extract_actions(raw)
        observations = self.extract_observations(raw)
        outcome = self.extract_outcome(raw)
        payment = self.extract_payment(raw)
        quality = self.infer_settlement_quality(raw, {})
        task = self.normalize_task(raw)

        searches = sum(1 for a in actions if a["action_type"] == "search")
        clicks = sum(1 for a in actions if a["action_type"] == "click")
        buys = sum(1 for a in actions if a["action_type"] == "buy")

        rep_state = _infer_representational_state(actions)
        environment = {
            "type": "web_shopping",
            "has_runnable_feedback": True,
            "feedback_type": "state_check",
        }

        labels = dict(EMPTY_LABELS)
        _apply_failure_labels(labels, raw, actions, searches)
        _apply_metabolization(labels, raw, outcome)

        constraints = raw.get("constraints", [])
        metadata = raw.get("metadata", {})
        metadata.update(
            {
                "constraint_count": len(constraints),
                "search_count": searches,
                "click_count": clicks,
            }
        )

        outcome["settlement_quality"] = quality["settlement_quality"]
        outcome["confidence"] = quality["confidence"]

        return {
            "dataset": self.name,
            "domain": self.domain,
            "task_id": raw.get("task_id", "unknown"),
            "source_uri": self.source_uri,
            "desired_direction": task,
            "environment": environment,
            "representational_state": rep_state,
            "payment": payment,
            "affordance_path": {
                "actions": actions,
                "observations": observations,
            },
            "outcome": outcome,
            "labels": labels,
            "metadata": metadata,
        }

    def validate_record(self, record: dict[str, Any]) -> list[str]:
        errors = super().validate_record(record)
        if record.get("domain") != "shopping":
            errors.append("domain_mismatch:expected_shopping")
        return errors


def _check_constraints(chosen_item: dict[str, Any], constraints: list[str]) -> bool:
    attrs = chosen_item.get("attrs", {})
    price = chosen_item.get("price")
    for constraint in constraints:
        if ":" not in constraint:
            continue
        key, value = constraint.split(":", 1)
        key = key.strip().lower()
        value = value.strip().lower()
        if key == "color" and attrs.get("color", "").lower() != value:
            return False
        if key == "price" and price is not None:
            if "under" in value or "below" in value:
                threshold = _extract_number(value)
                if threshold is not None and price > threshold:
                    return False
            if "over" in value or "above" in value:
                threshold = _extract_number(value)
                if threshold is not None and price < threshold:
                    return False
        if key == "ram" and attrs.get("ram", "").lower() != value:
            attr_ram = attrs.get("ram", "").lower()
            if value not in attr_ram:
                return False
    return True


def _extract_number(text: str) -> float | None:
    import re

    match = re.search(r"\$?(\d+(?:\.\d+)?)", text)
    if match:
        return float(match.group(1))
    return None


def _infer_representational_state(
    actions: list[dict[str, Any]],
) -> dict[str, Any]:
    searches = sum(1 for a in actions if a["action_type"] == "search")
    clicks = sum(1 for a in actions if a["action_type"] == "click")
    buys = sum(1 for a in actions if a["action_type"] == "buy")

    if searches <= 1 and clicks <= 1 and buys == 1:
        return {
            "start": "general",
            "desired": "specific",
            "path_shape": "direct_action_with_feedback",
            "confidence": 0.85,
            "evidence": ["single_search_to_click_to_buy"],
        }
    if searches >= 2 and clicks >= 1:
        return {
            "start": "general",
            "desired": "specific",
            "path_shape": "GA_to_SA_to_SC",
            "confidence": 0.75,
            "evidence": [
                f"multiple_searches:{searches}",
                "comparisons_before_selection",
            ],
        }
    return {
        "start": "general",
        "desired": "specific",
        "path_shape": "mixed_navigation",
        "confidence": 0.5,
        "evidence": [f"searches:{searches}", f"clicks:{clicks}", f"buys:{buys}"],
    }


def _apply_failure_labels(
    labels: dict[str, Any],
    raw: dict[str, Any],
    actions: list[dict[str, Any]],
    search_count: int,
) -> None:
    reward = raw.get("reward", 0.0)
    chosen_item = raw.get("chosen_item")
    constraints = raw.get("constraints", [])

    if reward == 0.0 and chosen_item is not None:
        if not _check_constraints(chosen_item, constraints):
            labels["failure_mode"] = "constraint_miss"
            labels["failure_mode_confidence"] = 0.85
            labels["failure_mode_evidence"] = [
                f"chosen_item_violates_constraint:{chosen_item.get('name', 'unknown')}"
            ]

    clicks = sum(1 for a in actions if a["action_type"] == "click")
    buys = sum(1 for a in actions if a["action_type"] == "buy")
    if buys >= 1 and clicks == 0 and reward < 1.0:
        labels["failure_mode"] = "premature_choice"
        labels["failure_mode_confidence"] = 0.8
        labels["failure_mode_evidence"] = ["bought_without_clicking_to_inspect"]

    if search_count > 5:
        existing = labels.get("failure_mode")
        if existing is None:
            labels["failure_mode"] = "over_search"
            labels["failure_mode_confidence"] = 0.7
            labels["failure_mode_evidence"] = [f"search_count:{search_count}"]
        else:
            labels["failure_mode_evidence"].append(
                f"over_search:search_count:{search_count}"
            )

    action_types = {a["action_type"] for a in actions}
    known_types = {"search", "click", "buy"}
    unknown_types = action_types - known_types
    if unknown_types:
        labels["failure_mode"] = "missing_affordance"
        labels["failure_mode_confidence"] = 0.6
        labels["failure_mode_evidence"] = [
            f"unrecognized_action_types:{sorted(unknown_types)}"
        ]


def _apply_metabolization(
    labels: dict[str, Any],
    raw: dict[str, Any],
    outcome: dict[str, Any],
) -> None:
    if outcome.get("success"):
        actions = raw.get("trajectory", [])
        has_compare = any(
            s.get("action_type") == "click"
            for s in actions
            if s.get("role") == "assistant"
        )
        if has_compare:
            labels["metabolization_candidate"] = "compare_constraints_before_selection"
            labels["metabolization_candidate_confidence"] = 0.8
            labels["metabolization_candidate_evidence"] = [
                "successful_comparison_and_purchase"
            ]
        else:
            labels["metabolization_candidate"] = "search_before_patch"
            labels["metabolization_candidate_confidence"] = 0.6
            labels["metabolization_candidate_evidence"] = [
                "direct_search_to_buy_without_comparison"
            ]


def _estimate_complexity(searches: int, clicks: int) -> str:
    total = searches + clicks
    if total <= 2:
        return "low"
    if total <= 5:
        return "medium"
    return "high"
