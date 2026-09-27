# Journal Intelligence and Exemplars

Journal requirements change. Retrieve the current official requirements every
time a target journal is set; do not rely on stored model knowledge.

## Source hierarchy

1. official journal website and article-type instructions
2. official publisher author guidelines and editorial policies
3. official ethics, AI, data-sharing, and preprint policies
4. submission-system instructions
5. secondary websites: supplementary only, labelled as such

Every requirement in `journal_profile.yaml` carries a `source_url` and a
`retrieved` date. A requirement that could not be retrieved is `UNVERIFIED`.

## Journal profile

Use `templates/journal_profile.yaml`. Minimum fields for Standard depth:
article type, word limits (main text, abstract), abstract structure, reference
style and limit, figure/table limits, required declarations, reporting-guideline
requirement, AI policy, data/code availability policy, review model
(single/double blind), open-access model and APC.

## Legitimacy and fit check

Before investing in journal-specific work:

| Check | How |
|---|---|
| indexing | MEDLINE/PubMed (NLM catalog), Web of Science, Scopus where relevant |
| open-access legitimacy | DOAJ listing for OA journals; Think.Check.Submit. criteria |
| publisher membership | COPE membership, OASPA for OA publishers |
| warning signs | unsolicited invitations, very fast guaranteed review, hidden fees, fake metrics, editorial board not verifiable |
| scope fit | aims and scope statement vs. research question; recent similar papers |
| funder rules | open-access mandates (e.g. DFG, Horizon Europe, Plan S), data-sharing requirements |
| costs | APC, page/colour charges, waivers |

Report failures as blockers; do not label a journal "predatory" without evidence,
describe the specific failed checks instead.

## Mode E: journal selection

1. Extract scope keywords, article type, study design, and audience from the study.
2. Find journals that published comparable papers in the last 3–5 years.
3. Apply the legitimacy check.
4. Return a shortlist (3–6) with: scope match evidence (example papers),
   article-type acceptance, word limits, OA/APC, review model, indexing.
5. Never rank by "acceptance probability". Impact metrics may be listed if
   retrieved from an official source with date.

## Exemplar module

Published papers in the target journal show local conventions. Publication does
not prove every choice in them is optimal, so exemplars never override reporting
guidelines, evidence, or methodological best practice.

### Selection

Prefer papers that match several of: same journal, same article type, similar
research question, similar design, similar method and data modality, similar
outcome type, published in the last 3–5 years. Do not select by keyword overlap alone.

| Depth | Exemplars |
|---|---|
| Lite | none required |
| Standard | 3–5 |
| Full | 5–10 (max 15) |

Fewer than 3 suitable papers in the target journal: use sister journals from the
same publisher or field, and state this in the style profile.

### Aggregate style profile

Infer journal-level patterns, not the voice of one paper:

```yaml
title:        {typical_length, colon_use, design_named_in_title, claim_strength}
abstract:     {structured, headings, numbers_reported, conclusion_style}
introduction: {paragraphs, literature_density, final_paragraph_pattern}
methods:      {heading_depth, reproducibility_detail, software_reporting, statistics_detail}
results:      {text_vs_table_balance, metric_reporting, subsection_style}
discussion:   {opening_pattern, literature_comparison, limitations_location, implications, conclusion_strength}
language:     {first_person, passive_voice, terminology, hedging, spelling_variant}
references:   {typical_count, recency}
figures_tables: {typical_count, use_of_supplement}
sources:      [list of exemplar DOIs, all verified]
```

### Copyright-safe use

Never copy sentences, reproduce distinctive wording, imitate one author's voice,
closely paraphrase a single source, or reconstruct article text. Allowed:
section architecture, length tendencies, terminology patterns, typical rhetorical
moves, presentation conventions, degree of caution.

### Congruence audit (before finalization)

Compare against the style profile: structure, abstract density, methodological
granularity, section balance, results presentation, discussion depth, conclusion
restraint, terminology, reference density, figure/table integration. Output
`JOURNAL CONGRUENCE: High | Moderate | Low` with reasons. Scientifically justified
deviations are not penalized. This is not a publication probability.
