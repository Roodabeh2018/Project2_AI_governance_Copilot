"""Shared data contracts for the three implementation tracks."""

from dataclasses import dataclass
from typing import Literal


KB = Literal["primary", "secondary"]
Visibility = Literal["internal", "public", "mixed"]
OutputVisibility = Literal["internal", "public"]
RetrievalStatus = Literal["success", "insufficient_source", "error"]
RequestType = Literal["governance_document", "internal_update"]


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
    primary_context: list[RetrievalResult]
    secondary_context: list[RetrievalResult]
    selected_findings: list[str]


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
