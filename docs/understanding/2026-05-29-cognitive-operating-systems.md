# Cognitive Operating Systems Grand Understanding

Source reviewed: `Cognitive Operating Systems (1).pdf`.

## Central Aim

The sought outcome is not a helper library with isolated math functions. The PDF describes a local-first developmental operating system for humans, organizations, and AI agents. Its purpose is to convert desired directions into repeated loops of horizon sensing, affordable affordance selection, payment, settlement, repetition, metabolization, positive disintegration, memory, and self-critique.

The enterprise product should therefore behave like an operational runtime for capability formation. It should answer:

- What can this observer currently perceive and afford?
- Which next transformation is spendable rather than merely imagined?
- What payment must be made, and what payment debt is accumulating?
- What actually settled, based on consequence rather than declared intent?
- Which repeated settlements are becoming capabilities or substrate?
- Which structures should dissolve, and which useful elements should be metabolized?
- Is the system spiraling outward through horizon expansion or rotating in place?
- What did the system become, and how did it become that?

## Non-Negotiable Invariants

- Outcomes are temporary attractors. They matter, but they are not terminal.
- Potential and possibility cannot be spent as affordance.
- Capabilities cannot be declared into existence. They require repeated settlement.
- Metabolization requires settlement, repetition, time, diversity, stability, and reduced attention burden.
- Payment and settlement ledgers are the truth surface.
- Simulation is useful only when it reduces real payment. It cannot replace real settlement.
- Positive disintegration must include safeguards against destructive misuse.
- The framework itself must be revisable through self-critique and settlement evidence.

## Enterprise-Shippable Implications

The current project needs to mature from a scaffold into a dependable runtime with:

- A durable service layer that coordinates direction, horizon, affordance, payment, settlement, repetition, metabolization, disintegration, absorption, trajectory, and self-critique.
- Typed records with schema validation and explicit lifecycle transitions.
- Storage safety strong enough for long-lived developmental memory: atomic append, ledger namespacing, quarantine metadata, indexes, backups, and migration/version handling.
- CLI and hook commands for real operating workflows, not only stateless calculators.
- Policy gates for payment thresholds, human review, safety, and absorption.
- Observability reports that expose horizon drift, circular motion, unaffordable action attempts, settlement quality, and metabolization candidates.
- Operational docs and runbooks for installation, validation, incident recovery, and enterprise deployment boundaries.
- A test matrix that covers lifecycle workflows, storage corruption, command behavior, policy enforcement, and regression cases.

## Product Shape

The right enterprise shape is a local developmental memory and decision runtime packaged as a Claude Code plugin. Claude skills and agents provide human-readable procedure; Python services provide deterministic accounting; hooks and CLI commands write evidence; optional MCP exposes computation. The ledgers are not audit decoration. They are the source of truth for whether the system is expanding its horizon or generating circular motion.

## Deterministic Metric Reference

This repository now has deterministic scoring surfaces, but this page originally did not explain them. That made the doctrine legible while leaving the operational math implicit. The missing reference material is the metric layer below.

### Primary runtime metric

- The primary metric in [HARNESS.md](/home/sprime01/projects/godspeed_agent/HARNESS.md) is `horizon_expansion`.
- The runtime treats outcome completion as non-terminal. A completed outcome matters only if it increases reachable affordances, reduces payment debt, or becomes reusable substrate.

### Error metric

- Implementation surface: [godspeed_nav/metrics.py](/home/sprime01/projects/godspeed_agent/godspeed_nav/metrics.py).
- CLI surface: `godspeed-nav compute-error`.
- Output fields: `error_vector`, `error_magnitude`, `dominant_error`.
- Meaning: compare desired state to observed state per key, then weight each delta.

$$
error\_vector[key] = (desired[key] - observed[key]) \times weight[key]
$$

$$
error\_magnitude = \sqrt{\sum error\_vector[key]^2}
$$

- `dominant_error` is the key with the largest absolute weighted deviation.
- Use this metric when the question is "how far are we from the desired direction right now?"

