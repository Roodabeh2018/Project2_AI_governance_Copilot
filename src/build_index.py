"""Build the chunk cache and vector index (Color A + B) in one command.

    python -m src.build_index

Needs OPENAI_API_KEY (embeddings). Used locally and as part of the Render build command,
because cache/ is git-ignored and must be rebuilt on the server.
"""
from src.chunking import rebuild_cache
from src.config import CACHE_DIR, PRIMARY_DIR, SECONDARY_DIR
from src.indexing import build_index


def main() -> None:
    chunks = rebuild_cache(PRIMARY_DIR, SECONDARY_DIR, CACHE_DIR)
    build_index(chunks, CACHE_DIR)
    print(f"Index built: {len(chunks)} chunks in {CACHE_DIR}")


if __name__ == "__main__":
    main()
