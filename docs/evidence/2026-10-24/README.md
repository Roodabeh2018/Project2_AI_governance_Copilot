# Evidence runs — 24 Oct 2026

Real-LLM outputs from the final integrated pipeline. Copied unchanged from the local `outputs/` folder (git-ignored), so that reviewers can read them.

| | |
|---|---|
| Commit | `main` `913961c` |
| Generation model | `gpt-4o-mini`, temperature 0.2 (`LLM_PROVIDER=openai`) |
| Embeddings | `text-embedding-3-small`; index rebuilt with `python -m src.build_index` (491 chunks) |
| Retrieval | top-k 3 Primary + 3 Secondary, minimum score 0.35 |
| Machine | Windows, conda env `bootcamp-env` |

| File | Original name | Command |
|---|---|---|
| `internal_monitoring_plan.md` | `governance_document_20261024_1532.md` | `python -m src.pipeline --type governance_document --document "AI System Monitoring Plan" --topic "monitoring and human oversight" --no-review` |
| `internal_update.md` | `internal_update_20261024_1532.md` | `python -m src.pipeline --type internal_update --topic "monitoring and human oversight" --no-review` |
| `public_monitoring_plan.md` | `governance_document_20261024_1533.md` | `python -m src.pipeline --type governance_document --visibility public --no-review` |

Checks of facts and citations: `docs/uniqueness_comparison.md` Part 1 and `docs/public_leakage_test.md` Run D. Known weaknesses of these runs are listed there too; the outputs are drafts and were not approved.
