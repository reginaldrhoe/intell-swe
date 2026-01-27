# Release Notes

![RAG-POC Logo](./docs/Logo%20design%20featurin.png#width=75px;height=38px)

Generated: 2026-01-24

## v2.3.2 - 2026-01-24

### [SECURITY] GitHub PAT Token Rotation

**Release Focus**: Regenerate and rotate GitHub Personal Access Token (PAT) for the rag-poc-release publisher.

### Security Updates

- Regenerated publisher token for rag-poc-release- key
- Token has appropriate repository scopes for release publishing
- Old token invalidated to prevent unauthorized access

### Verification

- Confirmed ability to publish and update releases on GitHub
- Token authentication validated with GitHub API
- Release publishing script fully functional

---

## v2.3.1 — 2025-11-29

### 🔧 Patch Release: Vite Dev Server Reliability

**Release Focus**: Address Vite dev server persistence issue discovered after v2.3.0 release with production-ready reliability tools and comprehensive documentation.

### 🚀 New Features

**Service Management Scripts**
- **`check_services.ps1`**: Real-time status diagnostics for all services (Vite, API, MySQL, Redis, Qdrant, Frontend)
  - ✅/❌ indicators for each service
  - Port numbers and URLs
  - Docker container count
  - Quick action commands
- **`start_vite.ps1`**: Simple one-shot Vite starter for testing and debugging
- **`start_vite_persistent.ps1`**: Production-grade Vite server with auto-restart capability ⭐
  - Automatic restart on crashes (3-second delay)
  - Restart counter and timestamps
  - Configurable restart limits (`-MaxRestarts` parameter)
  - Detects clean exits (Ctrl+C) vs. crashes
  - Informative logging with color-coded output

**Documentation**
- **`scripts/README.md`**: Comprehensive script documentation
  - Usage examples for all scripts
  - Environment variable reference
  - Service port reference table
  - Reliability best practices
  - Troubleshooting guide
  - Common tasks and workflows
- **`docs/VITE_RELIABILITY.md`**: Complete investigation and solutions
  - Root cause analysis (Vite as foreground process)
  - Reliability strategies (manual, scheduled task, Windows service)
  - Production recommendations
  - Quick reference guide

### 🔍 Problem Solved

**Issue**: Vite dev server (localhost:5173) stops running after terminal closure, system reboot, or crashes, unlike Docker services which auto-restart.

**Root Cause**: Vite is a foreground process without persistence mechanism. Unlike Docker containers with `restart: always`, it requires manual restart.

**Solution**: Three-tier approach:
1. **Immediate**: `start_vite_persistent.ps1` for auto-restart in current session
2. **Development**: Windows scheduled task for auto-start on login
3. **Production**: Use containerized frontend (port 3000) instead of Vite dev server

### 🛠️ Technical Details

**Persistent Vite Server** (`start_vite_persistent.ps1`):
```powershell
# Unlimited restarts (default)
.\scripts\start_vite_persistent.ps1

# Limit restarts to prevent infinite loops
.\scripts\start_vite_persistent.ps1 -MaxRestarts 10

# Custom API base
.\scripts\start_vite_persistent.ps1 -ApiBase "http://192.168.1.100:8001"
```

**Features**:
- Monitors Vite process exit codes
- Clean exit (0/1) = no restart (respects Ctrl+C)
- Crash (non-zero) = automatic restart after 3 seconds
- Restart limit prevents runaway loops
- Auto-installs npm dependencies if missing
- Sets `VITE_API_URL` environment variable

**Service Status Checker** (`check_services.ps1`):
```powershell
.\scripts\check_services.ps1
```

**Output Example**:
```
Service Status Check
======================================================================
Vite Dev UI        Port 5173  ❌ STOPPED
API (MCP)          Port 8001  ✅ RUNNING
  → http://localhost:8001/health
Frontend           Port 3000  ✅ RUNNING
MySQL              Port 3306  ✅ RUNNING
Redis              Port 6379  ✅ RUNNING
Qdrant             Port 6333  ✅ RUNNING

Docker Containers
   Running: 9 / 27

Quick Actions
   Start Vite:    .\scripts\start_vite.ps1
   Start All:     docker compose up -d
```

### 📦 File Changes

**New Files**:
- `scripts/check_services.ps1` (68 lines): Service status diagnostics
- `scripts/start_vite.ps1` (37 lines): Simple Vite starter
- `scripts/start_vite_persistent.ps1` (82 lines): Persistent auto-restart server
- `scripts/README.md` (348 lines): Comprehensive script documentation
- `docs/VITE_RELIABILITY.md` (445 lines): Investigation, solutions, deployment guides

### 🎯 Reliability Improvements

**Automatic Recovery**:
- Vite crashes are detected and process restarts within 3 seconds
- Configurable restart limits prevent infinite loops
- Graceful handling of manual stops (Ctrl+C detected)

**Deployment Options**:
1. **Manual Start** (simplest):
   ```powershell
   .\scripts\start_vite_persistent.ps1
   ```

2. **Auto-start on Login** (recommended for development):
   ```powershell
   # One-time setup
   $action = New-ScheduledTaskAction -Execute "powershell.exe" `
       -Argument "-WindowStyle Hidden -File C:\MySQL\agentic_rag_poc\scripts\start_vite_persistent.ps1"
   $trigger = New-ScheduledTaskTrigger -AtLogOn
   Register-ScheduledTask -TaskName "RAG-POC Vite Dev" -Action $action -Trigger $trigger
   ```

3. **Windows Service** (production):
   - Use NSSM (Non-Sucking Service Manager)
   - Detailed guide in `docs/VITE_RELIABILITY.md`

4. **Containerized Frontend** (demos/production):
   ```powershell
   docker compose up -d frontend
   # Access at http://localhost:3000
   ```

### 🐛 Known Issues Addressed

- ❌ **Before**: Vite stops on terminal closure → manual restart required
- ✅ **After**: Auto-restart script recovers from crashes automatically

- ❌ **Before**: No visibility into which services are running
- ✅ **After**: `check_services.ps1` provides instant diagnostics

- ❌ **Before**: No documentation for Vite reliability strategies
- ✅ **After**: Comprehensive guides for all deployment scenarios

### 📚 Documentation Updates

All new files include:
- Usage examples with PowerShell commands
- Parameter descriptions and defaults
- Troubleshooting sections
- Best practices for development vs. production
- Quick reference tables

### 🔄 Migration Guide

**From v2.3.0 to v2.3.1**:

1. **Pull latest changes**:
   ```powershell
   git pull origin main
   ```

2. **Check service status**:
   ```powershell
   .\scripts\check_services.ps1
   ```

3. **Start Vite with auto-restart**:
   ```powershell
   .\scripts\start_vite_persistent.ps1
   ```

4. **(Optional) Set up auto-start on login**:
   - See `docs/VITE_RELIABILITY.md` for scheduled task setup

**No Breaking Changes**: All improvements are additive. Existing workflows continue to work.

### ⚡ Quick Start

```powershell
# Check what's running
.\scripts\check_services.ps1

# Start Vite with auto-restart (recommended)
.\scripts\start_vite_persistent.ps1

# Access dev UI
start http://localhost:5173
```

### 🙏 Acknowledgments

This patch release ensures reliable development experience with Vite dev server, addressing feedback from production use of v2.3.0.

---

## v2.3.0 — 2025-11-29

### 🎯 Major Release: Agent Training & Test Artifact Intelligence

**Release Focus**: Comprehensive agent grounding enhancements to eliminate hallucinations, test artifact consumption for evidence-based analysis, and complete documentation overhaul for operational clarity.

### 🚀 Key Features

**Agent Grounding & Hallucination Prevention**
- **System-Level Grounding**: All agents now receive explicit system prompts enforcing factual, artifact-based analysis
- **Artifact Summary Injection**: Test results (JUnit, coverage, logs) automatically appended to task descriptions
- **Explicit Resource Requests**: Agents trained to request missing artifacts instead of inventing data
- **Deterministic Temperature**: Default `OPENAI_DEFAULT_TEMPERATURE=0.0` for reproducible outputs (configurable via env)
- **Grounding Prompts**: Each agent includes artifact-specific instructions (e.g., "Ground findings in artifacts summary; do not assume artifacts not listed")

**Test Artifact Consumption Architecture** (New Module: `mcp/artifacts.py`)
- **JUnit XML Parser**: Extracts test counts, failures, error messages, pass rates from pytest/JUnit output
- **Coverage XML Parser**: Parses Cobertura/coverage.py reports for line coverage percentages
- **Plain Log Analyzer**: Heuristic PASS/FAIL/ERROR counting from smoke/E2E test logs
- **Markdown Summary Generator**: Builds concise tables showing artifact signals (✅ PASS, ❌ FAIL, coverage %)
- **Automatic Discovery**: Backend auto-discovers default artifact paths if not explicitly provided
- **UI Integration**: "Include artifact summary" checkbox in task creation form (default: ON)

**Enhanced Agent Prompts** (All 6 Agents Updated)
- `EngineerCodeReviewCrewAI`: Git context + artifact summary + grounding instructions
- `RootCauseInvestigatorCrewAI`: Artifact-based root cause analysis with explicit "not available" statements
- `DefectDiscoveryCrewAI`: Pattern detection grounded in actual test failures vs. hypotheticals
- `RequirementsTracingCrewAI`: Trace links validated against artifact summary
- `PerformanceMetricsCrewAI`: Metrics derived from coverage/test data when present
- `AuditCrewAI`: Compliance findings grounded in provided artifacts

**Documentation Overhaul** (4 Major Documents Updated)
- **USER_MANUAL.md**: Added test artifact workflow, GitLab/GitHub CI integration, artifact download procedures, container requirements
- **OPERATION_MANUAL.md**: New "Test Artifact Workflow" section with architecture, integration solutions, monitoring, troubleshooting
- **USE_CASE_ANALYSIS.md**: "Test Artifact Integration" section with architecture diagram, consumption flow, enhanced use case impact table
- **ARCHITECTURE_ANALYSIS.md**: Container requirements, task automation architecture (current status + future roadmap)
- **AGENT_ENHANCEMENTS.md**: Task automation status clarification (backend exists, user-facing UI not implemented)

### 🔧 Technical Improvements

**Artifact Summary Module** (`mcp/artifacts.py` - **NEW**)
```python
summarize_junit_xml(path)      # → {'tests': int, 'failures': int, 'failed_tests': [(name, msg)]}
summarize_coverage_xml(path)   # → {'line_rate': float, 'lines_valid': int, 'lines_covered': int}
summarize_plain_log(path)      # → {'pass_count': int, 'fail_count': int, 'tail': str}
build_markdown_summary(...)    # → Markdown table with artifact signals
summarize_artifacts(paths)     # → Combined summary from multiple artifact types
```

**Backend Integration** (`mcp/mcp.py`)
- `POST /run-agents` accepts `artifact_paths` parameter with custom paths
- Automatic artifact discovery: checks default paths (`artifacts/pytest.xml`, `artifacts/coverage.xml`, etc.)
- Summary injection: Markdown artifact table appended to task description
- `artifact_summary` field exposed to agents for prompt consumption
- `/artifacts` static file serving for artifact downloads

**Agent Adapter Enhancements** (`agents/crewai_adapter.py`)
- New `default_temperature` property (env: `OPENAI_DEFAULT_TEMPERATURE`, default: 0.2)
- New `system_grounding` property with configurable grounding prompt (env: `ADAPTER_SYSTEM_GROUNDING`)
- System message always prepended to agent prompts for consistent grounding
- Grounding prompt enforces: "Always produce strictly factual outputs grounded in provided context"

**API Updates** (`mcp/api.py`)
- `POST /api/tasks` accepts `artifact_paths` and `include_artifacts` parameters
- Auto-populates default artifact paths when `include_artifacts=true` and no explicit paths provided
- Forwards artifact configuration to `/run-agents` for agent consumption

**UI Updates** (`web/src/AgentTaskForm.jsx`)
- New "Include artifact summary" checkbox (default: checked)
- Automatically forwards default artifact paths when checkbox enabled
- Supports custom artifact path specification via API

**Master Control Panel** (`agents/agents.py`)
- Artifact summary prepending: If agent output lacks summary table, automatically prepends it
- Ensures all agent responses begin with factual artifact data when available

### 📊 Test Coverage

**New Test Suite** (`tests/test_artifacts_summary.py` - **NEW**)
- End-to-end artifact summarization validation
- JUnit XML parser tests (pass/fail/skip counts, failure messages)
- Coverage XML parser tests (line rate extraction)
- Plain log analyzer tests (PASS/FAIL heuristics)
- Markdown summary generation tests
- Integration test with sample artifacts (pytest.xml, coverage.xml, smoke.log, e2e.log)

**Sample Test Artifacts Created** (`artifacts/*` - **NEW**)
- `pytest.xml`: 3 tests, 0 failures (sample JUnit output)
- `coverage.xml`: 78% line coverage (sample Cobertura)
- `smoke.log`: PASS/FAIL log samples
- `e2e.log`: E2E test output sample

**Supporting Scripts**
- `scripts/md_to_pdf.py`: Markdown to PDF conversion utility (uses ReportLab)
- `scripts/start_dev_ui.ps1`: PowerShell script for Vite dev server with auto-restart and API base configuration
- `docs/OPERATION_MANUAL.pdf`: PDF export of operation manual (generated via md_to_pdf.py)

**Test Results**
```
pytest tests/test_artifacts_summary.py -v
✅ test_summarize_artifacts_end_to_end PASSED
✅ test_junit_and_coverage_parsers PASSED
```

**Existing Tests (All Passing)**
- ✅ E2E: Agent dispatch, incremental sync (2/2)
- ✅ Smoke: Lock distributed, agent coordination (2/2)
- ✅ Unit: MCP, adapter, ingestion (4/4)
- ✅ New: Artifact summarization (2/2)
- **Total: 10/10 tests passing**

### 🎨 User Experience

**Artifact Workflow (Local Development)**
```powershell
# Generate test artifacts
pytest --junitxml=artifacts/pytest.xml --cov --cov-report=xml:artifacts/coverage.xml
python scripts/smoke_test.py > artifacts/smoke.log 2>&1

# Create task with automatic artifact summary
# UI: Enable "Include artifact summary" checkbox
# API: POST /run-agents with artifact_paths or include_artifacts=true
```

**GitLab/GitHub CI Integration**
```yaml
# .gitlab-ci.yml
test:
  script:
    - pytest --junitxml=artifacts/pytest.xml --cov --cov-report=xml:artifacts/coverage.xml
  artifacts:
    paths: [artifacts/]

analyze:
  needs: [test]
  script:
    # Option A: Download artifacts manually via GitLab API
    # Option B: Trigger agent run with artifact_paths
    - curl -X POST http://api:8001/run-agents \
      -d '{"title":"Analyze test results","artifact_paths":{"junit_xml":["artifacts/pytest.xml"],"coverage_xml":"artifacts/coverage.xml"}}'
```

**Example Artifact Summary Output**
```markdown
### Attached Test Artifacts Summary
| Artifact | Signal | Notes |
|---|---:|---|
| JUnit | 3/3 pass | 0 failing, 0 skipped |
| Coverage | 78.0% | Overall line rate |
| Smoke Log | pass=1 fail=1 | tail included below |
| E2E Log | pass=1 fail=0 | tail included below |

**Top Failures**
(none)
```

### 📚 Documentation Updates

**User Manual Enhancements**
- New section: "Test Artifacts: How Agents Access pytest Results"
  - pytest command examples for local dev and CI pipelines
  - GitLab/GitHub artifact download procedures (curl, gh CLI)
  - Three access methods: automatic discovery, explicit API, UI checkbox
  - Agent summary format with example Markdown table
- New section: "Dev UI (Vite) vs Containerized Frontend" with npm run dev instructions
- New section: "Container Requirements" listing required (mysql, mcp, worker, redis, qdrant) vs. optional services
- Added `OPENAI_DEFAULT_TEMPERATURE=0.0` to .env example
- Expanded task creation step 3 with artifact checkbox explanation
- Added "Task Automation & Scheduling (Planned)" section clarifying current status

**Operation Manual Enhancements**
- New section: "Test Artifact Workflow (How Agents Consume pytest Results)"
  - Architecture overview (agents consume, not execute tests)
  - pytest generation commands (--junitxml, --cov)
  - Three integration solutions: manual download, CI trigger, future webhook
  - Monitoring instructions (check /artifacts endpoint, logs)
  - Troubleshooting guide (no artifacts, coverage not parsed, GitLab access)
- New subsection: "Container Requirements (Summary)" with PowerShell check commands
- Updated "Prepare environment" to include mysql as required service

**Use Case Analysis Enhancements**
- New section: "Test Artifact Integration"
  - ASCII architecture diagram (Developer/CI → Artifacts → Backend → Agents)
  - Agent consumption flow explanation
  - Three access methods detailed
  - GitLab/GitHub CI integration patterns
  - Enhanced use case impact table showing artifact benefits for 5 key use cases

**Architecture Analysis Enhancements**
- New section: "Container Requirements" with mysql noted as required for agents
- New section: "Task Automation Architecture" with proposed architecture diagram
  - Current implementation status (backend exists, user layer missing)
  - Required components for full automation (DB model, API, UI, scheduler)
  - Three automation workflows: event-driven, scheduled, manual

**Agent Enhancements Documentation**
- Updated "Task Automation Module" section with detailed implementation gap analysis
  - What exists: backend scheduler infrastructure (`SimpleScheduler`)
  - What's missing: UI, DB model, API endpoints, trigger types
  - Required components listed with code examples
  - Impact assessment: significant feature gap

### 🔍 Quality Improvements

**Hallucination Prevention Strategy**
1. **System-level grounding**: Adapter injects grounding system message for all agents
2. **Artifact-based prompts**: Each agent receives explicit artifact context in prompt
3. **Explicit unavailability**: Agents trained to state "not available from artifacts" vs. inventing data
4. **Deterministic outputs**: Default temperature 0.0 for reproducible, factual responses
5. **Prepend enforcement**: MCP prepends artifact summary if agent omits it

**Documentation Completeness**
- All container requirements now consistent across 3 documentation files
- Test artifact consumption flow documented in 3 locations (user, ops, use case)
- GitLab/GitHub CI integration procedures provided with code examples
- Task automation status clarified (backend exists, user UI pending)

### ⚙️ Configuration

**New Environment Variables**
```env
OPENAI_DEFAULT_TEMPERATURE=0.0          # Default LLM temperature (0.0 = deterministic)
ADAPTER_SYSTEM_GROUNDING="..."           # System grounding prompt (optional override)
ARTIFACTS_DIR=artifacts                  # Artifact directory location (default: ./artifacts)
```

**Artifact Paths (Default Discovery)**
```
artifacts/pytest.xml        # JUnit XML primary
artifacts/junit.xml         # JUnit XML fallback
artifacts/coverage.xml      # Coverage report
artifacts/smoke.log         # Smoke test log
artifacts/e2e.log           # E2E test log
```

### 🐛 Bug Fixes

- Fixed missing artifact context in agent prompts (all 6 agents now receive artifact summary)
- Fixed hallucination risk from missing grounding instructions (system-level grounding added)
- Fixed documentation inconsistency: container requirements now aligned across USER_MANUAL, OPERATION_MANUAL, ARCHITECTURE_ANALYSIS

### 📦 File Changes

**New Files**
- `mcp/artifacts.py` (267 lines): Artifact parsing and summarization module
- `tests/test_artifacts_summary.py` (60 lines): Artifact summary test suite
- `artifacts/pytest.xml`: Sample JUnit XML
- `artifacts/coverage.xml`: Sample coverage XML
- `artifacts/smoke.log`: Sample smoke test log
- `artifacts/e2e.log`: Sample E2E test log
- `scripts/md_to_pdf.py`: Markdown to PDF conversion utility
- `scripts/start_dev_ui.ps1`: Vite dev server startup script
- `docs/OPERATION_MANUAL.pdf`: PDF export of operation manual
- `docs/TEST_COVERAGE_REPORT.md`: E2E/smoke test coverage report
- `docs/intelligent_framework.svg`: Architecture diagram

**Modified Files**
- `agents/agents.py`: Artifact summary prepending logic
- `agents/crewai_adapter.py`: System grounding, default temperature
- `agents/engineer_crewai.py`: Artifact summary injection, grounding prompt
- `agents/root_cause_crewai.py`: Artifact-based analysis, grounding
- `agents/defect_discovery_crewai.py`: Pattern detection with artifacts
- `agents/requirements_tracing_crewai.py`: Trace validation with artifacts
- `agents/perf_metrics_crewai.py`: Metrics from artifacts
- `agents/audit_crewai.py`: Compliance grounded in artifacts
- `mcp/mcp.py`: Artifact summarization, `/artifacts` static serving
- `mcp/api.py`: `artifact_paths` and `include_artifacts` support
- `web/src/AgentTaskForm.jsx`: "Include artifact summary" checkbox
- `docs/USER_MANUAL.md`: Test artifact section, container requirements, Vite UI, env vars
- `docs/OPERATION_MANUAL.md`: Test artifact workflow, container requirements, monitoring
- `docs/USE_CASE_ANALYSIS.md`: Test artifact integration section
- `docs/ARCHITECTURE_ANALYSIS.md`: Container requirements, task automation architecture
- `docs/AGENT_ENHANCEMENTS.md`: Task automation status clarification

### 🔮 Future Enhancements

**Webhook Artifact Integration** (Planned for v2.4.0)
- Automatic GitLab/GitHub artifact download via API on pipeline completion
- `/webhook/gitlab` endpoint enhancement to fetch artifacts
- Storage in local `artifacts/` directory
- Automatic agent run trigger with artifact summary

**User-Facing Task Scheduling UI** (Planned for v3.0.0)
- Database model: `ScheduledTask` with trigger types (immediate, daily, weekly, cron)
- API endpoints: CRUD operations for scheduled tasks
- UI components: `ScheduledTasks.jsx`, `TaskScheduler.jsx`
- Scheduler enhancement: cron expression support, dynamic schedule management

**Enhanced Artifact Types** (Under Consideration)
- Static analysis reports (pylint, mypy, SonarQube)
- Security scan results (bandit, safety)
- Performance profiling data (cProfile, py-spy)
- API response time logs (load testing)

### 📖 Migration Guide

**From v2.2.x to v2.3.0**

1. **No Breaking Changes**: All existing functionality preserved
2. **Optional Artifact Integration**: Enable via UI checkbox or API parameter
3. **Environment Variables** (optional):
   ```env
   OPENAI_DEFAULT_TEMPERATURE=0.0  # Add for deterministic outputs
   ```
4. **Artifact Directory Setup** (optional):
   ```powershell
   mkdir artifacts
   pytest --junitxml=artifacts/pytest.xml --cov --cov-report=xml:artifacts/coverage.xml
   ```
5. **UI Update**: Refresh browser to see "Include artifact summary" checkbox

**Recommended Actions**
- Review updated documentation: `USER_MANUAL.md`, `OPERATION_MANUAL.md`
- Test artifact workflow: run pytest with artifact flags, create task with checkbox enabled
- Verify container requirements: ensure `mysql` is running if agents will execute

### 🙏 Acknowledgments

This release represents a significant step toward production-ready intelligent agent operations, with comprehensive grounding strategies, test artifact consumption, and operational documentation to support enterprise deployments.

---

## v2.2.0 — 2025-11-26

### 🎯 Major Release: Incremental Git-Qdrant Synchronization

**Release Focus**: Intelligent incremental updates for Qdrant vector database to maintain perfect synchronization with repository changes, eliminating stale data and enabling efficient continuous integration.

### 🚀 Key Features

**Git Diff-Based Incremental Updates**
- **Automatic Change Detection**: Git diff between commits identifies added, modified, and deleted files
- **Selective Re-indexing**: Only processes changed files instead of entire repository (10-100x faster for typical changes)
- **Smart Point Deletion**: Removes Qdrant points for deleted/renamed files using `file_path` metadata filter
- **Database Tracking**: Persistent storage of last indexed commit per repo/branch/collection combination
- **Webhook Integration**: Automatic incremental updates on push events via GitHub webhooks

**Incremental Update Architecture**
- `get_changed_files()`: Compares commits using `git diff --name-status` returning added/modified/deleted file lists
- `IndexedCommit` model: Tracks `repo_url`, `branch`, `commit_sha`, `collection`, `file_count`, `chunk_count`, `indexed_at`
- Metadata enrichment: Every Qdrant point tagged with `commit_sha`, `branch`, `file_path`, `indexed_at` for precise updates
- Fallback safety: Automatically reverts to full index if git diff fails or no previous commit exists

**Performance Improvements**
- **Incremental updates**: 10-100x faster than full re-indexing for typical commits (1-10 files changed)
- **No stale data**: Deleted and renamed files properly cleaned from vector database
- **Branch-aware tracking**: Separate commit tracking per branch enables branch-specific updates
- **Efficient deletion**: File-level point removal using metadata filters (no collection recreation needed)

### 🔧 Technical Improvements

**Database Schema** (`mcp/models.py`)
- New `IndexedCommit` table with fields:
  - `repo_url`: Repository identifier (URL or local path)
  - `branch`: Branch name (default: "main")
  - `commit_sha`: Last successfully indexed commit (40-char hex)
  - `collection`: Qdrant collection name
  - `file_count`, `chunk_count`: Metrics for tracking
  - `indexed_at`: Timestamp for audit trail

**Ingestion Script Enhancements** (`scripts/ingest_repo.py`)
- `get_changed_files(repo_dir, from_commit, to_commit)`: Returns `{added: [], modified: [], deleted: []}`
- Added `--previous-commit` CLI argument for manual incremental runs
- Incremental file loading: Uses `PythonLoader` for individual files instead of `DirectoryLoader`
- Qdrant point deletion for removed files using `FilterSelector` with `file_path` match
- `_save_indexed_commit()`: Database persistence after successful ingestion
- Metadata enrichment: All points tagged with `commit_sha`, `branch`, `file_path`, `indexed_at`

**Webhook Handler Updates** (`mcp/mcp.py`)
- `_spawn_ingest_for_repo()`: Queries database for last indexed commit before spawning ingestion
- Passes `--previous-commit` flag to ingestion script for diff-based updates
- Logs incremental update information: `Incremental update from abc1234 to def5678`
- Supports Celery task queue with `previous_commit` parameter for distributed processing

**Quick Fix (Completed in v2.2.0)**
- All Qdrant points now include metadata: `commit_sha`, `branch`, `file_path`, `indexed_at`
- Enables future cleanup operations and incremental synchronization
- Backward compatible: Old points without metadata can coexist (re-indexed on next update)

### 📊 Test Coverage

**New Test Suite** (`test_incremental_sync.py`)
- End-to-end incremental sync validation
- Creates test git repository with initial commit (2 files)
- Simulates repository changes:
  - File modification (`module1.py` updated)
  - File addition (`module3.py` created)
  - File deletion (`module2.py` removed)
- Verifies:
  - Git diff detection (1 added, 1 modified, 1 deleted)
  - Incremental file loading (2 files vs full index)
  - Qdrant point deletion for removed files
  - Database commit tracking and updates

**Test Results**
```
Git diff from dcfe48da to f3223c37:
  Added: 1 files      (module3.py)
  Modified: 1 files   (module1.py)
  Deleted: 1 files    (module2.py)

Incremental update: loading 2 changed files  (NOT all files!)
Deleting 1 removed files from Qdrant...
  Deleted points for: module2.py
Upserted 2 points into 'test-sync'
Saved indexed commit: ... @ master -> f3223c37
```

**Existing Tests (All Passing)**
- ✅ E2E Test: `test_mcp_dispatch_monkeypatch` (1/1)
- ✅ Smoke Tests: Agent coordination, CrewAI adapter (2/2)
- ✅ Unit Tests: MCP, adapter, ingestion (4/4)
- **Total: 8/8 tests passing**

### 🎨 User Experience

**Webhook Workflow**
1. Developer pushes code to GitHub
2. Webhook triggers `POST /webhook/github` with commit details
3. System queries database for last indexed commit
4. Git diff identifies changed files since last index
5. Only changed files are re-indexed (fast!)
6. Deleted files removed from Qdrant
7. New commit SHA saved to database for next update

**Manual Incremental Update**
```bash
# First ingestion (full index)
python scripts/ingest_repo.py --repo-url https://github.com/user/repo --branch main

# Later, after changes (incremental update)
python scripts/ingest_repo.py --repo-url https://github.com/user/repo --branch main --previous-commit abc1234
```

**Automatic Mode** (with webhooks configured):
- No manual intervention required
- Every push automatically updates Qdrant incrementally
- Database tracks commit history per branch
- System stays perfectly synchronized with repository

### 🔍 Benefits

**Performance**
- 10-100x faster updates for typical commits (1-10 files changed vs entire repo)
- Reduced embedding API costs (only changed files embedded)
- Lower Qdrant storage churn (fewer points created/deleted)

**Accuracy**
- No stale data: Deleted files properly removed from search results
- Rename handling: Old paths deleted, new paths indexed
- Branch isolation: Each branch maintains separate commit tracking

**Reliability**
- Fallback safety: Auto-reverts to full index on git diff failure
- Database persistence: Survives container restarts
- Audit trail: `indexed_at` timestamps track update history

### 📚 Documentation Updates

**Quick Fix Documentation**
- Added explanation of metadata enrichment strategy
- Migration path from old points to new metadata-tagged points
- Cleanup strategies for points without metadata

**Best Fix Documentation**
- Comprehensive incremental update architecture
- Git diff-based change detection workflow
- Database schema and tracking mechanism
- Test suite usage and validation

### 🔄 Upgrade Path from v2.1.0

1. **Database Migration**: Auto-creates `indexed_commits` table on first run (no manual migration needed)
2. **First Webhook Push**: Performs full index, saves commit SHA to database
3. **Subsequent Pushes**: Automatic incremental updates with change detection
4. **Old Qdrant Points**: Can coexist with new metadata-tagged points (re-indexed incrementally)

### 📝 Pertinent Data

- **Files Modified**: 5 files (3 modified, 1 new model, 1 new test)
  - `mcp/models.py`: New `IndexedCommit` model
  - `scripts/ingest_repo.py`: Incremental update logic
  - `mcp/mcp.py`: Webhook handler with database query
  - `test_incremental_sync.py`: Comprehensive test suite
  - `RELEASE_NOTES.md`: This release documentation
- **Lines Changed**: ~600 insertions, ~50 deletions
- **Test Coverage**: 100% for incremental sync flow
- **Performance Impact**: 10-100x faster for incremental updates
- **Storage Impact**: +4 metadata fields per Qdrant point (~80 bytes)

### 🏆 Highlights

**Before v2.2.0**: Every webhook push re-indexed entire repository, deleted files remained in Qdrant, no change tracking

**After v2.2.0**: Webhook pushes trigger intelligent incremental updates, only changed files processed, deleted files removed, perfect Git-Qdrant synchronization

---

## v2.1.0 — 2025-11-26

### 🎯 Major Release: Multi-Source RAG Intelligence Framework

**Release Focus**: Enhanced agent intelligence through multi-source Retrieval-Augmented Generation combining Git repository access, Qdrant vector database, and OpenAI LLM for comprehensive code analysis.

### 🚀 Key Features

**Multi-Source RAG Architecture**
- **Git Integration**: Direct repository access for temporal/change intelligence
  - Commit metadata extraction (author, date, message, stats)
  - Diff analysis and file change tracking
  - Mounted git repository (read-only) in Docker containers
  - Tools: `get_commit_summary()`, `get_file_content()`, `parse_git_references()`
- **Qdrant Vector Database**: Semantic code search across entire codebase
  - Cross-file pattern discovery
  - Natural language queries for code retrieval
  - Relevance-ranked search results
- **OpenAI LLM**: Natural language understanding and synthesis
  - Multi-dimensional context (Git + Qdrant + Current Code)
  - Root cause analysis and recommendations
  - Change impact assessment

**Intelligence Framework Improvements**
- **8x More Answerable Question Types**: Combines temporal, semantic, and analytical intelligence
- **3-Tier Fallback Strategy**: Adaptive source selection (Git → Qdrant → Files)
- **Real-time Analysis**: No more stub responses - actual OpenAI-powered insights
- **Change-Aware Intelligence**: Understands code evolution over time

### 🔧 Technical Improvements

**Agent System Enhancements**
- Fixed CrewAI adapter to detect and skip in-repo stub shim
- Adapter now correctly uses OpenAI chat completions API
- Task enrichment ensures agents receive complete context (description, id, title)
- Comprehensive logging for debugging (adapter path, git tool execution, result tracking)

**Git Tools Implementation** (`agents/engineer_crewai.py`)
- `get_commit_summary(commit_sha)`: Fetches commit metadata using `--git-dir` and `--work-tree`
- `get_file_content(file_path, commit_sha)`: Retrieves file content from specific commits
- `parse_git_references(text)`: Regex-based detection of commit SHAs, branches, files
- Async execution with `asyncio.to_thread()` for non-blocking operations

**Infrastructure** (`docker-compose.yml`)
- Permanent git repository mounts:
  - `./.git:/repo/.git:ro` (Git metadata, read-only)
  - `./:/repo/workspace:ro` (Workspace files, read-only)
- `GIT_REPO_PATH=/repo` environment variable for mcp and worker services
- Ensures git tools work across container restarts

### 🎨 User Interface

**Settings UI** (`web/src/Settings.jsx`)
- Web-based RAG configuration management (no manual file editing)
- Repository URL and branch configuration
- Qdrant collection name management
- Auto-ingest toggle for webhook-based updates
- Real-time save/reload functionality

**Integration** (`web/src/App.jsx`)
- Settings component integrated into main application
- Token-based authentication support
- Responsive layout with settings panel

### 📚 Documentation

**New Documentation Files**
- `docs/AGENT_ENHANCEMENTS.md` (352 lines): Technical implementation details
  - 4-option enhancement strategy (OpenAI, Qdrant, Git, Parsing)
  - Workflow diagrams and data comparison tables
  - Testing procedures and verification steps
  
- `docs/ARCHITECTURE_ANALYSIS.md` (420+ lines): Comprehensive architectural analysis
  - Multi-source RAG vs single-source comparison
  - Real-world use case examples
  - ROI analysis (8x capability increase vs 20% complexity increase)
  - Architectural advantages for intelligent frameworks
  
- `docs/USER_MANUAL.md` (400+ lines): Complete end-user guide
  - Getting started and configuration
  - Task creation best practices
  - Understanding agent responses
  - Advanced features (webhooks, SSE, RBAC, OAuth)
  - Troubleshooting guide and API reference

**Updated Documentation**
- `README.md`: Complete rewrite with new architecture overview
  - Quick start guide with multi-source RAG explanation
  - Feature highlights and system architecture
  - Testing, troubleshooting, and version history sections
  
- `docs/OPERATION_MANUAL.md`: New Chapter 2 on AI-assisted coding evolution
  - Comparison of traditional AI coding assistants vs intelligent frameworks
  - Detailed explanation of temporal, semantic, and change-aware intelligence
  - Real-world examples showing framework advantages

### 🐛 Critical Bug Fixes

**CrewAI Adapter Issue** (Primary Fix)
- **Problem**: In-repo CrewAI stub shim was being used instead of real OpenAI API
  - All agent responses were generic stubs: `[stub] You are an expert...`
  - No actual LLM analysis, just placeholder templates
- **Solution**: Modified `agents/crewai_adapter.py` to detect stub at `/app/crewai/__init__.py`
  - Skips stub shim and falls through to OpenAI client
  - Uses proper `chat.completions.create()` API
  - Added debug logging for troubleshooting
- **Impact**: Transformed from meaningless stubs to real AI analysis (1800-3700+ character responses)

**Task Enrichment** (`mcp/mcp.py`)
- Fixed empty description on duplicate agent calls
- Copies description, id, title from database to task dict after lock acquisition
- Ensures git parsing receives complete task context

### 📊 Pertinent Data & Metrics

**Code Changes**
- **12 files modified**: 2,587 insertions, 197 deletions
- **4 new files created**: Settings UI + 3 documentation files
- **Commit**: dd6664c5 (pushed to main)
- **Tag**: v2.1.0

**Performance Characteristics**
- Git tool execution: ~100-430ms for commit summary retrieval
- Qdrant semantic search: Sub-second response times
- OpenAI LLM responses: 1800-3700 characters (vs ~500 char stubs)
- Task processing: Dual agent invocation (first without git, second with enriched context)

**Configuration Files**
- `agents/rag_config.json`: Now tracks only `main` branch (simplified)
- `docker-compose.yml`: Added git mounts and GIT_REPO_PATH environment variable

**Test Verification**
- Task 23 (`result_trace`): Successfully demonstrated git context in agent responses
- Task 24 (`root_cause`): Initial stub response, fixed in rebuild
- Final tests: Confirmed OpenAI response lengths (1886, 1865, 3629, 3308, 3785, 3740 chars)

### 🔄 Upgrade Path

**From v2.0.0 to v2.1.0**
1. Pull latest changes: `git pull origin main`
2. Rebuild containers: `docker compose build mcp worker`
3. Restart services: `docker compose up -d`
4. Verify OpenAI integration: Check logs for "OpenAI response received"
5. Configure repositories via Settings UI (http://localhost:5173)

**Environment Requirements**
- `OPENAI_API_KEY`: Required for real LLM analysis (stub fallback if missing)
- `GIT_REPO_PATH`: Auto-configured to `/repo` in containers
- `QDRANT_URL`: Must point to running Qdrant instance

### 🎓 Architectural Philosophy

This release represents a paradigm shift from **single-source RAG** (vector database only) to **multi-source intelligence**:

| Capability | Vector DB Only | Multi-Source (v2.1.0) |
|------------|----------------|----------------------|
| "What changed?" | ❌ | ✅ Git Tools |
| "Who changed it?" | ❌ | ✅ Git Attribution |
| "When changed?" | ❌ | ✅ Git Timeline |
| "Find similar code" | ✅ | ✅ Qdrant |
| "Why was it changed?" | Partial | ✅ Git + LLM |
| "Show diff" | ❌ | ✅ Git Tools |
| "Impact analysis" | Partial | ✅ All Sources |
| "Related changes" | ❌ | ✅ Git + Qdrant |

**Result**: Comprehensive code intelligence platform that understands not just *how* code works, but *why* it exists, *when* it changed, and *who* contributed.

### 📝 Breaking Changes

**None** - Fully backward compatible with v2.0.0

### 🙏 Contributors

- reginaldrhoe: Architecture design, implementation, documentation

### 📖 References

- Agent Enhancements: `docs/AGENT_ENHANCEMENTS.md`
- Architecture Analysis: `docs/ARCHITECTURE_ANALYSIS.md`
- User Manual: `docs/USER_MANUAL.md`
- GitHub Release: https://github.com/reginaldrhoe/rag-poc/releases/tag/v2.1.0

---

## v2.0.0 — 2025-11-25

### Breaking/Defaults
- Default to Live mode for LLM calls: `OPENAI_API_BASE` now points to `https://api.openai.com/v1` for `mcp`, `worker`, and `openwebui` in `docker-compose.yml`.
- Set `TEST_HOLD_SECONDS=0` by default to avoid artificial delays outside of tests.


## v2.2.1 — Ops Manual Maintenance Section
- Documentation update: Added "Maintenance & Recovery: Ingestion Control" to `docs/OPERATION_MANUAL.md`.
- Details admin endpoint usage (`POST /admin/ingest`), full vs incremental behavior, and monitoring guidance.
- No code changes beyond previously merged admin endpoint; this release formalizes operational guidance.
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