### Payment metric

- Implementation surface: [godspeed_nav/metrics.py](/home/sprime01/projects/godspeed_agent/godspeed_nav/metrics.py).
- CLI surface: `godspeed-nav estimate-payment`.
- Output fields: `payment_burden`, `capacity_norm`, `spendability`, `dominant_cost`.
- Meaning: payment is a weighted cost norm, not a narrative claim.

$$
payment\_burden = \sqrt{\sum (cost[key] \times weight[key])^2}
$$

$$
capacity\_norm = \sqrt{\sum capacity[key]^2}
$$

- `spendability` is `affordable` when `payment_burden <= capacity_norm`, otherwise `unaffordable`.
- `dominant_cost` is the highest weighted cost axis.
- This is the reference for deciding whether an affordance is reachable now or should stay outside the active horizon.

### Settlement metric

- Implementation surface: [godspeed_nav/metrics.py](/home/sprime01/projects/godspeed_agent/godspeed_nav/metrics.py).
- CLI surface: `godspeed-nav score-settlement`.
- Output fields: `settlement_score`, `status`, `accepted_evidence`, `rejected_evidence`, `missing_evidence`, `improved_keys`, `regression_keys`, `payment_summary`.
- Meaning: settlement is consequence measured from before/after state plus observable evidence. Intent text does not count as proof.

Settlement scoring has two paths:

- If `desired.desired_state` is present, the scorer compares distance to the target before and after the action.
- Otherwise it falls back to directional change classification over all state keys.

The current status contract is:

- `failed` when evidence is intent-only, when no observable change exists, or when the score collapses to `0`.
- `partial` when some improvement exists but the result is mixed or incomplete.
- `success` when score is at least `0.7` and there are no regressions.

Important implementation details:

- Evidence strings beginning with `intent:` are rejected.
- If both improvements and regressions exist, a nominally high score is capped below success.
- If neither improvement nor regression can be observed, the scorer records `missing_evidence: ["observable_change"]`.

### Affordance ranking metric

- Implementation surface: [godspeed_nav/metrics.py](/home/sprime01/projects/godspeed_agent/godspeed_nav/metrics.py).
- CLI surface: `godspeed-nav rank-affordances`.
- Output fields: `ranked_affordances`, `next_recommended_affordance`, `rejected_candidates`.
- Meaning: the runtime ranks the next spendable move by expected expansion divided by payment burden and risk.

$$
rank\_score = \frac{expected\_horizon\_delta}{payment\_burden \times (1 + risk)}
$$

- Candidates without a payment estimate are rejected explicitly.
- This is the clearest mathematical expression of the doctrine's phrase "the next affordable affordance."

### Metabolization metric

- Implementation surface: [godspeed_nav/metabolization.py](/home/sprime01/projects/godspeed_agent/godspeed_nav/metabolization.py).
- CLI surface: `godspeed-nav metabolization`.
- Output fields: `metabolization_score`, `status_recommendation`, `missing_evidence`.
- Meaning: a pattern becomes metabolized only when repeated settlement is strong enough to lower attention and maintenance burden.

Current thresholds:

- At least `3` settlement events.
- Reuse frequency at least `3`.
- Context diversity at least `2`.
- Stability at least `0.8`.
- Maintenance burden at most `0.3`.
- Attention burden at most `0.3`.

$$
metabolization\_score = \frac{positive\_factors}{6}
$$

- `status_recommendation` becomes `substrate_candidate` only when the score is at least `0.75` and no required evidence is missing.

### Trajectory and circular-motion metrics

- Implementation surfaces: [godspeed_nav/trajectory.py](/home/sprime01/projects/godspeed_agent/godspeed_nav/trajectory.py) and [godspeed_nav/reports.py](/home/sprime01/projects/godspeed_agent/godspeed_nav/reports.py).
- Meaning: the runtime tracks whether the system is spiraling outward or merely rotating.

