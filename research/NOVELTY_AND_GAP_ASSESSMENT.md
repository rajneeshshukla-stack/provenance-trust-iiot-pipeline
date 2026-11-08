# Novelty and gap assessment (stress test)

Evidence base: 15 closest works examined in depth + 13 named sources + standards (see `CLOSEST_PRIOR_WORK.md`).
Search limitations: dblp, OpenAlex and Semantic Scholar unavailable; IEEE Xplore and ACM DL full texts not fetchable.
Every absence statement below is therefore "in the examined literature".

> Note (revision 2): the sections before "Revision 2" record the first-draft assessment and are kept for traceability.
> They are superseded by the "Revision 2" section at the end, which reflects the literature audit, the B4 baseline
> and the narrowed claims of the revised manuscript.

## Stress test of candidate claims

| Claim | Verdict | Reasoning |
|---|---|---|
| A "We introduce Zero Trust to IIoT." | **Rejected as novelty** | Federici 2023, Zanasi 2024, Zhang 2026, James 2025, Wang 2025 (review) already do; NIST SP 800-207 is the foundation. The manuscript uses ZT as foundation only. |
| B "We introduce a secure edge-to-cloud IIoT architecture." | **Rejected as novelty** | Vendor references (Microsoft OPC UA reference solution, AWS IoT Lens) and IIRA/RAMI describe such architectures; the architecture figure is explicitly "supporting". |
| C "Identity + provenance automatically establishes novelty." | **Rejected** | Aman 2017/2019, BlockPro, Saito 2025 and Tsai 2026 combine identity and provenance. Novelty must come from the mechanism-level integration *and* delivery semantics *and* the joint evaluation. |
| D "Data-object trust continuity across identity, authorized ingestion, integrity, provenance and deterministic resilient processing is insufficiently integrated in the closest examined literature." | **Supported (narrowed wording)** | No examined work combines identity-bound, policy-admitted per-event provenance with deterministic delivery-history classification and lineage. Partial integrations acknowledged: Tsai 2026 (identity+policy+revocation history+content addressing, no delivery semantics); MQTT-I and WedgeChain (integrity+ordering/duplicates/equivocation, weak identity, no authorization). Manuscript wording: "none of the examined works combines …". |
| E "Security and distributed event-correctness behaviour are rarely evaluated together in a reproducible IIoT pipeline." | **Supported; reworded to "we found no study that jointly evaluates …"** | MQTT-I and ENTRUST evaluate overhead only; Saito simulates loss only; Matias 2026 evaluates recovery without security; Faraj 2025 (SLR) reports that most provenance studies overlook replay and packet drop. |
| F "The trust-state mechanism makes a measurable methodological contribution beyond implementation integration." | **Partially supported by this study's own evidence** | Evidence produced: (i) Rule L is a set-function of evidence → convergence proven by construction and tested under 60 random permutations with duplicates and forgery; (ii) ablations show causal contribution of each mechanism (A1–A12, Holm-corrected paired tests); (iii) the retry/replay distinction is shown to be unnecessary for safety (both are idempotent) — a design insight that removes a common requirement. Still missing for a stronger claim: formal specification/model checking (e.g., TLA+), and evaluation on real industrial deployments. |

## What is genuinely new (supported)

1. **Relay statement binding workload identity to one signed observation** so that Zero-Trust identity crosses the broker
   (no examined work binds a SPIFFE-like workload identity into IoT data provenance — gap (ii) in the search log).
2. **Rule L**: event-identity slot state as a pure function of admitted versions and successor-implied digests, which
   (a) makes authoritative outcomes order-independent for a fixed admitted evidence set, (b) turns equivocation, and gap-fill whose genuine successor arrives, into contest, and (c) makes the
   retry/replay label non-authoritative.
3. **Lineage-driven taint propagation after retroactive revocation** with origin-key precision (no examined work, gap (iv)).
4. **Joint, paired-seed evaluation** of attacks and delivery failures with three baselines, twelve ablations and an
   independent auditor with decision replay.

## Engineering integration vs research contribution

Technology choices (Ed25519, JCS, X.509/SPIFFE, Merkle trees, MQTT, SQLite) are standard and are **not** claimed. The
contribution is the admission semantics, the state model with invariants, the threat/failure equivalence model, and the
measured trade-offs. Reviewers may still view parts as integration; mitigation: emphasize Rule L, the convergence and
non-authority-of-replay-label results, taint precision, and the ablation evidence.

## Remaining uncertainties

* Possible relevant work behind IEEE Xplore / ACM DL paywalls (search limitation).
* Kovach et al. 2024 was not read (metadata only) — no claims made about it.
* James et al. 2025 abstract only.
* Whether OPC UA PubSub deployments with signing + sequence numbers already provide most of the replay protection
  in practice (no peer-reviewed experimental evaluation found).

## Revision 2 (independent literature and novelty audit, 3 November 2026)

The independent audit (`research/literature/D_revision2_literature_and_novelty_audit.md`) found close, partly standardized prior
art for every PBTI element that the first draft did not cite: IETF SCITT (RFC 9943) for policy-gated registration of signed
statements with receipts and reproducible registration decisions; Secure Scuttlebutt, PeerReview and the Global Data Plane for
hash-linked signed feeds and fork/equivocation evidence; COSE countersignatures through a broker in the IETF ACE pub/sub profile
(RFC 9338) for the relay statement; RFC 5280 invalidity date and C2PA for compromise-time semantics; Taser, Warp and Ammann et al.
for retroactive taint and repair; Sparkplug, Kafka and CloudEvents for producer sequence numbers and first-writer-wins de-duplication.

Revised classification used in the manuscript (Table 1):
* Element 1 (origin statement, event identity, predecessor hash): application of existing techniques.
* Element 2 (relay statement binding a workload identity): integration (countersignature through an MQTT broker for IIoT telemetry).
* Element 3 (versioned path-bound admission, credential lifecycle): integration.
* Element 4 (Rule L): narrow methodological improvement - per-identity contest from admitted versions (order-independent for a fixed admitted set) and
  successor-implied digests, versus first-writer-wins or whole-feed invalidation; its cost is visible under benign sequence faults (E8).
* Element 5 (evidence, decision replay, lineage, taint): integration; taint is an IIoT, revocation-triggered instance of intrusion recovery.

Claims removed or narrowed: "no examined work binds workload identity into provenance" and "no examined work implements taint
propagation from a retroactively revoked credential" are now domain-restricted statements with the analogues cited. The baseline B4 is
described as a combination of mainstream practice; a baseline that also uses the published analogues (B5) was not evaluated and is
listed as open research.
