import pytest

fakeredis = pytest.importorskip("fakeredis")

from viralpanel.idempotency import IdempotencyManager


def test_lock_blocks_duplicates():
    m = IdempotencyManager(client=fakeredis.FakeRedis())
    assert m.acquire_lock("k") is True
    assert m.acquire_lock("k") is False
    m.release_lock("k")
    assert m.acquire_lock("k") is True
