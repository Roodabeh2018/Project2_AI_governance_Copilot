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
import hashlib
import inspect
import json
import re
from pathlib import Path

from src import gap_register
from src.config import DATA_DIR, OUTPUT_DIR, PRIMARY_DIR, ROOT, SECONDARY_DIR, load_config
from src.contracts import (ConfigurationError, GeneratedDraft, GenerationError, GenerationRequest,
                           RetrievalContext, RetrievalError, RetrievalResult, SourceChunk,
                           retrieval_context_from_dict)
from src.llm_generator import ensure_saveable, generate_draft, parse_findings
from src.prompts import label_context

DEFAULT_SYSTEM = "Credit Decision Support AI"
OUTPUT_FOLDERS = {"governance_document": "governance_documents", "internal_update": "internal_updates"}
SYSTEM_ID = re.compile(r"\b[A-Z]{1,6}-\d{1,4}\b")          # e.g. AI-99
FRONT_MATTER = re.compile(r"^---\s*\n.*?\n---\s*\n", re.S)


# ---------- steps ----------

def build_query(request: GenerationRequest) -> str:
    parts = [request.ai_system if request.output_visibility == "internal" else None,
             request.document_type if request.request_type == "governance_document" else None,
             request.topic]
    return " ".join(p for p in parts if p)


_DOC_CACHE: dict = {"key": None, "docs": []}


def company_documents():
    """Color A canonical SourceDocuments (Primary + Secondary), reloaded only when a KB file changes."""
    from src.ingestion import load_documents          # Color A module (contract §5.1)
    key = tuple(sorted((str(f), f.stat().st_mtime_ns, f.stat().st_size)
                       for d in (PRIMARY_DIR, SECONDARY_DIR) for f in d.rglob("*") if f.is_file()))
    if _DOC_CACHE["key"] != key:
        _DOC_CACHE.update(key=key, docs=load_documents(PRIMARY_DIR, SECONDARY_DIR))
    return _DOC_CACHE["docs"]


def _canonical_index() -> tuple[dict, dict]:
    """Exact (kb, relative path) index, and a separate basename index used only when unambiguous."""
    exact, by_name = {}, {}
    for doc in company_documents():
        exact[(doc.kb, doc.source_file)] = doc
        by_name.setdefault((doc.kb, Path(doc.source_file).name), []).append(doc)
    return exact, by_name


def _resolve_document(kb, source_file, canonical: tuple[dict, dict]):
    """Exact path first; basename fallback only when exactly one source matches. Ambiguous → None."""
    exact, by_name = canonical
    if (kb, source_file) in exact:
        return exact[(kb, source_file)]
    matches = by_name.get((kb, Path(str(source_file or "")).name), [])
    return matches[0] if len(matches) == 1 else None


def _as_result(rank: int, item, canonical: tuple[dict, dict]) -> RetrievalResult | None:
    """Contract RetrievalResult, or a legacy Color B dict resolved against Color A metadata.

    Visibility, source type and document type always come from Color A's canonical document,
    never from the legacy label. A legacy result that Color A does not know, or that matches more
    than one canonical source, is dropped (fail closed).
    """
    if isinstance(item, RetrievalResult):
        return item
    doc = _resolve_document(item.get("kb"), item.get("source_file"), canonical)
    if doc is None:
        return None
    section = item.get("section") or doc.title
    text = FRONT_MATTER.sub("", item.get("text", ""))
    # Keep a canonical chunk ID when Color B supplies one; otherwise derive a stable ID that also
    # depends on the excerpt text, so repeated section titles never share an ID.
    fallback_id = f"{doc.source_id}#{section}#{hashlib.sha256(text.encode('utf-8')).hexdigest()[:10]}"
    chunk = SourceChunk(
        chunk_id=item.get("chunk_id") or fallback_id,
        kb=doc.kb, source_file=doc.source_file, source_type=doc.source_type,
        document_type=doc.document_type, visibility=doc.visibility,
        page_start=item.get("page_start"), page_end=item.get("page_end"),
        section=section, article_or_annex=item.get("article_or_annex"), title=doc.title,
        text=text,
        source_locator=item.get("source_locator") or f"{doc.source_file}, {section}")
    return RetrievalResult(rank=rank, score=float(item.get("score", 0)), chunk=chunk,
                           citation=item.get("citation") or chunk.source_locator)


def _as_context(raw, request: GenerationRequest, top_k_primary: int, top_k_secondary: int) -> RetrievalContext:
    """Normalise Color B output to the contract RetrievalContext with independent top-k per KB."""
    if isinstance(raw, RetrievalContext):
        raw.primary_results = raw.primary_results[:top_k_primary]
        raw.secondary_results = raw.secondary_results[:top_k_secondary]
        return raw
    if not isinstance(raw, dict):
        raise RetrievalError(f"Unexpected retrieval output type: {type(raw).__name__}")
    canonical = _canonical_index()

    def resolve(items, k):
        results = [r for r in (_as_result(i + 1, it, canonical) for i, it in enumerate(items or [])) if r]
        return [RetrievalResult(rank=i + 1, score=r.score, chunk=r.chunk, citation=r.citation)
                for i, r in enumerate(results[:k])]

    return RetrievalContext(
        query=raw.get("query", build_query(request)),
        output_visibility=request.output_visibility,
        retrieval_status=raw.get("retrieval_status", "success"),
        primary_results=resolve(raw.get("primary_results"), top_k_primary),
        secondary_results=resolve(raw.get("secondary_results"), top_k_secondary),
        message=raw.get("message"))


