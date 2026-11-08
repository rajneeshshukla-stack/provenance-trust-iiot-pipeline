# A. Named papers: bibliographic verification and content extraction

Manuscript context: provenance-bound, trust-aware ingestion for IIoT edge-to-cloud data pipelines (target: MDPI *Future Internet*).
Verification date: 2026-11-03 (all fetches were made on this date).

---

## 0. Method, access legend, global caveats

**Where the bibliographic fields come from.** Every field comes from one of these sources: the Crossref REST API (`api.crossref.org`); DOI content negotiation at `doi.org` (BibTeX); the `doi.org` RA and handle API; publisher pages (MDPI via WebFetch, CRAD, SpringerLink, ScienceDirect, Microsoft Learn, AWS Docs); the arXiv API and arXiv PDFs; and, where explicitly labelled, index records (OpenAlex, Semantic Scholar, institutional portals). No field was filled from memory. A field that could not be traced is marked **[BIBLIOGRAPHIC VERIFICATION REQUIRED]**.

**Access levels**
- **FULL TEXT (VoR):** the publisher's version of record was read.
- **FULL TEXT (preprint):** an arXiv/submitted version was read. The VoR was not accessed, so the content may differ from the published version.
- **PARTIAL FULL TEXT:** some sections could not be reached. The missing sections are named.
- **ABSTRACT ONLY** / **METADATA ONLY.**

**Content conventions**
- "Not reported" means the examined text does not mention the item. "Not examined (no full text)" means only the abstract or metadata was seen.
- Quotes are verbatim fragments. MDPI and ScienceDirect HTML has no page numbers, so locations are given as section or table numbers.
- For the Chinese-language paper, page numbers are journal page numbers, and the English renderings in square brackets are my translations.

**Endpoints that were blocked or unusable in this session**
- `dl.acm.org`: WebFetch returned `client_error`; shell request returned HTTP 403.
- `ieeexplore.ieee.org`: WebFetch returned an empty page; the shell got HTTP 202 with an empty body.
- `mdpi.com`: shell access is blocked by policy, so WebFetch was used. The MDPI `/pdf` rendition came back as binary and the `/xml` rendition as a bot-check page.
- `hal.science`, `publica.fraunhofer.de`, `dblp.org`: bot challenge.
- `repositorio.unican.es`: TLS verification failed from the shell, even with the proxy CA bundle, and the site is robots-disallowed for WebFetch.
- Semantic Scholar API: HTTP 429 after the first call.
- Crossref: intermittent HTTP 429; retried with back-off.

The WebFetch conversion of MDPI and SpringerLink pages stops at about 100,000 characters. Where that cut off main text, the affected sections are stated for each source.

### Summary table

| # | KEY | DOI | Bibliographic status | Content access |
|---|---|---|---|---|
| 1 | federici2023zt | 10.3390/electronics12030566 | Verified (Crossref + doi.org + MDPI) | FULL TEXT (VoR HTML) |
| 2 | wang2025ztiiot | 10.7544/issn1000-1239.202440840 | Verified (publisher page + DOI RA = ISTIC; not in Crossref) | FULL TEXT (VoR PDF, in Chinese) |
| 3 | zhang2026lztaka | 10.3390/app16136765 | Verified; the claimed date conflict was **not reproduced** | PARTIAL FULL TEXT (VoR HTML through §5.6 and the start of §6) |
| 4 | faraj2025provslr | 10.1145/3718735 | Verified; article number unconfirmed | FULL TEXT (preprint, arXiv v2); VoR not accessed |
| 5 | sigwart2019bcprov | 10.1145/3365871.3365886 | Verified | FULL TEXT (preprint, arXiv v2); VoR not accessed |
| 6 | kovach2024sovereign | 10.1145/3685651.3686658 | Verified (metadata) | METADATA ONLY, plus an abstract from an index (OpenAlex) |
| 7 | asad2026replaypdm | 10.3390/systems14101255 | Verified | FULL TEXT (VoR HTML) |
| 8 | lezzi2025cyberres | 10.1007/s11301-025-00495-8 | Verified; online year 2025 vs. issue year 2026 | FULL TEXT (VoR HTML) |
| 9 | alotaibi2026resilient | 10.3390/app16042079 | Verified | PARTIAL FULL TEXT (§1–§6.1) |
| 10 | rodigari2021ztmc | 10.1109/CLOUD53861.2021.00097 | Verified | FULL TEXT (preprint, arXiv v1); VoR not accessed |
| 11 | alayed2026iztsdn | 10.3390/electronics15112376 | Verified | FULL TEXT (VoR HTML; Table 5 image not readable) |
| 12 | zanasi2024flexzt | 10.1016/j.adhoc.2024.103414 | Verified | FULL TEXT (VoR, open access) |
| 13a | microsoft2026opcuaref | n/a | Verified URL, title, dates | Full page read |
| 13b | aws2025iotlens (+ aws2021securingiot, historical) | n/a | Lens verified; the whitepaper's availability is inconsistent | Lens pages read; whitepaper landing page only |

### All dates found (reported as found; not resolved)

| Src | Date field | Value | Where found |
|---|---|---|---|
| 1 | Published online | 22 January 2023 | MDPI article page; Crossref `published-online` 2023-01-22 (no print date in Crossref) |
| 2 | Received / Revised | 2024-10-31 / 2025-03-27 | PDF p. 2784 footnote ("收稿日期：2024-10-31；修回日期：2025-03-27") |
| 2 | Online | 2025-04-03 | `citation_online_date` meta tag, crad.ict.ac.cn |
| 2 | Issue date | 2025-11-01 | `citation_date` / `dc.date` meta tags, crad.ict.ac.cn |
| 3 | Published (online) | 6 July 2026 | MDPI article page; meta `citation_online_date` 2026/07/06; `dc.date` 2026-07-06 |
| 3 | Publication date (month only) | 2026/7 | MDPI meta `citation_publication_date` |
| 3 | Issue | Vol. 16, Issue 13, "2026 July-1" | MDPI issue table-of-contents page |
| 3 | Crossref created / published-online / issued | 2026-07-06 (created 2026-07-06T14:01:08Z) | api.crossref.org |
| 3 | Crossref journal-issue published-online | 2026-07 (month only) | api.crossref.org |
| 3 | Crossref deposited | 2026-07-08 | api.crossref.org |
| 3 | Licence start (VoR) | 2026-07-06 | api.crossref.org |
| 3 | Version Notes | "article pdf uploaded." 6 July 2026 13:48 CEST, "Version of Record"; HTML "Original file" 6 July 2026 13:50 CEST; HTML "Update" **4 September 2026 05:43 CEST** | MDPI `/notes` page |
| 3 | OpenAlex / Semantic Scholar | 2026-07-06 / 2026-07-06 | api.openalex.org; api.semanticscholar.org |
| 3 | Received / Revised / Accepted | **not found** (no submission-history line in the retrieved page text) | MDPI page via WebFetch |
| 4 | Received / Accepted | 2024-05-24 / 2025-02-13 | Crossref `assertion` (publication history) |
| 4 | Published (online) | 2025-05-08 | Crossref `published-online` and `assertion` |
| 4 | Issue (print) | 2025-10-31, Vol. 57, No. 10 | Crossref `published-print` / `journal-issue` |
| 4 | Crossref created | 2025-02-19 | Crossref (OpenAlex `publication_date` = 2025-02-19) |
| 4 | IP Paris research portal | "Publication date" 8 May 2025; meta online date 2025/08/08 | researchportal.ip-paris.fr (via WebFetch) |
| 4 | arXiv v1 / v2 | 2024-07-03 / 2024-11-02 | export.arxiv.org API |
| 5 | arXiv v1 / v2 | 2019-05-15 / 2019-08-06 | export.arxiv.org API |
| 5 | Published | 2019-10-22 | Crossref (online, print, and assertion) |
| 6 | Crossref created | 2024-10-11 (OpenAlex `publication_date` = 2024-10-11) | Crossref; OpenAlex |
| 6 | Published (online and print) | 2024-10-22 | Crossref |
| 7 | Published online | 6 October 2026 | MDPI page (meta online 2026/10/06, publication 2026/10); Crossref |
| 8 | Received / Accepted / First online | 12 March 2024 / 17 February 2025 / 11 April 2025 | Crossref `assertion` |
| 8 | Issue (print) | June 2026, Vol. 76, No. 2 | Crossref `published-print` |
| 8 | BibTeX `year` | 2025 (from `issued` = online date) | doi.org negotiation |
| 9 | Published online | 20 February 2026 | MDPI page; Crossref (issue online 2026-02) |
| 9 | Preprint | 2025-12-19 (Preprints.org, 10.20944/preprints202512.1717.v1) | Crossref search result |
| 10 | arXiv v1 | 2021-05-05 | arXiv API |
| 10 | Conference | 5–10 September 2021, Chicago, IL, USA | Crossref `event` |
| 10 | published-print / Crossref created | 2021-09 / 2021-11-08 | Crossref |
| 11 | Published online | 1 June 2026 | MDPI page; Crossref |
| 12 | Crossref created | 2024-02-07 | Crossref |
| 12 | Available online | 8 February 2024 | ScienceDirect page metadata (via WebFetch) |
| 12 | Issue | April 2024 (Crossref `published-print` 2024-04); "1 April 2024" (ScienceDirect) | Crossref; ScienceDirect |
| 13a | `ms.date` / displayed "Last updated" / `updated_at` | 2026-07-22 / 2026-08-18 (`data-article-date-source="calculated"`) / 2026-10-27T05:04:00Z | Microsoft Learn HTML |
| 13b | IoT Lens publication date | July 2, 2025 (revisions: Nov 1, 2018; Dec 23, 2019; Mar 10, 2021; Mar 31, 2023; Jul 2, 2025) | AWS Docs, `iot-lens.html` and `document-revisions.html` |
| 13b | Whitepaper publication date | December 20, 2021 ("for historical reference only") | AWS whitepaper landing page (via WebFetch) |

---

## 1. Federici et al. (2023), Electronics

- **KEY:** federici2023zt
- **VERIFIED CITATION:** Federici, F.; Martintoni, D.; Senni, V. A Zero-Trust Architecture for Remote Access in Industrial IoT Infrastructures. *Electronics* **2023**, *12*, 566. https://doi.org/10.3390/electronics12030566
- **BIBTEX** (from doi.org negotiation; only the citation key was changed):
```bibtex
@article{federici2023zt, title={A Zero-Trust Architecture for Remote Access in Industrial IoT Infrastructures}, volume={12}, ISSN={2079-9292}, url={http://dx.doi.org/10.3390/electronics12030566}, DOI={10.3390/electronics12030566}, number={3}, journal={Electronics}, publisher={MDPI AG}, author={Federici, Fabio and Martintoni, Davide and Senni, Valerio}, year={2023}, month=Jan, pages={566} }
```
- **TYPE:** Peer-reviewed journal article. The MDPI page places it in the Special Issue "Cybersecurity and Privacy Issues in Cyber-Physical Systems and Industrial Control Systems".
- **Other verified details (MDPI page):**
  - Volume 12, issue 3, article 566.
  - All three authors are affiliated with Applied Research and Technology, Collins Aerospace, Rome, Italy. Federici and Martintoni contributed equally; Senni is the corresponding author.
  - Funding: Horizon 2020 grant No. 871518 (COLLABS).
- **VERIFICATION SOURCES:**
  - `https://api.crossref.org/works?query.bibliographic=…` (title search)
  - `https://api.crossref.org/works/10.3390/electronics12030566`
  - `https://doi.org/10.3390/electronics12030566` (Accept: application/x-bibtex)
  - `https://www.mdpi.com/2079-9292/12/3/566/htm` (WebFetch, three extraction and verification passes)
- **ACCESS LEVEL:** FULL TEXT (VoR HTML). Characters 0–100,000 of 111,986 were read, covering §1–§6 (Conclusions and Future Work). The last ~12k characters (back matter and references) were not read.

**CONTENT**
- **Research problem:** Secure remote access for collaboration in IIoT infrastructures. The abstract describes the approach as going "beyond the traditional perimeter-based security approach". It "covers the protection of both the network and edge domains of a complex IIoT infrastructure".
- **Domain:** Manufacturing (Industry 4.0 secure remote maintenance, §3.1) and civil aviation (connected aircraft, §3.2).
- **Architecture:** Two layers, following "the Gateway Portal Model of NIST SP 800-207" (§4).
  - **Network layer, SDN (§5.1):** "The Control Layer of the prototype is implemented using an OpenFloodlight SDN controller". It "communicates to the Data Layer with its Southbound API using the OpenFlow protocol". The Data Layer uses "OpenVirtualSwitch" devices. The Control Layer acts as the PDP, the Data Layer as the PEP, and the Application Layer hosts the Trust Algorithm.
  - **Edge layer (§5.2):** "The proposed implementation adopts the Siemens Simatic IoT2050 as the reference industrial gateway." Arm TrustZone "has been selected as the underlying TEE supporting technology", and "The open-source OP-TEE framework … is instead adopted". The "Web Front-end is implemented using the Node-RED JavaScript framework".
  - **IAM:** "The SDN platform receives an authorization token from the IAM on its Nothbound APIs" (§5.1; spelling as in source).
