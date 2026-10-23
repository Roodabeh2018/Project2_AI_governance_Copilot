import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import indexing, retrieval


def make_chunk(chunk_id, kb, visibility, text):
    return {
        "chunk_id": chunk_id,
        "kb": kb,
        "source_file": f"{chunk_id}.md",
        "section": "Test section",
        "visibility": visibility,
        "document_type": "test",
        "text": text,
        "source_locator": f"{chunk_id}.md, Test section",
    }


class IndexingTests(unittest.TestCase):
    def test_markdown_sources_generate_loadable_chunks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            primary = root / "primary"
            secondary = root / "secondary"
            primary.mkdir()
            secondary.mkdir()
            (primary / "policy.md").write_text(
                "---\ntitle: Policy\nvisibility: internal\n"
                "document_type: policy\n---\n"
                "# Governance\n\nThe policy covers human oversight.\n\n"
                "## Monitoring\n\nMonitoring frequency needs review.\n",
                encoding="utf-8",
            )
            (secondary / "framework.md").write_text(
                "---\ntitle: Framework\nvisibility: public\n"
                "document_type: framework_summary\n---\n"
                "# Risk Management\n\nA public framework for AI risk.\n",
                encoding="utf-8",
            )
            chunks_path = root / "cache" / "chunks.jsonl"

            created = indexing.create_chunks_from_markdown(root, chunks_path)
            loaded = indexing.load_chunks(chunks_path)

        self.assertEqual(len(created), 3)
        self.assertEqual(len(loaded), 3)
        self.assertEqual(loaded[0]["visibility"], "internal")
        self.assertEqual(loaded[-1]["visibility"], "public")
        self.assertEqual(loaded[1]["source_locator"], "policy.md, Monitoring")

    def test_build_and_reload_index_returns_relevant_chunks(self):
        chunks = [
            make_chunk(
                "monitoring",
                "primary",
                "internal",
                "Monitoring schedule and escalation thresholds",
            ),
            make_chunk(
                "framework",
                "secondary",
                "public",
                "A general framework for AI risk management",
            ),
        ]

        with tempfile.TemporaryDirectory() as directory:
            index_path = Path(directory) / "vector_index.json"
            indexing.build_index(chunks, index_path)
            loaded_index = indexing.load_index(index_path)

            results = indexing.search_index(
                "monitoring escalation schedule",
                loaded_index,
                path=index_path,
            )

        self.assertEqual([result["chunk_id"] for result in results], ["monitoring"])
        self.assertEqual(results[0]["source_locator"], "monitoring.md, Test section")
        self.assertGreater(results[0]["score"], 0)

    def test_public_search_excludes_internal_and_mixed_chunks(self):
        chunks = [
            make_chunk("internal", "primary", "internal", "AI oversight controls"),
            make_chunk("mixed", "primary", "mixed", "AI oversight procedures"),
            make_chunk("public", "secondary", "public", "AI oversight framework"),
        ]
        with tempfile.TemporaryDirectory() as directory:
            index = indexing.build_index(
                chunks, Path(directory) / "vector_index.json"
            )
            results = indexing.search_index(
                "AI oversight",
                index,
                output_visibility="public",
                kb="secondary",
            )

        self.assertEqual([result["chunk_id"] for result in results], ["public"])

    def test_load_chunks_rejects_duplicate_chunk_ids(self):
        chunk = make_chunk("same", "primary", "internal", "test passage")

        with tempfile.TemporaryDirectory() as directory:
            chunks_path = Path(directory) / "chunks.jsonl"
            chunks_path.write_text(
                json.dumps(chunk) + "\n" + json.dumps(chunk) + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "Duplicate chunk_id"):
                indexing.load_chunks(chunks_path)

    def test_retrieve_uses_persisted_index_when_available(self):
        chunks = [
            make_chunk("internal", "primary", "internal", "monitoring schedule"),
            make_chunk("public", "primary", "public", "public monitoring framework"),
        ]

        with tempfile.TemporaryDirectory() as directory:
            index_path = Path(directory) / "vector_index.json"
            indexing.build_index(chunks, index_path)
            with patch.object(retrieval, "INDEX_PATH", index_path):
                results = retrieval.retrieve(
                    "monitoring schedule", output_visibility="public"
                )

        self.assertTrue(all(
            result["visibility"] == "public"
            for result in results["primary_results"] + results["secondary_results"]
        ))
        self.assertEqual(results["primary_results"][0]["chunk_id"], "public")


if __name__ == "__main__":
    unittest.main()
