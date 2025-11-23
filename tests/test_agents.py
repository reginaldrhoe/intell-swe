from agents.agents import MasterControlPanel


def test_master_control_panel_handles_task():
    mcp = MasterControlPanel()
    sample_task = {
        "title": "Unit test task",
        "description": "A simple test",
        "files": ["a.py"]
    }
    # submit_task runs the async handler synchronously
    results = mcp.submit_task(sample_task)
    assert isinstance(results, dict)
    assert len(results) > 0
    # Each agent should have produced a string result
    for k, v in results.items():
        assert isinstance(v, str)
