# AI Governance Copilot — Shared Engineering Contract

## 1. Purpose

This document defines the shared contracts between the three implementation tracks:

- Color A — Ingestion & Knowledge Base
- Color B — Retrieval, Index & Grounding
- Color C — Prompt, LLM, CLI & Gradio

All developers must use these shared models, field names, enums, paths and interfaces. No track should create a parallel or incompatible version of these definitions.

---

# 2. Shared Project Structure

```text
src/
├── contracts.py          # Shared data models and enums
├── config.py             # Environment and application settings
├── ingestion.py          # Color A
├── chunking.py           # Color A
├── indexing.py           # Color B
├── retrieval.py          # Color B
├── prompts.py            # Color C
├── llm_generator.py      # Color C
├── pipeline.py           # Color C
└── app.py                # Gradio interface

knowledge_base/
├── primary/              # Internal company documents
└── secondary/            # EU AI Act and public sources

cache/
├── chunks.jsonl
├── source_manifest.json
├── vectors.npy
└── metadata.json

outputs/
├── governance_documents/
└── internal_updates/

tests/
├── fixtures/
├── test_ingestion.py
├── test_retrieval.py
├── test_visibility.py
└── test_pipeline.py
```

The exact filenames may change only by team agreement.

---

# 3. Shared Ontology

## 3.1 Knowledge-base types

```text
primary
secondary
```

### Primary KB

Internal company documents, such as:

```text
policy
inventory
risk_assessment
technical_documentation
procedure
validation_report
monitoring_notes
```

### Secondary KB

Public or regulatory sources, such as:

```text
eu_ai_act
regulatory_reference
framework_reference
public_guidance
```

User-uploaded internal documents must go to `primary`.

User-uploaded public documents must go to `secondary`.

---

## 3.2 Visibility values

```text
internal
public
mixed
```

Rules:

```text
internal:
May be used only for internal outputs.

public:
May be used for internal or public outputs.

mixed:
Must be filtered carefully and should not be used for public output by default.
```

---

## 3.3 Request types

```text
governance_document
internal_update
```

Optional future type:

```text
linkedin
```

The `linkedin` type is not required for the MVP.

---

## 3.4 Output visibility

```text
internal
public
```

This field controls retrieval filtering before prompt construction.

```text
output_visibility = "public"
```

means that internal chunks must not enter the prompt.

---

## 3.5 Retrieval status

```text
success
insufficient_source
error
```

---

## 3.6 Evidence status

```text
evidence_found
evidence_incomplete
evidence_not_found
```

These labels must be used consistently in generated outputs.

---

# 4. Shared Data Models

The models below should be defined once in:

```text
src/contracts.py
```

No developer should redefine these models in another module.

## 4.1 SourceDocument

```python
@dataclass
class SourceDocument:
    source_id: str
    kb: Literal["primary", "secondary"]
    source_file: str
    source_type: str
    document_type: str
    visibility: Literal["internal", "public", "mixed"]
    title: str
    text: str
```

---

## 4.2 SourceChunk

```python
@dataclass
class SourceChunk:
    chunk_id: str
    kb: Literal["primary", "secondary"]
    source_file: str
    source_type: str
    document_type: str
    visibility: Literal["internal", "public", "mixed"]
    page_start: int | None
    page_end: int | None
    section: str
    article_or_annex: str | None
    title: str
    text: str
    source_locator: str
```

Required invariant:

```text
Every chunk must have a non-empty chunk_id, source_file, kb,
visibility, document_type, text and source_locator.
```

---

## 4.3 RetrievalResult

```python
@dataclass
class RetrievalResult:
    rank: int
    score: float
    chunk: SourceChunk
    citation: str
```

---

## 4.4 RetrievalContext

```python
@dataclass
class RetrievalContext:
    query: str
    output_visibility: Literal["internal", "public"]
    retrieval_status: Literal["success", "insufficient_source", "error"]
    primary_results: list[RetrievalResult]
    secondary_results: list[RetrievalResult]
    message: str | None = None
```

Primary and secondary results must remain separate.

Do not merge them into one unlabelled list.

---

## 4.5 GenerationRequest

```python
@dataclass
class GenerationRequest:
    request_type: Literal["governance_document", "internal_update"]
    document_type: str | None
    ai_system: str | None
    topic: str
    output_visibility: Literal["internal", "public"]
    primary_context: list[RetrievalResult]
    secondary_context: list[RetrievalResult]
    selected_findings: list[str]
```

---

## 4.6 GeneratedDraft

```python
@dataclass
class GeneratedDraft:
    title: str
    request_type: str
    status: str
    content_markdown: str
    citations: list[str]
    evidence_status: str
    open_questions: list[str]
    output_path: str | None
```

The default status must be:

```text
Draft — human review required
```

---

# 5. Required Function Interfaces

## 5.1 Color A — Ingestion

```python
def load_documents(
    primary_path: Path,
    secondary_path: Path
) -> list[SourceDocument]:
    ...
```

```python
def chunk_documents(
    documents: list[SourceDocument]
) -> list[SourceChunk]:
    ...
```

```python
def save_chunks(
    chunks: list[SourceChunk],
    output_path: Path
) -> None:
    ...
```

Color A must deliver:

```text
list[SourceChunk]
chunks.jsonl
source_manifest.json
```

---

## 5.2 Color B — Index and retrieval

```python
def build_index(
    chunks: list[SourceChunk],
    index_path: Path
) -> None:
    ...
```

```python
def retrieve(
    query: str,
    output_visibility: Literal["internal", "public"],
    top_k_primary: int,
    top_k_secondary: int
) -> RetrievalContext:
    ...
```

```python
def has_sufficient_source(
    context: RetrievalContext
) -> bool:
    ...
```

