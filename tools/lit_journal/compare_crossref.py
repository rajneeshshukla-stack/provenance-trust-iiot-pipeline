#!/usr/bin/env python3
"""Compare bbl entries with Crossref records.

Usage: python3 -I compare_crossref.py <main.bbl> <crossref_dir> <out_tsv>
Prints, per key, the bbl text and the Crossref fields side by side, plus automatic flags.
"""
import json
import re
import sys
import unicodedata

bbl, cdir, out = sys.argv[1], sys.argv[2], sys.argv[3]
s = open(bbl, encoding="utf-8").read()
items = re.split(r"\\bibitem", s)[1:]
entries = {}
for it in items:
    m = re.match(r"(?:\[(?:[^\[\]]|\[[^\]]*\])*\])?\{([^}]+)\}", it, re.S)
    entries[m.group(1)] = it[m.end():].strip()


def norm(t):
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"\\[a-zA-Z]+", " ", t)
    t = re.sub(r"[{}\\~'`\"^]", "", t)
    t = re.sub(r"[^a-z0-9 ]", " ", t.lower())
    return re.sub(r"\s+", " ", t).strip()


def dp(d):
    try:
        return "-".join(str(x) for x in d["date-parts"][0])
    except Exception:
        return ""


rows = []
idx = [l.rstrip("\n").split("\t") for l in open(f"{cdir}/index.tsv")]
for key, doi, code, url in idx:
    text = entries.get(key, "")
    if code != "200":
        rows.append((key, doi, code, "", "", "", "", "", "", "", "", "", "NOT IN CROSSREF"))
        continue
    msg = json.load(open(f"{cdir}/{key}.json"))["message"]
    title = " ".join(msg.get("title", []))
    sub = " ".join(msg.get("subtitle", []))
    authors = msg.get("author", [])
    fam = [a.get("family", a.get("name", "")) for a in authors]
    given = [a.get("given", "") for a in authors]
    cont = " | ".join(msg.get("container-title", []))
    scont = " | ".join(msg.get("short-container-title", []))
    vol = msg.get("volume", "")
    iss = msg.get("issue", "")
    page = msg.get("page", "")
    artno = msg.get("article-number", "")
    issued = dp(msg.get("issued", {}))
    pprint = dp(msg.get("published-print", {}))
    ponline = dp(msg.get("published-online", {}))
    typ = msg.get("type", "")
    ev = msg.get("event", {})
    evs = (ev.get("name", "") + " / " + ev.get("location", "")) if ev else ""
    flags = []
    nt = norm(text)
    if norm(title) not in nt:
        flags.append("TITLE?")
    for f in fam:
        if norm(f) and norm(f).split()[-1] not in nt:
            flags.append(f"AUTHOR?{f}")
    if vol and not re.search(r"\{\\bf\s*\d{4}\}, \{\\em\s*" + re.escape(vol) + r"\}", text) and f"{{\\em {vol}}}" not in text and vol not in text:
        flags.append(f"VOL?{vol}")
    pg = page or artno
    if pg:
        p0 = pg.split("-")[0]
        if p0 not in text:
            flags.append(f"PAGE?{pg}")
    yrs = re.findall(r"\b(19|20)\d{2}\b", text)
    yr_text = re.findall(r"\b(?:19|20)\d{2}\b", text)
    iy = issued[:4]
    if iy and iy not in yr_text:
        flags.append(f"YEAR?{iy}")
    rows.append((key, doi, code, typ, title + (": " + sub if sub else ""), "; ".join(f"{g} {f}".strip() for g, f in zip(given, fam)), cont, scont, vol, iss, pg, f"issued {issued}; print {pprint}; online {ponline}; event {evs}", " ".join(flags) or "OK"))

with open(out, "w") as fo:
    fo.write("key\tdoi\thttp\ttype\tcr_title\tcr_authors\tcr_container\tcr_short\tvol\tissue\tpages\tdates\tauto_flags\n")
    for r in rows:
        fo.write("\t".join(str(x).replace("\t", " ") for x in r) + "\n")
for r in rows:
    print("==", r[0], "|", r[1], "|", r[3], "|", r[12])
    print("   CR:", r[4], "||", r[5], "||", r[6], "||", r[8], r[9], r[10], "||", r[11])
    print("   BBL:", re.sub(r"\s+", " ", entries.get(r[0], ""))[:400])
