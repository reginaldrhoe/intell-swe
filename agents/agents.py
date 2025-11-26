import asyncio
import os
import logging
logging.basicConfig(level=logging.INFO)
# Base class for all agents

class Agent:
    def __init__(self, name):
        self.name = name
    async def process(self, task):
        raise NotImplementedError("Subclasses must implement the process method.")
# Specialized agents
class EngineerCodeReviewAgent(Agent):
    async def process(self, task):
        logging.info(f"{self.name}: Analyzing code for task '{task['title']}'.")
        await asyncio.sleep(1)  # Simulated processing delay
        return f"{self.name}: Suggest reviewing files {task.get('files', 'N/A')} ."
class RootCauseInvestigatorAgent(Agent):
    async def process(self, task):
        logging.info(f"{self.name}: Investigating root cause for task '{task['title']}'.")
        await asyncio.sleep(1)
        return f"{self.name}: Likely cause identified in module X."
class DefectDiscoveryAgent(Agent):
    async def process(self, task):
        logging.info(f"{self.name}: Discovering defects associated with task '{task['title']}'.")
        await asyncio.sleep(1)
        return f"{self.name}: Found potential systemic issues in the CI pipeline."
class RequirementsTracingAgent(Agent):
    async def process(self, task):
        logging.info(f"{self.name}: Tracing requirements for task '{task['title']}'.")
        await asyncio.sleep(1)
        return f"{self.name}: Mismatch found between requirement Y and implementation."
class PerformanceMetricsAgent(Agent):
    async def process(self, task):
        logging.info(f"{self.name}: Generating performance metrics for task '{task['title']}'.")
        await asyncio.sleep(1)
        return f"{self.name}: All performance metrics are within the acceptable range."
class AuditAgent(Agent):
    async def process(self, task):
        logging.info(f"{self.name}: Auditing compliance for task '{task['title']}'.")
        await asyncio.sleep(1)
        return f"{self.name}: Compliance check passed."
# CrewAI data integration module to simulate data capture from external sources.

class CrewAIDataIntegration:
    def fetch_defect_data(self, task):
        logging.info("CrewAI: Fetching defect and integration data for the task.")
        # Simulate fetching data from Git, JIRA, CAMEO, RAG database, etc.
        simulated_data = {
            "defects": 5,
            "last_commit": "abcd1234",
            "issue_summary": "Intermittent failure in integration tests."
        }
        return simulated_data

# Agent management layer that holds and dispatches tasks to agents.

class AgentManagementLayer:
    def __init__(self):
        # lazy import of crewai-backed agents if present
        from .engineer_crewai import EngineerCodeReviewCrewAI
        try:
            from .root_cause_crewai import RootCauseInvestigatorCrewAI
            from .defect_discovery_crewai import DefectDiscoveryCrewAI
            from .requirements_tracing_crewai import RequirementsTracingCrewAI
            from .perf_metrics_crewai import PerformanceMetricsCrewAI
            from .audit_crewai import AuditCrewAI
            extra_agents = [
                RootCauseInvestigatorCrewAI("RootCauseAgent"),
                DefectDiscoveryCrewAI("DiscoveryAgent"),
                RequirementsTracingCrewAI("RequirementsAgent"),
                PerformanceMetricsCrewAI("MetricsAgent"),
                AuditCrewAI("AuditAgent"),
            ]
        except Exception:
            # fall back to the simple built-in agents if crewai-backed ones aren't importable
            extra_agents = [
                RootCauseInvestigatorAgent("RootCauseAgent"),
                DefectDiscoveryAgent("DiscoveryAgent"),
                RequirementsTracingAgent("RequirementsAgent"),
                PerformanceMetricsAgent("MetricsAgent"),
                AuditAgent("AuditAgent"),
            ]

        self.agents = [EngineerCodeReviewCrewAI("EngineerAgent")] + extra_agents

    async def process_task(self, task):
        results = {}
        # Dispatch the task concurrently to all agents
        tasks = [asyncio.create_task(agent.process(task)) for agent in self.agents]
        responses = await asyncio.gather(*tasks)
        for agent, response in zip(self.agents, responses):
            # Normalize agent responses to simple strings so callers/tests
            # don't need to know agent-specific return shapes.
            if isinstance(response, str):
                results[agent.name] = response
            elif isinstance(response, dict):
                # Prefer common keys used by crewai-backed agents
                if "result" in response:
                    results[agent.name] = response.get("result")
                elif "text" in response:
                    results[agent.name] = response.get("text")
                else:
                    # Fallback to stringifying the dict
                    results[agent.name] = str(response)
            else:
                results[agent.name] = str(response)
        return results
 # Master Control Panel that orchestrates the entire process

