#!/usr/bin/env python3
"""Independent re-implementation of the PBTI V4 preregistered statistics.

Written from the TEXT of research/V4/PREREGISTRATION_V4.md (sections 3-9) and
research/V4/PREREGISTRATION_V4_AMENDMENT_1.md only, without reading
analysis/analyze_v4.py or analysis/validate_v4_stats.py.

Procedure (prereg section 4):
  * run = experimental unit; paired difference d = arm - reference per seed;
  * mean(d); 95 % percentile bootstrap CI (10,000 resamples, RNG seed 20261104);
    90 % bootstrap CI (same resamples) for equivalence;
  * two-sided Wilcoxon signed-rank, zero differences discarded; all-zero -> "identical", p = 1;
  * Holm within each family = campaign x outcome; alpha = 0.05;
  * margins: O1 1, O2 1 % of the median reachable count of the cell, NLX 60 record-s,
    W 0.6 s, AV5 0.01;
  * classes: identical -> equivalent (90 % CI inside (-D, +D)) -> better/worse beyond D
    (Holm p < .05 and 95 % CI entirely beyond the margin) -> different within D (Holm p < .05)
    -> inconclusive.

Nothing in this module writes inside the repository.
"""
from __future__ import annotations

import json
import math
from collections import defaultdict

import numpy as np

REPO = "/home/claude/PBTI_v7/work/repo_v6"
RAW = REPO + "/results/v4/raw"

B = 10_000
SEED = 20261104
ALPHA = 0.05

OUTCOMES = ["O1", "O2", "NLX", "W", "AV5"]
DIRECTION = {"O1": "lower", "O2": "lower", "NLX": "lower", "W": "lower", "AV5": "higher"}
FIXED_MARGIN = {"O1": 1.0, "NLX": 60.0, "W": 0.6, "AV5": 0.01}


# --------------------------------------------------------------------------- data
def load_jsonl(name):
    rows = []
    with open(f"{RAW}/{name}") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def cell_of(row):
    """Design point: 'point' for sweep/factorial campaigns, 'scenario' otherwise."""
    return row["point"] if "point" in row else row["scenario"]


def outcome_value(row, o):
    # prereg section 3 table: field definitions
    if o == "O1":
        return float(row["nonlegit_auth"])
    if o == "O2":
        return float(row["legit_missing"])
    if o == "NLX":
        return float(row["tm_nl_rec_s"])
    if o == "W":
        return float(row["tm_wh_rec_s"]) / float(row["tm_reach"])
    if o == "AV5":
        return float(row["tm_avail_5s"])
    raise KeyError(o)


def is_error_row(row):
    # prereg section 9: "Error rows are not results". The runner rows carry no explicit status
    # field; we treat a row as an error row if it has an 'error'/'exception' key or lacks a
    # primary outcome field.
    if any(k in row for k in ("error", "exception", "traceback")):
        return True
    for f in ("nonlegit_auth", "legit_missing", "tm_nl_rec_s", "tm_wh_rec_s", "tm_reach", "tm_avail_5s"):
        v = row.get(f)
        if v is None or (isinstance(v, float) and not math.isfinite(v)):
            return True
    if row.get("tm_reach", 0) == 0:
        return True
    return False


class Campaign:
    def __init__(self, rows):
        self.by = {}
        self.errors = []
        self.reach = defaultdict(list)
        for r in rows:
            key = (cell_of(r), r["arm"], int(r["seed"]))
            if key in self.by:
                raise ValueError(f"duplicate run {key}")
            if is_error_row(r):
                self.errors.append(key)
                continue
            self.by[key] = r
            self.reach[cell_of(r)].append(float(r["tm_reach"]))
        self.seeds = sorted({k[2] for k in self.by})

    def paired(self, cell, arm, ref, o):
        """Paired per-seed values; a seed with an error row in either arm of the cell is excluded
        (prereg section 9: excluded from every comparison of that cell)."""
        bad_seeds = {s for (c, a, s) in self.errors if c == cell}
        xs, ys, seeds = [], [], []
        for s in self.seeds:
            if s in bad_seeds:
                continue
            ka, kr = (cell, arm, s), (cell, ref, s)
            if ka in self.by and kr in self.by:
                xs.append(outcome_value(self.by[ka], o))
                ys.append(outcome_value(self.by[kr], o))
                seeds.append(s)
        return np.array(xs), np.array(ys), seeds

    def margin(self, cell, o, rounded=False):
        if o != "O2":
            return FIXED_MARGIN[o]
        m = 0.01 * float(np.median(self.reach[cell]))
        return float(round(m)) if rounded else m


