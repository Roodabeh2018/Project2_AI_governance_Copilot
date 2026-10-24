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
| M1 | Ingest primary company AI governance docs with visibility tags | `src/ingestion.py`, `knowledge_base/primary/` | Loader reports files and tags |
| M2 | Ingest the official EU AI Act PDF and optional public uploads | `src/ingestion.py`, `knowledge_base/secondary/` | PDF pages/articles are retained with source metadata |
| M3 | Chunk, index and retrieve top-k chunks with metadata | `src/chunking.py`, `src/indexing.py`, `src/retrieval.py` | Query returns separate primary and secondary results |
| M4 | Call an LLM with retrieved context and source citations | `src/llm_generator.py` | Unsupported query returns `insufficient_source` |
| M5 | Use reusable prompt templates | `src/prompts.py` | Document draft and internal update work; public output excludes internal facts |
| M6 | Provide one end-to-end CLI pipeline, then local Gradio UI | `src/pipeline.py`, `src/app.py` | CLI and Gradio write/display a draft in `outputs/` |
| M7 | Demonstrate value versus generic ChatGPT | `docs/uniqueness_comparison.md` | Actual side-by-side output shows at least 3 supplied-company-specific facts with citations, when using internal context |
| M8 | Document project structure, agent instructions and RAG decision | `project_structure.md`, `AGENTS.md`, `rag_decision.md` | Complete documents; `AGENTS.md` rules are included in generation prompts |

## 4. Out of scope for the two-day sprint
- Definitive legal opinions or autonomous compliance decisions.
- Claiming legal non-compliance solely because evidence was not retrieved.
- Live regulatory monitoring/web scraping.
- Automatic publication or approval.
- Production integrations, enterprise access controls or complex dashboards.
- A Gradio UI before the CLI and all mandatory requirements work.

## 5. Risks — exactly three
| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| AI invents a requirement or makes an unsupported compliance claim | Medium | High | RAG-grounded evidence, citations, insufficient-source fallback, human review |
| Internal or confidential facts leak into a public post | Medium | High | Synthetic data only, visibility tags, filter public retrieval before generation, leakage tests |
| RAG implementation blocks the end-to-end demo | Medium | High | Keep the retrieval scope minimal, use shared fixtures and reduce optional features; do not bypass RAG |

## 6. WBS / Trello work breakdown
1. **Structure and board:** project structure, `AGENTS.md`, RAG decision, Trello lists/cards, definition of done.
2. **Knowledge bases:** synthetic company documents and public reference notes.
3. **Ingestion and retrieval:** Markdown/PDF loader, chunking, embeddings, vector store and top-k retrieval.
4. **Generation:** LLM client, prompt templates, document draft, internal update, pipeline command.
5. **Close:** tests, uniqueness comparison, README, demo and Day 1/Day 2 board screenshots.

## 7. Team split along the RAG pipeline (as built)
The split follows the pipeline in `rag_decision.md`. Each color owns consecutive steps and hands over through the shared contract (`docs/shared_engineering_contract.md`) and shared fixtures.

| RAG step (`rag_decision.md`) | Owner | Implemented in |
|---|---|---|
| 1–2. Load Markdown/PDF files, parse text and metadata (incl. `visibility` from front matter) | **Color A — Armin** | `src/ingestion.py`, `src/kb_validation.py` |
| 3. Split into chunks keeping source file, section/page/article and visibility | **Color A — Armin** | `src/chunking.py` → `cache/chunks.jsonl` |
| 4. Embed chunks and store them in a local vector index | **Color B — Murat** | `src/indexing.py` (OpenAI `text-embedding-3-small`, `cache/vectors.npy` + `metadata.json`) |
| 5. Retrieve top-k per knowledge base (Primary and Secondary separately), filtered by visibility, with a minimum score and a named-system check | **Color B — Murat** | `src/retrieval.py` |
| 6. Pass retrieved context and a reusable prompt template to the LLM | **Color C — Roodi** | `src/prompts.py`, `src/llm_generator.py` |
| 7. Require source references, cautious wording and placeholders; check the output | **Color C — Roodi** | `src/llm_generator.py` (validator, verdict check, status line) |
| 8. Save the Markdown draft; human review and approval; gap register | **Color C — Roodi** | `src/pipeline.py` (CLI), `src/app.py` (Gradio), `src/gap_register.py` |

Everyone worked in parallel on a branch and integrated through pull requests reviewed by a teammate.

## 7a. WBS → Trello card → Must ID
Trello cards as they appear on the board (`docs/screenshots/`). Color A cards are blue, Color B green, Color C orange.

| WBS (§6) | Trello card | Owner | Must ID (§3) |
|---|---|---|---|
| 1. Structure and board | Board, lists and the shared contract were set up before the cards (`project_structure.md`, `AGENTS.md`, `rag_decision.md`, `docs/shared_engineering_contract.md`); no separate card | Team | M8 |
| 2. Knowledge bases | 01 Ingest Primary and Secondary Knowledge Bases | Armin | M1, M2 |
| 2. Knowledge bases | 02 Normalize EU AI Act and Uploaded Documents | Armin | M2 |
| 3. Ingestion and retrieval | 03 Define and Validate the Unified Source/Chunk Schema | Armin | M1–M3 |
| 3. Ingestion and retrieval | 04 Implement Ingestion, Chunking and Local Cache | Armin | M3 |
| 3. Ingestion and retrieval | 05 Validate the Integrated Knowledge Base | Armin | M1–M3 |
| 3. Ingestion and retrieval | 06 Build the Local Vector Index | Murat | M3 |
| 3. Ingestion and retrieval | 07 Implement Separate Primary and Secondary Retrieval | Murat | M3 |
| 3. Ingestion and retrieval | 08 Implement Output-Visibility Filtering | Murat | M3, M5 |
| 3. Ingestion and retrieval | 09 Implement Source Sufficiency and Safety Handling | Murat | M4 |
| 3. Ingestion and retrieval | 10 Run Retrieval Evaluation and Grounding Tests | Murat | M3, M4 (`docs/answer_key_results.md`) |
| 4. Generation | 11 Define Prompt Contracts and Reusable Templates | Roodi | M5, M8 |
| 4. Generation | 12 Implement the LLM Generator and CLI Pipeline | Roodi | M4, M6 |
| 4. Generation | 13 Build the Local Gradio Interface | Roodi | M6 |
| 5. Close | 14 Integrate, Compare and Prepare the Final Demo | Roodi | M7 (+ README, demo, board evidence) |

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
