"""Run a smoke test of AgentManagementLayer with CrewAIAdapter mocked.

This script monkeypatches `agents.crewai_adapter.CrewAIAdapter.run` to return
a deterministic response, then invokes the MCP to handle a sample task.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import asyncio
from agents.agents import MasterControlPanel
import agents.crewai_adapter as adapter_mod

async def main():
    # monkeypatch the adapter.run
    async def fake_run(self, prompt, **kwargs):
        return {"text": "[mocked] analysis result for prompt: " + prompt[:80]}

    adapter_mod.CrewAIAdapter.run = fake_run

    mcp = MasterControlPanel()
    task = {"title": "Smoke task", "description": "Run agents on sample", "files": ["a.py"]}
    results = await mcp.handle_task(task)
    print('Results:')
    for k, v in results.items():
        print(k, '->', v)

if __name__ == '__main__':
    asyncio.run(main())
