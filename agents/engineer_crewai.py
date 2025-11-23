from .crewai_adapter import CrewAIAdapter
from .agents import Agent
import asyncio


class EngineerCodeReviewCrewAI(Agent):
    """Engineer code review agent backed by CrewAIAdapter.

    The agent builds a concise prompt from the task and asks CrewAI to
    produce a review summary and suggested fixes.
    """
    def __init__(self, name: str = "EngineerCrewAI"):
        super().__init__(name)
        self.adapter = CrewAIAdapter()

    async def process(self, task):
        title = task.get("title", "Code review")
        desc = task.get("description", "")
        files = task.get("files", [])
        prompt = (
            f"You are an expert Python engineer. Perform a lightweight code review for: {title}\n"
            f"Description: {desc}\n"
            f"Files: {files}\n"
            "Give a short summary of potential defects and 3 concrete suggestions to fix them."
        )
        # Delegate to adapter
        res = await self.adapter.run(prompt)
        # Ensure a string return
        text = res.get("text") if isinstance(res, dict) else str(res)
        return {"agent": self.name, "result": text}
