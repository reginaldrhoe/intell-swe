# Operation Manual — intell-swe v3.0.0 (Enterprise Multiuser Framework)

**Version**: 3.0 (Updated Jan 2026)  
**Last Updated**: 2026-01-27

## Table of Contents

1. [LLM Setup & Configuration](#1-llm-setup--configuration)
2. [Deployment Instructions](#2-deployment-instructions)
3. [Multiuser Architecture](#3-multiuser-architecture)
4. [Authentication & Authorization](#4-authentication--authorization)
5. [Operational Workflow](#5-operational-workflow)

---

## 1. LLM Setup & Configuration

### Overview

This enterprise framework supports two LLM providers:
- **OpenAI** (production-recommended)
- **Claude/Anthropic** (alternative, excellent for code analysis)

For comprehensive setup instructions, see [docs/LLM_SETUP_GUIDE.md](../LLM_SETUP_GUIDE.md).

### Quick Setup

**Option A: OpenAI**
```env
OPENAI_API_KEY=sk-proj-YOUR_KEY_HERE
CREWAI_MODEL=gpt-4o-mini
```

**Option B: Claude/Anthropic**
```env
ANTHROPIC_API_KEY=sk-ant-YOUR_KEY_HERE
CREWAI_MODEL=claude-3-5-sonnet-20241022
CREWAI_PROVIDER=anthropic
```

The system **auto-detects** which provider to use from available API keys.

### CrewAI Agent Framework

Intel-SWE uses **CrewAI** for intelligent multi-agent task orchestration:

- **Multi-agent workflows**: Agents collaborate to perform complex analysis
- **LLM flexibility**: Works with both OpenAI and Anthropic models
- **Graceful fallback**: If CrewAI not installed, uses direct LLM API calls
- **Auto-detection**: Provider selected based on `.env` API keys

**Environment variables for CrewAI**:
- `CREWAI_MODEL` - Model name (e.g., `gpt-4o-mini`, `claude-3-5-sonnet-20241022`)
- `CREWAI_PROVIDER` - Override provider if both keys are set (`openai` or `anthropic`)
- `CREWAI_API_KEY` - Optional; for CrewAI cloud credentials only

**Setup checklist**:
- [ ] Set `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` in `.env`
- [ ] (Optional) Set `CREWAI_MODEL` for specific model selection
- [ ] (Optional) Install CrewAI: `pip install crewai>=0.1.0`
- [ ] Verify agents load: `python -c "from agents.core.crewai_adapter import CrewAIAdapter; print('✓ CrewAI configured')"`

For detailed agent types and capabilities, see [docs/manuals/AGENT_ENHANCEMENTS.md](AGENT_ENHANCEMENTS.md).

---

## 2. Deployment Instructions

### 2.1 Local Development

```powershell
# 1. Clone repository
git clone https://github.com/yourusername/intell-swe.git
cd intell-swe

# 2. Create .env with LLM configuration
# (see section 1 above or docs/LLM_SETUP_GUIDE.md)

# 3. Start services
docker compose build mcp worker
docker compose up -d postgres redis qdrant mcp worker

# 4. Access application
# Web UI: http://localhost:5173
# API: http://localhost:8001
```

### 2.2 Production Deployment (Kubernetes)

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: intell-swe-llm-keys
type: Opaque
stringData:
  OPENAI_API_KEY: sk-proj-...  # Choose ONE provider
  # ANTHROPIC_API_KEY: sk-ant-...
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: intell-swe-mcp
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: mcp
        image: your-registry/intell-swe-mcp:v3.0.0
        envFrom:
        - secretRef:
            name: intell-swe-llm-keys
        env:
        - name: CREWAI_MODEL
          value: "gpt-4o-mini"
        - name: QDRANT_URL
          value: "http://qdrant:6333"
```

Deploy:
```bash
kubectl apply -f deployment.yaml
kubectl rollout status deployment/intell-swe-mcp
```

---

## 3. Multiuser Architecture

Scope
- This document describes the v3.0.0 multiuser architecture, operational workflows for running and monitoring agent runs with per-user isolation, GitLab OAuth authentication, admin capabilities, and step-by-step instructions for testing and deployment.

Audience
- Platform administrators configuring multiuser deployments, developers operating local dev environments, and SREs managing production clusters with PostgreSQL and GitLab OAuth integration.

---

## 4. User Interface (v3.0.0 Multiuser)

### Authentication & Authorization
- **GitLab OAuth**: Users authenticate via GitLab SSO
- **Role-Based Access**: Users see only their tasks; admins see all tasks
- **Session Management**: Bearer tokens with secure server-side validation
- **User Context**: All API requests include authenticated user identity

### Tasks List (`GET /api/tasks`)
- Displays persisted `Task` records filtered by `user_id` (automatic)
- Admin users can view `/admin/tasks` to see organization-wide tasks
- Typical actions: create new task (POST to `/api/tasks` via UI or API), view details, trigger run
- Task metadata includes: `user_id`, `repo_ref`, `branch`, `logo_url`, timestamps

### Task Detail / Run UI
- Shows task metadata (title, description, status, owner) and timeline of `Activity` events
- A `Run` button triggers a `POST /run-agents` request with user context
- Real-time updates via user-scoped SSE channel: `tasks:{user_id}:{task_id}`
- Status updates reflect `running`/`failed`/`done` states with per-user notification

### Jobs / Worker View
- Displays worker (Celery) status: queued tasks by user, currently running jobs, recent failures
- Admin view shows cross-user metrics and resource utilization
- Per-user task isolation ensures workers process tasks with correct user context

### Real-time Updates (SSE)
- User-scoped SSE connection to `GET /events/tasks/{task_id}` (auto-filtered by user_id)
- Events include: agent activity, status updates, structured progress messages
- Admin users can subscribe to organization-wide event streams

## 2. AI-Assisted Coding and Enterprise Intelligent Frameworks

AI-assisted coding has evolved from IDE plugins to **enterprise-scale intelligent frameworks** that support multiuser collaboration, secure repository access, and organization-wide code intelligence. Platforms like **intell-swe v3.0.0** represent this next generation by combining AI-powered analysis with role-based access control, per-user task isolation, and production-grade authentication. These frameworks integrate seamlessly with enterprise identity providers (GitLab OAuth), enforce security policies at the API layer, and provide centralized monitoring through tools like Prometheus. The shift from single-user IDE assistants to multiuser frameworks enables organizations to standardize code analysis, maintain audit trails, and scale AI capabilities across development teams while ensuring data privacy and compliance.

**The Intelligent Framework Advantage: Beyond Single-Context AI**

While traditional AI coding assistants excel at generating code from current context, this intelligent framework represents a significant architectural evolution by implementing **multi-source Retrieval-Augmented Generation (RAG)** that combines temporal, semantic, and analytical intelligence:

**Temporal Intelligence via Git Integration**
- Traditional assistants analyze only the *current state* of code; this framework understands *code evolution over time*
- Answers critical questions standard AI cannot: "When was this bug introduced?", "Who changed the authentication logic?", "What was modified in the last merge?"
- Provides cryptographically verified commit history with author attribution, timestamps, and exact diffs—not interpretations

**Semantic Intelligence via Qdrant Vector Database**
- While IDE assistants search within open files, this framework performs **cross-codebase semantic search** across the entire repository
- Discovers conceptually similar code patterns even when variable names differ
- Enables natural language queries like "Find all error handling patterns" without knowing specific file locations
- Ranks results by relevance, surfacing the most applicable code examples

**Change-Aware Analysis**
- Standard AI tools suggest code based on patterns; this framework explains *why code changed* by analyzing commit messages and diffs
- Performs impact assessment: "What else was modified when the API changed?" 
- Traces code lineage: "How did this function evolve from version 1.0 to 2.0?"
- Provides root cause analysis for incidents by examining the exact changes that introduced issues

**Multi-Dimensional Context for LLM Reasoning**
- GitHub Copilot receives context from your current file; this framework provides the LLM with three perspectives simultaneously:
  1. **Git metadata**: When/who/why changes occurred (temporal context)
  2. **Qdrant search results**: Related code across the codebase (semantic context)  
  3. **Current code state**: Files and functions being analyzed (static context)
- Results in 8x more answerable question types with dramatically richer analysis

**Intelligent Source Selection**
The framework implements a 3-tier fallback strategy that adapts to query types:
- **Tier 1 (Git Tools)**: When analyzing specific commits, branches, or time periods
- **Tier 2 (Qdrant RAG)**: When finding similar patterns or performing semantic searches
- **Tier 3 (Explicit Files)**: When user specifies exact files to analyze

**Real-World Comparison**

*Traditional AI Assistant Query*: "Explain this authentication code"
- **Response**: Describes the current implementation based on visible code
- **Limitation**: No awareness of *when* it was added, *why* it was designed this way, or *what changed recently*

*Intelligent Framework Query*: "What is the root cause of commit 37c2ed14?"
- **Git Analysis**: "Merged ci/dispatch-qdrant branch on Nov 26, 2025 by reginaldrhoe. Added E2E CI tests with mock OpenAI. Files changed: lock_smoke_test.yml (+70 lines), openai_mock.py (+41 lines)"
- **Qdrant Context**: "Found similar testing patterns in test_crewai_adapter.py using mock implementations"
- **LLM Synthesis**: "The root cause was the need for CI testing without external API dependencies. The mock service enables deterministic offline testing following established patterns in the codebase."

**Architectural Advantages for Software Engineering**

1. **Compliance & Audit**: Verifiable change history with author attribution and timestamps
2. **Onboarding**: New developers can ask "What changed in the auth module recently?" and get temporal analysis
3. **Code Review Automation**: Analyzes diffs with context from related historical changes
4. **Refactoring Safety**: Identifies similar code patterns that need updating across the codebase
5. **Incident Response**: Pinpoints exactly when and why bugs were introduced with commit-level precision
6. **Knowledge Preservation**: Captures the "why" behind changes through commit messages, not just the "what"

This multi-source architecture transforms AI from a code completion tool into a **comprehensive engineering intelligence platform** that understands not just *how* code works, but *why* it exists, *when* it changed, and *who* contributed—context essential for professional software development at scale.

For detailed architectural analysis, see `docs/ARCHITECTURE_ANALYSIS.md`.

---

3. Operational Workflow

This section documents the common sequence an operator or dev follows to run a task and monitor progress.

### Container Requirements (Summary)

For agent runs, SQL is required. Ensure the following containers are running:

- Required:
  - `mysql` — persistent SQL store backing tasks and activities (required for agents)
  - `mcp` — FastAPI backend
  - `worker` — Celery worker for agent execution
  - `redis` — broker/locks
  - `qdrant` — vector DB

- Optional:
  - `frontend` — containerized UI at `http://localhost:3000` (devs may use Vite UI at `http://localhost:5173` outside Docker)
  - `openai-mock` — local OpenAI-compatible mock service
  - `prometheus` — metrics scraping

Quick checks (PowerShell):
```powershell
docker compose ps
docker compose ps mysql
Select-String -Path .env -Pattern '^DATABASE_URL'
```

1) Prepare environment
  - Ensure required services are running via `docker compose`: `mysql`, `redis`, `qdrant`, `mcp`, `worker` (and optionally `prometheus`).
   - Confirm `REDIS_URL` and other env values are set in `.env` (or compose service environment).

2) Create or identify a Task
   - Use the UI or API to create a `Task` record. Example (PowerShell):

```powershell
Invoke-RestMethod -Uri http://localhost:8001/api/tasks -Method Post -Body (@{ title='smoke'; description='smoke' } | ConvertTo-Json) -ContentType 'application/json'
```

3) Start a run
   - From the UI click Run, or call the run endpoint:

```powershell
Invoke-RestMethod -Uri http://localhost:8001/run-agents -Method Post -Body (@{ id=11; title='Lock test task' } | ConvertTo-Json) -ContentType 'application/json'
```

4) Observe progress
   - Open SSE connection to `GET /events/tasks/{id}` in the UI to receive events, or poll `/api/tasks/{id}`.
   - Prometheus scrapes `/metrics` for counters and can alert on abnormal rates (e.g., many 409s).

5) Troubleshooting duplicate-run behavior
   - The system uses a layered duplicate-protection strategy (up-front Redis check, tokenized redis lock, DB-level atomic update). If you see duplicate runs, check:
     - Redis connectivity and TTLs (ensure `REDIS_URL` points to the running redis service).
     - Sentinel logs inside the `mcp` container under `/tmp` (see smoke test below).

