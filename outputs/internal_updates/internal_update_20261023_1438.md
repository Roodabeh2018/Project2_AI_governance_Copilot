# Internal update — monitoring and human oversight
Status: Draft — human review required

## What the documents say
The Human Oversight Procedure draft indicates that analysts review outputs from the Credit Decision Support AI, but lacks measurable criteria for intervention, including error or uncertainty criteria, escalation response times, and procedures for disabling the system [P1]. The Monitoring Notes document does not include an approved monitoring schedule, nor does it define monitoring frequencies, metrics, or escalation thresholds [P2]. The Testing and Validation Report is preliminary and lacks essential details such as model/version tested, acceptance thresholds, and independent review [P3].

## Potential gaps             
| Requirement | Evidence status      | Gap                                              | Sources |
|-------------|----------------------|--------------------------------------------------|---------|
| GOV-04      | evidence_not_found    | No inventory entry with owners and model details | [P1]    |
| GOV-06      | evidence_not_found    | No risk classification assessment                 | [P2]    |
| RISK-02     | evidence_not_found    | No approved risk assessment with rationale        | [P2]    |
| TECH-03     | evidence_not_found    | No technical documentation available              | [P3]    |
| HUM-01      | evidence_incomplete   | Missing intervention criteria and escalation plan | [P1]    |
| TEST-03     | evidence_incomplete   | Preliminary report lacks key validation details   | [P3]    |
| MON-02      | evidence_incomplete   | No monitoring plan with owner or frequency       | [P2]    |
| MON-09      | evidence_not_found    | No incident response procedure documented         | [P2]    |

## Next steps
- Complete the Human Oversight Procedure with clear intervention criteria and escalation processes [OWNER TO CONFIRM].
- Develop a comprehensive monitoring plan that includes metrics and thresholds [OWNER TO CONFIRM].
- Finalize the Testing and Validation Report with necessary details and approvals [OWNER TO CONFIRM].

## Open Questions
- What are the specific criteria for intervention in the Human Oversight Procedure?
- Who will be responsible for the monitoring plan and what will be the frequency of monitoring?

Overall evidence status: evidence_incomplete

```json
[
    {"requirement_id": "GOV-04", "status": "evidence_not_found", "sources": ["P1"], "note": "No inventory entry found."},
    {"requirement_id": "GOV-06", "status": "evidence_not_found", "sources": ["P2"], "note": "No risk classification assessment found."},
    {"requirement_id": "RISK-02", "status": "evidence_not_found", "sources": ["P2"], "note": "No approved risk assessment found."},
    {"requirement_id": "TECH-03", "status": "evidence_not_found", "sources": ["P3"], "note": "No technical documentation found."},
    {"requirement_id": "HUM-01", "status": "evidence_incomplete", "sources": ["P1"], "note": "Missing intervention criteria."},
    {"requirement_id": "TEST-03", "status": "evidence_incomplete", "sources": ["P3"], "note": "Preliminary report lacks key validation details."},
    {"requirement_id": "MON-02", "status": "evidence_incomplete", "sources": ["P2"], "note": "No monitoring plan found."},
    {"requirement_id": "MON-09", "status": "evidence_not_found", "sources": ["P2"], "note": "No incident response procedure found."}
]
```

## Source Register
| Label | Source | Section | Locator | KB | Visibility | Cited |
|---|---|---|---|---|---|---|
| P1 | human_oversight_procedure.md | Human Oversight Procedure — Synthetic Draft | human_oversight_procedure.md, Human Oversight Procedure — Synthetic Draft | primary | internal | yes |
| P2 | monitoring_notes.md | Monitoring Notes — Credit Decision Support AI (Synthetic) | monitoring_notes.md, Monitoring Notes — Credit Decision Support AI (Synthetic) | primary | internal | yes |
| P3 | testing_validation_report.md | Credit Decision Support AI — Testing and Validation Report (Synthetic) | testing_validation_report.md, Credit Decision Support AI — Testing and Validation Report (Synthetic) | primary | internal | yes |

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
