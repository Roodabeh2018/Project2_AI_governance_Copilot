# Public-output retrieval leakage test

**Run date:** 2026-10-23

## Test

Query: “General public information about human oversight and high-risk AI systems”

The live local index was queried with `output_visibility="public"`. The resulting `RetrievalContext` was passed through the pipeline's pre-generation visibility enforcement and used to build a prompt. The prompt was checked against the indexed non-public chunk texts.

## Result

- Retrieval status: `success`
- Retrieved results: 5
- Results with visibility other than `public`: 0
- Non-public chunk texts found in the constructed prompt: 0
- Citations equal to each result's `SourceChunk.source_locator`: all passed

The filter is applied before prompt construction. The pipeline's public-visibility regression also injects internal and mixed chunks into a context and verifies they are removed before the generation function is called.

This test covers source filtering and prompt construction; it does not validate arbitrary text a language model might generate. Human review remains required for any public communication.
