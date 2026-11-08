#!/usr/bin/env python3
"""Security/correctness campaign (virtual-time testbed).

Usage:
  python experiments/run_campaign.py scenarios  --seeds 10 --workers 2
  python experiments/run_campaign.py revocation --seeds 10 --workers 2
  python experiments/run_campaign.py ablations  --seeds 10 --workers 2
  python experiments/run_campaign.py audit      --seeds 5  --workers 2
Each run appends one JSON line to results/raw/<campaign>.jsonl; a manifest with hardware,
software versions, the source-tree digest and all parameters is written alongside.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing as mp
import os
import platform
import random
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pbti.audit import TAMPER_CLASSES, audit_b3, audit_pbti, tamper_b3, tamper_pbti  # noqa: E402
from pbti.oracle import evaluate  # noqa: E402
from pbti.scenarios import SCENARIOS, build  # noqa: E402
from pbti.sweep import FACTORS, LEVELS, build_sweep, factorial_runs  # noqa: E402
from pbti.verifier import Ablation  # noqa: E402

SYSTEMS = ["B1", "B2", "B3", "PBTI"]
ABLATIONS = ["full", "no_relay_sig", "static_policy", "no_obs_sig", "no_prev_link", "edge_event_id",
             "no_conflict", "no_staleness", "arrival_order", "no_commitment", "no_quarantine",
             "no_revocation", "volatile_buffer"]


def source_digest() -> str:
    h = hashlib.sha256()
    for p in sorted((ROOT / "src").rglob("*.py")):
        h.update(p.relative_to(ROOT).as_posix().encode())
        h.update(p.read_bytes())
    return h.hexdigest()


def manifest(campaign: str, args) -> dict:
    import cryptography, numpy, scipy, pandas
    try:
        cpu = [l for l in open("/proc/cpuinfo") if l.startswith("model name")][0].split(":")[1].strip()
    except Exception:  # noqa: BLE001
        cpu = platform.processor()
    import psutil
    return {"campaign": campaign, "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "args": vars(args),
            "source_sha256": source_digest(), "python": sys.version, "platform": platform.platform(),
            "cpu": cpu, "logical_cpus": os.cpu_count(), "ram_gb": round(psutil.virtual_memory().total / 2 ** 30, 2),
            "versions": {"cryptography": cryptography.__version__, "numpy": numpy.__version__,
                         "scipy": scipy.__version__, "pandas": pandas.__version__}}


_SKAB_CACHE: dict = {}


def _skab(path: str) -> dict:
    if path not in _SKAB_CACHE:
        from pbti.dataset import load_skab
        _SKAB_CACHE[path] = load_skab(path)
    return _SKAB_CACHE[path]


def job(spec: dict) -> dict:
    t0 = time.perf_counter()
    try:
        kind = spec["kind"]
        ab = None
        if spec["system"] == "PBTI" and spec.get("ablation") not in (None, "full", "baseline"):
            ab = Ablation(**{spec["ablation"]: True})
        kw = {}
        if "refresh_ms" in spec:
            kw["refresh_ms"] = spec["refresh_ms"]
        if kind in ("sweep", "factorial"):   # V3
            w = build_sweep(spec["levels"], spec["system"], spec["seed"])
        elif kind == "replay":               # V3 SKAB dataset replay (src/pbti/dataset.py)
            from pbti.dataset import build_replay
            w = build_replay(_skab(spec["skab_dir"]), spec["system"], spec["seed"], spec["speed"], spec["stress"])
        else:
            w = build(spec["scenario"], spec["system"], spec["seed"], ablation=ab, **kw)
        w.run()
        r = evaluate(w)
        r.update({"scenario": spec["scenario"], "kind": kind, "ablation_name": spec.get("ablation", "full")})
        for k in ("factor", "level", "levels", "run", "signs", "speed", "stress"):
            if k in spec:
                r[k] = spec[k]
        if kind == "replay":
            from pbti.dataset import label_breakdown
            r.update(label_breakdown(w))
        if "refresh_ms" in spec:
            r["refresh_ms"] = spec["refresh_ms"]
        if kind == "audit":
            rng = random.Random(1000 + spec["seed"])
            cls = spec["tamper"]
            if spec["system"] == "PBTI":
                n = tamper_pbti(w.sys, cls, spec["k"], rng)
                a = audit_pbti(w.sys, replay=True)
            else:
                n = tamper_b3(w.sys, cls, spec["k"], rng)
                a = audit_b3(w.sys)
            r.update({"tamper": cls, "tampered": n, "audit_pass": a["pass"], "audit_findings": a["findings"],
                      "audit_static_s": a.get("static_s"), "audit_replay_s": a.get("replay_s")})
        elif spec["system"] in ("PBTI", "PBTI-R", "B5", "B5S") and spec.get("audit", True) and spec.get("ablation", "full") in ("full", "baseline"):
            a = audit_pbti(w.sys, replay=True)
            r.update({"audit_pass": a["pass"], "audit_findings": a["findings"],
                      "audit_static_s": a["static_s"], "audit_replay_s": a.get("replay_s")})
        r["wall_s"] = time.perf_counter() - t0
        return r
    except Exception as e:  # noqa: BLE001
        return {"error": repr(e), "trace": traceback.format_exc(), **spec}


def specs(campaign: str, seeds: int, seed_start: int = 1, systems=None, audit_seeds: int = 10 ** 9) -> list[dict]:
    """systems=None: the original matrix (B1-B3 and PBTI). systems=[...]: only those pipelines
    (used for the strongest-combination baseline B4 added in revision 2)."""
    out = []
    sel = list(systems) if systems else SYSTEMS
    if campaign == "scenarios":
        for sc in SCENARIOS:
            if sc == "S99_mixed":
                continue
            for s in sel:
                for seed in range(seed_start, seed_start + seeds):
                    out.append({"kind": "scenario", "scenario": sc, "system": s, "seed": seed,
                                "audit": seed < seed_start + audit_seeds})
    elif campaign == "revocation":
        for refresh in (0, 1_000, 5_000, 30_000):
            for s in SYSTEMS:
                for seed in range(seed_start, seed_start + seeds):
                    out.append({"kind": "revocation", "scenario": "S14_revocation", "system": s, "seed": seed,
                                "refresh_ms": refresh, "audit": False})
    elif campaign == "ablations":
        for seed in range(seed_start, seed_start + seeds):
            if "PBTI" in sel:
                for a in ABLATIONS:
                    out.append({"kind": "ablation", "scenario": "S99_mixed", "system": "PBTI", "seed": seed,
                                "ablation": a, "audit": False})
            for s in [x for x in sel if x != "PBTI"] if systems else ("B1", "B2", "B3"):
                out.append({"kind": "ablation", "scenario": "S99_mixed", "system": s, "seed": seed,
                            "ablation": "baseline"})
    elif campaign == "sweep":   # V3 single-factor sweep (src/pbti/sweep.py, docs/V3_SWEEP_DESIGN.md)
        sel = list(systems) if systems else ["PBTI", "B4", "B5"]
        points = [("none", 0.0)]
        for f in FACTORS:
            for r in LEVELS:
                if r == 0.0 and f not in ("revstale", "compromise"):
                    continue
                points.append((f, r))
        for f, r in points:
            for s in sel:
                for seed in range(seed_start, seed_start + seeds):
                    out.append({"kind": "sweep", "scenario": "SWEEP", "factor": f, "level": r,
                                "levels": ({} if f == "none" else {f: r}), "system": s, "seed": seed, "audit": False})
    elif campaign == "factorial":   # V3 2^(7-3) resolution-IV design at 0 / 10 %
        sel = list(systems) if systems else ["PBTI", "B4", "B5"]
        for fr in factorial_runs(0.10):
            for s in sel:
                for seed in range(seed_start, seed_start + seeds):
                    out.append({"kind": "factorial", "scenario": "FACTORIAL", "run": fr["run"], "signs": fr["signs"],
                                "levels": fr["levels"], "system": s, "seed": seed, "audit": False})
    elif campaign == "replay":      # V3 SKAB replay at 1x, 5x, 10x: stressed runs and an unstressed control
        from pbti.dataset import SPEEDS
        sel = list(systems) if systems else ["PBTI", "B4", "B5"]
        for speed in SPEEDS:
            for s in sel:
                for seed in range(seed_start, seed_start + seeds):
                    out.append({"kind": "replay", "scenario": f"SKAB_x{speed}", "system": s, "seed": seed, "speed": speed,
                                "stress": True, "audit": seed < seed_start + audit_seeds})
                for seed in range(seed_start, seed_start + 3):
                    out.append({"kind": "replay", "scenario": f"SKAB_x{speed}_clean", "system": s, "seed": seed,
                                "speed": speed, "stress": False, "audit": False})
    elif campaign == "audit":
        for seed in range(1, seeds + 1):
            for cls in TAMPER_CLASSES:
                for s in ("PBTI", "B3"):
                    out.append({"kind": "audit", "scenario": "S05_stolen_key", "system": s, "seed": seed,
                                "tamper": cls, "k": 50})
    return out


def _write_dataset_record(skab_dir: str, out: Path) -> None:
    """Provenance of the replayed dataset: source, licence, commit, access date and per-file SHA-256."""
    import subprocess
    from pbti.dataset import ROWS, SOURCE, STRESS, load_skab
    try:
        commit = subprocess.run(["git", "-C", skab_dir, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    except Exception:  # noqa: BLE001
        commit = None
    rec = dict(SOURCE, commit=commit, accessed=time.strftime("%Y-%m-%d"), rows_per_file=ROWS, stress=STRESS,
               files=load_skab(skab_dir)["meta"])
    out.with_name(out.stem + "_dataset.json").write_text(json.dumps(rec, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("campaign", choices=["scenarios", "revocation", "ablations", "audit", "sweep", "factorial", "replay"])
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--out", default=None)
    ap.add_argument("--only-errors-of", default=None, help="re-run only the specs that errored in this JSONL file")
    ap.add_argument("--systems", nargs="+", default=None, help="restrict to these pipelines (e.g. B4)")
    ap.add_argument("--seed-start", type=int, default=1, help="first seed (scenarios, revocation and ablation campaigns)")
    ap.add_argument("--audit-seeds", type=int, default=10 ** 9, help="V3: run the independent audit only for the first N seeds")
    ap.add_argument("--scenarios", nargs="+", default=None, help="V3: restrict the scenario campaign to these scenarios")
    ap.add_argument("--skab-dir", default=None, help="V3: local clone of https://github.com/waico/SKAB (replay campaign)")
    args = ap.parse_args()
    out = Path(args.out or ROOT / "results" / "raw" / f"{args.campaign}.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    if not args.only_errors_of:
        (out.with_suffix(".manifest.json")).write_text(json.dumps(manifest(args.campaign, args), indent=1))
    todo = specs(args.campaign, args.seeds, args.seed_start, args.systems, args.audit_seeds)
    if args.scenarios:
        todo = [t for t in todo if t["scenario"] in args.scenarios]
    if args.campaign == "replay":
        if not args.skab_dir:
            ap.error("--skab-dir is required for the replay campaign")
        for t in todo:
            t["skab_dir"] = args.skab_dir
        _write_dataset_record(args.skab_dir, out)
    mode = "w"
    if args.only_errors_of:
        prev = [json.loads(l) for l in open(args.only_errors_of)]
        keep = [r for r in prev if "error" not in r]
        errs = {(r["scenario"], r["system"], r["seed"], r.get("ablation"), r.get("tamper"), r.get("refresh_ms")) for r in prev if "error" in r}
        todo = [t for t in todo if (t["scenario"], t["system"], t["seed"], t.get("ablation"), t.get("tamper"), t.get("refresh_ms")) in errs]
        with open(out, "w") as fh:
            for r in keep:
                fh.write(json.dumps(r, default=str) + "\n")
        mode = "a"
        print(f"re-running {len(todo)} errored specs; kept {len(keep)} rows", flush=True)
    done = 0
    t0 = time.time()
    with open(out, mode) as fh, mp.get_context("fork").Pool(args.workers, maxtasksperchild=8) as pool:
        for r in pool.imap_unordered(job, todo):
            fh.write(json.dumps(r, default=str) + "\n")
            fh.flush()
            done += 1
            if done % 20 == 0 or done == len(todo):
                print(f"[{args.campaign}] {done}/{len(todo)} runs, {time.time() - t0:.0f}s", flush=True)
    print("written", out)


if __name__ == "__main__":
    main()
