# Settlement Dataset RuVector Extension

## Why RuVector Is Not Required in This Phase

The current settlement dataset framework operates entirely on deterministic, structured data. All operations — ingestion, profiling, labeling, policy mining, eval construction, metabolization candidate mining — use exact field matching, counting, and rule-based classification. These operations do not require vector similarity search.

RuVector is reserved for a future phase when the volume and diversity of settlement records justify semantic retrieval over structured queries.

## Future Vector Memory Use Cases

When the settlement ledger grows to contain records from many datasets and domains, the following use cases become relevant:

1. **Failure mode similarity search:** Given a new failure during live harness operation, find historically similar failures and their recovery paths.
2. **Recovery path retrieval:** Given a failure mode and context, find the lowest-payment recovery path from historical traces.
3. **Cross-domain pattern transfer:** Find successful patterns from one domain that may apply to a different domain facing a structurally similar problem.
4. **Metabolization candidate enrichment:** Augment structured pattern matching with semantic similarity to discover patterns not captured by templates.
5. **Policy conflict detection:** Detect semantically similar policies that may conflict when both are active.

## How Settlement Summaries Would Be Embedded

Only structured summaries would be embedded, never raw traces:

- **Settlement summary:** Dataset, domain, settlement quality, confidence, failure mode, payment profile, path shape.
- **Affordance path summary:** Action types and counts, observation types, recovery events.
- **Label summary:** Failure mode, policy signal, metabolization candidate, with evidence.

Raw traces are too long, noisy, and inconsistent for effective embedding. The canonical schema provides the structure needed for meaningful vector retrieval.

## Extension Point Design

The RuVector extension would plug into two surfaces:

1. **Ledger export:** After exporting settlement records to SQLite, generate embeddings for settlement summaries and store them in a vector index alongside the ledger.
2. **Query interface:** Add semantic query methods to `query_ledger.py` that combine structured filters (dataset, quality, confidence) with vector similarity ranking.

The existing `LedgerStore.search_developmental_memory()` method in `godspeed_nav/storage.py` already provides the interface. The settlement dataset extension would populate the index that this method queries.

No schema changes are required. The canonical settlement record already contains all the structured fields needed for summary generation and embedding.

## When to Consider Activating RuVector

Consider activating RuVector when:

1. **Sufficient settlement history exists.** The ledger contains records from 3+ datasets with diverse failure modes and recovery patterns.
2. **Structured queries reach their limit.** Exact field matching cannot find relevant patterns because the search context is novel or cross-domain.
3. **Pattern volume exceeds manual review.** The number of metabolization candidates and policy proposals is large enough that semantic ranking improves triage efficiency.
4. **The harness has a live retrieval need.** The harness needs to retrieve historical settlement patterns during real-time operation, not just offline analysis.

Until these conditions are met, structured queries and deterministic mining are sufficient and preferred.
