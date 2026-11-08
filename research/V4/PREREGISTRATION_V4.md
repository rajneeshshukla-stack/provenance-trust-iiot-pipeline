# PBTI V4 — Preregistration of the confirmatory experiments (A1, A3) and of the A0 replication gate

Status: frozen before any confirmatory run (seeds 21–40) was executed. The file's SHA-256, the SHA-256 of every
source and configuration file it depends on, and the UTC time of freezing are recorded in
`research/V4/PREREGISTRATION_V4.sha256` (written by `scripts/freeze_prereg.py`). This is an **internal**
preregistration: the timestamp is self-recorded in this package and has not been deposited with an external registry
(an optional OSF deposit is listed as an author action). Amendments, if any, are appended in Section 10 with their own
hash and time and are never silently merged into the text above.

## 1. What was seen before freezing (development disclosure)

* The V3 results (seeds 1–20 of all scenario campaigns, the V3 factorial and sweep) were known; they motivated A1
  (review timing), A2 (time-dependent outcomes) and A3 (selective holds).
* A3 design: the PBTI-SH rule (Section 5) was designed after a diagnostic on V3 factorial runs 3, 4, 8, 15 with seeds
  1–5: every forgery PBTI kept had no admitted successor, and B5 held 37 of those 61 at the end of the run.
* Smoke runs on seed 1 (S05 and S08; one factorial point): withheld record-seconds in S05 were PBTI 59,427,
  B5-hist 106,119, B5 with event-driven review 59,488, PBTI-SH 60,682. These single-seed development values are not
  evidence and are not reused in any confirmatory analysis.
* Pilots for error checking only: A0 seeds 1–3 on the pre-D05 source (198 rows, all identical to the archive) and
  seed 1 on the final source; A1 seed 101 and A3 seed 101 on the final source. A first A1 pilot on the pre-D05 source
  was stopped after 52 of 92 runs (0 errors); its rows are kept, uninspected, as
  `results/v4/pilot/superseded_A1_pilot_pre_D05_s101.jsonl`.
  Development seeds (1–5 for the diagnostic, 101–103 for pilots) are disjoint from the confirmatory seeds 21–40.

## 2. Campaigns, arms and seeds

| Campaign | Config | Role | Seeds | Units |
|---|---|---|---|---|
| A0_core | `experiments/v4_configs/A0_core.json` | replication gate + descriptive temporal metrics | 1–20 (historical) | 16 scenarios × {PBTI, B4, B5-hist, B5S} + PBTI-R-hist on S12, S99 = 1,320 runs; audit on seeds 1–5 |
| A1_review | `experiments/v4_configs/A1_review.json` | **confirmatory** | 21–40 | S05, S08, S12, S99 × 22 arms = 1,760 runs; audit on seeds 21–22 |
| A3_selective | `experiments/v4_configs/A3_selective.json` | **confirmatory** | 21–40 | 21 grid points × 7 arms = 2,940 runs; audit on seeds 21–22 |
| A3_scenarios | `experiments/v4_configs/A3_scenarios.json` | control (side effects of PBTI-SH) | 1–20 | 16 scenarios × PBTI-SH + 4 × PBTI-SH-T30 = 400 runs, paired with A0 rows |

Arms. `B5-hist` = feed-level baseline with the V3 reviewer (one-shot rule, minimum case age 60 s, review cadence
10 s). `B5-dRcC` / `PBTI-R-dRcC` = deferring reviewer with minimum case age R ∈ {0, 1, 5, 60} s and periodic
cadence C ∈ {1, 10} s. `-event` = event-driven review (minimum age 0, review triggered by every admission that can change the
evidence of a pending case; cascading). `B5-oneshot-d0c10` = exploratory (one-shot rule at R = 0, cadence 10 s). `PBTI` (no
reviewer), `PBTI-R-hist` (PBTI with the V3 reviewer); `B5S` (no recovery) only in A0. A3 arms: `PBTI`, `PBTI-SH`
(no timeout), `PBTI-SH-T30` (30 s timeout), `B5-hist`, `B5-event`, `B5S`, `PBTI-R-hist`. The arm sets were trimmed for run time before
freezing (A1: B5s dropped, it is in A0). The A1 pilot (seed 101) ran an intermediate
16-arm configuration without the cadence-10 s arms for R ∈ {0, 1, 5} s, which use the same code path as the piloted
R = 60 s, cadence 10 s arms. Pairing: within a scenario (or grid point) and seed,
all arms see the identical workload, fault and attack schedule (the World is seeded identically), so differences are
paired by seed.

