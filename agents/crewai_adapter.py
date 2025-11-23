"""Lightweight adapter for CrewAI (or fallback to OpenAI / stub).

This adapter exposes a simple interface `CrewAIAdapter.run(prompt, **kwargs)`
which returns a dict with a `text` field. It will attempt to import the
`crewai` package; if not present it will fall back to using OpenAI's
completion via `openai.OpenAI` when `OPENAI_API_KEY` is set. Otherwise a
deterministic stub is used for offline tests.
"""
from typing import Any, Dict, Optional
import os
import asyncio

try:
    import crewai  # type: ignore
except Exception:
    crewai = None

try:
    from openai import OpenAI as OpenAIClient  # type: ignore
except Exception:
    OpenAIClient = None


class CrewAIAdapter:
    def __init__(self, model: Optional[str] = None):
        self.model = model or os.getenv("CREWAI_MODEL") or "gpt-4o-mini"

    async def run(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Run the prompt through CrewAI or a fallback.

        Returns a dict containing at least the key `text`.
        """
        # Try native crewai integration
        if crewai is not None:
            try:
                client = crewai.Client() if hasattr(crewai, "Client") else crewai
                resp = client.completions.create(model=self.model, prompt=prompt, **kwargs)
                text = getattr(resp, "text", None) or getattr(resp, "content", None) or str(resp)
                return {"text": text}
            except Exception:
                # fall through to openai
                pass

        # Try OpenAI v1 client if available
        if os.getenv("OPENAI_API_KEY") and OpenAIClient is not None:
            try:
                client = OpenAIClient()
                # Use a lightweight chat completion if available
                resp = client.responses.create(model=self.model, input=prompt)
                # Attempt to extract content
                text = None
                if hasattr(resp, "output"):
                    # new responses API may have output
                    out = resp.output
                    if isinstance(out, list) and len(out) > 0:
                        text = out[0].get("content") if isinstance(out[0], dict) else str(out[0])
                if text is None:
                    text = getattr(resp, "text", None) or str(resp)
                return {"text": text}
            except Exception:
                pass

        # Deterministic fallback: echo prompt summary
        return {"text": f"[stub] {prompt[:500]}"}