3. Smoke Test: sentinel-based lock test

Purpose
- Verify cross-process duplicate protection works: when two concurrent `POST /run-agents` calls target the same task id, one should acquire the lock and the other should be rejected.

Files created by `mcp` (inside container)
- `/tmp/run_agents_entered.log` — each handler entry (timestamp + id)
- `/tmp/run_agents_lock_acquired.log` — records of locks acquired (method, token_len)
- `/tmp/run_agents_lock_conflict.log` — records of conflicts/up-front detections

Automated smoke test (PowerShell)
- A reusable script is included at `scripts/run_lock_smoke.ps1`. From the repo root run:

```powershell
# Run for task id 11
.\scripts\run_lock_smoke.ps1 -TaskId 11
```

What the script does
- Sends two near-concurrent POSTs to `POST /run-agents` for the same task id (one background job and one foreground request). It then reads the sentinel files from the `mcp` container and validates that at least one `LOCK_ACQUIRED` and one `LOCK_CONFLICT` entry exist.

Interpreting results
- PASS: script exits 0 and shows at least one lock-acquired and one conflict entry. This means cross-process protection triggered as expected.
- FAIL: missing entries indicate either `mcp` didn't run the sentinel-enabled code, Redis was not reachable, or the up-front check/lock flow fell back to DB path unexpectedly. Inspect container logs and sentinel files to diagnose.

