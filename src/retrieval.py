import re
from pathlib import Path

if __package__:
    from .indexing import INDEX_PATH, load_index, search_index
else:
    from indexing import INDEX_PATH, load_index, search_index

ROOT = Path(__file__).resolve().parent.parent
KB = ROOT / "knowledge_base"
_VISIBILITIES = {"internal", "public", "mixed"}
_OUTPUT_VISIBILITIES = {"internal", "public"}


def load_documents():
    documents = []

    for folder, kb in [(KB / "primary", "primary"), (KB / "secondary", "secondary")]:
        for path in sorted(folder.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            metadata = {}
            front_matter = re.match(r"\A---\s*\n(.*?)\n---\s*\n?", text, re.DOTALL)
            if front_matter:
                for line in front_matter.group(1).splitlines():
                    key, separator, value = line.partition(":")
                    if separator:
                        metadata[key.strip()] = value.strip()
                text = text[front_matter.end():]

            visibility = metadata.get("visibility")
            if visibility not in _VISIBILITIES:
                raise ValueError(
                    f"Invalid or missing visibility metadata in {path}: {visibility!r}"
                )

            sections = re.split(r"(?m)(?=^#{1,3}\s)", text)

            for section in sections:
                section = section.strip()
                if not section:
                    continue

                heading = next(
                    (line.lstrip("# ").strip()
                     for line in section.splitlines()
                     if line.startswith("#")),
                    path.stem,
                )
                documents.append({
                    "kb": kb,
                    "visibility": visibility,
                    "document_type": metadata.get("document_type"),
                    "source_file": path.name,
                    "section": heading,
                    "text": section,
                    "source_locator": f"{path.name}, {heading}",
                })

    return documents


def retrieve(query, output_visibility="internal", top_k=3):
    if output_visibility not in _OUTPUT_VISIBILITIES:
        raise ValueError(
            f"output_visibility must be one of {sorted(_OUTPUT_VISIBILITIES)}"
        )
    if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k < 1:
        raise ValueError("top_k must be a positive integer")
    if not isinstance(query, str):
        raise TypeError("query must be a string")

    if INDEX_PATH.exists():
        index = load_index(INDEX_PATH)
        primary_results = search_index(
            query, index, top_k, output_visibility, kb="primary"
        )
        secondary_results = search_index(
            query, index, top_k, output_visibility, kb="secondary"
        )
        return {
            "query": query,
            "output_visibility": output_visibility,
            "retrieval_status": (
                "success"
                if primary_results or secondary_results
                else "insufficient_source"
            ),
            "primary_results": primary_results,
            "secondary_results": secondary_results,
        }

    terms = set(re.findall(r"\b[a-zA-Z0-9-]{3,}\b", query.lower()))
    results = []

    for doc in load_documents():
        if output_visibility == "public" and doc["visibility"] != "public":
            continue

        text_terms = set(re.findall(
            r"\b[a-zA-Z0-9-]{3,}\b",
            (doc["section"] + " " + doc["text"]).lower(),
        ))
        score = len(terms & text_terms)

        if score:
            results.append({**doc, "score": score})

    results.sort(key=lambda item: item["score"], reverse=True)

    primary_results = [r for r in results if r["kb"] == "primary"][:top_k]
    secondary_results = [r for r in results if r["kb"] == "secondary"][:top_k]

    return {
        "query": query,
        "output_visibility": output_visibility,
        "retrieval_status": (
            "success" if primary_results or secondary_results else "insufficient_source"
        ),
        "primary_results": primary_results,
        "secondary_results": secondary_results,
    }


if __name__ == "__main__":
    import json
    import sys

    query = " ".join(sys.argv[1:]) or "human oversight high-risk AI"
    context = retrieve(query)
    print(json.dumps(context, indent=2, ensure_ascii=False))
