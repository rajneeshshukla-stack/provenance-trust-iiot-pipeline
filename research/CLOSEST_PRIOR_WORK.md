# Closest prior work — structured comparison

Source records (full extraction, quotes, access level, BibTeX): `research/literature/B_closest_prior_work_records.md`
(15 works examined in depth, 9 screened) and `research/literature/A_named_papers_verification.md` (13 sources named in
the research note). All DOIs were checked against Crossref on 3 Nov 2026. "Not reported" = absent from the examined
text; "n/e" = not examined beyond abstract/metadata.

> Note (revision 2): sections 1-3 record the first-draft comparison of the 15 IoT-focused works. The closer standardized
> and research analogues found later are in the "Revision 2" section and in Table 1 of the revised manuscript.

## 1. Ranked closest works and precise differences

| Rank | Work (DOI) | Access | What it does | Overlap with PBTI | Precise difference |
|---|---|---|---|---|---|
| 1 | Buccafurri, De Angelis, Lazzaro, **MQTT-I**, IEEE TDSC 2024 (10.1109/TDSC.2024.3358630) | author post-print | End-to-end data-flow integrity for MQTT: completeness, correctness, ordering, timeliness via per-topic sequence numbers, out-of-order buffer, hash chains, signed chained Merkle roots per round; untrusted broker | integrity under an untrusted intermediary; ordering; loss detection; Merkle evidence | verification per round (stated vulnerability window), no device credential lifecycle/revocation, no edge-workload identity or path-bound admission, no replay-vs-retry or equivocation classes, no disconnection backlog handling, no raw preservation or lineage; evaluates throughput/energy only |
| 2 | Nawab, **WedgeChain**, ICDE 2021 (10.1109/ICDE51399.2021.00042) | full text | Edge-cloud store with untrusted edge; clients sign entries; cloud lazily certifies digests and detects inconsistent views | client signatures, untrusted intermediary, equivocation-like detection; discusses replay vs idempotent requests | no device/workload identity binding, policy or revocation; replay only discussed; no late/backlog/stale classes; no lineage; raw data stays at edge; key-value workloads, not IIoT |
| 3 | Saito, R10-HTC 2025 (10.1109/R10-HTC63995.2025.11394180) | full text | Tamper-evident sensors sign readouts linked by previous and past digests; Merkle checkpoints anchored on a blockchain; verifiability under data loss | device signatures; hash links; checkpoints | no relay identity, admission, revocation, replay/duplicate/ordering classification; loss tolerance in simulation only |
| 4 | Tsai, Hsieh, Chang, Sensors 2026 (10.3390/s26196262) | full text | Endpoint-signed deterministic records for edge **actuation**, content-addressed bundles, five-step on-chain commitment check (capability, active endpoint, key, scheme not revoked, policy), key history distinguishing retirement from compromise | strongest partial integration of identity, policy, revocation history, content addressing | actuation records, not telemetry streams; no replay/duplicate/ordering/disconnection handling; no edge-workload identity; compromise not propagated to audit outcomes or derived data (no taint) |
| 5 | Dahlmanns et al., **ENTRUST**, SaT-CPS 2021 (10.1145/3445969.3450423) | full text | Transparent end-to-end security for industrial pub/sub: per-topic keys from a key server with ACL authorization; per-publisher counters + time offset/heartbeats detect duplicated or dropped messages | industrial pub/sub; end-to-end integrity; authorization; duplicate/drop detection | symmetric per-topic MAC (no non-repudiation or provenance chain), pre-shared identity, no evidence log, raw preservation, revocation semantics for past data or backlog recovery; overhead-only evaluation |
| runner-up | Lazzaro & Buccafurri, Future Internet 2024 (10.3390/fi16070246) | full text | MQTT accountability via Merkle roots on Ethereum and trees on IPFS; detects modification, injection, deletion, reordering per round | evidence anchoring; same target journal | no per-message signatures; messages discarded after hashing |
| anchor | Hasan, Sion, Winslett, ACM TOS 2009 (10.1145/1629080.1629082) | metadata + FAST'09 version | Signed, chained provenance records preventing history forgery | chained signatures, provenance integrity | no ingestion semantics, identity lifecycle or delivery classification |
| anchor | Kafka idempotent producer (KIP-98 design page; Wang et al., SIGMOD 2021, 10.1145/3448016.3457556) | KIP page full; SIGMOD metadata | producer id + epoch + sequence de-duplicates broker-level retries; epoch fences zombies | **identity structure closest to PBTI's (did, ep, seq)** | no cryptographic binding, provenance or replay-versus-retry security semantics; duplicates treated as benign |

