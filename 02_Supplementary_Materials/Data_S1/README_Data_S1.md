# Data S1 — per-cell result tables and comparisons (V9)

Supplementary data of the article *Provenance-Bound Trust-Aware Ingestion for Industrial IoT Edge-to-Cloud Data
Pipelines: Per-Identity Conflict Containment and Its Security–Availability Trade-offs*. Every file is written by the
analysis scripts of the research package from the stored per-run raw results; this folder was assembled by
`tools/v9/build_data_s1.py`, which copies the generated files and computes nothing itself (the control-trace JSON
is only converted to CSV).

42 CSV files: UTF-8, comma-separated, one header row. `SHA256SUMS.txt` lists their SHA-256; verify with
`sha256sum -c Data_S1/SHA256SUMS.txt` from the folder that contains `Data_S1/`.

## Which comparator the tables use

All B5 and B5s rows of the simulation stages in the top-level tables come from the corrected implementation of the
feed-level comparator (`src/pbti/b5_corrected.py`), rerun on the original seeds and configurations of every
simulation stage (`experiments/v9/run_all_b5c.sh`) and analysed with the unchanged analysis scripts, outcome
definitions, comparison families, margins and gates. All other rows are the frozen historical results. The
performance tables (`v3_batching_summary.csv`, `v3_e2e_skab_summary.csv`) keep the historical B5 runs: they contain
no fork evidence (disposition sequences equal to those of PBTI; every MQTT receipt admitted), so the correction
cannot change their dispositions, and they were not repeated, so their timings are those of the historical module. The tables produced with
the historical comparator are kept in `historical_comparator/` for every file whose content changed
(12 of 23); the others are byte-identical under both comparators. Claim-gate outcomes
changed: 0; registered-prediction outcomes changed: 0; registered
comparisons whose class changed: 0 of 1,182 (details in `comparator_correction/` and Document S1).

## Stage names and internal identifiers

The article names stages by purpose; file names keep the identifiers under which the stages were run, because the
recorded hashes refer to them: main evaluation = `v3_scenarios`, `v3_x1`; mixed workload = `v3_mixed`, `v3_x2`;
re-execution with time-dependent outcomes = `A0`; review-schedule evaluation = `A1`; selective-hold grid = `A3`;
selective-hold factorial cells = `A3F`; selective-hold controls = `A3S`; lifecycle analysis = `A5`; stressor sweep
= `v3_sweep`; sensitivity factorial = `v3_factorial`; public-telemetry replay = `v3_replay`; performance =
`v3_batching`, `v3_e2e`; comparisons with B1–B4 = `v2_paired_tests`. `v2`, `v3` and `A*` are stage identifiers, not
versions of this dataset.

## Files analysed with the corrected comparator

