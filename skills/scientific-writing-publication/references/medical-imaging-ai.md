# Medical Imaging AI and Segmentation

Apply together with `statistics-ml-checklist.md` and the CLAIM checklist
(plus TRIPOD+AI or STARD/STARD-AI where applicable).

## Items to inspect

| Area | Items |
|---|---|
| Data | origin, institutions, time period, patient selection, inclusion/exclusion flow, prevalence, demographics |
| Acquisition | modality, scanner vendors and models, field strength or kVp, slice thickness, reconstruction kernel, contrast protocol |
| De-identification | method used, DICOM tags removed, burned-in text, defacing for head imaging |
| Reference standard | definition, who annotated, number of annotators, expertise and years of experience, annotation tool, instructions, blinding, adjudication of disagreement |
| Agreement | inter- and intra-rater reliability with appropriate statistic (e.g. ICC with model stated, Dice between raters); report per GRRAS |
| Splits | patient-level split, site-level split if generalization is claimed, counts per split, no overlap verified |
| Preprocessing | resampling, cropping, intensity normalization, windowing; fitted on training data only |
| Augmentation | types and parameters; applied to training data only |
| Model | architecture, pretrained weights and their source, framework name and version, number of parameters |
| Training | loss, optimizer, learning rate and schedule, batch size, epochs, stopping criterion, hardware, training time, random seeds |
| Evaluation | metrics and justification, per-case distribution, CIs, subgroup and per-site results, failure cases |
| Availability | code, weights, containers, data access procedure, license (verified) |

## Segmentation metrics

Choose metrics by the clinical question, following Metrics Reloaded and the
metric-pitfalls literature (see `reporting-guidelines.md`). Combine an overlap
metric with a boundary/distance metric, and add object-level metrics where
counting or detecting structures matters.

| Metric | Use | Pitfalls |
|---|---|---|
| Dice Similarity Coefficient / IoU | volumetric overlap | biased against small structures; insensitive to boundary errors; undefined when reference and prediction are both empty |
| Hausdorff distance (95th percentile preferred) | worst boundary error | sensitive to outliers; undefined for empty masks; report units (mm) |
| Average symmetric surface distance | mean boundary error | undefined for empty masks |
| Normalized surface Dice | boundary agreement within a tolerance | tolerance must be justified clinically |
| Lesion/object-level sensitivity, precision, F1 | detection of multiple objects | matching criterion must be stated |
| Volume difference / Bland–Altman | volumetric agreement | not a substitute for overlap |

Always state:

- how empty reference and/or prediction masks were handled
  (excluded, scored as 1 or 0, reported separately)
- aggregation: per case, per patient, per structure; mean and median with
  dispersion (SD/IQR) and CIs
- whether results are reported per class or averaged, and how
- the physical spacing used for distance metrics

## Typical claims to downgrade

| Overclaim | Evidence-matched wording |
|---|---|
| "The model is ready for clinical use." | "The model showed high segmentation agreement on internal test data; clinical validation is pending." |
| "Outperforms state of the art." | "Achieved a higher mean Dice than <baseline> on <dataset> (difference 0.02, 95 % CI ...)." Only if a paired comparison exists. |
| "Generalizes across scanners." | Only with a per-scanner or external evaluation; otherwise a limitation. |
| "Reduces reading time." | Only with a reader study measuring reading time. |
