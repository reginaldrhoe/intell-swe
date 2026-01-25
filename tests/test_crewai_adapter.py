import asyncio
import os

from agents.core.crewai_adapter import CrewAIAdapter
from agents.impl.engineer_crewai import EngineerCodeReviewCrewAI

def test_crewai_adapter_fallback_stub():
    # Ensure the adapter returns a stub when no crewai/openai clients are present
    # Remove env vars that would trigger real clients
    os.environ.pop("CREWAI_API_KEY", None)
    os.environ.pop("OPENAI_API_KEY", None)

    adapter = CrewAIAdapter(model="test-model")

    result = asyncio.run(adapter.run("Hello world"))
    assert isinstance(result, dict)
    assert "text" in result
    assert result["text"].startswith("[stub]")

def test_crewai_adapter_and_agent_basic():
    adapter = CrewAIAdapter(model="text-embedding-3-small")
    # run adapter synchronously via asyncio
    res = asyncio.run(adapter.run("Summarize: test"))
    assert isinstance(res, dict)
    assert "text" in res

    agent = EngineerCodeReviewCrewAI("TestEngineer")
    task = {"title": "Sample task", "description": "Check this code", "files": ["a.py"]}
    out = asyncio.run(agent.process(task))
    assert isinstance(out, dict)
    assert out.get("agent") == "TestEngineer"
    assert "result" in out
