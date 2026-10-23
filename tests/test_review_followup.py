"""Regression tests for the retrospective review of PR #1 (Color C).

Offline: LLM_PROVIDER=mock, shared fixtures, a temporary gap register.
"""
import json
import os
import sys
from pathlib import Path

import pytest

os.environ["LLM_PROVIDER"] = "mock"
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import gap_register, llm_generator, pipeline  # noqa: E402
from src.contracts import (DRAFT_STATUS, GenerationError, GenerationRequest,  # noqa: E402
                           retrieval_context_from_dict)

FIX = ROOT / "tests" / "fixtures"


def _ctx(name="sample_retrieved_context.json"):
    return retrieval_context_from_dict(json.loads((FIX / name).read_text(encoding="utf-8")))


def _req(request_type="governance_document", visibility="internal"):
    return GenerationRequest(request_type=request_type, document_type="AI System Monitoring Plan",
                             ai_system="Credit Decision Support AI", topic="monitoring and human oversight",
                             output_visibility=visibility)


@pytest.fixture(autouse=True)
def temp_register(tmp_path, monkeypatch):
    monkeypatch.setattr(gap_register, "REGISTER", tmp_path / "gap_register.json")
    monkeypatch.setattr(pipeline, "OUTPUT_DIR", tmp_path / "outputs")
    monkeypatch.setattr(pipeline, "ROOT", tmp_path)


# --- P1.1: visibility is enforced on a pre-populated request ---

def test_prepopulated_public_request_never_sends_internal_text_to_the_prompt(monkeypatch):
    ctx = _ctx()
    req = _req(visibility="public")
    req.primary_context, req.secondary_context = ctx.primary_results, ctx.secondary_results
    assert any(r.chunk.visibility == "internal" for r in req.primary_context)
    prompts = []
    monkeypatch.setattr(llm_generator, "generate_text",
                        lambda prompt: prompts.append(prompt) or llm_generator._mock_answer(prompt))
    pipeline.run_pipeline(req, save=False)
    assert all(r.chunk.visibility == "public" for r in req.primary_context + req.secondary_context)
    internal_text = [r.chunk.text[:60] for r in ctx.primary_results if r.chunk.visibility == "internal"]
    assert prompts and not any(t in prompts[0] for t in internal_text)


# --- P2.6: sufficiency is re-checked after visibility filtering ---

def test_public_request_with_only_internal_context_returns_insufficient_source():
    ctx = _ctx()
    ctx.secondary_results = []
    draft = pipeline.run_pipeline(_req(visibility="public"), ctx, save=False)
    assert draft.status == "insufficient_source"


# --- P1.2: the gap register needs valid IDs, statuses and supporting references ---

def _approve_with_findings(findings):
    req = _req("internal_update")
    draft = pipeline.run_pipeline(req, _ctx(), save=False)
    draft.content_markdown = draft.content_markdown.split("```json")[0] + \
        "```json\n" + json.dumps(findings) + "\n```\n"
    return pipeline.approve(draft, req, "Reviewer")


def test_evidence_found_without_sources_does_not_mark_complete():
    with pytest.raises(GenerationError, match="evidence_found without a supporting"):
        _approve_with_findings([{"requirement_id": "MON-02", "status": "evidence_found", "sources": []}])
    assert gap_register.status_table("Credit Decision Support AI")[6]["status"] == "open"
    assert not gap_register.REGISTER.exists()


@pytest.mark.parametrize("finding, message", [
    ({"requirement_id": "XYZ-01", "status": "evidence_incomplete", "sources": ["P1"]}, "not a requirement"),
    ({"requirement_id": "MON-02", "status": "done", "sources": ["P1"]}, "status"),
    ({"requirement_id": "MON-02", "status": "evidence_found", "sources": ["P9"]}, "not supplied"),
    ({"requirement_id": "MON-02", "status": "evidence_found", "sources": ["S1"]}, "company document"),
])
def test_invalid_findings_are_rejected_and_nothing_is_saved(finding, message):
    with pytest.raises(GenerationError, match=message):
        _approve_with_findings([finding])
    assert not gap_register.REGISTER.exists()
    assert not (pipeline.OUTPUT_DIR / "internal_updates").exists()


def test_valid_evidence_found_marks_complete_with_full_references():
    path, changes = _approve_with_findings(
        [{"requirement_id": "MON-02", "status": "evidence_found", "sources": ["P1", "S1"], "note": "ok"}])
    assert changes == ["MON-02: open → complete"]
    row = gap_register.status_table("Credit Decision Support AI")[6]
    assert row["status"] == "complete" and "P1: human_oversight_procedure.md" in row["sources"]


# --- P2.3: missing status line is guaranteed, compliance verdicts are rejected ---

def test_missing_status_line_is_added(monkeypatch):
    monkeypatch.setattr(llm_generator, "generate_text",
                        lambda prompt: llm_generator._mock_answer(prompt).replace(f"Status: {DRAFT_STATUS}", ""))
    draft = pipeline.run_pipeline(_req(), _ctx(), save=False)
    assert f"Status: {DRAFT_STATUS}" in draft.content_markdown


