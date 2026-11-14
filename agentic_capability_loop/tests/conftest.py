"""Pin a deployment world for the adapter tests (Stage 9).

Consequential events refuse to emit without a pinned world_ref, so the suite
pins one by default. Tests that exercise the unpinned path delete it.
"""

import pytest

TEST_WORLD_REF = "world:acl@sha256:" + "b" * 64


@pytest.fixture(autouse=True)
def pinned_world(monkeypatch):
    monkeypatch.setenv("GSA_WORLD_REF", TEST_WORLD_REF)
    return TEST_WORLD_REF
