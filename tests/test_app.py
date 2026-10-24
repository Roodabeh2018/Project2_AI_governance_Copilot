"""UI tests for the Gradio app (Color C). Offline: LLM_PROVIDER=mock, shared fixture, temporary files.

They check that the human-readable controls still pass the exact contract values to the pipeline,
that the findings JSON is hidden from the readable draft but kept in the state, and that review
buttons are only enabled when there is a draft to review.
"""
import json
import os
import sys
from pathlib import Path

import pytest

os.environ["LLM_PROVIDER"] = "mock"
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import app, gap_register, pipeline  # noqa: E402
from src.contracts import DRAFT_STATUS, RetrievalError  # noqa: E402


@pytest.fixture(autouse=True)
def temp_files(tmp_path, monkeypatch):
    monkeypatch.setattr(gap_register, "REGISTER", tmp_path / "gap_register.json")
    monkeypatch.setattr(pipeline, "OUTPUT_DIR", tmp_path / "outputs")
    monkeypatch.setattr(pipeline, "ROOT", tmp_path)
    monkeypatch.setattr(app, "ROOT", tmp_path)


def _interactive(update):
    return update.get("interactive")


def test_labels_map_to_unchanged_contract_values():
    assert [v for _, v in app.REQUEST_TYPES] == ["governance_document", "internal_update"]
    assert [v for _, v in app.VISIBILITIES] == ["internal", "public"]
    assert [v for _, v in app.KNOWLEDGE_BASES] == ["primary", "secondary"]
    assert "Credit Decision Support AI" in app.known_ai_systems()
    assert app.DOCUMENT_TYPES[0] == "AI System Monitoring Plan" and len(app.DOCUMENT_TYPES) == 6


def test_selected_values_are_passed_to_the_pipeline_exactly(monkeypatch):
    seen = {}
    real = app.run_pipeline

    def spy(request, context=None, save=True):
        seen.update(request_type=request.request_type, ai_system=request.ai_system,
                    document_type=request.document_type, topic=request.topic,
                    visibility=request.output_visibility, findings=request.selected_findings, save=save)
        return real(request, context, save=save)
    monkeypatch.setattr(app, "run_pipeline", spy)
    app.generate("governance_document", "Custom System X", "My custom document", "my own topic",
                 "public", "shorter please", True)
    assert seen == {"request_type": "governance_document", "ai_system": "Custom System X",
                    "document_type": "My custom document", "topic": "my own topic", "visibility": "public",
                    "findings": ["Reviewer feedback to apply: shorter please"], "save": False}


def test_findings_json_is_hidden_from_the_draft_but_kept_in_state():
    header, readable, findings, rows, state, msg, ok, no, keep = app.generate(
        "internal_update", "Credit Decision Support AI", "", "monitoring and human oversight",
        "internal", "", True)
    assert "```json" not in readable and DRAFT_STATUS in readable
    assert json.loads(findings) and "requirement_id" in findings
    assert "```json" in state[0].content_markdown                     # still there for approval/validation
    assert rows and all(_interactive(b) for b in (ok, no, keep))
    assert "badge-draft" in header and "not a compliance determination" in header


def test_review_buttons_stay_disabled_without_a_draft(monkeypatch):
    monkeypatch.setattr(app, "FIXTURE", ROOT / "tests" / "fixtures" / "sample_retrieved_context_negative.json")
    header, readable, findings, rows, state, msg, ok, no, keep = app.generate(
        "governance_document", "Credit Decision Support AI", "AI System Monitoring Plan", "monitoring",
        "internal", "", True)
    assert state is None and not any(_interactive(b) for b in (ok, no, keep))
    assert "Insufficient source" in header and "Nothing can be approved" in msg


def test_generation_error_is_shown_near_the_action(monkeypatch):
    def failing(*_a, **_k):
        raise RetrievalError("index not built yet")
    monkeypatch.setattr(app, "run_pipeline", failing)
    *_, state, msg, ok, no, keep = app.generate(
        "governance_document", "Credit Decision Support AI", "AI System Monitoring Plan", "monitoring",
        "internal", "", False)
    assert state is None and "index not built yet" in msg and "msg-error" in msg
    assert not any(_interactive(b) for b in (ok, no, keep))


def test_approval_flow_unchanged_and_badge_updates():
    *_, state, _msg, _ok, _no, _keep = app.generate(
        "internal_update", "Credit Decision Support AI", "", "monitoring and human oversight", "internal", "", True)
    msg, header, ok, no, keep = app.decide("approved", "", "", state)
    assert "reviewer name" in msg
    msg, header, ok, no, keep = app.decide("approved", "Roodi", "", state)
    assert "Saved" in msg and "badge-approved" in header
    assert not any(_interactive(b) for b in (ok, no, keep))         # cannot approve twice
    assert gap_register.REGISTER.exists()


def test_decide_without_draft():
    msg, *_ = app.decide("approved", "Roodi", "", None)
    assert "Generate a draft first" in msg


def test_upload_reports_index_failure_separately(tmp_path, monkeypatch):
    monkeypatch.setattr(app, "PRIMARY_DIR", tmp_path / "primary")
    doc = tmp_path / "note.md"
    doc.write_text("# Note\ntext", encoding="utf-8")
    import src.indexing as indexing

    def broken(*_a, **_k):
        raise RetrievalError("embedding service unavailable")
    monkeypatch.setattr(indexing, "build_index", broken)
    msg = app.upload([str(doc)], "primary")
    assert "Upload succeeded" in msg and "re-indexing failed" in msg and "embedding service unavailable" in msg
    assert app.selected_files([str(doc)]) == "Selected: note.md"


def test_register_summary_counts_and_legend():
    summary = app.register_summary("Credit Decision Support AI")
    assert "Open: <b>8</b>" in summary and "Complete: <b>0</b>" in summary and "Last refreshed" in summary
    rows = app.register("Credit Decision Support AI")
    assert len(rows) == 8 and rows[0][1] == "🔴 Open" and len(rows[0]) == len(app.REGISTER_HEADERS)
