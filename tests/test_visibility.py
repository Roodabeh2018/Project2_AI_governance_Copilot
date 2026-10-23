from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from src import indexing, pipeline, retrieval
from src.contracts import (
    DRAFT_STATUS,
    GenerationRequest,
    RetrievalResult,
)


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_PRIMARY_CHUNKS = ROOT / "tests" / "fixtures" / "sample_primary_chunks.jsonl"
SAMPLE_SECONDARY_CHUNKS = ROOT / "tests" / "fixtures" / "sample_secondary_chunks.jsonl"


def _build_mixed_index(tmp_path, monkeypatch):
    chunks = (
        indexing.load_chunks(SAMPLE_PRIMARY_CHUNKS)
        + indexing.load_chunks(SAMPLE_SECONDARY_CHUNKS)
    )
    mixed_chunk = replace(
        chunks[0],
        chunk_id=f"{chunks[0].chunk_id}_mixed",
        visibility="mixed",
    )
    chunks.append(mixed_chunk)

    monkeypatch.setattr(
        indexing,
        "_embed_texts",
        lambda texts: np.tile(np.array([[1.0, 0.0]], dtype=np.float32), (len(texts), 1)),
    )
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
    return index_path


def test_internal_retrieval_allows_all_visibility_values(tmp_path, monkeypatch):
    index_path = _build_mixed_index(tmp_path, monkeypatch)

    context = retrieval.retrieve(
        "evidence",
        output_visibility="internal",
        top_k_primary=10,
        top_k_secondary=10,
        index_path=index_path,
        context_path=tmp_path / "internal.json",
    )

    assert {result.chunk.visibility for result in context.primary_results} == {
        "internal",
        "public",
        "mixed",
    }
    assert context.secondary_results


def test_public_retrieval_and_pipeline_exclude_internal_and_mixed_chunks(
    tmp_path, monkeypatch
):
    index_path = _build_mixed_index(tmp_path, monkeypatch)
    context = retrieval.retrieve(
        "evidence",
        output_visibility="public",
        top_k_primary=10,
        top_k_secondary=10,
        index_path=index_path,
        context_path=tmp_path / "public.json",
    )

    assert context.primary_results
    assert context.secondary_results
    assert all(
        result.chunk.visibility == "public"
        for result in context.primary_results + context.secondary_results
    )

    internal_chunk = indexing.load_chunks(SAMPLE_PRIMARY_CHUNKS)[0]
    mixed_chunk = replace(
        internal_chunk,
        chunk_id=f"{internal_chunk.chunk_id}_prompt_test",
        visibility="mixed",
    )
    context.primary_results.extend(
        [
            RetrievalResult(
                rank=99,
                score=1.0,
                chunk=internal_chunk,
                citation=internal_chunk.source_locator,
            ),
            RetrievalResult(
                rank=100,
                score=1.0,
                chunk=mixed_chunk,
                citation=mixed_chunk.source_locator,
            ),
        ]
    )
    request = GenerationRequest(
        request_type="governance_document",
        document_type="Summary",
        ai_system=None,
        topic="general public information",
        output_visibility="public",
    )
    captured = {}

    def capture_generation(generation_request):
        captured["request"] = generation_request
        return SimpleNamespace(status=DRAFT_STATUS)

    monkeypatch.setattr(pipeline, "generate_draft", capture_generation)
    pipeline.run_pipeline(request, context, save=False)

    prompt_request = captured["request"]
    retrieved = prompt_request.primary_context + prompt_request.secondary_context
    assert retrieved
    assert all(result.chunk.visibility == "public" for result in retrieved)
    assert internal_chunk.text not in "\n".join(
        result.chunk.text for result in retrieved
    )
    assert mixed_chunk.text not in "\n".join(
        result.chunk.text for result in retrieved
    )
