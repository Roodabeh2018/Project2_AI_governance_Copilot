# Generic baseline — ChatGPT output (verbatim text)

Captured 23 Oct 2026 from chatgpt.com, no files attached. Original file: `chatgpt_baseline.docx`.

Prompt: `Draft an AI System Monitoring Plan for the AI system "Credit Decision Support AI" at Northstar Digital Bank, based on the EU AI Act. Cite your sources.`

---

AI System Monitoring Plan

Credit Decision Support AI  |  Northstar Digital Bank

| Document status | Accountable owner | Review cycle | Version |
|---|---|---|---|
| Draft for governance review | To be assigned by Northstar | Quarterly; annual approval | 0.1 \| 23 Oct 2026 |

Purpose. This plan defines how Northstar monitors the Credit Decision Support AI during live use to detect performance degradation, unfair outcomes, unsafe use, data problems, and risks to people. It is a deployer-side operating plan and a proposed control framework. The legal owner must confirm the bank’s role, product scope, national supervisory requirements, and vendor documentation before approval.

Decision requested. Assign named accountable owners, validate the thresholds and baseline data in Section 5, complete the required impact assessments, and approve the escalation and suspension authority before production use.

1. Scope and assumptions

The system supports assessment of the creditworthiness or credit score of natural persons for consumer credit applications. On that assumption, it is a high-risk AI system under Annex III, point 5(b), of the EU AI Act, except where the system is intended solely to detect financial fraud. [1] The plan applies to each model version, decision policy, channel, product, and relevant supplier component used in that process.

Role assumption: Northstar is the deployer; a third-party vendor is the provider. Confirm this against the contract and actual system design. Northstar may acquire provider obligations if it rebrands the system, substantially modifies it, or changes its intended purpose in a way covered by Article 25. [1]

Coverage: application intake, feature construction, score or recommendation generation, policy cut-offs, human review, final decision, customer communication, appeals, and relevant post-decision outcomes.

Out of scope: this plan does not establish that any particular credit model, decision threshold, data source, or automated decision process is lawful. GDPR, consumer-credit, equal-treatment, prudential, outsourcing, and national rules require separate legal and compliance review.

No live deployment should proceed until Northstar has reviewed provider instructions, conformity and registration information where applicable, data protection assessments, the fundamental-rights impact assessment, and the bank’s model-risk approval.

2. Legal and control basis

The AI Act requires deployers to use high-risk systems in line with instructions, assign competent and authorized human overseers, monitor operation, act on risk signals, and retain logs under their control for an appropriate period of at least six months, subject to other applicable law. Financial institutions subject to Union financial-services internal-governance rules may satisfy the Article 26(5) monitoring obligation through those rules. [1]

The provider must operate a documented post-market monitoring system and plan to collect and analyse performance data over the system lifetime. Article 72(4) allows qualifying financial institutions to integrate the relevant post-market elements with existing financial-services governance arrangements where they achieve an equivalent level of protection. This does not remove Northstar’s need to monitor its use, report issues to the provider, and preserve evidence. [1]

Because this is an Annex III 5(b) creditworthiness system, Northstar must assess whether Article 27 requires a fundamental-rights impact assessment (FRIA) before use; the provision includes deployers of such systems, subject to its stated SME exception. Assess the GDPR separately: a DPIA is required where the processing is likely to create high risk, and Article 22 safeguards may apply to solely automated decisions with legal or similarly significant effects. [1][2]

The EBA Guidelines on loan origination and monitoring provide complementary sector governance context across the lifecycle of credit facilities. Northstar should map this plan to its applicable internal credit-risk, model-risk, outsourcing, and conduct frameworks. [3]

3. Outcomes and operating principles

Keep the system within its approved purpose, population, products, channels, and operating conditions.

Detect changes in data, model behaviour, decision outcomes, and credit performance early enough to contain harm.

Test outcome quality and error patterns across relevant customer groups, while respecting lawful data use and privacy controls.

Ensure human reviewers can understand the output, challenge it, override it, and escalate cases without being pressured to rubber-stamp recommendations.

Provide a clear customer route for explanation, correction of inaccurate data, complaint, and reconsideration where applicable.

Keep versioned evidence sufficient to reconstruct what the system received, produced, and how the decision was handled.

4. Ownership and decision rights

