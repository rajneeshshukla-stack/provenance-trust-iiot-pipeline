#!/usr/bin/env python3
"""V9 rerun of the V4 campaigns (experiments/run_v4.py) for the B5 and B5S arms with the corrected B5
(src/pbti/b5_corrected.py), on the frozen configuration files, design points and seeds.  The frozen runner's
expand() and job() are reused unchanged; only the B5 class is replaced in this process.

usage: python3 experiments/v9/run_v4_b5c.py experiments/v4_configs/A1_review.json --out results/v9/raw/A1_review_B5c.jsonl
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v9_common as C  # noqa: E402

import run_v4  # noqa: E402

KEYS = ("campaign", "arm", "kind", "scenario", "seed", "point", "run")


def key_of(r):
    return tuple(json.dumps(r.get(k), sort_keys=True) for k in KEYS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config")
    ap.add_argument("--systems", nargs="+", default=["B5", "B5S"], choices=["B5", "B5S"])
    ap.add_argument("--arms", nargs="+", default=None, help="restrict to these arms")
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=2)
    a = ap.parse_args()
    C.install_corrected_b5()
    rec = C.impl_record()
    orig_eval = run_v4.evaluate

    def evaluate_v9(w):
        r = orig_eval(w)
        if hasattr(w.sys, "v9_counters"):
            c = w.sys.v9_counters()
            r.update(c)
            r["held_distinct_ever_v9"] = c["held_distinct_ever"]
        r.update(rec)
        r.update(C.w_split(w))
        return r
    run_v4.evaluate = evaluate_v9
    cpath = Path(a.config)
    conf = json.loads(cpath.read_text())
    todo = [s for s in run_v4.expand(conf) if s["system"] in a.systems and (not a.arms or s["arm"] in a.arms)]
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    man = C.manifest("v9_" + conf["campaign"], vars(a),
                     {"frozen_runner": "experiments/run_v4.py", "config_file": str(cpath),
                      "config_sha256": hashlib.sha256(cpath.read_bytes()).hexdigest(), "n_specs": len(todo),
                      "arms": sorted({s["arm"] for s in todo})})
    mpath = out.with_suffix(".manifest.json")
    if mpath.exists():
        old = json.loads(mpath.read_text())
        old.setdefault("resumed", []).append(man["started"])
        man = old
    mpath.write_text(json.dumps(man, indent=1, default=str))
    errors = C.run_pool(todo, run_v4.job, out, key_of, a.workers, conf["campaign"] + "-B5c")
    print("written", out, "errors", errors)


if __name__ == "__main__":
    main()
