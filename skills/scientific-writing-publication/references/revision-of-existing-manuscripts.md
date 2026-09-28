# Mode B: Optimize or Rebuild an Existing Manuscript

Use when the user uploads an unfinished, weak, or badly structured manuscript
(DOCX, PDF, DOC/ODT/RTF, Markdown) and wants it brought to a target level.
The existing manuscript is the **primary content source**: its data, results,
methods descriptions, citations, and the authors' terminology are preserved and
reorganized. Nothing is added that is not in the manuscript, the study files, or
verified literature.

## Principles

1. **Preserve, then improve.** Every content block of the original ends up in the
   revision or is discarded with a stated reason. Nothing disappears silently.
2. **No new facts.** New numbers, methods details, or results require a source
   (supplied data file, protocol, author answer); otherwise `[MISSING: ...]`.
3. **Writing cannot repair design.** Separate what text can fix from what needs
   author information, new analyses, or a changed framing (see fix classes).
4. **Authors decide the intervention level** after seeing the diagnosis.
5. **Traceability.** Every revised paragraph names its source blocks
   (`<!-- src: P0012 -->`), so authors and `compare_versions.py` can audit it.
6. **The original file is never overwritten.**

## Step 1: Intake and extraction

```bash
python3 scripts/extract_manuscript.py manuscript.docx --out-dir manuscript-workspace/
```

- Produces `*.inventory.md` (readable, block IDs), `*.inventory.json`, and
  `*.clean.md` (no block IDs) for running `manuscript_checks.py` and
  `check_citations.py` on the original.
- Prefer DOCX over PDF. PDF extraction loses tables, superscript citations, and
  some paragraph boundaries; if only a PDF is supplied, ask once for the DOCX,
  and otherwise check tables and figures manually against the PDF.
- If the host offers a dedicated DOCX or PDF skill, it MAY be used for extraction;
  the block-ID inventory is still created.
- Read the extraction warnings and act on them:

| Warning | Action |
|---|---|
| unaccepted tracked changes | ask whether to accept all, reject all, or keep for review |
| comments present | import each comment as an open task in `missing_information.md` or the revision plan |
| reference-manager fields (Zotero, EndNote, Mendeley, Citavi) | tell the authors that the rebuilt file has static citations; they re-link with their reference manager, or the revision keeps citation keys |
| equations as placeholders | check each equation manually |
| scanned PDF | OCR first, or ask for the source file |
| author names in metadata | remove before double-blind submission |

- Also ask for (once, only if not supplied): target journal and article type,
  study data/results files, protocol/SAP, reporting checklist if one exists,
  prior reviewer comments, and the desired language of the output.
- Run the data-protection check (gate 2) on the extracted text.

## Step 2: Content inventory

From the inventory, build a content map. Classify each block by **content type**,
independent of where it currently sits:

```text
BACKGROUND | GAP | AIM | HYPOTHESIS | DESIGN | SETTING | PARTICIPANTS | DATA |
INTERVENTION | REFERENCE_STANDARD | METHOD | STATISTICS | ETHICS | RESULT |
INTERPRETATION | COMPARISON_LITERATURE | LIMITATION | IMPLICATION |
CONCLUSION | DECLARATION | FIGURE_TABLE | REDUNDANT | OFF_TOPIC
```

Also record per block: claims (to the evidence ledger), numbers (the number
registry is the set of numbers in the original plus data files), citations, and
the terminology used for key concepts (keep it unless it is wrong).

## Step 3: Diagnosis

### 3a. Structural map

For each block: current section, content type, correct target section. Typical
findings in weak manuscripts:

| Finding | Example |
|---|---|
| results inside Methods | performance numbers in the data description |
| methods inside Results | preprocessing or statistics introduced in Results |
| interpretation inside Results | "which shows the model is clinically useful" |
| new results in Discussion | numbers that appear nowhere in Results |
| aim missing or vague | no explicit objective at the end of the Introduction |
| textbook introduction | long general background, no specific gap |
| limitations missing or hidden | none, or only "small sample size" |
| abstract not matching body | numbers or claims absent from the main text |
| redundancy | same content repeated across sections |
| missing required sections | declarations, data availability, ethics statement |

### 3b. Maturity scorecard

Score each dimension 1–5 before revision (and again after). Anchors:
1 = absent or wrong, 2 = major problems, 3 = acceptable with clear gaps,
4 = good with minor gaps, 5 = meets the target journal's standard.

| Dimension | What 5 looks like |
|---|---|
| Research question and aim | specific, answerable, stated at end of Introduction and matching the design |
| Structure | article-type architecture; every content type in its correct section |
| Introduction and gap | concise, specific gap supported by current literature |
| Methods reproducibility | all reporting-guideline methods items present |
| Results reporting | complete, with denominators, uncertainty, primary before secondary |
| Statistics and validation | appropriate, correctly reported, no leakage or clustering errors |
| Discussion and claims | evidence-calibrated, compared with literature, honest limitations, no spin |
| Evidence and citations | verified, appropriate, correctly placed |
| Reporting-guideline completeness | all applicable items PASS or justified N/A |
| Journal fit and formatting | scope, article type, limits, declarations met |
| Language and clarity | precise, consistent terminology, no filler |

