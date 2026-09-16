"""Shared v006 parent-trajectory corpus builder.

Streams the configured v006 calibration sources, normalises rows into
settlement records, and converts each usable record into a compact
parent-trajectory record.  The corpus is the contemporary substrate for
all v006 experiments; features are derived from pre-outcome signals
only, and labels come exclusively from ``outcome.success``.

Source scope: as of T03b the v006 corpus streams swegym_openhands and
nebius_swe_agent only.  ``agenttrove`` is rejected for v006 -- its live
revision carries no populated terminal-label column (see the rejection
note in ``configs/settlement_datasets/v006_corpus.yaml``); its adapter
remains available for fixture/local input.

Proof classification: all parents inherit ``external-proxy-settlement``
records and are valid for calibration/experiment use only.

**No raw trajectory text is stored.**  Events carry derived markers,
lengths, and content hashes only.

**Identity model (trajectory vs instance):**
- ``group_key`` = ``<dataset>:<instance_or_task_id>`` -- the task
  instance a trajectory belongs to.  Same-instance trajectories never
  straddle partitions: splits and prefix grouping MUST key on
  ``group_key``, which is stricter than per-parent uniqueness.
- ``parent_id`` = ``<dataset>:<instance_or_task_id>:<run_discriminator>``
  -- one distinct parent run over that instance.  ``instance_or_task_id``
  is the record's ``task_id`` (the HF ``instance_id`` for
  swegym/nebius); records without a task_id fall back to
  ``<content_hash[:16]>``.
- ``run_discriminator`` resolution: ``<metadata.source_run_id>-`` +
  ``sha1[:10]`` of the full canonical trajectory content hash (events +
  label) when the source provides a per-run field (swegym rows carry
  ``run_id``), else ``sha1[:10]`` of the content hash alone.  The
  content-hash component is mandatory: source run ids name a sampling
  batch and repeat across distinct runs of one instance (observed in
  the live swegym window), and same-instance runs can also share an
  identical first action, so neither alone satisfies the requirement
  that different runs of one instance get different ``parent_id``
  values.
- Deduplication drops only TRUE duplicates: same dataset and identical
  full-trajectory content hash (canonical event list including the
  label).  Distinct runs over one instance always survive.  Dropped
  rows are counted in ``duplicates_dropped``.

**Event derivation (from the settlement record's affordance_path only,
never re-parsed raw rows):**
- ``kind``: ``action`` for ``affordance_path.actions``,
  ``observation`` for ``affordance_path.observations``.
- Per adapter reality: swegym_openhands emits assistant actions and
  tool observations; nebius emits ai/assistant actions and user/tool
  observations (user entries carry tool output); agenttrove's
  settlement record carries actions only (user/system context is
  therefore represented as a count, not as events).
- ``cmd_family`` (actions with role ``assistant`` only, first match
  wins, case-insensitive keyword regexes):
  1. ``git``: ``\\bgit\\b``
  2. ``install``: pip/apt/conda/npm/uv install forms
  3. ``test``: pytest/unittest/tox/nosetests/npm test/make test/cargo test
  4. ``python``: ``\\bpython3?\\b``
  5. ``edit``: apply_patch/str_replace_editor/sed/nano/vim/nvim/touch/edit
  6. ``inspect``: cat/ls/head/tail/grep/find/rg/awk/diff/status/log/show/view/open/list/check
  Order rationale: ``git`` wins over ``inspect`` (``git diff``), install
  wins over test (``pip install pytest``), test wins over python
  (``python -m pytest``).  No match on non-empty content -> ``other``;
  empty content -> ``None``; all other events -> ``None``.
- ``is_error``: observations whose lowercased content contains any of
  ``error``/``fail``/``traceback``/``exception``/``assertionerror``.
- ``mentions_bash``: assistant content contains ``bash``.
- ``has_terminal_output``: observation content contains
  ``New Terminal Output:`` (agenttrove terminal marker).  Because the
  agenttrove settlement record carries no observations, this marker is
  always False for agenttrove parents.

**v005 feature reproduction:** ``counts`` copies the settlement
record's payment counters verbatim (``turns``, ``tool_calls``,
``commands``, ``elapsed_steps``, ``error_count``), so v005
full-trajectory features are reproducible without re-derivation.
``total_messages`` equals v005's ``elapsed_steps`` (all messages).
``n_context_events`` is ``total_messages - n_actions -
n_observations`` (clamped at 0): user/system messages for
swegym_openhands, system messages for nebius (its adapter emits user
entries as observations), and non-observation user messages for
agenttrove -- noting agenttrove's labeler caps ``actions`` at 20
entries, so the subtraction can undercount context on long traces.

**Context scoping (v007 correction MAJOR-1):** live rows interleave
context messages mid-trajectory, so the trajectory-total
``n_context_events`` says nothing about how much context an agent had
absorbed at prefix time.  Each event therefore carries ``ctx``: the
number of context messages whose raw-sequence index is strictly below
the event's turn index, derived from the adapter's
``context_positions(raw)`` at stream time.  ``context_scoped`` marks
whether real position data was supplied (legacy callers that skip it
get ``ctx`` 0 on every event); ``trailing_context`` is the diagnostic
count of context messages at or after the last event
(``n_context_events - ctx of last event``; expected >= 0).  ``ctx`` is
excluded from the trajectory content hash, so identity (``parent_id``)
is invariant to the annotation and the corrected corpus keeps v007
parent ids.

**Label provenance:** ``label`` is 1 iff ``outcome.success is True``,
0 iff ``outcome.success is False``; records with undefined success or
confidence below ``min_confidence`` are rejected (reason recorded,
never swallowed).
"""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Sequence

