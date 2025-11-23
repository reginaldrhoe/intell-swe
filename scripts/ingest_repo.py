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


def ingest_repo(repo_dir: Optional[str] = None, collection: Optional[str] = None, qdrant_url: Optional[str] = None, repo_url: Optional[str] = None):
    # If repo_url provided, clone into a temp dir and use that
    temp_dir = None
    if repo_url:
        if repo_url.startswith("http") or repo_url.endswith(".git"):
            temp_dir = tempfile.mkdtemp(prefix="ingest_repo_")
            print(f"Cloning {repo_url} into {temp_dir}...")
            try:
                subprocess.check_call(["git", "clone", repo_url, temp_dir])
                repo_dir = temp_dir
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

    print(f"Loading Python files from {repo_dir}...")

    # Load Python files from the repo (excluding venv and git)
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
    try:
        # If we cloned the repo, try to read the HEAD commit
        if temp_dir:
            rev = subprocess.check_output(["git", "-C", temp_dir, "rev-parse", "HEAD"]).decode().strip()
            revision = rev
    except Exception:
        revision = None

    for doc in chunks:
        meta = dict(doc.metadata or {})
        meta.setdefault("ingested_at", ingested_at)
        meta.setdefault("ingested_by", ingested_by)
        meta.setdefault("ingested_via", ingested_via)
        meta.setdefault("ingested_host", ingested_host)
        meta.setdefault("ingested_from", repo_url or repo_dir)
        if revision:
            meta.setdefault("revision", revision)
        doc.metadata = meta

    # Ensure the Qdrant collection exists with the correct vector size.
    # Try to create the collection using qdrant-client if available to avoid
    # LangChain wrapper recreation issues across versions.
    if QdrantClient is not None and qdrant_models is not None:
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
    if QdrantClient is not None and qdrant_models is not None:
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

        texts = [d.page_content for d in chunks]
        vectors = embeddings.embed_documents(texts)
        points = []
        for i, (vec, doc) in enumerate(zip(vectors, chunks)):
            payload = dict(doc.metadata or {})
            payload["page_content"] = doc.page_content
            # use integer id to satisfy PointStruct validation
            points.append(qdrant_models.PointStruct(id=i, vector=vec, payload=payload))

        client.upsert(collection_name=collection, points=points)
        print(f"Upserted {len(points)} points into '{collection}' via qdrant-client")
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
    p.add_argument("--collection", help="Qdrant collection name (defaults to env RAG_COLLECTION or 'rag-poc')")
    p.add_argument("--qdrant", help="Qdrant URL (defaults to env QDRANT_URL or http://qdrant:6333)")
    args = p.parse_args()
    ingest_repo(repo_dir=args.repo, collection=args.collection, qdrant_url=args.qdrant, repo_url=args.repo_url)


if __name__ == "__main__":
    _cli()
