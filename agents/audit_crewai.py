from .crewai_adapter import CrewAIAdapter
from .agents import Agent


class AuditCrewAI(Agent):
    def __init__(self, name: str = "AuditCrewAI"):
        super().__init__(name)
        self.adapter = CrewAIAdapter()

    async def process(self, task):
        prompt = (
            "You are an audit compliance expert. Check the task context for compliance gaps,"
            f" required artifacts, and suggest remediation steps.\nTask: {task.get('title')}\n"
            f"Details: {task.get('description')}\nFiles: {task.get('files')}\nReturn findings and priorities."
        )
        res = await self.adapter.run(prompt)
        return {"agent": self.name, "result": res.get("text")}
