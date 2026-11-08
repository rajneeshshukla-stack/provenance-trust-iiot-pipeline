#!/usr/bin/env python3
"""Print <title> and lines matching regexes from downloaded pages.

Usage: python3 -I inspect_pages.py <webdir> <key> <regex> [<regex> ...]
For PDFs, pdftotext must have been run beforehand to produce body.txt.
"""
import html
import os
import re
import sys

webdir, key, pats = sys.argv[1], sys.argv[2], sys.argv[3:]
d = os.path.join(webdir, key)
p = os.path.join(d, "body.txt") if os.path.exists(os.path.join(d, "body.txt")) else os.path.join(d, "body")
raw = open(p, "rb").read().decode("utf-8", "replace")
t = re.search(r"<title[^>]*>(.*?)</title>", raw, re.S | re.I)
print("TITLE:", html.unescape(t.group(1)).strip() if t else None)
txt = re.sub(r"<script.*?</script>|<style.*?</style>", " ", raw, flags=re.S | re.I)
txt = re.sub(r"<[^>]+>", " ", txt)
txt = html.unescape(txt)
txt = re.sub(r"[ \t\r\f\v]+", " ", txt)
for pat in pats:
    ms = list(re.finditer(pat, txt, re.I))
    print(f"-- /{pat}/: {len(ms)} hits")
    for m in ms[:4]:
        s = max(0, m.start() - 160)
        e = min(len(txt), m.end() + 160)
        print("   ...", re.sub(r"\s+", " ", txt[s:e]), "...")
