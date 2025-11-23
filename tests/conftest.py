import asyncio

# Ensure a default event loop exists in the main thread for tests.
# Some CI environments / Python versions raise when calling
# `asyncio.get_event_loop()` if no loop has been set; create and set
# one early so tests that use `get_event_loop().run_until_complete(...)`
# or similar APIs don't fail.
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())
