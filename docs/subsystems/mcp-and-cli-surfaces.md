# Subsystem: MCP & CLI Surfaces

The **MCP & CLI Surfaces** subsystem provides the primary execution interfaces through which human operators, terminal scripts, and AI agents (such as Claude Code) interact with GodSpeed-Agent.

---

## 1. Purpose

The subsystem exposes the complete capabilities of the runtime—from stateless error calculations to complex multi-ledger horizon reviews—via standard terminal CLI commands and a local JSON-RPC Model Context Protocol (MCP) server.

---

## 2. Responsibilities

- **CLI Dispatching**: Implements `godspeed-nav` subcommands with robust argument parsing, JSON decoding, and typed error handling.
- **MCP Server Implementation**: Exposes 21 typed cybernetic tools over `stdio` using the standard JSON-RPC MCP specification.
- **Exit Code & Serialization Contracts**:
  - Exits `0` with sorted JSON output on successful completion.
  - Exits `2` with `{"code": "...", "message": "..."}` on `DomainRuleError`.
  - Exits `1` on unhandled unexpected runtime faults.
- **Workspace Resolution**: Dynamically discovers and links target workspace directories and `.godspeed-harness` storage roots.

---

## 3. Non-Responsibilities

- **Business Logic Implementation**: Contains zero business rules; strictly validates arguments and delegates to `NavigationRuntime`, `metrics`, `storage`, and `validation`.

---

## 4. Position in the System

```mermaid
flowchart TD
    subgraph Operators ["Invoking Entities"]
        USER["Human Operator / Bash Script"]
        CLAUDE["Claude Code (MCP Client)"]
    end

    subgraph Surfaces ["MCP & CLI Subsystem"]
        CLI["godspeed_nav/cli.py\n(Argparse Dispatcher)"]
        MCP["mcp/cybernetic_nav_server/server.py\n(JSON-RPC over stdio)"]
    end

    subgraph Runtime ["Core Systems"]
        NR["NavigationRuntime"]
        MET["Metrics & Scoring"]
        VAL["Enterprise Validation"]
    end

    USER -->|Terminal Arguments| CLI
    CLAUDE -->|tools/call (JSON-RPC)| MCP

    CLI --> NR
    CLI --> MET
    CLI --> VAL

    MCP --> NR
    MCP --> MET
    MCP --> VAL
```

---

## 5. The 21 MCP Tools

The MCP server exposes 21 distinct tools grouped under the `cybernetic_nav.` namespace:

| Tool Name | CLI Command Equivalent | Primary Function |
| :--- | :--- | :--- |
| `cybernetic_nav.compute_error` | `compute-error` | Weighted distance between desired and observed states. |
| `cybernetic_nav.estimate_payment` | `estimate-payment` | Evaluates multidimensional payment burden and spendability. |
| `cybernetic_nav.rank_affordances` | `rank-affordances` | Orders candidates by expected expansion vs burden. |
| `cybernetic_nav.review_representational_transition` | `review-representational-transition` | Checks adjacency and blocks opposition jumps. |
| `cybernetic_nav.score_settlement` | `score-settlement` | Evaluates empirical consequence from before/after state diffs. |
| `cybernetic_nav.update_trajectory` | N/A (Internal/CLI) | Updates polar coordinates $(\theta, r)$. |
| `cybernetic_nav.detect_circular_motion` | N/A (Internal/CLI) | Checks for $\ge 2\pi$ rotation with $\le 0.1$ radial growth. |
| `cybernetic_nav.compute_metabolization` | `metabolization` | Evaluates 6-factor substrate readiness. |
| `cybernetic_nav.review_absorbability` | `absorbability` | Audits candidate license, pathway, and human review gates. |
| `cybernetic_nav.review_positive_disintegration` | N/A (Direct) | Evaluates dissolution vs salvage for high-debt structures. |
| `cybernetic_nav.start_direction` | `start-direction` | Initializes an active desired direction and horizon. |
| `cybernetic_nav.review_horizon` | `review-horizon` | Gates candidates and produces ranked affordances. |
| `cybernetic_nav.record_settlement` | `record-settlement` | Commits verified consequence to the settlement ledger. |
| `cybernetic_nav.runtime_snapshot` | `runtime-snapshot` | Returns active directions and counts across all ledgers. |
| `cybernetic_nav.cognitive_surfaces` | `cognitive-surfaces` | Inspects representational, repetition, and critique state. |
| `cybernetic_nav.developmental_report` | `developmental-report` | Produces comprehensive health and trajectory report. |
| `cybernetic_nav.predictive_extensions` | `predictive-extensions` | Executes advisory heuristic or sklearn predictions. |
| `cybernetic_nav.write_ledger_event` | N/A (Direct API) | Appends custom event envelope to specified ledger. |
| `cybernetic_nav.read_developmental_memory` | N/A (Direct API) | Queries lineage: paid paths, failures, substrate. |
| `cybernetic_nav.search_developmental_memory` | `search-developmental-memory` | Local RuVector semantic vector search over memory. |
| `cybernetic_nav.validate_enterprise_readiness` | `validate` | Runs complete 12-point enterprise audit suite. |

---

## 6. Error Handling & Exit Contracts

The CLI catches `DomainRuleError` explicitly and writes structured JSON to `stderr`:
```bash
$ godspeed-nav record-settlement --affordance-id unknown-id ...
# Output on stderr:
{"code": "settlement_requires_executable_affordance", "message": "Affordance 'unknown-id' is not a persisted executable affordance..."}
# Exit code: 2
```

In the MCP server, errors are captured and returned in standard tool call format:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "isError": true,
    "content": [
      {
        "type": "text",
        "text": "DomainRuleError [settlement_requires_executable_affordance]: Affordance 'unknown-id' is not a persisted executable affordance..."
      }
    ]
  }
}
```

---

### Source Trail
- CLI Implementation: `godspeed_nav/cli.py` (lines 1–313)
- MCP Implementation: `mcp/cybernetic_nav_server/server.py` (lines 1–218)
- Comprehensive Reference: `docs/references/cli-reference.md`
- Test Suite: `tests/test_cli_hooks_mcp.py`
