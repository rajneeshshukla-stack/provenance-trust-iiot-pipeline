# V3 attack and fault-rate sweep and fractional-factorial design

This document specifies experiments X3 (sweep) and X4 (factorial) of `research/V3/PREREGISTRATION.md`. The code is in
`src/pbti/sweep.py`, the job runner in `experiments/run_campaign.py` (`sweep` and `factorial` campaigns), and the
analysis in `analysis/analyze_v3.py`. Raw rows are in `results/raw/v3_sweep.jsonl` and `results/raw/v3_factorial.jsonl`.

## 1. Purpose

The V2 scenarios set each stressor to one hand-picked intensity. The sweep asks how the outcomes change as the
intensity of one stressor rises from 0 to 20 %, holding everything else at zero, and the factorial asks whether
stressors that act together interact. Both are run on the same paired seeds for PBTI, B4 (first-writer-wins) and B5
(feed-level fork hold with review-based recovery), so differences between pipelines are differences under the same
events.

## 2. Common set-up

| Item | Value |
|---|---|
| Topology | 4 gateways x 6 devices (1 legacy device per gateway), 1 Hz, as in the V2 scenarios |
| Production phase | 120 s (V2 scenarios: 300 s), followed by the usual drain |
| Levels | r in {0, 0.01, 0.05, 0.10, 0.20} |
| Seeds | 1-20 for every cell (paired across pipelines and levels) |
| Pipelines | PBTI, B4, B5 (B5 review period 10 s, minimum hold age 60 s, as in X1) |
| Outcomes | O1 non-legitimate authoritative records, O2 legitimate observations missing at the end; secondary: current-value error rate, quarantined legitimate records, recovery latency, evidence bytes |
| Audit | not run for sweep and factorial rows (the audit is exercised on X1 seeds 1-5) |

Randomness for every stressor is drawn from per-world streams seeded only by the run seed, never by the pipeline, so
two pipelines with the same seed and level receive the same network events and the same attacks.

## 3. Factors and level mapping

| Factor | What level r means |
|---|---|
| loss | each transmission is lost with probability r; the gateway retransmits after its RTO |
| dup | transport duplicate (redelivery) with probability r |
| reorder | extra delay U(0.2, 3) s with probability r (out-of-order delivery) |
| delay | long delay U(30, 90) s with probability r |
| burst | every gateway disconnected for r x 120 s from t = 24 s, then drains its backlog as a burst |
| clock | an observation's timestamp is wrong with probability r: +U(6, 30) s or -U(30, 90) s, 50/50 |
| revstale | two signing devices of cell 4 and gateway 4 impersonated from 24 s; keys revoked at 72 s with t_comp = 24 s; revocation status refreshed every r x 600 s (0, 6, 30, 60, 120 s) |
| compromise | the same compromise from 24 s, revoked with t_comp = 24 s after a discovery delay of r x 600 s |
| equivocation | one signing device per cell equivocates with stolen device and relay keys with probability r per message (cells 1-2 back-running, cells 3-4 front-running) |
| missing | a malicious broker acknowledges and discards runs of 5 consecutive messages of a device, a run starting with probability r/5 per message |
| relay | compromised gateway 2 (relay key only) forges r x 720 observations for its own devices (legacy and signing) and replays a fraction r of its traffic 2-30 s later |

The two time-valued factors (revstale, compromise) contain the compromise at every level, including 0: level 0 means
immediate status refresh, respectively immediate discovery. Their zero point is therefore not the shared no-stressor
run. For all other factors the zero point is the shared run with no stressor (`factor = none`).

Run count: 1 shared zero point + 11 factors x 4 non-zero levels + 2 time-valued zero points = 47 cells x 20 seeds
x 3 pipelines = 2,820 runs.

## 4. Fractional factorial (X4)

Seven factors that can be combined without changing each other's meaning are crossed at two levels (0 and 0.10) in a
standard 2^(7-3) design of resolution IV:

| Letter | A | B | C | D | E | F | G |
|---|---|---|---|---|---|---|---|
| Factor | loss | dup | reorder | delay | clock | equivocation | missing |

A, B, C and D form a full 2^4 factorial; the generators are E = ABC, F = BCD and G = ACD. The defining relation is
I = ABCE = BCDF = ACDG = ADEF = BDEG = ABFG = CEFG (all words have length 4). Consequently main effects are aliased
only with three-factor interactions, and two-factor interactions are aliased in seven chains of three:
AB = CE = FG, AC = BE = DG, AD = EF = CG, AE = BC = DF, AF = DE = BG, AG = CD = BF, BD = CF = EG. The 15 effect
degrees of freedom are the 7 main effects, these 7 chains and one chain of three-factor interactions.

Each of the 16 runs is repeated on seeds 1-20 for each of the three pipelines (960 runs). For each pipeline and
outcome, an effect is the mean response at the high level minus the mean at the low level (each mean over 8 runs x 20
seeds). Standard errors come from the seed-to-seed variation: the per-seed effect estimate is computed for each seed
and the 95 % interval is a t interval over the 20 per-seed estimates. Burst, revstale, compromise and relay are left
out of the factorial because they replace part of the topology's normal behaviour (an outage of every gateway, an
incident-response timeline, a compromised gateway) rather than adding independent per-message events.

## 5. Analysis

* Sweep curves: for every factor, pipeline and outcome, the mean over the 20 seeds with a 95 % bootstrap interval
  (10,000 resamples, percentile), plotted against r.
* Paired comparisons (the preregistered confirmatory tests are the X1 comparisons; the sweep is descriptive, as the
  preregistration states, and its tests are exploratory): per cell, the Wilcoxon signed-rank test of B4 - PBTI and B5 - PBTI over the 20 seeds, Holm-adjusted
  across all sweep cells of the same outcome and comparison. A cell where all 20 paired differences are zero is
  reported as "identical" rather than tested.
* Factorial: main effects and alias chains as above, per pipeline and outcome.

## 6. Limitations stated with the results

* All sweep runs use the discrete-event simulator; no sweep cell is a hardware or network measurement.
* The production phase is 120 s; effects that need longer to build up (for example long revocation-refresh periods
  relative to the run) are bounded by the run length, which is why revstale stops at 120 s.
* Levels are probabilities per message or fractions of a time scale; they are not calibrated to any particular plant.
* The burst factor disconnects every gateway at once, which is the harshest placement of an outage of that length.
