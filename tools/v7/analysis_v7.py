#!/usr/bin/env python3
r"""V7 analysis: compact primary-results table, effect-size table, deployment numbers and re-execution summary.

Reads only stored results (never writes into them):
  REPO/results/v4/summary/{A0_cells,A1_cells,A3F_cells,A1_comparisons,A3F_comparisons,A3_comparisons}.csv
  REPO/results/summary/{throughput_summary.json, v3_batching_summary.csv, v3_e2e_summary.csv}
  V7/results/deploy/message_breakdown.json, V7/results/reexec_cloud/reexecution_comparison.json (if present)
Writes into OUT (the V7 paper's generated/ directory):
  v7_macros.tex (\X... macros), tab_v7_primary.tex, tab_v7_effects.tex, tab_v7_messagebytes.tex
Every number printed in the V7 manuscript that is not an existing \R/\V/\W macro comes from here.

Usage: python3 -B analysis_v7.py REPO_DIR V7_DIR OUT_DIR
"""
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO, V7, OUT = (Path(p).resolve() for p in sys.argv[1:4])
S4 = REPO / "results" / "v4" / "summary"
S = REPO / "results" / "summary"
# V7 outputs live in V7/results/ in the working layout and in results/v7/ in the assembled repository
R7 = V7 / "results" / "v7" if (V7 / "results" / "v7" / "deploy").exists() else V7 / "results"
OUT.mkdir(parents=True, exist_ok=True)

ARM = {"PBTI": r"\sys", "PBTI-R-event": r"PBTI-R\textsubscript{ev}", "PBTI-R-hist": r"PBTI-R\textsubscript{60/10}",
       "B5-hist": r"B5\textsubscript{60/10}", "B5-event": r"B5\textsubscript{ev}", "B5S": "B5s", "PBTI-SH": "PBTI-SH",
       "PBTI-SH-T30": "PBTI-SH-T30", "B4": "B4"}
CELL = {"S05_stolen_key": "E5 stolen keys", "S08_seq_reuse_bug": "E8 sequence-reuse fault",
        "S12_beyond_horizon": "E11b beyond-horizon backlog", "S99_mixed": "Mixed workload"}
FG = ["run3", "run4", "run8", "run15"]          # factorial cells with equivocation and suppressed runs both high
DIGITS = {0: "Zero", 1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six", 7: "Seven", 8: "Eight",
          9: "Nine"}

macros = {}


def mname(*parts):
    s = "X" + "".join(re.sub(r"[^A-Za-z0-9]", "", str(p)).title() for p in parts)
    return re.sub(r"\d", lambda m: DIGITS[int(m.group())], s)


def put(name, value):
    if name in macros and macros[name] != value:
        raise ValueError(f"macro {name} redefined: {macros[name]} vs {value}")
    macros[name] = value


def thou(x, nd=0):
    s = f"{x:,.{nd}f}"
    return s.replace(",", "{,}")


def f1(x):
    return "--" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.1f}"


def fmt(outcome, x):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "--"
    if outcome in ("O1", "O2", "DEC"):
        return thou(x, 1) if abs(x) >= 1000 else f"{x:.1f}"
    if outcome == "NLX":
        return thou(x, 0)
    if outcome == "W":
        return f"{x:.2f}"
    if outcome == "AV5":
        return f"{x:.3f}"
    if outcome == "RECP50":
        return f"{x:.1f}"
    return f"{x}"


# ------------------------------------------------------------------ primary results table
a1 = pd.read_csv(S4 / "A1_cells.csv")
a3f = pd.read_csv(S4 / "A3F_cells.csv")
OUTS = ["O1", "O2", "NLX", "W", "AV5", "DEC", "RECP50"]
rows = []
for cell in ["S05_stolen_key", "S08_seq_reuse_bug", "S12_beyond_horizon", "S99_mixed"]:
    for arm in ["PBTI", "PBTI-R-event", "B5-hist", "B5-event"]:
        r = a1[(a1.cell == cell) & (a1.arm == arm)].iloc[0]
        vals = {o: (None if pd.isna(r[o]) else float(r[o])) for o in OUTS}
        if arm == "PBTI":
            vals["DEC"] = None           # no reviewer
        rows.append((CELL[cell], arm, vals, int(r["reach"])))
