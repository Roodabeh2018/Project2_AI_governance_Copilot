
import json
from pathlib import Path

CACHE_DIR = Path("cache")
CHUNKS_PATH = CACHE_DIR / "chunks.jsonl"


def load_chunks(path: Path = CHUNKS_PATH) -> list[dict]:
    """Load chunks produced by Color A from JSONL."""
    if not path.exists():
        raise FileNotFoundError(
            f"Chunks file not found: {path}. "
            "Ask Color A for chunks.jsonl first."
        )

    chunks = []

    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue

            try:
                chunk = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line {line_number}: {exc}"
                ) from exc

            required_fields = [
                "chunk_id",
                "kb",
                "source_file",
                "visibility",
                "document_type",
                "text",
                "source_locator",
            ]

            missing = [
                field for field in required_fields
                if not chunk.get(field)
            ]

            if missing:
                raise ValueError(
                    f"Chunk on line {line_number} is missing: "
                    f"{', '.join(missing)}"
                )

            if chunk["kb"] not in {"primary", "secondary"}:
                raise ValueError(
                    f"Invalid kb value on line {line_number}"
                )

            if chunk["visibility"] not in {
                "internal", "public", "mixed"
            }:
                raise ValueError(
                    f"Invalid visibility on line {line_number}"
                )

            chunks.append(chunk)

    if not chunks:
        raise ValueError("The chunks file contains no valid chunks.")

    return chunks


def save_metadata(chunks: list[dict]) -> None:
    """Save chunk metadata for the indexing stage."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    metadata = [
        {
            key: value
            for key, value in chunk.items()
            if key != "text"
        }
        for chunk in chunks
    ]

    output_path = CACHE_DIR / "metadata.json"
    output_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Validated {len(chunks)} chunks.")
    print(f"Metadata saved to {output_path}")
