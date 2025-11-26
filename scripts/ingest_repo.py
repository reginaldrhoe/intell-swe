from langchain_community.document_loaders import DirectoryLoader, PythonLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
try:
    from langchain_openai import OpenAIEmbeddings  # type: ignore
except Exception:
    try:
        from langchain_community.embeddings import OpenAIEmbeddings  # type: ignore
    except Exception:
        OpenAIEmbeddings = None
from langchain_community.vectorstores import Qdrant
import os
import shutil
from dotenv import load_dotenv
import argparse
from typing import Optional
import tempfile
import subprocess
import hashlib
import datetime
import getpass
import socket
try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models as qdrant_models
except Exception:
    QdrantClient = None
    qdrant_models = None


def _save_indexed_commit(repo_url: str, branch: str, commit_sha: str, collection: str, file_count: int, chunk_count: int):
    """Save indexed commit information to database for future incremental updates.
    
    Uses direct database access to avoid circular imports with mcp module.
    """
    try:
        # Import database session and model
        import sys
        from pathlib import Path
        project_root = Path(__file__).resolve().parent.parent
        sys.path.insert(0, str(project_root))
        
        from mcp.db import SessionLocal
        from mcp.models import IndexedCommit
        
        db = SessionLocal()
        try:
            # Check if record exists for this repo/branch
            existing = db.query(IndexedCommit).filter(
                IndexedCommit.repo_url == repo_url,
                IndexedCommit.branch == branch,
                IndexedCommit.collection == collection
            ).first()
            
            if existing:
                # Update existing record
                existing.commit_sha = commit_sha
                existing.file_count = file_count
                existing.chunk_count = chunk_count
                existing.indexed_at = datetime.datetime.utcnow()
            else:
                # Create new record
                new_record = IndexedCommit(
                    repo_url=repo_url,
                    branch=branch,
                    commit_sha=commit_sha,
                    collection=collection,
                    file_count=file_count,
                    chunk_count=chunk_count
                )
                db.add(new_record)
            
            db.commit()
            print(f"Saved indexed commit: {repo_url} @ {branch} -> {commit_sha[:8]}")
        finally:
            db.close()
    except Exception as e:
        print(f"Warning: could not save indexed commit to database: {e}")


class DeterministicEmbeddings:
    """Fallback embeddings provider that deterministically maps text -> fixed-dim vector.
    Implements `embed_documents` and `embed_query` to match LangChain's Embeddings API."""
    def __init__(self, dim: int = 64):
        self.dim = dim

    def _embed(self, text: str):
        h = hashlib.sha256(text.encode("utf-8")).digest()
        reps = (self.dim + len(h) - 1) // len(h)
        data = (h * reps)[: self.dim]
        # map bytes 0..255 to float -1..1
        vec = [((b / 255.0) * 2.0 - 1.0) for b in data]
        # normalize
        import math

        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec

    def embed_documents(self, texts):
        return [self._embed(t) for t in texts]

    def embed_query(self, text):
        return self._embed(text)

# Load environment variables from .env file
load_dotenv()


def get_changed_files(repo_dir: str, from_commit: Optional[str], to_commit: str):
    """Compare two commits and return lists of added, modified, and deleted files.
    
    Args:
        repo_dir: Path to git repository
        from_commit: Previous commit SHA (None for full index)
        to_commit: Current commit SHA
        
    Returns:
        dict with keys: 'added', 'modified', 'deleted' (lists of file paths)
    """
    if not from_commit:
        # No previous commit - this is a full index
        return None
    
    try:
        result = subprocess.run(
            ["git", "-C", repo_dir, "diff", "--name-status", from_commit, to_commit],
            capture_output=True,
            text=True,
            check=True
        )
        
        changes = {"added": [], "modified": [], "deleted": []}
        
        for line in result.stdout.strip().splitlines():
            if not line:
                continue
            parts = line.split("\t", 1)
            if len(parts) != 2:
                continue
            status, path = parts
            
            # Filter for Python files only
            if not path.endswith(".py"):
                continue
                
            if status == "A":
                changes["added"].append(path)
            elif status == "M":
                changes["modified"].append(path)
            elif status == "D":
                changes["deleted"].append(path)
            elif status.startswith("R"):  # Rename
                # Renamed files show as "R100\told.py\tnew.py"
                if "\t" in path:
                    old_path, new_path = path.split("\t", 1)
                    changes["deleted"].append(old_path)
                    changes["added"].append(new_path)
        
        print(f"Git diff from {from_commit[:8]} to {to_commit[:8]}:")
        print(f"  Added: {len(changes['added'])} files")
        print(f"  Modified: {len(changes['modified'])} files")
        print(f"  Deleted: {len(changes['deleted'])} files")
        
        return changes
    except Exception as e:
        print(f"Warning: git diff failed ({e}), will perform full index")
        return None


