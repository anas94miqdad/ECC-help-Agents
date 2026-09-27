# Compliance Matrix, Submission Package, Readiness Report

## Compliance matrix

One row per journal requirement and per reporting-guideline item
(`templates/compliance_matrix.csv`):

| requirement | source | manuscript_location | status | action |
|---|---|---|---|---|
| Structured abstract, max 250 words | Journal guidelines (URL, date) | Abstract | PASS | none |
| Data availability statement | Journal policy (URL, date) | Declarations | FAIL | add statement; authors confirm repository |
| CLAIM item: annotator expertise | CLAIM 2024 | Methods 2.3 | PARTIAL | add years of experience |

Status: `PASS | PARTIAL | FAIL | NOT_APPLICABLE | UNVERIFIED`. `NOT_APPLICABLE`
needs a one-line reason.

## Submission package

Generate only components the journal requires or the user asks for:

```text
01_Manuscript.docx
02_Title_Page.docx                  (separate if double-blind review)
03_Cover_Letter.docx
04_Highlights / Key_Points.docx
05_Graphical_Abstract_Brief.md      (brief for a designer; no AI-generated image if prohibited)
06_CRediT_Statement.docx
07_Declarations.docx                (ethics, consent, funding, COI, data/code availability, AI use)
08_Reporting_Checklist              (guideline checklist with page/line numbers)
09_Response_to_Reviewers.docx       (revisions only)
10_Supplementary_Material.docx
11_Reference_Audit.csv              (verification output)
12_Submission_Readiness_Report.md
```

Double-blind review: remove author names, affiliations, acknowledgments, funding
identifiers, self-identifying citations, and file metadata from the anonymized
manuscript.

## Cover letter

States: article type, title, main finding in one or two sentences with the
evidence level, why it fits the journal's scope, confirmation of originality and
no concurrent submission (authors confirm), preprint status, suggested/opposed
reviewers only if the authors supply them. No overclaiming.

## Submission readiness report

```text
MODE / DEPTH:
TARGET JOURNAL: name, guidelines URL, retrieval date
REPORTING GUIDELINE(S): name, version

A. Scientific readiness      research question, design, methods, statistics,
                             results, interpretation, limitations, novelty
B. Evidence readiness        verified references (n/N), unsupported claims,
                             sources with high risk of bias behind central claims,
                             counter-evidence searched, currency of literature
C. Journal readiness         scope, article type, word counts, abstract, figures,
                             tables, references, declarations, supplement
D. Reporting readiness       checklist items PASS/PARTIAL/FAIL/UNVERIFIED counts
E. Ethics and data protection de-identification confirmed, ethics, consent,
                             registration, AI disclosure drafted from log
F. Verification provenance   which tools checked what, and when; what could not be checked
G. Critical blockers         one line each, with the corrective action and owner
H. Author confirmations      gates 1, 7, 12 confirmed by whom and when

JOURNAL CONGRUENCE: High / Moderate / Low (reasons)
Note: this report is not a publication probability.
```

Example blockers:

```text
BLOCKER: No independent test cohort; the internal split is not patient-level.
         Action: authors confirm split unit or re-split and re-run.
BLOCKER: Two references supporting the primary novelty claim are UNVERIFIED.
BLOCKER: Journal requires a data availability statement.
BLOCKER: Primary endpoint differs between registration and Methods.
```
