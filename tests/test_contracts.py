import json
from pathlib import Path

import pytest

from src.contracts import (SchemaValidationError, SourceChunk, SourceDocument,
                           chunk_from_dict, validate_source_chunk)


FIXTURES = Path(__file__).parent / "fixtures"


def test_primary_fixture_matches_source_chunk_contract():
    line = (FIXTURES / "sample_primary_chunks.jsonl").read_text().splitlines()[0]
    chunk = SourceChunk(**json.loads(line))

    assert chunk.kb == "primary"
    assert chunk.visibility == "internal"
    assert chunk.source_locator


def test_secondary_fixture_preserves_pdf_locator():
    line = (FIXTURES / "sample_secondary_chunks.jsonl").read_text().splitlines()[1]
    chunk = SourceChunk(**json.loads(line))

    assert chunk.kb == "secondary"
    assert chunk.article_or_annex == "Article 14"
    assert "page=80" in chunk.source_locator


def test_source_document_has_one_shared_metadata_schema():
    document = SourceDocument(
        source_id="primary:policy.md",
        kb="primary",
        source_file="policy.md",
        source_type="company_document",
        document_type="policy",
        visibility="internal",
        title="Policy",
        text="Evidence.",
    )

    assert validate_source_chunk(
        SourceChunk(
            chunk_id="primary_policy_001",
            kb=document.kb,
            source_file=document.source_file,
            source_type=document.source_type,
            document_type=document.document_type,
            visibility=document.visibility,
            page_start=None,
            page_end=None,
            section="Policy",
            article_or_annex=None,
            title=document.title,
            text=document.text,
            source_locator="policy.md, Policy",
        )
    ).kb == "primary"


@pytest.mark.parametrize(
    "field,value",
    [
        ("chunk_id", ""),
        ("kb", "other"),
        ("source_file", ""),
        ("visibility", "secret"),
        ("document_type", ""),
        ("section", ""),
        ("source_locator", ""),
        ("text", ""),
    ],
)
def test_rejects_invalid_or_empty_chunk_fields(field, value):
    payload = {
        "chunk_id": "valid_chunk",
        "kb": "primary",
        "source_file": "policy.md",
        "source_type": "company_document",
        "document_type": "policy",
        "visibility": "internal",
        "page_start": None,
        "page_end": None,
        "section": "Policy",
        "article_or_annex": None,
        "title": "Policy",
        "text": "Evidence.",
        "source_locator": "policy.md, Policy",
    }
    payload[field] = value

    with pytest.raises(SchemaValidationError, match=field):
        chunk_from_dict(payload)


def test_rejects_invalid_page_range():
    payload = {
        "chunk_id": "chunk",
        "kb": "secondary",
        "source_file": "eu_ai_act.pdf",
        "source_type": "regulation",
        "document_type": "eu_ai_act",
        "visibility": "public",
        "page_start": 9,
        "page_end": 8,
        "section": "Article 14",
        "article_or_annex": "Article 14",
        "title": "Human oversight",
        "text": "Source text.",
        "source_locator": "eu_ai_act.pdf, page=9, Article 14",
    }

    with pytest.raises(SchemaValidationError, match="page_start"):
        chunk_from_dict(payload)
