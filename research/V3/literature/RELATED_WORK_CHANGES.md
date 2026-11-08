# Proposed edits to Related Work (main.tex §2), Table 1 and related sentences

3 November 2026. These are proposals only; main.tex was not edited. Line numbers refer to `01_repo_v3/paper/main.tex` as read on 3 Nov 2026. Each item gives the location, what to change, proposed wording, and the supporting source (details and quotes in `V3_LITERATURE_AUDIT.md`). New bib keys are in `suggested_bib_V3.bib`.

Priority: **[Correct]** = current text is inaccurate; **[Refine]** = accurate but imprecise or incomplete; **[Add]** = missing work.

## Corrections

**R3 [Correct] SCITT sentence (l.76).**
- Current: "...into an RFC~9162 log with receipts and auditor-reproducible registration decisions~\cite{rfc9943}; it leaves delivery history, revocation and derived-data consequences out of scope."
- Proposed: "The IETF SCITT architecture standardizes the registration of signed statements under a registration policy that is itself registered and applied as of registration time, into an append-only verifiable data structure (for example an RFC~9162 Merkle tree) with receipts, and requires that auditors can reproduce each registration check~\cite{rfc9943,rfc9942}; it defines no per-event delivery-history semantics (statements about the same subject supersede each other), leaves client authentication and revocation strategies for compromised keys out of scope, and does not address derived data."
- Source: RFC 9943 §4, §5.1.3 (VDS-agnostic; "Specific VDSs ... are out of scope"); §5.1.1.1-5.1.1.2; §6.3 step 1; §9.2; §9.4.2. RFC 9942 (RFC9162_SHA256 VDS, receipts).

**R4 [Correct] ACE described as the relay analogue (l.74; Table 1 l.91).**
- Current: "...countersigns published objects end to end through an untrusted broker with COSE countersignatures and per-publisher replay windows~\cite{...}, the closest analogue of the relay statement; ..."
- Proposed: "In the IETF ACE \pubsub\ profile for CoAP, an Internet-Draft in Working Group Last Call, each publisher countersigns its own group-encrypted object, so that subscribers authenticate the source end to end through a broker that is not trusted with the data, and subscribers keep a replay window per publisher~\cite{ietf_ace_coap_pubsub,rfc9338}; a second object with an already-received sequence number is discarded, so equivocation is not surfaced."
- Remove "the closest analogue of the relay statement". The ACE countersigner is the origin, so there is no relaying party; see R5 for the relay analogue.
- Table 1 row 2 (relay statement), "Closest prior art": "second-party COSE countersignatures~\cite{rfc9338}; publisher-signed objects through an untrusted broker~\cite{ietf_ace_coap_pubsub}; workload identity~\cite{spiffe_spec}".
- Source: draft-ietf-ace-coap-pubsub-profile-05 §1 ("Publisher signing such content with its own private key"), §6.1, §6.3, Security Considerations ("Broker is not trusted with the published topic data"); Datatracker history (WGLC since 8 Jan 2026).

