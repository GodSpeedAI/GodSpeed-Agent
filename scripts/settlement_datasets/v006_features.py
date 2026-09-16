"""v006 prefix-trajectory feature extraction over the shared corpus.

Three named feature families (naming is normative for the v006 dual-model
plan, amendments 1 and 10):

- ``v005_full_semantics``: exact replication of the 11 frozen v005
  features (``.agents/reports/v006-v005-reconstruction.md`` section 1)
  computed over a COMPLETE parent record.  Equivalence contract: for any
  parent produced by ``build_trajectory_corpus.build_parent``, these
  features equal
  ``run_calibration_pipeline.external_record_to_model_calibration`` +
  ``godspeed_nav.cognitive_model.build_calibration_frame`` flattening
  exactly (same rounding, same types).  Counters come verbatim from the
  corpus ``counts`` block, which copies the settlement record's payment
  counters: ``turns`` = adapter action count, ``tool_calls`` = adapter
  observation count, ``commands`` = adapter bash-mention count,
  ``error_count`` = adapter error counter, ``elapsed_steps`` =
  ``total_messages`` (all messages INCLUDING user/system context).
  ``error_recovery_ratio`` reproduces the H turn-index comparison rule
  over observation events (``i`` values), not list positions.

- ``v005_prefix_compatible``: the causal projection of the SAME 11
  formulas onto any event prefix.  **This is NOT the historical v005
  model; the prediction point and therefore some semantics differ**:
  - ``payment_predicted_total`` (elapsed_steps) for a prefix =
    ``ctx_through_cut + k``, where ``ctx_through_cut`` is the cut's last
    event's ``ctx`` value -- the number of context messages whose
    raw-sequence index is strictly below that event's turn index,
    recorded per event by the corpus builder from the adapter's
    ``context_positions(raw)``.  v007 CORRECTION (critique MAJOR-1):
    v006 estimated elapsed as ``n_context_events + k`` under the
    documented assumption that context messages precede the
    action/observation stream, but live swegym_openhands and swe_smith
    rows interleave context messages mid-trajectory (measured: up to 98
    future messages on swe_smith, 20 on swegym; nebius clean), so the
    full-trajectory context count leaked FUTURE context into the five
    elapsed-derived prefix features (payment_predicted_total,
    payment_error, horizon_delta, risk_estimate, avg_actions_per_step).
    The ctx-scoped rule counts only context absorbed at or before the
    cut.  Parents built without context positions
    (``context_scoped=false``) carry ``ctx`` 0, so elapsed = k; that
    fallback is valid only for sources with genuinely no scoped context.
    The prefix length ``k`` is the operating contract of the corpus cut
    planner (1 <= k <= n_events); ``k = 0`` yields ``elapsed_raw = 0``
    under the ctx rule (previously ``n_context_events``).
  - Prefix payment counters are derived from prefix events:
    ``turns`` = prefix actions, ``tool_calls`` = prefix observations,
    ``commands`` = prefix ``mentions_bash`` actions, ``errors`` = prefix
    ``is_error`` observations.  For swegym_openhands these are exact
    adapter replicas.  For nebius the adapter's ``commands`` counter
    (all ai/assistant turns) and ``error_count`` (keyword count over
    terminal ``eval_logs``) are NOT derivable from hashed events and are
    NOT causally available mid-trajectory, so the prefix family uses the
    observable causal estimates above; full-trajectory features are
    unaffected (they use the verbatim ``counts`` block).
  - ``tool_diversity_count`` keeps the parent-level
    ``tool_names_manifest``: the manifest is the pre-trajectory harness
    tool configuration, hence causal at every prefix (dataset-skewed
    exactly as in v005 -- only swegym populates it).
  - Prefix-feature omission check: T00 (``.agents/reports/
    v006-v005-reconstruction.md`` section 7.2) found ALL 11 features
    prefix-recomputable.  All 11 are implemented below; NONE is omitted.

- ``v006``: deterministic trajectory-state features over the prefix
  event list, following the T01 derivability table
  (``.agents/reports/v006-data-and-features.md`` section 2).  Adaptations
  vs T01, forced by the corpus schema (no raw text is stored; events
  carry ``cmd_family``/``hash``/markers only):
  - T01 says "tool" (tool name or command head); the corpus exposes the
    observable action identity ``cmd_family`` (+ ``mentions_bash`` +
    ``has_terminal_output`` modality).  Family features use
    ``family_value = cmd_family or "none"`` (empty-content actions form
    the pseudo-family ``none``).
  - T01 #12 verification regexes (lint/diff/build-verify...) are NOT
    computable from hashed content.  Exact rule shipped: a verification
    action is an action with ``cmd_family == "test"`` (pytest/unittest/
    tox/nosetests/npm test/make test/cargo test).  ``check``/``diff``
    forms land in the ``inspect``/``git`` families in the corpus
    taxonomy and are therefore not counted; flagged as the closest
    faithful variant.
  - T01 #2/#3 pairing used tool_call ids or alternation slots; the
    corpus has no ids, so an action is resolved iff any observation of
    any kind occurs later in the prefix.
  - T01 #15 evidence novelty is the lexical observation-hash novelty
    proxy (the semantic sense is NOT-DERIVABLE per T01).
  - T01 #17 "actions without new observations" is adapted to: an action
    is observation-less iff it has no later observation, or its next
    observation duplicates the hash of the observation immediately
    before it (empty-payload duplication is invisible without text;
    hash equality is the corpus proxy).
  - Recovery latency (#11) is measured as event-position gaps between an
    error observation and the next non-error observation, reported as
    mean over errors and first-recovery latency.  Both are RAW counts:
    never normalized by final trajectory length.
  - EXCLUDED as leakage (test-proven absence): any feature computed from
    FINAL trajectory length, e.g. ``prefix_fraction =
    prefix_len/final_len``.  Prefix position is only legal against an
    exogenous budget, which none of the sources records (T01 #19).

All features are finite floats rounded to 4 places (v005 families keep
H's int dtypes for ``tool_diversity_count``/``dataset_id``).  When a
quantity is undefined (e.g. no error yet) the value is 0.0 AND, where
disambiguation matters, a separate ``has_*`` indicator carries the
condition -- semantics are never smuggled into the value.

Schema version tags (normative): ``v005_full_semantics@1``,
``v005_prefix_compatible@2`` (bumped from @1 by the v007 ctx-scoped
elapsed correction, MAJOR-1: semantics changed, names/count unchanged),
``v006@1`` (``SCHEMA_VERSIONS``).

Determinism: no randomness, no clocks; every function is a pure
function of its inputs.
"""

