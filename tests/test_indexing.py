import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from src import indexing
from src.contracts import SourceChunk


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_CHUNKS = ROOT / "tests" / "fixtures" / "sample_chunks.jsonl"


def test_builds_and_reloads_local_vector_index_with_chunk_mapping(tmp_path, monkeypatch):
    loaded_chunks = indexing.load_chunks(SAMPLE_CHUNKS)
    assert loaded_chunks
    assert all(isinstance(chunk, SourceChunk) for chunk in loaded_chunks)
    chunks = loaded_chunks[:1]

    embeddings = np.eye(len(chunks), dtype=np.float32)
    monkeypatch.setattr(indexing, "_embed_texts", lambda texts: embeddings)
    index_dir = tmp_path / "cache"

    assert indexing.build_index(chunks, index_dir) is None
    assert (index_dir / "vectors.npy").is_file()
    metadata = json.loads((index_dir / "metadata.json").read_text(encoding="utf-8"))
    assert [entry["vector_id"] for entry in metadata["chunks"]] == list(range(len(chunks)))

    loaded = indexing.load_index(index_dir)
    assert loaded.vectors.shape == embeddings.shape
    assert [chunk.chunk_id for chunk in loaded.chunks] == [
        chunk.chunk_id for chunk in chunks
    ]
    match, score = loaded.search(embeddings[0], top_k=1)[0]
    assert match.chunk_id == chunks[0].chunk_id
    assert score == 1.0


def test_creates_embeddings_with_configured_model(monkeypatch):
    import openai

    class FakeEmbeddings:
        def create(self, *, model, input):
            assert model == "test-embedding-model"
            assert input == ["sample text"]
            return SimpleNamespace(
                data=[SimpleNamespace(index=0, embedding=[0.25, 0.75])]
            )

    class FakeClient:
        def __init__(self, *, api_key):
            assert api_key == "test-key"
            self.embeddings = FakeEmbeddings()

    monkeypatch.setattr(openai, "OpenAI", FakeClient)
    monkeypatch.setattr(indexing, "get_api_key", lambda: "test-key")
    monkeypatch.setattr(
        indexing,
        "load_config",
        lambda: SimpleNamespace(embedding_model="test-embedding-model"),
    )

    vectors = indexing._embed_texts(["sample text"])

    np.testing.assert_allclose(vectors, [[0.25, 0.75]])
