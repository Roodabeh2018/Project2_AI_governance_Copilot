"""Color C — LLM calls and draft assembly (contract §5.3).

generate_text(prompt) -> str          the only function that talks to the API
generate_draft(request) -> GeneratedDraft
LLM_PROVIDER=mock in .env gives a free canned answer for offline tests.
"""
from __future__ import annotations

import json
import re

from src.config import get_api_key, llm_provider, load_config
from src.contracts import (DRAFT_STATUS, ConfigurationError, GeneratedDraft, GenerationError,
                           GenerationRequest)
from src.prompts import REQUIRED_HEADINGS, build_prompt, label_context

LABEL = re.compile(r"\b([PS]\d+)\b")


def generate_text(prompt: str) -> str:
    """Send one prompt to the LLM and return its text. Raises clear errors (contract §9)."""
    if llm_provider() == "mock":
        return _mock_answer(prompt)
    key = get_api_key()                                   # ConfigurationError if missing
    import openai
    client = openai.OpenAI(api_key=key)
    model = load_config().model_name
    try:
        response = client.chat.completions.create(
            model=model, temperature=0.2,
            messages=[{"role": "user", "content": prompt}])
    except openai.AuthenticationError as exc:
        raise ConfigurationError("The API key was rejected — check OPENAI_API_KEY in .env.") from exc
    except openai.NotFoundError as exc:
        raise ConfigurationError(f"Model '{model}' not found — check MODEL_NAME in .env.") from exc
    except openai.RateLimitError as exc:
        raise GenerationError("Rate limit or quota reached — wait a minute or check billing.") from exc
    except openai.APIConnectionError as exc:
        raise GenerationError("Could not reach the OpenAI API — check the internet connection.") from exc
    except openai.OpenAIError as exc:
        raise GenerationError(f"LLM call failed: {exc}") from exc
    text = (response.choices[0].message.content or "").strip()
    if not text:
        raise GenerationError("The LLM returned an empty answer.")
    return text


def validate_output(text: str, request: GenerationRequest, labels: dict) -> list[str]:
    """Warnings for the human reviewer. Empty list = all checks passed."""
    warnings = []
    if DRAFT_STATUS not in text:
        warnings.append(f"Missing status line '{DRAFT_STATUS}'.")
    for heading in REQUIRED_HEADINGS[request.request_type]:
        if heading not in text:
            warnings.append(f"Missing section: {heading}")
    cited = set(LABEL.findall(text))
    if not cited:
        warnings.append("No source citations found.")
    unknown = sorted(c for c in cited if c not in labels)
    if unknown:
        warnings.append(f"Cites sources that were not supplied: {', '.join(unknown)}")
    gap_bullets = _section_bullets(text, "## Evidence Incomplete or Not Found")
    uncited = [b for b in gap_bullets if not LABEL.search(b)]
    if uncited:
        warnings.append(f"{len(uncited)} gap bullet(s) without a source label, e.g. '{uncited[0][:60]}'")
    expected = [(r"schedule|frequen|how often|cycle", "[MONITORING FREQUENCY TO CONFIRM]"),
                (r"criteri|threshold|time|target|sla", "[THRESHOLD TO CONFIRM]")]
    wrong = [b for b in gap_bullets for pattern, ph in expected
             if re.search(pattern, b.split(":")[0], re.I) and "[OWNER TO CONFIRM]" in b and ph not in b]
    if wrong:
        warnings.append(f"{len(wrong)} gap bullet(s) use [OWNER TO CONFIRM] for a schedule/criterion, "
                        f"e.g. '{wrong[0][:60]}'")
    if request.request_type == "governance_document":
        proposed = re.search(r"^## Proposed Content(.*?)(?=^## |\Z)", text, re.S | re.M)
        if proposed and not re.search(r"\bS\d+\b", proposed.group(1)):
            warnings.append("Proposed Content does not name any requirement [S#] it implements.")
    if re.search(r"\{[a-z_]+\}", text):
        warnings.append("Unfilled template placeholder found.")
    if re.search(r"\b(fully compliant|is compliant|non-compliant)\b", text, re.I):
        warnings.append("Contains a compliance verdict — rephrase as a potential gap.")
    if request.output_visibility == "public":
        internal = [lab for lab in cited if lab in labels and labels[lab].chunk.visibility != "public"]
        if internal:
            warnings.append(f"PUBLIC OUTPUT CITES INTERNAL SOURCES: {', '.join(internal)} — do not publish.")
    return warnings


