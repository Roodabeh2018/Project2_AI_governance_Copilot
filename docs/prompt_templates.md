# Prompt Templates — AI Governance Copilot

## Shared system instructions
Follow `AGENTS.md` and `docs/shared_engineering_contract.md`. Use only retrieved evidence. Cite source filename, section, page or article where available. Do not invent facts or legal conclusions. Use placeholders for unknowns. Label every generated document `Draft — human review required`.

## Template 1 — `governance_document`
Dynamic inputs:
- `{document_type}`
- `{ai_system}`
- `{selected_findings}`
- `{primary_context}`
- `{secondary_context}`
- `{output_visibility}`

Prompt:
```text
Draft a {document_type} for {ai_system} using only the evidence supplied below.

Selected potential findings:
{selected_findings}

Retrieved primary/internal context:
{primary_context}

Retrieved secondary/public context:
{secondary_context}

Output visibility:
{output_visibility}

Requirements:
- Mark the output "Draft — human review required".
- Use source-supported company facts only.
- Cite the source filename and section/page/article for material claims.
- Keep primary and secondary evidence clearly distinguishable.
- Clearly separate documented facts from proposed recommendations.
- Do not invent owners, dates, versions, classifications, frequencies, thresholds, approvals or test results.
- Put unknown information in explicit placeholders such as [OWNER TO CONFIRM].
- Include an evidence/source register, open questions and a blank human approval block.
- Do not claim legal non-compliance based only on missing evidence.
- Do not claim that generating this draft closes the gap or proves implementation.
```

## Template 2 — `internal_update`
```text
Write a concise internal AI governance update about {topic}.

Use only these retrieved contexts:
Primary context:
{primary_context}

Secondary context:
{secondary_context}

Include:
- What the supplied documents currently say.
- Potential documentation/evidence gaps, phrased cautiously.
- Proposed next steps and known owners only if sourced.
- Open questions and decisions needed.
- Source citations.
- A clear distinction between evidence_found, evidence_incomplete and evidence_not_found.

Do not invent facts or make a legal compliance determination. Label the output "Draft — human review required".
```

## Optional Template 3 — `linkedin`
```text
Write a short, professional LinkedIn post about {topic} for a general AI governance audience.

Use only public-tagged passages from the secondary context:
{secondary_context}

Do not include internal company names, internal risk findings, unapproved system details or confidential implementation status.
Do not imply that a company is compliant or non-compliant. Do not invent legal claims.
Output a draft for human review, not a published post.
```