| File | Content | One row per | Rows | Historical differs |
|---|---|---|---:|---|
| `v2_paired_tests.csv` | Main evaluation: paired tests of PBTI versus B1-B4 for non-legitimate authoritative observations, missing legitimate observations and current-value error (Document S1, Table S20) | metric x scenario x baseline | 180 | no |
| `v3_outcomes_full.csv` | Main evaluation: per-scenario outcomes of all eight pipelines with 95% bootstrap intervals (Document S1, Table S19) | scenario x pipeline | 106 | yes |
| `v3_x1_preregistered_tests.csv` | Main evaluation, first registration: paired tests of PBTI against B5 and B5s | outcome x scenario x comparator | 60 | no |
| `v3_x2_mixed.csv` | Mixed workload: outcomes, holds and releases | pipeline | 5 | yes |
| `v3_sweep_summary.csv` | Stressor sweep: means and 95% bootstrap intervals per factor level | factor x level x pipeline | 165 | yes |
| `v3_sweep_tests.csv` | Stressor sweep: paired tests of PBTI against each comparator | comparator x outcome x factor x level | 188 | no |
| `v3_factorial_effects.csv` | Sensitivity factorial: estimated effects on O1 and O2 with 95% intervals | pipeline x outcome x effect | 84 | yes |
| `v3_replay_summary.csv` | Public-telemetry (SKAB) replay with injected stressors: outcomes | speed x stress x pipeline | 18 | yes |
| `v3_replay_tests.csv` | Public-telemetry (SKAB) replay: paired tests | outcome x speed x comparator | 12 | no |
| `v3_batching_summary.csv` | In-process batching and worker study: throughput, latency, CPU and storage | pipeline x batch size x workers | 45 | no |
| `v3_e2e_summary.csv` | MQTT v5 over mutual TLS, 30 repetitions per cell: latency, throughput, CPU, queue depth, losses | pipeline x offered rate | 6 | no |
| `v3_e2e_tests.csv` | MQTT v5 over mutual TLS: PBTI versus B2 latency tests | offered rate x latency metric | 6 | no |
| `v3_e2e_skab_summary.csv` | SKAB replay through the MQTT/TLS deployment | replay speed x pipeline | 9 | no |
| `A0_cells.csv` | Re-execution of the main evaluation and mixed workload with the time-dependent outcomes | cell x arm | 66 | yes |
| `A1_cells.csv` | Review-schedule evaluation: all 22 arms (Document S1, Table S24) | cell x arm | 88 | yes |
| `A1_comparisons.csv` | Review-schedule evaluation: all registered comparisons | outcome x cell x arm x reference | 312 | yes |
| `A3_cells.csv` | Selective-hold grid (joint stressor grid) (Document S1, Table S25) | grid point x arm | 147 | yes |
| `A3_comparisons.csv` | Selective-hold grid: all registered comparisons | outcome x grid point x arm x reference | 630 | yes |
| `A3F_cells.csv` | Selective-hold factorial cells added by the amendment (Document S1, Table S26) | factorial cell x arm | 56 | yes |
| `A3F_comparisons.csv` | Selective-hold factorial cells: all comparisons | outcome x factorial cell x arm x reference | 240 | yes |
| `A3S_cells.csv` | Selective-hold controls on the scenario workloads | scenario x arm | 20 | no |
| `A3S_vs_A0_PBTI.csv` | Selective-hold controls: PBTI-SH next to PBTI (re-execution rows) per scenario | scenario | 16 | no |
| `A5_lifecycle_matrix.csv` | Lifecycle analysis: reviewed release under revoked credentials for each release-evidence policy (Document S1, Table S29) | pipeline x case x policy x window width | 68 | no |

## Historical comparator (`historical_comparator/`)

The same file names and columns as above, produced from the frozen historical results:
`v3_outcomes_full.csv`, `v3_x2_mixed.csv`, `v3_sweep_summary.csv`, `v3_factorial_effects.csv`, `v3_replay_summary.csv`, `A0_cells.csv`, `A1_cells.csv`, `A1_comparisons.csv`, `A3_cells.csv`, `A3_comparisons.csv`, `A3F_cells.csv`, `A3F_comparisons.csv`.

## Comparator correction and attacker-model robustness

| File | Content | One row per | Rows |
|---|---|---|---:|
| `comparator_correction/V9_runs_corrected_minus_original.csv` | Corrected minus historical B5/B5s, per specification: run-level means and differences of the primary outcomes and counters | stage x raw-result file x pipeline | 14 |
| `comparator_correction/V9_cells_corrected_minus_original.csv` | Corrected minus historical cell means of every B5/B5s arm of the re-execution, review-schedule and selective-hold stages | campaign x cell x arm | 163 |
| `comparator_correction/V9_comparisons_corrected_vs_original.csv` | Every registered comparison of the review-schedule and selective-hold stages: historical and corrected estimate, intervals, p-values and class | campaign x outcome x cell x arm x reference | 1182 |
| `comparator_correction/V9_W_split.csv` | Exploratory split of W into delay (observations authoritative at the end of the drain) and end-of-run loss (observations still missing then), same denominator and horizon as W | campaign x cell x arm | 50 |
| `attacker_model/V9_attacker_cells.csv` | Attacker-model robustness: mixed workload, seeds 21-40, registered and consistent impersonator, cell means | attacker x arm | 14 |
| `attacker_model/V9_attacker_comparisons.csv` | Attacker-model robustness: paired comparisons, classified descriptively with the registered margins | attacker x arm x reference x outcome | 105 |
| `attacker_model/V9_attacker_controls.csv` | Six deterministic control traces on the real verifiers (one device, ten 1 Hz observations, 200 s); review: one-shot, R = 60 s, C = 10 s (PBTI-R, B5, B5c) | trace x pipeline | 24 |

