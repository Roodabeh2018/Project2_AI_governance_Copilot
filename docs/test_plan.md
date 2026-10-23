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

## Results — 23 Oct 2026

Automated suite, `python -m pytest -q` (`LLM_PROVIDER=mock`, pypdf 6.x), by tested combination:

| Code | Result |
|---|---|
| `main` `5da8697` (this branch's base) | 56 passed |
| PR #13 `e2acabe` (main + Color C follow-up) | 74 passed |
| PR #13 `2424c7d` (after two re-reviews) | 91 passed |
| main + PR #13 + PR #12 `b8e88b5` (temporary local merge) | 97 passed |

Real-LLM runs used `gpt-4o-mini` on PR #13 `e2acabe` with the legacy Color B retrieval (before PR #12); their outputs are under `outputs/`. Rows citing `tests/test_review_followup.py` require PR #13.

| ID | Status | Evidence |
|---|---|---|
| T01 | ✅ | `tests/test_ingestion.py::test_loads_current_primary_and_official_secondary_baseline`, `test_bom_before_front_matter_preserves_visibility` |
| T02 | ✅ | `test_ingestion.py` baseline test checks `[PAGE 1]` … `[PAGE 144]` and `kb=secondary` |
| T03 | ✅ | `tests/test_chunking.py::test_chunks_headings_articles_and_pages` |
| T04 | ⚠️ partial | Separate primary/secondary fields: `tests/test_pipeline_adapter.py` (top-k per KB). Live retrieval does not yet search the EU AI Act PDF; it depends on PR #12 (Color B) |
| T05 | ✅ | `test_pipeline.py::test_governance_document_draft`; real run `outputs/governance_documents/governance_document_20261023_1432.md` |
| T06 | ✅ | Real run: "Business owner: [OWNER TO CONFIRM] [P3]", "Monitoring owner: [OWNER TO CONFIRM] [P3]" |
| T07 | ✅ | Real run: "Acceptance thresholds: [THRESHOLD TO CONFIRM] [P2]"; no numeric threshold invented |
| T08 | ✅ | Every run saved with `Status: Draft — human review required`; `test_review_followup.py::test_saved_markdown_contains_full_locators` |
| T09 | ✅ | `test_pipeline.py::test_internal_update_has_findings_json`; real run `outputs/internal_updates/internal_update_20261023_1438.md` (all automatic checks passed) |
| T10 | ✅ manual | Gradio app run locally (3 tabs: generate & review, upload, gap register) |
| S01 | ✅ | `test_pipeline.py::test_negative_query_returns_insufficient_source`; `--system AI-99` returns "AI system not found in the company documents: AI-99" |
| S02 | ⚠️ partial | Run 1432 had no regulatory context; the validator flagged "Cites sources that were not supplied: S1". It is not yet a hard stop |
| S03 | ❌ not tested | Conflicting sources: rule in the prompt (AGENTS.md rule 11), no automated test |
| S04 | ✅ | Drafts are never approved automatically; `test_review_followup.py` shows an invalid approval changes nothing in the gap register |
| S05 | ✅ | `docs/public_leakage_test.md` (Runs A and B); `test_pipeline.py::test_public_output_never_receives_internal_chunks`; `test_review_followup.py::test_prepopulated_public_request_never_sends_internal_text_to_the_prompt` |
| S06 | ✅ by design | Public output keeps only `visibility == "public"`, so `mixed` is excluded (`pipeline.visible()`). No dedicated `mixed` fixture yet |
| S07 | ❌ not tested | Prompt forbids describing drafts as approved; no automated check |
| S08 | n/a | Reference notes are excluded from the baseline KB by Color A; the official PDF is the regulatory source |

### Known gaps / next steps
- Merge PR #12 (Color B vector index), then repeat T04 and leakage Run A with real EU AI Act retrieval.
- Add a validator warning for template residue such as a literal `[P#]` (seen in leakage Run B).
- Add tests for S03 (conflicting sources) and S07 (draft described as approved).
