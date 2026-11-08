# V3 pre-registration of confirmatory comparisons

Written on 3 November 2026 before any B5, sweep, release-workflow, batching or new end-to-end result existed.
Its SHA-256 is recorded in `research/V3/PREREGISTRATION.sha256` at the time of writing; later edits are not allowed
(amendments go to `research/V3/PREREGISTRATION_AMENDMENTS.md` with a reason and a timestamp).

## Pipelines
* **PBTI**: unchanged revision-2 mechanism (Rule L per-identity classification).
* **B4**: unchanged revision-2 mainstream combination (first writer wins on (did, ep, seq); no relay signature,
  no Rule L, no quarantine, no taint).
* **B5**: literature-informed strong baseline. Origin signature (as PBTI); relay countersignature over the exact
  origin statement and signature in the style of RFC 9338 (as PBTI's relay statement); versioned path-bound
  admission and credential lifecycle (as PBTI); (did, ep, seq) idempotency (Kafka KIP-98 / CloudEvents style);
  append-only evidence (SCITT-style, as PBTI); **feed-level** fork evidence from hash links and duplicate identities
  (Secure Scuttlebutt / PeerReview / Global Data Plane style): once a fork is detected in a feed (did, ep), every
  observation of that feed from the fork point onwards is held; revocation-triggered taint (Taser/Warp style, as
  PBTI); quarantine with **review-based recovery**: after a review delay R = 60 s an automated reviewer releases
  held observations whose slot has exactly one version, no contradicting successor digest and at least one
  corroborating hash link, and rejects the others; every review decision is a signed audit event.
* **B5-strict**: as B5 but without recovery (feed frozen from the fork point for the rest of the run, as in Secure
  Scuttlebutt's "messages from the point of the fork onwards are ignored").

## Primary outcomes (end of run)
* **O1** non-legitimate observations that are authoritative.
* **O2** legitimate observations missing from the authoritative set.

Secondary: legitimate observations quarantined or held; current-value error rate; corrupted derived windows; time
from production to authority for observations recovered after a hold; number of review decisions; evidence bytes per
receipt; verifier CPU per message.

## Design
* X1: 15 scenarios x 20 paired seeds (seeds 1-20) for B5 and B5-strict; PBTI, B4, B1-B3 results are the stored
  revision-2 runs for the same seeds (validity guarded by the regression test and a re-run sample).
* X2: mixed workload x 20 seeds for B5 and B5-strict.
* X3: single-factor sweep, levels 0, 1, 5, 10, 20 %, 20 paired seeds, pipelines PBTI, B4, B5 (definitions in
  `docs/V3_SWEEP_DESIGN.md`).
* X4: 2^(7-3) resolution-IV fractional factorial at 0 % / 10 %, 20 seeds, pipelines PBTI, B4, B5.

## Multiplicity and thresholds
* X1: for each outcome, Holm over 15 scenarios x 2 comparisons (PBTI vs B5, PBTI vs B5-strict) = 30 tests;
  two-sided Wilcoxon signed-rank on paired seeds; pairs identical in every seed are reported as identical, not tested.
* Practical significance: O1 difference >= 1 observation per run; O2 difference >= 1 % of the legitimate
  observations of the run (72 for the 300 s scenarios).

## Predictions (stated before running)
* P1: B5 equals PBTI on O1 in all 15 scenarios.
* P2: B5-strict exceeds PBTI on O2 by at least the practical threshold in E5 and E8.
* P3: B5's end-of-run O2 is within the practical threshold of PBTI in every scenario, but observations held after a
  fork become authoritative only after >= R.
* P4: B4 remains worse than PBTI on O1 in E5 and E14.

## Decision rules for the novelty claim
* D1: if P1 and P3 hold, the manuscript must state that a literature-informed feed-level design with review-based
  recovery reaches PBTI's end-of-run security and availability, and that the remaining difference is automatic
  per-identity containment without a review cycle (time to availability, review workload), i.e. a narrow state-rule
  refinement, not superior security.
* D2: any scenario in which B5 or B5-strict beats PBTI on O1 or O2 is reported in the abstract-level summary.
* D3: any scenario in which PBTI beats B5 on O1 is reported with the mechanism responsible.
* The sweep (X3, X4) is descriptive: no single rate is presented as a guarantee.
