#!/usr/bin/env python3
"""Monte-Carlo fragility of the bootstrap-based classes.

For every non-identical comparison, the 'ideal' bootstrap distribution of the mean of n
resampled paired differences is computed exactly by convolution when the differences are
integers (O1, O2 and some others), otherwise approximated by 400,000 resamples. The joint
distribution of the four B = 10,000 percentile bounds (np.percentile linear positions) is then
simulated exactly through uniform order statistics (exponential spacings) mapped through the
ideal quantile function. Each simulated replicate is classified with the preregistered rules
and the (bootstrap-independent) Holm p-value, giving P(class) under resampling noise.
Output: results/stats_audit/class_fragility.csv
"""
import csv
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prereg_stats as ps  # noqa: E402
import run_audit as ra  # noqa: E402

OUT = ra.OUT
R = 4000
B = ps.B
QS = [0.025, 0.975, 0.05, 0.95]


def ideal_dist(d, rng, big=400_000):
    n = len(d)
    if np.all(d == np.round(d)) and (d.max() - d.min()) <= 20000:
        v = np.round(d).astype(np.int64)
        off = v.min()
        pmf = np.bincount(v - off) / n
        dist = np.array([1.0])
        # repeated squaring would be faster; n = 20 direct convolutions are fine
        for _ in range(n):
            dist = np.convolve(dist, pmf)
        keep = dist > 0
        support = (np.arange(len(dist))[keep] + off * n) / n
        p = dist[keep] / dist[keep].sum()
        return "exact", support, np.cumsum(p)
    idx = rng.integers(0, n, size=(big, n))
    means = np.sort(d[idx].mean(axis=1))
    return "mc400k", means, None


def quantile_fn(kind, support, cdf):
    if kind == "exact":
        def q(u):
            k = np.searchsorted(cdf, u, side="left")
            return support[np.minimum(k, len(support) - 1)]
    else:
        m = len(support)

        def q(u):
            return support[np.minimum((u * m).astype(np.int64), m - 1)]
    return q


def simulate_bounds(qf, rng, r=R, b=B):
    pos = [(b - 1) * qq for qq in QS]
    js = [int(np.floor(h)) for h in pos]
    ws = [h - j for h, j in zip(pos, js)]
    ranks = sorted({j + 1 for j in js} | {j + 2 for j in js})  # 1-based ranks
    shapes = np.diff([0] + ranks + [b + 1]).astype(float)
    g = rng.gamma(shapes, 1.0, size=(r, len(shapes)))
    s = np.cumsum(g, axis=1)
    u = s[:, :-1] / s[:, -1:]
    col = {rk: i for i, rk in enumerate(ranks)}
    out = []
    for j, w in zip(js, ws):
        x0 = qf(u[:, col[j + 1]])
        x1 = qf(u[:, col[j + 2]])
        out.append((1 - w) * x0 + w * x1)
    return out  # lo95, hi95, lo90, hi90 arrays


def main():
    camps = {"A1": ps.Campaign(ps.load_jsonl("A1_review.jsonl")),
             "A3": ps.Campaign(ps.load_jsonl("A3_selective.jsonl")),
             "A3F": ps.Campaign(ps.load_jsonl("A3_factorial.jsonl"))}
    rows = []
    rng = np.random.default_rng(777)
    for lab in ("A1", "A3", "A3F"):
        rep = {(r["outcome"], r["cell"], r["arm"], r["ref"], r["hypothesis"]): r
               for r in ra.read_csv(f"{ps.REPO}/results/v4/summary/{lab}_comparisons.csv")}
        mine = {(r["outcome"], r["cell"], r["arm"], r["ref"], r["hypothesis"]): r
                for r in ra.read_csv(f"{OUT}/recomputed_{lab}.csv")}
        for key, m in mine.items():
            o, cell, arm, ref, hyp = key
            x, y, _ = camps[lab].paired(cell, arm, ref, o)
            d = x - y
            if np.all(d == 0):
                continue
            kind, support, cdf = ideal_dist(d, rng)
            qf = quantile_fn(kind, support, cdf)
            lo95, hi95, lo90, hi90 = simulate_bounds(qf, rng)
            p_holm = float(m["p_holm"])
            margin = float(m["margin"])
            direction = m["direction"]
            classes = [ps.classify(d, (a, b_), (c, e), p_holm, margin, direction)
                       for a, b_, c, e in zip(lo95, hi95, lo90, hi90)]
            vals, cnts = np.unique(classes, return_counts=True)
            prob = dict(zip(vals.tolist(), (cnts / len(classes)).tolist()))
            if kind == "exact":
                ideal = [float(qf(np.array([qq]))[0]) for qq in QS]
            else:
                ideal = [float(np.percentile(support, 100 * qq)) for qq in QS]
            ideal_class = ps.classify(d, (ideal[0], ideal[1]), (ideal[2], ideal[3]), p_holm, margin, direction)
            rep_class = ps.base_class_of_label(rep[key]["class"]) if key in rep else ""
            modal = max(prob, key=prob.get)
            rows.append({"campaign": lab, "hypothesis": hyp, "cell": cell, "arm": arm, "ref": ref, "outcome": o,
                         "ideal_kind": kind, "margin": margin, "p_holm": p_holm,
                         "ideal_ci95": f"[{ideal[0]:.6g}, {ideal[1]:.6g}]", "ideal_ci90": f"[{ideal[2]:.6g}, {ideal[3]:.6g}]",
                         "ideal_class": ideal_class, "reported_class": rep_class, "my_class": m["class"],
                         "modal_class": modal, "p_modal": prob[modal],
                         "class_probs": "; ".join(f"{k}={v:.3f}" for k, v in sorted(prob.items(), key=lambda t: -t[1])),
                         "fragile": prob[modal] < 0.99})
    with open(f"{OUT}/class_fragility.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    fr = [r for r in rows if r["fragile"]]
    print("non-identical comparisons analysed:", len(rows), " fragile (modal class prob < 0.99):", len(fr))
    print("reported != ideal:", sum(r["reported_class"] != r["ideal_class"] for r in rows),
          " mine != ideal:", sum(r["my_class"] != r["ideal_class"] for r in rows))
    for r in fr:
        print(f'{r["campaign"]} {r["hypothesis"]} {r["cell"]} {r["arm"]}-{r["ref"]} {r["outcome"]}: ideal={r["ideal_class"]} '
              f'ideal90={r["ideal_ci90"]} ideal95={r["ideal_ci95"]} reported={r["reported_class"]} mine={r["my_class"]} probs: {r["class_probs"]}')
    for r in rows:
        if r["reported_class"] != r["ideal_class"] and not r["fragile"]:
            print("NONFRAGILE but reported != ideal:", r)


if __name__ == "__main__":
    main()
