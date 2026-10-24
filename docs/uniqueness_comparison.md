# Uniqueness Comparison — AI Governance Copilot vs. generic ChatGPT

Requirement **M7**: *actual side-by-side output shows at least 3 supplied-company-specific facts with citations, when using internal context.*

This file has two parts. **Part 1** is the final run with the integrated RAG pipeline, using company context and EU AI Act context. **Part 2** keeps the first comparison from 23 Oct, which used the legacy keyword retrieval, as history. The ChatGPT baseline is the same in both parts.

## Part 1 — Final run with the integrated RAG pipeline (24 Oct 2026)

### Run record

| | Generic baseline | AI Governance Copilot |
|---|---|---|
| Date | 23 Oct 2026 | 24 Oct 2026, 15:32 (CEST) |
| System / commit | ChatGPT (chatgpt.com), no files attached | `main` at **`913961c`** (Colors A + B + C integrated; vector index from PR #12) |
| Model | ChatGPT web (model not recorded) | Generation `gpt-4o-mini` (temperature 0.2); embeddings `text-embedding-3-small`; top-k 3 Primary + 3 Secondary, minimum score 0.35 |
| Index | — | Rebuilt before the run with `python -m src.build_index` |
| Command | Prompt below | `python -m src.pipeline --type governance_document --document "AI System Monitoring Plan" --topic "monitoring and human oversight" --no-review` |
| Full output | `docs/comparison/chatgpt_baseline.md` (original `.docx`) | `docs/evidence/2026-10-24/internal_monitoring_plan.md` |
| Further outputs, same commit | — | `internal_update.md` (internal update), `public_monitoring_plan.md` (public output), in `docs/evidence/2026-10-24/` |

Prompt given to ChatGPT; the same task is given to the Copilot through the template:

```
Draft an AI System Monitoring Plan for the AI system "Credit Decision Support AI"
at Northstar Digital Bank, based on the EU AI Act. Cite your sources.
```

### What changed compared with 23 Oct
The Copilot now receives **both** knowledge bases. The draft's Source Register lists 3 company documents and 3 chunks of the official EU AI Act PDF. It cites `[S1]` = Article 14, page 60, which was actually supplied. All automatic checks passed. On 23 Oct no regulation chunks were retrieved, and the validator flagged an unsupplied `[S1]`.

### Verified company-specific facts (Copilot only)
Checked by hand against `knowledge_base/primary/`. “Not documented” means **not documented in the supplied sources** (AGENTS.md rule 4).

| # | Statement in the Copilot output | Label | Verified in |
|---|---|---|---|
| 1 | Business owner, technical owner, model/version identifier, AI risk classification and rationale, monitoring owner, last review date and incident contact are not recorded; shown as placeholders | [P1] | `ai_system_inventory.md`: these fields are `[NOT RECORDED]` |
| 2 | The system supports analysts reviewing credit applications | [P1] | `ai_system_inventory.md`: “Purpose: supports analysts reviewing credit applications” |
| 3 | No monitoring schedule, metrics or escalation thresholds are documented | [P2] | `monitoring_notes.md`: “No approved monitoring schedule … does not define monitoring frequencies, metrics or escalation thresholds” |
| 4 | Proposed monitoring topics: performance, input-data drift, data quality, outcome differences, overrides, complaints, incidents, material changes | [S1] in the draft; content from [P2] | `monitoring_notes.md` lists exactly these as “suggestions for the document author to review” |
| 5 | *(internal update)* The system is recorded as in production; the technical documentation is incomplete | [P1], [P3] | `ai_system_inventory.md` (“in production in this synthetic scenario”); `technical_documentation_credit_support.md` (“Missing or unlinked details”) |

### Verified regulatory citations
Checked by opening the cited page of `knowledge_base/secondary/eu_ai_act/eu_ai_act_official.pdf`.

| Citation | Used for | Check |
|---|---|---|
| Article 14, page 60 | Human oversight; monitoring owner and review cycle | ✅ Article 14 (Human oversight) starts on page 60 |
| Annex III, page 127 | *(internal update)* creditworthiness systems are high-risk | ✅ Annex III point 5(b): “AI systems intended to be used to evaluate the creditworthiness of natural persons or establish their credit score” |
| Recitals, page 16 | *(internal update)* same statement | ✅ the page discusses creditworthiness and credit scores |
| Article 72, page 101 | *(public output)* post-market monitoring | ✅ Article 72 is on page 101 |
| Regulation title chunk, page 21 | *(monitoring plan)* “Roles (implements [S2])” | ⚠️ weak: a broad chunk, not a specific requirement for roles; a reviewer should replace it |

### Result
**M7 is met with the final pipeline.** The Copilot output has at least 4 verified company-specific facts with citations, plus verified EU AI Act citations with page numbers. ChatGPT, without company documents, gives a generic proposal with stated assumptions (see Part 2). Unknown values stay as placeholders.

### Honest limitations of the final run
1. **Placeholder types:** 8 of 11 gap bullets use the right placeholder type. Model/version, risk classification and rationale use `[OWNER TO CONFIRM]` where `[EVIDENCE TO PROVIDE]` fits better. The validator only checks schedule/criterion bullets, so it did not flag these.
2. **One weak regulatory citation:** “Roles (implements [S2])” cites the regulation's title chunk.
3. **Internal update over-states one gap:** it marks HUM-01 “Human oversight procedure not documented”, cited to the inventory. But `human_oversight_procedure.md` exists as an incomplete draft and was not among the top-3 retrieved chunks. It also omits TEST-03. This is why approval is manual and the gap register validates findings: a reviewer must correct HUM-01 to `evidence_incomplete` before approving.
4. **Request fields in public output:** `public_monitoring_plan.md` uses only public chunks: `company_profile.md`, `comms_guidelines.md` and EU AI Act chunks. Its title still contains the system name from the request field (see `docs/public_leakage_test.md`, request-field limitation).

---

## Part 2 — First comparison (23 Oct 2026, legacy retrieval, kept as history)

Requirement **M7**: *actual side-by-side output shows at least 3 supplied-company-specific facts with citations, when using internal context.*

Both runs were made on **23 Oct 2026** with the same request. The full outputs are kept below, not summarised from memory.

| | Generic baseline | AI Governance Copilot |
|---|---|---|
| System | ChatGPT (chatgpt.com), no files attached | `python -m src.pipeline --type governance_document` (gpt-4o-mini, `LLM_PROVIDER=openai`), code at PR #13 branch commit `e2acabe` (main `5da8697` + Color C follow-up fixes) with the legacy Color B retrieval, before PR #12 |
| Input | Prompt only | Same task + retrieved Northstar Primary chunks (Color A ingestion → Color B retrieval → Color C prompt) |
| Full output | `docs/comparison/chatgpt_baseline.md` (original: `chatgpt_baseline.docx`) | `governance_document_20261023_1432.md` (local `outputs/`, not committed; excerpts below) |
| Second output | — | `internal_update_20261023_1438.md` (local `outputs/`, not committed) |

### Test prompt

```
Draft an AI System Monitoring Plan for the AI system "Credit Decision Support AI"
at Northstar Digital Bank, based on the EU AI Act. Cite your sources.
```

### The actual distinction

ChatGPT had **no access to Northstar's documents**, and it says so. It writes a *generic proposal*: it calls its plan "a deployer-side operating plan and a proposed control framework". It labels its thresholds "proposed starting triggers for internal calibration; they are not numerical limits set by the EU AI Act". It also states its assumptions, e.g. "Role assumption: Northstar is the deployer; a third-party vendor is the provider". These are reasonable generic proposals. They are **not false claims about existing Northstar controls**.

The Copilot answers a different question: **what do the supplied Northstar documents actually record, and what is not documented in them?** It cites each statement to a company file and leaves every value the documents do not give as a placeholder for the accountable owner to fill in.

### Result summary

| Criterion | Generic ChatGPT | AI Governance Copilot |
|---|---|---|
| Basis | General knowledge + public law; explicit assumptions about Northstar | Supplied Northstar documents (retrieved chunks) |
| Company-specific facts from Northstar's documents | **0**, because it had no company documents | **22 cited gap statements** from 3 company documents (examples below) |
| Citations | 3 external sources (EUR-Lex AI Act, GDPR, EBA guidelines), at section level | Every bullet carries a `[P#]` label; the Source Register maps each label to file, section and visibility |
| Owners, thresholds, cadences | **Proposed generic values** for Northstar to calibrate (e.g. "proposed PSI >0.20", ">10% relative deterioration for 2 periods", monthly/quarterly reviews, eight role groups), clearly marked as proposals | **Placeholders** where the documents give no value: `[OWNER TO CONFIRM]`, `[MONITORING FREQUENCY TO CONFIRM]`, `[THRESHOLD TO CONFIRM]`, `[DATE TO COMPLETE]`, `[EVIDENCE TO PROVIDE]` |
| Current state vs. target state | Describes a target-state plan; cannot say what Northstar already has | Separates *Evidence Found* from *Evidence Incomplete or Not Found in the supplied documents*; overall status `evidence_incomplete` |
| Compliance wording | Cautious ("not legal advice") | No compliance verdict; explicit verdicts are rejected by an automatic check (PR #13) |
| Human review | Free-text note | Mandatory `Status: Draft — human review required`, review checklist and approval block; nothing is approved automatically |
| Self-checking | None | Automatic checks flagged 2 issues in this run (see limitations) |
| Memory across runs | None | Approved internal updates feed the **gap register** (open / complete / re_check per requirement) |
| Regulatory depth | **Stronger**: Art. 25–27, 72–73, Annex III 5(b), GDPR Art. 22/35, EBA guidelines | Weaker in this run: no EU AI Act `[S#]` context was retrieved (see limitations) |

### At least 3 company-specific, cited facts only the Copilot produced

Each statement was checked against the source file in `knowledge_base/primary/`. "Not documented" means **not documented in the supplied sources**. It does not mean the control does not exist at Northstar (AGENTS.md rule 4).

| # | Statement in the Copilot output | Label | Source file (verified) |
|---|---|---|---|
| 1 | The oversight procedure describes analysts reviewing outputs, but does not document measurable error/uncertainty criteria for escalation, an escalation response time, or a procedure for restricting or disabling the system | [P1] | `human_oversight_procedure.md` |
| 2 | Business owner, technical owner, monitoring owner, incident contact and monitoring schedule are recorded as `[NOT RECORDED]` in the inventory entry | [P3] | `ai_system_inventory.md` |
| 3 | The validation report does not document the model/version tested, acceptance thresholds, subgroup/fairness analysis, robustness testing or independent sign-off | [P2] | `testing_validation_report.md` |
| 4 | No approved monitoring schedule is included in the supplied documents; monitoring frequencies, metrics and escalation thresholds are not defined there | [P2] in the internal update | `monitoring_notes.md` |

The ChatGPT baseline cannot contain these statements because it had no company documents. Where the Copilot shows an empty, owner-assigned placeholder, ChatGPT shows a generic proposal. That proposal may be useful as a starting point. It cannot tell the reviewer what Northstar has already documented.

### Excerpts side by side

**Ownership**

> **ChatGPT:** "Credit Risk / Model Risk: Owns credit outcome monitoring, validation, benchmark comparison, overrides, drift review, and model approval." *(one of eight proposed role groups)*
>
> **Copilot:** "Business owner: [OWNER TO CONFIRM] [P3]. Technical owner: [OWNER TO CONFIRM] [P3]. Monitoring owner: [OWNER TO CONFIRM] [P3]."

**Thresholds**

> **ChatGPT:** "Thresholds below are proposed starting triggers for internal calibration; they are not numerical limits set by the EU AI Act … material population shift (proposed PSI >0.20)"
>
> **Copilot:** "Acceptance thresholds: [THRESHOLD TO CONFIRM] [P2]." / "Proposed: review every [MONITORING FREQUENCY TO CONFIRM]; escalate within [THRESHOLD TO CONFIRM]."

**What is known about the system**

> **ChatGPT:** "Role assumption: Northstar is the deployer; a third-party vendor is the provider. Confirm this against the contract…"
>
> **Copilot:** "The Credit Decision Support AI supports analysts in reviewing credit applications. [P3]"

### Honest limitations of this run

1. **No regulatory context.** At the time of the run, Color B's legacy retrieval read only the secondary reference notes, which Color A deliberately excludes from the baseline knowledge base. It did not search the EU AI Act PDF, so the Copilot draft received no `[S#]` chunks. The model still wrote "implements [S1]", and the automatic check caught it: *"Cites sources that were not supplied: S1"*. PR #12 (Color B vector index) fixed this; the repeated run is Part 1.
2. **Placeholder type.** The second automatic check flagged one gap bullet that uses `[OWNER TO CONFIRM]` for a criterion, where `[THRESHOLD TO CONFIRM]` was expected.
3. **Limited retrieval.** With top-k = 3, the internal update marked some requirements `evidence_not_found` (e.g. GOV-04 cited to `human_oversight_procedure.md`) even though `ai_system_inventory.md` is in the knowledge base. A human reviewer must check these statuses before approval. That is why approval is manual and the gap register only changes after validation.
4. ChatGPT gives a broader **regulatory** structure and a more complete generic target-state plan. The Copilot's value is **company-specific, traceable evidence with placeholders instead of proposed values**, not broader legal knowledge.

### Conclusion

M7 is met: the Copilot output contains **4 verified, cited, company-specific statements** that a generic model without the company documents cannot produce. It also keeps every value not given in the documents as a placeholder for the owner. ChatGPT's output is a generic proposal with stated assumptions. The two are complementary. The weakness in regulatory grounding was fixed by PR #12 (see Part 1).
