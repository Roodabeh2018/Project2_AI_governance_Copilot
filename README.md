# AI Governance Copilot

A short-course Python RAG prototype that helps an AI Governance / Risk analyst identify potential documentation gaps in a fictional organisation's supplied AI governance knowledge base and generate source-grounded draft documents and communications for human review.

## MVP
- Load the synthetic primary company documents and the official 144-page EU AI Act PDF.
- Accept optional user-uploaded internal documents into `primary` and public/reference documents into `secondary`.
- Retrieve source passages with metadata.
- Keep primary and secondary retrieval results separate and apply visibility filtering before prompt construction.
- Produce a cautious potential-gap summary.
- Generate at least one governance document draft (recommended: AI System Monitoring Plan).
- Generate an internal update using a second prompt template.
- Optional if time allows: a public LinkedIn-style post based only on public-tagged sources.
- Save Markdown drafts under `outputs/`.

## Data
All company documents are synthetic. Do not add confidential real company data. The official EU AI Act PDF is the baseline regulatory source for the MVP. Supporting notes are not authoritative legal text.

## Setup outline
1. Create/activate a Python virtual environment.
2. Install the packages chosen by the team and record them in `requirements.txt`.
3. Copy `.env.example` to `.env` and add API keys locally if needed. Never commit `.env`.
4. Place company documents in `knowledge_base/primary/`.
5. Keep the official EU AI Act PDF in `knowledge_base/secondary/eu_ai_act/`.
6. Place optional user-uploaded public/reference documents in `knowledge_base/secondary/`.
   Article/Annex Markdown replaces the official PDF only when
   `knowledge_base/secondary/eu_ai_act/.replace_official_pdf` exists; ordinary
   uploads remain additive.
7. Run the ingestion/indexing flow, then generate a draft using the CLI.
   The index is stored in `cache/vectors.npy` with its vector-to-chunk mapping
   in `cache/metadata.json`; reload it with `load_index(CACHE_DIR)` from
   `src.indexing`.
8. Review citations, placeholders and output status before presenting.

## Suggested demo
Ask what evidence exists for monitoring of a fictional AI system; show retrieved passages and a potential gap; generate an AI System Monitoring Plan with placeholders for unknowns; generate a short internal update. Explain that the result is a draft and not a compliance determination.
