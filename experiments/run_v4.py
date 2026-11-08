#!/usr/bin/env python3
"""V4 campaign runner (virtual-time testbed). Campaigns are defined by JSON configuration files in
experiments/v4_configs/ (design points x arms x seeds); each run writes one JSON line with the oracle's end-of-run
outcomes (O1 = nonlegit_auth, O2 = legit_missing, ...), the V4 temporal metrics (tm_*, src/pbti/temporal.py), the
arm configuration and, for audited seeds, the independent audit. A manifest with the configuration, its SHA-256, the
source-tree digest, hardware and software versions is written next to the output.

Usage:
  python3 experiments/run_v4.py experiments/v4_configs/A1_review.json --out results/v4/raw/A1_review.jsonl
  python3 experiments/run_v4.py CONFIG --seeds 101 102 --dry-run        # list the specifications only
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import multiprocessing as mp
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

import run_campaign as rc  # noqa: E402  (manifest helpers, source digest)
from pbti.audit import audit_pbti  # noqa: E402
from pbti.oracle import evaluate  # noqa: E402
from pbti.scenarios import build  # noqa: E402
from pbti.sweep import build_sweep, factorial_runs  # noqa: E402
from pbti.temporal import temporal_metrics  # noqa: E402

PBTI_FAMILY = ("PBTI", "PBTI-R", "PBTI-SH", "B5", "B5S")
CFG_KEYS = ("review_delay_ms", "review_every_ms", "review_mode", "review_rule", "temporal", "sh_timeout_ms",
            "release_evidence", "drain_ms", "duration_ms")


def expand(conf: dict, seeds=None) -> list[dict]:
    seeds = seeds or list(range(conf["seeds"]["start"], conf["seeds"]["start"] + conf["seeds"]["n"]))
    points = []
    for d in conf["design"]:
        if d["kind"] == "scenario":
            for sc in d["scenarios"]:
                points.append({"kind": "scenario", "scenario": sc})
        elif d["kind"] == "joint":            # full grid over the listed sweep factors
            names = sorted(d["factors"])
            for combo in itertools.product(*[d["factors"][n] for n in names]):
                lv = {n: float(v) for n, v in zip(names, combo) if float(v) > 0}
                points.append({"kind": "sweep", "scenario": "JOINT", "levels": lv,
                               "point": "+".join(f"{n}={v:g}" for n, v in zip(names, combo))})
        elif d["kind"] == "factorial":
            for fr in factorial_runs(d.get("high", 0.10)):
                if d.get("runs") and fr["run"] not in d["runs"]:
                    continue
                points.append({"kind": "sweep", "scenario": "FACTORIAL", "levels": fr["levels"], "run": fr["run"],
                               "signs": fr["signs"], "point": f"run{fr['run']}"})
        else:
            raise ValueError(d["kind"])
    out = []
    audit_n = conf.get("audit_seeds", 0)
    for p in points:
        for arm in conf["arms"]:
            if p["kind"] == "scenario" and arm.get("scenarios") and p["scenario"] not in arm["scenarios"]:
                continue
            for i, seed in enumerate(seeds):
                spec = dict(p, arm=arm["arm"], system=arm["system"], seed=seed, cfg=dict(arm.get("cfg", {})),
                            campaign=conf["campaign"], audit=(i < audit_n and arm["system"] in PBTI_FAMILY))
                spec["cfg"].setdefault("temporal", True)
                out.append(spec)
    return out


def job(spec: dict) -> dict:
    t0 = time.perf_counter()
    try:
        kw = {k: v for k, v in spec["cfg"].items() if k in CFG_KEYS}
        if spec["kind"] == "scenario":
            w = build(spec["scenario"], spec["system"], spec["seed"], **kw)
        else:
            w = build_sweep(spec["levels"], spec["system"], spec["seed"], **kw)
        w.run()
        r = evaluate(w)
        r.update(temporal_metrics(w))
        r.update({k: spec[k] for k in ("campaign", "arm", "kind", "scenario", "seed", "point", "run", "levels")
                  if k in spec})
        r["cfg"] = spec["cfg"]
        rv = w.reviewer
        if rv is not None:
            r["review_decisions"] = rv.decisions
            r["review_deferrals"] = getattr(rv, "deferrals", 0)
            r["review_mode"] = w.cfg.review_mode
            r["review_rule"] = rv.rule
            r["review_delay_ms"] = w.cfg.review_delay_ms
            r["review_every_ms"] = w.cfg.review_every_ms
            r["event_review_rounds"] = w.event_review_rounds
        for k in ("sh_holds", "sh_released", "sh_timeouts", "resumed_feeds"):
            if hasattr(w.sys, k):
                r[k] = getattr(w.sys, k)
        if hasattr(w.sys, "prov"):
            r["sh_provisional_end"] = len(w.sys.prov)
            r["sh_suspect_feeds"] = len(w.sys.suspect)
        if hasattr(w.sys, "held"):
            r["held_end"] = len(w.sys.held)
            r["held_distinct_ever"] = len({e[1] for e in w.sys.reg.state_events if e[3] == "HELD"})
        if spec.get("audit"):
            a = audit_pbti(w.sys, replay=True)
            r.update({"audit_pass": a["pass"], "audit_findings": a["findings"],
                      "audit_static_s": a["static_s"], "audit_replay_s": a.get("replay_s")})
        r["wall_s"] = time.perf_counter() - t0
        return r
    except Exception as e:  # noqa: BLE001  (an error row is recorded and reported; it is not a result)
        return {"error": repr(e), "trace": traceback.format_exc(), **{k: v for k, v in spec.items() if k != "cfg"},
                "cfg": spec.get("cfg")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config")
    ap.add_argument("--out", required=False)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--seeds", type=int, nargs="+", default=None, help="override the configured seed list (pilots)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    cpath = Path(a.config)
    conf = json.loads(cpath.read_text())
    todo = expand(conf, a.seeds)
    if a.dry_run:
        print(len(todo), "specifications")
        for t in todo[:5]:
            print(t)
        return
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    man = rc.manifest(conf["campaign"], a)
    man.update({"config_file": str(cpath), "config_sha256": hashlib.sha256(cpath.read_bytes()).hexdigest(),
                "config": conf, "n_specs": len(todo), "seeds": a.seeds or conf["seeds"]})
    out.with_suffix(".manifest.json").write_text(json.dumps(man, indent=1, default=str))
    t0 = time.time()
    done = errors = 0
    with open(out, "w") as fh, mp.get_context("fork").Pool(a.workers, maxtasksperchild=8) as pool:
        for r in pool.imap_unordered(job, todo):
            fh.write(json.dumps(r, default=str) + "\n")
            fh.flush()
            done += 1
            errors += "error" in r
            if done % 25 == 0 or done == len(todo):
                print(f"[{conf['campaign']}] {done}/{len(todo)} runs, {errors} errors, {time.time() - t0:.0f}s", flush=True)
    print("written", out, "errors", errors)


if __name__ == "__main__":
    main()
