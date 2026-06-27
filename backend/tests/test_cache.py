import time
import json


def test_cache_uses_memory_fallback_without_redis_url(client, monkeypatch):
    from app.cache.client import clear_cache_backend
    from app.cache.service import get_cache
    from app.core.config import get_settings

    monkeypatch.setenv("REDIS_URL", "")
    get_settings.cache_clear()
    clear_cache_backend()

    cache = get_cache()
    cache.set("capabilities", "ready", ttl_seconds=30)

    assert cache.get("capabilities") == "ready"
    cache.delete("capabilities")
    assert cache.get("capabilities") is None


def test_memory_cache_respects_ttl(client, monkeypatch):
    from app.cache.client import clear_cache_backend
    from app.cache.service import get_cache
    from app.core.config import get_settings

    monkeypatch.setenv("REDIS_URL", "")
    get_settings.cache_clear()
    clear_cache_backend()

    cache = get_cache()
    cache.set("short-lived", "value", ttl_seconds=0.01)
    time.sleep(0.02)

    assert cache.get("short-lived") is None


def test_settings_exposes_redis_url(monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/0")
    get_settings.cache_clear()

    assert get_settings().redis_url == "redis://redis:6379/0"


def test_task_queue_settings_and_inline_mode(monkeypatch):
    from app.core.config import get_settings
    from app.tasks.queue import enqueue_task, worker_queue_keys

    monkeypatch.setenv("TASK_QUEUE_MODE", "inline")
    monkeypatch.setenv("TASK_QUEUE_PREFIX", "test:tasks")
    monkeypatch.setenv("TASK_WORKER_QUEUES", "materials,presentations")
    get_settings.cache_clear()

    assert enqueue_task("material.parse", {"material_id": 1}, queue="materials") is False
    assert worker_queue_keys() == ["test:tasks:materials", "test:tasks:presentations"]


def test_ai_capabilities_endpoint_writes_cache(client, monkeypatch):
    from app.cache.client import clear_cache_backend
    from app.cache.service import get_cache
    from app.core.config import get_settings

    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODEL", "cached-model")
    monkeypatch.setenv("REDIS_URL", "")
    get_settings.cache_clear()
    clear_cache_backend()

    response = client.get("/api/ai/capabilities")

    assert response.status_code == 200
    cached = get_cache().get("ai:capabilities")
    assert cached is not None
    assert json.loads(cached)["text_model"] == "cached-model"
