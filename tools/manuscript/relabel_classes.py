#!/usr/bin/env python3
"""Presentation-only relabelling of one comparison class in the generated tables (values untouched).

The registered classification rule (analysis/analyze_v4.py:classify, unchanged) names a comparison whose
Holm-adjusted test is significant but which is neither equivalent within the margin (90% CI inside +-margin) nor
beyond it (95% CI beyond the margin) "different, within margin" (code "dw").  Because its 95% interval crosses a
margin boundary, the comparison establishes neither equivalence nor a difference beyond the margin, and the point
estimate can lie on either side of the boundary.  This script keeps the code "dw" and the classification, and replaces
only the wording of the legends and of the class column of the effect table by "significant, margin unresolved",
naming the historical label once.  Every data row is compared before and after; the script refuses to write if any
value other than the class wording changes.

Usage: python3 -I relabel_classes.py PAPER_DIR   (idempotent)
"""
import re
import sys
from pathlib import Path

D = Path(sys.argv[1]) / "generated"
MARK = "% class wording adjusted by tools/manuscript/relabel_classes.py"
LEG_OLD = "dw, different within the margin (significant, not equivalent)"
LEG_NEW = ("dw, significant, margin unresolved (Holm-adjusted $p<0.05$, 95\\% CI crossing a margin boundary; "
           "historical label ``different within the margin'')")
done = []
for f in sorted(D.glob("*.tex")):
    s = f.read_text()
    if MARK in s or f.name.endswith("macros.tex") or f.name.startswith("macros_"):
        continue
    t = s.replace(LEG_OLD, LEG_NEW)
    if f.name == "tab_effects.tex":
        t = re.sub(r"different within margin", "significant, margin unresolved", t)
    if t != s:
        strip = lambda x: re.sub(r"significant, margin unresolved|different within margin|" + re.escape(LEG_NEW) + "|" +  # noqa: E731
                                 re.escape(LEG_OLD), "", x)
        assert strip(s) == strip(t), f.name
        lines = t.splitlines()
        lines.insert(0, MARK)
        f.write_text("\n".join(lines) + "\n")
        done.append(f.name)
print("relabelled:", done or "none")