def ingest_repo(repo_dir: Optional[str] = None, collection: Optional[str] = None, qdrant_url: Optional[str] = None, repo_url: Optional[str] = None, branch: Optional[str] = None, commit: Optional[str] = None, previous_commit: Optional[str] = None):
    # If repo_url provided, clone into a temp dir and use that
    temp_dir = None
    if repo_url:
        if repo_url.startswith("http") or repo_url.endswith(".git"):
            temp_dir = tempfile.mkdtemp(prefix="ingest_repo_")
            print(f"Cloning {repo_url} into {temp_dir}...")
            try:
                if branch:
                    subprocess.check_call(["git", "clone", "--branch", branch, "--single-branch", repo_url, temp_dir])
                else:
                    subprocess.check_call(["git", "clone", repo_url, temp_dir])
                repo_dir = temp_dir
                # If a specific commit SHA was provided, attempt to checkout that commit
                if commit:
                    try:
                        subprocess.check_call(["git", "-C", temp_dir, "checkout", commit])
                    except Exception:
                        print(f"Warning: failed to checkout commit {commit}")
            except Exception as e:
                print("Failed to clone repo:", e)
                if temp_dir:
                    try:
                        shutil.rmtree(temp_dir)
                    except Exception:
                        pass
                raise

    # Default to the repo root (parent of scripts/)
    if repo_dir is None:
        repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Get current commit SHA for comparison
    current_commit_sha = None
    current_branch_name = None
    git_dir = temp_dir or repo_dir  # Use temp_dir if cloned, otherwise local repo_dir
    
    try:
        current_commit_sha = subprocess.check_output(["git", "-C", git_dir, "rev-parse", "HEAD"]).decode().strip()
        try:
            br = subprocess.check_output(["git", "-C", git_dir, "rev-parse", "--abbrev-ref", "HEAD"]).decode().strip()
            if br and br != "HEAD":
                current_branch_name = br
            elif branch:
                current_branch_name = branch
        except Exception:
            current_branch_name = branch
    except Exception as e:
        print(f"Warning: could not get git commit SHA: {e}")
    
    # Detect changed files for incremental update
    changed_files = None
    if previous_commit and current_commit_sha and git_dir:
        changed_files = get_changed_files(git_dir, previous_commit, current_commit_sha)
    
    # If we have changed files, we can do incremental update
    incremental = changed_files is not None
    files_to_delete = changed_files["deleted"] if incremental else []
    files_to_index = (changed_files["added"] + changed_files["modified"]) if incremental else None

    print(f"Loading Python files from {repo_dir}...")

    # Load Python files from the repo (excluding venv and git)
    if incremental and files_to_index is not None:
        # Incremental: only load changed files
        print(f"Incremental update: loading {len(files_to_index)} changed files")
        docs = []
        for file_path in files_to_index:
            full_path = os.path.join(git_dir, file_path)
            if os.path.exists(full_path):
                try:
                    loader = PythonLoader(full_path)
                    file_docs = loader.load()
                    docs.extend(file_docs)
                except Exception as e:
                    print(f"Warning: failed to load {file_path}: {e}")
            else:
                print(f"Warning: file not found: {full_path}")
    else:
        # Full index: load all Python files
        print("Full index: loading all Python files")
        loader = DirectoryLoader(
            repo_dir,
            glob="**/*.py",
            loader_cls=PythonLoader,
            recursive=True,
            # Exclude common non-source directories
            exclude=["**/.venv/**", "**/.git/**", "**/node_modules/**", "**/__pycache__/**"],
        )
        docs = loader.load()
    print(f"Loaded {len(docs)} Python files:")
    for doc in docs:
        print(" -", doc.metadata.get("source", "<unknown>"))

    # Split documents into chunks
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(docs)
    print(f"Split into {len(chunks)} chunks")

    # Embed and store in Qdrant
    print("Creating embeddings and storing in Qdrant...")
    # Determine embedding dimension from env or default
    dim = int(os.getenv("RAG_EMBED_DIM", "64"))
    embeddings = None
    if OpenAIEmbeddings is not None:
        try:
            embeddings = OpenAIEmbeddings()
        except Exception:
            embeddings = None
    if embeddings is None:
        print("OpenAI embeddings not available or failed — using deterministic fallback")
        embeddings = DeterministicEmbeddings(dim=dim)

    # Allow configuring Qdrant URL via environment variable; default to the
    # compose service hostname so this works when run inside the mcp container.
    qdrant_url = qdrant_url or os.getenv("QDRANT_URL") or "http://qdrant:6333"
    collection = collection or os.getenv("RAG_COLLECTION") or "rag-poc"

    # LangChain Qdrant wrapper may require different parameters depending on versions; pass url and collection_name when available
    # Add audit metadata to each chunk so ingestions are traceable
    ingested_by = os.getenv("RAG_INGESTOR") or os.getenv("RAG_INGESTED_BY") or "agentic-ingest"
    ingested_at = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    ingested_via = os.getenv("RAG_INGEST_VIA") or os.path.basename(__file__)
    ingested_host = os.getenv("RAG_INGEST_HOST") or socket.gethostname()
    revision = None
    current_branch = None
    try:
        # Use the commit SHA we already retrieved earlier
        if current_commit_sha:
            revision = current_commit_sha
            current_branch = current_branch_name
    except Exception:
        revision = None
        current_branch = branch

    for doc in chunks:
        meta = dict(doc.metadata or {})
        meta.setdefault("ingested_at", ingested_at)
        meta.setdefault("ingested_by", ingested_by)
        meta.setdefault("ingested_via", ingested_via)
        meta.setdefault("ingested_host", ingested_host)
        meta.setdefault("ingested_from", repo_url or repo_dir)
        if revision:
            meta.setdefault("revision", revision)
            meta.setdefault("commit_sha", revision)  # Normalized field for queries
        if current_branch:
            meta.setdefault("branch", current_branch)
        # Add file path for targeted deletion/updates
        file_path = meta.get("source")
        if file_path:
            # Normalize to relative path if possible
            if repo_dir and file_path.startswith(repo_dir):
                file_path = os.path.relpath(file_path, repo_dir)
            meta.setdefault("file_path", file_path)
        meta.setdefault("indexed_at", ingested_at)  # Queryable timestamp
        doc.metadata = meta

    # Ensure the Qdrant collection exists with the correct vector size.
    # Prefer the LangChain `Qdrant` wrapper by default to allow tests to
    # monkeypatch that symbol without the code trying to connect to a
    # real qdrant instance. Use the lower-level `qdrant_client` only when
    # explicitly requested via `QDRANT_FORCE_CLIENT=1`.
    use_qdrant_client = bool(QdrantClient is not None and qdrant_models is not None and os.getenv("QDRANT_FORCE_CLIENT") == "1")
    if use_qdrant_client:
        try:
            client = QdrantClient(url=qdrant_url)
            # determine vector size from the embeddings implementation
            try:
                sample_vec = embeddings.embed_query("__vector_size_probe__")
                vec_size = len(sample_vec)
            except Exception:
                vec_size = int(os.getenv("RAG_EMBED_DIM", "64"))

            try:
                client.get_collection(collection_name=collection)
                print(f"Qdrant collection '{collection}' already exists.")
            except Exception:
                print(f"Creating Qdrant collection '{collection}' with size={vec_size}...")
                params = qdrant_models.VectorParams(size=vec_size, distance=qdrant_models.Distance.COSINE)
                client.recreate_collection(collection_name=collection, vectors_config=params)
        except Exception as e:
            print("Warning: failed to precreate collection via qdrant-client:", e)

    # Prefer direct qdrant-client upsert to avoid LangChain wrapper/version incompatibilities
    if use_qdrant_client:
        client = QdrantClient(url=qdrant_url)
        # determine vector size
        try:
            sample_vec = embeddings.embed_query("__vector_size_probe__")
            vec_size = len(sample_vec)
        except Exception:
            vec_size = int(os.getenv("RAG_EMBED_DIM", "64"))

        try:
            client.get_collection(collection_name=collection)
            print(f"Qdrant collection '{collection}' already exists.")
        except Exception:
            print(f"Creating collection '{collection}' (vec_size={vec_size}) via qdrant-client")
            params = qdrant_models.VectorParams(size=vec_size, distance=qdrant_models.Distance.COSINE)
            client.recreate_collection(collection_name=collection, vectors_config=params)

        # Delete points for deleted files (incremental update)
        if incremental and files_to_delete:
            print(f"Deleting {len(files_to_delete)} removed files from Qdrant...")
            for deleted_file in files_to_delete:
                try:
                    # Normalize path to match what's stored in metadata
                    normalized_path = deleted_file.replace("\\", "/")
                    client.delete(
                        collection_name=collection,
                        points_selector=qdrant_models.FilterSelector(
                            filter=qdrant_models.Filter(
                                must=[
                                    qdrant_models.FieldCondition(
                                        key="file_path",
                                        match=qdrant_models.MatchValue(value=normalized_path)
                                    )
                                ]
                            )
                        )
                    )
                    print(f"  Deleted points for: {deleted_file}")
                except Exception as e:
                    print(f"  Warning: failed to delete {deleted_file}: {e}")

        texts = [d.page_content for d in chunks]
        vectors = embeddings.embed_documents(texts)
        points = []
        for i, (vec, doc) in enumerate(zip(vectors, chunks)):
            payload = dict(doc.metadata or {})
            payload["page_content"] = doc.page_content
            # use integer id to satisfy PointStruct validation
            points.append(qdrant_models.PointStruct(id=i, vector=vec, payload=payload))

        if points:
            client.upsert(collection_name=collection, points=points)
            print(f"Upserted {len(points)} points into '{collection}' via qdrant-client")
        
        # Store indexed commit info for future incremental updates
        if current_commit_sha:
            # Use repo_url if available, otherwise use repo_dir as identifier
            repo_identifier = repo_url or repo_dir or "unknown"
            try:
                # Save to database via API call or direct DB access
                _save_indexed_commit(
                    repo_url=repo_identifier,
                    branch=current_branch or branch or "main",
                    commit_sha=current_commit_sha,
                    collection=collection,
                    file_count=len(docs),
                    chunk_count=len(chunks)
                )
            except Exception as e:
                print(f"Warning: failed to save indexed commit: {e}")
        
        return
    # Fall back to LangChain wrapper only if qdrant-client isn't available
    vectorstore = Qdrant.from_documents(
        chunks,
        embeddings,
        url=qdrant_url,
        collection_name=collection,
    )
    print(f"Ingested via LangChain Qdrant wrapper into '{collection}'")
    return
    print(f"Ingested {len(chunks)} chunks into Qdrant collection '{collection}'.")
    if temp_dir:
        try:
            import shutil
            shutil.rmtree(temp_dir)
        except Exception:
            pass


def _cli():
    p = argparse.ArgumentParser(description="Ingest repo into Qdrant for RAG")
    p.add_argument("--repo", help="Path to repository root (defaults to project root)")
    p.add_argument("--repo-url", help="Remote repository URL to clone (overrides --repo)")
    p.add_argument("--branch", help="Branch or ref to check out when cloning (e.g. 'main' or 'refs/heads/main')")
    p.add_argument("--commit", help="Specific commit SHA to check out after cloning")
    p.add_argument("--previous-commit", help="Previous commit SHA for incremental diff-based update")
    p.add_argument("--collection", help="Qdrant collection name (defaults to env RAG_COLLECTION or 'rag-poc')")
    p.add_argument("--qdrant", help="Qdrant URL (defaults to env QDRANT_URL or http://qdrant:6333)")
    args = p.parse_args()
    ingest_repo(repo_dir=args.repo, collection=args.collection, qdrant_url=args.qdrant, repo_url=args.repo_url, branch=args.branch, commit=args.commit, previous_commit=args.previous_commit)


if __name__ == "__main__":
    _cli()
