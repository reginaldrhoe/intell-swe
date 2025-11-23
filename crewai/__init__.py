from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional
import asyncio


@dataclass
class Task:
    name: str
    input: Any = None
    metadata: Dict[str, Any] = None


class Process:
    def __init__(self, result: Any, metadata: Optional[Dict[str, Any]] = None):
        self.result = result
        self.metadata = metadata or {}

    def output(self) -> Any:
        return self.result


class Agent:
    """A minimal Agent wrapper.

    Can be used as a decorator to register a callable as an agent, or
    constructed directly with a callable. The `run` method is async and
    will execute sync callables on the default executor.
    """

    def __init__(self, func: Optional[Callable] = None, name: Optional[str] = None):
        self._func = func
        self.name = name or (getattr(func, "__name__", None) if func is not None else "agent")

    async def run(self, task: Task) -> Process:
        if self._func is None:
            return Process(None)
        if asyncio.iscoroutinefunction(self._func):
            res = await self._func(task)
        else:
            # Use asyncio.to_thread for sync callables — avoids relying on
            # event loop policies that may be different in CI/pytest.
            res = await asyncio.to_thread(self._func, task)
        return Process(res)

    def __call__(self, func: Callable) -> "Agent":
        return Agent(func, name=getattr(func, "__name__", None))


class _ClientAPI:
    """A tiny stubbed client surface that mimics common CrewAI shapes used
    by the adapter tests. Methods return simple serializable objects so the
    adapter can extract text content.
    """

    class _Completions:
        def create(self, model: str, prompt: str, **kwargs):
            return {"text": f"[stub] {prompt[:500]}"}

    class _Responses:
        def create(self, model: str, input: str, **kwargs):
            return {"output": [{"content": f"[stub] {input[:500]}"}]}

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.completions = self._Completions()
        self.responses = self._Responses()


def Client(api_key: Optional[str] = None):
    """Factory that returns a small client-like object.

    The real CrewAI package exposes richer objects; tests here only need a
    compact API with `.completions.create` or `.responses.create` or a
    top-level `create`-like call. We provide small implementations for
    those shapes.
    """

    return _ClientAPI(api_key=api_key)


def create(model: str, prompt: str, **kwargs):
    """Top-level convenience create() that mirrors older simplistic APIs.

    Returns a small dict with a `text` field.
    """

    return {"text": f"[stub] {prompt[:500]}"}


class Crew:
    """Simple collection of agents that can be run on a task."""

    def __init__(self, agents: Optional[List[Agent]] = None):
        self.agents = agents or []

    async def run(self, task: Task) -> List[Process]:
        results = []
        for agent in self.agents:
            proc = await agent.run(task)
            results.append(proc)
        return results


def tool(func: Optional[Callable] = None, *, name: Optional[str] = None):
    """Minimal no-op tool decorator that marks a function as a tool.

    The decorator attaches attributes `_is_tool` and `_tool_name` so
    downstream code can introspect tools.
    """

    def _decorate(f: Callable) -> Callable:
        setattr(f, "_is_tool", True)
        setattr(f, "_tool_name", name or getattr(f, "__name__", None))
        return f

    if func is None:
        return _decorate
    return _decorate(func)
