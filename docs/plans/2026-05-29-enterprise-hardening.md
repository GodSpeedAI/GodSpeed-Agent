# Enterprise Hardening Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Mature Godspeed Agent Harness from a conforming scaffold into an enterprise-shippable local developmental runtime aligned with `Cognitive Operating Systems (1).pdf`.

**Architecture:** Add an orchestration layer over the existing deterministic modules, strengthen ledger durability, and expose workflow commands that create connected developmental records rather than isolated calculations. Keep the system local-first, deterministic by default, and test-first.

**Tech Stack:** Python 3.11+, uv, pytest, PyYAML, NumPy/Pandas where useful, JSONL storage, optional Scikit-learn only behind maturity gates.

## Phase 1: Runtime Orchestration Foundation

Build `godspeed_nav/runtime.py` and `godspeed_nav/policies.py` to coordinate desired directions, horizon review, affordance ranking, payment estimation, settlement recording, trajectory update, and metabolization review. Add CLI commands for starting a direction, reviewing the horizon, selecting an affordance, recording settlement, and generating a runtime snapshot.

Verification: workflow tests prove one complete desired-direction cycle writes consistent ledgers and returns the next affordable affordance.

## Phase 2: Enterprise Ledger Durability

Strengthen `LedgerStore` with safe ledger names, atomic append locks, typed event envelopes, monotonic sequence numbers, checksums, index files, backup/export commands, migration/version metadata, and richer quarantine reports.

Verification: storage tests cover concurrent appends, unsafe ledger names, corrupt records, backup/export round trips, and indexed reads.

## Phase 3: Policy Gates and Safety

Implement policy enforcement for unaffordable actions, human review requirements, disintegration safeguards, absorption prerequisites, simulation thresholds, and ML maturity thresholds. Make policy decisions explainable and ledger-backed.

Verification: tests prove high-risk disintegration and absorption require review, unaffordable actions block when configured, and ML refuses below settlement thresholds.

## Phase 4: Developmental Observability

Add report generation for settlement quality, payment debt, horizon drift, circular motion, metabolization candidates, dead directions, and self-critique findings. Expose reports via CLI and local files under `.godspeed-harness/reports`.

Verification: report tests build reports from fixture ledgers and assert actionable fields.

## Phase 5: Hooks and MCP as Workflow Surfaces

Upgrade hooks and MCP wrapper so they call the runtime orchestration layer, not only individual calculators. Hook failures must never corrupt ledgers. MCP tools must keep filesystem access inside configured storage roots.

Verification: hook/MCP tests cover end-to-end event ingestion and structured error codes.

## Phase 6: Enterprise Documentation and Release Gates

Add installation, configuration, operations, security, backup/restore, incident recovery, release checklist, and enterprise readiness docs. Add a `godspeed-nav validate` command that runs package, config, storage, hook, report, and sample workflow checks.

Verification: `uv run pytest -q` and `uv run python -m godspeed_nav.cli validate` pass on a clean checkout.