def _section_bullets(text: str, heading: str) -> list[str]:
    match = re.search(rf"^{re.escape(heading)}.*?\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    if not match:
        return []
    return [line.strip("-* ").strip() for line in match.group(1).splitlines() if line.strip().startswith(("-", "*"))]


def _overall_evidence_status(text: str) -> str:
    m = re.search(r"Overall evidence status:\s*\**\s*(evidence_found|evidence_incomplete|evidence_not_found)", text)
    if m:
        return m.group(1)
    for status in ("evidence_not_found", "evidence_incomplete", "evidence_found"):
        if status in text:
            return status
    return "evidence_incomplete"


def parse_findings(text: str) -> list[dict]:
    """Findings JSON block (internal_update) → list of {requirement_id, status, sources, note}."""
    match = re.search(r"```json\s*(.*?)```", text, re.S)
    if not match:
        return []
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return []
    return [f for f in data if isinstance(f, dict) and f.get("requirement_id")]


def source_register(labels: dict, cited: list[str]) -> str:
    rows = ["| Label | Source | Section | KB | Visibility | Cited |", "|---|---|---|---|---|---|"]
    for lab, r in labels.items():
        rows.append(f"| {lab} | {r.chunk.source_file} | {r.chunk.section} | {r.chunk.kb} | "
                    f"{r.chunk.visibility} | {'yes' if lab in cited else 'no'} |")
    return "\n".join(rows)


def generate_draft(request: GenerationRequest) -> GeneratedDraft:
    """Contract §5.3: prompt → LLM → checks → GeneratedDraft (not saved yet: pipeline saves it)."""
    if not request.primary_context and not request.secondary_context:
        raise GenerationError("No context supplied — the pipeline must stop with insufficient_source first.")
    labels = label_context(request)
    text = generate_text(build_prompt(request))

    if text.strip().lower().startswith("insufficient source"):
        return GeneratedDraft(title="insufficient source", request_type=request.request_type,
                              status="insufficient_source", content_markdown="**insufficient source**",
                              citations=[], evidence_status="evidence_not_found", open_questions=[],
                              output_path=None)

    warnings = validate_output(text, request, labels)
    cited = sorted(set(LABEL.findall(text)) & set(labels), key=lambda x: (x[0], int(x[1:])))
    title_match = re.search(r"^# (.+)$", text, re.M)
    content = (
        text
        + "\n\n## Source Register\n" + source_register(labels, cited)
        + "\n\n## Human-Review Checklist\n- [ ] Verify citations\n- [ ] Confirm placeholders\n- [ ] Review and approve\n"
        + ("\n## Automatic checks\n" + "\n".join(f"- ⚠️ {w}" for w in warnings) + "\n" if warnings
           else "\n## Automatic checks\n- ✅ All checks passed\n")
    )
    return GeneratedDraft(
        title=title_match.group(1).strip() if title_match else request.topic,
        request_type=request.request_type,
        status=DRAFT_STATUS,
        content_markdown=content,
        citations=[f"{lab}: {labels[lab].citation}" for lab in cited],
        evidence_status=_overall_evidence_status(text),
        open_questions=_section_bullets(text, "## Open Questions"),
        output_path=None,
    )


def _mock_answer(prompt: str) -> str:
    """Free, deterministic answer that follows the template (LLM_PROVIDER=mock)."""
    title = re.search(r"^# (.+)$", prompt, re.M)
    lines = [f"# {title.group(1) if title else 'Mock draft'}", f"Status: {DRAFT_STATUS}"]
    for heading in re.findall(r"^(## [A-Za-z ]+?)\s{2,}|^(## [A-Za-z ]+)$", prompt, re.M):
        h = (heading[0] or heading[1]).strip()
        lines += ["", h, "- Mock content from the supplied context [P1] [S1]. Owner: [OWNER TO CONFIRM]"]
    lines += ["", "Overall evidence status: evidence_incomplete"]
    ids = re.findall(r"^- ([A-Z]+-\d{2}):", prompt, re.M)
    if "```json" in prompt and ids:
        findings = [{"requirement_id": i, "status": "evidence_incomplete", "sources": ["P1", "S1"],
                     "note": "Mock finding."} for i in ids]
        lines += ["", "```json", json.dumps(findings, indent=1), "```"]
    return "\n".join(lines)