## 3. Outcomes (per run; the run is the experimental unit)

Primary outcomes (all from `src/pbti/oracle.py` and `src/pbti/temporal.py`; definitions in the module docstrings):

| Code | Outcome | Field | Direction preferred |
|---|---|---|---|
| O1 | final non-legitimate authoritative observations | `nonlegit_auth` | lower |
| O2 | final legitimate observations not authoritative | `legit_missing` | lower |
| NLX | non-legitimate exposure (record-seconds authoritative over [0, T_end]) | `tm_nl_rec_s` | lower |
| W | mean withheld seconds per reachable legitimate observation | `tm_wh_rec_s / tm_reach` | lower |
| AV5 | fraction of reachable legitimate observations first available within 5 s of production | `tm_avail_5s` | higher |

Secondary (descriptive, no confirmatory test): AV1/AV30/AV60, Kaplan–Meier first-availability quantiles
(censored at T_end), withdrawals, freshness (missing and stale fractions), containment latency, derived-window
exposure and correction latency, alert outcomes of the monitoring workload (alert when temp_c > nominal + 2.5 °C;
missed if not raised within 5 s), review decisions and deferrals, holds, SH holds/releases/timeouts.

## 4. Comparisons, tests, margins and claim language

Paired difference d = (arm − reference) per seed. For each comparison and outcome: mean of d, 95 % percentile
bootstrap CI (10,000 resamples, RNG seed 20261104), 90 % bootstrap CI for equivalence, two-sided Wilcoxon
signed-rank test (zero differences discarded, `zero_method="wilcox"`; if all 20 differences are zero the result is
reported as "identical in all seeds" with p = 1). Holm–Bonferroni correction within each family; a family is one
campaign × one outcome (all scenarios/grid points and comparisons of that outcome together); α = 0.05.

Practical margins Δ (per run), fixed now:

| Outcome | Δ | Rationale |
|---|---|---|
| O1 | 1 observation | one retained forgery per run |
| O2 | 1 % of the median reachable count of the cell (72 for the 300 s scenarios with 7,200 observations; 29 for the 120 s A3 grid with about 2,880) | loss of 1 % of the data |
| NLX | 60 record-s | one forged observation authoritative for one minute |
| W | 0.6 s | below the 1 s sampling period (equals 4,320 record-s for 7,200 observations and about 1,740 record-s for 2,900) |
| AV5 | 0.01 | one percentage point |

Classification of each comparison (applied mechanically by `analysis/analyze_v4.py`):
* **identical**: all paired differences are zero;
* **equivalent within Δ**: the 90 % CI of the mean difference lies inside (−Δ, +Δ);
* **better / worse beyond Δ**: Holm-adjusted p < 0.05 and the 95 % CI lies entirely beyond −Δ (better for
  "lower") or +Δ (worse), mirrored for AV5;
* **different, within Δ**: Holm-adjusted p < 0.05 but the 95 % CI overlaps ±Δ;
* **inconclusive**: none of the above.

## 5. Frozen rules

Reviewer (src/pbti/review.py). Release predicate `corroborated` (unchanged from V3): the slot holds that single digest
and (the predecessor is authoritative with exactly the digest named by `prev`, or an admitted successor's `prev`
names exactly this digest). Rule `oneshot` (V3): an uncorroborated reviewed case is REJECTED. Rule `defer` (V4):
RELEASE if corroborated; REJECT only if `contradicted` (another digest is known for the slot, or `prev` names a digest
absent from known predecessor evidence); otherwise the case stays QUARANTINED for a later review.

PBTI-SH (src/pbti/selective.py; rule text in the module docstring, quoted here in substance): a feed becomes suspect
at its first CONTESTED slot, for the rest of the epoch; in a suspect feed a COMMITTED observation that is not
successor-corroborated (I(e) = V(e) = {cd}) is provisional (not authoritative, not in derived processing), including
retroactively at the moment the feed becomes suspect; release only by an admitted successor link naming exactly its
digest; a predecessor link is not sufficient; contested provisional slots are never released; tainted slots are never
released; timeout 0 (none) in `PBTI-SH`, 30 s in `PBTI-SH-T30`.

