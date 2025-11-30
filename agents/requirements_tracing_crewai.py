from .crewai_adapter import CrewAIAdapter
from .agents import Agent


class RequirementsTracingCrewAI(Agent):
    def __init__(self, name: str = "RequirementsCrewAI"):
        super().__init__(name)
        self.adapter = CrewAIAdapter()

    async def process(self, task):
        art_sum = task.get('artifact_summary')
        art_block = ("\n\n=== Attached Test Artifacts Summary ===\n" + str(art_sum)) if art_sum else ""
        grounding = ("Base trace links on the artifacts summary where applicable; "
                     "call out unavailable mappings explicitly.")
        prompt = (
            "You are a requirements tracing expert. Given the task and available artifacts,\n"
            f"link requirements to tests and code areas and flag missing traceability.\nTask: {task.get('title')}\n"
            f"Details: {task.get('description')}\nFiles: {task.get('files')}" + art_block + "\n" + grounding + "\n"
            "Provide a mapping and any gaps."
        )
        res = await self.adapter.run(prompt)
        return {"agent": self.name, "result": res.get("text")}
