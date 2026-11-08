# V3 literature audit: close works and standards for PBTI

Prepared 3 November 2026 (all URLs below accessed 3 November 2026). Scope: the Related Work section (main.tex lines 70-80), Table 1 (lines 82-98), and the sentences elsewhere in main.tex that cite the same sources (lines 51, 57, 68, 195, 305; supplementary Table S13). The earlier audit `research/literature/D_revision2_literature_and_novelty_audit.md` (the "D audit") was re-checked against primary sources rather than copied; Section 0.3 lists where it is confirmed, corrected or extended.

Read-only inputs: `paper/main.tex`, `paper/references.bib`, `paper/supplementary.tex`, `research/REFERENCE_VERIFICATION.md`, `research/literature/D_revision2_literature_and_novelty_audit.md`, `research/V3/PREREGISTRATION.md`. Nothing outside `02_work/literature/` was modified. Scratch downloads were kept in `/tmp/v3lit_dl/` (outside the repository) and are not part of the deliverable.

---

## 0. Method

### 0.1 Access levels used

- **FULL TEXT**: the whole paper was obtained and the relevant sections read. When the copy is not the publisher's version of record (VoR), this is stated (e.g. "accepted manuscript", "author-hosted copy carrying the ACM copyright notice").
- **SPEC TEXT**: official specification, RFC, Internet-Draft or product documentation; the relevant clauses were located and read.
- **ABSTRACT**: only the abstract (Crossref/OpenAlex/publisher landing page) was read.
- **METADATA**: only bibliographic metadata (Crossref, DataCite, publisher or distributor catalogue).
- "(via WebFetch)" means the text was read through the WebFetch tool, which returns an extracted and summarised view of the page. Quotes obtained this way are reproduced as returned, and are marked.

Crossref records were fetched from `https://api.crossref.org/works/{DOI}`; OpenAlex records from `https://api.openalex.org/works/https://doi.org/{DOI}` (abstracts reconstructed from the inverted index); DataCite from `https://api.datacite.org/dois/{DOI}`. RFCs from `https://www.rfc-editor.org/rfc/rfcNNNN.txt`; Internet-Draft status from the IETF Datatracker API and history page.

### 0.2 Evidence categories for item (7)

- **Experimentally demonstrated**: measured in PBTI's own single-host synthetic testbed against the authors' baselines (B1-B4) or ablations. This is not a comparison against an implementation of the cited work unless stated.
- **Theoretically established**: follows from the definitions or specifications (argued in the paper; there is no formal proof, as main.tex l.309 states).
- **Only asserted**: stated in main.tex without an experiment or argument that compares with the cited mechanism.

### 0.3 Status of the D audit (revision 2) after re-verification

Confirmed: SCITT policy registration "most recently committed to the VDS at the time of Registration" (RFC 9943 §5.1.1.1) and auditor reproduction of registration checks (§5.1.1.2); SSB fork rule "All messages from the point of the fork onwards are ignored"; PeerReview linear-hash-chain evidence and log replay; GDP "hole" and "branch" definitions in Mor's dissertation; Sparkplug `seq` 0-255, `bdSeq`, Reorder Timeout and Rebirth, and non-normative security; ACE replay window per publisher (default 32); NIST SP 800-207A per-connection service authentication; NiFi per-FlowFile provenance and lineage; CloudEvents `source`+`id` duplicate rule.

Corrected or refined:

1. **SCITT does not mandate an RFC 9162 log.** RFC 9943 is VDS-agnostic: "SCITT supports multiple VDSs" (§4); "Specific VDSs, such as those described in [RFC9162] and [RFC9942] ... are out of scope for this document" (§5.1.3). RFC9162_SHA256 is one VDS registered by RFC 9942. The D audit and main.tex l.76 both say "an RFC 9162 log".
2. **"Equivocation" in SCITT is a property of the Transparency Service** ("a state where a TS provides inconsistent proofs to Relying Parties", §3). It is not an issuer signing two statements for one event. Two statements from one issuer about one subject are treated as **supersession** (§9.2).
3. **The ACE pub-sub countersignature is applied by the publisher itself to its own encrypted object** (draft-05 §6.1). There is no second party, so it is a per-object *origin* signature that crosses an untrusted broker, not a relay countersignature. The D audit's B5/C\* mapping ("RFC 9338 countersignature by the edge workload, as publishers do in the ACE CoAP pub-sub profile") conflates the two roles. main.tex l.74 calls ACE "the closest analogue of the relay statement".
4. **The SSB ICN 2019 paper does not mention "canonical JSON".** The canonical-JSON signing rule is in the SSB Protocol Guide (ssbc.github.io), which main.tex does not cite.
5. **GDP ICDCS 2019 full text (accepted manuscript) is available** through the NSF Public Access Repository (PAR 10111285). It already defines holes and branches, so mor2019gdp can be cited for them at FULL TEXT level, not only at abstract level. The VoR (IEEE) was not accessed.
6. **Mor dissertation date.** The dissertation is dated "Fall 2019" (title page; copyright 2019) and is also Technical Report UCB/EECS-2020-10 (10 January 2020). The D audit cites the 2020 report; main.tex cites the 2019 dissertation. Both are the same document.
7. **Sparkplug `bdSeq` also wraps after 255.** The D audit mentions only `seq`.
8. **Kafka's idempotent producer enforces strict in-order sequences.** It does not only de-duplicate: a sequence that is not exactly last+1 is rejected, lower as duplicate and higher as a fatal out-of-sequence error (KIP-98). PBTI's B4/B5 "(did, ep, seq) idempotency" accepts gaps and out-of-order arrivals, so it is CloudEvents-like keyed de-duplication with a Kafka-like key, not Kafka semantics.
9. **Intrusion recovery is now FULL TEXT for Taser, Retro and Warp** (the D audit had abstracts and first pages). Ammann et al. 2002 remains ABSTRACT.
10. **New since revision 2:**
    - NIST SP 800-82 Rev. 4 initial public draft (21 Sep 2026; comments due 30 Nov 2026), which adds "IIoT and cloud convergence" and "applying zero trust principles".
    - Kafka 4.4 documentation (Oct 2026).
    - NiFi current release 2.12.0 (13 Sep 2026).
    - KIP-1269 ("Configurable number of batches to retain in broker", voting in progress).
    - The ACE draft is unchanged since -05 (6 Jul 2026), still In WG Last Call.

---

## 1. Summary table

| # | Work / standard | Access | main.tex description | Action |
|---|---|---|---|---|
| A | RFC 9943 SCITT | SPEC TEXT | partly inaccurate ("RFC 9162 log"; "out of scope" over-attributed) | correct |
| B | RFC 9942 COSE Receipts (not cited) | SPEC TEXT (abstract, §5 located) | - | add |
| C | RFC 9338 COSE countersignatures | SPEC TEXT | accurate ("analogous to a countersignature") | add precise binding sentence |
| D | ACE CoAP pub-sub profile -05 | SPEC TEXT (I-D) | **mischaracterized** as "closest analogue of the relay statement" | correct |
| E | Secure Scuttlebutt (ICN 2019) | FULL TEXT | mostly accurate; "canonical JSON" not in the cited paper; "turn forks into evidence" overstated for SSB | refine; cite Protocol Guide |
| F | PeerReview (SOSP 2007) | FULL TEXT (non-publisher copy) | accurate | minor wording |
| G | Global Data Plane (ICDCS 2019; dissertation 2019) | FULL TEXT (AM; thesis) | accurate in l.76; Table 1 "evidence" loose | refine |
| H | Sparkplug 3.0.0 / ISO/IEC 20237:2023 | SPEC TEXT / METADATA | accurate but incomplete | add 0-255 wrap, Rebirth, "non-normative" |
| I | Kafka idempotent producer (KIP-98; docs 4.4) | FULL TEXT (KIP) / SPEC TEXT (docs) | accurate; B4 description (l.195) partly inaccurate | refine |
| J | Apache NiFi provenance | SPEC TEXT | accurate | update version/URL |
| K | Taser, Retro, Warp, Ammann et al. | FULL TEXT (3), ABSTRACT (1) | accurate | add Retro; note triggers |
| L | NIST SP 800-207 / 800-207A | SPEC TEXT | accurate (800-207 tenet 3 says per-session) | optional precision |
| M | NISTIR 8259A | SPEC TEXT | accurate; Table S13 "boot epoch" not in 8259A | soften S13 |
| N | NIST SP 800-82r3 (+ r4 ipd) | SPEC TEXT / METADATA+abstract | accurate | mention r4 ipd; use §5.2.3.4 |
| O | IEC 62443-3-3 / 4-2 | ABSTRACT (webstore) | accurate at concept level | keep "alignment, not conformance" |
| P | Recent 2023-2026 papers | ABSTRACT / METADATA | not cited | consider 3-5 additions |

