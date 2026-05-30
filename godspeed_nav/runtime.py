from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from godspeed_nav.metrics import estimate_payment, rank_affordances, score_settlement
from godspeed_nav.schemas import now_iso
from godspeed_nav.storage import LedgerStore
from godspeed_nav.trajectory import update_trajectory


class NavigationRuntime:
    """Coordinates the developmental loop over local ledgers."""

    def __init__(self, storage_root: str | Path):
        self.store = LedgerStore(storage_root)

    def start_direction(
        self,
        label: str,
        statement: str,
        kind: str = "goal",
        source: str | None = None,
    ) -> dict[str, Any]:
        direction = {
            "id": f"dir-{uuid4().hex}",
            "label": label,
            "kind": kind,
            "statement": statement,
            "source": source,
            "status": "active",
            "horizon_id": f"hor-{uuid4().hex}",
            "created_at": now_iso(),
        }
        self.store.append("desired_directions", direction)
        self.store.append(
            "horizons",
            {
                "id": direction["horizon_id"],
                "observer_id": "local-operator",
                "visible_affordance_ids": [],
                "potential_ids": [],
                "capability_basis": [],
                "substrate_basis": [],
                "radius": 1.0,
                "created_at": now_iso(),
                "updated_at": now_iso(),
            },
        )
        return direction

    def review_horizon(
        self,
        direction_id: str,
        candidates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        affordances: list[dict[str, Any]] = []
        payments: dict[str, dict[str, float]] = {}
        rejected: list[dict[str, Any]] = []

        for candidate in candidates:
            candidate_id = candidate["id"]
            if not candidate.get("pathway"):
                record = self._potential_record(direction_id, candidate, "missing_pathway")
                self.store.append("potentials", record)
                rejected.append({"id": candidate_id, "reason": "missing_pathway"})
                continue

            payment = estimate_payment(
                candidate.get("costs", {}),
                candidate.get("weights", {}),
                candidate.get("capacities", {}),
            )
            payment_record = {
                "id": f"pay-{uuid4().hex}",
                "affordance_id": candidate_id,
                "dimensions": candidate.get("costs", {}),
                **payment,
                "created_at": now_iso(),
            }
            self.store.append("payments", payment_record)

            if payment["spendability"] != "affordable":
                self.store.append(
                    "possibilities",
                    {
                        "id": candidate_id,
                        "direction_id": direction_id,
                        "statement": candidate.get("statement", ""),
                        "candidate_pathway": candidate.get("pathway", ""),
                        "unknowns": ["payment_exceeds_capacity"],
                        "current_status": "possibility",
                        "created_at": now_iso(),
                    },
                )
                rejected.append({"id": candidate_id, "reason": "unaffordable"})
                continue

            affordance = {
                "id": candidate_id,
                "direction_id": direction_id,
                "statement": candidate.get("statement", ""),
                "pathway": candidate["pathway"],
                "expected_horizon_delta": candidate.get("expected_horizon_delta", 0),
                "risk": candidate.get("risk", 0),
                "payment_id": payment_record["id"],
                "current_status": "affordance",
                "created_at": now_iso(),
            }
            self.store.append("affordances", affordance)
            affordances.append(affordance)
            payments[candidate_id] = payment

        ranked = rank_affordances(affordances, payments)
        review = {
            "direction_id": direction_id,
            "ranked_affordances": ranked["ranked_affordances"],
            "next_affordance": ranked["next_recommended_affordance"],
            "rejected_candidates": rejected + ranked["rejected_candidates"],
            "created_at": now_iso(),
        }
        self.store.append("horizon_reviews", review)
        return review

    def record_settlement(
        self,
        affordance_id: str,
        before_state: dict[str, Any],
        after_state: dict[str, Any],
        payment_actual: dict[str, float],
        evidence: list[str],
        horizon_delta: float,
    ) -> dict[str, Any]:
        settlement_result = score_settlement(
            before_state,
            after_state,
            {"affordance_id": affordance_id},
            payment_actual,
            {"evidence": evidence},
        )
        settlement = {
            "id": f"set-{uuid4().hex}",
            "affordance_id": affordance_id,
            "before_state": before_state,
            "after_state": after_state,
            "payment_actual": payment_actual,
            "score": settlement_result["settlement_score"],
            "status": settlement_result["status"],
            "evidence": evidence,
            "created_at": now_iso(),
        }
        self.store.append("settlements", settlement)

        previous = self._latest_trajectory()
        trajectory = update_trajectory(
            previous_theta=previous.get("new_theta", previous.get("theta", 0)),
            previous_radius=previous.get("new_radius", previous.get("radius", 1)),
            settlement_score=settlement["score"],
            horizon_delta=horizon_delta,
        )
        trajectory_record = {
            "id": f"traj-{uuid4().hex}",
            "settlement_id": settlement["id"],
            **trajectory,
            "created_at": now_iso(),
        }
        self.store.append("trajectories", trajectory_record)
        return {**settlement, "trajectory": trajectory}

    def snapshot(self) -> dict[str, Any]:
        ledgers = {
            "desired_directions": self.store.read("desired_directions"),
            "affordances": self.store.read("affordances"),
            "possibilities": self.store.read("possibilities"),
            "potentials": self.store.read("potentials"),
            "payments": self.store.read("payments"),
            "settlements": self.store.read("settlements"),
            "trajectories": self.store.read("trajectories"),
        }
        return {
            "counts": {name: len(records) for name, records in ledgers.items()},
            "active_directions": [
                item for item in ledgers["desired_directions"] if item.get("status") == "active"
            ],
            "latest_trajectory": ledgers["trajectories"][-1] if ledgers["trajectories"] else None,
        }

    def _potential_record(
        self,
        direction_id: str,
        candidate: dict[str, Any],
        reason: str,
    ) -> dict[str, Any]:
        return {
            "id": candidate["id"],
            "direction_id": direction_id,
            "statement": candidate.get("statement", ""),
            "required_capabilities": candidate.get("required_capabilities", []),
            "missing_pathway_reason": reason,
            "current_status": "potential",
            "created_at": now_iso(),
        }

    def _latest_trajectory(self) -> dict[str, Any]:
        trajectories = self.store.read("trajectories")
        return trajectories[-1] if trajectories else {}
