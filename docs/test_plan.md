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
