#!/usr/bin/env python3
"""Self-checks of the audit's own Wilcoxon / Holm / bootstrap code (synthetic data only)."""
import itertools
import os
import sys
import warnings

import numpy as np
import scipy.stats as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prereg_stats as ps  # noqa: E402

warnings.simplefilter("ignore")
rng = np.random.default_rng(1)
bad = 0
n_cases = 0
for trial in range(3000):
    n = 20
    kind = trial % 4
    if kind == 0:
        d = rng.normal(0.3, 1, n)
    elif kind == 1:
        d = rng.integers(-3, 4, n).astype(float)
    elif kind == 2:
        d = np.where(rng.random(n) < 0.6, 0.0, rng.normal(0, 1, n))
    else:
        d = rng.integers(-1, 3, n).astype(float) * 0.5
    if np.all(d == 0):
        continue
    n_cases += 1
    mine = ps.wilcoxon(d)
    sp_auto = st.wilcoxon(d, zero_method="wilcox").pvalue
    sp_norm = st.wilcoxon(d, zero_method="wilcox", method="approx").pvalue
    if not np.isclose(mine["auto"], sp_auto, rtol=1e-9, atol=1e-14):
        bad += 1
        print("auto mismatch", d, mine["auto"], sp_auto)
    if not np.isclose(mine["normal"], sp_norm, rtol=1e-9, atol=1e-14):
        bad += 1
        print("normal mismatch", d, mine["normal"], sp_norm)
print("wilcoxon vs scipy: cases", n_cases, "mismatches", bad)

# exact conditional vs brute-force sign enumeration (small n, ties)
bad = 0
for trial in range(300):
    n = int(rng.integers(1, 11))
    d = rng.integers(-3, 4, n).astype(float)
    nz = d[d != 0]
    if len(nz) == 0:
        continue
    ranks, _ = ps._avg_ranks(np.abs(nz))
    obs = ranks[nz > 0].sum()
    sums = [sum(r for r, s in zip(ranks, signs) if s) for signs in itertools.product([0, 1], repeat=len(nz))]
    sums = np.array(sums)
    p_bf = min(1.0, 2 * min(np.mean(sums <= obs + 1e-12), np.mean(sums >= obs - 1e-12)))
    if not np.isclose(p_bf, ps.wilcoxon(d)["exact_cond"], rtol=1e-12):
        bad += 1
        print("exact mismatch", d, p_bf, ps.wilcoxon(d)["exact_cond"])
print("exact-conditional vs brute force mismatches:", bad)

# Holm vs a direct definition
bad = 0
for trial in range(500):
    m = int(rng.integers(1, 30))
    p = rng.random(m) ** 3
    p[rng.random(m) < 0.3] = 1.0
    adj = ps.holm(p)
    order = np.argsort(p, kind="mergesort")
    ref = np.empty(m)
    for k in range(m):
        ref[order[k]] = min(1.0, max((m - j) * p[order[j]] for j in range(k + 1)))
    if not np.allclose(adj, ref):
        bad += 1
print("holm mismatches:", bad)

# bootstrap reproducibility and nesting 90 within 95
d = rng.normal(0, 1, 20)
a = ps.bootstrap_cis(d)
b = ps.bootstrap_cis(d)
print("bootstrap deterministic:", a[0] == b[0] and a[1] == b[1],
      " 90 within 95:", a[0][0] <= a[1][0] <= a[1][1] <= a[0][1])