Manual sentinel inspection
- You can manually inspect sentinels via:

```powershell
docker compose ps -q mcp | ForEach-Object { docker exec $_ sh -lc "echo '--- /tmp/run_agents_entered.log ---'; cat /tmp/run_agents_entered.log || true; echo '--- /tmp/run_agents_lock_acquired.log ---'; cat /tmp/run_agents_lock_acquired.log || true; echo '--- /tmp/run_agents_lock_conflict.log ---'; cat /tmp/run_agents_lock_conflict.log || true" }
```

4. Operational checks and tips
- If the second request returns 200 (both succeed) during tests:
  - Ensure `TEST_HOLD_SECONDS` is set in the `mcp` service env (increase to 30) so the first run is long enough to conflict deterministically.
  - Verify Redis is reachable from the `mcp` container and `task:{id}:lock` key semantics work (use `redis-cli` inside container to inspect keys).

- To speed up developer iterations, consider mounting source into the `mcp` container during local dev so you don't need to rebuild the image for every change.

5. Where to find logs and artifacts
- FastAPI / uvicorn logs: visible from `docker compose logs mcp`.
- Sentinel files: `/tmp/run_agents_entered.log`, `/tmp/run_agents_lock_acquired.log`, `/tmp/run_agents_lock_conflict.log` inside the `mcp` container.
- Application metrics: `http://localhost:8001/metrics` (Prometheus format).

