#!/usr/bin/env python3
r"""V9 analysis: corrected-minus-original comparison of every comparison family, claim gates and predictions; the E04
consistent-impersonator campaign; the split of W into delay and end-of-run loss; the E09/E10 lifecycle facts; and the
differential check of the corrected comparator.  Writes the \Y... macros and the V9 supplementary tables.

Inputs (read only):
  ORIG  historical tree (stored summaries of the frozen campaigns: results/summary, results/v4/summary)
  CORR  corrected tree after tools/v9/regenerate_analysis.sh (same files, B5/B5S rows from the corrected reruns)
  ORIG/results/v9/{raw,summary,b5c_refmodel}  V9 rows and checks; ORIG/results/v7/v7_analysis/w_decomposition
Outputs:
  GEN/v9_macros.tex, GEN/tabS_v9_*.tex          (article and Document S1)
  SUM/*.csv|json                                (Data S1 additions)
usage: python3 tools/v9/analysis_v9.py ORIG CORR GEN SUM
"""
from __future__ import annotations

import json
import math
import sys
import zlib
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

ORIG, CORR, GEN, SUM = (Path(p).resolve() for p in sys.argv[1:5])
GEN.mkdir(parents=True, exist_ok=True)
SUM.mkdir(parents=True, exist_ok=True)
V9 = ORIG / "results" / "v9"
RNG_SEED, N_BOOT = 20261104, 10_000
MARGIN = {"O1": 1.0, "O2": 72.0, "NLX": 60.0, "W": 0.6, "AV5": 0.01}
DIG = {0: "Zero", 1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six", 7: "Seven", 8: "Eight", 9: "Nine"}
MAC: dict[str, str] = {}
CELLNAME = {"S05_stolen_key": "E5", "S08_seq_reuse_bug": "E8", "S12_beyond_horizon": "E11b", "S99_mixed": "mixed"}
ARMTEX = {"PBTI": r"\sys", "PBTI-R-hist": r"\Rhist", "PBTI-R-event": r"\Rev", "B5-hist": r"\Bhist",
          "B5-event": r"\Bev", "B5c-hist": r"\Bhist", "B5c-event": r"\Bev"}


def M(name, value):
    assert name.isalpha(), name
    MAC["Y" + name] = str(value)


def fmt(x, d=1):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "--"
    s = f"{x:,.{d}f}".replace(",", "{,}")
    return "$-$" + s[1:] if s.startswith("-") else s


def fint(n):
    return f"{int(n):,}".replace(",", "{,}")


def sign(x, d=1):
    s = fmt(x, d)
    return s if s.startswith("$-$") or s == "--" or float(x) == 0 else "$+$" + s


def load(p):
    return [json.loads(l) for l in open(p) if l.strip()]


def boot_ci(d, key, level=0.95):
    d = np.asarray(d, float)
    if len(d) == 0:
        return (math.nan, math.nan)
    if np.all(d == d[0]):
        return (float(d[0]), float(d[0]))
    rng = np.random.default_rng(RNG_SEED + zlib.crc32(key.encode()))
    idx = rng.integers(0, len(d), size=(N_BOOT, len(d)))
    m = d[idx].mean(axis=1)
    a = (1 - level) / 2
    return (float(np.quantile(m, a)), float(np.quantile(m, 1 - a)))


def classify(d, outcome, key):
    """Descriptive class with the registered margins and rules (exploratory use; no family correction)."""
    d = np.asarray(d, float)
    if np.all(d == 0):
        return "identical", 1.0
    mg = MARGIN[outcome]
    lo90, hi90 = boot_ci(d, key + "|90", 0.90)
    lo95, hi95 = boot_ci(d, key, 0.95)
    nz = d[d != 0]
    p = float(wilcoxon(nz).pvalue) if len(nz) else 1.0
    if -mg < lo90 and hi90 < mg:
        return "equivalent within margin", p
    better_low = outcome != "AV5"
    if p < 0.05:
        if (hi95 < -mg) if better_low else (lo95 > mg):
            return "better beyond margin", p
        if (lo95 > mg) if better_low else (hi95 < -mg):
            return "worse beyond margin", p
        return "significant, margin unresolved", p
    return "inconclusive", p


# =========================================================================== A. registered comparison families
KEY = ["campaign", "outcome", "cell", "arm", "ref", "hypothesis"]
fam_rows, changes = [], []
for fname in ("A1_comparisons.csv", "A3_comparisons.csv", "A3F_comparisons.csv"):
    o = pd.read_csv(ORIG / "results/v4/summary" / fname)
    c = pd.read_csv(CORR / "results/v4/summary" / fname)
    m = o.merge(c, on=KEY, suffixes=("_orig", "_corr"), how="outer", indicator=True, validate="one_to_one")
    assert (m["_merge"] == "both").all(), fname
    m["b5"] = m.arm.str.startswith("B5") | m.ref.str.startswith("B5")
    m["d_mean_d"] = m.mean_d_corr - m.mean_d_orig
    m["class_changed"] = m.class_orig != m.class_corr
    m["estimate_changed"] = m.d_mean_d.abs() > 1e-12
    for _, r in m.iterrows():
        fam_rows.append({k: r[k] for k in KEY} | {
            "involves_B5": bool(r.b5), "mean_d_original": r.mean_d_orig, "mean_d_corrected": r.mean_d_corr,
            "ci95_original": r.ci95_orig, "ci95_corrected": r.ci95_corr, "p_holm_original": r.p_holm_orig,
            "p_holm_corrected": r.p_holm_corr, "class_original": r.class_orig, "class_corrected": r.class_corr,
            "class_changed": bool(r.class_changed)})
        if r.class_changed:
            changes.append(fam_rows[-1])
fam = pd.DataFrame(fam_rows)
fam.to_csv(SUM / "V9_comparisons_corrected_vs_original.csv", index=False)
n_cmp, n_b5 = len(fam), int(fam.involves_B5.sum())
n_est = int((fam.mean_d_corrected - fam.mean_d_original).abs().gt(1e-12).sum())
M("CmpN", fint(n_cmp))
M("CmpBfiveN", fint(n_b5))
M("CmpEstChanged", fint(n_est))
M("CmpClassChanged", fint(len(changes)))
M("CmpClassChangedBfive", fint(sum(1 for x in changes if x["involves_B5"])))
M("CmpClassChangedOther", fint(sum(1 for x in changes if not x["involves_B5"])))
for camp in ("A1", "A3", "A3F"):
    sub = fam[fam.campaign == camp]
    nm = {"A1": "Review", "A3": "Grid", "A3F": "Cells"}[camp]
    M(f"Cmp{nm}N", fint(len(sub)))
    M(f"Cmp{nm}ClassChanged", fint(int(sub.class_changed.sum())))
# table of class changes
L = [r"\begin{tabularx}{\linewidth}{@{}llll>{\raggedright\arraybackslash}X>{\raggedright\arraybackslash}X@{}}",
     r"\toprule", r"Stage & Outcome & Cell & Comparison & Original: mean (95\% CI), class & Corrected: mean (95\% CI), class\\",
     r"\midrule"]
SHORTCELL = {"S05_stolen_key": "E5", "S08_seq_reuse_bug": "E8", "S12_beyond_horizon": "E11b", "S99_mixed": "mixed"}


def armlab(a):
    return {"PBTI": r"\sys", "PBTI-SH": "PBTI-SH", "PBTI-SH-T30": "PBTI-SH-T30", "B5S": "B5s"}.get(
        a, a.replace("B5-hist", r"\Bhist").replace("B5-event", r"\Bev").replace("PBTI-R-hist", r"\Rhist")
        .replace("PBTI-R-event", r"\Rev").replace("B5-", "B5 ").replace("PBTI-R-", "PBTI-R "))


def cls(c):
    return {"equivalent within margin": "equivalent", "different, within margin": "significant, margin unresolved",
            "equivalent within margin (significant difference)": "equivalent (significant difference)",
            "better beyond margin": "better beyond margin", "worse beyond margin": "worse beyond margin"}.get(c, c)


def ci_txt(s):
    try:
        a, b = json.loads(s)
        return f"[{fmt(a, 3)}, {fmt(b, 3)}]"
    except Exception:  # noqa: BLE001
        return str(s)


for x in sorted(changes, key=lambda r: (r["campaign"], r["outcome"], str(r["cell"]), r["arm"])):
    cell = SHORTCELL.get(x["cell"], str(x["cell"]).replace("_", r"\_").replace("+", "+\\allowbreak{}"))
    L.append(f"{x['campaign']} & {x['outcome']} & {cell} & {armlab(x['arm'])} $-$ {armlab(x['ref'])} & "
             f"{fmt(x['mean_d_original'], 3)} {ci_txt(x['ci95_original'])}, {cls(x['class_original'])} & "
             f"{fmt(x['mean_d_corrected'], 3)} {ci_txt(x['ci95_corrected'])}, {cls(x['class_corrected'])}\\\\")
if not changes:
    L.append(r"\multicolumn{6}{@{}l}{No comparison changed its class.}\\")
L += [r"\bottomrule", r"\end{tabularx}"]
(GEN / "tabS_v9_classchanges.tex").write_text("\n".join(L) + "\n")

# =========================================================================== B. gates and registered predictions
ro = json.loads((ORIG / "results/v4/summary/v4_analysis_report.json").read_text())
rc = json.loads((CORR / "results/v4/summary/v4_analysis_report.json").read_text())
gates = {}
for grp in ("A1_gates", "A3_gates", "A3F_gates"):
    for g, v in ro[grp].items():
        if isinstance(v, dict) and "holds" in v:
            gates[g] = {"original": v["holds"], "corrected": rc[grp][g]["holds"],
                        "detail_equal": ro[grp][g] == rc[grp][g]}
        else:
            gates[g] = {"original": None, "corrected": None, "detail_equal": ro[grp][g] == rc[grp][g]}
v3o = json.loads((ORIG / "results/summary/v3_analysis_report.json").read_text())["predictions"]
v3c = json.loads((CORR / "results/summary/v3_analysis_report.json").read_text())["predictions"]
preds = {p: {"original": v3o[p]["holds"], "corrected": v3c[p]["holds"]} for p in ("P1", "P2", "P3", "P4")}
gate_changes = [g for g, v in gates.items() if v["original"] != v["corrected"]]
pred_changes = [p for p, v in preds.items() if v["original"] != v["corrected"]]
(SUM / "V9_gates_and_predictions.json").write_text(json.dumps({"gates": gates, "predictions": preds,
                                                              "gate_changes": gate_changes,
                                                              "prediction_changes": pred_changes}, indent=1))
M("GateChanges", len(gate_changes))
M("PredChanges", len(pred_changes))
M("GateChangesList", ", ".join(gate_changes) if gate_changes else "none")
M("GateDetailChanged", ", ".join(g for g, v in gates.items() if not v["detail_equal"]) or "none")

# V3 registered tests (X1) and mixed workload (X2)
x1o = pd.read_csv(ORIG / "results/summary/v3_x1_preregistered_tests.csv")
x1c = pd.read_csv(CORR / "results/summary/v3_x1_preregistered_tests.csv")
X1KEY = ["outcome", "scenario", "comp"]
assert all(k in x1o.columns for k in X1KEY) and not x1o.duplicated(X1KEY).any()
x1 = x1o.merge(x1c, on=X1KEY, suffixes=("_o", "_c"), validate="one_to_one")
assert len(x1) == len(x1o) == len(x1c)
num = [c for c in x1o.columns if c not in X1KEY and x1o[c].dtype != object]
x1_changed = sum(1 for _, r in x1.iterrows() if any(
    (not (pd.isna(r[c + "_o"]) and pd.isna(r[c + "_c"]))) and r[c + "_o"] != r[c + "_c"] for c in num))
M("XoneN", len(x1))
M("XoneChanged", x1_changed)

# =========================================================================== C. per-cell differences (B5, B5S arms)
cell_rows = []
for camp, fname in (("A0", "A0_cells.csv"), ("A1", "A1_cells.csv"), ("A3", "A3_cells.csv"), ("A3F", "A3F_cells.csv")):
    o = pd.read_csv(ORIG / "results/v4/summary" / fname)
    c = pd.read_csv(CORR / "results/v4/summary" / fname)
    m = o.merge(c, on=["campaign", "cell", "arm"], suffixes=("_o", "_c"), validate="one_to_one")
    assert len(m) == len(o) == len(c), fname
    m = m[m.arm.str.startswith("B5")]
    for _, r in m.iterrows():
        row = {"campaign": camp, "cell": r.cell, "arm": r.arm}
        for k in ("O1", "O2", "NLX", "W", "AV5", "HOLDS", "DEC", "RECP50"):
            row[k + "_original"], row[k + "_corrected"] = r[k + "_o"], r[k + "_c"]
            row[k + "_diff"] = r[k + "_c"] - r[k + "_o"]
        cell_rows.append(row)
cells = pd.DataFrame(cell_rows)
cells.to_csv(SUM / "V9_cells_corrected_minus_original.csv", index=False)
sumtab = []
for camp in ("A0", "A1", "A3", "A3F"):
    sub = cells[cells.campaign == camp]
    rr = {"campaign": camp, "cells": len(sub)}
    for k in ("O1", "O2", "NLX", "W", "AV5", "HOLDS"):
        d = sub[k + "_diff"].astype(float)
        rr[k + "_cells_changed"] = int((d.abs() > 1e-12).sum())
        rr[k + "_min"], rr[k + "_max"] = float(d.min()), float(d.max())
    sumtab.append(rr)
(SUM / "V9_cells_summary.json").write_text(json.dumps(sumtab, indent=1))
# all stages together (cells of every B5/B5S arm of the re-execution, review-schedule, grid and factorial-cell stages)
_d = {k: cells[k + "_diff"].astype(float) for k in ("O1", "O2", "NLX", "W", "AV5")}
M("CellAllN", fint(len(cells)))
M("CellAllChanged", fint(int(sum((_d[k].abs() > 1e-12) for k in _d).gt(0).sum())))
M("CellAllWMaxDrop", fmt(abs(min(0.0, _d["W"].min())), 3))
M("CellAllWMaxRise", fmt(max(0.0, _d["W"].max()), 3))
M("CellAllOTwoMaxDrop", fmt(abs(min(0.0, _d["O2"].min())), 1))
M("CellAllOTwoMaxRise", fmt(max(0.0, _d["O2"].max()), 1))
M("CellAllNLXMaxRise", fmt(max(0.0, _d["NLX"].max()), 1))
M("CellAllNLXMaxDrop", fmt(abs(min(0.0, _d["NLX"].min())), 1))
M("CellAllAVFiveMaxRise", fmt(max(0.0, _d["AV5"].max()), 4))
M("CellAllAVFiveMaxDrop", fmt(abs(min(0.0, _d["AV5"].min())), 4))
M("CellAllOOneMaxRise", fmt(max(0.0, _d["O1"].max()), 2))
M("CellAllOOneMaxDrop", fmt(abs(min(0.0, _d["O1"].min())), 2))
M("CellAllOneDirection", "yes" if (_d["W"].max() <= 1e-12 and _d["O2"].max() <= 1e-12 and _d["NLX"].min() >= -1e-12
                                    and _d["AV5"].min() >= -1e-12 and _d["O1"].min() >= -1e-12) else "no")
for rr in sumtab:
    nm = {"A0": "Reexec", "A1": "Review", "A3": "Grid", "A3F": "Cells"}[rr["campaign"]]
    for k in ("O1", "O2", "NLX", "W", "AV5"):
        M(f"Cell{nm}{k.replace('5', 'Five').replace('1', 'One').replace('2', 'Two')}Changed", rr[k + "_cells_changed"])
    M(f"Cell{nm}N", rr["cells"])
    M(f"Cell{nm}WMin", fmt(rr["W_min"], 3))
    M(f"Cell{nm}WMax", fmt(rr["W_max"], 3))
    M(f"Cell{nm}NLXMin", fmt(rr["NLX_min"], 1))
    M(f"Cell{nm}NLXMax", fmt(rr["NLX_max"], 1))
    M(f"Cell{nm}AVFiveMax", fmt(rr["AV5_max"], 4))
    M(f"Cell{nm}AVFiveMin", fmt(rr["AV5_min"], 4))


# =========================================================================== C2. run-level differences (raw rows)
sys.path.insert(0, str(ORIG / "tools" / "v9"))
import build_corrected_tree as BT  # noqa: E402
RUNLAB = {"results/raw/v3_scenarios_b5.jsonl": "Main evaluation (15 scenarios, seeds 1--20)",
          "results/raw/v3_mixed_b5.jsonl": "Mixed workload (seeds 1--20)",
          "results/raw/v3_sweep.jsonl": "Stressor sweep", "results/raw/v3_factorial.jsonl": "Sensitivity factorial",
          "results/raw/v3_replay_skab.jsonl": "SKAB replay",
          "results/v4/raw/A0_core.jsonl": "Re-execution with the tracer",
          "results/v4/raw/A1_review.jsonl": "Review-schedule evaluation (seeds 21--40)",
          "results/v4/raw/A3_selective.jsonl": "Selective-hold grid",
          "results/v4/raw/A3_factorial.jsonl": "Selective-hold factorial cells"}
run_rows = []
for rel, (fields, sysmap) in BT.PLAN.items():
    orig = {}
    for r in load(ORIG / rel):
        if "error" not in r and r.get("system") in sysmap:
            orig[(r["system"],) + BT.key(r, fields)] = r
    corr = {}
    for system, fname in sysmap.items():
        pth = V9 / "raw" / fname
        if pth.exists():
            for r in load(pth):
                if "error" not in r and r.get("system") == system:
                    corr[(system,) + BT.key(r, fields)] = r
    for system in sorted(set(sysmap)):
        ks = [k for k in orig if k[0] == system]
        rr = {"stage": RUNLAB[rel], "file": rel, "system": system, "runs": len(ks),
              "rerun": sum(1 for k in ks if k in corr)}
        def ov(r):
            out = {"O1": r["nonlegit_auth"], "O2": r["legit_missing"]}
            if "tm_reach" in r:
                out.update(NLX=r["tm_nl_rec_s"], W=r["tm_wh_rec_s"] / max(1, r["tm_reach"]), AV5=r["tm_avail_5s"])
            out["holds"] = r.get("holds", 0)
            return out
        diffs = defaultdict(list)
        changed = 0
        o1_changed = 0
        for k in ks:
            if k not in corr:
                continue
            a, b = ov(orig[k]), ov(corr[k])
            ch = False
            for f in a:
                if f in b:
                    diffs[f].append(b[f] - a[f])
                    ch |= (f != "holds" and abs(b[f] - a[f]) > 1e-12)
            changed += ch
            o1_changed += abs(b["O1"] - a["O1"]) > 1e-12
        rr["runs_outcome_changed"] = changed
        rr["runs_O1_changed"] = o1_changed
        for f, d in diffs.items():
            rr[f + "_mean_diff"] = float(np.mean(d)) if d else math.nan
            rr[f + "_min_diff"] = float(np.min(d)) if d else math.nan
            rr[f + "_max_diff"] = float(np.max(d)) if d else math.nan
        run_rows.append(rr)
runs = pd.DataFrame(run_rows)
runs.to_csv(SUM / "V9_runs_corrected_minus_original.csv", index=False)
M("RunsAll", fint(runs.runs.sum()))
M("RunsRerun", fint(runs.rerun.sum()))
M("RunsChanged", fint(runs.runs_outcome_changed.sum()))
M("RunsOOneChanged", fint(runs.runs_O1_changed.sum()))
M("RunsOOneChangedAny", "no" if all((runs.get("O1_min_diff", 0).fillna(0) == 0) & (runs.get("O1_max_diff", 0).fillna(0) == 0)) else "yes")
L = [r"\begin{tabularx}{\linewidth}{@{}>{\raggedright\arraybackslash}X lrrrrrrr@{}}", r"\toprule",
     r"Stage & Pipeline & Runs & Changed & $\Delta$O1 & $\Delta$O2 & $\Delta$NLX & $\Delta W$ (s) & $\Delta$AV5\\",
     r"\midrule"]


def rng_txt(r, f, d):
    lo, hi = r.get(f + "_min_diff"), r.get(f + "_max_diff")
    if lo is None or (isinstance(lo, float) and math.isnan(lo)):
        return "--"
    if lo == 0 and hi == 0:
        return "0"
    return f"{fmt(lo, d)} to {fmt(hi, d)}"


for _, r in runs.iterrows():
    L.append(f"{r.stage} & {'B5s' if r.system == 'B5S' else 'B5'} & {fint(r.runs)} & {fint(r.runs_outcome_changed)} & "
             f"{rng_txt(r, 'O1', 0)} & {rng_txt(r, 'O2', 0)} & {rng_txt(r, 'NLX', 1)} & {rng_txt(r, 'W', 3)} & "
             f"{rng_txt(r, 'AV5', 4)}\\\\")
L += [r"\bottomrule", r"\end{tabularx}"]
(GEN / "tabS_v9_runs.tex").write_text("\n".join(L) + "\n")

# =========================================================================== D. raw rows, invariance, differential check
rowc = json.loads((V9 / "summary" / "b5c_row_comparison.json").read_text())
tot = Counter()
for f, d in rowc["files"].items():
    for s, v in d.items():
        if isinstance(v, dict) and "rows" in v:
            tot["rows"] += v["rows"]
            tot["replaced"] += v["replaced"]
            tot["missing"] += v["missing_corrected"]
            tot["outcome_changed"] += v["rows_with_outcome_change"]
            tot["nofork"] += v["nofork_rows"]
            tot["nofork_identical"] += v["nofork_rows_identical"]
M("RowsN", fint(tot["rows"]))
M("RowsReplaced", fint(tot["replaced"]))
M("RowsMissing", fint(tot["missing"]))
M("RowsOutcomeChanged", fint(tot["outcome_changed"]))
M("RowsNofork", fint(tot["nofork"]))
M("RowsNoforkIdentical", fint(tot["nofork_identical"]))
diff = Counter()
for p in sorted((V9 / "b5c_refmodel").glob("*.jsonl")):
    for line in open(p):
        r = json.loads(line)
        diff["n"] += 1
        diff["equal"] += bool(r.get("cmp", {}).get("all_core"))
        diff["counters"] += bool(r.get("counters_match"))
        diff["hist_differs"] += not r.get("corrected_equals_historical", True)
M("RefN", fint(diff["n"]))
M("RefEqual", fint(diff["equal"]))
M("RefCounters", fint(diff["counters"]))
M("RefHistDiffers", fint(diff["hist_differs"]))
tests = sum(1 for line in open(ORIG / "tests" / "test_b5_corrected.py") if line.startswith("def test_"))
M("RegTests", tests)

# =========================================================================== E. E04 consistent impersonator
def metrics(r):
    return {"O1": r["nonlegit_auth"], "O2": r["legit_missing"], "NLX": r["tm_nl_rec_s"],
            "W": r["tm_wh_rec_s"] / max(1, r["tm_reach"]), "AV5": r["tm_avail_5s"],
            "DEC": r.get("review_decisions") or 0}


E04 = {}
for r in load(ORIG / "results/v4/raw/A1_review.jsonl"):
    if r.get("scenario") == "S99_mixed" and r["arm"] in ("PBTI", "PBTI-R-hist", "PBTI-R-event", "B5-hist", "B5-event"):
        E04[(r["arm"], "registered", r["seed"])] = metrics(r)
corr_a1 = V9 / "raw" / "A1_review_B5c.jsonl"
for r in load(corr_a1):
    if "error" not in r and r.get("scenario") == "S99_mixed" and r["arm"] in ("B5-hist", "B5-event"):
        E04[(r["arm"].replace("B5-", "B5c-"), "registered", r["seed"])] = metrics(r)
repro = []
for r in load(V9 / "raw" / "attacker_consistent_impersonator.jsonl"):
    if "error" in r:
        continue
    k = (r["label"], r["variant"], r["seed"])
    if r["variant"] == "registered":
        ref = E04.get(k)
        repro.append(ref is not None and all(abs(metrics(r)[x] - ref[x]) < 1e-9 for x in ("O1", "O2", "NLX", "W", "AV5")))
        continue
    E04[k] = metrics(r)
M("EfourReproN", len(repro))
M("EfourRunsN", fint(sum(1 for r in load(V9 / "raw" / "attacker_consistent_impersonator.jsonl") if "error" not in r)))
M("EfourReproOk", sum(repro))
LABELS = ["PBTI", "PBTI-R-hist", "PBTI-R-event", "B5c-hist", "B5c-event", "B5-hist", "B5-event"]
SEEDS = list(range(21, 41))
e04_cells, e04_cmp = [], []
for lab in LABELS:
    for var in ("registered", "consistent"):
        vals = [E04.get((lab, var, s)) for s in SEEDS]
        if any(v is None for v in vals):
            continue
        row = {"arm": lab, "attacker": var, "n": len(vals)}
        for k in ("O1", "O2", "NLX", "W", "AV5", "DEC"):
            x = [v[k] for v in vals]
            row[k] = float(np.mean(x))
            row[k + "_ci95"] = boot_ci(x, f"E04|cell|{lab}|{var}|{k}")
        e04_cells.append(row)
PAIRS = [("B5c-hist", "PBTI"), ("B5c-event", "PBTI"), ("B5c-hist", "PBTI-R-hist"), ("B5c-event", "PBTI-R-event"),
         ("PBTI-R-event", "PBTI"), ("B5-hist", "B5c-hist"), ("B5-event", "B5c-event")]
# registered attacker: where the comparison is one of the registered comparisons of the review-schedule evaluation
# (corrected tree), report that comparison (estimate, interval and registered class) instead of a second bootstrap
A1C = pd.read_csv(CORR / "results/v4/summary/A1_comparisons.csv")
A1ARM = {"B5c-hist": "B5-hist", "B5c-event": "B5-event", "PBTI-R-hist": "PBTI-R-hist", "PBTI-R-event": "PBTI-R-event",
         "PBTI": "PBTI"}


def registered_cmp(a, b, k):
    if a not in A1ARM or b not in A1ARM:
        return None
    q = A1C[(A1C.cell == "S99_mixed") & (A1C.arm == A1ARM[a]) & (A1C.ref == A1ARM[b]) & (A1C.outcome == k)]
    return q.iloc[0] if len(q) == 1 else None


for var in ("registered", "consistent"):
    for a, b in PAIRS:
        if any(E04.get((a, var, s)) is None or E04.get((b, var, s)) is None for s in SEEDS):
            continue
        for k in ("O1", "O2", "NLX", "W", "AV5"):
            d = [E04[(a, var, s)][k] - E04[(b, var, s)][k] for s in SEEDS]
            reg = registered_cmp(a, b, k) if var == "registered" else None
            if reg is not None:
                assert abs(float(reg.mean_d) - float(np.mean(d))) < 1e-9, (a, b, k)
                e04_cmp.append({"attacker": var, "arm": a, "ref": b, "outcome": k, "n": len(d),
                                "mean_d": float(reg.mean_d), "ci95": tuple(json.loads(reg.ci95)),
                                "p_wilcoxon": float(reg.p), "class": reg["class"],
                                "source": f"registered comparison {reg.hypothesis}"})
                continue
            key = f"E04|{var}|{a}|{b}|{k}"
            c, p = classify(d, k, key)
            e04_cmp.append({"attacker": var, "arm": a, "ref": b, "outcome": k, "n": len(d),
                            "mean_d": float(np.mean(d)), "ci95": boot_ci(d, key), "p_wilcoxon": p, "class": c,
                            "source": "recomputed (exploratory)"})
for lab in LABELS:                                    # attacker effect within an arm
    if any(E04.get((lab, v, s)) is None for v in ("registered", "consistent") for s in SEEDS):
        continue
    for k in ("O1", "O2", "NLX", "W", "AV5"):
        d = [E04[(lab, "consistent", s)][k] - E04[(lab, "registered", s)][k] for s in SEEDS]
        key = f"E04|attacker|{lab}|{k}"
        c, p = classify(d, k, key)
        e04_cmp.append({"attacker": "consistent minus registered", "arm": lab, "ref": lab, "outcome": k,
                        "n": len(d), "mean_d": float(np.mean(d)), "ci95": boot_ci(d, key), "p_wilcoxon": p,
                        "class": c, "source": "recomputed (exploratory)"})
pd.DataFrame(e04_cells).to_csv(SUM / "V9_attacker_cells.csv", index=False)
pd.DataFrame(e04_cmp).to_csv(SUM / "V9_attacker_comparisons.csv", index=False)
cellmap = {(r["arm"], r["attacker"]): r for r in e04_cells}
TAG = {"PBTI": "PBTI", "PBTI-R-hist": "Rhist", "PBTI-R-event": "Rev", "B5c-hist": "Bhist", "B5c-event": "Bev",
       "B5-hist": "BhistOld", "B5-event": "BevOld"}
for (lab, var), r in cellmap.items():
    v = "Con" if var == "consistent" else "Reg"
    M(f"Efour{v}{TAG[lab]}OOne", fmt(r["O1"], 1))
    M(f"Efour{v}{TAG[lab]}OTwo", fmt(r["O2"], 1))
    M(f"Efour{v}{TAG[lab]}NLX", fint(round(r["NLX"])))
    M(f"Efour{v}{TAG[lab]}W", fmt(r["W"], 2))
    M(f"Efour{v}{TAG[lab]}AVFive", fmt(r["AV5"], 3))
for r in e04_cmp:
    if r["attacker"] not in ("consistent", "registered"):
        continue
    v = "Con" if r["attacker"] == "consistent" else "Reg"
    k = r["outcome"].replace("O1", "OOne").replace("O2", "OTwo").replace("AV5", "AVFive")
    base = f"Efour{v}{TAG[r['arm']]}vs{TAG[r['ref']]}{k}"
    d = 3 if r["outcome"] in ("W", "AV5") else 1
    M(base, sign(r["mean_d"], d))
    M(base + "Lo", fmt(r["ci95"][0], d))
    M(base + "Hi", fmt(r["ci95"][1], d))
    M(base + "Class", cls(r["class"]))
for var, v in (("registered", "Reg"), ("consistent", "Con")):
    for a, b in (("B5c-hist", "PBTI"), ("B5c-event", "PBTI"), ("B5c-hist", "PBTI-R-hist"), ("B5c-event", "PBTI-R-event")):
        ra, rb = cellmap.get((a, var)), cellmap.get((b, var))
        if ra and rb and rb["NLX"]:
            M(f"Efour{v}{TAG[a]}vs{TAG[b]}NLXPct", fmt(100 * (ra["NLX"] - rb["NLX"]) / rb["NLX"], 0))
same_hist = all(cellmap.get((f"B5-{x}", var)) and cellmap.get((f"B5c-{x}", var)) and
                all(abs(cellmap[(f"B5-{x}", var)][k] - cellmap[(f"B5c-{x}", var)][k]) < 1e-9 for k in ("O1", "O2", "NLX"))
                for x in ("hist", "event") for var in ("registered", "consistent"))
M("EfourHistCorrSameFinal", "yes" if same_hist else "no")
# largest corrected-minus-historical difference of the B5 cell means in this campaign (both schedules, both attackers)
for k, nm, d in (("O1", "OOne", 1), ("O2", "OTwo", 1), ("NLX", "NLX", 1), ("W", "W", 3), ("AV5", "AVFive", 4)):
    diffs = [abs(cellmap[(f"B5c-{x}", var)][k] - cellmap[(f"B5-{x}", var)][k]) for x in ("hist", "event")
             for var in ("registered", "consistent") if cellmap.get((f"B5c-{x}", var)) and cellmap.get((f"B5-{x}", var))]
    M(f"EfourHistCorrMax{nm}", fmt(max(diffs), d) if diffs else "--")
# E04 table (Document S1)
L = [r"\begin{tabular}{@{}llrrrrr@{}}", r"\toprule",
     r"Pipeline & Attacker & O1 & O2 & NLX (record-s) & $W$ (s) & AV5\\", r"\midrule"]
for lab in LABELS:
    for var in ("registered", "consistent"):
        r = cellmap.get((lab, var))
        if r is None:
            continue
        name = {"B5c-hist": r"\Bhist", "B5c-event": r"\Bev", "B5-hist": r"\Bhist\ (historical B5)",
                "B5-event": r"\Bev\ (historical B5)"}.get(lab, ARMTEX.get(lab, lab))
        L.append(f"{name} & {var} & {fmt(r['O1'])} & {fmt(r['O2'])} & {fint(round(r['NLX']))} & {fmt(r['W'], 2)} & "
                 f"{fmt(r['AV5'], 3)}\\\\")
    if lab in ("PBTI-R-event", "B5c-event"):
        L.append(r"\midrule")
L += [r"\bottomrule", r"\end{tabular}"]
(GEN / "tabS_v9_e04_cells.tex").write_text("\n".join(L) + "\n")
L = [r"\begin{tabularx}{\linewidth}{@{}ll>{\raggedright\arraybackslash}X>{\raggedright\arraybackslash}X>{\raggedright\arraybackslash}X@{}}",
     r"\toprule", r"Comparison & Outcome & Registered attacker: mean (95\% CI) & Consistent attacker: mean (95\% CI) & Class (consistent)\\",
     r"\midrule"]
idx = {(r["attacker"], r["arm"], r["ref"], r["outcome"]): r for r in e04_cmp}
for a, b in PAIRS[:5]:
    for k in ("O1", "NLX", "W", "AV5"):
        rg, cn = idx.get(("registered", a, b, k)), idx.get(("consistent", a, b, k))
        if cn is None:
            continue
        d = 3 if k in ("W", "AV5") else 1
        rt = f"{sign(rg['mean_d'], d)} [{fmt(rg['ci95'][0], d)}, {fmt(rg['ci95'][1], d)}]" if rg else "--"
        ct = f"{sign(cn['mean_d'], d)} [{fmt(cn['ci95'][0], d)}, {fmt(cn['ci95'][1], d)}]"
        L.append(f"{ARMTEX[a]} $-$ {ARMTEX[b]} & {k} & {rt} & {ct} & {cls(cn['class'])}\\\\")
    L.append(r"\midrule")
L[-1] = r"\bottomrule"
L.append(r"\end{tabularx}")
(GEN / "tabS_v9_e04_cmp.tex").write_text("\n".join(L) + "\n")
ctl = json.loads((V9 / "raw" / "attacker_controls.json").read_text())
L = [r"\begin{tabularx}{\linewidth}{@{}>{\raggedright\arraybackslash}X lrrrr@{}}", r"\toprule",
     r"Trace & Pipeline & \makecell[r]{Forged authoritative\\at end} & \makecell[r]{Forged exposure\\(record-s)} & "
     r"\makecell[r]{Genuine authoritative\\at end} & \makecell[r]{Genuine withheld\\(record-s)}\\",
     r"\midrule"]
TR = {"T1_contradiction_admitted": "T1 forged version, contradicting successor admitted",
      "T2_contradiction_absent": "T2 forged version, successors suppressed",
      "T3_consistent_takeover": "T3 consistent takeover of the rest of the feed",
      "T4_fresh_identities": "T4 forgeries at identities the device does not use",
      "T5_fresh_identities_later_contradicted": "T5 as T4, the device later reaches them",
      "T6_epoch_advance": "T6 forged epoch advance (drain 20 s)"}
last = None
for r in ctl["rows"]:
    name = TR[r["trace"]] if r["trace"] != last else ""
    if last is not None and r["trace"] != last:
        L.append(r"\addlinespace")
    last = r["trace"]
    pipe = {"B5": "B5 (historical)", "B5c": "B5 (corrected)", "PBTI": r"\sys", "PBTI-R": "PBTI-R"}[r["pipeline"]]
    L.append(f"{name} & {pipe} & {r['forged_authoritative_end']}/{r['forged_admitted_arrivals']} & "
             f"{fmt(r['forged_exposure_record_s'])} & {r['genuine_authoritative_end']}/{r['genuine_arrived']} & "
             f"{fmt(r['genuine_withheld_record_s'])}\\\\")
L += [r"\bottomrule", r"\end{tabularx}"]
(GEN / "tabS_v9_e04_controls.tex").write_text("\n".join(L) + "\n")

# =========================================================================== F. W split (delay vs end-of-run loss)
wd = defaultdict(dict)        # (campaign, cell, arm) -> seed -> (W, delay, loss)
for r in load(ORIG / "results/v7/v7_analysis/w_decomposition/all.jsonl"):
    if r["arm"].startswith("B5"):
        wd[(r["campaign"], r["cell"], r["arm"] + " (historical)")][r["seed"]] = (r["W"], r["W_delay"], r["W_loss"])
    else:
        wd[(r["campaign"], r["cell"], r["arm"])][r["seed"]] = (r["W"], r["W_delay"], r["W_loss"])
w_ok = True
for camp, fname, cellkey in (("A1_review", "A1_review_B5c.jsonl", "scenario"), ("A3_factorial", "A3_factorial_B5c.jsonl", "point")):
    p = V9 / "raw" / fname
    if not p.exists():
        continue
    for r in load(p):
        if "error" in r or r.get("system") != "B5" or "wd_delay_ms" not in r:
            continue
        cell = r.get(cellkey) if camp == "A1_review" else r.get("point")
        if camp == "A1_review" and cell not in ("S05_stolen_key", "S99_mixed"):
            continue
        if camp == "A3_factorial" and cell not in ("run3", "run4", "run8", "run15"):
            continue
        n = r["wd_reach"]
        W = r["tm_wh_rec_s"] / r["tm_reach"]
        w_ok &= (r["wd_delay_ms"] + r["wd_loss_ms"] == round(r["tm_wh_rec_s"] * 1000)) and n == r["tm_reach"]
        wd[(camp, cell, r["arm"])][r["seed"]] = (W, r["wd_delay_ms"] / 1000 / n, r["wd_loss_ms"] / 1000 / n)
split_rows = []
for (camp, cell, arm), by in sorted(wd.items()):
    if len(by) != 20:
        continue
    W = np.mean([v[0] for v in by.values()])
    D = np.mean([v[1] for v in by.values()])
    Lo = np.mean([v[2] for v in by.values()])
    split_rows.append({"campaign": camp, "cell": cell, "arm": arm, "n": len(by), "W": W, "W_delay": D, "W_loss": Lo,
                       "loss_share": Lo / W if W else math.nan})
split = pd.DataFrame(split_rows)
split.to_csv(SUM / "V9_W_split.csv", index=False)
M("WsplitSumOk", "yes" if w_ok else "no")


def sp(camp, cell, arm, k):
    s = split[(split.campaign == camp) & (split.cell == cell) & (split.arm == arm)]
    return float(s[k].iloc[0]) if len(s) else math.nan


for cell, nm in (("S05_stolen_key", "Efive"), ("S99_mixed", "Mixed")):
    for arm, t in (("PBTI", "PBTI"), ("B5-hist", "Bhist"), ("B5-event", "Bev"), ("PBTI-R-event", "Rev")):
        for k, kk in (("W", "W"), ("W_delay", "Delay"), ("W_loss", "Loss")):
            M(f"Wd{nm}{t}{kk}", fmt(sp("A1_review", cell, arm, k), 2))
        M(f"Wd{nm}{t}LossPct", fmt(100 * sp("A1_review", cell, arm, "loss_share"), 1))
FGC = ("run3", "run4", "run8", "run15")
for arm, t in (("PBTI-SH", "SH"), ("B5-hist", "Bhist"), ("PBTI", "PBTI")):
    sh = [100 * sp("A3_factorial", c, arm, "loss_share") for c in FGC]
    if not any(math.isnan(x) for x in sh):
        M(f"WdFG{t}LossPctMin", fmt(min(sh), 0))
        M(f"WdFG{t}LossPctMax", fmt(max(sh), 0))
L = [r"\begin{tabular}{@{}llrrrr@{}}", r"\toprule",
     r"Workload & Pipeline & $W$ (s) & Delay (s) & End-of-run loss (s) & Loss share\\", r"\midrule"]
NAMES = {"S05_stolen_key": "E5 stolen keys", "S99_mixed": "Mixed workload", "run3": "Cell run3", "run4": "Cell run4",
         "run8": "Cell run8", "run15": "Cell run15"}
for camp, cells_ in (("A1_review", ("S05_stolen_key", "S99_mixed")), ("A3_factorial", FGC)):
    for cell in cells_:
        first = True
        for arm in ("PBTI", "PBTI-R-event", "PBTI-SH", "B5-hist", "B5-event"):
            s = split[(split.campaign == camp) & (split.cell == cell) & (split.arm == arm)]
            if not len(s):
                continue
            r = s.iloc[0]
            L.append(f"{NAMES[cell] if first else ''} & {ARMTEX.get(arm, arm)} & {fmt(r.W, 2)} & {fmt(r.W_delay, 2)} & "
                     f"{fmt(r.W_loss, 2)} & {fmt(100 * r.loss_share, 1)}\\%\\\\")
            first = False
        L.append(r"\addlinespace")
L[-1] = r"\bottomrule"
L.append(r"\end{tabular}")
(GEN / "tabS_v9_wsplit.tex").write_text("\n".join(L) + "\n")

# =========================================================================== G. E09 / E10
a5 = json.loads((V9 / "summary" / "a5_e09_e10.json").read_text())
e09 = a5["e09_superseded_snapshot"]
ok09 = all(x["first_decision"] == "STALE_REVIEW" and x["state_after_first_decision"] == "QUARANTINED"
           and x["case_state_end"] == "RELEASED" and [y["outcome"] for y in x["review_records"]] == ["STALE_REVIEW", "RELEASED"]
           for x in e09)
M("EnineConfirmed", "yes" if ok09 else "no")
M("EnineRefusedAt", fmt(e09[0]["review_records"][0]["t_ms"] / 1000, 1))
M("EnineFreshAt", fmt(e09[0]["review_records"][1]["t_ms"] / 1000, 0))
rec = sorted({x["width_s"] for x in a5["e10_widths"] if x["genuine_recovered"]})
wh = sorted({x["width_s"] for x in a5["e10_widths"] if x["genuine_withheld"]})
both = lambda v: " and ".join(f"{w:g}" for w in v)  # noqa: E731
M("EtenRecovered", both(rec))
M("EtenWithheld", both(wh))
M("AfiveRegenerated", "yes" if a5["a5_regenerated_equals_stored"] else "no")
M("AfiveCorrectedDiffs", len(a5["corrected_b5_differences"]))

# =========================================================================== write
(GEN / "v9_macros.tex").write_text("% AUTO-GENERATED by tools/v9/analysis_v9.py -- do not edit by hand\n" +
                                   "".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in sorted(MAC.items())))
(SUM / "V9_macros.json").write_text(json.dumps(MAC, indent=1, sort_keys=True))
print(f"{len(MAC)} V9 macros; comparisons {n_cmp} (B5: {n_b5}), estimates changed {n_est}, class changes {len(changes)}, "
      f"gate changes {gate_changes}, prediction changes {pred_changes}; E04 cells {len(e04_cells)}; W split rows {len(split)}")
