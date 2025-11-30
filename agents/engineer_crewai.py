from .crewai_adapter import CrewAIAdapter
from .agents import Agent
import asyncio
import os
import hashlib
import subprocess
import re
from typing import Optional, List, Dict, Any

try:
    from qdrant_client import QdrantClient
except Exception:
    QdrantClient = None


def get_commit_summary(commit_sha: str, repo_path: Optional[str] = None) -> Optional[str]:
    """Get commit summary including metadata, changed files, and diffs.
    
    Args:
        commit_sha: Git commit SHA (full or abbreviated)
        repo_path: Path to git repository (defaults to GIT_REPO_PATH env or /repo)
    
    Returns:
        Formatted commit summary or None if git command fails
    """
    try:
        # Use mounted git repo path from environment
        cwd = repo_path or os.getenv("GIT_REPO_PATH") or "/repo"
        
        # Get commit metadata and stats
        result = subprocess.run(
            ["git", "--git-dir", f"{cwd}/.git", "--work-tree", f"{cwd}/workspace", 
             "show", commit_sha, "--stat", "--pretty=format:%H%n%an <%ae>%n%ad%n%s%n%b", "--date=iso"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return None
            
        output = result.stdout
        
        # Get file changes with diff summary
        diff_result = subprocess.run(
            ["git", "--git-dir", f"{cwd}/.git", "--work-tree", f"{cwd}/workspace",
             "diff-tree", "--no-commit-id", "--name-status", "-r", commit_sha],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if diff_result.returncode == 0:
            output += f"\n\n=== File Changes ===\n{diff_result.stdout}"
        
        return output
    except Exception as e:
        return f"Error fetching commit: {str(e)}"


def get_file_content(file_path: str, commit_sha: Optional[str] = None, repo_path: Optional[str] = None, max_lines: int = 200) -> Optional[str]:
    """Get file content from a specific commit or current state.
    
    Args:
        file_path: Path to file relative to repo root
        commit_sha: Optional commit SHA (if None, uses current state)
        repo_path: Path to git repository
        max_lines: Maximum lines to return
    
    Returns:
        File content or None if unavailable
    """
    try:
        # Use mounted git repo path from environment
        cwd = repo_path or os.getenv("GIT_REPO_PATH") or "/repo"
        
        if commit_sha:
            cmd = ["git", "--git-dir", f"{cwd}/.git", "show", f"{commit_sha}:{file_path}"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        else:
            full_path = os.path.join(f"{cwd}/workspace", file_path)
            result = subprocess.run(["cat", full_path], capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            return None
        
        lines = result.stdout.splitlines()
        if len(lines) > max_lines:
            return "\n".join(lines[:max_lines]) + f"\n... ({len(lines) - max_lines} more lines)"
        return result.stdout
    except Exception:
        return None


def parse_git_references(text: str) -> Dict[str, Any]:
    """Parse git commit references and branch names from task text.
    
    Detects patterns like:
    - commit:37c2ed14, commit 37c2ed14
    - branch:main, branch main
    - SHA: abc123def
    - #37c2ed14
    
    Returns:
        Dict with 'commits' (list), 'branches' (list), 'files' (list)
    """
    result = {"commits": [], "branches": [], "files": []}
    
    if not text:
        return result
    
    # Pattern 1: commit:SHA or commit SHA
    commit_patterns = [
        r'commit[:\s]+([a-f0-9]{7,40})',
        r'SHA[:\s]+([a-f0-9]{7,40})',
        r'#([a-f0-9]{7,40})',
        r'\b([a-f0-9]{40})\b',  # full SHA
        r'\b([a-f0-9]{7,9})\b',  # short SHA (7-9 chars to avoid false positives)
    ]
    
    for pattern in commit_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        result["commits"].extend(matches)
    
    # Pattern 2: branch:name or branch name
    branch_patterns = [
        r'branch[:\s]+([a-zA-Z0-9/_-]+)',
        r'on\s+([a-zA-Z0-9/_-]+)\s+branch',
    ]
    
    for pattern in branch_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        result["branches"].extend(matches)
    
    # Deduplicate
    result["commits"] = list(set(result["commits"]))
    result["branches"] = list(set(result["branches"]))
    
    return result


class EngineerCodeReviewCrewAI(Agent):
    """Engineer code review agent backed by CrewAIAdapter.

    The agent builds a concise prompt from the task and asks CrewAI to
    produce a review summary and suggested fixes.
    """
    def __init__(self, name: str = "EngineerCrewAI"):
        super().__init__(name)
        self.adapter = CrewAIAdapter()

    async def process(self, task):
        import logging
        logger = logging.getLogger("EngineerCrewAI")
        
        title = task.get("title", "Code review")
        desc = task.get("description", "")
        files = task.get("files", [])
        
        logger.info(f"EngineerCrewAI processing task: title={title}, desc_len={len(desc)}, desc_preview={desc[:100] if desc else 'EMPTY'}")
        
        # OPTION 4: Parse git references from task title/description
        git_refs = parse_git_references(f"{title} {desc}")
        logger.info(f"Parsed git refs: {git_refs}")
        git_context = []
        
        # OPTION 3: If commits are detected, fetch git data directly
        if git_refs.get("commits"):
            for commit_sha in git_refs["commits"][:3]:  # Limit to 3 commits
                try:
                    logger.info(f"Fetching git summary for commit: {commit_sha}")
                    commit_summary = await asyncio.to_thread(get_commit_summary, commit_sha)
                    if commit_summary:
                        git_context.append(f"\n=== Commit {commit_sha} ===\n{commit_summary}")
                        logger.info(f"Successfully fetched commit {commit_sha}, summary length: {len(commit_summary)}")
                    else:
                        logger.warning(f"get_commit_summary returned None for {commit_sha}")
                except Exception as e:
                    logger.exception(f"Error fetching commit {commit_sha}: {e}")
        
        # OPTION 2: If no git context and no explicit files, try RAG/Qdrant retrieval
        if not git_context and not files:
            try:
                collection = (os.getenv("RAG_COLLECTION") or "rag-poc")
                qurl = os.getenv("QDRANT_URL") or "http://qdrant:6333"
                if QdrantClient is not None:
                    client = QdrantClient(url=qurl)
                    # craft a simple query vector using a deterministic embedding
                    query_text = f"{title}\n{desc}"
                    def _deterministic_embed(text, dim=64):
                        h = hashlib.sha256(text.encode("utf-8")).digest()
                        reps = (dim + len(h) - 1) // len(h)
                        data = (h * reps)[:dim]
                        vec = [((b / 255.0) * 2.0 - 1.0) for b in data]
                        # normalize
                        import math
                        norm = math.sqrt(sum(v * v for v in vec))
                        if norm > 0:
                            vec = [v / norm for v in vec]
                        return vec

                    qvec = _deterministic_embed(query_text, dim=int(os.getenv("RAG_EMBED_DIM", "64")))
                    try:
                        hits = client.search(collection_name=collection, query_vector=qvec, limit=5)
                        rag_files = []
                        for h in hits:
                            payload = h.payload or {}
                            src = payload.get("path") or payload.get("source") or payload.get("ingested_from")
                            snippet = (payload.get("page_content") or "").strip().replace("\n", " ")[:800]
                            rag_files.append(f"{src}: {snippet}")
                        if rag_files:
                            files = rag_files
                    except Exception:
                        # fall back to empty files list if qdrant search fails
                        pass
            except Exception:
                pass
        
        # Build enhanced prompt with git context, artifacts summary, RAG files, or explicit files
        context_parts = []
        art_sum = task.get("artifact_summary")
        if art_sum:
            context_parts.append("=== Attached Test Artifacts Summary ===")
            context_parts.append(str(art_sum))
        if git_context:
            context_parts.append("=== Git Commit Data ===")
            context_parts.extend(git_context)
        if files:
            context_parts.append(f"\n=== Relevant Files ===\n{files}")
        
        context_str = "\n".join(context_parts) if context_parts else "No specific context available"
        
        grounding = ("Ground your analysis strictly in the attached artifacts summary when present. "
                     "If a requested detail is not present, state 'not available from artifacts'. "
                     "Do not invent test names or counts.")

        prompt = (
            f"You are an expert Python engineer. Perform a detailed code review and analysis.\n\n"
            f"Task: {title}\n"
            f"Description: {desc}\n\n"
            f"{context_str}\n\n"
            f"{grounding}\n\n"
            f"Provide:\n"
            f"1. A concise summary of what changed (if commit data available)\n"
            f"2. Key functionality added or modified\n"
            f"3. Potential defects or issues\n"
            f"4. 3-5 concrete suggestions for improvement\n"
        )
        
        # OPTION 1: Delegate to adapter (uses OpenAI if OPENAI_API_KEY is set, otherwise stub)
        res = await self.adapter.run(prompt)
        # Ensure a string return
        text = res.get("text") if isinstance(res, dict) else str(res)
        logger.info(f"Agent result length: {len(text)}, has_git_context: {len(git_context) > 0}, preview: {text[:200]}")
        return {"agent": self.name, "result": text}
