# Prompt Templates — AI Governance Copilot

## Shared system instructions
Follow `agents.md`. Use retrieved evidence only. Cite sources. Do not invent facts or legal conclusions. Use placeholders for unknowns. Label all generated documents as drafts requiring human review.

## Template 1 — `governance_document`
Dynamic inputs:
- `{document_type}`
- `{ai_system}`
- `{selected_findings}`
- `{internal_context}`
- `{reference_context}`
- `{existing_document}`

Prompt:
```text
Draft a {document_type} for {ai_system} using only the evidence supplied below.

Selected potential findings:
{selected_findings}

Retrieved internal/company passages:
{internal_context}

Retrieved public regulatory/framework passages:
{reference_context}

Existing document, if any:
{existing_document}

Requirements:
- Mark the output "Draft — human review required".
- Use source-supported company facts only.
- Cite the source filename and section for material claims.
- Clearly separate current documented facts from proposed recommendations.
- Do not invent owners, dates, versions, classifications, frequencies, thresholds, approval records or test results.
- Put unknown information in explicit placeholders such as [OWNER TO CONFIRM].
- Include an evidence/source register, open questions and an approval block left blank.
- Do not claim legal non-compliance based only on missing evidence.
- Do not claim that generating this draft closes the gap or proves implementation.
```

## Template 2 — `internal_update`
```text
Write a concise internal AI governance update about {topic}.

Use only the retrieved source passages:
{retrieved_context}

Include:
- What the supplied documents currently say.
- Potential documentation/evidence gaps, phrased cautiously.
- Proposed next steps and any known owners (only if sourced).
- Open questions and decisions needed.
- Source citations.
- A clear distinction between evidence found and evidence not found in the supplied files.

Do not invent facts or make a legal compliance determination. Label the output "Draft — human review required".
```

## Optional Template 3 — `linkedin`
```text
Write a short, professional LinkedIn post about {topic} for a general AI governance audience.

Use only public-tagged retrieved passages:
{public_retrieved_context}

Do not include internal company names/details, internal risk findings, unapproved system details, or confidential implementation status.
Use an educational tone. Cite public sources when available.
Do not imply that a company is compliant or non-compliant. Do not invent legal claims.
Output a draft for human review, not a published post.
```
