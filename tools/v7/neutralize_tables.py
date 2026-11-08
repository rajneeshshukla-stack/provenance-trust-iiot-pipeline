#!/usr/bin/env python3
"""Replace internal arm and stage labels in the generated LaTeX tables by the neutral display names of the V7 article.

Only labels change; every number is copied unchanged (a check below compares the sequence of numeric tokens of each
file before and after). Source: SRC (the V6 generated/ directory, unchanged); destination: DST (the V7 generated/).

Display names: B5 with the one-shot rule, R = 60 s, C = 10 s -> B5_{60/10}; deferring rule with R, C -> B5_{D R/C};
one-shot rule at R = 0, C = 10 -> B5_{0/10}; event-driven -> B5_{ev}; likewise for PBTI-R.

Layout: in the factorial-cell table the parenthetical list of high factors is moved from the first row of each cell
into the empty first-column cells of the following rows, so that the table fits the page (text and numbers
unchanged; checked below).

Usage: python3 -B neutralize_tables.py SRC_DIR DST_DIR
"""
import re
import sys
from pathlib import Path

SRC, DST = Path(sys.argv[1]), Path(sys.argv[2])
FILES = ["tabS_v4_a1_tests.tex", "tabS_v4_a3.tex", "tabS_v4_a3_gates.tex", "tabS_v4_a3f.tex", "tabS_v4_a5.tex",
         "tabS_env.tex", "tab_ablations.tex", "tabS_v4_temporal.tex", "tabS_v4_a3_scenarios.tex", "tabS_v3_b5.tex"]
ARM = [
    (r"B5-oneshot-d(\d+)c(\d+)", r"B5\\textsubscript{\1/\2}"),
    (r"(B5|PBTI-R)-d(\d+)c(\d+)", r"\1\\textsubscript{D\2/\3}"),
    (r"PBTI-R-hist", r"PBTI-R\\textsubscript{60/10}"),
    (r"B5-hist", r"B5\\textsubscript{60/10}"),
    (r"PBTI-R-event", r"PBTI-R\\textsubscript{ev}"),
    (r"B5-event", r"B5\\textsubscript{ev}"),
]
SPECIFIC = {
    "tabS_v4_a1_tests.tex": [(r"\\caption\{A1 \(seeds 21--40\): every preregistered comparison",
                              r"\\caption{Review-schedule evaluation (seeds 21--40): every registered comparison"),
                             (r"mechanical classification of the preregistration", "mechanical classification of the registered plan")],
    "tabS_v4_a3.tex": [(r"\\caption\{A3 \(seeds 21--40;", r"\\caption{Selective-hold grid (seeds 21--40;")],
    "tabS_v4_a3_gates.tex": [(r"(?m)^A3F &", "cells &"), (r"(?m)^A3 &", "grid &")],
    "tabS_v4_a5.tex": [(r"discretionary \(V3\)", "discretionary")],
    "tabS_env.tex": [(r"\(64 revision-2, 50 V3\)", "(64 earlier scenario runs, 50 feed-level extension runs)")],
    "tab_ablations.tex": [(r"(?m)^A(\d+) ", r"Ab\1 ")],
}
NUM = re.compile(r"(?<![A-Za-z])[-+]?\d[\d{},.]*")


def wrap_cell_labels(text, width=34):
    """Move '(factor, factor, ...)' of each factorial cell into the empty first cells of the following rows."""
    lines = text.split("\n")
    out, i = [], 0
    while i < len(lines):
        m = re.match(r"^(run\d+(?:\$\^\{FG\}\$)?) \((.*?)\) & (.*)$", lines[i])
        if not m:
            out.append(lines[i]); i += 1; continue
        label, factors, rest = m.group(1), m.group(2), m.group(3)
        words, chunks, cur = [w + "," for w in factors.split(", ")], [], ""
        words[-1] = words[-1][:-1]
        for w in words:
            if cur and len(cur) + 1 + len(w) > width:
                chunks.append(cur); cur = w
            else:
                cur = (cur + " " + w).strip()
        chunks.append(cur)
        chunks[0] = "(" + chunks[0]
        chunks[-1] = chunks[-1] + ")"
        out.append(f"{label} & {rest}")
        i += 1
        for c in chunks:
            if i < len(lines) and lines[i].startswith(" & "):
                out.append(c + lines[i]); i += 1
            else:
                raise SystemExit("not enough continuation rows for the factor list")
    joined = "\n".join(out)
    if re.sub(r"\s+", " ", joined.replace("\n", " ")).replace(" ", "") == "":
        raise SystemExit("empty table")
    return joined


def numbers(text):
    # numeric tokens outside the replaced labels (labels contain digits such as R and C values; drop them first)
    t = re.sub(r"(B5|PBTI-R)-(d\d+c\d+|oneshot-d\d+c\d+)", "", text)
    t = re.sub(r"(B5|PBTI-R)\\textsubscript\{[^}]*\}", "", t)
    t = re.sub(r"(?m)^A(\d+) ", "", t)
    t = re.sub(r"(?m)^Ab(\d+) ", "", t)
    t = re.sub(r"\\caption\{A\d ", "", t)
    t = t.replace("(64 revision-2, 50 V3)", "").replace("(64 earlier scenario runs, 50 feed-level extension runs)", "")
    t = re.sub(r"\\caption\{(Review-schedule evaluation|Selective-hold grid) ", "", t)
    t = t.replace("discretionary (V3)", "discretionary")
    t = re.sub(r"(?m)^(A3F|A3|cells|grid) &", "", t)
    return NUM.findall(t)


for f in FILES:
    src = (SRC / f).read_text()
    out = src
    for pat, rep in SPECIFIC.get(f, []):
        out = re.sub(pat, rep, out)
    for pat, rep in ARM:
        out = re.sub(pat, rep, out)
    if f == "tabS_v4_a3f.tex":
        before = re.sub(r"\s", "", out.replace("&", ""))
        out = wrap_cell_labels(out)
        # same multiset of characters apart from whitespace and column separators (only the labels move)
        if sorted(before) != sorted(re.sub(r"\s", "", out.replace("&", ""))):
            raise SystemExit("layout step changed the content of tabS_v4_a3f.tex")
    if numbers(src) != numbers(out):
        raise SystemExit(f"numeric content changed in {f}")
    left = re.findall(r"V3|V4|revision-2|-hist\b|B5-event|PBTI-R-event|B5-d\d|PBTI-R-d\d", out)
    (DST / f).write_text(out.replace("% AUTO-GENERATED by analysis/analyze_v4.py -- do not edit by hand",
                                     "% AUTO-GENERATED by analysis/analyze_v4.py; labels neutralized by tools/v7/neutralize_tables.py"))
    print(f"{f}: ok; remaining internal labels: {sorted(set(left)) or 'none'}")
