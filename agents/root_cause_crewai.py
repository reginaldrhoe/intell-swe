from .crewai_adapter import CrewAIAdapter
from .agents import Agent


class RootCauseInvestigatorCrewAI(Agent):
    def __init__(self, name: str = "RootCauseCrewAI"):
        super().__init__(name)
        self.adapter = CrewAIAdapter()

    async def process(self, task):
        prompt = (
            f"You are an expert at root cause analysis. Given the following task and context,"
            f" identify likely root causes and suggest diagnostic steps.\nTask: {task.get('title')}\n"
            f"Details: {task.get('description')}\nFiles: {task.get('files')}\nProvide a concise list of potential root causes and 5 diagnostics."
        )
        res = await self.adapter.run(prompt)
        return {"agent": self.name, "result": res.get("text")}
