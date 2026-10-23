"""Retrieve relevant evidence independently from the Primary and Secondary KBs."""
from __future__ import annotations

import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Literal

import numpy as np

from src.config import CACHE_DIR, load_config
from src.contracts import (
    RetrievalContext,
    RetrievalError,
    RetrievalResult,
)
from src.indexing import LocalVectorIndex, _embed_texts, load_index

RETRIEVED_CONTEXT_PATH = CACHE_DIR / "retrieved_context.json"


def retrieve(
    query: str,
    output_visibility: Literal["internal", "public"] = "internal",
    top_k_primary: int = 3,
    top_k_secondary: int = 3,
    *,
    index_path: Path = CACHE_DIR,
    context_path: Path = RETRIEVED_CONTEXT_PATH,
) -> RetrievalContext:
    """Retrieve separately ranked top-k results and save their context JSON."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string.")
    if output_visibility not in {"internal", "public"}:
        raise ValueError("output_visibility must be 'internal' or 'public'.")
    if top_k_primary < 1 or top_k_secondary < 1:
        raise ValueError("top_k_primary and top_k_secondary must be positive.")

    config = load_config()
    index = load_index(index_path)
    requested_system = _requested_ai_system(query)
    known_systems = _known_ai_systems(index)
    if requested_system and requested_system.casefold() not in {
        system.casefold() for system in known_systems
    }:
        context = RetrievalContext(
            query=query,
            output_visibility=output_visibility,
            retrieval_status="insufficient_source",
            primary_results=[],
            secondary_results=[],
            message=(
                f"No matching AI-system entry was found in the supplied inventory for "
                f"'{requested_system}'; this does not establish whether the system exists "
                "elsewhere."
            ),
        )
        _save_context(context, Path(context_path))
        return context

    query_vectors = _embed_texts([query])
    if query_vectors.shape[0] != 1 or query_vectors.shape[1] != index.vectors.shape[1]:
        raise RetrievalError("Query embedding dimension does not match the local index.")
    query_vector = query_vectors[0]

    primary_results = _retrieve_group(
        index,
        query_vector,
        "primary",
        output_visibility,
        top_k_primary,
        config.minimum_retrieval_score,
    )
    secondary_results = _retrieve_group(
        index,
        query_vector,
        "secondary",
        output_visibility,
        top_k_secondary,
        config.minimum_retrieval_score,
    )
    has_results = bool(primary_results or secondary_results)
    context = RetrievalContext(
        query=query,
        output_visibility=output_visibility,
        retrieval_status="success" if has_results else "insufficient_source",
        primary_results=primary_results,
        secondary_results=secondary_results,
        message=None if has_results else "No chunks met the minimum retrieval score.",
    )
    _save_context(context, Path(context_path))
    return context


def _retrieve_group(
    index: LocalVectorIndex,
    query_vector: np.ndarray,
    kb: Literal["primary", "secondary"],
    output_visibility: Literal["internal", "public"],
    top_k: int,
    minimum_score: float,
) -> list[RetrievalResult]:
    selected = [
        (position, chunk)
        for position, chunk in enumerate(index.chunks)
        if chunk.kb == kb
        and (output_visibility != "public" or chunk.visibility == "public")
    ]
    if not selected:
        return []

    positions = [position for position, _ in selected]
    chunks = [chunk for _, chunk in selected]
    group_index = LocalVectorIndex(
        vectors=index.vectors[positions],
        chunks=chunks,
    )
    matches = group_index.search(query_vector, top_k=top_k)
    results = []
    for chunk, score in matches:
        if score < minimum_score:
            continue
        results.append(
            RetrievalResult(
                rank=len(results) + 1,
                score=score,
                chunk=chunk,
                citation=chunk.source_locator,
            )
        )
    return results


def _known_ai_systems(index: LocalVectorIndex) -> set[str]:
    systems = set()
    for chunk in index.chunks:
        if chunk.document_type != "inventory":
            continue
        match = re.match(r"^\s*System:\s*(.+?)\s*$", chunk.section, flags=re.IGNORECASE)
        if match:
            systems.add(match.group(1))
    return systems


def _requested_ai_system(query: str) -> str | None:
    labeled_system = re.search(
        r"(?:^|[;\n])\s*AI system:\s*([^;\n]+)",
        query,
        flags=re.IGNORECASE,
    )
    if labeled_system:
        return labeled_system.group(1).strip().rstrip(".")

    system_id = re.search(
        r"\bAI[-_][A-Z0-9]+\b",
        query,
        flags=re.IGNORECASE,
    )
    return system_id.group(0) if system_id else None


def _save_context(context: RetrievalContext, path: Path) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(asdict(context), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise RetrievalError(f"Unable to save retrieved context to {path}: {exc}") from exc


def has_sufficient_source(context: RetrievalContext) -> bool:
    """Return whether retrieval found at least one supported result."""
    return (
        context.retrieval_status == "success"
        and bool(context.primary_results or context.secondary_results)
    )
