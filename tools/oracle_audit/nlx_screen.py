#!/usr/bin/env python3
"""Same screening as drain_screen.py for NLX (margin 60 record-s): a non-legitimate pair still authoritative at T_end
accrues exposure until T_end, so x seconds less drain lower NLX by x * tm_nl_auth_end (exact when every
non-legitimate episode that ends before T_end also ends before the shortened end). Gate-relevant comparisons:
PBTI-SH vs PBTI (H3a; G3 on the grid, G3F on the four factorial cells with equivocation and suppressed runs high)."""
import json
from collections import defaultdict
import numpy as np
from drain_screen import load, cls as _cls
import drain_screen
drain_screen.M = 60.0
out = []
for camp in ("A3_selective", "A3_factorial"):
    by = load(camp)
    for i, p in enumerate(sorted(by)):
        a, b = by[p].get("PBTI-SH", {}), by[p].get("PBTI", {})
        seeds = sorted(set(a) & set(b))
        d = np.array([a[s]["tm_nl_rec_s"] - b[s]["tm_nl_rec_s"] for s in seeds])
        k = np.array([a[s]["tm_nl_auth_end"] - b[s]["tm_nl_auth_end"] for s in seeds], dtype=float)
        o1p = np.mean([b[s]["nonlegit_auth"] for s in seeds])
        r = {"campaign": camp, "cell": p, "pbti_O1_mean": float(o1p), "dNLX_full": float(d.mean()),
             "dNLX_drain120": float((d - 60 * k).mean()), "dNLX_drain60": float((d - 120 * k).mean()),
             "class_full": _cls(d, 1000 + i), "class_drain120": _cls(d - 60 * k, 1000 + i),
             "class_drain60": _cls(d - 120 * k, 1000 + i)}
        out.append(r)
json.dump(out, open("/home/claude/PBTI_v7/results/oracle_audit/nlx_screen.json", "w"), indent=1)
for r in out:
    if r["pbti_O1_mean"] > 0 or r["campaign"] == "A3_factorial":
        ch = "  <-- class changes" if len({r["class_full"], r["class_drain120"], r["class_drain60"]}) > 1 else ""
        print(f'{r["campaign"]:12s} {r["cell"][:38]:38s} PBTI O1 {r["pbti_O1_mean"]:5.2f}  dNLX full {r["dNLX_full"]:+8.1f} {r["class_full"]:10s} '
              f'120s {r["dNLX_drain120"]:+8.1f} {r["class_drain120"]:10s} 60s {r["dNLX_drain60"]:+8.1f} {r["class_drain60"]}{ch}')