import yaml

from scripts.settlement_datasets.adapter_base import (
    SettlementDatasetAdapter,
    write_records_jsonl,
)
from scripts.settlement_datasets.registry import get_adapter
from scripts.settlement_datasets.run_scoped_paths import utc_now_iso

CORPORA_ROOT = Path("data/settlement_datasets/corpora")
SUMMARY_RUN_DIR = Path("data/settlement_datasets/runs/hf-calibration-006-experiments")

REASON_OUTCOME_UNDEFINED = "outcome_success_undefined"
REASON_CONFIDENCE_BELOW_THRESHOLD = "confidence_below_threshold"

_ERROR_KEYWORDS = ("error", "fail", "traceback", "exception", "assertionerror")

_CMD_FAMILY_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("git", re.compile(r"\bgit\b")),
    (
        "install",
        re.compile(
            r"\b(?:pip3?\s+install|apt(?:-get)?\s+install|conda\s+install"
            r"|npm\s+install|uv\s+pip\s+install|uv\s+add)\b"
        ),
    ),
    (
        "test",
        re.compile(
            r"\b(?:pytest|py\.test|unittest|tox|nosetests"
            r"|npm\s+test|make\s+test|cargo\s+test)\b"
        ),
    ),
    ("python", re.compile(r"\bpython3?\b")),
    (
        "edit",
        re.compile(
            r"\b(?:apply_patch|str_replace_editor|sed|nano|vim|nvim|touch)\b|\bedit"
        ),
    ),
    (
        "inspect",
        re.compile(
            r"\b(?:cat|ls|head|tail|grep|find|rg|awk|diff|status|log"
            r"|show|view|open|list|check)\b"
        ),
    ),
)

# Every string stored in an event is a short derived marker; this bound
# is asserted by tests to guard against accidentally embedding text.
_MAX_EVENT_STRING_LEN = 12
_MAX_EVIDENCE_MARKER_LEN = 48

