# Godspeed Agent Harness

Godspeed Agent Harness is a local-first Claude Code plugin and Python harness for horizon-centric cybernetic navigation. It converts desired directions into horizon checks, affordance candidates, payment estimates, settlement events, and developmental memory.

Outcome completion is not terminal. A settled outcome becomes substrate and should expose new affordances.

## Package

- `.claude-plugin/plugin.json` contains plugin identity metadata.
- `skills/`, `agents/`, `hooks/`, `mcp/`, `monitors/`, `bin/`, and settings files live at plugin root level.
- `godspeed_nav/` contains deterministic local computation and storage code.

## Implementation-defined Behavior

Implementation-defined defaults are documented in `HARNESS.md`. This implementation uses `.godspeed-harness` as the local storage root, JSONL ledgers, Python deterministic computation, and a default maximum payment burden of `100`.

No external API calls by default. MCP tools and hook scripts operate on local input, local computation, and configured local storage.

## Self-Critique

The harness doctrine is not protected from review. Use the `framework-reconstruction` skill when doctrine, policy, skills, or navigation assumptions fail settlement. Failed structure should dissolve or be replaced, and repeated successful patterns should become substrate.

## Verification

Run:

```bash
uv run pytest -q
```

Sample CLI:

```bash
uv run python -m godspeed_nav.cli compute-error --desired '{"tests": 3}' --observed '{"tests": 1}'
```
