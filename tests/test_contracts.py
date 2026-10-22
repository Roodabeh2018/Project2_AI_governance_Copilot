import json
from pathlib import Path

from src.contracts import SourceChunk


FIXTURES = Path(__file__).parent / "fixtures"


def test_primary_fixture_matches_source_chunk_contract():
    line = (FIXTURES / "sample_primary_chunks.jsonl").read_text().splitlines()[0]
    chunk = SourceChunk(**json.loads(line))

    assert chunk.kb == "primary"
    assert chunk.visibility == "internal"
    assert chunk.source_locator


def test_secondary_fixture_preserves_pdf_locator():
    line = (FIXTURES / "sample_secondary_chunks.jsonl").read_text().splitlines()[1]
    chunk = SourceChunk(**json.loads(line))

    assert chunk.kb == "secondary"
    assert chunk.article_or_annex == "Article 14"
    assert "page=80" in chunk.source_locator
