# C. Standards, Specifications, RFCs, Systems Literature and Dataset: Verified References

Manuscript: provenance-bound, trust-aware ingestion for IIoT edge-to-cloud pipelines (target: MDPI *Future Internet*).
Verification date: 3 November 2026. All fields below were taken from registry records or pages fetched during this task; nothing was filled from memory.

## How this was verified

- **Crossref:** `/home/claude/work/tools/crossref.py` (search/doi) plus direct `api.crossref.org/works/<DOI>` JSON dumps (subtitle, container, editors, ISBN, event).
- **RFCs:** `https://www.rfc-editor.org/rfc/rfcNNNN.json` and `.txt` (title, authors, date, status, stream, obsoletes/updates), cross-checked against Crossref (`10.17487/RFCNNNN`).
- **NIST:** CSRC landing pages (`csrc.nist.gov/pubs/...`), the NIST PDFs on `nvlpubs.nist.gov` (imprint and "How to Cite" blocks), and Crossref.
- **Standards bodies and specifications:** IEC webstore pages (title, edition, dates, lifecycle JSON), the ISA public TOC PDF, the OASIS spec HTML, the W3C TR page, the OPC Foundation Online Reference (Markdown export of the specification), DIN data via Crossref and Austrian Standards, and the IIC PDF via WebFetch.
- **USENIX papers:** USENIX presentation pages (BibTeX blocks), proceedings TOC PDFs, and printed page footers read with `pdftotext`.
- **HAI dataset:**
  - README via raw.githubusercontent.com.
  - Repository tree via `git clone --filter=blob:none --no-checkout`. No data blobs were downloaded.
  - File sizes via HTTP `Content-Length` (gz files) and Git LFS pointer `size` fields (LFS files).
  - CSV headers, first rows and last rows via HTTP Range requests (≤128 KiB per file).
  - Technical manual PDF from the repository.
  - CC BY-SA 4.0 deed and legal code from creativecommons.org.

**Access limitations met (so you know what was not used):**
- **dblp.org:** served a proof-of-work anti-bot page (Anubis), so dblp was not used.
- **DIN Media (dinmedia.de, din.de):** in maintenance during the whole session.
- **iiconsortium.org:** blocked curl with a Cloudflare challenge and S3 AccessDenied, so it was reached via WebFetch.
- **GitHub REST API:** not enabled for this session. github.com HTML pages return 403 to curl. Git and raw.githubusercontent.com worked.

**Flag legend:**
- **[VERIFIED]:** every field is traceable to a fetched record.
- **[VERIFIED – NOTE]:** verified, with a caveat you must act on.
- **[BIBLIOGRAPHIC VERIFICATION REQUIRED]:** the field could not be traced to a fetched source in this task.

Country names (e.g., "USA", "Germany", "Switzerland", "Canada") were appended to verified city names. The city or address itself is from the fetched source.

---

## Summary table