# Documented in corpus_manifest.json / corpus_summary.json so downstream
# consumers key splits and grouping on the right field.
IDENTITY_MODEL: dict[str, str] = {
    "group_key": (
        "<dataset>:<instance_or_task_id> -- the shared task instance; "
        "same-instance trajectories never straddle partitions, so splits "
        "and prefix grouping MUST key on group_key"
    ),
    "parent_id": (
        "<dataset>:<instance_or_task_id>:<run_discriminator> -- one "
        "distinct parent run over the instance"
    ),
    "run_discriminator": (
        "<metadata.source_run_id>-<sha1[:10] of full canonical trajectory "
        "content hash (events incl. label)> when the source provides a "
        "per-run field, else the content hash alone; the content-hash "
        "component is mandatory because source run ids repeat across "
        "distinct runs of one instance"
    ),
    "deduplication": (
        "drop only true duplicates: same dataset and identical "
        "full-trajectory content hash (canonical events including label); "
        "counted as duplicates_dropped"
    ),
}


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


def load_corpus_config(path: str | Path) -> dict[str, Any]:
    """Load and validate a corpus configuration file."""
    with Path(path).open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    required_keys = {"corpus_id", "min_confidence", "usability_rule", "datasets"}
    missing = required_keys - set(data.keys())
    if missing:
        raise ValueError(f"Corpus config missing required keys: {missing}")

    for ds in data["datasets"]:
        for key in (
            "name",
            "source_uri",
            "adapter",
            "split",
            "max_rows",
            "revision_sha",
            "license_status",
        ):
            if key not in ds:
                raise ValueError(f"Dataset entry missing required key: {key}")

    return data


# ---------------------------------------------------------------------------
# Event and parent conversion
# ---------------------------------------------------------------------------


def _classify_cmd_family(content: str) -> str | None:
    """Deterministic keyword-regex cmd family for assistant action content."""
    lowered = content.lower()
    if not lowered.strip():
        return None
    for family, pattern in _CMD_FAMILY_PATTERNS:
        if pattern.search(lowered):
            return family
    return "other"


def _event_from_entry(entry: dict[str, Any], kind: str) -> dict[str, Any]:
    content = entry.get("content") or ""
    role = entry.get("role") or "assistant"
    lowered = content.lower()
    is_action = kind == "action"
    is_observation = kind == "observation"
    is_assistant = role == "assistant"
    return {
        "i": entry.get("turn_index", 0),
        "kind": kind,
        "role": role,
        "content_len": len(content),
        "hash": hashlib.sha1(content.encode("utf-8")).hexdigest()[:10],
        "mentions_bash": is_action and is_assistant and "bash" in lowered,
        "is_error": is_observation
        and any(kw in lowered for kw in _ERROR_KEYWORDS),
        "cmd_family": _classify_cmd_family(content)
        if is_action and is_assistant
        else None,
        "has_terminal_output": is_observation
        and "New Terminal Output:" in content,
    }


