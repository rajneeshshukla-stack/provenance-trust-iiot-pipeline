# A8 crosswalk: manuscript statements ↔ state machine ↔ source ↔ tests ↔ results

Every behavioural statement of the V4 manuscript that concerns admission, Rule L, review, revocation or taint is listed
with the state-machine row it corresponds to (`docs/STATE_MACHINE.md`, Supplementary Tables S3/S4), the source
function that implements it, the tests that check it and the experiment whose results depend on it. Paths are relative
to the repository root. "—" means not applicable.

| # | Manuscript statement (section) | State machine | Source | Tests / checks | Results |
|---|---|---|---|---|---|
| X1 | The relay statement binds exactly one signed observation through `odig` (3.3) | M1 REJECT BINDING_MISMATCH / INTEGRITY_RELAY | `src/pbti/verifier.py` `PBTIVerifier.ingest` | `tests/test_evidence_and_envelope.py`; ProVerif models `formal/*.pv` | E5 stolen-key broker injections rejected (A0 rows, `rx[stolenkey-broker]`) |
| X2 | Rule L: COMMITTED iff \|V(e) ∪ I(e)\| = 1 with a version, CONTESTED iff ≥ 2, ABSENT without a version, LOST after gap closure (3.3) | M2 rows 1–6, 9 | `src/pbti/registry.py` `Slot.state`; `verifier.py` `_history` | `tests/test_registry_rules.py`; `formal/rule_l_bounded_check.py`; `formal/v4_locality_lifecycle_check.py` (C1) | E5, E8 (A0) |
| X3 | Order independence holds for a fixed admitted evidence set, not for every arrival schedule (3.3, 3.4) | I9 | set semantics of `Slot.versions` / `Slot.implied` | permutation tests; V3 bounded check (390,024 orders); V4 check M (both orders) | E9, E10 (A0) |
| X4 | Proposition 1: k admitted statements change evidence, class and authority of at most 2k identities (3.4) | M2 (evidence update) | `verifier.py` `_history` (the only writes to V and I), `b5.py` `_history` | `formal/LOCALITY_PROOF.md` (proof); V4 check M, L, C8 (bounded) | contrast with B5 holds: A1 `W`, `holds` |
| X5 | Identical admitted contents are idempotent; RETRY/SUSPECTED_REPLAY has no authority (3.3) | M1 DUPLICATE; I3 | `_history` duplicate branch | V3 bounded check S4; unit tests | E6, E7 (A0) |
| X6 | Ordinary admission after an observed revocation is refused or quarantined (3.3) | M1 row 11; I7 | `ingest` revocation block | V4 check C5; `tests/test_v3_review_b5.py` | E14 (A0) |
| X7 | A REVOKED_BUFFERED waiver needs the release-evidence condition; discretionary = `ts < t_comp` (3.3) | M2 ABSENT (R) | `verifier.py` `_pre_compromise_ok` | `tests/test_v4_release_evidence.py` | A5 matrix; all campaigns use `discretionary` |
| X8 | The discretionary condition admits backdated forgeries; the witness policy does not (4.x A5) | — | `_pre_compromise_ok`; `src/pbti/timewitness.py` | `test_backdated_forgery_released_only_by_discretionary_policy` | A5 rows `backdated_*` |
| X9 | Taint by commit time ≥ t_comp of the origin key; revised records only move t_comp earlier and re-run the selector; a REVOKED_BUFFERED release is exempt only while its condition holds (3.3) | M2 COMMITTED → TAINTED; I7 | `verifier.py` `_apply_taints`; `identity.py` `TrustRegistry.revoke`, `TrustView.status` | `test_revised_*`, `test_reannounced_*`; V4 check C4; counterexample `results/v4/formal/counterexamples/` | E14 (A0); A5 `full_sequence_revised_taint` |
| X10 | A release re-runs admission with only the case's reason waived; a conflict records evidence, nothing becomes authoritative (3.3) | M2 (R) rows | `verifier.py` `_release` | V3 review tests; V4 check C6 | A5; E11b (A0, A1) |
| X11 | A decision on a stale snapshot is refused and the case returns to QUARANTINED (3.3) | review case machine | `verifier.py` `_apply_review` (STALE_REVIEW) | V3 stale-review test; A5 `stale_reviewer_snapshot`; V4 check C7 | — |
| X12 | A revoked reviewer cannot decide (3.3) | review case machine | `_apply_review` (REVIEWER_REVOKED) | V3 tests; A5 `revoked_reviewer` | — |
| X13 | LOST → COMMITTED/CONTESTED only through an authorized release (STALE_SLOT waived) (Table S3) | M2 LOST rows | `_history` STALE_SLOT guard; `_tick` gap closure | V3 long-gap test; V4 check C (CLOSE + REL) | — (1 h horizon not reached in campaigns) |
| X14 | B5 holds every identity ≥ fork point of the feed until review; B5s never releases (3.6) | — (B5) | `src/pbti/b5.py` `_fork`, `_history`, `_release`, `_maybe_resume` | `tests/test_v3_review_b5.py` | E5, E8 holds (A0); A1 |
| X15 | V3 reviewer: one-shot rule, minimum age 60 s, cadence 10 s (3.6) | — | `src/pbti/review.py` `AutoReviewer(rule="oneshot")`; `sim.py` periodic tick | `tests/test_v3_review_b5.py`; A0 replication | A0 (identical to archive); A1 `-hist` arms |
| X16 | Deferring rule; event-driven review is not R = 0 with a periodic scheduler (3.6) | — | `review.py` `run_on`, `contradicted`; `sim.py` `_event_review` | `tests/test_v4_review_and_selective.py` | A1 |
| X17 | PBTI-SH: suspect feed from first contest; successor-link release only; timeout variant; contested/tainted never released (3.6) | — (separate class) | `src/pbti/selective.py` `SelectiveHoldVerifier` | `tests/test_v4_review_and_selective.py` | A3, A3F, A3 scenario controls |
| X18 | Time-dependent outcomes: (identity, content key) pairs; censoring; withdrawals; freshness; containment; derived exposure; alerts (3.7) | — | `src/pbti/temporal.py` `Tracer`, `compute` | `tests/test_v4_temporal.py` (15 handcrafted traces) | `tm_*` fields of A0, A1, A3 |
| X19 | The tracer's final authoritative set equals the pipeline's in every run (3.7) | — | `temporal.temporal_metrics` | pilot gate `scripts/pilot_gate.py` | `tm_end_state_matches_authoritative` in all rows |
| X20 | The V4 source reproduces the archived V3 rows (4.x) | — | `scripts/compare_a0.py` | — | `results/v4/summary/A0_comparison.json` |
| X21 | The auditor replays decisions including reviews (3.5) | I10 | `src/pbti/audit.py` `audit_pbti` | audit tests | `audit_pass` of audited runs |
| X22 | A witness token binds the exact digest and witness time; an outage yields no token (3.3, 4.x) | — | `timewitness.TimeWitness.stamp`, `valid`, `proves_before` | `test_witness_token_*` | A5 |
| X23 | With a compromise-time interval, recovery requires a token before t_low (4.x) | — | `_pre_compromise_ok` (`compromise_low`) | `test_compromise_interval_width_trades_recovery` | A5 interval rows |
| X24 | No hardware-backed signing, trusted time in deployment, multi-host or device results are claimed (5) | — | — (`experiments/run_multihost.py`, `run_device_bench.py` not run) | — | A6/A7 not executable |

Release verification: the release-evidence policy defaults to `discretionary` in `PBTIVerifier.__init__` and in
`WorldConfig.release_evidence`; every campaign row records its configuration (`cfg`), and no campaign sets another
policy. The revocation/release/taint behaviours X6–X13 were exercised by the V4 bounded lifecycle check
(`results/v4/formal/v4_locality_lifecycle_check.json`, all invariants hold) and by the A5 matrix.
