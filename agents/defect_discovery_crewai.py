from .crewai_adapter import CrewAIAdapter
from .agents import Agent


class DefectDiscoveryCrewAI(Agent):
    def __init__(self, name: str = "DiscoveryCrewAI"):
        super().__init__(name)
        self.adapter = CrewAIAdapter()

    async def process(self, task):
        prompt = (
            "You are an analytics expert. Analyze the provided CI/test logs and repo context to detect patterns\n"
            f"Task: {task.get('title')}\nDetails: {task.get('description')}\nFiles: {task.get('files')}\n"
            "Return detected defect patterns, frequency, and suggested mitigations."
        )
        res = await self.adapter.run(prompt)
        return {"agent": self.name, "result": res.get("text")}
