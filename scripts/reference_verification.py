#!/usr/bin/env python3
"""Generate research/REFERENCE_VERIFICATION.md from paper/references.bib plus curated verification notes."""
import re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
bib = (ROOT / "paper" / "references.bib").read_text()
cited = set(re.findall(r"\\cite\{([^}]+)\}", (ROOT / "paper" / "main.tex").read_text()))
cited = {k.strip() for c in cited for k in c.split(",")}
NOTES = {
 "rfc9943": ("verified", "Revision 2: RFC Editor text read by the literature audit; DOI and title confirmed in Crossref (3 Nov 2026)."),
 "rfc9338": ("verified", "Revision 2: RFC header read; DOI and title confirmed in Crossref."),
 "ietf_ace_coap_pubsub": ("verified (work in progress)", "Revision 2: IETF Datatracker page and draft sections 1, 6.1, 6.3 read; an Internet-Draft, not a standard."),
 "sparkplug3": ("verified (specification)", "Revision 2: official Eclipse PDF read; ISO/IEC 20237:2023 publication is cited separately (iso20237)."),
 "tarr2019ssb": ("verified", "Revision 2: Crossref (main title + subtitle), conference full text read."),
 "haeberlen2007peerreview": ("verified", "Revision 2: Crossref (main title + subtitle), full text read."),
 "mor2019gdp": ("verified (abstract only)", "Revision 2: Crossref and abstract; holes/branches terminology is cited from the author's dissertation (mor2019thesis)."),
 "mor2019thesis": ("verified", "Revision 2 (validation fix): title, author, Fall 2019 and UC Berkeley confirmed on the eScholarship PDF and dblp (phd/us/Mor19); holes and branches (section 3.4.2) read by the literature audit."),
 "iso20237": ("verified (standard; metadata only)", "Revision 2 (validation fix): ISO catalogue page 86204 confirms ISO/IEC 20237:2023, 'Information technology - Sparkplug version 3.0', Edition 1, 2023-10, 123 pages; content cited from the Eclipse specification (sparkplug3)."),
 "nsa2024datapillar": ("verified (grey literature)", "Revision 2 (validation fix): official NSA PDF (U/OO/140279-24, PP-24-1320, April 2024, Ver. 1.0) and NSA press release of 9 April 2024; the data-object enforcement statement was read by the literature audit."),
 "nifi_userguide": ("verified (product documentation)", "Revision 2 (validation fix): Apache NiFi User Guide (1.x) Data Provenance section; cited only for provenance events and lineage per data item. Version-dependent page."),
 "goel2005taser": ("verified (abstract only)", "Revision 2: Crossref; abstract only."),
 "chandra2011warp": ("verified (abstract and introduction)", "Revision 2: Crossref; abstract and first page read."),
 "ammann2002recovery": ("verified (abstract only)", "Revision 2: Crossref; given names abbreviated as in Crossref."),
 "c2pa23": ("verified (specification)", "Revision 2: official HTML specification v2.3 read (sections 15.2, 15.9, 19)."),
 "nist_sp800_207a": ("verified", "Revision 2: NIST PDF read; DOI confirmed in Crossref."),
 "cloudevents102": ("verified (specification; year not verified)", "Revision 2: tagged v1.0.2 specification on GitHub read; release year not verified, so none is given."),
 "zhang2026lztaka": ("verified", "Research note claimed conflicting publisher dates; MDPI, Crossref, OpenAlex and Semantic Scholar all give 6 July 2026 (HTML updated 4 Sep 2026). Conflict NOT reproduced; received/accepted dates not visible."),
 "kovach2024sovereign": ("partially verified", "Metadata only (ACM 403); conference dates [BIBLIOGRAPHIC VERIFICATION REQUIRED]. Not cited in the manuscript for any content claim."),
 "lezzi2025cyberres": ("verified", "Online 11 Apr 2025, issue June 2026 (vol. 76, no. 2); year set to 2026 to match volume."),
 "faraj2025provslr": ("verified", "Online 8 May 2025, issue 31 Oct 2025 (vol. 57, no. 10); article number unconfirmed; content read from arXiv v2."),
 "wang2025ztiiot": ("verified", "DOI registered with ISTIC (not Crossref); BibTeX from publisher page; in Chinese."),
 "james2025mqttzt": ("verified (abstract only)", "Only abstract examined; cited for broker-side ZT access control only."),
 "din_spec_91345": ("partially verified", "DOI, title, April 2016 and page count verified; publisher city [BIBLIOGRAPHIC VERIFICATION REQUIRED] (DIN site under maintenance)."),
 "iic_iira_v110": ("partially verified", "Issuing body is the Industry IoT Consortium; personal editors not retrievable from the PDF."),
 "rfc9846": ("verified", "Obsoletes RFC 8446 (July 2026); cited as the current TLS 1.3 specification."),
 "rfc9162": ("verified", "Obsoletes RFC 6962."),
 "opcua_part2": ("verified", "Replay statement is in Part 2 §5.1.6 and is configuration-dependent; Part 14 does not use the word 'replay'."),
 "oasis_mqtt5": ("verified", "QoS 1/2 are single-hop client-server guarantees (§4.3, §4.3.2, §4.3.3)."),
 "merkle1988signature": ("verified", "CRYPTO '87 proceedings published 1988 (LNCS 293)."),
 "crosby2009tamper": ("verified", "Pages 317–333; venue Montreal (USENIX contents page wrongly lists San Jose)."),
 "aws2025iotlens": ("verified (grey literature)", "Current AWS IoT Lens (2 Jul 2025); the 2021 'Securing IoT with AWS' whitepaper is historical and was not cited."),
 "microsoft2026opcuaref": ("verified (grey literature)", "Microsoft Learn page, ms.date 2026-07-22, last update 2026-08-18."),
 "kip98": ("verified (grey literature)", "Apache Kafka design page, full page read by the literature agent; not peer reviewed."),
 "rizzardi2016aups": ("verified", "BibTeX from literature record (doi.org request rate-limited); DOI checked against Crossref."),
 "sigwart2019bcprov": ("verified", "Content from arXiv v2 preprint (VoR not accessed)."),
 "rodigari2021ztmc": ("verified", "Content from arXiv v1 preprint (VoR not accessed)."),
 "asad2026replaypdm": ("verified", "'Replay' denotes dataset re-streaming (NASA C-MAPSS), not a security replay."),
}
entries = re.findall(r"@(\w+)\s*\{\s*([^,\s]+)\s*,(.*?)(?=\n@|\Z)", bib, re.S)
lines = ["# Reference verification record", "",
         "Generated by `scripts/reference_verification.py`. Bibliographic fields come from Crossref / doi.org content negotiation,",
         "the RFC Editor, NIST CSRC, W3C, OASIS, the OPC Foundation reference site, IEC webstore and publisher pages, fetched on",
         "3 November 2026 (details and quotes in `research/literature/*.md`). No field was filled from memory.", "",
         f"Entries in bibliography: {len(entries)}; cited in main.tex: {len(cited)}.", "",
         "| # | Key | Type | Identifier | Status | Notes |", "|---|---|---|---|---|---|"]