| Role | Accountability |
|---|---|
| Executive accountable owner (to assign) | Accepts residual risk; funds remediation; approves deployment, material changes, and restart after a critical suspension. |
| Credit Risk / Model Risk | Owns credit outcome monitoring, validation, benchmark comparison, overrides, drift review, and model approval. |
| AI System Owner / Product | Maintains intended purpose, version inventory, vendor coordination, release controls, and monitoring dashboard. |
| Compliance / AI Act lead | Tracks regulatory duties, FRIA follow-up, customer-facing transparency, incident classification, and authority notifications. |
| Data Protection Officer / Privacy | Reviews DPIA, lawful data use, minimisation, retention, access controls, and data subject rights. |
| Operations / Human reviewers | Apply the operating instructions, document overrides and reasons, escalate unsafe or anomalous outputs. |
| Technology / Security / Data Engineering | Monitors availability, interfaces, data pipelines, access, cybersecurity events, and reliable log capture. |
| Internal Audit | Independently tests monitoring design, evidence, escalation, and closure of findings. |

5. Monitoring framework

Northstar should set initial baselines from the approved validation period and a representative historical reference cohort. Thresholds below are proposed starting triggers for internal calibration; they are not numerical limits set by the EU AI Act and are not legal safe harbours. A breach triggers investigation and documented disposition, not an automatic conclusion of illegality.

| Monitoring area | Signals / measures | Cadence | Trigger and response |
|---|---|---|---|
| Credit performance | Default / delinquency rate by risk band; calibration and ranking metrics; approval and loss rates; stability by product and cohort. | Monthly; quarterly validation | Material deterioration from approved risk appetite or validation interval; e.g., >10% relative deterioration in a key metric for 2 periods, or breach of bank risk appetite. Credit Risk investigates; restrict affected segment if material. |
| Data quality and drift | Missingness, invalid values, schema changes, feature distributions, population stability, out-of-range values, source freshness. | Daily automated checks; monthly review | Critical feature unavailable or invalid; material population shift (proposed PSI >0.20) or unexplained data break. Stop automated recommendations for affected flow until resolved. |
| Fairness and access | Application, referral, approval, pricing/limit, error, override, appeal and default outcomes across legally permissible and meaningful cohorts; proxy and intersectional analysis where lawful. | Monthly / quarterly, with adequate sample sizes | Material unexplained disparity, worsening trend, or credible complaint pattern. Compliance and Credit Risk perform root-cause analysis; consider mitigation, human review, or suspension. Ratios are diagnostic only. |
| Human oversight | Review rate, override rate and reason, reviewer disagreement, time per case, escalation, sampling of accepted recommendations. | Monthly; sample weekly | Override or disagreement shifts beyond control limits; reviewer cannot explain or challenge output; evidence of rubber-stamping. Increase review and retrain; suspend affected automation if oversight is ineffective. |
| Customer impact and redress | Complaints, appeals, correction requests, adverse-action/explanation quality, reversal rates and time to resolve. | Monthly; urgent case escalation | Any credible pattern of incorrect adverse outcomes, inaccessible appeal path, or missed legal response deadline. Remediate cases and process; notify Compliance and DPO. |
| Operational and security | Availability, latency, failed requests, access anomalies, cybersecurity events, logging completeness, vendor incidents. | Continuous alerts; monthly summary | Security compromise, unexplained output changes, missing decision logs, or sustained service failure. Incident response; fail safe to approved manual process. |
| Use and change control | Population, product, geography, channel, input, threshold, policy, prompt/rule, vendor/model version, and integration changes. | At each release; monthly inventory reconciliation | Any use outside approved purpose or unapproved material change. Block release or revert; complete impact and validation review before restart. |

6. Review cadence and evidence

| When | Required activity | Record |
|---|---|---|
| Continuous / per decision | Validate input schema, service health, decision trace, model and policy version, and required event logs. Route errors to safe fallback. | Immutable decision event record and alert log. |
| Weekly | Operations reviews high-severity alerts, outages, unusual overrides, complaints and unresolved cases. | Triage queue, owner, severity, action and due date. |
| Monthly | Cross-functional monitoring forum reviews metrics, group-level outcomes, drift, human oversight, customer impact, vendor updates, and open corrective actions. | Signed dashboard pack and decision minutes. |
| Quarterly | Model Risk performs deeper validation and cohort analysis; Compliance reviews fairness and redress; DPO checks privacy issues and data minimisation. | Validation report, FRIA/DPIA action log, and approvals. |
| Annually / material change | Reapprove purpose, risk appetite, impact assessments, monitoring design, skills, vendor controls, and contingency arrangements. Revalidate after material change. | Annual approval and versioned plan. |
| Retention | Retain AI Act logs under Northstar’s control for the applicable period, at least six months under Article 26(6), unless other applicable law specifies otherwise. Align longer retention with GDPR storage limitation, banking recordkeeping, litigation holds, and documented purpose. | Retention schedule, access log, deletion evidence. |

Log at minimum the system and policy version, timestamp, application or case pseudonymous identifier, input feature provenance or controlled references, score/recommendation and confidence where available, applicable threshold, human reviewer identity and action, override reason, final decision, and subsequent alert/incident references. Do not copy unnecessary personal data into monitoring logs. Restrict access and protect logs against alteration.

