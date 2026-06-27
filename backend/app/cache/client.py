from __future__ import annotations

from functools import lru_cache
from time import monotonic
from typing import Protocol


class CacheBackend(Protocol):
    def get(self, key: str) -> str | None: ...

    def set(self, key: str, value: str, ttl_seconds: float = 300) -> None: ...

    def delete(self, key: str) -> None: ...


class MemoryCacheBackend:
    def __init__(self) -> None:
        self._items: dict[str, tuple[str, float | None]] = {}

    def get(self, key: str) -> str | None:
        value = self._items.get(key)
        if value is None:
            return None

        payload, expires_at = value
        if expires_at is not None and expires_at <= monotonic():
            self._items.pop(key, None)
            return None
        return payload

    def set(self, key: str, value: str, ttl_seconds: float = 300) -> None:
        expires_at = monotonic() + ttl_seconds if ttl_seconds > 0 else None
        self._items[key] = (value, expires_at)

    def delete(self, key: str) -> None:
        self._items.pop(key, None)


class RedisCacheBackend:
    def __init__(self, redis_url: str) -> None:
        try:
            from redis import Redis
        except ImportError as exc:
            raise RuntimeError("redis package is not installed") from exc

        self._client = Redis.from_url(redis_url, decode_responses=True)

    def get(self, key: str) -> str | None:
        value = self._client.get(key)
        return value if isinstance(value, str) else None

    def set(self, key: str, value: str, ttl_seconds: float = 300) -> None:
        self._client.set(key, value, ex=max(1, int(ttl_seconds)))

    def delete(self, key: str) -> None:
        self._client.delete(key)


class ResilientCacheBackend:
    def __init__(self, primary: CacheBackend, fallback: MemoryCacheBackend | None = None) -> None:
        self._primary = primary
        self._fallback = fallback or MemoryCacheBackend()

    def get(self, key: str) -> str | None:
        try:
            return self._primary.get(key)
        except Exception:
            return self._fallback.get(key)

    def set(self, key: str, value: str, ttl_seconds: float = 300) -> None:
        try:
            self._primary.set(key, value, ttl_seconds)
        except Exception:
            self._fallback.set(key, value, ttl_seconds)

    def delete(self, key: str) -> None:
        try:
            self._primary.delete(key)
        except Exception:
            self._fallback.delete(key)


@lru_cache
def get_cache_backend(redis_url: str = "") -> CacheBackend:
    if not redis_url:
        return MemoryCacheBackend()
    try:
        return ResilientCacheBackend(RedisCacheBackend(redis_url))
    except RuntimeError:
        return MemoryCacheBackend()


def clear_cache_backend() -> None:
    get_cache_backend.cache_clear()
