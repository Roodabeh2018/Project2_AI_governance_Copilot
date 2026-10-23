import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from src import indexing, llm_generator, pipeline, retrieval
from src.contracts import GenerationRequest


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


def test_unknown_ai_system_returns_insufficient_source_without_generation(
    tmp_path, monkeypatch
):
    chunks = (
        indexing.load_chunks(ROOT / "tests" / "fixtures" / "sample_primary_chunks.jsonl")
        + indexing.load_chunks(ROOT / "tests" / "fixtures" / "sample_secondary_chunks.jsonl")
    )
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
        lambda texts: pytest.fail("unknown system should not be embedded"),
    )
    monkeypatch.setattr(
        retrieval,
        "load_config",
        lambda: SimpleNamespace(minimum_retrieval_score=0.35),
    )
    monkeypatch.setattr(
        pipeline,
        "retrieve_context",
        lambda request: retrieval.retrieve(
            pipeline.build_query(request),
            request.output_visibility,
            3,
            3,
            index_path=index_path,
            context_path=tmp_path / "unknown.json",
        ),
    )
    monkeypatch.setattr(
        pipeline,
        "generate_draft",
        lambda request: pytest.fail("unsupported request must not reach generation"),
    )
    request = GenerationRequest(
        request_type="internal_update",
        document_type=None,
        ai_system="AI-99",
        topic="monitoring status",
        output_visibility="internal",
    )

    draft = pipeline.run_pipeline(request, save=False)

    assert draft.status == "insufficient_source"
    assert "AI-99" in draft.content_markdown
    assert "does not establish whether the system exists elsewhere" in draft.content_markdown
    assert "AI-99 does not exist" not in draft.content_markdown
    assert request.primary_context == []
    assert request.secondary_context == []


@pytest.mark.parametrize(
    ("requested_id", "documented_id"),
    [("AI-99", "AI-999"), ("AI-4", "AI-42")],
)
def test_system_id_prefix_is_not_supported_by_a_longer_id(
    requested_id, documented_id, tmp_path, monkeypatch
):
    primary_chunk = indexing.load_chunks(
        ROOT / "tests" / "fixtures" / "sample_primary_chunks.jsonl"
    )[0]
    primary_chunk = replace(
        primary_chunk,
        document_type="policy",
        section=f"Policy evidence for {documented_id}",
        text=f"The policy documents {documented_id} only.",
    )
    secondary_chunks = indexing.load_chunks(
        ROOT / "tests" / "fixtures" / "sample_secondary_chunks.jsonl"
    )
    chunks = [primary_chunk, *secondary_chunks]
    monkeypatch.setattr(
        indexing,
        "_embed_texts",
        lambda texts: np.tile(
            np.array([[1.0, 0.0]], dtype=np.float32), (len(texts), 1)
        ),
    )
    index_path = tmp_path / "cache"
    indexing.build_index(chunks, index_path)
    monkeypatch.setattr(
        retrieval,
        "_embed_texts",
        lambda texts: pytest.fail("unsupported system IDs must not be embedded"),
    )
    monkeypatch.setattr(
        retrieval,
        "load_config",
        lambda: SimpleNamespace(minimum_retrieval_score=0.35),
    )
    monkeypatch.setattr(
        pipeline,
        "retrieve_context",
        lambda request: retrieval.retrieve(
            pipeline.build_query(request),
            request.output_visibility,
            3,
            3,
            index_path=index_path,
            context_path=tmp_path / f"{requested_id}.json",
        ),
    )
    monkeypatch.setattr(
        pipeline,
        "generate_draft",
        lambda request: pytest.fail("unsupported system IDs must not reach generation"),
    )
    request = GenerationRequest(
        request_type="internal_update",
        document_type=None,
        ai_system=requested_id,
        topic="monitoring status",
        output_visibility="internal",
    )

    draft = pipeline.run_pipeline(request, save=False)

    assert draft.status == "insufficient_source"
    assert requested_id in draft.content_markdown
    assert "No matching Primary evidence" in draft.content_markdown


@pytest.mark.parametrize(
    "query",
    [
        "What controls are needed for AI-based credit decisions?",
        "Explain AI-system monitoring and human oversight",
    ],
)
def test_ordinary_ai_wording_is_not_misread_as_a_system_id(
    query, tmp_path, monkeypatch
):
    index_path, _ = _build_sample_index(tmp_path, monkeypatch)
    embedded_queries = []

    def embed_query(texts):
        embedded_queries.extend(texts)
        return np.array([[1.0, 0.0]], dtype=np.float32)

    monkeypatch.setattr(retrieval, "_embed_texts", embed_query)

    context = retrieval.retrieve(
        query,
        index_path=index_path,
        context_path=tmp_path / "ordinary-wording.json",
    )

    assert context.retrieval_status == "success"
    assert embedded_queries == [query]


