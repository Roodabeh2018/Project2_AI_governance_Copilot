from pathlib import Path

import pytest

from src.contracts import IngestionError
from src import ingestion
from src.ingestion import load_documents


ROOT = Path(__file__).resolve().parents[1]
PRIMARY = ROOT / "knowledge_base" / "primary"
SECONDARY = ROOT / "knowledge_base" / "secondary"


def test_loads_current_primary_and_official_secondary_baseline():
    documents = load_documents(PRIMARY, SECONDARY)

    primary = [document for document in documents if document.kb == "primary"]
    secondary = [document for document in documents if document.kb == "secondary"]

    assert len(primary) == 9
    assert [document.source_file for document in secondary] == ["eu_ai_act/eu_ai_act_official.pdf"]
    assert sum(document.visibility == "internal" for document in primary) == 7
    assert {document.source_file for document in primary if document.visibility == "public"} == {
        "comms_guidelines.md",
        "company_profile.md",
    }
    assert secondary[0].document_type == "eu_ai_act"
    assert "[PAGE 1]" in secondary[0].text
    assert "[PAGE 144]" in secondary[0].text
    assert "Artificial Intelligence Act" in secondary[0].text


def test_loads_future_public_uploads_and_preserves_metadata(tmp_path):
    primary = tmp_path / "primary"
    secondary = tmp_path / "secondary" / "uploads"
    primary.mkdir(parents=True)
    secondary.mkdir(parents=True)

    (primary / "company_note.md").write_text(
        "---\ntitle: Internal Note\nvisibility: internal\n" \
        "document_type: procedure\n---\n# Ignored heading\nEvidence.",
        encoding="utf-8",
    )
    (secondary / "public_guidance.txt").write_text("Public source.", encoding="utf-8")

    documents = load_documents(primary, tmp_path / "secondary")

    assert [document.source_id for document in documents] == [
        "primary:company_note.md",
        "secondary:uploads/public_guidance.txt",
    ]
    assert documents[0].title == "Internal Note"
    assert documents[0].document_type == "procedure"
    assert documents[1].visibility == "public"
    assert documents[1].document_type == "uploaded_document"


def test_invalid_front_matter_is_an_ingestion_error(tmp_path):
    primary = tmp_path / "primary"
    secondary = tmp_path / "secondary"
    primary.mkdir()
    secondary.mkdir()
    (primary / "broken.md").write_text("---\nvisibility: internal\n# missing close", encoding="utf-8")

    with pytest.raises(IngestionError, match="no closing"):
        load_documents(primary, secondary)


def test_normalizes_uploaded_text_and_preserves_article_identifier(tmp_path):
    primary = tmp_path / "primary"
    secondary = tmp_path / "secondary" / "uploads"
    primary.mkdir(parents=True)
    secondary.mkdir(parents=True)
    (secondary / "public_guidance.md").write_text(
        "\ufeff# Public guidance\r\n\r\n\r\nArticle 14 — Human oversight\r\nA\u00a0B  \r\n",
        encoding="utf-8",
    )

    documents = load_documents(primary, tmp_path / "secondary")

    text = documents[0].text
    assert "\ufeff" not in text
    assert "\r" not in text
    assert "[ARTICLE 14]" in text
    assert "A B" in text
    assert "\n\n\n" not in text


def test_prefers_article_markdown_over_official_pdf(tmp_path):
    primary = tmp_path / "primary"
    secondary = tmp_path / "secondary" / "eu_ai_act"
    primary.mkdir(parents=True)
    secondary.mkdir(parents=True)
    (secondary / "article_14.md").write_text(
        "# Article 14 — Human oversight\nThe source text.", encoding="utf-8"
    )
    # If preference is not applied, this intentionally invalid PDF would fail.
    (secondary / "eu_ai_act_official.pdf").write_bytes(b"not a real PDF")

    documents = load_documents(primary, tmp_path / "secondary")

    assert [document.source_file for document in documents] == [
        "eu_ai_act/article_14.md"
    ]
    assert "[ARTICLE 14]" in documents[0].text


def test_pdf_extraction_is_cached_for_unchanged_file(tmp_path, monkeypatch):
    primary = tmp_path / "primary"
    secondary = tmp_path / "secondary"
    primary.mkdir()
    secondary.mkdir()
    pdf_path = secondary / "source.pdf"
    pdf_path.write_bytes(b"placeholder")

    calls = 0

    class FakePage:
        def extract_text(self):
            return "Public source"

    class FakeReader:
        metadata = {"/Title": "Fake source"}
        pages = [FakePage()]

        def __init__(self, path):
            nonlocal calls
            calls += 1

    ingestion._PDF_TEXT_CACHE.clear()
    monkeypatch.setattr(ingestion, "PdfReader", FakeReader)

    load_documents(primary, secondary)
    load_documents(primary, secondary)

    assert calls == 1


def test_empty_source_is_an_ingestion_error(tmp_path):
    primary = tmp_path / "primary"
    secondary = tmp_path / "secondary"
    primary.mkdir()
    secondary.mkdir()
    (secondary / "empty.md").write_text("\ufeff\n\n", encoding="utf-8")

    with pytest.raises(IngestionError, match="empty"):
        load_documents(primary, secondary)