fg = a3f[a3f.cell.isin(FG)].groupby("arm")
for arm in ["PBTI", "PBTI-SH", "B5-hist", "B5-event", "B5S"]:
    g = fg.get_group(arm)
    vals = {o: (None if g[o].isna().all() else float(g[o].mean())) for o in OUTS}
    if arm in ("PBTI", "PBTI-SH", "B5S"):
        vals["DEC"] = None               # no reviewer
    rows.append(("Equivocation + suppressed messages", arm, vals, int(g["reach"].iloc[0])))

L = [r"\begin{tabular}{@{}llrrrrrrr@{}}\toprule",
     r"Workload & Pipeline & O1 & O2 & NLX (rec-s) & $W$ (s) & AV5 & Decisions & Release (s) \\ \midrule"]
last = None
for wl, arm, vals, reach in rows:
    lab = wl if wl != last else ""
    if wl != last and last is not None:
        L.append(r"\addlinespace[2pt]")
    last = wl
    cells = [fmt(o, vals[o]) for o in OUTS]
    L.append(f"{lab} & {ARM[arm]} & " + " & ".join(cells) + r" \\")
    key = {"E5 stolen keys": "Efive", "E8 sequence-reuse fault": "Eeight", "E11b beyond-horizon backlog": "Eelevenb",
           "Mixed workload": "Mixed", "Equivocation + suppressed messages": "FG"}[wl]
    AK = {"PBTI": "PBTI", "PBTI-R-event": "PBTIRevent", "B5-hist": "BFivehist", "B5-event": "BFiveevent",
          "B5S": "BFiveS", "PBTI-SH": "PBTISH"}
    OK = {"O1": "OOne", "O2": "OTwo", "NLX": "NLX", "W": "W", "AV5": "AVFive", "DEC": "DEC", "RECP50": "RecPFifty"}
    for o in OUTS:
        put("XPrim" + key + AK[arm] + OK[o], fmt(o, vals[o]))
L.append(r"\bottomrule\end{tabular}")
CSV = R7 / "v7_analysis"
CSV.mkdir(parents=True, exist_ok=True)
pd.DataFrame([{"workload": wl, "pipeline": arm, "legit_reachable_per_run": reach,
               **{o: vals[o] for o in OUTS}} for wl, arm, vals, reach in rows]).to_csv(CSV / "primary_results.csv", index=False)
(OUT / "tab_v7_primary.tex").write_text("% AUTO-GENERATED by tools/v7/analysis_v7.py -- do not edit by hand\n"
                                        + "\n".join(L) + "\n")
put("XPrimReachMain", thou(7200))
put("XPrimReachFG", thou(2880))

# relative differences used in the text (from the same cell means)
def mean_of(df, cell, arm, o):
    return float(df[(df.cell == cell) & (df.arm == arm)][o].iloc[0])


fgm = {arm: float(fg.get_group(arm)[o].mean()) for arm in ["PBTI", "PBTI-SH", "B5-hist", "B5-event", "B5S"]
       for o in ["O2"]}
put("XRelEfiveWBFivehist", f"{100 * (mean_of(a1, 'S05_stolen_key', 'B5-hist', 'W') / mean_of(a1, 'S05_stolen_key', 'PBTI', 'W') - 1):.0f}")
put("XRelMixedNLXBFivehist", f"{100 * (1 - mean_of(a1, 'S99_mixed', 'B5-hist', 'NLX') / mean_of(a1, 'S99_mixed', 'PBTI', 'NLX')):.0f}")
put("XFGSHOtwoExtra", f"{fg.get_group('PBTI-SH')['O2'].mean() - fg.get_group('PBTI')['O2'].mean():.1f}")
put("XFGSHOtwoExtraPct", f"{100 * (fg.get_group('PBTI-SH')['O2'].mean() - fg.get_group('PBTI')['O2'].mean()) / 2880:.1f}")

# ------------------------------------------------------------------ effect-size table (confirmatory comparisons)
c1 = pd.read_csv(S4 / "A1_comparisons.csv")
c3f = pd.read_csv(S4 / "A3F_comparisons.csv")
c3 = pd.read_csv(S4 / "A3_comparisons.csv")


def ci(s):
    lo, hi = json.loads(s)
    return lo, hi


def num(o, x):
    if o in ("O1", "O2"):
        return f"{x:.1f}"
    if o == "NLX":
        return thou(x, 0)
    if o == "W":
        return f"{x:.2f}" if abs(x) >= 0.1 else f"{x:.3f}"
    if o == "AV5":
        return f"{x:.3f}" if abs(x) >= 0.001 else f"{x:.4f}"
    return f"{x}"


def tex(t):
    """leading sign of a formatted number in math mode"""
    return re.sub(r"(?<![\w{])([+-])(?=\d)", lambda m: "$" + ("-" if m.group(1) == "-" else "+") + "$", t)


