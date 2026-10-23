# AI Governance Copilot

A short-course Python RAG prototype that helps an AI Governance / Risk analyst identify potential documentation gaps in a fictional organisation's supplied AI governance knowledge base and generate source-grounded draft documents and communications for human review.

## MVP
- Load primary company documents and secondary public regulatory/framework references.
- Retrieve source passages with metadata.
- Produce a cautious potential-gap summary.
- Generate at least one governance document draft (recommended: AI System Monitoring Plan).
- Generate an internal update using a second prompt template.
- Optional if time allows: a public LinkedIn-style post based only on public-tagged sources.
- Save Markdown drafts under `outputs/`.

## Data
All company documents are synthetic. Do not add confidential real company data. Regulatory reference notes should be supplemented with official texts from EUR-Lex, BaFin and EBA before relying on specific legal claims.

## Setup outline
1. Create/activate a Python virtual environment.
2. Install the packages chosen by the team and record them in `requirements.txt`.
3. Copy `.env.example` to `.env` and add API keys locally if needed. Never commit `.env`.
4. Place company documents in `knowledge_base/primary/`.
5. Place public regulatory/framework references in `knowledge_base/secondary/`.
6. Run `python -m src.indexing`. If `cache/chunks.jsonl` does not exist yet,
   the command creates section-sized chunks from the supplied Markdown files,
   validates them, and builds the local index. Retrieval uses the saved index
   when it exists; otherwise it uses the lightweight Markdown keyword fallback.
7. Review citations, placeholders and output status before presenting.

The local index uses TF-IDF vectors and cosine similarity. It runs offline and
does not require a paid embedding API; it is a lightweight lexical baseline,
not a semantic language-model embedding.

## Suggested demo
Ask what evidence exists for monitoring of a fictional AI system; show retrieved passages and a potential gap; generate an AI System Monitoring Plan with placeholders for unknowns; generate a short internal update. Explain that the result is a draft and not a compliance determination.
