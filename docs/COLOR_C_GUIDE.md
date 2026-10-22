# Color C — step-by-step (Roodi)

Your track: **prompts → LLM → pipeline → Gradio**, plus the **gap register** (card 16).
Everything below follows the Shared Engineering Contract (file names, models, enums, errors).
The code is written and tested offline (5/5 tests pass with the mock LLM). Your job: run it, verify each card, improve it with your coding agent, commit, move the card.

## Your files

| File | Contract | Owner |
|---|---|---|
| `src/contracts.py` | §4 models, §9 errors (+ small JSON helpers) | **shared — commit 1** |
| `src/config.py` | §8 `AppConfig`, env vars | **shared — commit 1** |
| `src/prompts.py` | §5.3 `build_prompt(request) -> str` | C |
| `src/llm_generator.py` | §5.3 `generate_text(prompt)`, `generate_draft(request)` | C |
| `src/pipeline.py` | §5.4 `run_pipeline(request) -> GeneratedDraft` + CLI | C |
| `src/app.py` | Gradio | C |
| `src/gap_register.py` + `data/requirements_checklist.json` | card 16 (not in the contract yet — tell the team) | C |
| `tests/test_pipeline.py` | §2 test file | C |
| `tests/fixtures/*` | §10 shared fixtures (built from our real documents) | **shared — commit 1** |

---

## Step 0 · Setup (10 min)

```bash
git pull origin main
git checkout -b color-c
python -m venv venv
source venv/bin/activate                 # Windows: venv\Scripts\activate
pip install openai python-dotenv gradio numpy pytest
cp .env.example .env                     # paste your OPENAI_API_KEY
```
Copy the files from this pack into the repo (same paths).

**Check first:** does `src/contracts.py` already exist in the repo (from A or B)?
- **No** → commit ours as *commit 1: shared contracts and fixtures* and tell A + B in Slack.
- **Yes** → keep theirs. Compare field names with ours; copy only the helper functions at the bottom of our file (`to_dict`, `retrieval_context_from_dict`, `generation_request_from_dict`).

```bash
git add src/contracts.py src/config.py tests/fixtures .env.example
git commit -m "Shared contracts, config and fixtures (commit 1)"
git push -u origin color-c
```
Slack: *"Shared contracts + fixtures pushed on color-c — please pull before coding."*

---

## Step 1 · Card 11 — prompt templates (20 min)

```bash
LLM_PROVIDER=mock python tests/test_pipeline.py
# Windows PowerShell: $env:LLM_PROVIDER="mock"; python tests/test_pipeline.py
```
**Verify:** 5 × PASS. Then open `src/prompts.py` and read:
- `GROUNDING_RULES` — the agents.md safety rules (citations, placeholders, no verdicts).
- Two templates: `governance_document` (e.g. AI System Monitoring Plan) and `internal_update` (gap update + findings JSON for the register).
- `[P#]` = primary evidence, `[S#]` = EU AI Act — kept in **separate slots** as the contract requires.

Agent prompt:
```
Read agents.md. Card: 11 Prompt contracts and templates — Must M5.
Review src/prompts.py against the Shared Engineering Contract §3.3 and §5.3.
Do not change function signatures. Run tests/test_pipeline.py and report.
```
Move card 11 → Review.

---

## Step 2 · Card 12 — LLM + CLI (today, before 18:00 = milestone)

**2a. Offline (free):**
```bash
LLM_PROVIDER=mock python -m src.pipeline --type governance_document --fixture tests/fixtures/sample_retrieved_context.json --no-review
```
→ file in `outputs/governance_documents/governance_document_YYYYMMDD_HHMM.md`

**2b. Real LLM, still with the fixture** (costs < 1 cent):
```bash
python -m src.pipeline --type governance_document --fixture tests/fixtures/sample_retrieved_context.json
```
Read the draft, then answer: `f` → type feedback (e.g. *"shorter purpose section"*) → it regenerates → `s` to save.

**Verify (write the answers in the Trello card):**
- [ ] `Status: Draft — human review required` under the title
- [ ] every claim cites `[P#]` or `[S#]`; Source Register at the end
- [ ] unknown owner/frequency/threshold = placeholder, **not invented**
- [ ] "Automatic checks" section says ✅ (or lists warnings)

