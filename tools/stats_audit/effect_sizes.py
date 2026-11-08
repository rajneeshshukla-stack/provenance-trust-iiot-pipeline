#!/usr/bin/env python3
"""STEP 6: effect sizes for the confirmatory comparisons discussed in the manuscript.

Selection: A1 = every preregistered comparison (H1a, H1b, H1c matched review, H1d) with gate roles G1/G2 marked;
A3 = the comparisons that decide G3/G4 (H3a O1 and NLX, and H3b PBTI-SH vs B5-hist W, at the joint-grid points
where PBTI's mean O1 > 0); A3F = the G3F/G4F comparisons at the four FG cells plus the FG-cell comparisons the text
and Table S30 discuss (H3a W, O2, AV5; H3b vs B5-hist O2; H3b vs B5-event W and NLX).

Values: means and paired mean differences are recomputed from the raw rows by the audit's code; 'ci95_*' are the
reported (manuscript) bounds, which the audit reproduces exactly with the analysis' seeding rule; 'audit_ci95_*' are
the audit's own bounds (fresh default_rng(20261104) per comparison). Writes results/stats_audit/effect_sizes.csv
and effect_sizes_README.md.
"""
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prereg_stats as ps  # noqa: E402
import run_audit as ra  # noqa: E402

OUT = ra.OUT
UNIT = {"O1": "observations/run", "O2": "observations/run", "NLX": "record-s/run", "W": "s/observation",
        "AV5": "fraction"}


def load(lab):
    mine = {(r["outcome"], r["cell"], r["arm"], r["ref"]): r for r in ra.read_csv(f"{OUT}/recomputed_{lab}.csv")}
    rep = {(r["outcome"], r["cell"], r["arm"], r["ref"]): r
           for r in ra.read_csv(f"{ps.REPO}/results/v4/summary/{lab}_comparisons.csv")}
    return mine, rep


