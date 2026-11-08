#!/usr/bin/env python3
"""Extract manuscript sentences (with file:line) that use claim language, with generated macros expanded.

Usage: paper_sentences.py [regex ...]   (default: the claim-language keywords of the audit brief)
Writes results/stats_audit/paper_claim_sentences.tsv
"""
import csv
import re
import sys

REPO = "/home/claude/PBTI_v7/work/repo_v6"
OUT = "/home/claude/PBTI_v7/results/stats_audit/paper_claim_sentences.tsv"
MACRO_FILES = [REPO + "/paper/generated/v4_macros.tex", REPO + "/paper/generated/v3_macros.tex",
               REPO + "/paper/generated/results_macros.tex"]
DEF = re.compile(r"\\newcommand\{\\([A-Za-z]+)\}\{(.*)\}\s*$")


def load_macros():
    m = {}
    for f in MACRO_FILES:
        try:
            for line in open(f):
                g = DEF.match(line.strip())
                if g:
                    m[g.group(1)] = g.group(2)
        except FileNotFoundError:
            pass
    return m


MAC = load_macros()
TOK = re.compile(r"\\([A-Za-z]+)")


def expand(s, depth=0):
    if depth > 5:
        return s

    def rep(mo):
        k = mo.group(1)
        if k in MAC:
            return "\u27e8" + expand(MAC[k], depth + 1) + "\u27e9"
        return mo.group(0)
    return TOK.sub(rep, s)


def sentences(text):
    # crude sentence split that keeps LaTeX intact
    parts = re.split(r"(?<=[.;:])\s+(?=[A-Z\\(])", text)
    return [p for p in parts if p.strip()]


KEYS = [r"equivalen", r"identical", r"better beyond", r"worse beyond", r"significan", r"within the margin",
        r"within margin", r"\bG[1-4]F?\b", r"gate", r"confirmatory", r"exploratory", r"preregist", r"pre-regist",
        r"inconclusive", r"Holm", r"margin"]


def main():
    keys = sys.argv[1:] or KEYS
    rx = re.compile("|".join(keys), re.I)
    rows = []
    for fname in ("main.tex", "supplementary.tex"):
        path = f"{REPO}/paper/{fname}"
        for ln, line in enumerate(open(path), 1):
            if line.lstrip().startswith("%"):
                continue
            for s in sentences(line.rstrip("\n")):
                e = expand(s)
                if rx.search(e) or rx.search(s):
                    rows.append((f"paper/{fname}:{ln}", s.strip(), e.strip()))
    with open(OUT, "w", newline="") as fh:
        w = csv.writer(fh, delimiter="\t")
        w.writerow(["loc", "raw", "expanded"])
        w.writerows(rows)
    print(len(rows), "sentences ->", OUT)


if __name__ == "__main__":
    main()
