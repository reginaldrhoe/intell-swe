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
    # Check if this is the in-repo stub shim - if so, ignore it and use OpenAI
    if hasattr(crewai, '__file__') and '/app/crewai' in crewai.__file__:
        print(f"[ADAPTER DEBUG] Detected in-repo crewai shim at {crewai.__file__}, skipping to use OpenAI")
        crewai = None
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
        # Default temperature can be overridden via env
        try:
            self.default_temperature = float(os.getenv("OPENAI_DEFAULT_TEMPERATURE", "0.2"))
        except Exception:
            self.default_temperature = 0.2
        # System grounding prompt (can be overridden via env)
        self.system_grounding = os.getenv(
            "ADAPTER_SYSTEM_GROUNDING",
            (
                "Always produce strictly factual outputs grounded in the provided context. "
                "If the prompt includes 'Attached Test Artifacts Summary', base all quantitative statements on it. "
                "If information is missing, explicitly state 'not available from artifacts' or 'resource not provided'. "
                "Do not invent test names, counts, coverage, metrics, or repository details. "
                "When critical resources are missing, request them succinctly (e.g., 'Please provide junit.xml or coverage.xml'). "
                "Prefer concise, verifiable outputs and avoid hypotheticals."
            ),
        )

    async def run(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Run the prompt through CrewAI or a fallback.

        This method ensures any blocking client calls run in a thread so the
        FastAPI event loop is not blocked. Returns a dict containing at least
        the key `text`.
        """
        print(f"[ADAPTER DEBUG] CrewAIAdapter.run called, prompt length: {len(prompt)}")
        self.logger.info("CrewAIAdapter.run called, prompt length: %d", len(prompt))
        
        # 1) Try native crewai integration (if installed)
        if crewai is not None:
            print(f"[ADAPTER DEBUG] Attempting CrewAI native client")
            self.logger.info("Attempting CrewAI native client")
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
        print(f"[ADAPTER DEBUG] Checking OpenAI: has_key={bool(os.getenv('OPENAI_API_KEY'))}, has_client={OpenAIClient is not None}")
        if os.getenv("OPENAI_API_KEY") and OpenAIClient is not None:
            print(f"[ADAPTER DEBUG] Attempting OpenAI client fallback")
            self.logger.info("Attempting OpenAI client fallback")
            try:
                def _call_openai():
                    self.logger.info("Creating OpenAI client...")
                    client = OpenAIClient()
                    self.logger.info("Calling chat.completions.create with model: %s", self.model)
                    # Use chat completions API (modern OpenAI API)
                    messages = []
                    # Always include a grounding system message to reduce hallucinations
                    messages.append({"role": "system", "content": self.system_grounding})
                    messages.append({"role": "user", "content": prompt})
                    response = client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        max_tokens=kwargs.get("max_tokens", 2000),
                        temperature=kwargs.get("temperature", self.default_temperature),
                    )
                    self.logger.info("OpenAI response received, content length: %d", len(response.choices[0].message.content))
                    return response.choices[0].message.content

                text = await asyncio.to_thread(_call_openai)
                self.logger.info("OpenAI call successful, returning text")
                return {"text": text}
            except Exception as e:
                self.logger.exception("OpenAI client failed as fallback: %s", e)

        # 3) Deterministic fallback: echo prompt summary
        self.logger.warning("Falling back to stub mode")
        return {"text": f"[stub] {prompt[:500]}"}