from __future__ import annotations

import math
from typing import Any, Callable, Hashable, Iterable, Sequence

import pandas as pd

FEATURE_FAMILIES: tuple[str, ...] = (
    "v005_full_semantics",
    "v005_prefix_compatible",
    "v006",
)

SCHEMA_VERSIONS: dict[str, str] = {
    "v005_full_semantics": "v005_full_semantics@1",
    "v005_prefix_compatible": "v005_prefix_compatible@2",
    "v006": "v006@1",
}

# H mapping (run_calibration_pipeline.py:204-209).
DATASET_ID_MAP: dict[str, int] = {
    "swegym_openhands": 0,
    "agenttrove": 1,
    "nebius_swe_agent": 2,
}

# Substrings that would mark a feature as computed from FINAL trajectory
# length.  Their presence in any shipped schema is leakage (T01 #19).
LEAKY_FEATURE_PATTERNS: tuple[str, ...] = (
    "fraction_of_final",
    "prefix_fraction",
    "pct_of_total_length",
)

V005_FEATURES: tuple[str, ...] = (
    "payment_predicted_total",
    "payment_actual_total",
    "payment_error",
    "horizon_delta",
    "risk_estimate",
    "debt_estimate",
    "tool_diversity_count",
    "error_recovery_ratio",
    "action_observation_ratio",
    "avg_actions_per_step",
    "dataset_id",
)

V006_FEATURES: tuple[str, ...] = (
    # depth
    "n_events",
    "n_actions",
    "n_observations",
    # closure
    "unresolved_action_rate",
    "action_observation_closure_ratio",
    # tool dynamics
    "used_family_diversity",
    "tool_switch_rate",
    "repeated_action_rate",
    "max_repeated_action_run",
    # errors
    "error_count",
    "error_rate",
    "distinct_error_count",
    "repeated_error_rate",
    # recovery
    "recovery_attempt_count",
    "recovery_rate",
    "recovery_latency_mean",
    "first_recovery_latency",
    "strategy_change_after_first_failure",
    # verification
    "verification_action_count",
    "verification_rate",
    "verification_after_edit_count",
    "verification_after_recovery_count",
    # evidence
    "observation_novelty_rate",
    "actions_since_last_observation",
    "actions_without_observation_rate",
    # stuck loop
    "stuck_cycle_max",
    "stuck_loop_indicator",
    # conditioning indicators
    "has_failure",
    "has_recovery",
)

