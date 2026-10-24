# Internal update — monitoring and human oversight
Status: Draft — human review required

## What the documents say     
The "Credit Decision Support AI" is designed to assist analysts in reviewing credit applications and is recorded as in production. However, the documentation lacks critical information regarding the business and technical owners, model/version identifier, AI risk classification, and monitoring details. The EU AI Act identifies that AI systems used for evaluating creditworthiness are classified as high-risk, necessitating robust human oversight measures to mitigate potential risks associated with their use [S2][S3].

## Potential gaps             
| Requirement | Evidence status       | Gap                                        | Sources |
|-------------|-----------------------|--------------------------------------------|---------|
| GOV-04      | evidence_not_found     | Missing owners, model version, classification, and contacts | [P1]    |
| GOV-06      | evidence_not_found     | AI Act applicability and risk classification not assessed | [P1]    |
| RISK-02     | evidence_not_found     | Approved risk assessment with rationale not provided | [P2]    |
| TECH-03     | evidence_incomplete    | Technical documentation is incomplete     | [P3]    |
| HUM-01      | evidence_not_found     | Human oversight procedure not documented   | [P1]    |
| MON-02      | evidence_not_found     | Monitoring plan with owner, frequency, metrics, and thresholds not documented | [P1]    |
| MON-09      | evidence_not_found     | AI incident response and escalation procedure not documented | [P1]    |

## Next steps                 
[OWNER TO CONFIRM]

## Open Questions
- Who are the designated business and technical owners for the "Credit Decision Support AI"?
- What is the model/version identifier for this AI system?
- What is the approved risk classification for this AI system?

Overall evidence status: evidence_not_found

```json
[
    {"requirement_id": "GOV-04", "status": "evidence_not_found", "sources": ["P1"], "note": "Missing owners, model version, classification, and contacts."},
    {"requirement_id": "GOV-06", "status": "evidence_not_found", "sources": ["P1"], "note": "AI Act applicability and risk classification not assessed."},
    {"requirement_id": "RISK-02", "status": "evidence_not_found", "sources": ["P2"], "note": "Approved risk assessment with rationale not provided."},
    {"requirement_id": "TECH-03", "status": "evidence_incomplete", "sources": ["P3"], "note": "Technical documentation is incomplete."},
    {"requirement_id": "HUM-01", "status": "evidence_not_found", "sources": ["P1"], "note": "Human oversight procedure not documented."},
    {"requirement_id": "MON-02", "status": "evidence_not_found", "sources": ["P1"], "note": "Monitoring plan with owner, frequency, metrics, and thresholds not documented."},
    {"requirement_id": "MON-09", "status": "evidence_not_found", "sources": ["P1"], "note": "AI incident response and escalation procedure not documented."}
]
```

## Source Register
| Label | Source | Section | Locator | KB | Visibility | Cited |
|---|---|---|---|---|---|---|
| P1 | ai_system_inventory.md | System: Credit Decision Support AI | ai_system_inventory.md, System: Credit Decision Support AI | primary | internal | yes |
| P2 | ai_risk_assessment_credit_support.md | Credit Decision Support AI — Risk Assessment (Synthetic) | ai_risk_assessment_credit_support.md, Credit Decision Support AI — Risk Assessment (Synthetic) | primary | internal | yes |
| P3 | technical_documentation_credit_support.md | Credit Decision Support AI — Technical Documentation (Synthetic) | technical_documentation_credit_support.md, Credit Decision Support AI — Technical Documentation (Synthetic) | primary | internal | yes |
| S1 | eu_ai_act/eu_ai_act_official.pdf | Article 14 | eu_ai_act/eu_ai_act_official.pdf, page=60, Article 14 | secondary | public | no |
| S2 | eu_ai_act/eu_ai_act_official.pdf | Regulation (EU) 2024/1689 of the European Parliament and of the Council of 13 June 2024 laying down harmonised rules on artificial intelligence and amending Regulations (EC) No 300/2008, (EU) No 167/2013, (EU) No 168/2013, (EU) 2018/858, (EU) 2018/1139 and (EU) 2019/2144 and Directives 2014/90/EU, (EU) 2016/797 and (EU) 2020/1828 (Artificial Intelligence Act)Text with EEA relevance. | eu_ai_act/eu_ai_act_official.pdf, page=16, Regulation (EU) 2024/1689 of the European Parliament and of the Council of 13 June 2024 laying down harmonised rules on artificial intelligence and amending Regulations (EC) No 300/2008, (EU) No 167/2013, (EU) No 168/2013, (EU) 2018/858, (EU) 2018/1139 and (EU) 2019/2144 and Directives 2014/90/EU, (EU) 2016/797 and (EU) 2020/1828 (Artificial Intelligence Act)Text with EEA relevance. | secondary | public | yes |
| S3 | eu_ai_act/eu_ai_act_official.pdf | Annex III | eu_ai_act/eu_ai_act_official.pdf, page=127, Annex III | secondary | public | yes |

## Human-Review Checklist
- [ ] Verify citations
- [ ] Confirm placeholders
- [ ] Review and approve

## Automatic checks
- ✅ All checks passed

## Approval
Reviewer: 
Decision: draft
Date: 