The lifecycle analysis (`A5_lifecycle_matrix.csv`) was recomputed with the corrected comparator by
`tools/v9/a5_and_e09_e10.py`; it gave the same matrix (0 differing rows).

## Conventions

* `nan`: not defined for that row (for example, no recovery event, or no containment episode).
* Values are means over the seeds or repetitions of the row (`n`, `seeds`, `n_seeds`) unless the column says
  otherwise; counts are per run; times are in seconds (`_s`) or milliseconds (`_ms`).

## Columns of the cell tables (`A0_cells`, `A1_cells`, `A3_cells`, `A3S_cells`, `A3F_cells`)

* `campaign`, `cell` (scenario, grid point or factorial cell), `arm` (pipeline and review setting), `n` (seeds).
* Means over seeds, with standard deviations in `*_sd`: `O1` non-legitimate authoritative observations at the end of
  a run; `O2` legitimate observations accepted by a gateway but absent from the authoritative set; `NLX` exposure to
  non-legitimate authoritative records (record-seconds); `W` mean withheld seconds per legitimate observation up to
  the end of the drain (observations still missing then contribute as end-of-run loss); `AV5` share of legitimate
  observations first available within 5 s.
* Means over seeds: `AV1`, `AV30`, `AV60` (share first available within 1, 30, 60 s); `KM50`, `KM90`, `KM99`
  (Kaplan–Meier quantiles of first availability, s); `NEVER` (legitimate observations never available); `WDR`
  (observations available and later not available); `FMISS` (share of 1 s samples without a correct available value)
  and `FSTALE` (mean staleness of the latest available correct value, s); `CLAT` (median containment latency, s);
  `DWNL` (derived-window time including a non-legitimate input, s) and `DWLAT` (median time to the first window version
  without it, s); `ALT`, `ALF`, `ALM` (true, false and missed alerts of the monitoring workload); `DEC`, `DEF` (review
  decisions and deferrals); `HOLDS` (hold transitions: one per observation entering the held set; the historical
  comparator also counted a hold twice when the held observation's own admission supplied the fork evidence);
  `SHH`, `SHR`, `SHT` (selective holds, releases and timeouts of PBTI-SH); `RECP50` (median recovery time of released
  observations, s); `reach` (legitimate observations accepted by a gateway).
* `audits`, `audits_pass`: runs checked by the auditor and runs that passed; `tracer_match`: runs whose traced end
  state equals the authoritative set.
* The time-dependent outcomes are defined in Document S1 (definitions of the time-dependent outcomes).

## Columns of the comparison tables (`A1_comparisons`, `A3_comparisons`, `A3F_comparisons`)

* `campaign`; `outcome` (O1, O2, NLX, W or AV5); `cell`; `arm` compared with `ref` (reference); `hypothesis`
  (registered hypothesis); `n` (paired seeds).
* `mean_d`: mean paired difference arm − reference; `mean_arm`, `mean_ref`: the two means; `ci95`, `ci90`: 95% and 90%
  percentile-bootstrap intervals of `mean_d` (10,000 resamples).
* `p`: two-sided Wilcoxon signed-rank test (1 when every paired difference is 0); `p_holm`: Holm-adjusted within the
  family of one campaign and one outcome; `m_family`: number of comparisons in that family.
* `direction`: preferred direction of the outcome (`lower` or `higher` is better); `margin`: equivalence margin D (O1
  1 observation, NLX 60 record-s, W 0.6 s, AV5 0.01; O2 1% of the cell's median number of reachable legitimate
  observations).
* `class` (α = 0.05): `identical` (every paired difference 0); `better beyond margin` / `worse beyond margin`
  (`p_holm` < α and the 95% interval beyond D in the preferred / other direction); `equivalent within margin` (90%
  interval inside (−D, D)), with `(significant difference)` added when `p_holm` < α; `different, within margin`
  (`p_holm` < α otherwise; the article calls this class "significant, margin unresolved": the 95% interval crosses a
  margin boundary, so neither equivalence nor a difference beyond the margin is established); `inconclusive` (all
  other cases). The class labels in the files are the registered labels and are not renamed.

## Columns of `comparator_correction/`

* `V9_runs_corrected_minus_original.csv`: one row per stage, raw-result file and pipeline (`system`): `runs` (runs of
  the specification), `rerun` (runs replaced by the corrected rerun), `runs_outcome_changed` (runs in which any
  primary outcome changed), `runs_O1_changed` (runs in which O1 changed), and the mean, minimum and maximum over runs of the corrected-minus-historical difference
  of O1, O2, NLX, W, AV5 and the hold counter (`<x>_mean_diff`, `<x>_min_diff`, `<x>_max_diff`; empty when the stage
  has no such outcome).
* `V9_cells_corrected_minus_original.csv`: one row per `campaign`, `cell` and B5/B5s `arm`, with the historical
  (`<x>_original`) and corrected (`<x>_corrected`) cell means and their difference (`<x>_diff`) for x = O1, O2, NLX,
  W, AV5, HOLDS, DEC and RECP50.
* `V9_comparisons_corrected_vs_original.csv`: every registered comparison of the review-schedule and selective-hold
  stages (`campaign`, `outcome`, `cell`, `arm`, `ref`, `hypothesis`; `involves_B5`: whether either side is a B5 or
  B5s arm) with the historical and corrected mean difference (`mean_d_original`, `mean_d_corrected`), 95% interval,
  Holm-adjusted p and class, and `class_changed`.
* `V9_W_split.csv`: `campaign`, `cell`, `arm`, `n` (seeds), `W` and its parts — `W_delay` (delay of observations
  authoritative at the end of the drain) and `W_loss` (contribution of observations still missing then, end-of-run
  loss), both in seconds per gateway-accepted legitimate observation, so that they sum to `W` — and `loss_share`
  (`W_loss` / `W`). Exploratory.

## Columns of `attacker_model/`

* `V9_attacker_cells.csv`: one row per `arm` and `attacker` (`registered`: the impersonator of the registered mixed
  workload; `consistent`: the consistent impersonator), `n` (seeds 21–40), and the means of O1, O2, NLX, W, AV5 and
  review decisions (`DEC`) with 95% percentile-bootstrap intervals (`<x>_ci95`, 10,000 resamples).
* `V9_attacker_comparisons.csv`: paired comparisons per `attacker`, `arm`, reference `ref` and `outcome`: `n`, `mean_d`
  (arm − reference), `ci95`, `p_wilcoxon` (two-sided Wilcoxon p before any adjustment), `class` and `source`. For the
  registered attacker, a comparison that is one of the registered comparisons of the review-schedule evaluation is
  copied from it (`source` names the hypothesis; registered interval and class); every other row is recomputed
  (`source` = `recomputed (exploratory)`) and classified with the registered margins and rules, used descriptively.
* `V9_attacker_controls.csv`: per control trace and pipeline, forged statements admitted on arrival, forged statements
  authoritative at the end, forged exposure (record-seconds), genuine statements arrived and authoritative at the
  end, genuine withheld record-seconds, dispositions on arrival and review outcomes.

## Columns of the lifecycle matrix (`A5_lifecycle_matrix.csv`)

One row per `pipeline`, `case`, release-evidence `policy` and `width_s`, the width of the uncertainty interval around
the compromise time (non-zero only in the rows of the witness policy that model this uncertainty). The other
columns (`legitimate`, `case_state`, `authoritative_end`, `tainted_end`, `malicious_authoritative`, `genuine_recovered`,
`genuine_withheld`, `first_decision`, `state_after_first_decision`, `authoritative_after_release`,
`in_window_after_release`, `window_versions_added`, `window_corrected`) record the outcome of each case as named; the
cases and policies are described with the lifecycle matrix in Document S1.

## Columns of the main-evaluation, sensitivity, replay and performance tables (`v2_*`, `v3_*`)

* Outcomes: `nonlegit_auth` (O1), `legit_missing` (O2), `legit_quarantined` (legitimate observations quarantined or
  held), `recovered_n` (released by review), `holds`, `dup_auth` (duplicate authoritative observations), `win_corrupt`,
  `win_incomplete` (corrupt and incomplete derived windows), `cv_wrong_rate` (current-value error), `n_reachable`
  (reachable legitimate observations), `store_bytes_per_reach` (persisted bytes per observation), `fork_events` (feed
  forks detected by the feed-level baselines B5 and B5s), `rec_p50_s` (median recovery time of released observations,
  s).
* Identifiers: `system` / `pipeline`, `scenario` and `label` (scenario name), `comp` / `baseline` (comparator of PBTI),
  `factor` and `level` (stressor and its level; `none` marks the shared zero-stress point), `effect` and `label` in
  the factorial table (factor or alias chain), `speed` (replay speed factor), `stress` (stressors injected), `rate`
  (offered messages/s), `batch` (batch size), `workers`, `metric`, `outcome`.
* Intervals: `*_ci_lo`, `*_ci_hi`, `*_lo`, `*_hi`, `tp_lo`, `tp_hi`, `p99_lo`, `p99_hi` and the `ci_lo`, `ci_hi` of
  `v3_x1_preregistered_tests.csv` are 95% percentile-bootstrap intervals (10,000 resamples); the `ci_lo`, `ci_hi` of
  `v3_factorial_effects.csv` are 95% t intervals over seeds.
* Tests: `p` is the two-sided Wilcoxon signed-rank p-value on paired seeds (zero differences dropped; rows identical
  in every seed are marked `identical` in `kind` and entered with `p` = 1); `p_holm` Holm-adjusted (in
  `v2_paired_tests.csv` across all scenarios of a metric, `p_holm_scen` within a scenario); `sig`: `p_holm` < 0.05;
  `rb` matched-pairs rank-biserial correlation of the paired differences, positive when the difference is positive
  (PBTI minus baseline in `v2_paired_tests.csv`; comparator minus PBTI, the sign of `mean_diff`, in the `v3_*` test
  tables); `mean_pbti`, `mean_comp` / `mean_base` (means of PBTI and of the comparator), `mean_diff` (comparator minus
  PBTI); `n_nonzero` / `n_identical` (seeds with a non-zero / zero paired difference); `practical` (|`mean_diff`| at
  least the practical threshold: 1 observation for O1, 72 for O2). The replay tests use the stressed runs. In the
  wall-clock end-to-end tests (`v3_e2e_tests.csv`), `p` is the Mann–Whitney U p-value (Holm-adjusted in `p_holm`),
  `delta` is Cliff's delta, and `n_pbti`, `n_b2` are the numbers of repetitions.
* Factorial (`v3_factorial_effects.csv`): `estimate` = mean over seeds (`n_seeds`) of the difference between the mean
  outcome of the runs at the high and at the low level of the factor or alias chain.
* SKAB replay (`v3_replay_summary.csv`): `label0_reach`, `label0_auth`, `label1_reach`, `label1_auth` (reachable and
  authoritative observations with SKAB label 0, normal, and 1, anomalous); `avail_label0`, `avail_label1` (authoritative
  share per label); `legit_rx_revoked` (legitimate observations rejected as revoked).
* Performance: `throughput` / `throughput_msg_s` (messages/s), `achieved_rate` (publisher send rate, messages/s),
  `lat_ms_p50`, `lat_ms_p95`, `lat_ms_p99` (ms; `*_median` = median over repetitions), `cpu_util_cores` (CPU time per
  wall-clock time), `cpu_us_per_msg` / `verifier_cpu_us_per_msg` (µs per message), `queue_depth_max`,
  `db_bytes_per_msg`, `evidence_bytes_per_msg`, `wire_bytes` (bytes per message on the wire), `rss_main_mb`,
  `rss_workers_mb`, `verifier_rss_peak_mb` (resident memory, MB), `sent`, `lost` (messages sent and not durably
  committed), `drops`, `timeouts` (always 0: the in-process benchmark has no drop or timeout path).
* `A3S_vs_A0_PBTI.csv`: `scenario`; `PBTI_<x>` is outcome x of PBTI (re-execution rows) and `SH_<x>` the same outcome
  of PBTI-SH on the same scenario, for x = O1, O2, W, AV5 and NLX (means over seeds).
