#!/usr/bin/env python3
"""Presentation-only layout change of a generated table (values untouched).

generated/tab_effects.tex (article Table 5, written by tools/v7/analysis_v7.py as tab_v7_effects.tex): set the table to the MDPI full
width with a flexible Class column, so that class labels such as "equivalent^s 2/4, worse 1/4, different within
margin 1/4" no longer wrap into three lines, and add a rule before the five rows that summarize the four factorial
cells. The data rows are compared before and after; the script refuses to write if any row changes.

Usage: python3 -I table_layout.py PAPER_DIR   (idempotent)
"""
import re
import sys
from pathlib import Path

f = Path(sys.argv[1]) / "generated" / "tab_effects.tex"
s = f.read_text()
MARK = "% layout adjusted by tools/manuscript/table_layout.py"
if MARK in s:
    print("already adjusted")
    sys.exit(0)


def rows(t):
    return [l.strip() for l in t.splitlines() if l.strip().endswith(r"\\") and "&" in l]


before = rows(s)
old_head = r"\begin{tabular}{@{}lllllr>{\raggedright\arraybackslash}p{3.0cm}l@{}}\toprule"
new_head = r"\begin{tabularx}{\fulllength}{@{}lllllr>{\raggedright\arraybackslash}Xl@{}}\toprule"
assert s.count(old_head) == 1 and s.count(r"\bottomrule\end{tabular}") == 1
s = s.replace(old_head, new_head).replace(r"\bottomrule\end{tabular}", r"\bottomrule\end{tabularx}")
first_fg = next(l for l in s.splitlines() if l.startswith(r"PBTI-SH $-$ \sys & 4 cells"))
s = s.replace(first_fg, "\\midrule\n" + first_fg, 1)
after = rows(s)
assert before == after, "data rows changed"
lines = s.splitlines()
lines.insert(1, MARK + " (full width, flexible Class column, rule before the factorial-cell rows; values unchanged)")
f.write_text("\n".join(lines) + "\n")
print("adjusted", f, len(after), "rows unchanged")
