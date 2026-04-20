from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import Any, Optional

from core.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_redis_client():
    if not settings.redis_url:
        return None
    try:
        import redis

        return redis.Redis.from_url(settings.redis_url, decode_responses=True)
    except Exception as exc:  # pragma: no cover - optional dependency/runtime issue
        logger.warning("redis unavailable: %s", exc)
        return None


def _safe_call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as exc:  # pragma: no cover - cache must never break requests
        logger.warning("cache operation failed: %s", exc)
        return None


def get_json(key: str) -> Optional[Any]:
    client = get_redis_client()
    if not client:
        return None
    raw = _safe_call(client.get, key)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        logger.warning("cache payload decode failed for key=%s", key)
        return None


def set_json(key: str, value: Any, ttl_seconds: int = 300) -> None:
    client = get_redis_client()
    if not client:
        return None
    payload = json.dumps(value, ensure_ascii=False, default=str)
    _safe_call(client.setex, key, ttl_seconds, payload)


def delete(key: str) -> None:
    client = get_redis_client()
    if not client:
        return None
    _safe_call(client.delete, key)


def delete_prefix(prefix: str) -> None:
    client = get_redis_client()
    if not client:
        return None
    keys = _safe_call(client.keys, f"{prefix}*") or []
    if keys:
        _safe_call(client.delete, *keys)
