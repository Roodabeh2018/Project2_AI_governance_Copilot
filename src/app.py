"""Color C — local Gradio interface.

Run:  python -m src.app    → http://127.0.0.1:7860
Tabs: 1) Generate & review  2) Upload documents  3) Gap register

UI only: the values passed to run_pipeline / approve / gap_register are the same contract values
as before (request_type, output_visibility, kb …). Human-readable labels are mapped to them here.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import re
import shutil
from pathlib import Path

import gradio as gr

from src import gap_register
from src.config import FIXTURES_DIR, PRIMARY_DIR, SECONDARY_DIR, ROOT, llm_provider
from src.contracts import (ConfigurationError, GenerationError, GenerationRequest, IngestionError,
                           RetrievalError, retrieval_context_from_dict)
from src.pipeline import DEFAULT_SYSTEM, approve, run_pipeline

FIXTURE = FIXTURES_DIR / "sample_retrieved_context.json"

# ---------- choices: (label shown to the user, contract value passed to the pipeline) ----------

REQUEST_TYPES = [("Governance document", "governance_document"), ("Internal update", "internal_update")]
VISIBILITIES = [("Internal / company-sensitive", "internal"), ("Public", "public")]
KNOWLEDGE_BASES = [("Primary: internal company documents", "primary"),
                   ("Secondary: public regulations and uploaded public sources", "secondary")]
DOCUMENT_TYPES = ["AI System Monitoring Plan", "Human Oversight Procedure", "AI Risk Assessment",
                  "Technical Documentation", "Testing and Validation Plan", "AI Incident Response Procedure"]
TOPICS = ["monitoring and human oversight", "risk classification", "technical documentation", "incident response"]

SAMPLE_CONTEXT_LABEL = "Use sample source context"


def sample_context_info() -> str:
    """Honest helper text: the sample replaces retrieval only, never generation."""
    if llm_provider() == "mock":
        return ("Skips the knowledge-base search and uses a saved example. Generation is in mock mode "
                "(LLM_PROVIDER=mock): no API calls, no cost.")
    return ("Skips the knowledge-base search and uses a saved example. Generation still uses the configured "
            "model and may incur API charges. For a fully offline test, set LLM_PROVIDER=mock.")


STATUS_ICON = {"open": "🔴 Open", "complete": "🟢 Complete", "re_check": "🟡 Re-check"}
DECISION_BADGE = {"draft": ("Draft — human review required", "badge-draft"),
                  "approved": ("Approved", "badge-approved"),
                  "rejected": ("Rejected", "badge-rejected"),
                  "insufficient_source": ("Insufficient source", "badge-rejected")}
REGISTER_HEADERS = ["ID", "Status", "Requirement", "EU AI Act", "Sources", "Approved by", "Updated"]

FINDINGS_BLOCK = re.compile(r"\n*```json\s*(.*?)```\n*", re.S)


def known_ai_systems() -> list[str]:
    """The default system plus every system that already has gap-register entries."""
    systems = [DEFAULT_SYSTEM]
    for name in gap_register._load().get("systems", {}):
        if name not in systems:
            systems.append(name)
    return systems


def split_findings(markdown: str) -> tuple[str, str]:
    """(human-readable draft, machine-readable findings JSON). The JSON stays in the draft object."""
    match = FINDINGS_BLOCK.search(markdown)
    if not match:
        return markdown, ""
    readable = FINDINGS_BLOCK.sub("\n\n", markdown, count=1).strip() + "\n"
    return readable, match.group(1).strip()


def _badge(kind: str) -> str:
    text, css = DECISION_BADGE.get(kind, DECISION_BADGE["draft"])
    return f'<span class="badge {css}">{html.escape(text)}</span>'


def result_header(title: str, kind: str, evidence_status: str = "") -> str:
    evidence = (f'<span class="evidence">Evidence status: <b>{html.escape(evidence_status.replace("_", " "))}</b></span>'
                if evidence_status else "")
    return (f'<div class="result-head"><h3>{html.escape(title)}</h3>{_badge(kind)}{evidence}</div>'
            '<p class="disclaimer">This is a draft for human review. It is not a compliance determination.</p>')


def _buttons(enabled: bool):
    return gr.update(interactive=enabled), gr.update(interactive=enabled), gr.update(interactive=enabled)


# ---------- tab 1: generate & review ----------

def generate(request_type, ai_system, document_type, topic, visibility, feedback, use_fixture):
    """Same pipeline call as before; returns header, readable draft, findings JSON, sources, state, message, buttons."""
    request = GenerationRequest(
        request_type=request_type, document_type=document_type, ai_system=ai_system or DEFAULT_SYSTEM,
        topic=topic, output_visibility=visibility,
        selected_findings=[f"Reviewer feedback to apply: {feedback}"] if feedback else [])
    context = retrieval_context_from_dict(json.loads(FIXTURE.read_text(encoding="utf-8"))) if use_fixture else None
    try:
        draft = run_pipeline(request, context, save=False)
    except (ConfigurationError, RetrievalError, GenerationError) as exc:
        return ("", "", "", [], None, f'<p class="msg-error">❌ Could not generate a draft: {html.escape(str(exc))}</p>',
                *_buttons(False))
    rows = [[r.chunk.kb, r.chunk.source_file, r.chunk.section, r.chunk.visibility, round(r.score, 3)]
            for r in request.primary_context + request.secondary_context]
    readable, findings = split_findings(draft.content_markdown)
    if draft.status == "insufficient_source":
        return (result_header("Insufficient source", "insufficient_source"), readable, "", rows, None,
                '<p class="msg-warn">⚠️ No draft was created: the sources are not sufficient. Nothing can be approved.</p>',
                *_buttons(False))
    header = result_header(draft.title, "draft", draft.evidence_status)
    return (header, readable, findings, rows, (draft, request),
            '<p class="msg-ok">✅ Draft generated. Inspect the sources, then approve, reject or save it as a draft.</p>',
            *_buttons(True))


def decide(decision, reviewer, comment, state):
    """Returns (message, header, approve/reject/save button updates). Approval logic unchanged."""
    keep = (gr.update(), gr.update(), gr.update())
    if not state or state[0].status == "insufficient_source":
        return '<p class="msg-warn">⚠️ Generate a draft first.</p>', gr.update(), *keep
    if decision != "draft" and not reviewer.strip():
        return '<p class="msg-warn">⚠️ Enter the reviewer name first.</p>', gr.update(), *keep
    draft, request = state
    try:
        path, changes = approve(draft, request, reviewer.strip(), comment, decision)
    except GenerationError as exc:
        return f'<p class="msg-error">❌ Not saved: {html.escape(str(exc))}</p>', gr.update(), *keep
    msg = f'<p class="msg-ok">✅ Saved <code>{html.escape(str(path.relative_to(ROOT)))}</code> as <b>{decision}</b>.</p>'
    if changes:
        msg += "<p>Gap register updated:</p><ul>" + "".join(f"<li>{html.escape(c)}</li>" for c in changes) + "</ul>"
    header = result_header(draft.title, decision, draft.evidence_status)
    final = decision in ("approved", "rejected")          # a decided draft cannot be decided twice
    return (msg, header, *_buttons(not final))


# ---------- tab 2: upload ----------

def selected_files(files) -> str:
    if not files:
        return "No files selected."
    return "Selected: " + ", ".join(Path(f).name for f in files)


def upload(files, kb):
    """Save into the KB, then rebuild the index (Colors A + B). Upload and indexing results are reported separately."""
    if not files:
        return '<p class="msg-warn">⚠️ Choose at least one file (.md, .txt or .pdf).</p>'
    target = PRIMARY_DIR if kb == "primary" else SECONDARY_DIR
    (target / "uploads").mkdir(parents=True, exist_ok=True)
    saved = []
    for f in files:
        dest = target / "uploads" / Path(f).name
        shutil.copy(f, dest)
        saved.append(html.escape(str(dest.relative_to(ROOT))))
    lines = [f'<p class="msg-ok">✅ Upload succeeded: {len(saved)} file(s) saved.</p>',
             "<ul>" + "".join(f"<li><code>{s}</code></li>" for s in saved) + "</ul>"]
    try:   # Color A + B interfaces (contract §5.1, §5.2)
        from src.chunking import chunk_documents, save_chunks
        from src.config import CACHE_DIR
        from src.indexing import build_index
        from src.ingestion import load_documents
        chunks = chunk_documents(load_documents(PRIMARY_DIR, SECONDARY_DIR))
        save_chunks(chunks, CACHE_DIR / "chunks.jsonl")
        build_index(chunks, CACHE_DIR)
        lines.append(f'<p class="msg-ok">✅ Search index rebuilt with {len(chunks)} chunks.</p>')
    except ImportError:
        lines.append('<p class="msg-error">❌ Upload succeeded, but the search index was not rebuilt '
                     '(indexing modules missing).</p>')
    except (ConfigurationError, IngestionError, RetrievalError) as exc:
        lines.append(f'<p class="msg-error">❌ Upload succeeded, but re-indexing failed: {html.escape(str(exc))}</p>')
    if kb == "secondary":
        changed = gap_register.mark_recheck("new regulation uploaded")
        lines.append(f"<p>New public source added: {len(changed)} complete item(s) set to 🟡 Re-check.</p>")
    return "\n".join(lines)


# ---------- tab 3: gap register ----------

def register(ai_system):
    return [[r["requirement_id"], STATUS_ICON.get(r["status"], r["status"]), r["requirement"], r["ai_act_reference"],
             r["sources"], r["approved_by"], r["updated_at"][:16].replace("T", " ")]
            for r in gap_register.status_table(ai_system or DEFAULT_SYSTEM)]


def register_summary(ai_system) -> str:
    rows = gap_register.status_table(ai_system or DEFAULT_SYSTEM)
    count = {s: sum(r["status"] == s for r in rows) for s in ("open", "complete", "re_check")}
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    return (f'<div class="summary"><span>🔴 Open: <b>{count["open"]}</b></span>'
            f'<span>🟢 Complete: <b>{count["complete"]}</b></span>'
            f'<span>🟡 Re-check: <b>{count["re_check"]}</b></span>'
            f'<span class="muted">Last refreshed: {now}</span></div>')


def refresh_register(ai_system):
    return register_summary(ai_system), register(ai_system)


# ---------- layout ----------

CSS = """
.panel {border: 1px solid #e5e2da; border-radius: 12px; padding: 16px; background: #fbfaf7;}
.steps {font-size: 15px; color: #4a5568;}
.result-head {display: flex; flex-wrap: wrap; align-items: center; gap: 12px;}
.result-head h3 {margin: 0;}
.badge {padding: 4px 12px; border-radius: 999px; font-weight: 600; font-size: 14px;}
.badge-draft {background: #eef1f6; color: #23314f; border: 1px solid #c9d3e3;}
.badge-approved {background: #e3f4e8; color: #14532d; border: 1px solid #8fd1a4;}
.badge-rejected {background: #fbe7e7; color: #7f1d1d; border: 1px solid #efa6a6;}
.evidence {font-size: 15px; color: #4a5568;}
.disclaimer {font-size: 14px; color: #6b7280; margin-top: 6px;}
.msg-ok {color: #14532d;} .msg-error {color: #991b1b;} .msg-warn {color: #92400e;}
.summary {display: flex; flex-wrap: wrap; gap: 20px; font-size: 16px;}
.muted {color: #6b7280;}
table thead th {font-weight: 700 !important;}
"""
THEME = gr.themes.Soft(primary_hue="orange", secondary_hue="slate", neutral_hue="slate")

with gr.Blocks(title="AI Governance Copilot") as demo:
    gr.Markdown("# AI Governance Copilot\nNorthstar Digital Bank (fictional) · every output is a **draft for human review**")
    state = gr.State(None)

    with gr.Tab("1 · Generate & review"):
        gr.Markdown("Create a source-grounded draft, inspect its sources, then approve, reject or save it.\n\n"
                    "**Configure → Generate → Inspect sources → Review → Approve / Reject / Save draft**",
                    elem_classes="steps")
        with gr.Group(elem_classes="panel"):
            gr.Markdown("### 1. Request type")
            request_type = gr.Radio(REQUEST_TYPES, value="governance_document", label="Output type",
                                    info="Governance document: a full draft document. Internal update: a short "
                                         "status update with findings per requirement for the gap register.")
        with gr.Group(elem_classes="panel"):
            gr.Markdown("### 2. Source and visibility")
            with gr.Row():
                visibility = gr.Radio(VISIBILITIES, value="internal", label="Who may read the output?",
                                      info="Public outputs only use sources tagged public.")
                use_fixture = gr.Checkbox(label=SAMPLE_CONTEXT_LABEL, info=sample_context_info())
        with gr.Group(elem_classes="panel"):
            gr.Markdown("### 3. Draft details")
            with gr.Row():
                ai_system = gr.Dropdown(known_ai_systems(), value=DEFAULT_SYSTEM, allow_custom_value=True,
                                        label="Which AI system are you reviewing?",
                                        info="Pick one or type a new system name.")
                document_type = gr.Dropdown(DOCUMENT_TYPES, value=DOCUMENT_TYPES[0], allow_custom_value=True,
                                            label="What should be generated?",
                                            info="Used for governance documents. Pick one or type your own.")
                topic = gr.Dropdown(TOPICS, value=TOPICS[0], allow_custom_value=True,
                                    label="What is the topic or question?",
                                    info="Pick a suggestion or type your own.")
        with gr.Group(elem_classes="panel"):
            gr.Markdown("### 4. Review feedback")
            feedback = gr.Textbox(label="Instructions for the next draft (optional)",
                                  info="Filled in after a review: what should the next draft change?")
        go = gr.Button("Generate draft", variant="primary")
        gen_msg = gr.HTML()

        with gr.Group(elem_classes="panel"):
            gr.Markdown("### 5. Generated result and approval")
            header = gr.HTML(result_header("No draft yet", "draft"))
            draft_md = gr.Markdown()
            sources = gr.Dataframe(headers=["KB", "File", "Section", "Visibility", "Score"], label="Retrieved sources",
                                   wrap=True, interactive=False)
            with gr.Accordion("Technical details: machine-readable findings", open=False):
                findings_json = gr.Code(language="json", label="Findings JSON (used for the gap register)",
                                        interactive=False)
            with gr.Row():
                reviewer = gr.Textbox(label="Reviewer name", info="Required to approve or reject.")
                comment = gr.Textbox(label="Comment")
            with gr.Row():
                ok_btn = gr.Button("Approve", variant="primary", interactive=False)
                no_btn = gr.Button("Reject", variant="secondary", interactive=False)
                keep_btn = gr.Button("Save as draft", variant="secondary", interactive=False)
            result_md = gr.HTML()

        gen_inputs = [request_type, ai_system, document_type, topic, visibility, feedback, use_fixture]
        gen_outputs = [header, draft_md, findings_json, sources, state, gen_msg, ok_btn, no_btn, keep_btn]
        go.click(lambda: ('<p class="msg-warn">⏳ Generating the draft…</p>', *_buttons(False)), None,
                 [gen_msg, ok_btn, no_btn, keep_btn]).then(generate, gen_inputs, gen_outputs, show_progress="full")
        decide_outputs = [result_md, header, ok_btn, no_btn, keep_btn]
        ok_btn.click(lambda r, c, s: decide("approved", r, c, s), [reviewer, comment, state], decide_outputs)
        no_btn.click(lambda r, c, s: decide("rejected", r, c, s), [reviewer, comment, state], decide_outputs)
        keep_btn.click(lambda r, c, s: decide("draft", r, c, s), [reviewer, comment, state], decide_outputs)

    with gr.Tab("2 · Upload documents"):
        gr.Markdown("Choose the correct knowledge base, upload, and the search index is rebuilt automatically.",
                    elem_classes="steps")
        with gr.Group(elem_classes="panel"):
            kb = gr.Radio(KNOWLEDGE_BASES, value="primary", label="Knowledge base",
                          info="Primary: internal company documents. Secondary: public regulations and public sources.")
            files = gr.File(file_count="multiple", file_types=[".md", ".txt", ".pdf"], type="filepath",
                            label="Documents (.md, .txt, .pdf)")
            chosen = gr.Markdown("No files selected.")
            up_btn = gr.Button("Upload documents and rebuild search index", variant="primary")
            up_msg = gr.HTML()
        files.change(selected_files, files, chosen)
        up_btn.click(lambda: '<p class="msg-warn">⏳ Uploading and rebuilding the search index…</p>', None, up_msg) \
            .then(upload, [files, kb], up_msg, show_progress="full")

    with gr.Tab("3 · Gap register"):
        gr.Markdown("Review the evidence status per requirement. 🔴 **Open**: evidence missing or incomplete · "
                    "🟢 **Complete**: an approved update found supporting evidence · 🟡 **Re-check**: a new public "
                    "source was added, review again.\n\n*Complete means approved evidence was found in the supplied "
                    "documents. It does not mean legal compliance was established.*", elem_classes="steps")
        with gr.Group(elem_classes="panel"):
            with gr.Row():
                reg_sys = gr.Dropdown(known_ai_systems(), value=DEFAULT_SYSTEM, allow_custom_value=True,
                                      label="AI system")
                reg_btn = gr.Button("Refresh", variant="secondary")
            reg_summary = gr.HTML()
            reg_tbl = gr.Dataframe(headers=REGISTER_HEADERS, wrap=True, interactive=False,
                                   column_widths=["8%", "12%", "28%", "14%", "20%", "9%", "9%"])
        reg_btn.click(refresh_register, reg_sys, [reg_summary, reg_tbl])
        reg_sys.change(refresh_register, reg_sys, [reg_summary, reg_tbl])
        demo.load(refresh_register, reg_sys, [reg_summary, reg_tbl])

if __name__ == "__main__":
    # Host, port and optional login come from src.config (contract §8); see launch_settings().
    from src.config import launch_settings
    demo.launch(**launch_settings(), theme=THEME, css=CSS)
