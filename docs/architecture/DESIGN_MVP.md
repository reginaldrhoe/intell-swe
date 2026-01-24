# MVP Design Summary — Intelligent Orchestration Framework

Overview
- Purpose: Minimal intelligent orchestration framework that accepts task requests, runs agent workflows, persists task and activity state, and prevents duplicate concurrent executions across API and worker processes.
- Primary goals: reliable cross-process duplicate protection, deterministic observability for concurrency behavior, and an extensible agent execution pipeline supporting both in-process and durable worker backends.

Infrastructure & Deployment
- Containers & services: `mcp` (FastAPI backend), optional `worker` (Celery or in-memory), `redis` (locks + optional pub/sub + Celery broker), `qdrant` (vector store), and SQL persistence (MySQL/SQLite). Prometheus scrapes `/metrics`.
- Build model: `mcp` is built into an image during development; code changes require rebuilding the image. Use bind mounts for faster local iteration if desired.
- Env configuration: `REDIS_URL`, `CELERY_BROKER_URL`, `TASK_LOCK_TTL`, `TEST_HOLD_SECONDS`, `QDRANT_URL`, `OPENAI_API_KEY`, and RBAC tokens.

Core Components
- API / Orchestrator (`mcp`): FastAPI app exposing `/run-agents`, `/api/tasks`, `/events/tasks/{task_id}` (SSE), `/metrics`, and RAG endpoints (similarity search, config). Persists through SQLAlchemy models (`Task`, `Activity`, `Agent`).
- MasterControlPanel: orchestrates agents, executes pipeline, publishes events via a publisher callback for SSE and persistence.
- Task Queue: pluggable; Celery-backed for durable processing (when `CELERY_BROKER_URL` present) or an in-memory `TaskQueue` for local runs.
- Redis Lock Helper: `mcp/redis_lock.py` implements tokenized locks for both async (`redis.asyncio`) and sync (`redis-py`) clients, including safe release logic.
- Vector store & embeddings: Qdrant for vectors; embeddings via OpenAI when available with a deterministic fallback for repeatable tests.

Concurrency & Duplicate Protection
- Multi-layer protection:
  1. Up-front Redis existence check (`task:{id}:lock`) — fast conflict rejection (async get or sync get via executor).
  2. Redis tokenized lock acquisition — async preferred, sync fallback in thread executor. Locks carry a token and TTL to allow safe release.
  3. DB-level atomic UPDATE fallback — set `status='running'` only when the row is not already `running`; if update touches 0 rows, respond 409.
- Workers use the same lock semantics to ensure cross-process exclusivity.
- Release occurs in `finally` blocks; TTLs and DB fallback mitigate leaks. Consider lease renewal for long-running runs.

Observability & Testing Instrumentation
- Structured log markers: `RUN_AGENTS_DBG` entries at key decision points (payload receipt, up-front check, lock attempts, acquisition/release).
- Deterministic sentinels (file-based) for smoke tests inside container:
  - `/tmp/run_agents_entered.log` — handler entry (timestamp + id)
  - `/tmp/run_agents_lock_acquired.log` — lock acquired records (method, token length)
  - `/tmp/run_agents_lock_conflict.log` — lock conflict records (up-front or attempted acquisition)
  These are simple, robust signals for automated tests and CI (less affected by log buffering).
- Metrics: `TASKS_ENQUEUED`, `AGENT_RUNS`, `INGEST_COUNTER` exposed at `/metrics` for Prometheus.

Failure Modes & Hardening
- Race window: up-front check is helpful but not sufficient; tokenized lock + DB atomic update close races.
- Redis unavailability: fallback to DB atomic update; lock helper tolerates missing async client by using a sync client in an executor.
- Lock leaks: mitigated via TTL; for long-running tasks add heartbeat/lease renewal.
- Developer iteration: because the code is copied into `mcp` image at build, frequent rebuilds slow feedback; recommend bind mounts for active dev.

Developer UX & CI
- Smoke tests: concurrent POSTs with `TEST_HOLD_SECONDS` can force deterministic conflict; tests read sentinel files to verify one `LOCK_ACQUIRED` and one `LOCK_CONFLICT` outcome.
- Local runs: in-memory `TaskQueue` enables running end-to-end without Celery.
- Determinism: deterministic embedding fallback allows reproducible similarity tests without external API keys.

Security & Operations
- RBAC: sample `agents/rbac.json` for local dev; production should use secure secrets and proper OAuth/JWT flows.
- Secrets: keep keys in `.env` or Docker secrets / vault in production.
- Lock safety: tokenized locks ensure only token-holder releases; TTL prevents permanent lock hold by crashed processes.

Extensibility & Next-Phase Features
- Lease/heartbeat for long-running tasks.
- Centralized Redis pub/sub for cross-instance SSE and coordination.
- Structured JSON logging and correlation IDs (`task_id`) for traceability.
- CI: add a job that builds `mcp`, runs sentinel-based smoke tests in Docker Compose, and asserts sentinel outputs.

Minimal Recommended Next Steps (priority order)
1. Stabilize and run sentinel smoke test with `TEST_HOLD_SECONDS=30` and assert sentinels show one acquired + one conflict.
2. Add lease renewal/heartbeat for long runs to avoid TTL races.
3. Move logs to structured JSON and include a `task_id` correlation field.
4. Add CI job to build `mcp` and run smoke tests; assert sentinel files.
5. Harden production deployment: use Docker secrets, add health checks and alerting on Redis or repeated 409s.

Suggested Diagrams
- Deployment diagram (containers and networked services).
- Component diagram (API, MasterControlPanel, Redis lock, worker, Qdrant, DB).
- Sequence diagram for `/run-agents` showing up-front check, lock acquisition (async/sync), DB fallback, worker processing, and release.

Contact
For further changes, edit `docs/DESIGN_MVP.md` or ask me to produce the CI smoke-test script and diagram SVG.