def sgn(o, x):
    t = num(o, x)
    return t if t.startswith("-") else "+" + t


def relpct(d, m):
    r = 100 * d / m
    return f"{r:+.1f}\\%" if abs(r) < 1 else f"{r:+.0f}\\%"


CLASS = {"identical": "identical", "equivalent within margin": "equivalent",
         "equivalent within margin (significant difference)": "equivalent$^{s}$",
         "better beyond margin": "better", "worse beyond margin": "worse",
         "different, within margin": "different within margin", "inconclusive": "inconclusive"}
EOUT = {"O1": "O1", "O2": "O2", "NLX": "NLX", "W": "$W$", "AV5": "AV5"}


def row_a1(hyp, arm, ref, cell, o, label, level):
    r = c1[(c1.hypothesis == hyp) & (c1.arm == arm) & (c1.ref == ref) & (c1.cell == cell) & (c1.outcome == o)].iloc[0]
    lo, hi = ci(r["ci95"])
    rel = "--" if (r["mean_ref"] == 0 or o == "W") else relpct(r["mean_d"], r["mean_ref"])
    d = "0 (all seeds)" if r["class"] == "identical" else f"{sgn(o, r['mean_d'])} [{num(o, lo)}, {num(o, hi)}]"
    return (label, CELL[cell].split(" ")[0] if cell != "S99_mixed" else "Mixed", EOUT[o], tex(d), tex(rel),
            num(o, r["margin"]) if o != "O2" else f"{r['margin']:.0f}", CLASS[r["class"]], level)


def row_fg(hyp, arm, ref, o, label, level):
    q = c3f[(c3f.hypothesis == hyp) & (c3f.arm == arm) & (c3f.ref == ref) & (c3f.cell.isin(FG)) & (c3f.outcome == o)]
    ds = q["mean_d"].tolist()
    rels = [] if o == "W" else [100 * d / m for d, m in zip(q["mean_d"], q["mean_ref"]) if m != 0]
    cls = q["class"].map(CLASS).value_counts()
    d = f"{sgn(o, min(ds))} to {sgn(o, max(ds))}"
    rel = f"{min(rels):+.0f} to {max(rels):+.0f}\\%" if rels else "--"
    ctext = ", ".join(f"{k} {v}/4" for k, v in cls.items())
    return (label, "4 cells", EOUT[o], tex(d), tex(rel), num(o, q['margin'].iloc[0]) if o != "O2" else f"{q['margin'].iloc[0]:.1f}",
            ctext, level)


E = [
    row_a1("H1a", "B5-hist", "PBTI", "S05_stolen_key", "W", r"B5\textsubscript{60/10} $-$ \sys", "A"),
    row_a1("H1a", "B5-hist", "PBTI", "S05_stolen_key", "AV5", r"B5\textsubscript{60/10} $-$ \sys", "A"),
    row_a1("H1a", "B5-hist", "PBTI", "S99_mixed", "NLX", r"B5\textsubscript{60/10} $-$ \sys", "A"),
    row_a1("H1a", "B5-hist", "PBTI", "S99_mixed", "W", r"B5\textsubscript{60/10} $-$ \sys", "A"),
    row_a1("H1b", "B5-event", "PBTI", "S05_stolen_key", "W", r"B5\textsubscript{ev} $-$ \sys", "A"),
    row_a1("H1b", "B5-event", "PBTI", "S99_mixed", "W", r"B5\textsubscript{ev} $-$ \sys", "A"),
    row_a1("H1b", "B5-event", "PBTI", "S12_beyond_horizon", "O2", r"B5\textsubscript{ev} $-$ \sys", "A"),
    row_a1("H1c", "B5-event", "PBTI-R-event", "S99_mixed", "W", r"B5\textsubscript{ev} $-$ PBTI-R\textsubscript{ev}", "A"),
    row_a1("H1c", "B5-event", "PBTI-R-event", "S99_mixed", "NLX", r"B5\textsubscript{ev} $-$ PBTI-R\textsubscript{ev}", "A"),
    row_fg("H3a", "PBTI-SH", "PBTI", "NLX", r"PBTI-SH $-$ \sys", "C"),
    row_fg("H3a", "PBTI-SH", "PBTI", "O2", r"PBTI-SH $-$ \sys", "C"),
    row_fg("H3b", "PBTI-SH", "B5-hist", "W", r"PBTI-SH $-$ B5\textsubscript{60/10}", "C"),
    row_fg("H3b", "PBTI-SH", "B5-hist", "O2", r"PBTI-SH $-$ B5\textsubscript{60/10}", "C"),
    row_fg("H3b", "PBTI-SH", "B5-event", "W", r"PBTI-SH $-$ B5\textsubscript{ev}", "C"),
]
L = [r"\begin{tabular}{@{}lllllr>{\raggedright\arraybackslash}p{3.0cm}l@{}}\toprule",
     r"Comparison & Workload & Outcome & Mean difference [95\% CI] & Relative & Margin & Class & Level \\ \midrule"]
