# V3 version-of-record (VoR) check for selected citations

Date of all checks: 3 November 2026.

Crossref records were retrieved from `https://api.crossref.org/works/{DOI}`. I used curl from the audit shell; this is the same REST API that WebFetch would query. OpenAlex records (`https://api.openalex.org/works/https://doi.org/{DOI}`) were used to find abstracts and open copies.

"VoR reached" means the publisher's own copy, or a copy explicitly identical to it. Where only an author or repository copy was read, this is stated and the access level is reported for that copy.

Publisher platforms blocked from this environment:
- ACM Digital Library: HTTP 403 from the shell and "client_error" from WebFetch, for both landing pages and PDFs.
- IEEE Xplore: HTTP 418 from the shell.

As a result, no ACM or IEEE VoR could be opened, including the gold-OA ACM items.

## Summary

| Key | Crossref metadata vs references.bib | VoR reached? | Best access achieved | All citing sentences supported? |
|---|---|---|---|---|
| sigwart2019bcprov | match | no | FULL TEXT of arXiv v2 preprint | yes, one with nuance (l.195 "signature and hash-chain") |
| faraj2025provslr | match | no (gold OA at ACM, blocked) | FULL TEXT of HAL-deposited author version (hal-05033850) | yes |
| rodigari2021ztmc | match | no | FULL TEXT of arXiv v1 preprint (3 pp.) | partly: l.72 "session, connection or flow level" does not fit request-level authorization |
| james2025mqttzt | match | no | ABSTRACT | partly: broker-side ABAC yes; "session/connection/flow level" not verifiable |
| kovach2024sovereign | match (venue, pages; event location now known) | no (gold OA at ACM, blocked) | ABSTRACT (+ conference slides) | yes (abstract level) |
| mor2019gdp | match | no | FULL TEXT of accepted manuscript (NSF PAR) | yes (l.76); Table 1 "evidence" loose |
| goel2005taser | match | no (ACM) | FULL TEXT of co-author-hosted copy with ACM notice | yes |
| chandra2011warp | match | no (ACM) | FULL TEXT of MIT-hosted copy with ACM notice | yes |
| ammann2002recovery | match (initials as in Crossref) | no | ABSTRACT | yes, at abstract level ("dependency graphs" wording from a related AFRL report) |

No bibliographic field in references.bib conflicts with Crossref for these nine entries. Two optional enrichments:
- `kovach2024sovereign`: Crossref gives the event as "eSAAM 2024 ... Mainz, Germany" and the publication date as 2024-10-22. This resolves the "[BIBLIOGRAPHIC VERIFICATION REQUIRED] conference dates" note in REFERENCE_VERIFICATION.md to the extent Crossref records it; Crossref has no event dates.
- `mor2019thesis`: add "also Technical Report UCB/EECS-2020-10".

---

## 1. sigwart2019bcprov

**Crossref** (10.1145/3365871.3365886):
- Title: "Blockchain-based Data Provenance for the Internet of Things".
- Venue: *Proceedings of the 9th International Conference on the Internet of Things* (IoT 2019, Bilbao, Spain), ACM, pp. 1-8, issued 2019-10-22.
- Authors: Marten Sigwart, Michael Borkowski, Marco Peise, Stefan Schulte, Stefan Tai.
- Licence field: ACM copyright policy (not open access).

**Bib comparison.** Matches. Optional additions: address Bilbao, Spain; month October.

