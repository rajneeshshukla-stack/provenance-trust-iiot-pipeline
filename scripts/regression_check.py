#!/usr/bin/env python3
"""Regression check: re-run a sample of stored specifications under the current source revision and compare every
outcome metric (timing and audit-timing fields excluded) with the stored raw results.

Revision 2 used it after adding B4 (B1-B3 and PBTI unchanged). V3 (`--v3`) samples every revision-2 file, including
the B4 files, and every V3 file (B5, B5s, PBTI-R, mixed workload, sweep, factorial, SKAB replay), because the V3 code
(B5, review workflow, sweep, dataset replay, policy-document validation) was added while some campaigns were running.
Output: results/summary/regression_check.json (revision 2) or regression_check_v3.json (V3).
Usage: python3 scripts/regression_check.py [--per-file N] [--v3 [--skab-dir DIR] [--workers W]]
"""
import argparse
import json
import multiprocessing as mp
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))
import run_campaign as rc  # noqa: E402

SKIP = ("_us", "_s", "wall", "ingest", "wrap", "devsign", "replay_s", "static_s")
V2_FILES = ["scenarios.jsonl", "scenarios_part2.jsonl", "scenarios_part3_b4.jsonl", "ablations.jsonl",
            "ablations_part2.jsonl", "ablations_part3_b4.jsonl", "revocation.jsonl", "revocation_part2.jsonl"]
V3_FILES = {"v3_scenarios_b5.jsonl": 12, "v3_scenarios_pbtir.jsonl": 4, "v3_mixed_b5.jsonl": 6, "v3_sweep.jsonl": 14,
            "v3_factorial.jsonl": 8, "v3_replay_skab.jsonl": 6}


def spec_of(r, skab_dir):
    kind = r.get("kind", "scenario")
    spec = {"kind": kind, "scenario": r["scenario"], "system": r["system"], "seed": r["seed"], "audit": False}
    if r.get("ablation_name") not in (None, "full", "baseline"):
        spec["ablation"] = r["ablation_name"]
    elif r.get("ablation_name") == "baseline":
        spec["ablation"] = "baseline"
    for k in ("refresh_ms", "factor", "level", "levels", "run", "signs", "speed", "stress"):
        if k in r:
            spec[k] = r[k]
    if kind == "replay":
        spec["skab_dir"] = skab_dir
    return spec


def check(item):
    f, r, skab_dir = item
    n = rc.job(spec_of(r, skab_dir))
    if "error" in n:
        return {"file": f, "scenario": r["scenario"], "system": r["system"], "seed": r["seed"], "identical": False,
                "differing_fields": ["ERROR " + n["error"][:200]]}
    diff = [k for k in r if not any(t in k for t in SKIP) and not k.startswith("audit") and r.get(k) != n.get(k)]
    return {"file": f, "scenario": r["scenario"], "system": r["system"], "seed": r["seed"], "kind": r.get("kind"),
            "factor": r.get("factor"), "level": r.get("level"), "ablation": r.get("ablation_name"),
            "refresh_ms": r.get("refresh_ms"), "identical": not diff, "differing_fields": diff[:10]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-file", type=int, default=12)
    ap.add_argument("--v3", action="store_true")
    ap.add_argument("--skab-dir", default=str(ROOT.parent.parent / "waico" / "skab"))
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--files", nargs="+", default=None, help="restrict the V3 plan to these result files")
    ap.add_argument("--out-name", default=None, help="output file name in results/summary")
    a = ap.parse_args()
    rng = random.Random(20261103)
    items = []
    if a.v3:
        plan = [(f, 8) for f in V2_FILES] + list(V3_FILES.items())
        if a.files:
            plan = [(f, k) for f, k in plan if f in a.files]
    else:
        plan = [(f, a.per_file) for f in ["scenarios.jsonl", "scenarios_part2.jsonl", "ablations.jsonl", "ablations_part2.jsonl",
                                          "revocation.jsonl"]]
    for f, k in plan:
        p = ROOT / "results" / "raw" / f
        if not p.exists():
            print("missing", f, flush=True)
            continue
        rows = [json.loads(l) for l in open(p) if l.strip()]
        rows = [r for r in rows if "error" not in r and (a.v3 or r.get("system") in ("B1", "B2", "B3", "PBTI"))]
        items += [(f, r, a.skab_dir) for r in rng.sample(rows, min(k, len(rows)))]
    out = {"source_sha256": rc.source_digest(), "mode": "v3" if a.v3 else "revision2", "checked": [], "differences": 0}
    with mp.get_context("fork").Pool(a.workers, maxtasksperchild=4) as pool:
        for res in pool.imap_unordered(check, items):
            out["checked"].append(res)
            out["differences"] += not res["identical"]
            print(res["file"], res["scenario"], res["system"], res["seed"], "identical" if res["identical"] else f"DIFF {res['differing_fields'][:5]}", flush=True)
    name = a.out_name or ("regression_check_v3.json" if a.v3 else "regression_check.json")
    (ROOT / "results" / "summary" / name).write_text(json.dumps(out, indent=1))
    print("checked", len(out["checked"]), "specs; differences:", out["differences"], "; source", out["source_sha256"][:16])
    return 1 if out["differences"] else 0


if __name__ == "__main__":
    sys.exit(main())