def test_primary_policy_can_support_system_without_inventory_entry(
    tmp_path, monkeypatch
):
    primary_chunks = indexing.load_chunks(
        ROOT / "tests" / "fixtures" / "sample_primary_chunks.jsonl"
    )
    secondary_chunks = indexing.load_chunks(
        ROOT / "tests" / "fixtures" / "sample_secondary_chunks.jsonl"
    )
    primary_evidence = primary_chunks[0]
    policy_for_ai_42 = replace(
        primary_evidence,
        chunk_id=f"{primary_evidence.chunk_id}_ai42",
        document_type="policy",
        section="AI Governance Policy",
        text="The AI governance policy explicitly documents AI-42.",
    )
    fake_secondary_inventory = replace(
        secondary_chunks[0],
        chunk_id=f"{secondary_chunks[0].chunk_id}_public_inventory",
        document_type="inventory",
        section="System: AI-99",
        text="System: AI-99 is a public example.",
    )
    chunks = [policy_for_ai_42, *primary_chunks[1:], *secondary_chunks, fake_secondary_inventory]
    monkeypatch.setattr(
        indexing,
        "_embed_texts",
        lambda texts: np.tile(
            np.array([[1.0, 0.0]], dtype=np.float32), (len(texts), 1)
        ),
    )
    index_path = tmp_path / "cache"
    indexing.build_index(chunks, index_path)
    monkeypatch.setattr(
        retrieval,
        "_embed_texts",
        lambda texts: np.array([[1.0, 0.0]], dtype=np.float32),
    )

    context = retrieval.retrieve(
        "AI system: AI-42; Topic: monitoring status",
        index_path=index_path,
        context_path=tmp_path / "ai-42.json",
    )

    assert context.retrieval_status == "success"
    assert any(result.chunk.chunk_id == policy_for_ai_42.chunk_id
               for result in context.primary_results)
    assert "No matching inventory entry was found" in (context.message or "")
    assert all(result.chunk.kb == "primary"
               for result in context.primary_results)


def test_inventory_prefix_does_not_suppress_missing_inventory_limitation(
    tmp_path, monkeypatch
):
    primary_chunks = indexing.load_chunks(
        ROOT / "tests" / "fixtures" / "sample_primary_chunks.jsonl"
    )
    secondary_chunks = indexing.load_chunks(
        ROOT / "tests" / "fixtures" / "sample_secondary_chunks.jsonl"
    )
    policy_for_ai_99 = replace(
        primary_chunks[0],
        chunk_id=f"{primary_chunks[0].chunk_id}_ai99",
        document_type="policy",
        section="AI Governance Policy",
        text="The policy documents AI-99.",
    )
    inventory_for_ai_999 = replace(
        primary_chunks[1],
        chunk_id=f"{primary_chunks[1].chunk_id}_ai999",
        document_type="inventory",
        section="System: AI-999",
        text="The inventory documents AI-999.",
    )
    chunks = [
        policy_for_ai_99,
        inventory_for_ai_999,
        *primary_chunks[2:],
        *secondary_chunks,
    ]
    monkeypatch.setattr(
        indexing,
        "_embed_texts",
        lambda texts: np.tile(
            np.array([[1.0, 0.0]], dtype=np.float32), (len(texts), 1)
        ),
    )
    index_path = tmp_path / "cache"
    indexing.build_index(chunks, index_path)
    monkeypatch.setattr(
        retrieval,
        "_embed_texts",
        lambda texts: np.array([[1.0, 0.0]], dtype=np.float32),
    )

    context = retrieval.retrieve(
        "AI system: AI-99; Topic: monitoring status",
        index_path=index_path,
        context_path=tmp_path / "ai-99-with-ai-999-inventory.json",
    )

    assert context.retrieval_status == "success"
    assert "No matching inventory entry was found" in (context.message or "")