Release-evidence policy (A5) is not part of A1/A3; all A0/A1/A3 runs use the V3 `discretionary` policy.
Revocation records (decision D05, made before freezing): a key stays revoked from its first revocation; a revised record
merges conservatively (earliest revocation and compromise times) and re-runs the taint selector; a slot committed by an
authorized REVOKED_BUFFERED release is exempt from the commit-time selector only while its release condition holds.

## 6. Hypotheses and confirmatory comparisons

A1 (scenarios S05, S08, S12, S99; seeds 21–40):
* **H1a (replication)**: PBTI vs B5-hist — O1 and NLX identical or equivalent; W and AV5 worse for B5-hist beyond Δ in
  S05 and S99 (fork scenarios).
* **H1b (delay attribution)**: PBTI vs B5-event — W and AV5 equivalent within Δ in all four scenarios. If H1b fails,
  the residual difference is reported and the claim "PBTI's availability advantage is due to the review delay" is not
  made.
* **H1c (matched recovery)**: for every matched review setting X ∈ {hist, d0c1, d1c1, d5c1, d60c1, d60c10,
  event} and X ∈ {d0c10, d1c10, d5c10}, PBTI-R-X vs B5-X on O1, O2, NLX, W, AV5 (classification as in Section 4).
* **H1d (security cost of fast review)**: B5-X vs B5-hist on O1 and NLX for X ≠ hist (two-sided; no direction
  predicted).
* Descriptive: W and AV5 as functions of R and C (no test); B5-oneshot-d0c10 vs B5-d0c10.

A3 (joint grid of equivocation × suppression {0, 1, 5, 10} %, equivocation 5 % × delay {1, 5, 10} %, equivocation 5 %
× long suppression runs {1, 5} %; 120 s production, 180 s drain; seeds 21–40):
* **H3a**: PBTI-SH vs PBTI — O1 and NLX (expected lower for PBTI-SH where PBTI's O1 > 0), O2, W, AV5 (expected worse).
* **H3b**: PBTI-SH vs B5-hist, vs B5-event, vs B5S and vs PBTI-R-hist — O1, O2, NLX, W, AV5.
* **H3c**: PBTI-SH-T30 vs PBTI-SH — same outcomes (timeout trade-off).
* Controls (A3_scenarios, seeds 1–20, descriptive): PBTI-SH vs PBTI on all 16 scenarios; any O1 increase is reported.

## 7. Claim gates (what the manuscript may say)

* **G1** "the availability difference between PBTI and B5 reflects B5's review schedule": only if H1b classifies W and
  AV5 as identical/equivalent in S05 and S99.
* **G2** "with the same reviewer, per-identity and feed-level containment have equal final outcomes": only for the
  settings and scenarios in which H1c classifies O1 and O2 as identical/equivalent; otherwise the exceptions are
  listed.
* **G3** "selective holds reduce retained forgeries": only if H3a classifies O1 as better beyond Δ (or NLX better beyond
  Δ) in at least half of the grid points in which PBTI's mean O1 > 0.
* **G4** PBTI-SH is presented as a useful extension (method section and abstract) only if G3 holds and, at the same
  points, PBTI-SH is not worse than B5-hist beyond Δ on W. Otherwise PBTI-SH is reported as a negative or mixed result
  in the discussion and future work, with the numbers.
* No claim of superiority is made from secondary outcomes; equality in tested cells is not a universal equivalence.

## 8. A0 replication gate (seeds 1–20)

For every archived V3 row (PBTI, B4, B5, B5s; PBTI-R on S12 and S99), every deterministic field (counts, ratios,
states, recovery latencies, receipts, review outcomes) must equal the V4 re-run exactly; wall-clock fields (ingest
and signing µs, wall_s, audit timings) are excluded (`scripts/compare_a0.py`). Any difference blocks the claim
"V4 changes preserve historical results" and is reported per field. A0 temporal metrics on seeds 1–20 are descriptive.

## 9. Exclusions and deviations

Error rows are not results; if a confirmatory run errors, its seed is excluded from every comparison of that cell
and the exclusion is reported. Audit failures are reported, not excluded. Seeds are fixed (no optional stopping).
Every deviation from this document is listed in the results report with its reason.

## 10. Amendments

None at freezing time.
