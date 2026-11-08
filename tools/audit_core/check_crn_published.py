#!/usr/bin/env python3
"""Check common-random-number pairing in the published V4 raw rows: within (campaign, point, seed), every PBTI-wire arm
must see the same production (n_produced, n_reachable) and the same number of receipts per attack/legit label."""
import json, sys, collections
from pathlib import Path
RAW = Path(sys.argv[1])
FAM = {"PBTI", "PBTI-R", "PBTI-SH", "B5", "B5S", "B4"}
out = {}
for fn in sorted(RAW.glob("*.jsonl")):
    rows = [json.loads(l) for l in open(fn)]
    groups = collections.defaultdict(list)
    for r in rows:
        if "error" in r:
            continue
        key = (r.get("scenario"), r.get("point"), r.get("seed"))
        lab = collections.Counter()
        for k, v in r.items():
            if k.startswith("rx["):
                lab[k[3:k.index("]")]] += v
        groups[key].append((r["arm"], r["system"], r["n_produced"], r["n_reachable"], r["n_receipts"], dict(lab)))
    bad = []
    for key, g in groups.items():
        ref = None
        for arm, sysname, npd, nr, nrc, lab in g:
            sig = (npd, nr, nrc, tuple(sorted(lab.items())))
            if ref is None:
                ref = (arm, sig)
            elif sig != ref[1]:
                bad.append((key, ref[0], arm, ref[1][:3], sig[:3],
                            {k: (dict(ref[1][3]).get(k), lab.get(k)) for k in set(dict(ref[1][3])) | set(lab)
                             if dict(ref[1][3]).get(k) != lab.get(k)}))
    out[fn.name] = {"groups": len(groups), "mismatching_groups": len(bad), "examples": bad[:5]}
    print(fn.name, "groups", len(groups), "mismatches", len(bad))
    for b in bad[:5]:
        print("   ", b)
json.dump(out, open(sys.argv[2], "w"), indent=1, default=str)