# --------------------------------------------------------------------------- bootstrap
_IDX_CACHE = {}


def bootstrap_index(n, b=B, seed=SEED):
    """Resample indices: a fresh numpy Generator seeded with the preregistered seed for every
    comparison (one natural reading of 'RNG seed 20261104')."""
    key = (n, b, seed)
    if key not in _IDX_CACHE:
        rng = np.random.default_rng(seed)
        _IDX_CACHE[key] = rng.integers(0, n, size=(b, n))
    return _IDX_CACHE[key]


def bootstrap_cis(d, b=B, seed=SEED):
    idx = bootstrap_index(len(d), b, seed)
    means = d[idx].mean(axis=1)
    lo95, hi95 = np.percentile(means, [2.5, 97.5])
    lo90, hi90 = np.percentile(means, [5.0, 95.0])
    return (float(lo95), float(hi95)), (float(lo90), float(hi90)), means


# --------------------------------------------------------------------------- Wilcoxon
def _avg_ranks(a):
    """1-based average ranks with exact-equality ties; returns ranks and tie-group sizes."""
    n = len(a)
    order = np.argsort(a, kind="mergesort")
    sa = a[order]
    ranks = np.empty(n)
    ties = []
    i = 0
    while i < n:
        j = i
        while j + 1 < n and sa[j + 1] == sa[i]:
            j += 1
        ranks[order[i : j + 1]] = (i + j) / 2.0 + 1.0
        ties.append(j - i + 1)
        i = j + 1
    return ranks, ties


def _subset_sum_counts(int_weights):
    """counts[s] = number of sign assignments whose 'positive' weights sum to s."""
    total = int(sum(int_weights))
    counts = np.zeros(total + 1, dtype=np.float64)
    counts[0] = 1.0
    for w in int_weights:
        w = int(w)
        if w == 0:
            counts = counts * 2.0
        else:
            shifted = np.zeros_like(counts)
            shifted[w:] = counts[: total + 1 - w]
            counts = counts + shifted
    return counts


def wilcoxon(d):
    """Two-sided Wilcoxon signed-rank test, zero differences discarded (zero_method='wilcox').

    Returns dict with p-values for three variants (all computed here, no scipy):
      'exact_cond' : exact sign-flip null conditional on the observed (mid)ranks;
      'normal'     : normal approximation with tie correction, no continuity correction;
      'auto'       : exact (no ties) null if there are no zeros and no ties among |d|, else 'normal'
                     (the documented default behaviour of scipy.stats.wilcoxon, which the
                     preregistration's zero_method="wilcox" refers to).
    """
    d = np.asarray(d, dtype=float)
    n_all = len(d)
    nz = d[d != 0]
    n = len(nz)
    if n == 0:
        return {"n_nonzero": 0, "W_plus": 0.0, "exact_cond": 1.0, "normal": 1.0, "auto": 1.0,
                "has_ties": False, "has_zeros": n_all > 0}
    ranks, ties = _avg_ranks(np.abs(nz))
    w_plus = float(ranks[nz > 0].sum())
    has_ties = any(t > 1 for t in ties)
    has_zeros = n < n_all
    # normal approximation
    mu = n * (n + 1) / 4.0
    var = n * (n + 1) * (2 * n + 1) / 24.0 - sum(t ** 3 - t for t in ties) / 48.0
    z = (w_plus - mu) / math.sqrt(var)
    p_norm = math.erfc(abs(z) / math.sqrt(2.0))
    # exact conditional (doubled ranks are integers)
    w2 = np.rint(2 * ranks).astype(int)
    counts = _subset_sum_counts(w2)
    tot = counts.sum()
    s_obs = int(round(2 * w_plus))
    p_le = counts[: s_obs + 1].sum() / tot
    p_ge = counts[s_obs:].sum() / tot
    p_exact = min(1.0, 2.0 * min(p_le, p_ge))
    p_auto = p_exact if (not has_ties and not has_zeros and n <= 50) else p_norm
    return {"n_nonzero": n, "W_plus": w_plus, "exact_cond": float(p_exact), "normal": float(p_norm),
            "auto": float(p_auto), "has_ties": has_ties, "has_zeros": has_zeros, "z": z}


