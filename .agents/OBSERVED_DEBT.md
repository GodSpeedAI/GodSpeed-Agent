# Observed Debt

Record concrete debt, gaps, risks, or defects found while working but outside
the current task. Each entry needs evidence, impact, and a next move. Remove an
entry when resolved; do not use this file as a backlog of ideas.

<!-- Entry format:
## Open: Short problem statement
- Observed: YYYY-MM-DD
- Evidence: file, line, command, or failing proof
- Impact: concrete cost or risk
- Next move: smallest credible resolution
- Scope: why it was not fixed in the discovering task
-->

## Open: Legacy DOMAIN_MODEL_HASH falls back to forbidden namespace pseudo-hash
- Observed: 2026-08-26 (pre-existing; re-confirmed during T09)
- Evidence: `agentic_capability_loop/adapters.py` `_load_hash()` returns
  `sha256("agentic_capability_loop")` (`dc144cbd71a4…`) when the SEA manifest
  is absent — the exact constant every canonical convergence gate refuses.
- Impact: legacy Family-A emit path can stamp fallback pseudo-identity; any
  consumer enforcing frozen ENV-I2 fails closed, so legacy envelopes are
  dead-on-arrival at canonical seams.
- Next move: resolve the real manifest digest at startup and refuse to emit
  without it (fail closed) instead of warning + falling back.
- Scope: out of T09 scope; canonical path (`developmental_events.py`) already
  refuses the hash outright.

## Open: variation_context is free-form; relevance of declared variation is unverifiable
- Observed: 2026-08-26 (T09 durable memory gate)
- Evidence: `godspeed_nav/developmental_memory.py` `_evaluate_promotion` checks
  pre-declaration and distinctness of `variation_context`, not semantic
  relevance to the capability.
- Impact: a producer could declare two trivially different contexts to satisfy
  the metabolized bar without meaningful variation.
- Next move: define a declared variation vocabulary/schema when the memory
  ledger needs semantic checks (E10/T10 candidate input).
- Scope: needs a cross-component contract decision, not a runtime-only fix.

## Open: NATS→ledger bridge route should reuse the developmental gate class live
- Observed: 2026-08-26 (T09)
- Evidence: `agentic_capability_loop/publisher.py` drain is offline in the
  harness; live broker composition untested. In-process equivalent proven via
  `godspeed_nav.developmental_memory`.
- Impact: deployed bridge could drift from the tested fail-closed semantics if
  it validates with different code.
- Next move: when the addon bridge is stood up, import
  `developmental_memory.ingest_developmental_event` as its validation route.
- Scope: no broker available in this environment.
