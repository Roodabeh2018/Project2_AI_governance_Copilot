# Retrieval answer-key evaluation

**Run date:** 2026-10-23
**Index:** 491 chunks, 1536-dimensional vectors
**Retrieval:** top 3 Primary and top 3 Secondary results per query, configured minimum-score threshold

No pre-existing 14-case answer-key file was present in the repository. To run the requested evaluation without treating absent test data as fact, the 14 cases below were derived from explicit statements in the supplied synthetic knowledge-base documents. This is a source-derived retrieval check, not an authoritative compliance assessment.

## Reproduction

From the repository root, rebuild the local index after any source or embedding-model change, then run:

```bash
python tests/evaluate_retrieval.py
```

The script makes live embedding API calls and may incur usage charges. For each answer-key case it sends the exact query `AI system: Credit Decision Support AI; Topic: <query topic below>`, retrieves top 3 per KB, and passes the case if at least one expected Primary source file appears in the Primary results and every returned citation equals its chunk's `source_locator`. It also runs the positive query, the AI-99 negative query, and the public prompt leakage check.

| ID | Exact query topic | Source-grounded expected evidence | Expected Primary source | Result |
|---|---|---|---|
| AK01 | `AI system inventory business owner technical owner` | Business and technical owner fields are marked `[NOT RECORDED]`. | [ai_system_inventory.md](../knowledge_base/primary/ai_system_inventory.md) — “System: Credit Decision Support AI” | Hit |
| AK02 | `inventory model version identifier` | Model/version identifier is marked `[NOT RECORDED]`. | [ai_system_inventory.md](../knowledge_base/primary/ai_system_inventory.md) — “System: Credit Decision Support AI” | Hit |
| AK03 | `AI risk classification status classification rationale credit decision support` | Risk classification and classification rationale are marked `[NOT RECORDED]`. | [ai_system_inventory.md](../knowledge_base/primary/ai_system_inventory.md) — “System: Credit Decision Support AI” | Hit |
| AK04 | `monitoring owner monitoring schedule last review incident contact` | Monitoring owner, last review date, incident contact and monitoring schedule are marked `[NOT RECORDED]`. | [ai_system_inventory.md](../knowledge_base/primary/ai_system_inventory.md) — “System: Credit Decision Support AI” | Hit |
| AK05 | `risk assessment approval record assessment date next review date` | Risk-assessment approval and assessment dates are not supplied. | [ai_risk_assessment_credit_support.md](../knowledge_base/primary/ai_risk_assessment_credit_support.md) — “Status” and “Incomplete areas” | Hit |
| AK06 | `residual risk rationale controls evidence supporting reduction` | The risk assessment says its residual-risk rationale is not explained. | [ai_risk_assessment_credit_support.md](../knowledge_base/primary/ai_risk_assessment_credit_support.md) — “Initial risk notes” and “Incomplete areas” | Hit |
| AK07 | `data quality provenance evidence incomplete` | Data quality/provenance evidence is incomplete or not supplied. | [ai_risk_assessment_credit_support.md](../knowledge_base/primary/ai_risk_assessment_credit_support.md) and [technical_documentation_credit_support.md](../knowledge_base/primary/technical_documentation_credit_support.md) | Hit |
| AK08 | `fairness subgroup evaluation evidence` | Fairness/subgroup evaluation evidence is not supplied. | [ai_risk_assessment_credit_support.md](../knowledge_base/primary/ai_risk_assessment_credit_support.md) — “Incomplete areas” | Hit |
| AK09 | `validation dataset acceptance criteria` | Validation dataset and acceptance criteria are not supplied. | [ai_risk_assessment_credit_support.md](../knowledge_base/primary/ai_risk_assessment_credit_support.md) — “Incomplete areas” | Hit |
| AK10 | `reassessment triggers material change criteria` | Reassessment triggers and material-change criteria are not defined. | [ai_risk_assessment_credit_support.md](../knowledge_base/primary/ai_risk_assessment_credit_support.md) — “Incomplete areas” | Hit |
| AK11 | `technical documentation data flow diagram referenced not attached` | The data-flow diagram is referenced but not attached. | [technical_documentation_credit_support.md](../knowledge_base/primary/technical_documentation_credit_support.md) — “Missing or unlinked details” | Hit |
| AK12 | `model version data provenance data lineage` | Model/version and data provenance/lineage details are not supplied. | [technical_documentation_credit_support.md](../knowledge_base/primary/technical_documentation_credit_support.md) — “Recorded context” and “Missing or unlinked details” | Hit |
| AK13 | `test evidence independent sign-off test results` | Independent reviewer/sign-off evidence is missing or incomplete. | [testing_validation_report.md](../knowledge_base/primary/testing_validation_report.md) — “Missing or incomplete” | Hit |
| AK14 | `change management deployment rollback details incomplete` | Change-management triggers and deployment/rollback details are incomplete. | [technical_documentation_credit_support.md](../knowledge_base/primary/technical_documentation_credit_support.md) — “Missing or unlinked details” | Hit |

**Result: 14/14 source-file hits. Citation-to-source-locator checks passed for all returned results.**

## Shared positive query

Query: “What does the EU AI Act say about human oversight of high-risk AI systems?”

- Status: `success`
- Results: 3 Primary and 3 Secondary
- Top Secondary result: `eu_ai_act/eu_ai_act_official.pdf`, page 60, Article 14
- All six result citations matched their `SourceChunk.source_locator`.

## Shared negative query

Query: “What is the monitoring status of AI system AI-99?”

- Status: `insufficient_source`
- Results: 0 Primary and 0 Secondary
- No query embedding or generation was attempted after the Primary-evidence check.
- The response says no matching Primary evidence was found and explicitly avoids claiming that AI-99 does not exist.

This evaluation checks retrieval and citation mapping only. It does not establish that controls are implemented or that any legal requirement is met.
