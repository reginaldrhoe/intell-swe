import types
from types import SimpleNamespace

from scripts import ingest_repo as ingest_module


def test_ingest_repo_monkeypatched(monkeypatch, tmp_path):
    called = {}

    # Fake loader that returns one simple document
    class DummyLoader:
        def __init__(self, repo_dir, **kwargs):
            self.repo_dir = repo_dir

        def load(self):
            doc = SimpleNamespace()
            doc.metadata = {"source": str(tmp_path / "a.py")}
            doc.page_content = "print('hello')\n"
            return [doc]

    # Fake splitter that returns the same docs as chunks
    class DummySplitter:
        def __init__(self, **kwargs):
            pass

        def split_documents(self, docs):
            return docs

    # Fake embeddings factory
    class DummyEmbeddings:
        def __call__(self):
            return object()

    # Fake Qdrant vectorstore
    class DummyQdrant:
        @classmethod
        def from_documents(cls, chunks, embeddings, url=None, collection_name=None):
            called['chunks'] = chunks
            called['url'] = url
            called['collection'] = collection_name
            return cls()

    # Apply monkeypatches to avoid requiring real langchain/qdrant
    monkeypatch.setattr(ingest_module, 'DirectoryLoader', DummyLoader)
    monkeypatch.setattr(ingest_module, 'RecursiveCharacterTextSplitter', DummySplitter)
    monkeypatch.setattr(ingest_module, 'OpenAIEmbeddings', lambda: DummyEmbeddings())
    monkeypatch.setattr(ingest_module, 'Qdrant', DummyQdrant)

    # create a small file to represent repo contents
    file_path = tmp_path / "a.py"
    file_path.write_text("print('ok')\n")

    ingest_module.ingest_repo(repo_dir=str(tmp_path), collection='test-collection', qdrant_url='http://localhost:6333')

    assert called.get('collection') == 'test-collection'
    assert called.get('url') == 'http://localhost:6333'
    assert isinstance(called.get('chunks'), list)
