from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml


DEFAULT_ONTOLOGY_PATH = Path("configs/settlement_datasets/harness_action_ontology.yaml")
GENERIC_TOKENS = {
    "action",
    "agent",
    "answer",
    "before",
    "block",
    "call",
    "continue",
    "exists",
    "final",
    "must",
    "next",
    "operator",
    "require",
    "required",
    "should",
    "signal",
    "step",
    "task",
    "until",
}


def load_action_ontology(path: str | Path = DEFAULT_ONTOLOGY_PATH) -> dict[str, Any]:
    ontology_path = Path(path)
    with ontology_path.open() as f:
        data = yaml.safe_load(f) or {}
    data.setdefault("actions", {})
    return data


def _normalize_text(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value.lower()).split())


def _tokenize(value: str) -> list[str]:
    return [
        token
        for token in _normalize_text(value).split()
        if len(token) > 2 and token not in GENERIC_TOKENS
    ]


def _flatten_value(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        phrases: list[str] = []
        for key, nested in value.items():
            phrases.append(f"{key} {nested}")
            phrases.extend(_flatten_value(key))
            phrases.extend(_flatten_value(nested))
        return phrases
    if isinstance(value, (list, tuple, set)):
        phrases: list[str] = []
        for item in value:
            phrases.extend(_flatten_value(item))
        return phrases
    return [str(value)]


def _entry_phrases(entry: dict[str, Any], role: str) -> list[str]:
    phrases = [entry.get("description", "")]
    phrases.extend(entry.get("aliases", []))
    if role == "policy":
        phrases.extend(_flatten_value(entry.get("compatible_policy_actions", [])))
    else:
        phrases.extend(_flatten_value(entry.get("compatible_eval_behaviors", [])))
    return [phrase for phrase in phrases if phrase]


def _score_phrase(raw_text: str, phrase: str) -> tuple[float, list[str]]:
    raw_norm = _normalize_text(raw_text)
    phrase_norm = _normalize_text(phrase)
    if not raw_norm or not phrase_norm:
        return 0.0, []

    raw_tokens = set(_tokenize(raw_norm))
    phrase_tokens = set(_tokenize(phrase_norm))
    if not raw_tokens or not phrase_tokens:
        return 0.0, []

    overlap = raw_tokens & phrase_tokens
    if raw_norm == phrase_norm:
        return 1.0, sorted(overlap)
    if phrase_norm in raw_norm or raw_norm in phrase_norm:
        return max(0.9, len(overlap) / max(1, len(phrase_tokens))), sorted(overlap)

    coverage = len(overlap) / max(1, len(phrase_tokens))
    precision = len(overlap) / max(1, len(raw_tokens))
    score = round((coverage * 0.7) + (precision * 0.3), 3)
    return score, sorted(overlap)


def _normalize(raw: Any, ontology: dict[str, Any], role: str) -> dict[str, Any]:
    raw_text = " ".join(_flatten_value(raw))
    raw_tokens = _tokenize(raw_text)
    best_action: str | None = None
    best_confidence = 0.0
    best_evidence: list[str] = []
    best_family: str | None = None

    for action_id, entry in ontology.get("actions", {}).items():
        for phrase in _entry_phrases(entry, role):
            score, overlap = _score_phrase(raw_text, phrase)
            if score > best_confidence:
                best_action = action_id
                best_confidence = score
                best_evidence = overlap or [_normalize_text(phrase)]
                best_family = entry.get("family")

    if best_confidence < 0.45:
        best_action = None
        best_family = None
        best_evidence = []

    unmatched = [token for token in raw_tokens if token not in best_evidence]
    return {
        "raw": raw,
        "canonical_action": best_action,
        "family": best_family,
        "confidence": round(best_confidence, 3),
        "matched_evidence": best_evidence,
        "unmatched_tokens": unmatched,
    }


def normalize_policy_action(raw_action: Any, ontology: dict[str, Any]) -> dict[str, Any]:
    return _normalize(raw_action, ontology, role="policy")


def normalize_eval_behavior(raw_behavior: Any, ontology: dict[str, Any]) -> dict[str, Any]:
    return _normalize(raw_behavior, ontology, role="eval")


def compare_normalized_actions(
    policy_action: dict[str, Any],
    eval_behavior: dict[str, Any],
) -> dict[str, Any]:
    if not " ".join(_flatten_value(eval_behavior.get("raw"))):
        return {
            "semantic_match": False,
            "match_category": "insufficient_evidence",
            "match_confidence": 0.0,
            "match_evidence": [],
            "mismatch_reason": "Eval replay item has no expected behavior text to normalize.",
        }

    if policy_action.get("canonical_action") is None:
        return {
            "semantic_match": False,
            "match_category": "unknown_policy_action",
            "match_confidence": 0.0,
            "match_evidence": [],
            "mismatch_reason": "Policy action could not be normalized to the canonical ontology.",
        }

    if eval_behavior.get("canonical_action") is None:
        return {
            "semantic_match": False,
            "match_category": "unknown_eval_behavior",
            "match_confidence": 0.0,
            "match_evidence": [],
            "mismatch_reason": "Eval expected behavior could not be normalized to the canonical ontology.",
        }

    if policy_action["canonical_action"] == eval_behavior["canonical_action"]:
        confidence = min(policy_action.get("confidence", 0.0), eval_behavior.get("confidence", 0.0))
        category = "exact_semantic_match" if confidence >= 0.75 else "partial_semantic_match"
        return {
            "semantic_match": True,
            "match_category": category,
            "match_confidence": 1.0 if category == "exact_semantic_match" else 0.5,
            "match_evidence": sorted(
                set(policy_action.get("matched_evidence", []))
                | set(eval_behavior.get("matched_evidence", []))
            ),
            "mismatch_reason": None,
        }

    if (
        policy_action.get("family")
        and policy_action.get("family") == eval_behavior.get("family")
    ):
        return {
            "semantic_match": True,
            "match_category": "partial_semantic_match",
            "match_confidence": 0.5,
            "match_evidence": [policy_action["family"]],
            "mismatch_reason": None,
        }

    return {
        "semantic_match": False,
        "match_category": "mismatch",
        "match_confidence": 0.0,
        "match_evidence": [],
        "mismatch_reason": (
            f"Canonical actions differ: {policy_action.get('canonical_action')} vs "
            f"{eval_behavior.get('canonical_action')}."
        ),
    }
