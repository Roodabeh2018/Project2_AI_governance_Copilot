from pathlib import Path

import pytest

from src.contracts import IngestionError
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
