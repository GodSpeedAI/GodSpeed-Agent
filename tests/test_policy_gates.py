from godspeed_nav.policies import PolicyDecision, enforce_absorption_review, enforce_disintegration_review
from godspeed_nav.runtime import NavigationRuntime


def test_unaffordable_candidate_is_blocked_when_policy_requires_blocking(tmp_path):
    runtime = NavigationRuntime(
        tmp_path / ".godspeed-harness",
        policy={"block_unaffordable_actions": True},
    )
    direction = runtime.start_direction(label="Safety", statement="Avoid unaffordable transformations")

    review = runtime.review_horizon(
        direction_id=direction["id"],
        candidates=[
            {
                "id": "risky",
                "statement": "Large risky move",
                "pathway": "one big migration",
                "costs": {"time": 100, "risk": 100},
                "capacities": {"time": 1, "risk": 1},
                "expected_horizon_delta": 10,
                "risk": 10,
            }
        ],
    )

    assert review["policy_decisions"][0]["decision"] == "block"
    assert review["policy_decisions"][0]["code"] == "unaffordable_action"
    assert review["next_affordance"] is None


def test_absorption_requires_human_review_when_configured():
    decision = enforce_absorption_review(
        proposal={"id": "absorb-1", "pathway": "patch plan"},
        policy={"require_human_review_for_absorption": True},
    )

    assert decision == PolicyDecision(
        decision="requires_review",
        code="human_review_required",
        reason="Absorption requires human review before execution.",
    )


def test_disintegration_requires_human_review_when_configured():
    decision = enforce_disintegration_review(
        candidate={"id": "old-process", "risk": "low"},
        policy={"require_human_review_for_disintegration": True},
    )

    assert decision.decision == "requires_review"
    assert decision.code == "human_review_required"


def test_policy_allows_review_when_human_review_disabled():
    decision = enforce_absorption_review(
        proposal={"id": "absorb-1", "pathway": "patch plan"},
        policy={"require_human_review_for_absorption": False},
    )

    assert decision.decision == "allow"