class MasterControlPanel:
    def __init__(self, publisher=None):
        """publisher: optional async function (task_id:int, event:dict) -> None
        that will be awaited to publish per-task events (SSE/redis).
        """
        self.data_integration = CrewAIDataIntegration()
        self.agent_manager = AgentManagementLayer()
        self.publisher = publisher

    async def handle_task(self, task):
        logging.info("MCP: Received new task.")
        # Optional test-only hold to keep the task "running" for a period so
        # distributed lock behavior can be observed during smoke tests.
        try:
            hold = int(os.getenv('TEST_HOLD_SECONDS', '0') or '0')
            if hold > 0:
                logging.info("TEST_HOLD_SECONDS set; sleeping %s seconds to hold task", hold)
                await asyncio.sleep(hold)
        except Exception:
            pass
        # Enrich task data using CrewAI's integration layer
        defect_data = self.data_integration.fetch_defect_data(task)
        task.update(defect_data)
        logging.info("MCP: Enriched task data, dispatching to agents.")

        results = {}
        task_id = task.get('id')
        from datetime import datetime
        # Run agents concurrently but emit per-agent events as they progress.
        lock = asyncio.Lock()

        async def run_agent(agent):
            nonlocal results
            try:
                if self.publisher and task_id is not None:
                    try:
                        await self.publisher(task_id, {"type": "agent_status", "agent": agent.name, "status": "running"})
                    except Exception:
                        # swallow publisher errors so they don't stop agent work
                        pass

                resp = await agent.process(task)

                # Normalize response similar to previous behavior
                if isinstance(resp, str):
                    content = resp
                elif isinstance(resp, dict):
                    if "result" in resp:
                        content = resp.get("result")
                    elif "text" in resp:
                        content = resp.get("text")
                    else:
                        content = str(resp)
                else:
                    content = str(resp)

                # Safely write result
                async with lock:
                    results[agent.name] = content

                # Publish activity + done status
                if self.publisher and task_id is not None:
                    try:
                        await self.publisher(task_id, {"type": "activity", "agent": agent.name, "content": content, "created_at": datetime.utcnow().isoformat()})
                        await self.publisher(task_id, {"type": "agent_status", "agent": agent.name, "status": "done"})
                    except Exception:
                        pass
            except Exception as e:
                # Publish failure and record error
                try:
                    if self.publisher and task_id is not None:
                        await self.publisher(task_id, {"type": "agent_status", "agent": agent.name, "status": "failed", "error": str(e)})
                except Exception:
                    pass
                async with lock:
                    results[agent.name] = str(e)

        # Spawn all agent tasks and wait for them to complete concurrently
        agent_tasks = [asyncio.create_task(run_agent(agent)) for agent in self.agent_manager.agents]
        # Wait for all agent tasks to finish; exceptions are handled per-agent
        await asyncio.gather(*agent_tasks)

        # Publish an overall task 'done' status so the server persists the Task.status
        try:
            if self.publisher and task_id is not None:
                try:
                    await self.publisher(task_id, {"type": "status", "status": "done"})
                except Exception:
                    # swallow publisher errors
                    pass
        except Exception:
            pass

        return results

    def submit_task(self, task):
        # Use asyncio to run the asynchronous handle_task function
        return asyncio.run(self.handle_task(task))

# Example usage of the framework
if __name__ == "__main__":
    mcp = MasterControlPanel()
    sample_task = {
        "title": "Defect in Pipeline Test Failure",
        "description": "CI pipeline shows failure in integration tests on branch feature-x.",
        "files": ["pipeline.py", "integration_tests.py"]
    }
    results = mcp.submit_task(sample_task)
    for agent, result in results.items():
        logging.info(f"{agent}: {result}")