---

## A. RFC 9943: SCITT architecture

1. **Bibliographic.**
   - *An Architecture for Trustworthy and Transparent Digital Supply Chains*. H. Birkholz, A. Delignat-Lavaud, C. Fournet, Y. Deshpande, S. Lasker.
   - IETF RFC 9943, Standards Track, June 2026. DOI 10.17487/RFC9943; Crossref: type report, issued 2026-06.
   - Bib entry `rfc9943` matches.
2. **Official URL.** https://www.rfc-editor.org/info/rfc9943 ; text https://www.rfc-editor.org/rfc/rfc9943.txt
3. **Access.** SPEC TEXT: full RFC text; §§3, 4, 5, 5.1.1-5.1.3, 6.3, 7, 9.1-9.7 read.
4. **Mechanism relevant to PBTI.**
   - Issuers produce COSE_Sign1 *Signed Statements*.
   - The TS verifies the issuer signature and, for X.509, "MUST build and validate a complete certification path ... to one of the root certificates currently registered as a trust anchor" (§5.1.1.1).
   - "Registration Policies and trust anchors MUST be made Transparent ... by Registering them as Signed Statements on the VDS. The TS MUST apply the Registration Policy that was most recently committed to the VDS at the time of Registration" (§5.1.1.1).
   - "TSs MUST ensure that for any Signed Statement they register, enough information is made available to Auditors to reproduce the Registration checks" (§5.1.1.2).
   - The VDS must be append-only, non-equivocating and *replayable* (§5.1.3). Receipts "MUST support inclusion proofs" (§3, via RFC 9942).
   - "The Registration time is recorded as the timestamp when the TS added the Signed Statement to its VDS" (§7).
   - Registration and receipt steps "may be shared between a batch of Signed Statements" (§6.3).
   - Policies may evaluate statements "given the current TS state and the entire Envelope" (§6.3, step 3).
   - Client authentication is "implementation specific and out of scope" (§6.3, step 1). The Client "is not necessarily the Issuer" (§7).
   - Ordering: "the Relying Party cannot assume that the ordering of Signed Statements in the VDS matches the ordering of their issuance" (§9.1).
   - Supersession: "A registered Statement may be superseded by a subsequently submitted Signed Statement from the same Issuer, with the same subject" (§9.2).
   - Key compromise: "Revocation strategies for compromised keys are out of scope for this document" (§9.4.2).
   - Equivocation is TS-level (§3).
5. **What PBTI does similarly.**
   - Per-statement admission under a versioned policy in force at decision time.
   - X.509 path validation of signers.
   - A Merkle-checkpointed evidence log copied to a witness.
   - An independent auditor that re-derives decisions (A-DET), which matches SCITT's "reproduce the Registration checks".
   - The commit time used for taint plays the role of SCITT's recorded registration time.
6. **What PBTI does differently.**
   - Per-event identity slots and delivery-history semantics: duplicate, contest, gap, horizon. SCITT defines none and treats same-subject statements as supersession.
   - A relay statement that binds the submitting edge workload into the evidence. In SCITT the submitting Client's authentication is out of scope and is not bound into the statement.
   - Revocation with a compromise time, and taint of derived data. SCITT puts revocation strategies out of scope and has no derived-data notion.
   - Evidence records for every receipt, including rejects. SCITT logs registered statements.
   - JSON/JCS with Ed25519 instead of COSE/CBOR.
7. **Evidence status.**
   - The delivery-history and taint mechanisms are *experimentally* exercised against B4 (E5, E8, E14), but not against a SCITT implementation. Relative to SCITT, the differences are design-level (*asserted*).
   - SCITT's state-dependent registration policies (§6.3) could in principle express a Rule-L-like policy. This is my inference, not tested.
8. **main.tex vs source.**
   - l.76: "The IETF SCITT architecture standardizes policy-gated registration of signed statements into an RFC~9162 log with receipts and auditor-reproducible registration decisions~\cite{rfc9943}; it leaves delivery history, revocation and derived-data consequences out of scope." **Partly supported.**
     - Policy-gated registration, receipts and auditor reproducibility: supported.
     - "RFC 9162 log": not supported. The VDS is generic (§§4, 5.1.3), and RFC9162_SHA256 is one VDS from RFC 9942.
     - "Out of scope": supported only for revocation (§9.4.2). Delivery history and derived data are simply not addressed (absence), not declared out of scope.
   - l.57 "Transparency services standardize policy-gated registration of signed statements" and Table 1 l.92 "SCITT registration policy": supported. l.94 "transparency logs and receipts [rfc9162, rfc9943]": supported; add rfc9942.
9. **Change.** Replace the sentence (RELATED_WORK_CHANGES R3). Add RFC 9942. Optionally position PBTI as "a SCITT-like registration profile for telemetry, adding per-event delivery-history semantics, relay binding and revocation-driven taint". Mention that SCITT leaves client authentication out of scope (§6.3), which is the gap the relay statement fills.

## B. RFC 9942: COSE Receipts (not cited in main.tex)

1. *CBOR Object Signing and Encryption (COSE) Receipts*. O. Steele, H. Birkholz, A. Delignat-Lavaud, C. Fournet. RFC 9942, Standards Track, June 2026. DOI 10.17487/RFC9942 (Crossref, issued 2026-06).
2. https://www.rfc-editor.org/info/rfc9942
3. SPEC TEXT, limited to the abstract and the RFC9162_SHA256 sections (located, not read in full).
4. Receipts "prove properties of a Verifiable Data Structure (VDS) to a verifier". It defines CBOR encodings for Merkle inclusion and consistency proofs. "RFC9162_SHA256 (395: 1) supports both (-1) inclusion and (-2) consistency proofs."
5-7. PBTI's signed checkpoints and witness copies play the role of receipts and consistency evidence. PBTI issues no per-statement receipts to the edge; main.tex l.313 lists "signed commit receipts at the edge" as future work. This is design-level.
8. Not cited. main.tex attributes "receipts" to rfc9943, which delegates them to RFC 9942.
9. Add `rfc9942` where receipts are mentioned (l.76, Table 1 l.94).

## C. RFC 9338: COSE countersignatures (what a countersignature binds)

1. **Bibliographic.** *CBOR Object Signing and Encryption (COSE): Countersignatures*. J. Schaad. RFC 9338 (part of STD 96), December 2022. DOI 10.17487/RFC9338 (Crossref, issued 2022-12). Bib entry `rfc9338` matches.
2. **Official URL.** https://www.rfc-editor.org/info/rfc9338
3. **Access.** SPEC TEXT (§§1, 2, 3, 3.1-3.3, 4, 6 read).
4. **Mechanism: exactly what is bound.**
   - A V2 countersignature is a signature over the CBOR-encoded `Countersign_structure` = [ `context`, `body_protected` (the target's serialized protected header), `sign_protected` (the countersigner's protected header; omitted for Countersignature0V2), `external_aad`, `payload`, `other_fields` ].
   - `other_fields` is "an array of all bstr fields after the second ... this would be an array of one element for the COSE_Sign1 structure containing the signature value" (§3.3).
   - The context is "CounterSignatureV2"/"CounterSignature0V2" when `other_fields` is present, and "CounterSignature"/"CounterSignature0" when it is absent.
   - So a V2 countersignature on a COSE_Sign1 covers the target's protected header, payload and signature value. The V1 algorithm of RFC 8152 was deprecated because "the cryptographically computed value was not always included" (§1).
   - Semantics: on COSE_Sign1 "the countersignature makes a statement about the existence of a signature" (§3). On COSE_Encrypt0 "the existence of the encrypted data is attested to", which is distinct from attesting to the plaintext (§3).
   - "The countersigner does not need to be related to the producer of what is being countersigned" (§3.1).
   - The application must check "that the key is correctly paired with the signing identity and that the signing identity is authorized" (§3.3). Authorization semantics are therefore left to the application.
