# AI Governance Copilot — Project Brief and Requirements

## 1. Project identity
- **Project name:** AI Governance Copilot
- **Course:** Ironhack Project 2 — AI Content Creator / Python integration project
- **Project type:** R&D prototype using Python and Retrieval-Augmented Generation (RAG)
- **Team:** 3 people
- **Timebox:** Two build days; presentation Monday afternoon
- **API budget:** Maximum €5
- **Data:** Synthetic company documents plus selected official/public regulatory references. Never use real confidential company documents.

## 2. Core idea
Build a Python application that reviews a fictional organisation's AI governance documentation and selected public regulatory/framework references. It identifies potential documentation or evidence gaps in the supplied knowledge base, then generates useful first-draft documents or updates to help address those gaps. The same pipeline can also generate source-cited communications such as internal governance updates and LinkedIn-style posts, using different prompt templates for different audiences.

The application is a **documentation and content-generation copilot**, not an autonomous compliance assessor. It must not declare legal non-compliance simply because a document or evidence item was not found.

## 3. One-sentence goal
Build a Python RAG app that uses a fictional company's AI governance documentation and public reference material to generate evidence-grounded drafts of missing or incomplete AI governance documents, plus source-cited internal updates and public-facing posts, with human review before use.

## 4. Problem and intended user
AI governance work often requires connecting policies, AI system inventories, risk assessments, technical documentation, human-oversight procedures, testing evidence and regulatory expectations. These materials may be incomplete or spread across different files. Teams need help spotting where documentation is incomplete and creating a structured first draft for review.

**Primary user:** AI Governance, Operational Risk, Technology Risk or Compliance analyst.

**User story:** “When I review the documentation for an AI system, I want the assistant to show evidence-backed potential documentation gaps and generate a draft document or update that helps address them, so I can review and complete it instead of starting from a blank page.”

## 5. Core workflow
1. Load internal/company documentation and public regulatory/framework references from separate knowledge-base folders.
2. Parse files and preserve source metadata.
3. Chunk documents, create embeddings and store chunks in a local vector index.
4. Retrieve relevant passages for the user's question or selected potential gap.
5. Generate an evidence-backed finding, clearly distinguishing existing evidence from missing evidence and recommendations.
6. Recommend a suitable document to create or update.
7. Generate a document draft from retrieved evidence and a reusable prompt template.
8. Mark unknown facts as placeholders rather than inventing them.
9. Save the result as Markdown under `outputs/`.
10. A human reviews, edits and approves or rejects the draft.

## 6. Main output types
### A. AI governance gap summary
A concise report containing:
- AI system / topic
- Potential documentation gap
- Evidence found in supplied documents
- Source filename and section for each material claim
- Evidence status: `Evidence found`, `Evidence incomplete`, or `Evidence not found in supplied documents`
- Suggested document or update
- Recommended next steps
- Open questions and human-review status

### B. Generated missing document or update
The MVP should generate at least one useful document type, preferably an **AI System Monitoring Plan**. If time permits, support a second type such as an AI Risk Assessment update or Human Oversight Procedure.

Other possible draft types include:
- AI Governance Policy
- AI System Inventory entry
- AI Risk Assessment
- Technical Documentation section
- Human Oversight Procedure
- AI Incident Response Procedure
- Testing and Validation Plan
- AI System Monitoring Plan

The generator should create a *draft*, not claim the document is approved or that the control has been implemented.

### C. Content-generation outputs
To retain the course's AI content creator requirements, the same pipeline should support at least two reusable content templates:
- `governance_document` — drafts a missing or incomplete governance document.
- `internal_update` — creates a concise internal update on the gap, proposed remediation and next steps.
- Optional `linkedin` — creates a public-facing post about a general AI governance lesson using public sources only, without exposing internal company details.

### D. Review-ready Markdown file
Every generated output should include title, draft status, source references, assumptions/placeholders, open questions and a human-review checklist. Save it under `outputs/`.

## 7. Important distinction
“Evidence not found in the supplied documents” does **not** mean “the company does not have this control” and does not prove legal non-compliance. The system reports a potential documentation/evidence gap for human review. Creating a draft document does not close a finding; closure requires human confirmation and evidence that the relevant control or process is implemented.
