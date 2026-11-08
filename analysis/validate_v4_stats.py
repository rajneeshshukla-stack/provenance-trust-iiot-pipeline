#!/usr/bin/env python3
"""Independent re-computation of the V4 confirmatory statistics (Part 7 research verification).

Written separately from analysis/analyze_v4.py (pandas-based loading, own pairing, own Holm and classification from
the text of research/V4/PREREGISTRATION_V4.md, Section 4); only scipy's Wilcoxon test and numpy's generator are
shared. Re-computes every comparison of A1, A3 and A3F from the raw JSONL files and compares mean differences,
bootstrap intervals (same seeding rule: RNG_SEED and CRC32 of the comparison key), p values, Holm-adjusted p values
and classifications with results/v4/summary/*_comparisons.csv. Exit status 1 on any mismatch.
"""
import json
import sys
import zlib
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results" / "v4" / "raw"
SUM = ROOT / "results" / "v4" / "summary"
SEED = 20261104


def outcome(df, code):
    if code == "W":
        return df["tm_wh_rec_s"] / df["tm_reach"].clip(lower=1)
    return df[{"O1": "nonlegit_auth", "O2": "legit_missing", "NLX": "tm_nl_rec_s", "AV5": "tm_avail_5s"}[code]]


PREF = {"O1": "lower", "O2": "lower", "NLX": "lower", "W": "lower", "AV5": "higher"}


def holm(p):
    p = np.asarray(p, float)
    order = np.argsort(p, kind="stable")
    out = np.empty_like(p)
    m = len(p)
    running = 0.0
    for rank, idx in enumerate(order):
        running = max(running, min(1.0, (m - rank) * p[idx]))
        out[idx] = running
    return out


def classify(d, D, pref, lo95, hi95, lo90, hi90, ph):
    if np.all(d == 0):
        return "identical"
    sig = ph < 0.05
    better = (hi95 < -D) if pref == "lower" else (lo95 > D)
    worse = (lo95 > D) if pref == "lower" else (hi95 < -D)
    if sig and better:
        return "better beyond margin"
    if sig and worse:
        return "worse beyond margin"
    if lo90 > -D and hi90 < D:
        return "equivalent within margin" + (" (significant difference)" if sig else "")
    return "different, within margin" if sig else "inconclusive"


def recompute(campaign, raw_name, sum_name):
    rawp, sump = RAW / raw_name, SUM / sum_name
    if not rawp.exists() or not sump.exists():
        return None
    rows = [json.loads(x) for x in rawp.read_text().splitlines() if x.strip()]
    df = pd.DataFrame([r for r in rows if "error" not in r])
    errs = [r for r in rows if "error" in r]
    df["cell"] = np.where(df["kind"] == "sweep", df.get("point"), df["scenario"])
    for e in errs:                                     # exclusion rule: drop the errored seed from its cell
        c = e.get("point") if e.get("kind") == "sweep" else e.get("scenario")
        df = df[~((df["cell"] == c) & (df["seed"] == e.get("seed")))]
    ref = pd.read_csv(sump)
    out = []
    for code, fam in ref.groupby("outcome", sort=False):
        recs = []
        for _, r in fam.iterrows():
            a = df[(df["cell"] == r["cell"]) & (df["arm"] == r["arm"])].set_index("seed")
            b = df[(df["cell"] == r["cell"]) & (df["arm"] == r["ref"])].set_index("seed")
            seeds = sorted(set(a.index) & set(b.index))
            d = (outcome(a.loc[seeds], code) - outcome(b.loc[seeds], code)).to_numpy(float)
            D = 0.01 * float(np.median(b.loc[seeds, "n_reachable"])) if code == "O2" else \
                {"O1": 1.0, "NLX": 60.0, "W": 0.6, "AV5": 0.01}[code]
            if np.all(d == d[0]):
                ci = {95: (d[0], d[0]), 90: (d[0], d[0])}
            else:
                rng = np.random.default_rng([SEED, zlib.crc32(f"{campaign}|{code}|{r['cell']}|{r['arm']}|{r['ref']}".encode())])
                bs = d[rng.integers(0, len(d), (10_000, len(d)))].mean(axis=1)
                ci = {95: tuple(np.percentile(bs, [2.5, 97.5])), 90: tuple(np.percentile(bs, [5, 95]))}
            p = 1.0 if np.all(d == 0) else float(stats.wilcoxon(d, zero_method="wilcox").pvalue)
            recs.append(dict(cell=r["cell"], arm=r["arm"], ref=r["ref"], d=d, mean_d=float(d.mean()), D=D,
                             ci95=ci[95], ci90=ci[90], p=p))
        ph = holm([x["p"] for x in recs])
        for x, h, (_, r) in zip(recs, ph, fam.iterrows()):
            cl = classify(x["d"], x["D"], PREF[code], *x["ci95"], *x["ci90"], h)
            ci95_ref = json.loads(r["ci95"])
            ok = (abs(x["mean_d"] - r["mean_d"]) < 1e-9 and abs(x["ci95"][0] - ci95_ref[0]) < 1e-9
                  and abs(x["ci95"][1] - ci95_ref[1]) < 1e-9 and abs(x["p"] - r["p"]) < 1e-12
                  and abs(h - r["p_holm"]) < 1e-12 and cl == r["class"] and abs(x["D"] - r["margin"]) < 1e-9)
            out.append({"campaign": campaign, "outcome": code, "cell": x["cell"], "arm": x["arm"], "ref": x["ref"],
                        "match": ok, "class_independent": cl, "class_reported": r["class"]})
    return out


def main():
    allr = []
    for camp, raw, sm in (("A1", "A1_review.jsonl", "A1_comparisons.csv"),
                          ("A3", "A3_selective.jsonl", "A3_comparisons.csv"),
                          ("A3F", "A3_factorial.jsonl", "A3F_comparisons.csv")):
        r = recompute(camp, raw, sm)
        if r is None:
            print(f"{camp}: inputs missing, skipped")
            continue
        n_bad = sum(not x["match"] for x in r)
        print(f"{camp}: {len(r)} comparisons re-computed independently, {n_bad} mismatches")
        allr += r
    rep = {"comparisons": len(allr), "mismatches": sum(not x["match"] for x in allr),
           "mismatch_examples": [x for x in allr if not x["match"]][:20]}
    (SUM / "v4_independent_stats_validation.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps({k: v for k, v in rep.items() if k != "mismatch_examples"}))
    sys.exit(1 if rep["mismatches"] or not allr else 0)


if __name__ == "__main__":
    main()
