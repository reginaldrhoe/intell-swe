from agents.core.crewai_adapter import CrewAIAdapter
from agents.core.agents import Agent


class RootCauseInvestigatorCrewAI(Agent):
    def __init__(self, name: str = "RootCauseCrewAI"):
        super().__init__(name)
        self.adapter = CrewAIAdapter()

    async def process(self, task):
        art_sum = task.get('artifact_summary')
        art_block = ("\n\n=== Attached Test Artifacts Summary ===\n" + str(art_sum)) if art_sum else ""
        grounding = ("Ground findings in the artifacts summary when present. "
                     "If data is missing, say 'not available from artifacts'.")
        prompt = (
            f"You are an expert at root cause analysis. Given the following task and context,"
            f" identify likely root causes and suggest diagnostic steps.\nTask: {task.get('title')}\n"
            f"Details: {task.get('description')}\nFiles: {task.get('files')}" + art_block + "\n" + grounding + "\n"
            f"Provide a concise list of potential root causes and 5 diagnostics."
        )
        res = await self.adapter.run(prompt)
        return {"agent": self.name, "result": res.get("text")}