FAMILY_FEATURES: dict[str, tuple[str, ...]] = {
    "v005_full_semantics": V005_FEATURES,
    "v005_prefix_compatible": V005_FEATURES,
    "v006": V006_FEATURES,
}

IDENTITY_COLUMNS: tuple[str, ...] = (
    "group_key",
    "parent_id",
    "dataset",
    "dataset_id",
    "prefix_kind",
    "k",
    "n_events_total",
    "label",
    "weight_base",
)

FULL_PREFIX_KIND = "full"

CANONICAL_CUT_KINDS: tuple[str, ...] = (
    "early",
    "pct25",
    "pct50",
    "after_first_failure",
    "after_first_recovery",
    "pre_terminal",
)


def _r4(value: float) -> float:
    """Round to 4 places, guarding -0.0."""
    out = round(float(value), 4)
    return out + 0.0 if out == 0 else out


def _dataset_id(dataset: str) -> int:
    return DATASET_ID_MAP.get(dataset, -1)


def _family_value(event: dict[str, Any]) -> str:
    """Observable tool identity of an action event (T01 adaptation)."""
    return event["cmd_family"] or "none"


def _check_families(families: Iterable[str]) -> tuple[str, ...]:
    requested = tuple(families)
    if not requested:
        raise ValueError("families must be a non-empty collection")
    unknown = [f for f in requested if f not in FEATURE_FAMILIES]
    if unknown:
        raise ValueError(
            f"Unknown feature families: {unknown}. Available: {list(FEATURE_FAMILIES)}"
        )
    # Deterministic canonical order regardless of caller order.
    return tuple(f for f in FEATURE_FAMILIES if f in requested)


# ---------------------------------------------------------------------------
# Family 1: v005_full_semantics (exact H replication over a full parent)
# ---------------------------------------------------------------------------


def v005_full_semantics_features(parent: dict[str, Any]) -> dict[str, Any]:
    """Exact v005 feature replication from a complete parent record.

    Equivalent by construction to
    ``external_record_to_model_calibration(record)`` flattened through
    ``build_calibration_frame`` for every parent that
    ``build_trajectory_corpus.build_parent`` accepted.
    """
    counts = parent["counts"]
    elapsed_raw = counts["elapsed_steps"]
    # H clamps the rate/efficiency denominator: max(payment.get(..., 1), 1).
    elapsed = max(elapsed_raw, 1)
    error_count = counts["error_count"]
    turns = counts["turns"]
    tool_calls = counts["tool_calls"]
    commands = counts["commands"]

    error_rate = error_count / elapsed
    payment_efficiency = (turns + tool_calls + commands) / max(elapsed, 1)
    inverse_risk = 1.0 - min(error_rate, 1.0)
    raw_delta = (inverse_risk * 0.6) + (min(payment_efficiency, 1.0) * 0.4)
    horizon_delta = round(min(max(raw_delta, 0.0), 1.0), 4)

    risk_estimate = min(1.0, error_rate)

    debt_estimate = 0.0
    if turns > 0 and tool_calls == 0:
        debt_estimate = min(turns / 20.0, 1.0)

    tool_diversity_count = len(set(parent["tool_names_manifest"]))

    # H compares turn_index values (event ``i``), not list positions.
    error_obs_i = [
        ev["i"] for ev in parent["events"]
        if ev["kind"] == "observation" and ev["is_error"]
    ]
    non_error_obs_i = [
        ev["i"] for ev in parent["events"]
        if ev["kind"] == "observation" and not ev["is_error"]
    ]
    if error_obs_i:
        recoveries = sum(
            1 for eidx in error_obs_i if any(nidx > eidx for nidx in non_error_obs_i)
        )
        error_recovery_ratio = round(recoveries / len(error_obs_i), 4)
    else:
        error_recovery_ratio = 0.0

    n_actions = sum(1 for ev in parent["events"] if ev["kind"] == "action")
    n_observations = sum(1 for ev in parent["events"] if ev["kind"] == "observation")
    action_observation_ratio = (
        round(n_actions / n_observations, 4) if n_observations > 0 else 0.0
    )
    avg_actions_per_step = round(n_actions / max(elapsed, 1), 4)

    predicted_total = float(elapsed_raw)
    actual_total = float(turns + tool_calls + commands + error_count)
    return {
        "payment_predicted_total": predicted_total,
        "payment_actual_total": actual_total,
        "payment_error": abs(actual_total - predicted_total),
        "horizon_delta": float(horizon_delta),
        "risk_estimate": float(risk_estimate),
        "debt_estimate": round(float(debt_estimate), 4),
        "tool_diversity_count": int(tool_diversity_count),
        "error_recovery_ratio": float(error_recovery_ratio),
        "action_observation_ratio": float(action_observation_ratio),
        "avg_actions_per_step": float(avg_actions_per_step),
        "dataset_id": int(_dataset_id(parent["dataset"])),
    }


