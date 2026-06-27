from app.cache.client import CacheBackend, get_cache_backend
from app.core.config import get_settings


def get_cache() -> CacheBackend:
    return get_cache_backend(get_settings().redis_url)
