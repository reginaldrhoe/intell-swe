"""Run a standalone mock OpenAI server on port 1573.

Usage:
  python scripts/run_openai_mock.py

The server exposes v1 endpoints compatible with common OpenAI HTTP usages:
  - POST /v1/chat/completions
  - POST /v1/completions
  - POST /v1/embeddings

Start this in CI or locally when your frontend or app expects a local OpenAI-compatible endpoint.
"""
import uvicorn
from mcp.openai_mock import app


def main():
    uvicorn.run(app, host='0.0.0.0', port=1573, log_level='info')


if __name__ == '__main__':
    main()
