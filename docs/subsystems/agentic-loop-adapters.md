# Subsystem: Agentic Loop Adapters

The **Agentic Loop Adapters** subsystem bridges GodSpeed-Agent's internal developmental records with external ecosystem protocols (CEP-0008 SS15) and transport brokers (NATS JetStream).

---

## 1. Purpose

The subsystem formats and publishes canonical GodSpeed-Agent events for consumption by external ledgers (such as `memory_ledger` or `agent_memory_ledger`). It provides an offline-first, staging-buffer architecture that guarantees internal navigation loops are never disrupted by external network outages.

---

## 2. Responsibilities

- **Wire Format Standardization**: Wraps internal GSA records into strict `sea.agent.event.v1.json` envelopes.
- **Content-Derived Idempotency Keys**: Generates deterministic SHA-256 idempotency digests across `(correlation_id, event_type, payload)`.
- **Provenance Tracking**: Appends CEP-0008 SS15 lineage records (`origin: "godspeed-agent"` and `chain: ["domain_model_hash:...", "correlation_id:..."]`).
- **Learning Proposal Lifecycle**: Manages learning proposals created from failed settlements or metabolization milestones.
- **Offline-First NATS JetStream Drain**: Flushes buffered outbound events to the subject `sea.agent.event.godspeed-agent.<event_type>` when connectivity is available.

---

## 3. Non-Responsibilities

- **Internal Event Gating**: Does not evaluate whether an affordance settled or whether a capability was earned; that is strictly owned by `godspeed_nav`.
- **Synchronous Delivery Guarantees**: Does not block the runtime waiting for network acknowledgments.

---

## 4. Position in the System

```mermaid
flowchart LR
    GSA["GodSpeed-Agent Runtime\n(NavigationRuntime)"] --> ADAPT["Event Adapters\n(agentic_capability_loop/adapters.py)"]

    ADAPT --> V1["v1 Envelope Builder\n• Idempotency Key (SHA-256)\n• CEP-0008 Provenance"]

    V1 --> OUTBOX["Local Outbox Ledger\n(agentic_outbound_events)"]

    OUTBOX --> PUB["SettlementPublisher\n(agentic_capability_loop/publisher.py)"]

    subgraph External ["External Network"]
        NATS["NATS JetStream Broker\n(sea.agent.event.godspeed-agent.*)"]
        ML["Memory Ledger / Event Log"]
    end

    PUB -.->|One-Way Drain (If Connected)| NATS --> ML
```

---

## 5. Core Abstractions

- `adapters.py`: Pure mapping functions:
  - `settlement_recorded_event`
  - `capability_updated_event`
  - `repetition_planned_event`
  - `learning_proposal_created_event`
  - `coherence_break_detected_event`
- `_idempotency_key`: Generates deterministic dedup hashes:
  $$\text{key} = \text{SHA256}(\text{correlation\_id} + "|" + \text{event\_type} + "|" + \text{JSON}(\text{payload}))$$
- `SettlementPublisher`: Asynchronous publisher class with graceful offline degradation.

---

## 6. Offline-First Staged Transport Pattern

The publisher follows the edge spool pattern:
1. When GodSpeed-Agent commits an event, the adapter writes the canonical v1 envelope to the local ledger `agentic_outbound_events`.
2. The local JSONL ledger remains the authoritative truth.
3. If `GSA_NATS_URL` is configured and the NATS server is reachable, `SettlementPublisher.drain()` publishes un-drained records with the `Nats-Msg-Id` idempotency header.
4. If NATS is unreachable or the `nats` Python package is not installed, the publisher logs a warning and returns zero. **The core navigation loop never halts.**

---

## 7. Envelope Structure (`sea.agent.event.v1.json`)

```json
{
  "event_id": "c1f7b0f1-...",
  "event_type": "SettlementRecorded",
  "occurred_at": "2026-06-03T18:00:00.000000+00:00",
  "idempotency_key": "3a8b...1f0",
  "provenance": {
    "origin": "godspeed-agent",
    "chain": [
      "domain_model_hash:dc144c...",
      "correlation_id:cycle-042"
    ]
  },
  "payload": {
    "affordance_id": "aff-001",
    "settlement_ref": "set-001",
    "settlement_status": "success",
    "score": 1.0
  }
}
```

---

## 8. Failure Modes

| Condition | Behavior | System Impact |
| :--- | :--- | :--- |
| `GSA_NATS_URL` unset | Publisher is permanently disabled. | Events accumulate locally; zero external network traffic. |
| NATS server connection failure | `publish()` catches error and sets `_connected = False`. | Event remains buffered locally; retried on subsequent drain. |
| Missing manifest file | Emits a warning and falls back to SHA-256 of namespace string. | Preserves valid hash structure until formal manifest is installed. |

---

### Source Trail
- Adapter Definitions: `agentic_capability_loop/adapters.py` (lines 1–432)
- Learning Proposals: `agentic_capability_loop/learning_proposals.py` (lines 1–120)
- NATS Publisher: `agentic_capability_loop/publisher.py` (lines 1–207)
- Contract Tests: `agentic_capability_loop/tests/test_adapters.py`, `agentic_capability_loop/tests/test_publisher.py`
