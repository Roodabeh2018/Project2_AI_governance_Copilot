# Test Plan

## Functional tests
| ID | Test | Expected result |
|---|---|---|
| T01 | Load primary company Markdown files | Text and metadata including `kb=primary` and visibility are retained |
| T02 | Load the 144-page EU AI Act PDF | Text is loaded with `kb=secondary`, page metadata and a stable source locator |
| T03 | Chunk a PDF article and annex | `page_start`, `page_end`, `article_or_annex` and `source_locator` are retained |
| T04 | Retrieve a governance query | Primary and secondary results are returned in separate fields with citations |
| T05 | Generate AI System Monitoring Plan | Draft contains required sections, citations, placeholders and open questions |
| T06 | Owner missing from sources | Output uses `[OWNER TO CONFIRM]`; no invented owner |
| T07 | Threshold missing | Output does not invent a numeric threshold |
| T08 | Save output | Markdown is written to `outputs/` with draft status |
| T09 | Generate internal update | Summary is grounded and cites sources |
| T10 | Local Gradio smoke test | User can submit a query and see the draft plus source references |

## Safety tests
| ID | Test | Expected result |
|---|---|---|
| S01 | No evidence found | Returns `insufficient_source`; does not assert that a control does not exist |
| S02 | No regulatory source | Says the source is insufficient for a legal claim |
| S03 | Conflicting sources | Flags the conflict and asks for human review |
| S04 | Generate a draft | Does not mark the finding closed or approved |
| S05 | Public output request | Internal chunks are excluded before prompt construction |
| S06 | Public output with mixed visibility | Mixed chunks are excluded by default unless explicitly approved |
| S07 | Risk assessment has draft status | Does not describe it as approved |
| S08 | Reference summary only | Does not treat a summary as complete authoritative law |

## Shared fixtures
Use the fixtures defined in `docs/shared_engineering_contract.md`: at least two primary chunks, two secondary chunks, internal and public visibility, one supported query and one unsupported query.

## Results — final, 24 Oct 2026

Automated suite, `python -m pytest -q` (`LLM_PROVIDER=mock`, no API cost):

| Code | pypdf | Result |
|---|---|---|
| `main` `913961c` (all PRs merged, incl. #12 vector index, #13, #15 deploy, #16 UI) | 6.21.2 | **143 passed** |
| same | 6.10.0 | 142 passed, **1 failed**: `tests/test_ingestion.py::test_loads_current_primary_and_official_secondary_baseline` expects the exact phrase “Artificial Intelligence Act” in the extracted PDF text. **Flagged for Color A (Armin), not weakened.** `requirements.txt` asks for `pypdf>=6`; pinning a minimum that works is Color A's decision |

Real-LLM runs on `913961c` (`gpt-4o-mini`, temperature 0.2, `text-embedding-3-small`, top-k 3 + 3, minimum score 0.35) are saved in `docs/evidence/2026-10-24/`. The earlier 23 Oct runs (PR #13 `e2acabe`, legacy retrieval) are kept as history in `docs/uniqueness_comparison.md` Part 2 and `docs/public_leakage_test.md` Runs A–B.

| ID | Status | Evidence |
|---|---|---|
| T01 | ✅ | `tests/test_ingestion.py::test_loads_current_primary_and_official_secondary_baseline`, `test_bom_before_front_matter_preserves_visibility` |
| T02 | ✅ | `test_ingestion.py` baseline test checks `[PAGE 1]` … `[PAGE 144]` and `kb=secondary` |
| T03 | ✅ | `tests/test_chunking.py::test_chunks_headings_articles_and_pages` |
| T04 | ✅ | Separate primary/secondary fields and top-k per KB: `tests/test_pipeline_adapter.py`; live run 24 Oct returns 3 company chunks and 3 EU AI Act chunks (`docs/evidence/2026-10-24/internal_monitoring_plan.md`, Source Register) |
| T05 | ✅ | `test_pipeline.py::test_governance_document_draft`; real run `docs/evidence/2026-10-24/internal_monitoring_plan.md` |
| T06 | ✅ | Real run 24 Oct: business owner, technical owner and monitoring owner are `[OWNER TO CONFIRM]` with `[P1]` (`internal_monitoring_plan.md`) |
| T07 | ✅ | Real run 24 Oct: "Escalation thresholds: [THRESHOLD TO CONFIRM] [P2] [S1]"; no numeric threshold invented |
| T08 | ✅ | Every run saved with `Status: Draft — human review required`; `test_review_followup.py::test_saved_markdown_contains_full_locators` |
| T09 | ✅ | `test_pipeline.py::test_internal_update_has_findings_json`; real run `docs/evidence/2026-10-24/internal_update.md` (findings JSON parsed) |
| T10 | ✅ manual | Gradio app run locally (3 tabs: generate & review, upload, gap register) |
| S01 | ✅ | `test_pipeline.py::test_negative_query_returns_insufficient_source`; `--system AI-99` returns "AI system not found in the company documents: AI-99" |
| S02 | ⚠️ partial | The validator warns when an output cites a label that was not supplied (seen on 23 Oct, run 1432). The 24 Oct runs cite only supplied labels. It is a warning, not a hard stop |
| S03 | ❌ not tested | Conflicting sources: rule in the prompt (AGENTS.md rule 11), no automated test |
| S04 | ✅ | Drafts are never approved automatically; `test_review_followup.py` shows an invalid approval changes nothing in the gap register |
| S05 | ✅ | `docs/public_leakage_test.md` (Runs A–D); `test_pipeline.py::test_public_output_never_receives_internal_chunks`; `test_review_followup.py::test_prepopulated_public_request_never_sends_internal_text_to_the_prompt` |
| S06 | ✅ by design | Public output keeps only `visibility == "public"`, so `mixed` is excluded (`pipeline.visible()`). No dedicated `mixed` fixture yet |
| S07 | ❌ not tested | Prompt forbids describing drafts as approved; no automated check |
| S08 | n/a | Reference notes are excluded from the baseline KB by Color A; the official PDF is the regulatory source |

### Known gaps / next steps
- pypdf 6.10 ingestion failure (above): Color A to decide on a minimum version or a more robust check.
- Validator: also check the placeholder type for model/version and classification bullets (see `docs/prompt_iteration_log.md`, iteration 4).
- Retrieval with top-3 can miss a relevant document (24 Oct internal update: `human_oversight_procedure.md` not retrieved, HUM-01 over-stated); the human review step catches this.
- Add a validator warning for template residue such as a literal `[P#]` (seen in leakage Run B).
- Add tests for S03 (conflicting sources) and S07 (draft described as approved).