for e in E:
    L.append(" & ".join(e) + r" \\")
L.append(r"\bottomrule\end{tabular}")
pd.DataFrame([dict(zip(["comparison", "workload", "outcome", "mean_difference_ci95", "relative", "margin", "class",
                       "evidence_level"], [re.sub(r"\\textsubscript\{([^}]*)\}", r"_\1", re.sub(r"[$]", "", x))
                                           .replace("\\sys", "PBTI").replace("\\%", "%").replace("^{s}", " (s)").replace("{,}", ",")
                                           .replace("\\", "") for x in e])) for e in E]).to_csv(
    CSV / "effect_sizes_primary.csv", index=False)
(OUT / "tab_v7_effects.tex").write_text("% AUTO-GENERATED by tools/v7/analysis_v7.py -- do not edit by hand\n"
                                        + "\n".join(L) + "\n")

# trade-off in a common unit (record-seconds per run): extra withheld genuine record-seconds versus exposure saved
def _cmp(hyp, arm, ref, cell, o):
    return c1[(c1.hypothesis == hyp) & (c1.arm == arm) & (c1.ref == ref) & (c1.cell == cell) & (c1.outcome == o)].iloc[0]


for cell, key in (("S05_stolen_key", "Efive"), ("S99_mixed", "Mixed")):
    reach = float(a1[(a1.cell == cell) & (a1.arm == "PBTI")]["reach"].iloc[0])
    put("XTrade" + key + "Wrec", thou(_cmp("H1a", "B5-hist", "PBTI", cell, "W")["mean_d"] * reach, 0))
    put("XTrade" + key + "NLX", thou(-_cmp("H1a", "B5-hist", "PBTI", cell, "NLX")["mean_d"], 0))

# design property: with the same reviewer and schedule B5's authoritative set is never larger than PBTI-R's;
# checked on every matched run of the review-schedule evaluation (direction of O1, NLX, O2, W, AV5)
_raw = [json.loads(l) for l in open(REPO / "results" / "v4" / "raw" / "A1_review.jsonl")]
_by = {(x["scenario"], x["arm"], x["seed"]): x for x in _raw}
_n = _v = 0
for (sc, arm, seed), x in _by.items():
    if not arm.startswith("B5-"):
        continue
    y = _by.get((sc, "PBTI-R-" + arm.split("-", 1)[1], seed))
    if y is None:
        continue
    _n += 1
    Wx, Wy = x["tm_wh_rec_s"] / x["tm_reach"], y["tm_wh_rec_s"] / y["tm_reach"]
    _v += int(x["nonlegit_auth"] > y["nonlegit_auth"] or x["tm_nl_rec_s"] > y["tm_nl_rec_s"] + 1e-6
              or x["legit_missing"] < y["legit_missing"] or Wx < Wy - 1e-9 or x["tm_avail_5s"] > y["tm_avail_5s"] + 1e-12)
put("XSubsetRuns", str(_n))
put("XSubsetViolations", str(_v))

