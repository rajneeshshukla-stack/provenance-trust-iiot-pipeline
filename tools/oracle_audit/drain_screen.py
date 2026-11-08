#!/usr/bin/env python3
"""Screen the preregistered W comparisons for dependence on the fixed 180 s drain (stored rows only).

A legitimate observation that is lost at T_end (never available, or withdrawn at the end; per stored row this is
legit_missing, consistency check C2) accrues withheld time until T_end. Shortening the drain by x seconds (all losses
and releases happening before the new end) lowers W of a run by x * lost / n_reach, so the paired difference becomes
    dW(x) = dW - x * (lost_arm - lost_ref) / n_reach.
This is exact whenever every loss and every release happens before the shortened end (verified against the exact
truncated histories in sensitivity.py: e.g. S12 PBTI-R vs PBTI, -3.753 and -2.144 s predicted and exact).
For each comparison the CI-based margin class (equivalent: 90% percentile-bootstrap CI inside +-0.6 s; beyond:
95% CI entirely beyond +-0.6 s on one side; otherwise: neither) is computed at the published drain and with 60 s
and 120 s less drain. This is a screening of the definition's sensitivity, not a re-analysis (no Wilcoxon/Holm)."""
import json
from collections import defaultdict

import numpy as np

REPO = "/home/claude/PBTI_v7/scratch/oracle_audit/repo"
M = 0.6
A1_SETTINGS = ["hist", "d0c1", "d0c10", "d1c1", "d1c10", "d5c1", "d5c10", "d60c1", "d60c10", "event"]


def load(camp):
    by = defaultdict(lambda: defaultdict(dict))
    for line in open(f"{REPO}/results/v4/raw/{camp}.jsonl"):
        r = json.loads(line)
        cell = r.get("point") if r.get("kind") == "sweep" else r.get("scenario")
        by[cell][r["arm"]][r["seed"]] = r
    return by


def boot(d, seed):
    rng = np.random.default_rng(seed)
    d = np.asarray(d)
    m = rng.choice(d, size=(10_000, len(d)), replace=True).mean(axis=1)
    return np.percentile(m, [2.5, 97.5, 5, 95])


def cls(d, seed):
    lo95, hi95, lo90, hi90 = boot(d, seed)
    if hi95 < -M:
        return "beyond(-)"
    if lo95 > M:
        return "beyond(+)"
    if -M < lo90 and hi90 < M:
        return "equivalent"
    return "neither"


def W(r):
    return r["tm_wh_rec_s"] / max(1, r["tm_reach"])


def main():
    comps = []
    a1 = load("A1_review")
    for sc in a1:
        comps.append(("A1", "H1a", sc, "B5-hist", "PBTI", a1))
        comps.append(("A1", "H1b", sc, "B5-event", "PBTI", a1))
        for x in A1_SETTINGS:
            comps.append(("A1", "H1c", sc, f"B5-{x}", f"PBTI-R-{x}", a1))
    for camp in ("A3_selective", "A3_factorial"):
        a3 = load(camp)
        for p in a3:
            for arm, ref, h in (("PBTI-SH", "PBTI", "H3a"), ("PBTI-SH", "B5-hist", "H3b"), ("PBTI-SH", "B5-event", "H3b"),
                                ("PBTI-SH", "B5S", "H3b"), ("PBTI-SH", "PBTI-R-hist", "H3b"), ("PBTI-SH-T30", "PBTI-SH", "H3c")):
                comps.append((camp, h, p, arm, ref, a3))
    out = []
    changed = defaultdict(int)
    total = defaultdict(int)
    for i, (camp, h, cell, arm, ref, by) in enumerate(comps):
        a, b = by[cell].get(arm, {}), by[cell].get(ref, {})
        seeds = sorted(set(a) & set(b))
        if len(seeds) < 2:
            continue
        d = np.array([W(a[s]) - W(b[s]) for s in seeds])
        slope = np.array([(a[s]["legit_missing"] - b[s]["legit_missing"]) / max(1, b[s]["tm_reach"]) for s in seeds])
        row = {"campaign": camp, "hyp": h, "cell": cell, "arm": arm, "ref": ref, "n": len(seeds),
               "dW_full": float(d.mean()), "dW_drain120": float((d - 60 * slope).mean()),
               "dW_drain60": float((d - 120 * slope).mean()), "dlost_per_obs": float(slope.mean())}
        row["class_full"] = cls(d, i)
        row["class_drain120"] = cls(d - 60 * slope, i)
        row["class_drain60"] = cls(d - 120 * slope, i)
        out.append(row)
        key = (camp, h)
        total[key] += 1
        if len({row["class_full"], row["class_drain120"], row["class_drain60"]}) > 1:
            changed[key] += 1
    json.dump(out, open("/home/claude/PBTI_v7/results/oracle_audit/drain_screen.json", "w"), indent=1)
    print("comparisons whose CI-based W margin class changes with a 120 s or 60 s drain (of all W comparisons):")
    for key in sorted(total):
        print(f"  {key[0]:13s} {key[1]}: {changed[key]}/{total[key]}")
    print("\nexamples:")
    for r in sorted(out, key=lambda r: -abs(r["dW_full"] - r["dW_drain60"]))[:14]:
        flag = "  <-- class changes" if len({r["class_full"], r["class_drain120"], r["class_drain60"]}) > 1 else ""
        print(f"  {r['campaign']:12s} {r['hyp']} {r['cell'][:34]:34s} {r['arm']:13s} vs {r['ref']:12s} "
              f"dW full {r['dW_full']:+6.2f} ({r['class_full']}), drain120 {r['dW_drain120']:+6.2f} "
              f"({r['class_drain120']}), drain60 {r['dW_drain60']:+6.2f} ({r['class_drain60']}){flag}")
    ch = [r for r in out if len({r["class_full"], r["class_drain120"], r["class_drain60"]}) > 1]
    print(f"\n{len(ch)} of {len(out)} W comparisons change CI-based margin class:")
    for r in ch:
        print(f"  {r['campaign']:12s} {r['hyp']} {r['cell'][:40]:40s} {r['arm']:13s} vs {r['ref']:12s} "
              f"full {r['dW_full']:+6.2f} {r['class_full']:10s} | 120s {r['dW_drain120']:+6.2f} {r['class_drain120']:10s}"
              f" | 60s {r['dW_drain60']:+6.2f} {r['class_drain60']}")


if __name__ == "__main__":
    main()