6. Next operational improvements (short list)
- Add a small UI panel for lock/conflict history for a selected task id.
- Convert sentinel smoke test to a Python script for CI portability and add a GitHub Actions job that runs it.
- Add a health check endpoint that validates Redis and DB connectivity and fails if either is unhealthy.

7. End-to-end and UI tests (new additions)

- **E2E integration script**: `scripts/run_e2e_integration.py` — a scaffold that:
  - Creates a Task via `POST /api/tasks`.
  - Ingests a small document via `POST /api/ingest`.
  - Waits briefly for vector indexing, then calls the agent via `POST /run-agents` and asserts that retrieval text is visible in the response.
  - Supports a deterministic mock mode so CI can run without an OpenAI key:
    - Run with `--mock` or omit `OPENAI_API_KEY` in the environment to run in mock mode.
    - Example (mock mode):

```powershell
python scripts/run_e2e_integration.py --mock
```

  - Example (live mode, requires app to call OpenAI internally):

```powershell
# ensure OPENAI_API_KEY is set in environment for the app
python scripts/run_e2e_integration.py
```

- **Playwright UI test scaffold**: `tests/ui/test_ui_agent_flow.py` (Python Playwright)
  - Minimal scaffold that opens the frontend, fills a query input, and asserts that a visible response contains the expected retrieval text.
  - Setup and run:

```powershell
python -m pip install playwright pytest
playwright install
pytest tests/ui/test_ui_agent_flow.py -q
```