5. **Similar.** PBTI's relay statement contains odig = H(JCS(obs) ‖ σ_o) and is signed by a second party (the edge workload). It therefore binds the same coverage as a V2 countersignature on COSE_Sign1: the content and the origin signature.
6. **Different.**
   - PBTI binds by digest inside a separate signed JSON statement that also carries workload identity (wid, wkid), relay time and mode, with domain separation. RFC 9338 embeds the countersignature in the unprotected header.
   - The encoding is JCS and Ed25519 rather than deterministic CBOR.
   - PBTI adds workload-identity semantics (SPIFFE ID) and a path-bound authorization policy, which RFC 9338 leaves to the application.
7. **Evidence status.**
   - Equivalent binding strength is *theoretically evident*: both cover content and signature.
   - The security effect of having a relay signature is *experimentally demonstrated* against B4 and ablation A1 (E5 stolen device key; mixed workload).
   - Any advantage over an RFC 9338-based relay is neither claimed nor tested. The preregistered B5 uses a relay countersignature "in the style of RFC 9338", which is faithful if it covers header, payload and origin signature.
8. **main.tex vs source.**
   - (C1) l.68 "a relay statement, analogous to a countersignature": supported.
   - l.74 "[ACE] countersigns published objects ... with COSE countersignatures~\cite{ietf_ace_coap_pubsub,rfc9338}": the RFC 9338 part is supported; for ACE see D.
   - Table 1 l.91 "COSE countersignatures through a broker~\cite{rfc9338,ietf_ace_coap_pubsub}": partly misleading (see D).
9. **Change.** State the precise coverage and cite RFC 9338 as the relay analogue (second-party countersignature). Do not cite ACE as the relay analogue (R4, R5).

## D. IETF ACE CoAP pub-sub profile: current version and status

1. **Bibliographic.**
   - *CoAP Publish-Subscribe Profile for Authentication and Authorization for Constrained Environments (ACE)*. F. Palombini (Ericsson), C. Sengul (Brunel University), M. Tiloca (RISE AB).
   - Internet-Draft draft-ietf-ace-coap-pubsub-profile-**05**, 6 July 2026, expires 7 January 2027. Intended status: Standards Track (draft header).
   - IETF stream, ACE WG. **WG state "In WG Last Call"**, set 8 January 2026 (Datatracker history). No newer revision as of 3 Nov 2026.
   - It replaces draft-ietf-ace-pubsub-profile (-00 to -11, 2020-2025). It depends on draft-ietf-core-coap-pubsub, at -22 (2 Nov 2026) and "Submitted to IESG for Publication / AD Evaluation".
2. **Official URL.** https://datatracker.ietf.org/doc/draft-ietf-ace-coap-pubsub-profile/05/ ; text https://www.ietf.org/archive/id/draft-ietf-ace-coap-pubsub-profile-05.txt ; history https://datatracker.ietf.org/doc/draft-ietf-ace-coap-pubsub-profile/history/
3. **Access.** SPEC TEXT (Internet-Draft, work in progress): §1, §6.1-6.3, Security Considerations read.
4. **Mechanism.**
   - "The Publisher uses the symmetric COSE Key received from the KDC to protect the payload ... creates a COSE_Encrypt0 object". Then: "the Publisher uses its private key ... in order to countersign the COSE_Encrypt0 object as specified in [RFC9338]" (§6.1).
   - The Countersign_structure uses context "CounterSignature", and 'payload' "is the ciphertext of the COSE_Encrypt0 object".
   - "source authentication of published topic data is achieved by means of the corresponding Publisher signing such content with its own private key" (§1).
   - Partial IV = "the current Sender Sequence Number of the Publisher", reset to 0 on joining or rekeying (§6.1).
   - Replay: "every Subscriber maintains a Replay Window for each different Publisher ... RECOMMENDED ... default size of 32". The Subscriber "MUST verify that ... SN_P ... has not been received before from P. If the verification above fails, the Subscriber MUST stop processing the COSE_Encrypt0 object" (§6.3). The window is reinitialised on a new group key.
   - Trust: "The Broker is only trusted with verifying that a Publisher is authorised to publish on a certain topic ... However, the Broker is not trusted with the published topic data in itself".
5. **Similar.** Per-object source authentication end to end through an untrusted broker; per-publisher sequence numbers; external authorization (AS/KDC).
6. **Different.**
   - The countersigner is the publisher (origin) itself. There is no second, relaying party, so ACE is an analogue of PBTI's *origin* statement crossing a broker, not of the relay statement.
   - The signature attests the ciphertext (RFC 9338 §3).
   - A second object with an already-received SN is dropped before any content comparison: first-arrival wins and no conflict evidence is produced. This is an inference from §6.3.
   - It has no durable per-identity history, no evidence log or lineage, no backlog semantics beyond the window, and no revocation-to-data consequences. It is CoAP, not MQTT, and an Internet-Draft.
7. **Evidence status.**
   - The PBTI contest of a conflicting version is *experimentally demonstrated* only against B4's first-writer-wins (E5).
   - Against ACE semantics, it is *theoretically* evident from §6.3 (window semantics) but not tested.
8. **main.tex vs source.**
   - l.74: "The IETF ACE \pubsub\ profile for CoAP countersigns published objects end to end through an untrusted broker with COSE countersignatures and per-publisher replay windows ..., the closest analogue of the relay statement; its window treats a second version of a sequence number as a replay, so equivocation is not surfaced." The first clause is **supported**.
   - "the closest analogue of the relay statement" is **not supported**: the ACE countersignature is the publisher's own source signature, not a relay or second-party countersignature.
   - The final clause is **supported as an inference** from §6.3.
   - Table 1 l.91 lists ACE under the relay statement: same issue.
   - The bib note should record the WGLC state.
9. **Change.**
   - Move ACE to the origin-signature or replay discussion.
   - Name RFC 9338 (generic second-party countersignature) as the relay analogue. Optionally also name in-toto/WIMSE workload-signed statements (D audit, not re-verified here).
   - Mark ACE as "Internet-Draft in WG Last Call" (R4).

## E. Secure Scuttlebutt (Tarr et al., ICN 2019): feed fork semantics

1. **Bibliographic.** D. Tarr, E. Lavoie, A. Meyer, C. Tschudin, *Secure Scuttlebutt: An Identity-Centric Protocol for Subjective and Decentralized Applications*. ICN '19, 24-26 Sep 2019, Macao, China, pp. 1-11. DOI 10.1145/3357150.3357396 (Crossref: title "Secure Scuttlebutt" with subtitle; licence CC BY-SA 4.0). The bib entry `tarr2019ssb` matches.
2. **Official URL.** https://doi.org/10.1145/3357150.3357396 ; PDF read: https://conferences2.sigcomm.org/acm-icn/2019/proceedings/icn19-19.pdf
3. **Access.** FULL TEXT: the ACM-formatted paper with DOI and CC BY-SA licence block, from the SIGCOMM proceedings site (the ACM DL itself was blocked). Additionally SPEC TEXT: *Scuttlebutt Protocol Guide*, https://ssbc.github.io/scuttlebutt-protocol-guide/ ("Message format", "Signature").
4. **Mechanism.**
   - Each message contains "the backlink to the previous message", "the public key of the message's author", "the sequence number of the message, which must be one more than the sequence number of the previous message", "a claimed timestamp", "a hash indicator", "the content", and "the author's signature over all the previous data". "Each user is identified by an ed25519 keypair."
   - Fork rule: "message has exactly zero or one incoming backlinks. If it has more than one, the log is considered forked. All messages from the point of the fork onwards are ignored, the log cannot be appended to anymore."
   - Footnote 4: "A nontrivial problem is how nodes should react to forked feeds: ideally, the information that a fork occurred should be propagated. We leave this open for future work."
   - §6.3: one identity used concurrently on two devices yields "two competing hash chains with the consequence that peer relays would stop propagating at least one, if not both log extensions".
   - Protocol Guide: "Before signing a message it must be serialized according to a specific canonical JSON format", defined by ECMA-262 `JSON.stringify` formatting.