# --------------------------------------------------------------------------- Holm
def holm(pvals):
    p = np.asarray(pvals, dtype=float)
    m = len(p)
    order = np.argsort(p, kind="mergesort")
    adj = np.empty(m)
    running = 0.0
    for k, i in enumerate(order):
        running = max(running, min(1.0, (m - k) * p[i]))
        adj[i] = running
    return adj


# --------------------------------------------------------------------------- classes
def classify(d, ci95, ci90, p_holm, margin, direction, strict=True):
    """Prereg section 4 class rules, applied in the listed order."""
    if np.all(d == 0):
        return "identical"
    lt = (lambda a, b: a < b) if strict else (lambda a, b: a <= b)
    lo90, hi90 = ci90
    lo95, hi95 = ci95
    if (-margin < lo90) and (hi90 < margin):
        return "equivalent"
    if p_holm < ALPHA:
        if lt(hi95, -margin):  # entirely below -margin
            return "better" if direction == "lower" else "worse"
        if lt(margin, lo95):  # entirely above +margin
            return "worse" if direction == "lower" else "better"
        return "different"
    return "inconclusive"


LABEL = {
    "identical": "identical",
    "equivalent": "equivalent within margin",
    "better": "better beyond margin",
    "worse": "worse beyond margin",
    "different": "different, within margin",
    "inconclusive": "inconclusive",
}


def base_class_of_label(label):
    """Map a reported label to the prereg base class."""
    label = str(label).strip()
    if label.startswith("equivalent"):
        return "equivalent"
    for k, v in LABEL.items():
        if label == v:
            return k
    return "UNKNOWN:" + label


# --------------------------------------------------------------------------- comparison specs
A1_SCEN = ["S05_stolen_key", "S08_seq_reuse_bug", "S12_beyond_horizon", "S99_mixed"]
H1C_SETTINGS = ["hist", "d0c1", "d1c1", "d5c1", "d60c1", "d60c10", "event", "d0c10", "d1c10", "d5c10"]
A3_ARMS = [("H3a", "PBTI-SH", "PBTI"), ("H3b", "PBTI-SH", "B5-hist"), ("H3b", "PBTI-SH", "B5-event"),
           ("H3b", "PBTI-SH", "B5S"), ("H3b", "PBTI-SH", "PBTI-R-hist"), ("H3c", "PBTI-SH-T30", "PBTI-SH")]


def a1_specs():
    """(hypothesis, arm, ref, outcomes_text, outcomes_all) per scenario.

    outcomes_text: the outcomes the prereg text names for the hypothesis (section 6);
    all five outcomes are also computed so the reported (wider) family can be reproduced."""
    out = []
    for s in A1_SCEN:
        out.append((s, "H1a", "B5-hist", "PBTI", ["O1", "NLX", "W", "AV5"]))
        out.append((s, "H1b", "B5-event", "PBTI", ["W", "AV5"]))
        for x in H1C_SETTINGS:
            out.append((s, "H1c", f"B5-{x}", f"PBTI-R-{x}", list(OUTCOMES)))
        for x in H1C_SETTINGS:
            if x != "hist":
                out.append((s, "H1d", f"B5-{x}", "B5-hist", ["O1", "NLX"]))
    return out


def a3_specs(cells):
    out = []
    for c in cells:
        for h, a, r in A3_ARMS:
            out.append((c, h, a, r, list(OUTCOMES)))
    return out


A3_GRID = (
    [f"equivocation={e}+missing={m}" for e in ("0", "0.01", "0.05", "0.1") for m in ("0", "0.01", "0.05", "0.1")]
    + [f"delay={x}+equivocation=0.05" for x in ("0.01", "0.05", "0.1")]
    + [f"equivocation=0.05+missing_long={x}" for x in ("0.01", "0.05")]
)
A3F_CELLS = [f"run{r}" for r in (2, 3, 4, 5, 8, 9, 14, 15)]
FG_CELLS = ["run3", "run4", "run8", "run15"]


