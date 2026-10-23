# Public Leakage Test — AI Governance Copilot

Risk from `project_structure.md` §5: *Internal or confidential facts leak into a public post.*
Safety tests **S05 / S06** in `docs/test_plan.md`: internal and mixed chunks must be excluded **before prompt construction** when the output is public.

Runs A and B were performed on 23 Oct 2026 with a real LLM (`gpt-4o-mini`, `LLM_PROVIDER=openai`), Windows, conda env `bootcamp-env`, and the PR #13 branch before PR #12. Run C is the separate local-index retrieval/prompt check described below.

**Scope of this test:** it checks **chunk filtering before prompt construction**, i.e. which source chunks the LLM receives. It does **not** prove that the whole generated text is safe to publish. Request fields such as the AI system name and document title are also placed in the prompt, and the model can write any text. Every public output still needs human review before use.

## Run A: public output with real retrieval

```
python -m src.pipeline --type governance_document --visibility public --no-review
```

**Result:**

```
**insufficient source** — no supporting source retrieved
```

**Interpretation: PASS for chunk filtering (fail closed).** With the legacy Color B retrieval, no chunk that Color A marks `public` was retrieved for this query. The pipeline did **not** fall back to internal documents. It stopped with `insufficient_source` and saved nothing.

## Run B: public output with mixed internal and public context

This run uses the shared fixture `tests/fixtures/sample_retrieved_context.json`. It contains **3 internal Primary chunks** (`human_oversight_procedure.md`, `monitoring_notes.md`, `ai_system_inventory.md`) and **3 public Secondary chunks** (EU AI Act Articles 9, 14, 26).

```
python -m src.pipeline --type governance_document --visibility public --fixture tests/fixtures/sample_retrieved_context.json --no-review
```

**Saved:** `outputs/governance_documents/governance_document_20261023_1441.md`

**Source Register of the generated draft:**

| Label | Source | Section | Locator | KB | Visibility | Cited |
|---|---|---|---|---|---|---|
| S1 | article_014.md | Article 14 | EU AI Act, Article 14 (Human oversight) | secondary | public | yes |
| S2 | article_009.md | Article 9 | EU AI Act, Article 9 (Risk management system) | secondary | public | yes |
| S3 | article_026.md | Article 26 | EU AI Act, Article 26 (Obligations of deployers of high-risk AI systems) | secondary | public | no |

**Checks:**

| Check | Result |
|---|---|
| Any internal chunk in the Source Register? | **No.** All 3 internal Primary chunks were removed before the prompt was built; only `[S#]` labels exist |
| Text from the removed internal chunks in the output? (e.g. "[NOT RECORDED]" inventory fields, "no approved monitoring schedule", "deputy/backup accountable person") | **None found** (manual check of these phrases) |
| Text from request fields in the output? | **Yes.** The title and purpose contain "Credit Decision Support AI", which comes from the request field `ai_system`, not from any public-tagged source |
| "Evidence Found" section | "None". The fixture contains no Primary chunk tagged `public` (the contract allows Primary chunks that are explicitly tagged public), so no company evidence was available |
| Draft status line | `Status: Draft — human review required` |
| Automatic checks | ✅ All checks passed |

**Interpretation: PASS for chunk filtering.** None of the internal chunks reached the LLM.

**Limitation, request fields:** the name "Credit Decision Support AI" in the public output was supplied by the user in the request, not retrieved. Visibility filtering applies to retrieved chunks only. Request fields are passed to the prompt as typed, so a public request should not name internal systems or details unless they are approved for publication. Proposed follow-up: for public outputs, omit or generalise the `ai_system` field, as `build_query()` already does for retrieval.

**Finding to improve:** the model wrote a literal `[P#]` next to several gap bullets, e.g. "Monitoring owner: [OWNER TO CONFIRM] [P#] [S1]". It is not a real label and no internal content is behind it, but it is noise in a public draft. The output validator does not catch it yet, because it only recognises real labels such as `P1`. Proposed follow-up: flag `[P#]` / `[S#]` template residue as an automatic-check warning.

## Run C: public retrieval with the local vector index

**Run date:** 23 Oct 2026. This run used the local index built from the supplied Primary and
Secondary chunks and the retrieval evaluation in `tests/evaluate_retrieval.py`. It queried
“General public information about human oversight and high-risk AI systems” with
`output_visibility="public"`, then passed the retrieved results to `build_prompt()`.
No language-model generation was performed for this run.

**Result:**

- Retrieval status: `success`
- Retrieved results: 5
- Results with visibility other than `public`: 0
- Non-public indexed chunk texts found in the constructed prompt: 0
- Citations equal to each result's `SourceChunk.source_locator`: all passed

**Interpretation: PASS for chunk filtering.** The live local-index run returned public results
without including non-public chunks in the generated prompt. This checks retrieval, prompt
construction and citation locators; it does not validate arbitrary text a language model might
generate. Human review remains required for any public communication.

## Automated regression tests (offline, `LLM_PROVIDER=mock`)

The two tests marked *(PR #13)* were added by that follow-up and are present in the integrated branch.

| Test | What it proves |
|---|---|
| `tests/test_pipeline.py::test_public_output_never_receives_internal_chunks` | Public run on the shared fixture keeps only public chunks |
| `tests/test_pipeline_adapter.py::test_public_request_excludes_internal_docs_mislabelled_by_legacy_retrieval` | Visibility comes from Color A's canonical metadata, not from a wrong label in the retrieval output |
| `tests/test_pipeline_adapter.py::test_basename_collision_never_assigns_public_metadata_to_internal_text` | An internal file and a public upload with the same file name cannot be confused |
| `tests/test_review_followup.py::test_prepopulated_public_request_never_sends_internal_text_to_the_prompt` *(PR #13)* | Internal text is filtered even when context is passed in directly; the prompt sent to the LLM is inspected |
| `tests/test_review_followup.py::test_public_request_with_only_internal_context_returns_insufficient_source` *(PR #13)* | If nothing public remains after filtering, the result is `insufficient_source`, never an internal fallback |

Run them with:

```
python -m pytest -q
```

## Defence in depth (for retrieved chunks)

1. **Color A** assigns `visibility` from each document's front matter (canonical metadata).
2. **Color B** filters by visibility during retrieval.
3. **Color C** filters again before prompt construction, on every context path. It takes visibility from Color A, drops sources it cannot resolve unambiguously, and re-checks sufficiency after filtering.
4. **Output validator** warns if a public output cites an internal label.
5. **Human review**: nothing is published automatically. This is also the safeguard for text that does not come from chunks (request fields, model wording).

Run A records the earlier legacy retrieval behavior before PR #12. Run C records the subsequent
local-index behavior; it does not replace the still-useful fixture-based Run B.
