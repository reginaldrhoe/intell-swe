# Release Notes

Generated: 2025-11-23T21:20:14.597578Z
## v2.0.0 — 2025-11-25

### Breaking/Defaults
- Default to Live mode for LLM calls: `OPENAI_API_BASE` now points to `https://api.openai.com/v1` for `mcp`, `worker`, and `openwebui` in `docker-compose.yml`.
- Set `TEST_HOLD_SECONDS=0` by default to avoid artificial delays outside of tests.

### Features
- Add `docker-compose.override.mock.yml` to easily flip into full Mock mode (no external API calls). In Mock mode, `openai-mock` is started and `TEST_HOLD_SECONDS` is increased to `10` for deterministic lock/sentinel testing.
- Add `e2e-mock` job to CI (`.github/workflows/lock_smoke_test.yml`) that runs after the lock smoke test and validates ingestion→retrieval via `/similarity-search` with the OpenAI mock.
- Add artifact upload for E2E job: captures `e2e_output.txt` and container logs (`mcp.log`, `worker.log`, `qdrant.log`, `openai-mock.log`).

### Docs
- README: Add “E2E test (mock mode)” and “Switch Mock ↔ Live” sections with copy-paste commands for local dev and CI context.

### Internal
- Package version bumped to `2.0.0` in `setup.py`.

### Upgrade Notes
- To remain in mock mode for local testing: use `docker compose -f docker-compose.yml -f docker-compose.override.mock.yml up -d --build`.
- To run live mode: set `OPENAI_API_KEY` in `.env` and use standard `docker compose up -d --build`.

## v1.0.0 — 2025-11-23

### Ci
- ci: add workflow_dispatch input for QDRANT_FORCE_CLIENT (
841f5196) — reginaldrhoe

### Other
- Merge pull request #2 from reginaldrhoe/ci/dispatch-qdrant (dc5bbe32) — Reginald Rhoe

### Frontend
- Add Vite + React frontend scaffold (`web/`) with a minimal SPA for the MVP: `AgentTaskForm` component, login buttons, and API integration. The app captures OAuth `#access_token` fragments and stores a bearer token in `localStorage` for dev testing.
- Added runtime-configurable API base and token inputs in the app so the UI can target a local or remote backend easily (`localStorage` keys: `ragpoc_api_base`, `ragpoc_token`).
- Added `web/src/styles.css` and React entry (`web/src/main.jsx`, `web/src/App.jsx`) and simple login helper (`web/src/LoginButton.jsx`).
- Added GitHub Pages demo copy at `docs/index.html` (standalone static form) with configurable API base and token support for publishing quick demos.
- Wire-up notes: CORS middleware and backend health endpoint were added/adjusted so the frontend can talk to the `mcp` API during local development (backend default mapping `http://localhost:8001`).
