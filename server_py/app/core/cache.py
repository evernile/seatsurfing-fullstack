from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class _CacheEntry:
    value: bytes
    expires_at: float


class TTLCache:
    """
    Cache in-memory con TTL (semplice e sufficiente per dev/local).
    API pensata per imitare GetCache() del Go:
      - get(key) -> bytes (o solleva KeyError)
      - set(key, value, ttl_seconds)
      - delete(key)
    """

    def __init__(self) -> None:
        self._store: Dict[str, _CacheEntry] = {}

    def set(self, key: str, value: bytes, ttl_seconds: int) -> None:
        self._store[key] = _CacheEntry(value=value, expires_at=time.time() + ttl_seconds)

    def get(self, key: str) -> bytes:
        entry = self._store.get(key)
        if not entry:
            raise KeyError(key)
        if entry.expires_at < time.time():
            # expired
            self._store.pop(key, None)
            raise KeyError(key)
        return entry.value

    def delete(self, key: str) -> None:
        self._store.pop(key, None)


# Singleton "tipo Go"
_cache_singleton: Optional[TTLCache] = None


def get_cache() -> TTLCache:
    global _cache_singleton
    if _cache_singleton is None:
        _cache_singleton = TTLCache()
    return _cache_singleton