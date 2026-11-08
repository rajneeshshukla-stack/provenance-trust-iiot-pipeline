# B. Closest prior work: provenance-bound trust-aware ingestion (IIoT edge-to-cloud)

Prepared: 2026-11-03. Scope: 2009-2026, peer-reviewed primary studies preferred, plus a few technique-defining classics.

## 0. Method, sources and integrity rules applied

- **Bibliographic verification.** Every citation below was checked against its Crossref record (`api.crossref.org/works/<DOI>`). BibTeX comes verbatim from doi.org content negotiation (`Accept: application/x-bibtex`) and was cached in `/tmp/lit/meta/`. Conference locations and dates come from the Crossref `event` field or are printed on the examined PDF (the source is noted in each case). Journal names are given in full, as Crossref records them; apply ISO-4 abbreviations at typesetting.
- **Content verification.** Comparison fields were filled only from text I actually read in this task. Wording used throughout:
  - "Not reported": the examined text does not mention it.
  - "Not examined (abstract only)" or "(metadata only)": no full text was available.
  - Where the examined version is a preprint, an author manuscript or a conference precursor, this is stated.
- **Tool limits encountered.** dblp returned a bot challenge. OpenAlex and Semantic Scholar returned HTTP 429. IEEE Xplore, ACM DL, ScienceDirect and Wiley pages could not be fetched. MDPI PDFs were blocked to curl (the HTML was read instead). Full texts were therefore taken from author, institutional and arXiv copies. Discovery used Crossref keyword search, the arXiv API and web search. Some relevant work behind those paywalls may have been missed.
- **Mechanism components** used for comparison (labels C1-C14):
  - C1: per-event device signature.
  - C2: gateway signing for legacy devices.
  - C3: edge-workload identity or countersigned relay statement.
  - C4: path-bound authorization or admission policy.
  - C5: credential status (rotation, revocation).
  - C6: replay versus legitimate retry.
  - C7: duplicate or equivocation detection.
  - C8: ordering, late or out-of-order handling.
  - C9: disconnection or backlog recovery.
  - C10: hash-chained or Merkle evidence log.
  - C11: content-addressed immutable raw storage.
  - C12: lineage from derived data to raw, and taint on retroactive revocation.
  - C13: IIoT or industrial evaluation.
  - C14: per-item trust or admission scoring.

---

## 1. Ranking: the five closest works

| Rank | Work | DOI | Why closest | Precise difference from the mechanism |
|---|---|---|---|---|
| 1 | Buccafurri, De Angelis, Lazzaro, MQTT-I (TDSC 2024) | 10.1109/TDSC.2024.3358630 | Only examined work that formally defines and enforces end-to-end *data-flow* integrity: completeness, correctness, ordering and timeliness. It uses per-topic sequence numbers, an out-of-order buffer, hash chains and signed, chained Merkle roots, under an untrusted intermediary, on constrained hardware. | Verification is per round, not per event; a round is a stated vulnerability window. There is no device credential lifecycle or revocation, no edge-workload identity or countersignature, and no path-bound admission. There is no replay-versus-retry or equivocation classification, and no disconnection or backlog handling. Raw data is not preserved and there is no lineage. Evaluation covers throughput and energy only. |
| 2 | Nawab, WedgeChain (ICDE 2021) | 10.1109/ICDE51399.2021.00042 | Edge-to-cloud with an untrusted edge. Clients (e.g., IoT sensors) sign entries; the cloud certifies block digests and detects an edge giving inconsistent views (equivocation-like). It explicitly discusses edge replay versus idempotent requests and binding requests to a log position. | No device or workload identity binding, authorization policy or revocation. Replay countermeasures are discussed but not implemented or evaluated. There are no late, backlog or stale classes and no lineage. Raw data stays at the untrusted edge; only digests are certified. It relies on punishment deterrence and assumes malicious acts are not catastrophic. Evaluated on AWS key-value workloads, not IIoT. |
| 3 | Saito (IEEE R10-HTC 2025) | 10.1109/R10-HTC63995.2025.11394180 | The device itself signs readouts (with time and location metadata). Readouts are linked by redundant previous and a-past digests, and Merkle checkpoint evidence is anchored on a blockchain so that verifiability survives data loss. | No edge countersignature or workload identity, no admission policy, no revocation, and no replay, duplicate or ordering classification. Loss tolerance is shown in simulation (with a prototype), not in an IIoT pipeline. |
| 4 | Tsai, Hsieh, Chang (Sensors 2026) | 10.3390/s26196262 | Closest on object-level trust records. The endpoint signs deterministically serialized records that can carry a previous anchor. Bundles are content-addressed off chain. On-chain commitments pass a five-step check (capability, active endpoint, key, scheme not revoked, policy). A key history distinguishes routine retirement from compromise, and the auditor resolves the key valid at commitment time. | Concerns actuation-decision records, not telemetry streams. No replay, duplicate, ordering or disconnection handling and no edge-workload identity. Compromise reports are not connected to audit outcomes or to taint propagation. Evaluation is post-quantum signing latency and gas. |
| 5 | Dahlmanns et al., ENTRUST (SaT-CPS 2021) | 10.1145/3445969.3450423 | Industrial cyber-physical publish/subscribe with end-to-end confidentiality and integrity, key-server access-control list (ACL) authorization per topic, and per-publisher counters with a time offset or heartbeats to detect duplicated or dropped messages. | Uses a symmetric per-topic MAC, so there are no signatures, non-repudiation or provenance chain. Identity is a pre-shared key. There is no evidence log, raw preservation, revocation semantics for past data or backlog recovery. Evaluation measures overhead only. |

Runner-up, important because it appeared in the target journal: Lazzaro & Buccafurri, *Future Internet* 2024 (10.3390/fi16070246). It provides accountability through blockchain transactions, with Merkle roots on Ethereum and Merkle trees on IPFS, and detects modification, injection, deletion and reordering at round granularity. There are no per-message signatures, and messages are discarded after hashing.

---

## 2. Coverage matrix

Codes:
- **Y**: in the described design.
- **Y\***: in the design and also evaluated for that property.
- **P**: partial.
- **Disc**: discussed only.
- **–**: not reported.
- **n/e**: not examined (abstract only).

| Work | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 | C9 | C10 | C11 | C12 | C13 | C14 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MQTT-I 2024 | P | – | – | – | – | – | P | Y | – | Y | – | – | – | – |
| WedgeChain 2021 | Y | – | P | – | – | Disc | Y | P | – | Y | P | – | – | – |
| Saito 2025 | Y/P | – | – | – | – | – | – | – | P (loss, Y\*) | Y | – | – | – | – |
| Tsai 2026 | Y | – | – | Y | Y | – | – | P | – | Y | Y | P | P | – |
| ENTRUST 2021 | P | – | – | Y | P | P | Y | P | – | – | – | – | P | – |
| Lazzaro 2024 (FI) | – | – | – | P | – | – | P | P | – | Y | P | – | – | – |
| Hasan 2009 | P | – | P | – | – | – | P | P | – | Y | P | P | – | – |
| Aman 2017/2019 | P | P | – | P | P | P | – | – | – | – | – | – | – | – |
| BlockPro 2018 | P | – | – | P | P | P | – | – | – | Y | P | – | – | – |
| Lim 2010 | – | – | – | – | – | – | – | – | – | – | – | – | – | Y\* |
| AUPS 2016 | – | – | – | Y | P | Disc | – | – | – | – | – | – | – | P |
| ZONIA 2025 | – | – | – | P | – | – | – | – | – | P | – | – | – | Y\* |
| MQTT-ZT 2025 | n/e | n/e | n/e | Y | n/e | n/e | n/e | n/e | n/e | n/e | n/e | n/e | n/e | n/e |
| Sukumaran 2026 | – | – | – | – | – | – | – | – | – | Y | P | P | – | – |
| Matias 2026 | – | – | – | – | – | – | – | P | Y\* | – | – | – | Y | – |

Matrix readings:
- Columns C2, C3, C6 and C12 (taint) are essentially empty.
- No row combines C1/C3/C4/C5 (identity and authorization) with C6-C9 (event correctness) and C10-C12 (evidence, raw data and lineage).

---

## 3. Per-work records (15 works)

### 3.1 BUCCAFURRI2024 (MQTT-I)

**Bibliographic record**

- **VERIFIED CITATION:** Buccafurri, F.; De Angelis, V.; Lazzaro, S. MQTT-I: Achieving End-to-End Data Flow Integrity in MQTT. *IEEE Transactions on Dependable and Secure Computing* **2024**, *21*, 4717–4734. https://doi.org/10.1109/TDSC.2024.3358630
- **BIBTEX:** `@article{Buccafurri_2024, title={MQTT-I: Achieving End-to-End Data Flow Integrity in MQTT}, volume={21}, ISSN={2160-9209}, url={http://dx.doi.org/10.1109/tdsc.2024.3358630}, DOI={10.1109/tdsc.2024.3358630}, number={5}, journal={IEEE Transactions on Dependable and Secure Computing}, publisher={Institute of Electrical and Electronics Engineers (IEEE)}, author={Buccafurri, Francesco and De Angelis, Vincenzo and Lazzaro, Sara}, year={2024}, month=Sept, pages={4717–4734} }`
- **TYPE:** Journal.
- **SOURCES:**
  - https://api.crossref.org/works/10.1109/tdsc.2024.3358630
  - Author post-print: https://iris.unirc.it/retrieve/4886410f-f55e-4e1e-8105-b96b48b4331c/Buccafurri_2024_TDSC_MQTT-I_Post.pdf
