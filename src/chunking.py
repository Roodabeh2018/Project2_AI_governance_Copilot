"""Create contract-compliant chunks and rebuild the local chunk cache.

Chunking is intentionally deterministic and dependency-free. Headings,
Article/Annex markers and PDF page markers establish semantic/source
boundaries; a character limit is only a fallback for unusually long sections.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from src.contracts import (
    SchemaValidationError,
    SourceChunk,
    SourceDocument,
    to_dict,
    validate_source_chunk,
)


DEFAULT_MAX_CHUNK_CHARACTERS = 1800
_PAGE_MARKER = re.compile(r"^\s*\[PAGE\s+(\d+)\]\s*$", flags=re.IGNORECASE)
_ARTICLE_MARKER = re.compile(
    r"^\s*\[(ARTICLE|ANNEX)\s+([0-9]+|[IVXLCDM]+)\]\s*$",
    flags=re.IGNORECASE,
)
_ARTICLE_HEADING = re.compile(
    r"^\s*(?:#{1,6}\s*)?(Article|Annex)\s+([0-9]+|[IVXLCDM]+)"
    r"(?:\s*[-—:.)]\s*(.*))?\s*$",
    flags=re.IGNORECASE,
)
_MARKDOWN_HEADING = re.compile(r"^\s*#{1,6}\s+(.+?)\s*$")


@dataclass
class _RawSegment:
    lines: list[str]
    section: str
    article_or_annex: str | None
    page_start: int | None
    page_end: int | None


def chunk_documents(
    documents: list[SourceDocument],
    max_chunk_characters: int = DEFAULT_MAX_CHUNK_CHARACTERS,
) -> list[SourceChunk]:
    """Chunk both KBs while retaining the shared source metadata.

    The default limit is a fallback only. Semantic boundaries are preferred,
    and the same input produces the same chunk IDs and ordering.
    """
    if max_chunk_characters < 1:
        raise ValueError("max_chunk_characters must be positive")

    chunks: list[SourceChunk] = []
    for document in documents:
        _validate_document(document)
        segments = _split_into_segments(document)
        source_index = 1
        for segment in segments:
            for text in _split_long_segment(segment, max_chunk_characters):
                if not text.strip():
                    continue
                chunk = SourceChunk(
                    chunk_id=f"{_slug(document.kb + '_' + document.source_file)}"
                    f"_{source_index:04d}",
                    kb=document.kb,
                    source_file=document.source_file,
                    source_type=document.source_type,
                    document_type=document.document_type,
                    visibility=document.visibility,
                    page_start=segment.page_start,
                    page_end=segment.page_end,
                    section=segment.section or document.title,
                    article_or_annex=segment.article_or_annex,
                    title=document.title,
                    text=text,
                    source_locator=_source_locator(
                        document.source_file,
                        segment.page_start,
                        segment.page_end,
                        segment.section or document.title,
                        segment.article_or_annex,
                    ),
                )
                validate_source_chunk(chunk)
                chunks.append(chunk)
                source_index += 1
    return chunks


def save_chunks(chunks: list[SourceChunk], output_path: Path) -> None:
    """Overwrite the local JSONL cache and its derived source manifest."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    validated_chunks = []
    for chunk in chunks:
        if not isinstance(chunk, SourceChunk):
            raise SchemaValidationError("save_chunks expects SourceChunk objects")
        validated_chunks.append(validate_source_chunk(chunk))

    jsonl = "".join(
        json.dumps(to_dict(chunk), ensure_ascii=False, sort_keys=True) + "\n"
        for chunk in validated_chunks
    )
    output_path.write_text(jsonl, encoding="utf-8")

    manifest_path = output_path.with_name("source_manifest.json")
    manifest = _build_source_manifest(validated_chunks)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def rebuild_cache(
    primary_path: Path,
    secondary_path: Path,
    cache_dir: Path,
    max_chunk_characters: int = DEFAULT_MAX_CHUNK_CHARACTERS,
) -> list[SourceChunk]:
    """Reload both KBs, recreate chunks and overwrite the local cache."""
    from src.ingestion import load_documents

    documents = load_documents(primary_path, secondary_path)
    chunks = chunk_documents(documents, max_chunk_characters=max_chunk_characters)
    save_chunks(chunks, Path(cache_dir) / "chunks.jsonl")
    return chunks


def _validate_document(document: SourceDocument) -> None:
    if not isinstance(document, SourceDocument):
        raise SchemaValidationError("chunk_documents expects SourceDocument objects")
    if not document.text.strip():
        raise SchemaValidationError(
            f"SourceDocument.text is empty: {document.source_file}"
        )