8. Test Artifact Workflow (How Agents Consume pytest Results)

### Architecture Overview

Agents are **test result consumers**, not executors. The workflow:

```
1. Developer/CI runs pytest → generates artifacts/pytest.xml
2. Backend parses artifacts → builds Markdown summary
3. Summary injected into agent prompt → enables evidence-based analysis
```

### Generating Test Artifacts

**Local Development**:
```powershell
# JUnit XML output
pytest --junitxml=artifacts/pytest.xml

# Coverage report
pytest --cov --cov-report=xml:artifacts/coverage.xml

# Smoke/E2E logs
python scripts/smoke_test.py > artifacts/smoke.log 2>&1
```

**CI Pipeline** (GitHub Actions):
```yaml
- name: Test with artifacts
  run: |
    pytest --junitxml=artifacts/pytest.xml \
           --cov --cov-report=xml:artifacts/coverage.xml
- name: Upload artifacts
  uses: actions/upload-artifact@v3
  with:
    name: test-results
    path: artifacts/
```

### Providing Artifacts to Agents

**Option A: Automatic Discovery**
- If artifacts exist at default paths, backend auto-discovers them
- No configuration needed

**Option B: Explicit API**
```powershell
$body = @{
  title = 'Prepare test results tabulation and evaluation';
  description = 'Summarize repo tests';
  artifact_paths = @{
    junit_xml = @('artifacts/pytest.xml', 'artifacts/junit.xml');
    coverage_xml = 'artifacts/coverage.xml';
    smoke_log = 'artifacts/smoke.log';
    e2e_log = 'artifacts/e2e.log'
  }
} | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8001/run-agents `
  -Method Post -Body $body -ContentType 'application/json'
```

**Option C: UI Checkbox**
- Enable "Include artifact summary" when creating task
- Uses default paths automatically

### GitLab/GitHub CI Integration

**Challenge**: Agents read local filesystem; CI artifacts are in remote pipelines.

**Solution A: Download Artifacts Manually**
```powershell
# GitLab
curl --header "PRIVATE-TOKEN: <token>" \
  "https://gitlab.com/api/v4/projects/<id>/jobs/<job_id>/artifacts" \
  -o artifacts.zip
unzip artifacts.zip -d artifacts/

# GitHub
gh run download <run_id> --name test-results --dir artifacts/
```

**Solution B: CI Job Triggers Agent**
```yaml
# .gitlab-ci.yml
test:
  script:
    - pytest --junitxml=artifacts/pytest.xml
  artifacts:
    paths: [artifacts/]

analyze:
  needs: [test]
  script:
    - curl -X POST http://api:8001/run-agents \
      -d '{"title":"CI test analysis","artifact_paths":{"junit_xml":["artifacts/pytest.xml"]}}'
```

**Solution C: Webhook Integration** (future enhancement):
- GitLab pipeline completes → webhook to `/webhook/gitlab`
- Backend downloads artifacts via GitLab API
- Stores in `artifacts/` and triggers agent run

### Artifact Summary Output

Backend builds a concise Markdown table:

```markdown
### Attached Test Artifacts Summary
| Artifact | Signal | Notes |
| JUnit | ✅ PASS | 0 failing, 2 skipped |
| Coverage | 87.3% | Overall line rate |

#### Failed Tests
- test_auth.py::test_invalid_token: AssertionError
```

This summary is:
- Appended to task description
- Exposed as `artifact_summary` field to agents
- Used for evidence-based analysis vs. hypotheticals

### Monitoring

**Check artifact discovery**:
```powershell
# View served artifacts
curl http://localhost:8001/artifacts/

