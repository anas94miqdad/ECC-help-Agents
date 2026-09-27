# Manuscript Sections, Spin, Citations, Consistency

## Architecture

Structure = study design + article type + journal requirements + reporting
guideline, refined by the exemplar style profile. The style profile never
overrides mandatory journal or guideline items.

## Writing plan (before drafting, Mode A)

Article type, target journal, reporting guideline(s), exemplar set, style profile,
research question, core contribution, primary claims with ledger IDs, section
outline with word budget, missing information, major scientific risks, analyses
still missing. Drafting may start with explicit `[MISSING: ...]` placeholders only
if the missing items are non-central; central gaps block drafting.

## Title

Accurate, no overclaiming, names the design where required or useful
(e.g. "a retrospective multicentre study"), uses journal-typical terminology,
consistent with the actual scope.

## Abstract

- follows the journal's structure and word limit
- contains only results that appear in the main text, with identical numbers
- reports key quantitative results with uncertainty (CI)
- conclusion matches the primary endpoint and the evidence level
- run `scripts/manuscript_checks.py` for the numeric abstract-to-body check

## Introduction

Problem, then current knowledge, then the specific unresolved gap, then why it
matters, then objective/hypothesis. No textbook-style openings. The final
paragraph states the objective, the research question, the hypothesis where
applicable, and the contribution.

## Methods

Maximize reproducibility; follow the reporting-guideline items. Report where
applicable: design, setting, dates, participants and eligibility, data sources,
variables and definitions, reference standard, interventions, sample size,
statistical methods, software with versions, ethics, consent, registration,
data and code availability. Never invent missing details; use `[MISSING: ...]`.

## Results

Findings without interpretation; consistent with tables and figures; correct
denominators; participant flow (diagram where required); missing data per
variable; primary before secondary outcomes; no methods that were not described
in Methods; no selective reporting of favourable metrics.

## Discussion

Principal finding, then comparison with prior literature (including conflicting
studies), possible explanations, implications justified by the evidence,
strengths, limitations, future research, restrained conclusion.

Explicitly prevent: causal language for associations, generalization beyond the
study population or setting, clinical-utility claims without clinical evidence,
superiority claims without a paired statistical comparison, and omission of
conflicting literature found in the counter-evidence search.

## Spin check (abstract, discussion, conclusion, title)

Spin means reporting that makes results look more favourable than they are.
Check for:

| Pattern | Example |
|---|---|
| focus on secondary outcomes when the primary was null | "Although the primary endpoint was not met, patients showed significant improvement in ..." |
| within-group change presented as between-group effect | "Symptoms improved significantly in the intervention arm" |
| non-significant result described as trend or as equivalence | "a trend towards benefit", "comparable" without equivalence testing |
| subgroup result generalized | "effective in older patients" from an unplanned subgroup |
| causal language in observational research | "X reduces Y" from a cohort study |
| accuracy presented as clinical benefit | "improves patient care" from Dice/AUC alone |
| conclusion omits important harms or limitations | |

Any hit is rewritten to evidence-matched wording and logged.

## Citation placement

- attach each citation to the exact claim it supports; avoid dumping several
  references at the end of a long paragraph
- when references support different parts of a sentence, place them separately
- every citation answers: which claim does this source support?
- no citations added for journal fit or self-promotion

## Consistency audits (gate 8)

| Audit | Checks |
|---|---|
| Abstract to main text | every number and claim in the abstract exists in the main text with the same value |
| Methods to Results | every result has a described method; every described analysis has a result or a stated reason |
| Text to tables/figures | numbers, denominators, units, rounding match |
| Endpoints | primary endpoint identical in registration, Methods, Results, Abstract |
| Terminology | one term per concept throughout |
| Placeholders | no `[MISSING: ...]` left at submission; each either resolved or listed as a blocker |

## Reference quality control

Remove duplicates; DOI syntax and DOI-to-title match; year, authors, journal;
retractions and corrections; every in-text citation resolves to an entry and every
entry is cited; numbering order where the style requires it; apply the journal's
style (Vancouver, AMA, APA, Harvard, publisher-specific) only after verification.
Use `scripts/verify_references.py` and `scripts/check_citations.py`.

## Style

Precise, concise, evidence-calibrated, discipline-appropriate, terminology-consistent.
Avoid promotional terms unless objectively justified: groundbreaking, revolutionary,
remarkable, unprecedented, highly innovative, game-changing, paradigm shift,
novel (when novelty is not demonstrated), and filler such as "It is important to
note that", "plays a crucial role", "in today's world". Use the spelling variant
(British/American) the journal expects. `scripts/manuscript_checks.py` flags
common hype terms.
