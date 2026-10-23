import json
import math
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "cache"
CHUNKS_PATH = CACHE_DIR / "chunks.jsonl"
INDEX_PATH = CACHE_DIR / "vector_index.json"
INDEX_FORMAT_VERSION = 1
_TOKEN_PATTERN = re.compile(r"\b[a-zA-Z0-9-]{2,}\b")
_REQUIRED_FIELDS = (
    "chunk_id",
    "kb",
    "source_file",
    "visibility",
    "document_type",
    "text",
    "source_locator",
)


def _tokenize(text: str) -> list[str]:
    return _TOKEN_PATTERN.findall(text.lower())


def load_chunks(path: Path = CHUNKS_PATH) -> list[dict]:
    """Load and validate chunks produced by the document-processing stage."""
    if not path.exists():
        raise FileNotFoundError(
            f"Chunks file not found: {path}. "
            "Create chunks.jsonl before building the vector index."
        )

    chunks = []
    chunk_ids = set()

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

            if not isinstance(chunk, dict):
                raise ValueError(f"Chunk on line {line_number} must be a JSON object")

            missing = [
                field for field in _REQUIRED_FIELDS
                if not isinstance(chunk.get(field), str) or not chunk[field].strip()
            ]
            if missing:
                raise ValueError(
                    f"Chunk on line {line_number} is missing valid values for: "
                    f"{', '.join(missing)}"
                )

            if chunk["chunk_id"] in chunk_ids:
                raise ValueError(
                    f"Duplicate chunk_id on line {line_number}: {chunk['chunk_id']}"
                )
            if chunk["kb"] not in {"primary", "secondary"}:
                raise ValueError(f"Invalid kb value on line {line_number}")
            if chunk["visibility"] not in {"internal", "public", "mixed"}:
                raise ValueError(f"Invalid visibility on line {line_number}")

            chunk_ids.add(chunk["chunk_id"])
            chunks.append(chunk)

    if not chunks:
        raise ValueError("The chunks file contains no valid chunks.")

    return chunks


def save_metadata(chunks: list[dict]) -> None:
    """Save chunk metadata for inspection without duplicating passage text."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    metadata = [
        {key: value for key, value in chunk.items() if key != "text"}
        for chunk in chunks
    ]
    output_path = CACHE_DIR / "metadata.json"
    output_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Validated {len(chunks)} chunks.")
    print(f"Metadata saved to {output_path}")


def build_index(chunks: list[dict], path: Path = INDEX_PATH) -> dict:
    """Build and persist a normalized TF-IDF vector index using only stdlib."""
    if not chunks:
        raise ValueError("Cannot build an index without chunks.")

    document_frequencies = Counter()
    token_counts = []
    for chunk in chunks:
        counts = Counter(_tokenize(chunk["text"]))
        token_counts.append(counts)
        document_frequencies.update(counts.keys())

    document_count = len(chunks)
    idf = {
        token: math.log((document_count + 1) / (frequency + 1)) + 1
        for token, frequency in document_frequencies.items()
    }
    documents = []

    for chunk, counts in zip(chunks, token_counts):
        vector = {
            token: (1 + math.log(count)) * idf[token]
            for token, count in counts.items()
        }
        norm = math.sqrt(sum(weight * weight for weight in vector.values()))
        if norm:
            vector = {token: weight / norm for token, weight in vector.items()}

        documents.append({
            "chunk_id": chunk["chunk_id"],
            "metadata": {key: value for key, value in chunk.items() if key != "text"},
            "text": chunk["text"],
            "vector": vector,
        })

    index = {
        "format_version": INDEX_FORMAT_VERSION,
        "idf": idf,
        "documents": documents,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(index, ensure_ascii=False),
        encoding="utf-8",
    )
    return index


def load_index(path: Path = INDEX_PATH) -> dict:
    """Reload a previously built local index from JSON."""
    if not path.exists():
        raise FileNotFoundError(f"Vector index not found: {path}")

    try:
        index = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid vector index JSON in {path}: {exc}") from exc

    if (
        not isinstance(index, dict)
        or index.get("format_version") != INDEX_FORMAT_VERSION
        or not isinstance(index.get("idf"), dict)
        or not isinstance(index.get("documents"), list)
    ):
        raise ValueError(f"Unsupported or malformed vector index: {path}")

    for document in index["documents"]:
        if (
            not isinstance(document, dict)
            or not isinstance(document.get("metadata"), dict)
            or not isinstance(document.get("text"), str)
            or not isinstance(document.get("vector"), dict)
        ):
            raise ValueError(f"Malformed document entry in vector index: {path}")
    return index


def search_index(
    query: str,
    index: dict | None = None,
    top_k: int = 3,
    output_visibility: str = "internal",
    kb: str | None = None,
    path: Path = INDEX_PATH,
) -> list[dict]:
    """Return the top matching chunks, optionally filtering to public sources."""
    if not isinstance(query, str):
        raise TypeError("query must be a string")
    if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k < 1:
        raise ValueError("top_k must be a positive integer")
    if output_visibility not in {"internal", "public"}:
        raise ValueError("output_visibility must be 'internal' or 'public'")
    if kb not in {None, "primary", "secondary"}:
        raise ValueError("kb must be 'primary', 'secondary', or None")

    index = load_index(path) if index is None else index
    query_counts = Counter(_tokenize(query))
    query_vector = {
        token: (1 + math.log(count)) * index["idf"][token]
        for token, count in query_counts.items()
        if token in index["idf"]
    }
    norm = math.sqrt(sum(weight * weight for weight in query_vector.values()))
    if not norm:
        return []
    query_vector = {token: weight / norm for token, weight in query_vector.items()}

    results = []
    for document in index["documents"]:
        metadata = document["metadata"]
        if output_visibility == "public" and metadata.get("visibility") != "public":
            continue
        if kb is not None and metadata.get("kb") != kb:
            continue

        score = sum(
            weight * document["vector"].get(token, 0)
            for token, weight in query_vector.items()
        )
        if score:
            results.append({
                **metadata,
                "text": document["text"],
                "score": score,
            })

    results.sort(key=lambda item: item["score"], reverse=True)
    return results[:top_k]


def main() -> None:
    chunks = load_chunks()
    save_metadata(chunks)
    index = build_index(chunks)
    print(f"Built vector index with {len(index['documents'])} chunks at {INDEX_PATH}")


if __name__ == "__main__":
    main()
