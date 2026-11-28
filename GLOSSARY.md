# GodSpeed-Agent developmental assessment

GodSpeed-Agent evaluates evidence from attempted work and uses warranted consequences to improve future navigation.

## Language

**Provisional Evidence**:
Received evidence held pending corroboration or assessment before it can support a developmental update.

**Developmental Assessment**:
A judgment about what registered consequences warrant learning or changing about the observer after an attempted transformation.
_Avoid_: Developmental settlement (for the runtime classification), Operational Settlement

**Capability Promotion**:
An authorized change in the standing of a claimed developmental capability supported by cited, recorded settlements of that capability. The gate (`_evaluate_promotion`, `godspeed_nav/developmental_memory.py`) scales the bar with the target:

- `active` needs one successful settlement.
- `repeated` (and any other target below `metabolized`) needs at least two successful settlements scoring 0.7 or higher (`Capability.from_settlements`, `godspeed_nav/schemas.py`). It runs no variation check, so both settlements may share one context.
- `metabolized` needs the same two successes, each carrying a declared variation context recorded before the request, at least two distinct contexts among them, and a lifecycle that the stability and metabolization scores support. Variation asserted inline in the request does not count.

**Capability History**:
The ordered, attributable body of attempts, outcomes, and assessments used to judge sustained capability.

## Sources and boundary

The [developmental memory implementation](godspeed_nav/developmental_memory.py), [developmental events](godspeed_nav/developmental_events.py) and [evidence intake](godspeed_nav/evidence_ingest.py) govern this runtime’s local terms. `SettlementRecorded` records the developmental classification and `CapabilityUpdated` records a capability state change on the applicable path. Existing E-series names retain their contract meaning.

An operational receipt or proof can inform Developmental Assessment. Provisional Evidence alone cannot promote capability. The runtime checks cited settlement history and, for the metabolized state, qualifying successful variations and its own lifecycle thresholds. [CognitiveOS v17 §11](https://github.com/GodSpeedAI/godspeed-growth/blob/a1012f0/world/cognitive_os_manifesto_v17.md#11-capability) states the broader theory, including transfer, recovery, lower burden, and discrimination. The runtime thresholds establish only the evidence they measure.
