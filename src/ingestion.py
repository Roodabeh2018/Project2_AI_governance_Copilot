"""Load Primary and Secondary knowledge-base documents.

This module owns document discovery and text extraction only. Chunking, indexing
and retrieval are deliberately kept in their separate Color A/B modules.
"""
from __future__ import annotations

import re
from pathlib import Path

from src.contracts import IngestionError, SourceDocument

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover - exercised only in incomplete installs
    PdfReader = None


SUPPORTED_SUFFIXES = {".md", ".txt", ".pdf"}
VALID_VISIBILITIES = {"internal", "public", "mixed"}

# These files are provenance notes/checklists, not part of the agreed baseline
# KB. They remain in the repository for human reference.
SECONDARY_REFERENCE_ONLY_FILES = {
    "eu_ai_act_reference_notes.md",
    "iso_42001_reference_notes.md",
    "nist_ai_rmf_reference_notes.md",
    "source_verification_checklist.md",
}

PRIMARY_DOCUMENT_TYPES = {
    "ai_governance_policy": "policy",
    "ai_risk_assessment_credit_support": "risk_assessment",
    "ai_system_inventory": "inventory",
    "comms_guidelines": "public_guidance",
    "company_profile": "company_profile",
    "human_oversight_procedure": "procedure",
    "monitoring_notes": "monitoring_notes",
    "technical_documentation_credit_support": "technical_documentation",
    "testing_validation_report": "validation_report",
}


def load_documents(primary_path: Path, secondary_path: Path) -> list[SourceDocument]:
    """Load supported documents from both KB roots in deterministic order.

    ``source_file`` is always a POSIX-style path relative to its KB root. The
    official EU AI Act PDF is included from Secondary, while the existing
    reference notes/checklist are excluded because they are supporting material
    rather than the agreed baseline source. Future public uploads are supported
    anywhere below ``secondary/uploads`` or directly in Secondary.
    """
    primary_path = Path(primary_path)
    secondary_path = Path(secondary_path)
    _validate_root(primary_path, "primary")
    _validate_root(secondary_path, "secondary")

    documents: list[SourceDocument] = []
    documents.extend(_load_root(primary_path, "primary"))
    documents.extend(_load_root(secondary_path, "secondary"))
    return documents


def _validate_root(path: Path, kb: str) -> None:
    if not path.exists():
        raise IngestionError(f"{kb} knowledge-base path does not exist: {path}")
    if not path.is_dir():
        raise IngestionError(f"{kb} knowledge-base path is not a directory: {path}")


def _load_root(root: Path, kb: str) -> list[SourceDocument]:
    documents: list[SourceDocument] = []
    for path in _iter_supported_files(root):
        if kb == "secondary" and not _include_secondary(path, root):
            continue
        documents.append(_load_document(path, root, kb))
    return documents


def _iter_supported_files(root: Path):
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix().lower()):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        if any(part.startswith(".") for part in path.relative_to(root).parts):
            continue
        yield path


def _include_secondary(path: Path, root: Path) -> bool:
    relative = path.relative_to(root)
    if path.name.lower() in SECONDARY_REFERENCE_ONLY_FILES:
        return False
    if path.suffix.lower() == ".pdf":
        return True
    # The Gradio upload flow stores public uploads below this directory.
    if relative.parts and relative.parts[0].lower() == "uploads":
        return True
    # Allow a future public source placed directly in Secondary, while keeping
    # the current reference-only files excluded explicitly above.
    return True


def _load_document(path: Path, root: Path, kb: str) -> SourceDocument:
    relative_file = path.relative_to(root).as_posix()
    source_id = f"{kb}:{relative_file}"

    try:
        if path.suffix.lower() == ".pdf":
            title, text, metadata = _read_pdf(path)
        else:
            raw_text = path.read_text(encoding="utf-8")
            metadata, body = _parse_front_matter(raw_text)
            title = metadata.get("title") or _title_from_markdown(body, path)
            text = body
    except IngestionError:
        raise
    except (OSError, UnicodeError) as exc:
        raise IngestionError(f"Unable to read source file {path}: {exc}") from exc
    except Exception as exc:
        raise IngestionError(f"Unable to parse source file {path}: {exc}") from exc

    default_visibility = "internal" if kb == "primary" else "public"
    visibility = metadata.get("visibility", default_visibility)
    if visibility not in VALID_VISIBILITIES:
        raise IngestionError(
            f"Invalid visibility {visibility!r} in {path}; "
            f"expected one of {sorted(VALID_VISIBILITIES)}"
        )

    return SourceDocument(
        source_id=source_id,
        kb=kb,
        source_file=relative_file,
        source_type=metadata.get("source_type") or _source_type(path, kb),
        document_type=metadata.get("document_type") or _document_type(path, kb),
        visibility=visibility,
        title=title,
        text=text,
    )


def _read_pdf(path: Path) -> tuple[str, str, dict[str, str]]:
    if PdfReader is None:
        raise IngestionError("PDF support requires the pypdf package")

    try:
        reader = PdfReader(str(path))
        metadata = reader.metadata or {}
        title = str(getattr(metadata, "title", None) or "").strip()
        pages: list[str] = []
        for page_number, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            pages.append(f"[PAGE {page_number}]\n{page_text.strip()}")
        text = "\n\n".join(pages).strip()
    except Exception as exc:
        raise IngestionError(f"Unable to extract PDF {path}: {exc}") from exc

    return title or _title_from_filename(path), text, {}


def _parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    """Read simple YAML-like metadata without adding a YAML dependency."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text

    end = next((index for index in range(1, len(lines)) if lines[index].strip() == "---"), None)
    if end is None:
        raise IngestionError("Front matter starts with '---' but has no closing '---'")

    metadata: dict[str, str] = {}
    for line in lines[1:end]:
        if not line.strip():
            continue
        if ":" not in line:
            raise IngestionError(f"Invalid front matter line: {line!r}")
        key, value = line.split(":", 1)
        key, value = key.strip(), value.strip()
        if not key or not value:
            raise IngestionError(f"Invalid front matter line: {line!r}")
        metadata[key] = value.strip("'\"")

    body = "\n".join(lines[end + 1 :]).lstrip("\n")
    return metadata, body


def _title_from_markdown(text: str, path: Path) -> str:
    match = re.search(r"^#\s+(.+?)\s*$", text, flags=re.MULTILINE)
    return match.group(1).strip() if match else _title_from_filename(path)


def _title_from_filename(path: Path) -> str:
    return path.stem.replace("_", " ").replace("-", " ").strip().title()


def _source_type(path: Path, kb: str) -> str:
    if kb == "primary":
        return "company_document"
    if "eu_ai_act" in path.as_posix().lower() or "ai_act" in path.stem.lower():
        return "regulation"
    return "public_upload"


def _document_type(path: Path, kb: str) -> str:
    if kb == "primary":
        return PRIMARY_DOCUMENT_TYPES.get(path.stem.lower(), "company_document")
    if "eu_ai_act" in path.as_posix().lower() or "ai_act" in path.stem.lower():
        return "eu_ai_act"
    return "uploaded_document"


if __name__ == "__main__":  # pragma: no cover - convenience CLI
    from src.config import PRIMARY_DIR, SECONDARY_DIR

    loaded = load_documents(PRIMARY_DIR, SECONDARY_DIR)
    print(f"Loaded {len(loaded)} documents: "
          f"{sum(document.kb == 'primary' for document in loaded)} primary, "
          f"{sum(document.kb == 'secondary' for document in loaded)} secondary")
    for document in loaded:
        print(f"- {document.kb}: {document.source_file} [{document.document_type}]")