# --------------------------------------------------------------------------- core computation
def compute_rows(camp, campaign_label, specs, all_outcomes_for=None, b=B, seed=SEED):
    """Compute one record per (cell, hypothesis, arm, ref, outcome).

    all_outcomes_for: set of hypotheses for which all five outcomes are computed even if the
    text names fewer (flag 'in_text' records whether the text names the outcome)."""
    recs = []
    for spec in specs:
        cell, hyp, arm, ref, outs_text = spec
        outs = OUTCOMES if (all_outcomes_for and hyp in all_outcomes_for) else outs_text
        for o in outs:
            x, y, seeds = camp.paired(cell, arm, ref, o)
            d = x - y
            ci95, ci90, _ = bootstrap_cis(d, b, seed)
            w = wilcoxon(d)
            recs.append({
                "campaign": campaign_label, "outcome": o, "cell": cell, "arm": arm, "ref": ref,
                "hypothesis": hyp, "n": len(d), "seeds": seeds,
                "mean_d": float(d.mean()), "mean_arm": float(x.mean()), "mean_ref": float(y.mean()),
                "ci95": ci95, "ci90": ci90,
                "p_auto": w["auto"], "p_exact": w["exact_cond"], "p_normal": w["normal"],
                "n_nonzero": w["n_nonzero"], "has_ties": w["has_ties"], "has_zeros": w["has_zeros"],
                "all_zero": bool(np.all(d == 0)), "tiny_nonzero": int(np.sum((d != 0) & (np.abs(d) < 1e-9))),
                "direction": DIRECTION[o], "margin": camp.margin(cell, o),
                "margin_rounded": camp.margin(cell, o, rounded=True),
                "in_text": o in outs_text, "d": d.tolist(),
            })
    return recs


def apply_holm_and_classes(recs, pkey="p_auto", family_filter=None, tag="", margin_key="margin", strict=True):
    """Holm within campaign x outcome over the records selected by family_filter."""
    fam = defaultdict(list)
    for i, r in enumerate(recs):
        if family_filter is None or family_filter(r):
            fam[(r["campaign"], r["outcome"])].append(i)
        elif r["all_zero"]:
            # identical rows left out of a family are still 'identical' (p = 1, untested)
            r[f"p_holm{tag}"] = 1.0
            r[f"m_family{tag}"] = 0
            r[f"class{tag}"] = "identical"
            r[f"label{tag}"] = "identical"
    for key, idxs in fam.items():
        p = [recs[i][pkey] for i in idxs]
        adj = holm(p)
        for i, a in zip(idxs, adj):
            r = recs[i]
            r[f"p_holm{tag}"] = float(a)
            r[f"m_family{tag}"] = len(idxs)
            c = classify(np.array(r["d"]), r["ci95"], r["ci90"], a, r[margin_key], r["direction"], strict)
            r[f"class{tag}"] = c
            lab = LABEL[c]
            if c == "equivalent" and a < ALPHA:
                lab = "equivalent within margin (significant difference)"
            r[f"label{tag}"] = lab
    return recs


# --------------------------------------------------------------------------- gates
EQ = {"identical", "equivalent"}


