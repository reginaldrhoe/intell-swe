# Implementation Guide (Part 1)

## Purpose
This guide is for GitHub Copilot DUO inside VS Code. Copilot DUO should follow it autonomously to rebuild Intel-SWE from a fresh fork. Keep the steps simple and safe. Do not use Docker; use Apptainer instead.

## Rules
- Work only in a non-root folder (example: `/home/<you>/work/intell_swe_fork`).
- Do not commit secrets or tokens.
- Assume no database or container passwords are available.
- Prefer placeholders for all credentials.
- Use Apptainer (not Docker or Docker Compose).
- Run Apptainer, databases, and all services as a non-root user.

## Install-time checklist (ask the admin)
- Python module name and version.
- Non-root base path for installs and data.
- GitHub fork URL and upstream URL.
- Apptainer storage path and image cache location.
- If Kubernetes is used: namespace, storage class, ingress type, and hostnames.

## Step 1: Fork and clone
1. Navigate to the Intel-SWE repository: **https://github.com/reginaldrhoe/intell-swe**
2. Fork the repository to the admin GitHub account.
3. Clone the fork into a non-root directory.
4. Add the original repository as `upstream`:
   ```bash
   git remote add upstream https://github.com/reginaldrhoe/intell-swe.git
   ```
5. Open the cloned folder in VS Code.

## Step 2: Local Python setup (module-based)
1. Load Python 3.11 with the module system (example: `module load python/3.11`).
2. Confirm the module path and Python version.
3. Create a Python 3.11 virtual environment in the repo root (non-root path).
4. Activate the virtual environment.
5. Install dependencies from `requirements.txt`.
6. Freeze a requirements snapshot for troubleshooting (optional).
7. Confirm `python --version` shows 3.11.x.

## Step 3: Web UI setup
1. Go to the `web` folder.
2. Confirm Node.js is available (from the module system if required).
3. Install Node.js dependencies.
4. Keep the dev server instructions ready, but do not run it until services exist.

## Step 4: Apptainer plan (containers)
Use Apptainer to replace Docker Compose. Create a simple, repeatable plan to run these services:
- PostgreSQL
- Redis
- Qdrant
- MCP API
- Worker

Guidance:
- Decide where Apptainer images and cache live (non-root path).
- Use `apptainer pull` for base images when possible.
- For each service, create an Apptainer definition file or use an image with the correct entrypoint.
- Use `apptainer instance start` and `apptainer instance stop` to manage services.
- Map ports to local host the same way Docker Compose would.
- Mount non-root volumes for data and logs (no `/root` paths).
- Keep a short run order: databases first, then MCP API, then worker, then web UI.

## Optional: Kubernetes (if available)
Kubernetes can help if you want a more standard deployment, but it is not required for the rebuild.

If you choose to use Kubernetes:
1. Create manifests for PostgreSQL, Redis, Qdrant, MCP API, and Worker.
2. Use ConfigMaps for non-secret settings and Secrets for credentials (placeholders until real secrets are provided).
3. Expose MCP API and web UI with Services and Ingress.
4. Keep persistent volumes in a non-root path.
5. Validate `/health` and `/metrics` before moving on.

Sample manifest layout (short):
```
k8s/
	namespace.yaml
	configmap-mcp.yaml
	secret-placeholder.yaml
	postgres/
		deployment.yaml
		service.yaml
		pvc.yaml
	redis/
		deployment.yaml
		service.yaml
	qdrant/
		deployment.yaml
		service.yaml
		pvc.yaml
	mcp/
		deployment.yaml
		service.yaml
	worker/
		deployment.yaml
	web/
		deployment.yaml
		service.yaml
	ingress.yaml
```

Kubernetes prerequisites (checklist):
- Cluster access (kubeconfig) and namespace permissions.
- `kubectl` installed on the admin host.
- Storage class available for PVCs.
- Ingress controller installed (or use NodePort for testing).
- DNS or local host mapping for the web UI and MCP API endpoints.

At installation time, ask the admin for:
- Namespace name and storage class.
- Ingress type and hostnames.
- Non-root base path for PV data.

## Step 5: Configuration files
1. Create a `.env` file from a safe template.
2. Add only non-secret settings first (ports, hostnames, feature flags).
3. Use placeholders for passwords and API keys.
4. Keep all secrets out of source control.
5. Record missing secrets in a local note for the admin to fill later.

**Database configuration:**
- Ensure database connection strings point to the Intel-SWE instance databases (PostgreSQL for app data, Qdrant for vectors).
- Set `DATABASE_URL`, `QDRANT_URL`, and `REDIS_URL` in `.env`.

**Repository targets for analysis:**
- Use the Settings UI (after first run) or edit `agents/core/rag_config.json` to add target repositories.
- Include the Intel-SWE repository itself in the config so the admin can add MCP resources and adjust configuration as needed.
- Specify repository URLs and branches to analyze.
- Example: `{"repo_url": "https://github.com/org/project.git", "branches": ["main", "develop"], "collection": "project_main"}`