### 3c. Gap analysis

Run the reporting-guideline checklist, the journal profile (if a target journal
is known), `manuscript_checks.py`, `check_citations.py`, and
`verify_references.py` on the original. List every gap with a **fix class**:

| Fix class | Meaning | Who acts |
|---|---|---|
| TEXT | fixable by rewriting or restructuring existing content | skill |
| INFO | needs a fact only the authors have (ethics number, scanner model) | authors |
| ANALYSIS | needs an analysis that was not done (CI, paired test, calibration) | authors run it; skill may propose the plan |
| DESIGN | cannot be fixed by writing (no external validation, slice-level split) | reframe claims, state as limitation, or change article type/journal |

## Step 4: Target level and intervention level

Define the target explicitly: target journal (or journal tier/type), article type,
word and element limits, reporting guideline, language.

Then recommend one intervention level and let the authors confirm **[AUTHOR]**:

| Level | When | What changes |
|---|---|---|
| L1 Polish | structure sound, scorecard mostly >= 4 | language, terminology, consistency, formatting; sentence order kept |
| L2 Section revision | 1–3 sections weak | rewrite weak sections; structure otherwise kept |
| L3 Restructure | content present but misplaced; scorecard structure <= 2 | move, merge, split blocks into the correct architecture; rewrite transitions |
| L4 Rebuild | aim unclear, architecture wrong, or article type changes | new outline from the content map; text rewritten; original blocks reused as content, not wording |

At every level the content-preservation rules apply. L3 and L4 are the typical
choice for badly structured manuscripts.

## Step 5: Revision blueprint

Before writing, produce the blueprint and show it to the authors:

```text
New outline (headings, target word budget per section)
  for each section: source blocks (P/T/F/C IDs) in intended order
Move list:        P0014 Results -> Methods 2.4 (preprocessing description)
Merge list:       P0003 + P0009 -> Introduction para 2 (duplicate background)
Split list:       P0021 -> Results (numbers) + Discussion (interpretation)
Discard list:     P0030 = duplicate of P0012; P0031 = out of scope (reason each)
New content:      only placeholders or sourced additions (with source)
Open questions:   INFO and ANALYSIS items for the authors
```

## Step 6: Rewrite rules

- Keep every number exactly as in the source (same value, unit, rounding) unless a
  supplied data file shows a different value; then flag the discrepancy, do not
  choose silently.
- Keep the original citations attached to the claims they support; verify them;
  replace only when verification fails or a more appropriate primary source is
  needed, and record the change.
- Keep the authors' key terminology; harmonize synonyms to one term.
- Downgrade overclaims to evidence-matched wording (spin check).
- Methods and Results text is rewritten only from the original, study files, or
  author answers; never from general knowledge of "how such studies are done".
- Add required but missing elements as structured placeholders:
  `[MISSING: ethics committee and vote number]`.
- Carry reviewer comments embedded in the original into Word comments:
  `{>>Original comment: ... Status: addressed in 2.3 / needs author input<<}`.
- Translation (e.g. German draft to English journal) is allowed; the source-marker
  rules still apply; state that native-speaker or professional language review
  is recommended when the journal requires it.
- Mark every paragraph with `<!-- src: ... -->`; list discarded blocks once with
  `<!-- discarded: ID = reason; ... -->`.

## Step 7: Verification

```bash
python3 scripts/compare_versions.py manuscript-workspace/<name>.inventory.json revised.md --data results.csv
python3 scripts/manuscript_checks.py revised.md --abstract-limit 250 --main-limit 3500
python3 scripts/check_citations.py revised.md
python3 scripts/verify_references.py manuscript-workspace/source_library.csv
```

All of the following must hold before delivery:

- no uncovered original blocks; every discard has a reason
- no new numbers without a source (each is either traced to a data file or removed)
- no original results lost unintentionally
- abstract numbers found in the main text
- citations consistent; references verified or flagged

Then run the reviewer simulation (`review-and-revision.md`) on the revision and
re-score the maturity scorecard.

## Step 8: Deliverables

```bash
python3 scripts/build_docx.py revised.md --out <name>_revised.docx --double-spacing --line-numbers
```

1. `<name>_revised.docx`: clean revised manuscript; open issues as Word comments,
   placeholders highlighted. The original file stays unchanged.
2. **Tracked-changes view**: tell the authors to open the original in Word and use
   Review > Compare > Compare documents with the revised file (LibreOffice:
   Edit > Track Changes > Compare Document). For L3/L4 rebuilds the comparison is
   large; the change report is the better guide.
3. `revision_report.md` (template in `templates/revision_report.md`): diagnosis,
   scorecard before/after, structural changes, content changes with reasons,
   discarded blocks, open questions by fix class, verification results,
   remaining blockers.
4. `traceability.csv`: revised paragraph -> source block IDs (from the markers).
5. Updated workspace files (ledger, missing information, compliance matrix).

State clearly: the revision improves presentation and compliance of the existing
work; it does not change the underlying study, and remaining DESIGN issues are
listed as such.