- **Zero-Trust depth:** Two-stage control. The SDN network gates access to gateway services. The TEE-based gateway then gates edge resources.
  - "The decision to grant, deny, or revoke the access to the resource is taken by the Policy Engine (PE)" (§4).
  - At the gateway: "The Gateway-TEE checks for the compliance of the request with the security policies, and then authorizes the request." (§5.3).
  - Access is time-bounded: "The proposed solution limits access to a target network resource, and for a limited amount of time" (§5.3).
- **Device identity:** Not reported. No certificate, key, TPM, or TLS mechanism is described. The gateway "provides authentication" (§5.3), but no mechanism is given.
- **Workload identity:** Not reported.
- **Authorization/policy:** NIST roles (PE, PA, PEP, PDP, Trust Algorithm). Requests are checked against "the reference security policies" (§5.2). Network reconfiguration is driven by the IAM token, with "automatic reversion to the original configurations one that the remote access has terminated" (§5.1).
- **Payload integrity/signatures:** Not reported. Integrity appears only in requirement SR1 ("ensuring the confidentiality and integrity of the resource", §3.3) and in TEE integrity monitoring.
- **Provenance:** Not reported.
- **Lineage:** Not reported.
- **Replay treatment:** Not reported.
- **Duplicate treatment:** Not reported.
- **Event ordering:** Not reported.
- **Disconnected-edge recovery/buffering:** Not reported.
- **Raw/immutable preservation:** "TEE-based solutions can host secure storage and integrity monitoring services in the Secure World" … "guaranteeing tamper-proof logging" (§5.3). No mechanism is specified. SR4: "The solution shall provide robust logging guarantees, ensuring that a subject is properly traced … at all times while accessing a resource." (§3.3).
- **Credential revocation (manuscript topic):** No credential revocation mechanism is reported. The Cleanup phase "is in charge of reverting the network reconfiguration to the original state" (§5.3).
- **Threat model:** "the considered attackers are either insiders" or "cyber-criminals (well-equipped professionals with interests in industrial espionage or extortion)". The analysis uses STRIDE ("a security threat analysis is performed using the STRIDE methodology", §3.3). The requirements are SR1 least privilege, SR2 resilience to DoS, SR3 fine-grained access control, and SR4 robust logging (§3.3).
- **Implementation/technologies:** OpenFloodlight, OpenFlow, OpenVirtualSwitch, Siemens Simatic IoT2050, Arm TrustZone, OP-TEE, Node-RED, Linux, and a SysML model-based migration process (§4.1).
- **Testbed:** A demonstrator "developed in the context of the COLLABS EU project", "reproducing a real manufacturing infrastructure". It has "four network segments (public internet, enterprise, manufacturing, and shop floor)" and "around 40 network nodes (between services and equipment)" (§5). The connected-aircraft scenario was not implemented.
- **Baselines:** None (related work is compared only qualitatively).
- **Metrics/quantitative results:** None. Validation is qualitative and goes requirement by requirement (§5.3).
- **Stated limitations:** "One area of improvement for the current work is the evaluation of the performance, both in terms of throughput and in terms of energy efficiency" (§2). Future work (§6) covers additional intermediate authorization layers and automated generation and analysis of model-based configurations.

**RELEVANCE:** This paper is an IIoT Zero-Trust *access-control* architecture (SDN PDP/PEP plus a TEE gateway) for human remote-maintenance sessions. It overlaps with the manuscript on policy-based admission and edge enforcement. It does not address telemetry ingestion, per-event admission, payload signatures, provenance, replay or duplicates, or buffering. It also gives no performance data.

**FLAGS:** None bibliographic. Received, revised, and accepted dates were not visible in the retrieved text (not needed for the MDPI reference format).

---

## 2. Wang et al. (2025), Journal of Computer Research and Development (in Chinese)

- **KEY:** wang2025ztiiot
- **VERIFIED CITATION:** Wang, H.; Lü, F.; Cheng, Y.; Lü, S.; Sun, D.; Sun, L. Review of Zero Trust Security Research in Industrial Internet of Things. *Journal of Computer Research and Development* **2025**, *62*, 2784–2805. (In Chinese.) https://doi.org/10.7544/issn1000-1239.202440840
  - Chinese title (publisher page): 工业物联网零信任安全研究综述.
  - Journal (publisher meta): 计算机研究与发展, ISSN 1000-1239.
  - The ISO journal abbreviation is not shown on any fetched page. The publisher's `citation_journal_abbrev` is "jsjyjyfz", a pinyin code. The full journal name is used above. **[BIBLIOGRAPHIC VERIFICATION REQUIRED: abbreviation]**
- **BIBTEX:** Constructed by me from the publisher's `citation_*` / `dc.*` meta tags. DOI negotiation is not available: the DOI's registration agency is ISTIC, and `doi.org` returned HTML instead of BibTeX. Crossref returns 404 for this DOI.
```bibtex
% Chinese title: 工业物联网零信任安全研究综述 ; journal: 计算机研究与发展
@article{wang2025ztiiot,
  title   = {Review of Zero Trust Security Research in Industrial Internet of Things},
  author  = {Wang, Hangyu and L{\"u}, Fei and Cheng, Yuliang and L{\"u}, Shichao and Sun, Degang and Sun, Limin},
  journal = {Journal of Computer Research and Development},
  year    = {2025},
  volume  = {62},
  number  = {11},
  pages   = {2784--2805},
  issn    = {1000-1239},
  doi     = {10.7544/issn1000-1239.202440840},
  url     = {https://crad.ict.ac.cn/en/article/doi/10.7544/issn1000-1239.202440840},
  note    = {In Chinese}
}
```
- **TYPE:** Review/survey in a peer-reviewed journal. The section label on the page is "Network and Information Security".
- **Other verified details (PDF p. 2784):**
  - Affiliations:
    - Institute of Information Engineering, Chinese Academy of Sciences (CAS), Beijing
    - School of Cyber Security, University of CAS, Beijing
    - College of Artificial Intelligence, Shenyang Aerospace University, Shenyang
    - Computer Network Information Center, CAS, Beijing
  - Corresponding author: 吕飞 (Lü Fei).
  - Funding: "Beijing Natural Science Foundation (L234033)".
  - CLC TP393.08; CSTR 32373.14.issn1000-1239.202440840.
- **VERIFICATION SOURCES:**
  - WebSearch, exact title
  - `https://crad.ict.ac.cn/en/article/doi/10.7544/issn1000-1239.202440840` (WebFetch and shell, meta tags)
  - `https://crad.ict.ac.cn/cn/article/doi/10.7544/issn1000-1239.202440840` (shell, meta tags)
  - `https://doi.org/ra/10.7544/issn1000-1239.202440840` (RA = ISTIC)
  - `https://doi.org/api/handles/10.7544/issn1000-1239.202440840`
  - `https://doi.org/10.7544/issn1000-1239.202440840` (BibTeX negotiation; returned HTML)
  - `https://api.crossref.org/works/10.7544/issn1000-1239.202440840` (404)
  - `https://crad.ict.ac.cn/cn/article/pdf/preview/10.7544/issn1000-1239.202440840.pdf` (22-page PDF)
- **ACCESS LEVEL:** FULL TEXT (VoR PDF, Chinese).
  - Read closely: the introduction, §1.2–1.3, §2.1, §3.1–3.5, §6.1–6.3, and §7.
  - §4 (access control) and §5 (application scenarios) were checked by keyword search only.

