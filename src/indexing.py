"""Build and reload the local vector index (Shared Engineering Contract §5.2)."""
from __future__ import annotations

import hashlib
import io
import json
import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from src.config import CACHE_DIR, get_api_key, load_config
from src.contracts import (
    ConfigurationError,
    RetrievalError,
    SchemaValidationError,
    SourceChunk,
    chunk_from_dict,
    to_dict,
)

CHUNKS_PATH = CACHE_DIR / "chunks.jsonl"
VECTORS_FILENAME = "vectors.npy"
METADATA_FILENAME = "metadata.json"
INDEX_FORMAT_VERSION = 1
EMBEDDING_BATCH_SIZE = 100


@dataclass
class LocalVectorIndex:
    """In-memory vectors and their canonical source-chunk mapping."""

    vectors: np.ndarray
    chunks: list[SourceChunk]

    def search(
        self,
        query_vector: list[float] | np.ndarray,
        top_k: int = 3,
    ) -> list[tuple[SourceChunk, float]]:
        """Return the top matching chunks and cosine-similarity scores."""
        query = np.asarray(query_vector, dtype=np.float32)
        if query.ndim != 1 or query.shape[0] != self.vectors.shape[1]:
            raise ValueError(
                f"Query vector must have {self.vectors.shape[1]} dimensions."
            )
        if not np.isfinite(query).all() or not np.linalg.norm(query):
            raise ValueError("Query vector must contain finite, non-zero values.")
        if top_k < 1:
            raise ValueError("top_k must be positive.")

        vector_norms = np.linalg.norm(self.vectors, axis=1)
        if np.any(vector_norms == 0):
            raise SchemaValidationError("The local index contains a zero vector.")
        scores = (self.vectors @ query) / (vector_norms * np.linalg.norm(query))
        matches = np.argsort(-scores, kind="stable")[:top_k]
        return [(self.chunks[int(i)], float(scores[i])) for i in matches]


def load_chunks(path: Path = CHUNKS_PATH) -> list[SourceChunk]:
    """Load and validate chunks produced by Color A from JSONL."""
    if not path.exists():
        raise FileNotFoundError(
            f"Chunks file not found: {path}. "
            "Ask Color A for chunks.jsonl first."
        )

    chunks: list[SourceChunk] = []
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line {line_number}: {exc}"
                ) from exc
            try:
                chunks.append(chunk_from_dict(value))
            except (SchemaValidationError, TypeError, KeyError) as exc:
                raise SchemaValidationError(
                    f"Invalid chunk on line {line_number}: {exc}"
                ) from exc

    if not chunks:
        raise ValueError("The chunks file contains no valid chunks.")
    return chunks


def build_index(chunks: list[SourceChunk], index_path: Path) -> None:
    """Create embeddings and persist vectors plus their chunk mapping."""
    if not chunks:
        raise ValueError("Cannot build an index without chunks.")
    if not all(isinstance(chunk, SourceChunk) for chunk in chunks):
        raise SchemaValidationError("Index input must contain SourceChunk values.")

    vectors = _embed_texts([chunk.text for chunk in chunks])
    if vectors.ndim != 2 or vectors.shape[0] != len(chunks):
        raise RetrievalError("Embedding service returned an invalid vector matrix.")
    if (
        vectors.shape[1] == 0
        or not np.isfinite(vectors).all()
        or np.any(np.linalg.norm(vectors, axis=1) == 0)
    ):
        raise RetrievalError("Embedding service returned invalid vector values.")

    index_dir = Path(index_path)
    metadata = {
        "format_version": INDEX_FORMAT_VERSION,
        "embedding_model": load_config().embedding_model,
        "vector_count": len(chunks),
        "vector_dimension": int(vectors.shape[1]),
        "chunks": [
            {"vector_id": vector_id, **to_dict(chunk)}
            for vector_id, chunk in enumerate(chunks)
        ],
    }
    try:
        index_dir.mkdir(parents=True, exist_ok=True)
        _write_index_files(index_dir, vectors, metadata)
    except OSError as exc:
        raise RetrievalError(f"Unable to save local vector index to {index_dir}: {exc}") from exc


