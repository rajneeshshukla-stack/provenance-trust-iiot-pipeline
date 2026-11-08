#!/usr/bin/env python3
"""A0: compare the V4 reproduction of the core scenario campaign with the archived V2/V3 raw rows, field by field.

For every new row (results/v4/raw/A0_core.jsonl) the archived row with the same scenario, pipeline and seed is looked
up in the historical file that produced the published numbers; every deterministic field of the archived row (all
fields except wall-clock timing and audit timing, as in scripts/regression_check.py) must be equal. Fields that the V4
row adds (tm_*, review settings, cfg, arm, campaign) are not part of the comparison. This is a full reproduction of
the listed campaigns, not a sampled regression.

Usage: python3 scripts/compare_a0.py results/v4/raw/A0_core.jsonl [--out results/v4/summary/A0_comparison.json]
"""
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results" / "raw"
SKIP = ("_us", "wall", "ingest", "wrap", "devsign")     # wall-clock timing (substring); and any field ending in _s


def skipped(k):
    return any(t in k for t in SKIP) or k.endswith("_s") or k.startswith("audit") or k in META
# runner bookkeeping written by the historical runners (experiments/run_*.py), not outcomes of the run: the ablation
# runner labels its rows with ablation_name and kind="ablation"; the V4 runner writes kind="scenario". Their values
# are reported (metadata_values) but not compared.
META = ("ablation_name", "kind")

# arm -> (historical file(s), selector) for scenarios E1-E15 and for the mixed workload S99_mixed
HIST = {
    "PBTI": (["scenarios.jsonl", "scenarios_part2.jsonl"], ["ablations.jsonl", "ablations_part2.jsonl"]),
    "B4": (["scenarios_part3_b4.jsonl"], ["ablations_part3_b4.jsonl"]),
    "B5-hist": (["v3_scenarios_b5.jsonl"], ["v3_mixed_b5.jsonl"]),
    "B5S": (["v3_scenarios_b5.jsonl"], ["v3_mixed_b5.jsonl"]),
    "PBTI-R-hist": (["v3_scenarios_pbtir.jsonl"], ["v3_mixed_b5.jsonl"]),
}
SYS = {"PBTI": "PBTI", "B4": "B4", "B5-hist": "B5", "B5S": "B5S", "PBTI-R-hist": "PBTI-R"}


def load(files, mixed):
    idx = {}
    for f in files:
        for line in (RAW / f).read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if "error" in r:
                continue
            if mixed and r.get("ablation_name") not in ("full", "baseline", None):
                continue
            idx[(r["scenario"], r["system"], r["seed"])] = (f, r)
    return idx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("new")
    ap.add_argument("--out", default=str(ROOT / "results" / "v4" / "summary" / "A0_comparison.json"))
    a = ap.parse_args()
    cache = {}
    res = {"compared": 0, "identical": 0, "missing_historical": [], "errors_new": 0, "differences": [],
           "by_arm": defaultdict(lambda: Counter()), "metadata_values": Counter(), "skipped_fields": set(),
           "excluded": {"timing_substrings": list(SKIP), "suffix": "_s", "audit_prefix": "audit",
                        "runner_metadata": list(META)}}
    for line in Path(a.new).read_text().splitlines():
        n = json.loads(line)
        if "error" in n:
            res["errors_new"] += 1
            continue
        arm = n["arm"]
        mixed = n["scenario"] == "S99_mixed"
        files = HIST[arm][1 if mixed else 0]
        key = (tuple(files), mixed)
        if key not in cache:
            cache[key] = load(files, mixed)
        hit = cache[key].get((n["scenario"], SYS[arm], n["seed"]))
        if hit is None:
            res["missing_historical"].append([arm, n["scenario"], n["seed"]])
            continue
        f, h = hit
        diff = [k for k in h if not skipped(k) and h.get(k) != n.get(k)]
        cmp_fields = [k for k in h if not skipped(k)]
        res["_nf"] = res.get("_nf", 0) + len(cmp_fields)
        res["skipped_fields"].update(k for k in h if k not in cmp_fields)
        for k in META:
            if k in h:
                res["metadata_values"][f"{k}={h.get(k)!r}->{n.get(k)!r}"] += 1
        res["compared"] += 1
        res["by_arm"][arm]["compared"] += 1
        if diff:
            res["differences"].append({"arm": arm, "scenario": n["scenario"], "seed": n["seed"], "file": f, "fields": diff[:12]})
            res["by_arm"][arm]["different"] += 1
        else:
            res["identical"] += 1
            res["by_arm"][arm]["identical"] += 1
    res["by_arm"] = {k: dict(v) for k, v in res["by_arm"].items()}
    res["metadata_values"] = dict(res["metadata_values"])
    res["n_field_comparisons_total"] = res.pop("_nf", 0)
    res["skipped_fields"] = sorted(res["skipped_fields"])
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k != "differences"}, indent=1))
    print("differences:", len(res["differences"]), res["differences"][:3])


if __name__ == "__main__":
    main()
