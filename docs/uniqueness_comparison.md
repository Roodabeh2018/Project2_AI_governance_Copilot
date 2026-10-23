# Uniqueness Comparison — AI Governance Copilot vs. generic ChatGPT

Requirement **M7**: *actual side-by-side output shows at least 3 supplied-company-specific facts with citations, when using internal context.*

Both runs were made on **23 Oct 2026** with the same request. Full outputs are kept, not summarised from memory.

| | Generic baseline | AI Governance Copilot |
|---|---|---|
| System | ChatGPT (chatgpt.com), no files attached | `python -m src.pipeline --type governance_document` (gpt-4o-mini, `LLM_PROVIDER=openai`) |
| Input | Prompt only | Same task + retrieved Northstar Primary chunks (Color A ingestion → Color B retrieval → Color C prompt) |
| Full output | `docs/comparison/chatgpt_baseline.md` (original: `chatgpt_baseline.docx`) | `outputs/governance_documents/governance_document_20261023_1432.md` |
| Second output | — | `outputs/internal_updates/internal_update_20261023_1438.md` (internal update, same pipeline) |

## Test prompt

```
Draft an AI System Monitoring Plan for the AI system "Credit Decision Support AI"
at Northstar Digital Bank, based on the EU AI Act. Cite your sources.
```

## Result summary

| Criterion | Generic ChatGPT | AI Governance Copilot |
|---|---|---|
| Company-specific facts from Northstar's own documents | **0**. It cannot know them; it states assumptions instead ("Role assumption: Northstar is the deployer; a third-party vendor is the provider"). | **22 cited gap statements** from 3 company documents (examples below) |
| Citations | 3 external sources (EUR-Lex AI Act, GDPR, EBA guidelines), not linked to individual claims about Northstar | Every bullet carries a `[P#]` label; the Source Register maps each label to file, section and visibility |
| Invented values | **Many.** Thresholds (">10% relative deterioration for 2 periods", "PSI >0.20"), daily/weekly/monthly/quarterly/annual cadences, eight named role groups with duties, "Version 0.1", "Quarterly; annual approval" | **None.** Unknowns stay as placeholders: `[OWNER TO CONFIRM]`, `[MONITORING FREQUENCY TO CONFIRM]`, `[THRESHOLD TO CONFIRM]`, `[DATE TO COMPLETE]`, `[EVIDENCE TO PROVIDE]` |
| Gap vs. evidence distinction | Writes a target-state plan as if designing from scratch; no evidence status | Separates *Evidence Found* from *Evidence Incomplete or Not Found* and gives an overall status (`evidence_incomplete`) |
| Compliance wording | Cautious ("not legal advice") | No compliance verdict; verdicts are rejected by an automatic check |
| Human review | Free text note | Mandatory `Status: Draft — human review required`, review checklist, approval block; nothing is approved automatically |
| Self-checking | None | Automatic checks flagged 2 issues in this run (see limitations) |
| Memory across runs | None | Approved internal updates feed the **gap register** (open / complete / re_check per requirement) |
| Regulatory depth | **Stronger**: Art. 25–27, 72–73, Annex III 5(b), GDPR Art. 22/35, EBA guidelines | Weaker in this run: no EU AI Act `[S#]` context was retrieved (see limitations) |

## At least 3 company-specific, cited facts only the Copilot produced

Each fact was checked against the source file in `knowledge_base/primary/`.

| # | Fact in the Copilot draft | Label | Source file (verified) |
|---|---|---|---|
| 1 | Analysts review outputs, but there are no measurable error/uncertainty criteria for escalation, no escalation response time and no procedure for restricting or disabling the system | [P1] | `human_oversight_procedure.md` |
| 2 | Business owner, technical owner, monitoring owner, incident contact and monitoring schedule are not recorded for the system | [P3] | `ai_system_inventory.md` (fields marked `[NOT RECORDED]`) |
| 3 | The validation report does not give the model/version tested, acceptance thresholds, subgroup/fairness analysis, robustness testing or independent sign-off | [P2] | `testing_validation_report.md` |
| 4 | No approved monitoring schedule exists; frequencies, metrics and escalation thresholds are not defined | [P2] in the internal update | `monitoring_notes.md` |

ChatGPT's plan contains none of these facts. Instead it fills the same places with plausible but unsupported values, for example a PSI threshold of 0.20 and monthly forums. For Northstar these would be **invented controls**, and AGENTS.md rule 6 forbids exactly that.

## Excerpts side by side

**Ownership**

> **ChatGPT:** "Credit Risk / Model Risk: Owns credit outcome monitoring, validation, benchmark comparison, overrides, drift review, and model approval." *(eight role groups, none from Northstar's documents)*
>
> **Copilot:** "Business owner: [OWNER TO CONFIRM] [P3]. Technical owner: [OWNER TO CONFIRM] [P3]. Monitoring owner: [OWNER TO CONFIRM] [P3]."

**Thresholds**

> **ChatGPT:** "material population shift (proposed PSI >0.20) … >10% relative deterioration in a key metric for 2 periods"
>
> **Copilot:** "Acceptance thresholds: [THRESHOLD TO CONFIRM] [P2]." / "Proposed: review every [MONITORING FREQUENCY TO CONFIRM]; escalate within [THRESHOLD TO CONFIRM]."

**What is actually known**

> **ChatGPT:** "Role assumption: Northstar is the deployer; a third-party vendor is the provider. Confirm this against the contract…"
>
> **Copilot:** "The Credit Decision Support AI supports analysts in reviewing credit applications. [P3]"

## Honest limitations of this run

1. **No regulatory context.** Color B's current retrieval reads only the secondary reference notes, and Color A deliberately excludes those notes from the baseline knowledge base. The EU AI Act PDF is not searched yet. So the Copilot draft received no `[S#]` chunks. The model still wrote "implements [S1]", and the automatic check caught it: *"Cites sources that were not supplied: S1"*. This shows the safety check working. It also shows that the Color B integration must be finished before the demo.
2. **Placeholder type.** The second automatic check flagged one gap bullet that uses `[OWNER TO CONFIRM]` for a criterion, where `[THRESHOLD TO CONFIRM]` was expected.
3. **Limited retrieval.** With top-k = 3, the internal update marked some requirements `evidence_not_found` (e.g. GOV-04 cited to `human_oversight_procedure.md`) even though `ai_system_inventory.md` exists. A human reviewer must check these statuses before approval. This is why approval is manual and the gap register only changes after validation.
4. ChatGPT gives a more complete **regulatory** structure. The Copilot's value is **company-specific, traceable evidence without invention**, not broader legal knowledge.

## Conclusion

M7 is met: the Copilot output contains **at least 4 verified, cited, company-specific facts** that the generic baseline does not contain, and it keeps every unknown value as a placeholder. ChatGPT invents them. The remaining weakness is regulatory grounding, which depends on Color B searching Color A's EU AI Act chunks.
