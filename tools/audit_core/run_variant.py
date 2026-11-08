#!/usr/bin/env python3
"""Run one specification like experiments/run_v4.py job(), with the B5 class replaced by an audit variant.
usage: run_variant.py REPO VARIANT(orig|instr|norehold|nostuck) SYSTEM SCENARIO|JSON-levels SEED [cfg-json]"""
import json, sys, time
REPO = sys.argv[1]
sys.path.insert(0, REPO + "/src"); sys.path.insert(0, "/home/claude/PBTI_v7/tools/audit_core")
import pbti.sim as sim
import b5_variants as bv
variant, system, where, seed = sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5])
cfg = json.loads(sys.argv[6]) if len(sys.argv) > 6 else {}
cls = {"orig": None, "instr": bv.B5Instr, "norehold": bv.B5NoReHold,
       "nostuck": bv.B5NoStuck}[variant]
if cls is not None:
    sim.B5FeedLevel = cls
from pbti.oracle import evaluate
from pbti.scenarios import build
from pbti.sweep import build_sweep, factorial_runs
from pbti.temporal import temporal_metrics
cfg.setdefault("temporal", True)
t0 = time.perf_counter()
if where.startswith("{"):
    w = build_sweep(json.loads(where), system, seed, **cfg)
elif where.startswith("run"):
    lv = [fr for fr in factorial_runs(0.10) if fr["run"] == int(where[3:])][0]["levels"]
    w = build_sweep(lv, system, seed, **cfg)
else:
    w = build(where, system, seed, **cfg)
w.run()
r = evaluate(w); r.update(temporal_metrics(w))
keep = ("nonlegit_auth", "legit_missing", "tm_nl_rec_s", "tm_wh_rec_s", "tm_reach", "tm_avail_5s", "holds",
        "fork_events", "review[RELEASED_HOLD]", "review[REJECTED]", "review[RELEASE_FAILED]", "review[RELEASED]",
        "tm_end_state_matches_authoritative", "tm_zero_flips")
out = {k: r.get(k) for k in keep}
out["W"] = r["tm_wh_rec_s"] / max(1, r["tm_reach"])
out.update(variant=variant, system=system, where=where, seed=seed, cfg=cfg, wall_s=round(time.perf_counter() - t0, 1))
if hasattr(w.sys, "c"):
    out["counters"] = w.sys.c
print(json.dumps(out))
