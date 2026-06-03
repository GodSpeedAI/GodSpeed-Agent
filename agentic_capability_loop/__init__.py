"""agentic_capability_loop adapter for GodSpeed-Agent.

This package handles the settlement phase of the agentic capability loop:
  - Consumes EvidenceRecorded events
  - Emits SettlementRecorded, CapabilityUpdated, RepetitionPlanned, TwinUpdated
  - Detects CoherenceBreak and emits LearningProposalCreated

See: docs/specs/domains/agentic_capability_loop/agentic_capability_loop.manifest.json (in SEA-Forge)
"""
