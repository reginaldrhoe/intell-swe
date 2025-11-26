from .crewai_adapter import CrewAIAdapter
from .agents import Agent
import asyncio
import os
import hashlib

try:
    from qdrant_client import QdrantClient
except Exception:
    QdrantClient = None


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
        # If no explicit files were provided, try to query the RAG/Qdrant
        # collection for relevant chunks and include them in the prompt.
        if not files:
            try:
                collection = (os.getenv("RAG_COLLECTION") or "rag-poc")
                qurl = os.getenv("QDRANT_URL") or "http://qdrant:6333"
                if QdrantClient is not None:
                    client = QdrantClient(url=qurl)
                    # craft a simple query vector using a deterministic embedding
                    query_text = f"{title}\n{desc}"
                    def _deterministic_embed(text, dim=64):
                        h = hashlib.sha256(text.encode("utf-8")).digest()
                        reps = (dim + len(h) - 1) // len(h)
                        data = (h * reps)[:dim]
                        vec = [((b / 255.0) * 2.0 - 1.0) for b in data]
                        # normalize
                        import math
                        norm = math.sqrt(sum(v * v for v in vec))
                        if norm > 0:
                            vec = [v / norm for v in vec]
                        return vec

                    qvec = _deterministic_embed(query_text, dim=int(os.getenv("RAG_EMBED_DIM", "64")))
                    try:
                        hits = client.search(collection_name=collection, query_vector=qvec, limit=5)
                        files = []
                        for h in hits:
                            payload = h.payload or {}
                            src = payload.get("path") or payload.get("source") or payload.get("ingested_from")
                            snippet = (payload.get("page_content") or "").strip().replace("\n", " ")[:800]
                            files.append(f"{src}: {snippet}")
                    except Exception:
                        # fall back to empty files list if qdrant search fails
                        files = []
            except Exception:
                files = []
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
