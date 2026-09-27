# Statistical and Machine-Learning Integrity

Flag issues; never invent analyses or outputs that were not performed. Offering
an analysis plan or code is allowed; the authors run it and supply the results.

## 1. Design and pre-specification

- protocol, statistical analysis plan (SAP), or registration available?
- primary endpoint identical across registration, protocol, Methods, Results, Abstract
  (outcome switching check)
- analyses not pre-specified are labelled exploratory or post hoc
- deviations from protocol/SAP are reported with reasons
- no HARKing: hypotheses in the Introduction match what was planned
- sample-size justification or power calculation, or an explicit statement that
  none was done and why

## 2. Analysis

- choice of test fits data type, distribution, and pairing
- assumptions checked (normality, proportional hazards, linearity, independence)
- multiplicity: correction or explicit rationale for none
- effect sizes with confidence intervals, not p-values alone
- exact p-values (e.g. p = 0.032, p < 0.001), not "p < 0.05" or "NS"
- statistical significance distinguished from clinical relevance
  (minimal clinically important difference where defined)
- missing data: amount per variable, mechanism assumptions, handling method,
  sensitivity analysis
- confounding: adjustment set justified (e.g. causal diagram) in observational studies
- subgroup analyses pre-specified, interaction tests reported, not over-interpreted
- sensitivity and robustness analyses reported

## 3. Non-independent data (frequent error)

Several lesions, fractures, teeth, eyes, images, or visits per patient are
**clustered**. Check:

- unit of analysis stated (patient, lesion, image, slice)
- CIs and tests account for clustering (patient-level bootstrap, mixed models,
  GEE, or aggregation per patient)
- data splits are at patient level (see ML section)
- denominators are reported for each unit

## 4. Model comparison

"Model A 0.87 vs. model B 0.85" is not evidence of superiority. Require:

- paired comparison on the same test cases
- CI of the difference (e.g. paired bootstrap at patient level) or an appropriate
  paired test (e.g. DeLong for correlated AUCs, Wilcoxon signed-rank for per-case scores)
- same preprocessing, data, and tuning budget for baselines
- strong, current baselines, not only weak or outdated ones
- claims of non-inferiority need a pre-specified margin

## 5. Machine learning

- train / validation / test independence at **patient level**; site level where
  generalization across sites is claimed
- hyperparameter tuning and model selection only on validation data;
  test set used once
- nested cross-validation when data are too small for a hold-out test set
- no preprocessing leakage (normalization statistics, feature selection,
  imputation, or augmentation fitted on data that includes the test set)
- no temporal leakage in longitudinal data
- class imbalance handled and reported; metrics suited to prevalence
  (e.g. PR curves when positives are rare)
- external validation on independent data, or the absence stated as a limitation
- calibration (calibration plot, slope, intercept) for risk predictions,
  not only discrimination
- clinical utility claims need decision-curve analysis or a clinical study;
  accuracy alone does not show utility
- subgroup performance and fairness across relevant groups (sex, age, site, scanner)
- uncertainty of all performance estimates (CIs)
- failure-case analysis
- random seeds, number of runs, and variance across runs
- code, environment, and model availability (verified, not assumed)

## 6. Red flags that trigger an explicit reviewer note

- test performance higher than validation performance without explanation
- very high performance on small data without external validation
- results only as means without dispersion or CIs
- many metrics reported, one highlighted
- "trend towards significance"
- conclusions based on secondary or post hoc outcomes when the primary was null
