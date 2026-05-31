# Settlement Dataset Adapter Framework Validation Report

**Date:** 2026-05-30
**Datasets:** agenttrove (5), swegym (5), apibank (5), webshop (5)
**Scope:** Full pipeline validation against test fixtures (20 records total)

## 1. Commands Run

```bash
PYTHONPATH=. uv run python scripts/settlement_datasets/ingest_dataset.py --dataset all --limit 5
PYTHONPATH=. uv run python scripts/settlement_datasets/profile_dataset.py --dataset all
PYTHONPATH=. uv run python scripts/settlement_datasets/label_dataset.py --dataset all
PYTHONPATH=. uv run python scripts/settlement_datasets/export_ledger.py --dataset all
PYTHONPATH=. uv run python scripts/settlement_datasets/mine_policies.py --dataset all --min-confidence 0.0 --min-supporting-traces 1
PYTHONPATH=. uv run python scripts/settlement_datasets/build_eval_suites.py --dataset all --min-confidence 0.0
PYTHONPATH=. uv run python scripts/settlement_datasets/mine_metabolization_candidates.py --dataset all --min-confidence 0.0
PYTHONPATH=. uv run python scripts/settlement_datasets/query_ledger.py --db data/settlement_datasets/settlement_ledger.sqlite --query summarize_by_dataset --format json

uv run pytest tests/test_settlement_datasets.py -v   # 66 passed
uv run pytest tests/test_agenttrove.py -q             # 71 passed (no regression)
uv run pytest -q                                       # 270 passed
```

All pipeline stages completed without errors.

## 2. Datasets Sampled

| Dataset | Records | Domain | Source |
|---|---|---|---|
| agenttrove | 5 | code | Fixture: `tests/fixtures/settlement_datasets/agenttrove/sample.jsonl` |
| swegym | 5 | code | Fixture: `tests/fixtures/settlement_datasets/swegym/sample.jsonl` |
| apibank | 5 | api | Fixture: `tests/fixtures/settlement_datasets/apibank/sample.jsonl` |
| webshop | 5 | shopping | Fixture: `tests/fixtures/settlement_datasets/webshop/sample.jsonl` |

AgentTrove also has 100 real traces from the correction pass at `data/agenttrove/raw_samples/sample.jsonl`. The SWE-Gym, API-Bank, and WebShop adapters are fixture-backed in this phase.

## 3. Records Processed

**Total: 20 records across 4 datasets.**

All 20 records were successfully ingested, normalized to the canonical schema, and passed adapter validation with zero errors.

## 4. Parse Success/Failure Counts

| Dataset | Parsed | Parse Failures | Validation Errors |
|---|---|---|---|
| agenttrove | 5 | 0 | 0 |
| swegym | 5 | 0 | 0 |
| apibank | 5 | 0 | 0 |
| webshop | 5 | 0 | 0 |

All adapters correctly parse their fixture data into canonical settlement records.

## 5. Settlement Quality Distribution by Dataset

| Quality | agenttrove | swegym | apibank | webshop |
|---|---|---|---|---|
| clean_success | 2 | 2 | 2 | 1 |
| recovered_success | 1 | 1 | 1 | 1 |
| partial_success | 0 | 0 | 0 | 2 |
| failure_with_signal | 2 | 2 | 1 | 0 |
| unknown | 0 | 0 | 1 | 1 |

Each adapter produces varied settlement quality labels matching its fixture scenarios.

## 6. Confidence Distribution by Dataset

| Dataset | Avg Confidence | High (>=0.65) | Low (<0.65) |
|---|---|---|---|
| agenttrove | 0.860 | 5/5 | 0/5 |
| swegym | 0.800 | 5/5 | 0/5 |
| apibank | 0.680 | 4/5 | 1/5 |
| webshop | 0.600 | 2/5 | 3/5 |

AgentTrove and SWE-Gym produce the highest confidence labels. WebShop has the lowest, primarily because some shopping scenarios produce `unknown` or `partial_success` settlements with lower structural signal confidence.

## 7. Top Failure Modes by Dataset

### agenttrove
- tool_thrashing: 1
- failed_recovery: 1
- premature_closure: 1
- context_loss: 1
- unknown: 1

### swegym
- test_failure: 2

### apibank
- wrong_tool: 1
- wrong_arguments: 1

### webshop
- constraint_miss: 1
- premature_choice: 1
- over_search: 1

Each adapter produces domain-specific failure modes. Code adapters produce test/command failures. API adapter produces tool/argument errors. Shopping adapter produces constraint/search failures.

## 8. Top Recovery Patterns

4 traces classified as `recovered_success`:
- agenttrove: 1 (error → fix → success)
- swegym: 1 (bad patch → re-edit → pass)
- apibank: 1 (wrong room → correct room → success)
- webshop: 1 (no results → refined search → found)

Recovery patterns span all domains, suggesting cross-domain recovery skills are viable metabolization targets.

## 9. Candidate Harness Policies

8 policies mined at min_confidence=0.0, min_support=1:

| Policy | Traces | Datasets | Status |
|---|---|---|---|
| compare_constraints_before_selection | 3 | 2 | proposed |
| require_explicit_settlement_for_failure | 3 | 2 | proposed |
| require_reflection_after_repeated_errors | 2 | 1 | proposed |
| search_before_patch | 2 | 1 | proposed |
| inspect_api_schema_before_call | 2 | 1 | proposed |
| reset_plan_after_payment_spiral | 1 | 1 | proposed |
| test_before_final_answer | 1 | 1 | proposed |
| prevent_premature_concretion | 1 | 1 | proposed |