**2c. Negative + error checks:**
```bash
python -m src.pipeline --type internal_update --fixture tests/fixtures/sample_retrieved_context_negative.json
# → **insufficient source** — AI system AI-99 not found …
```
Put a wrong key in `.env`, run 2b → *"The API key was rejected…"* (no crash). Restore the key.

**2d. Prompt iteration (graded: "iterative prompt engineering"):** if the real draft invents a value or misses a section, change the template wording, rerun, and write one line per change in `docs/prompt_templates.md` (what you changed, why, result).

Commit:
```bash
git add src/prompts.py src/llm_generator.py src/pipeline.py tests/test_pipeline.py
git commit -m "C: prompts, LLM generator, CLI pipeline (cards 11-12)"
git push
```
✅ **18:00 milestone** = 2b works. Post the output file in Slack.

---

## Step 3 · Integration with Color B (Friday morning, by 12:00)

When B pushes `src/retrieval.py` with `retrieve(...)` and `has_sufficient_source(...)`:
```bash
git pull origin main          # or merge B's branch
python -m src.pipeline --type governance_document --document "AI System Monitoring Plan" --topic "monitoring and human oversight"
python -m src.pipeline --type internal_update --topic "monitoring and human oversight"
python -m src.pipeline --type internal_update --system "AI-99" --topic "monitoring status"     # → insufficient source
python -m src.pipeline --type internal_update --topic "lessons on AI monitoring" --visibility public
```
**Verify:** real retrieval (no `--fixture`) → primary **and** secondary sources in the Source Register; public run → every source has visibility `public`.
If B's `retrieve()` returns something else than `RetrievalContext` → ask B to fix it to the contract, don't adapt your code.

---

## Step 4 · Card 16 — gap register (Friday, ~1 h)

The loop agreed with the teacher, as a rehearsal:
```bash
python -m src.pipeline --type internal_update --topic "monitoring and human oversight"   # approve: a + your name
python -m src.gap_register                                                              # MON-02 / HUM-01 = open
# Color A uploads the revised samples/monitoring_notes.md → A/B re-index
python -m src.pipeline --type internal_update --topic "monitoring"                      # approve again
python -m src.gap_register                                                              # MON-02 = complete
```
`data/gap_register.json` keeps the history (who approved what, when). Uploading a regulation in Gradio sets complete items to `re_check`.
Tell the team in Slack: *"gap_register.py + data/requirements_checklist.json are new files — please add them to the contract structure (§2)."*

---

## Step 5 · Card 13 — Gradio (Friday, after the CLI works)

```bash
python -m src.app        # http://127.0.0.1:7860
```
- **Tab 1:** tick *Use sample context* until B is merged → Generate → read the sources table → reviewer name → Approve.
- **Tab 2:** upload → file goes to `knowledge_base/primary|secondary/uploads/` → calls A's `load_documents/chunk_documents/save_chunks` and B's `build_index` (works automatically once their modules exist).
- **Tab 3:** gap register table.

**Verify:** approve without a name is blocked; an approved internal update changes Tab 3.

---

## Step 6 · Card 14 — evidence & demo (Friday 14:00–17:00, with Murat)

1. **ChatGPT comparison** — paste into chatgpt.com (no files):
   ```
   Draft an AI System Monitoring Plan for the AI system "Credit Decision Support AI"
   at Northstar Digital Bank, based on the EU AI Act. Cite your sources.
   ```
   Put both full outputs side by side in `docs/uniqueness_comparison.md` → list ≥ 3 company-specific cited facts only ours has (e.g. "no approved monitoring schedule [P2]") + placeholders instead of invented values + gap register memory.
2. **Public leakage test** → save the public run from step 3 as `docs/public_leakage_test.md`.
3. README "How to run" + Day 2 Trello screenshot.

---

## Timeline

| When | Card | Done when |
|---|---|---|
| Today → 17:00 | 0 + 11 | contracts committed, 5 tests pass |
| Today → 18:00 | 12 | real LLM draft from fixture saved ✅ milestone |
| Fri 09:00–12:00 | integration | real two-KB CLI run with B |
| Fri 12:00–13:00 | 16 | register loop works |
| Fri 13:00–14:00 | 13 | Gradio 3 tabs |
| Fri 14:00–17:00 | 14 | comparison, leakage test, README, demo |

**Agent rule for every session:** `Read agents.md. Card: <nr + title> — Must <ID>. Inspect first, short plan, focused change, run tests/test_pipeline.py, report files changed + result.`
