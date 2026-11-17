# Workflow: The Core Developmental Cycle

This document traces the primary execution workflow of GodSpeed-Agent from initial direction conception to settled capability metabolization.

---

## 1. Summary

The Core Developmental Cycle is the fundamental engine of capability formation in GodSpeed-Agent. An agent or operator identifies an attractor direction, establishes its representational coordinates, reviews candidate affordance pathways against payment capacity and governance gates, spends the top-ranked affordance, records empirical before/after settlement consequences, updates spiral trajectory, and plans repetition under variation until the capability crystallizes into permanent substrate.

---

## 2. Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor Op as Operator / Agent
    participant CLI as CLI / MCP Surface
    participant RT as NavigationRuntime
    participant CC as Cognitive Model Core
    participant MET as Metrics Engine
    participant ST as LedgerStore (.godspeed-harness)

    Op->>CLI: start-direction (label, statement)
    CLI->>RT: start_direction()
    RT->>ST: append("desired_directions"), append("horizons")
    RT-->>CLI: direction dict (dir-id, hor-id)

    Op->>CLI: set-representational-state (dir-id, scope, givenness, phase)
    CLI->>RT: set_representational_state()
    RT->>ST: append("representational_states")

    Op->>CLI: review-horizon (dir-id, candidates)
    CLI->>RT: review_horizon()
    loop For Each Candidate
        RT->>MET: estimate_payment(costs, capacities)
        RT->>RT: enforce_payment_policy()
        alt Pathway Missing
            RT->>ST: append("potentials", candidate)
        else Unaffordable / Blocked
            RT->>ST: append("possibilities", candidate)
        else Affordable & Approved
            RT->>ST: append("affordances", candidate)
            RT->>ST: append("affordance_paths", path_details)
        end
    end
    RT->>CC: rank_candidates_by_controller(affordances)
    RT->>ST: append("horizon_reviews", review)
    RT-->>CLI: review dict (ranked_affordances, next_affordance)

    Note over Op: Agent executes top affordance in project workspace

    Op->>CLI: record-settlement (affordance-id, before, after, payment, evidence, horizon_delta)
    CLI->>RT: record_settlement()
    RT->>RT: _require_executable_affordance(aff-id)
    RT->>MET: score_settlement(before, after, desired, payment, evidence)
    RT->>ST: append_event("settlements", settlement)
    RT->>MET: update_trajectory(theta, radius, score, horizon_delta)
    RT->>ST: append("trajectories", trajectory)
    RT->>MET: _update_capability_evidence(aff-id)
    RT->>ST: append("capabilities", capability)
    RT->>MET: _schedule_repetition(aff-id)
    RT->>ST: append("repetition_schedules", schedule)
    RT-->>CLI: settlement outcome dict
```

---

## 3. Detailed Execution Steps

### Step 1: Direction Initiation
- **Invocation**: `godspeed-nav start-direction --label "..." --statement "..."`
- **Method**: `NavigationRuntime.start_direction` (`runtime.py:31`)
- **State Written**:
  - `desired_directions.jsonl`: ID `dir-<uuid>`, status `"active"`, linked `horizon_id`.
  - `horizons.jsonl`: ID `hor-<uuid>`, observer `"local-operator"`, initial radius $1.0$.

### Step 2: Representational Anchoring
- **Invocation**: `godspeed-nav set-representational-state --direction-id <id> --scope-position 0.2 --mode-of-givenness-position 0.2 --phase "general" ...`
- **Method**: `NavigationRuntime.set_representational_state` (`runtime.py:65`)
- **State Written**:
  - `representational_states.jsonl`: Continuous coordinates $(0.2, 0.2)$, phase `"general"`.

### Step 3: Horizon Review & Gating
- **Invocation**: `godspeed-nav review-horizon --direction-id <id> --candidates '[...]'`
- **Method**: `NavigationRuntime.review_horizon` (`runtime.py:91`)
- **Logic**:
  1. Partitions candidates missing pathways into `potentials.jsonl`.
  2. Computes payment burden norm via `estimate_payment` (`metrics.py:102`).
  3. Evaluates `enforce_payment_policy` (`policies.py:17`).
  4. Partitions candidates exceeding capacity into `possibilities.jsonl`.
  5. Commits viable candidates to `affordances.jsonl` and `affordance_paths.jsonl`.
  6. Ranks approved affordances using the cybernetic controller loss function (`cognitive_model.py:288`).
  7. Persists review summary to `horizon_reviews.jsonl`.

### Step 4: Empirical Action & Observation
- The agent or operator executes the physical actions (e.g. running tests, generating code, applying migrations).
- GSA does not intervene in execution; it awaits observable before/after state diffs and verification logs.

### Step 5: Settlement Recording
- **Invocation**: `godspeed-nav record-settlement --affordance-id <id> --before '{...}' --after '{...}' --payment '{...}' --evidence '["..."]' --horizon-delta 1.0`
- **Method**: `NavigationRuntime.record_settlement` (`runtime.py:542`)
- **Logic**:
  1. `_require_executable_affordance`: Confirms that `affordance-id` is in `affordances.jsonl` with `current_status == 'affordance'`.
  2. `score_settlement`: Strips intent strings (`"intent:..."`), calculates net progress versus desired state, checks for regressions (`metrics.py:122`).
  3. Writes event envelope to `settlements.jsonl`.
  4. Updates spiral trajectory in `trajectories.jsonl`:
     $$\Delta\theta = \max(0.1, |\Delta h| \times 0.1), \quad \Delta r = \max(0, \text{score} - 0.5) \times \max(0, \Delta h)$$
  5. Updates capability evidence in `capabilities.jsonl` using `compute_metabolization`.
  6. Emits repetition plan in `repetition_schedules.jsonl` if not yet a substrate candidate.

---

## 4. Failure & Alternate Branches

| Point of Failure | Cause | Outcome |
| :--- | :--- | :--- |
| Horizon Review | Candidate missing `pathway` string. | Diverted to `potentials.jsonl`; excluded from affordance list. |
| Horizon Review | Candidate payment burden exceeds capacity norm. | Diverted to `possibilities.jsonl`; excluded from affordance list. |
| Horizon Review | Candidate risk exceeds context ceiling. | Blocked by hard gate in `evaluate_candidate_model`. |
| Settlement | Candidate affordance was never reviewed or was diverted to `possibilities`. | Execution aborted with `DomainRuleError("settlement_requires_executable_affordance")`. |
| Settlement | Evidence consists solely of `"intent:..."` strings. | Scored as `0.0` with status `"failed"` and `missing_evidence: ["observable_consequence"]`. |
| Settlement | Key regressions outweigh improvements. | Score capped at `0.69`; status set to `"partial"`. |

---

### Source Trail
- Coordinator: `godspeed_nav/runtime.py`
- Metrics: `godspeed_nav/metrics.py`
- Cognitive Model: `godspeed_nav/cognitive_model.py`
- Verification Suite: `tests/test_runtime_workflow.py`