Color B must deliver:

```text
RetrievalContext
retrieved_context.json
retrieval test results
```

---

## 5.3 Color C — Prompt and generation

```python
def build_prompt(
    request: GenerationRequest
) -> str:
    ...
```

```python
def generate_text(
    prompt: str
) -> str:
    ...
```

```python
def generate_draft(
    request: GenerationRequest
) -> GeneratedDraft:
    ...
```

---

## 5.4 Pipeline

```python
def run_pipeline(
    request: GenerationRequest
) -> GeneratedDraft:
    ...
```

The pipeline must execute:

```text
Request
→ Retrieval
→ Visibility filtering
→ Prompt construction
→ LLM generation
→ Output validation
→ Markdown save
```

---

# 6. Shared Rules for Retrieval

1. Retrieve from Primary and Secondary KBs separately.
2. Apply visibility filtering before prompt construction.
3. Preserve source metadata in every result.
4. Do not let the Secondary KB crowd out the Primary KB.
5. Do not treat retrieval failure as proof that evidence does not exist.
6. Return `insufficient_source` for unsupported queries.
7. Use configurable values for:

```text
top_k_primary
top_k_secondary
minimum_score
```

Suggested initial values:

```text
top_k_primary = 3
top_k_secondary = 3
minimum_score = 0.35
```

These values may be tuned during testing.

---

# 7. Shared File and Naming Conventions

## Python

```text
snake_case for files and functions
PascalCase for classes
UPPER_CASE for constants
```

Examples:

```text
source_chunk.py       # avoid
source_chunk          # avoid as a module if contracts.py owns it
contracts.py          # preferred
SourceChunk           # class
chunk_documents       # function
DEFAULT_TOP_K         # constant
```

## Files

```text
chunks.jsonl
source_manifest.json
retrieved_context.json
answer_key_results.md
public_leakage_test.md
```

## Output filenames

```text
governance_document_YYYYMMDD_HHMM.md
internal_update_YYYYMMDD_HHMM.md
```

---

# 8. Configuration Contract

Use environment variables only through `src/config.py`.

```text
OPENAI_API_KEY
MODEL_NAME
EMBEDDING_MODEL
TOP_K_PRIMARY
TOP_K_SECONDARY
MIN_RETRIEVAL_SCORE
```

No API key may appear in source code, tests or Trello comments.

Suggested configuration object:

```python
@dataclass
class AppConfig:
    model_name: str
    embedding_model: str
    top_k_primary: int
    top_k_secondary: int
    minimum_retrieval_score: float
```

---

# 9. Error Contract

Use shared error classes from `src/contracts.py` or `src/errors.py`.

```python
class ConfigurationError(Exception):
    pass


class IngestionError(Exception):
    pass


class RetrievalError(Exception):
    pass


class GenerationError(Exception):
    pass
```

Required behavior:

```text
Missing API key → clear configuration error
Unreadable source file → clear ingestion error
Empty retrieval → insufficient_source
LLM failure → clear generation error
Invalid metadata → validation error
```

Do not silently return empty lists or empty strings when an error occurs.

---

# 10. Shared Test Fixtures

Create small fixtures so all three developers can work in parallel.

```text
tests/fixtures/
├── sample_primary_chunks.jsonl
├── sample_secondary_chunks.jsonl
├── sample_retrieved_context.json
└── sample_generation_request.json
```

The fixture must contain:

```text
At least 2 primary chunks
At least 2 secondary chunks
At least 1 internal chunk
At least 1 public chunk
At least 1 matching query
At least 1 unsupported query
```

Shared positive query:

```text
What does the EU AI Act say about human oversight of high-risk AI systems?
```

Shared negative query:

```text
What is the monitoring status of AI system AI-99?
```

Expected negative result:

```text
retrieval_status = "insufficient_source"
```

---

# 11. Git and Integration Rules

1. Do not modify another color's core module without agreement.
2. Commit shared contracts before feature work.
3. Pull the latest shared contract before integration.
4. Do not redefine shared fields locally.
5. Do not rename fields without updating all three tracks.
6. Every pull request must include a test or fixture update where relevant.
7. Keep commits small and focused.
8. Use the same sample fixtures across all branches.

Suggested commit sequence:

```text
commit 1: shared contracts and fixtures
commit 2: Color A ingestion
commit 3: Color B index and retrieval
commit 4: Color C prompts and CLI
commit 5: Gradio integration
commit 6: tests and demo evidence
```

---

# 12. Decisions to Confirm Before Coding

The team must agree on these items:

```text
Exact location of the nine primary company documents
Whether EU AI Act Article/Annex Markdown already exists
PDF conversion fallback if Markdown is unavailable
Embedding model
LLM model
Top-k values
Minimum retrieval score
Chunk size and overlap
Output filename format
Gradio input fields
Gradio upload behavior
Whether user uploads persist in the KB
```

Recommended MVP defaults:

```text
Primary internal uploads persist in knowledge_base/primary/
Public uploads persist in knowledge_base/secondary/
User uploads do not become public automatically.
Default internal upload visibility = internal.
Default public upload visibility = public.
```

---

# 13. Final Integration Definition

The system is considered integrated when this flow works:

```text
Primary company documents
+
EU AI Act / public sources
        ↓
SourceDocument
        ↓
SourceChunk
        ↓
Local vector index
        ↓
Separate primary and secondary retrieval
        ↓
Visibility filtering
        ↓
GenerationRequest
        ↓
Prompt template
        ↓
LLM
        ↓
GeneratedDraft
        ↓
Markdown output
        ↓
Gradio display
```

The most important rule is:

```text
One shared contract, one source of truth, no duplicated models.
```