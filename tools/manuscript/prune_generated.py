#!/usr/bin/env python3
"""Remove from PAPER_DIR/generated every file that neither the article parts nor Document S1 input.

The analysis scripts write more tables than the manuscript uses (earlier layouts); the unused ones stay in the
analysis output directories of the repository and are only left out of the manuscript sources.
Usage: python3 -I prune_generated.py PAPER_DIR
"""
import re
import sys
from pathlib import Path

P = Path(sys.argv[1]).resolve()
used = {"main_xref.tex", "supp_xref.tex"}          # written by xref_maps.py during the build
for f in sorted((P / "parts").glob("*.tex")) + [P / "supplementary.tex"]:
    for m in re.finditer(r"\\input\{generated/([^}]+)\}", f.read_text()):
        n = m.group(1)
        used.add(n if n.endswith(".tex") else n + ".tex")
removed = []
for p in sorted((P / "generated").iterdir()):
    if p.is_file() and p.name not in used:
        p.unlink()
        removed.append(p.name)
missing = sorted(n for n in used if not (P / "generated" / n).exists() and n not in ("main_xref.tex", "supp_xref.tex"))
print(f"generated/: {len(used)} used, removed {removed}" + (f", MISSING {missing}" if missing else ""))
if missing:
    raise SystemExit(1)