# ---------------------------------------------------------------------------
# Family 2: v005_prefix_compatible (causal projection of the same formulas)
# ---------------------------------------------------------------------------


def v005_prefix_compatible_features(parent: dict[str, Any], k: int) -> dict[str, Any]:
    """The 11 H formulas recomputed causally on the first ``k`` events.

    Elapsed time through the cut is prefix-scoped (v007 correction
    MAJOR-1): the cut's last event's ``ctx`` count plus ``k`` -- never
    the trajectory-total ``n_context_events``.  See the module docstring
    for the documented semantic deviations (ctx-scoped elapsed estimate;
    event-derived payment counters) and the ``ctx``-0 fallback for
    parents built without context positions.
    """
    events = parent["events"][:k]
    n_actions = sum(1 for ev in events if ev["kind"] == "action")
    n_observations = sum(1 for ev in events if ev["kind"] == "observation")
    n_bash_actions = sum(
        1 for ev in events if ev["kind"] == "action" and ev["mentions_bash"]
    )
    error_count = sum(
        1 for ev in events if ev["kind"] == "observation" and ev["is_error"]
    )

    turns = n_actions
    tool_calls = n_observations
    commands = n_bash_actions

    # Context messages absorbed at or before the cut (v007 correction
    # MAJOR-1): recorded per event by the corpus builder from the
    # adapter's context_positions; parents without the annotation
    # (context_scoped=false) default to 0, so elapsed = k.
    ctx_through_cut = events[-1].get("ctx", 0) if events else 0
    elapsed_raw = ctx_through_cut + k
    elapsed = max(elapsed_raw, 1)

    error_rate = error_count / elapsed
    payment_efficiency = (turns + tool_calls + commands) / max(elapsed, 1)
    inverse_risk = 1.0 - min(error_rate, 1.0)
    raw_delta = (inverse_risk * 0.6) + (min(payment_efficiency, 1.0) * 0.4)
    horizon_delta = round(min(max(raw_delta, 0.0), 1.0), 4)

    risk_estimate = min(1.0, error_rate)

    debt_estimate = 0.0
    if turns > 0 and tool_calls == 0:
        debt_estimate = min(turns / 20.0, 1.0)

    # Pre-trajectory harness tool configuration: causal at any prefix.
    tool_diversity_count = len(set(parent["tool_names_manifest"]))

    error_obs_i = [
        ev["i"] for ev in events
        if ev["kind"] == "observation" and ev["is_error"]
    ]
    non_error_obs_i = [
        ev["i"] for ev in events
        if ev["kind"] == "observation" and not ev["is_error"]
    ]
    if error_obs_i:
        recoveries = sum(
            1 for eidx in error_obs_i if any(nidx > eidx for nidx in non_error_obs_i)
        )
        error_recovery_ratio = round(recoveries / len(error_obs_i), 4)
    else:
        error_recovery_ratio = 0.0

    action_observation_ratio = (
        round(n_actions / n_observations, 4) if n_observations > 0 else 0.0
    )
    avg_actions_per_step = round(n_actions / max(elapsed, 1), 4)

    predicted_total = float(elapsed_raw)
    actual_total = float(turns + tool_calls + commands + error_count)
    return {
        "payment_predicted_total": predicted_total,
        "payment_actual_total": actual_total,
        "payment_error": abs(actual_total - predicted_total),
        "horizon_delta": float(horizon_delta),
        "risk_estimate": float(risk_estimate),
        "debt_estimate": round(float(debt_estimate), 4),
        "tool_diversity_count": int(tool_diversity_count),
        "error_recovery_ratio": float(error_recovery_ratio),
        "action_observation_ratio": float(action_observation_ratio),
        "avg_actions_per_step": float(avg_actions_per_step),
        "dataset_id": int(_dataset_id(parent["dataset"])),
    }


# ---------------------------------------------------------------------------
# Family 3: v006 trajectory-state features over a prefix
# ---------------------------------------------------------------------------