for i, (typ, key, body) in enumerate(entries, 1):
    doi = re.search(r"doi\s*=\s*\{([^}]+)\}", body, re.I)
    url = re.search(r"\burl\s*=\s*\{([^}]+)\}", body)
    ident = ("doi:" + doi.group(1)) if doi else (url.group(1) if url else "--")
    if key in NOTES:
        st, note = NOTES[key]
    elif typ in ("misc", "techreport") and not doi:
        st, note = "verified (standard/specification page)", "Issuing body page fetched; access date 3 Nov 2026."
    else:
        st, note = "verified", "Crossref record and doi.org BibTeX."
    kind = {"article": "journal article", "inproceedings": "conference/workshop paper", "inbook": "book chapter (LNCS)",
            "misc": "standard / specification / grey literature", "techreport": "technical report / standard", "book": "report"}.get(typ, typ)
    if key.startswith("rfc"):
        kind = "IETF RFC"
    if key.startswith(("nist", "iec", "din", "iic", "opcua", "oasis", "w3c")):
        kind = "standard / guidance"
    if key in ("faraj2025provslr", "wang2025ztiiot", "lezzi2025cyberres", "alotaibi2026resilient"):
        kind += " (review)"
    lines.append(f"| {i} | `{key}` | {kind} | {ident} | {st} | {note} |" + ("" if key in cited else " **(not cited in main.tex)**"))
uncited = sorted({k for _, k, _ in entries} - cited)
lines += ["", "## Consistency", "", f"* Keys cited but not in the bibliography: {sorted(cited - {k for _, k, _ in entries}) or 'none'}",
          f"* Bibliography entries not cited in main.tex: {uncited or 'none'}"]
(ROOT / "research" / "REFERENCE_VERIFICATION.md").write_text("\n".join(lines) + "\n")
print("entries", len(entries), "cited", len(cited), "uncited", uncited)