**R5 [Correct/Refine] State what a countersignature binds (new clause in l.74 or l.76).**
- Proposed: "An RFC~9338 countersignature is a second signer's signature over the target's protected header, payload and, for a signed object, its signature value~\cite{rfc9338}; the relay statement binds the same material through $H(\mathrm{JCS}(\Sobs)\,\|\,\sigma_o)$ and adds the workload identity and path authorization that RFC~9338 leaves to the application."
- Source: RFC 9338 §3.3 (Countersign_structure; other_fields = the COSE_Sign1 signature); §3 ("makes a statement about the existence of a signature"); §3.3 (identity and authorization checks are the application's).

**R11 [Correct] B4 description (l.195).**
- Current: "idempotent admission keyed by the producer-assigned event identity as in Kafka's idempotent producer~\cite{kip98} (exact duplicates suppressed; a conflicting version of an admitted identity rejected, first writer wins)".
- Proposed: "idempotent admission keyed by the producer-assigned event identity, as CloudEvents consumers key on (source, id) and Kafka on (producer, epoch, sequence)~\cite{cloudevents102,kip98} (exact duplicates suppressed; a conflicting version of an admitted identity rejected, first writer wins); unlike Kafka's broker, which accepts only the next expected sequence number, B4 accepts gaps and reordering".
- Apply the same wording to B5 in V3.
- Source: KIP-98 "Idempotent Producer Guarantees" ("reject a produce request if its sequence number is not exactly one greater ... lower ... duplicate error ... higher ... out-of-sequence error ... fatal"); CloudEvents 1.0.2 `id` attribute.

## Refinements

**R1 [Refine] Introduction l.57.**
- Current: "signed logs turn forks into evidence~\cite{tarr2019ssb,haeberlen2007peerreview}".
- Proposed: "signed hash-linked logs make forks detectable~\cite{tarr2019ssb} and turn them into verifiable evidence~\cite{haeberlen2007peerreview}".
- Source: SSB ICN'19 §2 (fork rule) and footnote 4 ("how nodes should react to forked feeds ... We leave this open for future work"); PeerReview §4 ("verifiable evidence that j is faulty").

**R2 [Refine] Zero-Trust paragraph (l.72).**
- (a) "...policy decision and enforcement points that make per-request access decisions~\cite{nist_sp800_207}". 800-207's tenet 3 says access is *granted* per session, so "decisions" is the defensible word.
- (b) "...and its guidance for cloud-native applications authenticates services per connection, because per-request authentication is 'highly disruptive'~\cite{nist_sp800_207a}".
- (c) Replace "These works operate at the session, connection or flow level" with "These works decide at the point of access (per session, connection, request or flow)". rodigari2021ztmc authorizes "every request" (abstract), and james2025mqttzt's granularity is not determinable from its abstract.
- Optional: cite 800-207 tenet 2 ("provide source authentication") as the principle PBTI extends to data objects.
- Sources: SP 800-207 §2 (definition) and §2.1 (tenets 2-3); SP 800-207A ID-SEG-REC-2 note; Rodigari et al. abstract (arXiv v1); James et al. abstract.

**R6 [Refine] SSB, GDP and the Table 1 Rule-L row.**
- l.76 SSB: keep the sentence, but either cite the protocol guide for the canonical form ("...Ed25519 over canonical JSON~\cite{tarr2019ssb,ssb_protocol_guide}") or drop "canonical JSON". The ICN paper states the fields and ed25519 identities but not canonical JSON.
- l.76 GDP: "...names holes and branches in signed edge-data streams and accepts branches as a partial order of records~\cite{mor2019gdp,mor2019thesis}".
- Table 1 row 4, "Closest prior art": "fork detection~\cite{tarr2019ssb} and evidence~\cite{haeberlen2007peerreview}; holes and branches~\cite{mor2019gdp}; first-writer-wins de-duplication and replay windows~\cite{kip98,cloudevents102,ietf_ace_coap_pubsub}; convergent state~\cite{shapiro2011crdt}".
- Optional, for (C2) l.68: "unlike first-writer-wins de-duplication, whole-feed invalidation after a fork, or acceptance of branches as a partial order".
- Source: SSB Protocol Guide ("serialized according to a specific canonical JSON format"); GDP accepted manuscript §V ("Such branches result in a partial order of records ... strong eventual consistency"); dissertation §3.4.2.

**R7 [Refine] Kafka sentence (l.78).**
- Proposed: "Kafka's idempotent producer de-duplicates retries by producer identifier, epoch and per-partition sequence number within one producer session, and requires acknowledgement by all in-sync replicas and at most five in-flight requests~\cite{kip98,kafka44_producerconfigs,wang2021kafka}; CloudEvents consumers may treat events with the same source and identifier as duplicates~\cite{cloudevents102}; both make a conflicting second version indistinguishable from a retry."
- Source: KIP-98 ("we can only guarantee idempotent production within a single producer session"); Kafka 4.4 `enable.idempotence` ("requires max.in.flight.requests.per.connection to be less than or equal to 5 ..., retries to be greater than 0, and acks must be 'all'").

**R8 [Refine/Add] Intrusion recovery (l.76; Table 1 row 5).**
- Proposed: "Intrusion-recovery systems revert tainted operations and repair dependent state along dependency graphs, starting from detection points supplied by an intrusion detector or administrator, or from a patch~\cite{goel2005taser,kim2010retro,chandra2011warp,ammann2002recovery}; we found none that triggers such repair from credential revocation with a compromise time in IIoT data pipelines."
- Add `kim2010retro` to Table 1 row 5.
- Source: Taser §2.3.2 (detection points "provided by an intrusion detection system (IDS) or an administrator"); Retro (assumes detection tools "pinpoint attack edges"); Warp abstract ("When an administrator learns of a security vulnerability"); Ammann et al. abstract.

**R10 [Refine] Sigwart et al. (l.76).**
- Current: "Sigwart et al. leave open how only correct records enter a provenance system".
- Proposed: "Sigwart et al. restrict record creation to token holders and leave the correctness of records at entry to future work~\cite{sigwart2019bcprov}".
- Source: arXiv v2 ("As a first step, we implement the concept of ownership of data points using tokens ... In future work, this concept could be further extended by mechanisms that guarantee the correctness of the records themselves"). The VoR was not accessed.

**R12 [Refine] Standards alignment (l.305) and Supplementary Table S13.**
- l.305: change "realizes NIST SP~800-207 decision and enforcement points for data objects" to "applies the NIST SP~800-207 decision/enforcement pattern to data objects".
- S13, NISTIR 8259A row: "boot epoch" is not part of 8259A's Device Identification (unique logical and physical identifiers). Mark it as a PBTI extension or drop it. Optionally use 8259A's own mapping to IEC 62443-4-2 (Device Identification → CR 1.2; Data Protection → CR 3.1, 3.4, 4.1-4.3; Cybersecurity State Awareness → CR 2.8, 3.9, 6.1) instead of naming SR/CR content from the unread IEC text.
- Optional new sentence motivating gateway attestation: "OT guidance notes that PLCs and controllers may not support Zero-Trust protocols and recommends applying them at higher architectural levels~\cite{nist_sp800_82r3}". Source: SP 800-82r3 §5.2.3.4 OT-specific guidance.
- Optional: "a fourth revision, released as an initial public draft in September 2026, adds IIoT and cloud convergence and zero-trust principles~\cite{nist_sp800_82r4ipd}". Cite as a draft only.

**R13 [Refine] NiFi (l.76; bib).**
- Keep the sentence (supported). Update `nifi_userguide` to the 2.x guide (current release 2.12.0), or label the entry 1.x explicitly.
- Optional contrast: "...without cryptographic binding of producers or tamper evidence against administrators", marked as our reading of the documentation.

## Additions

**R9 [Add] Recent work (2023-2026), cautiously and at abstract level.**
- ¶2, beside ENTRUST and MQTT-I: "SMQTT adds key-server-managed, group-key end-to-end authenticity and replay protection to MQTT without broker changes~\cite{yousaf2026smqtt}".
- ¶1 or ¶3: "device credentials have been split into a technical X.509 credential and an operational verifiable credential with separate revocation paths, both bound to the session identity~\cite{lazzaro2026vciot}". This paper is in *Future Internet*, the target journal.
- ¶3, beside tamper-evident logs: "hash-chained audit trails with signed checkpoints have been proposed for zero-trust sensor-cloud repositories~\cite{wang2026apex}", and "IoT provenance graphs have been annotated with security metadata such as signature-verification results~\cite{jaigirdar2023secprov}".
- Optional: `oskouei2025bimqtt` (a two-page paper on ring-signature origin authentication on MQTT).
- Do **not** cite `faraj2024zircon` or `yuan2026iiotaudit` for content until they have been read (metadata only).

**R14 [Add] Sparkplug details (l.74).**
- Proposed: "Sparkplug, the MQTT specification for IIoT standardized as ISO/IEC~20237~\cite{iso20237}, numbers each edge node's messages with an 8-bit sequence that wraps after 255 and each MQTT session with a birth/death sequence that also wraps; host applications that see a gap beyond a reorder timeout request a rebirth, and security is covered only by non-normative guidance on TLS, credentials and broker access control~\cite{sparkplug3}."
- Source: Sparkplug 3.0.0 NBIRTH/NDEATH rules ("between 0 and 255 ... wraps back to zero"; bdSeq "If ... 255 was sent ... MUST have a value of 0"); §5.9; §1.7; Chapter 7 ("provided for guidance only and is non-normative").

**R15 [Add, optional] Positioning sentence for l.80.**
- Proposed: "Because SCITT registration policies may depend on the service's current state~\cite{rfc9943}, \sys\ can be read as a telemetry-specific registration profile: per-event conflict semantics, relay binding and revocation-driven taint on top of policy-gated registration and auditable decisions."
- Source: RFC 9943 §6.3 step 3 ("evaluated given the current TS state").

## Bookkeeping for REFERENCE_VERIFICATION.md (authors to apply)

- `mor2019gdp`: "abstract only" → "accepted manuscript (NSF PAR 10111285) read; VoR not accessed".
- `goel2005taser`, `chandra2011warp`: "abstract only" or "abstract and introduction" → "full text of a non-publisher copy carrying the ACM notice".
- `kovach2024sovereign`: Crossref gives the event as eSAAM 2024, Mainz, Germany, published 2024-10-22; content remains abstract-level.
- `ietf_ace_coap_pubsub`: add "In WG Last Call since 8 Jan 2026; no newer revision as of 3 Nov 2026".
- New keys: rfc9942, kim2010retro, ssb_protocol_guide, kafka44_producerconfigs, nist_sp800_82r4ipd, and any recent works adopted.
