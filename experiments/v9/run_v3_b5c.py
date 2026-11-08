#!/usr/bin/env python3
"""V9 rerun of the V3 campaigns (experiments/run_campaign.py) for B5 and B5S with the corrected B5
(src/pbti/b5_corrected.py), on the same specifications and seeds as the frozen rows.  The frozen runner, its
specification lists and its job function are reused unchanged; only the B5 class is replaced in this process.

usage: python3 experiments/v9/run_v3_b5c.py scenarios --systems B5 --out results/v9/raw/v3_scenarios_B5c.jsonl
       (campaigns: scenarios, ablations [mixed workload], sweep, factorial, replay [--skab-dir])
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v9_common as C  # noqa: E402

import run_campaign as rc  # noqa: E402

AUDIT_SEEDS = {"scenarios": 5, "ablations": 10 ** 9, "sweep": 10 ** 9, "factorial": 10 ** 9, "replay": 2}
KEYS = ("kind", "scenario", "system", "seed", "factor", "level", "run", "speed", "stress", "ablation")


def key_of(r):
    # a specification without "ablation" runs the full configuration and its result row records "full"; the two must
    # give the same key, or a resumed campaign would rerun specifications that are already present
    return tuple(json.dumps(r.get(k) if not (k == "ablation" and r.get(k) is None) else "full", sort_keys=True)
                 for k in KEYS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("campaign", choices=sorted(AUDIT_SEEDS))
    ap.add_argument("--systems", nargs="+", default=["B5"], choices=["B5", "B5S"])
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--seed-start", type=int, default=1)
    ap.add_argument("--skab-dir", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=2)
    a = ap.parse_args()
    C.install_corrected_b5()
    rec = C.impl_record()
    orig_eval = rc.evaluate

    def evaluate_v9(w):
        r = orig_eval(w)
        if hasattr(w.sys, "v9_counters"):
            c = w.sys.v9_counters()
            r.update(c)
            r["held_distinct_ever_v9"] = c["held_distinct_ever"]
        r.update(rec)
        r.update(C.w_split(w))
        return r
    rc.evaluate = evaluate_v9
    todo = rc.specs(a.campaign, a.seeds, a.seed_start, a.systems, AUDIT_SEEDS[a.campaign])
    if a.campaign == "replay":
        if not a.skab_dir:
            ap.error("--skab-dir is required for the replay campaign")
        for t in todo:
            t["skab_dir"] = a.skab_dir
    for t in todo:
        if a.campaign == "ablations":
            t.setdefault("ablation", "baseline")
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    man = C.manifest("v9_" + a.campaign, vars(a), {"frozen_runner": "experiments/run_campaign.py",
                                                    "n_specs": len(todo),
                                                    "audit_seeds": AUDIT_SEEDS[a.campaign]})
    mpath = out.with_suffix(".manifest.json")
    if mpath.exists():                         # resumed: keep the first manifest, add this start
        old = json.loads(mpath.read_text())
        old.setdefault("resumed", []).append(man["started"])
        man = old
    mpath.write_text(json.dumps(man, indent=1, default=str))
    errors = C.run_pool(todo, rc.job, out, key_of, a.workers, "v3-" + a.campaign + "-" + "+".join(a.systems))
    print("written", out, "errors", errors)


if __name__ == "__main__":
    main()
