# Architectural Review & Improvement Plan

## Goal Description
Update the plan to reflect work shipped in v2.3.2 → v2.4.0 (scheduler MVP, agent refactor, docs reorg) and track the immediate security fix (PAT removal/rotation). This remains the roadmap for automation, scalability, and maintainability.

## Current Architecture Assessment

**Strengths:**
- **Multi-Source Intelligence:** Git (temporal), Qdrant (semantic), and LLM (reasoning) pairing remains solid.
- **Incremental Sync:** Diff-based ingestion stays efficient.
- **Concurrency Control:** Redis lock (`mcp/redis_lock.py`) continues to guard duplicate tasks.
- **Automation Foundation (new in v2.4.0):** DB-backed scheduler, API, and UI surfaced for recurring agent runs.

**Weaknesses & Gaps:**
- **Scheduler robustness:** Basic interval/cron scheduling shipped, but lacks dependency checks (e.g., `croniter` optional), history/visibility, and guardrails (pause/disable UX, retries, max concurrency).
- **Security debt:** v2.3.2 release note contained a committed PAT; remove/rotate immediately and scrub history (see Release Security Fix below).
- **Codebase Structure:** Initial refactor landed (`agents/core`, `agents/impl`, `agents/services`), but scripts and demos still import the old module path (e.g., `agents.agents` in `scripts/run_agent_delegation_demo.py`)—needs cleanup.
- **Scalability of "Defect Discovery":** Cross-repo RAG stubbed; needs real embedding + Qdrant queries and feedback loops.

## User Review Required
> [!IMPORTANT]
> **Release Security Fix**
> - Revoke the exposed PAT from v2.3.2 notes, generate a new repo-scoped token, update CI/CD secrets, and scrub the token from git history (see `docs/release/GIT_HISTORY_SCRUB_PLAN.md`).
> 
> **Automation Layer Hardening**
> - Approve adding cron dependency (`croniter`), job audit trail, and pause/resume controls to the scheduler UI/API.

## Proposed Changes

### 1. Implement Full Task Automation Layer (shipped as MVP; harden next)
**Goal:** Enable “set and forget” defect/code-review runs.
- **Delivered in v2.4.0:**
    - DB model `ScheduledTask` in `mcp/models.py`.
    - API router `mcp/scheduler_api.py` (list/create/delete), mounted under `/api/scheduler`.
    - Scheduler service `agents/services/scheduler.py` polling DB and dispatching to MCP.
    - UI component `web/src/ScheduledTasks.jsx` surfaced in `web/src/App.jsx`.
- **Gaps to close:**
    - Add cron support dependency (`croniter`) to `requirements.txt` and enforce validation.
    - Add job state toggles (pause/disable) and history view.
    - Add retries/backoff and per-tenant rate limits.
    - Secure API: ensure auth/role checks and avoid task payload injection.

### 2. Refactor `agents` Directory Structure (partially done)
**Goal:** Improve maintainability and separation of concerns.
- **Delivered:** Moved core/impl/services files into the target layout; added import checker `scripts/verify_imports.py`.
- **Next:** Fix lingering imports in scripts (`scripts/run_agent_delegation_demo.py` still uses `agents.agents`), add type hints/tests for `agents/services/scheduler.py`, and document public import surface.

### 3. Documentation Reorganization (done)
**Goal:** Make documentation navigable for different stakeholders.
- **Delivered:** Content moved into `docs/architecture`, `docs/manuals`, `docs/analysis`, `docs/legal`, `docs/release`; new analysis artifacts added.
- **Next:** Add index/TOC and prune binary drafts that do not belong in repo (large PDFs/DOCs were added—decide retention policy).

### 4. Enhance "Defect Discovery" Agent (Use Cases #3, #7, #18, #20, #23 + #28)
**Goal:** Move from simple retrieval to intelligent, cross-repo, evidence-backed detection.

**Delivered (partial in v2.4.0):**
- New `agents/impl/defect_discovery_crewai.py` adds product_line-aware context and Qdrant stub for cross-repo signals.
- `agents/core/rag_config.json` gains repo config; wiring to Qdrant is scaffolded.

**Next:**
- Implement real embedding + Qdrant search (share deterministic embedding helper from `mcp.mcp`).
- Add feedback loop (store confirmed defects) and clustering for systemic patterns.
- Add risk scoring per repo and time window; expose results in UI.
- Add tests covering cross-repo retrieval paths.

### 5. Release Security Fix (critical)
**Goal:** Remove committed credentials and prevent recurrence.
- **Done in docs:** Replaced leaked PAT in `v2.3.2-release.md` with placeholder guidance; added scrub plan doc path reference (`docs/release/GIT_HISTORY_SCRUB_PLAN.md`).
- **Required actions:**
    - Revoke the exposed PAT in GitHub; rotate to a new repo-scoped token stored in secrets.
    - Run history scrub per plan; force-push cleaned branch and re-tag v2.3.2/v2.4.0 if needed.
    - Add pre-commit or CI secret scanner to block future leaks.

## Verification Plan

### Automated Tests
1. **Scheduler Smoke Test:** Create/delete tasks via `/api/scheduler`; assert `next_run_at` updates and jobs dispatch (interval + cron). Add unit tests for `agents/services/scheduler.py` with croniter present/absent.
2. **Refactoring Check:** Run `python scripts/verify_imports.py` and `pytest` to ensure imports succeed post-refactor.
3. **Multi-Repo Query Test:**
    - Configure `rag_config.json` with 2 mock repos.
    - Ingest data into both.
    - Run `DefectDiscoveryCrewAI` and assert cross-repo hits are returned (once Qdrant query implemented).
4. **Secret Scan:** Add CI step (e.g., `gitleaks`) to block committed secrets; verify it fails on seeded test token.

### Manual Verification
1. **Docs Navigation:** Confirm new folder structure and index coverage; decide on removal/retention of large binaries.
2. **UI Test:** Create, view, and delete schedules in `ScheduledTasks` panel; confirm execution in DB and logs.
3. **Security:** Confirm PAT revoked; ensure release notes no longer contain secrets.
