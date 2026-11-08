# Baseline definitions and documented deviations

All baselines and PBTI share: the storage back-end (`src/pbti/store.py`), the downstream processor
(`src/pbti/processor.py`: 10 s event-time windows, current-value table), the policy document, the identity registry
(X.509 certificates issued by the same CA), the edge buffer and network model. Differences are confined to the wire
format and the admission logic (`src/pbti/baselines.py`).

| | B1 Conventional | B2 Zero-Trust access-controlled | B3 Provenance-focused | PBTI | B4 Strongest combination (revision 2) |
|---|---|---|---|---|---|
| Message protection | none (TLS hop-by-hop assumed) | none (mTLS hop-by-hop assumed) | origin signature (device or gateway key) | origin + relay signatures, `odig` binding | origin signature over the PBTI observation statement (relay statement ignored) |
| Identity used for decisions | transport session (gateway) | transport session (workload SVID) | origin key | origin key + relay workload key | origin key + transport session (workload SVID) |
| Credential status | at session establishment only | every message (continuous) | at verification, no rotation grace | every message, rotation grace, compromise window | every message, same rotation grace as PBTI, no compromise window |
| Authorization | plant-wide publish ACL | path-bound policy (same document as PBTI) | none beyond key registration | path-bound policy + origin requirement | path-bound policy + origin requirement (same document as PBTI) |
| Freshness | none | skew + horizon (reject) | none | skew + horizon (quarantine) | skew + horizon (reject) |
| Duplicate handling | message-id TTL (300 s) + business-key upsert | same as B1 | content-hash uniqueness + business-key upsert | event identity (did, ep, seq) + Rule L | event identity (did, ep, seq), CloudEvents-style de-duplication on a Kafka-like key; exact duplicates suppressed, gaps and reordering accepted |
| Conflicting content | last arrival wins (silent overwrite) | same | last arrival wins | contested (never authoritative) | first writer wins; later versions rejected and logged |
| Ordering for current value | source timestamp | source timestamp | source timestamp | (ep, seq) | (ep, seq) |
| Evidence | bronze append (no integrity anchor) | same | hash-chained ledger + signed heads | Merkle-checkpointed evidence log + witness + receipt log | hash-chained ledger + signed heads (as B3) |
| Lineage/taint | inputs only | inputs only | inputs only | inputs + Merkle root + causes; taint after revocation | inputs only (no taint) |

## Deviations of B3 from the literature class it approximates
* No consensus network or blockchain (a single append-only hash chain with signed heads) — favours B3's latency.
* Legacy devices are signed by the gateway key (provenance schemes rarely specify this case).
* Revocation is checked at verification time (many schemes do not specify revocation at all) — strengthens B3.
* B3 is not a re-implementation of Hasan et al., BlockPro, Sigwart et al. or any other specific system.

## Why B4 was added (revision 2)
An independent audit asked whether a strong combination of existing techniques already reproduces PBTI's outcomes.
B4 combines the strongest elements of B2 and B3 with idempotency on the producer-assigned event identity and PBTI's rotation grace. V3 correction: this is CloudEvents-style de-duplication on a Kafka-like (producer, epoch, sequence) key, not Kafka semantics: Kafka's broker accepts only the next expected sequence number (KIP-98), whereas B4 accepts gaps and reordering.
It deliberately lacks only the PBTI-specific mechanisms (relay statement through the broker, predecessor-link contest,
quarantine archive (with signed review and release; see the correction note at the end), decision-replay evidence and retroactive taint), so differences between B4 and PBTI isolate them.
B4 also removes two configuration choices that disadvantaged earlier baselines: B3's missing rotation grace (E13) and
B1-B3's (device, timestamp) business key (E10).

## Fairness notes
* B1/B2 receive the same mutual-TLS session model as PBTI's transport in the MQTT experiment; in the virtual-time testbed
  the broker attacker (AP1) can claim any publisher identity towards the subscriber, as a compromised broker can.
* Baselines are not given features PBTI lacks; PBTI is not given extra storage or CPU.


## B5 and B5-strict (V3): literature-informed feed-level baselines

