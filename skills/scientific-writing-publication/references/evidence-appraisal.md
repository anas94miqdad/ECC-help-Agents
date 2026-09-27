# Evidence: Search, Verification, Appraisal, Support

## 1. Search to answer evidence needs

Search for specific evidence needs, not to collect references. Typical needs:
clinical background, epidemiology, standard of care, methodological background,
prior methods and their performance, validation strategies, known limitations,
implementation barriers, regulatory or policy context, and the research gap.

### Source preference (biomedical)

Choose by evidence need, not a fixed pyramid:

| Need | Preferred source types |
|---|---|
| effect of an intervention | systematic reviews/meta-analyses of RCTs, then RCTs |
| diagnostic or prognostic performance | systematic reviews of accuracy/prediction studies, then well-designed primary studies |
| epidemiology | registries, population-based cohorts, official statistics |
| standard of care | current clinical guidelines, consensus statements |
| methods | original methods papers, methodological guidance, standards |
| regulation | official regulatory documents |

Label lower-quality sources (narrative reviews, editorials, preprints, grey
literature) as such. Preprints are cited only if the journal allows it and they
are marked as not peer reviewed.

### Search log (reproducibility, PRISMA-S style)

Record every search in `search_log.csv`: date, database/interface, full query
string, filters and limits, hits, number screened, number kept. For systematic
reviews this is mandatory and reported; for other manuscripts it is kept in the
workspace so the evidence base can be audited.

### Counter-evidence search (mandatory)

Searching only for supporting evidence is confirmation bias. For every central
claim (novelty, superiority, clinical relevance, main comparison), run at least
one search designed to find contradicting, null, or negative results, for example
by adding terms like `no difference`, `failed`, `external validation`,
`limitations`, `bias`, or by searching for the competing method's best results.
Record the query and outcome in the ledger (`counter_evidence_checked`).

### Systematic reviews

The skill supports protocol writing, search strategy drafting, deduplication,
PRISMA flow bookkeeping, and reporting. It does not replace the second
independent human reviewer required for screening, data extraction, and risk-of-bias
assessment. Without a registered protocol and two human reviewers, stop and say so.

## 2. Verification (does the source exist?)

Check against Crossref, PubMed, or the publisher record, preferably with
`scripts/verify_references.py`:

- title, authors (at least first author), journal, year, volume/issue/pages
- DOI resolves to the same title; PMID matches where applicable
- publication type (original, review, editorial, preprint, erratum)
- retraction, expression of concern, correction (Crossref update notices, which
  include Retraction Watch data, and PubMed publication types)

| State | Meaning |
|---|---|
| `VERIFIED` | metadata confirmed in an authoritative record |
| `PARTIALLY_VERIFIED` | exists, but some metadata unconfirmed or mismatched |
| `UNVERIFIED` | not yet checked or check not possible |
| `REJECTED` | does not exist or does not match the claimed record |
| `RETRACTED` | retracted or withdrawn; expression of concern noted separately |

An absent retraction notice is not proof of absence. Report it as
"no notice found in <database> on <date>".

## 3. Appraisal (how trustworthy is it?)

Record in `source_library.csv` for sources that support central claims:

- `design`: RCT, cohort, diagnostic accuracy, systematic review, ...
- `appraisal_tool`: RoB 2, ROBINS-I, QUADAS-2, PROBAST+AI, AMSTAR 2, ...
- `risk_of_bias`: low / some concerns / high / not assessed
- `main_concern`: one sentence (e.g. "spectrum bias: case-control sampling")
- `certainty` (GRADE-style, for the body of evidence behind a central claim):
  high / moderate / low / very low

Wording in the manuscript follows certainty: "reduces" (high), "probably reduces"
(moderate), "may reduce" (low), "the evidence is very uncertain" (very low).

## 4. Support (does it support this claim?)

| Class | Meaning |
|---|---|
| `DIRECT` | source explicitly supports the claim as worded |
| `PARTIAL` | supports part of the claim, or only the abstract was read |
| `INDIRECT` | relevant, but does not establish the claim |
| `CONTRADICTED` | source conflicts with the claim |
| `UNSUPPORTED` | no valid supporting evidence found |

Rules:

- `access_level = abstract-only` caps support at `PARTIAL`.
- `source_locator` names where in the source the support is (page, table, figure,
  section). Without a locator, support is at most `PARTIAL`.
- `CONTRADICTED` and `UNSUPPORTED` claims are removed or explicitly qualified.
- Prefer the primary source over a review citing it, when the claim is a specific
  finding.

## 5. Evidence ledger

Use `templates/evidence_ledger.csv`. Columns:

```text
claim_id, claim_text, claim_class, manuscript_location, source_id, doi_or_pmid,
access_level, source_locator, support, verification, risk_of_bias, certainty,
counter_evidence_checked, notes
```

`manuscript_location` is where the claim sits in the manuscript; `source_locator`
is where the evidence sits in the source. The ledger is mandatory at Standard and
Full depth; at Lite depth only for claims touched in the edit.

## 6. Claim-to-citation audit

For each externally sourced claim: claim present, citation present, citation
verified, citation relevant, claim fully supported, claim stronger than evidence,
more primary or more recent source available.

Output per claim: `PASS | WEAK_SUPPORT | PARTIAL_SUPPORT | UNSUPPORTED |
CONTRADICTED | SOURCE_NOT_VERIFIED`. Every critical non-PASS item is resolved
before gate 9 passes.
