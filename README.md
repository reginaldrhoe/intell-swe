# rag-poc

An AI-powered code review and analysis system that combines Retrieval-Augmented Generation (RAG) with Git integration and intelligent agents to provide deep insights into your codebase.

## Features

- **Settings UI**: Web-based interface to configure repositories, branches, and Qdrant collections without manual file editing
- **Enhanced Agents**: CrewAI-powered agents with multi-source intelligence:
  - **Git Integration**: Direct access to commit metadata, diffs, and file history
  - **Qdrant RAG**: Semantic search across your codebase
  - **Smart Context**: Automatic commit detection and enrichment
- **Real-time Updates**: Server-Sent Events (SSE) for live agent activity streaming
- **Task Queue**: Celery + Redis for durable background processing
- **Monitoring**: Prometheus metrics and health endpoints
- **OAuth SSO**: GitHub and GitLab authentication
- **RBAC**: Role-based access control for multi-user environments

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Git repository access (local or remote)
- OpenAI API key (recommended for production use)

### 1. Environment Setup

Create a `.env` file with the following variables:

```env
# Required
OPENAI_API_KEY=sk-...                      # OpenAI API key for embeddings and LLM
QDRANT_URL=http://qdrant:6333              # Qdrant vector database URL
GIT_REPO_PATH=/repo                        # Path to mounted git repository

# Optional
CELERY_BROKER_URL=redis://redis:6379/0     # Task queue (recommended)
CREWAI_API_KEY=...                         # CrewAI credentials (if using CrewAI cloud)
OPENAI_API_BASE=https://api.openai.com/v1  # Custom OpenAI endpoint
```

### 2. Start Services

```powershell
# Build and start all services
docker compose build mcp worker
docker compose up -d redis qdrant mcp worker

# Verify services are running
Invoke-RestMethod -Uri http://localhost:8001/health
```

### 3. Access the Application

- **Web UI**: http://localhost:5173 (Vite dev server) or http://localhost:3000 (Docker)
- **API**: http://localhost:8001
- **Metrics**: http://localhost:8001/metrics

### 4. Configure Your Repository

1. Open the Settings UI in the web interface
2. Add your repository URL (e.g., `https://github.com/yourusername/yourrepo.git`)
3. Select branches to track (e.g., `main`, `develop`)
4. Configure the Qdrant collection name
5. Enable auto-ingest to automatically index code changes
6. Click **Save Configuration**

### 5. Create a Task

Submit a task for agent analysis:

```powershell
$body = @{
    title = 'Analyze commit feature_abc123'
    description = 'Review the changes in commit feature_abc123 and provide code quality feedback'
} | ConvertTo-Json

Invoke-RestMethod -Uri http://localhost:8001/run-agents `
    -Method Post `
    -Body $body `
    -ContentType 'application/json' `
    -Headers @{ Authorization = 'Bearer demo' }
```

The agents will:
- Parse the commit SHA from the description
- Fetch commit metadata (author, date, message, files changed)
- Retrieve relevant code context from Qdrant
- Provide comprehensive analysis with quality feedback

## Architecture

### Agent Intelligence System

The agent system combines four complementary data sources:

1. **OpenAI Integration**: High-quality LLM analysis (configured in `.env`)
2. **Qdrant RAG**: Semantic search across indexed codebase (file content)
3. **Git Tools**: Direct access to commit history and metadata
4. **Task Parsing**: Automatic detection of commit SHAs, branches, and files

For detailed implementation, see [docs/manuals/AGENT_ENHANCEMENTS.md](docs/manuals/AGENT_ENHANCEMENTS.md).

### System Components

- **MCP Service**: FastAPI backend with task management, agent orchestration, and SSE
- **Worker Service**: Celery worker for background task processing
- **Qdrant**: Vector database for semantic code search
- **Redis**: Message broker for task queue and SSE pub/sub
- **Frontend**: React (Vite) application with real-time updates

## Development

### Running Tests

```powershell
# Unit tests
pytest -q

# Agent smoke tests (no external APIs)
python scripts/run_agent_smoke2.py

# E2E integration test (mock mode)
python scripts/run_e2e_integration.py --mock
```

### Local Frontend Development

```powershell
cd web
npm install
npm run dev
# Access at http://localhost:5173
```

### Monitoring and Debugging

```powershell
# View MCP logs
docker compose logs -f mcp

# View worker logs
docker compose logs -f worker

# Check Prometheus metrics
Invoke-RestMethod -Uri http://localhost:8001/metrics

# Inspect tasks
Invoke-RestMethod -Uri http://localhost:8001/api/tasks `
    -Headers @{ Authorization = 'Bearer demo' }
```

## Configuration

### RAG Configuration File

The system uses `agents/rag_config.json` to track repositories and collections:

```json
{
  "collection": "rag-poc",
  "repos": [
    {
      "url": "https://github.com/reginaldrhoe/rag-poc.git",
      "auto_ingest": true,
      "collection": "rag-poc",
      "branches": ["main"]
    }
  ]
}
```

**Important**: Use the Settings UI instead of editing this file manually.

### Git Repository Access

The system requires read access to the Git repository for commit analysis:

- **Local repositories**: Mounted as Docker volumes (`.git` directory)
- **Remote repositories**: Cloned during webhook ingestion
- **Configuration**: Set `GIT_REPO_PATH=/repo` in docker-compose.yml

See `docker-compose.yml` for volume mount configuration:

```yaml
volumes:
  - ./.git:/repo/.git:ro        # Git metadata (read-only)
  - ./:/repo/workspace:ro       # Working directory (read-only)