def v006_prefix_features(parent: dict[str, Any], k: int) -> dict[str, Any]:
    """Deterministic trajectory-state features over ``events[:k]``."""
    events = parent["events"][:k]
    n = len(events)

    action_pos = [p for p, ev in enumerate(events) if ev["kind"] == "action"]
    obs_pos = [p for p, ev in enumerate(events) if ev["kind"] == "observation"]
    n_actions = len(action_pos)
    n_obs = len(obs_pos)

    last_obs_pos = obs_pos[-1] if obs_pos else -1

    # --- closure ---
    # Corpus has no tool_call ids: an action is resolved iff any
    # observation of any kind occurs later in the prefix.
    unresolved = sum(1 for p in action_pos if p > last_obs_pos)
    if n_actions > 0:
        unresolved_action_rate = _r4(unresolved / n_actions)
        closure_ratio = _r4((n_actions - unresolved) / n_actions)
    else:
        unresolved_action_rate = 0.0
        closure_ratio = 0.0

    # --- tool dynamics ---
    families_in_order = [_family_value(events[p]) for p in action_pos]
    used_family_diversity = len(set(families_in_order))
    if n_actions >= 2:
        switches = sum(
            1
            for a, b in zip(families_in_order, families_in_order[1:])
            if a != b
        )
        tool_switch_rate = _r4(switches / (n_actions - 1))
    else:
        tool_switch_rate = 0.0
    hashes_in_order = [events[p]["hash"] for p in action_pos]
    repeats = sum(
        1 for a, b in zip(hashes_in_order, hashes_in_order[1:]) if a == b
    )
    repeated_action_rate = _r4(repeats / n_actions) if n_actions > 0 else 0.0
    max_run = 0
    run = 0
    prev: str | None = None
    for h in hashes_in_order:
        run = run + 1 if h == prev else 1
        max_run = max(max_run, run)
        prev = h
    max_repeated_action_run = float(max_run)  # 0.0 when no actions

    # --- errors ---
    error_pos = [
        p for p in obs_pos if events[p]["is_error"]
    ]
    error_count = len(error_pos)
    error_rate = _r4(error_count / n) if n > 0 else 0.0
    error_hashes = [events[p]["hash"] for p in error_pos]
    distinct_error_count = len(set(error_hashes))
    seen: set[str] = set()
    repeated_errors = 0
    for h in error_hashes:
        if h in seen:
            repeated_errors += 1
        seen.add(h)
    repeated_error_rate = (
        _r4(repeated_errors / error_count) if error_count > 0 else 0.0
    )

    # --- recovery ---
    error_pos_set = set(error_pos)
    recovery_attempt_count = sum(
        1 for p in action_pos if (p - 1) in error_pos_set
    )
    recovery_rate = (
        _r4(recovery_attempt_count / error_count) if error_count > 0 else 0.0
    )

    # Latency = event-position gap from an error observation to the next
    # non-error observation.  Raw counts; never normalized by final length.
    non_error_obs_pos = [p for p in obs_pos if not events[p]["is_error"]]
    first_recovery_latency = 0.0
    latencies: list[int] = []
    for idx, epos in enumerate(error_pos):
        later = [q for q in non_error_obs_pos if q > epos]
        if not later:
            continue
        latency = later[0] - epos
        latencies.append(latency)
        if idx == 0:
            first_recovery_latency = float(latency)
    # has_recovery: at least one error observation is followed by a
    # non-error observation within the prefix.
    has_recovery = 1.0 if latencies else 0.0
    recovery_latency_mean = (
        _r4(sum(latencies) / len(latencies)) if latencies else 0.0
    )

    # Strategy change after the first failure: family of the first
    # post-failure action vs the family of the action immediately before
    # the failure.  Undefined -> 0.0; has_failure disambiguates.
    strategy_change = 0.0
    if error_pos:
        first_error = error_pos[0]
        pre_actions = [p for p in action_pos if p < first_error]
        post_actions = [p for p in action_pos if p > first_error]
        if pre_actions and post_actions:
            pre_family = _family_value(events[pre_actions[-1]])
            post_family = _family_value(events[post_actions[0]])
            strategy_change = 1.0 if post_family != pre_family else 0.0

    # --- verification (exact rule: cmd_family == "test") ---
    verify_pos = [p for p in action_pos if events[p]["cmd_family"] == "test"]
    verification_action_count = float(len(verify_pos))
    verification_rate = (
        _r4(len(verify_pos) / n_actions) if n_actions > 0 else 0.0
    )
    edit_pos_set = {
        p for p in action_pos if events[p]["cmd_family"] == "edit"
    }
    verification_after_edit_count = float(
        sum(1 for p in verify_pos if any(e < p for e in edit_pos_set))
    )
    # After an error observation AND a recovery action preceding the
    # verification action.
    verification_after_recovery_count = float(
        sum(
            1
            for p in verify_pos
            if any(
                epos < p and any(epos < apos < p for apos in action_pos)
                for epos in error_pos
            )
        )
    )

    # --- evidence ---
    seen_obs: set[str] = set()
    novel = 0
    for p in obs_pos:
        h = events[p]["hash"]
        if h not in seen_obs:
            novel += 1
            seen_obs.add(h)
    observation_novelty_rate = _r4(novel / n_obs) if n_obs > 0 else 0.0
    actions_since_last_observation = float(
        sum(1 for p in action_pos if p > last_obs_pos)
    )

    # T01 #17 adaptation: an action is observation-less when it has no
    # later observation, or its next observation duplicates the payload
    # (hash) of the observation immediately preceding the action.
    without_new = 0
    for p in action_pos:
        prev_obs = [q for q in obs_pos if q < p]
        next_obs = [q for q in obs_pos if q > p]
        if not next_obs:
            without_new += 1
        elif prev_obs and events[next_obs[0]]["hash"] == events[prev_obs[-1]]["hash"]:
            without_new += 1
    actions_without_observation_rate = (
        _r4(without_new / n_actions) if n_actions > 0 else 0.0
    )

    # --- stuck loop: consecutive (action hash A -> error observation)
    # pairs with identical A and identical error hash ---
    stuck_cycle_max = 0
    chain = 0
    prev_sig: tuple[str, str] | None = None
    prev_end = -2
    for p in range(n - 1):
        if (
            events[p]["kind"] == "action"
            and events[p + 1]["kind"] == "observation"
            and events[p + 1]["is_error"]
        ):
            sig = (events[p]["hash"], events[p + 1]["hash"])
            if prev_sig == sig and p == prev_end + 2:
                chain += 1
            else:
                chain = 1
            stuck_cycle_max = max(stuck_cycle_max, chain)
            prev_sig = sig
            prev_end = p
        # Non-matching positions break adjacency via prev_end.
    stuck_loop_indicator = 1.0 if stuck_cycle_max >= 2 else 0.0

    has_failure = 1.0 if error_count > 0 else 0.0

    return {
        "n_events": float(n),
        "n_actions": float(n_actions),
        "n_observations": float(n_obs),
        "unresolved_action_rate": unresolved_action_rate,
        "action_observation_closure_ratio": closure_ratio,
        "used_family_diversity": float(used_family_diversity),
        "tool_switch_rate": tool_switch_rate,
        "repeated_action_rate": repeated_action_rate,
        "max_repeated_action_run": max_repeated_action_run,
        "error_count": float(error_count),
        "error_rate": error_rate,
        "distinct_error_count": float(distinct_error_count),
        "repeated_error_rate": repeated_error_rate,
        "recovery_attempt_count": float(recovery_attempt_count),
        "recovery_rate": recovery_rate,
        "recovery_latency_mean": recovery_latency_mean,
        "first_recovery_latency": first_recovery_latency,
        "strategy_change_after_first_failure": strategy_change,
        "verification_action_count": verification_action_count,
        "verification_rate": verification_rate,
        "verification_after_edit_count": verification_after_edit_count,
        "verification_after_recovery_count": verification_after_recovery_count,
        "observation_novelty_rate": observation_novelty_rate,
        "actions_since_last_observation": actions_since_last_observation,
        "actions_without_observation_rate": actions_without_observation_rate,
        "stuck_cycle_max": float(stuck_cycle_max),
        "stuck_loop_indicator": stuck_loop_indicator,
        "has_failure": has_failure,
        "has_recovery": has_recovery,
    }


