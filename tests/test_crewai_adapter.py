import asyncio
from agents.crewai_adapter import CrewAIAdapter
from agents.engineer_crewai import EngineerCodeReviewCrewAI


def test_crewai_adapter_and_agent_basic():
    adapter = CrewAIAdapter(model="text-embedding-3-small")
    # run adapter synchronously via asyncio
    res = asyncio.get_event_loop().run_until_complete(adapter.run("Summarize: test"))
    assert isinstance(res, dict)
    assert "text" in res

    agent = EngineerCodeReviewCrewAI("TestEngineer")
    task = {"title": "Sample task", "description": "Check this code", "files": ["a.py"]}
    out = asyncio.get_event_loop().run_until_complete(agent.process(task))
    assert isinstance(out, dict)
    assert out.get("agent") == "TestEngineer"
    assert "result" in out
