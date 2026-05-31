# Metabolization Candidate Mining

## What Metabolization Candidates Are

Metabolization candidates are repeated successful or recovered behavioral patterns extracted from settlement records. They represent affordances that have survived settlement across multiple traces and are ready for harness validation.

A candidate is not yet a metabolized capability. It is a pattern that has been observed, extracted, and proposed as a potential skill. The distinction matters: metabolization requires repetition, time, and successful settlement in the live harness. Candidates are the starting point, not the conclusion.

## How Candidates Are Mined

The mining process:

1. **Filter by confidence:** Only records with `outcome.confidence >= min_confidence` (default 0.65) are considered.
2. **Match against templates:** Each candidate template defines a pattern (e.g., "reflect_after_repeated_tool_error", "search_before_patch"). Records are matched based on settlement quality, failure mode, payment profile, and representational path shape.
3. **Aggregate supporting traces:** Records matching a template are collected with their task IDs, datasets, settlement quality distribution, and payment profiles.
4. **Assign status:** Candidates with 3+ supporting traces receive `"repeated"` status. Candidates with fewer receive `"candidate"` status.
5. **Assemble proposed skill:** Each candidate includes a proposed skill with trigger, procedure, settlement criteria, and retirement criteria.

## Candidate Schema

Each candidate record contains:

```json
{
  "candidate_id": "string",
  "domain": "string",
  "dataset_sources": ["string"],
  "pattern_name": "string",
  "description": "string",
  "supporting_trace_count": "integer",
  "supporting_trace_ids": ["string"],
  "settlement_quality_distribution": {"quality": count},
  "payment_profile": {
    "median_steps": "integer",
    "median_tool_calls": "integer",
    "median_error_count": "integer"
  },
  "failure_modes_recovered_from": ["string"],
  "proposed_skill": {
    "name": "string",
    "trigger": "string",
    "procedure": ["string"],
    "settlement_criteria": "string",
    "retirement_criteria": "string"
  },
  "metabolization_status": "candidate | repeated",
  "risks": ["string"],
  "evidence_summary": "string"
}
```

## Status Progression

```
candidate -> repeated -> tested -> metabolized
```

| Status | Meaning | How Assigned |
|---|---|---|
| `candidate` | Pattern observed in fewer than 3 traces | Fewer than 3 supporting traces |
| `repeated` | Pattern observed in 3+ traces across one or more datasets | 3 or more supporting traces |
| `tested` | Pattern validated against eval suites in the harness | Manual: after eval testing |
| `metabolized` | Pattern has survived repeated settlement in the live harness | Manual: after harness validation |

## Why Candidates Stay at "candidate" or "repeated" Until Harness Validation

The mining process can only assign `candidate` or `repeated` status. It cannot assign `tested` or `metabolized` because:

1. **Mining is retrospective.** It examines historical traces, not live harness behavior. A pattern that appears successful in historical data may not generalize.
2. **Metabolization requires the live loop.** Per the framework doctrine, capabilities become real only after they survive settlement. Settlement requires the full desired-direction-to-outcome loop, not just pattern extraction from static traces.
3. **No auto-promotion.** The mining output is input to the harness validation process, not a substitute for it.

To promote a candidate to `tested`, run it against the corresponding eval suite. To promote to `metabolized`, demonstrate repeated successful settlement in the live harness over time.

## Available Pattern Templates

| Pattern Name | Description | Match Criteria |
|---|---|---|
| `reflect_after_repeated_tool_error` | After 3+ errors, agent reflects and changes approach | error_count >= 2, settlement quality is clean_success or recovered_success |
| `test_before_final_answer` | Before submitting, agent runs verification | clean_success with test feedback |
| `search_before_patch` | Before editing, agent searches relevant context | Failure mode is poor_localization or bad_patch, then recovered to success |
| `inspect_api_schema_before_call` | Before API calls, agent inspects schemas | Failure mode is wrong_tool or wrong_arguments, then recovered to success |
| `compare_constraints_before_selection` | Before selecting, agent compares against constraints | Failure mode is constraint_miss or premature_choice, then recovered to success |
| `reset_plan_after_payment_spiral` | When payment exceeds threshold, agent resets approach | Failure mode is payment_spiral or over_search, with recovery |
| `route_through_intermediate_representation` | For complex tasks, agent creates intermediate plan | clean_success with GA_to_SA_to_SC or GA_to_GC_to_SC path shape |

## How to Use Candidates for Skill Development

1. **Mine candidates:**

```bash
uv run python -m scripts.settlement_datasets.mine_metabolization_candidates --dataset all
```

2. **Review candidate output:**

```bash
cat data/settlement_datasets/metabolization_candidates/candidates.jsonl | python -m json.tool --no-ensure-ascii
```

3. **Select a candidate with `repeated` status.** These have the strongest evidence.

4. **Extract the proposed skill.** Each candidate includes a `proposed_skill` with trigger, procedure, settlement criteria, and retirement criteria.

5. **Implement the skill in the harness.** Use the proposed procedure as the starting implementation.

6. **Test against eval suites.** Run the skill against the corresponding eval suite to verify settlement behavior.

7. **Monitor in the live loop.** If the skill produces repeated successful settlement, promote the candidate to `metabolized`.

## Running the Miner

```bash
uv run python -m scripts.settlement_datasets.mine_metabolization_candidates --dataset all --min-confidence 0.65
```

Output: `data/settlement_datasets/metabolization_candidates/candidates.jsonl`