_FAMILY_EXTRACTORS = {
    "v005_full_semantics": lambda parent, k: v005_full_semantics_features(parent),
    "v005_prefix_compatible": v005_prefix_compatible_features,
    "v006": v006_prefix_features,
}


def extract_family_features(
    family: str, parent: dict[str, Any], k: int | None = None
) -> dict[str, Any]:
    """Dispatch one family's extractor.

    ``v005_full_semantics`` is trajectory-global by design and ignores
    ``k``; the prefix families require ``k`` (the full-trajectory causal
    projection uses ``k == len(events)``).
    """
    if family not in _FAMILY_EXTRACTORS:
        raise ValueError(f"Unknown feature family: {family}")
    if family == "v005_full_semantics":
        return _FAMILY_EXTRACTORS[family](parent, 0)
    if k is None:
        raise ValueError(f"family {family!r} requires a prefix length k")
    return _FAMILY_EXTRACTORS[family](parent, k)


# ---------------------------------------------------------------------------
# Prefix cut planning
# ---------------------------------------------------------------------------


def _first_error_position(events: Sequence[dict[str, Any]]) -> int | None:
    for p, ev in enumerate(events):
        if ev["kind"] == "observation" and ev["is_error"]:
            return p
    return None


def _cut_k(kind: str, events: Sequence[dict[str, Any]]) -> int | None:
    """Raw cut position for one canonical kind; ``None`` when undefined."""
    n = len(events)
    if kind == "early":
        return min(8, max(2, math.floor(0.10 * n)))
    if kind == "pct25":
        return math.ceil(0.25 * n)
    if kind == "pct50":
        return math.ceil(0.50 * n)
    first_error = _first_error_position(events)
    if kind == "after_first_failure":
        return None if first_error is None else first_error + 1
    if kind == "after_first_recovery":
        if first_error is None:
            return None
        post = [p for p, ev in enumerate(events) if ev["kind"] == "action" and p > first_error]
        return None if not post else post[0] + 1
    if kind == "pre_terminal":
        return None if n < 2 else n - 1
    raise ValueError(
        f"Unknown cut kind: {kind}. Available: {list(CANONICAL_CUT_KINDS)}"
    )


