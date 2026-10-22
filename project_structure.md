# project_structure.md — AI Governance Copilot

## 1. Project objectives: quality, time and cost
**Quality**
- Every factual claim in a finding, generated document or post must be traceable to retrieved source passages.
- Cite source filename and section/page/article wherever possible.
- Do not invent requirements, owners, model versions, dates, monitoring frequencies, thresholds, approvals or test results.
- Public content must not use internal-tagged information.
- Use cautious wording and require human review.

**Time**
- Two-day build with a Monday afternoon presentation.
- By the end of Day 1, both knowledge bases should load/index and one query should return a grounded answer with a source.
- Prioritise one end-to-end working flow over a broad feature set.

**Cost**
- Maximum €5 API spend.
- Build/cache the vector index once and reuse it.
- Limit repeated test generations and use the least expensive model that passes grounding checks.

## 2. Stakeholders
| Stakeholder | Need |
|---|---|
| Team of three builders | Shared repository, clear task split, working prototype |
| Instructor/evaluator | Project structure, RAG decision, Trello/Kanban, uniqueness and demo evidence |
| Fictional Head of AI Governance/Compliance | Drafts grounded enough for expert review; final say on approval |
| AI system owners and risk teams | Clear action items and unresolved questions |
| Compliance/legal reviewers and auditors | No unsupported claims or overstated compliance |
| LLM/embedding provider | Cost and availability controlled through caching and limited tests |

## 3. Must-have requirements
| ID | Requirement | Implementation target | Acceptance check |
|---|---|---|---|
| M1 | Ingest primary company AI governance docs with visibility tags | `src/document_processor.py`, `knowledge_base/primary/` | Loader reports files and tags |
| M2 | Ingest secondary public references/framework notes | `src/document_processor.py`, `knowledge_base/secondary/` | At least 8 source/reference files or documented constraint |
| M3 | Chunk, embed, store and retrieve top-k chunks with metadata | `src/retriever.py` | Query on monitoring or risk assessment retrieves relevant internal and reference passages |
| M4 | Call an LLM with retrieved context; cite sources and use fallback | `src/llm_generator.py` | Unsupported query says “insufficient source” |
| M5 | Use at least two reusable prompt templates | `src/prompt_templates.py` | Document draft and internal update work; optional public template excludes internal facts |
| M6 | Provide one end-to-end CLI pipeline saving Markdown | `src/content_pipeline.py` | CLI writes draft into `outputs/` |
| M7 | Demonstrate value versus generic ChatGPT | `docs/uniqueness_comparison.md` | Actual side-by-side output shows at least 3 supplied-company-specific facts with citations, when using internal context |
| M8 | Document project structure, agent instructions and RAG decision | `project_structure.md`, `agents.md`, `rag_decision.md` | Complete documents; `agents.md` rules are included in generation prompts |

## 4. Out of scope for the two-day sprint
- Definitive legal opinions or autonomous compliance decisions.
- Claiming legal non-compliance solely because evidence was not retrieved.
- Live regulatory monitoring/web scraping.
- Automatic publication or approval.
- Production integrations, enterprise access controls or complex dashboards.
- A UI before the CLI and all mandatory requirements work.

## 5. Risks — exactly three
| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| AI invents a requirement or makes an unsupported compliance claim | Medium | High | RAG-grounded evidence, citations, insufficient-source fallback, human review |
| Internal or confidential facts leak into a public post | Medium | High | Synthetic data only, visibility tags, filter public retrieval before generation, leakage tests |
| RAG implementation blocks the end-to-end demo | Medium | High | Timebox retrieval work; prioritise CLI; use a documented summary-in-prompt fallback if needed |

## 6. WBS / Trello work breakdown
1. **Structure and board:** project structure, `agents.md`, RAG decision, Trello lists/cards, definition of done.
2. **Knowledge bases:** synthetic company documents and public reference notes.
3. **Ingestion and retrieval:** Markdown/PDF loader, chunking, embeddings, vector store and top-k retrieval.
4. **Generation:** LLM client, prompt templates, document draft, internal update, pipeline command.
5. **Close:** tests, uniqueness comparison, README, demo and Day 1/Day 2 board screenshots.

## 7. Proposed team split (confirm together)
- **Person 1:** domain knowledge base, project structure, risk register and uniqueness comparison.
- **Person 2:** document processor, chunking, embeddings/vector store and retrieval.
- **Person 3:** LLM client, prompt templates and end-to-end pipeline.
Everyone updates the same Trello board and works on a Git branch. The original course guidance suggests one card per person at a time and WIP 2 for the board.

## 8. Definition of done
- [ ] Both knowledge bases load with source metadata.
- [ ] A query retrieves relevant internal and reference passages.
- [ ] At least one potential gap is returned with evidence/source citations.
- [ ] A draft AI System Monitoring Plan (or agreed governance document) is generated.
- [ ] Unknown values appear as placeholders.
- [ ] An internal update can be generated from the same pipeline.
- [ ] Unsupported query returns “insufficient source”.
- [ ] Draft saved to `outputs/` and labelled “Draft — human review required”.
- [ ] Actual uniqueness comparison and test results recorded.
- [ ] No automatic approval, closure or publishing.
