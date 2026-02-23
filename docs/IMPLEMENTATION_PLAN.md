# Implementation Plan for a New Admin

## Goal
Help a new admin set up a fresh Intel-SWE fork in VS Code on RHEL 8, enable GitHub Copilot DUO, and prepare a simple implementation guide that Copilot DUO can follow autonomously to rebuild Intel-SWE. The setup must not be installed at the root level, and containers will use Apptainer instead of Docker.

## What You Will Achieve
- VS Code installed and ready (with Copilot DUO enabled).
- A fork of Intel-SWE cloned to a non-root folder.
- An `IMPLEMENTATION_GUIDE.md` that Copilot can use to rebuild Intel-SWE from the fork.
- Clear instructions for adding more users later.

## Prerequisites (Install These First)
Keep these versions or newer:

- **RHEL 8** (Admin access for installs).
- **VS Code 1.90+** (required).
- **Git 2.44+**.
- **Python 3.11.x via module** (must be loaded with `module load`).
- **Node.js 20 LTS** (for the web UI).
- **Apptainer 1.3+**.
- **GitHub access token** (already available to you).

## Step-by-Step Plan (Simple Language)

### 1. Install and verify tools
1. Install VS Code 1.90 or newer.
2. Install Git and Node.js 20 LTS.
3. Ensure Python 3.11 is available as a module and can be loaded.
4. Install Apptainer 1.3 or newer.

### 2. Open VS Code and enable Copilot DUO
1. Open VS Code.
2. Install the **GitHub Copilot** and **GitHub Copilot Chat** extensions.
3. Sign in to GitHub in VS Code and confirm the DUO license is active.

### 3. Fork and clone Intel-SWE (not at root level)
1. In a browser, navigate to the Intel-SWE repository: **https://github.com/reginaldrhoe/intell-swe**
2. Fork the Intel-SWE repository to your GitHub account.
3. Choose a non-root folder, for example:
   - `/home/<you>/work/intell_swe_fork`
4. Clone your fork into that folder.
5. Open the cloned folder in VS Code.

### 4. Create the implementation guide
1. Use the file named `IMPLEMENTATION_GUIDE.md` in the docs folder.
2. This guide tells Copilot how to rebuild Intel-SWE using Apptainer.
3. Keep it short, step-by-step, and easy to follow.

### 5. Configure databases and target repositories
1. Do not add database passwords or container credentials yet.
2. Use placeholders where needed.
3. Keep tokens in local files only (never commit secrets).
4. Set database URLs to point to the Intel-SWE instance (PostgreSQL, Redis, Qdrant).
5. After first run, use the Settings UI or edit `agents/core/rag_config.json` to add target repositories and branches for analysis.
6. Include the Intel-SWE repository in the config so the admin can manage MCP resources and modify configuration.
7. Target repositories are analyzed by Intel-SWE (read-only for code; write access for issues, merge requests, and queries).
8. Plan for initial full ingestion of both the Intel-SWE fork and all target repositories (can take significant time).
9. Decide at setup time whether to use GitHub or GitLab for the Intel-SWE fork and target repositories (configure OAuth, tokens, and webhooks accordingly).

### 6. Final step: prepare user onboarding
1. Add a short section on how the admin will add new users later.
2. Include RBAC setup details:
   - Decide which auth path is used (OAuth vs token-based).
   - Define default roles for new users (admin, editor, viewer).
   - Record where role mappings live (RBAC file or environment variable) and that it must be updated by the admin.
3. Explain that the admin will instruct Copilot in VS Code to create onboarding steps and docs.

## Success Check
- VS Code is open, Copilot DUO is working.
- The Intel-SWE fork is cloned in a non-root folder.
- `IMPLEMENTATION_GUIDE.md` is ready for Copilot to follow.
- You have a clear plan for adding users later.
