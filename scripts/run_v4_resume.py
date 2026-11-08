#!/usr/bin/env python3
"""Resume a V4 campaign after an interruption (decision D08).

Uses the frozen runner `experiments/run_v4.py` unchanged: its `expand()` gives the campaign's specifications and its
`job()` executes one run. Rows already present in the output file (valid JSON lines, including error rows, which are
deterministic) are kept; a truncated last line is dropped; only the missing specifications are run and appended.
Every run is deterministic for its specification and independent of the others, so a resumed campaign is identical
to an uninterrupted one apart from the order of rows and wall-clock fields. Each resume writes
`<out>.resume<k>.manifest.json` (source digest, configuration hash, rows kept, rows to run).
"""
import argparse
import hashlib
import json
import multiprocessing as mp
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))
import run_v4  # noqa: E402  (frozen runner, imported unchanged)
import run_campaign as rc  # noqa: E402


def key(r):
    return (r.get("arm"), r.get("scenario"), r.get("point"), r.get("seed"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config")
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=2)
    a = ap.parse_args()
    cpath = Path(a.config)
    conf = json.loads(cpath.read_text())
    todo_all = run_v4.expand(conf, None)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    kept, dropped = [], 0
    if out.exists():
        for line in out.read_text().splitlines():
            if not line.strip():
                continue
            try:
                kept.append(json.loads(line))
            except json.JSONDecodeError:
                dropped += 1
        if dropped:                                   # rewrite without the truncated line(s)
            tmp = out.with_suffix(".tmp")
            tmp.write_text("".join(json.dumps(r, default=str) + "\n" for r in kept))
            tmp.replace(out)
    done = {key(r) for r in kept}
    todo = [s for s in todo_all if key(s) not in done]
    k = 1
    while out.with_suffix(f".resume{k}.manifest.json").exists():
        k += 1
    if not out.with_suffix(".manifest.json").exists():
        k = 0
    man = rc.manifest(conf["campaign"], a)
    man.update({"config_file": str(cpath), "config_sha256": hashlib.sha256(cpath.read_bytes()).hexdigest(),
                "config": conf, "n_specs": len(todo_all), "rows_kept": len(kept), "truncated_lines_dropped": dropped,
                "rows_to_run": len(todo), "runner": "scripts/run_v4_resume.py (frozen experiments/run_v4.py job/expand)",
                "runner_sha256": hashlib.sha256((ROOT / "experiments" / "run_v4.py").read_bytes()).hexdigest()})
    mpath = out.with_suffix(".manifest.json") if k == 0 else out.with_suffix(f".resume{k}.manifest.json")
    mpath.write_text(json.dumps(man, indent=1, default=str))
    print(f"[{conf['campaign']}] specs {len(todo_all)}, kept {len(kept)}, dropped {dropped}, to run {len(todo)}", flush=True)
    if not todo:
        print("complete", flush=True)
        return
    t0 = time.time()
    n = errors = 0
    with open(out, "a") as fh, mp.get_context("fork").Pool(a.workers, maxtasksperchild=8) as pool:
        for r in pool.imap_unordered(run_v4.job, todo):
            fh.write(json.dumps(r, default=str) + "\n")
            fh.flush()
            n += 1
            errors += "error" in r
            if n % 25 == 0 or n == len(todo):
                print(f"[{conf['campaign']}] {len(kept) + n}/{len(todo_all)} runs ({n} this resume), {errors} errors, "
                      f"{time.time() - t0:.0f}s", flush=True)
    print("complete", flush=True)


if __name__ == "__main__":
    main()