**Target repository permissions:**
- Intel-SWE will read and analyze code (read-only; it will not modify source code).
- Intel-SWE can write to issues, merge requests, and perform queries on target repositories.
- Ensure GitHub/GitLab access tokens have appropriate scopes: `repo:read` for code, `repo:write` for issues/MRs.

**Initial ingestion requirements:**
- Both the Intel-SWE fork and all target repositories require full initial ingestion into Qdrant.
- Initial ingestion can take significant time depending on repository size (minutes to hours).
- Monitor ingestion progress via logs and the `/metrics` endpoint.
- After initial ingestion, incremental updates use git diffs (much faster).

**Choose GitHub or GitLab (setup decision):**
- At setup time, decide whether to use GitHub or GitLab for the Intel-SWE fork and target repositories.
- Configuration differences:
  - **GitHub**: Set `GITHUB_CLIENT_ID`/`GITHUB_CLIENT_SECRET`, use GitHub Personal Access Token, configure webhooks at `/webhook/github`, use `https://github.com/user/repo.git` URLs.
  - **GitLab**: Set `GITLAB_CLIENT_ID`/`GITLAB_CLIENT_SECRET`, use GitLab Personal Access Token, configure webhooks at `/webhook/gitlab`, use `https://gitlab.com/user/repo.git` URLs.
- Both providers support the same features (OAuth, issues, merge requests, code analysis).

**Agent LLM configuration (CrewAI):**
- Choose an LLM provider: OpenAI or Anthropic/Claude.
- Set the appropriate API key in `.env`: `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`.
- Optionally select a specific model: `CREWAI_MODEL=gpt-4o-mini` (OpenAI) or `CREWAI_MODEL=claude-3-5-sonnet-20241022` (Claude).
- See [docs/LLM_SETUP_GUIDE.md](LLM_SETUP_GUIDE.md) for detailed LLM and CrewAI configuration.
- The system auto-detects the provider; no changes needed if only one API key is set.

## Step 6: First run checklist
Provide a checklist for the admin to validate:
- Services are running (health endpoints reachable).
- The API starts without errors.
- The web UI loads.
- Database connections succeed (check logs for PostgreSQL, Redis, Qdrant connectivity).
- Target repositories are configured (via Settings UI or `rag_config.json`).
- Initial full ingestion completes for both Intel-SWE fork and all target repositories (monitor logs; can take minutes to hours).
- Incremental ingestion is confirmed working after a test commit.

## Step 7: MCP resources (Prometheus, CAMEO, SonarQube)
Add instructions for optional MCP resources. Keep them simple and safe.

Prometheus (monitoring):
1. Use `prometheus/prometheus.yml` as the base config.
2. Ensure the MCP API is reachable at the configured target and that `/metrics` is exposed.
3. Start Prometheus with Apptainer and map port 9090.
4. Validate metrics are available before using them in dashboards.

CAMEO (requirements):
1. If CAMEO integration is not wired, export requirements from CAMEO to a file (CSV or JSON).
2. Store the export in a non-root `artifacts/` folder.
3. Add the file path to the MCP task payload using `artifact_paths` so agents can read it.
4. Use placeholders for any credentials.

SonarQube (static analysis):
1. Generate a SonarQube report outside the system (no passwords are available).
2. Store the report in `artifacts/`.
3. Add the report path to the MCP task payload using `artifact_paths`.
4. Treat this as an external input until full integration exists.

## Step 8: Persist resource results in the database (optional)
Add a minimal ingestion path so resource outputs are stored in the DB instead of only on disk.

1. **Define storage targets**
	- Add DB tables or JSON fields to store parsed outputs (Prometheus snapshots, CAMEO exports, SonarQube reports).
	- Keep raw artifacts on disk and store metadata + summaries in DB.

2. **Add an API endpoint for uploads**
	- Create a small API route to accept uploaded artifacts or file references.
	- Parse the payload and write normalized data into the DB.

3. **Wire agents to read from DB**
	- Update agents to prefer DB-backed resource data.
	- Fall back to `artifact_paths` if the DB data is missing.

## Step 9: User onboarding note (admin task)
Add a short section that tells the admin how to add users later:
- If using GitLab OAuth, explain that new users must be added in the OAuth provider and granted the correct role.
- If using local auth, provide a minimal step list to create a user and assign role.

RBAC setup details:
1. **Decide auth path**: OAuth (GitLab/GitHub) or token-based (simple bearer token).
2. **Define default roles**: admin, editor, viewer.
3. **Locate role mappings**:
   - For token-based: check `agents/rbac.json` or `RAG_ROLE_TOKENS` environment variable.
   - For OAuth: roles are stored in the database or derived from OAuth provider groups.
4. **Admin action**: Update the role mapping file or environment variable when adding new users.
5. **Test**: Confirm new users can authenticate and see only their permitted actions.

## Part 2 (Future)
Part 2 will cover a full rebuild from scratch if Intel-SWE is not available.