**Access.**
- VoR (https://dl.acm.org/doi/10.1145/3365871.3365886): blocked.
- Read instead: FULL TEXT of arXiv:1905.06852v2 (6 Aug 2019), https://arxiv.org/pdf/1905.06852. It uses the ACM template with a placeholder DOI ("https://doi.org/10.1145/nnnnnnn.nnnnnnn"), so it is an author preprint, not the VoR.
- OpenAlex also lists the TUHH repository record hdl:11420/11840 (submitted version), which returned a server error.

**Citing sentences.**
- l.57: "Ledger-anchored provenance~\cite{sigwart2019bcprov,...} ... protect records after they are created". **Supported.** The preprint says: "once records have entered the system, the integrity of records depends on the underlying blockchain technology".
- l.76: "IoT provenance schemes use ... blockchains~\cite{javaid2018blockpro,sigwart2019bcprov,lazzaro2024mqtt}". **Supported** (Ethereum smart-contract framework).
- l.76: "Sigwart et al. leave open how only correct records enter a provenance system~\cite{sigwart2019bcprov}". **Supported**, with one nuance. The preprint says: "the framework also needs to provide mechanisms to ensure only correct records enter the system in the first place. As a first step, we implement the concept of ownership of data points using tokens to prevent arbitrary clients from creating provenance records. In future work, this concept could be further extended by mechanisms that guarantee the correctness of the records themselves." A fairer wording is "leave the correctness of records at entry to future work, beyond token-based ownership".
- l.195: "B3 approximates the class of signature and hash-chain provenance schemes~\cite{hasan2009tos,javaid2018blockpro,sigwart2019bcprov}". **Loosely supported.** Sigwart's scheme is ledger- and token-based (Ethereum transactions are signed and the chain is hash-linked), but it does not sign individual provenance records with device keys. "Signature- and ledger-based" would be more accurate.

**Caveat.** Content was read in a preprint, so sentence support is conditional on the VoR not differing.

## 2. faraj2025provslr

**Crossref** (10.1145/3718735):
- Title: "Security Approaches for Data Provenance in the Internet of Things: A Systematic Literature Review".
- *ACM Computing Surveys* 57(10), pp. 1-41, published online 2025-05-08, issue 2025-10-31.
- Authors: Omair Faraj, David Megias, Joaquin Garcia-alfaro (sic, Crossref capitalisation).
- Licence: CC BY 4.0.

**Bib comparison.** Matches. Crossref gives no article number, so none should be added.

**Access.**
- VoR (gold OA, https://dl.acm.org/doi/10.1145/3718735): blocked.
- Read instead: FULL TEXT of the HAL deposit hal-05033850v1 (submitted 28 Jul 2025), https://hal.science/hal-05033850/document, 36 pages. It is ACM-typeset but lacks the final VoR markers (no volume/article footer, no DOI line, no licence block), so it is an author-deposited version, not verifiably the VoR.

**Citing sentence.**
- l.57: "A recent systematic review of IoT provenance security finds that most studies address forgery and modification but overlook replay, packet drop and provenance-chain tampering~\cite{faraj2025provslr}." **Supported.** The HAL text says: "While most papers address forgery and modification attacks, both for data and provenance, they tend to overlook other significant attack vectors such as replay attacks, packet drop, and provenance chain tampering."

## 3. rodigari2021ztmc

**Crossref** (10.1109/cloud53861.2021.00097):
- Title: "Performance Analysis of Zero-Trust multi-cloud".
- Venue: 2021 IEEE 14th International Conference on Cloud Computing (CLOUD), Chicago, IL, USA (event start 2021-09-05), pp. 730-732, issued Sept 2021.
- Authors: Simone Rodigari, Donna O'Shea, Pat McCarthy, Martin McCarry, Sean McSweeney.

**Bib comparison.** Matches.

**Access.**
- VoR (IEEE): blocked.
- Read instead: FULL TEXT of arXiv:2105.02334v1 (5 May 2021, 3 pages; submitted version), https://arxiv.org/pdf/2105.02334.

**Citing sentence.**
- l.72: "overhead has been measured for multi-cloud service meshes~\cite{rodigari2021ztmc} ... These works operate at the session, connection or flow level". The first clause is **supported**. The paper "proposes a multi-cloud framework and a testing workflow to analyse performance of the data plane under load and the impact on the control plane, when Zero Trust is enabled" (Istio).
- The second clause is **not a good fit**. The paper frames Zero Trust as "encrypting all network communication, authenticating, and authorizing every request" (abstract), which is request-level, not session-, connection- or flow-level. Suggested wording: "operate at the point of access (session, connection, request or flow)".

## 4. james2025mqttzt

**Crossref** (10.1109/csr64739.2025.11130016):
- Title: "A Novel MQTT-ZT Secure Broker: Zero Trust Architecture for IoT Security".
- Venue: 2025 IEEE International Conference on Cyber Security and Resilience (CSR), Chania, Crete, Greece (event start 2025-08-04), pp. 433-439.
- Authors: Meha James, Thomas Newe, Donna O'Shea, George D. O'Mahony.
- University of Limerick Pure record: Munster Technological University; ISBN 9798331535919; no full-text file.

**Bib comparison.** Matches.

**Access.**
- VoR (IEEE): blocked. No open copy found (UL Pure: none; OpenAlex: closed).
- Read: ABSTRACT only (OpenAlex). The paper "integrates Attribute-Based Access Control (ABAC) directly into the broker using a built-in Policy Enforcement Point (PEP) and Axiomatics' ALFA policy engine"; processing times are "20-79 ms for publishers and 24-63 ms for subscribers ... at 200 clients".

**Citing sentences.**
- l.51: "...broker-side access control~\cite{...,james2025mqttzt,...}". **Supported** (abstract).
- l.72: "...and to broker-side controls~\cite{james2025mqttzt} ... These works operate at the session, connection or flow level". The broker-side part is **supported**. The granularity claim is **not verifiable** from the abstract: per-publish authorization at the broker is plausible but unconfirmed. Suggested wording as for rodigari2021ztmc.

## 5. kovach2024sovereign

**Crossref** (10.1145/3685651.3686658):
- Title: "Sovereign IIoT Data Exchange Using DAG-Based DLT and International Data Spaces Architecture".
- Venue: *Proceedings of the 4th Eclipse Security, AI, Architecture and Modelling Conference on Data Space* (eSAAM 2024, Mainz, Germany), ACM, pp. 76-85, published 2024-10-22.
- Authors (with ORCIDs): Anhelina Kovach, Jorge Lanza, Leticia Montalvillo, Aitor Urbieta.
- Licence: CC BY 4.0.

**Bib comparison.** Matches. Optional additions: address Mainz, Germany; month October.

**Access.**
- VoR (gold OA, ACM DL): blocked.
- University of Cantabria repository (hdl:10902/34512): robots-disallowed.
- Read: ABSTRACT (OpenAlex): "integrating IOTA Distributed Ledger Technology (DLT) with the International Data Spaces (IDS) Reference Architecture Model (RAM), creating a decentralized data space optimized for IIoT ecosystems". Also the presentation slides at https://www.eclipse.org/events/2024/esaam2024/presentations/eSAAM24_1440_kovach.pdf (title slide and outline only).

**Citing sentence.**
- l.78: "...and sovereign IIoT data exchange has been built on DAG-based ledgers~\cite{kovach2024sovereign}." **Supported** at abstract level (IOTA is the DAG-based DLT named in the title).

## 6. mor2019gdp

**Crossref** (10.1109/icdcs.2019.00164):
- Title: "Global Data Plane: A Federated Vision for Secure Data in Edge Computing".
- Venue: 2019 IEEE 39th International Conference on Distributed Computing Systems (ICDCS), Dallas, TX, USA (event start 2019-07-07), pp. 1652-1663, issued July 2019.
- Authors: Nitesh Mor, Richard Pratt, Eric Allman, Kenneth Lutz, John Kubiatowicz.

**Bib comparison.** Matches (DOI case differs; DOIs are case-insensitive).

**Access.**
- VoR (IEEE): blocked.
- Read: FULL TEXT of the **accepted manuscript** in the NSF Public Access Repository (PAR ID 10111285, NSF award 1838833), https://par.nsf.gov/servlets/purl/10111285. PDF created May 2019 and modified Aug 2019; no IEEE copyright footer, so this is not the VoR.
- Companion: FULL TEXT of the dissertation via UCB/EECS-2020-10 (see the audit, item G).

**Citing sentences.**
- l.76: "the Global Data Plane names holes and branches in signed edge-data streams~\cite{mor2019gdp,mor2019thesis}". **Supported by the accepted manuscript itself.** It says: "the hash-pointer chain can result in a 'hole'"; "a branch is a condition when two or more records have hash pointers that point to the same record. Such branches result in a partial order of records."
- l.93 (Table 1): "fork and equivocation evidence~\cite{tarr2019ssb,haeberlen2007peerreview,mor2019gdp}". **Loosely supported.** GDP represents branches as a partial order with "strong eventual consistency" for readers. It does not treat them as evidence of misbehaviour.

**Change to REFERENCE_VERIFICATION.md** (for the authors, not done here): "verified (abstract only)" can become "accepted manuscript (NSF PAR) read; VoR not accessed".

## 7. goel2005taser

**Crossref** (10.1145/1095810.1095826):
- Title: "The taser intrusion recovery system" (sentence case in Crossref).
- Venue: *Proceedings of the twentieth ACM symposium on Operating systems principles* (SOSP05, Brighton, UK), ACM, pp. 163-176, issued 2005-10-20.
- Authors: Ashvin Goel, Kenneth Po, Kamran Farhadi, Zheng Li, Eyal de Lara.
- Relation: is-identical-to 10.1145/1095809.1095826 (the ACM SIGOPS OSR issue).

**Bib comparison.** Matches.

**Access.**
- VoR (ACM): blocked.
- Read: FULL TEXT of https://www.cs.toronto.edu/~delara/papers/sosp2005.pdf, a copy hosted by co-author de Lara that carries "SOSP'05, October 23-26, 2005, Brighton, United Kingdom. Copyright 2005 ACM 1-59593-079-5/05/0010". It is likely the camera-ready, but this is not verifiable as the VoR.

**Citing sentences.**
- l.57: "intrusion-recovery systems repair state derived from compromised inputs~\cite{goel2005taser}". **Supported.** The paper: "Taser reverts tainted, i.e. attack-dependent, file-system operations but preserves legitimate operations".
- l.76: "Intrusion-recovery systems revert tainted operations and repair dependent state along dependency graphs~\cite{goel2005taser,...}". **Supported.** "The tainting algorithm derives the set of tainted objects using the audit log, the dependency rules ... and an initial set of tainted objects, known as detection points"; "selective redo algorithm that only replays legitimate operations".
- l.94: "intrusion recovery~\cite{goel2005taser,...}". **Supported.**
- The trigger in Taser is detection points "provided by an intrusion detection system (IDS) or an administrator". This is consistent with main.tex's claim that none triggers repair from credential revocation.

## 8. chandra2011warp

**Crossref** (10.1145/2043556.2043567):
- Title: "Intrusion recovery for database-backed web applications".
- Venue: *Proceedings of the Twenty-Third ACM Symposium on Operating Systems Principles* (SOSP '11, Cascais, Portugal), ACM, pp. 101-114, issued 2011-10-23.
- Authors: Ramesh Chandra, Taesoo Kim, Meelap Shah, Neha Narula, Nickolai Zeldovich.

**Bib comparison.** Matches.

**Access.**
- VoR (ACM): blocked.
- Read: FULL TEXT of https://pdos.csail.mit.edu/papers/warp:sosp11.pdf (MIT PDOS copy carrying "SOSP '11, October 23-26, 2011, Cascais, Portugal. Copyright 2011 ACM 978-1-4503-0977-6/11/10"). Not verifiable as the VoR.

**Citing sentences.**
- l.76 and l.94. **Supported.** Warp "constructs a global dependency graph from this logged information, and uses it to retroactively patch vulnerabilities by rolling back parts of the system to an earlier checkpoint, fixing the vulnerability ..., and re-executing any past actions that may have been affected by the fix".
- Trigger: "When an administrator learns of a security vulnerability". Warp also handles "configuration mistakes, such as accidentally giving permissions to the wrong user". This is relevant to PBTI's policy-version changes; main.tex could note it.

## 9. ammann2002recovery

**Crossref** (10.1109/tkde.2002.1033782):
- Title: "Recovery from malicious transactions".
- *IEEE Transactions on Knowledge and Data Engineering* 14(5):1167-1185, issued Sept 2002.
- Authors: P. Ammann, S. Jajodia, Peng Liu.

**Bib comparison.** Matches (initials as in Crossref).

**Access.**
- VoR (IEEE): blocked. OpenAlex: closed; only a CiteSeerX "submitted version" summary record, not fetched.
- Read: ABSTRACT (OpenAlex): "Recovery is complicated by the presence of benign transactions that depend, directly or indirectly, on the malicious transactions. We present algorithms to restore only the damaged part of the database. We identify the information that needs to be maintained for such algorithms."
- Also read via WebFetch: the related final technical report *Trusted Recovery from Information Attacks*, AFRL-IF-RS-TR-2001-158, Aug 2001 (Jajodia, Ammann, Liu), https://apps.dtic.mil/sti/pdfs/ADA394732.pdf. It describes "dependency-graph based algorithms" and lists the TKDE paper as under review. It is not the TKDE paper.

**Citing sentences.**
- l.76 "revert tainted operations and repair dependent state along dependency graphs" and l.94. **Supported at abstract level** for "repair dependent state". The "dependency graphs" wording is supported only by the related report, not by text verified in the TKDE paper. Acceptable as part of a three-citation group; no change required.

---

## Other VoR observations made in passing

| Key | Observation |
|---|---|
| tarr2019ssb | The ACM-formatted PDF with DOI and CC BY-SA 4.0 licence block, from the SIGCOMM proceedings site, was read in full. It is very likely identical to the VoR. |
| haeberlen2007peerreview | A copy carrying the ACM copyright line, from an MPI-SWS course page, was read in full. The VoR was not accessed. |
| kim2010retro (not yet cited) | USENIX open-access proceedings PDF (the publisher's copy), read in full. |
| alsaedi2020toniot (dataset paper) | The IEEE Access VoR was blocked. A figshare copy (RMIT repository record, licence field "All Rights Reserved") was read. |
