"""Regression tests for the Color B adapter in src/pipeline.py (review of PR #10).

Offline: LLM_PROVIDER=mock, fake Color A documents and fake Color B retrieve functions.
"""
import os
import sys
import types
from pathlib import Path

import pytest

os.environ["LLM_PROVIDER"] = "mock"
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import pipeline  # noqa: E402
from src.contracts import GenerationRequest, RetrievalError, SourceDocument  # noqa: E402


def _doc(kb, source_file, visibility, text="", document_type="policy"):
    return SourceDocument(source_id=f"{kb}:{source_file}", kb=kb, source_file=source_file,
                          source_type="company_document" if kb == "primary" else "regulation",
                          document_type=document_type, visibility=visibility,
                          title=Path(source_file).stem, text=text or "Credit Decision Support AI")


DOCS = [
    _doc("primary", "ai_system_inventory.md", "internal", "System: Credit Decision Support AI. Owner: [NOT RECORDED]"),
    _doc("primary", "company_profile.md", "public", "Northstar Digital Bank profile"),
    _doc("primary", "systems_register.txt", "internal", "Fraud Screening Model FS-7 is in production"),
    _doc("primary", "vendor_contract.pdf", "internal", "[PAGE 1] Vendor model VM-12 used by underwriting"),
    _doc("secondary", "eu_ai_act/eu_ai_act_official.pdf", "public", "Article 14 Human oversight"),
    _doc("secondary", "board_minutes.md", "internal", "Internal board discussion"),
]


def _item(kb, source_file, visibility_label, score=1.0, section="Section"):
    return {"kb": kb, "source_file": source_file, "visibility": visibility_label, "section": section,
            "text": f"text of {source_file}", "source_locator": f"{source_file}, {section}", "score": score}


@pytest.fixture(autouse=True)
def fake_color_a(monkeypatch):
    monkeypatch.setattr(pipeline, "company_documents", lambda: DOCS)


def _use_retrieve(monkeypatch, fn):
    monkeypatch.setitem(sys.modules, "src.retrieval", types.SimpleNamespace(retrieve=fn))


def _req(visibility="internal", topic="monitoring and human oversight", ai_system="Credit Decision Support AI"):
    return GenerationRequest(request_type="governance_document", document_type="AI System Monitoring Plan",
                             ai_system=ai_system, topic=topic, output_visibility=visibility)


# --- P1: internal content never reaches a public generation through the legacy adapter ---

def test_public_request_excludes_internal_docs_mislabelled_by_legacy_retrieval(monkeypatch):
    def legacy(query, output_visibility="internal", top_k=3):
        return {"retrieval_status": "success",
                "primary_results": [_item("primary", "ai_system_inventory.md", "public"),
                                    _item("primary", "company_profile.md", "internal")],
                "secondary_results": [_item("secondary", "board_minutes.md", "public"),
                                      _item("secondary", "eu_ai_act/eu_ai_act_official.pdf", "public")]}
    _use_retrieve(monkeypatch, legacy)
    req = _req("public")
    pipeline.run_pipeline(req, save=False)
    used = req.primary_context + req.secondary_context
    assert {r.chunk.source_file for r in used} == {"company_profile.md", "eu_ai_act/eu_ai_act_official.pdf"}
    assert all(r.chunk.visibility == "public" for r in used)


def test_metadata_comes_from_color_a_and_unknown_sources_are_dropped(monkeypatch):
    def legacy(query, output_visibility="internal", top_k=3):
        return {"primary_results": [_item("primary", "ai_system_inventory.md", "public"),
                                    _item("primary", "not_in_kb.md", "internal")],
                "secondary_results": []}
    _use_retrieve(monkeypatch, legacy)
    ctx = pipeline.retrieve_context(_req())
    [result] = ctx.primary_results
    assert result.chunk.visibility == "internal"                 # canonical, not the legacy label
    assert result.chunk.document_type == "policy" and result.chunk.source_type == "company_document"
    assert result.chunk.chunk_id.startswith("primary:ai_system_inventory.md")


# --- P2: unknown-system detection ---

def test_requirement_ids_are_not_treated_as_ai_systems():
    assert pipeline.unknown_systems(_req(topic="MON-02 monitoring plan and HUM-01 oversight")) == []


def test_systems_documented_in_txt_and_pdf_are_known():
    assert pipeline.unknown_systems(_req(topic="FS-7 and VM-12 monitoring")) == []
    assert pipeline.unknown_systems(_req(topic="AI-99 monitoring")) == ["AI-99"]


# --- P2: independent top-k per knowledge base ---

def test_legacy_signature_respects_separate_top_k(monkeypatch):
    monkeypatch.setenv("TOP_K_PRIMARY", "1")
    monkeypatch.setenv("TOP_K_SECONDARY", "3")

    def legacy(query, output_visibility="internal", top_k=3):
        return {"primary_results": [_item("primary", "ai_system_inventory.md", "internal", s) for s in (3, 2, 1)],
                "secondary_results": [_item("secondary", "eu_ai_act/eu_ai_act_official.pdf", "public", s,
                                            f"Article {s}") for s in (3, 2, 1)]}
    _use_retrieve(monkeypatch, legacy)
    ctx = pipeline.retrieve_context(_req())
    assert len(ctx.primary_results) == 1 and len(ctx.secondary_results) == 3


def test_contract_signature_receives_both_top_k_values(monkeypatch):
    monkeypatch.setenv("TOP_K_PRIMARY", "1")
    monkeypatch.setenv("TOP_K_SECONDARY", "2")
    seen = {}

    def contract(query, output_visibility, top_k_primary, top_k_secondary):
        seen.update(p=top_k_primary, s=top_k_secondary)
        return {"primary_results": [], "secondary_results": []}
    _use_retrieve(monkeypatch, contract)
    pipeline.retrieve_context(_req())
    assert seen == {"p": 1, "s": 2}


# --- P2: a genuine TypeError inside retrieval is not hidden ---

def test_genuine_type_error_inside_retrieval_is_raised(monkeypatch):
    calls = []

    def broken(query, output_visibility, top_k_primary, top_k_secondary):
        calls.append(1)
        raise TypeError("bug inside Color B")
    _use_retrieve(monkeypatch, broken)
    with pytest.raises(TypeError, match="bug inside Color B"):
        pipeline.retrieve_context(_req())
    assert calls == [1]                                          # no silent retry with another signature


def test_retrieval_module_missing_raises_retrieval_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "src.retrieval", None)
    with pytest.raises(RetrievalError):
        pipeline.retrieve_context(_req())