def _trajectory_content_hash(events: list[dict[str, Any]], label: int) -> str:
    """Stable sha1 over the canonical event list including the label.

    ``ctx`` is excluded from the canonical form: it is a derived
    context-scoping annotation (v007 correction MAJOR-1), and identity
    must stay invariant to it so the ctx-annotated rebuild keeps the
    v007 corpus parent ids.
    """
    canonical = json.dumps(
        {
            "events": [
                {key: value for key, value in event.items() if key != "ctx"}
                for event in events
            ],
            "label": label,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha1(canonical.encode("utf-8")).hexdigest()


def _derive_identity_parts(
    record: dict[str, Any], content_hash: str
) -> tuple[str, str, str]:
    """Return ``(parent_id, group_key, dataset)`` for a settlement record.

    ``parent_id`` names one parent run (dataset:instance:discriminator);
    ``group_key`` names the shared task instance (dataset:instance).
    """
    dataset = record.get("dataset", "unknown")
    task_id = str(record.get("task_id") or "")
    instance_part = task_id or content_hash[:16]
    metadata = record.get("metadata") or {}
    source_run_id = str(metadata.get("source_run_id") or "")
    if source_run_id:
        # Source run ids identify a sampling batch and can repeat across
        # runs of one instance, so the content-hash component is always
        # appended to keep distinct runs distinct.
        discriminator = f"{source_run_id}-{content_hash[:10]}"
    else:
        discriminator = content_hash[:10]
    return (
        f"{dataset}:{instance_part}:{discriminator}",
        f"{dataset}:{instance_part}",
        dataset,
    )


def _label_source(outcome: dict[str, Any]) -> str:
    """Short, sanitised evidence markers -- never raw trajectory text."""
    parts = [f"success={outcome.get('success')}"]
    quality = outcome.get("settlement_quality")
    if quality:
        parts.append(f"settlement_quality={quality}")
    for entry in outcome.get("evidence", []) or []:
        if not isinstance(entry, str):
            continue
        if len(entry) <= _MAX_EVIDENCE_MARKER_LEN and not any(
            ch.isspace() for ch in entry
        ):
            parts.append(entry)
    return "; ".join(parts)


def build_parent(
    record: dict[str, Any],
    *,
    revision_sha: str,
    license_status: str,
    min_confidence: float,
    context_positions: Sequence[int] | None = None,
) -> tuple[dict[str, Any] | None, str | None]:
    """Convert a settlement record into a parent-trajectory record.

    Returns ``(parent, None)`` on success or ``(None, rejection_reason)``
    when the usability rule rejects the record.

    ``context_positions`` is the sorted list of raw-sequence indices of
    context (non-event) messages, from
    ``SettlementDatasetAdapter.context_positions(raw)``.  Each event
    gains ``ctx`` = the number of positions strictly below its turn
    index (how much off-stream context the agent had absorbed by that
    event), the parent gains ``context_scoped=True``, and
    ``trailing_context`` records context at or after the last event.
    Callers that omit the parameter (legacy signature) get ``ctx`` 0 on
    every event and ``context_scoped=False`` -- valid only for sources
    with genuinely no scoped context, and prefix features then fall back
    to ``elapsed = k``.
    """
    outcome = record.get("outcome", {})
    success = outcome.get("success")
    if success is None:
        return None, REASON_OUTCOME_UNDEFINED
    confidence = outcome.get("confidence", 0.0) or 0.0
    if confidence < min_confidence:
        return None, REASON_CONFIDENCE_BELOW_THRESHOLD

    dataset = record.get("dataset", "unknown")
    payment = record.get("payment", {})
    affordance_path = record.get("affordance_path", {})
    actions = affordance_path.get("actions", []) or []
    observations = affordance_path.get("observations", []) or []

    events = [_event_from_entry(entry, "action") for entry in actions]
    events.extend(_event_from_entry(entry, "observation") for entry in observations)
    # Stable sort by turn index; actions precede observations at equal i.
    events.sort(key=lambda ev: ev["i"])

    total_messages = int(payment.get("elapsed_steps", 0) or 0)
    n_context_events = max(total_messages - len(actions) - len(observations), 0)

    # Context scoping (v007 correction MAJOR-1): per-event cumulative
    # context counts strictly below each event's turn index.
    context_scoped = context_positions is not None
    positions = sorted(context_positions) if context_positions else []
    for event in events:
        event["ctx"] = bisect.bisect_left(positions, event["i"])
    trailing_context = (
        n_context_events - events[-1]["ctx"] if events else n_context_events
    )

    metadata = record.get("metadata", {})
    tool_names_manifest = [t for t in (metadata.get("tool_names") or []) if t]

    label = 1 if success is True else 0
    content_hash = _trajectory_content_hash(events, label)
    parent_id, group_key, _ = _derive_identity_parts(record, content_hash)

    parent = {
        "parent_id": parent_id,
        "group_key": group_key,
        "dataset": dataset,
        "revision_sha": revision_sha,
        "license_status": license_status,
        "label": label,
        "label_source": _label_source(outcome),
        "outcome_confidence": float(confidence),
        "n_context_events": n_context_events,
        "context_scoped": context_scoped,
        "trailing_context": trailing_context,
        "total_messages": total_messages,
        "tool_names_manifest": tool_names_manifest,
        # Verbatim v005 payment counters for exact feature reproduction.
        "counts": {
            "turns": int(payment.get("turns", 0) or 0),
            "tool_calls": int(payment.get("tool_calls", 0) or 0),
            "commands": int(payment.get("commands", 0) or 0),
            "elapsed_steps": total_messages,
            "error_count": int(payment.get("error_count", 0) or 0),
        },
        "events": events,
    }
    return parent, None


# ---------------------------------------------------------------------------
# Corpus build
# ---------------------------------------------------------------------------


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _top_rejection_reasons(reasons: Counter[str], top: int = 5) -> list[dict[str, Any]]:
    return [
        {"reason": reason, "count": count}
        for reason, count in reasons.most_common(top)
    ]


def build_corpus(
    *,
    config_path: str | Path,
    output_root: str | Path | None = None,
    summary_path: str | Path | None = None,
) -> dict[str, Any]:
    """Stream every configured source and write the corpus + manifest + summary.

    Counting contract per dataset:
    ``scanned == usable + rejected + duplicates_dropped`` where
    ``rejected`` covers adapter errors and usability rejections (both
    recorded in ``top_rejection_reasons``) and duplicates are TRUE
    duplicates only: later rows whose full-trajectory content hash
    (canonical events including label) repeats within the dataset.
    Distinct runs over one instance always survive.
    """
    config = load_corpus_config(config_path)
    created_at = utc_now_iso()

    corpus_root = (
        Path(output_root) if output_root else CORPORA_ROOT / str(config["corpus_id"])
    )
    corpus_root.mkdir(parents=True, exist_ok=True)

    min_confidence = float(config["min_confidence"])
    manifest_datasets: dict[str, dict[str, Any]] = {}
    total_usable = 0

    for source in config["datasets"]:
        ds_name = source["name"]
        adapter = get_adapter(source["adapter"])
        max_rows = source.get("max_rows")
        # Context scoping (v007 correction MAJOR-1): adapters that
        # implement context_positions scope their parents; adapters on
        # the base default declare no separable context and stay
        # unscoped (ctx 0, context_scoped=false) rather than claiming a
        # scope they cannot see.
        adapter_scopes_context = (
            type(adapter).context_positions
            is not SettlementDatasetAdapter.context_positions
        )

        stream_kwargs: dict[str, Any] = {}
        if source.get("input_path"):
            stream_kwargs["input_path"] = source["input_path"]
        else:
            stream_kwargs["source_uri"] = source.get("source_uri", adapter.source_uri)
            stream_kwargs["split"] = source.get("split", "train")

        counts = {
            "scanned": 0,
            "normalized": 0,
            "usable": 0,
            "rejected": 0,
            "adapter_errors": 0,
            "duplicates_dropped": 0,
        }
        rejection_reasons: Counter[str] = Counter()
        label_counts = {"success": 0, "failure": 0}
        seen_content: set[tuple[str, str]] = set()
        parents: list[dict[str, Any]] = []

        for raw in adapter.stream(limit=max_rows, **stream_kwargs):
            counts["scanned"] += 1
            try:
                record = adapter.to_settlement_record(raw)
            except Exception as exc:
                reason = f"adapter_error:{type(exc).__name__}:{str(exc)[:60]}"
                rejection_reasons[reason] += 1
                counts["adapter_errors"] += 1
                counts["rejected"] += 1
                continue

            # Enforce external-proxy-settlement classification.
            metadata = record.get("metadata", {})
            metadata["settlement_classification"] = "external-proxy-settlement"
            record["metadata"] = metadata

            counts["normalized"] += 1

            parent, reason = build_parent(
                record,
                revision_sha=str(source["revision_sha"]),
                license_status=str(source["license_status"]),
                min_confidence=min_confidence,
                context_positions=(
                    adapter.context_positions(raw)
                    if adapter_scopes_context
                    else None
                ),
            )
            if parent is None:
                rejection_reasons[reason] += 1
                counts["rejected"] += 1
                continue

            content_hash = _trajectory_content_hash(parent["events"], parent["label"])
            key = (ds_name, content_hash)
            if key in seen_content:
                counts["duplicates_dropped"] += 1
                continue
            seen_content.add(key)

            parents.append(parent)
            counts["usable"] += 1
            label_counts["success" if parent["label"] == 1 else "failure"] += 1

        corpus_path = corpus_root / f"{ds_name}.jsonl"
        write_records_jsonl(parents, str(corpus_path))

        total_usable += counts["usable"]
        manifest_datasets[ds_name] = {
            "source_uri": source["source_uri"],
            "split": source["split"],
            "max_rows": max_rows,
            "revision_sha": source["revision_sha"],
            "license_status": source["license_status"],
            # Context scoping (v007 correction MAJOR-1): true iff every
            # surviving parent was built from real context positions.
            "context_scoped": bool(parents)
            and all(parent["context_scoped"] for parent in parents),
            **counts,
            "label_counts": label_counts,
            "top_rejection_reasons": _top_rejection_reasons(rejection_reasons),
            "corpus_file": str(corpus_path),
            "sha256": _sha256_file(corpus_path),
        }

    manifest = {
        "corpus_id": str(config["corpus_id"]),
        "created_at": created_at,
        "config_path": str(config_path),
        "settlement_classification": config.get(
            "settlement_classification", "external-proxy-settlement"
        ),
        "usability_rule": config["usability_rule"],
        "min_confidence": min_confidence,
        "identity_model": IDENTITY_MODEL,
        "datasets": manifest_datasets,
    }
    manifest_path = corpus_root / "corpus_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    summary = {
        "corpus_id": str(config["corpus_id"]),
        "created_at": created_at,
        "config_path": str(config_path),
        "corpus_manifest_path": str(manifest_path),
        "settlement_classification": manifest["settlement_classification"],
        "usability_rule": config["usability_rule"],
        "min_confidence": min_confidence,
        "total_usable_parents": total_usable,
        "identity_model": IDENTITY_MODEL,
        "datasets": {
            ds_name: {
                "scanned": ds["scanned"],
                "normalized": ds["normalized"],
                "usable": ds["usable"],
                "rejected": ds["rejected"],
                "adapter_errors": ds["adapter_errors"],
                "duplicates_dropped": ds["duplicates_dropped"],
                "context_scoped": ds["context_scoped"],
                "label_counts": ds["label_counts"],
                "top_rejection_reasons": ds["top_rejection_reasons"],
                "revision_sha": ds["revision_sha"],
                "license_status": ds["license_status"],
                "corpus_file": ds["corpus_file"],
                "sha256": ds["sha256"],
            }
            for ds_name, ds in manifest_datasets.items()
        },
    }

    summary_resolved = Path(summary_path) if summary_path else SUMMARY_RUN_DIR / "corpus_summary.json"
    summary_resolved.parent.mkdir(parents=True, exist_ok=True)
    summary_resolved.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    summary["corpus_summary_path"] = str(summary_resolved)

    return summary


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point for the corpus builder."""
    parser = argparse.ArgumentParser(
        description="Build the shared v006 parent-trajectory corpus."
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Path to corpus configuration YAML",
    )
    parser.add_argument(
        "--output-root",
        default=None,
        help="Override corpus output root directory",
    )
    parser.add_argument(
        "--summary-path",
        default=None,
        help="Override corpus summary JSON path",
    )

    args = parser.parse_args()

    summary = build_corpus(
        config_path=args.config,
        output_root=args.output_root,
        summary_path=args.summary_path,
    )

    # Print summary to stdout for CLI consumers
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
