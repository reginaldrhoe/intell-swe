from .crewai_adapter import CrewAIAdapter
from .agents import Agent


class DefectDiscoveryCrewAI(Agent):
    def __init__(self, name: str = "DiscoveryCrewAI"):
        super().__init__(name)
        self.adapter = CrewAIAdapter()

    async def process(self, task):
        art_sum = task.get('artifact_summary')
        art_block = ("\n\n=== Attached Test Artifacts Summary ===\n" + str(art_sum)) if art_sum else ""
        grounding = ("Use the artifacts summary for defect patterns and frequencies; "
                     "avoid hypothetical examples not supported by the summary.")
        prompt = (
            "You are an analytics expert. Analyze the provided CI/test logs and repo context to detect patterns\n"
            f"Task: {task.get('title')}\nDetails: {task.get('description')}\nFiles: {task.get('files')}" + art_block + "\n" + grounding + "\n"
            "Return detected defect patterns, frequency, and suggested mitigations."
        )
        res = await self.adapter.run(prompt)
        return {"agent": self.name, "result": res.get("text")}