def plan_prefix_cuts(
    parent: dict[str, Any], cuts: Iterable[str] = CANONICAL_CUT_KINDS
) -> dict[str, Any]:
    """Plan prefix cuts for one parent.

    Returns ``{"prefixes": [(prefix_kind, k)], "yields": {kind: k or
    None}, "dropped_aliases": {kind: kept_kind}}``:

    - ``prefixes``: deduplicated ``(prefix_kind, k)`` pairs with
      ``1 <= k <= n_events``.  Identical ``k`` values across kinds keep
      the earliest kind in canonical order (``early, pct25, pct50,
      after_first_failure, after_first_recovery, pre_terminal``); later
      kinds are recorded in ``dropped_aliases``.
    - ``yields``: per requested kind, the enforced ``k`` (``None`` when
      the cut is undefined for this parent, e.g. no error observation
      yet, or ``n < 2`` for ``pre_terminal``).
    """
    requested = list(cuts)
    unknown = [c for c in requested if c not in CANONICAL_CUT_KINDS]
    if unknown:
        raise ValueError(
            f"Unknown cut kinds: {unknown}. Available: {list(CANONICAL_CUT_KINDS)}"
        )
    events = parent["events"]
    n = len(events)

    prefixes: list[tuple[str, int]] = []
    yields: dict[str, int | None] = {}
    dropped_aliases: dict[str, str] = {}
    claimed: dict[int, str] = {}
    for kind in CANONICAL_CUT_KINDS:
        if kind not in requested:
            continue
        raw_k = _cut_k(kind, events)
        if raw_k is None:
            yields[kind] = None
            continue
        k = min(max(raw_k, 1), n) if n > 0 else None
        if k is None or k < 1 or k > n:
            # Empty event stream: no legal prefix exists.
            yields[kind] = None
            continue
        yields[kind] = k
        kept = claimed.get(k)
        if kept is not None:
            dropped_aliases[kind] = kept
            continue
        claimed[k] = kind
        prefixes.append((kind, k))
    return {
        "prefixes": prefixes,
        "yields": yields,
        "dropped_aliases": dropped_aliases,
    }


def generate_prefixes(
    parent: dict[str, Any], cuts: Iterable[str] = CANONICAL_CUT_KINDS
) -> list[tuple[str, int]]:
    """Deduplicated ``(prefix_kind, k)`` cut list for one parent.

    Use :func:`plan_prefix_cuts` for the per-cut yields and dropped
    alias bookkeeping behind this list.
    """
    return plan_prefix_cuts(parent, cuts)["prefixes"]


# ---------------------------------------------------------------------------
# Frame builders
# ---------------------------------------------------------------------------


