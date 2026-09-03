# How-To: Run Enterprise Readiness Validation

This guide shows you how to run and interpret GodSpeed-Agent's 12-point enterprise validation suite to audit workspace integrity, storage invariants, policy gates, and doctrine drift.

---

## 1. Goal

Verify that a GodSpeed-Agent installation or receiving workspace meets all enterprise architectural standards, that no required files are missing, that storage invariants hold under lock, and that doctrine terms remain uncompromised.

---

## 2. Prerequisites

- Python 3.11+ environment with `godspeed-nav` installed or runnable via `uv run`.
- Read and write access to the target workspace.

---

## 3. Procedure

Execute the validation command pointing to your workspace and a dedicated validation storage root:

```bash
uv run godspeed-nav validate \
  --workspace-root . \
  --storage-root .godspeed-harness/validation
```

---

## 4. Interpreting Output

A fully compliant repository returns exit code `0` and a JSON object containing:

```json
{
  "all_passed": true,
  "checks": {
    "config": { "passed": true },
    "developmental_memory": { "passed": true },
    "developmental_report": { "passed": true },
    "doctrine_drift": { "passed": true },
    "executable_affordance_rule": { "passed": true },
    "mcp_server": { "passed": true },
    "plugin_structure": { "passed": true },
    "predictive_extensions": { "passed": true },
    "provisional_evidence_boundary": { "passed": true },
    "runtime_workflow": { "passed": true },
    "storage": { "passed": true },
    "storage_invariants": { "passed": true }
  }
}
```

---

## 5. Troubleshooting Check Failures

### Failure in `plugin_structure`
- **Symptom**: `"plugin_structure": {"passed": false, "details": {"missing": [".claude-plugin/plugin.json"]}}`
- **Fix**: Ensure all standard plugin root files exist. Restore missing manifests from repository templates.

### Failure in `doctrine_drift`
- **Symptom**: `"doctrine_drift": {"passed": false, "details": {"doctrine_drift_detected": true}}`
- **Fix**: Check `docs/references/policy-reference.md` and `agents/evaluator.md`. The validation suite verifies that these files explicitly declare:
  1. Simulation is not settlement.
  2. Intent-only evidence is rejected.
  Restore the normative language if it was accidentally edited.

### Failure in `executable_affordance_rule`
- **Symptom**: Settling an unknown affordance did not raise `settlement_requires_executable_affordance`.
- **Fix**: Verify that `godspeed_nav/runtime.py` contains `_require_executable_affordance` and that no code changes bypassed the check.

### Failure in `storage_invariants`
- **Symptom**: Atomic append-if-absent failed or secret redaction failed.
- **Fix**: Check file permissions on `.godspeed-harness/ledgers/`. Verify that operating-system file locking (`flock`) is supported on your filesystem.

---

### Source Trail
- Validation Implementation: `godspeed_nav/validation.py`
- CLI Command: `godspeed_nav/cli.py` (`subcommands.add_parser("validate")`)
- Test Contract: `tests/test_validation.py`
