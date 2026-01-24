# Test Coverage — rag-poc (MVP v2.3.0)

<img src="../docs/Logo%20design%20featurin.png" alt="Logo" width="200">

Scope
- Summarizes available tests, demos, and instrumentation across RBAC, distributed locks, CI scaffolds, multi-agent coordination, and delegation.

## RBAC
- Components: tokenized role checks; sample `agents/rbac.json`; protected admin endpoints.
- Endpoints: `POST /admin/ingest` requires `editor` token; other protected routes use bearer `Authorization`.
- Coverage:
  - API call-level validation via smoke/E2E scripts (manual and CI scaffold).
  - No dedicated unit test suite for fine-grained RBAC yet.
- Status: functional for dev/test; production to adopt OAuth/JWT.

## Distributed Locks
- Components: Redis tokenized locks with TTL; DB atomic update fallback.
- Endpoints/Paths: `POST /run-agents`, `mcp/redis_lock.py`.
- Instrumentation: sentinel files inside `mcp` container (`/tmp/run_agents_*`).
- Coverage:
  - `scripts/run_lock_smoke.ps1` exercises duplicate protection; asserts one acquire + one conflict.
  - Metrics observable via `/metrics` (Prometheus) and sentinel logs.
- Status: stable; lease/heartbeat renewal planned.

## CI Integration
- Components: E2E script (`scripts/run_e2e_integration.py`), UI scaffold (`tests/ui/test_ui_agent_flow.py`), OpenAI mock (`mcp/openai_mock.py`, `scripts/run_openai_mock.py`).
- Coverage:
  - E2E (mock/real) verifies ingest → vectorize → agent retrieval.
  - UI scaffold checks basic agent flow rendering.
  - Pytest coverage artifacts: `--cov --cov-report=xml:artifacts/coverage.xml`.
- Status: partial wiring documented; workflows suggested but not standardized.

## Multi-Agent Coordination (Parallel)
- Components: `agents/agents.py` uses `asyncio.create_task` + `gather`.
- Instrumentation (added): per-agent start/end/duration; coordination metrics appended to results as `__coordination_metrics__` and emitted via `agents_metrics` publisher event.
- Demo Reproduction:
```powershell
python - <<'PY'
from agents.agents import MasterControlPanel
import json
mcp = MasterControlPanel()
res = mcp.submit_task({"id": 123, "title": "Concurrency verification", "description": "Collect metrics"})
print(json.dumps(res["__coordination_metrics__"], indent=2))
PY
```
- Sample Metrics:
  - `wall_time` ≈ 3.09s, `sum_agent_durations` ≈ 3.11s, `parallel_efficiency_ratio` ≈ 1.00, `overlap_time` > 0 — confirms concurrent execution.
- Status: instrumented and demonstrated.

## Agent Delegation Demo
- Script: `scripts/run_agent_delegation_demo.py`.
- Pattern: phased execution with evidence flow — Engineer → (RootCause, Discovery) → (Requirements, Metrics, Audit).
- Run:
```powershell
python scripts\run_agent_delegation_demo.py
```
- Output: structured JSON report including per-phase results and `delegation` provenance (from/to, context_keys).
- Status: added and verified.

## Next Coverage Improvements
- RBAC: add unit tests for role resolution and denied/allowed paths.
- Locks: add heartbeat/lease renewal tests for long-running tasks.
- CI: standardize GitHub Actions jobs for smoke, E2E, UI; artifact upload; optional PDF regeneration.
- Metrics: export `agent_duration_seconds{agent=...}` and `delegation_phase_seconds{phase=...}` to Prometheus.