def _base_row(parent: dict[str, Any], prefix_kind: str, k: int, weight_base: float) -> dict[str, Any]:
    return {
        "group_key": parent["group_key"],
        "parent_id": parent["parent_id"],
        "dataset": parent["dataset"],
        "dataset_id": _dataset_id(parent["dataset"]),
        "prefix_kind": prefix_kind,
        "k": k,
        "n_events_total": len(parent["events"]),
        "label": parent["label"],
        "weight_base": weight_base,
    }


def _feature_columns(families: Sequence[str]) -> list[str]:
    cols: list[str] = []
    for family in families:
        for name in FAMILY_FEATURES[family]:
            if name != "dataset_id" and name not in cols:
                cols.append(name)
    return cols


def _finish_frame(rows: list[dict[str, Any]], families: Sequence[str]) -> pd.DataFrame:
    columns = list(IDENTITY_COLUMNS) + _feature_columns(families)
    return pd.DataFrame(rows, columns=columns)


def build_prefix_frame(
    parents: Iterable[dict[str, Any]],
    families: Iterable[str],
    cuts: Iterable[str] = CANONICAL_CUT_KINDS,
) -> pd.DataFrame:
    """One row per (parent, generated prefix cut) with family features.

    ``weight_base = 1 / (number of prefix rows generated for that parent
    across the requested cuts)`` is the parent-balancing base
    (amendment 3); downstream training multiplies by any preregistered
    source weight and applies weights only within the training
    partition.  All prefix rows of one parent share its ``group_key``;
    partition splits MUST be grouped by ``group_key`` (enforce with
    :func:`assert_grouped`).
    """
    families_order = _check_families(families)
    rows: list[dict[str, Any]] = []
    for parent in parents:
        plan = plan_prefix_cuts(parent, cuts)
        prefixes = plan["prefixes"]
        if not prefixes:
            continue
        weight_base = 1.0 / len(prefixes)
        for prefix_kind, k in prefixes:
            row = _base_row(parent, prefix_kind, k, weight_base)
            for family in families_order:
                features = extract_family_features(family, parent, k)
                # dataset_id is carried by the identity column.
                features.pop("dataset_id", None)
                row.update(features)
            rows.append(row)
    return _finish_frame(rows, families_order)


def build_full_frame(
    parents: Iterable[dict[str, Any]],
    families: Iterable[str],
) -> pd.DataFrame:
    """One row per parent for full-trajectory arms (weight 1.0).

    ``prefix_kind`` is ``"full"`` and ``k = n_events_total``.  The
    ``v005_full_semantics`` family uses the verbatim ``counts`` block;
    prefix families evaluated here are the causal projection at the end
    of the stream (documented deviations apply).
    """
    families_order = _check_families(families)
    rows: list[dict[str, Any]] = []
    for parent in parents:
        n = len(parent["events"])
        row = _base_row(parent, FULL_PREFIX_KIND, n, 1.0)
        for family in families_order:
            features = extract_family_features(family, parent, n)
            features.pop("dataset_id", None)
            row.update(features)
        rows.append(row)
    return _finish_frame(rows, families_order)


# ---------------------------------------------------------------------------
# Leakage and grouping guards
# ---------------------------------------------------------------------------


def assert_no_leaky_features(feature_names: Iterable[str]) -> None:
    """Reject any feature name computed from FINAL trajectory length.

    Prefix position is only legal against an exogenous interaction
    budget; fractions of final length leak the label-bearing horizon
    into prefix rows (T01 #19).
    """
    leaked = [
        name
        for name in feature_names
        if any(pattern in name for pattern in LEAKY_FEATURE_PATTERNS)
    ]
    if leaked:
        raise ValueError(
            f"Leaky features (computed from final trajectory length): {leaked}"
        )


def assert_grouped(
    rows: Iterable[dict[str, Any]],
    split_fn: Callable[[dict[str, Any]], Hashable],
) -> int:
    """Guard: all rows of one ``group_key`` land in a single partition.

    ``split_fn`` maps a row to its partition id.  Raises ``ValueError``
    when any ``group_key`` straddles partitions (same-instance
    trajectories must never leak across the train/eval boundary).
    Returns the number of distinct group keys checked.
    """
    seen: dict[str, Hashable] = {}
    for row in rows:
        group_key = row["group_key"]
        partition = split_fn(row)
        if group_key in seen and seen[group_key] != partition:
            raise ValueError(
                f"group_key {group_key!r} straddles partitions: "
                f"{seen[group_key]!r} and {partition!r}"
            )
        seen[group_key] = partition
    return len(seen)
