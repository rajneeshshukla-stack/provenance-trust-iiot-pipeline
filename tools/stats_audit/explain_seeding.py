#!/usr/bin/env python3
"""STEP 3 check: with the analysis' seeding rule (default_rng([20261104, crc32(key)])) my bootstrap code
reproduces every reported CI bound; with the literal rule (default_rng(20261104)) bounds differ only by MC noise."""
import csv, json, sys, os, zlib
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prereg_stats as ps
import run_audit as ra

res = {}
for lab, raw, rep in (("A1", "A1_review.jsonl", "A1_comparisons.csv"), ("A3", "A3_selective.jsonl", "A3_comparisons.csv"),
                      ("A3F", "A3_factorial.jsonl", "A3F_comparisons.csv")):
    camp = ps.Campaign(ps.load_jsonl(raw))
    n = exact = 0
    worst = 0.0
    cls_same = 0
    for r in ra.read_csv(f"{ps.REPO}/results/v4/summary/{rep}"):
        x, y, _ = camp.paired(r["cell"], r["arm"], r["ref"], r["outcome"])
        d = x - y
        key = f'{lab}|{r["outcome"]}|{r["cell"]}|{r["arm"]}|{r["ref"]}'
        if np.all(d == d[0]):
            c95 = c90 = (float(d[0]), float(d[0]))
        else:
            rng = np.random.default_rng([ps.SEED, zlib.crc32(key.encode())])
            m = d[rng.integers(0, len(d), (ps.B, len(d)))].mean(axis=1)
            c95 = tuple(np.percentile(m, [2.5, 97.5])); c90 = tuple(np.percentile(m, [5, 95]))
        r95, r90 = ra.parse_ci(r["ci95"]), ra.parse_ci(r["ci90"])
        diffs = [abs(a - b) for a, b in zip(c95 + c90, r95 + r90)]
        n += 1
        exact += int(max(diffs) <= 1e-12 * max(1.0, max(abs(v) for v in r95 + r90)))
        worst = float(max(worst, max(diffs)))
        cl = ps.classify(d, c95, c90, float(r["p_holm"]), float(r["margin"]), r["direction"])
        cls_same += int(cl == ps.base_class_of_label(r["class"]))
    res[lab] = {"rows": n, "ci_bounds_identical": exact, "max_abs_diff": worst, "class_match_with_crc32_seeding": cls_same}
print(json.dumps(res, indent=1))
json.dump(res, open(f"{ra.OUT}/seeding_explanation.json", "w"), indent=1)
