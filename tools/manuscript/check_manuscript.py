#!/usr/bin/env python3
"""Consistency checks of the manuscript and its supplement.

Run after tools/manuscript/build_all.sh:  python3 -I check_manuscript.py PAPER_DIR [MAX_MAIN_PAGES]

Failing checks (exit code 1):
 1. every data macro (\\R..., \\V..., \\W..., \\X..., \\Y...) used in main.tex / supplementary.tex is defined in generated/*.tex;
 2. no "??" (unresolved \\ref, \\Sref or \\Mref) in either PDF and no undefined reference or citation in the last pass;
 3. no internal version, stage or revision wording in reader-facing text (V2-V9, "this revision", "previous version",
    campaign names A0-A5/A3F, "-hist" arm names; repository paths and file names are allowed);
 4. supplementary tables and figures are numbered consecutively, and every "Table S<n>" / "Figure S<n>" printed in
    the article exists in the supplement;
 5. the article PDF has at most MAX_MAIN_PAGES pages (default 25; everything counted, supplement excluded);
 6. the abstract printed in the PDF has at most 200 words;
 7. every \\cite key exists in references.bib and every entry of references.bib is cited (no orphan entries);
 8. every figure is included at a scale of at least 0.98 of its natural size (so the 8-9 pt labels stay 8-9 pt).
Reported only: author placeholders, overfull boxes, page count of the supplement.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

D = Path(sys.argv[1]).resolve()
MAXP = int(sys.argv[2]) if len(sys.argv) > 2 else 25
res = {"checks": {}, "fail": []}


def pdftext(p, layout=True):
    a = ["pdftotext"] + (["-layout"] if layout else []) + [str(p), "-"]
    return subprocess.run(a, capture_output=True, text=True).stdout


def pages(p):
    out = subprocess.run(["pdfinfo", str(p)], capture_output=True, text=True).stdout
    return int(re.search(r"Pages:\s+(\d+)", out).group(1))


def strip_comments(s):
    return re.sub(r"(?<!\\)%.*$", "", s, flags=re.M)


main_src, supp_src = strip_comments((D / "main.tex").read_text()), strip_comments((D / "supplementary.tex").read_text())

# 1 ---------------------------------------------------------------- data macros
defined = set()
for f in (D / "generated").glob("*.tex"):
    defined |= set(re.findall(r"\\newcommand\{\\([A-Za-z]+)\}", f.read_text()))
missing = {}
for name, src in (("main.tex", main_src), ("supplementary.tex", supp_src)):
    used = set(re.findall(r"\\([RVWXY][A-Z][A-Za-z]*)", src))
    m = sorted(u for u in used if u not in defined and not u.startswith(("Rightarrow", "Vert", "Wide")))
    if m:
        missing[name] = m
res["checks"]["undefined_data_macros"] = missing
if missing:
    res["fail"].append("undefined data macros")

# 2 ---------------------------------------------------------------- unresolved references
main_txt, supp_txt = pdftext(D / "main.pdf"), pdftext(D / "supplementary.pdf")
q = {"main": main_txt.count("??"), "supplementary": supp_txt.count("??")}
res["checks"]["unresolved_??"] = q
if any(q.values()):
    res["fail"].append("unresolved references (??)")
und = {}
for log in ("main.log", "supplementary.log"):
    t = (D / log).read_text(errors="replace")
    und[log] = len(re.findall(r"(?:Reference|Citation) `[^']+' on page \d+ undefined", t)) + \
        len(re.findall(r"Undefined (?:supplementary|article) label", t))
res["checks"]["undefined_in_last_pass"] = und
if any(und.values()):
    res["fail"].append("undefined references in log")

# 3 ---------------------------------------------------------------- internal wording
LABELS = re.compile(r"(?<![\w.-])V[2-9](?:\.\d)?\b|(?i:revision[- ]2|this revision|previous version|earlier version of|"
                    r"the revision\b|moved from|moved to the|relocated|formerly)|\bA[0-5]\b|\bA3F\b|\bA3S\b|-hist\b|\bhist\b")
PATHS = re.compile(r"[\w./-]*(?:A[0-5]|v[2-9]|V[2-9])[\w./-]*\.(?:jsonl|json|md|py|csv|tex|pdf)|research/V[34][\w/.-]*|"
                   r"experiments/v4_configs[\w/.-]*|experiments/v9[\w/.-]*|results/v[479][\w/.-]*|tools/v[79][\w/.-]*|v3_[\w.-]+|\bV3_[\w.-]+|b5_corrected_v9")


def label_hits(text):
    t = PATHS.sub(" ", re.sub(r"-\n\s*", "", text))
    return [t[max(0, m.start() - 50):m.end() + 50].replace("\n", " ") for m in LABELS.finditer(t)]


res["checks"]["internal_wording_main"] = label_hits(main_txt)
res["checks"]["internal_wording_supplement"] = label_hits(supp_txt)
if res["checks"]["internal_wording_main"] or res["checks"]["internal_wording_supplement"]:
    res["fail"].append("internal wording")

# 4 ---------------------------------------------------------------- supplement numbering and article citations
flat = re.sub(r"\s+", " ", pdftext(D / "main.pdf", layout=False))
cited_t, cited_f = set(), set()
for kind, store in (("Table", cited_t), ("Figure", cited_f)):
    for m in re.finditer(kind + r"s? (S\d+(?:(?:, | and |–|--)S\d+)*)", flat):
        nums = [int(x) for x in re.findall(r"S(\d+)", m.group(1))]
        if "–" in m.group(1) or "--" in m.group(1):
            for a, b in re.findall(r"S(\d+)(?:–|--)S(\d+)", m.group(1)):
                nums += list(range(int(a), int(b) + 1))
        store.update(nums)
supp_flat = pdftext(D / "supplementary.pdf", layout=False)
have_t = [int(n) for n in re.findall(r"Table S(\d+):", supp_flat)]    # caption format of the supplement
have_f = [int(n) for n in re.findall(r"Figure S(\d+):", supp_flat)]
st, sf = sorted(set(have_t)), sorted(set(have_f))
res["checks"]["supplement_tables"] = {"count": len(st), "consecutive": st == list(range(1, len(st) + 1)),
                                      "cited_by_article_missing": sorted(n for n in cited_t if n not in st)}
res["checks"]["supplement_figures"] = {"count": len(sf), "consecutive": sf == list(range(1, len(sf) + 1)),
                                       "cited_by_article_missing": sorted(n for n in cited_f if n not in sf)}
if (res["checks"]["supplement_tables"]["cited_by_article_missing"] or
        res["checks"]["supplement_figures"]["cited_by_article_missing"] or
        not res["checks"]["supplement_tables"]["consecutive"] or not res["checks"]["supplement_figures"]["consecutive"]):
    res["fail"].append("supplement numbering or article citations")
res["checks"]["supplement_items_cited_by_article"] = {"tables": sorted(cited_t), "figures": sorted(cited_f)}

# 5 ---------------------------------------------------------------- pages
pm, ps = pages(D / "main.pdf"), pages(D / "supplementary.pdf")
res["checks"]["pages"] = {"main": pm, "limit": MAXP, "supplementary": ps}
if pm > MAXP:
    res["fail"].append(f"article has {pm} pages (> {MAXP})")

# 6 ---------------------------------------------------------------- abstract
p1 = subprocess.run(["pdftotext", "-f", "1", "-l", "1", str(D / "main.pdf"), "-"], capture_output=True, text=True).stdout
m = re.search(r"Abstract:?\s*(.*?)Keywords:", p1, re.S)
aw = len(re.sub(r"^\s*\d+\s*$", "", m.group(1), flags=re.M).split()) if m else None
res["checks"]["abstract_words_pdf"] = aw
if aw is None or aw > 200:
    res["fail"].append("abstract length")

# 7 ---------------------------------------------------------------- bibliography
bib = (D / "references.bib").read_text()
keys = re.findall(r"@\w+\{([^,\s]+),", bib)
cited = set()
for mm in re.finditer(r"\\cite[pt]?\*?(?:\[[^\]]*\])?\{([^}]+)\}", main_src):
    cited |= {k.strip() for k in mm.group(1).split(",")}
res["checks"]["bibliography"] = {"entries": len(keys), "cited": len(cited),
                                 "cited_not_in_bib": sorted(cited - set(keys)),
                                 "orphan_entries": sorted(set(keys) - cited),
                                 "duplicate_keys": sorted({k for k in keys if keys.count(k) > 1})}
if cited - set(keys) or set(keys) - cited or res["checks"]["bibliography"]["duplicate_keys"]:
    res["fail"].append("bibliography")
res["checks"]["cites_in_supplement_source"] = len(re.findall(r"\\cite", supp_src))

# 8 ---------------------------------------------------------------- figure scale
W = {"main_full": 525.52245, "supp": 17.4 / 2.54 * 72.27}
figs = []
for name, src, width in (("main", main_src, W["main_full"]), ("supp", supp_src, W["supp"])):
    for mm in re.finditer(r"\\includegraphics(?:\[([^\]]*)\])?\{([^}]+)\}", src):
        opt, path = mm.group(1) or "", mm.group(2)
        info = subprocess.run(["pdfinfo", str(D / path)], capture_output=True, text=True).stdout
        wbp = float(re.search(r"Page size:\s+([\d.]+) x", info).group(1))
        nat = wbp * 72.27 / 72
        fw = re.search(r"width=([\d.]*)\\linewidth", opt)
        target = (float(fw.group(1) or 1) * width) if fw else nat
        figs.append({"doc": name, "file": path, "natural_pt": round(nat, 1), "placed_pt": round(target, 1),
                     "scale": round(target / nat, 3)})
res["checks"]["figure_scale"] = figs
if any(f["scale"] < 0.98 for f in figs):
    res["fail"].append("figure scaled below 0.98")

# 9 ---------------------------------------------------------------- pending markers ([[...]] check markers, development placeholders)
pend = {f: len(re.findall(r"V71-PENDING|\[\[[A-Z-]+\]\]|DEV PLACEHOLDER", (D / f).read_text())) for f in ("main.tex", "supplementary.tex", "references.bib")}
pend["generated/macros_Y.tex"] = len(re.findall(r"DEV PLACEHOLDER", (D / "generated" / "macros_Y.tex").read_text()))
res["checks"]["pending_markers"] = pend
if any(pend.values()):
    res["fail"].append("pending markers")

# reported only -------------------------------------------------------
res["checks"]["author_placeholders_main"] = len(re.findall(r"AUTHORS? TO (?:COMPLETE|CONFIRM)|AUTHOR INPUT REQUIRED",
                                                           (D / "main.tex").read_text()))
ov = {}
for log in ("main.log", "supplementary.log"):
    t = (D / log).read_text(errors="replace")
    ov[log] = [float(x) for x in re.findall(r"Overfull \\[hv]box \(([\d.]+)pt too", t)]
res["checks"]["overfull_boxes_pt"] = ov
res["verdict"] = "PASS" if not res["fail"] else "FAIL: " + "; ".join(res["fail"])
out = json.dumps(res, indent=1, ensure_ascii=False)
(D / "manuscript_checks.json").write_text(out)
print(out[:7000])
sys.exit(1 if res["fail"] else 0)
