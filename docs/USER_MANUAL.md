# RAG-POC User Manual

## Table of Contents

1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Using the Web Interface](#using-the-web-interface)
4. [Configuring Repositories](#configuring-repositories)
5. [Creating and Managing Tasks](#creating-and-managing-tasks)
6. [Understanding Agent Responses](#understanding-agent-responses)
7. [Advanced Features](#advanced-features)
8. [Troubleshooting](#troubleshooting)
9. [API Reference](#api-reference)

---

## Introduction

RAG-POC is an AI-powered code review and analysis system that combines multiple intelligence sources to provide deep insights into your codebase:

- **Git Integration**: Direct access to commit history, diffs, and file changes
- **Qdrant RAG**: Semantic search across your indexed codebase
- **OpenAI LLM**: Advanced language model for code analysis and recommendations
- **CrewAI Agents**: Specialized agents for different analysis tasks

### How It Works

1. **Code Ingestion**: Your repository code is indexed into Qdrant vector database
2. **Task Submission**: You create tasks describing what you want analyzed
3. **Agent Analysis**: Agents retrieve relevant context from Git and Qdrant
4. **Results**: You receive comprehensive analysis with code quality feedback

---

## Getting Started

### Prerequisites

Before using RAG-POC, ensure you have:

- Docker and Docker Compose installed
- Access to a Git repository (local or remote)
- An OpenAI API key (recommended for production use)

### Initial Setup

1. **Clone the repository:**
   ```powershell
   git clone https://github.com/reginaldrhoe/rag-poc.git
   cd rag-poc
   ```

2. **Create environment file:**
   Create a `.env` file in the root directory:
   ```env
   OPENAI_API_KEY=sk-your-api-key-here
   QDRANT_URL=http://qdrant:6333
   CELERY_BROKER_URL=redis://redis:6379/0
   GIT_REPO_PATH=/repo
   ```

3. **Start the services:**
   ```powershell
   docker compose build mcp worker
   docker compose up -d
   ```

4. **Verify the setup:**
   ```powershell
   Invoke-RestMethod -Uri http://localhost:8001/health
   ```

5. **Access the web interface:**
   Open your browser to http://localhost:5173

---

## Using the Web Interface

### Overview

The web interface provides:

- **Task Dashboard**: View all tasks and their status
- **Task Creation**: Submit new analysis tasks
- **Real-time Updates**: Live agent activity via Server-Sent Events (SSE)
- **Settings Panel**: Configure repositories and collections

### Authentication

The system uses bearer token authentication:

1. In the web interface, click the **Token** input field
2. Enter your authentication token (default: `demo` for development)
3. The token is stored in local storage for future sessions

### Dashboard Navigation

- **Tasks List**: Shows all tasks with status (pending, running, completed, failed)
- **Create Task**: Button to open task creation form
- **Settings**: Button to access repository configuration
- **Filters**: Filter tasks by status or date

---

## Configuring Repositories

The Settings UI allows you to manage which repositories are indexed for RAG analysis.

### Accessing Settings

1. Click the **Settings** button in the web interface
2. Or access directly at http://localhost:5173 (scroll to Settings section)

### Adding a Repository

1. In the Settings panel, click **Add Repository**
2. Fill in the repository details:
   - **Repository URL**: GitHub/GitLab clone URL (e.g., `https://github.com/username/repo.git`)
   - **Branches**: Comma-separated list (e.g., `main,develop`)
   - **Collection**: Qdrant collection name (e.g., `my-project`)
   - **Auto-ingest**: Enable to automatically index code on webhook events

3. Click **Save Configuration**

### Modifying Repositories

1. Locate the repository in the Settings panel
2. Update any fields (URL, branches, collection name)
3. Toggle **Auto-ingest** as needed
4. Click **Save Configuration**

### Removing Repositories

1. Click the **Remove** button next to the repository
2. Click **Save Configuration** to apply changes

### Configuration Details

**Repository URL**: Must be a valid Git clone URL
- ✅ `https://github.com/username/repo.git`
- ✅ `git@github.com:username/repo.git`
- ❌ `https://github.com/username/repo` (missing .git)

**Branches**: Only listed branches will be tracked
- Single branch: `main`
- Multiple branches: `main,develop,staging`

**Collection**: Qdrant collection name where code is indexed
- Use unique names for different projects
- Cannot be empty

**Auto-ingest**: When enabled, code is automatically indexed on Git push events
- Requires webhook configuration (see [Webhook Integration](#webhook-integration))

---

## Creating and Managing Tasks

### Creating a Task via Web Interface

1. Click **Create Task** button
2. Fill in the task form:
   - **Title**: Brief description (e.g., "Review PR #42")
   - **Description**: Detailed analysis request (see [Best Practices](#task-description-best-practices))
3. Click **Submit**
4. Watch real-time agent activity in the task detail view

### Creating a Task via API

```powershell
$body = @{
    title = 'Analyze commit abc123'
    description = 'Review the changes in commit abc123 and provide code quality feedback'
} | ConvertTo-Json

Invoke-RestMethod -Uri http://localhost:8001/run-agents `
    -Method Post `
    -Body $body `
    -ContentType 'application/json' `
    -Headers @{ Authorization = 'Bearer demo' }
```

### Task Description Best Practices

The description field is critical for getting good results. Follow these guidelines:

#### Include Specific References

**Commit SHAs**: Mention commit hashes for detailed analysis
```
Analyze commit 37c2ed14 and provide feedback on code quality
```

**Branch Names**: Reference branches for comparative analysis
```
Compare changes between main and feature/new-api
```

**File Paths**: Specify files for focused review
```
Review the changes in src/api/users.py for security issues
```

#### Use Clear Instructions

Be explicit about what you want:
- ✅ "Analyze the error handling in commit abc123 and suggest improvements"
- ✅ "Review the authentication logic in auth.py for security vulnerabilities"
- ❌ "Check this" (too vague)
- ❌ "Look at code" (no specific target)

#### Combine Multiple Sources

The agents can handle complex requests:
```
Review commit feature_abc123, focusing on:
1. Changes to database schema in models.py
2. API endpoint security in api/views.py
3. Test coverage for new features
```

### Task Status

Tasks progress through these states:

- **pending**: Waiting to be processed
- **running**: Agent is actively analyzing
- **completed**: Analysis finished successfully
- **failed**: Error occurred during processing

### Viewing Task Results

1. Click on a task in the dashboard
2. View agent activities in chronological order
3. Each activity shows:
   - Agent name (e.g., EngineerCrewAI)
   - Timestamp
   - Analysis content

### Task Activities

Activities are incremental outputs from agents:

- **Status Updates**: "Agent running", "Agent completed"
- **Analysis Content**: Code review, suggestions, findings
- **Context Information**: Git metadata, file references

---

## Understanding Agent Responses

### Response Structure

Agent responses typically include:

1. **Git Commit Data**: When commits are detected
   ```
   === Git Commit Data ===
   === Commit 37c2ed14 ===
   37c2ed14253a63c10684d12d7b13509fe5e6741b
   Author: John Doe <john@example.com>
   Date: 2025-11-26 02:01:21 -0800
   Message: Merge ci/dispatch-qdrant: E2E CI tests
   
   Files Changed:
   .github/workflows/lock_smoke_test.yml | 70 ++++++++++++
   mcp/openai_mock.py                    | 41 +++++++
   ```

2. **Code Analysis**: Quality assessment and recommendations
   ```
   Code Quality Assessment:
   - Strong test coverage added
   - Mock implementation follows best practices
   - Potential improvement: Add error handling for edge cases
   ```

3. **Relevant Context**: Related code snippets from Qdrant
   ```
   Related Code:
   File: agents/engineer_crewai.py
   Lines: 45-60
   [code snippet showing similar patterns]
   ```

### Interpreting Results

#### High-Quality Responses

Look for responses that include:
- ✅ Specific commit metadata (SHA, author, date, message)
- ✅ File-level change statistics (additions, deletions)
- ✅ Code quality assessment with examples
- ✅ Actionable recommendations

#### Stub Responses

If you see `[stub]` prefix, it means:
- OpenAI API is unavailable or key is invalid
- System is using fallback stub mode
- Results are placeholder text, not real analysis

**Fix**: Verify OpenAI API key configuration:
```powershell
docker compose exec mcp printenv | Select-String "OPENAI"
```

### Multi-Source Intelligence

The system combines four data sources:

1. **Git Tools**: Commit metadata, diffs, file history
2. **Qdrant RAG**: Semantic search of code content
3. **OpenAI LLM**: Natural language understanding and generation
4. **Task Parsing**: Automatic detection of commit SHAs, branches, files

This multi-source approach provides:
- **Historical Context**: What changed and when
- **Code Semantics**: What the code does
- **Quality Assessment**: How good the code is

---

## Advanced Features

### Webhook Integration

Automatically ingest code changes when you push to Git.

#### Setup GitHub Webhook

1. Go to your repository settings on GitHub
2. Navigate to **Settings** > **Webhooks** > **Add webhook**
3. Configure webhook:
   - **Payload URL**: `http://your-server:8001/webhook/github`
   - **Content type**: `application/json`
   - **Events**: Select "Just the push event"
4. Click **Add webhook**

#### Manual Webhook Trigger

For testing or manual ingestion:

```powershell
$body = @{
    repository = @{
        clone_url = 'https://github.com/username/repo.git'
        html_url = 'https://github.com/username/repo'
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

#### Monitoring Ingestion

Watch worker logs for ingestion progress:
```powershell
docker compose logs -f worker
```

Successful ingestion shows:
```
Ingested via LangChain Qdrant wrapper into 'collection-name'
```

### Real-Time Updates (SSE)

The web interface uses Server-Sent Events for live updates:

- **Automatic Connection**: Opens when viewing a task
- **Live Activity**: Agent status and content streamed in real-time
- **No Polling**: Efficient push-based updates

#### SSE API Endpoint

For custom integrations:
```javascript
const eventSource = new EventSource(
  'http://localhost:8001/events/tasks/123',
  { headers: { Authorization: 'Bearer demo' } }
);

eventSource.addEventListener('message', (event) => {
  const data = JSON.parse(event.data);
  console.log('Event:', data);
});
```

### Role-Based Access Control (RBAC)

Configure user roles in `agents/rbac.json`:

```json
{
  "admin-token": "admin",
  "editor-token": "editor",
  "viewer-token": "viewer"
}
```

**Permissions**:
- **admin**: Full access (create, read, update, delete tasks)
- **editor**: Create and read tasks
- **viewer**: Read-only access

Use the appropriate token in the web interface or API requests.

### OAuth Single Sign-On

Authenticate with GitHub or GitLab:

1. Configure OAuth in `.env`:
   ```env
   GITHUB_CLIENT_ID=your_client_id
   GITHUB_CLIENT_SECRET=your_client_secret
   OAUTH_REDIRECT_BASE=http://localhost:8001
   OAUTH_FRONTEND_CALLBACK=http://localhost:3000/
   OAUTH_JWT_SECRET=your_secret_key
   ```

2. Register OAuth app on GitHub/GitLab with callback URL:
   ```
   http://localhost:8001/auth/callback?provider=github
   ```

3. Start OAuth flow:
   ```
   http://localhost:8001/auth/login?provider=github
   ```

4. After authentication, you'll receive a JWT token

### Prometheus Monitoring

Monitor system metrics at http://localhost:8001/metrics

Key metrics:
- `task_queue_size`: Number of pending tasks
- `agent_execution_duration_seconds`: Agent processing time
- `http_request_duration_seconds`: API response times

Prometheus scrapes metrics automatically (configured in `prometheus/prometheus.yml`).

---

## Troubleshooting

### Common Issues

#### 1. Agents Return Stub Responses

**Symptoms**: Agent responses start with `[stub]`

**Causes**:
- OpenAI API key missing or invalid
- API quota exceeded
- Network connectivity issues

**Solutions**:
```powershell
# Check OpenAI configuration
docker compose exec mcp printenv | Select-String "OPENAI"

# Verify API key is valid
curl https://api.openai.com/v1/models `
  -H "Authorization: Bearer $env:OPENAI_API_KEY"

# Restart services with updated .env
docker compose down
docker compose up -d
```

#### 2. Git Tools Not Working

**Symptoms**: No commit data in agent responses

**Causes**:
- Git repository not mounted in Docker
- GIT_REPO_PATH not configured
- .git directory missing

**Solutions**:
```powershell
# Verify git mount
docker compose exec mcp ls -la /repo/.git

# Check GIT_REPO_PATH
docker compose exec mcp printenv GIT_REPO_PATH

# Rebuild with correct configuration
docker compose build mcp worker
docker compose up -d
```

#### 3. Qdrant Returns No Results

**Symptoms**: Agent says "No relevant context found"

**Causes**:
- Repository not ingested into Qdrant
- Collection name mismatch
- Qdrant service not running

**Solutions**:
```powershell
# Check Qdrant service
docker compose ps qdrant

# Trigger manual ingestion
$body = @{
    repository = @{ clone_url = 'https://github.com/username/repo.git' }
    ref = 'refs/heads/main'
} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Uri 'http://localhost:8001/webhook/github' `
    -Method Post -Body $body -ContentType 'application/json' `
    -Headers @{ 'X-GitHub-Event' = 'push' }

# Monitor ingestion logs
docker compose logs -f worker
```

#### 4. Web Interface Not Loading

**Symptoms**: Blank page or connection errors

**Causes**:
- Frontend service not running
- Port conflicts
- CORS configuration issues

**Solutions**:
```powershell
# Check frontend service
docker compose ps

# For Vite dev server
cd web
npm install
npm run dev

# Check CORS configuration in mcp/main.py
# Ensure your frontend URL is in CORS_ALLOW_ORIGINS
```

#### 5. SSE Connection Drops

**Symptoms**: Real-time updates stop working

**Causes**:
- Proxy timeout (Nginx, etc.)
- Browser connection limit
- Missing Redis for multi-container setup

**Solutions**:
```powershell
# For multi-container deployments, configure Redis
# Add to .env:
REDIS_URL=redis://redis:6379/0

# Restart services
docker compose down
docker compose up -d

# Configure proxy timeout (Nginx example)
# proxy_read_timeout 3600s;
# proxy_connect_timeout 3600s;
```

### Logging and Diagnostics

#### View Service Logs

```powershell
# MCP backend logs
docker compose logs -f mcp

# Worker logs (ingestion, background tasks)
docker compose logs -f worker

# All services
docker compose logs -f

# Last 100 lines
docker compose logs --tail 100 mcp
```

#### Enable Debug Logging

Add to `.env`:
```env
LOG_LEVEL=DEBUG
```

Restart services:
```powershell
docker compose down
docker compose up -d
```

#### Health Check

```powershell
# Service health
Invoke-RestMethod -Uri http://localhost:8001/health

# Qdrant health
Invoke-RestMethod -Uri http://localhost:6333/health

# Redis connection
docker compose exec redis redis-cli ping
```

### Getting Help

1. **Check Logs**: Always start with service logs
2. **Review Configuration**: Verify `.env` and `agents/rag_config.json`
3. **Test Components**: Isolate issues (API, frontend, Qdrant, etc.)
4. **Consult Documentation**: See [docs/AGENT_ENHANCEMENTS.md](AGENT_ENHANCEMENTS.md) for technical details

---

## API Reference

### Authentication

All API requests require bearer token authentication:

```powershell
$headers = @{ Authorization = 'Bearer demo' }
```

### Endpoints

#### Tasks

**Create Task**
```powershell
POST /run-agents
Content-Type: application/json

{
  "title": "Task title",
  "description": "Detailed description"
}
```

**List Tasks**
```powershell
GET /api/tasks
Authorization: Bearer demo
```

**Get Task**
```powershell
GET /api/tasks/{id}
Authorization: Bearer demo
```

**Delete Task**
```powershell
DELETE /api/tasks/{id}
Authorization: Bearer demo
```

#### Configuration

**Get RAG Configuration**
```powershell
GET /rag-config
Authorization: Bearer demo
```

**Update RAG Configuration**
```powershell
POST /rag-config
Content-Type: application/json

{
  "collection": "my-collection",
  "repos": [
    {
      "url": "https://github.com/username/repo.git",
      "auto_ingest": true,
      "collection": "my-collection",
      "branches": ["main"]
    }
  ]
}
```

#### Webhooks

**GitHub Webhook**
```powershell
POST /webhook/github
X-GitHub-Event: push
Content-Type: application/json

{
  "repository": {
    "clone_url": "https://github.com/username/repo.git"
  },
  "ref": "refs/heads/main",
  "head_commit": {
    "id": "abc123",
    "message": "Commit message"
  }
}
```

#### Search

**Similarity Search**
```powershell
GET /similarity-search?query=authentication&k=5
Authorization: Bearer demo
```

#### Events (SSE)

**Subscribe to Task Events**
```javascript
GET /events/tasks/{id}
Authorization: Bearer demo
Accept: text/event-stream
```

#### Health

**Health Check**
```powershell
GET /health
```

**Metrics (Prometheus)**
```powershell
GET /metrics
```

### Response Codes

- `200 OK`: Successful request
- `201 Created`: Resource created
- `400 Bad Request`: Invalid input
- `401 Unauthorized`: Missing or invalid token
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

### Rate Limiting

No rate limiting is currently enforced in development mode.

For production deployments, consider implementing rate limiting at the proxy level (Nginx, etc.).

---

## Best Practices

### Task Management

1. **Use Descriptive Titles**: Makes it easier to find tasks later
2. **Include Commit SHAs**: Get detailed git analysis
3. **Reference Specific Files**: Focus agent attention
4. **One Task Per Feature**: Easier to track and review

### Repository Configuration

1. **Unique Collections**: Use different collections for different projects
2. **Minimal Branches**: Only track active development branches
3. **Enable Auto-ingest**: Keep Qdrant synchronized with latest code
4. **Monitor Ingestion**: Check worker logs after pushes

### Performance

1. **Use Redis**: Enable for multi-container deployments
2. **Limit Branches**: Reduce ingestion overhead
3. **Archive Old Tasks**: Delete completed tasks periodically
4. **Monitor Metrics**: Use Prometheus to track performance

### Security

1. **Rotate Tokens**: Change bearer tokens regularly
2. **Use OAuth**: For production, prefer OAuth over static tokens
3. **Secure API Keys**: Store OpenAI key in `.env`, not in code
4. **Read-Only Mounts**: Git repository mounted read-only in Docker

---

## Conclusion

RAG-POC provides powerful code analysis capabilities through the combination of Git integration, vector search, and AI language models. By following this manual, you should be able to:

- Configure repositories and collections
- Create effective analysis tasks
- Interpret agent responses
- Troubleshoot common issues
- Use advanced features like webhooks and SSE

For technical implementation details, see:
- [docs/AGENT_ENHANCEMENTS.md](AGENT_ENHANCEMENTS.md) - Agent system architecture
- [docs/DESIGN_MVP.md](DESIGN_MVP.md) - Overall system design
- [README.md](../README.md) - Quick start and development guide

Happy analyzing! 🚀
