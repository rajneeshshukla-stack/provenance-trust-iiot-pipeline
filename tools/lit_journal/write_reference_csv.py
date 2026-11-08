#!/usr/bin/env python3
"""Write the reference verification table (CSV) from the audit judgments below.

Usage: python3 -I write_reference_csv.py <main.bbl> <out.csv>
The order of rows follows the order of \\bibitem entries in main.bbl (= citation order).
"""
import csv
import re
import sys

CR = "https://api.crossref.org/works/{d} ; https://doi.org/{d}"
V, MI = "VERIFIED", "MINOR MISMATCH"

# key: (short citation, source(s) checked, status, finding, correction needed)
J = {
 "iic_iira_v110": ("Industry IoT Consortium 2022, IIRA v1.10", "https://www.iiconsortium.org/wp-content/uploads/sites/2/2022/11/IIRA-v1.10.pdf (WebFetch; curl redirected to media.digitaltwinconsortium.org and got 403)", V, "Cover: 'The Industrial Internet Reference Architecture', Version 1.10, 2022-11-07, 'An Industry IoT Consortium Foundational Document'.", "None required. Optional: the iiconsortium.org URL now redirects to a Digital Twin Consortium host; re-check that the link resolves for readers before submission."),
 "din_spec_91345": ("DIN 2016, DIN SPEC 91345 RAMI4.0", CR.format(d="10.31030/2436156") + " ; https://www.dinmedia.de/en/technical-rule/din-spec-91345/250940128", V, "DOI resolves; Crossref record (type standard, DIN Media GmbH) carries the German title; DIN Media gives English title 'Reference Architecture Model Industrie 4.0 (RAMI4.0)', April 2016, 40 pages, original German with English version.", "None required. Optional (MDPI standard format): add the publisher given by Crossref, 'DIN Media GmbH'."),
 "nist_sp800_207": ("Rose et al. 2020, NIST SP 800-207", CR.format(d="10.6028/NIST.SP.800-207"), V, "Title, 4 authors, 2020 (issued 2020-08-11) match.", "None."),
 "federici2023zt": ("Federici et al. 2023, Electronics 12, 566", CR.format(d="10.3390/electronics12030566"), V, "Title, authors, Electronics 12(3) 566, 2023 match.", "None."),
 "zanasi2024flexzt": ("Zanasi et al. 2024, Ad Hoc Netw. 156, 103414", CR.format(d="10.1016/j.adhoc.2024.103414"), V, "All fields match.", "None."),
 "zhang2026lztaka": ("Zhang et al. 2026, Appl. Sci. 16, 6765", CR.format(d="10.3390/app16136765"), V, "All fields match (issued 2026-07-06).", "None."),
 "james2025mqttzt": ("James et al. 2025, MQTT-ZT broker, IEEE CSR 2025", CR.format(d="10.1109/csr64739.2025.11130016"), V, "Title, 4 authors, CSR 2025, pp. 433-439 match; event location Chania, Crete, Greece (not given in bbl).", "None. Optional: add 'Chania, Greece' to match MDPI proceedings format."),
 "oasis_mqtt5": ("OASIS 2019, MQTT Version 5.0", "https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html", MI, "OASIS Standard of 07 March 2019, edited by A. Banks, E. Briggs, K. Borgendale, R. Gupta. bbl prints only 'MQTT Version 5.0. OASIS Standard, 2019.' (no editors, no URL; the bib url/editor fields are not printed by mdpi.bst for @misc without note).", "Add editors (Banks, A.; Briggs, E.; Borgendale, K.; Gupta, R., Eds.), date 7 March 2019 and 'Available online: https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html (accessed on ...)'."),
 "opcua_part2": ("OPC Foundation 2025, OPC 10000-2 Security Model 1.05.06", "https://reference.opcfoundation.org/specs/OPC-10000-2/v1.05.06", MI, "Release 1.05.06, publication date 2025-10-22, current version: matches. bbl prints no URL for this online-only reference.", "Add 'Available online: https://reference.opcfoundation.org/specs/OPC-10000-2/v1.05.06 (accessed on ...)' via a note field."),
 "faraj2025provslr": ("Faraj et al. 2025, ACM Comput. Surv. 57, 1-41", CR.format(d="10.1145/3718735"), V, "Title, authors, vol. 57 no. 10, pp. 1-41, online 2025-05-08 match.", "None."),
 "sigwart2019bcprov": ("Sigwart et al. 2019, IoT 2019 (ACM)", CR.format(d="10.1145/3365871.3365886"), V, "All fields match; event Bilbao, Spain (not in bbl).", "None. Optional: add 'Bilbao, Spain'."),
 "aman2019provenance": ("Aman et al. 2019, IEEE IoT-J 6, 10441-10457", CR.format(d="10.1109/jiot.2019.2939286"), V, "All fields match.", "None."),
 "dahlmanns2021entrust": ("Dahlmanns et al. 2021, ENTRUST, SaT-CPS 2021", CR.format(d="10.1145/3445969.3450423"), V, "All fields match (pp. 78-87).", "None."),
 "buccafurri2024mqtti": ("Buccafurri et al. 2024, MQTT-I, IEEE TDSC 21, 4717-4734", CR.format(d="10.1109/tdsc.2024.3358630"), V, "All fields match.", "None."),
 "rfc9943": ("Birkholz et al. 2026, RFC 9943 (SCITT architecture)", CR.format(d="10.17487/RFC9943") + " ; https://www.rfc-editor.org/rfc/rfc9943.json", V, "Title, 5 authors, June 2026, Proposed Standard match.", "None."),
 "tarr2019ssb": ("Tarr et al. 2019, Secure Scuttlebutt, ACM ICN 2019", CR.format(d="10.1145/3357150.3357396"), V, "Title+subtitle, 4 authors, pp. 1-11, Macao match.", "None."),
 "haeberlen2007peerreview": ("Haeberlen et al. 2007, PeerReview, SOSP 2007", CR.format(d="10.1145/1294261.1294279"), V, "All fields match (pp. 175-188).", "None."),
 "goel2005taser": ("Goel et al. 2005, Taser, SOSP 2005", CR.format(d="10.1145/1095810.1095826"), V, "All fields match (pp. 163-176).", "None."),
 "kim2010retro": ("Kim et al. 2010, Retro, OSDI 2010", "https://www.usenix.org/conference/osdi10/intrusion-recovery-using-selective-re-execution ; https://www.usenix.org/legacy/events/osdi10/tech/full_papers/Kim.pdf", V, "USENIX page and BibTeX: 4 authors, 9th USENIX OSDI '10, Vancouver, BC, 2010; no DOI, no page numbers on the page or paper PDF.", "None required. Optional: print the USENIX URL (bib url field is not printed by mdpi.bst)."),
 "spiffe_spec": ("SPIFFE Project, SPIFFE standard", "https://raw.githubusercontent.com/spiffe/spiffe/main/standards/SPIFFE.md ; https://spiffe.io/", V, "Document title matches, 'Stability: Stable'; spiffe.io states SPIFFE/SPIRE are CNCF graduated projects.", "None required. Style risk: MDPI layout guide wants static content in the reference list and names GitHub as dynamic; cite a tagged/commit-pinned URL or spiffe.io."),
 "rfc9162": ("Laurie et al. 2021, RFC 9162 (CT v2.0)", CR.format(d="10.17487/RFC9162") + " ; https://www.rfc-editor.org/rfc/rfc9162.json", V, "Title, 3 authors, Dec 2021 match (status Experimental; obsoletes RFC 6962).", "None."),
 "nist_sp800_207a": ("Chandramouli & Butcher 2023, NIST SP 800-207A", CR.format(d="10.6028/NIST.SP.800-207A"), V, "Title ('Multi-Location Environments'), 2 authors, 2023-09-13 match.", "None."),
 "lazzaro2026vciot": ("Lazzaro et al. 2026, Future Internet 18, 557", CR.format(d="10.3390/fi18100557"), V, "All fields match (issued 2026-10-16).", "None."),
 "nsa2024datapillar": ("NSA 2024, ZT Data Pillar CSI", "https://media.defense.gov/2024/Apr/09/2003434442/-1/-1/0/CSI_DATA_PILLAR_ZT.PDF (WebFetch; curl 403)", V, "Title, U/OO/140279-24, PP-24-1320, Ver. 1.0, April 2024 match; text has 'ensure enforceability at the data object level' and no 'provenance'/'lineage'.", "None."),
 "rizzardi2016aups": ("Rizzardi et al. 2016, AUPS, Inf. Syst. 62, 29-41", CR.format(d="10.1016/j.is.2016.05.004"), V, "All fields match.", "None."),
 "yousaf2026smqtt": ("Yousaf et al. 2026, SMQTT, ICECET 2026", CR.format(d="10.1109/ICECET65726.2026.11632926"), V, "Title, 4 authors, pp. 1-7, Rome, July 2026 match.", "None."),
 "lazzaro2024mqtt": ("Lazzaro & Buccafurri 2024, Future Internet 16, 246", CR.format(d="10.3390/fi16070246"), V, "All fields match.", "None."),
 "ietf_ace_coap_pubsub": ("Palombini et al. 2026, draft-ietf-ace-coap-pubsub-profile-05", "https://datatracker.ietf.org/api/v1/doc/document/draft-ietf-ace-coap-pubsub-profile/?format=json ; https://datatracker.ietf.org/doc/draft-ietf-ace-coap-pubsub-profile/history/ ; https://www.ietf.org/archive/id/draft-ietf-ace-coap-pubsub-profile-05.txt", MI, "Authors, title, rev -05 (6 July 2026), intended Standards Track verified. STATUS OUTDATED: on 2026-11-04 the IETF WG state changed from 'In WG Last Call' to 'WG Consensus: Waiting for Write-Up'. bbl note and main.tex Section 2 still say 'in WG Last Call'.", "Replace 'in WG Last Call' (bbl note and main.tex l.72) with 'WG consensus, waiting for shepherd write-up (Datatracker, 4 November 2026)' or simply 'work in progress'; update the access date."),
 "rfc9338": ("Schaad 2022, RFC 9338 (COSE countersignatures)", CR.format(d="10.17487/RFC9338") + " ; https://www.rfc-editor.org/rfc/rfc9338.json", V, "Title, author, Dec 2022 match (Internet Standard).", "None."),
 "iso20237": ("ISO/IEC 2023, ISO/IEC 20237:2023 Sparkplug 3.0", "https://www.dinmedia.de/en/standard/iso-iec-20237/374306329 (iso.org page refused: curl 403, WebFetch client error)", V, "Via DIN Media catalogue: ISO/IEC 20237:2023-10, 'Information technology - Sparkplug version 3.0', 123 pages, current. Not checked on iso.org (unreachable).", "None required. Optional: add the publisher (ISO/IEC) per the MDPI standard format."),
 "sparkplug3": ("Eclipse Sparkplug Contributors 2022, Sparkplug 3.0.0", "https://sparkplug.eclipse.org/specification/version/3.0/documents/sparkplug-specification-3.0.0.pdf", V, "Cover: 'Sparkplug Specification', Eclipse Sparkplug Contributors, Version 3.0.0, 2022-11-16.", "None."),
 "hasan2009tos": ("Hasan et al. 2009, ACM TOS 5, 1-43", CR.format(d="10.1145/1629080.1629082"), V, "All fields match.", "None."),
 "crosby2009tamper": ("Crosby & Wallach 2009, USENIX Security 09", "https://www.usenix.org/conference/usenixsecurity09/technical-sessions/presentation/efficient-data-structures-tamper-evident ; https://www.usenix.org/legacy/events/sec09/tech/full_papers/crosby.pdf", V, "Authors, title, 18th USENIX Security Symposium, Montreal, Quebec, 2009 match. Pages 317-333 could not be confirmed (USENIX page lists none; paper PDF has 17 unnumbered pages, consistent with a 17-page range).", "None required; pages unconfirmed by this audit (dblp and OpenAlex unavailable). Optional: print the USENIX URL."),
 "rfc9942": ("Steele et al. 2026, RFC 9942 (COSE Receipts)", CR.format(d="10.17487/RFC9942") + " ; https://www.rfc-editor.org/rfc/rfc9942.json", V, "Title, 4 authors, June 2026 match.", "None."),
 "ssb_protocol_guide": ("SSB Consortium, Scuttlebutt Protocol Guide", "https://ssbc.github.io/scuttlebutt-protocol-guide/", V, "Page exists with 'Message format' and signature sections. The corporate author 'Secure Scuttlebutt Consortium' is not stated on the page (it corresponds to the GitHub org 'ssbc').", "None required. Optional: give the author as 'SSBC (Secure Scuttlebutt Consortium) contributors'."),
 "mor2019gdp": ("Mor et al. 2019, Global Data Plane, ICDCS 2019", CR.format(d="10.1109/ICDCS.2019.00164"), V, "All fields match (pp. 1652-1663, Dallas).", "None."),
 "aman2017provenance": ("Aman et al. 2017, IoTPTS 2017", CR.format(d="10.1145/3055245.3055255"), V, "All fields match (pp. 11-14).", "None."),
 "javaid2018blockpro": ("Javaid et al. 2018, BlockPro, BlockSys 2018", CR.format(d="10.1145/3282278.3282281"), V, "All fields match (pp. 13-18).", "None."),
 "saito2025authenticity": ("Saito 2025, R10-HTC 2025", CR.format(d="10.1109/r10-htc63995.2025.11394180"), V, "All fields match (pp. 258-263).", "None."),
 "jaigirdar2023secprov": ("Jaigirdar et al. 2023, IEEE Access 11, 55677-55691", CR.format(d="10.1109/ACCESS.2023.3280928"), V, "All fields match.", "None."),
 "tsai2026actuation": ("Tsai et al. 2026, Sensors 26, 6262", CR.format(d="10.3390/s26196262"), V, "All fields match (issued 2026-10-02).", "None."),
 "c2pa23": ("C2PA 2025, Technical Specification 2.3", "https://spec.c2pa.org/specifications/specifications/2.3/specs/C2PA_Specification.html", V, "Page title 'Content Credentials : C2PA Technical Specification'; version history '2.3 - December 2025'.", "None."),
 "rfc5280": ("Cooper et al. 2008, RFC 5280", CR.format(d="10.17487/RFC5280") + " ; https://www.rfc-editor.org/rfc/rfc5280.json", V, "Title, 6 authors, May 2008 match; not obsoleted.", "None."),
 "palyvos2019genealog": ("Palyvos-Giannas et al. 2019, GeneaLog, Parallel Comput. 89", CR.format(d="10.1016/j.parco.2019.102552"), V, "All fields match.", "None."),
 "sukumaran2026provenance": ("Sukumaran et al. 2026, Information 17, 499", CR.format(d="10.3390/info17050499"), V, "All fields match (issued 2026-05-19).", "None."),
 "w3c_prov_dm": ("W3C 2013, PROV-DM", "https://www.w3.org/TR/2013/REC-prov-dm-20130430/", MI, "W3C Recommendation 30 April 2013, editors Luc Moreau and Paolo Missier. bbl prints no editors (bib 'editor' field not printed for @misc).", "Add editors: 'Moreau, L.; Missier, P. (Eds.) PROV-DM: The PROV Data Model; W3C Recommendation, 30 April 2013'."),
 "nifi_userguide": ("Apache NiFi, User Guide: Data Provenance", "https://nifi.apache.org/nifi-docs/user-guide.html ; https://nifi.apache.org/documentation/", V, "Page and 'Data Provenance' section exist. The version '(NiFi 2.x)' is not stated on the page; the documentation index lists NiFi 2.12.0 and 1.28.1.", "None required. Optional: name the exact version read (e.g., the 2.x line shown on nifi.apache.org/documentation) since the page is version-dependent."),
 "chandra2011warp": ("Chandra et al. 2011, Warp, SOSP 2011", CR.format(d="10.1145/2043556.2043567"), V, "All fields match (pp. 101-114).", "None."),
 "nawab2021wedgechain": ("Nawab 2021, WedgeChain, ICDE 2021", CR.format(d="10.1109/icde51399.2021.00042"), V, "All fields match (pp. 408-419).", "None."),
 "kip98": ("Apache Kafka, KIP-98", "https://cwiki.apache.org/confluence/display/KAFKA/KIP-98+-+Exactly+Once+Delivery+and+Transactional+Messaging (redirects to /spaces/KAFKA/pages/66854913/...)", V, "Page title matches; 'Current state: Adopted'.", "None. Optional: use the redirect target URL."),
 "kafka44_producerconfigs": ("Apache Kafka 2026, 4.4 Producer Configs", "https://kafka.apache.org/44/configuration/producer-configs/", V, "Page 'Producer Configs' under 'AK 4.4.X' with enable.idempotence text.", "None."),
 "cloudevents102": ("CloudEvents Project, Spec v1.0.2", "https://raw.githubusercontent.com/cloudevents/spec/v1.0.2/cloudevents/spec.md ; https://github.com/cloudevents/spec/releases/tag/v1.0.2", V, "Spec at tag v1.0.2 titled 'CloudEvents - Version 1.0.2' with the source+id duplicate rule. Release page shows the tag date without a year; year not established.", "None required (no year given, as in bbl). GitHub URL is dynamic content per MDPI layout guide; tag-pinned URL is acceptable but could move to main text."),
 "akidau2015dataflow": ("Akidau et al. 2015, PVLDB 8, 1792-1803", CR.format(d="10.14778/2824032.2824076"), V, "All fields match; 11 authors (bbl lists 10 + et al., MDPI bst behaviour).", "None."),
 "shapiro2011crdt": ("Shapiro et al. 2011, CRDTs, SSS 2011 (LNCS)", CR.format(d="10.1007/978-3-642-24550-3_29"), MI, "Title, 4 authors, pp. 386-400, 2011 match. Formatting glitch from @inbook: 'Zawirski, M., Conflict-Free...' (comma instead of period) and missing series (Crossref container: Lecture Notes in Computer Science).", "Change entry type to @inproceedings (booktitle 'Stabilization, Safety, and Security of Distributed Systems', series 'Lecture Notes in Computer Science', publisher Springer: Berlin/Heidelberg, Germany) so mdpi.bst prints 'In Proceedings of ...' with correct punctuation."),
 "matias2026resilient": ("Matias & Macedo 2026, WTF 2026 (SBC)", CR.format(d="10.5753/wtf.2026.24074"), MI, "Title, 2 authors, pp. 242-246, 2026 match. bbl reads 'In Proceedings of the Anais do XXVII Workshop ...' ('Anais' = Proceedings; duplicated).", "Set booktitle to 'XXVII Workshop de Testes e Tolerancia a Falhas (WTF 2026)' so the entry reads 'In Proceedings of the XXVII Workshop ... (WTF 2026)'."),
 "asad2026replaypdm": ("Asad et al. 2026, Systems 14, 1255", CR.format(d="10.3390/systems14101255"), V, "All fields match (issued 2026-10-06).", "None."),
 "yang2018lorawan": ("Yang et al. 2018, LoRaWAN, IoTDI 2018", CR.format(d="10.1109/iotdi.2018.00022"), V, "All fields match (pp. 129-140).", "None."),
 "lezzi2025cyberres": ("Lezzi et al. 2026, Manag. Rev. Q. 76, 1107-1161", CR.format(d="10.1007/s11301-025-00495-8"), V, "Title, authors, vol. 76 no. 2, pp. 1107-1161 match; online 2025-04-11, issue June 2026 (bbl year 2026 consistent with volume).", "None (the key name says 2025; harmless)."),
 "lim2010trust": ("Lim et al. 2010, DMSN 2010", CR.format(d="10.1145/1858158.1858162"), V, "All fields match (pp. 2-7).", "None."),
 "gigli2025zonia": ("Gigli et al. 2025, ZONIA, IEEE IoT-J 12, 42021-42044", CR.format(d="10.1109/jiot.2025.3591301"), V, "All fields match.", "None."),
 "li2004sundr": ("Li et al. 2004, SUNDR, OSDI 2004", "https://www.usenix.org/conference/osdi-04/secure-untrusted-data-repository-sundr ; https://www.usenix.org/legacy/events/osdi04/tech/full_papers/li_j/li_j.pdf", V, "4 authors, OSDI '04, San Francisco, 2004; paper PDF footers show pages 121-136.", "None. Optional: print the USENIX URL."),
 "kleppmann2022bftcrdt": ("Kleppmann 2022, BFT CRDTs, PaPoC 2022", CR.format(d="10.1145/3517209.3524042"), V, "All fields match (pp. 8-15).", "None."),
 "lavoie2023twopbftlog": ("Lavoie 2023, 2P-BFT-Log, arXiv:2307.08381v2", "https://api.datacite.org/dois/10.48550/arXiv.2307.08381 ; https://export.arxiv.org/api/query?id_list=2307.08381", V, "DataCite and arXiv API: title, sole author, v2 of 28 July 2023 is the latest version; no journal reference (still a preprint).", "None."),
 "rfc9846": ("Rescorla 2026, RFC 9846 (TLS 1.3)", CR.format(d="10.17487/RFC9846") + " ; https://www.rfc-editor.org/rfc/rfc9846.json", V, "Title, author, July 2026, Proposed Standard; obsoletes RFC 8446.", "None."),
 "rfc8785": ("Rundgren et al. 2020, RFC 8785 (JCS)", CR.format(d="10.17487/RFC8785") + " ; https://www.rfc-editor.org/rfc/rfc8785.json", V, "Title, 3 authors, June 2020 match.", "None."),
 "rfc8032": ("Josefsson & Liusvaara 2017, RFC 8032 (EdDSA)", CR.format(d="10.17487/RFC8032") + " ; https://www.rfc-editor.org/rfc/rfc8032.json", V, "Title, 2 authors, Jan 2017 match.", "None."),
 "opa": ("Open Policy Agent contributors, OPA", "https://www.openpolicyagent.org/ ; https://github.com/open-policy-agent/opa/releases/latest ; https://github.com/open-policy-agent/opa/releases (tags page robots-blocked)", MI, "Homepage verified (CNCF Graduated). The claim 'release v1.22.0 (latest tag on 3 November 2026)' could not be confirmed: the GitHub latest-release page showed v1.21.4 (23 Oct) and the releases list snapshot showed v1.20.1 as Latest. OPA itself was not run in the study (rego-cpp was).", "Remove the version/date claim from howpublished, or verify it from the GitHub tags page; consider citing rego-cpp (the interpreter actually used) with its version, as MDPI asks for names and versions of software used."),
 "katser2020skab": ("Katser & Kozitsin 2020, SKAB (Kaggle)", "https://api.datacite.org/dois/10.34740/KAGGLE/DSV/1693952", V, "DataCite: 'SKAB - Skoltech Anomaly Benchmark', creators Katser, Kozitsin, Kaggle, 2020. bbl title 'Skoltech Anomaly Benchmark (SKAB)' is an equivalent form.", "None required. Optional: use the DataCite title; the GitHub URL in the entry is dynamic content per the MDPI layout guide (commit is pinned, which mitigates)."),
 "alsaedi2020toniot": ("Alsaedi et al. 2020, TON_IoT, IEEE Access 8", CR.format(d="10.1109/ACCESS.2020.3022862"), V, "All fields match.", "None."),
 "nist_csf2": ("NIST 2024, CSF 2.0 (CSWP 29)", CR.format(d="10.6028/NIST.CSWP.29"), V, "Title, corporate author, 2024-02-26 match.", "None."),
 "iec62443_3_3": ("IEC 2013, IEC 62443-3-3:2013", "https://webstore.iec.ch/en/publication/7033", V, "Title, Edition 1.0, publication date 2013-08-07, 80 pages match.", "None. Optional: the bib already has publisher/address (IEC, Geneva, Switzerland) but mdpi.bst does not print them for @misc."),
 "iec62443_4_2": ("IEC 2019, IEC 62443-4-2:2019", "https://webstore.iec.ch/en/publication/34421", V, "Title, Edition 1.0, publication date 2019-02-27, 192 pages match.", "None. Optional: as for 62443-3-3, publisher/address in the bib are not printed."),
 "nistir_8259a": ("Fagan et al. 2020, NISTIR 8259A", CR.format(d="10.6028/NIST.IR.8259A"), V, "Title, 4 authors, May 2020 match.", "None."),
 "nist_sp800_82r3": ("Stouffer et al. 2023, NIST SP 800-82r3", CR.format(d="10.6028/NIST.SP.800-82r3"), V, "Title, 10 authors, 2023-09-28 match.", "None."),
}

bbl, out = sys.argv[1], sys.argv[2]
s = open(bbl, encoding="utf-8").read()
keys = re.findall(r"\\bibitem(?:\[(?:[^\[\]]|\[[^\]]*\])*\])?\{([^}]+)\}", s, re.S)
missing = [k for k in keys if k not in J]
extra = [k for k in J if k not in keys]
assert not missing and not extra, (missing, extra)
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["n", "key", "short_citation", "source_checked", "status", "finding", "correction_needed", "access_date"])
    for i, k in enumerate(keys, 1):
        c, src, st, fi, co = J[k]
        w.writerow([i, k, c, src, st, fi, co, "2026-11-05"])
from collections import Counter
print(len(keys), Counter(J[k][2] for k in keys))
