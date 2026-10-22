"""Color C tests — run offline with the shared fixtures (no API key, no cost).

    pytest tests/test_pipeline.py          # or: python tests/test_pipeline.py
"""
import json
import os
import sys
from pathlib import Path

os.environ["LLM_PROVIDER"] = "mock"
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.contracts import (DRAFT_STATUS, GenerationRequest, generation_request_from_dict,  # noqa: E402
                           retrieval_context_from_dict)
from src.pipeline import run_pipeline  # noqa: E402
from src.prompts import build_prompt  # noqa: E402

FIX = ROOT / "tests" / "fixtures"


def _ctx(name):
    return retrieval_context_from_dict(json.loads((FIX / name).read_text(encoding="utf-8")))


def _req(request_type="governance_document", visibility="internal"):
    return GenerationRequest(request_type=request_type, document_type="AI System Monitoring Plan",
                             ai_system="Credit Decision Support AI", topic="monitoring and human oversight",
                             output_visibility=visibility)


def test_prompt_has_separate_primary_and_secondary_slots():
    req = generation_request_from_dict(json.loads((FIX / "sample_generation_request.json").read_text()))
    prompt = build_prompt(req)
    assert "PRIMARY CONTEXT" in prompt and "SECONDARY CONTEXT" in prompt
    assert "[P1]" in prompt and "[S1]" in prompt and "{" not in prompt.split("```json")[0].replace("{{", "")


def test_governance_document_draft():
    draft = run_pipeline(_req(), _ctx("sample_retrieved_context.json"), save=False)
    assert draft.status == DRAFT_STATUS
    assert draft.citations and draft.evidence_status in ("evidence_found", "evidence_incomplete", "evidence_not_found")
    assert "## Source Register" in draft.content_markdown


def test_internal_update_has_findings_json():
    draft = run_pipeline(_req("internal_update"), _ctx("sample_retrieved_context.json"), save=False)
    assert "```json" in draft.content_markdown


def test_negative_query_returns_insufficient_source():
    draft = run_pipeline(_req(), _ctx("sample_retrieved_context_negative.json"), save=False)
    assert draft.status == "insufficient_source" and draft.output_path is None


def test_public_output_never_receives_internal_chunks():
    req = _req(visibility="public")
    run_pipeline(req, _ctx("sample_retrieved_context.json"), save=False)
    assert all(r.chunk.visibility == "public" for r in req.primary_context + req.secondary_context)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"PASS  {name}")
