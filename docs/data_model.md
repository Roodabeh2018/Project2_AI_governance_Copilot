# Data Model — AI Governance Copilot

The canonical models are defined in `docs/shared_engineering_contract.md` and must be implemented once in `src/contracts.py`.

## SourceDocument
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

## SourceChunk
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

Every chunk must have a non-empty `chunk_id`, `source_file`, `kb`, `visibility`, `document_type`, `text` and `source_locator`.

## RetrievalContext
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

Primary and secondary results must remain separate and retain their source metadata.

## GenerationRequest
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

## GeneratedDraft
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

The default status is `Draft — human review required`. A generated draft must never automatically close a finding or imply legal compliance.

## PotentialFinding
```json
{
  "finding_id": "F-001",
  "ai_system": "Credit Decision Support AI",
  "topic": "Monitoring",
  "evidence_status": "evidence_incomplete",
  "summary": "The supplied documents do not specify an approved monitoring frequency or escalation threshold.",
  "sources": [{"source_file": "monitoring_notes.md", "section": "Monitoring Notes"}],
  "suggested_document": "AI System Monitoring Plan",
  "recommended_next_step": "Ask the accountable owner to confirm the monitoring schedule and thresholds.",
  "review_status": "Open"
}
```
