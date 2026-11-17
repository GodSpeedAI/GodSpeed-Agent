# How-To: Troubleshoot Common Failures

This guide provides diagnostics, root causes, and concrete recovery procedures for common operational and runtime errors in GodSpeed-Agent.

---

## 1. `DomainRuleError: settlement_requires_executable_affordance`

### Observable Symptom
Running `record-settlement` exits with code `2` and outputs:
```json
{
  "code": "settlement_requires_executable_affordance",
  "message": "Affordance 'aff-custom' is not a persisted executable affordance; settlement cannot proceed for an unknown, potential, or possibility identifier."
}
```

### Root Cause
An attempt was made to record a settlement for an affordance ID that either:
1. Was never submitted to `review-horizon`.
2. Lacked a pathway and was stored as a `potential`.
3. Exceeded payment capacity and was stored as a `possibility`.

### Recovery Procedure
1. Check `.godspeed-harness/ledgers/possibilities.jsonl` and `potentials.jsonl` to see why the candidate was diverted.
2. If it was a `possibility`, increase your capacity budget in `--candidates` or reduce estimated costs.
3. Run `godspeed-nav review-horizon` and confirm the candidate appears in `ranked_affordances`.
4. Re-run `record-settlement` using the confirmed affordance ID.

---

## 2. Blocked Representational Transition (`blocked_opposition_jump`)

### Observable Symptom
`review-representational-transition` returns:
```json
{
  "status": "blocked",
  "code": "blocked_opposition_jump",
  "recommended_next_phases": ["abstract", "concrete"]
}
```

### Root Cause
The agent attempted a direct diagonal leap across representational space (e.g. from `general` directly to `specific`) without transitioning through intermediate phases.

### Recovery Procedure
Follow the recommended next phase in the output:
1. First transition from `general` to `abstract` (e.g. document architecture specification).
2. Then transition from `abstract` to `specific` (e.g. define data schemas and interfaces).
3. If this transition represents a routine, repeatedly proven automated process, register `"general->specific"` in `--metabolized-shortcuts`.

---

## 3. `DomainRuleError: incomplete_execution_evidence`

### Observable Symptom
Inbound evidence ingestion fails with:
```json
{
  "code": "incomplete_execution_evidence",
  "message": "Execution evidence rejected: required field 'work_request_id' is missing or empty. Software proof alone is not settlement."
}
```

### Root Cause
An external system (e.g. SWE_SEED or a test harness) submitted an `EvidenceRecorded` event missing one of the 6 mandatory payload fields.

### Recovery Procedure
Ensure your evidence payload dictionary includes all required fields non-emptily:
- `event_id`
- `affordance_id`
- `work_request_id`
- `proof_result_id`
- `expected_result`
- `observed_result`

---

## 4. Circular Motion Flagged (`circular_motion`)

### Observable Symptom
The developmental report displays:
```json
{
  "trajectory": {
    "circular_motion": true,
    "latest_radius": 1.05,
    "latest_theta": 6.8
  }
}
```

### Root Cause
The agent has accumulated $>2\pi$ radians of activity (angular rotation) while achieving $\le 0.1$ radial growth. The system is performing repetitive busywork without developing new capability.

### Recovery Procedure
1. Inspect `repetition_schedules.jsonl` to see what tests are being run.
2. Stop re-executing the same test fixture with identical parameters.
3. Introduce **environmental variation**: change operating conditions, test edge-case inputs, or alter network latencies.
4. If the active goal cannot produce further expansion, archive the direction (`status = "dead"`) and launch a new attractor.

---

## 5. RuVector Bridge Node Missing (`ruvector_node_missing`)

### Observable Symptom
Running `search-developmental-memory` fails with:
```
RuVectorBridgeError [ruvector_node_missing]: Node.js is required for the RuVector bridge.
```

### Root Cause
Node.js is not installed on the system PATH, or npm dependencies have not been installed in `tools/ruvector/`.

### Recovery Procedure
1. Verify Node.js is installed: `node --version`.
2. Navigate to the bridge directory and install dependencies:
   ```bash
   cd tools/ruvector && npm install && cd ../..
   ```
3. Re-run `search-developmental-memory`.

---

### Source Trail
- Domain Errors: `godspeed_nav/schemas.py` (`DomainRuleError`)
- Representational Gating: `godspeed_nav/metrics.py` (`review_representational_transition`)
- Trajectory Detector: `godspeed_nav/trajectory.py` (`detect_circular_motion`)
- RuVector Bridge: `godspeed_nav/ruvector_bridge.py`
