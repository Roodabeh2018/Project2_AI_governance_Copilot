# Demo Script — 5 Minutes

**Prerequisites:** PR #12 (Color B vector index) and PR #13 (Color C checks) merged into `main`. Without PR #12 there is no EU AI Act context and public output returns *insufficient source*; without PR #13 the approval validation shown at 2:40 is not in place.

**Setup before the demo:** `conda activate bootcamp-env`, project folder open, `.env` with `LLM_PROVIDER=openai`, index built (README step 3), `python -m src.app` running at http://127.0.0.1:7860.
**Backup if the API fails:** set `LLM_PROVIDER=mock` and tick *"Use sample context"* in the app, or open the saved outputs listed below.

| Time | Who | What to show | What to say |
|---|---|---|---|
| 0:00–0:40 | Color A | `knowledge_base/primary/` (9 synthetic Northstar documents, front matter with `visibility`) and `knowledge_base/secondary/eu_ai_act/eu_ai_act_official.pdf` | "AI governance evidence is spread across policy, inventory, risk assessment, oversight procedure and validation report. All company data is fictional; the regulatory baseline is the official 144-page EU AI Act." |
| 0:40–1:20 | Color B | `python -m src.kb_validation`, then the retrieved sources table in the app | "Primary and Secondary are retrieved separately with their own top-k, so regulation never crowds out company evidence. Every chunk keeps file, section/page and visibility." |
| 1:20–2:40 | Color C | App tab **1 · Generate & review** → *governance_document*, "AI System Monitoring Plan", internal → **Generate** | Point at: `Status: Draft — human review required`; *Evidence Incomplete or Not Found* with `[P#]` citations; placeholders `[OWNER TO CONFIRM]`, `[THRESHOLD TO CONFIRM]`; Source Register; Automatic checks. "Not found in the supplied documents is a potential documentation gap, not proof that a control is missing, and not a compliance verdict." |
| 2:40–3:20 | Color C | Switch to *internal_update* → **Generate** → enter reviewer name → **Approve** → tab **3 · Gap register** | "Only a human approval updates the register, and only when every finding is backed by a supplied source. Uploading a new regulation sets complete items back to *re_check*." |
| 3:20–3:50 | Color C | Visibility → *public* → **Generate** (or show `docs/public_leakage_test.md`) | "Public output only ever sees public-tagged chunks. Internal facts are removed before the prompt is built. If nothing public is left, we answer *insufficient source*." |
| 3:50–4:10 | Color C | AI system → `AI-99` → **Generate** | "An unknown system gives *insufficient source* instead of an invented answer." |
| 4:10–4:50 | All | `docs/uniqueness_comparison.md` side by side with ChatGPT | "Without our documents, ChatGPT can only propose a generic framework, with proposed thresholds such as PSI > 0.20 and assumed roles. The Copilot reports what Northstar's own documents record and what is not documented in them, with 22 cited statements, and leaves unknown values as placeholders for the owner." |
| 4:50–5:00 | All | Trello board (Day 1 / Day 2 screenshots) | Lessons learned: shared contract + fixtures let three people build in parallel; PR reviews caught real safety bugs (visibility, gap register validation). |

## Saved outputs to fall back on
- `outputs/governance_documents/governance_document_20261023_1432.md`: monitoring plan, internal
- `outputs/internal_updates/internal_update_20261023_1438.md`: internal update with findings JSON
- `outputs/governance_documents/governance_document_20261023_1441.md`: public output (leakage test Run B)

## Likely questions
- **Why RAG, not just ChatGPT?** Traceability to company files, visibility filtering, and placeholders instead of assumed values. See `rag_decision.md`.
- **Is this a compliance assessment?** No. It drafts documents for human review and never declares compliance or non-compliance.
- **What did it cost?** gpt-4o-mini drafts cost a fraction of a cent each; embeddings are built once and cached (budget €5).