def main():
    frag = {(r["campaign"], r["outcome"], r["cell"], r["arm"], r["ref"]): r for r in ra.read_csv(f"{OUT}/class_fragility.csv")}
    gates = json.load(open(f"{OUT}/gates_recomputed.json"))["primary"]
    sel = []
    m1, r1 = load("A1")
    for k, r in m1.items():
        o, cell, arm, ref = k
        role = ""
        if r["hypothesis"] == "H1b" and o in ("W", "AV5") and cell in ("S05_stolen_key", "S99_mixed"):
            role = "G1"
        if r["hypothesis"] == "H1c" and o in ("O1", "O2"):
            role = "G2"
        sel.append(("A1", k, role, r, r1[k]))
    m3, r3 = load("A3")
    for p in gates["G3"]["points_pbti_O1_gt0"]:
        for o, ref, role in (("O1", "PBTI", "G3"), ("NLX", "PBTI", "G3"), ("W", "B5-hist", "G4")):
            k = (o, p, "PBTI-SH", ref)
            sel.append(("A3", k, role, m3[k], r3[k]))
    mf, rf = load("A3F")
    for c in ps.FG_CELLS:
        for o, ref, role in (("O1", "PBTI", "G3F"), ("NLX", "PBTI", "G3F"), ("W", "B5-hist", "G4F"),
                             ("W", "PBTI", "text/Table S30"), ("O2", "PBTI", "text/Table S30"),
                             ("AV5", "PBTI", "text/Table S30"), ("O2", "B5-hist", "text/Table S30"),
                             ("W", "B5-event", "text"), ("NLX", "B5-event", "text")):
            k = (o, c, "PBTI-SH", ref)
            sel.append(("A3F", k, role, mf[k], rf[k]))
    rows = []
    for camp, (o, cell, arm, ref), role, m, rep in sel:
        mean_ref = float(m["mean_ref"])
        md = float(m["mean_d"])
        c95 = ra.parse_ci(rep["ci95"])
        note = []
        fr = frag.get((camp, o, cell, arm, ref))
        if fr and fr["fragile"] == "True":
            note.append(f"MC-fragile class ({fr['class_probs']} at B=10,000); ideal-bootstrap class {fr['ideal_class']}")
        base_rep = ps.base_class_of_label(rep["class"])
        if base_rep == "different" and abs(md) > float(m["margin"]):
            note.append("point estimate beyond the margin; 95% CI touches/overlaps it")
        if m.get("class_nonstrict") and m["class_nonstrict"] != m["class"]:
            note.append(f"audit 95% CI [{float(m['ci95_lo']):.4g}, {float(m['ci95_hi']):.4g}] ends exactly at the margin "
                        f"(reported [{c95[0]:.4g}, {c95[1]:.4g}]); '{m['class_nonstrict']}' only under a non-strict reading "
                        f"of 'entirely beyond', '{m['class']}' under the strict reading used by the analysis")
        if m.get("class_exact") and m["class_exact"] != m["class"]:
            note.append(f"with exact Wilcoxon p: '{m['class_exact']}'")
        rows.append({
            "family": f"{camp} x {o}", "campaign": camp, "hypothesis": m["hypothesis"], "gate_role": role,
            "comparison": f"{arm} - {ref}", "arm": arm, "reference": ref, "outcome": o, "unit": UNIT[o],
            "design_point": cell, "n_seeds": m["n"],
            "mean_arm": float(m["mean_arm"]), "mean_ref": mean_ref,
            "mean_diff": md, "ci95_lo": c95[0], "ci95_hi": c95[1],
            "audit_ci95_lo": float(m["ci95_lo"]), "audit_ci95_hi": float(m["ci95_hi"]),
            "rel_diff": (md / mean_ref) if mean_ref != 0 else "NA",
            "margin": float(m["margin"]), "direction_preferred": m["direction"],
            "p_holm": float(rep["p_holm"]), "m_family": int(rep["m_family"]),
            "class_reported": rep["class"], "class_audit": m["class"], "class_note": "; ".join(note),
        })
    cols = list(rows[0].keys())
    with open(f"{OUT}/effect_sizes.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: (repr(v) if isinstance(v, float) else v) for k, v in r.items()})
    print(len(rows), "rows written;", sum(1 for r in rows if r["class_note"]), "with notes")
    readme = """# effect_sizes.csv: column definitions

One row per confirmatory paired comparison discussed in the manuscript (V4: A1 all preregistered comparisons; A3
joint-grid comparisons deciding gates G3/G4; A3F factorial-cell comparisons deciding G3F/G4F plus those discussed
in the text and Table S30). Paired by seed (seeds 21-40, n = 20 runs per arm); the run is the unit.

| column | definition |
|---|---|
| family | Holm family: campaign x outcome (A1, A3, A3F) |
| campaign | A1 (matched review), A3 (selective holds, joint grid), A3F (amendment 1 factorial cells) |
| hypothesis | preregistered hypothesis (H1a-H1d, H3a-H3c) |
| gate_role | gate the row decides (G1, G2, G3, G4, G3F, G4F) or 'text' / 'text/Table S30' when only discussed |
| comparison | arm - reference (sign convention of every difference) |
| arm, reference | pipeline arms |
| outcome, unit | O1, O2 (observations per run), NLX (record-seconds per run), W (seconds per observation), AV5 (fraction) |
| design_point | scenario (A1: S05 = E5, S08 = E8, S12 = E11b, S99 = mixed) or grid point / factorial cell |
| n_seeds | number of paired seeds |
| mean_arm, mean_ref | mean of the outcome over seeds for the arm and the reference |
| mean_diff | mean paired difference (arm - reference), absolute units |
| ci95_lo, ci95_hi | 95 % percentile bootstrap CI of mean_diff as reported in results/v4/summary (10,000 resamples; seeded with [20261104, CRC32(comparison key)]); reproduced bit-for-bit by the audit |
| audit_ci95_lo, audit_ci95_hi | the audit's independent 95 % CI (fresh numpy default_rng(20261104) per comparison); differs from ci95 only by Monte-Carlo error |
| rel_diff | mean_diff / mean_ref (relative to the comparator mean); NA if mean_ref = 0 |
| margin | preregistered practical margin (O1 1; O2 1 % of the cell's median reachable count: 72 or 71.95 in A1, 28.8 in A3/A3F; NLX 60; W 0.6; AV5 0.01) |
| direction_preferred | 'lower' or 'higher' is better for the outcome; 'better'/'worse' classes refer to the arm |
| p_holm | Holm-adjusted two-sided Wilcoxon signed-rank p (scipy default: exact without ties/zeros, else normal approximation), within the family |
| m_family | number of comparisons in the Holm family |
| class_reported | class in results/v4/summary/*_comparisons.csv (as used by the manuscript) |
| class_audit | class from the audit's independent implementation (base class: identical, equivalent, better, worse, different = 'different, within margin', inconclusive) |
| class_note | robustness notes: Monte-Carlo-fragile class; point estimate beyond the margin although classed 'different, within margin'; CI bound exactly at the margin; class under exact Wilcoxon p |
"""
    open(f"{OUT}/effect_sizes_README.md", "w").write(readme)


if __name__ == "__main__":
    main()
