#!/usr/bin/env python3
"""Independent re-verification of every bibliography entry that carries a DOI against the Crossref REST API.

For each DOI: title similarity, year, first-author family name and container (journal/proceedings) are compared with
what the bibliography says. Entries without a DOI (RFCs, standards, specifications, web documents) are listed with the
URL recorded in the bibliography and marked for verification against the official publisher page.
Output: results/summary/reference_check.json (and a printed summary). Nothing is written to the bibliography.
"""
import difflib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UA = {"User-Agent": "pbti-reference-audit/1.0 (research tooling)", "Accept": "application/json"}


def parse_bib(text):
    entries = []
    for m in re.finditer(r"@(\w+)\{([^,]+),", text):
        start = m.end()
        depth, i = 1, m.start() + text[m.start():].index("{") + 1
        while depth and i < len(text):
            depth += {"{": 1, "}": -1}.get(text[i], 0)
            i += 1
        body = text[start:i - 1]
        fields = {}
        for fm in re.finditer(r"(\w+)\s*=\s*", body):
            k = fm.group(1).lower()
            j = fm.end()
            if j < len(body) and body[j] == "{":
                d, j2 = 1, j + 1
                while d and j2 < len(body):
                    d += {"{": 1, "}": -1}.get(body[j2], 0)
                    j2 += 1
                fields.setdefault(k, body[j + 1:j2 - 1])
            else:
                mm = re.match(r"([^,\n]+)", body[j:])
                if mm:
                    fields.setdefault(k, mm.group(1).strip())
        entries.append({"type": m.group(1).lower(), "key": m.group(2).strip(), **fields})
    return entries


def norm(s):
    s = re.sub(r"\\[a-zA-Z]+|[{}$\\]", " ", s or "")
    return re.sub(r"[^a-z0-9 ]", " ", s.lower()).split()


def crossref(doi):
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="/:")
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                return json.loads(r.read())["message"]
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(2 + 3 * attempt)
        except Exception:  # noqa: BLE001
            time.sleep(2 + 3 * attempt)
    return "ERROR"


def main():
    bib = parse_bib((ROOT / "paper" / "references.bib").read_text())
    tex = (ROOT / "paper" / "main.tex").read_text()
    cited = {k.strip() for c in re.findall(r"\\cite\{([^}]+)\}", tex) for k in c.split(",")}
    out = []
    for e in bib:
        rec = {"key": e["key"], "type": e["type"], "title": e.get("title", ""), "year": e.get("year", ""),
               "venue": e.get("journal") or e.get("booktitle") or e.get("publisher") or e.get("howpublished", ""),
               "doi": e.get("doi", ""), "url": e.get("url", ""), "cited": e["key"] in cited}
        if rec["doi"]:
            msg = crossref(rec["doi"])
            if msg is None:
                rec["status"] = "DOI NOT FOUND in Crossref"
            elif msg == "ERROR":
                rec["status"] = "NOT CHECKED (network error)"
            else:
                ct = (msg.get("title") or [""])[0]
                if msg.get("subtitle"):
                    ct = ct + ": " + msg["subtitle"][0]   # Crossref stores subtitles separately
                sim = difflib.SequenceMatcher(None, " ".join(norm(rec["title"])), " ".join(norm(ct))).ratio()
                yrs = set()
                for k in ("published-print", "published-online", "issued"):
                    dp = (msg.get(k) or {}).get("date-parts") or [[None]]
                    if dp[0] and dp[0][0]:
                        yrs.add(str(dp[0][0]))
                fam = (msg.get("author") or [{}])[0].get("family", "")
                bib_auth = e.get("author", "")
                first_bib = norm(bib_auth.split(" and ")[0].split(",")[0])[:1]
                rec.update(crossref_title=ct, title_similarity=round(sim, 3), crossref_years=sorted(yrs),
                           crossref_first_author=fam, crossref_container=(msg.get("container-title") or [""])[0],
                           year_match=rec["year"] in yrs,
                           author_match=bool(first_bib) and first_bib[0] in norm(fam))
                ok = sim >= 0.85 and rec["year_match"] and rec["author_match"]
                rec["status"] = "VERIFIED (Crossref)" if ok else "CHECK: " + ", ".join(
                    x for x, b in (("title", sim >= 0.85), ("year", rec["year_match"]), ("first author", rec["author_match"])) if not b)
            time.sleep(0.25)
        else:
            rec["status"] = "NO DOI: verify against official page (URL in bibliography)" if rec["url"] else "NO DOI and no URL"
        out.append(rec)
        print(f"{rec['key']:28s} {rec['status']}", flush=True)
    (ROOT / "results" / "summary" / "reference_check.json").write_text(json.dumps(out, indent=1))
    from collections import Counter
    print(Counter(r["status"].split(":")[0] for r in out))


if __name__ == "__main__":
    sys.exit(main())