# exploratory split of W into delay and permanent loss (tools/v7/w_decomposition.py), if available
_wd = R7 / "v7_analysis" / "w_decomposition_summary.json"
if _wd.exists():
    wd = json.loads(_wd.read_text())
    put("XWdRuns", str(wd["runs"]))
    put("XWdAllMatch", "all" if wd["all_W_match_stored"] else "NOT all")
    C = wd["cells"]
    put("XWdEfivePBTIW", f"{C['A1_review|S05_stolen_key|PBTI']['W']:.2f}")
    put("XWdEfivePBTILossPct", f"{100 * C['A1_review|S05_stolen_key|PBTI']['W_loss'] / C['A1_review|S05_stolen_key|PBTI']['W']:.1f}")
    put("XWdEfivePBTIDelay", f"{C['A1_review|S05_stolen_key|PBTI']['W_delay']:.2f}")
    put("XWdEfiveBhistDelay", f"{C['A1_review|S05_stolen_key|B5-hist']['W_delay']:.2f}")
    put("XWdMixedPBTIDelay", f"{C['A1_review|S99_mixed|PBTI']['W_delay']:.2f}")
    put("XWdMixedBhistDelay", f"{C['A1_review|S99_mixed|B5-hist']['W_delay']:.2f}")
    put("XWdMixedPBTILoss", f"{C['A1_review|S99_mixed|PBTI']['W_loss']:.2f}")
    put("XWdMixedBhistLoss", f"{C['A1_review|S99_mixed|B5-hist']['W_loss']:.2f}")
    fgc = ["run3", "run4", "run8", "run15"]
    sh_loss = [100 * C[f"A3_factorial|{c}|PBTI-SH"]["W_loss"] / C[f"A3_factorial|{c}|PBTI-SH"]["W"] for c in fgc]
    b5_loss = [100 * C[f"A3_factorial|{c}|B5-hist"]["W_loss"] / C[f"A3_factorial|{c}|B5-hist"]["W"] for c in fgc]
    put("XWdFGSHLossPctMin", f"{min(sh_loss):.0f}")
    put("XWdFGSHLossPctMax", f"{max(sh_loss):.0f}")
    put("XWdFGBhistLossPctMin", f"{min(b5_loss):.0f}")
    put("XWdFGBhistLossPctMax", f"{max(b5_loss):.0f}")
    pr = {(x["cell"], x["arm"], x["ref"]): x for x in wd["pairs"]}
    dl = [pr[(c, "PBTI-SH", "B5-hist")]["W_delay"]["mean_d"] for c in fgc]
    ls = [pr[(c, "PBTI-SH", "B5-hist")]["W_loss"]["mean_d"] for c in fgc]
    assert max(dl) < 0, dl  # PBTI-SH has less delay than B5-hist in every factorial cell; report magnitudes
    put("XWdFGSHvsBhistDelayMin", f"{-max(dl):.1f}")
    put("XWdFGSHvsBhistDelayMax", f"{-min(dl):.1f}")
    put("XWdFGSHvsBhistLossMin", f"{min(ls):.1f}")
    put("XWdFGSHvsBhistLossMax", f"{max(ls):.1f}")
    e = pr[("S05_stolen_key", "B5-hist", "PBTI")]
    put("XWdEfiveBhistDelayDiff", f"{e['W_delay']['mean_d']:.2f}")
    put("XWdEfiveBhistLossDiff", f"{e['W_loss']['mean_d']:.4f}")

# exploratory consistent-impersonator check of the mixed workload (tools/v7/consistent_impersonator_check.py)
_ci = R7 / "v7_analysis" / "consistent_impersonator.jsonl"
if _ci.exists():
    ci_rows = [json.loads(l) for l in open(_ci)]
    seeds = sorted({x["seed"] for x in ci_rows})
    def _m(arm, var, k):
        v = [x[k] for x in ci_rows if x["arm"] == arm and x["variant"] == var]
        return float(np.mean(v)) if v else float("nan")
    put("XCiSeeds", f"{seeds[0]}--{seeds[-1]}" if len(seeds) > 1 else str(seeds[0]))
    put("XCiNSeeds", str(len(seeds)))
    put("XCiRegMatch", "all" if all(x.get("matches_stored") is True for x in ci_rows if x["variant"] == "registered") else "NOT all")
    for var, vk in (("registered", "Reg"), ("consistent", "Con")):
        for arm, ak in (("PBTI", "PBTI"), ("B5-hist", "Bhist"), ("B5-event", "Bev")):
            put(f"XCi{vk}{ak}OOne", f"{_m(arm, var, 'O1'):.1f}")
            put(f"XCi{vk}{ak}NLX", thou(_m(arm, var, 'NLX'), 0))
        put(f"XCi{vk}BhistNLXPct", f"{100 * (1 - _m('B5-hist', var, 'NLX') / _m('PBTI', var, 'NLX')):.0f}")
        put(f"XCi{vk}BevNLXPct", f"{100 * (1 - _m('B5-event', var, 'NLX') / _m('PBTI', var, 'NLX')):.0f}")
        put(f"XCi{vk}BhistNLXDiff", thou(_m('PBTI', var, 'NLX') - _m('B5-hist', var, 'NLX'), 0))

# class counts for the matched comparison (H1c) and for the selective-hold grid (G3) used in the text
h1c = c1[c1.hypothesis == "H1c"]
put("XHcN", str(len(h1c)))
put("XHcIdentEquiv", str(int(h1c["class"].isin(["identical", "equivalent within margin",
                                                  "equivalent within margin (significant difference)"]).sum())))
