#!/usr/bin/env python3
"""Mid-run consistency of the temporal tracer: after every k-th receipt and after every periodic review tick, the
tracer's authoritative pairs must equal the pipeline's authoritative set at that instant."""
import json, sys
REPO = sys.argv[1]
sys.path.insert(0, REPO + "/src")
from pbti.scenarios import build
from pbti.sweep import build_sweep, factorial_runs
where, system, seed = sys.argv[2], sys.argv[3], int(sys.argv[4])
cfg = json.loads(sys.argv[5]) if len(sys.argv) > 5 else {}
K = 25
if where.startswith("run"):
    lv = [fr for fr in factorial_runs(0.10) if fr["run"] == int(where[3:])][0]["levels"]
    w = build_sweep(lv, system, seed, temporal=True, **cfg)
else:
    w = build(where, system, seed, temporal=True, **cfg)
stats = {"checks": 0, "mismatch_checks": 0, "max_diff": 0}
def check():
    stats["checks"] += 1
    a = set(w.sys.authoritative()); b = w.tracer.end_state()
    if a != b:
        stats["mismatch_checks"] += 1; stats["max_diff"] = max(stats["max_diff"], len(a ^ b))
n = [0]
orig_rx = w.receive
def rx(wire, meta, label):
    orig_rx(wire, meta, label); n[0] += 1
    if n[0] % K == 0: check()
w.receive = rx
if hasattr(w, "_review_tick") and w.reviewer is not None and w.cfg.review_mode == "periodic":
    orig_rt = w._review_tick
    def rt():
        orig_rt(); check()
    w._review_tick = rt
    # the first tick was scheduled with the bound method before patching: re-route queued entries
    w.q = [(t, qn, (rt if getattr(fn, "__name__", "") == "_review_tick" else fn), args) for (t, qn, fn, args) in w.q]
w.run(); check()
print(json.dumps({"where": where, "system": system, "seed": seed, "cfg": cfg, **stats}))
