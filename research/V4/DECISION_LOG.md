# V4 research decision log

Every decision taken autonomously during the V4 revision, with the alternatives considered and the reason for the
choice. Times are America/Chicago (UTC-6). Entries are appended; earlier entries are not edited (corrections are new
entries that reference the earlier one).

## D01 (2026-11-04 22:30) Authoritative starting artifact
* Inputs: `v3.zip` (SHA-256 5237a84f...) containing `Provenance-Bound_Trust-Aware_Ingestion_V2_Final_Package.zip`
  (7fe053ce...) and `Provenance-Bound_Trust-Aware_Ingestion_V3_Research_Resolution_and_Submission_Package.zip`
  (524a50fd...); the master prompt (`f35830c5-attachment.txt`, ca56a0a6...) and the revision memo
  (`Paper-2_Revision_Memo_Before_After_and_Experiment_Plan.docx`, 9eb07a61...).
* The prompt names a "V2 ZIP" as the starting artifact but also says that the memo "references a V3 source of
  record". The memo states that its source of record is the V3 manuscript inside the V3 package, and every passage
  it quotes (B5, PBTI-R, the 60 s review delay, SKAB, the sweep) exists only in V3. V2 has none of the B5/review
  machinery that R04, R08, R10 and A1-A5 revise.
* Alternatives: (a) start from V2 and re-implement V3; (b) start from V3, preserving V2 unchanged as history.
* Decision: (b). The V3 package is the most complete and internally consistent package (it contains the unchanged
  V2 repository snapshot and per-file hashes, and verified 421/421 against its own manifest on extraction). The
  traceability matrix records, for every memo item, the V3 source location and whether the item existed in V2.
  Both input ZIPs are kept byte-identical in the V4 package.

## D02 (22:40) Treatment of the memo's labels
* EDIT NOW items are applied after checking each sentence against the code and data. RESEARCH PLAN and GATED
  TEMPLATE items are implemented only where the work is actually performed; otherwise their text goes to Future
  Work. Bracketed author fields of R14 are never filled with invented content (they stay as author actions).

## D03 (22:50) Review-delay comparison design (R04, A1)
* The historical reviewer is one-shot: a case reviewed while uncorroborated is REJECTED for good. With a 60 s minimum
  age this rarely matters (the successor that corroborates a held observation normally arrives within about 1 s);
  with a minimum age of 0-1 s or event-driven review it would reject most held observations before their successor
  arrives, so an R sweep with the one-shot rule would measure the rule's impatience rather than the feed-level
  response.
* Decision: the A1 matrix uses a deferring reviewer with the same eligibility and corroboration predicate
  (`review.corroborated`): RELEASE if corroborated, REJECT only if the slot is contradicted (more than one digest
  known), otherwise leave the case pending for a later review. The historical one-shot rule at R = 60 s, cadence
  10 s is kept as the regression reference (it must reproduce the V3 rows exactly).
* Event-driven review is a separate trigger mode (review after every admission, on the cases whose identity or
  hash-link neighbourhood the admission touched, with deterministic identity ordering and an iterative, bounded
  cascade), not R = 0 with a periodic scheduler.

