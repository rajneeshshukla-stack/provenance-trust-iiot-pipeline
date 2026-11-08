#!/usr/bin/env python3
"""Count B5 'stuck re-ingest' events (released non-fork case turned into a feed hold without a pending case) and
no-evidence re-holds of released observations, over seeds, for one scenario and review configuration."""
import json, sys
REPO = sys.argv[1]
sys.path.insert(0, REPO + "/src"); sys.path.insert(0, "/home/claude/PBTI_v7/tools/audit_core")
import pbti.sim as sim
import b5_variants as bv
sim.B5FeedLevel = bv.B5Instr
from pbti.scenarios import build
sc = sys.argv[2]; cfg = json.loads(sys.argv[3]); seeds = [int(x) for x in sys.argv[4:]]
for s in seeds:
    w = build(sc, "B5", s, temporal=False, **cfg)
    w.run()
    print(json.dumps({"scenario": sc, "seed": s, "cfg": cfg, **w.sys.c}), flush=True)
