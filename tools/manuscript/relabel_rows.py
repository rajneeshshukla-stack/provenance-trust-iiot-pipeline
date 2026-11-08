#!/usr/bin/env python3
"""Presentation-only additions to row labels of generated tables (values untouched).

generated/tabS_lifecycle.tex (Document S1, lifecycle analysis; written by analysis/analyze_v4.py): the row
"Decision on a superseded snapshot" records the final state ("recovered") only. The trace of this case
(tools/v9/a5_and_e09_e10.py, results/v9/summary/a5_e09_e10.json) shows that the decision bound to the superseded
snapshot is refused and that the observation is recovered only by a later decision on the current snapshot; the
label now says so, with the times taken from the generated macros. Every cell after the label is compared before
and after; the script refuses to write if anything else changes.

Usage: python3 -I relabel_rows.py PAPER_DIR   (idempotent)
"""
import sys
from pathlib import Path

f = Path(sys.argv[1]) / "generated" / "tabS_lifecycle.tex"
s = f.read_text()
MARK = "% row label extended by tools/manuscript/relabel_rows.py"
if MARK in s:
    print("already relabelled")
    sys.exit(0)
OLD = "Decision on a superseded snapshot &"
NEW = (r"Decision on a superseded snapshot (refused at \YEnineRefusedAt~s; released by a fresh decision at "
       r"\YEnineFreshAt~s) &")
assert s.count(OLD) == 1, "row not found"
t = s.replace(OLD, NEW)
cells = lambda x: [l.split("&", 1)[1] for l in x.splitlines() if "&" in l]  # noqa: E731
assert cells(s) == cells(t)
f.write_text(MARK + "\n" + t)
print("relabelled: tabS_lifecycle.tex (superseded-snapshot row)")
