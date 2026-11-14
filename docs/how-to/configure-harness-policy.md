# How-To: Configure Harness Policy

This guide explains how to customize GodSpeed-Agent's operational parameters, payment limits, and review gates via `HARNESS.md`.

---

## 1. Goal

Configure project-level safety boundaries, payment capacities, model providers, and review gates to match your deployment requirements.

---

## 2. Configuration Location

GodSpeed-Agent reads policy configuration from the YAML frontmatter of `HARNESS.md` located in your project's workspace root:

```markdown
---
harness:
  mode: local
  primary_metric: horizon_expansion
  allow_outcome_language: true
  outcome_as_terminal: false
storage:
  root: .godspeed-harness
  format: jsonl
  retain_raw_events: true
  redact_secrets: true
computation:
  engine: python
  use_pandas: true
  use_numpy: true
  model_provider: heuristic
  ml_event_threshold: 200
  simulation_threshold: 1000
safety:
  block_unaffordable_actions: false
  warn_unaffordable_actions: true
  max_payment_burden: 100
  require_human_review_for_absorption: true
  require_human_review_for_disintegration: true
---
```

---

## 3. Configuration Scenarios

### Scenario A: Strict Production CI Mode
*Objective*: Hard-block any action exceeding capacity, enforce maximum human review, and keep risk ceilings low ($0.05$).

```yaml
safety:
  block_unaffordable_actions: true
  warn_unaffordable_actions: false
  max_payment_burden: 50
  require_human_review_for_absorption: true
  require_human_review_for_disintegration: true
computation:
  model_provider: heuristic
  ml_event_threshold: 500
```
*Effect*: Any affordance whose payment burden exceeds capacity raises an immediate policy block. No un-reviewed external code can be absorbed.

---

### Scenario B: Autonomous Research & Exploration
*Objective*: Allow experimental exploration, enable advisory warnings instead of hard blocks, and permit larger payment burdens ($200$).

```yaml
safety:
  block_unaffordable_actions: false
  warn_unaffordable_actions: true
  max_payment_burden: 200
  require_human_review_for_absorption: false
  require_human_review_for_disintegration: true
computation:
  model_provider: sklearn
  ml_event_threshold: 50
```
*Effect*: Unaffordable candidates are flagged with warnings rather than blocked; the scikit-learn provider activates after only 50 recorded settlements.

---

## 4. Validating Your Configuration

After modifying `HARNESS.md`, verify that the configuration parses correctly and satisfies enterprise requirements:

```bash
uv run godspeed-nav validate --workspace-root .
```

Confirm that `checks.config.passed` is `true`.

---

### Source Trail
- Schema & Parser: `godspeed_nav/config.py`
- Policy Enforcement: `godspeed_nav/policies.py`
- Reference Manual: `docs/references/policy-reference.md`
