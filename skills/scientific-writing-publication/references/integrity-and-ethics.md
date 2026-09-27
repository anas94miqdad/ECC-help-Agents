# Integrity, Ethics, and Data Protection

## Never fabricate

Never invent any of the following. Mark unknowns as `[MISSING: <what>]`.

- references, DOIs, PMIDs, authors, journal names, titles, publication dates
- study populations, sample sizes, inclusion/exclusion counts, flow-diagram numbers
- statistical values: p-values, confidence intervals, effect estimates, Dice, AUC,
  sensitivity, specificity, calibration measures
- methods, software and framework versions, hardware, hyperparameters, random seeds
- ethics approvals, vote numbers, consent procedures, trial registrations
- funding statements, conflicts of interest, author contributions
- repository links, dataset names, accession numbers, model weights
- quotes attributed to people or sources
- figures, images, or image panels
- journal requirements and editorial policies

### Allowed with labelling (`DERIVED`)

| Allowed | Condition |
|---|---|
| arithmetic from supplied numbers (percentages, totals, differences) | show the formula or source cells; recomputable |
| proposed limitations inferred from the design | marked as proposal; authors confirm |
| proposed wording for declarations | only after the journal policy was retrieved; authors confirm facts |
| analysis code or an analysis plan for a missing analysis | never report its results as performed |

Not allowed: imputing missing statistics, back-calculating CIs from rounded values
and presenting them as reported, or "typical" values from other studies.

## Authorship and responsibility

- Authorship follows the ICMJE criteria (substantial contribution, drafting or
  critical revision, final approval, accountability). Contributions are described
  with CRediT where the journal requires it.
- An AI system cannot meet these criteria and MUST NOT be listed as author or
  described as co-author (ICMJE, COPE position, and major publisher policies).
- The skill does not decide authorship order, disputes, or ghost/gift authorship;
  it flags them for the authors.

## Data protection (GDPR / DSGVO and local law)

Before any study material is processed:

1. Ask whether the material is de-identified. Default assumption for clinical
   material: it might not be.
2. Scan supplied text for direct identifiers: names, dates of birth, exact
   admission dates, patient or case numbers, addresses, phone numbers, emails,
   DICOM header fields (PatientName, PatientID, PatientBirthDate, InstitutionName),
   burned-in image annotations, faces or tattoos in photos.
3. If found: stop processing that item, tell the user which field type was found
   (not its value), and ask for a de-identified version.
4. Rare diseases, small subgroups, or detailed timelines can re-identify patients
   even without direct identifiers. Flag cell counts below 5 and detailed
   case timelines for author review.
5. Do not copy study data into outputs beyond what the manuscript needs.
6. Institutional rules may prohibit sending study data to external AI services at
   all. Remind the user once to check their institution's policy; do not decide it.

## Ethics, consent, registration

- Ethics committee approval and vote number: required from documents, never assumed.
- Waiver of consent: must be stated by the ethics committee, not inferred.
- Case reports and identifiable images: documented written patient consent.
- Clinical trials: prospective registration (e.g. ClinicalTrials.gov, DRKS, ISRCTN)
  with registration number and date; flag retrospective registration.
- Systematic reviews: protocol registration (e.g. PROSPERO, OSF) with ID.
- Animal studies: approval authority and number; ARRIVE 2.0.

## AI-use log and disclosure

Maintain `ai_use_log.csv` throughout the session:

```text
date,tool,version_or_model,purpose,manuscript_section,human_verified_by
```

At submission:

1. Retrieve the journal's and the publisher's AI policy (URL + date).
2. Draft the disclosure from the log, in the location the journal requires
   (Methods, Acknowledgments, or a dedicated declaration).
3. Many journals prohibit AI-generated or AI-altered images and figures; check.
4. Authors confirm the final text. Responsibility remains with them.

## Publication ethics (COPE-aligned)

Flag for the authors, never resolve silently:

- **Duplicate or redundant publication** and salami slicing: overlap with prior
  papers, theses, or conference proceedings from the same data.
- **Text recycling** from the authors' own earlier papers: rewrite or cite;
  follow journal policy.
- **Preprints and conference abstracts**: disclose per journal policy.
- **Image integrity**: no selective enhancement, splicing, or duplication; state
  any processing applied uniformly.
- **Citation manipulation**: do not add citations to the target journal, an editor,
  or the authors' own work unless they support a specific claim. Exemplar papers
  are for style analysis; they are cited only if scientifically relevant.
- **Spin and selective reporting**: see `manuscript-sections.md`.
- **Plagiarism**: never copy or closely paraphrase distinctive text from any source,
  including exemplars.
- **Conflicts of interest**: collected from authors, not inferred.
