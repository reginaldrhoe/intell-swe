# Git History Scrub & Secret Rotation Plan

This document outlines a safe, staged approach to rotate exposed secrets and (optionally) rewrite Git history to remove any previously-committed secrets.

Important: Rewriting history is disruptive for all collaborators. Coordinate with your team and ensure everyone knows how to update local clones after a rewrite.

1) Immediate (no-history-change)
- Rotate any secrets that may have been committed (change keys in provider console, delete old keys).
- Remove secrets from the working tree and stop tracking them:
  - Add secrets to `.gitignore` (e.g., `.env`).
  - `git rm --cached .env` then commit and push.
- Issue: Key rotation is the only reliable way to prevent active misuse. Always rotate any leaked API keys.

2) Short-term (recommended)
- Run a scan for sensitive values in history using `git log --all --pretty=format:%H` and `git grep` on each commit, or use tools like `truffleHog`, `git-secrets`, or `gitleaks`.
- Collect a list of commits and files that contain secrets.
- Create a remediation branch so you can test the rewrite without touching `main` directly.

3) History rewrite options
Option A: BFG Repo-Cleaner (simpler)
- Install: `brew install bfg` or download jar
- Example to remove `.env` contents and replace with placeholder:
  - `git clone --mirror git@github.com:your/repo.git`
  - `bfg --delete-files .env repo.git` or use `--replace-text` with a file mapping secrets to placeholders
  - `cd repo.git && git reflog expire --expire=now --all && git gc --prune=now --aggressive`
  - `git push --force` (to remote) — coordinate with team

Option B: git filter-repo (recommended modern tool)
- Install: `pip install git-filter-repo` or use system package
- Example to remove a file from all history:
  - `git clone --mirror git@github.com:your/repo.git`
  - `git -C repo.git filter-repo --invert-paths --path .env`
  - `git -C repo.git reflog expire --expire=now --all && git -C repo.git gc --prune=now --aggressive`
  - `git push --force`

4) After the rewrite
- Communicate to all contributors to re-clone the repository or follow the recommended steps to reset local branches.
- Verify CI and deploys that may rely on secrets stored in repo — update secrets to use a vault/CI secret storage.

5) Long-term hardening
- Add pre-commit checks to block committing `.env` or common secret patterns (`pre-commit`, `gitleaks` as git hook).
- Add CI checks scanning for secrets on PRs (GitHub Actions using `gitleaks-action` or similar).
- Move secrets into environment variables or a secrets manager (AWS Secrets Manager, Azure Key Vault, HashiCorp Vault, GitHub Actions secrets, etc.).

6) Notes and cautions
- Force-pushing rewritten history will break forks and clones. Only do this when you can coordinate.
- Rewriting history does not remove copies already cloned by third parties or cached in backups.
- Rotating keys is the most important immediate action.

If you want, I can:
- Draft the exact `git-filter-repo` or BFG commands for your repository and produce a step-by-step checklist for execution.
- Create a PR that adds `pre-commit` config and a CI job to run `gitleaks` on PRs.
