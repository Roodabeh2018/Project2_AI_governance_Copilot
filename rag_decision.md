# rag_decision.md — RAG decision for AI Governance Copilot

## Decision
Use Retrieval-Augmented Generation (RAG) with a local vector store, top-k retrieval and source metadata for the MVP.

## Why RAG fits
The app needs to use both company-specific documents and public regulatory/framework references. It must retrieve relevant passages for a particular AI system or governance topic and cite where information came from. RAG allows a growing set of policies, inventories, risk assessments, technical documentation and public references to be searched without putting the entire corpus into every prompt.

## Alternatives considered
| Option | Pros | Cons |
|---|---|---|
| Put all knowledge directly into every prompt | Fastest setup for a tiny corpus | Poor scalability; repeated token cost; weak source selection and metadata filtering |
| Fine-tune a model | Could shape style | Does not keep changing company facts current or guarantee citations; too much for the timebox |
| RAG | Retrieves relevant source passages, supports citations and metadata filters | More setup; retrieval can miss evidence and needs testing |

## Criteria
1. Source traceability for each finding and generated claim.
2. Ability to separate company-specific and public regulatory knowledge.
3. Visibility filtering for public versus internal content.
4. Ability to update and re-index documents.
5. Two-day timebox and €5 API limit.

RAG is selected because traceability and metadata filtering matter to the use case. Keep the implementation minimal.

## Pipeline
1. Load Markdown/PDF files.
2. Parse text and document metadata.
3. Split into chunks while retaining source filename, section and visibility.
4. Build local TF-IDF vectors from chunks and store them in a JSON vector index.
5. Retrieve top-k chunks for the user's request, filtering by document visibility.
6. Pass the retrieved context and a reusable prompt template to the LLM.
7. Require source references, cautious language and placeholders for unknowns.
8. Save Markdown draft to `outputs/`.

## Fallback
Timebox RAG implementation. If the end-to-end flow is not working by the end of Day 1, use concise prepared summaries of the most important documents directly in the prompt and document the deviation here. Continue to deliver a working end-to-end pipeline. Do not let a UI block the core requirements.

## Limitations
- RAG can fail to retrieve relevant evidence.
- The MVP TF-IDF vectors are a lightweight lexical baseline, not semantic model embeddings.
- The index must be rebuilt after the source chunks change.
- A missing passage is not proof that a control does not exist.
- The supplied reference notes may not contain complete/current legal text.
- RAG is not a legal opinion or compliance certification.
- Human review remains mandatory.
