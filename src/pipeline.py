"""Color C — end-to-end pipeline (contract §5.4) + CLI with human review.

Request → Retrieval (Color B) → Visibility filtering → Prompt → LLM → Output validation → Markdown save

Until Color B's src/retrieval.py is ready, use the shared fixture:
    python -m src.pipeline --type governance_document --fixture tests/fixtures/sample_retrieved_context.json
With Color B ready:
    python -m src.pipeline --type governance_document --document "AI System Monitoring Plan" --topic "monitoring and human oversight"
    python -m src.pipeline --type internal_update --topic "monitoring and human oversight"
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

from src import gap_register
from src.config import OUTPUT_DIR, ROOT, load_config
from src.contracts import (ConfigurationError, GeneratedDraft, GenerationError, GenerationRequest,
                           RetrievalContext, RetrievalError, retrieval_context_from_dict)
from src.llm_generator import generate_draft, parse_findings

DEFAULT_SYSTEM = "Credit Decision Support AI"
OUTPUT_FOLDERS = {"governance_document": "governance_documents", "internal_update": "internal_updates"}


# ---------- steps ----------

def build_query(request: GenerationRequest) -> str:
    parts = [request.ai_system if request.output_visibility == "internal" else None,
             request.document_type if request.request_type == "governance_document" else None,
             request.topic]
    return " ".join(p for p in parts if p)


def retrieve_context(request: GenerationRequest) -> RetrievalContext:
    """Calls Color B. Raises RetrievalError with a clear message if B is not merged yet."""
    try:
        from src.retrieval import retrieve            # Color B module (contract §5.2)
    except ImportError as exc:
        raise RetrievalError("src/retrieval.py (Color B) is not available yet — "
                             "run with --fixture tests/fixtures/sample_retrieved_context.json") from exc
    cfg = load_config()
    return retrieve(build_query(request), request.output_visibility, cfg.top_k_primary, cfg.top_k_secondary)


def sufficient(context: RetrievalContext) -> bool:
    try:
        from src.retrieval import has_sufficient_source  # Color B
        return has_sufficient_source(context)
    except ImportError:
        return context.retrieval_status == "success" and bool(context.primary_results or context.secondary_results)


def enforce_visibility(context: RetrievalContext) -> RetrievalContext:
    """Defence in depth: B filters already; C drops anything not public for a public output."""
    if context.output_visibility == "public":
        context.primary_results = [r for r in context.primary_results if r.chunk.visibility == "public"]
        context.secondary_results = [r for r in context.secondary_results if r.chunk.visibility == "public"]
    return context


def save_markdown(draft: GeneratedDraft, decision: str = "draft", reviewer: str = "", comment: str = "") -> Path:
    folder = OUTPUT_DIR / OUTPUT_FOLDERS.get(draft.request_type, "other")
    folder.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M")
    path = folder / f"{draft.request_type}_{stamp}.md"
    n = 2
    while path.exists():                              # two drafts in the same minute
        path = folder / f"{draft.request_type}_{stamp}_{n}.md"
        n += 1
    approval = (f"\n## Approval\nReviewer: {reviewer}\nDecision: {decision}\n"
                f"Date: {dt.date.today().isoformat() if decision != 'draft' else ''}\n"
                + (f"Comment: {comment}\n" if comment else ""))
    path.write_text(draft.content_markdown + approval, encoding="utf-8")
    draft.output_path = str(path.relative_to(ROOT))
    return path


def insufficient_draft(request: GenerationRequest, message: str) -> GeneratedDraft:
    return GeneratedDraft(title="insufficient source", request_type=request.request_type,
                          status="insufficient_source",
                          content_markdown=f"**insufficient source** — {message}",
                          citations=[], evidence_status="evidence_not_found", open_questions=[], output_path=None)


# ---------- contract entry point ----------

def run_pipeline(request: GenerationRequest, context: RetrievalContext | None = None,
                 save: bool = True) -> GeneratedDraft:
    """Contract §5.4. Pass `context` to skip retrieval (fixtures / tests)."""
    if not request.primary_context and not request.secondary_context:
        context = context or retrieve_context(request)
        context.output_visibility = request.output_visibility
        if not sufficient(context):
            return insufficient_draft(request, context.message or "no supporting source retrieved")
        context = enforce_visibility(context)
        request.primary_context, request.secondary_context = context.primary_results, context.secondary_results
    draft = generate_draft(request)
    if save and draft.status != "insufficient_source":
        save_markdown(draft)
    return draft


def approve(draft: GeneratedDraft, request: GenerationRequest, reviewer: str, comment: str = "",
            decision: str = "approved") -> tuple[Path, list[str]]:
    """Human decision → saved file with approval block; approved internal_update updates the gap register."""
    path = save_markdown(draft, decision, reviewer, comment)
    changes = []
    if decision == "approved" and request.request_type == "internal_update":
        changes = gap_register.record_approved(request.ai_system or DEFAULT_SYSTEM,
                                               parse_findings(draft.content_markdown), reviewer)
    return path, changes


# ---------- CLI ----------

def main():
    p = argparse.ArgumentParser(description="AI Governance Copilot — generate a draft for human review.")
    p.add_argument("--type", required=True, choices=list(OUTPUT_FOLDERS), dest="request_type")
    p.add_argument("--document", default="AI System Monitoring Plan", dest="document_type")
    p.add_argument("--system", default=DEFAULT_SYSTEM, dest="ai_system")
    p.add_argument("--topic", default="monitoring and human oversight")
    p.add_argument("--visibility", choices=["internal", "public"], default="internal")
    p.add_argument("--fixture", help="use a saved RetrievalContext JSON instead of Color B")
    p.add_argument("--no-review", action="store_true", help="save as draft without asking")
    a = p.parse_args()

    feedback = []
    for _ in range(3):
        request = GenerationRequest(request_type=a.request_type, document_type=a.document_type,
                                    ai_system=a.ai_system, topic=a.topic, output_visibility=a.visibility,
                                    selected_findings=[f"Reviewer feedback to apply: {f}" for f in feedback])
        context = None
        if a.fixture:
            context = retrieval_context_from_dict(json.loads(Path(a.fixture).read_text(encoding="utf-8")))
        try:
            draft = run_pipeline(request, context, save=False)
        except (ConfigurationError, RetrievalError, GenerationError) as exc:
            raise SystemExit(f"Error: {exc}")
        print("\n" + "=" * 80 + "\n" + draft.content_markdown + "\n" + "=" * 80)
        if draft.status == "insufficient_source":
            return
        if a.no_review:
            print(f"Saved: {save_markdown(draft)}")
            return
        choice = input("[a]pprove  [f]eedback + regenerate  [r]eject  [s]ave as draft: ").strip().lower()
        if choice == "f":
            feedback.append(input("Feedback: ").strip())
            continue
        if choice in ("a", "r"):
            reviewer = input("Reviewer name: ").strip()
            comment = input("Comment (optional): ").strip() if choice == "r" else ""
            path, changes = approve(draft, request, reviewer, comment, "approved" if choice == "a" else "rejected")
        else:
            path, changes = save_markdown(draft), []
        print(f"Saved: {path.relative_to(ROOT)}")
        for c in changes:
            print(f"Gap register: {c}")
        return


if __name__ == "__main__":
    main()
