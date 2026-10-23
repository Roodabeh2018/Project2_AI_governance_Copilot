import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from src import indexing, retrieval


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_CHUNKS = ROOT / "tests" / "fixtures" / "sample_chunks.jsonl"


def _build_sample_index(tmp_path, monkeypatch):
    chunks = indexing.load_chunks(SAMPLE_CHUNKS)
    vectors = np.array(
        [[1.0, 0.0], [0.0, 1.0], [1.0, 0.0], [0.0, 1.0]],
        dtype=np.float32,
    )
    monkeypatch.setattr(indexing, "_embed_texts", lambda texts: vectors)
    index_path = tmp_path / "cache"
    indexing.build_index(chunks, index_path)
    monkeypatch.setattr(
        retrieval,
        "_embed_texts",
        lambda texts: np.array([[1.0, 0.0]], dtype=np.float32),
    )
    monkeypatch.setattr(
        retrieval,
        "load_config",
        lambda: SimpleNamespace(minimum_retrieval_score=0.35),
    )
    return index_path, chunks


def test_retrieves_top_k_per_kb_preserves_scores_and_saves_context(tmp_path, monkeypatch):
    index_path, chunks = _build_sample_index(tmp_path, monkeypatch)
    context_path = tmp_path / "retrieved_context.json"

    context = retrieval.retrieve(
        "human oversight",
        top_k_primary=1,
        top_k_secondary=1,
        index_path=index_path,
        context_path=context_path,
    )

    assert context.retrieval_status == "success"
    assert len(context.primary_results) == len(context.secondary_results) == 1
    assert context.primary_results[0].chunk.kb == "primary"
    assert context.secondary_results[0].chunk.kb == "secondary"
    assert context.primary_results[0].chunk.chunk_id == chunks[0].chunk_id
    assert context.secondary_results[0].chunk.chunk_id == chunks[2].chunk_id
    assert context.primary_results[0].rank == context.secondary_results[0].rank == 1
    assert context.primary_results[0].score == context.secondary_results[0].score == 1.0
    assert context.primary_results[0].citation == chunks[0].source_locator

    saved = json.loads(context_path.read_text(encoding="utf-8"))
    assert saved["query"] == "human oversight"
    assert saved["primary_results"][0]["score"] == 1.0
    assert saved["secondary_results"][0]["chunk"]["chunk_id"] == chunks[2].chunk_id


def test_public_retrieval_filters_internal_chunks_and_unsupported_query(tmp_path, monkeypatch):
    index_path, _ = _build_sample_index(tmp_path, monkeypatch)

    public_context = retrieval.retrieve(
        "public evidence",
        output_visibility="public",
        index_path=index_path,
        context_path=tmp_path / "public.json",
    )
    assert public_context.primary_results == []
    assert public_context.secondary_results
    assert all(
        result.chunk.visibility == "public"
        for result in public_context.secondary_results
    )

    monkeypatch.setattr(
        retrieval,
        "_embed_texts",
        lambda texts: np.array([[-1.0, 0.0]], dtype=np.float32),
    )

    context = retrieval.retrieve(
        "unsupported evidence",
        index_path=index_path,
        context_path=tmp_path / "unsupported.json",
    )

    assert context.retrieval_status == "insufficient_source"
    assert context.primary_results == []
    assert context.secondary_results == []
    assert context.message
