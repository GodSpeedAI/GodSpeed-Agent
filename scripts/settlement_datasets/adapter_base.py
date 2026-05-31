from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Iterator


EMPTY_OUTCOME: dict[str, Any] = {
    "success": None,
    "reward": None,
    "score": None,
    "settlement_quality": "unknown",
    "confidence": 0.0,
    "evidence": [],
}

EMPTY_LABELS: dict[str, Any] = {
    "failure_mode": None,
    "failure_mode_confidence": 0.0,
    "failure_mode_evidence": [],
    "harness_policy_signal": None,
    "harness_policy_signal_confidence": 0.0,
    "harness_policy_signal_evidence": [],
    "metabolization_candidate": None,
    "metabolization_candidate_confidence": 0.0,
    "metabolization_candidate_evidence": [],
}

CANONICAL_FIELDS: set[str] = {
    "dataset",
    "domain",
    "task_id",
    "source_uri",
    "desired_direction",
    "environment",
    "representational_state",
    "payment",
    "affordance_path",
    "outcome",
    "labels",
    "metadata",
}

REQUIRED_PAYMENT_FIELDS: set[str] = {
    "turns",
    "tool_calls",
    "commands",
    "page_actions",
    "api_calls",
    "elapsed_steps",
    "error_count",
    "estimated_complexity",
    "evidence",
}

REQUIRED_OUTCOME_FIELDS: set[str] = {
    "success",
    "reward",
    "score",
    "settlement_quality",
    "confidence",
    "evidence",
}

REQUIRED_LABELS_FIELDS: set[str] = {
    "failure_mode",
    "failure_mode_confidence",
    "failure_mode_evidence",
    "harness_policy_signal",
    "harness_policy_signal_confidence",
    "harness_policy_signal_evidence",
    "metabolization_candidate",
    "metabolization_candidate_confidence",
    "metabolization_candidate_evidence",
}


class SettlementDatasetAdapter(ABC):
    name: str
    domain: str
    source_uri: str

    @abstractmethod
    def stream(
        self, limit: int | None = None, **kwargs: Any
    ) -> Iterator[dict[str, Any]]: ...

    @abstractmethod
    def normalize_task(self, raw: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def extract_actions(self, raw: dict[str, Any]) -> list[dict[str, Any]]: ...

    @abstractmethod
    def extract_observations(self, raw: dict[str, Any]) -> list[dict[str, Any]]: ...

    @abstractmethod
    def extract_outcome(self, raw: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def extract_payment(self, raw: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def infer_settlement_quality(
        self, raw: dict[str, Any], extracted: dict[str, Any]
    ) -> dict[str, Any]: ...

    @abstractmethod
    def to_settlement_record(self, raw: dict[str, Any]) -> dict[str, Any]: ...

    def validate_record(self, record: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        for field in CANONICAL_FIELDS:
            if field not in record:
                errors.append(f"missing_required_field:{field}")

        payment = record.get("payment", {})
        for pf in REQUIRED_PAYMENT_FIELDS:
            if pf not in payment:
                errors.append(f"missing_payment_field:{pf}")

        outcome = record.get("outcome", {})
        for of_ in REQUIRED_OUTCOME_FIELDS:
            if of_ not in outcome:
                errors.append(f"missing_outcome_field:{of_}")

        labels = record.get("labels", {})
        for lf in REQUIRED_LABELS_FIELDS:
            if lf not in labels:
                errors.append(f"missing_labels_field:{lf}")

        return errors


def make_empty_payment() -> dict[str, Any]:
    return {
        "turns": 0,
        "tool_calls": 0,
        "commands": 0,
        "page_actions": 0,
        "api_calls": 0,
        "elapsed_steps": 0,
        "error_count": 0,
        "estimated_complexity": "unknown",
        "evidence": [],
    }


def make_empty_representational_state() -> dict[str, Any]:
    return {
        "start": "unknown",
        "desired": "unknown",
        "path_shape": "unknown",
        "confidence": 0.0,
        "evidence": [],
    }


def make_empty_environment() -> dict[str, Any]:
    return {
        "type": "unknown",
        "has_runnable_feedback": False,
        "feedback_type": "unknown",
    }


def write_records_jsonl(records: list[dict[str, Any]], output_path: str | Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, sort_keys=True) + "\n")
    return output_path


def read_records_jsonl(input_path: str | Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with Path(input_path).open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records
