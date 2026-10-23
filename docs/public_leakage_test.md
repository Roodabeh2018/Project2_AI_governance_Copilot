# Public Leakage Test — AI Governance Copilot

Risk from `project_structure.md` §5: *Internal or confidential facts leak into a public post.*
Safety tests **S05 / S06** in `docs/test_plan.md`: internal and mixed chunks must be excluded **before prompt construction** when the output is public.

All runs: 23 Oct 2026, real LLM (`gpt-4o-mini`, `LLM_PROVIDER=openai`), Windows, conda env `bootcamp-env`.

## Run A: public output with real retrieval

```
python -m src.pipeline --type governance_document --visibility public --no-review
```

**Result:**

```
**insufficient source** — no supporting source retrieved
```

**Interpretation: PASS (fail closed).** With the current Color B retrieval, no chunk that Color A marks `public` was retrieved for this query. The pipeline did **not** fall back to internal documents. It stopped with `insufficient_source` and saved nothing.

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
| Internal facts in the text? (e.g. "[NOT RECORDED]" inventory fields, "no approved monitoring schedule", "deputy/backup accountable person") | **None found** |
| "Evidence Found" section | "None", which is correct because no company evidence is allowed in a public output |
| Draft status line | `Status: Draft — human review required` |
| Automatic checks | ✅ All checks passed |

**Interpretation: PASS.** Internal content never reached the LLM.

**Finding to improve:** the model wrote a literal `[P#]` next to several gap bullets, e.g. "Monitoring owner: [OWNER TO CONFIRM] [P#] [S1]". It is not a real label and no internal content is behind it, but it is noise in a public draft. The output validator does not catch it yet, because it only recognises real labels such as `P1`. Proposed follow-up: flag `[P#]` / `[S#]` template residue as an automatic-check warning.

## Automated regression tests (offline, `LLM_PROVIDER=mock`)

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

## Defence in depth

1. **Color A** assigns `visibility` from each document's front matter (canonical metadata).
2. **Color B** filters by visibility during retrieval.
3. **Color C** filters again before prompt construction, on every context path. It takes visibility from Color A, drops sources it cannot resolve unambiguously, and re-checks sufficiency after filtering.
4. **Output validator** warns if a public output cites an internal label.
5. **Human review**: nothing is published automatically.

## Limitation

Run A cannot show a positive public draft from real retrieval yet, because the current retrieval does not search the EU AI Act PDF. Murat's PR #12 (local vector index + separate KB retrieval) addresses this. Run A should be repeated after it is merged.