**CONTENT**
- **Research problem:** A systematic review of zero trust in IIoT. It covers principles, ZTA migration and evaluation, key technologies (authentication, SDP, micro-segmentation, channel security, trust evaluation), access control, application scenarios, and challenges (English abstract).
- **Review method:** "本文基于Buck等人[7]提出的文献检索方法，对谷歌学术核心数据库中近5年的相关文献进行系统性整理和综述" [following Buck et al.'s retrieval method, the review covers the past 5 years of literature in the Google Scholar core database]. The selection is "具有代表性的理论及应用类文献（涵盖SCI和CCF-C及以上级别）" [representative theory and application papers, SCI or CCF-C and above] (Introduction, p. 2785). No counts of retrieved or included papers were seen in the examined text.
- **Domain:** IIoT in general. The scenarios are ICS, electric IoT, IoV, satellite IoT, and the semiconductor industry (§5).
- **Architecture:** A generic industrial ZTA (Fig. 2, §2.1). The PDP (PA + PE) sits in the control plane and the PEP in the data plane. The trust-evaluation inputs are industrial protocols, threat sources, "工控行为日志" [industrial-control behaviour logs], device state and environment, and industry rules.
- **Zero-Trust depth:** Survey level. The IIoT ZT principles (§1.2) include low latency, communication security ("确保信息传递的完整性和安全性" [ensure integrity and security of information transfer]), dynamic authorization, minimum security posture, and information recording ("需要详细记录设备的状态、历史行为及环境参数等信息" [record device state, history, and environmental parameters in detail], p. 2787).
- **Device identity:** "在IIoT环境中，设备常作为访问资源的主体" [in IIoT, devices are often the access subjects] (§3.1, p. 2790). The approaches reviewed are:
  - public-key and digital-signature authentication;
  - digital certificates carrying access-permission metadata (Zanasi et al. [34]; Chen et al. [35]);
  - MFA tokens stored on a blockchain (Daah et al. [40]);
  - physical characteristics as edge-device credentials (Ali et al. [41]);
  - PUF-based and SPDM-based chip-to-chip trust (semiconductor scenario).
- **Workload identity:** Not reported. The only related mention is an edge system that hosts workloads during testing (Buras et al. [123]).
- **Authorization/policy:** SDP models (client–gateway, client–server, client–gateway–client, server–server; §3.2). Trust evaluation is classed as condition-based, score-based, independent, or context-based (§3.5). §4 traces access control from early models through RBAC and ABAC to dynamic access control.
- **Credential revocation (manuscript topic):** §3.1(3), "零信任凭证撤销方案" [zero-trust credential revocation schemes]: "凭证撤销方案旨在解决令牌的有效期限问题" [revocation schemes address token validity periods]. Two examples:
  - Liu et al. [44] "采用可撤销群签名方案，将过期时间嵌入边缘设备的密钥中" [revocable group signatures embedding expiry into edge-device keys].
  - Rivera et al. [45] embed JSON Web Tokens as encrypted metadata in non-fungible tokens "以实现一次性令牌的固定期限撤销" [for fixed-term revocation of one-time tokens] (p. 2790).
- **Payload integrity/signatures:** Channel security (§3.4) is defined as protecting "数据的机密性和完整性，以防止信息泄露或篡改" [confidentiality and integrity, preventing leakage or tampering]. Mechanisms reviewed: TLS and mTLS ("mTLS是对TLS的拓展，通过双向认证提升了通信的安全性"), SM2/SM3/SM4 bidirectional SSL (Li et al. [38]), robust watermarking of datasets (Filip et al. [43]), and AEAD for semiconductor node data (Ahmed et al. [70]). No per-message telemetry signature scheme is discussed.
- **Provenance:** Not reported; there are no hits for 溯源 or 血缘. The closest item is dataset-fingerprint authentication using locality-sensitive hashing (Filip et al. [43]).
- **Lineage:** Not reported.
- **Replay treatment:** Not reported (no hits for 重放).
- **Duplicate treatment:** Not reported. "减少重复认证" refers to repeated *authentication*, not duplicate data.
- **Event ordering:** Not reported.
- **Disconnected-edge recovery/buffering:** Not reported. Caching is discussed only for short-term *authentication* state: "动态访问控制可通过本地缓存和预认证机制减少延迟" [local caching and pre-authentication reduce latency] (§6.2, p. 2799).
- **Raw/immutable preservation:** Not reported. Blockchain appears only for MFA tokens, trust factors, and resource information.
- **Threat model:** Not a formal model; this is a review.
- **Implementation/testbed/baselines:** Not applicable (review).
- **Metrics/quantitative results:** No quantitative synthesis. Table 4 lists deployment problems, including time overhead ("ZTA保护系统时产生大量时间开销", p. 2799).
- **Stated limitations and challenges (§6.1–6.3, §7):**
  - The feasibility of ZT is questioned because of implicit trust zones such as PDPs, human decision-makers, and trust algorithms (Michael et al. [126]).
  - Legacy migration is costly.
  - ZT in power grids "可能会导致延迟，甚至阻碍控制系统获取关键信息" [may cause delays, even hinder control systems from obtaining key information] (Swearingen et al. [128], p. 2798).
  - Multi-PDP decisions add delay.
  - Incremental deployment can produce "ZTA孤岛" [ZTA islands].
  - Future directions: AI (privacy, compute, explainability), cryptography (post-quantum, compute burden), and IIoT heterogeneity and real-time trade-offs.
  - §7: existing models "在应对复杂异构网络、高实时性需求和资源受限设备等方面仍面临诸多挑战" [still face many challenges with heterogeneous networks, real-time needs, and resource-constrained devices].
- **Cross-links:** It cites Federici et al. as [23], with the URL mdpi.com/2079-9292/12/3/566 (= source 1), and cites Zanasi et al.

**RELEVANCE:** The most recent IIoT-specific ZT survey in this set. It is useful to support the claim that IIoT ZT work concentrates on authentication, SDP, micro-segmentation, and trust scoring. Its examined text has nothing on data provenance, per-event admission, replay or duplicate handling, or edge buffering, which supports the manuscript's gap statement.

**FLAGS:**
- The journal abbreviation is unverified **[BIBLIOGRAPHIC VERIFICATION REQUIRED]**.
- The article is in Chinese, which the manuscript should state.
- The DOI is ISTIC-registered and not in Crossref, so reference-checking tools may flag it. The DOI does resolve to the publisher page.

---

## 3. Zhang et al. (2026), Applied Sciences ("publisher dates conflict" claim)

- **KEY:** zhang2026lztaka
- **VERIFIED CITATION:** Zhang, X.; Mu, Z.; Mu, D.; Liu, X. A Lightweight Zero-Trust Authentication and Key Agreement Scheme for the Industrial Internet of Things. *Appl. Sci.* **2026**, *16*, 6765. https://doi.org/10.3390/app16136765
  - The MDPI page's citation line reads "Appl. Sci. 2026, 16(13), 6765".
- **BIBTEX** (doi.org negotiation; only the key was changed):
```bibtex
@article{zhang2026lztaka, title={A Lightweight Zero-Trust Authentication and Key Agreement Scheme for the Industrial Internet of Things}, volume={16}, ISSN={2076-3417}, url={http://dx.doi.org/10.3390/app16136765}, DOI={10.3390/app16136765}, number={13}, journal={Applied Sciences}, publisher={MDPI AG}, author={Zhang, Xun and Mu, Zhiying and Mu, Dejun and Liu, Xin}, year={2026}, month=July, pages={6765} }
```
- **TYPE:** Peer-reviewed journal article. MDPI section "Article"; Special Issue "Security, Privacy and Application in New Intelligence Techniques: 2nd Edition".
- **Other verified details:**
  - Affiliations (MDPI page): X. Zhang, Z. Mu (corresponding), and D. Mu are at the School of Cybersecurity, Northwestern Polytechnical University, Xi'an. X. Liu is at the School of Information Science & Engineering, Lanzhou University.
  - Funders (Crossref): National Natural Science Foundation of China, awards 62372069 and 62272389.
- **DATES (every date found):** see the date table in §0. In summary, all sources agree on **6 July 2026**:
  - MDPI page, MDPI meta tags, Crossref (created, published-online, issued), OpenAlex, and Semantic Scholar all give 6 July 2026 as the online date.
  - The issue is "2026 July-1" (Vol. 16, Issue 13).
  - Crossref has no print date. Its journal-issue date is 2026-07, month only.
  - MDPI Version Notes: VoR PDF uploaded 6 July 2026; HTML **updated 4 September 2026** ("Update").
  - Received, revised, and accepted dates were **not found** in any retrieved text.
  - **I could not reproduce a conflict among publisher or registry dates.** I did not resolve the question further.
- **VERIFICATION SOURCES:**
  - Crossref title search; `https://api.crossref.org/works/10.3390/app16136765`
  - `https://doi.org/10.3390/app16136765` (BibTeX)
  - `https://www.mdpi.com/2076-3417/16/13/6765` (WebFetch ×2)
  - `…/6765/htm` (WebFetch ×3, including offset)
  - `…/6765/notes`
  - `https://www.mdpi.com/2076-3417/16/13` (issue table of contents)
  - `…/6765/pdf` (binary, unreadable)
  - `…/6765/xml` (bot check)
  - `https://api.openalex.org/works/doi:10.3390/app16136765`
  - `https://api.semanticscholar.org/graph/v1/paper/DOI:10.3390/app16136765`
- **ACCESS LEVEL:** PARTIAL FULL TEXT (VoR HTML in its post-4-September-2026 state). §1–§5.6 and the first paragraph of §6 (Discussion) were read. The rest of §6, §7 (Conclusions), the appendices, and the Table 8 and Table 9 images were **not examined**: the HTML conversion stopped at about 105k characters, and the PDF and XML could not be read.

**CONTENT**
- **Research problem:** Per the abstract, existing IIoT authentication schemes verify identity and set up session keys but give little support to zero-trust access decisions after authentication. The proposed scheme embeds role-, device-, environment-, and behaviour-aware control points in the authentication flow.
- **Domain:** IIoT. Industrial users (engineers, operators, technicians), an industrial gateway node (GWN), and field devices.
- **Architecture:** Users hold a smart card, a password, and a fingerprint. The GWN keeps relation tables and operator–asset mappings inside a TEE using secGear. The other entities are field devices, an access proxy, a bypass policy engine with an optional auxiliary risk module, and an enrollment terminal for out-of-band registration.
- **Zero-Trust depth:** Role, device, environment, and behaviour checks are part of the authentication flow (§4.1). The risk module supplies evidence for "re-verification, privilege degradation, audit escalation, or session termination" (Abstract). Break-the-glass emergency access is supported.
- **Device identity:** Keys and pseudonyms, for example TC_j = h(ID_j ∥ R_j), PID_j = h(ID_j ∥ K_GWN), and a per-session HMAC pseudonym (§4.4–4.5). No PUF.
- **Workload identity:** Not reported.
- **Authorization/policy:** Role-based operation lists, device risk levels, environment attributes (login time, process area, terminal type, MAC address), and a behaviour anomaly score. Operator–asset mappings stay inside the enclave.
- **Payload integrity/signatures:** These are at handshake and session level only: "The GWN replies with r 2 together with an SM2 signature on ( r 1 , r 2 )" (§4.5), plus MAC tags. No signatures on telemetry payloads are reported.
- **Provenance:** Not reported.
- **Lineage:** Not reported.
- **Replay treatment (security replay):**
  - Adversary model: "an adversary can eavesdrop, replay, delete, and modify public-channel messages" (§3.2).
  - Mechanism: "replayed messages fail timestamp and MAC checks" (§4.7), using timestamps T1–T4 and fresh nonces.
  - §5.2 has a subsection titled "Replay, tampering, and freshness".
  - Claimed scope: "supporting resistance to replay and man-in-the-middle attacks at the cryptographic protocol layer" (§5.1).
- **Duplicate treatment:** Not reported.
- **Event ordering:** Not reported.
- **Disconnected-edge recovery/buffering:** Not reported.
- **Raw/immutable preservation:** Not reported. An audit log is appended to (Algorithm 1), "all emergency operations are logged for post hoc audit" (§4.1), and "Emergency access follows a stricter audit model rather than a stricter blocking model" (§4.7).
- **Credential revocation (manuscript topic):** §4.8, "Key Management and Revocation": "Revocation is a local enclave operation and does not require contacting the field devices."
  - User revocation: "To revoke a user, the gateway deletes the user’s entries from the enclave-stored relation tables".
  - Device revocation: "To revoke a device, the gateway deletes its record from G W D L I S T".
- **Threat model:** "We adopt the Dolev–Yao model" (§3.2). It also covers a privileged insider exfiltrating relation tables or mappings from the GWN, gateway malware, and coerced login. "Attacks against the TEE hardware itself are outside the scope of this paper." (§3.2).
- **Implementation/technologies:** secGear confidential computing, SM2, HMAC, and AES-GCM, with an LSTM-64 behaviour model. Formal verification: BAN logic (goals G1–G4) and AVISPA (OFMC and CL-AtSe returned SAFE, Fig. 3).
- **Testbed:** None measured. Latency figures are "representative benchmark-level estimates for the architectures rather than measured per-platform figures" (§4.2). The cost basis is mobile operator terminals and MICAz-class devices (Table 7).
- **Baselines:** Li et al. [7], Xiong et al. [8], Das et al. [9], and Vinoth et al. [10]. §5.6 compares against EDHOC, DTLS 1.3, and Noise, but this is "a positioning comparison, not a same-hardware, same-implementation, same-network head-to-head benchmark".
- **Metrics and results (§5.3):**
  - "The proposed scheme totals 87.3 ms".
  - "its field device cost is 3 T H = 24 ms".
  - "The communication overhead is 1216 bits, the lowest among the compared schemes". The text gives Das et al. 1536, Xiong et al. 2208, Li et al. 2720, and Vinoth et al. 3040 bits.
  - "The scheme storage overhead is 1152 bits across U, GWN, and FD".
- **Stated limitations:**
  - The default configuration "should not be interpreted as a plant-ready coercion detector" (§4.2).
  - "It does not prove that the auxiliary risk evaluation module detects every coerced login" (§5.1).
  - The §5.5 analysis "is not an operational detection performance claim".
  - End-to-end measurement on edge hardware is left to future work.

**RELEVANCE:** This is a session-level ZT authentication and key-agreement protocol for IIoT with nonce and timestamp replay resistance and enclave-local revocation. It is relevant to the manuscript's identity, admission, and revocation thread. It does not deal with per-event ingestion, payload provenance, duplicates or retries, ordering, or buffering, and its costs are analytic estimates.

**FLAGS:**
- **[BIBLIOGRAPHIC VERIFICATION REQUIRED]:** the "conflicting publisher dates" mentioned in the research note could not be reproduced. Every source I fetched gives 6 July 2026 (issue "2026 July-1"). Please identify which source showed the conflicting date. Two candidates: the MDPI HTML "Update" of 4 September 2026, or the month-only issue date 2026-07.
- Received, revised, and accepted dates are unknown.
- The content was read from the HTML version updated on 4 September 2026, not from the 6 July 2026 VoR PDF. Quotes should be re-checked against the PDF before citing.

---

## 4. Faraj, Megías, Garcia-Alfaro (2025), ACM Computing Surveys

- **KEY:** faraj2025provslr
- **VERIFIED CITATION:** Faraj, O.; Megias, D.; Garcia-Alfaro, J. Security Approaches for Data Provenance in the Internet of Things: A Systematic Literature Review. *ACM Comput. Surv.* **2025**, *57*, 1–41. https://doi.org/10.1145/3718735
  - The abbreviation "ACM Comput. Surv." is Crossref's `short-container-title`.
  - The second author appears as "Megías" in the arXiv v2 running head and in OpenAlex, and as "Megias" in the Crossref deposit.
  - The IP Paris research portal gives the **article number as 261**. This is **not confirmed** by Crossref, which has pages "1-41" and no article number, and the ACM page could not be reached. **[BIBLIOGRAPHIC VERIFICATION REQUIRED: article number; ACM format would be "57, 261"]**
- **BIBTEX** (doi.org negotiation; key changed; one correction):
```bibtex
@article{faraj2025provslr, title={Security Approaches for Data Provenance in the Internet of Things: A Systematic Literature Review}, volume={57}, ISSN={1557-7341}, url={http://dx.doi.org/10.1145/3718735}, DOI={10.1145/3718735}, number={10}, journal={ACM Computing Surveys}, publisher={Association for Computing Machinery (ACM)}, author={Faraj, Omair and Megias, David and Garcia-Alfaro, Joaquin}, year={2025}, month=May, pages={1–41} }
```
  - Correction: the negotiated entry has `Garcia-alfaro` (casing error in the deposit), changed to `Garcia-Alfaro` to match the arXiv author list.
  - The `pages` field contains a Unicode en dash as negotiated; `--` may be needed for classic BibTeX.
- **TYPE:** Review/survey (systematic literature review) in a peer-reviewed journal. Crossref licence: CC BY 4.0 (VoR).
- **Other verified details:**
  - Affiliations (Crossref): IN3, Universitat Oberta de Catalunya (UOC), CYBERCAT, Barcelona, and SAMOVAR, Télécom SudParis, Institut Polytechnique de Paris (Faraj, Megias); SAMOVAR, Télécom SudParis (Garcia-Alfaro).
  - Dates: see §0 (received 2024-05-24; accepted 2025-02-13; online 2025-05-08; issue 2025-10-31).
- **VERIFICATION SOURCES:**
  - Crossref search and `https://api.crossref.org/works/10.1145/3718735`
  - `https://doi.org/10.1145/3718735` (BibTeX)
  - `https://dl.acm.org/doi/10.1145/3718735` and `…/doi/pdf/10.1145/3718735` (both failed)
  - `https://export.arxiv.org/api/query?id_list=2407.03466`
  - `https://arxiv.org/html/2407.03466v2` (WebFetch ×2)
  - `https://arxiv.org/pdf/2407.03466v2` (40-page PDF, full text)
  - `https://api.openalex.org/works/doi:10.1145/3718735`
  - `https://hal.science/hal-05033850` (bot-blocked)
  - `https://recerca.uoc.edu/documentos/6880a3bf3871d04c4eb499e0?lang=en`
  - `https://researchportal.ip-paris.fr/en/publications/security-approaches-for-data-provenance-in-the-internet-of-things/`
- **ACCESS LEVEL:** FULL TEXT (preprint): arXiv v2 (updated 2024-11-02; comment "40 pages (35+5), 16 tables, 8 figures"), read in full. The ACM VoR (accepted 2025-02-13) was not accessed.

**CONTENT** (from arXiv v2)
- **Research problem:** A systematic review of security techniques for data provenance in IoT. RQ1–RQ6 cover how provenance links to IoT; storage techniques, attacks, and requirements; how to categorize the approaches; implementations; advantages and limitations; and research gaps (§2.1, §10).
- **Method (§2.4, Fig. 2):** Kitchenham-based SLR. Sources: IEEEXplore, ScienceDirect, Scopus, Web of Science, ACM DL, and Springer Link. Studies from 2013–2023, plus two highly cited older papers.
  - The search led "to a total of 2706 papers".
  - Screening reduced "the number of relevant papers to 107".
  - Full-text analysis led to "the exclusion of 67 papers".
  - Final set: "Selected studies for reviewing - 40 papers".
- **Domain:** IoT and wireless sensor networks.
- **Definitions:** Provenance is "the process of recording the history of data origin, evolution, and activities", "also known as lineage [142]" (§1). "In database systems, provenance was traditionally referred to as lineage" (§3.2).
- **Taxonomy:** "Cryptography-based, Digital Watermarking, Bloom filters, Physical Unclonable Functions, Fingerprints, Blockchain-based, Frameworks with storing methods, Data Santization [sic], Lexical chaining, Graph-based, Path difference and Logging-based" (§3.4).
- **Architecture / Zero-Trust depth / device identity / workload identity / authorization:** Not reported as Zero Trust. The review covers techniques such as PUF-based device authentication among the reviewed works.
- **Payload integrity/signatures:** Integrity, unforgeability, and non-repudiation appear as requirements (§3.5). Cryptography-based techniques are reviewed (Table 10). "none of the selected papers in the systematic literature review satisfy all of the security requirements" (§3.5).
- **Provenance and lineage:** This is the core topic of the paper.
  - Storage options: local database, in-packet, blockchain, cloud (§4).
  - Size: "the provenance associated with data of size 270 MB amounts to approximately 6 GB in size [78]" (§4).
  - "provenance records in large-scale systems typically exceed the size of the actual data when processed and transmitted" (§8).
- **Replay treatment (security replay):**
  - Freshness: "no adversary can replay previous information to deceive a gateway or base station" (§3.5).
  - Packet replay attack: "The attacker then replays or re-sends these recorded packets at a later time, attempting to deceive the system into thinking the information is fresh and legitimate." (§5.1).
  - Provenance replay attack: "replaying a previously recorded provenance record at a later point, thereby manipulating the integrity of the provenance chain" (§5.2).
  - Reviewed works "tend to overlook other significant attack vectors such as replay attacks, packet drop, and provenance chain tampering" (§5.2).
- **Duplicate treatment:** Not reported for data. Duplicates are mentioned only in the review's own exclusion criterion EC6.
- **Event ordering:** Provenance chain tampering means altering "the order of this chain and modify its contents" (§5.2). "almost all the proposed methods do not consider chain tampering" (§9.2).
- **Disconnected-edge recovery/buffering:** Not reported.
- **Raw/immutable preservation:** On blockchain: "Once recorded on the blockchain, these records cannot be altered or removed." The open issues include "The storage of blockchain is expensive" (§9.2).
- **Threat model:** A taxonomy of data attacks (packet drop, packet replay, forgery, modification, eavesdrop) and provenance attacks (record drop, replay, forging/append, modification, chain tampering, inference) (§5).
- **Implementation/testbed/baselines:** Not applicable (review). "the majority of studies predominantly use simulation-based approaches" (§8, Table 13).
- **Metrics:** Table 14 lists the metrics used across studies. "most existing studies focus primarily on a limited subset of these, typically provenance length, energy consumption, and computation time" (§8).
- **Open issues (§9.2):**
  - privacy of blockchain-stored provenance;
  - the narrow range of attacks studied;
  - watermarking (only one work);
  - "Lack of complete provenance management system and narrow focus";
  - lack of efficient query support;
  - expensive blockchain storage;
  - integrating provenance with IDS.
- **Stated limitations:** The examined arXiv v2 text has no separate threats-to-validity section. Design constraints include English-only studies (EC4) and search on titles, abstracts, and keywords only.

**RELEVANCE:** The main recent survey on securing provenance in IoT, and the best support for the manuscript's provenance, replay, and chain-tampering threat categories and for "provenance larger than data". It is network/WSN-centric and has no ingestion-pipeline, ZT-admission, duplicate/retry, or disconnected-edge treatment.

**FLAGS:**
- **[BIBLIOGRAPHIC VERIFICATION REQUIRED]:** article number 261 (one portal only) and the "Megías"/"Megias" spelling.
- The content is from the preprint. Re-check quotes against the ACM VoR (CC BY, open access per Crossref and OpenAlex) before citing specific sentences.
- The online date is inconsistent across indexes (2025-02-19 at OpenAlex, which equals the Crossref created date; 2025-05-08 at Crossref; an "08/08" meta date on the IP Paris portal).

---

## 5. Sigwart et al. (2019), ACM IoT 2019

- **KEY:** sigwart2019bcprov
- **VERIFIED CITATION:** Sigwart, M.; Borkowski, M.; Peise, M.; Schulte, S.; Tai, S. Blockchain-based Data Provenance for the Internet of Things. In *Proceedings of the 9th International Conference on the Internet of Things (IoT 2019)*, Bilbao, Spain, 22–25 October 2019; ACM: New York, NY, USA, 2019; pp. 1–8. https://doi.org/10.1145/3365871.3365886
  - Location and publisher location come from Crossref (`event.location` "Bilbao Spain"; `publisher-location` "New York, NY, USA").
  - The conference dates "October 22–25" come from the arXiv PDF footer "IOT’19, October 22–25, Bilbao, Spain".
- **BIBTEX** (doi.org negotiation; key changed):
```bibtex
@inproceedings{sigwart2019bcprov, series={IoT 2019}, title={Blockchain-based Data Provenance for the Internet of Things}, url={http://dx.doi.org/10.1145/3365871.3365886}, DOI={10.1145/3365871.3365886}, booktitle={Proceedings of the 9th International Conference on the Internet of Things}, publisher={ACM}, author={Sigwart, Marten and Borkowski, Michael and Peise, Marco and Schulte, Stefan and Tai, Stefan}, year={2019}, month=Oct, pages={1–8}, collection={IoT 2019} }
```
- **TYPE:** Conference paper (peer-reviewed proceedings, ACM).
- **Affiliations (arXiv PDF):** TU Wien (Sigwart, Borkowski, Schulte); TU Berlin (Peise, Tai).
- **VERIFICATION SOURCES:**
  - Crossref search and `https://api.crossref.org/works/10.1145/3365871.3365886`
  - `https://doi.org/10.1145/3365871.3365886` (BibTeX)
  - `https://api.openalex.org/works/doi:10.1145/3365871.3365886`
  - `https://export.arxiv.org/api/query?id_list=1905.06852`
  - `https://arxiv.org/pdf/1905.06852` (v2, 8 pages)
- **ACCESS LEVEL:** FULL TEXT (preprint): arXiv v2 of 2019-08-06, the submitted version. Its ACM Reference Format block still shows a placeholder DOI. The ACM VoR was not accessed.

**CONTENT**
- **Research problem:** Per the abstract, "current solutions do not address the heterogeneous nature of IoT applications and their data". The paper proposes a generic blockchain-based provenance framework.
- **Domain:** Generic IoT, illustrated with a vaccine cold chain and health monitoring (§2).
- **Architecture:** Three layers "all embedded within a blockchain smart contract platform": a storage layer, a generic provenance layer, and a specific provenance layer (Fig. 1, §4).
  - The data model follows Olufowobi et al.: prov(dp) = ⟨addr(dp), {prov(idp)}, context(dp)⟩.
  - Code is open source at `github.com/msigwart/iotprovenance` (per the paper).
- **Zero-Trust depth:** Not reported.
- **Device identity:** Not reported as device identity. Data points are ERC-721 tokens, and "only the owner or a client authorised by the owner can create provenance records for it" (§4).
- **Workload identity:** Not reported.
- **Authorization/policy:** Token ownership. Specific contracts choose which API parts to expose, and whitelists or purchased tokens are discussed (§4).
- **Payload integrity/signatures:** "once records have entered the system, the integrity of records depends on the underlying blockchain technology". However, "the framework also needs to provide mechanisms to ensure only correct records enter the system in the first place", which is left to future work (§5, Req. 8).
- **Provenance:** This is the core topic. Functional requirements Req. 1–7 cover abstraction, high- and low-level provenance, completeness, lineage, derivation, modifications, and parallel provenance.
- **Lineage:** "Provenance records for a data point can be created based on the last provenance record for that same data point. This enables the creation of lineage." (Req. 4, §3).
- **Replay treatment:** Not reported.
- **Duplicate treatment:** Not reported.
- **Event ordering:** Not reported. Ordering is implicit only through record chaining.
- **Disconnected-edge recovery/buffering:** Not reported.
- **Raw/immutable preservation:** "Delete refers to the invalidation of provenance records, since truly deleting data from a blockchain is not possible." (§4). Raw data storage is not discussed.
- **Threat model:** Not reported as a formal model.
- **Implementation/technologies:** Ethereum smart contracts (Solidity) and ERC-721.
- **Testbed:** "public Ethereum test networks Rinkeby and Ropsten" (§5).
- **Baselines:** None.
- **Metrics/results (§5, Fig. 2):**
  - Throughput: "we submit up to 150 transactions to the test network during a 60 second time frame"; result "an average throughput of only 1-1.6 TPS".
  - Latency: "the average latency converges to the average block time (∼14-30 seconds)".
  - Context: "The maximum global throughput of the Ethereum blockchain is roughly 20 TPS". Throughput "was measured from a user perspective, i.e., transactions were submitted from a single account".
- **Stated limitations:** "Regarding scalability and privacy, the use of blockchain technology poses limitations." (§5). Future work is to evaluate state channels, zero-knowledge proofs, and sidechains (§7).

**RELEVANCE:** A canonical reference for ledger-anchored IoT provenance and lineage. It is the counterpoint that motivates a lightweight, non-blockchain provenance binding at ingestion: its throughput is 1–1.6 TPS, and it explicitly leaves admission-time correctness of records unsolved. It does not address replay, duplicates, ordering, or edge buffering.

**FLAGS:** The content is from the preprint (arXiv v2), so verify quotes against the ACM VoR. Faraj et al. (source 4) cite this paper as [128].

---

## 6. Kovach et al. (2024), ACM eSAAM 2024

- **KEY:** kovach2024sovereign
- **VERIFIED CITATION:** Kovach, A.; Lanza, J.; Montalvillo, L.; Urbieta, A. Sovereign IIoT Data Exchange Using DAG-Based DLT and International Data Spaces Architecture. In *Proceedings of the 4th Eclipse Security, AI, Architecture and Modelling Conference on Data Space (eSAAM 2024)*, Mainz, Germany, [conference dates **BIBLIOGRAPHIC VERIFICATION REQUIRED**]; ACM: New York, NY, USA, 2024; pp. 76–85. https://doi.org/10.1145/3685651.3686658
  - Crossref `event`: name "eSAAM 2024: 4th Eclipse Security, AI, Architecture and Modelling Conference on Data Space", location "Mainz Germany". The record has no event dates.
- **BIBTEX** (doi.org negotiation; key changed):
```bibtex
@inproceedings{kovach2024sovereign, series={eSAAM 2024}, title={Sovereign IIoT Data Exchange Using DAG-Based DLT and International Data Spaces Architecture}, url={http://dx.doi.org/10.1145/3685651.3686658}, DOI={10.1145/3685651.3686658}, booktitle={Proceedings of the 4th Eclipse Security, AI, Architecture and Modelling Conference on Data Space}, publisher={ACM}, author={Kovach, Anhelina and Lanza, Jorge and Montalvillo, Leticia and Urbieta, Aitor}, year={2024}, month=Oct, pages={76–85}, collection={eSAAM 2024} }
```
- **TYPE:** Conference paper (ACM proceedings). The Crossref VoR licence is CC BY 4.0.
- **Affiliations (Crossref):** Ikerlan Technology Research Centre, Basque Research and Technology Alliance (Kovach, Montalvillo, Urbieta); Network Planning and Mobile Communications Laboratory, University of Cantabria (Lanza).
- **VERIFICATION SOURCES:**
  - Crossref search and `https://api.crossref.org/works/10.1145/3685651.3686658` (no abstract deposited)
  - `https://doi.org/10.1145/3685651.3686658` (BibTeX)
  - `https://api.openalex.org/works/doi:10.1145/3685651.3686658` (abstract inverted index)
  - `https://hdl.handle.net/api/handles/10902/34512`, which resolves to `https://repositorio.unican.es/handle/10902/34512` (TLS failure from the shell; robots-disallowed for WebFetch)
  - `https://dl.acm.org/doi/10.1145/3685651.3686658` (HTTP 403)
  - WebSearch; `https://publica.fraunhofer.de/handle/publica/417354` (bot-blocked); `https://idus.us.es/handle/11441/160035` (a different paper; see FLAGS)
  - Semantic Scholar API (429)
- **ACCESS LEVEL:** METADATA ONLY, plus an **index-supplied abstract** (OpenAlex). The abstract was not seen on the ACM page.

**CONTENT**
- **Abstract (as indexed by OpenAlex, reconstructed from its inverted index; not verified against the publisher):** "Securing interoperable and sovereign data exchange in the Industrial Internet of Things (IIoT) for machine data exploitation by third parties presents a significant challenge. This work addresses this by integrating IOTA Distributed Ledger Technology (DLT) with the International Data Spaces (IDS) Reference Architecture Model (RAM), creating a decentralized data space optimized for IIoT ecosystems. This research demonstrates the practical implementation of core IDS architectural concepts within the IOTA framework, overcoming theoretical DLT limitations and showcasing IOTA’s capability to enhance data sovereignty and interoperability in the IIoT, moving beyond traditional blockchains, which are constrained by scalability and efficiency issues. It sets the stage for future evaluations and broader applicability studies, paving the way for advancements in secure, sovereign, interoperable, and efficient data management."
- **Research problem / domain:** Per the index abstract only: sovereign IIoT data exchange with third parties, using IOTA (DAG-based DLT) and the IDS RAM.
- Architecture; Zero-Trust depth; device identity; workload identity; authorization/policy; payload integrity/signatures; provenance; lineage; replay treatment; duplicate treatment; event ordering; disconnected-edge recovery/buffering; raw/immutable preservation; threat model; implementation/technologies; testbed; baselines; metrics; stated limitations: **Not examined (no full text).** The index abstract suggests no quantitative evaluation ("sets the stage for future evaluations"), but this was not verified in the paper.

**RELEVANCE:** Probably relevant to the manuscript's data-sovereignty and DLT-anchored-integrity context for IIoT data exchange. Because the paper itself was not read, no claim about it should go beyond the bibliographic record.

**FLAGS:**
- **[SOURCE REQUIRED]:** obtain the full text (the CC BY VoR on ACM DL, or UCrea handle 10902/34512) before citing any content.
- Conference dates are unverified.
- Overlap warning: the index abstract's opening ("Securing interoperable and sovereign data exchange in the Industrial Internet of Things (IIoT)") matches the opening of a *different* paper by the same authors: "IOTA-Enabled Decentralized Data Space for IIoT Ecosystems" (JNIC 2024, Sevilla, pp. 214–221, ISBN 978-84-09-62140-8, per idus.us.es). Do not conflate the two papers.

---

## 7. Asad et al. (2026), Systems: "replay" means dataset replay

- **KEY:** asad2026replaypdm
- **VERIFIED CITATION:** Asad, M.; Alhasawi, Y.; Alghamdi, S.; Bakry, D.S.; Rejeb, A. A Replay-Based Big Data Framework for Predictive Maintenance in Industrial IoT. *Systems* **2026**, *14*, 1255. https://doi.org/10.3390/systems14101255
- **BIBTEX** (doi.org negotiation; key changed):
```bibtex
@article{asad2026replaypdm, title={A Replay-Based Big Data Framework for Predictive Maintenance in Industrial IoT}, volume={14}, ISSN={2079-8954}, url={http://dx.doi.org/10.3390/systems14101255}, DOI={10.3390/systems14101255}, number={10}, journal={Systems}, publisher={MDPI AG}, author={Asad, Muhammad and Alhasawi, Yaser and Alghamdi, Salem and Bakry, Dana Sami and Rejeb, Abderahman}, year={2026}, month=Oct, pages={1255} }
```
- **TYPE:** Peer-reviewed journal article.
- **Affiliations (Crossref):**
  - University of Plymouth, UK (Asad)
  - King Abdulaziz University, Jeddah (Alhasawi, Bakry)
  - Institute of Public Administration, Riyadh (Alghamdi)
  - Széchenyi István University, Győr (Rejeb)
- **VERIFICATION SOURCES:**
  - Crossref search and `https://api.crossref.org/works/10.3390/systems14101255`
  - `https://doi.org/10.3390/systems14101255` (BibTeX)
  - `https://www.mdpi.com/2079-8954/14/10/1255/htm` (WebFetch ×4, including offset 100000)
- **ACCESS LEVEL:** FULL TEXT (VoR HTML, 112,619 characters; both portions examined). Table images (e.g., Tables 6, 9, 11) were not readable; their values were taken from the prose where available.

**CONTENT**
- **Meaning of "replay":** Replaying a **static historical dataset as a simulated stream**, not security replay.
  - "Since the original CMAPSS dataset is static, we simulate a real-time industrial environment by replaying the dataset" (§4.3).
  - "The producer controls the replay rate to emulate different workload levels" (§3.2).
  - The experiments used "a controlled replay-based Kafka–Spark environment" (§4.4).
  - No security replay analysis appears; there are no hits for "security".
- **Research problem:** A scalable Kafka–Spark streaming pipeline for predictive maintenance, evaluated under controlled replay load.
- **Domain:** IIoT predictive maintenance (turbofan engines, NASA C-MAPSS FD001).
- **Architecture:** Edge gateways send data over MQTT to Apache Kafka, then to Spark Streaming and an LSTM, with Grafana dashboards and Docker. "Kafka acts as a distributed buffer, ensuring decoupling between data producers" (§3.1). "Each Kafka message includes a key, value, and timestamp" (§3.2). Each partition "is replicated R times across brokers to guard against node failures" (§3.2).
- **Zero-Trust depth / device identity / workload identity / authorization / payload integrity / provenance / lineage:** Not reported. There are no hits for security, authentication, encryption, provenance, or integrity.
- **Replay treatment (security sense):** Not reported.
- **Duplicate treatment:** Not reported (no hits for duplicate or idempotent).
- **Event ordering:** Not reported beyond Kafka's ordered partitions. No late or out-of-order handling.
- **Exactly-once:** Spark "provides exactly-once processing semantics" (§3.3). This is stated as a framework property and not tested.
- **Disconnected-edge recovery/buffering:** Not reported. Kafka is described only as a decoupling buffer, and no failure or recovery tests were run.
- **Raw/immutable preservation:** Not reported. Preprocessing is done offline before replay (§4.2).
- **Threat model:** Not reported.
- **Implementation/technologies (Table 2, §4.4):** "Apache Kafka 3.6.1", "1 broker", "4 partitions", "Apache Spark 3.5.0", TensorFlow/Keras, and "8-core Intel Core i7 CPU, 16 GB RAM, CPU-based inference". The model is a two-layer LSTM (64 units).
- **Testbed:** A single machine. Replay reached "up to one million sensor events per minute" (§4.3), and the evaluation went up to 1.2 million events/min.
- **Baselines (§6.4, Table 7):** "the rule-based model performed the weakest, achieving an accuracy of 71.2% and a relatively low recall of 62.1%." "The Random Forest model … reached an accuracy of 82.1% with an F1-score of 79.5%."
- **Metrics and results:**
  - Classification (§6.1): "accuracy of 90.4%, with strong precision and recall values of 89.2% and 87.6%"; "F1-score of 88.4%"; "The average processing latency was measured at 412 milliseconds".
  - ROC (§6.5): "The AUC score is 0.942".
  - Latency under load (§6.3): "At an input rate of 100,000 events/min, the observed post-Spark prediction-stage latency was 290 milliseconds"; "At 500,000 events/min … 415 milliseconds"; "at 1.2 million events/min it reached 570 milliseconds".
  - Resources (§6.7, Table 10): "28.5% of CPU and 540 MB of memory" at 100,000 events/min; "42.3% and memory usage to 688 MB" at 500,000; "CPU usage increased to 63.7%, memory usage reached 872 MB" at 1.2 million.
  - The latency "does not include Kafka ingestion/queueing or Spark micro-batch scheduling and processing time" (§7.4).
- **Stated limitations:**
  - A single controlled run.
  - "the original Spark micro-batch interval was not retained in the experimental logs" (§7.4).
  - Horizontal scaling was not tested.
  - Offline training only.
  - Simulation, not evidence of deployment readiness.
  - Future work: end-to-end latency instrumentation, scaling tests, edge deployment, XAI, and federated learning (§8).

**RELEVANCE:** Useful mainly to disambiguate terminology. "Replay" here means dataset re-streaming, which the manuscript should keep distinct from security replay and from retry/redelivery. It is also an example of an IIoT Kafka–Spark ingestion pipeline with no identity, provenance, or duplicate/ordering controls.

**FLAGS:**
- Possibly related preprint, relationship not verified: Research Square, "A Scalable Big Data Framework for Real-Time Predictive Maintenance in Industrial IoT", 10.21203/rs.3.rs-7330045/v1, posted 2026-01-20. Crossref lists the authors as "Aasad, Muhammad; Alhasawi, Yaser; Rejeb, Abderahman".
- Only the main text was checked for keywords. Tables 9 and 11 were not readable as images.

---

## 8. Lezzi et al. (2025 online / 2026 issue), Management Review Quarterly

- **KEY:** lezzi2025cyberres
- **VERIFIED CITATION:** Lezzi, M.; Corallo, A.; Lazoi, M.; Nimis, A. Measuring cyber resilience in industrial IoT: a systematic literature review. *Manag. Rev. Q.* **2026**, *76*, 1107–1161. https://doi.org/10.1007/s11301-025-00495-8
  - The abbreviation is from Crossref `short-container-title` "Manag Rev Q".
  - The year shown is the issue year: Vol. 76, No. 2, June 2026. The article was first published online on 11 April 2025, and the negotiated BibTeX uses `year=2025`. Choose one convention and apply it consistently. **[BIBLIOGRAPHIC VERIFICATION REQUIRED: year convention, not resolved here]**
- **BIBTEX** (doi.org negotiation; key changed):
```bibtex
@article{lezzi2025cyberres, title={Measuring cyber resilience in industrial IoT: a systematic literature review}, volume={76}, ISSN={2198-1639}, url={http://dx.doi.org/10.1007/s11301-025-00495-8}, DOI={10.1007/s11301-025-00495-8}, number={2}, journal={Management Review Quarterly}, publisher={Springer Science and Business Media LLC}, author={Lezzi, Marianna and Corallo, Angelo and Lazoi, Mariangela and Nimis, Aldo}, year={2025}, month=Apr, pages={1107–1161} }
```
- **TYPE:** Review/survey (systematic literature review) in a peer-reviewed journal. Licence: CC BY 4.0 (Crossref).
- **Dates (Crossref):** received 12 March 2024; accepted 17 February 2025; first online 11 April 2025; issue June 2026.
- **VERIFICATION SOURCES:**
  - Crossref search and `https://api.crossref.org/works/10.1007/s11301-025-00495-8`
  - `https://doi.org/10.1007/s11301-025-00495-8` (BibTeX)
  - `https://link.springer.com/article/10.1007/s11301-025-00495-8` (WebFetch ×2)
- **ACCESS LEVEL:** FULL TEXT (VoR HTML). The first 100,000 of 104,584 characters were read. Table 9 and the appendix tables were only partly present as text. The §5 limitations discussion was not reached in the verbatim pass.

**CONTENT**
- **Research problem:** Which metrics can measure the cyber resilience of business performance in IIoT, and in which industries and for which assets. RQ1–RQ5 cover definition, standards guidance, metrics, industries, and assets.
- **Method (§2.2):**
  - Scopus "returned 214 papers" and Web of Science "returned 28 papers", for "an initial sample of 242 scientific papers".
  - Filters reduced this "to 213", and duplicate removal "reduced the number of papers to 189".
  - Title/abstract screening excluded "106 publications".
  - Full-text screening excluded "60 publications".
  - "23 papers" were analysed, and a third criterion "allowed the final sample of papers to be extended by six units". These six are standards and guidance documents.
  - The databases were accessed in January 2023.
- **Definition:** NIST: "the ability to anticipate, withstand, recover from, and adapt to adverse conditions, stresses, attacks, or compromises" "on systems that use or are enabled by cyber resources" (§1).
- **Domain:** IIoT, CPS, and ICS from a management perspective.
- **Architecture / Zero-Trust depth / device identity / workload identity / authorization / payload signatures / provenance / lineage / replay / duplicates / ordering / buffering / immutable storage:** Not reported. The review addresses metrics, not mechanisms. Authentication strength appears only as an input to one metric.
- **Disconnected-edge recovery:** Not reported as a mechanism. Recovery appears only as a resilience goal and in time-based metrics.
- **Threat model / implementation / testbed / baselines:** Not applicable (review).
- **Findings (quantitative counts):**
  - Sectors: "8 of the 23 papers discuss the relevance of cyber resilience in the energy sector"; "two papers referring to the transport sector and two for the water sector"; "the remaining 11 papers do not specify the target industry sector" (§3.4).
  - Assets: "ICS and CPS appear to be the assets mainly covered, with four and fourteen mentions, respectively" (§3.5).
  - Goals: "the goals most considered in the definitions are withstand and recover, repeated 14 and 15 times respectively" (§3.1.2). A word cloud elsewhere gives "“recover” (repeated 10 times) and “withstand” (repeated 7 times)" (§3.1). The paper does not explain the difference.
  - Metrics are classed as static or dynamic and by phase (anticipate, withstand, recover, evolve); see Table 9.
- **Stated limitations:** "this literature review cannot be considered exhaustive". Only two databases were searched, and the results depend on the keywords used (§2).

**RELEVANCE:** Supports the manuscript's resilience framing (withstand and recover) and the observation that IIoT resilience work is measured with metrics rather than designed into the ingestion and recovery mechanisms. It has no direct mechanism overlap.

**FLAGS:**
- The online-versus-issue year is unresolved (2025 vs. 2026).
- The two counts for withstand and recover (14/15 vs. 10/7) are both in the source; quote the right one for the context.

---

## 9. Alotaibi (2026), Applied Sciences

- **KEY:** alotaibi2026resilient
- **VERIFIED CITATION:** Alotaibi, B. A Review of Resilient IoT Systems: Trends, Challenges, and Future Directions. *Appl. Sci.* **2026**, *16*, 2079. https://doi.org/10.3390/app16042079
- **BIBTEX** (doi.org negotiation; key changed):
```bibtex
@article{alotaibi2026resilient, title={A Review of Resilient IoT Systems: Trends, Challenges, and Future Directions}, volume={16}, ISSN={2076-3417}, url={http://dx.doi.org/10.3390/app16042079}, DOI={10.3390/app16042079}, number={4}, journal={Applied Sciences}, publisher={MDPI AG}, author={Alotaibi, Bandar}, year={2026}, month=Feb, pages={2079} }
```
- **TYPE:** Review/survey (MDPI article type "Review"). It is a structured narrative review, not a protocol-registered systematic review.
- **Affiliation (Crossref and MDPI):** Department of Information Technology, University of Tabuk, Tabuk 47512, Saudi Arabia.
- **Preprint:** Preprints.org, 10.20944/preprints202512.1717.v1 (2025-12-19, per a Crossref search result).
- **VERIFICATION SOURCES:**
  - Crossref search and `https://api.crossref.org/works/10.3390/app16042079`
  - `https://doi.org/10.3390/app16042079` (BibTeX)
  - `https://www.mdpi.com/2076-3417/16/4/2079/htm` (WebFetch ×4, including offset)
- **ACCESS LEVEL:** PARTIAL FULL TEXT. §1–§6.1 were examined. **§7, §8 (Challenges and Future Directions), §9 (Conclusions), any limitations paragraph, and the back matter were not examined**, because the HTML conversion was truncated.

**CONTENT**
- **Research problem:** A review of resilience in IoT systems, with a stressor × layer taxonomy and the author's own illustrative simulations.
- **Method (§2):** "We focused on studies published from 2022 to 2025". "We included peer-reviewed journal and conference papers in English". "Papers that covered only standard security topics, without focusing on resilience, were excluded". The abstract counts "more than forty representative studies", and no exact count is given.
- **Definition:** Resilience is "the capacity of a system to withstand, recover from, and adapt to disruptions while maintaining essential functionality" (§1; first fragment verified verbatim).
- **Domain:** General IoT, including IIoT, healthcare, and vehicles as examples.
- **Architecture / taxonomy:** Stressor types (adversarial, environmental/operational, hybrid) crossed with layers (hardware, network/protocol, learning/AI, application, governance/trust).
- **Zero-Trust depth:** Not reported (no hits for zero trust).
- **Device identity:** "The hardware layer is tamper-resistant, features redundant sensing, and incorporates PUFs" (§5).
- **Workload identity / authorization-policy detail:** Not reported in the examined portion.
- **Payload integrity / provenance / lineage:** Among the poisoning mitigations: "cryptographic or signed provenance logs to trace data lineage" (§4.2). "Blockchain-anchored logs document device identity, software lineage, and security events" (§4.3).
- **Replay treatment (security replay):** "link-layer replay attacks like Roll-Jam". Mitigation: "cryptographic freshness with nonce-based challenge–response and strict single-use counters"; "Desynchronization resilient rolling code updates use session-bound keys and monotone counters" (§4.2).
- **Duplicate treatment:** Not reported for data. The only hit is the review's own duplicate removal (§2).
- **Event ordering:** Not reported.
- **Disconnected-edge recovery/buffering:** "ECG wearables buffer data locally and synchronize later" (§4.3; a hospital outage example). Burst-loss mitigations for LPWANs are covered (§4.2).
- **Raw/immutable preservation:** "immutable event logs ensure that braking decisions are based on authentic" … "time-synchronized sensor data rather than spoofed inputs" (§4.3).
- **Threat model:** Not a formal model. Stressors are classified.
- **Implementation/testbed:** The author's simulations use the ToN-IoT dataset ("we experimented using ToN-IoT dataset", §4.2).
- **Baselines:** Not applicable.
- **Metrics/results (author's simulations, §4.2):**
  - "Relative to the clean baseline where the accuracy is 0.9996, FGSM declines gradually to 0.299 at ϵ = 0.15".
  - For PGD and BIM, "at ϵ = 0.05, accuracy is 0.006 and 0.170, respectively".
  - Hybrid stress: "the performance falls by a magnitude of Δ ≈ 0.34", "reaching its baseline level within about 48 s, the recovery time" (Fig. 12).
- **Stated limitations:** Not examined. The limitations and conclusions sections were not reached.

**RELEVANCE:** A broad 2026 resilience review that names signed provenance logs, nonce- and counter-based replay defence, local buffering with later synchronization, and immutable event logs as resilience techniques. These are useful supporting citations, but the paper treats each only briefly and as examples, not as an ingestion design.

**FLAGS:** §7–§9 are unexamined. Re-check any "challenges/future directions" claim against the article PDF before citing.

---

## 10. Rodigari et al. (2021), IEEE CLOUD 2021

- **KEY:** rodigari2021ztmc
- **VERIFIED CITATION:** Rodigari, S.; O'Shea, D.; McCarthy, P.; McCarry, M.; McSweeney, S. Performance Analysis of Zero-Trust multi-cloud. In *Proceedings of the 2021 IEEE 14th International Conference on Cloud Computing (CLOUD)*, Chicago, IL, USA, 5–10 September 2021; IEEE, 2021; pp. 730–732. https://doi.org/10.1109/CLOUD53861.2021.00097
  - The event name, location, and dates are from Crossref `event`.
  - The IEEE publisher location is not in the Crossref record. **[BIBLIOGRAPHIC VERIFICATION REQUIRED: publisher location for MDPI format]**
  - The IEEE Xplore document number, from the doi.org redirect, is 9582229.
- **BIBTEX** (doi.org negotiation; key changed):
```bibtex
@inproceedings{rodigari2021ztmc, title={Performance Analysis of Zero-Trust multi-cloud}, url={http://dx.doi.org/10.1109/CLOUD53861.2021.00097}, DOI={10.1109/cloud53861.2021.00097}, booktitle={2021 IEEE 14th International Conference on Cloud Computing (CLOUD)}, publisher={IEEE}, author={Rodigari, Simone and O’Shea, Donna and McCarthy, Pat and McCarry, Martin and McSweeney, Sean}, year={2021}, month=Sept, pages={730–732} }
```
  - Notes: the entry has a curly apostrophe in "O’Shea", `month=Sept` (not a standard BibTeX month macro), and a lowercased DOI, all as negotiated.
- **TYPE:** Conference paper, 3 pages (a short paper).
- **Affiliations (arXiv PDF):** Munster Technological University, Cork, Ireland; McCarry at Pilz Ireland Industrial Automation Limited, Cork.
- **VERIFICATION SOURCES:**
  - Crossref search and `https://api.crossref.org/works/10.1109/CLOUD53861.2021.00097`
  - `https://doi.org/10.1109/CLOUD53861.2021.00097` (BibTeX; redirect to `https://ieeexplore.ieee.org/document/9582229/`; the IEEE page was unreadable)
  - `https://api.openalex.org/works/doi:10.1109/CLOUD53861.2021.00097`
  - `https://export.arxiv.org/api/query?id_list=2105.02334`
  - `https://arxiv.org/pdf/2105.02334` (v1, 3 pages)
- **ACCESS LEVEL:** FULL TEXT (preprint). arXiv v1 of 2021-05-05; its comment reads: "This paper was submitted for the IEEE CLOUD 2021 Conference and is currently being reviewed". The IEEE VoR was not accessed.

**CONTENT**
- **Research problem:** Is there a performance penalty for enabling Zero Trust with a sidecar-proxy service mesh (Istio) across two public clouds? "To the best of our knowledge, no previous work has provided a performance analysis of Zero Trust in a multi-cloud environment." (Abstract).
- **Domain:** Cloud-native microservices on Kubernetes in a multi-cloud setup (GKE and EKS, London region). Not IIoT, although one co-author is from industrial automation.
- **Architecture:** Scenario 1 is a DNS load balancer across GKE and EKS. Scenario 2 adds the Istio service mesh to enable ZT (Fig. 1, §III).
- **Zero-Trust depth:** "authenticating, and authorizing every request" and "encrypting all network communication" (Abstract), through the sidecar proxy. Istio was chosen for its "service based identity model and centralised view of security policies" (§III).
- **Device identity:** Not reported.
- **Workload identity:** Istio's service-based identity is mentioned (§III); the mechanism is not detailed.
- **Authorization/policy:** Istio policy enforcement, "to include encryption, authentication and authorization" (§V).
- **Payload integrity / provenance / lineage / replay / duplicates / ordering / disconnected-edge / immutable storage:** Not reported.
- **Threat model:** Not reported.
- **Implementation/technologies:** Kubernetes (GKE v1.18.16-gke.302, EKS v1.18.9-eks-d1db3c; Table I), Istio, Prometheus, Grafana, and cURL scripts.
- **Testbed (Table I):** GKE has 2 nodes, 8 vCPU, 32 Gb, E2-standard-4. EKS has 2 nodes, 4 vCPU, 16 Gb, T2.medium.
- **Baselines:** Multi-cloud without Istio, compared with the same setup with Istio.
- **Metrics/results:**
  - "Each test comprised 1000 sequential HTTP requests and all requests were successful" (§V).
  - Table II (GKE responding), "Pod to Service with the same cluster": GKE pod CPU max 0.1 vCores, pod memory 175 MiB, cluster CPU 5.6%, cluster memory 5.3%; GKE-ISTIO 0.9 vCores, 85 MiB, 17.8%, 5.6%.
  - Table III (EKS responding), same-cluster rows: EKS 1.1 vCores, 230 MiB, 33.3%, 17.2%; EKS-ISTIO 0.9 vCores, 115 MiB, 30.1%, 18.7%.
  - "In both Table II and Table III pod memory usage with the Istio service mesh is reduced by 50%" (§V).
  - Latency appears in Fig. 2 at the 50/75/90/99th percentiles, with no numeric values in the text. "higher latency for simple multi-cloud deployment, particularly for 75% and above" (§V).
  - Conclusion: "no evident performance penalty at the data-plane level when enabling Zero Trust with a side-car proxy implementation" (§V).
- **Stated limitations:**
  - "the number of tests and test scenarios should improve to provide statistical significance in terms of resource analysis" (§V).
  - The two clusters had unequal specifications. Future tests will use similar specifications and add control-plane analysis (§VI).

**RELEVANCE:** An early, small-scale measurement of ZT (mTLS and per-request authorization through a service mesh) overhead in multi-cloud settings. It can be cited for workload-level ZT on the cloud side of the pipeline. Its limits for the manuscript: preliminary data, a short paper, no IIoT data path, and no event-level admission.

**FLAGS:**
- The content is from the preprint (submitted before review), so verify against the IEEE VoR.
- The publisher location is unverified.
- OpenAlex lists "Patrick McCarthy" and "Sean G. McSweeney". Crossref and arXiv list "Pat McCarthy" and "Sean McSweeney", which are used here.

---

## 11. Alayed, Tahir, Hassan (2026), Electronics

- **KEY:** alayed2026iztsdn
- **VERIFIED CITATION:** Alayed, W.; Tahir, H.A.; Hassan, W.U. End-to-End Performance Analysis of an Intelligent Zero-Trust Framework for SDN: A Quantitative Evaluation of Latency and Overhead. *Electronics* **2026**, *15*, 2376. https://doi.org/10.3390/electronics15112376
- **BIBTEX** (doi.org negotiation; key changed):
```bibtex
@article{alayed2026iztsdn, title={End-to-End Performance Analysis of an Intelligent Zero-Trust Framework for SDN: A Quantitative Evaluation of Latency and Overhead}, volume={15}, ISSN={2079-9292}, url={http://dx.doi.org/10.3390/electronics15112376}, DOI={10.3390/electronics15112376}, number={11}, journal={Electronics}, publisher={MDPI AG}, author={Alayed, Walaa and Tahir, Hassam Ahmed and Hassan, Waqar Ul}, year={2026}, month=June, pages={2376} }
```
- **TYPE:** Peer-reviewed journal article, an empirical re-evaluation of a published framework.
- **Affiliations (MDPI page):** Princess Nourah bint Abdulrahman University, Riyadh (Alayed, corresponding); Swinburne University of Technology (Tahir); NUST, Risalpur (Hassan).
- **Date:** published online 1 June 2026 (MDPI and Crossref).
- **VERIFICATION SOURCES:**
  - Crossref search and the `https://api.crossref.org/works/10.3390/electronics15112376` record
  - `https://doi.org/10.3390/electronics15112376` (BibTeX)
  - `https://www.mdpi.com/2079-9292/15/11/2376/htm` (WebFetch ×2; the first 100,000 of 104,583 characters)
- **ACCESS LEVEL:** FULL TEXT (VoR HTML; Table 5 is an image and its values were not readable).

**CONTENT**
- **Research problem:** Quantify the end-to-end latency, controller overhead, and scalability of the IZTSDN framework of Guo et al. [4]. The paper says the original reported accuracy and throughput only.
  - Reference [4], as given in this paper: X. Guo et al., "An intelligent zero trust secure framework for cyber defense in software-defined environments", *PeerJ Computer Science*, DOI 10.7717/peerj-cs.1674. That reference was not verified independently.
- **Domain:** SDN networks. IIoT is not addressed; "industrial control" is named only as a latency-sensitive use case.
- **Architecture:** A Ryu v4.34 controller and Open vSwitch v2.15.0. The components are the CALSeq2Seq anomaly detector (1D-CNN plus self-attention plus LSTM Seq2Seq), the UBTA trust engine, policy enforcement through flow rules, and an mTLS gateway.
- **Zero-Trust depth:** Two phases.
  - Pre-connection: a single-packet-authorization request triggers trust evaluation, and flow rules are installed only if the predicted trust is at least 0.5.
  - Post-connection: authorized flows are monitored, and attacked ports are blocked for 120 s.
  - Access thresholds rise from browsing (≥0.5) to deletion (≥0.95).
- **Device identity:** Not reported beyond mTLS channel establishment.
- **Workload identity:** Not reported.
- **Authorization/policy:** A trust-score threshold per action class, enforced through flow rules.
- **Payload integrity/signatures:** Not reported beyond mTLS.
- **Provenance / lineage / replay / duplicates / ordering / disconnected-edge / immutable storage:** Not reported.
- **Threat model:** Network attacks, namely SYN, UDP, and ICMP floods and nmap scans. Out of scope: APTs, encrypted and application-layer attacks, lateral movement, and insider misuse (§6.1).
- **Implementation/technologies:** Mininet, hping3, iPerf3, wrk2, and Scapy, on a Dell PowerEdge R740 (dual Xeon Gold 6248R, 256 GB) with Ubuntu 20.04 VMs.
- **Testbed:** Topologies from 4 nodes up to 64 nodes (fat-tree). Measurements were "averaged over 10 runs (n = 1000 samples per metric)" (§5), with "A minimum of N = 1000 measurements per latency component per scenario" (§4.2).
- **Baselines:** Baseline SDN (Ryu without security modules), DeepIDS, SDP implementations, OverWatch, and the IZTSDN figures claimed by Guo et al.
- **Metrics/results:**
  - Normal conditions (Abstract): "the mean latency is 83 ± 4 ms (95% CI, N = 1000 , σ = 12 ms)".
  - Under attack (Abstract): "Under DDoS attack, the mean latency increases to 235 ± 11 ms (95% CI, N = 1000 , σ = 38 ms)", and "CPU usage reaches 94 ± 2 % (95% CI)".
  - Throughput (§5.3): "throughput retention drops to 62% (vs. Guo et al.'s claimed 80.5% [4])".
  - Overall (§7): "The framework imposes a 4.2× CPU overhead and exhibits super-linear scalability degradation".
- **Stated limitations (§6.1):**
  - KVM/QEMU virtualization overhead.
  - A single centralized controller; only x86 platforms.
  - Synthetic traffic models.
  - Single-threaded Python may exaggerate the overhead.
  - "The projected improvements (e.g., 60–80% latency reduction, 3–5× throughput capacity) are theoretical estimates" (§6.2).

**RELEVANCE:** A rare quantitative ZT overhead study with confidence intervals. It is useful to justify measuring admission latency and CPU cost in the manuscript's evaluation and to show that ML-based continuous verification can dominate latency. It works at the network-flow level, with no per-event data admission, provenance, or IIoT ingestion semantics.

**FLAGS:**
- The WebFetch extraction reported internal inconsistencies in the paper: DeepIDS accuracy differs between §2.1 and §5.1, and the number of scales differs between §4.5 and Fig. 5. These were not verified verbatim.
- The source of the 4.2× ratio could not be traced in the text.
- Reference [4] should be verified separately if cited.

---

## 12. Zanasi, Russo, Colajanni (2024), Ad Hoc Networks

- **KEY:** zanasi2024flexzt
- **VERIFIED CITATION:** Zanasi, C.; Russo, S.; Colajanni, M. Flexible zero trust architecture for the cybersecurity of industrial IoT infrastructures. *Ad Hoc Networks* **2024**, *156*, 103414. https://doi.org/10.1016/j.adhoc.2024.103414
  - Crossref's `short-container-title` is "Ad Hoc Networks". An ISO abbreviation was not shown on any fetched page. **[BIBLIOGRAPHIC VERIFICATION REQUIRED: abbreviation, if MDPI copy-editing requires one]**
- **BIBTEX** (doi.org negotiation; key changed):
```bibtex
@article{zanasi2024flexzt, title={Flexible zero trust architecture for the cybersecurity of industrial IoT infrastructures}, volume={156}, ISSN={1570-8705}, url={http://dx.doi.org/10.1016/j.adhoc.2024.103414}, DOI={10.1016/j.adhoc.2024.103414}, journal={Ad Hoc Networks}, publisher={Elsevier BV}, author={Zanasi, Claudio and Russo, Silvio and Colajanni, Michele}, year={2024}, month=Apr, pages={103414} }
```
- **TYPE:** Peer-reviewed journal article. Open access under CC BY-NC-ND 4.0 (Crossref and ScienceDirect); "© 2024 The Author(s). Published by Elsevier B.V." (Crossref).
- **Other details:**
  - Affiliations: University of Bologna, Department of Computer Science and Engineering; corresponding author Colajanni (ScienceDirect).
  - Dates: available online 8 February 2024; issue April 2024.
  - Preprint: SSRN 10.2139/ssrn.4481853 (2023), "Flexible Zero Trust Architecture for the Cybersecurity of Industrial Iot Infrastructures" (Crossref search result; not read).
- **VERIFICATION SOURCES:**
  - Crossref search and `https://api.crossref.org/works/10.1016/j.adhoc.2024.103414`
  - `https://doi.org/10.1016/j.adhoc.2024.103414` (BibTeX)
  - `https://www.sciencedirect.com/science/article/pii/S1570870524000258` (WebFetch ×3)
- **ACCESS LEVEL:** FULL TEXT (VoR, open access). Figures 4–5 and 12–14 were not readable as text.

**CONTENT**
- **Research problem:** Existing ZT solutions suit uniform, centralized IT but not heterogeneous IIoT with hard real-time, high-reliability, and decentralized decision-making needs (Abstract, §1). Backward compatibility with legacy equipment is a design principle (§3).
- **Domain:** IIoT and IT/OT networks, for example power grids, transport, and water treatment (§1).
- **Architecture:** Network micro-segmentation on an overlay SDN built with **Nebula**, which is peer-to-peer with no central controller and uses a "Lighthouse" for discovery. Around it:
  - a centralized security management layer: a Dhall-based configuration library that type-checks policies and validates CSRs against the configuration;
  - a certificate authority;
  - the NEST service, an adaptation of EST and the only publicly exposed component.
- **Zero-Trust depth:** Resource-centric, mutual, and location-independent trust. Policies are group-based (for example SSH between groups). Each node enforces locally at connection handshake time with no central authority in the path. Policies are distributed asynchronously.
- **Device identity:** Custom (non-X.509) Nebula certificates carry security-group metadata and are used for mutual authentication. Enrollment uses a secret token: "To generate the secret token, HMAC is applied to the client hostname using a 256-bit symmetric key." (§4.2). Re-enrollment uses the current certificate as authorization (§4.5).
- **Workload identity:** Not reported separately; Kubernetes clients are covered only in the performance testbed.
- **Authorization/policy:** Group-based firewall rules compiled from the central configuration. A monitoring service compares the live state with the global configuration.
- **Credential revocation (manuscript topic):**
  - "The Nebula overlay network does not support traditional Certificate Revocation Lists (CRLs)." "Instead, it offers the capability to define certificate blacklists within the node configuration."
  - "By removing the certificate’s public key from the CA’s database, the renewal process is halted." (§4.4).
  - Re-enrollment involves "verifying that the certificate has not been blacklisted as per the security policies" (§4.5).
- **Payload integrity/signatures:** Not reported. Connections are encrypted end to end and mutually authenticated. The terms "integrity" and "replay" do not appear in the text.
- **Provenance:** Not reported.
- **Lineage:** Not reported.
- **Replay treatment:** Not reported.
- **Duplicate treatment:** Not reported.
- **Event ordering:** Not reported.
- **Disconnected-edge recovery/buffering:** Partial, for *control-plane* availability only: the design "ensures the enforcement of security policies even if the central management service becomes temporarily unavailable" (§3). There is no data buffering or recovery.
- **Raw/immutable preservation:** Not reported. Request logs of the NEST and configuration services are shown in figures, and audit and immutable storage are not addressed.
- **Threat model:** Not formal. The implicit threats are a compromised central SDN controller as a single point of failure, lateral movement, spoofing, topology exploration, privilege escalation through CSRs, and configuration error.
- **Implementation/technologies:** Nebula, Dhall, the NEST service (based on EST), and a CA.
- **Testbed:** Azure VMs (B1ls, B2s), a Raspberry Pi 4b Lighthouse, a Windows PC, an Android phone, and two Kubernetes clusters in different data centres (§4.1, §5).
- **Baselines:** A "baseline architecture not using our proposal" (§5); its composition is not described.
- **Metrics/results:**
  - Table 1, "Nebula overheads" (RAM / CPU / connections → CPU usage / RAM usage):
    - 1 GB, 1 vCPU, 50 connections → 18.4% / 1.5%
    - 4 GB, 2 vCPU, 200 connections → 12.8% / <1%
    - 8 GB, 2 vCPU, >300 connections → 15.1% / <1%
  - Configuration switch: "typically on the order of 100 ms, as determined by our testing", and on Windows "approximately 3–4 s" (§4.5).
  - Re-enrollment stress test: "we configure the certificate validity to two minutes" (§4.5).
  - "In total, we execute twelve tests for increasing numbers of clients going from 50 to 300 with steps of 50 clients." (§5). This is internally inconsistent: steps of 50 from 50 to 300 give six client counts.
  - Response-time results (Figs. 12–14) are described only qualitatively.
- **Stated limitations:**
  - Asynchronous propagation of topology changes.
  - Remediation after compromise may take longer than in a centralized system.
  - The configuration service is a potential bottleneck.
  - Monitoring only detects differences between the intended and actual topology.
  - Future work: an analytics engine, possibly AI-based (§6–§7).

**RELEVANCE:** The closest IIoT ZT *infrastructure* design in this set. Its points of overlap with the manuscript are decentralized enforcement that survives loss of the management plane, certificate enrollment and renewal, and blacklist-based revocation without CRLs. It works at the connection and segment level and does not address per-event payload signatures, provenance, replay or duplicates, ordering, or edge data buffering.

**FLAGS:**
- The journal abbreviation is unverified.
- The "twelve tests" versus six client counts discrepancy is in the source.

---

## 13. Vendor guidance (grey literature; not peer reviewed)

### 13a. Microsoft: OPC UA reference solution (Azure Architecture Center)

- **KEY:** microsoft2026opcuaref
- **EXACT TITLE:** "OPC UA reference solution" (page H1). The HTML `<title>` is "OPC UA reference solution - Azure Architecture Center | Microsoft Learn".
- **PUBLISHER:** Microsoft (Microsoft Learn, Azure Architecture Center; `ms.service` = azure-architecture-center, `ms.subservice` = architecture-guide). `ms.author` / `author` = "erichb" (an alias; the full name was not shown on the fetched page). `ms.topic` = concept-article.
- **URL (canonical):** https://learn.microsoft.com/en-us/azure/architecture/guide/iot/iot-industrial-solution-architecture
  - The legacy URL `https://learn.microsoft.com/en-us/azure/iot/tutorial-iot-industrial-solution-architecture` returns HTTP 301 to `…/azure/architecture/solution-ideas/articles/iot-industrial-solution-architecture`, which then reaches the canonical URL above.
  - A search engine still lists the legacy URL as "Tutorial: Implement the Azure Industrial IoT reference solution architecture". That title is from the search index only and is not current.
- **DATES:**
  - `ms.date` 2026-07-22.
  - Displayed "Last updated on" date: 2026-08-18. This is a `<local-time datetime="2026-08-18T05:04:00.000Z" data-article-date-source="calculated">` value.
  - `updated_at` 2026-10-27T05:04:00Z.
  - Accessed 3 November 2026.
  - Source markdown: `github.com/MicrosoftDocs/architecture-center-pr/blob/live/docs/guide/iot/iot-industrial-solution-architecture.md`, commit e50c619….
- **MDPI-style reference:** Microsoft. OPC UA Reference Solution. Azure Architecture Center, Microsoft Learn. Available online: https://learn.microsoft.com/en-us/azure/architecture/guide/iot/iot-industrial-solution-architecture (accessed on 3 November 2026).
- **BIBTEX** (constructed from page metadata):
```bibtex
@misc{microsoft2026opcuaref,
  author       = {{Microsoft}},
  title        = {{OPC UA} reference solution},
  howpublished = {Azure Architecture Center, Microsoft Learn},
  year         = {2026},
  url          = {https://learn.microsoft.com/en-us/azure/architecture/guide/iot/iot-industrial-solution-architecture},
  note         = {ms.date 2026-07-22; displayed last update 2026-08-18; accessed 2026-11-03}
}
```
- **TYPE:** Vendor guidance (reference architecture / solution documentation). "This solution is provided as-is and isn't a Microsoft-supported product offering."
- **VERIFICATION SOURCES:**
  - WebSearch
  - WebFetch of the legacy URL
  - shell `curl` of the legacy URL (301) and of the final URL (full HTML parsed for meta tags and quotes)
  - `https://github.com/digitaltwinconsortium/ManufacturingOntologies` (WebFetch). This is the repository that holds the station information model and simulation. Its About text is "A reference solution for leveraging manufacturing ontologies", and its README does not mention Microsoft, Azure, or Azure IoT Operations.
- **ACCESS LEVEL:** Full page read.

**CONTENT (as stated on the page)**
- **Scope:**
  - "This solution leverages Azure IoT Operations, a platform for connecting, managing, and processing industrial telemetry."
  - "This article describes Microsoft's implementation of the Cloud Initiative reference architecture"; "The OPC Foundation Cloud Initiative extends this approach to cloud-native architectures."
- **Architecture:**
  - A simulated production line: Munich and Seattle lines with Assembly, Test, and Packaging stations, exposed as OPC UA servers.
  - The edge runs K3s with Azure Arc and Azure IoT Operations (connector for OPC UA, MQTT broker, data flows).
  - Cloud side: Azure Event Hubs, then Azure Data Explorer, Azure Databricks (Delta Lake), or Microsoft Fabric (eventhouse). Key Vault and a managed identity are also used.
- **Device/application identity:** OPC UA application certificates. "The Azure IoT Operations connector for OPC UA uses a self-signed application instance certificate, and each station in turn presents its own self-signed server certificate." Recommendation: "Use a proper PKI/CA (or OPC UA GDS) instead of self-signed certificates."
- **Workload identity:** "Cloud services authenticate to Azure Data Explorer, Key Vault, and Event Hubs by using a user-assigned managed identity and Entra tokens (no shared keys for those hops). Azure Data Explorer read uses Entra workload identity federation." Recommendation: "Scope each service to its own identity rather than one shared identity."
- **Threat model:** "This section is a threat model of the reference solution. The model uses the Microsoft STRIDE methodology" (section "Security review (STRIDE)", with subsections for Trust boundaries and each STRIDE category).
- **Payload integrity in transit:** "Transport to Event Hubs is TLS-encrypted. The Azure IoT Operations MQTT broker hop uses TLS and SAT authorization." Recommendations: "Retain TLS everywhere. Retain OPC UA message signing and encryption end-to-end".
- **Audit / non-repudiation:** "there's no signed audit trail of who or what triggered a physical command. Add tamper-evident audit logging for control actions." On attribution, "Azure platform logs … exist, but the i3X API Basic authentication user is a single shared admin account".
- **Immutable storage:** "Delta Lake retains history. Enable immutability and retention policies where required."
- **Disconnected edge:** "Azure IoT Operations can operate offline for 72 hours at most, and performance might degrade during that period, so a production adaptation needs to define buffering, recovery, and data-loss behavior for longer outages."
- **Network exposure:** "PostgreSQL uses an AllowAllAzureIps firewall rule." Recommendation: "Use private endpoints or virtual network integration."
- **Not addressed on the page:** replay, duplicates, ordering, and data provenance or lineage (no hits).

**RELEVANCE:** A current, official industrial OPC UA edge-to-cloud reference with an explicit STRIDE review. It openly lists gaps that the manuscript targets: no signed audit trail, buffering, recovery, and data-loss behaviour left undefined for outages longer than 72 h, immutability only recommended, and no replay, duplicate, or provenance treatment.

**FLAGS:**
- Grey literature that changes frequently: cite it with the access date and the `ms.date`.
- The author's full name is not shown, so do not expand "erichb".

### 13b. AWS IoT security guidance

**Primary (current, official) source:**
- **KEY:** aws2025iotlens
- **EXACT TITLE:** "Internet of Things (IoT) Lens", part of the **AWS Well-Architected Framework**. Security pillar page title: "Security - Internet of Things (IoT) Lens".
- **PUBLISHER:** Amazon Web Services (AWS Documentation, AWS Well-Architected). The page describes itself as "This whitepaper describes the AWS IoT Lens for the AWS Well-Architected Framework…".
- **URLs:**
  - Abstract and introduction: https://docs.aws.amazon.com/wellarchitected/latest/iot-lens/iot-lens.html
  - Security pillar: https://docs.aws.amazon.com/wellarchitected/latest/iot-lens/security.html
  - Revisions: https://docs.aws.amazon.com/wellarchitected/latest/iot-lens/document-revisions.html
- **DATE:** "Publication date: July 2, 2025" (`iot-lens.html`). Document revisions:
  - "Initial publication", November 1, 2018
  - "Whitepaper updated", December 23, 2019
  - "Minor update", March 10, 2021
  - "Major update" (Lens Checklist, IIoT), March 31, 2023
  - "Major update" (best practices added), July 2, 2025
- **MDPI-style reference:** Amazon Web Services. Internet of Things (IoT) Lens—AWS Well-Architected Framework. 2 July 2025. Available online: https://docs.aws.amazon.com/wellarchitected/latest/iot-lens/iot-lens.html (accessed on 3 November 2026).
- **BIBTEX** (constructed from page metadata):
```bibtex
@misc{aws2025iotlens,
  author       = {{Amazon Web Services}},
  title        = {Internet of Things ({IoT}) Lens -- {AWS} Well-Architected Framework},
  howpublished = {AWS Whitepaper / AWS Well-Architected Framework},
  year         = {2025},
  month        = jul,
  url          = {https://docs.aws.amazon.com/wellarchitected/latest/iot-lens/iot-lens.html},
  note         = {Publication date: July 2, 2025; accessed 2026-11-03}
}
```
- **TYPE:** Vendor guidance (Well-Architected lens).
- **VERIFICATION SOURCES:** shell `curl` of the IoT Lens pages:
  - `toc-contents.json`, `iot-lens.html`, `document-revisions.html`, `security.html`
  - `identity-and-access-management.html`, `detective-controls.html`, `infrastructure-protection.html`, `data-protection.html`, `vulnerability-management.html`
  - `iot-edge-computing.html`, `failure-management.html`, `workload-architecture.html`, `foundations.html`
- **ACCESS LEVEL:** The named pages were read.
- **CONTENT:** The Lens "includes both IoT and industrial IoT (IIoT) workloads". The security pillar's best-practice headings, verbatim, map to the requested topics as follows.
  - **Identity:**
    - "IOTSEC01-BP01 Assign unique identities to each IoT device"
    - "IOTSEC02-BP02 Use a trusted platform module (TPM) to implement cryptographic controls"
    - "IOTSEC02-BP03 Use protected boot and persistent storage encryption"
    - "IOTSEC05-BP01 Perform certificate lifecycle management"
  - **Logging, monitoring, auditing:**
    - "IOTSEC06-BP01 Collect and analyze logs and metrics to capture authorization errors and failures to enable appropriate response"
    - "IOTSEC06-BP02 Send alerts when security events, misconfiguration, and behavior violations are detected"
    - "IOTSEC07-BP03 Log and monitor network configuration changes and network communication"
  - **Secure connectivity:**
    - "IOTSEC07-BP01 Configure cloud infrastructure to have secure communications"
    - "IOTSEC10-BP01 Use encryption to protect IoT data in transit and at rest"
  - **Updates:**
    - "IOTSEC09-BP01 Manage and maintain IoT Device software using an automated, monitored, and audited mechanism"
    - "IOTSEC13-BP02 Deploy updates to IoT device firmware or software to address identified issues"
  - **Edge buffering and ordering (reliability pillar):**
    - "IOTREL12-BP01 Provide adequate device storage for offline operations"
    - "store and forward critical data when devices become disconnected from the cloud"
    - "Messages collected on the device are queued and processed in FIFO order"
    - "If the cache size exceeds the maximum disk buffer size, the connector discards the earliest data from the queue"
    - "IoT devices send lots of data in small sizes without order, and the cloud application should be able to handle this"
    - "Because IoT data is not ordered, including an accurate timestamp with the data will enhance your analytic capabilities"
    - "IOTREL07-BP01 Store data before processing"
  - Provenance, lineage, replay, and duplicate handling: not reported. A keyword search of all 14 downloaded Lens pages found no hits for "replay", "provenance", "lineage", "idempot", or "dedup". The single "duplicate" hit refers to a PUF being "virtually impossible to duplicate, clone, or predict" (`identity-and-access-management.html`), not to data duplicates.
- **RELEVANCE:** Official, current, IIoT-inclusive AWS guidance covering identity, connectivity, updates, logging, monitoring, and auditing. Its reliability pillar explicitly concedes unordered IoT data and lossy edge caches (oldest-first discard), which is a direct practitioner anchor for the manuscript's out-of-order and disconnected-edge problem statement.

**Historical (as named in the research note, probably):**
- **KEY:** aws2021securingiot
- **EXACT TITLE:** "Securing Internet of Things (IoT) with AWS" (AWS Whitepaper).
- **PUBLISHER:** Amazon Web Services.
- **DATE:** "Publication date: December 20, 2021". The page carries the notice "This whitepaper is for historical reference only. Some content might be outdated and some links might not be available."
- **URL:** https://docs.aws.amazon.com/whitepapers/latest/securing-iot-with-aws/securing-iot-with-aws.html
- **Abstract (WebFetch):** "This whitepaper is a detailed look at how customers can use AWS security services to secure their Internet of Things (IoT) workloads in consumer and industrial environments."
- **BIBTEX** (constructed):
```bibtex
@misc{aws2021securingiot,
  author       = {{Amazon Web Services}},
  title        = {Securing Internet of Things ({IoT}) with {AWS}},
  howpublished = {AWS Whitepaper},
  year         = {2021},
  month        = dec,
  url          = {https://docs.aws.amazon.com/whitepapers/latest/securing-iot-with-aws/securing-iot-with-aws.html},
  note         = {Publication date: December 20, 2021; marked "for historical reference only"; accessed 2026-11-03}
}
```
- **ACCESS / CONFLICT:**
  - WebFetch was served the whitepaper landing page twice.
  - Plain shell requests on 2026-11-03 to the same URL, to its subpages (`security-challenges-and-focus-areas.html`, `deploy-security-auditing-and-monitoring.html`), to its PDF, and to its `toc-contents.json` all returned **HTTP 302 to https://docs.aws.amazon.com/iot/latest/developerguide/security.html** ("Security in AWS IoT - AWS IoT Core").
  - WebFetch also received that developer-guide page for the subpages and for `document-history.html`.
  - The whitepaper's table of contents could therefore **not** be verified. Section names seen only in search results ("deploy security auditing and monitoring", "AWS IoT Greengrass – Software for edge computing", "Security challenges and focus areas", "Appendix 1 – AWS IoT services and security capabilities") are unverified.
- **FLAGS:** **[SOURCE REQUIRED]** if the manuscript wants to cite the 2021 whitepaper: it is archived ("historical reference only") and is being redirected. Recommendation: cite the IoT Lens (2025) as the current official AWS guidance, or cite the whitepaper with an archived copy.
- **Not used:** the AWS Prescriptive Guidance page `…/security-reference-architecture/secure-edge.html` appeared in search results, but the fetched content was the generic SRA core architecture, not IoT.

---

## Unresolved items (consolidated)

1. **Source 3:** The "conflicting publisher dates" could not be reproduced. All fetched sources give 6 July 2026, and the HTML was updated on 4 September 2026. Received and accepted dates are unknown. **[BIBLIOGRAPHIC VERIFICATION REQUIRED]**
2. **Source 4:** The ACM article number (261) appears on one portal only. The name appears as "Megías" or "Megias", and there are index date inconsistencies. **[BIBLIOGRAPHIC VERIFICATION REQUIRED]**
3. **Source 6:** No full text; the abstract comes from an index; the conference dates are unverified. **[SOURCE REQUIRED]**
4. **Source 8:** Online year 2025 versus issue year 2026; a year convention needs to be chosen. **[BIBLIOGRAPHIC VERIFICATION REQUIRED]**
5. **Sources 2 and 12:** ISO journal abbreviations are unverified. **[BIBLIOGRAPHIC VERIFICATION REQUIRED]**
6. **Source 10:** The IEEE publisher location is not in the registry record. **[BIBLIOGRAPHIC VERIFICATION REQUIRED]**
7. **Sources 4, 5, and 10:** Content was read from preprints. Re-check quotes against the VoRs. ACM DL and IEEE Xplore were blocked in this session.
8. **Sources 3 and 9:** The later sections were not examined because of HTML truncation.
9. **Source 13b:** The availability of the 2021 AWS whitepaper is inconsistent (redirected). **[SOURCE REQUIRED]** if cited.
