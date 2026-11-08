# effect_sizes.csv: column definitions

One row per confirmatory paired comparison discussed in the manuscript (V4: A1 all preregistered comparisons; A3
joint-grid comparisons deciding gates G3/G4; A3F factorial-cell comparisons deciding G3F/G4F plus those discussed
in the text and Table S30). Paired by seed (seeds 21-40, n = 20 runs per arm); the run is the unit.

| column | definition |
|---|---|
| family | Holm family: campaign x outcome (A1, A3, A3F) |
| campaign | A1 (matched review), A3 (selective holds, joint grid), A3F (amendment 1 factorial cells) |
| hypothesis | preregistered hypothesis (H1a-H1d, H3a-H3c) |
| gate_role | gate the row decides (G1, G2, G3, G4, G3F, G4F) or 'text' / 'text/Table S30' when only discussed |
| comparison | arm - reference (sign convention of every difference) |
| arm, reference | pipeline arms |
| outcome, unit | O1, O2 (observations per run), NLX (record-seconds per run), W (seconds per observation), AV5 (fraction) |
| design_point | scenario (A1: S05 = E5, S08 = E8, S12 = E11b, S99 = mixed) or grid point / factorial cell |
| n_seeds | number of paired seeds |
| mean_arm, mean_ref | mean of the outcome over seeds for the arm and the reference |
| mean_diff | mean paired difference (arm - reference), absolute units |
| ci95_lo, ci95_hi | 95 % percentile bootstrap CI of mean_diff as reported in results/v4/summary (10,000 resamples; seeded with [20261104, CRC32(comparison key)]); reproduced bit-for-bit by the audit |
| audit_ci95_lo, audit_ci95_hi | the audit's independent 95 % CI (fresh numpy default_rng(20261104) per comparison); differs from ci95 only by Monte-Carlo error |
| rel_diff | mean_diff / mean_ref (relative to the comparator mean); NA if mean_ref = 0 |
| margin | preregistered practical margin (O1 1; O2 1 % of the cell's median reachable count: 72 or 71.95 in A1, 28.8 in A3/A3F; NLX 60; W 0.6; AV5 0.01) |
| direction_preferred | 'lower' or 'higher' is better for the outcome; 'better'/'worse' classes refer to the arm |
| p_holm | Holm-adjusted two-sided Wilcoxon signed-rank p (scipy default: exact without ties/zeros, else normal approximation), within the family |
| m_family | number of comparisons in the Holm family |
| class_reported | class in results/v4/summary/*_comparisons.csv (as used by the manuscript) |
| class_audit | class from the audit's independent implementation (base class: identical, equivalent, better, worse, different = 'different, within margin', inconclusive) |
| class_note | robustness notes: Monte-Carlo-fragile class; point estimate beyond the margin although classed 'different, within margin'; CI bound exactly at the margin; class under exact Wilcoxon p |
