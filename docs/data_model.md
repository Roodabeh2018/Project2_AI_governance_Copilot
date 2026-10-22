# Suggested Data Model

## SourceChunk
```json
{
  "chunk_id": "string",
  "source_file": "string",
  "section": "string",
  "visibility": "public | internal | mixed",
  "document_type": "policy | inventory | risk_assessment | technical_documentation | procedure | validation_report | regulatory_reference",
  "text": "string"
}
```

## PotentialFinding
```json
{
  "finding_id": "F-001",
  "ai_system": "Credit Decision Support AI",
  "topic": "Monitoring",
  "evidence_status": "evidence_incomplete",
  "summary": "The supplied documents do not specify an approved monitoring frequency or escalation threshold.",
  "sources": [
    {"source_file": "monitoring_notes.md", "section": "Monitoring Notes"}
  ],
  "suggested_document": "AI System Monitoring Plan",
  "recommended_next_step": "Ask the accountable owner to confirm the monitoring schedule and thresholds.",
  "review_status": "Open"
}
```

## GeneratedDocument
```json
{
  "document_id": "DOC-001",
  "title": "AI System Monitoring Plan",
  "ai_system": "Credit Decision Support AI",
  "content_markdown": "string",
  "source_finding_ids": ["F-001"],
  "source_files": ["monitoring_notes.md"],
  "status": "Draft — human review required",
  "open_questions": ["Who is the accountable monitoring owner?"],
  "reviewer": null,
  "approval_date": null
}
```

A generated draft must never automatically change a finding to closed.
