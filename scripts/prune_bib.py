#!/usr/bin/env python3
"""Keep in paper/references.bib only the entries cited in paper/main.tex; move the others (verified entries that the
V3 text no longer cites) to paper/references_uncited_v3.bib, so nothing is lost. Idempotent."""
import re
from pathlib import Path

P = Path(__file__).resolve().parents[1] / "paper"


def entries(text):
    out, i = {}, 0
    pat = re.compile(r"@(\w+)\{([^,\s]+),")
    while True:
        m = pat.search(text, i)
        if not m:
            return out
        depth = 0
        for j in range(text.index("{", m.start()), len(text)):
            depth += {"{": 1, "}": -1}.get(text[j], 0)
            if depth == 0:
                break
        out[m.group(2)] = text[m.start():j + 1]
        i = j + 1


bib, unc_p = P / "references.bib", P / "references_uncited_v3.bib"
E = entries(bib.read_text())
U = entries(unc_p.read_text()) if unc_p.exists() else {}
E.update({k: v for k, v in U.items() if k not in E})
cited = {k.strip() for c in re.findall(r"\\cite\{([^}]+)\}", (P / "main.tex").read_text()) for k in c.split(",")}
keep = [k for k in E if k in cited]
drop = [k for k in E if k not in cited]
bib.write_text("% References cited in main.tex (V3). Entries no longer cited are kept in references_uncited_v3.bib.\n\n"
               + "\n\n".join(E[k] for k in keep) + "\n")
unc_p.write_text("% Verified entries not cited by the V3 manuscript (kept for provenance; not used by the build).\n\n"
                 + "\n\n".join(E[k] for k in drop) + "\n")
print(f"cited and kept: {len(keep)}; moved to {unc_p.name}: {len(drop)}; missing from bib: {sorted(cited - set(E))}")
