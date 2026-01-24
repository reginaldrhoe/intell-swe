from agents.core.crewai_adapter import CrewAIAdapter
from agents.core.agents import Agent


class AuditCrewAI(Agent):
    def __init__(self, name: str = "AuditCrewAI"):
        super().__init__(name)
        self.adapter = CrewAIAdapter()

    async def process(self, task):
        art_sum = task.get('artifact_summary')
        art_block = ("\n\n=== Attached Test Artifacts Summary ===\n" + str(art_sum)) if art_sum else ""
        grounding = ("Ground compliance findings in the provided artifacts summary; "
                     "do not assume artifacts that are not listed.")
        prompt = (
            "You are an audit compliance expert. Check the task context for compliance gaps,"
            f" required artifacts, and suggest remediation steps.\nTask: {task.get('title')}\n"
            f"Details: {task.get('description')}\nFiles: {task.get('files')}" + art_block + "\n" + grounding + "\n"
            "Return findings and priorities."
        )
        res = await self.adapter.run(prompt)
        return {"agent": self.name, "result": res.get("text")}