5. **Similar.** PBTI's observation statement has the same structure: author key/did, seq, prev, ts, payload and an Ed25519 signature over a canonical form.
6. **Different.**
   - A boot epoch (ep) namespaces sequences after reboot. SSB has none; state loss forks the feed (inference from §6.3).
   - RFC 8785 JCS instead of JSON.stringify formatting.
   - Per-slot contest instead of whole-feed invalidation.
   - Out-of-order arrival is admitted. SSB appends strictly in order; out-of-order messages are fetched by plugins.
   - Relay statement, policy and revocation.
7. **Evidence status.**
   - Per-slot versus whole-feed handling is *only asserted*; B5-strict, which implements the SSB rule, is planned but not yet run.
   - Order-independence of Rule L is *theoretically* argued (monotone function of a grow-only set) and unit-tested, with no formal proof.
8. **main.tex vs source.**
   - l.76: "Secure Scuttlebutt feeds use the structure of the observation statement here (author key, sequence, hash of the previous message, Ed25519 over canonical JSON) and treat a fork as invalidating the feed from that point~\cite{tarr2019ssb}". **Supported, except "canonical JSON"**, which is not in the cited paper (it is in the Protocol Guide).
   - l.57: "signed logs turn forks into evidence~\cite{tarr2019ssb,haeberlen2007peerreview}". Overstated for SSB: SSB detects forks and ignores the feed, and leaves propagation of fork information as future work. Fully supported for PeerReview.
   - Table 1 l.90 "signed feeds": supported. l.93 "fork and equivocation evidence": "fork detection" is more accurate for SSB.
9. **Change.** Cite the Protocol Guide for canonical JSON, or drop "canonical JSON". Reword l.57 (R1, R6).

## F. PeerReview (Haeberlen, Kouznetsov, Druschel, SOSP 2007)

1. **Bibliographic.** *PeerReview: Practical Accountability for Distributed Systems*. SOSP '07, 14-17 Oct 2007, Stevenson, WA, USA, pp. 175-188. DOI 10.1145/1294261.1294279 (Crossref title "PeerReview" with subtitle). The bib entry matches.
2. **Official URL.** https://doi.org/10.1145/1294261.1294279 ; copy read: https://courses.mpi-sws.org/ds-ws16/papers/PeerReview-SOSP-2007.pdf
3. **Access.** FULL TEXT: a copy carrying the ACM copyright line "SOSP'07 ... Copyright 2007 ACM 978-1-59593-591-5/07/0010", hosted on an MPI-SWS course page. It was not obtained from the publisher.
4. **Mechanism.**
   - A per-node tamper-evident log with a hash chain, and signed *authenticators* that commit to log prefixes.
   - Consistency: witnesses obtain authenticators and challenge the node. "If j is correct, these log entries form a linear hash chain that contains the hash values in all the other authenticators. If they do not, ω has obtained verifiable evidence that j is faulty." Fig. 3 shows "a forked log with two branches".
   - Audit: "i replays j's log using a reference implementation that defines j's expected behavior."
   - Assumptions: deterministic nodes, signing, and periodic checking by a correct node.
   - Duplicates: "If i has already received m, it can simply re-send the earlier acknowledgment."
