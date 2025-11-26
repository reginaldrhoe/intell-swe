"""Simple Redis lock helpers (async + sync) used for cross-process task locking.

This module provides tiny wrappers to acquire/release a tokenized lock
so multiple processes (FastAPI + Celery workers) can coordinate task runs.

It prefers `redis.asyncio` for async usage and `redis` (sync) for worker
processes. Functions are intentionally small and tolerate missing Redis.
"""
from uuid import uuid4
from typing import Optional, Tuple

DEFAULT_TTL = 60 * 60  # 1 hour

try:
    import redis.asyncio as aioredis  # type: ignore
except Exception:
    aioredis = None

try:
    import redis as redis_sync  # type: ignore
except Exception:
    redis_sync = None


async def acquire_lock_async(redis_client, key: str, ttl: int = DEFAULT_TTL) -> Optional[str]:
    """Attempt to set a lock key with a random token. Returns the token if acquired, else None."""
    if redis_client is None or aioredis is None:
        return None
    token = uuid4().hex
    try:
        ok = await redis_client.set(key, token, nx=True, ex=ttl)
        if ok:
            return token
    except Exception:
        # swallow — caller can fallback to DB-only protection
        pass
    return None


async def release_lock_async(redis_client, key: str, token: str) -> None:
    """Release lock only if token matches (uses a small Lua script to be atomic)."""
    if redis_client is None or aioredis is None:
        return
    try:
        lua = """
        if redis.call('get', KEYS[1]) == ARGV[1] then
            return redis.call('del', KEYS[1])
        else
            return 0
        end
        """
        try:
            await redis_client.eval(lua, 1, key, token)
        except Exception:
            # Some redis clients don't expose eval in the same way; try simple check/delete
            try:
                cur = await redis_client.get(key)
                if cur == token:
                    await redis_client.delete(key)
            except Exception:
                pass
    except Exception:
        pass


def acquire_lock_sync(redis_url: str, key: str, ttl: int = DEFAULT_TTL) -> Tuple[Optional[object], Optional[str]]:
    """Synchronous acquire for worker processes. Returns (client, token) if acquired else (None, None)."""
    if redis_sync is None or not redis_url:
        return (None, None)
    try:
        client = redis_sync.from_url(redis_url, decode_responses=True)
        token = uuid4().hex
        ok = client.set(key, token, nx=True, ex=ttl)
        if ok:
            return (client, token)
    except Exception:
        pass
    return (None, None)


def release_lock_sync(redis_client, key: str, token: str) -> None:
    """Synchronous release of the lock if token matches."""
    if redis_client is None:
        return
    try:
        try:
            # atomic via Lua
            lua = """
            if redis.call('get', KEYS[1]) == ARGV[1] then
                return redis.call('del', KEYS[1])
            else
                return 0
            end
            """
            redis_client.eval(lua, 1, key, token)
        except Exception:
            cur = None
            try:
                cur = redis_client.get(key)
            except Exception:
                cur = None
            if cur == token:
                try:
                    redis_client.delete(key)
                except Exception:
                    pass
    except Exception:
        pass
