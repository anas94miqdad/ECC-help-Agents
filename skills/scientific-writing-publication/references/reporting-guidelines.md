# Reporting Guidelines and Appraisal Tools

**Snapshot date of this table: 2026-09.** Guidelines are updated regularly.
Before use, confirm the current version and official checklist on the EQUATOR
Network (equator-network.org) or the guideline's official website, and record
the version and URL in `reporting_guideline.md`. If the journal names a specific
version, the journal's choice wins.

## Selection table

| Study type | Guideline (version in snapshot) | Extensions / notes |
|---|---|---|
| Randomized controlled trial | CONSORT 2025 (replaces CONSORT 2010) | CONSORT-AI for AI interventions; cluster, non-inferiority, pilot, harms extensions; check each extension's alignment with the 2025 core |
| Trial protocol | SPIRIT 2025 (replaces SPIRIT 2013) | SPIRIT-AI |
| Observational (cohort, case-control, cross-sectional) | STROBE | RECORD for routinely collected data; STROBE-MR for Mendelian randomization |
| Diagnostic accuracy | STARD 2015 | STARD-AI for AI-based index tests |
| Prediction model development/validation | TRIPOD+AI (2024, replaces TRIPOD 2015) | TRIPOD-LLM for large language models; TRIPOD-Cluster for clustered data; TRIPOD-SRMA for reviews of models |
| Medical imaging AI | CLAIM (2024 update) | use together with TRIPOD+AI or STARD(-AI) as applicable |
| Early-stage clinical evaluation of AI decision support | DECIDE-AI | |
| Studies of chatbot / LLM health advice | CHART | |
| Reliability and agreement studies (e.g. inter-rater) | GRRAS | |
| Systematic review / meta-analysis | PRISMA 2020 | PRISMA-S (search reporting), PRISMA-DTA, PRISMA-NMA, PRISMA-IPD; MOOSE for observational meta-analyses |
| Scoping review | PRISMA-ScR | |
| Review protocol | PRISMA-P | register in PROSPERO or OSF |
| Case report | CARE | documented patient consent |
| Animal research | ARRIVE 2.0 | |
| Qualitative research | SRQR or COREQ | |
| Health economic evaluation | CHEERS 2022 | |
| Quality improvement | SQUIRE 2.0 | |
| Clinical practice guideline | AGREE II (appraisal), RIGHT (reporting) | |
| Study protocol, non-trial | SPIRIT-based or journal-specified | |

When several apply (e.g. imaging AI diagnostic study), combine them and
de-duplicate items in one checklist.

## Guideline profile

For each selected guideline record: name, version, official URL, retrieval date,
each item with status `PASS | PARTIAL | FAIL | NOT_APPLICABLE | UNVERIFIED`,
manuscript location (section + paragraph or line), and the action needed.
Many journals require the completed checklist as a submission file.

## Risk-of-bias and appraisal tools (for cited evidence)

| Evidence type | Tool |
|---|---|
| Randomized trials | RoB 2 |
| Non-randomized studies of interventions | ROBINS-I (check for the current version) |
| Non-randomized studies of exposures | ROBINS-E |
| Diagnostic accuracy studies | QUADAS-2; QUADAS-C for comparative accuracy |
| Prediction model studies | PROBAST; PROBAST+AI for AI-based models |
| Systematic reviews | AMSTAR 2 or ROBIS |
| Animal studies | SYRCLE risk-of-bias tool |
| Qualitative studies | CASP qualitative or JBI checklist |
| Certainty of a body of evidence | GRADE |

Full formal appraisal is required for systematic reviews. For other manuscripts,
a brief structured appraisal (tool name + overall judgement + main concern) is
recorded for sources supporting central claims.

## Metric guidance (imaging and ML)

- Metrics Reloaded (Maier-Hein et al., Nature Methods 2024): problem-aware
  selection of validation metrics.
- Metric-related pitfalls in image analysis validation (Reinke et al.,
  Nature Methods 2024).

Verify bibliographic details of these through Crossref/PubMed before citing,
like any other source.

## Key references verified at snapshot

Checked against PubMed and Crossref on 2026-09-27 with
`scripts/verify_references.py`. Re-run before citing; notices can appear later.

| Reference | DOI | Note |
|---|---|---|
| Maier-Hein L et al. Metrics reloaded: recommendations for image analysis validation. Nat Methods 2024;21(2):195-212 | 10.1038/s41592-023-02151-z | |
| Gallifant J et al. The TRIPOD-LLM reporting guideline for studies using large language models. Nat Med 2025;31(1):60-69 | 10.1038/s41591-024-03425-5 | |
| Sounderajah V et al. The STARD-AI reporting guideline for diagnostic accuracy studies using artificial intelligence. Nat Med 2025;31(10):3283-3289 | 10.1038/s41591-025-03953-8 | a correction notice exists; cite together with the correction as required |
| CHART Collaborative. Reporting guideline for chatbot health advice studies: the Chatbot Assessment Reporting Tool (CHART) statement. BMJ Med 2025;4(1):e001632 | 10.1136/bmjmed-2025-001632 | |
