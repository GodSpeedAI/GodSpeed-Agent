"""v007 failure-episode construction and recovery-prediction features.

Builds the failure-episode training unit for the v007 conditional
recovery predictor over the admitted v006 parent-trajectory corpus,
exactly per the FROZEN coordinator decisions in
``.agents/plans/godspeed-agent-v007-recovery-prediction.yaml`` (section
``coordinator_decisions``).  v006 modules are IMPORTED, never forked:
every shared formula (prefix families, rounding, guards, identity map)
comes from ``scripts/settlement_datasets/v006_features.py``.

Frozen definitions implemented here
-----------------------------------

FAILURE EPISODE.  Opens at the first error observation of a MAXIMAL RUN
of error observations, where intervening ACTIONS are allowed (they
belong to the failed state) and the run is PRECEDED by >= 1 non-error
observation (leading context errors never open episodes and are not
counted as exclusions; the manifest records them informationally as
``leading_error_runs``).  The opening error observation index is ``e``
(a list position in ``parent['events']`` -- the same position space the
v006 prefix extractors cut on).  Later error observations of the same
run are part of the same failed state, not new episodes.

ELIGIBILITY.  ``e`` must not be the trajectory's final event
(``e != n_events - 1``); otherwise the candidate is excluded and
counted under ``failure_is_final_event``.

EPISODE RECORD.  ``{episode_id, episode_index, parent_id, group_key,
split_group, dataset, parent_label, e, r0_k, r1_k, recovery_success,
audit_bucket, n_events_total}`` with ``episode_id = parent_id + ':ep' +
<running 0-based index>`` (only eligible episodes consume an index),
``r0_k = e + 1`` (window closes at the failure event, inclusive), and
``r1_k`` per the R1 rule below.  ``split_group = '<dataset>:<repository>'``
parses the repository from the instance_id by stripping a trailing
``-<version>`` tag (SWE-bench id convention); it is the v007 PARTITION
key.  The corpus ``group_key`` (``<dataset>:<instance>``) is kept as
inherited identity.  All episodes of one ``split_group`` MUST land in
one partition (enforced with :func:`assert_grouped_by_split_group`,
which delegates to the v006 :func:`assert_grouped` guard).

R1 WINDOW.  ``k1`` closes at the first ACTION event with index > e (the
recovery attempt, inclusive) PLUS any CONSECUTIVE observation events
that directly follow that action before the next action event (the
attempt's immediate result -- typically one tool output; including it
makes "same failure immediately repeated" an in-window feature).  If no
post-failure action exists, ``r1_k is None`` (R0-only episode; counted).
If the attempt action is the final event, R1 closes at the action
(``r1_k = n_events``).

ESCAPE (LABEL-SIDE ONLY, never a feature).  The first observation event
with index > e and ``is_error=False``.  Note the escape may fall INSIDE
the R1 window (e.g. the attempt's result is a non-error observation);
it still only ever feeds labels.

TARGET.  ``recovery_success = 1 iff (parent_label == 1) AND (an escape
exists after e)``; otherwise 0.  Audit buckets partition all episodes:
``escape_with_settlement`` (the completing positive cell),
``escape_no_settlement``, ``no_escape_with_settlement`` (trailing-error
edge: terminal success with no observable escape -- labeled 0),
``no_escape_no_settlement``.  All episodes are labeled by the one rule;
buckets only count them.

Definitional subtleties (all resolved by the frozen decisions)
--------------------------------------------------------------

- ``fail_event_index`` is the RAW opening index ``e`` -- an absolute
  count, legal at R0; it is NOT a fraction of the final length (the
  v006 leak patterns never apply; ``assert_no_leaky_features`` runs
  over every shipped schema).
- ``prior_episode_count`` = episodes opened before this one (equals the
  episode's running 0-based index).
- ``prior_escape_count`` = prior episodes of the same parent whose
  escape observation index is < e.  By the maximality argument every
  prior episode's escape is < e (a later episode's opening run is
  separated from an earlier episode's run by a non-error observation,
  which is that earlier episode's escape), and an episode with NO
  escape is necessarily the parent's last.  Hence
  ``prior_escape_count == prior_episode_count`` holds by construction;
  both features are kept because the frozen schema names both, and the
  equality is a scan invariant the tests pin.
- ``errors_opening_run_available_at_r0 = 1`` constant.  The frozen
  decision resolves the earlier ambiguous "consecutive_pre_fail_errors"
  wording explicitly: the size of THIS episode's error run is partially
  future at R0 (later errors of the run are after e); at R0 exactly one
  fact is available -- the run opened at e -- so the feature is the
  constant 1.0.
- ``current_streak_prior_nonerror`` = number of consecutive non-error
  observations immediately preceding e, counted over the observation
  subsequence (actions are transparent -- consistent with the episode
  "run" semantics in which intervening actions belong to the failed
  state).  The streak is broken by the first earlier error observation.
  Every valid episode has streak >= 1 (its run is preceded by a
  non-error observation).
- ``attempt_repeats_prior_action`` compares the attempt hash with the
  hash of the immediately preceding ACTION event (last action with
  index < a, where a is the attempt position).  Because the attempt is
  the FIRST action after e, that action is necessarily the last action
  before e -- so ``has_prior_action`` and ``has_pre_failure_action``
  always coincide; both indicators are kept because the frozen schema
  names both.  Undefined (no prior action) -> 0.0 + indicators 0.0.
- ``attempt_family_change`` compares the attempt's cmd_family with the
  last pre-failure action's cmd_family using the v006
  ``_family_value`` convention (``cmd_family or "none"``), so
  empty-content actions form the pseudo-family ``none`` exactly as in
  the v006 ``strategy_change_after_first_failure`` formula.
- ``obs_between_failure_and_attempt`` counts observation events with
  index strictly between e and the attempt position a.
- ``new_obs_between_failure_and_attempt`` counts hash-novel observations
  after e and before/at k1 (positions e < q < k1), where novelty uses
  the v006 first-occurrence-in-the-prefix convention: walking the
  prefix ``events[:k1]`` in order, an observation is novel iff its hash
  was not seen at an earlier observation.
- ``attempt_result_is_error`` / ``attempt_result_same_hash_as_failure``
  read the attempt's immediate result observation (first observation
  directly after the attempt action).  It is INSIDE the R1 window by
  construction, hence causal at R1; the frozen decisions explicitly
  admit it.  Undefined (no result observation) -> 0.0 +
  ``has_attempt_result`` 0.0.
- R0 rows carry the R1-addition columns as 0.0 with ``has_*``
  indicators 0.0 (v006 convention: undefined quantities are 0.0 and,
  where disambiguation matters, a separate indicator carries the
  condition).  ``recovery_attempt_present`` is 1.0 on every R1 row by
  construction.
- The frame carries ONE additional causal column beyond the frozen R0/R1
  schemas: ``consecutive_error_observations`` (length of the
  immediately-preceding error-observation run ending at the row's cut,
  actions transparent), which serves the preregistered representation
  ablation.  It is NOT part of ``R0_FEATURES`` or ``R1_ADDITIONS``.
- REPRESENTATION ABLATION ``v005_minimal_recovery@1`` (7 features):
  ``error_count_so_far`` is pulled from the v006 family's
  ``error_count`` at the same cut (name aliased, formula never forked);
  ``repeated_error_rate`` / ``error_rate`` from the v006 family;
  ``action_observation_ratio`` / ``tool_diversity_count`` /
  ``dataset_id`` from the v005-prefix family (H's int dtypes kept for
  the latter two); ``consecutive_error_observations`` computed here.
  :func:`select_ablation_features` materializes the named schema from a
  frame.
- WEIGHTS.  Build-time ``weight_base = 1/(all episodes of the parent)``
  is a provenance base only.  The FROZEN training weight --
  ``1/(number of TRAINING episodes of that parent)`` -- is
  partition-dependent and is computed by
  :func:`parent_balanced_training_weights` on the single-point training
  frame (R0 and R1 are never pooled, so episodes are counted per
  point).  Counting keys ``episode_id`` (nunique), never rows: an
  episode with both points contributes two rows but one episode.
- LABEL HYGIENE.  ``assert_no_leaky_features`` (v006) runs over every
  shipped schema, and :func:`assert_no_label_features` rejects any
  feature name containing ``escape`` / ``recovery_success`` / ``label``
  / ``settlement`` -- escape and terminal outcome live on the label
  side only.  DOCUMENTED COLLISION RESOLUTION: the frozen R0 feature
  ``prior_escape_count`` necessarily contains the substring ``escape``
  while remaining strictly causal (prior episodes' escapes are all < e,
  see above); it is the single named exception to the substring guard.
  No other escape-derived name is admitted.

Determinism: no randomness, no clocks in the feature path; every
function is a pure function of its inputs.  The CLI manifest carries a
single ``created_at`` provenance timestamp (v006 corpus convention);
the episode table itself is byte-stable across runs.

Schema version tags (normative): ``v007_episodes@1``, ``v007_r0@1``,
``v007_r1@1``, ``v005_minimal_recovery@1`` (``SCHEMA_VERSIONS``).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Hashable, Iterable, Sequence

import pandas as pd
import yaml

from scripts.settlement_datasets.adapter_base import read_records_jsonl
from scripts.settlement_datasets.run_scoped_paths import utc_now_iso
from scripts.settlement_datasets.v006_features import (
    DATASET_ID_MAP,
    FEATURE_FAMILIES,
    V005_FEATURES,
    V006_FEATURES,
    _family_value,
    _r4,
    assert_grouped,
    assert_no_leaky_features,
    extract_family_features,
    v005_prefix_compatible_features,
    v006_prefix_features,
)

# ---------------------------------------------------------------------------
# Schema versions
# ---------------------------------------------------------------------------

EPISODE_SCHEMA_VERSION = "v007_episodes@1"
R0_SCHEMA_VERSION = "v007_r0@1"
R1_SCHEMA_VERSION = "v007_r1@1"
V005_MINIMAL_RECOVERY_SCHEMA_VERSION = "v005_minimal_recovery@1"

SCHEMA_VERSIONS: dict[str, str] = {
    "v007_episodes": EPISODE_SCHEMA_VERSION,
    "v007_r0": R0_SCHEMA_VERSION,
    "v007_r1": R1_SCHEMA_VERSION,
    "v005_minimal_recovery": V005_MINIMAL_RECOVERY_SCHEMA_VERSION,
}

POINT_R0 = "R0"
POINT_R1 = "R1"

# ---------------------------------------------------------------------------
# Audit / exclusion buckets (frozen)
# ---------------------------------------------------------------------------

AUDIT_ESCAPE_WITH_SETTLEMENT = "escape_with_settlement"
AUDIT_ESCAPE_NO_SETTLEMENT = "escape_no_settlement"
AUDIT_NO_ESCAPE_WITH_SETTLEMENT = "no_escape_with_settlement"
AUDIT_NO_ESCAPE_NO_SETTLEMENT = "no_escape_no_settlement"

AUDIT_BUCKETS: tuple[str, ...] = (
    AUDIT_ESCAPE_WITH_SETTLEMENT,
    AUDIT_ESCAPE_NO_SETTLEMENT,
    AUDIT_NO_ESCAPE_WITH_SETTLEMENT,
    AUDIT_NO_ESCAPE_NO_SETTLEMENT,
)

EXCLUSION_FAILURE_IS_FINAL_EVENT = "failure_is_final_event"

EXCLUSION_BUCKETS: tuple[str, ...] = (EXCLUSION_FAILURE_IS_FINAL_EVENT,)

# Label-side names that must never appear as feature names.
FORBIDDEN_LABEL_SUBSTRINGS: tuple[str, ...] = (
    "escape",
    "recovery_success",
    "label",
    "settlement",
)

# The single preregistered exception to the substring guard: the FROZEN
# R0 feature ``prior_escape_count`` counts PRIOR episodes' escapes
# (strictly before e, hence causal); it is not the episode's own escape.
# Its causal purity is pinned by the mutation-invariance tests.  This
# resolves the collision between the frozen R0 schema (which names the
# feature) and the label-hygiene guard; any OTHER escape-derived name is
# still rejected.
CAUSAL_ESCAPE_FEATURE_EXCEPTION = "prior_escape_count"

# ---------------------------------------------------------------------------
# Feature schemas
# ---------------------------------------------------------------------------

# Episode-positional causal additions (part of R0; identical values on
# the episode's R1 row).
R0_EPISODE_FEATURES: tuple[str, ...] = (
    "fail_event_index",
    "prior_episode_count",
    "prior_escape_count",
    "errors_opening_run_available_at_r0",
    "current_streak_prior_nonerror",
)

# v005 prefix family minus dataset_id (carried as an identity column).
_V005_PREFIX_FEATURES: tuple[str, ...] = tuple(
    name for name in V005_FEATURES if name != "dataset_id"
)

# R0 = full v006 family + v005 prefix family + episode-positional
# additions, everything recomputed at k = r0_k = e + 1.
R0_FEATURES: tuple[str, ...] = tuple(V006_FEATURES) + _V005_PREFIX_FEATURES + R0_EPISODE_FEATURES

# R1 additions, on top of R0_FEATURES recomputed at k = r1_k.
R1_ADDITIONS: tuple[str, ...] = (
    "recovery_attempt_present",
    "attempt_repeats_prior_action",
    "has_prior_action",
    "attempt_family_change",
    "has_pre_failure_action",
    "obs_between_failure_and_attempt",
    "new_obs_between_failure_and_attempt",
    "attempt_result_is_error",
    "has_attempt_result",
    "attempt_result_same_hash_as_failure",
)

R1_FEATURES: tuple[str, ...] = R0_FEATURES + R1_ADDITIONS

# Extra causal column carried by the frame for the ablation arm only.
ABLATION_EXTRA_COLUMN = "consecutive_error_observations"

# Preregistered representation-ablation schema (7 features).
V005_MINIMAL_RECOVERY_FEATURES: tuple[str, ...] = (
    "error_count_so_far",
    ABLATION_EXTRA_COLUMN,
    "repeated_error_rate",
    "error_rate",
    "action_observation_ratio",
    "tool_diversity_count",
    "dataset_id",
)

_EPISODE_COLUMNS: tuple[str, ...] = (
    "episode_id",
    "episode_index",
    "parent_id",
    "group_key",
    "split_group",
    "dataset",
    "dataset_id",
    "point",
    "e",
    "r0_k",
    "r1_k",
    "n_events_total",
    "parent_label",
    "recovery_success",
    "audit_bucket",
    "n_parent_episodes",
    "weight_base",
)

FRAME_COLUMNS: tuple[str, ...] = (
    _EPISODE_COLUMNS + R0_FEATURES + R1_ADDITIONS + (ABLATION_EXTRA_COLUMN,)
)


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------


def assert_no_label_features(feature_names: Iterable[str]) -> None:
    """Reject any feature name carrying label-side semantics.

    Escape, terminal settlement, and the target itself are label-side
    quantities (REQ-V007-FEATURES); their names must never appear in a
    feature schema.  The frozen causal ``prior_escape_count`` feature is
    the single documented exception (see
    ``CAUSAL_ESCAPE_FEATURE_EXCEPTION``); every other name containing a
    forbidden substring is rejected.
    """
    leaked = [
        name
        for name in feature_names
        if name != CAUSAL_ESCAPE_FEATURE_EXCEPTION
        and any(pattern in name for pattern in FORBIDDEN_LABEL_SUBSTRINGS)
    ]
    if leaked:
        raise ValueError(
            f"Label-side feature names are forbidden in v007 schemas: {leaked}"
        )


def assert_recovery_schemas_clean() -> None:
    """Run both guards over every shipped v007 feature schema."""
    for names in (
        R0_FEATURES,
        R1_FEATURES,
        V005_MINIMAL_RECOVERY_FEATURES,
    ):
        assert_no_leaky_features(names)
        assert_no_label_features(names)


def assert_grouped_by_split_group(
    rows: Iterable[dict[str, Any]],
    split_fn: Callable[[dict[str, Any]], Hashable],
) -> int:
    """Guard: all episodes of one ``split_group`` land in one partition.

    Delegates to the v006 :func:`assert_grouped` guard with
    ``group_key`` projected onto the coarser v007 ``split_group``
    (``<dataset>:<repository>``), so same-repository episodes never
    straddle partitions.  Returns the number of distinct split groups
    checked.
    """
    projected = [dict(row, group_key=row["split_group"]) for row in rows]
    return assert_grouped(projected, split_fn)


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------

_VERSION_TAG = re.compile(r"-\d[\d.]*$")


def parse_repository(instance_id: str) -> str:
    """Strip a trailing ``-<version>`` tag from a SWE-bench instance id.

    ``django__django-4.2`` -> ``django__django``; ids without a trailing
    version tag are returned unchanged.
    """
    return _VERSION_TAG.sub("", instance_id)


def split_group_for_parent(parent: dict[str, Any]) -> str:
    """v007 partition key ``<dataset>:<repository>`` for one parent."""
    dataset, sep, instance = parent["group_key"].partition(":")
    if not sep:
        return parent["group_key"]
    return f"{dataset}:{parse_repository(instance)}"


# ---------------------------------------------------------------------------
# Episode scan (pure)
# ---------------------------------------------------------------------------


def _r1_cut(events: list[dict[str, Any]], e: int) -> int | None:
    """Frozen R1 cut: first action after e plus its consecutive trailing
    observations; ``None`` when no post-failure action exists."""
    n = len(events)
    a: int | None = None
    for p in range(e + 1, n):
        if events[p]["kind"] == "action":
            a = p
            break
    if a is None:
        return None
    m = 0
    while a + 1 + m < n and events[a + 1 + m]["kind"] == "observation":
        m += 1
    return a + 1 + m


def _episode_record(
    parent: dict[str, Any],
    e: int,
    r1_k: int | None,
    index: int,
    n: int,
) -> dict[str, Any]:
    label = parent["label"]
    # Conservative placeholders; build_failure_scan patches both fields
    # for every record once escapes are known (the target requires the
    # escape AND the terminal label -- escape alone never suffices).
    return {
        "episode_id": f"{parent['parent_id']}:ep{index}",
        "episode_index": index,
        "parent_id": parent["parent_id"],
        "group_key": parent["group_key"],
        "split_group": split_group_for_parent(parent),
        "dataset": parent["dataset"],
        "parent_label": label,
        "e": e,
        "r0_k": e + 1,
        "r1_k": r1_k,
        "recovery_success": 0,
        "audit_bucket": (
            AUDIT_NO_ESCAPE_WITH_SETTLEMENT
            if label == 1
            else AUDIT_NO_ESCAPE_NO_SETTLEMENT
        ),
        "n_events_total": n,
    }


def build_failure_scan(parent: dict[str, Any]) -> dict[str, Any]:
    """Pure one-pass episode scan of a parent.

    Returns ``{"episodes": [episode records], "escape_positions":
    [int | None parallel to episodes], "exclusions":
    [{"e", "bucket"}], "leading_error_runs": int}``.  Escape positions
    are LABEL-SIDE audit data: they are deliberately NOT part of the
    episode records and never enter the feature frame.
    """
    events = parent["events"]
    n = len(events)

    episodes: list[dict[str, Any]] = []
    escape_positions: list[int | None] = []
    exclusions: list[dict[str, Any]] = []
    leading_error_runs = 0

    seen_obs = False  # any observation seen yet
    last_obs_was_error = False
    leading_run_open = False
    open_index: int | None = None  # episode whose error run is open

    for p, ev in enumerate(events):
        if ev["kind"] != "observation":
            continue
        if ev["is_error"]:
            if not seen_obs:
                # Leading context error: no non-error observation precedes
                # this run, so it never opens an episode.
                if not leading_run_open:
                    leading_error_runs += 1
                    leading_run_open = True
            elif not last_obs_was_error:
                # First error observation of a maximal run preceded by
                # >= 1 non-error observation: candidate opening.
                if p == n - 1:
                    exclusions.append(
                        {"e": p, "bucket": EXCLUSION_FAILURE_IS_FINAL_EVENT}
                    )
                else:
                    record = _episode_record(parent, p, None, len(episodes), n)
                    record["r1_k"] = _r1_cut(events, p)
                    open_index = len(episodes)
                    episodes.append(record)
                    escape_positions.append(None)
            last_obs_was_error = True
            seen_obs = True
        else:
            # Non-error observation: closes any open run and is that
            # episode's escape (label-side only).
            if open_index is not None:
                escape_positions[open_index] = p
                open_index = None
            last_obs_was_error = False
            seen_obs = True

    # Patch the label side now that escapes are known.
    for index, record in enumerate(episodes):
        escaped = escape_positions[index] is not None
        if record["parent_label"] == 1 and escaped:
            record["recovery_success"] = 1
            record["audit_bucket"] = AUDIT_ESCAPE_WITH_SETTLEMENT
        elif record["parent_label"] == 1:
            record["recovery_success"] = 0
            record["audit_bucket"] = AUDIT_NO_ESCAPE_WITH_SETTLEMENT
        elif escaped:
            record["recovery_success"] = 0
            record["audit_bucket"] = AUDIT_ESCAPE_NO_SETTLEMENT
        else:
            record["recovery_success"] = 0
            record["audit_bucket"] = AUDIT_NO_ESCAPE_NO_SETTLEMENT

    return {
        "episodes": episodes,
        "escape_positions": escape_positions,
        "exclusions": exclusions,
        "leading_error_runs": leading_error_runs,
    }


def build_failure_episodes(parent: dict[str, Any]) -> list[dict[str, Any]]:
    """Pure episode records for one parent per the frozen definition."""
    return build_failure_scan(parent)["episodes"]


# ---------------------------------------------------------------------------
# Episode feature extraction (pure; causal at the row's cut)
# ---------------------------------------------------------------------------


def _consecutive_error_observations(parent: dict[str, Any], k: int) -> int:
    """Length of the error-observation run ending at cut ``k``.

    Walks backwards over observation events from the last event in the
    window ``events[:k]``; actions are transparent (episode "run"
    semantics); the first non-error observation stops the count.
    """
    events = parent["events"]
    count = 0
    q = k - 1
    while q >= 0:
        ev = events[q]
        if ev["kind"] == "observation":
            if not ev["is_error"]:
                break
            count += 1
        q -= 1
    return count


def _current_streak_prior_nonerror(parent: dict[str, Any], e: int) -> int:
    """Consecutive non-error observations immediately preceding ``e``.

    Observation-subsequence walk (actions transparent); broken by the
    first earlier error observation.
    """
    events = parent["events"]
    count = 0
    q = e - 1
    while q >= 0:
        ev = events[q]
        if ev["kind"] == "observation":
            if ev["is_error"]:
                break
            count += 1
        q -= 1
    return count


def _episode_positional_features(
    parent: dict[str, Any],
    record: dict[str, Any],
    prior_escape_count: int,
) -> dict[str, float]:
    """Episode-positional causal additions (identical on R0 and R1)."""
    return {
        "fail_event_index": _r4(float(record["e"])),
        "prior_episode_count": _r4(float(record["episode_index"])),
        "prior_escape_count": _r4(float(prior_escape_count)),
        "errors_opening_run_available_at_r0": 1.0,
        "current_streak_prior_nonerror": _r4(
            float(_current_streak_prior_nonerror(parent, record["e"]))
        ),
    }


def _r1_addition_features(
    parent: dict[str, Any], record: dict[str, Any]
) -> dict[str, float]:
    """R1-addition features for one episode with ``r1_k is not None``.

    All inputs live inside the closed R1 window ``events[:r1_k]`` (the
    attempt result is in-window by the frozen construction).
    """
    events = parent["events"]
    n = len(events)
    e = record["e"]
    r1_k = record["r1_k"]
    assert r1_k is not None  # caller contract; never relied on at runtime

    feats: dict[str, float] = {name: 0.0 for name in R1_ADDITIONS}
    feats["recovery_attempt_present"] = 1.0

    attempt = next(
        p for p in range(e + 1, n) if events[p]["kind"] == "action"
    )
    prev_action = next(
        (p for p in range(attempt - 1, -1, -1) if events[p]["kind"] == "action"),
        None,
    )
    if prev_action is not None:
        feats["has_prior_action"] = 1.0
        feats["attempt_repeats_prior_action"] = (
            1.0 if events[attempt]["hash"] == events[prev_action]["hash"] else 0.0
        )
        # The attempt is the FIRST action after e, so the immediately
        # preceding action is necessarily the last pre-failure action.
        feats["has_pre_failure_action"] = 1.0
        feats["attempt_family_change"] = (
            1.0
            if _family_value(events[attempt]) != _family_value(events[prev_action])
            else 0.0
        )

    feats["obs_between_failure_and_attempt"] = _r4(
        float(
            sum(
                1
                for q in range(e + 1, attempt)
                if events[q]["kind"] == "observation"
            )
        )
    )

    if attempt + 1 < n and events[attempt + 1]["kind"] == "observation":
        result = events[attempt + 1]
        feats["has_attempt_result"] = 1.0
        feats["attempt_result_is_error"] = 1.0 if result["is_error"] else 0.0
        feats["attempt_result_same_hash_as_failure"] = (
            1.0 if result["hash"] == events[e]["hash"] else 0.0
        )

    seen_hashes: set[str] = set()
    novel = 0
    for q in range(r1_k):
        ev = events[q]
        if ev["kind"] != "observation":
            continue
        h = ev["hash"]
        if h not in seen_hashes:
            if q > e:
                novel += 1
            seen_hashes.add(h)
    feats["new_obs_between_failure_and_attempt"] = _r4(float(novel))

    return {name: _r4(value) for name, value in feats.items()}


def v005_minimal_recovery_features(
    parent: dict[str, Any], k: int
) -> dict[str, Any]:
    """Preregistered 7-feature ablation vector at any cut ``k``.

    Names map onto the v006 extractor outputs (never forked):
    ``error_count_so_far`` <- v006 ``error_count``;
    ``repeated_error_rate`` / ``error_rate`` <- v006 family;
    ``action_observation_ratio`` / ``tool_diversity_count`` /
    ``dataset_id`` <- v005 prefix family (H's int dtypes kept).
    ``consecutive_error_observations`` is computed here.
    """
    v006 = v006_prefix_features(parent, k)
    v005 = v005_prefix_compatible_features(parent, k)
    return {
        "error_count_so_far": v006["error_count"],
        "consecutive_error_observations": _r4(
            float(_consecutive_error_observations(parent, k))
        ),
        "repeated_error_rate": v006["repeated_error_rate"],
        "error_rate": v006["error_rate"],
        "action_observation_ratio": v005["action_observation_ratio"],
        "tool_diversity_count": v005["tool_diversity_count"],
        "dataset_id": v005["dataset_id"],
    }


def select_ablation_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Materialize the ``v005_minimal_recovery@1`` schema from a frame.

    ``error_count_so_far`` aliases the frame's ``error_count`` column
    (identical v006 formula at the row's cut); all other names are
    frame columns.  Raises ``ValueError`` on a frame missing any
    required column.
    """
    source_columns: list[str] = []
    for name in V005_MINIMAL_RECOVERY_FEATURES:
        column = "error_count" if name == "error_count_so_far" else name
        if column not in frame.columns:
            raise ValueError(
                f"Frame missing required ablation column: {column!r}"
            )
        source_columns.append(column)
    subset = frame.loc[:, source_columns].copy()
    subset.columns = list(V005_MINIMAL_RECOVERY_FEATURES)
    return subset[list(V005_MINIMAL_RECOVERY_FEATURES)]


# ---------------------------------------------------------------------------
# Frame builder
# ---------------------------------------------------------------------------


def _check_families(families: Sequence[str]) -> tuple[str, ...]:
    unknown = [family for family in families if family not in FEATURE_FAMILIES]
    if unknown:
        raise ValueError(
            f"Unknown feature families: {unknown}. "
            f"Available: {list(FEATURE_FAMILIES)}"
        )
    return tuple(family for family in ("v006", "v005_prefix_compatible") if family in families)


def build_episode_frame(
    corpus_iter: Iterable[dict[str, Any]],
    families: Sequence[str] = ("v006", "v005_prefix_compatible"),
) -> pd.DataFrame:
    """One row per (episode, point): R0 rows always, R1 rows when the
    episode has a post-failure attempt.

    Row identity carries the episode record fields plus ``point``
    (``'R0' | 'R1'``), ``dataset_id``, ``n_parent_episodes`` and the
    build-time ``weight_base = 1/(all episodes of the parent)``.  The
    frozen partition-time training weight is computed by
    :func:`parent_balanced_training_weights`.  Feature columns are
    ``R0_FEATURES`` (``R1`` rows recompute the prefix families at
    ``r1_k``), ``R1_ADDITIONS`` (0.0 with ``has_*`` = 0.0 on R0 rows),
    and the ablation-only ``consecutive_error_observations`` at the
    row's cut.
    """
    assert_recovery_schemas_clean()
    families_order = _check_families(families)
    rows: list[dict[str, Any]] = []

    for parent in corpus_iter:
        scan = build_failure_scan(parent)
        episodes = scan["episodes"]
        if not episodes:
            continue
        n_parent_episodes = len(episodes)
        weight_base = 1.0 / n_parent_episodes
        escape_positions = scan["escape_positions"]

        for record in episodes:
            index = record["episode_index"]
            prior_escape_count = sum(
                1
                for j in range(index)
                if escape_positions[j] is not None
                and escape_positions[j] < record["e"]
            )
            positional = _episode_positional_features(
                parent, record, prior_escape_count
            )
            identity = {
                "episode_id": record["episode_id"],
                "episode_index": record["episode_index"],
                "parent_id": record["parent_id"],
                "group_key": record["group_key"],
                "split_group": record["split_group"],
                "dataset": record["dataset"],
                "dataset_id": DATASET_ID_MAP.get(parent["dataset"], -1),
                "point": POINT_R0,
                "e": record["e"],
                "r0_k": record["r0_k"],
                "r1_k": record["r1_k"],
                "n_events_total": record["n_events_total"],
                "parent_label": record["parent_label"],
                "recovery_success": record["recovery_success"],
                "audit_bucket": record["audit_bucket"],
                "n_parent_episodes": n_parent_episodes,
                "weight_base": weight_base,
            }

            # ---- R0 row (window closes at the failure event) ----
            r0_row = dict(identity)
            for family in families_order:
                feats = extract_family_features(family, parent, record["r0_k"])
                feats.pop("dataset_id", None)
                r0_row.update(feats)
            r0_row.update(positional)
            for name in R1_ADDITIONS:
                r0_row.setdefault(name, 0.0)
            r0_row[ABLATION_EXTRA_COLUMN] = _r4(
                float(_consecutive_error_observations(parent, record["r0_k"]))
            )
            rows.append(r0_row)

            # ---- R1 row (window closes at the attempt + its result) ----
            if record["r1_k"] is not None:
                r1_row = dict(identity)
                r1_row["point"] = POINT_R1
                for family in families_order:
                    feats = extract_family_features(
                        family, parent, record["r1_k"]
                    )
                    feats.pop("dataset_id", None)
                    r1_row.update(feats)
                r1_row.update(positional)
                r1_row.update(_r1_addition_features(parent, record))
                r1_row[ABLATION_EXTRA_COLUMN] = _r4(
                    float(
                        _consecutive_error_observations(parent, record["r1_k"])
                    )
                )
                rows.append(r1_row)

    return pd.DataFrame(rows, columns=list(FRAME_COLUMNS))


def parent_balanced_training_weights(frame: pd.DataFrame) -> pd.Series:
    """FROZEN training weight: ``1/(training episodes of that parent)``.

    Apply to a single-point (R0 or R1, never pooled) TRAINING frame.
    Episodes are counted as distinct ``episode_id`` values per parent --
    never rows -- so an episode contributing both an R0 and an R1 row to
    a pooled frame still counts once.
    """
    if frame.empty:
        return pd.Series(dtype=float)
    episode_counts = frame.groupby("parent_id")["episode_id"].nunique()
    reciprocal = 1.0 / episode_counts
    return frame["parent_id"].map(reciprocal).astype(float)


# ---------------------------------------------------------------------------
# Config, CLI, manifest
# ---------------------------------------------------------------------------


def load_episode_config(path: str | Path) -> dict[str, Any]:
    """Load and validate a v007 episode configuration file."""
    with Path(path).open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    required_keys = {
        "episodes_id",
        "sources",
        "episode_definition",
        "audit_buckets",
        "exclusion_buckets",
        "feature_schemas",
        "output",
    }
    missing = required_keys - set(data.keys())
    if missing:
        raise ValueError(f"Episode config missing required keys: {missing}")

    for source in data["sources"]:
        for key in ("name", "corpus_path"):
            if key not in source:
                raise ValueError(f"Source entry missing required key: {key}")

    output = data["output"]
    for key in ("root", "episode_table", "manifest"):
        if key not in output:
            raise ValueError(f"Output block missing required key: {key}")

    return data


def _median(values: Sequence[float]) -> float:
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return float(ordered[mid])
    return (ordered[mid - 1] + ordered[mid]) / 2


def _episodes_per_parent_stats(
    parent_episode_counts: Sequence[int],
    parents_scanned: int,
) -> dict[str, Any]:
    with_episodes = [count for count in parent_episode_counts if count > 0]
    distribution = (
        {
            "mean": _r4(sum(with_episodes) / len(with_episodes)),
            "median": _r4(_median(with_episodes)),
            "max": float(max(with_episodes)),
        }
        if with_episodes
        else {"mean": 0.0, "median": 0.0, "max": 0.0}
    )
    return {
        "parents_scanned": parents_scanned,
        "parents_with_episodes": len(with_episodes),
        "parents_without_episodes": parents_scanned - len(with_episodes),
        "episodes_per_parent": distribution,
    }


def _json_safe(value: Any) -> Any:
    """Convert numpy/pandas scalars and NaN to JSON-native values."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def _frame_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return [
        {key: _json_safe(value) for key, value in row.items()}
        for row in frame.to_dict("records")
    ]


def build_episode_table(config: dict[str, Any]) -> dict[str, Any]:
    """Build the episode frame over every configured source + manifest.

    A source with zero episodes (nebius, v006-verified) is handled
    gracefully and recorded with zeros, never treated as an error.
    Bucket/label/r0-only counts are derived from the built frame so the
    manifest cannot disagree with the materialized table; the episode
    scan is re-run only for scan-only quantities (exclusions, leading
    runs, per-parent episode counts).
    """
    columns = list(FRAME_COLUMNS)
    audit_totals: Counter[str] = Counter()
    exclusion_totals: Counter[str] = Counter()
    label_totals: Counter[int] = Counter()
    per_source: dict[str, dict[str, Any]] = {}
    frames: list[pd.DataFrame] = []
    all_parent_episode_counts: list[int] = []

    for source in config["sources"]:
        parents = read_records_jsonl(source["corpus_path"])
        frame = build_episode_frame(parents)
        frames.append(frame)

        parent_episode_counts = [
            len(build_failure_episodes(parent)) for parent in parents
        ]
        all_parent_episode_counts.extend(parent_episode_counts)

        exclusion_counts: Counter[str] = Counter()
        leading_runs = 0
        for parent in parents:
            scan = build_failure_scan(parent)
            leading_runs += scan["leading_error_runs"]
            for entry in scan["exclusions"]:
                exclusion_counts[entry["bucket"]] += 1

        if frame.empty:
            audit_counts: Counter[str] = Counter()
            label_counts: Counter[int] = Counter()
            r0_only = 0
            episodes = 0
        else:
            # Bucket/label counts are EPISODE counts: collapse the two
            # rows (R0/R1) of one episode before counting.
            episode_level = frame.drop_duplicates(subset=["episode_id"])
            audit_counts = Counter(episode_level["audit_bucket"])
            label_counts = Counter(
                int(value) for value in episode_level["recovery_success"]
            )
            episodes = len(episode_level)
            r0_only = int(episode_level["r1_k"].isna().sum())

        audit_totals.update(audit_counts)
        exclusion_totals.update(exclusion_counts)
        label_totals.update(label_counts)

        per_source[source["name"]] = {
            "corpus_path": source["corpus_path"],
            "revision_sha": source.get("revision_sha"),
            "license_status": source.get("license_status"),
            "episodes": episodes,
            "r0_only_episodes": r0_only,
            "episodes_with_r1": episodes - r0_only,
            "recovery_success_1": label_counts[1],
            "recovery_success_0": label_counts[0],
            "audit_buckets": dict(audit_counts),
            "exclusions": dict(exclusion_counts),
            "leading_error_runs": leading_runs,
            **_episodes_per_parent_stats(parent_episode_counts, len(parents)),
        }
        if source.get("expected_episodes") == 0 and episodes == 0:
            per_source[source["name"]]["note"] = (
                "zero episodes as expected (v006-verified: source has no "
                "is_error events)"
            )

    full_frame = (
        pd.concat(frames, ignore_index=True)
        if frames
        else pd.DataFrame(columns=columns)
    )
    if full_frame.empty:
        full_frame = pd.DataFrame(columns=columns)

    r0_rows = int((full_frame["point"] == POINT_R0).sum()) if not full_frame.empty else 0
    r1_rows = int((full_frame["point"] == POINT_R1).sum()) if not full_frame.empty else 0
    total_episodes = int(full_frame["episode_id"].nunique()) if not full_frame.empty else 0
    r0_only_total = (
        int(full_frame.loc[full_frame["r1_k"].isna(), "episode_id"].nunique())
        if not full_frame.empty
        else 0
    )
    with_episodes = [count for count in all_parent_episode_counts if count > 0]

    manifest = {
        "episodes_id": str(config["episodes_id"]),
        "created_at": utc_now_iso(),
        "schema_versions": dict(SCHEMA_VERSIONS),
        "totals": {
            "episodes": total_episodes,
            "r0_only_episodes": r0_only_total,
            "episodes_with_r1": total_episodes - r0_only_total,
            "rows_r0": r0_rows,
            "rows_r1": r1_rows,
            "rows_total": int(len(full_frame)),
            "columns": int(len(full_frame.columns)),
            "recovery_success_1": label_totals[1],
            "recovery_success_0": label_totals[0],
            "audit_buckets": {
                bucket: audit_totals[bucket] for bucket in AUDIT_BUCKETS
            },
            "exclusions": {
                bucket: exclusion_totals[bucket] for bucket in EXCLUSION_BUCKETS
            },
        },
        "episodes_per_parent": {
            "mean": _r4(sum(with_episodes) / len(with_episodes))
            if with_episodes
            else 0.0,
            "median": _r4(_median(with_episodes)) if with_episodes else 0.0,
            "max": float(max(with_episodes)) if with_episodes else 0.0,
            "parents_with_episodes": len(with_episodes),
            "parents_without_episodes": len(all_parent_episode_counts)
            - len(with_episodes),
        },
        "feature_schemas": {
            "r0": {"version": R0_SCHEMA_VERSION, "n_features": len(R0_FEATURES)},
            "r1_additions": {
                "version": R1_SCHEMA_VERSION,
                "n_features": len(R1_ADDITIONS),
            },
            "r1_total": {
                "version": R1_SCHEMA_VERSION,
                "n_features": len(R1_FEATURES),
            },
            "ablation": {
                "version": V005_MINIMAL_RECOVERY_SCHEMA_VERSION,
                "n_features": len(V005_MINIMAL_RECOVERY_FEATURES),
            },
        },
        "sources": per_source,
    }
    return {"frame": full_frame, "manifest": manifest}


def main() -> None:
    """CLI entry point: materialize the episode table + manifest."""
    parser = argparse.ArgumentParser(
        description=(
            "Build the v007 failure-episode table over the v006 corpus."
        )
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Path to the v007 episode configuration YAML",
    )
    args = parser.parse_args()

    config = load_episode_config(args.config)
    built = build_episode_table(config)
    frame: pd.DataFrame = built["frame"]
    manifest: dict[str, Any] = built["manifest"]

    output = config["output"]
    table_path = Path(output["episode_table"])
    manifest_path = Path(output["manifest"])
    table_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    with table_path.open("w", encoding="utf-8") as f:
        for record in _frame_records(frame):
            f.write(json.dumps(record, sort_keys=True) + "\n")

    manifest["episode_table"] = str(table_path)
    manifest["episode_table_sha256"] = hashlib.sha256(
        table_path.read_bytes()
    ).hexdigest()
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