Trajectory update:

- `theta_delta = max(0.1, abs(horizon_delta) * 0.1)`
- `radius_growth = max(0.0, settlement_score - 0.5) * max(0.0, horizon_delta)`

Circular motion detection currently flags stagnation when:

- rotation is at least one full turn, $2\pi$
- radius growth is at most `0.1`

This is not yet a sophisticated progress model, but it is the active operational definition behind the report language.

## Developmental Report Field Reference

The `godspeed-nav developmental-report` command summarizes local ledger state into the observability surface below.

- `settlement_quality`: count of settlement statuses such as `success`, `partial`, and `failed`.
- `payment_debt.total_burden`: sum of recorded `payment_burden` values across the payment ledger.
- `payment_debt.payment_count`: number of payment events recorded.
- `trajectory.latest_theta`: latest angular position.
- `trajectory.latest_radius`: latest radius after settlement-driven growth.
- `trajectory.circular_motion`: whether the recent trajectory indicates rotation without meaningful outward movement.
- `trajectory.radius_growth`: observed radial change across the sampled trajectory window.
- `horizon.active_direction_count`: number of desired directions still marked `active`.
- `metabolization.candidate_count`: number of capabilities currently marked `capability` or `substrate_candidate`.
- `metabolization.candidate_ids`: identifiers for those candidates.

## Reference Material Still Missing

To make the documentation fully fleshed out, the repository still needs a few explicit reference surfaces beyond this page.

- A ledger reference that names every JSONL ledger, its event envelope, and the required fields per record.
- A schema index that links each file in [schemas/](/home/sprime01/projects/godspeed_agent/schemas) to the runtime command or workflow that produces it.
- A CLI reference with one concrete input/output example per command, especially for `score-settlement`, `developmental-report`, and `predictive-extensions`.
- A report interpretation guide that explains what operators should do when they see `partial` settlement, `unaffordable` payment, or `circular_motion: true`.
- A policy reference that maps [HARNESS.md](/home/sprime01/projects/godspeed_agent/HARNESS.md) settings to runtime consequences, warnings, and hard blocks.
- A runtime workflow example that follows one desired direction from creation through horizon review, settlement, report review, and metabolization.

The operator-facing reference set now lives under [docs/references](/home/sprime01/projects/godspeed_agent/docs/references) and should be read alongside this understanding note when moving from doctrine to operation.

## Documentation Priority Order

If this documentation is being expanded next, the highest-value order is:

1. Add a CLI and ledger reference, because those are the direct evidence surfaces.
2. Add a report interpretation guide, because the current report fields are only obvious if you read the code.
3. Add schema and policy indexes, because enterprise operators need to know which fields are normative and which defaults are implementation-defined.

## Verified Gap Status

The earlier gap summary is now partly stale. Several of the foundational concerns it named are no longer open gaps.

- Runtime orchestration is Mostly resolved through `NavigationRuntime`, workflow-grade CLI commands, and enterprise validation.
- Storage durability is Mostly resolved for the current scale through checksummed event envelopes, indexes, backups, quarantine handling, and migration status.
- Runbooks, release checks, and enterprise validation are Mostly resolved as operating surfaces, even though the operator reference layer is still missing.

The remaining gaps are narrower and more important than the old broad list:

- Desired direction, horizon, affordance, payment, settlement, and trajectory are connected, but repetition and metabolization are still only thinly owned by the runtime.
- CLI workflow commands exist, but the operator-facing reference layer is still missing, especially ledger, schema, policy, report, and end-to-end workflow documentation.
- Hook events now record payment, settlement, trajectory, and reports, but they are not yet reconciled into one fully explainable session flow from prompt hypothesis through stop-time review.
- Positive disintegration and absorption are still a gap because their review artifacts and policy reasoning remain too thin for enterprise scrutiny.
- Future ML-era retrieval may justify a richer local data layer, but that should be an explicit storage-evolution decision rather than an implicit rewrite of the JSONL truth surface.
