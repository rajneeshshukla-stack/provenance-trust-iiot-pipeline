#!/usr/bin/env python3
"""Minimal reproduction: B5 re-holds observations that review already released, although the arriving receipt adds
no new fork evidence (it is the late successor of an already-contested slot, its prev naming one of the known versions).
Run from the scratch copy: python3 repro_b5_rehold.py <repo>"""
import sys
REPO = sys.argv[1]
sys.path.insert(0, REPO + "/src"); sys.path.insert(0, REPO + "/tests")
from test_v3_review_b5 import env, chain, msg, wd_of, RID
from pbti.b5 import B5FeedLevel
from pbti.review import AutoReviewer

def auth(v):
    return sorted(k[2] for k, _ in v.authoritative())

def scenario(resume_first: bool):
    v, trust, dsk, wsk, rsk, _ = env(cls=B5FeedLevel)
    c = chain(dsk, wsk, 8)
    v.ingest(c[0][0], 1_000); v.ingest(c[1][0], 2_000)
    alt, _ = msg(dsk, wsk, 1, c[0][1], 2_000, val=9.0)
    print("  alt seq1:", v.ingest(alt, 2_050).disp, "fork:", v.fork)
    # seq 2 is delayed in the network; 3, 4, 5 arrive and are held
    for i, t in ((3, 4_000), (4, 5_000), (5, 6_000)):
        print(f"  seq{i}:", v.ingest(c[i][0], t).disp)
    age = 0 if resume_first else 1_500        # with 1.5 s minimum age at t=6.1 s, seq 5 (t_q 6.0 s) stays pending
    rv = AutoReviewer(RID, "rk:auto:1", rsk, min_age_ms=age, rule="defer")
    print("  review@6.1s:", [r["outcome"] for r in rv.run(v, 6_100)], "fork:", v.fork, "authoritative:", auth(v))
    print("  late seq2 arrives @7s:", v.ingest(c[2][0], 7_000).disp, "fork:", v.fork, "fork_events:", v.fork_events)
    print("  authoritative after late seq2:", auth(v))
    print("  case states 3,4,5:", [v.qcases[wd_of(c[i][0])]["state"] for i in (3, 4, 5)])
    return auth(v)

print("A) feed resumed before the late successor arrives")
a = scenario(True)
print("B) feed still forked (one case pending) when the late successor arrives")
b = scenario(False)
ok = (3 in a and 4 in a and 5 in a) and (3 in b and 4 in b)
print("RESULT:", "no re-hold" if ok else "DEFECT REPRODUCED: released observations 3,4(,5) were withdrawn again without new fork evidence")
