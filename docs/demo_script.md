# Presentation and Demo Script — about 8 minutes

- **Live app:** https://project2-ai-governance-copilot.onrender.com/ (login shared privately in the team). The free plan sleeps after 15 minutes, so **open it 10 minutes before**.
- **Plan B:** `python -m src.app` locally; or show the saved outputs in `docs/evidence/`.
- **Speakers:** a suggested split; change it as the team prefers.
- **Setup:** `main` at the presented commit, index built (`python -m src.build_index`), `LLM_PROVIDER=openai`.

## Part 1 — Project structure (about 3 min, slides)

| Time | Who | Topic | What to say | Evidence |
|---|---|---|---|---|
| 0:00–0:30 | All | Problem and user | AI governance evidence is spread across policy, inventory, risk assessment, oversight procedure and validation report. Our user is an AI governance / risk analyst who needs a first draft they can check. | `PROJECT_BRIEF.md` §4 |
| 0:30–1:00 | Armin | **Quality / Time / Cost** | Quality: every claim traceable to a source, no invented values, public outputs never use internal sources, human review. Time: two build days, one end-to-end flow before extras. Cost: €5 API cap, gpt-4o-mini, embeddings built once and cached, free mock mode for tests. | `project_structure.md` §1 |
| 1:00–1:20 | Armin | **Stakeholders** | Builders, instructor, the fictional Head of AI Governance (final say on approval), system owners, compliance reviewers/auditors, the LLM provider (cost). | `project_structure.md` §2 |
| 1:20–1:45 | Murat | **Top risk** | The biggest risk is the AI inventing a requirement or stating a compliance verdict. Mitigation: retrieval-grounded citations, the *insufficient source* stop, a hard verdict check and human approval. The other two risks were public leakage and RAG blocking the demo. | `project_structure.md` §5 |
| 1:45–2:15 | Murat | **RAG decision** | We chose RAG over “everything in the prompt” and fine-tuning, because we need traceable sources, separate company vs. regulation knowledge, and visibility filtering. Two knowledge bases with separate top-k, so the 144-page Act never crowds out the 9 company documents. | `rag_decision.md`, `project_structure.md` §7 |
| 2:15–3:00 | Roodi | **WBS → board** and **Day 1 → Day 2 Kanban** | 5 WBS packages → 14 Trello cards → Must IDs M1–M8, three colors along the pipeline. Show the mid-project board, then the final board with all 14 cards in Done. Be honest: at one point three cards were in progress under a WIP limit of 2. | `project_structure.md` §6, §7a; `docs/screenshots/` |

## Part 2 — Live demo (about 4 min)

| Time | Who | What to show | What to say |
|---|---|---|---|
| 3:00–3:30 | Armin | `knowledge_base/primary/` (front matter with `visibility`) and the EU AI Act PDF | All company data is fictional; the regulation is the official text. 491 chunks with source, section/page and visibility. |
| 3:30–5:00 | Roodi | App tab **1 · Generate & review** → Governance document, Internal, Credit Decision Support AI, AI System Monitoring Plan → **Generate draft** | Point at: status badge and disclaimer; *Evidence Incomplete or Not Found* with `[P#]` company citations; `[S#]` EU AI Act citation with page; placeholders such as `[OWNER TO CONFIRM]`; retrieved sources table; automatic checks. “Not documented in the supplied sources” is a potential gap, not a compliance verdict. |
| 5:00–5:40 | Roodi | Switch to **Internal update** → Generate → reviewer name → **Approve** → tab **3 · Gap register** | Only a named human can approve, and only valid findings with supplied sources change the register. *Complete* means approved evidence was found, not legal compliance. |
| 5:40–6:10 | Murat | **Public** output, then AI system **AI-99** | Public output receives only public chunks. An unknown system gives *insufficient source*. That does not prove that the system doesn't exist. |
| 6:10–6:30 | Murat | Tab **2 · Upload documents** (explain only) | Primary = internal company documents, Secondary = public sources; upload rebuilds the index; a new regulation sets complete items to re-check. |

## Part 3 — Uniqueness and lessons (about 1 min)

| Time | Who | What to show | What to say |
|---|---|---|---|
| 6:30–7:15 | Roodi | `docs/uniqueness_comparison.md` | Same request to ChatGPT and to our copilot. ChatGPT gives a solid generic proposal, with proposed thresholds and assumed roles. Our copilot reports what Northstar’s own documents record and what is not documented in them, cites the EU AI Act page, and leaves unknown values as placeholders for the owner. |
| 7:15–8:00 | All | Lessons | A shared engineering contract let three people build in parallel. Every change went through a reviewed pull request, and every review finding became a regression test (143 tests, mock mode, no API cost). In governance, a placeholder is more honest than a confident guess. |

## Likely questions
- **Why RAG, not just ChatGPT?** Traceability to company files, visibility filtering, and placeholders instead of assumed values (`rag_decision.md`).
- **Is this a compliance assessment?** No. It drafts documents for human review and never declares compliance or non-compliance.
- **Is the vector store a database?** No, a local NumPy index (`cache/vectors.npy`). That's enough for a 491-chunk prototype and matches `rag_decision.md`.
- **What did it cost?** gpt-4o-mini drafts cost a fraction of a cent each; embeddings are built once and cached (budget €5).
- **How did you use agents?** `AGENTS.md` rules are part of every prompt and guided our code changes; see `docs/agent_usage.md`.
