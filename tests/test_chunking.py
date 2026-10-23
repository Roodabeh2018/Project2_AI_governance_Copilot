import json
from pathlib import Path

import pytest

from src.chunking import chunk_documents, rebuild_cache, save_chunks
from src.contracts import SchemaValidationError, SourceDocument
from src.ingestion import load_documents


ROOT = Path(__file__).resolve().parents[1]
PRIMARY = ROOT / "knowledge_base" / "primary"
SECONDARY = ROOT / "knowledge_base" / "secondary"


def test_chunks_both_kbs_and_preserves_shared_metadata():
    documents = load_documents(PRIMARY, SECONDARY)
    chunks = chunk_documents(documents)

    assert chunks
    assert {chunk.kb for chunk in chunks} == {"primary", "secondary"}
    assert all(chunk.chunk_id for chunk in chunks)
    assert all(chunk.source_file for chunk in chunks)
    assert all(chunk.visibility in {"internal", "public", "mixed"} for chunk in chunks)
    assert all(chunk.document_type and chunk.text and chunk.source_locator for chunk in chunks)
    assert len({chunk.chunk_id for chunk in chunks}) == len(chunks)
    assert any(chunk.kb == "secondary" and chunk.page_start == 1 for chunk in chunks)


def test_chunk_ids_are_distinct_for_slug_collisions():
    documents = [
        SourceDocument(
            source_id="primary:a-b.md", kb="primary", source_file="a-b.md",
            source_type="company_document", document_type="policy", visibility="internal",
            title="A", text="Evidence A.",
        ),
        SourceDocument(
            source_id="primary:a_b.md", kb="primary", source_file="a_b.md",
            source_type="company_document", document_type="policy", visibility="internal",
            title="B", text="Evidence B.",
        ),
    ]

    chunks = chunk_documents(documents)

    assert len({chunk.chunk_id for chunk in chunks}) == 2
    assert chunks[0].chunk_id != chunks[1].chunk_id


def test_chunks_headings_articles_and_pages():
    document = SourceDocument(
        source_id="secondary:eu_ai_act/article_14.md",
        kb="secondary",
        source_file="eu_ai_act/article_14.md",
        source_type="regulation",
        document_type="eu_ai_act",
        visibility="public",
        title="Article 14",
        text=(
            "[PAGE 80]\n[ARTICLE 14]\nArticle 14 — Human oversight\n"
            "Natural persons oversee the system.\n\n"
            "[PAGE 81]\nThe oversight record is retained."
        ),
    )

    chunks = chunk_documents([document])

    assert len(chunks) == 2
    assert [chunk.page_start for chunk in chunks] == [80, 81]
    assert all(chunk.article_or_annex == "Article 14" for chunk in chunks)
    assert chunks[0].section == "Article 14 — Human oversight"
    assert "page=80" in chunks[0].source_locator
    assert "Article 14" in chunks[1].source_locator


def test_save_chunks_writes_jsonl_and_manifest_and_rebuilds(tmp_path):
    documents = load_documents(PRIMARY, SECONDARY)
    chunks = chunk_documents(documents, max_chunk_characters=1000)
    output_path = tmp_path / "cache" / "chunks.jsonl"

    save_chunks(chunks[:2], output_path)
    first_lines = output_path.read_text(encoding="utf-8").splitlines()
    first_manifest = json.loads(
        (output_path.parent / "source_manifest.json").read_text(encoding="utf-8")
    )
    save_chunks(chunks[2:5], output_path)
    second_lines = output_path.read_text(encoding="utf-8").splitlines()
    second_manifest = json.loads(
        (output_path.parent / "source_manifest.json").read_text(encoding="utf-8")
    )

    assert len(first_lines) == 2
    assert first_manifest["chunk_count"] == 2
    assert len(second_lines) == 3
    assert second_manifest["chunk_count"] == 3
    assert second_manifest["chunk_count"] != first_manifest["chunk_count"]
    assert all(json.loads(line)["chunk_id"] in {chunk.chunk_id for chunk in chunks[2:5]}
               for line in second_lines)


def test_rebuild_cache_reads_both_roots_and_overwrites_previous_cache(tmp_path):
    primary = tmp_path / "primary"
    secondary = tmp_path / "secondary"
    primary.mkdir()
    secondary.mkdir()
    (primary / "policy.md").write_text("# Policy\nInternal evidence.", encoding="utf-8")
    (secondary / "guidance.md").write_text("# Guidance\nPublic evidence.", encoding="utf-8")

    first = rebuild_cache(primary, secondary, tmp_path / "cache")
    (primary / "policy.md").unlink()
    (primary / "new_policy.md").write_text("# New policy\nNew evidence.", encoding="utf-8")
    second = rebuild_cache(primary, secondary, tmp_path / "cache")

    assert {chunk.source_file for chunk in first} == {"policy.md", "guidance.md"}
    assert {chunk.source_file for chunk in second} == {"new_policy.md", "guidance.md"}
    cached = (tmp_path / "cache" / "chunks.jsonl").read_text(encoding="utf-8")
    assert '"source_file": "policy.md"' not in cached
    assert "new_policy.md" in cached


def test_rejects_invalid_chunk_size():
    document = SourceDocument(
        source_id="primary:note.md", kb="primary", source_file="note.md",
        source_type="company_document", document_type="procedure", visibility="internal",
        title="Note", text="Evidence.",
    )

    with pytest.raises(ValueError, match="positive"):
        chunk_documents([document], max_chunk_characters=0)


def test_rejects_non_document_input():
    with pytest.raises(SchemaValidationError, match="SourceDocument"):
        chunk_documents(["not a document"])
