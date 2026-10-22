import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KB = ROOT / "knowledge_base"


def load_documents():
    documents = []

    for folder, kb, visibility in [
        (KB / "primary", "primary", "internal"),
        (KB / "secondary", "secondary", "public"),
    ]:
        for path in sorted(folder.glob("*.md")):
            text = path.read_text(encoding="utf-8")
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
                    "source_file": path.name,
                    "section": heading,
                    "text": section,
                    "source_locator": f"{path.name}, {heading}",
                })

    return documents


def retrieve(query, output_visibility="internal", top_k=3):
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

    return {
        "query": query,
        "output_visibility": output_visibility,
        "retrieval_status": "success" if results else "insufficient_source",
        "primary_results": [r for r in results if r["kb"] == "primary"][:top_k],
        "secondary_results": [r for r in results if r["kb"] == "secondary"][:top_k],
    }


if __name__ == "__main__":
    import json
    import sys

    query = " ".join(sys.argv[1:]) or "human oversight high-risk AI"
    context = retrieve(query)
    print(json.dumps(context, indent=2, ensure_ascii=False))
