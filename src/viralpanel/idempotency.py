import redis

from viralpanel.config import get_settings


class IdempotencyManager:
    """Atomic distributed locks backed by Redis (SET NX EX)."""

    def __init__(self, client=None, prefix: str = "viralpanel:lock:"):
        self.client = client or redis.Redis.from_url(get_settings().redis_url)
        self.prefix = prefix

    def acquire_lock(self, key: str, ttl_seconds: int = 3600) -> bool:
        return bool(self.client.set(self.prefix + key, "1", nx=True, ex=ttl_seconds))

    def release_lock(self, key: str) -> None:
        self.client.delete(self.prefix + key)