def test_pipeline_preserves_missing_inventory_limitation_in_saved_draft(
    tmp_path, monkeypatch
):
    primary_evidence = indexing.load_chunks(
        ROOT / "tests" / "fixtures" / "sample_primary_chunks.jsonl"
    )[0]
    policy_for_ai_42 = replace(
        primary_evidence,
        document_type="policy",
        section="AI Governance Policy",
        text="The policy documents AI-42 and describes its monitoring approach.",
    )
    secondary_chunks = indexing.load_chunks(
        ROOT / "tests" / "fixtures" / "sample_secondary_chunks.jsonl"
    )
    chunks = [policy_for_ai_42, *secondary_chunks]
    monkeypatch.setattr(
        indexing,
        "_embed_texts",
        lambda texts: np.tile(
            np.array([[1.0, 0.0]], dtype=np.float32), (len(texts), 1)
        ),
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
    monkeypatch.setattr(
        pipeline,
        "retrieve_context",
        lambda request: retrieval.retrieve(
            pipeline.build_query(request),
            request.output_visibility,
            3,
            3,
            index_path=index_path,
            context_path=tmp_path / "retrieved-context.json",
        ),
    )
    monkeypatch.setattr(llm_generator, "llm_provider", lambda: "mock")
    monkeypatch.setattr(pipeline, "OUTPUT_DIR", tmp_path / "outputs")
    monkeypatch.setattr(pipeline, "ROOT", tmp_path)
    request = GenerationRequest(
        request_type="governance_document",
        document_type="AI System Monitoring Plan",
        ai_system="AI-42",
        topic="monitoring status",
        output_visibility="internal",
    )

    draft = pipeline.run_pipeline(request, save=True)

    expected_limitation = (
        "No matching inventory entry was found for 'AI-42'; retrieval is based "
        "on other Primary evidence."
    )
    saved_draft = tmp_path / draft.output_path
    assert draft.status == "Draft — human review required"
    assert expected_limitation in draft.open_questions
    assert "## Retrieval Limitations" in draft.content_markdown
    assert expected_limitation in draft.content_markdown
    assert saved_draft.is_file()
    assert expected_limitation in saved_draft.read_text(encoding="utf-8")


def test_exact_inventory_id_suppresses_missing_inventory_limitation(
    tmp_path, monkeypatch
):
    primary_chunks = indexing.load_chunks(
        ROOT / "tests" / "fixtures" / "sample_primary_chunks.jsonl"
    )
    secondary_chunks = indexing.load_chunks(
        ROOT / "tests" / "fixtures" / "sample_secondary_chunks.jsonl"
    )
    inventory_for_ai_99 = replace(
        primary_chunks[0],
        document_type="inventory",
        section="System: AI-99",
        text="The inventory documents AI-99.",
    )
    chunks = [inventory_for_ai_99, *primary_chunks[1:], *secondary_chunks]
    monkeypatch.setattr(
        indexing,
        "_embed_texts",
        lambda texts: np.tile(
            np.array([[1.0, 0.0]], dtype=np.float32), (len(texts), 1)
        ),
    )
    index_path = tmp_path / "cache"
    indexing.build_index(chunks, index_path)
    monkeypatch.setattr(
        retrieval,
        "_embed_texts",
        lambda texts: np.array([[1.0, 0.0]], dtype=np.float32),
    )

    context = retrieval.retrieve(
        "AI system: AI-99; Topic: monitoring status",
        index_path=index_path,
        context_path=tmp_path / "ai-99-exact-inventory.json",
    )

    assert context.retrieval_status == "success"
    assert context.message is None


def test_secondary_inventory_cannot_whitelist_internal_ai_system(
    tmp_path, monkeypatch
):
    primary_chunks = indexing.load_chunks(
        ROOT / "tests" / "fixtures" / "sample_primary_chunks.jsonl"
    )
    secondary_chunks = indexing.load_chunks(
        ROOT / "tests" / "fixtures" / "sample_secondary_chunks.jsonl"
    )
    fake_secondary_inventory = replace(
        secondary_chunks[0],
        chunk_id=f"{secondary_chunks[0].chunk_id}_public_inventory",
        document_type="inventory",
        section="System: AI-99",
        text="System: AI-99 is a public example.",
    )
    chunks = [*primary_chunks, *secondary_chunks, fake_secondary_inventory]
    monkeypatch.setattr(
        indexing,
        "_embed_texts",
        lambda texts: np.tile(
            np.array([[1.0, 0.0]], dtype=np.float32), (len(texts), 1)
        ),
    )
    index_path = tmp_path / "cache"
    indexing.build_index(chunks, index_path)
    monkeypatch.setattr(
        retrieval,
        "_embed_texts",
        lambda texts: pytest.fail("secondary inventory cannot authorize a system"),
    )

    context = retrieval.retrieve(
        "AI system: AI-99; Topic: monitoring status",
        index_path=index_path,
        context_path=tmp_path / "ai-99-secondary-only.json",
    )

    assert context.retrieval_status == "insufficient_source"
    assert context.primary_results == []
    assert context.secondary_results == []
    assert "No matching Primary evidence" in (context.message or "")