7. Escalation, suspension and incident handling

Any employee may raise a concern through the model-risk or incident channel. The System Owner opens a case, preserves logs and model artifacts, assigns severity, and notifies Credit Risk, Compliance, Privacy, Security, Operations, and the provider as relevant.

| Severity | Examples | Required action |
|---|---|---|
| Critical | Credible risk of serious harm or fundamental-rights impact; security compromise; systemic erroneous rejection/approval; system used outside approved purpose; inability to produce decision trace. | Immediately disable the affected automated component or revert to approved manual decisioning. Preserve evidence. Notify accountable owner and provider without delay. Compliance determines external notification duties and timing. |
| High | Material drift or unexplained group disparity; significant increase in overrides/appeals; repeated data integrity failures; vendor change with possible impact. | Restrict impacted segment or require 100% qualified human review. Root-cause analysis and corrective-action plan. Restart only after documented approval. |
| Moderate / low | Isolated defect without evidence of material customer impact; minor performance or documentation issue. | Track to a named owner and deadline. Monitor for recurrence; escalate if trend or impact worsens. |

Under Article 26(5), if Northstar has reason to consider that use in accordance with instructions may present a risk within Article 79(1), it must inform the provider or distributor and relevant market-surveillance authority without undue delay and suspend use. A deployer that identifies a serious incident must immediately inform the provider first, then the importer/distributor and relevant authority; the provider reporting deadlines under Article 73 are generally 15 days, 2 days for specified widespread incidents, and 10 days where a death is involved. Compliance owns legal classification, reporting, and coordination; do not wait for root-cause certainty where a required report may be due. [1]

Restart requires: documented root cause; customer remediation decision; corrected and tested system or control; regression and fairness validation; provider confirmation where relevant; updated impact assessments and instructions; approval by Credit Risk, Compliance, and the accountable owner; and a monitored restart period.

8. Customer safeguards and privacy

Confirm that customer notices accurately describe AI involvement, the system’s role, relevant decision factors, and available routes to obtain human intervention or challenge where required.

Ensure reviewers have authority and time to assess cases independently, including the ability to disregard the recommendation and record why.

Provide a process to correct inaccurate input data and reassess an affected decision; connect complaints and appeals to monitoring signals.

Use protected or sensitive attributes for fairness testing only where lawful, necessary, access-controlled, and reviewed by the DPO; document proxy limitations and avoid treating group metrics as proof about any individual.

Complete and maintain a GDPR DPIA where required. Assess Article 22 applicability and safeguards for any solely automated decision with legal or similarly significant effects. [2]

9. Provider coordination and change management

Contract and operating procedures should require timely access to version notices, performance and incident information, material-change disclosure, provider monitoring findings, audit evidence, log availability, and support for corrective action. The bank should share relevant use-context and outcome signals with the provider while minimising personal data and preserving confidentiality. Each update requires impact screening, validation, approval, rollback readiness, and a new baseline where necessary.

10. Approval checklist

☐ Confirm intended purpose, Annex III classification, Northstar/provider legal roles, and product/channel coverage.

☐ Obtain and review provider instructions, technical documentation, post-market monitoring plan, logging design, and incident contacts.

☐ Complete Article 27 FRIA applicability and assessment; complete GDPR DPIA and Article 22 assessment as applicable.

☐ Calibrate proposed thresholds using Northstar’s representative validation and operational data; approve fairness cohorts and lawful data basis.

☐ Name decision rights for alert triage, risk acceptance, suspension, customer remediation, external notifications, and restart.

☐ Approve log schema, retention schedule, access restrictions, manual fallback, staff training, and dashboard/reporting cadence.

Sources

[1] Regulation (EU) 2024/1689 (Artificial Intelligence Act), consolidated text dated 27 July 2026. Key provisions: Articles 12, 14, 25–27, 72–73; Annex III, point 5(b). https://eur-lex.europa.eu/eli/reg/2024/1689/2026-07-27/eng

[2] Regulation (EU) 2016/679 (General Data Protection Regulation), Articles 22 and 35. https://eur-lex.europa.eu/eli/reg/2016/679/oj/eng

[3] European Banking Authority, Guidelines on loan origination and monitoring, EBA/GL/2020/06 (29 May 2020). https://www.eba.europa.eu/activities/single-rulebook/regulatory-activities/credit-risk/guidelines-loan-origination-and-monitoring

Legal status note. This is an operational draft, not legal advice. The monitoring indicators and thresholds are proposed controls for Northstar to calibrate. The applicable law and supervisory expectations should be confirmed by Northstar Legal and Compliance against the current consolidated texts and the bank’s actual system and operating model.