def gates(a1, a3, a3f, camp3, camp3f, tag=""):
    ck = f"class{tag}"
    idx1 = {(r["cell"], r["hypothesis"], r["arm"], r["ref"], r["outcome"]): r for r in a1}
    idx3 = {(r["cell"], r["hypothesis"], r["arm"], r["ref"], r["outcome"]): r for r in a3}
    idx3f = {(r["cell"], r["hypothesis"], r["arm"], r["ref"], r["outcome"]): r for r in a3f}
    out = {}
    # G1: H1b classifies W and AV5 identical/equivalent in S05 and S99
    g1_detail = {}
    for s in ("S05_stolen_key", "S99_mixed"):
        for o in ("W", "AV5"):
            g1_detail[f"{s}/{o}"] = idx1[(s, "H1b", "B5-event", "PBTI", o)][ck]
    out["G1"] = {"holds": all(v in EQ for v in g1_detail.values()), "detail": g1_detail}
    # G2: settings x scenarios where H1c O1 and O2 are identical/equivalent
    ok, exc = [], []
    for x in H1C_SETTINGS:
        for s in A1_SCEN:
            c1 = idx1[(s, "H1c", f"B5-{x}", f"PBTI-R-{x}", "O1")][ck]
            c2 = idx1[(s, "H1c", f"B5-{x}", f"PBTI-R-{x}", "O2")][ck]
            (ok if (c1 in EQ and c2 in EQ) else exc).append({"setting": x, "scenario": s, "O1": c1, "O2": c2})
    out["G2"] = {"n_ok": len(ok), "n_exceptions": len(exc), "exceptions": exc}

    # G3/G4 on the joint grid
    def pbti_mean_o1(camp, cell):
        _, y, _ = camp.paired(cell, "PBTI", "PBTI", "O1")
        return float(y.mean())

    pos = [c for c in A3_GRID if pbti_mean_o1(camp3, c) > 0]
    better = [c for c in pos if idx3[(c, "H3a", "PBTI-SH", "PBTI", "O1")][ck] == "better"
              or idx3[(c, "H3a", "PBTI-SH", "PBTI", "NLX")][ck] == "better"]
    g3 = len(pos) > 0 and len(better) >= len(pos) / 2.0
    w_pos = {c: idx3[(c, "H3b", "PBTI-SH", "B5-hist", "W")][ck] for c in pos}
    w_better = {c: w_pos[c] for c in better}
    out["G3"] = {"holds": g3, "points_pbti_O1_gt0": pos,
                 "pbti_mean_O1": {c: pbti_mean_o1(camp3, c) for c in pos},
                 "points_O1_or_NLX_better": better,
                 "H3a_O1": {c: idx3[(c, "H3a", "PBTI-SH", "PBTI", "O1")][ck] for c in pos},
                 "H3a_NLX": {c: idx3[(c, "H3a", "PBTI-SH", "PBTI", "NLX")][ck] for c in pos}}
    out["G4"] = {"holds_at_points_with_O1_gt0": g3 and all(v != "worse" for v in w_pos.values()),
                 "holds_at_points_counted_better": g3 and all(v != "worse" for v in w_better.values()),
                 "W_vs_B5hist_at_O1_gt0_points": w_pos}
    # G3F/G4F on the four FG cells
    betterf = [c for c in FG_CELLS if idx3f[(c, "H3a", "PBTI-SH", "PBTI", "O1")][ck] == "better"
               or idx3f[(c, "H3a", "PBTI-SH", "PBTI", "NLX")][ck] == "better"]
    g3f = len(betterf) >= 2
    wf = {c: idx3f[(c, "H3b", "PBTI-SH", "B5-hist", "W")][ck] for c in FG_CELLS}
    out["G3F"] = {"holds": g3f, "FG_cells_O1_or_NLX_better": betterf,
                  "H3a_O1": {c: idx3f[(c, "H3a", "PBTI-SH", "PBTI", "O1")][ck] for c in FG_CELLS},
                  "H3a_NLX": {c: idx3f[(c, "H3a", "PBTI-SH", "PBTI", "NLX")][ck] for c in FG_CELLS},
                  "pbti_mean_O1": {c: pbti_mean_o1(camp3f, c) for c in FG_CELLS}}
    out["G4F"] = {"holds_at_all_FG_cells": g3f and all(v != "worse" for v in wf.values()),
                  "holds_at_cells_counted_better": g3f and all(wf[c] != "worse" for c in betterf),
                  "W_vs_B5hist_FG": wf}
    # H1a / H1b hypothesis status (not gates)
    h1a = {}
    for s in A1_SCEN:
        h1a[s] = {o: idx1[(s, "H1a", "B5-hist", "PBTI", o)][ck] for o in ("O1", "NLX", "W", "AV5")}
    out["H1a_classes"] = h1a
    out["H1a_holds"] = (all(h1a[s][o] in EQ for s in A1_SCEN for o in ("O1", "NLX"))
                        and all(h1a[s][o] == "worse" for s in ("S05_stolen_key", "S99_mixed") for o in ("W", "AV5")))
    h1b = {s: {o: idx1[(s, "H1b", "B5-event", "PBTI", o)][ck] for o in ("W", "AV5")} for s in A1_SCEN}
    out["H1b_classes"] = h1b
    out["H1b_holds"] = all(v in EQ for s in A1_SCEN for v in h1b[s].values())
    return out
