from .crewai_adapter import CrewAIAdapter
from .agents import Agent


class PerformanceMetricsCrewAI(Agent):
    def __init__(self, name: str = "PerfMetricsCrewAI"):
        super().__init__(name)
        self.adapter = CrewAIAdapter()

    async def process(self, task):
        art_sum = task.get('artifact_summary')
        art_block = ("\n\n=== Attached Test Artifacts Summary ===\n" + str(art_sum)) if art_sum else ""
        grounding = ("Use the artifact summary data (pass/fail counts, coverage) when present; "
                     "do not fabricate metrics.")
        prompt = (
            "You are a performance engineer. Given the task context, summarize performance implications,"
            f" identify metrics to monitor, and suggest thresholds/alerts.\nTask: {task.get('title')}\n"
            f"Details: {task.get('description')}\nFiles: {task.get('files')}" + art_block + "\n" + grounding + "\n"
            "Return items as bullet list."
        )
        res = await self.adapter.run(prompt)
        return {"agent": self.name, "result": res.get("text")}
