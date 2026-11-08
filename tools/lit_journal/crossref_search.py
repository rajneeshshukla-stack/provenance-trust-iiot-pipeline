#!/usr/bin/env python3
"""Search Crossref works (2023-2026) and print candidates.

Usage: python3 -I crossref_search.py <outdir> "<query>" [rows]
Saves the raw JSON to <outdir>/<slug>.json and prints DOI | year | type | title | container.
"""
import json
import re
import subprocess
import sys
import urllib.parse

outdir, q = sys.argv[1], sys.argv[2]
rows = sys.argv[3] if len(sys.argv) > 3 else "20"
slug = re.sub(r"[^A-Za-z0-9]+", "_", q)[:80]
params = {
    "query.bibliographic": q,
    "filter": "from-pub-date:2023-01-01,until-pub-date:2026-12-31",
    "rows": rows,
    "select": "DOI,title,container-title,type,issued,author,abstract",
    "mailto": "research-audit@example.org",
}
url = "https://api.crossref.org/works?" + urllib.parse.urlencode(params)
r = subprocess.run(["curl", "-sS", "-o", f"{outdir}/{slug}.json", "-w", "%{http_code}", url], capture_output=True, text=True)
print("HTTP", r.stdout, url)
try:
    d = json.load(open(f"{outdir}/{slug}.json"))
except Exception as e:
    print("ERR", e)
    sys.exit(0)
for it in d["message"]["items"]:
    y = it.get("issued", {}).get("date-parts", [[None]])[0][0]
    t = " ".join(it.get("title", [""]))
    c = " ".join(it.get("container-title", [""]))
    a = it.get("author", [])
    fa = a[0].get("family", "") if a else ""
    ab = "ABS" if it.get("abstract") else "-"
    print(f"{it['DOI']} | {y} | {it.get('type')} | {fa} | {t[:110]} | {c[:60]} | {ab}")
