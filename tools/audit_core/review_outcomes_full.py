#!/usr/bin/env python3
"""Full (untruncated) review outcomes per case reason for one run."""
import json, sys, collections
REPO = sys.argv[1]
sys.path.insert(0, REPO + "/src")
from pbti.scenarios import build
system, sc, seed = sys.argv[2], sys.argv[3], int(sys.argv[4])
cfg = json.loads(sys.argv[5]) if len(sys.argv) > 5 else {}
w = build(sc, system, seed, temporal=False, **cfg)
w.run()
v = w.sys
by = collections.Counter()
for rec in v.evidence.records:
    d = json.loads(rec)
    if d.get("type") == "REVIEW":
        by[(d.get("orig_reason"), d.get("outcome"))] += 1
print(json.dumps({"system": system, "scenario": sc, "seed": seed, "cfg": cfg,
                  "outcomes": {f"{a}|{b}": n for (a, b), n in sorted(by.items())},
                  "held_end": len(getattr(v, "held", ())),
                  "pending_cases": sum(1 for c in v.qcases.values() if c["state"] == "QUARANTINED")}))
