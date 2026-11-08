#!/usr/bin/env python3
"""Minimal reproduction: in B5, a corroborated STALE_TS case whose identity lies in a held feed is released by the
reviewer, the re-run admission turns it into a feed hold (QUARANTINE/FEED_FORK_HOLD) but no FEED_FORK_HOLD case can be
opened (the wire digest already has the STALE_TS case), and _release closes that case REJECTED. The observation stays
in B5.held with no pending case for good, while PBTI-R releases the same observation. The re-run also calls _fork for
the contested predecessor and re-holds an already released successor."""
import sys
REPO = sys.argv[1]
sys.path.insert(0, REPO + "/src"); sys.path.insert(0, REPO + "/tests")
from test_v3_review_b5 import env, chain, msg, wd_of, RID
from pbti.b5 import B5FeedLevel
from pbti.verifier import PBTIVerifier
from pbti.review import AutoReviewer

def run(cls):
    v, trust, dsk, wsk, rsk, _ = env({"h_max_ms": 5_000}, cls=cls)
    c = chain(dsk, wsk, 6)
    v.ingest(c[0][0], 1_000); v.ingest(c[1][0], 2_000)
    alt, _ = msg(dsk, wsk, 1, c[0][1], 2_000, val=9.0)
    v.ingest(alt, 2_050)                                    # fork / contest at seq 1
    r2 = v.ingest(c[2][0], 9_000)                           # seq 2 (ts 2 s) arrives at 9 s: STALE_TS (h_max 5 s)
    w3, cd3 = msg(dsk, wsk, 3, c[2][1], 8_900)              # seq 3 fresh, its prev names seq 2's digest
    w4, cd4 = msg(dsk, wsk, 4, cd3, 9_000)
    r3 = v.ingest(w3, 9_100)
    r4 = v.ingest(w4, 9_200)
    rv = AutoReviewer(RID, "rk:auto:1", rsk, min_age_ms=0, rule="defer")
    out = [(r["outcome"]) for r in rv.run(v, 9_300)]
    out2 = [(r["outcome"]) for r in rv.run(v, 20_000)]
    a = sorted(k[2] for k, _ in v.authoritative())
    held = sorted(k[2] for k in getattr(v, "held", ()))
    pending = [c_["eid"][2] for c_ in v.qcases.values() if c_["state"] == "QUARANTINED"]
    print(f"{cls.__name__:14s} seq2:{r2.disp}/{r2.why} seq3:{r3.disp} seq4:{r4.disp} review1:{out} review2:{out2}")
    print(f"{'':14s} authoritative seqs={a} held={held} pending cases (seq)={pending} case(seq2)={v.qcases[wd_of(c[2][0])]['state']}")
    return a

a_r = run(PBTIVerifier)
a_b = run(B5FeedLevel)
print("RESULT:", "DEFECT REPRODUCED: seq 2 recovered by PBTI-R but stuck in B5 (held, no pending case)" if 2 in a_r and 2 not in a_b else "not reproduced")