def test_compliance_verdict_is_not_valid_output(monkeypatch):
    monkeypatch.setattr(llm_generator, "generate_text",
                        lambda prompt: llm_generator._mock_answer(prompt) + "\nThe system is fully compliant [P1].")
    with pytest.raises(GenerationError, match="compliance verdict"):
        pipeline.run_pipeline(_req(), _ctx(), save=False)


def test_unsaveable_draft_cannot_be_saved():
    draft = pipeline.run_pipeline(_req(), _ctx(), save=False)
    draft.content_markdown = draft.content_markdown.replace(DRAFT_STATUS, "Final")
    with pytest.raises(GenerationError, match="status line"):
        pipeline.save_markdown(draft)


# --- P2.4: the saved Source Register keeps the full locator ---

def test_saved_markdown_contains_full_locators():
    ctx = _ctx()
    draft = pipeline.run_pipeline(_req(), ctx, save=False)
    text = pipeline.save_markdown(draft).read_text(encoding="utf-8")
    for r in ctx.primary_results + ctx.secondary_results:
        assert r.citation in text


# --- P2.5: malformed findings JSON gives a controlled error ---

@pytest.mark.parametrize("payload", ["null", "123", '{"requirement_id": "MON-02"}', "[1, 2]",
                                     '[{"requirement_id": "MON-02", "status": "evidence_found", "sources": "P1"}]',
                                     "[{not json"])
def test_malformed_findings_raise_generation_error(payload):
    with pytest.raises(GenerationError):
        llm_generator.parse_findings(f"```json\n{payload}\n```")


# --- Re-review of e2acabe ---

@pytest.mark.parametrize("sentence", [
    "Northstar Digital Bank complies with the EU AI Act.",
    "Northstar Digital Bank is noncompliant with the EU AI Act.",
    "The system is compliant with Article 14.",
    "The bank is not compliant with Article 26.",
    "The system is fully compliant.",
    "Northstar is in full compliance with the AI Act.",
    "The deployer violates Article 26(5).",
])
def test_common_compliance_verdicts_are_rejected(monkeypatch, sentence):
    monkeypatch.setattr(llm_generator, "generate_text",
                        lambda prompt: llm_generator._mock_answer(prompt) + f"\n{sentence} [P1]")
    with pytest.raises(GenerationError, match="compliance verdict"):
        pipeline.run_pipeline(_req(), _ctx(), save=False)


@pytest.mark.parametrize("sentence", [
    "The plan supports ensuring compliance with relevant regulations [S1].",
    "This draft is not a compliance determination [P1].",
])
def test_non_verdict_compliance_wording_is_allowed(monkeypatch, sentence):
    monkeypatch.setattr(llm_generator, "generate_text",
                        lambda prompt: llm_generator._mock_answer(prompt) + f"\n{sentence}")
    assert pipeline.run_pipeline(_req(), _ctx(), save=False).status == DRAFT_STATUS


def test_sufficiency_is_judged_on_the_filtered_context(monkeypatch):
    """Strong internal evidence + weak public results: after filtering, the weak rest is not enough."""
    import types
    strong = lambda ctx: any(r.score >= 0.5 for r in ctx.primary_results + ctx.secondary_results)  # noqa: E731
    monkeypatch.setitem(sys.modules, "src.retrieval", types.SimpleNamespace(has_sufficient_source=strong))
    ctx = _ctx()
    for r in ctx.secondary_results:
        r.score = 0.1                                            # weak public results
    called = []
    monkeypatch.setattr(llm_generator, "generate_text", lambda prompt: called.append(prompt) or "")
    draft = pipeline.run_pipeline(_req(visibility="public"), ctx, save=False)
    assert draft.status == "insufficient_source" and called == []

    req = _req(visibility="public")                              # pre-populated path
    req.primary_context, req.secondary_context = ctx.primary_results, ctx.secondary_results
    assert pipeline.run_pipeline(req, save=False).status == "insufficient_source" and called == []


def test_status_phrase_elsewhere_does_not_count_as_status_line(monkeypatch):
    def answer(prompt):
        return llm_generator._mock_answer(prompt).replace(
            f"Status: {DRAFT_STATUS}", f"Source document label: {DRAFT_STATUS}")
    monkeypatch.setattr(llm_generator, "generate_text", answer)
    draft = pipeline.run_pipeline(_req(), _ctx(), save=False)
    assert f"\nStatus: {DRAFT_STATUS}\n" in draft.content_markdown
    draft.content_markdown = draft.content_markdown.replace(f"Status: {DRAFT_STATUS}", "")
    with pytest.raises(GenerationError, match="status line"):
        pipeline.save_markdown(draft)


@pytest.mark.parametrize("status", ["[]", "{}"])
def test_non_string_status_raises_generation_error(status):
    with pytest.raises(GenerationError, match="status"):
        llm_generator.parse_findings(f'```json\n[{{"requirement_id": "MON-02", "status": {status}, "sources": []}}]\n```')
