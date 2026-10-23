"""Run the live, embedding-backed retrieval evaluation.

This makes embedding API calls and may incur usage charges. Run from the
repository root after building the current local index:
    python tests/evaluate_retrieval.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import CACHE_DIR  # noqa: E402
from src.contracts import GenerationRequest  # noqa: E402
from src.indexing import load_index  # noqa: E402
from src.prompts import build_prompt  # noqa: E402
from src.retrieval import retrieve  # noqa: E402

ANSWER_KEY = (
    ("AK01", "AI system inventory business owner technical owner", {"ai_system_inventory.md"}),
    ("AK02", "inventory model version identifier", {"ai_system_inventory.md"}),
    ("AK03", "AI risk classification status classification rationale credit decision support",
     {"ai_system_inventory.md"}),
    ("AK04", "monitoring owner monitoring schedule last review incident contact",
     {"ai_system_inventory.md"}),
    ("AK05", "risk assessment approval record assessment date next review date",
     {"ai_risk_assessment_credit_support.md"}),
    ("AK06", "residual risk rationale controls evidence supporting reduction",
     {"ai_risk_assessment_credit_support.md"}),
    ("AK07", "data quality provenance evidence incomplete",
     {"ai_risk_assessment_credit_support.md", "technical_documentation_credit_support.md"}),
    ("AK08", "fairness subgroup evaluation evidence",
     {"ai_risk_assessment_credit_support.md"}),
    ("AK09", "validation dataset acceptance criteria",
     {"ai_risk_assessment_credit_support.md"}),
    ("AK10", "reassessment triggers material change criteria",
     {"ai_risk_assessment_credit_support.md"}),
    ("AK11", "technical documentation data flow diagram referenced not attached",
     {"technical_documentation_credit_support.md"}),
    ("AK12", "model version data provenance data lineage",
     {"technical_documentation_credit_support.md"}),
    ("AK13", "test evidence independent sign-off test results",
     {"testing_validation_report.md"}),
    ("AK14", "change management deployment rollback details incomplete",
     {"technical_documentation_credit_support.md"}),
)


def main() -> None:
    index = load_index(CACHE_DIR)
    print(f"Index loaded: {len(index.chunks)} chunks, vectors={index.vectors.shape}")

    positive = retrieve(
        "What does the EU AI Act say about human oversight of high-risk AI systems?"
    )
    positive_results = positive.primary_results + positive.secondary_results
    positive_citations_valid = all(
        result.citation == result.chunk.source_locator for result in positive_results
    )
    print(
        f"Positive query: {positive.retrieval_status}; "
        f"primary={len(positive.primary_results)}; secondary={len(positive.secondary_results)}; "
        f"citations_valid={positive_citations_valid}"
    )
    if positive.secondary_results:
        print(f"Top Secondary citation: {positive.secondary_results[0].citation}")

    negative = retrieve("What is the monitoring status of AI system AI-99?")
    print(
        f"AI-99 negative query: {negative.retrieval_status}; "
        f"primary={len(negative.primary_results)}; secondary={len(negative.secondary_results)}"
    )

    hits = 0
    for case_id, topic, expected_sources in ANSWER_KEY:
        query = f"AI system: Credit Decision Support AI; Topic: {topic}"
        context = retrieve(query, top_k_primary=3, top_k_secondary=3)
        primary_files = {result.chunk.source_file for result in context.primary_results}
        results = context.primary_results + context.secondary_results
        citations_valid = all(
            result.citation == result.chunk.source_locator for result in results
        )
        matching_sources = primary_files & expected_sources
        passed = bool(matching_sources) and citations_valid
        hits += passed
        print(f"{case_id}: {'PASS' if passed else 'FAIL'}")

    public = retrieve(
        "General public information about human oversight and high-risk AI systems",
        output_visibility="public",
    )
    public_results = public.primary_results + public.secondary_results
    request = GenerationRequest(
        request_type="governance_document",
        document_type="General public information",
        ai_system=None,
        topic="General lessons about human oversight",
        output_visibility="public",
        primary_context=public.primary_results,
        secondary_context=public.secondary_results,
    )
    prompt = build_prompt(request)
    nonpublic_chunks = [
        chunk for chunk in index.chunks if chunk.visibility != "public"
    ]
    leakage = [
        chunk for chunk in nonpublic_chunks if chunk.text and chunk.text in prompt
    ]
    public_checks_pass = (
        all(result.chunk.visibility == "public" for result in public_results)
        and not leakage
        and all(result.citation == result.chunk.source_locator for result in public_results)
    )
    print(
        f"Public leakage: {public.retrieval_status}; results={len(public_results)}; "
        f"nonpublic_prompt_chunks={len(leakage)}; citations_valid="
        f"{all(result.citation == result.chunk.source_locator for result in public_results)}"
    )
    print(f"Answer-key expected-source hits: {hits}/{len(ANSWER_KEY)}")

    if (
        positive.retrieval_status != "success"
        or len(positive.primary_results) == 0
        or len(positive.secondary_results) == 0
        or not positive_citations_valid
        or negative.retrieval_status != "insufficient_source"
        or negative.primary_results
        or negative.secondary_results
        or hits != len(ANSWER_KEY)
        or not public_checks_pass
    ):
        raise SystemExit("Retrieval evaluation failed.")


if __name__ == "__main__":
    main()