ev = h1c[h1c.arm == "B5-event"]
put("XHcEventN", str(len(ev)))
put("XHcEventIdentEquiv", str(int(ev["class"].isin(["identical", "equivalent within margin",
                                                     "equivalent within margin (significant difference)"]).sum())))

# counts used in the matched-review sentences (statistics audit M1, M11): counts of classes, not family sizes
EQUIV = ["identical", "equivalent within margin", "equivalent within margin (significant difference)"]
put("XHcOOneIdentical", str(int((h1c[h1c.outcome == "O1"]["class"] == "identical").sum())))
put("XHcOOneN", str(int((h1c.outcome == "O1").sum())))
put("XHcOTwoIdentEquiv", str(int(h1c[h1c.outcome == "O2"]["class"].isin(EQUIV).sum())))
put("XHcOTwoN", str(int((h1c.outcome == "O2").sum())))
mx = h1c[(h1c.outcome == "NLX") & (h1c.cell == "S99_mixed")]
put("XHcMixedNLXBetter", str(int((mx["class"] == "better beyond margin").sum())))
put("XHcMixedNLXN", str(len(mx)))
dd = mx[mx.arm == "B5-d0c1"].iloc[0]
put("XHcMixedNLXdZerocOne", thou(abs(dd["mean_d"]), 0))
h1d = c1[(c1.hypothesis == "H1d") & (c1.outcome == "O1")]
put("XHdOOneIdentical", str(int((h1d["class"] == "identical").sum())))
put("XHdOOneN", str(len(h1d)))

# ------------------------------------------------------------------ deployment and overhead numbers
mb = json.loads((R7 / "deploy" / "message_breakdown.json").read_text())
grp = mb["pbti_group_bytes_mean"]
gk = list(grp)
put("XMbPBTI", f"{mb['mean_wire_bytes_json']['PBTI']:.0f}")
put("XMbBTwo", f"{mb['mean_wire_bytes_json']['B2']:.0f}")
put("XMbRatio", f"{mb['ratio_PBTI_to_B2_json']:.2f}")
put("XMbShared", f"{grp[gk[0]]:.0f}")
put("XMbObsAdd", f"{grp[gk[1]]:.0f}")
put("XMbOsig", f"{grp[gk[2]]:.0f}")
put("XMbRel", f"{grp[gk[3]]:.0f}")
put("XMbRsig", f"{grp[gk[4]]:.0f}")
put("XMbStruct", f"{mb['pbti_json_structure_and_key_overhead_bytes']:.0f}")
sig = grp[gk[2]] + grp[gk[4]]
put("XMbSigShare", f"{100 * sig / mb['mean_wire_bytes_json']['PBTI']:.0f}")
put("XMbRelShare", f"{100 * grp[gk[3]] / mb['mean_wire_bytes_json']['PBTI']:.0f}")
put("XMbBinTxtPBTI", f"{mb['binary_estimate_text_keys']['PBTI']:.0f}")
put("XMbBinTxtBTwo", f"{mb['binary_estimate_text_keys']['B2']:.0f}")
put("XMbBinIntPBTI", f"{mb['binary_estimate_int_keys']['PBTI']:.0f}")
put("XMbBinIntBTwo", f"{mb['binary_estimate_int_keys']['B2']:.0f}")
put("XMbBinTxtRatio", f"{mb['ratio_PBTI_to_B2_binary_text_keys']:.2f}")
put("XMbBinIntRatio", f"{mb['ratio_PBTI_to_B2_binary_int_keys']:.2f}")
put("XMbN", thou(mb["n_messages"]))
T = [r"\begin{tabular}{@{}lr@{}}\toprule", r"Part of a \sys\ message & Bytes \\ \midrule",
     r"Payload and identifiers also carried by B2 (\textsf{pl}, \textsf{did}, \textsf{aid}, \textsf{ts}, \textsf{sch}) & "
     + f"{grp[gk[0]]:.0f}" + r" \\",
     r"Observation-statement additions (version, type, epoch, sequence, \textsf{prev} digest, key id) & "
     + f"{grp[gk[1]]:.0f}" + r" \\",
     r"Origin signature $\sigma_o$ (base64url) & " + f"{grp[gk[2]]:.0f}" + r" \\",
     r"Relay statement (workload id, key id, \textsf{odig}, relay time, mode, version, type) & "
     + f"{grp[gk[3]]:.0f}" + r" \\",
     r"Relay signature $\sigma_w$ (base64url) & " + f"{grp[gk[4]]:.0f}" + r" \\",
     r"JSON structure & " + f"{mb['pbti_json_structure_and_key_overhead_bytes']:.0f}" + r" \\ \midrule",
     r"Total (B2 message: " + f"{mb['mean_wire_bytes_json']['B2']:.0f}" + r") & "
     + f"{mb['mean_wire_bytes_json']['PBTI']:.0f}" + r" \\",
     r"Estimate in CBOR, text / integer keys (B2: " + f"{mb['binary_estimate_text_keys']['B2']:.0f} / "
     + f"{mb['binary_estimate_int_keys']['B2']:.0f}" + r") & " + f"{mb['binary_estimate_text_keys']['PBTI']:.0f} / "
     + f"{mb['binary_estimate_int_keys']['PBTI']:.0f}" + r" \\", r"\bottomrule\end{tabular}"]
