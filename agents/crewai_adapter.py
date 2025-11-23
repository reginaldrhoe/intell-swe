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
import logging

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
        # Model name can be configured with CREWAI_MODEL
        self.model = model or os.getenv("CREWAI_MODEL") or "gpt-4o-mini"
        # Support explicit API key wiring for crewai client
        self.api_key = os.getenv("CREWAI_API_KEY")
        self.logger = logging.getLogger("crewai_adapter")

    async def run(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Run the prompt through CrewAI or a fallback.

        This method ensures any blocking client calls run in a thread so the
        FastAPI event loop is not blocked. Returns a dict containing at least
        the key `text`.
        """
        # 1) Try native crewai integration (if installed)
        if crewai is not None:
            try:
                def _call_crewai():
                    if hasattr(crewai, "Client"):
                        client = crewai.Client(api_key=self.api_key) if self.api_key else crewai.Client()
                    else:
                        client = crewai

                    if hasattr(client, "completions"):
                        return client.completions.create(model=self.model, prompt=prompt, **kwargs)
                    if hasattr(client, "responses"):
                        return client.responses.create(model=self.model, input=prompt, **kwargs)
                    return client.create(model=self.model, prompt=prompt, **kwargs)

                resp = await asyncio.to_thread(_call_crewai)
                # Extract textual content robustly
                text = None
                if isinstance(resp, dict):
                    text = resp.get("text") or resp.get("content") or str(resp)
                else:
                    text = getattr(resp, "text", None) or getattr(resp, "content", None) or str(resp)
                return {"text": text}
            except Exception as e:
                self.logger.exception("CrewAI client failed, falling back: %s", e)

        # 2) Try OpenAI v1 client if available and API key present
        if os.getenv("OPENAI_API_KEY") and OpenAIClient is not None:
            try:
                def _call_openai():
                    client = OpenAIClient()
                    # Use the Responses API if present
                    if hasattr(client, "responses"):
                        return client.responses.create(model=self.model, input=prompt)
                    # Fallback to older completions/chat APIs
                    if hasattr(client, "completions"):
                        return client.completions.create(model=self.model, prompt=prompt)
                    return client.create(model=self.model, prompt=prompt)

                resp = await asyncio.to_thread(_call_openai)
                # Attempt to extract content
                text = None
                if hasattr(resp, "output"):
                    out = resp.output
                    if isinstance(out, list) and len(out) > 0:
                        # Try common shapes
                        first = out[0]
                        if isinstance(first, dict):
                            text = first.get("content") or first.get("text")
                        else:
                            text = str(first)
                if text is None:
                    text = getattr(resp, "text", None) or str(resp)
                return {"text": text}
            except Exception as e:
                self.logger.exception("OpenAI client failed as fallback: %s", e)

        # 3) Deterministic fallback: echo prompt summary
        return {"text": f"[stub] {prompt[:500]}"}
