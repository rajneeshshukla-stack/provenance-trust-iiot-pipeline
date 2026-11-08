#!/usr/bin/env python3
"""Fetch OpenAlex records for DOIs and print reconstructed abstracts.

Usage: python3 -I openalex_abstracts.py <outdir> <doi> [<doi> ...]
"""
import json
import subprocess
import sys
import time

outdir, dois = sys.argv[1], sys.argv[2:]
for doi in dois:
    f = f"{outdir}/oa_" + doi.replace("/", "_") + ".json"
    code = ""
    for attempt in range(5):
        r = subprocess.run(["curl", "-sS", "-o", f, "-w", "%{http_code}",
                            f"https://api.openalex.org/works/doi:{doi}?mailto=research-audit@example.org"],
                           capture_output=True, text=True)
        code = r.stdout.strip()
        if code in ("200", "404"):
            break
        time.sleep(5 * (attempt + 1))
    print("==", doi, "HTTP", code)
    if code != "200":
        continue
    w = json.load(open(f))
    inv = w.get("abstract_inverted_index") or {}
    pos = []
    for word, ps in inv.items():
        for p in ps:
            pos.append((p, word))
    abstract = " ".join(wd for _, wd in sorted(pos))
    src = ((w.get("primary_location") or {}).get("source") or {}).get("display_name")
    print("   title:", w.get("display_name"), "| year:", w.get("publication_year"), "| source:", src,
          "| type:", w.get("type"), "| cited_by:", w.get("cited_by_count"))
    print("   ABSTRACT:", abstract if abstract else None)
    time.sleep(1.5)
