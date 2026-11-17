"""Unit tests for the GSA settlement publisher (WP-3, F-02).

The drain/watermark logic is tested deterministically with a fake publisher
(no live NATS). The live end-to-end (GSA → NATS → ledger → Postgres) lives in
`tests/e2e/`.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from agentic_capability_loop.adapters import emit_settlement_recorded
from agentic_capability_loop.publisher import SettlementPublisher
from godspeed_nav.storage import LedgerStore

OUTBOX = "agentic_outbound_events"


class _FakePublisher(SettlementPublisher):
    """Records publishes; programmable to succeed/fail to test drain ordering."""

    def __init__(self, *, fail_after: int | None = None):
        super().__init__(nats_url=None, enabled=False)
        self.published: list[dict] = []
        self._fail_after = fail_after  # fail every publish after N successes
        self._successes = 0

    async def publish(self, envelope):  # type: ignore[override]
        if self._fail_after is not None and self._successes >= self._fail_after:
            return False
        self.published.append(envelope)
        self._successes += 1
        return True


def _seed(store: LedgerStore, count: int) -> list[dict]:
    envs = []
    for i in range(count):
        settlement = emit_settlement_recorded(
            f"wr-{i}", f"pr-{i}", f"ev-{i}", "usable", f"match-{i}"
        )
        envs.append(store.append_event(OUTBOX, settlement))
    return envs


def test_publisher_disabled_by_default_is_noop(tmp_path):
    p = SettlementPublisher()  # no GSA_NATS_URL
    import asyncio

    result = asyncio.run(p.publish({"event_type": "X"}))
    assert result is False
    assert p.enabled is False


def test_drain_forwards_unforwarded_records_and_advances_watermark(tmp_path):
    store = LedgerStore(str(tmp_path))
    _seed(store, 3)
    pub = _FakePublisher()

    import asyncio

    r1 = asyncio.run(pub.drain(store, OUTBOX))
    assert r1 == {"forwarded": 3, "skipped": 0, "total": 3}
    assert len(pub.published) == 3
    # Watermark advanced to the last sequence.
    wm = pub._read_watermark(store)
    assert wm[OUTBOX] == 3

    # A second drain with nothing new forwards nothing.
    r2 = asyncio.run(pub.drain(store, OUTBOX))
    assert r2 == {"forwarded": 0, "skipped": 0, "total": 0}
    assert len(pub.published) == 3


def test_drain_picks_up_only_new_records_after_first_drain(tmp_path):
    store = LedgerStore(str(tmp_path))
    _seed(store, 2)
    pub = _FakePublisher()
    import asyncio

    asyncio.run(pub.drain(store, OUTBOX))
    assert len(pub.published) == 2

    # Append more after the first drain.
    _seed(store, 2)  # sequences 3,4
    r = asyncio.run(pub.drain(store, OUTBOX))
    assert r == {"forwarded": 2, "skipped": 0, "total": 2}
    assert len(pub.published) == 4


def test_drain_stops_on_failure_and_leaves_buffer_in_order(tmp_path):
    store = LedgerStore(str(tmp_path))
    _seed(store, 5)
    # Fail after the 2nd success → forward 2, then stop (3,4,5 stay buffered).
    pub = _FakePublisher(fail_after=2)
    import asyncio

    r = asyncio.run(pub.drain(store, OUTBOX))
    assert r["forwarded"] == 2
    assert pub._read_watermark(store)[OUTBOX] == 2

    # A fresh publisher that succeeds drains the remaining 3 in order.
    pub2 = _FakePublisher()
    r2 = asyncio.run(pub2.drain(store, OUTBOX))
    assert r2 == {"forwarded": 3, "skipped": 0, "total": 3}
    outcomes = [e["payload"]["outcome"] for e in pub2.published]
    assert outcomes == ["usable", "usable", "usable"]


def test_published_envelopes_are_v1_conformant(tmp_path):
    """The drain forwards the inner v1 record, not the JSONL wrapper."""
    from agentic_capability_loop.tests.test_v1_contract import assert_v1  # noqa: E402

    store = LedgerStore(str(tmp_path))
    _seed(store, 1)
    pub = _FakePublisher()
    import asyncio

    asyncio.run(pub.drain(store, OUTBOX))
    assert len(pub.published) == 1
    forwarded = pub.published[0]
    assert forwarded["source_agent"] == "godspeed-agent"
    assert_v1(forwarded)  # teeth: what leaves the process is v1
