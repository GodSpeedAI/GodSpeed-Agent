# GodSpeed-Agent developmental assessment

GodSpeed-Agent evaluates evidence from attempted work and uses warranted consequences to improve future navigation.

## Language

**Provisional Evidence**:
Received evidence held pending corroboration or assessment before it can support a developmental update.

**Developmental Assessment**:
A judgment about what registered consequences warrant learning or changing about the observer after an attempted transformation.
_Avoid_: Developmental settlement (for the runtime classification), Operational Settlement

**Capability Promotion**:
An authorized change in the standing of a claimed developmental capability supported by qualifying settlements and variation.

**Capability History**:
The ordered, attributable body of attempts, outcomes, and assessments used to judge sustained capability.

## Sources and boundary

The [developmental memory implementation](godspeed_nav/developmental_memory.py), [developmental events](godspeed_nav/developmental_events.py) and [evidence intake](godspeed_nav/evidence_ingest.py) govern this runtime’s local terms. `SettlementRecorded` records the developmental classification and `CapabilityUpdated` records a capability state change on the applicable path. Existing E-series names retain their contract meaning.

An operational receipt or proof can inform Developmental Assessment. Provisional Evidence alone cannot promote capability. The runtime checks cited settlement history and, for the metabolized state, qualifying successful variations and its own lifecycle thresholds. [CognitiveOS v17 §11](https://github.com/GodSpeedAI/godspeed-growth/blob/a1012f0/world/cognitive_os_manifesto_v17.md#11-capability) states the broader theory, including transfer, recovery, lower burden, and discrimination. The runtime thresholds establish only the evidence they measure.
