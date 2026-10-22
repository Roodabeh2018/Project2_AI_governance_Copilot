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


class SchemaValidationError(ValueError):
    """Raised when a shared source or chunk violates the data contract."""


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

    def __post_init__(self) -> None:
        validate_source_document(self)


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

    def __post_init__(self) -> None:
        validate_source_chunk(self)


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

_REQUIRED_SOURCE_DOCUMENT_FIELDS = (
    "source_id", "source_file", "source_type", "document_type", "title", "text"
)
_REQUIRED_SOURCE_CHUNK_FIELDS = (
    "chunk_id", "source_file", "source_type", "document_type", "section",
    "title", "text", "source_locator"
)


def _require_non_empty_strings(obj, fields: tuple[str, ...], model_name: str) -> None:
    for field_name in fields:
        value = getattr(obj, field_name)
        if not isinstance(value, str) or not value.strip():
            raise SchemaValidationError(
                f"{model_name}.{field_name} must be a non-empty string"
            )


def _validate_common_metadata(obj, model_name: str) -> None:
    _require_non_empty_strings(obj, ("source_file", "source_type", "document_type"), model_name)
    if obj.kb not in ("primary", "secondary"):
        raise SchemaValidationError(f"{model_name}.kb must be 'primary' or 'secondary'")
    if obj.visibility not in ("internal", "public", "mixed"):
        raise SchemaValidationError(
            f"{model_name}.visibility must be 'internal', 'public' or 'mixed'"
        )


def validate_source_document(document: SourceDocument) -> SourceDocument:
    """Validate and return one canonical SourceDocument."""
    _require_non_empty_strings(document, _REQUIRED_SOURCE_DOCUMENT_FIELDS, "SourceDocument")
    _validate_common_metadata(document, "SourceDocument")
    return document


def validate_source_chunk(chunk: SourceChunk) -> SourceChunk:
    """Validate and return one canonical SourceChunk.

    This is deliberately kept beside the dataclass so every producer and
    consumer receives the same validation, including fixture deserialization.
    """
    _require_non_empty_strings(chunk, _REQUIRED_SOURCE_CHUNK_FIELDS, "SourceChunk")
    _validate_common_metadata(chunk, "SourceChunk")

    if chunk.page_start is not None and (
        not isinstance(chunk.page_start, int) or isinstance(chunk.page_start, bool)
        or chunk.page_start < 1
    ):
        raise SchemaValidationError("SourceChunk.page_start must be a positive integer or None")
    if chunk.page_end is not None and (
        not isinstance(chunk.page_end, int) or isinstance(chunk.page_end, bool)
        or chunk.page_end < 1
    ):
        raise SchemaValidationError("SourceChunk.page_end must be a positive integer or None")
    if (chunk.page_start is not None and chunk.page_end is not None
            and chunk.page_start > chunk.page_end):
        raise SchemaValidationError("SourceChunk.page_start cannot exceed page_end")
    if chunk.article_or_annex is not None and (
        not isinstance(chunk.article_or_annex, str) or not chunk.article_or_annex.strip()
    ):
        raise SchemaValidationError("SourceChunk.article_or_annex must be text or None")
    return chunk

def to_dict(obj) -> dict:
    return asdict(obj)


def chunk_from_dict(d: dict) -> SourceChunk:
    if not isinstance(d, dict):
        raise SchemaValidationError("SourceChunk JSON value must be an object")
    return SourceChunk(**d)


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
