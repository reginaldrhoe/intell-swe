import asyncio
import pytest

from mcp import redis_lock


class FakeAsyncRedis:
    def __init__(self):
        self.store = {}

    async def set(self, key, value, nx=False, ex=None):
        if nx and key in self.store:
            return False
        self.store[key] = value
        return True

    async def get(self, key):
        return self.store.get(key)

    async def delete(self, key):
        return self.store.pop(key, None)

    async def eval(self, lua, num_keys, key, token):
        if self.store.get(key) == token:
            self.store.pop(key, None)
            return 1
        return 0


class FakeSyncClient:
    def __init__(self):
        self.store = {}

    def set(self, key, value, nx=False, ex=None):
        if nx and key in self.store:
            return False
        self.store[key] = value
        return True

    def get(self, key):
        return self.store.get(key)

    def delete(self, key):
        return self.store.pop(key, None)

    def eval(self, lua, num_keys, key, token):
        if self.store.get(key) == token:
            self.store.pop(key, None)
            return 1
        return 0


@pytest.mark.asyncio
async def test_acquire_release_async():
    fake = FakeAsyncRedis()
    key = 'test:1:lock'

    token = await redis_lock.acquire_lock_async(fake, key, ttl=5)
    assert isinstance(token, str) and len(token) > 0

    # Second attempt should fail (nx)
    token2 = await redis_lock.acquire_lock_async(fake, key, ttl=5)
    assert token2 is None

    # Release and allow re-acquire
    await redis_lock.release_lock_async(fake, key, token)
    token3 = await redis_lock.acquire_lock_async(fake, key, ttl=5)
    assert isinstance(token3, str) and token3 != token


def test_acquire_release_sync(monkeypatch):
    fake_client = FakeSyncClient()

    class FakeRedisModule:
        @staticmethod
        def from_url(url, decode_responses=True):
            return fake_client

    monkeypatch.setattr(redis_lock, 'redis_sync', FakeRedisModule)

    key = 'test:2:lock'
    client, token = redis_lock.acquire_lock_sync('redis://unused', key, ttl=5)
    assert client is not None and token is not None

    # second attempt fails
    client2, token2 = redis_lock.acquire_lock_sync('redis://unused', key, ttl=5)
    assert client2 is None and token2 is None

    # release and try again
    redis_lock.release_lock_sync(client, key, token)
    client3, token3 = redis_lock.acquire_lock_sync('redis://unused', key, ttl=5)
    assert client3 is not None and token3 is not None