def _split_into_segments(document: SourceDocument) -> list[_RawSegment]:
    segments: list[_RawSegment] = []
    lines: list[str] = []
    section = document.title
    article_or_annex: str | None = None
    current_page: int | None = None
    page_start: int | None = None
    page_end: int | None = None

    def flush() -> None:
        nonlocal lines, page_start, page_end
        if lines:
            segments.append(_RawSegment(lines, section, article_or_annex, page_start, page_end))
            lines = []
            page_start = current_page
            page_end = current_page

    for line in document.text.splitlines():
        page_match = _PAGE_MARKER.match(line)
        if page_match:
            if _has_meaningful_lines(lines):
                flush()
            current_page = int(page_match.group(1))
            # The flush above belongs to the previous page; this marker starts
            # a new segment on the newly observed page.
            page_start = current_page
            page_end = current_page
            lines.append(line.strip())
            continue

        heading = _heading_metadata(line)
        if heading is not None:
            if _has_meaningful_lines(lines):
                flush()
            section, heading_article = heading
            if heading_article is not None:
                article_or_annex = heading_article
            lines.append(line.rstrip())
            if page_start is None:
                page_start = current_page
            page_end = current_page
            continue

        if not lines:
            page_start = current_page
            page_end = current_page
        lines.append(line.rstrip())

    if _has_meaningful_lines(lines):
        flush()
    return segments


def _heading_metadata(line: str) -> tuple[str, str | None] | None:
    marker = _ARTICLE_MARKER.match(line)
    if marker:
        kind, identifier = marker.groups()
        label = f"{kind.title()} {identifier.upper()}"
        return label, label

    article_heading = _ARTICLE_HEADING.match(line)
    if article_heading:
        kind, identifier, rest = article_heading.groups()
        label = f"{kind.title()} {identifier.upper()}"
        return (f"{label} — {rest.strip()}" if rest else label), label

    markdown_heading = _MARKDOWN_HEADING.match(line)
    if markdown_heading:
        return markdown_heading.group(1).strip(), None
    return None


def _has_meaningful_lines(lines: list[str]) -> bool:
    return any(
        line.strip()
        and not _PAGE_MARKER.match(line)
        and not _ARTICLE_MARKER.match(line)
        for line in lines
    )


def _split_long_segment(segment: _RawSegment, max_characters: int) -> list[str]:
    text = "\n".join(segment.lines).strip()
    if len(text) <= max_characters:
        return [text]

    paragraphs = re.split(r"\n\s*\n", text)
    pieces: list[str] = []
    current = ""
    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if len(paragraph) > max_characters:
            if current:
                pieces.append(current)
                current = ""
            pieces.extend(_split_long_line(paragraph, max_characters))
            continue
        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if current and len(candidate) > max_characters:
            pieces.append(current)
            current = paragraph
        else:
            current = candidate
    if current:
        pieces.append(current)
    return pieces


def _split_long_line(text: str, max_characters: int) -> list[str]:
    words = text.split()
    pieces: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}" if current else word
        if current and len(candidate) > max_characters:
            pieces.append(current)
            current = word
        else:
            current = candidate
    if current:
        pieces.append(current)
    return pieces


def _source_locator(
    source_file: str,
    page_start: int | None,
    page_end: int | None,
    section: str,
    article_or_annex: str | None,
) -> str:
    parts = [source_file]
    if page_start is not None and page_end is not None and page_start != page_end:
        parts.append(f"pages={page_start}-{page_end}")
    elif page_start is not None:
        parts.append(f"page={page_start}")
    if article_or_annex:
        parts.append(article_or_annex)
    elif section:
        parts.append(section)
    return ", ".join(parts)


def _build_source_manifest(chunks: list[SourceChunk]) -> dict:
    grouped: dict[tuple[str, str], dict] = {}
    for chunk in chunks:
        key = (chunk.kb, chunk.source_file)
        source = grouped.setdefault(
            key,
            {
                "source_id": f"{chunk.kb}:{chunk.source_file}",
                "kb": chunk.kb,
                "source_file": chunk.source_file,
                "source_type": chunk.source_type,
                "document_type": chunk.document_type,
                "visibility": chunk.visibility,
                "title": chunk.title,
                "chunk_count": 0,
            },
        )
        source["chunk_count"] += 1

    sources = sorted(grouped.values(), key=lambda item: (item["kb"], item["source_file"]))
    return {
        "schema_version": "1.0",
        "chunk_count": len(chunks),
        "source_count": len(sources),
        "sources": sources,
    }


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "source"