All policies default to `proposed`. None are auto-activated. Cross-dataset policies (compare_constraints, require_explicit_settlement) have supporting evidence from 2+ datasets.

## 10. Metabolization Candidates

7 candidates mined at min_confidence=0.0:

| Candidate | Supporting Traces | Status |
|---|---|---|
| reflect_after_repeated_tool_error | 11 | repeated |
| test_before_final_answer | 11 | repeated |
| search_before_patch | 11 | repeated |
| inspect_api_schema_before_call | 11 | repeated |
| compare_constraints_before_selection | 11 | repeated |
| reset_plan_after_payment_spiral | 11 | repeated |
| route_through_intermediate_representation | 11 | repeated |

All candidates are at `repeated` status (>=3 supporting traces) but none are `metabolized` without harness validation. The high trace counts reflect permissive confidence filtering; at 0.65 threshold, these counts would decrease.

## 11. Example Normalized Settlement Records

### agenttrove: clean_success
```json
{
  "dataset": "agenttrove",
  "domain": "code",
  "task_id": "cc-impl-sort",
  "outcome": {"settlement_quality": "clean_success", "confidence": 0.95},
  "payment": {"turns": 6, "commands": 2, "error_count": 0},
  "environment": {"type": "simulated_terminal", "feedback_type": "tool_output"}
}
```

### swegym: clean_success
```json
{
  "dataset": "swegym",
  "domain": "code",
  "task_id": "swe-clean-001",
  "outcome": {"settlement_quality": "clean_success", "confidence": 0.9},
  "payment": {"turns": 8, "commands": 3, "error_count": 0},
  "environment": {"type": "code_repository", "feedback_type": "tests"}
}
```

### apibank: clean_success
```json
{
  "dataset": "apibank",
  "domain": "api",
  "task_id": "api-clean-001",
  "outcome": {"settlement_quality": "clean_success", "confidence": 0.9},
  "payment": {"turns": 3, "api_calls": 1, "error_count": 0},
  "environment": {"type": "api_sandbox", "feedback_type": "tool_output"}
}
```

### webshop: clean_success
```json
{
  "dataset": "webshop",
  "domain": "shopping",
  "task_id": "ws-clean-001",
  "outcome": {"settlement_quality": "clean_success", "confidence": 0.9},
  "payment": {"turns": 3, "page_actions": 1, "error_count": 0},
  "environment": {"type": "web_shopping", "feedback_type": "state_check"}
}
```

## 12. Examples of Rejected Low-Confidence Records

At confidence threshold 0.65, these records would be excluded from policy mining and eval generation:

| Dataset | Task ID | Quality | Confidence | Reason |
|---|---|---|---|---|
| apibank | api-wrong-args-004 | unknown | 0.1 | No structural signal for settlement quality |
| webshop | ws-wrong-item-003 | unknown | 0.1 | Constraint mismatch with no clear outcome |
| webshop | ws-premature-004 | partial_success | 0.6 | Below 0.65 threshold |
| webshop | ws-over-search-005 | partial_success | 0.6 | Below 0.65 threshold |

## 13. Known Weaknesses

1. **WebShop confidence is consistently lower** — The shopping domain's structural signals are weaker than code/API domains. Success/failure is often ambiguous (partial matches, subjective constraint satisfaction).

2. **Metabolization candidate matching is too permissive** — At min_confidence=0.0, most successful traces match most candidate templates. The matching heuristics need tightening per domain.

3. **SWE-Gym is fixture-backed** — The adapter uses synthetic SWE-style traces. Real SWE-Gym or SWE-Bench traces would exercise different failure modes (complex multi-file patches, deep dependency chains).

4. **API-Bank failure mode detection is coarse** — Only detects wrong_tool, wrong_arguments, and missing_precondition. Real API traces may have more nuanced failure patterns (rate limiting, cascading failures, state-dependent errors).

5. **Cross-dataset policy aggregation is simple** — Currently counts failure modes across datasets. Does not weight by dataset size, domain relevance, or confidence distribution.

6. **AgentTrove adapter inherits the existing pipeline's complexity** — The `to_settlement_record` method delegates to the full AgentTrove label_trace pipeline, which requires the YAML rules config. This coupling is intentional for backward compatibility but adds complexity.

## 14. Recommended Next Fixes

1. **Increase fixture coverage** — Add 20+ records per adapter to exercise more edge cases (null reward, long traces, multi-step recovery, malformed data).

2. **Tighten metabolization matching** — Add domain-specific matching heuristics instead of one-size-fits-all pattern matching.

3. **Add real SWE-Gym data** — Implement HuggingFace streaming for SWE-Gym or SWE-Bench traces to validate against real code repair data.

4. **Improve WebShop confidence calibration** — The shopping domain needs domain-specific structural signals beyond reward alone.

5. **Weight cross-dataset policies** — Weight policy evidence by dataset size and domain relevance, not just raw trace count.

6. **Add SFT export to the framework** — Port the existing AgentTrove ShareGPT export to work across all adapters with label-gating.

7. **Add config YAML for each adapter** — Move hardcoded thresholds (confidence, payment complexity) into per-adapter YAML configs similar to `configs/agenttrove/settlement_label_rules.yaml`.
