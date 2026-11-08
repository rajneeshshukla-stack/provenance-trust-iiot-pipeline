#!/usr/bin/env python3
"""Re-run the preregistered classification (analysis/analyze_v4.py: boot, wilcoxon, holm, classify; imported from the
read-only repository) for the A1 W/AV5/O2/NLX/O1 comparisons B5-X vs PBTI-R-X on S99, replacing the B5-X rows by the
audit's no-re-hold variant. All other comparisons of each family keep their published p values (Holm over the family)."""
import csv, json, sys
from pathlib import Path
sys.dont_write_bytecode = True
REPO = Path("/home/claude/PBTI_v7/work/repo_v6")                 # published rows and CSVs: read only
CODE = Path("/home/claude/PBTI_v7/scratch/audit_core/repo")       # identical analysis code, imported from the copy
sys.path.insert(0, str(CODE / "analysis")); sys.path.insert(0, str(CODE / "src"))
import analyze_v4 as AV
pub = [json.loads(l) for l in open(REPO / "results/v4/raw/A1_review.jsonl")]
fix = [json.loads(l) for l in open(sys.argv[1])]
ARMS = {(1000, 10000): "d1c10", (5000, 1000): "d5c1"}
fixed = {}
for r in fix:
    tag = ARMS[(r["cfg"]["review_delay_ms"], r["cfg"]["review_every_ms"])]
    fixed[(tag, r["seed"])] = r
comps = list(csv.DictReader(open(REPO / "results/v4/summary/A1_comparisons.csv")))
getters = {"W": lambda r: r["tm_wh_rec_s"] / max(1, r["tm_reach"]), "AV5": lambda r: r["tm_avail_5s"],
           "O2": lambda r: r["legit_missing"], "O1": lambda r: r["nonlegit_auth"], "NLX": lambda r: r["tm_nl_rec_s"]}
out = []
for code, get in getters.items():
    fam = [c for c in comps if c["outcome"] == code]
    ps = [float(c["p"]) for c in fam]
    new = {}
    for tag in ("d1c10", "d5c1"):
        arm, ref = f"B5-{tag}", f"PBTI-R-{tag}"
        A = {r["seed"]: r for r in pub if r["arm"] == arm and r["scenario"] == "S99_mixed"}
        B = {r["seed"]: r for r in pub if r["arm"] == ref and r["scenario"] == "S99_mixed"}
        seeds = sorted(set(A) & set(B) & {s for (t, s) in fixed if t == tag})
        if len(seeds) < 20:
            print("incomplete", tag, len(seeds)); continue
        # the published classification, recomputed from the published rows (sanity check of the replication)
        d_pub = [get(A[s]) - get(B[s]) for s in seeds]
        d_fix = [get({**A[s], **{k: fixed[(tag, s)][k] for k in ("tm_wh_rec_s", "tm_reach", "tm_avail_5s", "legit_missing", "nonlegit_auth", "tm_nl_rec_s")}}) - get(B[s]) for s in seeds]
        key = f"A1|{code}|S99_mixed|{arm}|{ref}"
        idx = next(i for i, c in enumerate(fam) if c["cell"] == "S99_mixed" and c["arm"] == arm and c["ref"] == ref)
        for label, d in (("published-rows", d_pub), ("no-rehold-B5", d_fix)):
            ci = AV.boot(d, key=key)
            p = AV.wilcoxon(d)
            ps2 = list(ps); ps2[idx] = p
            for j, v in new.items():
                if label == "no-rehold-B5": ps2[j] = v
            ph = AV.holm(ps2)[idx]
            c = {"d": d, "margin": float(fam[idx]["margin"]), "direction": fam[idx]["direction"], "ci95": ci[95],
                 "ci90": ci[90], "p_holm": float(ph)}
            cls = AV.classify(c)
            out.append({"outcome": code, "cell": "S99_mixed", "arm": arm, "ref": ref, "variant": label,
                        "mean_d": sum(d) / len(d), "ci95": ci[95], "ci90": ci[90], "p_holm": float(ph), "class": cls,
                        "published_class": fam[idx]["class"], "published_mean_d": float(fam[idx]["mean_d"])})
            if label == "no-rehold-B5":
                new[idx] = p
for o in out:
    print(f'{o["outcome"]:4s} {o["arm"]:9s} vs {o["ref"]:12s} {o["variant"]:15s} mean_d={o["mean_d"]:.4f} '
          f'ci95=[{o["ci95"][0]:.4f},{o["ci95"][1]:.4f}] ci90=[{o["ci90"][0]:.4f},{o["ci90"][1]:.4f}] '
          f'p_holm={o["p_holm"]:.3g} class={o["class"]!r}  (published: {o["published_mean_d"]:.4f}, {o["published_class"]!r})')
json.dump(out, open(sys.argv[2], "w"), indent=1)