| # | Key(s) | Status | Action items |
|---|---|---|---|
| 1 | `nist_sp800_207` | VERIFIED | none |
| 2 | `nist_csf2` | VERIFIED | Corporate author (no personal authors) |
| 3 | `nist_sp800_82r3` | VERIFIED – NOTE | Rev. 4 **initial public draft** published 21 Sep 2026 (comments due 30 Nov 2026); Rev. 3 remains the final version |
| 4 | `nistir_8259a` | VERIFIED | CSRC now labels it "NIST IR 8259A"; the DOI and PDF use NISTIR 8259A |
| 5 | `iec62443_3_3`, `iec62443_4_2` | VERIFIED | FR names verified on IEC webstore and ISA TOC |
| 6 | `iic_iira_v110` | VERIFIED – NOTE | Issuing body on v1.10 cover is **Industry IoT Consortium**, not "Industrial Internet Consortium". Personal editors not retrievable |
| 7 | `din_spec_91345` | VERIFIED – NOTE | Publisher city [BIBLIOGRAPHIC VERIFICATION REQUIRED] (DIN Media site in maintenance) |
| 8 | `w3c_prov_dm` | VERIFIED | none |
| 9 | `openlineage_spec` | VERIFIED | Spec version 2-0-2 |
| 10 | `spiffe_spec`, `spiffe_x509svid`, `spire` | VERIFIED | none |
| 11 | `opa` | VERIFIED | none |
| 12 | `oasis_mqtt5` | VERIFIED | QoS facts below |
| 13 | `opcua_part14`, `iec62541_14_2026`, `opcua_part2` | VERIFIED – NOTE | Part 14 never uses the word "replay". Replay is addressed in Part 2 §5.1.6. IEC 62541-14 is now **Ed. 2.0 (2026)** |
| 14 | `rfc8032` `rfc8785` `rfc9162` `rfc6962` `rfc4303` `rfc9334` `rfc5280` `rfc8446` `rfc9846` `rfc9052` | VERIFIED – NOTE | **RFC 8446 is obsoleted by RFC 9846 (July 2026)**. RFC 6962 is obsoleted by RFC 9162 |
| 15 | `akidau2015dataflow` | VERIFIED | none |
| 16 | `wang2021kafka` | VERIFIED | none |
| 17 | `carbone2015flink` | VERIFIED | No DOI; stable URL given |
| 18 | `helland2012queue`, `helland2012cacm` | VERIFIED | Two venues; pick one |
| 19 | `shapiro2011crdt` | VERIFIED | none |
| 20 | `torresarias2019intoto` | VERIFIED | No DOI (USENIX) |
| 21 | `hasan2009fast` (+ `hasan2009tos`) | VERIFIED | No DOI for the FAST paper; the ACM TOS extended version has a DOI |
| 22 | `crosby2009tamper` | VERIFIED – NOTE | Printed pp. 317–333 (p. 334 blank). USENIX's own TOC header wrongly says "San Jose" |
| 23 | `merkle1988signature` | VERIFIED – NOTE | Publication year is **1988** (CRYPTO '87 proceedings) |
| 24 | `bernstein2012ed25519` | VERIFIED | none |
| 25 | `shin2020hai`, `shin2021hai`, `hai_github` | VERIFIED – NOTE | **License inconsistency in README** (CC BY-SA 4.0 vs CC BY 4.0 metadata). No LICENSE file. Column counts in the manual and README disagree with the files |

---

## Part A: Standards and guidance

### 1. NIST SP 800-207, Zero Trust Architecture. [VERIFIED]

- **KEY:** `nist_sp800_207`
- **VERIFIED CITATION (MDPI):** Rose, S.; Borchert, O.; Mitchell, S.; Connelly, S. *Zero Trust Architecture*; NIST Special Publication 800-207; National Institute of Standards and Technology: Gaithersburg, MD, USA, 2020. https://doi.org/10.6028/NIST.SP.800-207
- **Fields:**
  - Authors and affiliations (CSRC): Scott Rose (NIST), Oliver Borchert (NIST), Stu Mitchell (Stu2Labs), Sean Connelly (DHS).
  - Date: August 2020 (Crossref published-online 2020-08-11).
  - Length: 59 pages ("Natl. Inst. Stand. Technol. Spec. Publ. 800-207, 59 pages (August 2020)", from the PDF).
  - Imprint: "100 Bureau Drive (Mail Stop 8920) Gaithersburg, MD 20899-8920" (PDF).
  - Status: final. No supersession notice on CSRC as of 3 Nov 2026; the only planning note concerns unofficial translations.
- **TYPE:** Technical report (NIST Special Publication)
- **BIBTEX:**
```bibtex
@techreport{nist_sp800_207,
  author      = {Rose, Scott and Borchert, Oliver and Mitchell, Stu and Connelly, Sean},
  title       = {Zero Trust Architecture},
  institution = {National Institute of Standards and Technology},
  address     = {Gaithersburg, MD, USA},
  type        = {NIST Special Publication},
  number      = {800-207},
  year        = {2020},
  month       = aug,
  doi         = {10.6028/NIST.SP.800-207},
  url         = {https://doi.org/10.6028/NIST.SP.800-207}
}
```
- **SOURCES:** https://csrc.nist.gov/pubs/sp/800/207/final ; https://api.crossref.org/works/10.6028/NIST.SP.800-207 ; https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-207.pdf

### 2. NIST Cybersecurity Framework 2.0 (NIST CSWP 29). [VERIFIED]

- **KEY:** `nist_csf2`
- **VERIFIED CITATION (MDPI):** National Institute of Standards and Technology. *The NIST Cybersecurity Framework (CSF) 2.0*; NIST Cybersecurity White Paper (CSWP) 29; National Institute of Standards and Technology: Gaithersburg, MD, USA, 2024. https://doi.org/10.6028/NIST.CSWP.29
- **Fields:**
  - Exact title: "The NIST Cybersecurity Framework (CSF) 2.0".
  - Author: "National Institute of Standards and Technology" (CSRC Author(s) field). Crossref has no author.
  - Date Published: February 26, 2024 (CSRC; Crossref 2024-02-26).
  - NIST's own "How to Cite": "National Institute of Standards and Technology (2024) The NIST Cybersecurity Framework (CSF) 2.0. (National Institute of Standards and Technology, Gaithersburg, MD), NIST Cybersecurity White Paper (CSWP) NIST CSWP 29. https://doi.org/10.6028/NIST.CSWP.29" (PDF).
- **TYPE:** Technical report (NIST Cybersecurity White Paper)
- **BIBTEX:**
```bibtex
@techreport{nist_csf2,
  author      = {{National Institute of Standards and Technology}},
  title       = {The {NIST} Cybersecurity Framework ({CSF}) 2.0},
  institution = {National Institute of Standards and Technology},
  address     = {Gaithersburg, MD, USA},
  type        = {NIST Cybersecurity White Paper (CSWP)},
  number      = {29},
  year        = {2024},
  month       = feb,
  doi         = {10.6028/NIST.CSWP.29},
  url         = {https://doi.org/10.6028/NIST.CSWP.29},
  note        = {Published 26 February 2024}
}
```
- **SOURCES:** https://csrc.nist.gov/pubs/cswp/29/the-nist-cybersecurity-framework-csf-20/final ; https://api.crossref.org/works/10.6028/NIST.CSWP.29 ; https://nvlpubs.nist.gov/nistpubs/CSWP/NIST.CSWP.29.pdf

### 3. NIST SP 800-82 Rev. 3, Guide to Operational Technology (OT) Security. [VERIFIED – NOTE]

- **KEY:** `nist_sp800_82r3`
- **VERIFIED CITATION (MDPI):** Stouffer, K.; Pease, M.; Tang, C.Y.; Zimmerman, T.; Pillitteri, V.; Lightman, S.; Hahn, A.; Saravia, S.; Sherule, A.; Thompson, M. *Guide to Operational Technology (OT) Security*; NIST Special Publication 800-82, Revision 3; National Institute of Standards and Technology: Gaithersburg, MD, USA, 2023. https://doi.org/10.6028/NIST.SP.800-82r3
- **Fields:**
  - Authors (CSRC): Keith Stouffer, Michael Pease, CheeYee Tang, Timothy Zimmerman, Victoria Pillitteri, Suzanne Lightman (NIST); Adam Hahn, Stephanie Saravia, Aslam Sherule, Michael Thompson (MITRE).
  - NIST "How to Cite" writes "Tang CY". Crossref writes "Tang, CheeYee".
  - Date: September 2023 (Crossref 2023-09-28).
  - Supersedes SP 800-82 Rev. 2 (06/03/2015).
  - Title capitalization: CSRC and the PDF use "Security"; Crossref lowercases it.
- **NOTE:** The CSRC planning note (09/21/2026) announces the **initial public draft of SP 800-82 Rev. 4**, published September 21, 2026, with comments due November 30, 2026. The Rev. 4 author list differs (Stouffer, Pease, Tang, Hahn, Gilsinn, Rebori-Carretero, Alexander, Fialk, Silva). Cite Rev. 3 as the final publication. Optionally mention the Rev. 4 draft (https://csrc.nist.gov/pubs/sp/800/82/r4/ipd), but do not cite a draft as final.
- **TYPE:** Technical report (NIST Special Publication)
- **BIBTEX:**
```bibtex
@techreport{nist_sp800_82r3,
  author      = {Stouffer, Keith and Pease, Michael and Tang, CheeYee and Zimmerman, Timothy and Pillitteri, Victoria and Lightman, Suzanne and Hahn, Adam and Saravia, Stephanie and Sherule, Aslam and Thompson, Michael},
  title       = {Guide to Operational Technology ({OT}) Security},
  institution = {National Institute of Standards and Technology},
  address     = {Gaithersburg, MD, USA},
  type        = {NIST Special Publication},
  number      = {800-82, Rev. 3},
  year        = {2023},
  month       = sep,
  doi         = {10.6028/NIST.SP.800-82r3},
  url         = {https://doi.org/10.6028/NIST.SP.800-82r3}
}
```
- **SOURCES:** https://csrc.nist.gov/pubs/sp/800/82/r3/final ; https://csrc.nist.gov/pubs/sp/800/82/r4/ipd ; https://api.crossref.org/works/10.6028/NIST.SP.800-82r3 ; https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-82r3.pdf

### 4. NISTIR 8259A, IoT Device Cybersecurity Capability Core Baseline. [VERIFIED]

- **KEY:** `nistir_8259a`
- **VERIFIED CITATION (MDPI):** Fagan, M.; Megas, K.N.; Scarfone, K.; Smith, M. *IoT Device Cybersecurity Capability Core Baseline*; NISTIR 8259A; National Institute of Standards and Technology: Gaithersburg, MD, USA, 2020. https://doi.org/10.6028/NIST.IR.8259A
- **Fields:**
  - Authors (CSRC): Michael Fagan (NIST), Katerina Megas (NIST; Crossref "Katerina N" Megas), Karen Scarfone (Scarfone Cybersecurity), Matthew Smith (G2).
  - Date: May 2020; 23 pages (PDF: "23 pages (May 2020)").
  - Series label: the PDF and DOI use "NISTIR 8259A"; the current CSRC heading reads "NIST IR 8259A". Either is traceable.
  - Imprint (PDF): Gaithersburg, MD 20899-2000.
- **TYPE:** Technical report (NIST Interagency/Internal Report)
- **BIBTEX:**
```bibtex
@techreport{nistir_8259a,
  author      = {Fagan, Michael and Megas, Katerina N. and Scarfone, Karen and Smith, Matthew},
  title       = {{IoT} Device Cybersecurity Capability Core Baseline},
  institution = {National Institute of Standards and Technology},
  address     = {Gaithersburg, MD, USA},
  type        = {NIST Interagency or Internal Report (NISTIR)},
  number      = {8259A},
  year        = {2020},
  month       = may,
  doi         = {10.6028/NIST.IR.8259A},
  url         = {https://doi.org/10.6028/NIST.IR.8259A}
}
```
- **SOURCES:** https://csrc.nist.gov/pubs/ir/8259/a/final ; https://api.crossref.org/works/10.6028/NIST.IR.8259A ; https://nvlpubs.nist.gov/nistpubs/ir/2020/NIST.IR.8259A.pdf

### 5. IEC 62443-3-3 and IEC 62443-4-2. [VERIFIED]

#### 5a. IEC 62443-3-3:2013

- **KEY:** `iec62443_3_3`
- **VERIFIED CITATION (MDPI):** *IEC 62443-3-3:2013*; Industrial Communication Networks—Network and System Security—Part 3-3: System Security Requirements and Security Levels. International Electrotechnical Commission (IEC): Geneva, Switzerland, 2013.
- **Fields (IEC webstore, publication 7033):**
  - Exact title: "Industrial communication networks - Network and system security - Part 3-3: System security requirements and security levels".
  - International Standard, **Edition 1.0**, publication date **2013-08-07**.
  - ISBN 9782832264225; 80 pages; TC 65; stability date 2027.
  - "The contents of the corrigendum of April 2014 have been included in this copy." Lifecycle JSON: IEC 62443-3-3:2013/COR1:2014, 2014-04-24.
  - `underDevelopmentProduct: []`, i.e., no new edition listed as under development.
- **ISA equivalent (for information):** ISA-62443-3-3 (99.03.03)-2013, dated 12 August 2013 (isa.org TOC PDF header).
- **TYPE:** International Standard

#### 5b. IEC 62443-4-2:2019

- **KEY:** `iec62443_4_2`
- **VERIFIED CITATION (MDPI):** *IEC 62443-4-2:2019*; Security for Industrial Automation and Control Systems—Part 4-2: Technical Security Requirements for IACS Components. International Electrotechnical Commission (IEC): Geneva, Switzerland, 2019.
- **Fields (IEC webstore, publication 34421):**
  - Exact title: "Security for industrial automation and control systems - Part 4-2: Technical security requirements for IACS components".
  - **Edition 1.0**, publication date **2019-02-27**.
  - ISBN 9782832265970; 192 pages; TC 65; stability date 2027.
  - "The contents of the corrigendum of August 2022 have been included in this copy." Lifecycle: IEC 62443-4-2:2019/COR1:2022, 2022-08-30.
  - Nothing under development.
- **TYPE:** International Standard

#### Seven Foundational Requirements (content facts)

**Primary source:** the IEC webstore page for IEC 62443-4-2:2019, https://webstore.iec.ch/en/publication/34421. Abstract text, verbatim:

> "As defined in IEC TS 62443-1-1 there are a total of seven foundational requirements (FRs): a) identification and authentication control (IAC), b) use control (UC), c) system integrity (SI), d) data confidentiality (DC), e) restricted data flow (RDF), f) timely response to events (TRE), and g) resource availability (RA)."

**Corroborating source:** the ISA-62443-3-3 (99.03.03)-2013 public TOC PDF (https://www.isa.org/getmedia/4379f3a1-2687-4a0a-9d0f-20d743233c1b/ISA-62443-3-3_TOC.pdf), where the FRs are Clauses 5–11:

| FR | Name (ISA TOC wording) | Abbrev. (IEC webstore) | ISA-62443-3-3 clause |
|---|---|---|---|
| FR 1 | Identification and authentication control | IAC | 5 |
| FR 2 | Use control | UC | 6 |
| FR 3 | System integrity | SI | 7 |
| FR 4 | Data confidentiality | DC | 8 |
| FR 5 | Restricted data flow | RDF | 9 |
| FR 6 | Timely response to events | TRE | 10 |
| FR 7 | Resource availability | RA | 11 |

**Additional verified abstract facts:**
- IEC 62443-3-3:2013 "provides detailed technical control system requirements (SRs) associated with the seven foundational requirements (FRs) described in IEC 62443-1-1 including defining the requirements for control system capability security levels, SL-C(control system)".
- IEC 62443-4-2:2019 "provides detailed technical control system component requirements (CRs) associated with the seven foundational requirements (FRs) described in IEC TS 62443-1-1".
- The two pages differ: 3-3 says "IEC 62443-1-1", 4-2 says "IEC TS 62443-1-1".

**BIBTEX:**
```bibtex
@misc{iec62443_3_3,
  author       = {{International Electrotechnical Commission}},
  title        = {{IEC} 62443-3-3:2013 Industrial communication networks -- Network and system security -- Part 3-3: System security requirements and security levels},
  howpublished = {International Standard, Edition 1.0},
  publisher    = {International Electrotechnical Commission},
  address      = {Geneva, Switzerland},
  year         = {2013},
  month        = aug,
  isbn         = {9782832264225},
  url          = {https://webstore.iec.ch/en/publication/7033},
  note         = {Published 2013-08-07; Corrigendum 1 (2014-04-24) included}
}
@misc{iec62443_4_2,
  author       = {{International Electrotechnical Commission}},
  title        = {{IEC} 62443-4-2:2019 Security for industrial automation and control systems -- Part 4-2: Technical security requirements for {IACS} components},
  howpublished = {International Standard, Edition 1.0},
  publisher    = {International Electrotechnical Commission},
  address      = {Geneva, Switzerland},
  year         = {2019},
  month        = feb,
  isbn         = {9782832265970},
  url          = {https://webstore.iec.ch/en/publication/34421},
  note         = {Published 2019-02-27; Corrigendum 1 (2022-08-30) included}
}
```
- **SOURCES:** https://webstore.iec.ch/en/publication/7033 ; https://webstore.iec.ch/en/publication/34421 (IEC address in page footer: "3 rue de Varembé PO Box 131 CH-1211 Geneva 20 Switzerland") ; https://www.isa.org/getmedia/4379f3a1-2687-4a0a-9d0f-20d743233c1b/ISA-62443-3-3_TOC.pdf

### 6. Industrial Internet Reference Architecture (IIRA), latest version. [VERIFIED – NOTE]

- **KEY:** `iic_iira_v110`
- **VERIFIED CITATION (MDPI):** Industry IoT Consortium. *The Industrial Internet Reference Architecture*, Version 1.10; An Industry IoT Consortium Foundational Document; Industry IoT Consortium, 7 November 2022. Available online: https://www.iiconsortium.org/wp-content/uploads/sites/2/2022/11/IIRA-v1.10.pdf (accessed on 3 November 2026).
- **Fields (from the PDF cover via WebFetch):**
  - Title "The Industrial Internet Reference Architecture"; "Version 1.10"; date printed "2022-11-07".
  - Cover line "An Industry IoT Consortium Foundational Document".
- **NOTES:**
  1. **Issuing-body name:** the v1.10 cover says **Industry IoT Consortium**. "Industrial Internet Consortium" appears in IIC site post titles from 2019–2021, and 2022 posts use "Industry IoT Consortium". Use the name on the cover. The exact rename date was not verified.
  2. **Latest version:** v1.10 (2022-11-07) is the newest version found. The IIC landing page (https://www.iiconsortium.org/iira/) still shows v1.9 text and a v1.9 contributor list, so it is stale. A third-party article, "IIC Revises IIRA Version 1.10" (embeddedcomputing.com), was seen in search results. Nothing newer was found in searches on 3 Nov 2026.
  3. **Personal authors/editors** (section "Authors & Legal Notice", p. 70 per the TOC) could not be extracted from the PDF. If you need personal authors: [BIBLIOGRAPHIC VERIFICATION REQUIRED]. Corporate authorship, as above, is fully verified.
  4. curl to iiconsortium.org was blocked (Cloudflare challenge; PDF returned S3 AccessDenied). The PDF content was retrieved with WebFetch.
- **TYPE:** Technical report / consortium specification (web PDF)
- **BIBTEX:**
```bibtex
@misc{iic_iira_v110,
  author       = {{Industry IoT Consortium}},
  title        = {The Industrial Internet Reference Architecture, Version 1.10},
  howpublished = {An Industry IoT Consortium Foundational Document},
  year         = {2022},
  month        = nov,
  url          = {https://www.iiconsortium.org/wp-content/uploads/sites/2/2022/11/IIRA-v1.10.pdf},
  note         = {Dated 2022-11-07. Accessed on 3 November 2026}
}
```
- **SOURCES:** https://www.iiconsortium.org/wp-content/uploads/sites/2/2022/11/IIRA-v1.10.pdf ; https://www.iiconsortium.org/iira/ ; search-result listing of https://embeddedcomputing.com/application/industrial/industrial-iot/iic-revises-iira-version-110-eyeing-trends-in-industry

### 7. RAMI 4.0, DIN SPEC 91345:2016-04. [VERIFIED – NOTE]

- **KEY:** `din_spec_91345`
- **VERIFIED CITATION (MDPI):** *DIN SPEC 91345:2016-04*; Reference Architecture Model Industrie 4.0 (RAMI4.0). DIN Deutsches Institut für Normung, 2016. https://doi.org/10.31030/2436156
- **Fields:**
  - English title (Austrian Standards): "Reference Architecture Model Industrie 4.0 (RAMI4.0)".
  - German title (Crossref): "DIN SPEC 91345:2016-04, Referenzarchitekturmodell Industrie 4.0 (RAMI4.0)".
  - Issue date: "2016 04" (April 2016).
  - Publisher listed by Austrian Standards: "DIN Deutsches Institut für Normung". DOI registrant in Crossref: "DIN Media GmbH" (type `standard`).
  - 40 pages; languages German and English; status "Current".
  - The Crossref date 2019-03-31 is the DOI record date, **not** the issue date. Use 2016.
- **NOTES:** Publisher city/address and the 2016 imprint name: [BIBLIOGRAPHIC VERIFICATION REQUIRED]. DIN Media (dinmedia.de) and din.de were in maintenance at every attempt, so the DIN product page (https://www.dinmedia.de/en/technical-rule/din-spec-91345/250940128) could not be read. Leave the city out, or verify it before submission.
- **TYPE:** Standard (DIN SPEC)
- **BIBTEX:**
```bibtex
@misc{din_spec_91345,
  author       = {{DIN Deutsches Institut f{\"u}r Normung}},
  title        = {{DIN SPEC} 91345:2016-04 Reference Architecture Model Industrie 4.0 ({RAMI4.0})},
  howpublished = {DIN SPEC (German/English), 40 pages},
  year         = {2016},
  month        = apr,
  doi          = {10.31030/2436156},
  url          = {https://doi.org/10.31030/2436156},
  note         = {German title: Referenzarchitekturmodell Industrie 4.0 (RAMI4.0)}
}
```
- **SOURCES:** https://api.crossref.org/works/10.31030/2436156 ; https://www.austrian-standards.at/en/shop/din-spec-91345-2016-04~p2222971

### 8. W3C PROV-DM: The PROV Data Model. [VERIFIED]

- **KEY:** `w3c_prov_dm`
- **VERIFIED CITATION (MDPI):** Moreau, L.; Missier, P., Eds. *PROV-DM: The PROV Data Model*; W3C Recommendation, 30 April 2013. Available online: http://www.w3.org/TR/2013/REC-prov-dm-20130430/ (accessed on 3 November 2026).
- **Fields (w3.org/TR/prov-dm/):**
  - "W3C Recommendation 30 April 2013".
  - Editors: Luc Moreau (University of Southampton), Paolo Missier (Newcastle University). A separate contributor list exists; contributors are not editors.
  - This version: http://www.w3.org/TR/2013/REC-prov-dm-20130430/ ; Latest: http://www.w3.org/TR/prov-dm/
  - The page says "Please refer to the errata for this document".
- **TYPE:** W3C Recommendation (web specification)
- **BIBTEX:**
```bibtex
@misc{w3c_prov_dm,
  editor       = {Moreau, Luc and Missier, Paolo},
  title        = {{PROV-DM}: The {PROV} Data Model},
  howpublished = {W3C Recommendation},
  year         = {2013},
  month        = apr,
  url          = {http://www.w3.org/TR/2013/REC-prov-dm-20130430/},
  note         = {30 April 2013. Latest version: http://www.w3.org/TR/prov-dm/. Accessed on 3 November 2026}
}
```
- **SOURCES:** https://www.w3.org/TR/prov-dm/ (served the 30 April 2013 REC)

### 9. OpenLineage specification. [VERIFIED]

- **KEY:** `openlineage_spec`
- **VERIFIED CITATION (MDPI):** OpenLineage Project. *OpenLineage Specification*, Spec Version 2-0-2; LF AI & Data Foundation. Available online: https://openlineage.io/spec/2-0-2/OpenLineage.json (accessed on 3 November 2026).
- **Fields:**
  - The spec "is formalized as a JsonSchema [OpenLineage.json]"; an OpenAPI spec (OpenLineage.yml) is also provided (spec/OpenLineage.md).
  - JSON Schema `$id` = `https://openlineage.io/spec/2-0-2/OpenLineage.json` (resolves, HTTP 200).
  - Human-readable spec: https://github.com/OpenLineage/OpenLineage/blob/main/spec/OpenLineage.md (content verified via raw.githubusercontent.com).
  - **Maintaining body:** "OpenLineage is an LF AI & Data Foundation Graduate project" (README). Website footer: "Copyright © 2026 The Linux Foundation®". License Apache-2.0.
  - Repository HEAD a5fba2187b4d; latest release tag 1.55.0 (git ls-remote, 3 Nov 2026).
- **TYPE:** Open specification (web)
- **BIBTEX:**
```bibtex
@misc{openlineage_spec,
  author       = {{OpenLineage Project}},
  title        = {{OpenLineage} Specification (spec version 2-0-2)},
  howpublished = {LF AI \& Data Foundation project; JSON Schema and OpenAPI specification},
  url          = {https://openlineage.io/spec/2-0-2/OpenLineage.json},
  note         = {Spec text: https://github.com/OpenLineage/OpenLineage/blob/main/spec/OpenLineage.md. Accessed on 3 November 2026}
}
```
- **SOURCES:** https://raw.githubusercontent.com/OpenLineage/OpenLineage/main/README.md ; https://raw.githubusercontent.com/OpenLineage/OpenLineage/main/spec/OpenLineage.md ; https://raw.githubusercontent.com/OpenLineage/OpenLineage/main/spec/OpenLineage.json ; https://openlineage.io/

### 10. SPIFFE specification / X.509-SVID, and SPIRE. [VERIFIED]

- **KEYS:** `spiffe_spec`, `spiffe_x509svid`, `spire`
- **VERIFIED CITATIONS (MDPI):**
  - SPIFFE Project. *Secure Production Identity Framework for Everyone (SPIFFE)*. Available online: https://github.com/spiffe/spiffe/blob/main/standards/SPIFFE.md (accessed on 3 November 2026).
  - SPIFFE Project. *The X.509 SPIFFE Verifiable Identity Document*. Available online: https://github.com/spiffe/spiffe/blob/main/standards/X509-SVID.md (accessed on 3 November 2026).
  - SPIFFE Project. *SPIRE*. Available online: https://github.com/spiffe/spire (accessed on 3 November 2026).
- **Fields:**
  - Both standards carry "Stability: Stable" (see STABILITY.md). The standards list in the spiffe/spiffe README includes SPIFFE.md, SPIFFE-ID.md, X509-SVID.md, JWT-SVID.md, Trust Domain and Bundle, Workload Endpoint, Workload API, Federation, Broker API/Endpoint.
  - **Maintaining body:** "SPIFFE is a graduated project of the Cloud Native Computing Foundation (CNCF)" and "SPIRE is a graduated project of the Cloud Native Computing Foundation (CNCF)" (READMEs). Governance is by the SPIFFE Steering Committee (SSC). spiffe.io footer: "SPIFFE and SPIRE are graduate projects of the Cloud Native Computing Foundation".
  - spiffe/spiffe HEAD 03e916d8f920 (no release tags). spiffe/spire HEAD b1fb5d5352d1; latest release tag v1.15.5. SPIRE docs: https://spiffe.io/docs/latest/spire-about/ ("About SPIRE").
- **TYPE:** Open specification (web) / open-source software
- **BIBTEX:**
```bibtex
@misc{spiffe_spec,
  author       = {{SPIFFE Project}},
  title        = {Secure Production Identity Framework for Everyone ({SPIFFE})},
  howpublished = {CNCF graduated project; specification (Stability: Stable)},
  url          = {https://github.com/spiffe/spiffe/blob/main/standards/SPIFFE.md},
  note         = {Accessed on 3 November 2026}
}
@misc{spiffe_x509svid,
  author       = {{SPIFFE Project}},
  title        = {The {X.509} {SPIFFE} Verifiable Identity Document},
  howpublished = {CNCF graduated project; specification (Stability: Stable)},
  url          = {https://github.com/spiffe/spiffe/blob/main/standards/X509-SVID.md},
  note         = {Accessed on 3 November 2026}
}
@misc{spire,
  author       = {{SPIFFE Project}},
  title        = {{SPIRE}},
  howpublished = {CNCF graduated project; open-source software, release v1.15.5 (latest tag on 3 November 2026)},
  url          = {https://github.com/spiffe/spire},
  note         = {Accessed on 3 November 2026}
}
```
- **SOURCES:** https://raw.githubusercontent.com/spiffe/spiffe/main/README.md ; https://raw.githubusercontent.com/spiffe/spiffe/main/standards/X509-SVID.md ; https://raw.githubusercontent.com/spiffe/spiffe/main/standards/SPIFFE.md ; https://raw.githubusercontent.com/spiffe/spire/main/README.md ; https://spiffe.io/ ; git ls-remote of both repos

### 11. Open Policy Agent (OPA). [VERIFIED]

- **KEY:** `opa`
- **VERIFIED CITATION (MDPI):** Open Policy Agent. Available online: https://www.openpolicyagent.org/ (accessed on 3 November 2026).
- **Fields:**
  - Site title: "Open Policy Agent - Homepage | Open Policy Agent".
  - **Maintaining body:** "Open Policy Agent is a Cloud Native Computing Foundation Graduated project" (homepage). The README says "OPA is proud to be a graduated project in the Cloud Native Computing Foundation (CNCF)" and links the CNCF graduation announcement dated 2021-02-04.
  - "© 2026 Open Policy Agent contributors. Licensed under the Apache License, Version 2.0" (homepage footer).
  - Repository https://github.com/open-policy-agent/opa (HEAD db327b4b7d0c; latest release tag v1.22.0).
- **TYPE:** Open-source software (web)
- **BIBTEX:**
```bibtex
@misc{opa,
  author       = {{Open Policy Agent contributors}},
  title        = {Open Policy Agent ({OPA})},
  howpublished = {CNCF graduated project; open-source software, release v1.22.0 (latest tag on 3 November 2026)},
  url          = {https://www.openpolicyagent.org/},
  note         = {Source: https://github.com/open-policy-agent/opa. Accessed on 3 November 2026}
}
```
- **SOURCES:** https://www.openpolicyagent.org/ ; https://raw.githubusercontent.com/open-policy-agent/opa/main/README.md

### 12. MQTT Version 5.0, OASIS Standard. [VERIFIED]

- **KEY:** `oasis_mqtt5`
- **VERIFIED CITATION (MDPI):** Banks, A.; Briggs, E.; Borgendale, K.; Gupta, R., Eds. *MQTT Version 5.0*; OASIS Standard; OASIS Open, 7 March 2019. Available online: https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html (accessed on 3 November 2026).
- **Fields:**
  - "MQTT Version 5.0 / OASIS Standard / 07 March 2019".
  - Editors: Andrew Banks (IBM), Ed Briggs (Microsoft), Ken Borgendale (IBM), Rahul Gupta (IBM).
  - TC: OASIS Message Queuing Telemetry Transport (MQTT) TC; Chair Richard Coppen (IBM).
  - Authoritative format: .docx. HTML and PDF are also published.
  - Supersedes MQTT Version 3.1.1 (OASIS Standard, 29 October 2014).
  - The spec's own citation format: "[mqtt-v5.0] MQTT Version 5.0. Edited by Andrew Banks, Ed Briggs, Ken Borgendale, and Rahul Gupta. 07 March 2019. OASIS Standard. https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html. Latest version: https://docs.oasis-open.org/mqtt/mqtt/v5.0/mqtt-v5.0.html."
  - On 3 Nov 2026 the "Latest version" HTML was byte-identical to the 07 March 2019 OS HTML. No later revision exists in the v5.0 directory (cos01, cos02, cs01, cs02, csprd01, csprd02, os).
- **TYPE:** Standard (OASIS)

#### Content facts: QoS definitions (MQTT 5.0 OS, Section 4.3)

- **Abstract** (three QoS levels):
  - "'At least once', where messages are assured to arrive but duplicates can occur."
  - "'Exactly once', where messages are assured to arrive exactly once."
- **§4.3, scope of the guarantees** (key for the manuscript's argument):
  - "The delivery protocol is symmetric, in the description below the Client and Server can each take the role of either sender or receiver. The delivery protocol is concerned solely with the delivery of an application message from a single sender to a single receiver. When the Server is delivering an Application Message to more than one Client, each Client is treated independently."
  - So the guarantees are **per hop** (client→server or server→client), not end-to-end publisher→subscriber.
- **§4.3.1 QoS 0: At most once delivery:** "The message arrives at the receiver either once or not at all."
- **§4.3.2 QoS 1: At least once delivery:**
  - "This Quality of Service level ensures that the message arrives at the receiver at least once. A QoS 1 PUBLISH packet has a Packet Identifier in its Variable Header and is acknowledged by a PUBACK packet."
  - Duplicates arise by design: "After it has sent a PUBACK packet the receiver MUST treat any incoming PUBLISH packet that contains the same Packet Identifier as being a new Application Message, irrespective of the setting of its DUP flag [MQTT-4.3.2-5]."
- **§4.3.3 QoS 2: Exactly once delivery:**
  - "This is the highest Quality of Service level, for use when neither loss nor duplication of messages are acceptable." It uses "a two-step acknowledgement process" (PUBREC, PUBREL, PUBCOMP).
  - Receiver: "Until it has received the corresponding PUBREL packet, the receiver MUST acknowledge any subsequent PUBLISH packet with the same Packet Identifier by sending a PUBREC. It MUST NOT cause duplicate messages to be delivered to any onward recipients in this case [MQTT-4.3.3-10]."
  - Receiver: "After it has sent a PUBCOMP, the receiver MUST treat any subsequent PUBLISH packet that contains that Packet Identifier as being a new Application Message [MQTT-4.3.3-12]."
- **§4.4 Message delivery retry:** "When a Client reconnects with Clean Start set to 0 and a session is present, both the Client and Server MUST resend any unacknowledged PUBLISH packets (where QoS > 0) and PUBREL packets using their original Packet Identifiers. This is the only circumstance where a Client or Server is REQUIRED to resend messages. Clients and Servers MUST NOT resend messages at any other time [MQTT-4.4.0-1]."
- **Implication you may state (paraphrase, not a quote):** QoS 1/2 are protocol-level, single-hop guarantees keyed by reusable Packet Identifiers within a session. They do not give application-level, end-to-end idempotence across reconnects without session state, broker restarts, or multi-hop bridges. Application-level dedup keys are still needed.

- **BIBTEX:**
```bibtex
@misc{oasis_mqtt5,
  editor       = {Banks, Andrew and Briggs, Ed and Borgendale, Ken and Gupta, Rahul},
  title        = {{MQTT} Version 5.0},
  howpublished = {OASIS Standard},
  publisher    = {OASIS Open},
  year         = {2019},
  month        = mar,
  url          = {https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html},
  note         = {07 March 2019. Latest version: https://docs.oasis-open.org/mqtt/mqtt/v5.0/mqtt-v5.0.html. Accessed on 3 November 2026}
}
```
- **SOURCES:** https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html ; https://docs.oasis-open.org/mqtt/mqtt/v5.0/mqtt-v5.0.html ; https://docs.oasis-open.org/mqtt/mqtt/v5.0/

### 13. OPC UA Part 14: PubSub (OPC 10000-14 / IEC 62541-14). [VERIFIED – NOTE]

#### 13a. OPC Foundation specification (recommended for technical claims)

- **KEY:** `opcua_part14`
- **VERIFIED CITATION (MDPI):** OPC Foundation. *OPC 10000-14: OPC Unified Architecture—Part 14: PubSub*, Release 1.05.06; OPC Foundation, 2025. Available online: https://reference.opcfoundation.org/specs/OPC-10000-14/v1.05.06 (accessed on 3 November 2026).
- **Fields (OPC Foundation Online Reference):**
  - Page title "OPC-10000-14 – OPC Unified Architecture - Part 14: PubSub".
  - Document "OPC 10000-14"; **Release Version 1.05.06**; **Publication Date 2025-10-22**.
  - Version history on the page: 1.05.06 (2025-10-22, current) and 1.04 (2018-02-06).
  - The Markdown export header reads "SPDX-License-Identifier: LicenseRef-OPC-Specification-1.15".
  - The site says "The official version is considered correct if there are differences with this website."

#### 13b. IEC edition

- **KEY:** `iec62541_14_2026`
- **VERIFIED CITATION (MDPI):** *IEC 62541-14:2026*; OPC Unified Architecture—Part 14: PubSub. International Electrotechnical Commission (IEC): Geneva, Switzerland, 2026.
- **Fields (IEC webstore 82257):**
  - Exact title "OPC unified architecture - Part 14: PubSub".
  - **Edition 2.0**, publication date **2026-01-12**; ISBN 9782832708439; 316 pages; stability date 2028.
  - "This second edition cancels and replaces the first edition published in 2020."
  - Predecessor (webstore 61108): IEC 62541-14:2020, "OPC Unified Architecture - Part 14: PubSub", Ed. 1.0, 2020-07-08, ISBN 9782832285770, 380 pages, status "Revised", withdrawal date 2026-01-12.
- **NOTES:**
  1. The webstore does not say which OPC release (1.05.0x) IEC 62541-14:2026 corresponds to. Do not assert a correspondence.
  2. The 2026 webstore abstract's "significant technical changes" list ("Quantity Model", "ValuePrecision Property") reads as unrelated to PubSub, possibly a webstore text error. Do not cite those change items.
  3. Cite **OPC 10000-14 v1.05.06** for section-level technical claims, because that is the text actually read. Cite IEC 62541-14:2026 only as the international-standard counterpart.

#### 13c. OPC 10000-2 (needed for the replay claim)

- **KEY:** `opcua_part2`
- **VERIFIED CITATION (MDPI):** OPC Foundation. *OPC 10000-2: OPC Unified Architecture—Part 2: Security Model*, Release 1.05.06; OPC Foundation, 2025. Available online: https://reference.opcfoundation.org/specs/OPC-10000-2/v1.05.06 (accessed on 3 November 2026).
- **Fields:** Release Version 1.05.06; Publication Date 2025-10-22.

#### Content facts: what PubSub message security provides (OPC 10000-14 v1.05.06, section numbers as printed)

- **§5.3.5 Message security:**
  - Levels: "No security", "Signing but no encryption", "Signing and encryption".
  - "Message security is end-to-end security (from Publisher to Subscriber) and requires common knowledge of the cryptographic keys".
  - Keys are managed per SecurityGroup (§5.3.7). Key distribution framework is in §5.4.5. Parameters are in §6.2.5.
  - "The message security for PubSub is independent of the transport protocol mapping and is completely defined by OPC UA."
- **§5.3.6 Transport security:**
  - "This could be TLS for broker-based middleware and DTLS for broker-less middleware."
  - "Transport security may be hop-by-hop security with some risk of man-in-the-middle attacks. It also requires trusting the Broker since the Broker can read the messages."
- **§5.3.7 SecurityGroup:** "The security keys are used to encrypt and decrypt NetworkMessages and to generate and check signatures on a NetworkMessage." Identified by SecurityGroupId and managed by a Security Key Service (SKS).
- **§5.4.5 Security Key Service** (5.4.5.1 General): the SKS "provides keys for message security that can be used by the Publisher to sign and encrypt NetworkMessages and by the Subscriber to verify the signature of NetworkMessages and to decrypt them". Keys are pulled with GetSecurityKeys (Method in **§8.3.2**) or pushed with SetSecurityKeys (§9.1.3.3). §5.4.5.1's internal cross-references say "8.2"; the headings are 8.3/8.3.2, so cite the headings.
- **§6.2.5 Shared PubSubGroup parameters:** §6.2.5.2 SecurityMode (MessageSecurityMode, from OPC 10000-4); §6.2.5.3 SecurityGroupId; §6.2.5.4 SecurityKeyServices.
- **§7.2.3 SequenceNumber in headers:**
  - "A SequenceNumber is a monotonically increasing number … The SequenceNumber starts at 0 and shall be incremented by exactly one for each message."
  - Newer/older test: "(received sequence number -1 - last processed sequence number) modulo 2^N". Results above the upper bound mean the message "is older than (or same as) than the last processed message and it shall be ignored unless reordering of messages is required". Bounds are in Table 152 (UInt16/UInt32).
  - Subscribers discard sequence records after "two times the message receive timeout".
- **§7.2.4.4.2 NetworkMessage layout, Table 154 (UADP):**
  - ExtendedFlags1 bit 4 "SecurityHeader enabled" ("If the SecurityMode in the configuration is SIGN or SIGNANDENCRYPT, this flag shall be set").
  - GroupHeader **SequenceNumber** (UInt16, per §7.2.3).
  - **SecurityHeader** fields:
    - **SecurityFlags**: bit 0 Signed, bit 1 Encrypted, bit 2 SecurityFooter enabled, bit 3 Force key reset.
    - **SecurityTokenId** (IntegerId): "The ID of the security token that identifies the security key in a SecurityGroup".
    - **NonceLength**.
    - **MessageNonce**: "A number used exactly once for a given security key. For a given security key a unique nonce shall be generated for every NetworkMessage".
    - **SecurityFooterSize**.
  - Trailer: **SecurityFooter** and **Signature** ("The signature of the NetworkMessage").
- **§7.2.4.4.3 UADP message security:**
  - Algorithms come from the SecurityPolicy (SymmetricEncryptionAlgorithm and SymmetricSignatureAlgorithm in OPC 10000-7).
  - Key data from GetSecurityKeys = SigningKey, EncryptingKey, KeyNonce (Table 155).
  - **§7.2.4.4.3.2 AES-CTR:** MessageNonce = Random[4] + **SequenceNumber (UInt32)**, which "is reset to 1 after the key and SecurityTokenId are updated in the Publisher" (Table 156). Counter block in Table 157.
  - "The signature is calculated on the entire NetworkMessage including any encrypted data."
  - "When a Subscriber or a Publisher receives a NetworkMessage, it shall verify the signature before processing the payload. If verification fails, it drops the NetworkMessage."
- **§7.2.4.5.4 DataSetMessage header (Table 162):** DataSetMessageSequenceNumber (UInt16) "Sequence number for each new DataSetMessage as defined in 7.2.3".
- **§8.3.2 GetSecurityKeys:**
  - SecurityTokenId "starts at 1 and is incremented by 1 each time the KeyLifetime elapses even if no keys are requested". It restarts at 1 after the UInt32 maximum.
  - Subscribers must expect overlap of previous/next keys ("Due to network latency, out of order delivery…").
- **§7.3.4.1 (MQTT mapping, General):** "Applications that require end-to-end message security with MQTT need to use the UADP NetworkMessages and binary message encoding … JSON encoded message bodies need to rely on the security mechanisms provided by MQTT and the MQTT broker." Annex B.3.1 says the same for AMQP.
- **Replay detection:**
  - **The word "replay" does not occur anywhere in OPC 10000-14 v1.05.06** (full-text search of the Markdown export).
  - Part 14 supplies the mechanisms: signed headers with sequence numbers, a nonce per key, and the §7.2.3 rule to ignore not-newer messages.
  - The explicit replay statement is in **OPC 10000-2 v1.05.06 §5.1.6 "Message replay"** (threat described in §4.3.6): "OPC UA PubSub uses PublisherIds, DataSetWriterIds, Timestamps, network message numbers and sequence numbers in published messages. When Messages are optionally signed they cannot be changed without detection, therefore it can be configured that replay of a message is not possible. It is worth noting that PubSub does allow the disabling of fields in a message. The disabling of the Timestamp, network message number and sequence number, could allow replay attacks. If a replay attack is of concern in a CSMS, then these fields need to be enabled."
  - Manuscript wording: replay resistance in PubSub is **configuration-dependent** (signing plus enabled sequence numbers, timestamps and network message numbers). It is not intrinsic to Part 14.

- **BIBTEX:**
```bibtex
@misc{opcua_part14,
  author       = {{OPC Foundation}},
  title        = {{OPC} 10000-14: {OPC} Unified Architecture -- Part 14: {PubSub}},
  howpublished = {Release 1.05.06},
  year         = {2025},
  month        = oct,
  url          = {https://reference.opcfoundation.org/specs/OPC-10000-14/v1.05.06},
  note         = {Published 2025-10-22. Accessed on 3 November 2026}
}
@misc{iec62541_14_2026,
  author       = {{International Electrotechnical Commission}},
  title        = {{IEC} 62541-14:2026 {OPC} unified architecture -- Part 14: {PubSub}},
  howpublished = {International Standard, Edition 2.0},
  publisher    = {International Electrotechnical Commission},
  address      = {Geneva, Switzerland},
  year         = {2026},
  month        = jan,
  isbn         = {9782832708439},
  url          = {https://webstore.iec.ch/en/publication/82257},
  note         = {Published 2026-01-12; replaces IEC 62541-14:2020 (Ed. 1.0)}
}
@misc{opcua_part2,
  author       = {{OPC Foundation}},
  title        = {{OPC} 10000-2: {OPC} Unified Architecture -- Part 2: Security Model},
  howpublished = {Release 1.05.06},
  year         = {2025},
  month        = oct,
  url          = {https://reference.opcfoundation.org/specs/OPC-10000-2/v1.05.06},
  note         = {Published 2025-10-22. Accessed on 3 November 2026}
}
```
- **SOURCES:** https://reference.opcfoundation.org/specs/OPC-10000-14 ; https://reference.opcfoundation.org/specs/OPC-10000-14/v1.05.06 ; https://reference.opcfoundation.org/specs/OPC-10000-14/v1.05.06/t63916693085/download/markdown ; https://reference.opcfoundation.org/specs/OPC-10000-2/v1.05.06/t63916693107/download/markdown ; https://webstore.iec.ch/en/publication/82257 ; https://webstore.iec.ch/en/publication/61108

---

## Part B: IETF RFCs (item 14)

All fields come from `https://www.rfc-editor.org/rfc/rfcNNNN.json` and the RFC text headers, cross-checked with Crossref (`10.17487/RFCNNNN`, publisher "RFC Editor"). RFC Editor records list authors by initials only, so full given names are not used. **TYPE:** IETF/IRTF/Independent RFC (report), cited as `@misc` with DOI.

| Key | RFC | Exact title | Authors | Date | Stream / Category | DOI | Status notes |
|---|---|---|---|---|---|---|---|
| `rfc8032` | 8032 | Edwards-Curve Digital Signature Algorithm (EdDSA) | S. Josefsson, I. Liusvaara | January 2017 | IRTF (source: Crypto Forum) / Informational | 10.17487/RFC8032 | 60 pp. |
| `rfc8785` | 8785 | JSON Canonicalization Scheme (JCS) | A. Rundgren, B. Jordan, S. Erdtman | June 2020 | Independent Submission / Informational | 10.17487/RFC8785 | 20 pp. |
| `rfc9162` | 9162 | Certificate Transparency Version 2.0 | B. Laurie, E. Messeri, R. Stradling | December 2021 | IETF (Public Notary Transparency) / Experimental | 10.17487/RFC9162 | Obsoletes RFC 6962; 53 pp. |
| `rfc6962` | 6962 | Certificate Transparency | B. Laurie, A. Langley, E. Kasper | June 2013 | IETF (non-WG) / Experimental | 10.17487/RFC6962 | **Obsoleted by RFC 9162**; 27 pp. |
| `rfc4303` | 4303 | IP Encapsulating Security Payload (ESP) | S. Kent | December 2005 | IETF (IP Security Protocol) / Proposed Standard | 10.17487/RFC4303 | Obsoletes RFC 2406; 44 pp. |
| `rfc9334` | 9334 | Remote ATtestation procedureS (RATS) Architecture | H. Birkholz, D. Thaler, M. Richardson, N. Smith, W. Pan | January 2023 | IETF (RATS) / Informational | 10.17487/RFC9334 | 46 pp. |
| `rfc5280` | 5280 | Internet X.509 Public Key Infrastructure Certificate and Certificate Revocation List (CRL) Profile | D. Cooper, S. Santesson, S. Farrell, S. Boeyen, R. Housley, W. Polk | May 2008 | IETF (PKIX) / Proposed Standard | 10.17487/RFC5280 | Updated by RFC 6818, 8398, 8399, 9549, 9598, 9608, 9618, 9925, 10007; 151 pp. |
| `rfc8446` | 8446 | The Transport Layer Security (TLS) Protocol Version 1.3 | E. Rescorla | August 2018 | IETF (TLS) / Proposed Standard | 10.17487/RFC8446 | **Obsoleted by RFC 9846**; 160 pp. |
| `rfc9846` | 9846 | The Transport Layer Security (TLS) Protocol Version 1.3 | E. Rescorla | July 2026 | IETF (TLS) / Proposed Standard | 10.17487/RFC9846 | Obsoletes RFC 5077, 5246, 6961, 7627, 8422, 8446; 137 pp. |
| `rfc9052` | 9052 | CBOR Object Signing and Encryption (COSE): Structures and Process | J. Schaad | August 2022 | IETF (COSE) / **Internet Standard** | 10.17487/RFC9052 | Obsoletes RFC 8152; updated by RFC 9338; 66 pp. |

**Action on TLS 1.3:** as of 3 Nov 2026 the RFC Editor lists **RFC 8446 as obsoleted by RFC 9846 (July 2026)**, which has the same title and author. For a 2026 submission, cite RFC 9846 as the current TLS 1.3 specification, or cite both ("RFC 8446, obsoleted by RFC 9846").

**Action on CT:** RFC 6962 is obsoleted by RFC 9162. Cite RFC 9162 for CT v2.0 and RFC 6962 only for CT v1 structures specifically.

### VERIFIED CITATIONS (MDPI)

- Josefsson, S.; Liusvaara, I. *Edwards-Curve Digital Signature Algorithm (EdDSA)*; RFC 8032; RFC Editor, 2017. https://doi.org/10.17487/RFC8032
- Rundgren, A.; Jordan, B.; Erdtman, S. *JSON Canonicalization Scheme (JCS)*; RFC 8785; RFC Editor, 2020. https://doi.org/10.17487/RFC8785
- Laurie, B.; Messeri, E.; Stradling, R. *Certificate Transparency Version 2.0*; RFC 9162; RFC Editor, 2021. https://doi.org/10.17487/RFC9162
- Laurie, B.; Langley, A.; Kasper, E. *Certificate Transparency*; RFC 6962; RFC Editor, 2013. https://doi.org/10.17487/RFC6962
- Kent, S. *IP Encapsulating Security Payload (ESP)*; RFC 4303; RFC Editor, 2005. https://doi.org/10.17487/RFC4303
- Birkholz, H.; Thaler, D.; Richardson, M.; Smith, N.; Pan, W. *Remote ATtestation procedureS (RATS) Architecture*; RFC 9334; RFC Editor, 2023. https://doi.org/10.17487/RFC9334
- Cooper, D.; Santesson, S.; Farrell, S.; Boeyen, S.; Housley, R.; Polk, W. *Internet X.509 Public Key Infrastructure Certificate and Certificate Revocation List (CRL) Profile*; RFC 5280; RFC Editor, 2008. https://doi.org/10.17487/RFC5280
- Rescorla, E. *The Transport Layer Security (TLS) Protocol Version 1.3*; RFC 8446; RFC Editor, 2018. https://doi.org/10.17487/RFC8446
- Rescorla, E. *The Transport Layer Security (TLS) Protocol Version 1.3*; RFC 9846; RFC Editor, 2026. https://doi.org/10.17487/RFC9846
- Schaad, J. *CBOR Object Signing and Encryption (COSE): Structures and Process*; RFC 9052; RFC Editor, 2022. https://doi.org/10.17487/RFC9052

### Content facts: RFC 4303 anti-replay sliding window (confirmed)

- **§3.4.3 "Sequence Number Verification"** defines the receiver-side anti-replay service and the sliding window:
  - "All ESP implementations MUST support the anti-replay service, though its use may be enabled or disabled by the receiver on a per-SA basis. This service MUST NOT be enabled unless the ESP integrity service also is enabled for the SA."
  - "Duplicates are rejected through the use of a sliding receive window. How the window is implemented is a local matter…"
  - "The 'right' edge of the window represents the highest, validated Sequence Number value received on this SA. Packets that contain sequence numbers lower than the 'left' edge of the window are rejected. Packets falling within the window are checked against a list of received packets within the window."
  - "The receive window is updated only if the integrity verification succeeds."
  - "A minimum window size of 32 packets MUST be supported when 32-bit sequence numbers are employed; a window size of 64 is preferred and SHOULD be employed as the default."
  - Multi-sender limitation: "this standard specifies no mechanisms for providing anti-replay for a multi-sender SA (unicast or multicast)."
- **§3.3.3 "Sequence Number Generation"** covers the sender side.
- **Appendix A2 "Anti-Replay Window"** (A2.1 "Managing and Using the Anti-Replay Window") covers Extended (64-bit) Sequence Numbers.

### BIBTEX (RFCs)

```bibtex
@misc{rfc8032, author={Josefsson, S. and Liusvaara, I.}, title={{Edwards-Curve Digital Signature Algorithm (EdDSA)}}, howpublished={RFC 8032}, publisher={RFC Editor}, year={2017}, month=jan, doi={10.17487/RFC8032}, url={https://www.rfc-editor.org/info/rfc8032/}, note={Informational; IRTF}}
@misc{rfc8785, author={Rundgren, A. and Jordan, B. and Erdtman, S.}, title={{JSON Canonicalization Scheme (JCS)}}, howpublished={RFC 8785}, publisher={RFC Editor}, year={2020}, month=jun, doi={10.17487/RFC8785}, url={https://www.rfc-editor.org/info/rfc8785/}, note={Informational; Independent Submission}}
@misc{rfc9162, author={Laurie, B. and Messeri, E. and Stradling, R.}, title={{Certificate Transparency Version 2.0}}, howpublished={RFC 9162}, publisher={RFC Editor}, year={2021}, month=dec, doi={10.17487/RFC9162}, url={https://www.rfc-editor.org/info/rfc9162/}, note={Experimental; obsoletes RFC 6962}}
@misc{rfc6962, author={Laurie, B. and Langley, A. and Kasper, E.}, title={{Certificate Transparency}}, howpublished={RFC 6962}, publisher={RFC Editor}, year={2013}, month=jun, doi={10.17487/RFC6962}, url={https://www.rfc-editor.org/info/rfc6962/}, note={Experimental; obsoleted by RFC 9162}}
@misc{rfc4303, author={Kent, S.}, title={{IP Encapsulating Security Payload (ESP)}}, howpublished={RFC 4303}, publisher={RFC Editor}, year={2005}, month=dec, doi={10.17487/RFC4303}, url={https://www.rfc-editor.org/info/rfc4303/}, note={Proposed Standard; obsoletes RFC 2406}}
@misc{rfc9334, author={Birkholz, H. and Thaler, D. and Richardson, M. and Smith, N. and Pan, W.}, title={{Remote ATtestation procedureS (RATS) Architecture}}, howpublished={RFC 9334}, publisher={RFC Editor}, year={2023}, month=jan, doi={10.17487/RFC9334}, url={https://www.rfc-editor.org/info/rfc9334/}, note={Informational}}
@misc{rfc5280, author={Cooper, D. and Santesson, S. and Farrell, S. and Boeyen, S. and Housley, R. and Polk, W.}, title={{Internet X.509 Public Key Infrastructure Certificate and Certificate Revocation List (CRL) Profile}}, howpublished={RFC 5280}, publisher={RFC Editor}, year={2008}, month=may, doi={10.17487/RFC5280}, url={https://www.rfc-editor.org/info/rfc5280/}, note={Proposed Standard; updated by RFCs 6818, 8398, 8399, 9549, 9598, 9608, 9618, 9925, 10007}}
@misc{rfc8446, author={Rescorla, E.}, title={{The Transport Layer Security (TLS) Protocol Version 1.3}}, howpublished={RFC 8446}, publisher={RFC Editor}, year={2018}, month=aug, doi={10.17487/RFC8446}, url={https://www.rfc-editor.org/info/rfc8446/}, note={Proposed Standard; obsoleted by RFC 9846}}
@misc{rfc9846, author={Rescorla, E.}, title={{The Transport Layer Security (TLS) Protocol Version 1.3}}, howpublished={RFC 9846}, publisher={RFC Editor}, year={2026}, month=jul, doi={10.17487/RFC9846}, url={https://www.rfc-editor.org/info/rfc9846/}, note={Proposed Standard; obsoletes RFCs 5077, 5246, 6961, 7627, 8422, 8446}}
@misc{rfc9052, author={Schaad, J.}, title={{CBOR Object Signing and Encryption (COSE): Structures and Process}}, howpublished={RFC 9052}, publisher={RFC Editor}, year={2022}, month=aug, doi={10.17487/RFC9052}, url={https://www.rfc-editor.org/info/rfc9052/}, note={Internet Standard; obsoletes RFC 8152; updated by RFC 9338}}
```

- **SOURCES:** https://www.rfc-editor.org/rfc/rfcNNNN.json and https://www.rfc-editor.org/rfc/rfcNNNN.txt for each RFC listed (the /info/rfcNNNN/ pages resolve, HTTP 200 after a 301 redirect) ; https://api.crossref.org/works/10.17487/RFCNNNN

---

## Part C: Systems and data-engineering literature

### 15. Akidau et al., The Dataflow Model (PVLDB 2015). [VERIFIED]

- **KEY:** `akidau2015dataflow`
- **VERIFIED CITATION (MDPI):** Akidau, T.; Bradshaw, R.; Chambers, C.; Chernyak, S.; Fernández-Moctezuma, R.J.; Lax, R.; McVeety, S.; Mills, D.; Perry, F.; Schmidt, E.; Whittle, S. The Dataflow Model: A Practical Approach to Balancing Correctness, Latency, and Cost in Massive-Scale, Unbounded, Out-of-Order Data Processing. *Proc. VLDB Endow.* **2015**, *8*, 1792–1803. https://doi.org/10.14778/2824032.2824076
- **Fields:**
  - Crossref: vol. 8, issue 12, pp. 1792–1803, August 2015, ISSN 2150-8097, 11 authors as listed.
  - Title capitalization checked against the PVLDB PDF (https://www.vldb.org/pvldb/vol8/p1792-Akidau.pdf).
- **TYPE:** Journal article
- **BIBTEX:**
```bibtex
@article{akidau2015dataflow,
  author  = {Akidau, Tyler and Bradshaw, Robert and Chambers, Craig and Chernyak, Slava and Fern{\'a}ndez-Moctezuma, Rafael J. and Lax, Reuven and McVeety, Sam and Mills, Daniel and Perry, Frances and Schmidt, Eric and Whittle, Sam},
  title   = {The Dataflow Model: A Practical Approach to Balancing Correctness, Latency, and Cost in Massive-Scale, Unbounded, Out-of-Order Data Processing},
  journal = {Proceedings of the VLDB Endowment},
  volume  = {8},
  number  = {12},
  pages   = {1792--1803},
  year    = {2015},
  month   = aug,
  doi     = {10.14778/2824032.2824076}
}
```
- **SOURCES:** https://api.crossref.org/works/10.14778/2824032.2824076 ; https://www.vldb.org/pvldb/vol8/p1792-Akidau.pdf

### 16. Wang et al., Consistency and Completeness (SIGMOD 2021). [VERIFIED]

- **KEY:** `wang2021kafka`
- **VERIFIED CITATION (MDPI):** Wang, G.; Chen, L.; Dikshit, A.; Gustafson, J.; Chen, B.; Sax, M.J.; Roesler, J.; Blee-Goldman, S.; Cadonna, B.; Mehta, A.; Madan, V.; Rao, J. Consistency and Completeness: Rethinking Distributed Stream Processing in Apache Kafka. In Proceedings of the 2021 International Conference on Management of Data (SIGMOD '21), Virtual Event, China, 20–25 June 2021; pp. 2602–2613. https://doi.org/10.1145/3448016.3457556
- **Fields:**
  - Crossref: title "Consistency and Completeness" with subtitle "Rethinking Distributed Stream Processing in Apache Kafka"; container "Proceedings of the 2021 International Conference on Management of Data"; event "SIGMOD/PODS '21", location "Virtual Event China"; pp. 2602–2613; 12 authors as listed; publisher ACM.
  - Dates from https://2021.sigmod.org/: the conference "was supposed to be held in Xi'an, Shaanxi, China, on June 20 - June 25, 2021" and is "transitioning to an online format … complemented with a local physical event at Xi'an".
- **TYPE:** Conference paper
- **BIBTEX:**
```bibtex
@inproceedings{wang2021kafka,
  author    = {Wang, Guozhang and Chen, Lei and Dikshit, Ayusman and Gustafson, Jason and Chen, Boyang and Sax, Matthias J. and Roesler, John and Blee-Goldman, Sophie and Cadonna, Bruno and Mehta, Apurva and Madan, Varun and Rao, Jun},
  title     = {Consistency and Completeness: Rethinking Distributed Stream Processing in {Apache Kafka}},
  booktitle = {Proceedings of the 2021 International Conference on Management of Data (SIGMOD '21)},
  pages     = {2602--2613},
  publisher = {ACM},
  year      = {2021},
  month     = jun,
  doi       = {10.1145/3448016.3457556}
}
```
- **SOURCES:** https://api.crossref.org/works/10.1145/3448016.3457556 ; https://2021.sigmod.org/

### 17. Carbone et al., Apache Flink (IEEE Data Eng. Bull. 2015). [VERIFIED]

- **KEY:** `carbone2015flink`
- **VERIFIED CITATION (MDPI):** Carbone, P.; Ewen, S.; Haridi, S.; Katsifodimos, A.; Markl, V.; Tzoumas, K. Apache Flink™: Stream and Batch Processing in a Single Engine. *Bulletin of the IEEE Computer Society Technical Committee on Data Engineering* **2015**, *38*, 28–38. Available online: http://sites.computer.org/debull/A15dec/p28.pdf (accessed on 3 November 2026).
- **Fields:**
  - Author order as printed in the PDF: Carbone, Ewen, Haridi, Katsifodimos, Markl, Tzoumas.
  - Title as printed includes "™" after "Flink".
  - Issue page header: "Bulletin of the Technical Committee on Data Engineering, December 2015 Vol. 38 No. 4, IEEE Computer Society". The PDF footer reads "Bulletin of the IEEE Computer Society Technical Committee on Data Engineering".
  - Printed page footers run 28–38. The next paper (CSA) starts at p. 39.
  - **No DOI:** no Crossref record was found by title search.
- **TYPE:** Journal article (bulletin; no DOI)
- **BIBTEX:**
```bibtex
@article{carbone2015flink,
  author  = {Carbone, Paris and Ewen, Stephan and Haridi, Seif and Katsifodimos, Asterios and Markl, Volker and Tzoumas, Kostas},
  title   = {{Apache Flink}{\texttrademark}: Stream and Batch Processing in a Single Engine},
  journal = {Bulletin of the IEEE Computer Society Technical Committee on Data Engineering},
  volume  = {38},
  number  = {4},
  pages   = {28--38},
  year    = {2015},
  month   = dec,
  url     = {http://sites.computer.org/debull/A15dec/p28.pdf},
  note    = {Accessed on 3 November 2026}
}
```
- **SOURCES:** http://sites.computer.org/debull/A15dec/issue1.htm ; http://sites.computer.org/debull/A15dec/p28.pdf

### 18. Helland, Idempotence Is Not a Medical Condition (2012). [VERIFIED; two venues]

- **KEYS:** `helland2012queue` (original, April 2012) and `helland2012cacm` (May 2012). Pick one; the Queue version predates the CACM version.
- **VERIFIED CITATIONS (MDPI):**
  - Helland, P. Idempotence Is Not a Medical Condition. *Queue* **2012**, *10*, 30–46. https://doi.org/10.1145/2181796.2187821
  - Helland, P. Idempotence Is Not a Medical Condition. *Commun. ACM* **2012**, *55*, 56–65. https://doi.org/10.1145/2160718.2160734
- **Fields:**
  - Queue: vol. 10, issue 4, pp. 30–46, April 2012 (online 2012-04-13); Crossref subtitle "An essential property for reliable systems".
  - CACM: vol. 55, issue 5, pp. 56–65, May 2012.
- **TYPE:** Journal/magazine article
- **BIBTEX:**
```bibtex
@article{helland2012queue,
  author  = {Helland, Pat},
  title   = {Idempotence Is Not a Medical Condition},
  journal = {Queue},
  volume  = {10},
  number  = {4},
  pages   = {30--46},
  year    = {2012},
  month   = apr,
  doi     = {10.1145/2181796.2187821}
}
@article{helland2012cacm,
  author  = {Helland, Pat},
  title   = {Idempotence Is Not a Medical Condition},
  journal = {Communications of the ACM},
  volume  = {55},
  number  = {5},
  pages   = {56--65},
  year    = {2012},
  month   = may,
  doi     = {10.1145/2160718.2160734}
}
```
- **SOURCES:** https://api.crossref.org/works/10.1145/2181796.2187821 ; https://api.crossref.org/works/10.1145/2160718.2160734

### 19. Shapiro et al., Conflict-Free Replicated Data Types (SSS 2011). [VERIFIED]

- **KEY:** `shapiro2011crdt`
- **VERIFIED CITATION (MDPI):** Shapiro, M.; Preguiça, N.; Baquero, C.; Zawirski, M. Conflict-Free Replicated Data Types. In *Stabilization, Safety, and Security of Distributed Systems: 13th International Symposium, SSS 2011, Grenoble, France, 10–12 October 2011*; Défago, X., Petit, F., Villain, V., Eds.; Lecture Notes in Computer Science; Springer: Berlin/Heidelberg, Germany, 2011; Volume 6976, pp. 386–400. https://doi.org/10.1007/978-3-642-24550-3_29
- **Fields:**
  - Crossref chapter: pp. 386–400; authors as listed.
  - Crossref book record 10.1007/978-3-642-24550-3: editors Xavier Défago, Franck Petit, Vincent Villain; subtitle "13th International Symposium, SSS 2011, Grenoble, France, October 10-12, 2011. Proceedings".
  - Springer book page: "Lecture Notes in Computer Science (LNCS), volume 6976"; Springer Berlin, Heidelberg; ISBNs 978-3-642-24549-7 (softcover), 978-3-642-24550-3 (eBook).
- **TYPE:** Conference paper (LNCS book chapter)
- **BIBTEX:**
```bibtex
@inproceedings{shapiro2011crdt,
  author    = {Shapiro, Marc and Pregui{\c{c}}a, Nuno and Baquero, Carlos and Zawirski, Marek},
  title     = {Conflict-Free Replicated Data Types},
  booktitle = {Stabilization, Safety, and Security of Distributed Systems (SSS 2011)},
  editor    = {D{\'e}fago, Xavier and Petit, Franck and Villain, Vincent},
  series    = {Lecture Notes in Computer Science},
  volume    = {6976},
  pages     = {386--400},
  publisher = {Springer},
  address   = {Berlin, Heidelberg},
  year      = {2011},
  doi       = {10.1007/978-3-642-24550-3_29}
}
```
- **SOURCES:** https://api.crossref.org/works/10.1007/978-3-642-24550-3_29 ; https://api.crossref.org/works/10.1007/978-3-642-24550-3 ; https://link.springer.com/book/10.1007/978-3-642-24550-3 (via doi.org redirect)

### 20. Torres-Arias et al., in-toto (USENIX Security 2019). [VERIFIED]

- **KEY:** `torresarias2019intoto`
- **VERIFIED CITATION (MDPI):** Torres-Arias, S.; Afzali, H.; Kuppusamy, T.K.; Curtmola, R.; Cappos, J. in-toto: Providing Farm-to-Table Guarantees for Bits and Bytes. In Proceedings of the 28th USENIX Security Symposium (USENIX Security 19), Santa Clara, CA, USA, 14–16 August 2019; pp. 1393–1410. Available online: https://www.usenix.org/conference/usenixsecurity19/presentation/torres-arias (accessed on 3 November 2026).
- **Fields:**
  - USENIX BibTeX: authors Santiago Torres-Arias, Hammad Afzali, Trishank Karthik Kuppusamy, Reza Curtmola, Justin Cappos; booktitle "28th USENIX Security Symposium (USENIX Security 19)"; ISBN 978-1-939133-06-9; pp. 1393–1410; publisher USENIX Association; month Aug.
  - Contents PDF: "August 14–16, 2019, Santa Clara, CA, USA", start page 1393. Paper PDF footers run 1393 to 1410.
  - Official title is in sentence case: "in-toto: Providing farm-to-table guarantees for bits and bytes". Keep "in-toto" lowercase.
  - **No DOI** (no Crossref record found).
- **TYPE:** Conference paper
- **BIBTEX:**
```bibtex
@inproceedings{torresarias2019intoto,
  author    = {Torres-Arias, Santiago and Afzali, Hammad and Kuppusamy, Trishank Karthik and Curtmola, Reza and Cappos, Justin},
  title     = {{in-toto}: Providing farm-to-table guarantees for bits and bytes},
  booktitle = {28th USENIX Security Symposium (USENIX Security 19)},
  pages     = {1393--1410},
  publisher = {USENIX Association},
  address   = {Santa Clara, CA, USA},
  year      = {2019},
  month     = aug,
  isbn      = {978-1-939133-06-9},
  url       = {https://www.usenix.org/conference/usenixsecurity19/presentation/torres-arias}
}
```
- **SOURCES:** https://www.usenix.org/conference/usenixsecurity19/presentation/torres-arias ; https://www.usenix.org/sites/default/files/sec19_contents.pdf ; https://www.usenix.org/system/files/sec19-torres-arias.pdf

### 21. Hasan, Sion, Winslett, The Case of the Fake Picasso (FAST 2009). [VERIFIED]

- **KEY:** `hasan2009fast`
- **VERIFIED CITATION (MDPI):** Hasan, R.; Sion, R.; Winslett, M. The Case of the Fake Picasso: Preventing History Forgery with Secure Provenance. In Proceedings of the 7th USENIX Conference on File and Storage Technologies (FAST '09), San Francisco, CA, USA, 25–27 February 2009; pp. 1–14. Available online: https://www.usenix.org/legacy/event/fast09/tech/full_papers/hasan/hasan.pdf (accessed on 3 November 2026).
- **Fields:**
  - Authors and affiliations (FAST '09 technical sessions page and PDF): Ragib Hasan (UIUC), Radu Sion (Stony Brook University), Marianne Winslett (UIUC).
  - PDF running footers: "USENIX Association 7th USENIX Conference on File and Storage Technologies 1" … "14".
  - Conference home page title: "7th USENIX Conference on File and Storage Technologies (FAST '09)"; "joined us in San Francisco".
  - Technical sessions ran Wednesday 25 to Friday 27 February 2009. The paper was in session "Augmenting File System Functionality", Wed 25 Feb.
  - **No DOI** (no Crossref record found).
- **Related DOI-bearing extended version (optional, verified):** Hasan, R.; Sion, R.; Winslett, M. Preventing History Forgery with Secure Provenance. *ACM Trans. Storage* **2009**, *5*, 1–43. https://doi.org/10.1145/1629080.1629082 (Crossref: vol. 5, issue 4, pages "1-43", December 2009).
- **TYPE:** Conference paper
- **BIBTEX:**
```bibtex
@inproceedings{hasan2009fast,
  author    = {Hasan, Ragib and Sion, Radu and Winslett, Marianne},
  title     = {The Case of the Fake {Picasso}: Preventing History Forgery with Secure Provenance},
  booktitle = {Proceedings of the 7th USENIX Conference on File and Storage Technologies (FAST '09)},
  pages     = {1--14},
  publisher = {USENIX Association},
  address   = {San Francisco, CA, USA},
  year      = {2009},
  month     = feb,
  url       = {https://www.usenix.org/legacy/event/fast09/tech/full_papers/hasan/hasan.pdf}
}
@article{hasan2009tos,
  author  = {Hasan, Ragib and Sion, Radu and Winslett, Marianne},
  title   = {Preventing History Forgery with Secure Provenance},
  journal = {ACM Transactions on Storage},
  volume  = {5},
  number  = {4},
  pages   = {1--43},
  year    = {2009},
  month   = dec,
  doi     = {10.1145/1629080.1629082}
}
```
- **SOURCES:** https://www.usenix.org/legacy/event/fast09/tech/ ; https://www.usenix.org/legacy/event/fast09/ ; https://www.usenix.org/legacy/events/fast09/tech/full_papers/hasan/hasan.pdf ; https://api.crossref.org/works/10.1145/1629080.1629082

### 22. Crosby & Wallach, Efficient Data Structures for Tamper-Evident Logging (USENIX Security 2009). [VERIFIED – NOTE]

- **KEY:** `crosby2009tamper`
- **VERIFIED CITATION (MDPI):** Crosby, S.A.; Wallach, D.S. Efficient Data Structures for Tamper-Evident Logging. In Proceedings of the 18th USENIX Security Symposium, Montreal, QC, Canada, 10–14 August 2009; pp. 317–333. Available online: https://www.usenix.org/conference/usenixsecurity09/technical-sessions/presentation/efficient-data-structures-tamper-evident (accessed on 3 November 2026).
- **Fields:**
  - Authors: Scott A. Crosby, Dan S. Wallach (Rice University).
  - USENIX BibTeX: booktitle "18th USENIX Security Symposium (USENIX Security 09)", address "Montreal, Quebec", month Aug, 2009. No pages or ISBN on that page.
  - Official TOC PDF: start page **317**; the next paper ("VPriv") starts at **335**.
  - The proceedings session PDF (sec09_crypto.pdf) shows printed footers 317–333 for this paper, with **p. 334 blank**. "pp. 317–333" reflects printed content; "pp. 317–334" reflects the TOC allocation. Either is traceable, but prefer 317–333.
  - Venue and dates from the Security '09 home page: "Join us in Montreal, Canada, August 10–14, 2009, for the 18th USENIX Security Symposium".
- **NOTE:** USENIX's own TOC PDF header (sec09_toc.pdf) wrongly prints "San Jose, CA, USA". Do not use that location.
- **No DOI** (no Crossref record found).
- **TYPE:** Conference paper
- **BIBTEX:**
```bibtex
@inproceedings{crosby2009tamper,
  author    = {Crosby, Scott A. and Wallach, Dan S.},
  title     = {Efficient Data Structures for Tamper-Evident Logging},
  booktitle = {18th USENIX Security Symposium (USENIX Security 09)},
  pages     = {317--333},
  publisher = {USENIX Association},
  address   = {Montreal, Quebec, Canada},
  year      = {2009},
  month     = aug,
  url       = {https://www.usenix.org/conference/usenixsecurity09/technical-sessions/presentation/efficient-data-structures-tamper-evident}
}
```
- **SOURCES:** https://www.usenix.org/conference/usenixsecurity09/technical-sessions/presentation/efficient-data-structures-tamper-evident ; https://www.usenix.org/legacy/events/sec09/tech/sec09_toc.pdf ; https://www.usenix.org/legacy/events/sec09/tech/full_papers/sec09_crypto.pdf ; https://www.usenix.org/legacy/event/sec09/ ; https://www.usenix.org/legacy/event/sec09/tech/full_papers/crosby.pdf

### 23. Merkle, A Digital Signature Based on a Conventional Encryption Function (CRYPTO '87). [VERIFIED – NOTE]

- **KEY:** `merkle1988signature`
- **VERIFIED CITATION (MDPI):** Merkle, R.C. A Digital Signature Based on a Conventional Encryption Function. In *Advances in Cryptology—CRYPTO '87*; Pomerance, C., Ed.; Lecture Notes in Computer Science; Springer: Berlin/Heidelberg, Germany, 1988; Volume 293, pp. 369–378. https://doi.org/10.1007/3-540-48184-2_32
- **Fields:**
  - Crossref chapter: pp. 369–378; print year 1988 (online 2000-12-01); author Ralph C. Merkle.
  - Crossref book 10.1007/3-540-48184-2: "Advances in Cryptology — CRYPTO '87: Proceedings", editor Carl Pomerance.
  - Springer page: "Lecture Notes in Computer Science, volume 293"; © 1988 Springer-Verlag Berlin Heidelberg.
- **NOTE:** The publication year is **1988**; CRYPTO '87 is the event name. The conference location and dates are not on the Springer page and were not verified, so they are omitted.
- **TYPE:** Conference paper (LNCS book chapter)
- **BIBTEX:**
```bibtex
@inproceedings{merkle1988signature,
  author    = {Merkle, Ralph C.},
  title     = {A Digital Signature Based on a Conventional Encryption Function},
  booktitle = {Advances in Cryptology -- {CRYPTO} '87},
  editor    = {Pomerance, Carl},
  series    = {Lecture Notes in Computer Science},
  volume    = {293},
  pages     = {369--378},
  publisher = {Springer},
  address   = {Berlin, Heidelberg},
  year      = {1988},
  doi       = {10.1007/3-540-48184-2_32}
}
```
- **SOURCES:** https://api.crossref.org/works/10.1007/3-540-48184-2_32 ; https://api.crossref.org/works/10.1007/3-540-48184-2 ; https://link.springer.com/book/10.1007/3-540-48184-2 (via doi.org redirect)

### 24. Bernstein et al., High-speed high-security signatures (J. Cryptogr. Eng. 2012). [VERIFIED]

- **KEY:** `bernstein2012ed25519`
- **VERIFIED CITATION (MDPI):** Bernstein, D.J.; Duif, N.; Lange, T.; Schwabe, P.; Yang, B.-Y. High-Speed High-Security Signatures. *J. Cryptogr. Eng.* **2012**, *2*, 77–89. https://doi.org/10.1007/s13389-012-0027-1
- **Fields (Crossref):** vol. 2, issue 2, pp. 77–89; online 2012-08-14, issue September 2012; ISSN 2190-8508/2190-8516; authors Daniel J. Bernstein, Niels Duif, Tanja Lange, Peter Schwabe, Bo-Yin Yang.
- **Related (seen in Crossref search):** a conference version with the same title, LNCS (2011), pp. 124–142, https://doi.org/10.1007/978-3-642-23951-9_9. Its LNCS volume and editors were **not** verified here. Cite the JCEN version unless you specifically need the conference version.
- **TYPE:** Journal article
- **BIBTEX:**
```bibtex
@article{bernstein2012ed25519,
  author  = {Bernstein, Daniel J. and Duif, Niels and Lange, Tanja and Schwabe, Peter and Yang, Bo-Yin},
  title   = {High-speed high-security signatures},
  journal = {Journal of Cryptographic Engineering},
  volume  = {2},
  number  = {2},
  pages   = {77--89},
  year    = {2012},
  doi     = {10.1007/s13389-012-0027-1}
}
```
- **SOURCES:** https://api.crossref.org/works/10.1007/s13389-012-0027-1

---

## Part D: Dataset (item 25): HAI (HIL-based Augmented ICS) security dataset. [VERIFIED – NOTE]

### 25a. Dataset paper (HAI 1.0)

- **KEY:** `shin2020hai`
- **VERIFIED CITATION (MDPI):** Shin, H.-K.; Lee, W.; Yun, J.-H.; Kim, H. HAI 1.0: HIL-based Augmented ICS Security Dataset. In Proceedings of the 13th USENIX Workshop on Cyber Security Experimentation and Test (CSET 20), Virtual Event, 10 August 2020. Available online: https://www.usenix.org/conference/cset20/presentation/shin (accessed on 3 November 2026).
- **Fields:**
  - USENIX BibTeX (verbatim fields): author "Hyeok-Ki Shin and Woomyo Lee and Jeong-Han Yun and HyoungChun Kim"; title "{HAI} 1.0: {HIL-based} Augmented {ICS} Security Dataset"; booktitle "13th USENIX Workshop on Cyber Security Experimentation and Test (CSET 20)"; year 2020; publisher USENIX Association; month aug.
  - CSET '20 home page: "will take place as a virtual event. It will be held on August 10, 2020"; co-located with USENIX Security '20.
  - Program: session "Industrial Control Systems", Monday, August 10, labelled "Short Extended Work Paper".
  - Affiliation: The Affiliated Institute of ETRI, Republic of Korea.
  - PDF: 5 pages; no proceedings pagination.
- **Citation title check:** the title you gave ("HAI 1.0: HIL-based Augmented ICS Security Dataset") is correct. The venue is a **Workshop** ("13th USENIX Workshop on Cyber Security Experimentation and Test"), not "Conference" as the HAI README BibTeX says.
- **DOI:** **none**. The README's ACM-DL identifier `10.5555/3485754.3485755` is **not a registered DOI**: doi.org returns 404 and the handle is not found. **Do not cite it as a DOI.**
- **TYPE:** Workshop paper
- **BIBTEX:**
```bibtex
@inproceedings{shin2020hai,
  author    = {Shin, Hyeok-Ki and Lee, Woomyo and Yun, Jeong-Han and Kim, HyoungChun},
  title     = {{HAI} 1.0: {HIL}-based Augmented {ICS} Security Dataset},
  booktitle = {13th USENIX Workshop on Cyber Security Experimentation and Test (CSET 20)},
  publisher = {USENIX Association},
  address   = {Virtual Event},
  year      = {2020},
  month     = aug,
  url       = {https://www.usenix.org/conference/cset20/presentation/shin}
}
```
- **SOURCES:** https://www.usenix.org/conference/cset20/presentation/shin ; https://www.usenix.org/system/files/cset20-paper-shin.pdf ; https://www.usenix.org/conference/cset20/workshop-program ; https://www.usenix.org/conference/cset20 ; https://doi.org/api/handles/10.5555/3485754.3485755 (not found)

### 25b. Companion paper (recommended by the maintainers for HAI 21.03)

- **KEY:** `shin2021hai`
- **VERIFIED CITATION (MDPI):** Shin, H.-K.; Lee, W.; Yun, J.-H.; Min, B.-G. Two ICS Security Datasets and Anomaly Detection Contest on the HIL-based Augmented ICS Testbed. In Proceedings of the Cyber Security Experimentation and Test Workshop (CSET '21), Virtual Event, CA, USA, 2021; pp. 36–40. https://doi.org/10.1145/3474718.3474719
- **Fields (Crossref):** container "Cyber Security Experimentation and Test Workshop"; event "CSET '21", location "Virtual CA USA"; pp. 36–40; issued 2021-08-09; publisher ACM.
- **TYPE:** Workshop paper
- **BIBTEX:**
```bibtex
@inproceedings{shin2021hai,
  author    = {Shin, Hyeok-Ki and Lee, Woomyo and Yun, Jeong-Han and Min, Byung-Gil},
  title     = {Two {ICS} Security Datasets and Anomaly Detection Contest on the {HIL}-based Augmented {ICS} Testbed},
  booktitle = {Cyber Security Experimentation and Test Workshop (CSET '21)},
  pages     = {36--40},
  publisher = {ACM},
  year      = {2021},
  doi       = {10.1145/3474718.3474719}
}
```
- **SOURCES:** https://api.crossref.org/works/10.1145/3474718.3474719

### 25c. Repository / dataset citation

- **KEY:** `hai_github`
- **VERIFIED CITATION (MDPI):** Shin, H.-K.; Lee, W.; Choi, S.; Yun, J.-H.; Min, B.-G. HAI Security Datasets. GitHub repository, 2023. Available online: https://github.com/icsdataset/hai (accessed on 3 November 2026).
- **Basis:** the README's own "Citation" block for HAI 22.04, HAI 23.05 and HAIEnd 23.05: `author={Shin, Hyeok-Ki; Lee, Woomyo; Choi, Seungoh; Yun, Jeong-Han; and Min, Byung-Gi}, title={HAI security datasets}, year={2023}, url={https://github.com/icsdataset/hai}`.
- **NOTE (inconsistencies in the maintainers' materials):**
  - The README spells "Min, Byung-Gi" in this block but "Min, Byung-Gil" elsewhere; Crossref has "Byung-Gil Min".
  - The technical manual v4.0 cites HAI 22.04 differently: "Hyeok-Ki Shin, Woomyo Lee, Jeong-Han Yun and Byung-Gil Min, 'ICS security dataset', 2022", without Choi.
  - Either form is traceable. The README block is the more recent one and covers 23.05.
  - Pin the snapshot in the manuscript: master HEAD **2a814cebc9a66b06c9e5cd545e2d72e65d383737** (commit date 2023-06-07, "Update README.md").
- **TYPE:** Dataset (software repository)
- **BIBTEX:**
```bibtex
@misc{hai_github,
  author       = {Shin, Hyeok-Ki and Lee, Woomyo and Choi, Seungoh and Yun, Jeong-Han and Min, Byung-Gil},
  title        = {{HAI} Security Datasets},
  howpublished = {GitHub repository},
  year         = {2023},
  url          = {https://github.com/icsdataset/hai},
  note         = {Versions HAI 20.07, 21.03, 22.04, 23.05 and HAIEnd 23.05; commit 2a814cebc9a66b06c9e5cd545e2d72e65d383737. License stated as CC BY-SA 4.0. Accessed on 3 November 2026}
}
```
- **SOURCES:** https://raw.githubusercontent.com/icsdataset/hai/master/README.md ; `git clone --filter=blob:none --no-checkout https://github.com/icsdataset/hai` (tree listing, 72 files) ; https://raw.githubusercontent.com/icsdataset/hai/master/hai_dataset_technical_details.pdf (Document version 4.0, May 2023, 50 pp.) ; https://media.githubusercontent.com/media/icsdataset/hai/master/<path> (LFS content, Range requests)

### 25d. HAI content facts

#### License (exact)

- **README, "## License" section:** "This work is licensed under a [Creative Commons Attribution-ShareAlike License (CC BY-SA 4.0)](http://creativecommons.org/licenses/by-sa/4.0/)."
- **Technical manual v4.0 cover (May 2023):** "Copyright license: CC BY-SA 4.0".
- **INCONSISTENCY:** the README's schema.org "Dataset Metadata" block (for Google Dataset Search) declares license name **"CC BY 4.0"** with url `https://creativecommons.org/licenses/by/4.0/`.
- **No LICENSE file** exists in the repository; none of the 72 tracked files is a LICENSE*.
- **Resolution:** treat **CC BY-SA 4.0** as the operative license (stated twice, in prose, by the licensor) and mention the metadata discrepancy. The Kaggle mirror's license was not checked.

#### Is redistribution of extracts permitted?

Yes, under CC BY-SA 4.0, subject to conditions. Sources: the deed and legal code at https://creativecommons.org/licenses/by-sa/4.0/ and /legalcode.en.

- **Deed:** "Share — copy and redistribute the material in any medium or format for any purpose, even commercially." "Adapt — remix, transform, and build upon the material for any purpose, even commercially."
- **Legal code, Section 2 (license grant):** "reproduce and Share the Licensed Material, in whole or in part; and produce, reproduce, and Share Adapted Material."
- **Section 4 (Sui Generis Database Rights):** grants the right "to extract, reuse, reproduce, and Share all or a substantial portion of the contents of the database".
- **Attribution conditions:** "You must give appropriate credit, provide a link to the license, and indicate if changes were made."
- **ShareAlike (Section 3(b)):** "if You Share Adapted Material You produce … The Adapter's License You apply must be a Creative Commons license with the same License Elements, this version or later, or a BY-SA Compatible License."
- **Practical consequence:** a published extract or derived CSV subset (filtered, resampled, relabelled) must carry attribution, a license link and a change notice, and must be released under CC BY-SA 4.0 (or later/compatible). It must not be placed under CC BY or a more restrictive license.

#### Versions and files (repository tree at commit 2a814ce)

**Versions:** HAI 20.07 (bug-fixed HAI 1.0; HAI 1.0 first released February 2020), HAI 21.03, HAI 22.04, HAI 23.05, and HAIEnd 23.05.
- The README says "HAI 20.07 is the bug-fixed version of HAI v1.0 released in February 2020" and "The version numbering follows a date-based scheme".
- HAI 23.05 and HAIEnd 23.05 were "collected simultaneously in the same experiment".
- There is also a Kaggle mirror (https://www.kaggle.com/datasets/icsdataset/hai-security-dataset; not checked).

**Storage:**
- From HAI 22.04 onward, files are in Git LFS ("use `git lfs pull`").
- 20.07 and 21.03 are gzip-compressed CSV.
- `.gitattributes` marks only `hai-23.05/**` and `haiend-23.05/**` as LFS, but the 22.04 CSVs are also served as LFS pointers.

**File sizes.** Exact bytes come from Git LFS pointers (uncompressed CSV) or HTTP Content-Length (compressed .gz). The README's "Size (MB)" equals MiB of the CSV for 22.04 and HAI 23.05. The README's HAIEnd sizes use a different convention; use bytes.

| Version | File | Bytes | Kind |
|---|---|---|---|
| HAI 20.07 | train1.csv.gz | 35,252,451 | gz (compressed) |
| | train2.csv.gz | 26,725,939 | gz |
| | test1.csv.gz | 32,813,703 | gz |
| | test2.csv.gz | 16,907,509 | gz |
| HAI 21.03 | train1.csv.gz | 30,651,421 | gz |
| | train2.csv.gz | 31,430,645 | gz |
| | train3.csv.gz | 67,961,579 | gz |
| | test1.csv.gz | 6,149,549 | gz |
| | test2.csv.gz | 16,765,328 | gz |
| | test3.csv.gz | 15,477,098 | gz |
| | test4.csv.gz | 5,602,841 | gz |
| | test5.csv.gz | 13,199,829 | gz |
| HAI 22.04 | train1.csv | 53,190,281 | LFS CSV |
| | train2.csv | 114,199,064 | LFS CSV |
| | train3.csv | 69,953,332 | LFS CSV |
| | train4.csv | 47,917,707 | LFS CSV |
| | train5.csv | 131,777,589 | LFS CSV |
| | train6.csv | 143,438,209 | LFS CSV |
| | test1.csv | 50,536,532 | LFS CSV |
| | test2.csv | 46,616,720 | LFS CSV |
| | test3.csv | 35,066,591 | LFS CSV |
| | test4.csv | 72,931,406 | LFS CSV |
| | summary/summary(<file>).txt ×10 | n/a | text |
| HAI 23.05 | hai-train1.csv | 162,418,984 | LFS CSV |
| | hai-train2.csv | 169,121,615 | LFS CSV |
| | hai-train3.csv | 72,774,793 | LFS CSV |
| | hai-train4.csv | 114,494,940 | LFS CSV |
| | hai-test1.csv | 31,255,559 | LFS CSV |
| | hai-test2.csv | 132,946,575 | LFS CSV |
| | label-test1.csv | 1,242,017 | LFS CSV |
| | label-test2.csv | 4,500,018 | LFS CSV |
| | summary_label1.txt, summary_label2.txt | n/a | text |
| HAIEnd 23.05 | end-train1.csv | 256,552,242 | LFS CSV |
| | end-train2.csv | 266,924,893 | LFS CSV |
| | end-train3.csv | 115,378,733 | LFS CSV |
| | end-train4.csv | 180,186,249 | LFS CSV |
| | end-test1.csv | 49,351,620 | LFS CSV |
| | end-test2.csv | 209,737,755 | LFS CSV |
| | label-test1.csv | 1,242,017 | LFS CSV (identical LFS oid to hai-23.05/label-test1.csv) |
| | label-test2.csv | 4,500,018 | LFS CSV |
| | summary_label1.txt, summary_label2.txt | n/a | text |

**Other files:** README.md, .gitattributes, hai_dataset_technical_details.pdf (2,929,375 bytes; 50 pages; "Document version: 4.0", "Release date: May 2023"), and graph/ (NetworkX JSON/PNG graphs of the boiler DCS plus graph_analysis.ipynb).

**README quantitative table** ("Interval (hours)" means recording duration, not sampling period):

| Version | Data points (README) | Normal files: duration h | Normal total | Attack files: #attacks / duration h | Attack total |
|---|---|---|---|---|---|
| HAI 23.05 / HAIEnd 23.05 | 86 / 225 | train1 78; train2 81; train3 35; train4 55 | 249 h | test1 14 / 15; test2 38 / 64 | 52 attacks, 79 h |
| HAI 22.04 | 86 | train1 26; train2 56; train3 35; train4 24; train5 66; train6 72 | 279 h | test1 7/24; test2 17/23; test3 10/17.3; test4 24/36 | 58 attacks, 100.3 h |
| HAI 21.03 | 78 (but see below) | train1 60; train2 63; train3 229 | 352 h | test1 5/12; test2 20/33; test3 8/30; test4 5/11; test5 12/26 | 50 attacks, 112 h |
| HAI 20.07 | 59 | train1 86; train2 91 | 177 h | test1 28/81; test2 10/42 | 38 attacks, 123 h |

The README mislabels the second 20.07 rows as "train1/test1"; the repository files are train1, train2, test1, test2. The manual's MB figures for 21.03 differ slightly from the README's (e.g., train1 110 vs 100).

#### Sampling interval

- **1 second between consecutive records**, observed in every file inspected (e.g., 20.07 train1: 2019-09-11 20:00:00, 20:00:01, 20:00:02 …; the same holds for 21.03, 22.04, 23.05 and HAIEnd 23.05).
- The README table header reads "Data Points (points/sec)"; the manual calls the same column "# of tags".
- No explicit "sampling interval" sentence was found in the README or the manual v4.0. State it as "1 s (as recorded in the CSV timestamps)".
- Timestamp format: "yyyy-MM-dd hh:mm:ss" (README; manual).

#### Columns, channels and labels (observed from file headers; these override README and manual counts)

| Version | Delimiter | Total columns | Time column | Data channels (by stage prefix) | Label column(s) |
|---|---|---|---|---|---|
| 20.07 | `;` | 64 | `time` | 59 (P1 31, P2 12, P3 5, P4 11) | `attack`, `attack_P1`, `attack_P2`, `attack_P3` (in-file) |
| 21.03 | `,` | 84 | `time` | **79** (P1 38, P2 22, P3 7, P4 12) | `attack`, `attack_P1`, `attack_P2`, `attack_P3` (in-file) |
| 22.04 | `,` | 88 | `timestamp` | 86 (P1 44, P2 24, P3 7, P4 11) | `Attack` only (in-file) |
| 23.05 (HAI) | `,` | 87 | `timestamp` | 86 (P1 37, P2 24, P3 7, P4 11, plus 7 DCS-logic tags `x1001_05_SETPOINT_OUT`, `x1001_15_ASSIGN_OUT`, `x1002_07_SETPOINT_OUT`, `x1002_08_SETPOINT_OUT`, `x1003_10_SETPOINT_OUT`, `x1003_18_SETPOINT_OUT`, `x1003_24_SUM_OUT`) | none in data files; separate `label-test1.csv`, `label-test2.csv` with columns `timestamp,label` |
| HAIEnd 23.05 | `,` | 226 | `Timestamp` | 225 boiler-DCS internal-logic points (e.g., `1001.2-OUT`, `DM-PP01-R`, `DM-PIT01`); no P1–P4 prefixes | none in data files; separate label files (same as HAI 23.05) |

**Label semantics:**
- README: "The last four columns provide data labels for whether an attack occurred. Out of these four columns, the attack column is applicable to all the process and the other three columns are applicable to the corresponding control processes."
- README: "From the HAI 22.04 version, attack labels for each process (attack_p1, attack_p2, attack p3) have been excluded."
- Manual (23.05): "The label dataset was marked as 1 only when attack occurred".

**Documentation errors to avoid repeating:**
- The README and manual give **78** data points for 21.03; the files contain **79**. The manual's "84 columns" total matches the files, so its "78" is internally inconsistent.
- The manual says 20.07 has "63 columns", but 1 + 59 + 4 = 64, as observed.
- The manual says 22.04 "includes 89 columns … 87 … SCADA data points … last four columns provide data labels". The files have 88 columns, 86 points and a single `Attack` label.
- The manual says 23.05 has "one label dataset"; the repository has two label files per dataset.

**Ingestion-relevant data-quality observations** (directly observed; not documented by the maintainers):
- **HAIEnd 23.05 uses non-zero-padded hours** for hours below 10. For example, the last rows of end-test1.csv read `2022-08-13 6:59:56 … 6:59:59`, while HAI files use `07:00:00`.
- **HAIEnd files are offset by −1 s relative to the HAI files and labels:**
  - end-test1.csv runs 2022-08-12 16:00:00 → 2022-08-13 6:59:59.
  - hai-test1.csv and label-test1.csv run 2022-08-12 16:00:01 → 2022-08-13 07:00:00.
  - end-train1 starts 18:00:00, while hai-train1 starts 18:00:01.
- Joining HAIEnd with labels therefore needs timestamp normalisation and an explicit alignment rule.
- 20.07 uses `;` as the delimiter while later versions use `,`.
- The time column is named `time`, `timestamp` or `Timestamp` depending on the version.

#### Process stages (README "HAI Testbed"; the manual uses the same P1–P4 split)

- **P1 Boiler Process:** "water-to-water heat transfer at a low pressure and a moderate temperature … controlled using Emerson Ovation DCS."
- **P2 Turbine Process:** "A rotor kit process that closely simulates the behavior of an actual rotating machine. It is controlled by GE's Mark VIe DCS."
- **P3 Water Treatment Process:** "pumping water to the upper reservoir and releasing it back into the lower reservoir. It is controlled by Siemens's S7-300 PLC."
- **P4 HIL Simulation:**
  - "Both the boiler and turbine processes are interconnected to synchronize with the rotating speed of the virtual steam-turbine power generation model. The pump and value [sic] in the water-treatment process are controlled by the pumped-storage hydropower generation model."
  - "dSPACE's SCALEXIO system … interconnected with the real-world processes through a Siemens S7-1500 PLC and ET200 remote IO devices for data-acquisition system based on the OPC gateway."

---

## Consolidated flags / [BIBLIOGRAPHIC VERIFICATION REQUIRED]

1. **DIN SPEC 91345:2016-04:** publisher city and 2016 imprint name are [BIBLIOGRAPHIC VERIFICATION REQUIRED]. DIN Media was in maintenance at every attempt. All other fields are verified (Crossref DOI 10.31030/2436156; Austrian Standards record).
2. **IIRA v1.10:** personal authors/editors are [BIBLIOGRAPHIC VERIFICATION REQUIRED] if wanted. Corporate authorship ("Industry IoT Consortium"), title, version and date are verified. Do **not** write "Industrial Internet Consortium" for v1.10.
3. **Bernstein et al., CHES 2011 conference version** (DOI 10.1007/978-3-642-23951-9_9): LNCS volume and editors were not verified. Not needed if you cite JCEN 2012.
4. **CRYPTO '87:** conference location and dates were not verified and are omitted. Year = 1988.
5. **Superseded or updated documents:**
   - RFC 8446 → obsoleted by **RFC 9846** (July 2026).
   - RFC 6962 → obsoleted by RFC 9162.
   - IEC 62541-14:2020 → withdrawn and replaced by **IEC 62541-14:2026 (Ed. 2.0)**.
   - NIST SP 800-82 Rev. 3 → Rev. 4 initial public draft (Sept 2026; draft only).
6. **OPC UA replay:** do not attribute "replay detection" to Part 14 itself. Cite OPC 10000-2 v1.05.06 §5.1.6, and note that it is configuration-dependent.
7. **MQTT QoS 1/2:** these are per-hop, protocol-level guarantees (§4.3), not end-to-end application guarantees.
8. **HAI:**
   - License stated as CC BY-SA 4.0, but the README metadata says CC BY 4.0, and there is no LICENSE file. Treat it as CC BY-SA 4.0 (ShareAlike applies to published extracts).
   - The 21.03 channel count is 79 (not 78).
   - `10.5555/3485754.3485755` is not a DOI.
   - HAIEnd timestamp format and offset caveats apply.
9. **Crosby & Wallach:** use pp. 317–333 (printed) and Montreal, not the "San Jose" printed in the USENIX TOC header.
10. **Tooling:** dblp could not be used (anti-bot proof-of-work page). The GitHub REST API was not enabled. All corresponding facts were obtained from the alternative primary sources listed above.
