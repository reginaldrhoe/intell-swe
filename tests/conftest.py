import asyncio
import pytest


# Ensure a default event loop exists for each test.
# Provide an autouse fixture so tests that call
# `asyncio.get_event_loop().run_until_complete(...)` succeed in CI.
@pytest.fixture(autouse=True)
def ensure_event_loop():
    try:
        loop = asyncio.get_event_loop()
        if loop is None or loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    yield
    # Do not close the loop here; pytest or other fixtures may reuse it.
