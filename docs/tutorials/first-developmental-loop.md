# Tutorial: Your First Developmental Loop

This tutorial guides you through executing a complete, real-world cybernetic navigation cycle in GodSpeed-Agent using terminal CLI commands.

---

## 1. Prerequisites & Setup

Ensure you have a working Python 3.11+ environment with `uv` installed. If you have not yet installed GodSpeed-Agent, complete the [Getting Started Guide](../getting-started.md).

We will run this tutorial inside a temporary workspace directory to observe how ledgers are created:

```bash
# Create and navigate to a sandbox workspace
mkdir -p /tmp/gsa-tutorial && cd /tmp/gsa-tutorial
```

---

## 2. Step 1: Start an Attractor Direction

Every developmental cycle begins with an active attractor direction.

Run:
```bash
uv run --directory /path/to/godspeed_agent godspeed-nav start-direction \
  --workspace-root . \
  --storage-root .godspeed-harness \
  --label "JWT Authentication" \
  --statement "Implement secure local JWT token verification"
```

**Expected Output**:
```json
{
  "created_at": "2026-06-03T18:00:00.000000+00:00",
  "horizon_id": "hor-4f91...",
  "id": "dir-8a2b...",
  "kind": "goal",
  "label": "JWT Authentication",
  "source": "cli",
  "statement": "Implement secure local JWT token verification",
  "status": "active"
}
```

*Take note of the returned `id` (e.g. `dir-8a2b...`). You will use it in Step 2.*

---

## 3. Step 2: Establish Representational State

Anchor the observer's position in scope and givenness:

```bash
uv run --directory /path/to/godspeed_agent godspeed-nav set-representational-state \
  --workspace-root . \
  --storage-root .godspeed-harness \
  --direction-id "dir-8a2b..." \
  --scope-position 0.3 \
  --mode-of-givenness-position 0.3 \
  --phase "general" \
  --radius 1.0 \
  --confidence 0.9
```

**Expected Output**:
```json
{
  "confidence": 0.9,
  "created_at": "2026-06-03T18:01:00.000000+00:00",
  "direction_id": "dir-8a2b...",
  "id": "rep-1c3d...",
  "mode_of_givenness_position": "0.3",
  "phase": "general",
  "quadrant": "0.3_0.3",
  "radius": 1.0,
  "scope_position": "0.3"
}
```

---

## 4. Step 3: Review the Horizon & Select an Affordance

Submit candidate pathways to the horizon review engine. One candidate has an affordable pathway; the other is unaffordable:

```bash
uv run --directory /path/to/godspeed_agent godspeed-nav review-horizon \
  --workspace-root . \
  --storage-root .godspeed-harness \
  --direction-id "dir-8a2b..." \
  --candidates '[
    {
      "id": "jwt-pyjwt-lib",
      "statement": "Use standard PyJWT library",
      "pathway": "import jwt; jwt.decode()",
      "costs": {"time": 2, "compute": 5},
      "capacities": {"time": 10, "compute": 20},
      "expected_horizon_delta": 3.0,
      "risk": 0.1
    },
    {
      "id": "jwt-custom-crypto",
      "statement": "Implement custom RSA crypto from scratch",
      "pathway": "write custom math routines",
      "costs": {"time": 50, "compute": 100},
      "capacities": {"time": 10, "compute": 20},
      "expected_horizon_delta": 1.0,
      "risk": 0.9
    }
  ]'
```

**Expected Output**:
```json
{
  "created_at": "2026-06-03T18:02:00.000000+00:00",
  "direction_id": "dir-8a2b...",
  "next_affordance": {
    "expected_horizon_delta": 3.0,
    "id": "jwt-pyjwt-lib",
    "pathway": "import jwt; jwt.decode()",
    "rank_score": 0.25298,
    "risk": 0.1
  },
  "ranked_affordances": [
    {
      "expected_horizon_delta": 3.0,
      "id": "jwt-pyjwt-lib",
      "pathway": "import jwt; jwt.decode()",
      "rank_score": 0.25298,
      "risk": 0.1
    }
  ],
  "rejected_candidates": [
    {
      "id": "jwt-custom-crypto",
      "reason": "unaffordable"
    }
  ]
}
```

*Notice*: `jwt-custom-crypto` was automatically rejected and appended to `possibilities.jsonl`. Only `jwt-pyjwt-lib` became an active affordance.

---

## 5. Step 4: Record Settlement Based on Consequence

Now record the empirical outcome of using the PyJWT library:

```bash
uv run --directory /path/to/godspeed_agent godspeed-nav record-settlement \
  --workspace-root . \
  --storage-root .godspeed-harness \
  --affordance-id "jwt-pyjwt-lib" \
  --before '{"jwt_verified": false, "auth_errors": 5}' \
  --after '{"jwt_verified": true, "auth_errors": 0}' \
  --payment '{"time": 2, "compute": 4}' \
  --evidence '["pytest tests/test_jwt.py: 6 passed in 0.12s"]' \
  --horizon-delta 3.0
```

**Expected Output**:
```json
{
  "affordance_id": "jwt-pyjwt-lib",
  "capability": {
    "attention_burden": 0.45,
    "id": "jwt-pyjwt-lib",
    "lifecycle_state": "active",
    "maintenance_burden": 0.45,
    "metabolization_score": 0.5,
    "settlement_count": 1,
    "stability": 1.0,
    "status": "not_metabolized"
  },
  "id": "set-9c4e...",
  "score": 1.0,
  "status": "success",
  "trajectory": {
    "circular_motion_flags": {
      "circular_motion": false
    },
    "new_radius": 2.5,
    "new_theta": 0.3
  }
}
```

---

## 6. Step 5: Verify Developmental State

Inspect the health report to verify that radial growth occurred:

```bash
uv run --directory /path/to/godspeed_agent godspeed-nav developmental-report \
  --workspace-root . \
  --storage-root .godspeed-harness
```

Verify that:
- `settlement_quality.success` is `1`.
- `trajectory.latest_radius` has grown to `2.5` ($\Delta r = 1.5$).
- `trajectory.circular_motion` is `false`.

Congratulations! You have completed your first cybernetic developmental loop.

---

### What to Read Next
- [Explanation: Why Horizon Over Outcomes](../explanations/why-horizon-over-outcomes.md)
- [Subsystem: Runtime Coordinator](../subsystems/runtime-coordinator.md)
- [How-To: Configure Harness Policy](../how-to/configure-harness-policy.md)