```

## Advanced Features

### Webhook Integration

Trigger automatic ingestion on Git push events:

```powershell
$body = @{
    repository = @{
        clone_url = 'https://github.com/yourusername/yourrepo.git'
        ## Releases
        - Latest patch: [`v2.2.1`](https://github.com/reginaldrhoe/rag-poc/releases/tag/v2.2.1)
        - All releases: https://github.com/reginaldrhoe/rag-poc/releases

        ## Documentation
        - User Manual: `docs/manuals/USER_MANUAL.md` (see “Ingestion Recovery (Admin)”)
        - Operation Manual: `docs/manuals/OPERATION_MANUAL.md` (see “Maintenance & Recovery: Ingestion Control”)
        html_url = 'https://github.com/yourusername/yourrepo'
    }
    head_commit = @{
        message = 'Update feature'
        id = 'abc123def456'
    }
    ref = 'refs/heads/main'
} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Uri 'http://localhost:8001/webhook/github' `
    -Method Post `
    -Body $body `
    -ContentType 'application/json' `
    -Headers @{ 'X-GitHub-Event' = 'push' }
```

### Maintenance: Force Ingestion

Use the secured admin endpoint to trigger a full or incremental ingest when desynchronization is suspected (requires an `Authorization` token with `editor` role):

```powershell
# Full ingest (auto collection)
Invoke-RestMethod -Uri 'http://localhost:8001/admin/ingest' `
  -Method POST `
  -Headers @{ Authorization = 'Bearer <ADMIN_TOKEN>' } `
  -ContentType 'application/json' `
  -Body (@{ repo_url = 'https://github.com/owner/repo'; branch = 'main' } | ConvertTo-Json)

# Incremental ingest from a known previous commit
Invoke-RestMethod -Uri 'http://localhost:8001/admin/ingest' `
  -Method POST `
  -Headers @{ Authorization = 'Bearer <ADMIN_TOKEN>' } `
  -ContentType 'application/json' `
  -Body (@{ repo_url = 'https://github.com/owner/repo'; branch = 'main'; commit = '<current_sha>'; previous_commit = '<previous_sha>' } | ConvertTo-Json)
```

Notes:
- If the last indexed commit is missing in the database, the system falls back to a full index and stores the current commit for future incremental updates.
- When webhooks are enabled and `auto_ingest` is true for the repo, pushes trigger ingestion automatically; the admin endpoint is for manual control and recovery.

### RBAC Configuration

Role-based access control via `agents/rbac.json`:

```json
{
  "demo": "admin",
  "viewer-token": "viewer",
  "editor-token": "editor"
}
```

Roles:
- **admin**: Full access (create, read, update, delete tasks)
- **editor**: Create and read tasks
- **viewer**: Read-only access

### OAuth SSO

Configure GitHub or GitLab authentication:

```env
GITHUB_CLIENT_ID=your_client_id
GITHUB_CLIENT_SECRET=your_client_secret
GITLAB_CLIENT_ID=your_client_id
GITLAB_CLIENT_SECRET=your_client_secret
OAUTH_REDIRECT_BASE=http://localhost:8001
OAUTH_FRONTEND_CALLBACK=http://localhost:3000/
OAUTH_JWT_SECRET=your_secret_key
```

Endpoints:
- `GET /auth/login?provider=github|gitlab` - Start OAuth flow
- `GET /auth/callback` - OAuth callback handler
- `GET /auth/me` - Current user info

## Quick Dev Ops Notes

### Celery + Redis
Enable durable task queue by setting `CELERY_BROKER_URL` in `.env`:
```env
CELERY_BROKER_URL=redis://redis:6379/0
```

### Prometheus Monitoring
Prometheus configuration in `prometheus/prometheus.yml` scrapes `/metrics` endpoint.

### RBAC
Token-to-role mapping in `agents/rbac.json` (used when `RAG_ROLE_TOKENS` env not set).

## Mock vs Live Mode

### Default: Live Mode

Uses real OpenAI API for embeddings and LLM calls:
```yaml
# docker-compose.yml
environment:
  OPENAI_API_BASE: https://api.openai.com/v1
  OPENAI_API_KEY: ${OPENAI_API_KEY}  # from .env
```

### Switch to Mock Mode (No External APIs)

```powershell
docker compose down
docker compose -f docker-compose.yml -f docker-compose.override.mock.yml up -d --build
```

Mock mode:
- Uses internal OpenAI mock service (no API key required)
- Returns deterministic stub responses for testing
- Ideal for CI/CD pipelines and offline development

### Switch Back to Live Mode

```powershell
docker compose down
docker compose up -d --build
```

## Testing

### Agent Smoke Tests

Run agents with mocked CrewAI (no credentials required):

```powershell
python scripts/run_agent_smoke2.py
```

### E2E Integration Test

Test webhook ingestion and retrieval with mock OpenAI:

```powershell
docker compose build mcp
docker compose up -d redis qdrant mcp worker openai-mock
python scripts/run_e2e_integration.py --mock
```

Override repository or query:
```powershell
$env:E2E_REPO_URL='https://github.com/reginaldrhoe/rag-poc.git'
python scripts/run_e2e_integration.py --mock --query "RUN_AGENTS_DBG"
```

### CI Workflows

- **Lock Smoke Test**: `.github/workflows/lock_smoke_test.yml` includes E2E mock test
- **CI Workflow**: Accepts `qdrant_force_client` input to run with real Qdrant client

Local deterministic ingest test:
```powershell
# Dry run (no network calls)
$env:QDRANT_FORCE_CLIENT=0
python scripts/ingest_repo.py --repo . --dry-run

# Real Qdrant writes
$env:QDRANT_FORCE_CLIENT=1
python scripts/ingest_repo.py --repo .
```

## Frontend Development

### Vite + React App (Recommended)

```powershell
cd web
npm install
npm run dev
# Access at http://localhost:5173
```

Features:
- Task management interface
- Real-time agent activity via SSE
- Settings UI for RAG configuration
- Bearer token authentication

### GitHub Pages Demo

Static demo at `docs/index.html`:

```powershell
python -m http.server 8003 -d docs
# Access at http://localhost:8003
```

Configure backend via query parameter: `?api=http://localhost:8001`

## SSE / Real-Time Updates

Server-Sent Events endpoint: `GET /events/tasks/{task_id}`

Event types:
- `{"type":"agent_status","agent":"AgentName","status":"running|done|failed"}`
- `{"type":"activity","agent":"AgentName","content":"...","created_at":"..."}`
- `{"type":"status","status":"running|done|failed"}`

### Scaling SSE Across Containers

For multi-instance deployments, configure Redis for cross-container event pub/sub:

```env
REDIS_URL=redis://redis:6379/0
# or
CELERY_BROKER_URL=redis://redis:6379/0
```

Without Redis, SSE uses in-memory queue (single container only).

## Documentation

- **[Agent Enhancements](docs/manuals/AGENT_ENHANCEMENTS.md)**: Detailed implementation of git tools, RAG integration, and task parsing
- **[Design MVP](docs/architecture/DESIGN_MVP.md)**: Architecture, concurrency model, and test instrumentation
- **[User Manual](docs/manuals/USER_MANUAL.md)**: Complete guide for end users

## Release Management

### Generating Release Notes

```powershell
python scripts/generate_release_notes.py
# or specify tag/output
python scripts/generate_release_notes.py --tag v2.0.0 -o RELEASE_NOTES.md
```

### Creating a Release

```powershell
# Update version in setup.py
git add -A
git commit -m "chore: release v2.0.0"
git tag -a v2.0.0 -m "v2.0.0"
git push origin HEAD
git push origin v2.0.0

# Regenerate release notes
python scripts/generate_release_notes.py --tag v2.0.0 -o RELEASE_NOTES.md
git add RELEASE_NOTES.md
git commit -m "docs: update release notes for v2.0.0"
git push origin HEAD
```

## Troubleshooting

### Agents Returning Stub Responses

Check OpenAI API key configuration:
```powershell
docker compose exec mcp printenv | Select-String "OPENAI"
```

Verify key is valid and has quota. Stub responses are a fallback when API is unavailable.

### Git Tools Not Working

Verify git repository is mounted:
```powershell
docker compose exec mcp ls -la /repo/.git
```

Check GIT_REPO_PATH environment variable:
```powershell
docker compose exec mcp printenv GIT_REPO_PATH
```

### Qdrant Not Returning Results

Trigger manual ingestion:
```powershell
$body = @{
    repository = @{ clone_url = 'https://github.com/yourusername/yourrepo.git' }
    ref = 'refs/heads/main'
} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Uri 'http://localhost:8001/webhook/github' `
    -Method Post `
    -Body $body `
    -ContentType 'application/json' `
    -Headers @{ 'X-GitHub-Event' = 'push' }
```

Check ingestion logs:
```powershell
docker compose logs -f worker
```

### SSE Connection Issues

Ensure CORS allows your frontend origin:
```python
# mcp/main.py
CORS_ALLOW_ORIGINS = ["http://localhost:5173", "http://localhost:3000"]
```

For cross-container SSE, configure Redis (see SSE section above).

## Contributing

1. Fork the repository
2. Create a feature branch
3. Run tests: `pytest -q`
4. Submit a pull request

## License

[Add your license information here]

---

## Version History

### v2.0.0 (Current)
- Settings UI for RAG configuration management
- Enhanced agents with git integration
- Multi-source intelligence (Git + Qdrant + OpenAI)
- Automatic commit detection and analysis
- Improved task enrichment and context handling

### v1.0.0
- Initial stable release
- In-repo CrewAI shim for testing
- CI workflows with deterministic tests
- Setup.py for editable installs