# Check backend logs
docker compose logs mcp | Select-String "artifact"
```

**Expected logs**:
```
INFO: Summarizing artifacts from artifact_paths
INFO: Found JUnit XML: 45 tests, 0 failures
INFO: Found coverage: 87.3% line rate
```

### Troubleshooting

**Issue**: "No artifacts found"
- **Check**: Artifacts exist at expected paths
- **Fix**: Run pytest with `--junitxml` flag

**Issue**: Coverage not parsed
- **Check**: XML uses standard Cobertura or coverage.py format
- **Fix**: Ensure `--cov-report=xml` is used

**Issue**: GitLab artifacts not accessible
- **Check**: Artifacts downloaded to local `artifacts/` directory
- **Fix**: Use GitLab API or CI job to copy artifacts

### Notes

- Artifacts are optional—agents run without them (analyze code/Git only)
- `artifacts/` directory served at `http://localhost:8001/artifacts/`
- Override location: set `ARTIFACTS_DIR` environment variable
- Supports: JUnit XML, Cobertura, coverage.py, plain text logs

  - Notes:
  - Update the selectors in `tests/ui/test_ui_agent_flow.py` to match your UI (defaults assume `#agent-query`, `#agent-submit`, `#agent-response`).
  - The UI test is optional for CI (it requires the frontend to be available at `http://localhost:3000` by default).

8. CI considerations

- The lock smoke-test workflow was updated to dynamically create a test Task at runtime and pass its id to the smoke-test. This makes CI runs reliable without relying on a hard-coded task id.
- If you want CI to run the E2E integration script:
  - Either provide an `OPENAI_API_KEY` secret for real agent calls, or run the script with `--mock` to avoid external API calls.
  - Example workflow step to run the E2E scaffold in mock mode:

```yaml
- name: Run E2E scaffold (mock)
  run: |
    python3 scripts/run_e2e_integration.py --mock
```

- **In-app / local OpenAI mock server**
  - A lightweight OpenAI-compatible mock server is provided at `mcp/openai_mock.py` and can be started on port `1573` using the helper script:

```powershell
python scripts/run_openai_mock.py
```

  - Endpoints exposed (compatible shape):
    - `POST http://localhost:1573/v1/chat/completions`
    - `POST http://localhost:1573/v1/completions`
    - `POST http://localhost:1573/v1/embeddings`

  - Behavior:
    - Deterministic replies: queries mentioning "sky" will return a reply containing "blue".
    - Embeddings are deterministic vectors derived from the input text.

  - Use this when running the frontend or CI to avoid real OpenAI calls. The frontend can be configured to point its OpenAI base URL to `http://localhost:1573`.

Contact and ownership
- File: `docs/OPERATION_MANUAL.md` — edit to extend UI details or to add organization-specific runbooks.
 
## Maintenance & Recovery: Ingestion Control

> **Note**: For automated task scheduling (immediate/daily/weekly triggers), see the Task Automation status in `docs/AGENT_ENHANCEMENTS.md`. The user-facing scheduling UI is not yet implemented; currently only manual and webhook-driven automation is available.

When Git and Qdrant can drift (e.g., deleted files remain in Qdrant, or the `IndexedCommit` table is missing a record), operators can force synchronization using the secured admin endpoint.

**Admin Endpoint**
- `POST /admin/ingest` (requires `Authorization` token with `editor` role)
- Body:
  - `repo_url` (required)
  - `branch` (optional)
  - `commit` (optional)
  - `collection` (optional)
  - `previous_commit` (optional)

**Behavior**
- If `IndexedCommit` is missing, the system performs a full index and writes the current commit to the database.
- If present, the system runs a git diff between previous and current, deletes points for removed files, and re-indexes only changed files.
- On diff failure, it falls back to full index.

**Usage (PowerShell)**
```powershell
# Full ingest
Invoke-RestMethod -Uri 'http://localhost:8001/admin/ingest' `
  -Method POST `
  -Headers @{ Authorization = 'Bearer <ADMIN_TOKEN>' } `
  -ContentType 'application/json' `
  -Body (@{ repo_url = 'https://github.com/owner/repo'; branch = 'main' } | ConvertTo-Json)

# Incremental ingest
Invoke-RestMethod -Uri 'http://localhost:8001/admin/ingest' `
  -Method POST `
  -Headers @{ Authorization = 'Bearer <ADMIN_TOKEN>' } `
  -ContentType 'application/json' `
  -Body (@{ repo_url = 'https://github.com/owner/repo'; branch = 'main'; commit = '<current_sha>'; previous_commit = '<previous_sha>' } | ConvertTo-Json)
```

**Monitoring**
- Check logs for `Incremental update from <prev> to <curr>` and `Deleted points for: <file>`.
- Verify `IndexedCommit` records and Qdrant collection counts.
