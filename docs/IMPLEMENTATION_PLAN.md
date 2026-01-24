# Architectural Review & Improvement Plan

## Goal Description
Review the `/docs` and current codebase to assess the `agentic-rag_poc` "Intelligent Defect Framework" and suggest architectural improvements. This document outlines the findings and proposes a roadmap for enhancing automation, scalability, and maintainability.

## Current Architecture Assessment

**Strengths:**
- **Multi-Source Intelligence:** The combination of Git (temporal), Qdrant (semantic), and LLM (reasoning) is a strong, defensible architecture.
- **Incremental Sync:** The diff-based ingestion capability is efficient.
- **Concurrency Control:** The distributed locking mechanism (`mcp/redis_lock.py`) effectively handles duplicate tasks.

**Weaknesses & Gaps:**
- **Missing Automation Layer:** No user-facing way to schedule recurring tasks.
- **Codebase Structure:** The `agents/` directory is cluttered.
- **Documentation Organization:** The `/docs` directory is hard to navigate.
- **Scalability of "Defect Discovery":** Lacks feedback loops and cross-repository intelligence.

## User Review Required
> [!IMPORTANT]
> **Approval needed for "Automation Layer" Implementation**
> The most significant proposed change is the addition of a full database model and API for `ScheduledTasks`. This requires schema changes to `mcp/models.py` and new frontend components.

## Proposed Changes

### 1. Implement Full Task Automation Layer
**Goal:** Enable users to define "set and forget" schedules for defect discovery and code review.
- **Backend (`mcp`):**
    - [NEW] `ScheduledTask` model in `models.py`.
    - [NEW] API endpoints in `mcp.py`: `POST /schedules`, `GET /schedules`, `DELETE /schedules/{id}`.
    - [MODIFY] `agents/scheduler.py`: Upgrade `SimpleScheduler` to load jobs from DB.
- **Frontend (`web`):**
    - [NEW] `SchedulerDashboard.jsx`: UI to manage recurring tasks.

### 2. Refactor `agents` Directory Structure
**Goal:** Improve maintainability and separation of concerns.
- **Proposed Structure:**
    - `agents/core/`: Base classes & adapters.
    - `agents/impl/`: Specific agent implementations.
    - `agents/tools/`: Shared tools (Git, Qdrant).
    - `agents/services/`: Background services.

### 3. Documentation Reorganization
**Goal:** Make documentation navigable for different stakeholders.
- **Proposed Structure:** `docs/architecture/`, `docs/manuals/`, `docs/analysis/`, `docs/legal/`, `docs/release/`.

### 4. Enhance "Defect Discovery" Agent (Use Cases #3, #7, #18, #20, #23 + New #28)
**Goal:** Move from simple retrieval to "Intelligent Framework" with learning and cross-repo capabilities.

**Features:**
- **Blame Analysis (Auto-Assign):** Automatically identify "Risky Committers" via `git blame` on detected defects (Use Case #3).
- **Feedback Loop (Prediction):** Store confirmed defects to fine-tune future searches and predict "Risky Timeframes" (Use Case #7, #20).
- **Systemic Pattern Detection:** Clustering of defects to find root causes (Use Case #23, #18).
- **[NEW] Cross-Repo Defect Comparison (New Use Case #28):**
    - **Description:** Compare defects across other product line repositories to identify shared vulnerabilities or patterns (e.g., "Do we have this same auth bug in our Payment Service?").
    - **Design:**
        - **Multi-Collection Querying:** Update `DefectDiscoveryAgent` to query Qdrant collections for *all* configured repositories in `rag_config.json`.
        - **Shared Taxonomy:** Ensure embeddings use a consistent model across repos to allow cross-repo similarity search.
        - **Config Update:** Enhance `rag_config.json` to group repos by "Product Line".

## Verification Plan

### Automated Tests
1. **Scheduler Smoke Test:** Verify scheduled task creation and execution.
2. **Refactoring Check:** Run `pytest` to ensure imports are correct.
3. **Multi-Repo Query Test:**
    - Configure `rag_config.json` with 2 mock repos.
    - Ingest data into both.
    - Run `DefectDiscoveryAgent` and assert it returns results from *both* repositories.

### Manual Verification
1. **Docs Navigation:** Check folder structure.
2. **UI Test:** Verify Scheduler UI.
