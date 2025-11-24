# Release Notes

Generated: 2025-11-23T21:20:14.597578Z
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