## D04 (22:55) Temporal metrics unit (R06, A2)
* An observation is identified by its event identity and its content key (device, asset, timestamp, schema,
  canonical payload: the oracle's content identity). A legitimate observation counts as available only if a pair
  (identity, content key) that the honest pipeline produced for it is authoritative; a forged content under the
  same identity is counted as non-legitimate and does not make the genuine observation available.
* The content key rather than the statement digest is used so that metadata the attacker can change without
  changing the measured value (e.g. a re-signed `prev` link) is not counted as a different value; this matches the
  definition of O1/O2.

## D05 (23:12) Revised revocation records and reviewed pre-compromise releases (A4 finding, R09)
* Finding: the extended bounded lifecycle check (`formal/v4_locality_lifecycle_check.py`, part C) found a minimal
  schedule [deliver G(0,0) at 2 s; revoke dk:d1:1 at 3 s with t_comp = 3 s; revoke it again at 5 s with the
  revised t_comp = 0] after which G(0,0) stayed authoritative although its commit time (2 s) is after the revised
  compromise time. Cause: the verifier's trust view reported a revocation only the first time a key id appeared, and
  the registry overwrote records, so a revision could also move t_comp later and loosen the REVOKED_BUFFERED waiver.
  Saved before the fix: `results/v4/formal/counterexamples/C4_revised_compromise_time.json`.
* Decision: a key stays revoked from its first revocation; a revised record merges conservatively (earliest
  revocation time, earliest known compromise time) and is reported to the verifier again, so the taint selector
  re-runs (taint stays monotone). A slot committed by an authorized REVOKED_BUFFERED release is exempt from the
  commit-time selector only while its release condition (`_pre_compromise_ok`) still holds under the current record;
  a revision that invalidates the condition taints it. This also removes a timing artefact: with event-driven review
  a release in the same second as the revocation would previously be tainted at the next tick.
* Historical impact: none expected; no V2/V3 scenario, sweep or replay revokes a key twice and periodic review
  releases at least 60 s after quarantine. Verified by the A0 field-by-field replication on the final source.
* Tests: tests/test_v4_release_evidence.py (revised earlier t_comp taints; a revision cannot move t_comp later;
  a re-announced revocation keeps a valid release; an invalidating revision taints it).

## D06 (23:15) A0 comparison: runner metadata
* The archived rows carry runner bookkeeping (`ablation_name`, and `kind = "ablation"` for the mixed-workload rows
  that the V3 ablation runner produced); the V4 runner writes neither. These two fields are reported with their
  values (`metadata_values`) but not compared. All other fields except wall-clock timings (`*_us*`, `wall*`,
  `ingest*`, `wrap*`, `devsign*`, `*_s`) and audit fields (audits ran on different seed subsets) are compared.
  The pilot (seeds 1-3, 198 rows, 8,314 field comparisons) was identical.

## D07 (23:43) Amendment 1: A3 factorial cells
* After the freeze, inspection of the A3 pilot (seed 101) showed that the preregistered joint grid produced almost no
  retained forgeries (PBTI O1 > 0 at 1 of 21 points, where every arm retained the same three). The V3 condition that
  motivated A3 combined equivocation and suppressed runs with the factorial's other delivery factors.
* Decision: add, by a separate amendment (the frozen document is unchanged), the eight V3 factorial cells with
  equivocation high (four with suppressed runs high) on fresh seeds 21-40, run after the frozen chain, with its own
  family and gates (G3F, G4F). The original A3 gates are reported unchanged. Data dependence is disclosed in the
  amendment and in the manuscript.

## D08 (2026-11-05 04:40) Interruption of the campaign chain; resumable execution
* The host was restarted while A0_core was running (318 of 1,320 rows written, all complete JSON lines; uptime reset
  at 04:34). The frozen chain (`run_v4_chain.sh`) and the queued amendment run were lost; A1, A3 and A3F had not
  started.
* Decision: continue with `scripts/run_v4_resume.py`, which imports the frozen `experiments/run_v4.py` unchanged
  (`expand`, `job`), keeps existing valid rows, drops a truncated last line if any, runs only the missing
  specifications and writes a resume manifest. Every run is deterministic for its specification and independent of
  the others, so resumed campaigns equal uninterrupted ones apart from row order and wall-clock fields.
* Execution order changed for robustness against further interruptions: A1 (confirmatory), A3_factorial (amendment
  1), A0 (resume), A3_selective, A3_scenarios. The order is operational and not part of the preregistration; the
  amendment's "after the frozen chain" refers to the use of the frozen source, which is unchanged
  (`scripts/verify_prereg_hashes.py`).

## D09 (2026-11-05 12:36 CST) Title and opening of the final release (V5)
* The authors judged that the V4 title ("Provenance-Bound Industrial Telemetry: Per-Identity Conflict Containment and
  Its Security–Availability Trade-offs", proposed by the memo, which marks its title as optional) made the paper read
  as a different topic from V3.
* Decision (authors): combined title "Provenance-Bound Trust-Aware Ingestion for Industrial IoT Edge-to-Cloud
  Pipelines: Per-Identity Conflict Containment and Its Security–Availability Trade-offs" (V3 name and topic, V4
  trade-off as subtitle); the abstract and the introduction open as in V3 (Zero Trust in brokered IIoT pipelines, the
  PBTI mechanism, "trust continuity at the data-object level") and then state the V4 findings unchanged in
  substance; keyword "edge-to-cloud" restored. No method, result, statistic, gate or claim scope changed. The
  bundle is released as V5; the research records keep their V4 names (frozen hashes).
