# RuVector Extension Point

## Status

RuVector integration is now implemented as a local bridge for structured developmental-memory search. The active bridge keeps Python as the truth surface owner and calls a small Node sidecar in `tools/ruvector/` to run RuVector similarity search over settlement and critique summaries.

Current limits:

- The bridge indexes structured summaries only; it does not ingest raw traces.
- The bridge rebuilds search state from the current structured documents for each query instead of maintaining a long-running external service.
- The active public surface is `godspeed-nav search-developmental-memory` and the corresponding `LedgerStore.search_developmental_memory(...)` method.

## What Should Be Embedded

Only labeled and structured content should be embedded:

- **Failure mode summaries** - Concise descriptions of detected failure patterns
- **Recovery event summaries** - How agents recovered from errors
- **Settlement records** - The full labeled settlement record
- **Policy evidence summaries** - Evidence supporting generated policies
- **Skill candidates** - Metabolization candidates with action sequences

## What Should Not Be Embedded

- **Raw traces** - Unlabeled traces are noisy and expensive to search
- **Full message content** - Too verbose; use summaries instead
- **Traces without settlement labels** - No structure for meaningful retrieval
- **Brittle successes without flags** - May mislead retrieval

## Why Raw Traces Should Not Be Embedded Before Labeling

1. Raw traces are long, noisy, and inconsistent in format
2. Without settlement labels, similarity search returns structurally similar traces that may have opposite outcomes
3. Embedding cost is proportional to content length; labeled summaries are much cheaper
4. Raw trace retrieval provides no actionable insight without the failure mode and settlement quality context

## How Settlement Records Support Semantic Retrieval

Settlement records provide the structured context that makes vector retrieval meaningful:

- **Failure mode** provides the search key (find traces similar to current failure)
- **Settlement quality** filters the result set (only recovered successes or clean failures)
- **Payment pattern** calibrates the result (find low-payment paths for the same task type)
- **Path shape** ensures representational compatibility (direct jumps vs. gradual transitions)

## Active Retrieval Use Cases

- Find traces similar to the current failure
- Find recovered successes for the same failure mode
- Find direct-jump failures in the same domain
- Find low-payment successful paths
- Find metabolization candidates by domain
- Find skill-induction candidates from repeated patterns
- Find harness policy violations in historical traces

## Implementation Path

The current bridge follows this path already:

1. Embed settlement record summaries (not raw traces)
2. Index by failure mode, settlement status, pathway text, and source ledger
3. Return semantic matches through the local CLI/storage surfaces

Future expansions can still add richer filtering, longer-lived indexes, and direct policy-feedback loops once settlement pressure justifies them.
