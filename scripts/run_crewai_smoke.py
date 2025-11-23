import asyncio
import sys
from pathlib import Path
# ensure repo root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agents.crewai_adapter import CrewAIAdapter
from agents.engineer_crewai import EngineerCodeReviewCrewAI

print('Running adapter test...')
adapter = CrewAIAdapter()
res = asyncio.get_event_loop().run_until_complete(adapter.run('Summarize: test'))
print('Adapter result type:', type(res), 'keys=', list(res.keys()))
assert isinstance(res, dict) and 'text' in res

print('Running agent test...')
agent = EngineerCodeReviewCrewAI('TestEngineer')
task = { 'title': 'Sample task', 'description': 'Check this code', 'files': ['a.py'] }
out = asyncio.get_event_loop().run_until_complete(agent.process(task))
print('Agent output:', out)
assert isinstance(out, dict) and out.get('agent') == 'TestEngineer' and 'result' in out
print('OK')
