import json
from dataclasses import replace
from pathlib import Path

import pytest

from src.chunking import chunk_documents
from src.contracts import SourceDocument
from src.ingestion import load_documents
from src.kb_validation import (
    KnowledgeBaseValidationError,
    load_cached_chunks,
    require_valid_knowledge_base,
    validate_knowledge_base,
    write_sample_chunks,
)


ROOT = Path(__file__).resolve().parents[1]
PRIMARY = ROOT / "knowledge_base" / "primary"
SECONDARY = ROOT / "knowledge_base" / "secondary"
FIXTURES = ROOT / "tests" / "fixtures"


def test_reports_current_primary_and_secondary_counts():
    report = require_valid_knowledge_base(PRIMARY, SECONDARY)

    assert report.is_valid
    assert report.primary_document_count == 9
    assert report.secondary_document_count == 1
    assert report.primary_chunk_count > 0
    assert report.secondary_chunk_count > 0
    assert "eu_ai_act/eu_ai_act_official.pdf" in report.secondary_files


def test_validates_shared_sample_chunks_fixture():
    chunks = load_cached_chunks(FIXTURES / "sample_chunks.jsonl")
    report = validate_knowledge_base(PRIMARY, SECONDARY, chunks=chunks)

    assert report.is_valid
    assert report.primary_chunk_count == 2
    assert report.secondary_chunk_count == 2


def test_expected_counts_are_optional_drift_checks():
    report = validate_knowledge_base(
        PRIMARY,
        SECONDARY,
        expected_primary_count=10,
        expected_secondary_count=1,
    )

    assert not report.is_valid
    assert "Expected 10 primary documents" in report.errors[0]


def test_rejects_chunk_from_unknown_source():
    documents = load_documents(PRIMARY, SECONDARY)
    chunks = chunk_documents(documents)[:1]
    unknown = SourceDocument(
        source_id="primary:unknown.md",
        kb="primary",
        source_file="unknown.md",
        source_type="company_document",
        document_type="procedure",
        visibility="internal",
        title="Unknown",
        text="Unknown evidence.",
    )
    unknown_chunk = chunk_documents([unknown])[0]

    report = validate_knowledge_base(PRIMARY, SECONDARY, chunks=chunks + [unknown_chunk])

    assert not report.is_valid
    assert any("unknown source" in error for error in report.errors)


def test_rejects_chunk_metadata_drift_from_source():
    documents = load_documents(PRIMARY, SECONDARY)
    chunks = chunk_documents(documents)
    drifted = replace(chunks[0], visibility="public")

    report = validate_knowledge_base(PRIMARY, SECONDARY, chunks=[drifted, *chunks[1:]])

    assert not report.is_valid
    assert any("visibility" in error and "mismatch" in error for error in report.errors)


def test_rejects_duplicate_chunk_ids():
    chunks = load_cached_chunks(FIXTURES / "sample_chunks.jsonl")
    duplicate = validate_knowledge_base(PRIMARY, SECONDARY, chunks=[chunks[0], chunks[0]])

    assert not duplicate.is_valid
    assert any("Duplicate chunk_id" in error for error in duplicate.errors)


def test_requires_chunks_from_both_kbs():
    chunks = load_cached_chunks(FIXTURES / "sample_primary_chunks.jsonl")
    report = validate_knowledge_base(PRIMARY, SECONDARY, chunks=chunks)

    assert not report.is_valid
    assert any("secondary chunks" in error for error in report.errors)


def test_cached_chunk_loader_rejects_invalid_json(tmp_path):
    path = tmp_path / "broken.jsonl"
    path.write_text("not json\n", encoding="utf-8")

    with pytest.raises(KnowledgeBaseValidationError, match="line 1"):
        load_cached_chunks(path)


def test_writes_a_two_kb_sample(tmp_path):
    chunks = chunk_documents(load_documents(PRIMARY, SECONDARY))
    output = tmp_path / "sample_chunks.jsonl"

    write_sample_chunks(chunks, output)
    saved = load_cached_chunks(output)

    assert len(saved) == 4
    assert [chunk.kb for chunk in saved] == ["primary", "primary", "secondary", "secondary"]