def load_index(index_path: Path = CACHE_DIR) -> LocalVectorIndex:
    """Reload vectors and their source-chunk mapping from a local index."""
    index_dir = Path(index_path)
    vectors_path = index_dir / VECTORS_FILENAME
    metadata_path = index_dir / METADATA_FILENAME
    try:
        vector_bytes = vectors_path.read_bytes()
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise RetrievalError(
            f"Unable to load local vector index from {index_dir}: {exc}"
        ) from exc

    if not isinstance(metadata, dict) or metadata.get("format_version") != INDEX_FORMAT_VERSION:
        raise SchemaValidationError("Unsupported or invalid local index metadata.")
    expected_vectors_hash = metadata.get("vectors_sha256")
    actual_vectors_hash = hashlib.sha256(vector_bytes).hexdigest()
    if not isinstance(expected_vectors_hash, str) or expected_vectors_hash != actual_vectors_hash:
        raise SchemaValidationError(
            "Vector data does not match its metadata; rebuild the local index before using it."
        )
    stored_model = metadata.get("embedding_model")
    configured_model = load_config().embedding_model
    if not isinstance(stored_model, str) or not stored_model:
        raise SchemaValidationError("Local index metadata has no embedding model.")
    if stored_model != configured_model:
        raise RetrievalError(
            f"Local index uses embedding model '{stored_model}', but the configured model is "
            f"'{configured_model}'. Rebuild the local index with the configured model."
        )
    try:
        vectors = np.load(io.BytesIO(vector_bytes), allow_pickle=False)
    except (OSError, ValueError) as exc:
        raise SchemaValidationError(f"Unable to decode local vector data: {exc}") from exc
    entries = metadata.get("chunks")
    if not isinstance(entries, list) or not entries:
        raise SchemaValidationError("Local index metadata has no chunk mappings.")
    if vectors.ndim != 2 or vectors.shape[0] != len(entries):
        raise SchemaValidationError("Vector data and chunk mapping counts do not match.")
    if vectors.shape[1] == 0 or vectors.shape[1] != metadata.get("vector_dimension"):
        raise SchemaValidationError("Vector dimension does not match index metadata.")
    if metadata.get("vector_count") != len(entries):
        raise SchemaValidationError("Vector count does not match index metadata.")
    if not np.isfinite(vectors).all() or np.any(np.linalg.norm(vectors, axis=1) == 0):
        raise SchemaValidationError("Local index contains invalid vectors.")

    chunks = []
    for vector_id, entry in enumerate(entries):
        if not isinstance(entry, dict) or entry.get("vector_id") != vector_id:
            raise SchemaValidationError(
                "Chunk mappings must have contiguous vector_id values starting at zero."
            )
        chunk_data = {key: value for key, value in entry.items() if key != "vector_id"}
        try:
            chunks.append(chunk_from_dict(chunk_data))
        except (SchemaValidationError, TypeError, KeyError) as exc:
            raise SchemaValidationError(
                f"Invalid chunk mapping for vector {vector_id}: {exc}"
            ) from exc
    return LocalVectorIndex(vectors=vectors, chunks=chunks)


def _embed_texts(texts: list[str]) -> np.ndarray:
    """Request OpenAI embeddings in bounded batches."""
    key = get_api_key()
    import openai

    config = load_config()
    client = openai.OpenAI(api_key=key)
    embeddings: list[list[float] | None] = [None] * len(texts)
    try:
        for start in range(0, len(texts), EMBEDDING_BATCH_SIZE):
            batch = texts[start:start + EMBEDDING_BATCH_SIZE]
            response = client.embeddings.create(
                model=config.embedding_model,
                input=batch,
            )
            for item in response.data:
                index = start + item.index
                if item.index < 0 or item.index >= len(batch) or embeddings[index] is not None:
                    raise RetrievalError("Embedding service returned invalid item indices.")
                embeddings[index] = item.embedding
    except openai.AuthenticationError as exc:
        raise ConfigurationError(
            "The API key was rejected — check OPENAI_API_KEY in .env."
        ) from exc
    except openai.NotFoundError as exc:
        raise ConfigurationError(
            f"Embedding model '{config.embedding_model}' not found — check EMBEDDING_MODEL in .env."
        ) from exc
    except openai.RateLimitError as exc:
        raise RetrievalError(
            "Embedding rate limit or quota reached — wait a minute or check billing."
        ) from exc
    except openai.APIConnectionError as exc:
        raise RetrievalError(
            "Could not reach the OpenAI API while creating embeddings."
        ) from exc
    except openai.OpenAIError as exc:
        raise RetrievalError(f"Embedding request failed: {exc}") from exc

    if any(embedding is None for embedding in embeddings):
        raise RetrievalError("Embedding service returned an incomplete result.")
    try:
        vector_matrix = np.asarray(embeddings, dtype=np.float32)
    except (TypeError, ValueError) as exc:
        raise RetrievalError("Embedding service returned malformed vectors.") from exc
    if vector_matrix.ndim != 2 or not np.isfinite(vector_matrix).all():
        raise RetrievalError("Embedding service returned invalid vector values.")
    return vector_matrix


def _write_index_files(
    index_dir: Path,
    vectors: np.ndarray,
    metadata: dict,
) -> None:
    """Write checksummed artifacts so interrupted replacement is detected."""
    vectors_path = index_dir / VECTORS_FILENAME
    metadata_path = index_dir / METADATA_FILENAME
    vectors_temp = index_dir / f".{VECTORS_FILENAME}.tmp"
    metadata_temp = index_dir / f".{METADATA_FILENAME}.tmp"
    vector_buffer = io.BytesIO()
    np.save(vector_buffer, vectors, allow_pickle=False)
    vector_bytes = vector_buffer.getvalue()
    metadata["vectors_sha256"] = hashlib.sha256(vector_bytes).hexdigest()
    try:
        with vectors_temp.open("wb") as file:
            file.write(vector_bytes)
        metadata_temp.write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        os.replace(vectors_temp, vectors_path)
        os.replace(metadata_temp, metadata_path)
    except OSError as exc:
        raise RetrievalError(f"Unable to write local vector index: {exc}") from exc
    finally:
        try:
            vectors_temp.unlink(missing_ok=True)
            metadata_temp.unlink(missing_ok=True)
        except OSError as exc:
            raise RetrievalError(f"Unable to clean up temporary index files: {exc}") from exc
