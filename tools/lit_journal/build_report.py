#!/usr/bin/env python3
"""Assemble the final report from a template plus generated tables.

Usage: python3 -I build_report.py <template.md> <reference_verification.csv> <urls_opened.tsv> <out.md>
Markers in the template: {{REF_TABLE}}, {{URL_LIST}}.
"""
import csv
import sys

tpl, csv_path, tsv_path, out = sys.argv[1:5]


def cell(s):
    return s.replace("|", "\\|").replace("\n", " ")


def short_src(s):
    # keep the first source only, shortened, for the markdown table (full sources are in the CSV)
    first = s.split(" ; ")[0]
    first = first.replace("https://api.crossref.org/works/", "Crossref ")
    return first if len(first) < 95 else first[:92] + "..."


rows = list(csv.DictReader(open(csv_path, encoding="utf-8")))
lines = ["| # | Key | Short citation | Source checked (first; all in CSV) | Status | Correction needed |",
         "|---|---|---|---|---|---|"]
for r in rows:
    lines.append("| {n} | `{key}` | {c} | {s} | {st} | {co} |".format(
        n=r["n"], key=r["key"], c=cell(r["short_citation"]), s=cell(short_src(r["source_checked"])),
        st=("**" + r["status"] + "**") if r["status"] != "VERIFIED" else r["status"], co=cell(r["correction_needed"])))
ref_table = "\n".join(lines)

urls = ["| URL / endpoint | Access date | Method | Result |", "|---|---|---|---|"]
for i, l in enumerate(open(tsv_path, encoding="utf-8")):
    if i == 0:
        continue
    p = l.rstrip("\n").split("\t")
    if len(p) < 4:
        continue
    urls.append("| " + " | ".join(cell(x) for x in p[:4]) + " |")
url_list = "\n".join(urls)

t = open(tpl, encoding="utf-8").read()
t = t.replace("{{REF_TABLE}}", ref_table).replace("{{URL_LIST}}", url_list)
open(out, "w", encoding="utf-8").write(t)
print("written", out, len(t), "chars")
