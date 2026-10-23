"""Validate the integrated Primary/Secondary KB before retrieval.

This module is intentionally read-only with respect to the knowledge base. It
loads the sources, validates the shared chunk contract and returns a compact
report that Color B can run before building or querying an index.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from src.chunking import chunk_documents
from src.contracts import (
    IngestionError,
    SchemaValidationError,
    SourceChunk,
    chunk_from_dict,
    to_dict,
    validate_source_chunk,
)
from src.ingestion import load_documents


class KnowledgeBaseValidationError(IngestionError):
    """Raised when the integrated KB cannot safely be passed to retrieval."""


@dataclass(frozen=True)
class KnowledgeBaseValidationReport:
    primary_document_count: int
    secondary_document_count: int
    primary_chunk_count: int
    secondary_chunk_count: int
    primary_files: tuple[str, ...]
    secondary_files: tuple[str, ...]
    errors: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return not self.errors

    @property
    def total_chunk_count(self) -> int:
        return self.primary_chunk_count + self.secondary_chunk_count


def validate_knowledge_base(
    primary_path: Path,
    secondary_path: Path,
    chunks: list[SourceChunk] | None = None,
    *,
    expected_primary_count: int | None = None,
    expected_secondary_count: int | None = None,
) -> KnowledgeBaseValidationReport:
    """Validate both KB roots and their chunks without changing source files.

    Expected counts are optional baseline checks. They should only be supplied
    when a caller intentionally wants to detect drift from a known snapshot;
    normal operation must allow future user uploads.
    """
    errors: list[str] = []
    try:
        documents = load_documents(primary_path, secondary_path)
    except IngestionError as exc:
        return KnowledgeBaseValidationReport(0, 0, 0, 0, (), (), (str(exc),))

    primary_documents = [document for document in documents if document.kb == "primary"]
    secondary_documents = [document for document in documents if document.kb == "secondary"]
    primary_files = tuple(document.source_file for document in primary_documents)
    secondary_files = tuple(document.source_file for document in secondary_documents)

    if expected_primary_count is not None and len(primary_documents) != expected_primary_count:
        errors.append(
            f"Expected {expected_primary_count} primary documents, found {len(primary_documents)}"
        )
    if expected_secondary_count is not None and len(secondary_documents) != expected_secondary_count:
        errors.append(
            f"Expected {expected_secondary_count} secondary documents, found {len(secondary_documents)}"
        )

    if chunks is None:
        try:
            chunks = chunk_documents(documents)
        except (SchemaValidationError, ValueError) as exc:
            errors.append(str(exc))
            chunks = []

    source_by_key = {(document.kb, document.source_file): document for document in documents}
    valid_chunks: list[SourceChunk] = []
    seen_chunk_ids: set[str] = set()
    for index, chunk in enumerate(chunks, start=1):
        try:
            validate_source_chunk(chunk)
        except (SchemaValidationError, AttributeError) as exc:
            errors.append(f"Chunk {index} is invalid: {exc}")
            continue
        source = source_by_key.get((chunk.kb, chunk.source_file))
        if source is None:
            errors.append(
                f"Chunk {chunk.chunk_id} references unknown source "
                f"{chunk.kb}:{chunk.source_file}"
            )
            continue
        if chunk.chunk_id in seen_chunk_ids:
            errors.append(f"Duplicate chunk_id: {chunk.chunk_id}")
            continue
        seen_chunk_ids.add(chunk.chunk_id)
        metadata_mismatch = False
        for field_name in ("source_type", "document_type", "visibility"):
            if getattr(chunk, field_name) != getattr(source, field_name):
                errors.append(
                    f"Chunk {chunk.chunk_id} metadata mismatch for {field_name}: "
                    f"source={getattr(source, field_name)!r}, "
                    f"chunk={getattr(chunk, field_name)!r}"
                )
                metadata_mismatch = True
                break
        if metadata_mismatch:
            continue
        valid_chunks.append(chunk)

    primary_chunk_count = sum(chunk.kb == "primary" for chunk in valid_chunks)
    secondary_chunk_count = sum(chunk.kb == "secondary" for chunk in valid_chunks)
    if not valid_chunks:
        errors.append("No valid chunks are available for retrieval")
    if not any(chunk.kb == "primary" for chunk in valid_chunks):
        errors.append("No valid primary chunks are available for retrieval")
    if not any(chunk.kb == "secondary" for chunk in valid_chunks):
        errors.append("No valid secondary chunks are available for retrieval")

    return KnowledgeBaseValidationReport(
        primary_document_count=len(primary_documents),
        secondary_document_count=len(secondary_documents),
        primary_chunk_count=primary_chunk_count,
        secondary_chunk_count=secondary_chunk_count,
        primary_files=primary_files,
        secondary_files=secondary_files,
        errors=tuple(errors),
    )


def require_valid_knowledge_base(
    primary_path: Path,
    secondary_path: Path,
    chunks: list[SourceChunk] | None = None,
    *,
    expected_primary_count: int | None = None,
    expected_secondary_count: int | None = None,
) -> KnowledgeBaseValidationReport:
    """Return a report or fail fast before index/retrieval work starts."""
    report = validate_knowledge_base(
        primary_path,
        secondary_path,
        chunks,
        expected_primary_count=expected_primary_count,
        expected_secondary_count=expected_secondary_count,
    )
    if not report.is_valid:
        raise KnowledgeBaseValidationError("; ".join(report.errors))
    return report


def load_cached_chunks(chunks_path: Path) -> list[SourceChunk]:
    """Load and validate a JSONL chunk cache for downstream retrieval."""
    chunks: list[SourceChunk] = []
    seen_chunk_ids: set[str] = set()
    path = Path(chunks_path)
    if not path.exists():
        raise KnowledgeBaseValidationError(f"Chunk cache does not exist: {path}")

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise KnowledgeBaseValidationError(f"Unable to read chunk cache {path}: {exc}") from exc

    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            raise KnowledgeBaseValidationError(
                f"Blank line in chunk cache {path} at line {line_number}"
            )
        try:
            payload = json.loads(line)
            chunk = chunk_from_dict(payload)
            if chunk.chunk_id in seen_chunk_ids:
                raise SchemaValidationError(f"Duplicate chunk_id: {chunk.chunk_id}")
            seen_chunk_ids.add(chunk.chunk_id)
            chunks.append(chunk)
        except (json.JSONDecodeError, SchemaValidationError, TypeError) as exc:
            raise KnowledgeBaseValidationError(
                f"Invalid chunk cache {path} at line {line_number}: {exc}"
            ) from exc
    if not chunks:
        raise KnowledgeBaseValidationError(f"Chunk cache is empty: {path}")
    return chunks


def write_sample_chunks(
    chunks: list[SourceChunk],
    output_path: Path,
    per_kb: int = 2,
) -> None:
    """Write a small deterministic sample for another track to consume."""
    if per_kb < 1:
        raise ValueError("per_kb must be positive")
    selected = [
        *[chunk for chunk in chunks if chunk.kb == "primary"][:per_kb],
        *[chunk for chunk in chunks if chunk.kb == "secondary"][:per_kb],
    ]
    if len(selected) < 2 * per_kb:
        raise KnowledgeBaseValidationError("Not enough chunks to create a two-KB sample")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "".join(json.dumps(to_dict(chunk), ensure_ascii=False, sort_keys=True) + "\n"
                for chunk in selected),
        encoding="utf-8",
    )


if __name__ == "__main__":  # pragma: no cover - convenience CLI
    from src.config import PRIMARY_DIR, SECONDARY_DIR

    report = require_valid_knowledge_base(PRIMARY_DIR, SECONDARY_DIR)
    print(
        f"Valid KB: {report.primary_document_count} primary documents, "
        f"{report.secondary_document_count} secondary documents, "
        f"{report.total_chunk_count} chunks"
    )
