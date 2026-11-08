# Change log V3 → V4

Starting artifact: the V3 package (which preserves the V2 package unaltered; decision D01). The file-level difference
to the V3 repository is listed in `08_Quality_Assurance/v3_to_v4_file_diff.json` (24 files changed, 52 added, none
removed, not counting the new V4 results and logs in `results/v4/` and `logs/v4/`; historical results byte-identical).

## Source code (frozen before the confirmatory runs; hashes in `research/V4/PREREGISTRATION_V4.sha256`)
* `src/pbti/temporal.py` (new): transition tracer and time-dependent outcomes (R06/A2).
* `src/pbti/review.py`: deferring review rule (`rule="defer"`, `contradicted`), `run_on` for event-driven review (R04/A1);
  the V3 one-shot rule is unchanged and remains the default.
* `src/pbti/sim.py`: review mode/rule/delay/cadence settings, event-driven review trigger, tracer hook, PBTI-SH system,
  release-evidence setting, revocation list for the tracer (defaults reproduce V3).
* `src/pbti/selective.py` (new): PBTI-SH selective evidence-gated holds as a separate class (R08/A3).
* `src/pbti/timewitness.py` (new): testbed time-stamping witness (R09/A5).
* `src/pbti/verifier.py`: release-evidence policy for the REVOKED_BUFFERED waiver (`none` | `discretionary` (default,
  V3) | `witness`); D05: release-aware taint selector (`pre_comp_released`).
* `src/pbti/identity.py`: D05: conservative merge of revised revocation records; trust view reports revised records.
* `src/pbti/audit.py`: replay verifier copies the release-evidence settings.
* `src/pbti/envelope.py`, `src/pbti/sweep.py`: PBTI-SH wire label; sweep keyword settings and long suppression runs.

## Experiments, checks and analysis
* `experiments/run_v4.py`, `experiments/v4_configs/*.json` (A0, A1, A3, A3 controls), `amendment1/A3_factorial.json`.
* `scripts/run_v4_resume.py` (D08), `scripts/compare_a0.py`, `scripts/pilot_gate.py`, `scripts/freeze_prereg.py`,
  `scripts/verify_prereg_hashes.py`, `scripts/a5_lifecycle_matrix.py`, `scripts/export_manuscript_v4.py`.
* `formal/LOCALITY_PROOF.md` (Proposition 1), `formal/v4_locality_lifecycle_check.py` (bounded checks M, L, C).
* `analysis/analyze_v4.py` (macros `\W...`, tables, figures, claim gates), `analysis/validate_v4_stats.py`
  (independent re-computation).
* Tests: `tests/test_v4_temporal.py` (15), `tests/test_v4_review_and_selective.py` (12),
  `tests/test_v4_release_evidence.py` (38), `tests/test_v4_oracle_traces.py` (9).

## Research records
* `research/V4/PREREGISTRATION_V4.md` (+ `.sha256`), `PREREGISTRATION_V4_AMENDMENT_1.md` (+ `.sha256`),
  `DECISION_LOG.md` (D01–D08), `DEVIATIONS_V4.json` (DV1–DV5), `A8_CROSSWALK.md`, this change log.

## Manuscript and supplement
* Title, abstract, keywords, introduction (RQ2, contributions), related work (positioning, Table 1, three new
  references), mechanism (Rule L, credential lifecycle, review and release, Algorithm 1), state model (Proposition 1),
  implementation, baselines, experimental design (metrics, time-dependent outcomes, V4 campaigns and preregistration,
  statistics, AI use), results (replication and time-dependent outcomes, matched review, reviewed release under
  revoked credentials, selective holds), discussion (RQ2, selective holds, security analysis, threats, limitations),
  conclusions, back matter.
* Supplement: Tables S3 and S4 synchronized (release transitions, LOST rows, I7); new Tables S22–S30 and Figure S2;
  V4 sections on
  time-dependent outcomes, replication, matched review, selective holds, reviewed release, locality and bounded checks,
  preregistration and reproduction, comparisons deciding the selective-hold gates.
* After the independent QA review (`08_Quality_Assurance/independent_review_report.md`): claim wording aligned with
  the gate outcomes (G1 and G3/G4 not met; G2, G3F, G4F met), hypotheses and gates defined in Section 3.7, Table S24
  with 90% intervals and Holm-adjusted p, Table S30 added, cover letter corrected.
* Documentation: `docs/STATE_MACHINE.md`, `docs/PROTOCOL_SPECIFICATION.md`, `docs/BASELINES.md`; `Makefile` V4 targets.
* Repository metadata: `README.md` and `paper/README.md` (V4 title and contents), `CITATION.cff` (V4 title, version
  0.4.0); historical notes added at the top of `research/COVER_LETTER.md`, `research/OPEN_RESEARCH_ITEMS.md` and
  `research/RESULTS_TEMPLATE.md` (their V2/V3 text is unchanged).

## Results (V4 campaigns)
* 7,540 runs in five campaigns (A0 1,320; A1 1,760; A3 grid 2,940; A3 controls 400; A3 factorial 1,120), 0 errors;
  every audited run passed; the tracer's end state equalled the pipeline's in every run.
* A0: all 1,320 archived rows reproduced field by field. Gates: G1 not met, G2 met, G3 and G4 not met, G3F and G4F
  met (`results/v4/summary/v4_analysis_report.json`).

## V5 release (authors' decision D09, 5 November 2026)
* Title: "Provenance-Bound Trust-Aware Ingestion for Industrial IoT Edge-to-Cloud Pipelines: Per-Identity Conflict Containment and Its Security–Availability Trade-offs" (V3 name and topic, V4 trade-off as
  subtitle; the memo marks its proposed title as optional).
* Abstract and introduction open as in V3 (Zero-Trust session identity in brokered IIoT edge-to-cloud pipelines,
  the PBTI mechanism, "trust continuity at the data-object level"), followed by the V4 findings unchanged in
  substance; keyword "edge-to-cloud" restored; supplement title, cover letter, README, CITATION.cff and reports
  updated. No method, result, statistic, gate or claim scope changed; research records keep their V4 names.
