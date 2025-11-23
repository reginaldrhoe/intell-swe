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

# Load environment variables from .env file
load_dotenv()


def ingest_repo(repo_dir: Optional[str] = None, collection: Optional[str] = None, qdrant_url: Optional[str] = None, repo_url: Optional[str] = None):
    # Default to the repo root (parent of scripts/)
    if repo_dir is None and not repo_url:
        repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    print(f"Loading Python files from {repo_dir}...")

    # Load Python files from the repo (excluding venv and git)
    loader = DirectoryLoader(
        repo_dir,
        glob="**/*.py",
        loader_cls=PythonLoader,
        recursive=True,
        # Exclude common non-source directories
        exclude=["**/.venv/**", "**/.git/**", "**/node_modules/**", "**/__pycache__/**"]
    )

    docs = loader.load()
    print(f"Loaded {len(docs)} Python files:")
    for doc in docs:
        print(" -", doc.metadata.get("source", "<unknown>"))

    # Split documents into chunks
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(docs)
    print(f"Split into {len(chunks)} chunks")

    # If a repo_url was provided (GitHub url), clone it into a temp dir first
    temp_dir = None
    if repo_url and (repo_url.startswith('http') or repo_url.endswith('.git')):
        import tempfile
        import subprocess
        temp_dir = tempfile.mkdtemp(prefix='ingest_repo_')
        print(f"Cloning {repo_url} into {temp_dir}...")
        try:
            subprocess.check_call(['git', 'clone', repo_url, temp_dir])
            # reload loader to point at clone
            loader = DirectoryLoader(
                temp_dir,
                glob="**/*.py",
                loader_cls=PythonLoader,
                recursive=True,
                exclude=["**/.venv/**", "**/.git/**", "**/node_modules/**", "**/__pycache__/**"]
            )
            docs = loader.load()
        except Exception as e:
            print("Failed to clone repo:", e)
            if temp_dir:
                try:
                    import shutil
                    shutil.rmtree(temp_dir)
                except Exception:
                    pass
            raise

    # Embed and store in Qdrant
    print("Creating embeddings and storing in Qdrant...")
    embeddings = OpenAIEmbeddings()

    # Allow configuring Qdrant URL via environment variable; default to the
    # compose service hostname so this works when run inside the mcp container.
    qdrant_url = qdrant_url or os.getenv("QDRANT_URL") or "http://qdrant:6333"
    collection = collection or os.getenv("RAG_COLLECTION") or "rag-poc"

    vectorstore = Qdrant.from_documents(
        chunks,
        embeddings,
        url=qdrant_url,
        collection_name=collection
    )
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
    p.add_argument("--collection", help="Qdrant collection name (defaults to env RAG_COLLECTION or 'rag-poc')")
    p.add_argument("--qdrant", help="Qdrant URL (defaults to env QDRANT_URL or http://qdrant:6333)")
    args = p.parse_args()
    ingest_repo(repo_dir=args.repo, collection=args.collection, qdrant_url=args.qdrant)


if __name__ == "__main__":
    _cli()