Code: `src/pbti/b5.py` (class `B5FeedLevel`), review workflow `src/pbti/review.py`; tests `tests/test_v3_review_b5.py`.
B5 is PBTI with Rule L replaced by a feed-level response and with the automated reviewer added; every other admission
mechanism (origin and relay statements, path-bound policy, credential lifecycle and revocation taint, horizon and epoch
checks, evidence log) is identical. The reviewer acts on every releasable quarantine reason (`review.RELEASABLE`:
STALE_TS, STALE_SLOT, STALE_EPOCH, REVOKED_BUFFERED and B5's FEED_FORK_HOLD), as in the preregistered "quarantine with
review-based recovery", so B5 differs from PBTI in two respects: the conflict response and the reviewer. PBTI-R (below)
adds the same reviewer to PBTI, so PBTI-R versus B5 isolates the conflict response, and PBTI versus PBTI-R the review
workflow (e.g. E11b, where B5 and PBTI-R release the same STALE_TS backlog).

| Element | B5 / B5-strict | Source of the idea |
|---|---|---|
| Statements, relay countersignature, path-bound admission, credential lifecycle, evidence | as PBTI | RFC 9338 second-party countersignature; SCITT registration (RFC 9943) |
| Idempotency | (did, ep, seq); exact duplicates suppressed | CloudEvents (source, id) de-duplication with a Kafka-like key |
| Fork evidence | two admitted contents for one identity, or a successor whose `prev` contradicts the known predecessor | SSB backlinks; PeerReview authenticators; GDP branches |
| Response to a fork | every observation of the feed (did, ep) from the fork point onwards is **held** (stored, not authoritative), including observations that arrive later | Secure Scuttlebutt fork rule (feed ignored from the fork point) |
| Recovery (B5 only) | held observations become review cases (reason FEED_FORK_HOLD), and so do the other releasable quarantine cases (STALE_TS, STALE_SLOT, STALE_EPOCH, REVOKED_BUFFERED); an automated reviewer (period 10 s, minimum case age R = 60 s) releases a held or quarantined observation when its slot has a single digest, no contradicting successor digest and a corroborating hash link (predecessor authoritative with digest = `prev`, or successor-implied digest = its digest), and rejects the others; a feed whose cases are all decided resumes | **our own extension** (none of SSB, PeerReview or GDP has an automated review-and-release step) |
| B5-strict | no recovery: the feed stays frozen for the rest of the run; a new boot epoch starts a new feed | exactly the SSB rule |
| Taint after revocation with t_comp | as PBTI | trigger is PBTI's own |

Every review decision is a signed evidence record (domain `PBTI-v1/quarantine-review`) that the auditor replays.

## PBTI-R (V3, exploratory)

PBTI with the same automated reviewer as B5 (period 10 s, minimum case age 60 s) acting on PBTI's quarantine cases
(releasable reasons: STALE_TS, STALE_SLOT, STALE_EPOCH, REVOKED_BUFFERED before t_comp). It measures the quarantine
release workflow under the same conditions as B5; it is not one of the preregistered confirmatory pipelines.


## V4 additions

* **Review settings (A1).** The V3 reviewer (`rule="oneshot"`, minimum case age R = 60 s, periodic cadence C = 10 s)
  is kept unchanged as `B5-hist` / `PBTI-R-hist`. A1 adds the deferring rule (`rule="defer"`: RELEASE if
  corroborated, REJECT only if contradicted, otherwise keep the case pending) with R ∈ {0, 1, 5, 60} s and
  C ∈ {1, 10} s, and event-driven review (`review_mode="event"`, R = 0: after every admission, the cases whose
  identity or hash-link neighbourhood the admission touched are reviewed immediately, cascading until no further
  case changes). Event-driven review is not R = 0 with a periodic scheduler. The same settings are applied to B5 and
  PBTI-R (matched review). These are operational design points of this testbed, not properties of SSB, PeerReview or
  GDP. Configurations: `experiments/v4_configs/A1_review.json`.
* **PBTI-SH (A3, V4 extension).** Separate class `SelectiveHoldVerifier` (`src/pbti/selective.py`); the historical
  PBTI verifier is unchanged. Rule frozen in `research/V4/PREREGISTRATION_V4.md` and in the module docstring. It
  receives exactly the same evidence as the comparators (no additional evidence source).
* **Release-evidence policy (A5).** All campaigns use `discretionary` (V3); `none` and `witness` are evaluated only
  in the deterministic lifecycle matrix (`scripts/a5_lifecycle_matrix.py`).

> **Correction (V7, 5 November 2026).** Earlier copies of this document said that quarantine release was "not implemented". That was true when the text was first written and stopped being true when the signed review-and-release workflow was added (`src/pbti/review.py`, `src/pbti/verifier.py`; transitions in `docs/STATE_MACHINE.md`, rows 8', 11 and the LOST/ABSENT release rows). Quarantined observations are archived and can be released only through a signed decision by an authorized reviewer, which re-runs admission with only the case's quarantine reason waived. The PBTI arm of the main evaluation runs without a reviewer, so in that stage quarantined data stay archived; the PBTI-R arms and the B5 comparators run with the automated reviewer. Only the phrase was corrected; no result, configuration or code changed.

## B5, corrected implementation (V9)

> **V9, 6 November 2026.** The historical implementation `src/pbti/b5.py` (class `B5FeedLevel`) is unchanged; it is
> listed in the preregistration freeze files and produced every frozen result. The corrected comparator is
> `src/pbti/b5_corrected.py` (class `B5Corrected`, identifier `b5_corrected_v9`); its runs are stored separately in
> `results/v9/raw/` with the implementation identifier, the SHA-256 of both modules and the source digest in every row.
> Regression tests: `tests/test_b5_corrected.py`; differential check against the reference model:
> `tools/v9/b5c_refmodel_diff.py`.

The specification of B5 is the table above, made definite at the six points where the earlier text was silent or
ambiguous (the switches of the reference model, `tools/b5_refmodel/refmodel.py`). The corrected implementation, the
tests and the result labels follow these statements; "(changed)" marks the points at which the historical
implementation did not (two of the six choices, and the recording of hold transitions on which the event-driven rule
depends).

| Point | Specification (V9) | Historical `b5.py` | Corrected `b5_corrected.py` |
|---|---|---|---|
| Fork evidence (switch `fork_rule`) | A receipt triggers the feed-level response only if it adds **new** fork evidence: E1 another admitted version of its identity exists; E2 an admitted successor's `prev` names another digest for its identity; E3 its own `prev` names a digest that is none of the admitted versions of its predecessor (fork point: the predecessor). A successor whose `prev` names one of the versions of an already contested predecessor adds no evidence. New evidence at a later point of a forked feed holds the feed again from that point, including released observations. | re-ran detection from slot state on every receipt at or right after a contested identity: re-held released observations and, after a resume, started a new hold without new evidence (audit F1, reference-model D2) | **(changed)** as specified |
| Review cases (switch `wire_cases`) | Every held committed observation has an open review case (reason FEED_FORK_HOLD) until it is decided. Cases remain keyed by wire digest (one case per wire): a reviewed release of another reason whose re-run admission lands in a held feed continues as that observation's hold case (outcome `DEFERRED_TO_FEED_HOLD`, minimum age counted from the hold); a pending case of another reason for the wire of a newly held observation becomes its hold case; a closed case is replaced by a new hold case. A hold case opened while a review decision is applied is decided from the next periodic pass on (event-driven review: within the same cascade, once its identity is a candidate). | closed such releases as `RELEASE_FAILED:QUARANTINE/FEED_FORK_HOLD` and opened no hold case when the wire already had a pending or closed case, leaving the observation held without a case for the rest of the run (audit F2, reference-model D4) | **(changed)** as specified |
| Review order (switch `order`) | Within a periodic pass, eligible cases are reviewed once each in identity order (did, epoch, sequence, wire digest), decisions taking effect immediately, so that a released predecessor can corroborate its successor in the same pass. Shared with PBTI-R. | identity order | identity order |
| Contested identities (switch `contested_cases`) | A contested identity of a held feed gets no review case (it cannot be released: the reviewer releases only single-digest identities). | no case | no case |
| Resume (switch `resume_timing`) | A forked feed resumes when none of its hold cases is undecided; the condition is checked after each hold-case decision (release or rejection), not at the end of a pass. A feed whose held identities are all contested therefore resumes only after some later hold case is decided. | after each hold-case decision | after each hold-case decision |
| Event-driven candidates (switch `event_scope`) | After an admission, the open cases whose identity or hash-link neighbourhood the admission touched are reviewed (the receipt's identity and its neighbours, identities whose slot state changed, newly opened cases); a release re-examines its neighbours; rounds repeat while new cases or state changes appear (`sim.World._event_review`, unchanged). Every hold transition is a slot-state change. | the rule as stated, but holds made on arrival were not recorded as state changes | **(changed)** every hold transition is recorded; rule unchanged |

Counters (results fields): `holds` counts hold transitions (an identity entering the held set; the historical counter
counted an identity held by the fork its own receipt revealed twice, audit F3 / D5); `fork_events` counts the times a
feed's fork point is set or lowered (now by new evidence only); `held_distinct_ever` counts distinct held identities
(the historical field missed holds made on arrival); `recovered_n` counts release events and the new field
`recovered_distinct` distinct released identities. Releasing a held identity whose slot is tainted is reported as
`RELEASE_FAILED:TAINTED` (historical label: `RELEASE_FAILED:CONFLICT`); labels after the colon enter no result column.

B5-strict (`B5S`, no recovery) uses the same class; without review its authoritative set is identical to that of the
historical implementation (only the counters differ), which the reruns confirm.