(OUT / "tab_v7_messagebytes.tex").write_text("% AUTO-GENERATED by tools/v7/analysis_v7.py -- do not edit by hand\n"
                                             + "\n".join(T) + "\n")

th = json.loads((S / "throughput_summary.json").read_text())["systems"]
p = th["PBTI"]
tot = sum(p[k] for k in ("stage_parse", "stage_crypto", "stage_lifecycle", "stage_policy", "stage_history",
                         "stage_commit"))
put("XStageTotal", f"{tot:.0f}")
put("XStageCryptoShare", f"{100 * p['stage_crypto'] / tot:.0f}")
put("XCpuPBTI", f"{p['cpu_us_per_msg']:.0f}")
put("XCpuBTwo", f"{th['B2']['cpu_us_per_msg']:.0f}")
put("XEvidenceBytes", f"{p['evidence_bytes']:.0f}")
put("XDbPBTI", f"{p['db_bytes_per_msg']:.0f}")
put("XDbBTwo", f"{th['B2']['db_bytes_per_msg']:.0f}")
# storage growth per day at 1,000 msg/s (arithmetic from measured bytes per message; not a measurement)
gb_day = (p["db_bytes_per_msg"]) * 1000 * 86400 / 1e9
put("XStorageGBDayAtThousand", f"{gb_day:.0f}")
gb_day_b2 = th["B2"]["db_bytes_per_msg"] * 1000 * 86400 / 1e9
put("XStorageGBDayAtThousandBTwo", f"{gb_day_b2:.0f}")
# largest persisted bytes per message of PBTI across the SKAB replays through MQTT/TLS (Table S32)
_sk = pd.read_csv(S / "v3_e2e_skab_summary.csv")
_skmax = float(_sk[_sk.system == "PBTI"]["db_bytes_per_msg"].max())
put("XDbPBTIMax", f"{_skmax:.0f}")
put("XStorageGBDayAtThousandMax", f"{_skmax * 1000 * 86400 / 1e9:.0f}")
e2e = pd.read_csv(S / "v3_e2e_summary.csv")
pb = e2e[e2e.system == "PBTI"].set_index("rate")
put("XEePBTIThousandPFifty", f"{pb.loc[1000, 'lat_ms_p50_median']:.1f}")
put("XEePBTIThousandPNinetyNine", f"{pb.loc[1000, 'lat_ms_p99_median']:.0f}")
put("XEePBTIFifteenHundredTp", thou(pb.loc[1500, "throughput_msg_s_median"], 0))
# devices supported at 1 Hz and 10 Hz by the measured sustained networked rate (simple division; extrapolation)
put("XDevicesOneHz", thou(1000))
put("XDevicesTenHz", thou(100))