- **ACCESS:** Full text (author's accepted version; the post-print itself notes the content may differ from the final version).

**Comparison fields**

- **Research problem:** End-to-end data-flow integrity in MQTT when the broker is untrusted. The authors state that no prior proposal targets this threat model.
- **Domain:** Generic MQTT IoT (examples: smart city, safety monitoring).
- **Architecture:**
  - Publisher, broker and subscriber; data are split into time rounds.
  - Publisher: per-topic hash chain `D[x] = H(m || D[x])` and per-topic sequence numbers. At the end of each round it builds a Merkle tree over the topic digests and signs `Hr = H(pr || cr || τp)`, chaining the previous root (Section 7.1, Algorithm 1).
  - Broker: computes the authentication paths (Section 7.2).
  - Subscribers: recompute roots and verify the signature (Section 7.3).
- **Zero-Trust depth:** Zero Trust is not claimed. Trust is removed from the broker; no continuous authorization.
- **Device identity:** The publisher's public/private key pair (Ed25519). Provisioning and PKI are not reported.
- **Workload identity:** Not reported.
- **Authorization:** Not reported.
- **Payload integrity:** Hash chain per topic plus one publisher signature per round (no per-message signature).
- **Provenance:** Publisher-signed round roots chained across rounds. No multi-hop provenance.
- **Lineage:** Not reported.
- **Replay treatment:** The word "replay" is not used. Rounds are bound by a timestamp τp, which subscribers check against local time modulo a threshold δ (Section 7.3). Compromises C1-C5 cover modification, injection, deletion, reordering and delay (Section 4).
- **Duplicate treatment:** "The introduction of the sequence number is necessary to guarantee message ordering and prevent duplicate messages" (Section 7.1). The authors note that QoS 2 avoids duplicates but does not guarantee ordering, and require at least QoS 1.
- **Event ordering:**
  - Weak liveness (order preserved) and strong liveness (delivery within Δ) are defined formally (Section 4).
  - A subscriber buffers out-of-order messages in a hash map keyed by sequence number, which the authors expect to be "very uncommon" (Section 7.3).
- **Disconnected-edge recovery:** Not reported. Clients may join and leave dynamically, but buffering or backlog is not described.
- **Raw preservation:** Not reported. Entities keep only digests. The broker discards the Merkle tree after providing paths and publishes only signed chained roots (Section 1).
- **Threat model:** Untrusted broker, or man-in-the-middle, able to perform C1-C5 (Section 4). Security analysis in Section 11.
- **Implementation:**
  - Publishers and subscribers on Raspberry Pi Pico W (Cortex-M0+, 133 MHz).
  - Broker built by customizing a HiveMQ Java library, on a laptop (i7-8850, 1.8 GHz, 16 GB).
  - ArduinoMQTT, Arduino Cryptography Library, SHA-256 and Ed25519 (Section 10.1).
- **Testbed:** Physical devices over Wi-Fi.
- **Baselines:** Standard MQTT, and a "baseline approach" (Section 6) that achieves the same security goals with per-topic signatures.
- **Metrics and results:**
  - Table 3 operation times:
    - hashing 0.147 ms;
    - signing 244.993 ms;
    - verification 390.775 ms;
    - QoS-1 publish 50.551 ms;
    - Merkle tree for 100 topics 14.684 ms.
  - Publishers:
    - Standard MQTT reaches about 20 msg/s.
    - With RT = 15 s, MQTT-I differs from MQTT by less than 1.7% (Fig. 2).
    - The baseline drops to 0 msg/s at |Tp| = 50.
    - With |Tp| = 20, MQTT-I reaches 6 msg/s at RT = 0.45 s and 16 msg/s at RT = 2 s; the baseline needs RT = 6.5 s for 1 msg/s (Fig. 3).
  - Subscribers: about 5% difference from MQTT (Fig. 4); MQTT-I approaches MQTT when RT > 6 s (Fig. 5).
  - Energy: measured for 2000 packets (Fig. 6). Cryptography adds about 1 mA against about 60 mA for Wi-Fi.
- **Limitations (stated):** The round time is a "vulnerability window", so the scheme may be unsuitable for hard real-time applications needing millisecond-level integrity (Section 10.5).
- **Artifacts:** No code link found.

**OVERLAP:** Per-producer sequence numbers for duplicate and ordering control; hash chaining; signed, chained commitments; an untrusted intermediary; formal treatment of deletion, reordering and delay.

**PRECISE DIFFERENCE:**
- Integrity is checked per round, not per event at ingestion.
- No identity lifecycle (rotation, revocation), no workload countersignature and no device-asset-workload policy.
- Sequence numbers reset every round, and there is no boot-epoch notion.
- No classification of idempotent retry, replay, equivocation, late, backlog or stale arrivals.
- No immutable raw store and no lineage or taint.

---

### 3.2 NAWAB2021 (WedgeChain)

**Bibliographic record**

- **VERIFIED CITATION:** Nawab, F. WedgeChain: A Trusted Edge-Cloud Store With Asynchronous (Lazy) Trust. In Proceedings of the 2021 IEEE 37th International Conference on Data Engineering (ICDE), Chania, Greece, 19–22 April 2021; pp. 408–419. https://doi.org/10.1109/ICDE51399.2021.00042
- **BIBTEX:** `@inproceedings{Nawab_2021, title={WedgeChain: A Trusted Edge-Cloud Store With Asynchronous (Lazy) Trust}, url={http://dx.doi.org/10.1109/icde51399.2021.00042}, DOI={10.1109/icde51399.2021.00042}, booktitle={2021 IEEE 37th International Conference on Data Engineering (ICDE)}, publisher={IEEE}, author={Nawab, Faisal}, year={2021}, month=Apr, pages={408–419} }`
- **TYPE:** Conference.
- **SOURCES:**
  - https://api.crossref.org/works/10.1109/icde51399.2021.00042 (includes the event record)
  - arXiv:2012.02258v1: https://arxiv.org/pdf/2012.02258v1
- **ACCESS:** Full text of the arXiv v1 preprint (Dec 2020). The ICDE version was not examined.

**Comparison fields**

- **Research problem:** An edge-cloud data store in which edge nodes are untrusted and edge-cloud coordination is expensive.
- **Domain:** Edge-cloud applications. IoT sensors are given as the example clients.
- **Architecture:**
  - Clients (authenticated, signing), untrusted edge nodes (log and LSMerkle index) and a trusted cloud node.
  - Phase I commit: an edge-signed promise.
  - Phase II commit: the cloud signs the block digest if it is the first digest for that block id; otherwise it "detects a malicious activity and rejects the request" (Section IV.B).
- **Zero-Trust depth:** Zero Trust is not claimed. The edge is untrusted, the cloud is trusted, and trust is lazy and asynchronous.
- **Device identity:** "Clients are authenticated nodes"; generated data "is signed". The key infrastructure is not reported.
- **Workload identity:** Not reported. All message exchanges are signed by the sender, including edge promises.
- **Authorization:** Not reported.
- **Payload integrity:** Client signatures; block digests certified by the cloud.
- **Provenance:** Signed client entries plus cloud-certified digests. A client can use the edge's signed promise to prove the edge lied.
- **Lineage:** Not reported.
- **Replay treatment (Section IV.E, discussion only):**
  - A replay is "the malicious edge node repeating a valid client request more than once".
  - In many edge applications requests are idempotent ("a sensor indicating that the temperature reading is x at timestamp ts has the same effect when repeated").
  - Timestamps, session ids or prior state can be added on the client side.
  - Alternatively, a client can sign each request for a reserved log position.
- **Duplicate treatment:** Covered only by the idempotency discussion above.
- **Equivocation:** The cloud detects inconsistent views by accepting only the first digest per block id (Section IV.B).
- **Event ordering:** Block ids are unique, monotonic numbers assigned by each edge node (Section III).
- **Disconnected-edge recovery:** Not reported.
- **Omission:** Omission attacks are mitigated by gossip messages signed by the cloud; omission of recent data remains possible (Section IV.E).
- **Raw preservation:** Data stays at the edge. The cloud stores only digests ("data-free certification").
- **Threat model:**
  - Byzantine edge, trusted cloud.
  - Assumes enforceable punishment, and that "malicious acts cannot lead to catastrophic consequences" (Section II).
- **Implementation:** WedgeChain plus the LSMerkle index.
- **Testbed:** Amazon EC2 m5d.xlarge machines across datacenters. California hosts the edge, Virginia the cloud; RTTs are 19–238 ms (Table I).
- **Baselines:** Cloud-only and Edge-baseline (Fig. 1).
- **Metrics and results:**
  - Latency as batch size grows from 100 to 2000 (Fig. 4a): WedgeChain 15 → 20 ms; Cloud-only 78 → 83 ms; Edge-baseline 109 → 213 ms.
  - Throughput (Fig. 4b): WedgeChain 6.6K → about 100K ops/s (15×).
- **Limitations (stated):** The punishment and deterrence assumptions; omission of recent data; single-partition operations.
- **Artifacts:** No code link found.

**OVERLAP:** Untrusted edge relays signed device data; the trusted cloud verifies and keeps a digest evidence log; equivocation detection; explicit replay-versus-idempotent reasoning.

**PRECISE DIFFERENCE:**
- Not IIoT.
- No device, asset or workload policy, and no credential revocation or taint.
- Replay and idempotency defences are only discussed, not implemented or evaluated.
- No late, backlog or stale classification and no disconnection recovery.
- Raw data is not preserved in a trusted content-addressed store.
- Trust relies on deterrence, which the paper restricts to non-catastrophic settings.

---

### 3.3 SAITO2025

**Bibliographic record**

- **VERIFIED CITATION:** Saito, K. Proof of Authenticity of General IoT Information with Tamper-Evident Sensors and Blockchain. In Proceedings of the 2025 IEEE 13th Region 10 Humanitarian Technology Conference (R10-HTC), Ichikawa, Japan, 29 September–1 October 2025; pp. 258–263. https://doi.org/10.1109/R10-HTC63995.2025.11394180
- **BIBTEX:** `@inproceedings{Saito_2025, title={Proof of Authenticity of General IoT Information with Tamper-Evident Sensors and Blockchain}, url={http://dx.doi.org/10.1109/r10-htc63995.2025.11394180}, DOI={10.1109/r10-htc63995.2025.11394180}, booktitle={2025 IEEE 13th Region 10 Humanitarian Technology Conference (R10-HTC)}, publisher={IEEE}, author={Saito, Kenji}, year={2025}, month=Sept, pages={258–263} }`
- **TYPE:** Conference.
- **SOURCES:**
  - https://api.crossref.org/works/10.1109/r10-htc63995.2025.11394180
  - arXiv:2512.18560v1 (accepted manuscript): https://arxiv.org/pdf/2512.18560v1
- **ACCESS:** Full text (arXiv accepted manuscript).

**Comparison fields**

- **Research problem:** Ensuring the authenticity (content, origin, time, location) of sensor data relayed through untrusted IoT services, while tolerating data loss (Section 3).
- **Domain:** General IoT; humanitarian, logistics and disaster-response settings.
- **Architecture:**
  - A tamper-evident sensor performs an atomic action: it returns a signed readout to the service and sends evidence to a neutral blockchain service (Section 4.1, Fig. 4).
  - The evidence is aggregated into a Merkle tree whose root is written to a blockchain; an Ethereum anchoring contract from the authors' BBc project is shown (Figs. 1–2).
  - For streams, evidence is sent only at periodic signed checkpoints (Fig. 5).
- **Zero-Trust depth:** Zero Trust is not claimed. Trust in intermediate services is minimized.
- **Device identity:** A public key identifies the sensor; keys are "lightweight self-managed public keys without centralized provisioning" (Section 7). PUFs are suggested for tamper evidence.
- **Workload identity:** Not reported.
- **Authorization:** Not reported.
- **Payload integrity:** Signatures over readouts and digests; previous and a-past digest links (Section 4.3).
- **Provenance:** Readout metadata includes time and location; the witness section carries digests (Section 4.2).
- **Lineage:** Not reported.
- **Replay treatment:** Not reported.
- **Duplicate treatment:** Not reported.
- **Event ordering:** Implicit in the digest chain; not otherwise reported.
- **Disconnected-edge recovery:** Not reported as such. Loss tolerance: a readout with up to a−1 consecutive losses can be re-linked to a checkpoint (Section 4.3).
- **Raw preservation:** Not reported. The blockchain records existence and integrity, not contents.
- **Threat model:** Untrusted services may alter, drop or delay data. Sensors are assumed tamper-evident; a compromised sensor could still emit well-formed false values (Sections 3, 4.1).
- **Implementation:** Simulation plus a prototype published on GitHub (Section 5.4).
- **Testbed:** Synthetic stream of 10,000 readouts with loss probability p ∈ [0, 0.5]. Results come from single runs, with trends said to be consistent across repeats (Section 5).
- **Baselines:** Parameter sweeps only. Related schemes are compared qualitatively (Section 7).
- **Metrics and results:**
  - s = 1 makes every non-lost readout verifiable.
  - a = 1 behaves like a singly linked list, where one loss breaks verifiability of everything after it.
  - Diminishing returns appear beyond about a = 10 (Figs. 7–9, Section 5).
  - Moderate redundancy (3- to 10-step links) is reported as sufficient (Section 6).
- **Limitations (stated):** Tamper-evident hardware is assumed; parameters a and s must be tuned or adapted.

**OVERLAP:** Device-signed observations with backward hash links; Merkle-aggregated external evidence log; verifiability under loss.

**PRECISE DIFFERENCE:**
- No gateway signing for legacy devices and no edge-workload countersignature.
- No admission policy and no credential status.
- No classification of retry, replay, duplicate, late or backlog arrivals.
- No immutable raw store or lineage.
- Evaluated by simulation, not in an IIoT pipeline.

---

### 3.4 TSAI2026

**Bibliographic record**

- **VERIFIED CITATION:** Tsai, K.-Y.; Hsieh, Y.-Y.; Chang, C.-C. Tamper-Evident Provenance for Secure IoT Edge Actuation with Signature-Independent On-Chain Commitments. *Sensors* **2026**, *26*, 6262. https://doi.org/10.3390/s26196262
- **BIBTEX:** `@article{Tsai_2026, title={Tamper-Evident Provenance for Secure IoT Edge Actuation with Signature-Independent On-Chain Commitments}, volume={26}, ISSN={1424-8220}, url={http://dx.doi.org/10.3390/s26196262}, DOI={10.3390/s26196262}, number={19}, journal={Sensors}, publisher={MDPI AG}, author={Tsai, Kuo-Yu and Hsieh, Yu-Yun and Chang, Che-Cheng}, year={2026}, month=Oct, pages={6262} }`
- **TYPE:** Journal.
- **SOURCES:**
  - https://api.crossref.org/works/10.3390/s26196262
  - https://www.mdpi.com/1424-8220/26/19/6262
- **ACCESS:** Full text (HTML), read in two passes:
  - Sections 1–5.1 and the closing part were read.
  - Table 1 is an image and was not readable.
  - Some middle text was truncated.

**Comparison fields**

- **Research problem:** Making post-incident evidence for IoT actuation decisions auditable and attributable to a registered endpoint (Section 1).
- **Domain:** Edge actuation, with a manufacturing authorization context drawn from the authors' prior work.
- **Architecture:**
  - Four actors: edge endpoint, content-addressed off-chain store (Walrus as the example), a Move contract on Sui, and an auditor (Section 3.1).
  - The on-chain commitment holds endpoint id, a SHA-256 anchor, blob id, schema label, scheme id and ledger timestamp; it contains no signature (Section 4.2).
- **Zero-Trust depth:** Zero Trust is not claimed. Each commitment is policy-checked.
- **Device identity:**
  - Endpoint object with owner, label, active flag and per-scheme public keys, plus an EndpointCap (Section 4.2).
  - Signature schemes are agile: Ed25519, ML-DSA, SLH-DSA.
- **Workload identity:** Not reported.
- **Authorization:**
  - `create_commitment` runs a five-step check: capability and owner, endpoint active, key held for the scheme, scheme registered and not REVOKED, and any optional CommitmentPolicy (Section 4.2, Fig. 3).
  - Execution authorization is delegated to the prior work [11].
- **Payload integrity:** The endpoint signs a deterministically serialized record. serde_json is used in the prototype, and BCS or JCS is recommended for production (Section 4.1).
- **Provenance:** The record holds schema version, task id, endpoint id, decision label, design-file hash, sensor-log hash, timestamp, telemetry and an optional previous anchor (Section 4.1).
- **Lineage:** Partial: the design-file and sensor-log hashes. Taint propagation is not reported.
- **Replay treatment:** Not reported.
- **Duplicate treatment:** Not reported.
- **Event ordering:** The optional previous anchor can form a local hash chain, but the contract "does not require that chain structure". The ledger is assumed to provide append-only ordering (Sections 3.2, 4.1).
- **Disconnected-edge recovery:** Not reported.
- **Raw preservation:** Full records and signatures are kept in an off-chain bundle referenced by blob id. The CLI does not retrieve bundles from Walrus (Section 3.1).
- **Credential status:**
  - KeyHistory records add and detach times and whether a detach was "a routine retirement or a compromise report".
  - The auditor uses the key "whose interval contains the commitment timestamp".
  - The history is capped at 64 records per endpoint (Section 4.2).
  - The text "does not say how an auditor treats commitments made before versus after a key is reported compromised".
- **Threat model:** External attacker; malicious endpoint (conditionally attributable); authorized-but-curious endpoint (Section 3.2). Physical truthfulness of data and signing time are not established (Abstract).
- **Implementation:** Rust CLI (`provenance-audit`) and a Sui Move package with 38 unit tests. The paper refers to "the public artifact"; no repository URL was found in the examined text.
- **Testbed:** Raspberry Pi 5 and Apple M1 Pro; Sui localnet (Sections 4.4, 5.1).
- **Baselines:** Ed25519 as the classical control (Section 4.5).
- **Metrics and results:**
  - Commitment gas is identical across Ed25519, ML-DSA-44 and SLH-DSA-SHA2-128f, despite a 267-fold range in signature size (Abstract).
  - On the Pi 5, the ML-DSA-44 sign median is 648.2 µs as the mean of run medians, or 593.3 µs pooled (Table 8).
  - SLH-DSA-SHA2-128s takes about 229 ms per signature (Section 5.1).
- **Limitations (stated):**
  - Results come from a localnet.
  - Verification timing repeats a single bundle, so it is not an end-to-end audit throughput figure.
  - Keys were not retained, so anomalous key sets cannot be remeasured.

**OVERLAP:** Canonically serialized signed records with hash linking; content-addressed raw bundles plus a ledger anchor; credential rotation and compromise history resolved at evidence time; policy-gated admission of commitments.

**PRECISE DIFFERENCE:**
- Commitments are single-hop (endpoint to ledger); there is no edge relay countersignature.
- No delivery-history semantics: retry, replay, equivocation, late, backlog, stale.
- Compromise reports are not propagated to past or derived data.
- The domain is actuation decisions, not high-rate telemetry ingestion.

---

### 3.5 DAHLMANNS2021 (ENTRUST)

**Bibliographic record**

- **VERIFIED CITATION:** Dahlmanns, M.; Pennekamp, J.; Fink, I.B.; Schoolmann, B.; Wehrle, K.; Henze, M. Transparent End-to-End Security for Publish/Subscribe Communication in Cyber-Physical Systems. In Proceedings of the 2021 ACM Workshop on Secure and Trustworthy Cyber-Physical Systems (SaT-CPS '21), Virtual Event, USA, 28 April 2021; pp. 78–87. https://doi.org/10.1145/3445969.3450423
- **BIBTEX:** `@inproceedings{Dahlmanns_2021, series={CODASPY ’21}, title={Transparent End-to-End Security for Publish/Subscribe Communication in Cyber-Physical Systems}, url={http://dx.doi.org/10.1145/3445969.3450423}, DOI={10.1145/3445969.3450423}, booktitle={Proceedings of the 2021 ACM Workshop on Secure and Trustworthy Cyber-Physical Systems}, publisher={ACM}, author={Dahlmanns, Markus and Pennekamp, Jan and Fink, Ina Berenice and Schoolmann, Bernd and Wehrle, Klaus and Henze, Martin}, year={2021}, month=Apr, pages={78–87}, collection={CODASPY ’21} }`
- **TYPE:** Workshop (co-located with ACM CODASPY '21).
- **SOURCES:**
  - https://api.crossref.org/works/10.1145/3445969.3450423
  - https://www.comsys.rwth-aachen.de/fileadmin/papers/2021/2021-dahlmanns-entrust.pdf
- **ACCESS:** Full text (author PDF). The date and "Virtual Event, USA" are printed in the paper's ACM reference format.

**Comparison fields**

- **Research problem:** End-to-end security for industrial publish/subscribe without trusting, or modifying, the broker (Section 3).
- **Domain:** Industrial cyber-physical systems.
- **Architecture:**
  - A key server acting as an ordinary pub/sub client.
  - A per-client pre-shared key exchanged out of band.
  - An ECDH handshake over dedicated key-exchange topics.
  - Topic keys issued under an ACL (Section 5).
- **Zero-Trust depth:** Zero Trust is not claimed. Trust is moved from the broker to the key server.
- **Device identity:** A pre-shared key per client.
- **Workload identity:** Not reported.
- **Authorization:** The key server's ACL decides which clients receive which topic keys (Section 5.2).
- **Payload integrity:** ChaCha20-Poly1305 with a symmetric topic key; non-repudiation is not reported.
- **Provenance:** Not reported.
- **Lineage:** Not reported.
- **Replay treatment:** Requirement R2 covers "dropped or duplicated and replayed messages"; a per-publisher message counter detects reuse (Sections 3.2, 6).
- **Duplicate treatment:** Counter-based detection of duplicated messages (Section 5.3).
- **Event ordering:**
  - Dropped messages are detected when the next message from the same publisher arrives.
  - A time offset or heartbeats signal when the next message is due (Sections 5.3, 6).
- **Disconnected-edge recovery:** Not reported.
- **Raw preservation:** Not reported.
- **Key rotation:** Topic keys are renewed on revoked access rights or timeout, and messages carry key ids (Section 5.2).
- **Threat model:** A misconfigured, malicious or compromised broker (Section 3.1).
- **Implementation:** Photon MQTT library, Arduino Cryptography Library and X25519 (Section 7).
- **Testbed:** Three RedBear Duo devices (Cortex-M3, 120 MHz) and Mosquitto on a Raspberry Pi 3. Results are means of 30 runs with 99% confidence intervals.
- **Baselines:** The same stack without security. Related work is compared in Table 1, which covers OPC UA PubSub, SMQTT, JEDI, PICADOR, MQT-TZ and MOUCON.
- **Metrics and results:**
  - ECDH takes about 97 ms, of which 93 ms is public-key operations.
  - A topic-key exchange takes 4.3 ms at the client and 4.4 ms at the key server (Section 7.1).
  - Per-message overhead is 67% at 128 B and 53% at 1 kB against the unprotected stack; encryption and authentication take 0.2 ms at 128 B (Section 7.2).
  - Each message grows by 42 B (Section 7.3).
- **Limitations (stated):** The PSK bootstrapping configuration overhead; the key server must be trusted and must not be run by potentially malicious cloud providers (Section 6).
- **Note on OPC UA PubSub (Section 4):** The authors' qualitative assessment is that OPC UA PubSub "includ[es] a sequence number in the message header and signature for dropping and duplication detection". Its security key service, however, must be reachable out of band, which may add attack vectors.

**OVERLAP:** Industrial setting; end-to-end payload protection across an untrusted broker; ACL-based authorization; counter-based duplicate, replay and drop detection.

**PRECISE DIFFERENCE:**
- The symmetric MAC gives no per-device attribution or non-repudiation; there is no provenance or relay chain and no workload identity.
- Counters cannot separate legitimate retry from replay or equivocation.
- No evidence log, raw preservation, backlog recovery or lineage.
- Only overhead was evaluated.

---

### 3.6 LAZZARO2024 (Future Internet)

**Bibliographic record**

- **VERIFIED CITATION:** Lazzaro, S.; Buccafurri, F. Achieving Accountability and Data Integrity in Message Queuing Telemetry Transport Using Blockchain and Interplanetary File System. *Future Internet* **2024**, *16*, 246. https://doi.org/10.3390/fi16070246
- **BIBTEX:** `@article{Lazzaro_2024, title={Achieving Accountability and Data Integrity in Message Queuing Telemetry Transport Using Blockchain and Interplanetary File System}, volume={16}, ISSN={1999-5903}, url={http://dx.doi.org/10.3390/fi16070246}, DOI={10.3390/fi16070246}, number={7}, journal={Future Internet}, publisher={MDPI AG}, author={Lazzaro, Sara and Buccafurri, Francesco}, year={2024}, month=July, pages={246} }`
- **TYPE:** Journal (the target journal).
- **SOURCES:**
  - https://api.crossref.org/works/10.3390/fi16070246
  - https://www.mdpi.com/1999-5903/16/7/246 (HTML)
  - Publisher PDF via https://iris.unirc.it/retrieve/a7c8741b-3bc9-4907-9c25-5f266675bdeb/Buccafurri_2024_FutInt_Achieving_Editor.pdf
- **ACCESS:** Full text.

**Comparison fields**

- **Research problem:** End-to-end data-flow integrity and accountability (non-repudiation by publisher and broker) in MQTT with an untrusted broker (Sections 4, 5).
- **Domain:** MQTT IoT (examples: healthcare, smart city).
- **Architecture:**
  - Temporal rounds and per-topic hash chains `H_t = Hash(m_t || H_{t-1})`.
  - The broker builds a Merkle tree over the topic chains, stores the tree on IPFS and records (root, IPFS address) in an Ethereum contract.
  - Publishers and subscribers verify the root against the contract, and alarm events signal violations (Sections 5.2–5.4).
- **Zero-Trust depth:** Zero Trust is not claimed. Trusted third parties are avoided.
- **Device identity:** Ethereum accounts; the broker adds publishers "upon authenticating" them, method unspecified (Section 5.2).
- **Workload identity:** Not reported.
- **Authorization:** Contract functions are restricted to registered clients or the owner. Topic-level authorization is not reported.
- **Payload integrity:** Hash chains and Merkle roots; per-message signatures are not used.
- **Provenance and accountability:** Blockchain transactions prevent the broker or publisher from denying that it sent a flow (Section 8.4.2).
- **Lineage:** Not reported.
- **Replay treatment:** Not reported as such. The adversary can modify, inject, delete or reorder messages (Section 8.2).
- **Duplicate treatment:** Not reported.
- **Event ordering:** Weak liveness (order preserved) is a target property (Section 8.3).
- **Disconnected-edge recovery:** Not reported.
- **Raw preservation:** Not preserved. After hashing, "the message is no longer needed and thus can be discarded" (Section 5.5). IPFS stores the Merkle tree, not the messages.
- **Threat model:** A malicious broker or man-in-the-middle; repudiation by publisher or broker. Assumes Ethereum account ownership and standard hash-function properties (Sections 8.1–8.2).
- **Implementation:** Customized HiveMQ broker; Raspberry Pi Pico W clients plus calibrated simulated clients; Sepolia testnet; IPFS Desktop (Section 7.1).
- **Testbed:** A temperature dataset with data roughly every 30 s (Section 7.2).
- **Baselines:** Not experimental. Section 5.5 compares Merkle trees over topics against trees over messages analytically.
- **Metrics and results:**
  - Gas (Section 6.1, Table 1): deployment 461,322 gas (about USD 23); addClient 68,401; addRootIPFSAddress 47,016; pullTheAlarm 26,763.
  - Contract calls take more than 15 s on average (Table 2: addRootIPFSAddress 18.088 s at the broker; getIPFSAddress 16.331 s at the client).
  - Client throughput falls by at most 20% at one round per 60 s, and by less than 10% for rounds longer than 5 min (Section 7.2).
  - Broker throughput falls by less than 3% for rounds longer than 5 min.
  - 1000 topics need about 32 KB of storage (Section 5.5).
- **Limitations (stated):** The round frequency limits hard real-time use (Section 7.3). Future work: adaptive round frequency (Section 9).

**OVERLAP:** Hash-chained flow evidence; Merkle roots anchored externally; content-addressed (IPFS) evidence storage; detection of deletion, injection and reordering; accountability.

**PRECISE DIFFERENCE:**
- No per-event device signature, edge countersignature, admission policy or credential status.
- Raw messages are discarded rather than preserved.
- No event classification (retry, replay, equivocation, late) and no recovery.
- No lineage.

---

### 3.7 HASAN2009 (seminal classic: secure provenance chains)

**Bibliographic record**

- **VERIFIED CITATION:** Hasan, R.; Sion, R.; Winslett, M. Preventing History Forgery with Secure Provenance. *ACM Transactions on Storage* **2009**, *5*, 1–43. https://doi.org/10.1145/1629080.1629082
- **BIBTEX:** `@article{Hasan_2009, title={Preventing history forgery with secure provenance}, volume={5}, ISSN={1553-3093}, url={http://dx.doi.org/10.1145/1629080.1629082}, DOI={10.1145/1629080.1629082}, number={4}, journal={ACM Transactions on Storage}, publisher={Association for Computing Machinery (ACM)}, author={Hasan, Ragib and Sion, Radu and Winslett, Marianne}, year={2009}, month=Dec, pages={1–43} }`
- **TYPE:** Journal.
- **SOURCES:**
  - https://api.crossref.org/works/10.1145/1629080.1629082, including the abstract.
  - Conference version, read in full: "The Case of the Fake Picasso: Preventing History Forgery with Secure Provenance", 7th USENIX Conference on File and Storage Technologies (FAST '09), https://static.usenix.org/legacy/events/fast09/tech/full_papers/hasan/hasan.pdf (no DOI).
- **ACCESS:**
  - Journal article: abstract only (via Crossref).
  - Mechanism details below come from the FAST '09 full text, which is the conference precursor with the same title core and authors.

**Comparison fields**

- **Research problem:** Integrity and confidentiality of provenance chains crossing untrusted environments.
- **Domain:** Documents and file systems (application layer).
- **Architecture:** Each provenance entry is `P_i = ⟨U_i, W_i, hash(D_i), C_i, public_i, I_i⟩` (FAST Section 3.1).
- **Zero-Trust depth:** Not applicable.
- **Device identity:** Principals hold signing keys, with optional certificates.
- **Workload identity:** Not reported.
- **Authorization:** Auditor read access via broadcast encryption (FAST Section 3.1.2).
- **Payload integrity:** `hash(D_i)` of the modified document in each entry.
- **Provenance:**
  - Chained-signature checksum `C_i = S_Ui(hash(U_i, W_i, hash(D_i), public_i, I_i) | C_{i-1})`.
  - Optional "spiral" checksums link to multiple earlier entries (FAST Section 3.1.3).
- **Lineage:** Property I6 prevents lineage forgery, i.e. claiming that one document's chain belongs to another (FAST Section 2).
- **Replay treatment:** Not reported.
- **Duplicate treatment:** Not reported.
- **Insertion and removal:** I1–I4 cover detection of removal or insertion by a single adversary or by colluders.
- **Event ordering:** Chains are "time-ordered".
- **Disconnected-edge recovery:** Not reported.
- **Raw preservation:** Document hashes only.
- **Threat model:** Inside or outside principals forging history, with collusion. Total removal of a chain (DoS) is out of scope (FAST Section 2).
- **Implementation:** The Sprov prototype (TOS abstract).
- **Testbed:** Not examined (journal version).
- **Baselines:** No security, per the abstract's overhead framing.
- **Metrics and results (TOS abstract, Crossref):** Runtime overhead of 1–13% when all file modifications are recorded, and 12–16% when all file reads and modifications are tracked.
- **Limitations:** Total chain removal is not addressed.

**OVERLAP:** Technique-defining for multi-principal, hash-chained signed provenance: a later principal's signature covers the predecessor's checksum. It is analogous to a device statement countersigned by a relay.

**PRECISE DIFFERENCE:**
- Document provenance, not streaming IIoT telemetry.
- No device or workload identity binding, admission policy or revocation effects.
- No delivery semantics (retry, replay, ordering).
- No ingestion pipeline.

---

### 3.8 AMAN2017 + AMAN2019 (PUF and wireless-fingerprint data provenance line)

**Bibliographic record**

- **VERIFIED CITATIONS:**
  - (a) Aman, M.N.; Chua, K.C.; Sikdar, B. Secure Data Provenance for the Internet of Things. In Proceedings of the 3rd ACM International Workshop on IoT Privacy, Trust, and Security (IoTPTS '17), Abu Dhabi, United Arab Emirates, 2 April 2017; pp. 11–14. https://doi.org/10.1145/3055245.3055255
  - (b) Aman, M.N.; Basheer, M.H.; Sikdar, B. Data Provenance for IoT With Light Weight Authentication and Privacy Preservation. *IEEE Internet of Things Journal* **2019**, *6*, 10441–10457. https://doi.org/10.1109/JIOT.2019.2939286
- **BIBTEX:**
  - (a) `@inproceedings{Aman_2017, series={ASIA CCS ’17}, title={Secure Data Provenance for the Internet of Things}, url={http://dx.doi.org/10.1145/3055245.3055255}, DOI={10.1145/3055245.3055255}, booktitle={Proceedings of the 3rd ACM International Workshop on IoT Privacy, Trust, and Security}, publisher={ACM}, author={Aman, Muhammad Naveed and Chua, Kee Chaing and Sikdar, Biplab}, year={2017}, month=Apr, pages={11–14}, collection={ASIA CCS ’17} }`
  - (b) `@article{Aman_2019, title={Data Provenance for IoT With Light Weight Authentication and Privacy Preservation}, volume={6}, ISSN={2372-2541}, url={http://dx.doi.org/10.1109/jiot.2019.2939286}, DOI={10.1109/jiot.2019.2939286}, number={6}, journal={IEEE Internet of Things Journal}, publisher={Institute of Electrical and Electronics Engineers (IEEE)}, author={Aman, Muhammad Naveed and Basheer, Mohammed Haroon and Sikdar, Biplab}, year={2019}, month=Dec, pages={10441–10457} }`
- **TYPE:** (a) workshop; (b) journal.
- **SOURCES:**
  - Crossref records for both DOIs.
  - https://www.ece.nus.edu.sg/stfpage/bsikdar/papers/asiaccs2_17.pdf
  - https://www.ece.nus.edu.sg/stfpage/bsikdar/papers/iotj_19b.pdf
- **ACCESS:** Full text of both (author copies).

**Comparison fields**

- **Research problem:** Provenance of IoT data, covering both source (which device) and location, without storing secrets on devices.
- **Domain:** IoT and wireless sensors.
- **Architecture:**
  - (a) Device to server/gateway: PUF challenge-response pairs (CRPs) and RSSI-based link fingerprints; each packet is encrypted with the current fingerprint and carries a MAC (Section 3.2).
  - (b) Adds a 6LoWPAN wireless gateway that generates link fingerprints and covers both single-hop and multi-hop cases.
- **Zero-Trust depth:** Not claimed.
- **Device identity:** The PUF. CRPs are renewed for every session in (a).
- **Workload identity:** Not reported.
- **Authorization:** The server rejects devices without a known CRP; (b) provides mutual authentication proved with BAN logic (Section VIII).
- **Payload integrity:** A MAC (symmetric key).
- **Provenance:** Device identity via the PUF and location via the link fingerprint.
- **Lineage:** Not reported.
- **Replay treatment:** In (a), replay of older sessions is prevented by a new nonce N_A per session (Section 3.3).
- **Duplicate treatment:** Not reported.
- **Event ordering:** Not reported.
- **Disconnected-edge recovery:** Not reported.
- **Raw preservation:** Not reported.
- **Gateway role:** In (b) the gateway is "considered to be secure" and the server "trusted" (assumptions c–d).
- **Threat model:**
  - (a) Physical attacks; impersonation; eavesdropping, modification, replay and injection; the attacker is at least two wavelengths away.
  - (b) The attacker fully controls the channel.
- **Implementation (b):** RSSI experiments on MICA-Z motes in an indoor lab, 1 h at one packet every 2 s, analysed offline in Matlab. Energy emulated on MICA2 with AVRORA over 100 runs (Sections IX–X).
- **Baselines (b):**
  - Correlation-based fingerprints [36] for misclassification.
  - The NI-ZKP protocol of Sanchez et al. [8] for energy.
- **Metrics and results (b):**
  - An MSE threshold of 15 separates legitimate from adversarial channels (Section IX).
  - At 256-bit keys, CPU energy is 83.8% lower and radio energy 73.5% lower than [8] (Section X, Table IV).
- **Limitations:** (a) is explicitly preliminary ("a more detailed and experimental evaluation ... is required", Section 4).

**OVERLAP:** Hardware-rooted device identity bound to each data packet; gateway involvement; nonce-based freshness.

**PRECISE DIFFERENCE:**
- Symmetric, link-bound provenance with no signatures or relay statements.
- No admission policy over device, asset and workload; no revocation.
- No duplicate or retry semantics, evidence log, raw store or lineage.

---

### 3.9 JAVAID2018 (BlockPro)

**Bibliographic record**

- **VERIFIED CITATION:** Javaid, U.; Aman, M.N.; Sikdar, B. BlockPro: Blockchain based Data Provenance and Integrity for Secure IoT Environments. In Proceedings of the 1st Workshop on Blockchain-enabled Networked Sensor Systems (BlockSys '18), Shenzhen, China, 4 November 2018; pp. 13–18. https://doi.org/10.1145/3282278.3282281
- **BIBTEX:** `@inproceedings{Javaid_2018, series={SenSys ’18}, title={BlockPro: Blockchain based Data Provenance and Integrity for Secure IoT Environments}, url={http://dx.doi.org/10.1145/3282278.3282281}, DOI={10.1145/3282278.3282281}, booktitle={Proceedings of the 1st Workshop on Blockchain-enabled Networked Sensor Systems}, publisher={ACM}, author={Javaid, Uzair and Aman, Muhammad Naveed and Sikdar, Biplab}, year={2018}, month=Nov, pages={13–18}, collection={SenSys ’18} }`
- **TYPE:** Workshop (at ACM SenSys '18).
- **SOURCES:**
  - https://api.crossref.org/works/10.1145/3282278.3282281
  - https://www.ece.nus.edu.sg/stfpage/bsikdar/papers/blocksys.pdf
- **ACCESS:** Full text (author copy).

**Comparison fields**

- **Research problem:** Data provenance and integrity for IoT against impersonation and tampering.
- **Domain:** Generic IoT.
- **Architecture:**
  - Two Ethereum smart contracts: one checks device registration and PUF CRPs (provenance), the other stores and retrieves data on chain.
  - Servers act as miners (Sections 3–4).
- **Zero-Trust depth:** Not claimed. All servers are "trusted hosts".
- **Device identity:** A PUF CRP plus an Ethereum address.
- **Workload identity:** Not reported.
- **Authorization:** A trusted list of registered devices, with register and delete functions.
- **Payload integrity:** `h(ID_A, data, R_i)` plus a MAC; immutable blockchain records.
- **Provenance:** The PUF challenge-response per transmission (Algorithm 1).
- **Lineage:** Not reported.
- **Replay treatment:** A server nonce N_1 is used in the challenge (Fig. 4). Replay is otherwise not reported.
- **Duplicate treatment:** Not reported.
- **Event ordering:** Not reported.
- **Disconnected-edge recovery:** Not reported.
- **Raw preservation:** Data are stored on chain.
- **Threat model:** Impersonation and data tampering.
- **Implementation:** Solidity in the Remix IDE; geth nodes on Ubuntu 17.04 (Section 6).
- **Testbed:** Two simulated IoT nodes and one server node.
- **Baselines:** Not reported.
- **Metrics and results:** None quantitative; the evaluation is functional.
- **Limitations:** Scalability is noted as a general blockchain concern.

**OVERLAP:** Admission gated by device identity; immutable evidence store.

**PRECISE DIFFERENCE:**
- No signatures over canonical event fields and no relay statement.
- No credential-status semantics beyond registration.
- No delivery semantics.
- No quantitative evaluation and no IIoT.

---

### 3.10 LIM2010 (seminal classic: data trustworthiness scoring)

**Bibliographic record**

- **VERIFIED CITATION:** Lim, H.-S.; Moon, Y.-S.; Bertino, E. Provenance-based Trustworthiness Assessment in Sensor Networks. In Proceedings of the Seventh International Workshop on Data Management for Sensor Networks (DMSN '10), Singapore, 13 September 2010; pp. 2–7. https://doi.org/10.1145/1858158.1858162
- **BIBTEX:** `@inproceedings{Lim_2010, series={DMSN ’10}, title={Provenance-based trustworthiness assessment in sensor networks}, url={http://dx.doi.org/10.1145/1858158.1858162}, DOI={10.1145/1858158.1858162}, booktitle={Proceedings of the Seventh International Workshop on Data Management for Sensor Networks}, publisher={ACM}, author={Lim, Hyo-Sang and Moon, Yang-Sae and Bertino, Elisa}, year={2010}, month=Sept, pages={2–7}, collection={DMSN ’10} }`
- **TYPE:** Workshop (at VLDB 2010).
- **SOURCES:**
  - https://api.crossref.org/works/10.1145/1858158.1858162
  - https://www.comp.nus.edu.sg/~vldb2010/proceedings/files/vldb_2010_workshop/DMSN_2010/individual-files/02.lim-10.pdf
- **ACCESS:** Full text.

**Comparison fields**

- **Research problem:** Quantitative trust scores for sensor data items used in SCADA or battlefield decisions.
- **Domain:** Sensor networks.
- **Architecture:**
  - A cyclic framework: trust in data items and in network nodes are interdependent.
  - Scores combine value similarity and provenance similarity (path edit distance over provenance trees) (Sections 2–3).
- **Zero-Trust depth:** Not applicable.
- **Device identity:** Not reported. Provenance paths are assumed to be given.
- **Workload identity:** Not reported.
- **Authorization:** Not reported.
- **Payload integrity:** Not reported.
- **Provenance:** Provenance trees, used as input to trust.
- **Lineage:** Not reported.
- **Replay treatment:** Not reported.
- **Duplicate treatment:** Not reported.
- **Event ordering:** Not reported.
- **Disconnected-edge recovery:** Not reported.
- **Raw preservation:** Not reported.
- **Threat model:** Injection of incorrect data items (simulated).
- **Implementation:** Java (JDK 1.6) on a 2.2 GHz Core2 Duo PC with 2 GB RAM.
- **Testbed:** A simulated f-ary complete tree with synthetic normally distributed data (Section 4.1).
- **Baselines:** Not reported.
- **Metrics and results:**
  - Elapsed time per item rises 9.7% as h goes from 5 to 6.
  - With ω = 80, the system processes 25 items/s (Fig. 5).
  - Trust scores react to injected incorrect items (Fig. 6).
- **Limitations (stated):** Application-sensitive parameters are left to future work; multi-attribute data and non-normal distributions are also future work.

**OVERLAP:** Per-item trust or admission scoring that depends on provenance.

**PRECISE DIFFERENCE:**
- Statistical, not cryptographic: no signatures, identity or policy.
- No delivery-history semantics and no evidence or raw store.

---

### 3.11 RIZZARDI2016 (AUPS)

**Bibliographic record**

- **VERIFIED CITATION:** Rizzardi, A.; Sicari, S.; Miorandi, D.; Coen-Porisini, A. AUPS: An Open Source AUthenticated Publish/Subscribe System for the Internet of Things. *Information Systems* **2016**, *62*, 29–41. https://doi.org/10.1016/j.is.2016.05.004
- **BIBTEX:** `@article{Rizzardi_2016, title={AUPS: An Open Source AUthenticated Publish/Subscribe system for the Internet of Things}, volume={62}, ISSN={0306-4379}, url={http://dx.doi.org/10.1016/j.is.2016.05.004}, DOI={10.1016/j.is.2016.05.004}, journal={Information Systems}, publisher={Elsevier BV}, author={Rizzardi, Alessandra and Sicari, Sabrina and Miorandi, Daniele and Coen-Porisini, Alberto}, year={2016}, month=Dec, pages={29–41} }`
- **TYPE:** Journal.
- **SOURCES:**
  - https://api.crossref.org/works/10.1016/j.is.2016.05.004
  - https://www.dista.uninsubria.it/~alessandra.rizzardi/documents/2016_AUPS.pdf
- **ACCESS:** Full text of the author-posted manuscript, whose pagination and content may differ from the published version.

**Comparison fields**

- **Research problem:** Adding key management and policy enforcement to MQTT.
- **Domain:** IoT middleware (NOS) with MQTT.
- **Architecture:**
  - NOS nodes host the policy enforcement and decision points (PEP/PDP).
  - An external Keys Topics Manager (KTM) issues temporary topic keys `⟨keyId, keyT, val, atb⟩`.
  - Data are encrypted before publishing (Section IV).
- **Zero-Trust depth:** Not claimed.
- **Device identity:** Registration of sources and users. Specific mechanisms are not detailed in the examined text.
- **Workload identity:** Not reported.
- **Authorization:** Topic-level ABAC.
- **Payload integrity:** Not reported as a signature; topic-key encryption is used.
- **Provenance:** Not reported.
- **Lineage:** Not reported.
- **Trust scoring:** NOS Analyzers annotate data with security and quality scores in [0, 1] (Section III).
- **Replay treatment:** Claimed as resilience ("temporary keys ... registration improves ... resilience to ... replay attacks"), not evaluated.
- **Duplicate treatment:** Not reported.
- **Event ordering:** Not reported.
- **Disconnected-edge recovery:** Not reported.
- **Raw preservation:** None. "NOS does not support persistent storage of IoT-generated data" (Section V.A).
- **Threat model:** Violation attempts. The robustness comparison with SecKit is qualitative.
- **Implementation:** Node.js, MongoDB and Mosquitto; open source on Bitbucket.
- **Testbed:** A Raspberry Pi (512 MB) with six sensors from a meteorological station, at 10 and 20 packets/s.
- **Baselines:** NOS without AUPS; SecKit (qualitative).
- **Metrics and results:**
  - Per incoming datum: database queries 2.4 ms, encryption 0.5 ms, and a 3.2 ms KTM HTTP call only when the key has expired.
  - Memory is about 7.5 MB, of which AUPS uses 8% (Section V.A).
- **Limitations (stated):** A large-scale evaluation of the KTM is needed.

**OVERLAP:** Policy-enforced authenticated pub/sub ingestion with per-item quality and security scoring.

**PRECISE DIFFERENCE:**
- Confidentiality and access control only: no per-event signatures, provenance or evidence log.
- No raw persistence and no delivery semantics.

---

### 3.12 GIGLI2025 (ZONIA)

**Bibliographic record**

- **VERIFIED CITATION:** Gigli, L.; Zyrianoff, I.; Montori, F.; Sciullo, L.; Kamienski, C.A.; Di Felice, M. ZONIA: A Zero-Trust Oracle System for Blockchain IoT Applications. *IEEE Internet of Things Journal* **2025**, *12*, 42021–42044. https://doi.org/10.1109/JIOT.2025.3591301
- **BIBTEX:** `@article{Gigli_2025, title={ZONIA: A Zero-Trust Oracle System for Blockchain IoT Applications}, volume={12}, ISSN={2372-2541}, url={http://dx.doi.org/10.1109/JIOT.2025.3591301}, DOI={10.1109/jiot.2025.3591301}, number={20}, journal={IEEE Internet of Things Journal}, publisher={Institute of Electrical and Electronics Engineers (IEEE)}, author={Gigli, Lorenzo and Zyrianoff, Ivan and Montori, Federico and Sciullo, Luca and Kamienski, Carlos A. and Di Felice, Marco}, year={2025}, month=Oct, pages={42021–42044} }`
- **TYPE:** Journal.
- **SOURCES:**
  - https://api.crossref.org/works/10.1109/JIOT.2025.3591301
  - arXiv:2410.10532v1, whose journal_ref matches the published article.
- **ACCESS:** Full text of the arXiv v1 preprint (Oct 2024). The published version may differ.

**Comparison fields**

- **Research problem:** Reliable IoT data delivered to blockchains through a decentralized oracle without trusted execution environments.
- **Domain:** IoT oracles (smart city, insurance).
- **Architecture:** Oracle and Indexer committees selected by randomness and reputation; truth inference across multiple sources; Ethereum contracts (Section II).
- **Zero-Trust depth:** "Zero-Trust Decentralized Design": anyone may join by staking, and no node is trusted (Section II).
- **Device identity:**
  - Oracles and indexers register a decentralized identifier (DID) with a public key and stake tokens (Section II.D).
  - "Producers do not require a registration process."
- **Workload identity:** Oracles and indexers have DIDs, but these are not bound to data items.
- **Authorization:** Staking plus reputation-weighted selection.
- **Payload integrity:** Not reported for producer data.
- **Provenance:** Not reported.
- **Lineage:** Not reported.
- **Replay treatment:** Not reported.
- **Duplicate treatment:** Not reported.
- **Event ordering:** Not reported.
- **Disconnected-edge recovery:** Not reported.
- **Raw preservation:** Not reported. Request resolution is "bounded by the relay blockchain transaction throughput" (Section IV), so results pass through blockchain transactions; this is the basis of the partial C10 entry.
- **Trust scoring:** A reputation system plus truth inference.
- **Threat model:** Data falsification and collusion by malicious nodes.
- **Implementation and testbed:** Geth-based Ethereum; 10-minute experiments with emulated location-based network delays (Section IV.A).
- **Baselines:** Parameter and method variants for truth inference.
- **Metrics and results:**
  - End-to-end resolution time ranges from 9 s at low workload to 15 s at high workload (Section IV).
  - High reliability is maintained even with 40% malicious nodes (Abstract).
- **Limitations (stated):** The testbed limited the parameter ranges that could be evaluated (Section IV.A).

**OVERLAP:** Explicitly "zero-trust" ingestion of IoT data, with per-request trust or admission via reputation.

**PRECISE DIFFERENCE:**
- Trust comes from redundancy across unidentified producers, not from per-object provenance.
- No device signatures, relay statements, revocation, delivery semantics or raw-plus-lineage store.

---

### 3.13 JAMES2025 (MQTT-ZT Secure Broker; Zero-Trust access-control comparator)

**Bibliographic record**

- **VERIFIED CITATION:** James, M.; Newe, T.; O'Shea, D.; O'Mahony, G.D. A Novel MQTT-ZT Secure Broker: Zero Trust Architecture for IoT Security. In Proceedings of the 2025 IEEE International Conference on Cyber Security and Resilience (CSR), Chania, Crete, Greece, 4–6 August 2025; pp. 433–439. https://doi.org/10.1109/CSR64739.2025.11130016
- **BIBTEX:** `@inproceedings{James_2025, title={A Novel MQTT-ZT Secure Broker: Zero Trust Architecture for IoT Security}, url={http://dx.doi.org/10.1109/CSR64739.2025.11130016}, DOI={10.1109/csr64739.2025.11130016}, booktitle={2025 IEEE International Conference on Cyber Security and Resilience (CSR)}, publisher={IEEE}, author={James, Meha and Newe, Thomas and O’Shea, Donna and O’Mahony, George D.}, year={2025}, month=Aug, pages={433–439} }`
- **TYPE:** Conference.
- **SOURCES:**
  - https://api.crossref.org/works/10.1109/CSR64739.2025.11130016
  - https://pure.ul.ie/en/publications/a-novel-mqtt-zt-secure-broker-zero-trust-architecture-for-iot-sec/
- **ACCESS:** Abstract only.

**Comparison fields (from the abstract)**

- **Research problem:** Role-based access control does not scale or enforce policy in real time in dynamic IoT.
- **Architecture:** An MQTT broker with an embedded Policy Enforcement Point and Axiomatics' ALFA policy engine, providing attribute-based access control under a Zero Trust architecture.
- **Zero-Trust depth:** "Continuously verifying access" at the broker.
- **Testbed:** A cyber range.
- **Metrics and results:**
  - Processing time is 20–79 ms for publishers and 24–63 ms for subscribers, with up to 200 clients.
  - "Traditional methods often exceeded 100 ms."
- **All other fields:** Not examined (abstract only).

**OVERLAP:** Represents the "Zero-Trust access-controlled pipeline" comparator: per-request ABAC at the broker.

**PRECISE DIFFERENCE (abstract-level):** Access decisions are made per client and connection. Data-object provenance, payload signatures, delivery semantics and evidence storage are not mentioned in the abstract.

---

### 3.14 SUKUMARAN2026 (lineage from ML artifacts to raw IoT data)

**Bibliographic record**

- **VERIFIED CITATION:** Sukumaran, S.; Korath, A.; Menon, G.A. Tamper-Evident Data and Model Provenance for IoT-Based Machine Learning Using Blockchain and Off-Chain Storage. *Information* **2026**, *17*, 499. https://doi.org/10.3390/info17050499
- **BIBTEX:** `@article{Sukumaran_2026, title={Tamper-Evident Data and Model Provenance for IoT-Based Machine Learning Using Blockchain and Off-Chain Storage}, volume={17}, ISSN={2078-2489}, url={http://dx.doi.org/10.3390/info17050499}, DOI={10.3390/info17050499}, number={5}, journal={Information}, publisher={MDPI AG}, author={Sukumaran, Sangheethaa and Korath, Arun and Menon, Gowri Arun}, year={2026}, month=May, pages={499} }`
- **TYPE:** Journal.
- **SOURCES:**
  - https://api.crossref.org/works/10.3390/info17050499
  - https://www.mdpi.com/2078-2489/17/5/499
- **ACCESS:** Full text (HTML, about 93% read). Table 4 contents were not visible.

**Comparison fields**

- **Research problem:** End-to-end provenance across the IoT machine-learning lifecycle: data, preprocessing and models.
- **Domain:** IoT-based machine learning.
- **Architecture:**
  - Devices, edge/gateway (filtering, aggregation, features), an off-chain store that is "available but not trusted", the ML engine, a permissioned blockchain, and an audit module (Section 3.1).
  - The experiment used a Hardhat local chain and local disk.
- **Zero-Trust depth:** Not claimed.
- **Device identity:** Device IDs appear in records. Signatures and key management are not described.
- **Workload identity:** Not reported.
- **Authorization:** Not reported.
- **Payload integrity:** SHA-256 hashes of batches, preprocessing outputs and models; which party computes them is not stated.
- **Provenance and lineage:**
  - Preprocessing records hold input and output hashes and a parameter hash.
  - Model records hold hashes of the training feature sets and of the configuration and metrics (Sections 4.4–4.6).
  - Broken links appear as "dangling provenance links".
  - No traversal algorithm or taint propagation is described.
- **Replay treatment:** Mentioned as a threat in Section 1.1 but not modelled.
- **Duplicate treatment:** Not reported.
- **Event ordering:** Not reported.
- **Disconnected-edge recovery:** Not reported; network effects were not modelled.
- **Raw preservation:** Raw data are kept off chain, with hashes on chain.
- **Threat model:**
  - Integrity attacks only.
  - Out of scope: DoS, side channels, node key compromise, adversarial ML (Sections 3.5, 8).
- **Implementation and testbed:** Python 3.12; synthetic sensor data inspired by TON_IoT.
- **Baselines:** Training with and without provenance verification.
- **Metrics and results:**
  - All injected violations were detected with no false positives (Section 6.1).
  - Verification latency is 22.96–31.33 ms (Section 6.4).
  - No noticeable change in model accuracy or F-score.
- **Limitations (stated):** Simulation only. Preprocessing tampering was not evaluated empirically (Section 6.5).

**OVERLAP:** Lineage from derived analytics back to raw IoT batches, with off-chain raw storage and on-chain evidence.

**PRECISE DIFFERENCE:**
- No signatures or identity, so tamper evidence is hash-only.
- No admission policy, no delivery semantics, and no revocation-driven taint propagation.

---

### 3.15 MATIAS2026 (IIoT edge store-and-forward resilience)

**Bibliographic record**

- **VERIFIED CITATION:** Matias, J.A.; Macêdo, R.J.d.A. Resilient IIoT Communication via Edge-Based Store-and-Forward and SLO Monitoring. In Anais do XXVII Workshop de Testes e Tolerância a Falhas (WTF 2026), Praia do Forte, BA, Brazil, 2026; pp. 242–246. https://doi.org/10.5753/wtf.2026.24074
- **BIBTEX:** `@inproceedings{Matias_2026, series={WTF 2026}, title={Resilient IIoT Communication via Edge-Based Store-and-Forward and SLO Monitoring}, url={http://dx.doi.org/10.5753/wtf.2026.24074}, DOI={10.5753/wtf.2026.24074}, booktitle={Anais do XXVII Workshop de Testes e Tolerância a Falhas (WTF 2026)}, publisher={Sociedade Brasileira de Computação - SBC}, author={Matias, José António and Macêdo, Raimundo José de Araújo}, year={2026}, month=May, pages={242–246}, collection={WTF 2026} }`
- **TYPE:** Workshop (short, work in progress).
- **SOURCES:**
  - https://api.crossref.org/works/10.5753/wtf.2026.24074
  - https://sol.sbc.org.br/index.php/wtf/article/view/42263, which gives the location and the 25 May 2026 publication date.
  - PDF https://sol.sbc.org.br/index.php/wtf/article/download/42263/42030/ (read via WebFetch).
- **ACCESS:** Full text.

**Comparison fields**

- **Research problem:** Making IIoT communication resilient to unstable wide-area links.
- **Domain:** IIoT, with an OPC UA–MQTT edge gateway.
- **Architecture:**
  - OT, edge and cloud layers.
  - A Java/Docker gateway with an in-memory FIFO buffer (MAX_BUFFER_SIZE), file-based persistence and RabbitMQ.
  - On reconnection, buffered messages are sent first, in batches (Sections 3.1–3.3).
- **Zero-Trust depth:** Not reported.
- **Device identity:** Not reported.
- **Workload identity:** Not reported.
- **Authorization:** Not reported.
- **Payload integrity:** Not reported. TLS, authentication, signatures and integrity mechanisms are not described.
- **Provenance:** Not reported.
- **Lineage:** Not reported.
- **Replay treatment:** Not reported.
- **Duplicate treatment:** Deduplication of resent messages is not addressed.
- **Event ordering:** No explicit guarantee is stated; FIFO buffering implies oldest first.
- **Disconnected-edge recovery:** Store-and-forward with persistence. When the buffer is full while disconnected, messages are dropped (messages 21–22 in the test).
- **Raw preservation:** Not reported.
- **Threat model:** None; faults are WAN outages.
- **Implementation and testbed:**
  - iFogSim2 with up to 200 sensors (20,000 msg/s).
  - A lab prototype with injected WAN failures, a 35-message cycle and a 10-message buffer (Section 3.4).
- **Baselines:** Cloud-only and a no-buffer configuration.
- **Metrics and results:**
  - Edge latency 3.77 ms versus cloud 23.21 ms at low load; edge P95 5 ms; cloud 961.97 ms under stress, against a 150 ms SLO.
  - 94.3% delivery reliability; 16 messages lost without the buffer versus 2 with it; 83.3% of downtime messages recovered (Section 3.4).
- **Limitations (stated):** Preliminary results; a single gateway is a single point of failure; higher data rates reduce resilience.

**OVERLAP:** IIoT disconnection and backlog recovery evaluated with fault injection.

**PRECISE DIFFERENCE:** No security of any kind, and no deduplication or replay-versus-retry handling of recovered backlog. It shows that resilience is evaluated separately from authenticity.

---

## 4. Supporting technique anchors and screened works (verified, not ranked)

| Key | Verified citation (DOI or URL) | Access | Relevance and note |
|---|---|---|---|
| YANG2018 | Yang, X.; Karampatzakis, E.; Doerr, C.; Kuipers, F. Security Vulnerabilities in LoRaWAN. In Proceedings of the 2018 IEEE/ACM Third International Conference on Internet-of-Things Design and Implementation (IoTDI), Orlando, FL, USA, 17–20 April 2018; pp. 129–140. https://doi.org/10.1109/IoTDI.2018.00022 | Full text (https://pure.tudelft.nl/ws/files/46032668/IoTDI2018.pdf, via WebFetch) | Primary experimental anchor for the boot-epoch component. After a reset, an ABP device "will reuse the frame counter value from 0 with the same keys", so old higher-counter frames can be replayed. A single replayed packet caused "an outage for 5 1/2 minutes" (Section IV.A). Not a pipeline study. |
| WANG2021 + KIP-98 | Wang, G.; Chen, L.; Dikshit, A.; Gustafson, J.; Chen, B.; Sax, M.J.; Roesler, J.; Blee-Goldman, S.; Cadonna, B.; Mehta, A.; Madan, V.; Rao, J. Consistency and Completeness: Rethinking Distributed Stream Processing in Apache Kafka. In Proceedings of the 2021 International Conference on Management of Data (SIGMOD '21), Virtual Event, China, 2021; pp. 2602–2613. https://doi.org/10.1145/3448016.3457556. Grey literature: Apache Kafka KIP-98, https://cwiki.apache.org/confluence/display/KAFKA/KIP-98+-+Exactly+Once+Delivery+and+Transactional+Messaging | SIGMOD paper: metadata plus the companion Confluent blog only. KIP-98: full page. | Technique anchor for (producer identity, epoch, sequence) idempotence, close to the mechanism's (device id, boot epoch, sequence) identity. In KIP-98, every producer gets a unique PID; sequence numbers increase monotonically; "lower sequence number result in a duplicate error"; a higher one gives "an out-of-sequence error"; an epoch bump fences "any previous zombie instance". There is no cryptographic binding, provenance or replay-versus-retry security semantics; duplicates are treated as benign. Cite the SIGMOD paper only for idempotent and transactional appends and revision-based ordering, which is all the examined blog text supports. |
| FARAJ2025 (secondary) | Faraj, O.; Megias, D.; Garcia-Alfaro, J. Security Approaches for Data Provenance in the Internet of Things: A Systematic Literature Review. *ACM Computing Surveys* **2025**, *57*, 1–41. https://doi.org/10.1145/3718735 | Full text of arXiv:2407.03466v2 | Secondary evidence for D and E. Section 5 (and Table 16) finds that "the majority of the reviewed papers do not consider most types of attacks. While most papers address forgery and modification attacks ... they tend to overlook other significant attack vectors such as replay attacks, packet drop, and provenance chain tampering." |
| LIANG2017 (ProvChain) | Liang, X.; Shetty, S.; Tosh, D.; Kamhoua, C.; Kwiat, K.; Njilla, L. ProvChain: A Blockchain-Based Data Provenance Architecture in Cloud Environment with Enhanced Privacy and Availability. In Proceedings of the 2017 17th IEEE/ACM International Symposium on Cluster, Cloud and Grid Computing (CCGRID), Madrid, Spain, 14–17 May 2017; pp. 468–477. https://doi.org/10.1109/CCGRID.2017.8 | Metadata only (Crossref; FIU Discovery). Neither IEEE Xplore nor an abstract source was reachable. | Named in the brief. Cloud (file) provenance anchored on a blockchain. The only content seen, on a project page (ww2.odu.edu/~sshetty/blockchain.html), mentions an ownCloud prototype and a "blockchain receipt". No comparison fields can be given. |
| BU2021 | Bu, T.; Li, X.; Huang, J.; Sun, Z. Research on Security Protection of OPC UA PubSub Protocol. *Journal of Physics: Conference Series* **2021**, *1738*, 012119. https://doi.org/10.1088/1742-6596/1738/1/012119 (Crossref lists the family name in lowercase as "bu") | Full text (open access, IOP) | OPC UA PubSub threat reconciliation. Replay is countered by PublisherId/DataSetId plus timestamp, network message number and sequence number; "Disabling timestamps, network message Numbers, and serial Numbers will allow replay attacks" (Section 2). Proposes an OSG security gateway. Design only; no quantitative evaluation found. |
| COLOMBO2024 | Colombo, P.; Ferrari, E. Access Control Integration in Sparkplug-Based Industrial Internet of Things Systems: Requirements and Open Challenges. In Proceedings of the 20th International Conference on Web Information Systems and Technologies (WEBIST), Porto, Portugal, 17–19 November 2024; pp. 380–384. https://doi.org/10.5220/0013055700003825 | Abstract only (SciTePress page) | The only peer-reviewed Sparkplug security item found. A position paper: Sparkplug's "basic data protection features" may hinder adoption, and access-control requirements are listed. No implementation. |
| PALYVOS2019 (GeneaLog) | Palyvos-Giannas, D.; Gulisano, V.; Papatriantafilou, M. GeneaLog: Fine-Grained Data Streaming Provenance in Cyber-Physical Systems. *Parallel Computing* **2019**, *89*, 102552. https://doi.org/10.1016/j.parco.2019.102552 | Abstract only (Chalmers research portal) | Lineage from detected events to source tuples in stream processing (Flink, Liebre), with constant per-tuple overhead. No tamper evidence or security, per the abstract. |
| TUNSTAD2019 (HyperProv) | Tunstad, P.; Khan, A.M.; Ha, P.H. HyperProv: Decentralized Resilient Data Provenance at the Edge with Blockchains. In Proceedings of the 20th International Middleware Conference Demos and Posters (Middleware '19), Davis, CA, USA, 9 December 2019; pp. 3–4. https://doi.org/10.1145/3366627.3368105 | Abstract only (arXiv:1910.05779) | Hyperledger Fabric provenance and lineage queries at the edge, on Raspberry Pi; 2-page demo. No delivery semantics in the abstract. |
| YAGIZ2026 (preprint) | Yagiz, M.A.; Horasan, F.; Yurttakal, A.H. Lightweight Tamper-Evident Log Integrity Verification for IoT Edge Environments: A Merkle Tree Pipeline with Adaptive Chunking. arXiv 2026, arXiv:2605.00065. BibTeX (arXiv): `@misc{yagiz2026lightweighttamperevidentlogintegrity, title={Lightweight Tamper-Evident Log Integrity Verification for IoT Edge Environments: A Merkle Tree Pipeline with Adaptive Chunking}, author={Muhammet Anil Yagiz and Fahrettin Horasan and Ahmet Hasim Yurttakal}, year={2026}, eprint={2605.00065}, archivePrefix={arXiv}, primaryClass={cs.CR}, url={https://arxiv.org/abs/2605.00065}}` | Abstract only. Not peer reviewed ("submitted to Computers and Security"). | Merkle evidence for IoT edge logs: more than 130,000 logs/s at 100,000 records and about 22 ms verification. Integrity only; no identity or delivery semantics. |
| Identified, not examined | Sigwart et al., Blockchain-based Data Provenance for the Internet of Things (IoT '19), https://doi.org/10.1145/3365871.3365886. Jaigirdar et al., Security-Aware Provenance for Transparency in IoT Data Propagation, *IEEE Access* 2023, https://doi.org/10.1109/ACCESS.2023.3280928. Faraj et al., ZIRCON (arXiv:2305.00266, abstract only). | Crossref metadata; arXiv abstracts | Provenance frameworks found too late in the task to examine. Read Jaigirdar et al. in particular, because it records the security controls applied along the propagation path. |

---

## 5. Search log and gaps

- **Crossref `query.bibliographic` queries** (each run with backoff):
  - Aman/Chua/Sikdar; BlockPro; ProvChain; Hasan/Sion/Winslett; AUPS.
  - MQTT payload signature and integrity; Sparkplug B security; OPC UA PubSub security (three variants).
  - Data-centric zero trust; zero-trust data provenance IoT; zero-trust data pipeline; zero-trust IIoT lineage; zero-trust edge-cloud IIoT integrity.
  - Trustworthy ingestion; OSCORE performance; provenance-based trustworthiness.
  - Kafka exactly-once; LoRaWAN vulnerabilities; blockchain provenance (LineageChain, HyperProv, Sigwart); security-aware provenance; WedgeChain.
- **arXiv API queries:**
  - `abs:"zero trust" AND abs:provenance` (no IoT-data primary work found).
  - `"zero trust" AND "data pipeline"` (none).
  - `provenance AND replay AND IoT` (none).
  - `"zero trust" AND (IIoT OR "industrial internet")`; `"zero trust" AND MQTT` (only federated-learning and segmentation papers).
- **Web searches** covered all seven problem areas, plus SPIFFE and IoT provenance, store-and-forward with provenance, exactly-once IoT ingestion, transparency logs for IoT, and gateway signing for legacy devices.
- **Gaps observed:**
  - (i) No peer-reviewed experimental evaluation of OPC UA PubSub message security (signing, sequence numbers, replay) was found; only a design paper (BU2021) and the qualitative assessment in ENTRUST.
  - (ii) No peer-reviewed work binding a SPIFFE-like *workload* identity into IoT data provenance or relay statements was found.
  - (iii) "Data-centric" or "data-object" Zero Trust appears in book chapters, preprints and reports (e.g., an OGC Testbed-21 report and TechRxiv preprints found via Crossref). No peer-reviewed primary implementation for IoT data objects was found.
  - (iv) No examined work implements taint propagation from a retroactively revoked credential to derived data.
- **Coverage caveat:** dblp, OpenAlex and Semantic Scholar were unavailable, and IEEE Xplore and ACM DL full texts could not be fetched. The absence statements above refer to what these searches surfaced.

---

## 6. Assessment of claims D and E

**(D) "Data-object trust continuity across identity, authorized ingestion, integrity, provenance and deterministic resilient processing is insufficiently integrated in the closest examined literature."**

**Verdict: SUPPORTED** for the 15 examined works and the screened set. No examined paper contradicts it, but several integrate two or three of the five facets, and the manuscript should acknowledge them.

- **Identity + authorization + integrity + provenance, without resilient processing:**
  - TSAI2026 is the strongest partial integration: registered endpoint keys, policy-gated commitments, revocation history and content-addressed bundles. It has no duplicate, replay, ordering or disconnection handling.
  - Also in this group: AMAN2019 and JAVAID2018 (hardware identity plus provenance, with no delivery semantics), and HASAN2009 (chained signatures).
- **Integrity + ordering/duplicates, with weak identity and no authorization or provenance chain:**
  - BUCCAFURRI2024 (MQTT-I).
  - LAZZARO2024, which also discards raw messages.
  - DAHLMANNS2021, which has ACL authorization but only a symmetric MAC.
- **Untrusted edge + evidence + replay discussion:** NAWAB2021 has no authorization, revocation or lineage, and its replay handling is discussion only.
- **Zero Trust:**
  - JAMES2025 is access control at the broker (abstract).
  - GIGLI2025 has unregistered producers and redundancy-based trust.
- **Lineage:** SUKUMARAN2026 is hash-only and has no taint.
- **Secondary support:** FARAJ2025 reports that IoT provenance studies mostly overlook replay, packet drop and chain tampering.
- **Wording caution:** "Insufficiently integrated" is an evaluative phrase. A defensible formulation is: "none of the examined works combines identity-bound, policy-admitted per-event provenance with deterministic delivery-history classification and lineage".

**(E) "Security and distributed event-correctness behaviour (duplicates, replay vs retry, reordering, disconnection recovery) are rarely evaluated together in a reproducible IIoT pipeline."**

**Verdict: SUPPORTED.** None of the examined works reports such a joint evaluation in an IIoT pipeline.

- **Mechanisms present but evaluation covers overhead only:** BUCCAFURRI2024 (formal analysis of deletion, reordering and delay, with throughput and energy experiments on generic MQTT) and DAHLMANNS2021 (counter-based duplicate and drop detection).
- **Replay discussed but not evaluated:** NAWAB2021.
- **Security-related loss tolerance in simulation only:** SAITO2025 evaluates verifiability under random loss.
- **Resilience without security:** MATIAS2026 evaluates IIoT disconnection recovery with fault injection but has no security and no deduplication.
- **Replay without pipeline semantics:** YANG2018 evaluates replay after a counter reset experimentally.
- **Reproducibility artifacts:**
  - Found only for SAITO2025 (GitHub prototype) and RIZZARDI2016 (Bitbucket).
  - TSAI2026 mentions a "public artifact" without a URL in the examined text.
  - No artifact link was found for MQTT-I, ENTRUST or WedgeChain.
- **Contradiction:** No paper contradicts E. The works a reviewer is most likely to raise as counter-examples are MQTT-I (integrity plus ordering plus duplicates by design) and ENTRUST (industrial end-to-end security plus duplicate and drop detection). Both treat these properties by design or proof, not through a joint fault- and attack-injection evaluation, and neither covers replay versus legitimate retry or disconnection backlog.
- **Recommended wording:** "We found no study that jointly evaluates ..." is more defensible than "rarely".
