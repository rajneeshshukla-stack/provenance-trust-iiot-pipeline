#!/usr/bin/env python3
"""Consistency gate between the manuscript and the generated results.

* lists every \\R<name> result macro used in paper/*.tex that analysis/analyze.py did not define;
* writes paper/generated/missing_macros.tex with visible red placeholders (drafts only);
* creates placeholder files for generated tables that do not exist yet;
* exits non-zero if anything is missing (the final build must pass with zero missing).
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "paper"
defined = set(re.findall(r"\\newcommand\{\\(R[A-Za-z]+)\}", (P / "generated" / "results_macros.tex").read_text()))
v3 = P / "generated" / "v3_macros.tex"          # V3: macros of analysis/analyze_v3.py (\\V...)
if v3.exists():
    defined |= set(re.findall(r"\\newcommand\{\\(V[A-Za-z]+)\}", v3.read_text()))
v4 = P / "generated" / "v4_macros.tex"          # V4: macros of analysis/analyze_v4.py (\\W...)
if v4.exists():
    defined |= set(re.findall(r"\\newcommand\{\\(W[A-Za-z]+)\}", v4.read_text()))
used, tables = set(), set()
for f in ("main.tex", "supplementary.tex"):
    p = P / f
    if p.exists():
        t = p.read_text()
        used |= set(re.findall(r"\\(R[A-Z][A-Za-z]+)", t)) | set(re.findall(r"\\(V[A-Z][A-Za-z]+)", t))
        used |= set(re.findall(r"\\(W[A-Z][A-Za-z]+)", t))
        tables |= set(re.findall(r"\\input\{(generated/[^}]+)\}", t))
missing = sorted(used - defined - {"Rescorla"})
with open(P / "generated" / "missing_macros.tex", "w") as fh:
    fh.write("% placeholders for result macros not (yet) produced by analysis/analyze.py\n")
    for m in missing:
        fh.write(f"\\providecommand{{\\{m}}}{{\\textcolor{{red}}{{\\textbf{{[{m}]}}}}}}\n")
missing_tables = []
for t in sorted(tables):
    f = P / (t if t.endswith(".tex") else t + ".tex")
    if not f.exists() and "missing_macros" not in t and "results_macros" not in t and "v3_macros" not in t \
            and "v4_macros" not in t:
        f.write_text("\\textcolor{red}{\\textbf{[RESULT PENDING: " + f.name.replace("_", "\\_") + "]}}\n")
        missing_tables.append(f.name)
print(f"macros used: {len(used)}, defined: {len(defined)}, missing: {len(missing)}")
for m in missing:
    print("  MISSING", m)
for t in missing_tables:
    print("  PLACEHOLDER TABLE", t)
sys.exit(1 if (missing or missing_tables) else 0)