# ------------------------------------------------------------------ re-execution summary (if available)
rx = R7 / "reexec_cloud" / "reexecution_comparison.json"
if rx.exists():
    d = json.loads(rx.read_text())
    t = d["totals"]
    put("XRxRuns", thou(t.get("compared", 0)))
    put("XRxIdentical", thou(t.get("identical", 0)))
    put("XRxDifferent", thou(t.get("different", 0)))
    put("XRxErrors", thou(t.get("errors_in_new", 0)))
    put("XRxFields", thou(t.get("n_field_comparisons", 0)))
    pt = (d.get("pytest") or {}).get("counts", {})
    put("XRxTestsPassed", str(pt.get("passed", "--")))
    put("XRxTestsSkipped", str(pt.get("skipped", 0)))
    a5 = d.get("a5_lifecycle_matrix") or {}
    put("XRxAfiveRows", str(a5.get("identical_rows", "--")))
    put("XRxAfiveTotal", str(a5.get("stored_rows", "--")))
    fc = d.get("formal_check") or {}
    put("XRxFormalSame", "identical" if fc.get("identical_excluding_timing") else "NOT identical")

    NAMES = {"A0_core_subset.jsonl": "Main evaluation and mixed workload (re-executed)",
             "A1_review_subset.jsonl": "Review-schedule evaluation", "A3_selective_subset.jsonl": "Selective-hold grid",
             "A3_scenarios_subset.jsonl": "Selective-hold controls", "A3_factorial_subset.jsonl": "Selective-hold factorial cells"}
    T = [r"\begin{tabular}{@{}lllrrrr@{}}\toprule",
         r"Stage & Seeds & Runs & Identical & Different & Errors & Field comparisons \\ \midrule"]
    for f, c in d["campaigns"].items():
        T.append(f"{NAMES.get(f, f)} & {', '.join(map(str, c['seeds']))} & {thou(c['compared'])} & {thou(c['identical'])} & "
                 f"{thou(c['different'])} & {c['errors_in_new']} & {thou(c['n_field_comparisons'])} \\\\")
    T.append(r"\midrule")
    T.append(f"Lifecycle analysis (all rows) & -- & {a5.get('stored_rows', '--')} & {a5.get('identical_rows', '--')} & "
             f"{len(a5.get('different_or_missing', [])) if a5 else '--'} & -- & -- \\\\")
    T.append(f"Bounded checks (all parts) & -- & -- & {'yes' if fc.get('identical_excluding_timing') else 'no'} & -- & -- & -- \\\\")
    T.append(f"Test suite & -- & -- & \\multicolumn{{4}}{{l}}{{{pt.get('passed', '--')} passed, {pt.get('skipped', 0)} skipped, "
             f"{pt.get('failed', 0)} failed}} \\\\")
    T.append(r"\bottomrule\end{tabular}")
    env = d.get("environment") or {}
    (OUT / "tabS_v7_reexec.tex").write_text("% AUTO-GENERATED by tools/v7/analysis_v7.py -- do not edit by hand\n"
                                            + "\n".join(T) + "\n")
    put("XRxCpu", env.get("cpu_model", "--").replace("(R)", "").replace("  ", " "))
    put("XRxCpus", str(env.get("logical_cpus", "--")))
    put("XRxOS", env.get("os", "--"))
    put("XRxPython", env.get("python", "--"))
    put("XRxDate", (env.get("time_utc") or "--")[:10])
else:   # re-execution not finished: visible markers that the final consistency check rejects
    (OUT / "tabS_v7_reexec.tex").write_text("% placeholder: re-execution not finished\n\\textbf{??}\n")
    for k in ("XRxCpu", "XRxCpus", "XRxOS", "XRxPython", "XRxDate"):
        put(k, r"\textbf{??}")
    for k in ("XRxRuns", "XRxIdentical", "XRxDifferent", "XRxErrors", "XRxFields", "XRxTestsPassed", "XRxTestsSkipped",
              "XRxAfiveRows", "XRxAfiveTotal", "XRxFormalSame"):
        put(k, r"\textbf{??}")

with open(OUT / "v7_macros.tex", "w") as fh:
    fh.write("% AUTO-GENERATED by tools/v7/analysis_v7.py -- do not edit by hand\n")
    for k in sorted(macros):
        fh.write(f"\\newcommand{{\\{k}}}{{{macros[k]}}}\n")
print(f"{len(macros)} macros; tables: tab_v7_primary.tex, tab_v7_effects.tex, tab_v7_messagebytes.tex")


# ------------------------------------------------------------------ run counts with thousands separators (raw rows)
def count_rows(p):
    n = e = 0
    for line in p.read_text().splitlines():
        if line.strip():
            if "error" in json.loads(line):
                e += 1
            else:
                n += 1
    return n, e


extra = {}
for tag, f in (("Reexec", "A0_core.jsonl"), ("Review", "A1_review.jsonl"), ("Grid", "A3_selective.jsonl"),
               ("Cells", "A3_factorial.jsonl"), ("Controls", "A3_scenarios.jsonl")):
    n, e = count_rows(REPO / "results" / "v4" / "raw" / f)
    extra["XRuns" + tag] = thou(n)
    extra["XRunErrors" + tag] = str(e)
with open(OUT / "v7_macros.tex", "a") as fh:
    for k in sorted(extra):
        fh.write(f"\\newcommand{{\\{k}}}{{{extra[k]}}}\n")
print("run-count macros:", extra)
