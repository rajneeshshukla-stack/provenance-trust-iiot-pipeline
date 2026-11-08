#!/usr/bin/env python3
"""Fetch Crossref records for every DOI in a .bbl file.

Usage: python3 -I fetch_crossref.py <main.bbl> <outdir>
Writes <outdir>/<key>.json (raw Crossref response) and <outdir>/index.tsv (key, doi, http status).
"""
import json
import re
import subprocess
import sys
import time
import urllib.parse

bbl, outdir = sys.argv[1], sys.argv[2]
s = open(bbl, encoding="utf-8").read()
items = re.split(r"\\bibitem", s)[1:]
rows = []
for it in items:
    m = re.match(r"(?:\[(?:[^\[\]]|\[[^\]]*\])*\])?\{([^}]+)\}", it, re.S)
    key = m.group(1)
    d = re.search(r"https://doi\.org/([^}\s]+)\}", it)
    if d:
        doi = d.group(1).rstrip("}")
        rows.append((key, doi))

with open(f"{outdir}/index.tsv", "w") as idx:
    for key, doi in rows:
        url = "https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="/") + "?mailto=research-audit@example.org"
        for attempt in range(4):
            r = subprocess.run(["curl", "-sS", "-o", f"{outdir}/{key}.json", "-w", "%{http_code}", url],
                               capture_output=True, text=True)
            code = r.stdout.strip()
            if code == "200" or code == "404":
                break
            time.sleep(3 * (attempt + 1))
        idx.write(f"{key}\t{doi}\t{code}\t{url}\n")
        print(key, doi, code, flush=True)
        time.sleep(0.4)
