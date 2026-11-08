#!/usr/bin/env python3
"""Exploratory split of the registered withheld-time outcome W into a delay part and a permanent-loss part.

W (registered; temporal.py) = (1/|L|) * sum over gateway-accepted legitimate observations of the time from gateway
acceptance to the end of the run during which the observation was not authoritative. Here, as in the oracle audit's
sensitivity analysis (tools/oracle_audit/sensitivity.py:metrics_at), the sum is split by the state at the end of the run:
  W_loss  = contribution of observations that are NOT authoritative at T_end (lost: never released, contested,
            tainted, or withdrawn and not restored), counted from acceptance to T_end;
  W_delay = contribution of observations that are authoritative at T_end (time withheld before or between
            availability intervals).
W = W_delay + W_loss exactly. Each run is re-executed with the oracle audit's capture (tools/oracle_audit/capture.py),
which re-runs the stored specification unchanged and records the authoritative-state history with an independent
poller; the recomputed W is checked against the stored row (it must be identical).

Usage: python3 -B w_decomposition.py PART NPARTS OUT_JSONL      (runs every NPARTS-th job starting at PART)
       python3 -B w_decomposition.py --aggregate OUT_JSONL SUMMARY_JSON
This is an exploratory analysis (evidence level B); the registered W and its comparisons are unchanged.
"""
import json
import sys
import time
import zlib
from pathlib import Path

import numpy as np

# the oracle audit tools sit next to this directory (tools/oracle_audit); their capture module points to a copy of
# the assembled repository through its REPO constant (see reports/08_REPRODUCIBILITY_INSTRUCTIONS.md, Section 8)
AUDIT = str(Path(__file__).resolve().parents[1] / "oracle_audit")
SEEDS = list(range(21, 41))
JOBS = ([("A1_review", arm, cell) for cell in ("S05_stolen_key", "S99_mixed")
         for arm in ("PBTI", "B5-hist", "B5-event", "PBTI-R-event")] +
        [("A3_factorial", arm, cell) for cell in ("run3", "run4", "run8", "run15")
         for arm in ("PBTI", "PBTI-SH", "B5-hist")])
PAIRS = [("A1_review", "S05_stolen_key", "B5-hist", "PBTI"), ("A1_review", "S05_stolen_key", "B5-event", "PBTI"),
         ("A1_review", "S99_mixed", "B5-hist", "PBTI"), ("A1_review", "S99_mixed", "B5-event", "PBTI"),
         ("A1_review", "S99_mixed", "B5-event", "PBTI-R-event")] + \
        [("A3_factorial", c, a, b) for c in ("run3", "run4", "run8", "run15")
         for a, b in (("PBTI-SH", "PBTI"), ("PBTI-SH", "B5-hist"))]


def run(part, nparts, out):
    sys.path.insert(0, AUDIT)
    import capture  # noqa: F401  (installs the process-local instrumentation of the oracle audit)
    from audit_runs import find_spec, stored_rows
    from sensitivity import metrics_at
    stored = stored_rows()
    done = set()
    if Path(out).exists():
        done = {(json.loads(l)["campaign"], json.loads(l)["arm"], json.loads(l)["cell"], json.loads(l)["seed"])
                for l in open(out)}
    jobs = [(c, a, cell, s) for (c, a, cell) in JOBS for s in SEEDS]
    with open(out, "a") as f:
        for i, (camp, arm, cell, seed) in enumerate(jobs):
            if i % nparts != part or (camp, arm, cell, seed) in done:
                continue
            t0 = time.time()
            cap = capture.run_spec(find_spec(camp, arm, cell, seed))
            iv, _z, _e = cap["_hist"]["poll_call"]
            m = metrics_at(cap["_legit"], iv, cap["t_end"])
            st = stored[(camp, arm, cell, seed)]
            w_st = st["tm_wh_rec_s"] / max(1, st["tm_reach"])
            rec = {"campaign": camp, "arm": arm, "cell": cell, "seed": seed, "W": m["W"], "W_delay": m["W_delay"],
                   "W_loss": m["W_loss"], "lost_at_end": m["lost"], "n": m["n"], "W_stored": w_st,
                   "W_matches_stored": abs(m["W"] - w_st) <= 1e-9 * max(1.0, abs(w_st)),
                   "O2_stored": st["legit_missing"], "run_s": round(time.time() - t0, 1)}
            f.write(json.dumps(rec) + "\n")
            f.flush()
            print(camp, arm, cell, seed, round(m["W"], 3), round(m["W_delay"], 3), round(m["W_loss"], 3),
                  rec["W_matches_stored"], flush=True)


def boot(d, key):
    d = np.asarray(d, float)
    if np.all(d == d[0]):
        return float(d[0]), float(d[0])
    rng = np.random.default_rng([20261104, zlib.crc32(key.encode())])
    b = d[rng.integers(0, len(d), (10_000, len(d)))].mean(axis=1)
    return float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))


def aggregate(out, summary):
    rows = [json.loads(l) for l in open(out)]
    by = {(r["campaign"], r["cell"], r["arm"], r["seed"]): r for r in rows}
    res = {"all_W_match_stored": all(r["W_matches_stored"] for r in rows), "runs": len(rows), "cells": {}, "pairs": []}
    for (camp, arm, cell) in JOBS:
        xs = [by[(camp, cell, arm, s)] for s in SEEDS if (camp, cell, arm, s) in by]
        if xs:
            res["cells"][f"{camp}|{cell}|{arm}"] = {k: float(np.mean([x[k] for x in xs]))
                                                    for k in ("W", "W_delay", "W_loss", "lost_at_end")} | {"n": len(xs)}
    for camp, cell, a, b in PAIRS:
        ss = [s for s in SEEDS if (camp, cell, a, s) in by and (camp, cell, b, s) in by]
        if not ss:
            continue
        rec = {"campaign": camp, "cell": cell, "arm": a, "ref": b, "n": len(ss)}
        for k in ("W", "W_delay", "W_loss"):
            d = [by[(camp, cell, a, s)][k] - by[(camp, cell, b, s)][k] for s in ss]
            lo, hi = boot(d, f"wdecomp|{k}|{camp}|{cell}|{a}|{b}")
            rec[k] = {"mean_d": float(np.mean(d)), "ci95": [lo, hi]}
        res["pairs"].append(rec)
    Path(summary).write_text(json.dumps(res, indent=1))
    print(json.dumps({"runs": res["runs"], "all_W_match_stored": res["all_W_match_stored"]}))


if __name__ == "__main__":
    if sys.argv[1] == "--aggregate":
        aggregate(sys.argv[2], sys.argv[3])
    else:
        run(int(sys.argv[1]), int(sys.argv[2]), sys.argv[3])
