#!/usr/bin/env python3
"""Run the independent recomputation and the row-by-row diff against the reported tables.

Outputs (all under /home/claude/PBTI_v7/results/stats_audit/):
  recomputed_{A1,A3,A3F}.csv      my comparison tables (primary variant + sensitivity columns)
  recomputed_A3S_vs_A0_PBTI.csv   descriptive control table
  diff_{A1,A3,A3F,A3S}.csv        row-by-row diff with the reported CSVs
  gates_recomputed.json           gate verdicts per variant
  recompute_summary.json          counts of matches/mismatches by file and tolerance used
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prereg_stats as ps  # noqa: E402

OUT = "/home/claude/PBTI_v7/results/stats_audit"
SUM = ps.REPO + "/results/v4/summary"
os.makedirs(OUT, exist_ok=True)

Z_MC = 4.0  # Monte-Carlo band half-width in binomial SDs for bootstrap quantile positions


def mc_band(means_sorted, q, b=ps.B, z=Z_MC):
    """Range of bootstrap-quantile estimates compatible with Monte-Carlo error.

    np.percentile(linear) puts quantile q at position (b-1)q of the sorted resample means. A
    different, equally valid resampling stream moves the empirical quantile by about
    sqrt(b q (1-q)) order-statistic positions; we accept reported bounds within +/- z of those."""
    # both the reported bound and mine carry independent Monte-Carlo error -> sqrt(2)
    sd = math.sqrt(2.0) * math.sqrt(b * q * (1 - q))
    pos = (b - 1) * q
    lo = int(max(0, math.floor(pos - z * sd)))
    hi = int(min(b - 1, math.ceil(pos + z * sd)))
    return float(means_sorted[lo]), float(means_sorted[hi])


def parse_ci(s):
    s = str(s).strip().strip("[]")
    a, b = s.split(",")
    return float(a), float(b)


def read_csv(path):
    with open(path) as fh:
        return list(csv.DictReader(fh))


def fmt(x):
    if isinstance(x, float):
        return repr(x)
    return x


def build(camp, label, specs, all_outcomes_for):
    recs = ps.compute_rows(camp, label, specs, all_outcomes_for)
    # attach MC bands for each bound (recompute the resample means once more per record)
    for r in recs:
        d = np.array(r["d"])
        _, _, means = ps.bootstrap_cis(d)
        ms = np.sort(means)
        r["band95_lo"] = mc_band(ms, 0.025)
        r["band95_hi"] = mc_band(ms, 0.975)
        r["band90_lo"] = mc_band(ms, 0.05)
        r["band90_hi"] = mc_band(ms, 0.95)
    return recs


def variants(recs):
    """Primary + sensitivity analyses. Primary = family as reported (all computed rows),
    p = scipy-default-like 'auto' Wilcoxon, O2 margin unrounded, strict inequalities."""
    ps.apply_holm_and_classes(recs, "p_auto", None, "")
    ps.apply_holm_and_classes(recs, "p_auto", lambda r: r["in_text"], "_text")
    ps.apply_holm_and_classes(recs, "p_exact", None, "_exact")
    ps.apply_holm_and_classes(recs, "p_normal", None, "_normal")
    ps.apply_holm_and_classes(recs, "p_auto", lambda r: not r["all_zero"], "_noident")
    ps.apply_holm_and_classes(recs, "p_auto", None, "_mround", margin_key="margin_rounded")
    ps.apply_holm_and_classes(recs, "p_auto", None, "_nonstrict", strict=False)
    return recs


TAGS = ["", "_text", "_exact", "_normal", "_noident", "_mround", "_nonstrict"]


def write_recomputed(recs, path):
    cols = ["campaign", "outcome", "cell", "arm", "ref", "hypothesis", "in_text", "n", "mean_d", "mean_arm",
            "mean_ref", "ci95_lo", "ci95_hi", "ci90_lo", "ci90_hi", "p_auto", "p_exact", "p_normal", "n_nonzero",
            "has_ties", "has_zeros", "direction", "margin", "margin_rounded"]
    for t in TAGS:
        cols += [f"p_holm{t}", f"m_family{t}", f"class{t}"]
    cols += ["label"]
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for r in recs:
            row = []
            for c in cols:
                if c == "ci95_lo":
                    v = r["ci95"][0]
                elif c == "ci95_hi":
                    v = r["ci95"][1]
                elif c == "ci90_lo":
                    v = r["ci90"][0]
                elif c == "ci90_hi":
                    v = r["ci90"][1]
                else:
                    v = r.get(c, "")
                row.append(fmt(v))
            w.writerow(row)


def close(a, b, rel=1e-9, abs_=1e-9):
    return abs(a - b) <= max(abs_, rel * max(abs(a), abs(b)))


def diff_table(recs, reported_path, path, campaign):
    rep = read_csv(reported_path)
    mine = {(r["outcome"], r["cell"], r["arm"], r["ref"], r["hypothesis"]): r for r in recs}
    seen = set()
    out = []
    counts = {"reported_rows": len(rep), "matched_keys": 0, "missing_in_mine": 0,
              "n": 0, "mean_d": 0, "mean_arm": 0, "mean_ref": 0, "margin": 0, "direction": 0,
              "ci_exact": 0, "ci_within_MC_band": 0, "ci_outside_MC_band": 0,
              "p_match_auto": 0, "p_match_exact": 0, "p_match_normal": 0, "p_match_none": 0,
              "p_holm_match": 0, "m_family_match": 0, "class_match": 0, "label_match": 0,
              "sig_match": 0, "class_mismatch": 0}
    for row in rep:
        key = (row["outcome"], row["cell"], row["arm"], row["ref"], row["hypothesis"])
        r = mine.get(key)
        if r is None:
            counts["missing_in_mine"] += 1
            out.append({"key": "|".join(key), "status": "MISSING_IN_RECOMPUTATION"})
            continue
        seen.add(key)
        counts["matched_keys"] += 1
        c95, c90 = parse_ci(row["ci95"]), parse_ci(row["ci90"])
        rp, rph = float(row["p"]), float(row["p_holm"])
        e = {"key": "|".join(key)}
        e["n_rep"], e["n_mine"] = int(row["n"]), r["n"]
        counts["n"] += e["n_rep"] == e["n_mine"]
        for f in ("mean_d", "mean_arm", "mean_ref", "margin"):
            e[f + "_rep"], e[f + "_mine"] = float(row[f]), r[f]
            counts[f] += close(float(row[f]), r[f])
        counts["direction"] += row["direction"] == r["direction"]
        # CI comparison
        bounds = [("ci95_lo", c95[0], r["ci95"][0], r["band95_lo"]), ("ci95_hi", c95[1], r["ci95"][1], r["band95_hi"]),
                  ("ci90_lo", c90[0], r["ci90"][0], r["band90_lo"]), ("ci90_hi", c90[1], r["ci90"][1], r["band90_hi"])]
        exact_all, band_all = True, True
        maxdiff, maxrel = 0.0, 0.0
        width = max(r["ci95"][1] - r["ci95"][0], 0.0)
        for name, rv, mv, band in bounds:
            e[name + "_rep"], e[name + "_mine"] = rv, mv
            ex = close(rv, mv, rel=1e-9, abs_=1e-9)
            inb = (band[0] - 1e-9 * max(1, abs(band[0]))) <= rv <= (band[1] + 1e-9 * max(1, abs(band[1])))
            exact_all &= ex
            band_all &= (ex or inb)
            maxdiff = max(maxdiff, abs(rv - mv))
            if width > 0:
                maxrel = max(maxrel, abs(rv - mv) / width)
        e["ci_max_absdiff"], e["ci_max_diff_over_width95"] = maxdiff, maxrel
        e["ci_status"] = "exact" if exact_all else ("within_MC_band" if band_all else "OUTSIDE_MC_band")
        counts["ci_exact"] += exact_all
        counts["ci_within_MC_band"] += (band_all and not exact_all)
        counts["ci_outside_MC_band"] += (not band_all)
        # p comparison
        e["p_rep"], e["p_auto"], e["p_exact"], e["p_normal"] = rp, r["p_auto"], r["p_exact"], r["p_normal"]
        pm = [nm for nm in ("auto", "exact", "normal") if close(rp, r["p_" + nm], rel=1e-7, abs_=1e-12)]
        e["p_matches"] = "+".join(pm) if pm else "NONE"
        for nm in ("auto", "exact", "normal"):
            counts["p_match_" + nm] += nm in pm
        counts["p_match_none"] += not pm
        e["p_holm_rep"], e["p_holm_mine"] = rph, r["p_holm"]
        counts["p_holm_match"] += close(rph, r["p_holm"], rel=1e-7, abs_=1e-12)
        e["m_family_rep"], e["m_family_mine"] = int(row["m_family"]), r["m_family"]
        counts["m_family_match"] += int(row["m_family"]) == r["m_family"]
        e["sig_rep"], e["sig_mine"] = rph < ps.ALPHA, r["p_holm"] < ps.ALPHA
        counts["sig_match"] += e["sig_rep"] == e["sig_mine"]
        e["class_rep"], e["label_rep"] = ps.base_class_of_label(row["class"]), row["class"]
        e["class_mine"], e["label_mine"] = r["class"], r["label"]
        counts["class_match"] += e["class_rep"] == e["class_mine"]
        counts["class_mismatch"] += e["class_rep"] != e["class_mine"]
        counts["label_match"] += e["label_rep"] == e["label_mine"]
        for t in TAGS[1:]:
            e["class" + t] = r.get("class" + t, "")
        e["status"] = "OK" if (e["class_rep"] == e["class_mine"] and e["sig_rep"] == e["sig_mine"]
                               and e["n_rep"] == e["n_mine"] and close(e["mean_d_rep"], e["mean_d_mine"])
                               and e["ci_status"] != "OUTSIDE_MC_band"
                               and close(e["margin_rep"], e["margin_mine"])) else "MISMATCH"
        out.append(e)
    extra = [k for k in mine if k not in seen]
    counts["recomputed_rows"] = len(recs)
    counts["recomputed_not_in_report"] = len(extra)
    counts["status_OK"] = sum(1 for e in out if e.get("status") == "OK")
    counts["status_MISMATCH"] = sum(1 for e in out if e.get("status") == "MISMATCH")
    cols = []
    for e in out:
        for k in e:
            if k not in cols:
                cols.append(k)
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for e in out:
            w.writerow({k: fmt(v) for k, v in e.items()})
    return counts, extra


def a3s_table(a0, a3s):
    """Descriptive control: PBTI (A0, seeds 1-20) vs PBTI-SH (A3_scenarios, seeds 1-20)."""
    rep = read_csv(SUM + "/A3S_vs_A0_PBTI.csv")
    scen = [r["scenario"] for r in rep]
    rows, diffs = [], []
    n_cmp = n_ok = 0
    for s in scen:
        rec = {"scenario": s}
        for o in ("O1", "O2", "W", "AV5", "NLX"):
            pb = [ps.outcome_value(a0.by[(s, "PBTI", k)], o) for k in range(1, 21)]
            sh = [ps.outcome_value(a3s.by[(s, "PBTI-SH", k)], o) for k in range(1, 21)]
            rec[f"PBTI_{o}"] = float(np.mean(pb))
            rec[f"SH_{o}"] = float(np.mean(sh))
            dd = np.array(sh) - np.array(pb)
            rec[f"d_{o}_mean"] = float(dd.mean())
            rec[f"d_{o}_n_increase"] = int(np.sum(dd > 0))
            rec[f"d_{o}_n_decrease"] = int(np.sum(dd < 0))
        rows.append(rec)
    for rr in rep:
        mine = next(x for x in rows if x["scenario"] == rr["scenario"])
        for k, v in rr.items():
            if k == "scenario":
                continue
            n_cmp += 1
            ok = close(float(v), mine[k], rel=1e-9, abs_=1e-9)
            n_ok += ok
            diffs.append({"scenario": rr["scenario"], "field": k, "reported": float(v), "mine": mine[k],
                          "status": "OK" if ok else "MISMATCH"})
    with open(OUT + "/recomputed_A3S_vs_A0_PBTI.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow({k: fmt(v) for k, v in r.items()})
    with open(OUT + "/diff_A3S.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(diffs[0].keys()))
        w.writeheader()
        for r in diffs:
            w.writerow({k: fmt(v) for k, v in r.items()})
    # T30 descriptive (4 scenarios)
    t30 = {}
    for s in sorted({k[0] for k in a3s.by if k[1] == "PBTI-SH-T30"}):
        t30[s] = {o: float(np.mean([ps.outcome_value(a3s.by[(s, "PBTI-SH-T30", k)], o) for k in range(1, 21)]))
                  for o in ("O1", "O2", "W", "AV5", "NLX")}
    return {"fields_compared": n_cmp, "fields_match": n_ok, "rows": rows, "t30_means": t30}


def main():
    a0 = ps.Campaign(ps.load_jsonl("A0_core.jsonl"))
    a1 = ps.Campaign(ps.load_jsonl("A1_review.jsonl"))
    a3 = ps.Campaign(ps.load_jsonl("A3_selective.jsonl"))
    a3f = ps.Campaign(ps.load_jsonl("A3_factorial.jsonl"))
    a3s = ps.Campaign(ps.load_jsonl("A3_scenarios.jsonl"))
    errors = {k: len(c.errors) for k, c in (("A0", a0), ("A1", a1), ("A3", a3), ("A3F", a3f), ("A3S", a3s))}

    r1 = variants(build(a1, "A1", ps.a1_specs(), all_outcomes_for={"H1a", "H1b"}))
    r3 = variants(build(a3, "A3", ps.a3_specs(ps.A3_GRID), None))
    r3f = variants(build(a3f, "A3F", ps.a3_specs(ps.A3F_CELLS), None))

    write_recomputed(r1, OUT + "/recomputed_A1.csv")
    write_recomputed(r3, OUT + "/recomputed_A3.csv")
    write_recomputed(r3f, OUT + "/recomputed_A3F.csv")

    summary = {"error_rows_excluded": errors, "bootstrap": {"B": ps.B, "seed": ps.SEED,
               "scheme": "numpy default_rng(seed) re-created per comparison; integers(0,n,(B,n)); "
                         "np.percentile linear; 90% and 95% from the same resamples"},
               "tolerance": {"means_margins": "rel 1e-9 / abs 1e-9",
                             "ci_bounds": f"exact (1e-9) or within the Monte-Carlo band: sorted resample means at "
                                          f"positions (B-1)q +/- {Z_MC}*sqrt(2)*sqrt(Bq(1-q)) of my bootstrap distribution (z=4 for the difference of two independent B=10,000 estimates)",
                             "p_values": "rel 1e-7 / abs 1e-12"}}
    extras = {}
    for lab, recs, rep in (("A1", r1, "A1_comparisons.csv"), ("A3", r3, "A3_comparisons.csv"),
                           ("A3F", r3f, "A3F_comparisons.csv")):
        c, extra = diff_table(recs, SUM + "/" + rep, OUT + f"/diff_{lab}.csv", lab)
        summary[lab] = c
        extras[lab] = ["|".join(k) for k in extra]
    summary["recomputed_not_in_report"] = extras
    summary["A3S"] = {k: v for k, v in a3s_table(a0, a3s).items() if k != "rows"}

    # class agreement of every sensitivity variant with the primary
    sens = {}
    for lab, recs in (("A1", r1), ("A3", r3), ("A3F", r3f)):
        sens[lab] = {}
        for t in TAGS[1:]:
            changed = [f'{r["hypothesis"]}|{r["cell"]}|{r["arm"]}-{r["ref"]}|{r["outcome"]}: {r["class"]} -> {r["class" + t]}'
                       for r in recs if ("class" + t) in r and r["class" + t] != r["class"]]
            sigchg = [f'{r["hypothesis"]}|{r["cell"]}|{r["arm"]}-{r["ref"]}|{r["outcome"]}: p_holm {r["p_holm"]:.4g} -> {r["p_holm" + t]:.4g}'
                      for r in recs if ("p_holm" + t) in r and ((r["p_holm"] < .05) != (r["p_holm" + t] < .05))]
            sens[lab][t] = {"n_rows_in_variant": sum(1 for r in recs if ("class" + t) in r),
                            "class_changes": changed, "significance_changes": sigchg}
    summary["sensitivity"] = sens

    g = {}
    for t in TAGS:
        # text-family variant only defines classes for in_text rows; gates use in-text rows only
        g[t or "primary"] = ps.gates(r1, r3, r3f, a3, a3f, t)
    with open(OUT + "/gates_recomputed.json", "w") as fh:
        json.dump(g, fh, indent=1)
    with open(OUT + "/recompute_summary.json", "w") as fh:
        json.dump(summary, fh, indent=1)
    print(json.dumps({k: v for k, v in summary.items() if k not in ("sensitivity",)}, indent=1)[:6000])
    for lab in sens:
        for t, v in sens[lab].items():
            print(lab, t, "rows", v["n_rows_in_variant"], "class changes", len(v["class_changes"]),
                  "sig changes", len(v["significance_changes"]))


if __name__ == "__main__":
    main()
