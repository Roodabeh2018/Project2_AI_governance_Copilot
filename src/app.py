"""Color C — local Gradio interface (build it AFTER the CLI works).

Run:  python -m src.app    → http://127.0.0.1:7860
Tabs: 1) Generate & review  2) Upload documents  3) Gap register
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import gradio as gr

from src import gap_register
from src.config import FIXTURES_DIR, PRIMARY_DIR, SECONDARY_DIR, ROOT
from src.contracts import (ConfigurationError, GenerationError, GenerationRequest, IngestionError,
                           RetrievalError, retrieval_context_from_dict)
from src.pipeline import DEFAULT_SYSTEM, approve, run_pipeline

FIXTURE = FIXTURES_DIR / "sample_retrieved_context.json"


def generate(request_type, ai_system, document_type, topic, visibility, feedback, use_fixture):
    request = GenerationRequest(
        request_type=request_type, document_type=document_type, ai_system=ai_system or DEFAULT_SYSTEM,
        topic=topic, output_visibility=visibility,
        selected_findings=[f"Reviewer feedback to apply: {feedback}"] if feedback else [])
    context = retrieval_context_from_dict(json.loads(FIXTURE.read_text(encoding="utf-8"))) if use_fixture else None
    try:
        draft = run_pipeline(request, context, save=False)
    except (ConfigurationError, RetrievalError, GenerationError) as exc:
        return f"**Error:** {exc}", [], None
    rows = [[r.chunk.kb, r.chunk.source_file, r.chunk.section, r.chunk.visibility, round(r.score, 3)]
            for r in request.primary_context + request.secondary_context]
    return draft.content_markdown, rows, (draft, request)


def decide(decision, reviewer, comment, state):
    if not state or state[0].status == "insufficient_source":
        return "Generate a draft first."
    if decision != "draft" and not reviewer.strip():
        return "Enter the reviewer name first."
    draft, request = state
    try:
        path, changes = approve(draft, request, reviewer.strip(), comment, decision)
    except GenerationError as exc:
        return f"**Not saved:** {exc}"
    msg = f"Saved `{path.relative_to(ROOT)}` — **{decision}**"
    return msg + ("\n\nGap register:\n" + "\n".join(f"- {c}" for c in changes) if changes else "")


def upload(files, kb):
    """Save into the KB (internal → primary, public → secondary), then ask A and B to rebuild."""
    if not files:
        return "Choose a file."
    target = PRIMARY_DIR if kb == "primary" else SECONDARY_DIR
    (target / "uploads").mkdir(parents=True, exist_ok=True)
    saved = []
    for f in files:
        dest = target / "uploads" / Path(f).name
        shutil.copy(f, dest)
        saved.append(f"- saved `{dest.relative_to(ROOT)}`")
    try:   # Color A + B interfaces (contract §5.1, §5.2)
        from src.chunking import chunk_documents, save_chunks
        from src.indexing import build_index
        from src.ingestion import load_documents
        from src.config import CACHE_DIR
        chunks = chunk_documents(load_documents(PRIMARY_DIR, SECONDARY_DIR))
        save_chunks(chunks, CACHE_DIR / "chunks.jsonl")
        build_index(chunks, CACHE_DIR)
        saved.append(f"\nIndex rebuilt with {len(chunks)} chunks.")
    except ImportError:
        saved.append("\n⚠️ Ingestion/index modules (Color A/B) not merged yet — file saved, index not rebuilt.")
    except (ConfigurationError, IngestionError, RetrievalError) as exc:
        saved.append(f"\n**Error while indexing:** {exc}")
    if kb == "secondary":
        changed = gap_register.mark_recheck("new regulation uploaded")
        saved.append(f"Regulation added → {len(changed)} complete item(s) set to re_check.")
    return "\n".join(saved)


def register(ai_system):
    icon = {"open": "🔴 open", "complete": "🟢 complete", "re_check": "🟡 re_check"}
    return [[r["requirement_id"], icon.get(r["status"], r["status"]), r["approved_by"], r["updated_at"][:16],
             r["ai_act_reference"], r["requirement"], r["sources"]] for r in gap_register.status_table(ai_system or DEFAULT_SYSTEM)]


with gr.Blocks(title="AI Governance Copilot") as demo:
    gr.Markdown("# AI Governance Copilot\nNorthstar Digital Bank (fictional) · every output is a draft for human review")
    state = gr.State(None)
    with gr.Tab("1 · Generate & review"):
        with gr.Row():
            request_type = gr.Radio(["governance_document", "internal_update"], value="governance_document",
                                    label="Output")
            visibility = gr.Radio(["internal", "public"], value="internal", label="Output visibility")
            use_fixture = gr.Checkbox(label="Use sample context (before Color B is merged)")
        with gr.Row():
            ai_system = gr.Textbox(DEFAULT_SYSTEM, label="AI system")
            document_type = gr.Textbox("AI System Monitoring Plan", label="Document to draft")
            topic = gr.Textbox("monitoring and human oversight", label="Topic")
        feedback = gr.Textbox(label="Reviewer feedback for a new draft (optional)")
        go = gr.Button("Generate", variant="primary")
        draft_md = gr.Markdown()
        sources = gr.Dataframe(headers=["KB", "File", "Section", "Visibility", "Score"], label="Retrieved sources")
        with gr.Row():
            reviewer = gr.Textbox(label="Reviewer name")
            comment = gr.Textbox(label="Comment")
        with gr.Row():
            ok_btn, no_btn, keep_btn = gr.Button("Approve"), gr.Button("Reject"), gr.Button("Save as draft")
        result_md = gr.Markdown()
        go.click(generate, [request_type, ai_system, document_type, topic, visibility, feedback, use_fixture],
                 [draft_md, sources, state])
        ok_btn.click(lambda r, c, s: decide("approved", r, c, s), [reviewer, comment, state], result_md)
        no_btn.click(lambda r, c, s: decide("rejected", r, c, s), [reviewer, comment, state], result_md)
        keep_btn.click(lambda r, c, s: decide("draft", r, c, s), [reviewer, comment, state], result_md)
    with gr.Tab("2 · Upload documents"):
        gr.Markdown("Internal company documents → **primary**. Public regulations → **secondary**.")
        files = gr.File(file_count="multiple", file_types=[".md", ".txt", ".pdf"], type="filepath")
        kb = gr.Radio(["primary", "secondary"], value="primary", label="Knowledge base")
        up_btn = gr.Button("Upload and re-index", variant="primary")
        up_msg = gr.Markdown()
        up_btn.click(upload, [files, kb], up_msg)
    with gr.Tab("3 · Gap register"):
        reg_sys = gr.Textbox(DEFAULT_SYSTEM, label="AI system")
        reg_btn = gr.Button("Refresh")
        reg_tbl = gr.Dataframe(headers=["ID", "Status", "Approved by", "Updated", "EU AI Act", "Requirement", "Sources"], wrap=True)
        reg_btn.click(register, reg_sys, reg_tbl)
        demo.load(register, reg_sys, reg_tbl)

if __name__ == "__main__":
    demo.launch()
