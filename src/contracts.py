"""Shared data models, enums and errors (Shared Engineering Contract §4, §9).

ONE source of truth: every color imports from here. Do not redefine these models elsewhere.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

KB = Literal["primary", "secondary"]
Visibility = Literal["internal", "public", "mixed"]
OutputVisibility = Literal["internal", "public"]
RequestType = Literal["governance_document", "internal_update"]
RetrievalStatus = Literal["success", "insufficient_source", "error"]

EVIDENCE_STATUSES = ("evidence_found", "evidence_incomplete", "evidence_not_found")
DRAFT_STATUS = "Draft — human review required"


# ---------- errors (§9) ----------

class ConfigurationError(Exception):
    pass


class IngestionError(Exception):
    pass


class RetrievalError(Exception):
    pass


class GenerationError(Exception):
    pass


# ---------- models (§4) ----------

@dataclass
class SourceDocument:
    source_id: str
    kb: KB
    source_file: str
    source_type: str
    document_type: str
    visibility: Visibility
    title: str
    text: str


@dataclass
class SourceChunk:
    chunk_id: str
    kb: KB
    source_file: str
    source_type: str
    document_type: str
    visibility: Visibility
    page_start: int | None
    page_end: int | None
    section: str
    article_or_annex: str | None
    title: str
    text: str
    source_locator: str


@dataclass
class RetrievalResult:
    rank: int
    score: float
    chunk: SourceChunk
    citation: str


@dataclass
class RetrievalContext:
    query: str
    output_visibility: OutputVisibility
    retrieval_status: RetrievalStatus
    primary_results: list[RetrievalResult]
    secondary_results: list[RetrievalResult]
    message: str | None = None


@dataclass
class GenerationRequest:
    request_type: RequestType
    document_type: str | None
    ai_system: str | None
    topic: str
    output_visibility: OutputVisibility
    primary_context: list[RetrievalResult] = field(default_factory=list)
    secondary_context: list[RetrievalResult] = field(default_factory=list)
    selected_findings: list[str] = field(default_factory=list)


@dataclass
class GeneratedDraft:
    title: str
    request_type: str
    status: str
    content_markdown: str
    citations: list[str]
    evidence_status: str
    open_questions: list[str]
    output_path: str | None


# ---------- JSON helpers (so fixtures and retrieved_context.json load into the same models) ----------

def to_dict(obj) -> dict:
    return asdict(obj)


def chunk_from_dict(d: dict) -> SourceChunk:
    return SourceChunk(**{k: d.get(k) for k in SourceChunk.__dataclass_fields__})


def result_from_dict(d: dict) -> RetrievalResult:
    return RetrievalResult(rank=d["rank"], score=d["score"], chunk=chunk_from_dict(d["chunk"]),
                           citation=d["citation"])


def retrieval_context_from_dict(d: dict) -> RetrievalContext:
    return RetrievalContext(
        query=d["query"], output_visibility=d["output_visibility"], retrieval_status=d["retrieval_status"],
        primary_results=[result_from_dict(r) for r in d.get("primary_results", [])],
        secondary_results=[result_from_dict(r) for r in d.get("secondary_results", [])],
        message=d.get("message"),
    )


def generation_request_from_dict(d: dict) -> GenerationRequest:
    return GenerationRequest(
        request_type=d["request_type"], document_type=d.get("document_type"), ai_system=d.get("ai_system"),
        topic=d.get("topic", ""), output_visibility=d.get("output_visibility", "internal"),
        primary_context=[result_from_dict(r) for r in d.get("primary_context", [])],
        secondary_context=[result_from_dict(r) for r in d.get("secondary_context", [])],
        selected_findings=d.get("selected_findings", []),
    )
