"""GSA → memory-ledger transport (WP-3, F-02).

Publishes GSA's v1 settlement/capability events to NATS subject
`sea.agent.event.godspeed-agent.<event_type>`, where the ledger bridge picks
them up and persists to `event_log.agent_events` (fail-closed v1 validation).

Offline-first by design (the §14 "staged transport" decision): the JSONL
`LedgerStore` stays the local write-ahead buffer; this publisher is a one-way
**drain** that forwards buffered events when NATS is reachable and silently
no-ops otherwise — mirroring edgeai's spool pattern. A failed publish never
breaks the inner loop; the event stays buffered and is retried on the next
drain.

Activation: set `GSA_NATS_URL` (or pass `nats_url`). Without it, or without the
`nats` package, the publisher is a no-op that logs once.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from godspeed_nav.storage import LedgerStore

logger = logging.getLogger(__name__)

SUBJECT_PREFIX = "sea.agent.event.godspeed-agent"
_IDEMPOTENCY_HEADER = "Nats-Msg-Id"


def _slug(event_type: str) -> str:
    return event_type.replace("_", "-").lower()


class SettlementPublisher:
    """One-way NATS drain for GSA's v1 envelopes.

    Disabled unless `GSA_NATS_URL` is set (or `nats_url` passed). When
    disabled, `publish`/`drain` are no-ops returning zero — the JSONL buffer
    is the source of truth until NATS is reachable.
    """

    def __init__(
        self,
        nats_url: str | None = None,
        *,
        enabled: bool | None = None,
        connect_timeout: int = 5,
    ) -> None:
        self._nats_url = nats_url or os.getenv("GSA_NATS_URL")
        self._connect_timeout = connect_timeout
        # Explicit enabled wins; otherwise enabled iff a URL is configured.
        self._enabled = bool(self._nats_url) if enabled is None else bool(enabled)
        self._nc: Any = None
        self._js: Any = None
        self._connect_attempted = False
        self._connected = False

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def connected(self) -> bool:
        return self._connected

    async def _ensure_connected(self) -> bool:
        if not self._enabled:
            return False
        if self._connected:
            return True
        if self._connect_attempted:
            # Don't retry every publish on a dead server — caller drains again later.
            return False
        self._connect_attempted = True
        try:
            import nats  # noqa: PLC0415
        except ImportError:
            logger.warning("gsa publisher disabled: nats package not installed")
            self._enabled = False
            return False
        try:
            self._nc = await nats.connect(
                self._nats_url, connect_timeout=self._connect_timeout
            )
            self._js = self._nc.jetstream()
            self._connected = True
            logger.info("gsa publisher connected to %s", self._nats_url)
            return True
        except Exception as exc:  # noqa: BLE001 — never break the loop on transport
            logger.warning("gsa publisher could not connect (%s); staying offline", exc)
            return False

    async def publish(self, envelope: dict[str, Any]) -> bool:
        """Publish a single v1 envelope. Returns True iff it reached NATS."""
        if not await self._ensure_connected() or self._js is None:
            return False
        event_type = envelope.get("event_type", "event")
        subject = f"{SUBJECT_PREFIX}.{_slug(event_type)}"
        msg_id = envelope.get("idempotency_key") or envelope.get("event_id", "")
        body = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode("utf-8")
        try:
            await self._js.publish(
                subject, body, headers={_IDEMPOTENCY_HEADER: msg_id}
            )
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("gsa publish failed for %s (%s); will retry on next drain", subject, exc)
            return False

    async def close(self) -> None:
        if self._nc is not None:
            try:
                await self._nc.close()
            except Exception:  # noqa: BLE001
                pass
            self._nc = None
            self._js = None
            self._connected = False

    # ── JSONL drain ────────────────────────────────────────────────────────

    def _watermark_path(self, store: "LedgerStore") -> Path:
        return Path(store.root) / "config" / "nats_forward_watermark.json"

    def _read_watermark(self, store: "LedgerStore") -> dict[str, int]:
        path = self._watermark_path(store)
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _write_watermark(self, store: "LedgerStore", wm: dict[str, int]) -> None:
        path = self._watermark_path(store)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(wm, sort_keys=True), encoding="utf-8")

    async def drain(
        self, store: "LedgerStore", ledger_name: str
    ) -> dict[str, int]:
        """Forward unforwarded `append_event` records from a ledger to NATS.

        The JSONL file is append-only and never rewritten — forwarding state is
        a per-ledger sequence watermark in `config/nats_forward_watermark.json`.
        Returns counts: {forwarded, skipped, total}.
        """
        events = store.read_events(ledger_name)
        wm = self._read_watermark(store)
        last_forwarded = wm.get(ledger_name, 0)
        forwarded = 0
        total = 0
        for env in events:
            seq = int(env.get("sequence", 0))
            if seq <= last_forwarded:
                continue
            total += 1
            record = env.get("record")
            if not isinstance(record, dict):
                continue
            if await self.publish(record):
                forwarded += 1
                # Advance per-success so a mid-drain failure retries from here.
                last_forwarded = seq
                wm[ledger_name] = last_forwarded
                self._write_watermark(store, wm)
            else:
                # Offline or publish failure — stop draining this ledger;
                # remaining events stay buffered (in-order forwarding).
                break
        return {"forwarded": forwarded, "skipped": total - forwarded, "total": total}


def drain_persisted_to_nats(
    store: "LedgerStore", ledger_names: tuple[str, ...]
) -> dict[str, dict[str, int]]:
    """Sync, best-effort drain of the given ledgers to NATS.

    Called from `persist_to_ledger` after the JSONL buffer is written: if
    `GSA_NATS_URL` is configured and NATS is reachable, settlements/capabilities
    are forwarded now; otherwise this is a no-op and the events stay buffered
    until a later drain (a hook/CLI invocation). Never raises — a transport
    failure must not break the inner loop.
    """
    import asyncio  # noqa: PLC0415

    pub = SettlementPublisher()
    if not pub.enabled:
        return {}
    results: dict[str, dict[str, int]] = {}
    try:
        loop = asyncio.new_event_loop()
        try:
            for name in ledger_names:
                results[name] = loop.run_until_complete(pub.drain(store, name))
        finally:
            loop.run_until_complete(pub.close())
            loop.close()
    except Exception as exc:  # noqa: BLE001
        logger.warning("best-effort NATS drain failed (%s); events stay buffered", exc)
        return results
    return results
