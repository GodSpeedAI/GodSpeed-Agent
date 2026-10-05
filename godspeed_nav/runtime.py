from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from godspeed_nav.metabolization import compute_metabolization, plan_repetition
from godspeed_nav.cognitive_model import rank_candidates_by_controller
from godspeed_nav.metrics import (
    estimate_payment,
    rank_affordances,
    review_representational_transition,
    score_settlement,
)
from godspeed_nav.policies import (
    enforce_payment_policy,
    enforce_representational_transition_policy,
)
from godspeed_nav.schemas import DomainRuleError, infer_capability_lifecycle, now_iso
from godspeed_nav.storage import LedgerStore
from godspeed_nav.trajectory import detect_circular_motion, update_trajectory


class NavigationRuntime:
    """Coordinates the developmental loop over local ledgers."""

    def __init__(self, storage_root: str | Path, policy: dict[str, Any] | None = None):
        self.store = LedgerStore(storage_root)
        self.policy = policy or {}

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

    def set_representational_state(
        self,
        direction_id: str,
        scope_position: str,
        mode_of_givenness_position: str,
        phase: str,
        radius: float,
        confidence: float,
        embodiment_position: str | None = None,
    ) -> dict[str, Any]:
        state = {
            "id": f"rep-{uuid4().hex}",
            "direction_id": direction_id,
            "scope_position": scope_position,
            "mode_of_givenness_position": mode_of_givenness_position,
            "embodiment_position": embodiment_position or mode_of_givenness_position,
            "phase": phase,
            "quadrant": f"{scope_position}_{mode_of_givenness_position}",
            "radius": radius,
            "confidence": confidence,
            "created_at": now_iso(),
        }
        self.store.append("representational_states", state)
        return state

    def review_horizon(
        self,
        direction_id: str,
        candidates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        affordances: list[dict[str, Any]] = []
        payments: dict[str, dict[str, float]] = {}
        rejected: list[dict[str, Any]] = []
        policy_decisions: list[dict[str, str]] = []

        for candidate in candidates:
            candidate_id = candidate["id"]
            if not candidate.get("pathway"):
                record = self._potential_record(
                    direction_id, candidate, "missing_pathway"
                )
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
            self.store.append_event("payments", payment_record)
            policy_decision = enforce_payment_policy(payment, self.policy)
            policy_decisions.append(policy_decision.to_dict())

            if (
                payment["spendability"] != "affordable"
                or policy_decision.decision == "block"
            ):
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
                "pathway_quality": float(candidate.get("pathway_quality", 0.5)),
                "expected_horizon_delta": candidate.get("expected_horizon_delta", 0),
                "risk": candidate.get("risk", 0),
                "payment_id": payment_record["id"],
                "current_status": "affordance",
                "created_at": now_iso(),
            }
            self.store.append("affordances", affordance)
            self.store.append(
                "affordance_paths",
                {
                    "id": f"path-{uuid4().hex}",
                    "affordance_id": candidate_id,
                    "direction_id": direction_id,
                    "statement": candidate.get("statement", ""),
                    "pathway": candidate["pathway"],
                    "required_preconditions": candidate.get(
                        "required_preconditions", []
                    ),
                    "transition_sequence": candidate.get(
                        "transition_sequence", [candidate["pathway"]]
                    ),
                    "expected_settlement": candidate.get("expected_settlement", {}),
                    "lifecycle_status": candidate.get("lifecycle_status", "candidate"),
                    "pathway_quality": float(candidate.get("pathway_quality", 0.5)),
                    "created_at": now_iso(),
                },
            )
            affordances.append(affordance)
            payments[candidate_id] = payment

        ranked = rank_affordances(affordances, payments)

        # Build advisory cognitive model output from accepted affordances.
        # Map affordance fields to the candidate shape expected by the
        # controller so that the cognitive model can rank them without
        # overriding existing runtime decisions.
        cognitive_candidates = []
        for aff in affordances:
            aff_id = aff["id"]
            pay = payments.get(aff_id, {})
            cognitive_candidates.append(
                {
                    "id": aff_id,
                    "governance_allowed": True,
                    "settlement_accessible": True,
                    "payment_required": pay.get("dimensions", {}),
                    "payment_capacity": {},
                    "risk": aff.get("risk", 0.0),
                    "debt": aff.get("debt", 0.0),
                    "expected_horizon_delta": aff.get("expected_horizon_delta", 0),
                    "direction_score": aff.get("direction_score", 0.0),
                    "burden": pay.get("payment_burden", 0.0),
                    "pathway": aff.get("pathway", ""),
                    "expected_settlement": aff.get("expected_settlement", {}),
                }
            )

        cognitive_model_output = {
            **rank_candidates_by_controller(
                cognitive_candidates,
                context=self.policy.get("context", "production"),
            ),
            "mode": "advisory",
        }

        review = {
            "direction_id": direction_id,
            "ranked_affordances": ranked["ranked_affordances"],
            "next_affordance": ranked["next_recommended_affordance"],
            "rejected_candidates": rejected + ranked["rejected_candidates"],
            "policy_decisions": policy_decisions,
            "cognitive_model": cognitive_model_output,
            "created_at": now_iso(),
        }
        self.store.append("horizon_reviews", review)
        return review

    # ------------------------------------------------------------------
    # T10 — Developmental memory -> next navigation (E10 / I12)
    # ------------------------------------------------------------------
    # The three methods below close the frozen E10/I12 boundary:
    # - ``get_developmental_memory`` projects durable history into a canonical
    #   DevelopmentalMemory envelope (memory_ledger -> godspeed_agent).
    # - ``ingest_developmental_memory`` validates a received envelope as GSA
    #   would on the next cycle (exclusive producer, identity, required fields).
    # - ``review_horizon_with_memory`` / ``rank_candidates_with_memory``
    #   implement the documented *gate-evaluation-after-memory* pattern:
    #   memory retrieval -> memory-informed scoring/boost -> HARD GATE
    #   evaluation (governance, payment, settlement, risk/debt ceilings).
    #   Memory is evidence that may reduce search burden (boost horizon/direction)
    #   but can NEVER flip a blocked gate to allowed. Historical capability
    #   evidence remains distinguishable from current affordance availability
    #   via the ``_historical_capability`` / ``_memory_influenced`` tags and
    #   via the envelope's ``capability_state`` vs the freshly computed
    #   ``current_status == 'affordance'``.
    # ------------------------------------------------------------------

    def get_developmental_memory(
        self,
        observer_or_system_id: str,
        domain_model_hash: str,
        *,
        parent_evidence_ids: list[str] | None = None,
        event_id: str | None = None,
        occurred_at: str | None = None,
    ) -> dict[str, Any]:
        """Project durable developmental history into a canonical DevelopmentalMemory envelope.

        This is the E10 retrieval seam (memory_ledger -> godspeed_agent). The
        envelope is derived ON DEMAND from the durable ``developmental_events``
        ledger via :func:`godspeed_nav.developmental_memory.build_developmental_memory_from_store`,
        so it reflects the same replay-through-the-gate truth that powers restart
        survival. Capability_state is computed honestly via
        ``infer_capability_lifecycle`` / ``compute_metabolization`` over the
        real settlement evidence — history cannot inflate into unearned
        capability.

        The returned envelope MUST be consumed as evidence in the next navigation
        cycle and then gated by current governance/payment/settlement checks
        (see :meth:`review_horizon_with_memory` / :meth:`rank_candidates_with_memory`).
        """
        from godspeed_nav.developmental_memory import (  # noqa: PLC0415 — lazy to keep graph flat
            build_developmental_memory_from_store,
        )

        return build_developmental_memory_from_store(
            self.store,
            observer_or_system_id=observer_or_system_id,
            domain_model_hash=domain_model_hash,
            parent_evidence_ids=parent_evidence_ids,
            event_id=event_id,
            occurred_at=occurred_at,
        )

    def ingest_developmental_memory(
        self,
        envelope: dict[str, Any],
        *,
        local_model_sha256: str | None = None,
        expected_observer_id: str | None = None,
    ) -> dict[str, Any]:
        """Validate a DevelopmentalMemory envelope as GSA on receipt (E10 consumer gate).

        Enforces exclusive producer (memory_ledger), canonical identity, required
        fields, namespace, and observer binding. Returns the validated summary.
        This gate runs BEFORE any navigation state is influenced — a refused
        envelope changes no horizon.
        """
        from godspeed_nav.developmental_memory import ingest_developmental_memory as _ingest  # noqa: PLC0415

        return _ingest(
            envelope,
            local_model_sha256=local_model_sha256,
            expected_observer_id=expected_observer_id,
        )

    def rank_candidates_with_memory(
        self,
        candidates: list[dict[str, Any]],
        developmental_memory: dict[str, Any] | None,
        *,
        context: str | None = None,
        boost_factor: float = 0.35,
    ) -> dict[str, Any]:
        """Rank navigation candidates with memory evidence, but AFTER hard gates.

        Gate-evaluation-after-memory pattern (E10/I12):

        1. Retrieval: caller already obtained ``developmental_memory`` via
           :meth:`get_developmental_memory` (or supplies None for empty history).
        2. Memory-informed scoring: candidates whose ``id`` echoes historical
           capability evidence receive a modest boost to ``expected_horizon_delta``
           / ``direction_score`` (reduced search burden) via
           :func:`godspeed_nav.developmental_memory.apply_developmental_memory_to_candidates`.
        3. Hard-gate evaluation: every boosted candidate is then evaluated through
           :func:`godspeed_nav.cognitive_model.evaluate_candidate_model` — governance
           (``governance_allowed``), settlement access (``settlement_accessible``),
           payment capacity (``payment_required`` vs ``payment_capacity``), and
           risk/debt ceilings. A candidate blocked on current state remains blocked
           regardless of historical success.

        Returns ``{"ranked": [...], "rejected": [...], "memory_applied": bool,
        "memory_event_id": str|None}`` — the ``ranked`` list is ordered by the
        controller objective (lower is better). Historical evidence is tagged
        distinctly (``_historical_capability``) from current affordance
        availability (``allowed == True``).
        """
        from godspeed_nav.cognitive_model import rank_candidates_by_controller  # noqa: PLC0415
        from godspeed_nav.developmental_memory import (  # noqa: PLC0415
            apply_developmental_memory_to_candidates,
        )

        ctx = context or self.policy.get("context", "production")
        influenced = apply_developmental_memory_to_candidates(
            candidates, developmental_memory, boost_factor=boost_factor
        )
        ranked_result = rank_candidates_by_controller(influenced, context=ctx)
        # Attach memory provenance to the result for auditability
        mem_id = developmental_memory.get("event_id") if isinstance(developmental_memory, dict) else None
        return {
            **ranked_result,
            "memory_applied": developmental_memory is not None,
            "memory_event_id": mem_id,
            "influenced_candidates": influenced,
        }

    def review_horizon_with_memory(
        self,
        direction_id: str,
        candidates: list[dict[str, Any]],
        developmental_memory: dict[str, Any] | None = None,
        *,
        observer_or_system_id: str | None = None,
        domain_model_hash: str | None = None,
    ) -> dict[str, Any]:
        """Horizon review that measurably incorporates developmental memory while preserving hard gates.

        This is the production navigation entry point for E10: durable history
        may reduce orchestration burden, but current governance/payment/settlement
        gates are evaluated AFTER memory — memory never creates an affordance.

        If ``developmental_memory`` is None and both ``observer_or_system_id``
        and ``domain_model_hash`` are supplied, the memory is retrieved on
        demand via :meth:`get_developmental_memory`. When memory is absent
        (no prior history) the method degenerates to the plain
        :meth:`review_horizon` behavior with zero boost.

        The returned review is persisted to ``horizon_reviews`` with an
        additional ``developmental_memory_ref`` field for provenance, and its
        ``ranked_affordances`` ordering reflects the memory-informed, gate-checked
        ranking.
        """
        from godspeed_nav.developmental_memory import (  # noqa: PLC0415
            apply_developmental_memory_to_candidates,
        )

        # Retrieval seam (E10) — on-demand projection when not supplied
        memory = developmental_memory
        if memory is None and observer_or_system_id and domain_model_hash:
            try:
                memory = self.get_developmental_memory(
                    observer_or_system_id=observer_or_system_id,
                    domain_model_hash=domain_model_hash,
                )
            except Exception:
                memory = None

        # Gate-evaluation-after-memory: influence THEN hard-gate check
        # We apply the same pattern as rank_candidates_with_memory but at the
        # affordance-review layer: memory boosts expected_horizon_delta/direction_score
        # before payment/policy gates. Candidates that are currently unaffordable or
        # lack a pathway remain rejected; memory does not manufacture a pathway.
        influenced_candidates = apply_developmental_memory_to_candidates(candidates, memory)
        review = self.review_horizon(direction_id, influenced_candidates)
        # Annotate review with memory provenance (if any) without mutating its ledger copy
        if memory is not None:
            review["developmental_memory_ref"] = memory.get("event_id")
            review["developmental_memory_capability_state"] = memory.get("payload", {}).get("capability_state")
            # Also expose which candidates were memory-influenced for test observability
            review["memory_influenced_ids"] = [
                c["id"] for c in influenced_candidates if c.get("_memory_influenced")
            ]
        else:
            review["developmental_memory_ref"] = None
            review["memory_influenced_ids"] = []
        # Persist the annotated review again with provenance (the base review was already stored;
        # we append a second entry with memory provenance so the ledger retains the evidence link)
        if memory is not None:
            self.store.append("horizon_reviews_with_memory", review)
        return review

    def review_representational_transition(
        self,
        current_state: dict[str, Any],
        target_state: dict[str, Any],
        capacity: float,
        metabolized_shortcuts: list[str] | None = None,
    ) -> dict[str, Any]:
        review = review_representational_transition(
            current_state=current_state,
            target_state=target_state,
            capacity=capacity,
            metabolized_shortcuts=metabolized_shortcuts,
        )
        policy_decision = enforce_representational_transition_policy(
            review, self.policy
        )
        record = {
            "id": f"rtr-{uuid4().hex}",
            **review,
            "policy_decision": policy_decision.to_dict(),
            "created_at": now_iso(),
        }
        self.store.append("representational_transitions", record)
        return record

    def read_developmental_memory(self) -> dict[str, Any]:
        return self.store.query_developmental_memory()

    def cognitive_surfaces(self) -> dict[str, Any]:
        from godspeed_nav.reports import generate_developmental_report

        snapshot = self.snapshot()
        report = generate_developmental_report(self.store.root)
        return {
            "representational_state": snapshot.get("latest_representational_state"),
            "representational_transition": snapshot.get(
                "latest_representational_transition"
            ),
            "affordance_path": snapshot.get("latest_affordance_path"),
            "latest_settlement": snapshot.get("latest_settlement"),
            "repetition": report.get(
                "repetition", {"schedule_count": 0, "latest": None}
            ),
            "self_critique": report.get(
                "self_critique", {"finding_count": 0, "finding_codes": []}
            ),
            "identity_state": report.get("identity_state", {}),
        }

    def review_self_critique(self) -> dict[str, Any]:
        findings: list[dict[str, Any]] = []
        active_directions = [
            item
            for item in self.store.read("desired_directions")
            if item.get("status") == "active"
        ]
        latest_settlement = (
            self.store.read("settlements")[-1]
            if self.store.read("settlements")
            else None
        )
        trajectories = self.store.read("trajectories")
        trajectory_points = [
            {
                "theta": float(item.get("new_theta", item.get("theta", 0.0))),
                "radius": float(item.get("new_radius", item.get("radius", 1.0))),
            }
            for item in trajectories
        ]
        circular = (
            detect_circular_motion(trajectory_points)
            if trajectory_points
            else {"circular_motion": False}
        )
        if (
            active_directions
            and latest_settlement
            and latest_settlement.get("status") == "success"
        ):
            latest_radius = (
                trajectory_points[-1]["radius"] if trajectory_points else 1.0
            )
            if latest_radius <= 1.05:
                findings.append(
                    {
                        "id": f"crit-{uuid4().hex}",
                        "code": "dead_end_direction",
                        "reason": "Settlement succeeded without meaningful horizon expansion.",
                        "created_at": now_iso(),
                    }
                )
        if circular.get("circular_motion"):
            findings.append(
                {
                    "id": f"crit-{uuid4().hex}",
                    "code": "circular_motion",
                    "reason": "Rotation is outpacing radial growth.",
                    "created_at": now_iso(),
                }
            )
        for capability in self.store.read("capabilities"):
            if capability.get("evidence_source") == "simulation" and capability.get(
                "lifecycle_state"
            ) in {
                "repeated",
                "metabolized",
            }:
                findings.append(
                    {
                        "id": f"crit-{uuid4().hex}",
                        "code": "simulation_is_not_capability",
                        "reason": "Simulation output cannot be metabolized capability evidence.",
                        "created_at": now_iso(),
                    }
                )

        for finding in findings:
            self.store.append("critique_findings", finding)
        return {"findings": findings, "finding_count": len(findings)}

    def record_settlement(
        self,
        affordance_id: str,
        before_state: dict[str, Any],
        after_state: dict[str, Any],
        payment_actual: dict[str, float],
        evidence: list[str],
        horizon_delta: float,
        observed_consequence: str | None = None,
        unexpected_consequence: list[str] | None = None,
        payment_variance: dict[str, float] | None = None,
        capability_delta: dict[str, Any] | None = None,
        identity_delta: dict[str, Any] | None = None,
        future_constraints_created: list[str] | None = None,
        future_affordances_created: list[str] | None = None,
        desired_direction: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._require_executable_affordance(affordance_id)
        settlement_result = score_settlement(
            before_state,
            after_state,
            desired_direction
            if desired_direction
            else {"affordance_id": affordance_id},
            payment_actual,
            {"evidence": evidence},
        )

        # Find the matched affordance to recover predicted payment and
        # risk/debt estimates for calibration (Section 5.5 / Section 17).
        matched_affordance: dict[str, Any] = {}
        for aff in self.store.read("affordances"):
            if aff.get("id") == affordance_id:
                matched_affordance = aff
                break

        # Recover predicted payment from the payment ledger if available.
        predicted_payment: dict[str, Any] = {}
        for pay_event in self.store.read_events("payments"):
            record = pay_event.get("record", pay_event)
            if record.get("affordance_id") == affordance_id:
                predicted_payment = record.get("dimensions", {})
                break

        settlement = {
            "id": f"set-{uuid4().hex}",
            "affordance_id": affordance_id,
            "before_state": before_state,
            "after_state": after_state,
            "payment_actual": payment_actual,
            "score": settlement_result["settlement_score"],
            "status": settlement_result["status"],
            "evidence": evidence,
            "observed_consequence": observed_consequence or "",
            "unexpected_consequence": unexpected_consequence or [],
            "payment_variance": payment_variance or {},
            "capability_delta": capability_delta or {},
            "identity_delta": identity_delta or {},
            "future_constraints_created": future_constraints_created or [],
            "future_affordances_created": future_affordances_created or [],
            "changed_keys": sorted(set(before_state) | set(after_state)),
            "model_calibration": {
                "payment_predicted": predicted_payment or None,
                "payment_actual": payment_actual,
                "settlement_success": settlement_result["status"] == "success",
                "settlement_score": settlement_result["settlement_score"],
                "horizon_delta": horizon_delta,
                "risk_estimate": matched_affordance.get("risk"),
                "debt_estimate": matched_affordance.get("debt"),
            },
            "created_at": now_iso(),
        }
        self.store.append_event("settlements", settlement)

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
        capability = self._update_capability_evidence(affordance_id)
        self._schedule_repetition(affordance_id, capability, trajectory)
        return {**settlement, "trajectory": trajectory, "capability": capability}

    def ingest_execution_evidence(self, event: dict[str, Any]) -> dict[str, Any]:
        """Validate and persist external execution evidence as provisional input.

        Software proof alone is never settlement. Complete non-empty evidence is
        classified ``provisional`` regardless of whether expected and observed
        strings match; match/mismatch is preserved as an observed proof fact.
        Missing required evidence raises ``DomainRuleError`` (code
        ``incomplete_execution_evidence``). This writes only the canonical
        ``execution_evidence`` ledger and never ``settlements``,
        ``capabilities``, ``trajectories``, or ``repetition_schedules``; a later
        ``record_settlement()`` with observable consequence is the only
        promotion path. Re-delivery of the same ``event_id`` returns the
        existing record without a duplicate write.
        """
        payload = event.get("payload", {})
        event_id = event.get("event_id")
        required = {
            "event_id": event_id,
            "affordance_id": payload.get("affordance_id"),
            "work_request_id": payload.get("work_request_id"),
            "proof_result_id": payload.get("proof_result_id"),
            "expected_result": payload.get("expected_result"),
            "observed_result": payload.get("observed_result"),
        }
        for field, value in required.items():
            if not value:
                raise DomainRuleError(
                    "incomplete_execution_evidence",
                    f"Execution evidence rejected: required field '{field}' is "
                    "missing or empty. Software proof alone is not settlement.",
                )

        self._require_executable_affordance(payload["affordance_id"])

        record = {
            "id": f"ee-{uuid4().hex}",
            "evidence_event_id": event_id,
            "affordance_id": payload["affordance_id"],
            "work_request_id": payload["work_request_id"],
            "proof_result_id": payload["proof_result_id"],
            "expected_result": payload["expected_result"],
            "observed_result": payload["observed_result"],
            "proof_match": payload["expected_result"] == payload["observed_result"],
            "classification": "provisional",
            "source_event_type": event.get("event_type"),
            "created_at": now_iso(),
        }
        # Atomic dedup + append under one flock: concurrent re-delivery of the
        # same event_id stores exactly one provisional record.
        envelope, _appended = self.store.append_event_if_absent(
            "execution_evidence", record, dedup_field="evidence_event_id"
        )
        return envelope["record"]

    def ingest_canonical_evidence_recorded(
        self,
        event: dict[str, Any],
        *,
        local_model_sha256: str,
        expected_work_request_id: str,
        known_parent_ids: list[str] | None = None,
        local_world_ref: str | None = None,
    ) -> dict[str, Any]:
        """T08: gate ONE canonical EvidenceRecorded into provisional storage.

        Composition of the pure canonical gate
        (:func:`godspeed_nav.evidence_ingest.ingest_evidence_recorded`) with
        this runtime's provisional evidence path. STRICTLY PROVISIONAL
        (frozen invariant I8): success writes ONLY the
        ``canonical_execution_evidence`` ledger and returns an inert
        provisional record; it can never create SettlementRecorded,
        CapabilityUpdated, trajectories, repetition schedules, or any
        metabolized capability. The lawful promotion path remains the
        explicit :meth:`record_settlement` action, which this method does not
        invoke or expose.

        Re-delivery under stable identity is consequence-free: the prior
        stored record is returned with status ``duplicate``.
        """
        from godspeed_nav.evidence_ingest import (  # noqa: PLC0415 — lazy import keeps module graph flat
            EvidenceAdmission,
            EvidenceIngestState,
            ingest_evidence_recorded,
        )

        state = getattr(self, "_canonical_evidence_state", None)
        if state is None:
            state = EvidenceIngestState()
            self._canonical_evidence_state = state

        admission: EvidenceAdmission = ingest_evidence_recorded(
            event,
            local_model_sha256=local_model_sha256,
            expected_work_request_id=expected_work_request_id,
            state=state,
            known_parent_ids=known_parent_ids,
            local_world_ref=local_world_ref,
        )
        if admission.status == "duplicate" or admission.record is None:
            return {"status": "duplicate", "record": None}

        # Mirror the legacy evidence boundary: only a persisted EXECUTABLE
        # affordance may carry developmental evidence forward.
        record = admission.record
        self._require_executable_affordance(record.affordance_id)

        stored, _appended = self.store.append_event_if_absent(
            "canonical_execution_evidence",
            {"id": f"cee-{uuid4().hex}", **record.to_ledger_record(now_iso())},
            dedup_field="evidence_event_id",
        )
        return {"status": "provisional_recorded", "record": stored["record"]}

    def snapshot(self) -> dict[str, Any]:
        ledgers = {
            "desired_directions": self.store.read("desired_directions"),
            "representational_states": self.store.read("representational_states"),
            "representational_transitions": self.store.read(
                "representational_transitions"
            ),
            "affordance_paths": self.store.read("affordance_paths"),
            "affordances": self.store.read("affordances"),
            "possibilities": self.store.read("possibilities"),
            "potentials": self.store.read("potentials"),
            "payments": self.store.read("payments"),
            "settlements": self.store.read("settlements"),
            "trajectories": self.store.read("trajectories"),
            "repetition_schedules": self.store.read("repetition_schedules"),
            "capabilities": self.store.read("capabilities"),
        }
        return {
            "counts": {name: len(records) for name, records in ledgers.items()},
            "active_directions": [
                item
                for item in ledgers["desired_directions"]
                if item.get("status") == "active"
            ],
            "latest_representational_state": (
                ledgers["representational_states"][-1]
                if ledgers["representational_states"]
                else None
            ),
            "latest_representational_transition": (
                ledgers["representational_transitions"][-1]
                if ledgers["representational_transitions"]
                else None
            ),
            "latest_affordance_path": (
                ledgers["affordance_paths"][-1] if ledgers["affordance_paths"] else None
            ),
            "latest_settlement": ledgers["settlements"][-1]
            if ledgers["settlements"]
            else None,
            "latest_repetition_schedule": (
                ledgers["repetition_schedules"][-1]
                if ledgers["repetition_schedules"]
                else None
            ),
            "latest_trajectory": ledgers["trajectories"][-1]
            if ledgers["trajectories"]
            else None,
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

    def _require_executable_affordance(self, affordance_id: str) -> dict[str, Any]:
        """Return the persisted affordance for ``affordance_id``.

        Raises ``DomainRuleError`` (code
        ``settlement_requires_executable_affordance``) when the identifier is
        unknown, or resolves to a potential/possibility/non-executable record.
        Only persisted affordances with ``current_status == 'affordance'`` may
        settle. This runs before any settlement-derived state is written.
        """
        for aff in self.store.read("affordances"):
            if aff.get("id") == affordance_id:
                if aff.get("current_status") != "affordance":
                    raise DomainRuleError(
                        "settlement_requires_executable_affordance",
                        f"Affordance '{affordance_id}' is not executable "
                        f"(status='{aff.get('current_status')}'); settlement "
                        "requires a persisted executable affordance.",
                    )
                return aff
        raise DomainRuleError(
            "settlement_requires_executable_affordance",
            f"Affordance '{affordance_id}' is not a persisted executable "
            "affordance; settlement cannot proceed for an unknown, potential, "
            "or possibility identifier.",
        )

    def _latest_trajectory(self) -> dict[str, Any]:
        trajectories = self.store.read("trajectories")
        return trajectories[-1] if trajectories else {}

    def _update_capability_evidence(self, affordance_id: str) -> dict[str, Any]:
        settlements = [
            item
            for item in self.store.read("settlements")
            if item.get("affordance_id") == affordance_id
            and item.get("status") == "success"
        ]
        changed_contexts = {
            tuple(item.get("changed_keys", []))
            for item in settlements
            if item.get("changed_keys")
        }
        settlement_count = len(settlements)
        stability = sum(float(item.get("score", 0.0)) for item in settlements) / max(
            1, settlement_count
        )
        burden_decay = max(0.0, 0.6 - (0.15 * settlement_count))
        metabolization = compute_metabolization(
            capability_id=affordance_id,
            settlement_events=settlements,
            reuse_frequency=settlement_count,
            context_diversity=max(1, len(changed_contexts)),
            stability=stability,
            maintenance_burden=burden_decay,
            attention_burden=burden_decay,
        )
        capability = {
            "id": affordance_id,
            "settlement_count": settlement_count,
            "context_diversity": max(1, len(changed_contexts)),
            "stability": stability,
            "maintenance_burden": burden_decay,
            "attention_burden": burden_decay,
            "metabolization_score": metabolization["metabolization_score"],
            "status": metabolization["status_recommendation"],
            "lifecycle_state": infer_capability_lifecycle(
                settlement_count=settlement_count,
                stability=stability,
                metabolization_score=metabolization["metabolization_score"],
            ),
            "missing_evidence": metabolization["missing_evidence"],
            "updated_at": now_iso(),
        }
        self.store.append("capabilities", capability)
        return capability

    def _schedule_repetition(
        self,
        affordance_id: str,
        capability: dict[str, Any],
        trajectory: dict[str, Any],
    ) -> dict[str, Any] | None:
        if capability.get("status") == "substrate_candidate":
            return None

        settlements = [
            item
            for item in self.store.read("settlements")
            if item.get("affordance_id") == affordance_id
            and item.get("status") == "success"
        ]
        changed_contexts = {
            tuple(item.get("changed_keys", []))
            for item in settlements
            if item.get("changed_keys")
        }
        trajectory_points = [
            {
                "theta": float(item.get("new_theta", item.get("theta", 0.0))),
                "radius": float(item.get("new_radius", item.get("radius", 1.0))),
            }
            for item in self.store.read("trajectories")
        ]
        circular = (
            detect_circular_motion(trajectory_points)
            if trajectory_points
            else {"circular_motion": False}
        )
        schedule = {
            "id": f"rep-sched-{uuid4().hex}",
            **plan_repetition(
                affordance_id=affordance_id,
                capability_status=str(capability.get("status", "not_metabolized")),
                variation_coverage=max(1, len(changed_contexts)),
                circular_motion=bool(circular.get("circular_motion", False)),
            ),
            "created_at": now_iso(),
        }
        self.store.append("repetition_schedules", schedule)
        return schedule

    def emit_developmental_event(
        self,
        event_type: str,
        *,
        work_request_id: str,
        source_evidence_refs: list[str],
        developmental_decision: dict[str, Any],
        domain_model_sha256: str,
        parent_evidence_ids: list[str],
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """T09: project ONE explicit developmental decision into its canonical
        E9 envelope and durably persist it through the idempotent memory gate
        (:mod:`godspeed_nav.developmental_events`,
        :mod:`godspeed_nav.developmental_memory`). godspeed_agent is the
        exclusive producer of all five developmental event types; every
        refusal happens before any write, and redelivery of an identical
        envelope creates no duplicate history."""
        from godspeed_nav.developmental_events import (  # noqa: PLC0415 — lazy import keeps module graph flat
            project_developmental_event,
        )
        from godspeed_nav.developmental_memory import (  # noqa: PLC0415
            persist_developmental_event,
        )

        envelope = project_developmental_event(
            event_type,
            work_request_id=work_request_id,
            source_evidence_refs=source_evidence_refs,
            developmental_decision=developmental_decision,
            domain_model_hash=domain_model_sha256,
            parent_evidence_ids=parent_evidence_ids,
            payload=payload,
        )
        return persist_developmental_event(
            self.store,
            envelope,
            local_model_sha256=domain_model_sha256,
        )

    def request_capability_promotion(
        self,
        capability_id: str,
        target_lifecycle: str,
        *,
        variation_evidence: list[str],
        work_request_id: str,
        source_evidence_refs: list[str],
        domain_model_sha256: str,
        parent_evidence_ids: list[str],
        rationale: str | None = None,
    ) -> dict[str, Any]:
        """T09/I9: request promotion of one capability through the SAME
        canonical, gated, idempotent surface as every other developmental
        decision. Metabolized capability is unreachable here without repeated
        settlement under DECLARED variation recorded in durable history —
        the durable memory gate refuses unearned promotions by name."""
        return self.emit_developmental_event(
            "CapabilityUpdated",
            work_request_id=work_request_id,
            source_evidence_refs=source_evidence_refs,
            developmental_decision={
                "action": "promote_capability",
                "capability_id": capability_id,
                "target_lifecycle": target_lifecycle,
                "rationale": rationale or "",
            },
            domain_model_sha256=domain_model_sha256,
            parent_evidence_ids=parent_evidence_ids,
            payload={
                "capability_id": capability_id,
                "target_lifecycle": target_lifecycle,
                "variation_evidence": variation_evidence,
            },
        )