def _requirement_ids() -> set[str]:
    path = DATA_DIR / "requirements_checklist.json"
    return {r["requirement_id"] for r in json.loads(path.read_text(encoding="utf-8"))} if path.exists() else set()


def unknown_systems(request: GenerationRequest) -> list[str]:
    """Named AI systems (e.g. AI-99) that appear in no Primary document (md, txt or pdf, via Color A).

    Requirement IDs from the checklist (e.g. MON-02) are not AI systems and are ignored.
    """
    names = [n for n in SYSTEM_ID.findall(f"{request.topic} {request.ai_system or ''}")
             if n not in _requirement_ids()]
    if request.ai_system and not SYSTEM_ID.fullmatch(request.ai_system):
        names.append(request.ai_system)
    company_text = " ".join(d.text for d in company_documents() if d.kb == "primary").lower()
    return [n for n in dict.fromkeys(names) if n.lower() not in company_text]


def _accepts_separate_top_k(fn) -> bool:
    try:
        params = inspect.signature(fn).parameters
    except (TypeError, ValueError):
        return True
    return "top_k_primary" in params or len(params) >= 4 or any(
        p.kind == p.VAR_POSITIONAL for p in params.values())


def retrieve_context(request: GenerationRequest) -> RetrievalContext:
    """Calls Color B (contract §5.2) and normalises the result."""
    try:
        from src.retrieval import retrieve            # Color B module
    except ImportError as exc:
        raise RetrievalError("src/retrieval.py (Color B) is not available yet — "
                             "run with --fixture tests/fixtures/sample_retrieved_context.json") from exc
    cfg = load_config()
    query = build_query(request)
    if _accepts_separate_top_k(retrieve):             # contract signature
        raw = retrieve(query, request.output_visibility, cfg.top_k_primary, cfg.top_k_secondary)
    else:                                             # legacy: retrieve(query, visibility, top_k) → sliced per KB
        raw = retrieve(query, request.output_visibility, max(cfg.top_k_primary, cfg.top_k_secondary))
    return _as_context(raw, request, cfg.top_k_primary, cfg.top_k_secondary)


def sufficient(context: RetrievalContext) -> bool:
    try:
        from src.retrieval import has_sufficient_source  # Color B
        return has_sufficient_source(context)
    except ImportError:
        return context.retrieval_status == "success" and bool(context.primary_results or context.secondary_results)


def visible(results: list[RetrievalResult], output_visibility: str) -> list[RetrievalResult]:
    """A public output may only use public chunks; an internal output may use everything."""
    return [r for r in results if output_visibility != "public" or r.chunk.visibility == "public"]


def enforce_visibility(context: RetrievalContext) -> RetrievalContext:
    """Defence in depth: B filters already; C drops anything not public for a public output."""
    context.primary_results = visible(context.primary_results, context.output_visibility)
    context.secondary_results = visible(context.secondary_results, context.output_visibility)
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
    ensure_saveable(draft.content_markdown)
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
    """Contract §5.4. Pass `context` to skip retrieval (fixtures / tests).

    Visibility is enforced on EVERY path (retrieved, fixture or pre-populated request), and
    sufficiency is checked again after filtering.
    """
    if not request.primary_context and not request.secondary_context:
        missing = unknown_systems(request) if context is None else []
        if missing:
            return insufficient_draft(request, f"AI system not found in the company documents: {', '.join(missing)}")
        context = context or retrieve_context(request)
        context.output_visibility = request.output_visibility
        if not sufficient(context):
            return insufficient_draft(request, context.message or "no supporting source retrieved")
        request.primary_context, request.secondary_context = context.primary_results, context.secondary_results
    request.primary_context = visible(request.primary_context, request.output_visibility)
    request.secondary_context = visible(request.secondary_context, request.output_visibility)
    filtered = RetrievalContext(query=build_query(request), output_visibility=request.output_visibility,
                                retrieval_status="success", primary_results=request.primary_context,
                                secondary_results=request.secondary_context)
    if not sufficient(filtered):                      # judged on what the LLM would actually receive
        return insufficient_draft(request, f"no sufficient {request.output_visibility} source "
                                           "left after visibility filtering")
    draft = generate_draft(request)
    if save and draft.status != "insufficient_source":
        save_markdown(draft)
    return draft


def approve(draft: GeneratedDraft, request: GenerationRequest, reviewer: str, comment: str = "",
            decision: str = "approved") -> tuple[Path, list[str]]:
    """Human decision → saved file with approval block; approved internal_update updates the gap register.

    Findings are parsed and validated BEFORE anything is saved, so an invalid approval changes nothing.
    """
    findings, supplied = [], {}
    if decision == "approved" and request.request_type == "internal_update":
        findings = parse_findings(draft.content_markdown)              # GenerationError if malformed
        supplied = {lab: r.citation for lab, r in label_context(request).items()}
        problems = gap_register.validate_findings(findings, supplied)
        if problems:
            raise GenerationError("Approval blocked, gap register unchanged: " + "; ".join(problems))
    path = save_markdown(draft, decision, reviewer, comment)
    changes = gap_register.record_approved(request.ai_system or DEFAULT_SYSTEM, findings, reviewer,
                                           supplied) if findings else []
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
            try:
                path, changes = approve(draft, request, reviewer, comment,
                                        "approved" if choice == "a" else "rejected")
            except GenerationError as exc:
                raise SystemExit(f"Error: {exc}")
        else:
            path, changes = save_markdown(draft), []
        print(f"Saved: {path.relative_to(ROOT)}")
        for c in changes:
            print(f"Gap register: {c}")
        return


if __name__ == "__main__":
    main()
