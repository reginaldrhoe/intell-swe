import asyncio

from agents.core.agents import MasterControlPanel


class DummyAgent:
    def __init__(self, name):
        self.name = name

    async def process(self, task):
        return f"{self.name}: handled {task.get('title')}"


def test_mcp_dispatch_monkeypatch():
    # Replace the AgentManagementLayer with a simple one that uses DummyAgent
    mcp = MasterControlPanel()

    # inject dummy agents directly
    mcp.agent_manager.agents = [DummyAgent("A1"), DummyAgent("A2")]

    result = asyncio.run(mcp.handle_task({"title": "test-task", "description": "desc"}))

    assert isinstance(result, dict)
    assert "A1" in result and "A2" in result
    assert result["A1"].startswith("A1:")
