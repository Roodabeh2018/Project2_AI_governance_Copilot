import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from src import indexing
from src.contracts import RetrievalError, SchemaValidationError, SourceChunk


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


def test_failed_metadata_replace_rejects_mismatched_index(tmp_path, monkeypatch):
    chunks = indexing.load_chunks(SAMPLE_CHUNKS)[:1]
    index_dir = tmp_path / "cache"
    monkeypatch.setattr(
        indexing,
        "_embed_texts",
        lambda texts: np.array([[1.0, 0.0]], dtype=np.float32),
    )
    indexing.build_index(chunks, index_dir)

    monkeypatch.setattr(
        indexing,
        "_embed_texts",
        lambda texts: np.array([[0.0, 1.0]], dtype=np.float32),
    )
    original_replace = indexing.os.replace
    metadata_path = index_dir / indexing.METADATA_FILENAME

    def fail_metadata_replace(source, destination):
        if Path(destination) == metadata_path:
            raise OSError("simulated metadata replacement failure")
        original_replace(source, destination)

    monkeypatch.setattr(indexing.os, "replace", fail_metadata_replace)
    with pytest.raises(RetrievalError, match="simulated metadata replacement failure"):
        indexing.build_index(chunks, index_dir)

    with pytest.raises(SchemaValidationError, match="does not match its metadata"):
        indexing.load_index(index_dir)


def test_rejects_embedding_model_mismatch_with_same_vector_dimensions(
    tmp_path, monkeypatch
):
    chunks = indexing.load_chunks(SAMPLE_CHUNKS)[:1]
    index_dir = tmp_path / "cache"
    monkeypatch.setattr(
        indexing,
        "load_config",
        lambda: SimpleNamespace(embedding_model="model-A"),
    )
    monkeypatch.setattr(
        indexing,
        "_embed_texts",
        lambda texts: np.array([[1.0, 0.0]], dtype=np.float32),
    )
    indexing.build_index(chunks, index_dir)

    monkeypatch.setattr(
        indexing,
        "load_config",
        lambda: SimpleNamespace(embedding_model="model-B"),
    )
    with pytest.raises(RetrievalError, match="Rebuild the local index"):
        indexing.load_index(index_dir)
