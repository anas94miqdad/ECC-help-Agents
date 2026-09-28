# Changelog

## 2.1.1 (2026-09)

Fixes found while revising real manuscripts with Mode B.

- `verify_references.py`: a DOI missing from Crossref is checked at the doi.org
  handle API before rejection; DOIs of other registration agencies (e.g. the EU
  Publications Office) are reported as PARTIALLY_VERIFIED instead of REJECTED.

- `compare_versions.py`: decimals at the start of a line (e.g. the median line of
  a two-line table cell) were mistaken for numbered headings and dropped from the
  original's number set, producing false "new number" findings.
- `manuscript_checks.py`: figure/table captions no longer count as in-text
  citations; captions that are never cited in the text are reported; keywords
  inside the abstract section are not counted towards the abstract word limit.
- `compare_versions.py`: revised reference entries are counted per line (entries
  with identical openings, e.g. several EU regulations, were merged); numbered
  headings starting with an acronym ("3.2. AI use cases") are recognized.
- `compare_versions.py`: numbers inside `{>>...<<}` notes to authors are not
  treated as manuscript text.
- `manuscript_checks.py`: table/figure captions placed after the reference list
  (common in journal submissions) are included in the "caption never cited" check.
- `extract_manuscript.py`: additionally writes `<name>.clean.md` (no block IDs)
  so the other checks can run on the original.

## 2.1 (2026-09)

Mode B extended to optimize or rebuild uploaded drafts (Word/PDF) using their
content as the basis.

- `references/revision-of-existing-manuscripts.md`: extraction, content
  inventory, structural map, 11-dimension maturity scorecard, fix classes
  (TEXT / INFO / ANALYSIS / DESIGN), intervention levels L1 Polish to L4 Rebuild,
  revision blueprint, rewrite rules, verification, deliverables.
- `scripts/extract_manuscript.py`: DOCX (headings incl. headings typed as plain
  text, lists, tables, captions, comments, tracked changes, footnotes/endnotes,
  equations, content controls, reference-manager fields, metadata), PDF (running
  headers/footers, page and line numbers, hyphenation, scanned-PDF detection),
  DOC/ODT/RTF via LibreOffice, Markdown/TXT; block-ID inventory.
- `scripts/compare_versions.py`: content-preservation check (uncovered blocks,
  unsourced new numbers, lost results, reference changes) and traceability CSV.
- `scripts/build_docx.py`: revised Markdown to DOCX with Word comments,
  highlighted placeholders, double spacing, line numbers, empty author metadata.
- German section headings recognized by all scripts.
- `templates/revision_report.md`; four new eval cases (11-14); stop conditions
  for unextractable uploads and requests to "complete" missing content.

## 2.0 (2026-09)

Rebuilt from the v1.0 design specification into an executable skill.

### Structure

- Single 1,800-line specification split into `SKILL.md` (core rules, modes,
  gates) plus `references/` loaded on demand (progressive disclosure).
- YAML frontmatter with trigger-oriented `description`.
- Consistent RFC 2119 wording (MUST / SHOULD / MAY).
- Persistent workspace files (`references/templates/`) instead of in-context objects.
- Deterministic checks moved into standard-library Python scripts:
  `verify_references.py`, `check_citations.py`, `manuscript_checks.py`.
- Integrity eval set (`evals/evals.json`, 10 trap cases).

### Scientific content

- Evidence model split into three axes: verification, appraisal (risk of bias
  with named tools, GRADE-style certainty), and support; abstract-only reading caps
  support at PARTIAL; `source_locator` and `access_level` added to the ledger.
- Mandatory counter-evidence search for central claims; PRISMA-S-style search log.
- Source preference by evidence need instead of a fixed hierarchy.
- New claim class `DERIVED` for recomputable values and proposed limitations.
- Reporting guidelines updated with versions (CONSORT 2025, SPIRIT 2025,
  TRIPOD+AI, TRIPOD-LLM, STARD-AI, CLAIM 2024, CHART, PRISMA family, ARRIVE 2.0,
  CHEERS 2022, SRQR/COREQ, SQUIRE 2.0, GRRAS, ...) and EQUATOR as canonical source.
- Statistics: protocol/SAP deviations, outcome switching, clustered data,
  paired model comparison, calibration, decision-curve analysis, fairness.
- Imaging AI: Metrics Reloaded, empty-mask handling, per-case reporting, overclaim table.
- Spin check for abstract, discussion, conclusion, title.
- Systematic reviews: protocol registration and a second human reviewer required.

### Ethics and responsibility

- AI is not an author (ICMJE/COPE); role renamed from "co-author" to assistant.
- Data protection (GDPR/DSGVO): de-identification check and stop condition.
- Documented consent for case reports; registration checks.
- Continuous AI-use log feeding the AI disclosure; AI-generated image policies.
- Publication ethics: duplicate publication, text recycling, preprints, image
  integrity, citation manipulation.
- Journal legitimacy check (indexing, DOAJ, COPE, warning signs, funder OA rules).
- Human author confirmation at gates 1, 7 and 12.

### Workflow

- New modes: C Targeted edit, D Response to reviewers (formalized), E Journal selection.
- Depth profiles Lite / Standard / Full.
- Twelve gates including data protection and reporting guideline.
- Fallbacks: sister journals when fewer than 3 exemplars; journal-agnostic drafting.
- Verification provenance: tool, date, and what could not be checked.
- Fetched content treated as data, not instructions (prompt-injection guard).
- Reviewer simulation in isolated contexts with an explicit limitation statement.