Other examined works (details in the records file): Aman et al. 2017/2019 (PUF/fingerprint data provenance), Javaid et
al. BlockPro 2018, Lim et al. 2010 (provenance-based trustworthiness), Rizzardi et al. AUPS 2016, Gigli et al. ZONIA 2025,
James et al. MQTT-ZT broker 2025 (abstract only), Sukumaran et al. 2026 (ML-to-raw provenance), Matias & Macêdo 2026
(IIoT store-and-forward without security), Yang et al. 2018 (LoRaWAN replay after counter reset), Bu et al. 2021 (OPC UA
PubSub security design), Palyvos-Giannas et al. GeneaLog 2019 (abstract only).

Named in the research note (verification records in file A): Federici et al. 2023 (ZT remote access, SDN+TEE, qualitative);
Wang et al. 2025 (ZT IIoT review, in Chinese); Zhang et al. 2026 (lightweight ZT AKA; claimed date conflict **not
reproduced**: all sources give 6 July 2026); Faraj et al. 2025 (provenance SLR; most studies overlook replay, packet drop,
chain tampering); Sigwart et al. 2019 (blockchain provenance; 1–1.6 TPS; correct-records-at-entry left to future work);
Kovach et al. 2024 (sovereign IIoT data exchange; **metadata only — no content claims made**); Asad et al. 2026 ("replay"
= dataset re-streaming); Lezzi et al. 2025/2026 (IIoT cyber-resilience SLR); Alotaibi 2026 (resilient IoT review);
Rodigari et al. 2021 (ZT multi-cloud overhead); Alayed et al. 2026 (ZT SDN latency/overhead); Zanasi et al. 2024 (flexible
IIoT ZT with Nebula overlay, blacklist revocation).

## 2. Coverage matrix

See Supplementary Table S1 (reproduced from section 2 of the records file). Readings: columns C2 (gateway signing for
legacy devices), C3 (workload identity / relay statement), C6 (replay vs retry) and C12 (taint) are essentially empty in
the examined literature; no row combines identity and authorization with delivery-history correctness and with evidence,
raw preservation and lineage.

## 3. How the manuscript positions itself against each closest work (one sentence each)

* **MQTT-I:** PBTI adds per-event (not per-round) admission bound to origin *and* relay identity under a versioned policy,
  credential lifecycle, delivery-history classification and lineage, and evaluates attacks and failures jointly.
* **WedgeChain:** PBTI admits data at the cloud boundary under identity-bound policy instead of certifying edge digests
  lazily, and implements and evaluates replay/retry, late and backlog semantics.
* **Saito:** PBTI uses the same signed hash-linking idea for gap-fill detection but adds the relay statement, admission,
  revocation semantics and delivery classes, evaluated in a pipeline with baselines.
* **Tsai et al.:** PBTI applies identity-, policy- and revocation-aware commitment to telemetry streams and connects
  compromise to derived data through taint propagation, with explicit delivery semantics.
* **ENTRUST:** PBTI replaces symmetric per-topic protection with per-object signatures and evidence that a third party can
  verify, and handles backlog recovery and retroactive revocation.
* **Kafka idempotent producer:** PBTI adopts the identity structure but binds it cryptographically end to end, classifies
  replays, and treats conflicting duplicates as security evidence.

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