5. **Similar.** A successor's commitment implies its predecessors' hashes (≈ PBTI's successor-implied digests). Forks become evidence. Deterministic replay by an auditor (≈ A-DET).
6. **Different.** PBTI applies the idea per event identity in data admission and produces authoritative-state outcomes (COMMITTED/CONTESTED) rather than exposing a node. PBTI has no per-device witness sets, and it replays the verifier's decisions rather than node behaviour.
7. **Evidence status.** PBTI's contest of equivocations and gap-fills is *experimentally demonstrated* against B4 (E5). Equivalence or difference relative to PeerReview-style exposure is *only asserted*.
8. **main.tex vs source.** l.76 "PeerReview turns equivocation in hash-chained logs into verifiable evidence and has auditors replay logs~\cite{haeberlen2007peerreview}" is **supported in substance**. The paper's terms are "forked log", "witnesses" and "auditing"; "equivocation" does not occur in it. Table 1 l.93-94 is supported.
9. **Change.** Optional wording: "turns a forked hash-chained log into verifiable evidence, and witnesses audit nodes by replaying their logs against a reference implementation".

## G. Global Data Plane (Mor et al., ICDCS 2019; Mor, dissertation 2019): holes and branches

1. **Bibliographic.**
   - (a) N. Mor, R. Pratt, E. Allman, K. Lutz, J. Kubiatowicz, *Global Data Plane: A Federated Vision for Secure Data in Edge Computing*. 2019 IEEE 39th ICDCS, Dallas, TX, USA (Crossref: July 2019; event start 2019-07-07), pp. 1652-1663, DOI 10.1109/ICDCS.2019.00164.
   - (b) N. Mor, *Global Data Plane: A Widely Distributed Storage and Communication Infrastructure*, PhD dissertation, University of California, Berkeley, Fall 2019 (title page; "Copyright 2019"; committee chair J. D. Kubiatowicz). The same document is Technical Report UCB/EECS-2020-10, 10 January 2020.
2. **Official URLs.**
   - (a) https://doi.org/10.1109/ICDCS.2019.00164 ; accepted manuscript https://par.nsf.gov/servlets/purl/10111285 (NSF PAR 10111285, award 1838833).
   - (b) https://escholarship.org/uc/item/25b9n38g (eScholarship returned HTTP 202 with an empty body to the shell); https://www2.eecs.berkeley.edu/Pubs/TechRpts/2020/EECS-2020-10.html (PDF read).
3. **Access.** (a) FULL TEXT of the accepted manuscript (not the IEEE VoR). (b) FULL TEXT (EECS PDF).
4. **Mechanism.**
   - DataCapsules are single-writer hash-pointer chains. "Each update is associated with a signed 'heartbeat' generated by the writer; such signature is over the most-recent record" (ICDCS AM).
   - Holes: "In case this DataCapsule-server crashes, the hash-pointer chain can result in a 'hole' ... Such holes can be transient or permanent" (AM). "A hole represents a sequence of records that are permanently lost. Whether holes are acceptable or not ... is an application-level decision" (thesis §3.4.2).
   - Branches: "a branch is a condition when two or more records have hash pointers that point to the same record. Such branches result in a partial order of records. In such a case, a reader can only expect strong eventual consistency" (AM).
   - The thesis adds that "in the presence of accidental or malicious stale servers ... the writer may start from an older record, thus resulting in an abandoned branch".
5. **Similar.** Hash-linked signed records for edge/IoT data. LOST ≈ hole; prev-link conflict ≈ branch.
6. **Different.**
   - GDP keeps branches as a partial order and makes no authority decision. PBTI contests the affected slots.
   - GDP signs heartbeats that attest the history, not necessarily each record.
   - GDP has no relay identity, admission policy, horizon quarantine or revocation-to-taint.
7. **Evidence status.** *Only asserted* (no GDP-style baseline).
8. **main.tex vs source.**
   - l.76 "the Global Data Plane names holes and branches in signed edge-data streams~\cite{mor2019gdp,mor2019thesis}": **supported** by both sources.
   - Table 1 l.93 "fork and equivocation evidence~\cite{...,mor2019gdp}": loose. GDP treats branches as a consistency condition (benign under quasi-single-writer mode, or caused by stale servers), not as evidence of misbehaviour.
   - REFERENCE_VERIFICATION's "mor2019gdp: verified (abstract only)" can be upgraded to "accepted manuscript read".
9. **Change.** Add "and treats branches as a partial order" (R6). Add a note to `mor2019thesis` that it is also UCB/EECS-2020-10 (bib file).

## H. Eclipse Sparkplug 3.0.0 / ISO/IEC 20237:2023

1. **Bibliographic.**
   - *Sparkplug 3.0.0: Sparkplug Specification*, Eclipse Sparkplug Contributors, Version 3.0.0, 2022-11-16 (PDF metadata and cover).
   - ISO/IEC 20237:2023, *Information technology — Sparkplug® version 3.0*, Edition 1.0, 2023-10, 123 pp., ISO/IEC JTC 1 (VDE Verlag catalogue).
2. **Official URLs.** https://sparkplug.eclipse.org/specification/version/3.0/documents/sparkplug-specification-3.0.0.pdf ; https://www.iso.org/standard/86204.html (returned a client error; not retrieved) ; metadata via https://www.vde-verlag.de/iec-standards/252221/iso-iec-20237-2023.html (via WebFetch).
3. **Access.** Eclipse: SPEC TEXT (§1.7, §5.9, Chapter 7, NBIRTH/NDEATH/payload rules). ISO: METADATA only, via a distributor; the ISO page was unreachable.
4. **Mechanism.**
   - `seq`: NBIRTH "MUST include a seq number that is between 0 and 255 (inclusive)", and following messages carry "a sequence number that is one more than the previous up to 255 where it wraps back to zero". The counter is Edge-Node-scoped and covers NBIRTH, DBIRTH, NDATA and DDATA.
   - `bdSeq`: "MUST start at zero and increment by one on every new MQTT CONNECT packet"; the Will (NDEATH) bdSeq must match the NBIRTH. "If in the previous NBIRTH a value of 255 was sent, the next ... bdSeq number value MUST have a value of 0." A Will death with a duplicate bdSeq "MUST be ignored".
   - §5.9: "Sparkplug Host Applications are required to validate the order of messages arriving from Edge Nodes". Hosts "SHOULD provide a configurable Reorder Timeout parameter". When it elapses with messages still missing, the host "MUST send an NCMD to the Edge Node with a Node Control/Rebirth request".
   - Store-and-forward of "historical data" while the Primary Host is offline is described.
   - Security: "Security is not directly addressed in the Sparkplug Specification with normative statements" (§1.7). Chapter 7 "is provided for guidance only and is non-normative" and covers TLS, client ID/username/password and ACLs, which "offer some security in preventing compromised credentials from being able to be used to spoof Edge Nodes" (§7.4.3).
5. **Similar.** (bdSeq, seq) ≈ (ep, seq) in an edge-node namespace, comparable to PBTI's workload-scoped namespace for gateway-attested devices. Reorder Timeout ≈ admission horizon; Rebirth ≈ state resynchronization.
6. **Different.**
   - Sparkplug's 8-bit wrapping `seq` (and wrapping `bdSeq`) cannot serve as a persistent event identity. PBTI's (did, ep, seq) does not wrap.
   - PBTI adds payload signatures and hash links, and resolves gaps by evidence and horizon instead of Rebirth (republishing state).
7. **Evidence status.** The identity limitation is *theoretically* evident from the spec (256 values). PBTI was not compared with a Sparkplug pipeline: *only asserted* for any behavioural difference.
8. **main.tex vs source.** l.74 "Sparkplug, the MQTT specification for IIoT standardized as ISO/IEC 20237, defines edge-node and birth/death sequence numbers and a reorder timeout but leaves security to TLS and broker access control" is **supported**. More precisely, security is non-normative guidance (TLS, credentials, ACLs). Table 1 l.90 "producer epochs and sequences~\cite{kip98,sparkplug3}": supported.
9. **Change.** Add the 0-255 wrap of both counters, the Rebirth request on reorder timeout, and "non-normative" (R14).

## I. Apache Kafka idempotent producer (KIP-98; current documentation)

1. **Bibliographic.**
   - (a) *KIP-98 - Exactly Once Delivery and Transactional Messaging*, Apache Kafka Improvement Proposal. "Created by Apurva Mehta, last updated by Matthias J. Sax on Mar 04, 2026"; joint work of J. Gustafson, F. P. Junqueira, A. Mehta, Sriram, G. Wang; status "Adopted"; JIRA KAFKA-4815.
   - (b) Apache Kafka 4.4 documentation, *Producer Configs* ("Last modified October 22, 2026: MINOR: Add 4.4 release") and *Design* ("Last modified October 26, 2026").
   - (c) KIP-1269, *Configurable number of batches to retain in broker* (author PoAn Yang; "Voting in progress"; last updated 13 Apr 2026).
   - (d) Wang et al., SIGMOD 2021, DOI 10.1145/3448016.3457556 (Crossref verified; content not re-read).
2. **Official URLs.**
   - https://cwiki.apache.org/confluence/display/KAFKA/KIP-98+-+Exactly+Once+Delivery+and+Transactional+Messaging
   - https://kafka.apache.org/44/configuration/producer-configs/
   - https://kafka.apache.org/44/design/design/
   - https://cwiki.apache.org/confluence/display/KAFKA/KIP-1269:+Configurable+number+of+batches+to+retain+in+broker
3. **Access.** (a) FULL TEXT (design page; "Idempotent Producer Guarantees" and protocol sections). (b) SPEC TEXT. (c) SPEC TEXT (via WebFetch). (d) METADATA.
4. **Mechanism.**
   - KIP-98: "Every new producer will be assigned a unique PID during initialization ... For a given PID, sequence numbers will start from zero and be monotonically increasing, with one sequence number per topic partition".
   - KIP-98: "The broker will reject a produce request if its sequence number is not exactly one greater than the last committed message from that PID/TopicPartition pair. Messages with a lower sequence number result in a duplicate error, which can be ignored by the producer. Messages with a higher number result in an out-of-sequence error, which indicates that some messages have been lost, and is fatal."
   - KIP-98: "since each new instance of a producer is assigned a new, unique, PID, we can only guarantee idempotent production within a single producer session."
   - The producer epoch serves zombie fencing for a TransactionalId: it ensures "only one legitimate active instance of a producer". ProduceRequests "include the PID, epoch, and sequence number".
   - Kafka 4.4 `enable.idempotence` (default `true`): "Note that enabling idempotence requires max.in.flight.requests.per.connection to be less than or equal to 5 (with message ordering preserved for any allowable value), retries to be greater than 0, and acks must be 'all'. Idempotence is enabled by default if no conflicting configurations are set. If conflicting configurations are set and idempotence is not explicitly enabled, idempotence is disabled. If idempotence is explicitly enabled and conflicting configurations are set, a ConfigException is thrown."
   - `transactional.id`: "enables reliability semantics which span multiple producer sessions ... If no TransactionalId is provided, then the producer is limited to idempotent delivery."
   - Design doc: "the broker assigns each producer an ID and deduplicates messages using a sequence number that is sent by the producer along with every message."
   - KIP-1269 (via WebFetch): the limit of 5 exists "because the Kafka broker hardcodes the number of distinct batch sequence numbers it retains" (`ProducerStateEntry#NUM_BATCHES_TO_RETAIN`).
   - **What it does not protect against.** Item (b) is stated in KIP-98, and (e) follows directly from the KIP-98 rule; (a), (c) and (d) are my inferences from the mechanism.
     - (a) application-level re-sends: each `send()` gets a new sequence, so the guarantee covers the producer's internal retries only;
     - (b) duplicates across producer restarts without `transactional.id` (a new PID);
     - (c) any authenticity or integrity property: PID and sequence are not cryptographically bound to content, so any client authorized to produce can write, and a different payload with an already-used sequence is answered as a duplicate because content is not compared;
     - (d) anything beyond the producer-to-partition hop;
     - (e) out-of-order arrival, which is rejected (OutOfOrderSequence), not buffered.
5. **Similar.** A producer-assigned (identity, epoch, sequence) key, under which a benign retry does not create a duplicate.
6. **Different.** PBTI's identity is origin-signed. Conflicting versions are contested rather than silently dropped. Gaps and out-of-order arrivals are admitted with gap evidence. The scope is end to end across MQTT and persistent across reboots via ep.
7. **Evidence status.** Against a Kafka-style key (B4): *experimentally demonstrated*, both the advantage (E5 front-running equivocations and gap-fills) and the cost (E8 sequence reuse). Note that B4 is not Kafka-faithful, because it accepts gaps and out-of-order sequences.
8. **main.tex vs source.**
   - l.78: "Kafka's idempotent producer de-duplicates retries by producer identifier, epoch and sequence number~\cite{kip98,wang2021kafka}, and CloudEvents consumers may treat events with the same source and identifier as duplicates~\cite{cloudevents102}; both make a conflicting second version indistinguishable from a retry." **Supported.** The last clause is a correct inference from KIP-98 and CloudEvents 1.0.2 ("Consumers MAY assume that Events with identical `source` and `id` are duplicates"). It omits "per partition" and "within a single producer session".
   - l.195 (B4): "idempotent admission keyed by the producer-assigned event identity as in Kafka's idempotent producer~\cite{kip98} (exact duplicates suppressed; a conflicting version of an admitted identity rejected, first writer wins)". **Partly accurate.** Kafka does not distinguish an exact duplicate from a conflicting version (both receive a duplicate error), and it rejects out-of-order sequences, which B4 does not.
9. **Change.** Add scope and constraints in one clause (R7). Re-describe B4/B5's key as "CloudEvents-style keyed de-duplication with a Kafka-like (producer, epoch, sequence) key" (R11).

## J. Apache NiFi data provenance

1. **Bibliographic.** Apache NiFi Team, *Apache NiFi User Guide*, section "Data Provenance", and *Apache NiFi In Depth*, section "Provenance Repository". The 1.x pages (cited URL) were "Last updated 2024-10-21"; the 1.x line ends at 1.28.1. The current release is **NiFi 2.12.0, released 2026-09-13** (download page); 2.x guide at https://nifi.apache.org/nifi-docs/user-guide.html. Not peer reviewed.
2. **URLs.** https://nifi.apache.org/docs/nifi-docs/html/user-guide.html (1.x) ; https://nifi.apache.org/nifi-docs/user-guide.html (2.x) ; https://nifi.apache.org/nifi-docs/nifi-in-depth.html
3. **Access.** SPEC TEXT (product documentation; Data Provenance and Provenance Repository sections read in both 1.x and 2.x).
4. **Mechanism.**
   - "Because NiFi records and indexes data provenance details as objects flow through the system, users may perform searches, conduct troubleshooting and evaluate things like dataflow compliance".
   - "The Provenance Repository is where the history of each FlowFile is stored. This history is used to provide the Data Lineage (also known as the Chain of Custody) of each piece of data. Each time that an event occurs for a FlowFile (FlowFile is created, forked, cloned, modified, etc.) a new provenance event is created."
   - Content storage "can be said to be an immutable versioned content store".
   - Caveat: "the content could be deleted before the provenance event that references it is deleted".
   - Users can replay FlowFiles and view lineage ("Find Parents", "Expand").
5. **Similar.** Lineage per data item, immutable content, replay.
6. **Different (inference from the sections read).** No cryptographic producer identity, signatures, hash chaining or external witness, so no tamper evidence against administrators. Retention-bounded. No automatic invalidation of descendants after compromise.
7. **Evidence status.** *Only asserted* (no NiFi comparison).
8. **main.tex vs source.** l.76 "Apache NiFi records fine-grained provenance and lineage for each data item it handles~\cite{nifi_userguide}" is **supported** (1.x and 2.x text identical for these passages).
9. **Change.** Update `nifi_userguide` to the 2.x URL and version, or state "1.x" explicitly. Optionally add the contrast "without cryptographic binding of producers" (marked as our reading) (R13).

## K. Intrusion recovery: Taser (SOSP 2005), Retro (OSDI 2010), Warp (SOSP 2011), Ammann et al. (TKDE 2002)

1. **Bibliographic.**
   - **Taser**: A. Goel, K. Po, K. Farhadi, Z. Li, E. de Lara, *The Taser Intrusion Recovery System*. SOSP '05, 23-26 Oct 2005, Brighton, UK, pp. 163-176, DOI 10.1145/1095810.1095826. Crossref: is-identical-to 10.1145/1095809.1095826, the ACM SIGOPS OSR issue.
   - **Retro**: T. Kim, X. Wang, N. Zeldovich, M. F. Kaashoek, *Intrusion Recovery Using Selective Re-execution*. 9th USENIX OSDI '10, Vancouver, BC, Canada, 2010. No DOI; USENIX citation metadata.
   - **Warp**: R. Chandra, T. Kim, M. Shah, N. Narula, N. Zeldovich, *Intrusion Recovery for Database-backed Web Applications*. SOSP '11, 23-26 Oct 2011, Cascais, Portugal, pp. 101-114, DOI 10.1145/2043556.2043567.
   - **Ammann et al.**: P. Ammann, S. Jajodia, P. Liu, *Recovery from Malicious Transactions*. IEEE TKDE 14(5):1167-1185, Sep 2002, DOI 10.1109/TKDE.2002.1033782.
2. **URLs (copies read).**
   - Taser: https://www.cs.toronto.edu/~delara/papers/sosp2005.pdf
   - Retro: https://www.usenix.org/conference/osdi10/intrusion-recovery-using-selective-re-execution (PDF https://www.usenix.org/legacy/events/osdi10/tech/full_papers/Kim.pdf)
   - Warp: https://pdos.csail.mit.edu/papers/warp:sosp11.pdf
   - Ammann et al.: abstract via OpenAlex. A related report, *Trusted Recovery from Information Attacks*, AFRL-IF-RS-TR-2001-158 (Jajodia, Ammann, Liu, Aug 2001), was read via WebFetch at https://apps.dtic.mil/sti/pdfs/ADA394732.pdf; it lists the TKDE paper as "under review".
3. **Access.**
   - Taser: FULL TEXT (co-author-hosted copy carrying "SOSP'05 ... Copyright 2005 ACM 1-59593-079-5/05/0010").
   - Retro: FULL TEXT (USENIX open-access proceedings; USENIX is the publisher).
   - Warp: FULL TEXT (MIT PDOS copy carrying "SOSP '11 ... Copyright 2011 ACM 978-1-4503-0977-6/11/10").
   - Ammann: ABSTRACT. The VoR was not accessed; OpenAlex lists only a CiteSeerX submitted-version record.
4. **Mechanism.**
   - Taser: "reverts tainted, i.e. attack-dependent, file-system operations but preserves legitimate operations". "The tainting algorithm derives the set of tainted objects using the audit log, the dependency rules ... and an initial set of tainted objects, known as detection points, that are provided by an intrusion detection system (IDS) or an administrator". The resolver "uses a selective redo algorithm that only replays legitimate operations".
   - Retro: "records an action history graph, which is a detailed dependency graph describing the system's execution ... uses the action history graph to undo an unwanted action and its indirect effects by first rolling back its direct effects, and then re-executing legitimate actions that were influenced by that change". It "assumes that intrusion detection and analysis tools ... detect attacks and pinpoint attack edges".
   - Warp: "When an administrator learns of a security vulnerability in a web application, he or she can use WARP to check whether that vulnerability was recently exploited". "WARP constructs a global dependency graph ... and uses it to retroactively patch vulnerabilities by rolling back parts of the system to an earlier checkpoint, fixing the vulnerability ... and re-executing any past actions that may have been affected". It also repairs "configuration mistakes, such as accidentally giving permissions to the wrong user".
   - Ammann (abstract): "Recovery is complicated by the presence of benign transactions that depend, directly or indirectly, on the malicious transactions. We present algorithms to restore only the damaged part of the database."
5. **Similar.** PBTI's taint is retroactive, dependency-driven (lineage) invalidation and recomputation of derived windows after late discovery of compromise, with raw data preserved.
6. **Different.**
   - Trigger: credential revocation with a compromise time (X.509 invalidity-date semantics). In the cited systems the trigger is IDS or administrator detection points, or a patch.
   - Precision: origin-key-precise, so device-signed data merely relayed by a compromised workload is not tainted.
   - Domain: IIoT telemetry windows. There is no re-execution of external effects.
7. **Evidence status.** The containment effect is *experimentally demonstrated* against B2-B4 (E14, revocation-interval sweep, ablation A11). "An IIoT instance of intrusion recovery" is a positioning claim, *only asserted* (no Taser/Warp-style baseline). Origin-key precision is a design property exercised in E14 but not separately quantified in main.tex.
8. **main.tex vs source.**
   - l.76 "Intrusion-recovery systems revert tainted operations and repair dependent state along dependency graphs~\cite{goel2005taser,chandra2011warp,ammann2002recovery}; we found none that triggers such repair from credential revocation in IIoT data pipelines." **Supported** for Taser and Warp (full text). For Ammann et al. it is supported at abstract level: "depend, directly or indirectly". "Dependency-graph based algorithms" is wording from the related 2001 AFRL report, not verified in the TKDE text.
   - l.57 "intrusion-recovery systems repair state derived from compromised inputs~\cite{goel2005taser}": supported.
   - Table 1 l.94: supported.
9. **Change.** Add Retro (the canonical selective re-execution system; bib entry provided). Say explicitly that the cited systems are triggered by detection points, an administrator or a patch (R8).

## L. NIST SP 800-207 and SP 800-207A

1. **Bibliographic.**
   - S. Rose, O. Borchert, S. Mitchell, S. Connelly, *Zero Trust Architecture*, NIST SP 800-207, August 2020, DOI 10.6028/NIST.SP.800-207.
   - R. Chandramouli, Z. Butcher, *A Zero Trust Architecture Model for Access Control in Cloud-Native Applications in Multi-Location Environments*, NIST SP 800-207A, September 2023, DOI 10.6028/NIST.SP.800-207A (Crossref issued 2023-09-13).
   - Both current; no superseding versions on CSRC.
2. **URLs.** https://csrc.nist.gov/pubs/sp/800/207/final ; https://csrc.nist.gov/pubs/sp/800/207/a/final ; PDFs at nvlpubs.nist.gov.
3. **Access.** SPEC TEXT (both PDFs; definition, tenets, PDP/PEP; 207A §3 identity-tier recommendations).
4. **Mechanism.**
   - 800-207 operative definition: ZT is "designed to minimize uncertainty in enforcing accurate, least privilege per-request access decisions in information systems and services in the face of a network viewed as compromised". Access is "granted through a policy decision point (PDP) and corresponding policy enforcement point (PEP)".
   - Tenet 3: "Access to individual enterprise resources is granted on a per-session basis".
   - Tenet 2: communication should "protect confidentiality and integrity, and provide source authentication".
   - Tenet 1 counts "small footprint devices that send data to aggregators/storage" among resources.
   - Abstract: authentication and authorization "are discrete functions performed before a session to an enterprise resource is established".
   - 800-207A ID-SEG-REC-2: each service presents "a short-lived cryptographically verifiable identity credential ... that is authenticated per connection and reauthenticated regularly". "In an ideal situation, services would be authenticated for each service request. Since this is highly disruptive ... this authentication is accomplished at the connection level via mutual Transport Layer Security (mTLS)".
   - No mention of queues or brokers was found in 207A (the text was searched for queue/broker/publish/asynchronous).
5. **Similar.** PBTI's verifier acts as PEP/PDP and applies short-lived workload credentials (SPIFFE).
6. **Different.** PBTI applies the decision per data object and carries the decision evidence with the object across an asynchronous broker.
7. **Evidence status.** The per-object-versus-session difference is *experimentally* exercised against B2 (per-message session verification; e.g. E5, E14), which is the authors' approximation, not a NIST reference implementation.
8. **main.tex vs source.**
   - l.72 "NIST SP 800-207 defines Zero Trust around policy decision and enforcement points that grant per-request access to resources": **supported** by the definition. Tenet 3 says access is *granted* per session; consider "per-request access decisions".
   - "its cloud-native profile authenticates services per connection~\cite{nist_sp800_207a}": **supported** ("profile" is informal; 207A calls itself a ZTA model).
   - Intro l.51 "requires authentication and authorization for every access to an enterprise resource": acceptable; the source wording is "before a session ... is established".
9. **Change.** Optional precision. Optionally cite tenet 2 ("source authentication"), which directly motivates object-level origin authentication (R2).

## M. NISTIR 8259A

1. M. Fagan, K. N. Megas, K. Scarfone, M. Smith, *IoT Device Cybersecurity Capability Core Baseline*, NISTIR 8259A, May 2020, DOI 10.6028/NIST.IR.8259A. CSRC still lists it as final, with a planning note about a federal profile and translations.
2. https://csrc.nist.gov/pubs/ir/8259/a/final ; PDF https://nvlpubs.nist.gov/nistpubs/ir/2020/NIST.IR.8259A.pdf
3. SPEC TEXT (Table 1 read).
4. Six capabilities.
   - "Device Identification: The IoT device can be uniquely identified logically and physically."
   - "Data Protection: The IoT device can protect the data it stores and transmits from unauthorized access and modification", including "digital signature validation".
   - Also Device Configuration, Logical Access to Interfaces, Software Update and Cybersecurity State Awareness.
   - Table 1 maps them to IEC 62443-4-2 CRs: Device Identification → CR 1.2; Data Protection → CR 3.1, CR 3.4, CR 4.1, CR 4.2, CR 4.3; Cybersecurity State Awareness → CR 2.8, CR 3.9, CR 6.1 (titles not verified; IEC text not accessed).
5-7. PBTI assumes these device capabilities (keyed identity, signing). This is alignment only, with nothing to test.
8. main.tex l.305 "to NISTIR~8259A device capabilities" is supported. Supplementary Table S13 "device identification (keyed identity, boot epoch)": the **boot epoch is not part of 8259A's Device Identification** (unique logical and physical identifiers). That mapping is the authors' extension.
9. Soften S13; optionally use 8259A's own IEC 62443-4-2 crosswalk (R12).

## N. NIST SP 800-82 Rev. 3 (and Rev. 4 initial public draft)

1. **Bibliographic.**
   - K. Stouffer et al. (10 authors), *Guide to Operational Technology (OT) Security*, NIST SP 800-82r3, September 2023 (Crossref issued 2023-09-28), DOI 10.6028/NIST.SP.800-82r3. Final and current.
   - **NIST SP 800-82 Rev. 4 initial public draft**, 21 September 2026, comments due 30 November 2026, DOI 10.6028/NIST.SP.800-82r4.ipd. Crossref lists only K. Stouffer; CSRC lists 9 authors.
2. **URLs.** https://csrc.nist.gov/pubs/sp/800/82/r3/final ; https://csrc.nist.gov/pubs/sp/800/82/r4/ipd
3. **Access.** r3: SPEC TEXT (PDF searched; §5.2.3.4 read). r4 ipd: METADATA plus the CSRC announcement text (draft PDF not read).
4. **Mechanism.**
   - r3 §5.2.3.4: ZTA is a paradigm where "authorization decisions are made closer to the resource being requested and are continuously evaluated".
   - r3 OT-specific guidance: "Some OT components (e.g., PLCs, controllers, HMI) may not support the technologies or protocols required to fully integrate with a ZTA implementation ... organizations should consider applying a ZTA to compatible devices, such as those typically found at the functionally higher levels of the OT architecture (e.g., Purdue model Levels 3, 4, 5, and the OT DMZ)". Also: "Within OT environments, shared credentials may be utilized".
   - r3 recommends encryption "to support secure connections or conduits for OT environments when the connections must pass over non-OT network segments".
   - r4 ipd announcement: adds "Industrial Internet of Things (IIoT) and cloud convergence" and "Security architecture guidelines focused on protecting system management functions and applying zero trust principles".
5. **Similar.** Gateway attestation for legacy devices matches r3's advice to apply ZTA where devices can support it.
6-7. Alignment only (*asserted*; no conformance).
8. main.tex l.305 "to OT security guidance~\cite{nist_sp800_82r3}" is supported. Table S13 "managed conduits" is IEC 62443 vocabulary; r3 uses "secure connections or conduits". Acceptable.
9. Optionally use r3 §5.2.3.4 to motivate gateway attestation. Mention r4 as an initial public draft (cite only as "ipd", not as final) (R12).

## O. IEC 62443-3-3:2013 and IEC 62443-4-2:2019 (concepts only)

1. **Bibliographic.**
   - IEC 62443-3-3:2013, *Industrial communication networks - Network and system security - Part 3-3: System security requirements and security levels*. Ed. 1.0, 2013-08-07, 80 pp., includes the April 2014 corrigendum, stability date 2027; the webstore shows a new edition "Under development".
   - IEC 62443-4-2:2019, *Security for industrial automation and control systems - Part 4-2: Technical security requirements for IACS components*. Ed. 1.0, 2019-02-27, 192 pp., includes the August 2022 corrigendum, stability date 2027; "Under development".
2. **URLs.** https://webstore.iec.ch/en/publication/7033 ; https://webstore.iec.ch/en/publication/34421
3. **Access.** ABSTRACT (webstore abstracts and metadata). The standards' texts were not accessed, so no SR/CR wording is verified.
4. **Concepts.**
   - 4-2 abstract: "there are a total of seven foundational requirements (FRs): a) identification and authentication control (IAC), b) use control (UC), c) system integrity (SI), d) data confidentiality (DC), e) restricted data flow (RDF), f) timely response to events (TRE), and g) resource availability (RA)".
   - 3-3 abstract: SRs are used "along with the defined zones and conduits for the system under consideration".
5-7. Concept-level alignment only; no conformance testing (main.tex l.305 and Table S13 already say so).
8. l.305 "to five IEC~62443 foundational requirements" is supported at concept level. S13 lists FR1, FR2, FR3, FR5, FR6, with FR4 and FR7 not addressed, which is consistent with the FR list.
9. Keep "alignment, not compliance". Do not name SR/CR titles unless the standard text is consulted. 8259A's crosswalk (M) gives CR numbers that can be cited via 8259A.

## P. Recent (2023-2026) peer-reviewed papers the manuscript should know about

All DOIs verified in Crossref (record exists; metadata below is from Crossref). Abstracts are from Crossref/OpenAlex unless noted. Access level is given per item.

1. **Jaigirdar, Tan, Rudolph, Bain (2023)**, *Security-Aware Provenance for Transparency in IoT Data Propagation*. IEEE Access 11:55677-55691. DOI 10.1109/ACCESS.2023.3280928. ABSTRACT.
   - Mechanism: "we integrate security metadata into the provenance graph with predefined security policies", evaluated on a "hypothetical IoT-Health scenario" in six simulated cases (e.g. "failed signature verification").
   - Relevance: recording admission and security decisions in provenance, close to PBTI's evidence records.
   - Difference: no delivery-history semantics, relay identity or taint (abstract-level reading).
2. **Lazzaro, Licciardi, Buccafurri (2026)**, *Verifiable Credentials for IoT Devices in the Context of the eIDAS Trust Framework*. **Future Internet** 18(10):557 (the target journal), published 16 Oct 2026. DOI 10.3390/fi18100557. FULL TEXT via WebFetch; the evaluation section was not fully read.
   - Mechanism: a stable X.509 technical credential plus a dynamic operational Verifiable Credential "bound to the authenticated device identity", with "separate update and revocation paths" (X.509 CRL; W3C Bitstring Status List v1.0). Authorization is evaluated per request against the mTLS session identity. About 226 µs per request.
   - Relevance: credential lifecycle, revocation and status for IoT devices.
   - Difference: binds credentials to sessions and requests, not to individual data objects (as returned via WebFetch).
3. **Yousaf, Veltri, Penzotti, Zanichelli (2026)**, *SMQTT: An End-to-End Security Framework for MQTT-Based Industrial IoT Communications*. 2026 6th ICECET, Rome, pp. 1-7. DOI 10.1109/ICECET65726.2026.11632926. ABSTRACT.
   - Mechanism: application-layer, group-based end-to-end security for MQTT "without requiring modifications to the standard broker"; a key server handles "client authentication, authorization, and group key distribution"; it provides "authenticity, confidentiality, and replay protection".
   - Relevance: the closest recent IIoT/MQTT analogue of PBTI's broker-crossing problem. It should sit beside ENTRUST and MQTT-I.
4. **Wang, Chen, Wu, Zhou, Zhu, Zhi (2026)**, *Auditable Zero-Trust Sensor-Cloud Repositories: Append-Only Logging and Anomaly Detection for Misbehavior Discovery* (APEX). 2026 SCECS, Xuzhou, pp. 284-290. DOI 10.1109/SCECS69812.2026.11565876. ABSTRACT.
   - Mechanism: "a tamper-evident audit trail via hash-chained log entries and periodic signed checkpoints" for zero-trust edge-cloud sensor repositories, plus anomaly detection on access streams.
   - Relevance: close to PBTI's evidence log and checkpoints. It audits access and retrieval rather than ingestion admission.
5. **Oskouei, Mandal, Ghorbani (2025)**, *BI-MQTT: Broker-Independent Integrity for Publish-Subscribe Messaging with Ring Signatures*. IEEE CASCON 2025, Toronto, pp. 601-602 (a two-page paper). DOI 10.1109/CASCON66301.2025.00104. ABSTRACT.
   - Mechanism: publishers ring-sign messages so "subscribers ... verify origin authenticity and integrity directly, without relying on broker trust", implemented on Mosquitto.
   - Relevance: broker-independent origin authentication (with anonymity, unlike PBTI's attributable identity). A short paper; cite only as an example.
6. **Faraj, Megías, Garcia-Alfaro (2024)**, *ZIRCON: Zero-watermarking-based approach for data integrity and secure provenance in IoT networks*. J. Inf. Secur. Appl. 85:103840. DOI 10.1016/j.jisa.2024.103840. METADATA only.
   - Same authors as faraj2025provslr. Not characterised; read before citing.
7. **Yuan, Mu, Dang, Chen, Gao, Li (2026)**, *A lightweight edge-cloud public auditing architecture with blockchain-assisted data provenance for IIoT*. J. Systems Architecture 181:104022 (Dec 2026). DOI 10.1016/j.sysarc.2026.104022. METADATA only.
   - IIoT edge-cloud plus provenance plus auditing, directly in scope by title. Read before citing.

Also seen (lower relevance): Zhang et al. (2025), TrID, Sci. Rep. 15:4796, DOI 10.1038/s41598-025-89589-7 (ABSTRACT; DID-based trusted IoT data collection); Chien, Shih, Huang (2025), Sensors 25(17):5308, DOI 10.3390/s25175308 (ABSTRACT; MQTT E2E models).

Evidence status for all of P: none is compared experimentally; any difference statement would be *asserted* at abstract level. Suggested placements are in RELATED_WORK_CHANGES R9.

---

## 2. Implications for the B5 baseline (fidelity to the published mechanisms)

These follow directly from the sources above and from `research/V3/PREREGISTRATION.md`.

1. **Relay countersignature (RFC 9338).** For fidelity, B5's relay must cover the origin's protected header (or canonical statement), payload and origin signature. PBTI's odig already does this. ACE is *not* a source for a relay countersignature: there, the publisher signs its own ciphertext.
2. **Feed-level fork handling.**
   - SSB: "All messages from the point of the fork onwards are ignored, the log cannot be appended to anymore". This is exactly B5-strict.
   - PeerReview: the reaction is node *exposure* with verifiable evidence, not a data hold.
   - GDP: branches are accepted as a partial order.
   - None of the three specifies an automated "review-based recovery". B5's reviewer (R = 60 s) is the authors' own extension and should be labelled as such.
3. **Idempotency.** True Kafka semantics reject out-of-order sequences (OutOfOrderSequence, fatal) and treat any lower sequence as a duplicate without content comparison. A Kafka-faithful variant would lose data under the reordering scenarios (E9, E10). B4/B5's (did, ep, seq) first-writer-wins key is CloudEvents-style keyed de-duplication; describe it so.
4. **Taint.** The Taser/Warp trigger is detection points, an administrator or a patch. B5's revocation-with-compromise-time trigger is PBTI's own (RFC 5280 invalidity-date semantics, §5.3.2 verified). Call it "Taser/Warp-style dependency-driven invalidation with PBTI's revocation trigger".
5. **SCITT-style evidence.** SCITT logs registered statements only. If B5 logs every receipt, that is PBTI's choice, not SCITT's.

## 3. Sources that could not be fully accessed

| Source | Outcome |
|---|---|
| ACM DL (dl.acm.org) for Sigwart, Faraj, Kovach, SSB, Taser, Warp, PeerReview | HTTP 403 (shell) / client error (WebFetch). Alternative copies used as stated. |
| IEEE Xplore (GDP ICDCS VoR, Rodigari, James, Ammann, Alsaedi/TON_IoT) | HTTP 418 (shell). The GDP accepted manuscript was found at NSF PAR. |
| ISO page for ISO/IEC 20237 | client error; metadata from VDE Verlag. |
| eScholarship PDF of the Mor dissertation | HTTP 202, empty body (shell); the EECS tech-report PDF was used. |
| NSA data-pillar CSI (media.defense.gov) | HTTP 403; not re-verified in V3 (D audit read it). |
| MDPI full text (Lazzaro 2026) | HTTP 403 (shell); read via WebFetch. |
| Ammann et al. 2002 VoR | not found open; abstract only. |
| C2PA 2.3, in-toto/WIMSE, OPC UA | not re-verified in V3 (outside the requested list); D audit records stand. |
