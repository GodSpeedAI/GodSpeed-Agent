from __future__ import annotations

from pathlib import Path

from scripts.settlement_datasets.action_ontology import (
    compare_normalized_actions,
    load_action_ontology,
    normalize_eval_behavior,
    normalize_policy_action,
)


ONTOLOGY_PATH = Path("configs/settlement_datasets/harness_action_ontology.yaml")


def test_load_action_ontology_contains_required_actions():
    ontology = load_action_ontology(ONTOLOGY_PATH)
    actions = ontology["actions"]
    assert "require_reflection" in actions
    assert "require_settlement_evidence" in actions
    assert "reset_plan" in actions
    assert "require_constraint_match" in actions
    assert "require_intermediate_representation" in actions


def test_normalize_policy_action_structured_reflection():
    ontology = load_action_ontology(ONTOLOGY_PATH)
    normalized = normalize_policy_action(
        {
            "require_operator": "reflection",
            "block_next_action_until": "revised_plan_exists",
        },
        ontology,
    )

    assert normalized["canonical_action"] == "require_reflection"
    assert normalized["confidence"] >= 0.8
    assert normalized["matched_evidence"]


def test_normalize_policy_action_structured_verification():
    ontology = load_action_ontology(ONTOLOGY_PATH)
    normalized = normalize_policy_action(
        {
            "require_operator": "verification_step",
            "block": "answer_without_test_or_settlement_signal",
        },
        ontology,
    )

    assert normalized["canonical_action"] == "require_settlement_evidence"
    assert normalized["confidence"] >= 0.8


def test_normalize_eval_behavior_verification_phrase():
    ontology = load_action_ontology(ONTOLOGY_PATH)
    normalized = normalize_eval_behavior(
        "Agent must verify answer before submitting.",
        ontology,
    )

    assert normalized["canonical_action"] == "require_settlement_evidence"
    assert normalized["confidence"] >= 0.8


def test_exact_semantic_match_for_verification_behavior():
    ontology = load_action_ontology(ONTOLOGY_PATH)
    policy_action = normalize_policy_action(
        {
            "require_operator": "verification_step",
            "block": "answer_without_test_or_settlement_signal",
        },
        ontology,
    )
    eval_behavior = normalize_eval_behavior(
        "Agent must verify answer before submitting.",
        ontology,
    )

    result = compare_normalized_actions(policy_action, eval_behavior)
    assert result["match_category"] == "exact_semantic_match"
    assert result["semantic_match"] is True
    assert result["match_confidence"] == 1.0


def test_partial_semantic_match_for_replan_after_error():
    ontology = load_action_ontology(ONTOLOGY_PATH)
    policy_action = normalize_policy_action(
        {
            "require_operator": "reflection",
            "block_next_action_until": "revised_plan_exists",
        },
        ontology,
    )
    eval_behavior = normalize_eval_behavior(
        "Agent must break tool loop and propose alternative approach.",
        ontology,
    )

    result = compare_normalized_actions(policy_action, eval_behavior)
    assert result["match_category"] == "partial_semantic_match"
    assert result["semantic_match"] is True
    assert 0.0 < result["match_confidence"] < 1.0


def test_mismatch_when_actions_are_semantically_different():
    ontology = load_action_ontology(ONTOLOGY_PATH)
    policy_action = normalize_policy_action(
        {
            "require_operator": "constraint_verification",
            "block": "selection_without_comparison",
        },
        ontology,
    )
    eval_behavior = normalize_eval_behavior(
        "Agent must verify answer before submitting.",
        ontology,
    )

    result = compare_normalized_actions(policy_action, eval_behavior)
    assert result["match_category"] == "mismatch"
    assert result["semantic_match"] is False


def test_unknown_policy_action_is_explicit():
    ontology = load_action_ontology(ONTOLOGY_PATH)
    policy_action = normalize_policy_action(
        {"require_operator": "totally_new_operator", "block": "opaque_barrier"},
        ontology,
    )

    assert policy_action["canonical_action"] is None
    assert policy_action["unmatched_tokens"]


def test_unknown_eval_behavior_is_explicit():
    ontology = load_action_ontology(ONTOLOGY_PATH)
    eval_behavior = normalize_eval_behavior(
        "Agent should sing a song about the result.",
        ontology,
    )

    assert eval_behavior["canonical_action"] is None
    assert eval_behavior["unmatched_tokens"]


def test_insufficient_evidence_when_eval_behavior_is_empty():
    ontology = load_action_ontology(ONTOLOGY_PATH)
    policy_action = normalize_policy_action(
        {
            "require_operator": "verification_step",
            "block": "answer_without_test_or_settlement_signal",
        },
        ontology,
    )
    eval_behavior = normalize_eval_behavior("", ontology)

    result = compare_normalized_actions(policy_action, eval_behavior)
    assert result["match_category"] == "insufficient_evidence"
    assert result["semantic_match"] is False
