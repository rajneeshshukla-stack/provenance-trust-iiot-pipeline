#!/usr/bin/env python3
"""V4 analysis: A0 replication + temporal metrics, A1 review-timing comparison, A3 selective holds, A5 lifecycle
matrix, A4 bounded checks. Statistics exactly as frozen in research/V4/PREREGISTRATION_V4.md (Sections 3-7).

Reads results/v4/raw/{A0_core,A1_review,A3_selective,A3_scenarios}.jsonl (or --raw-map for pilots) and writes
  paper/generated/v4_macros.tex                      LaTeX macros \\W... (every V4 number quoted in the manuscript)
  paper/generated/tab_v4_*.tex, tabS_v4_*.tex        tables
  paper/figures/fig_v4_*.pdf (+ png)                 figures
  results/v4/summary/*.csv|json                      machine-readable summaries, comparisons and claim gates
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import zlib
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
RAW4 = ROOT / "results" / "v4" / "raw"
SUM4 = ROOT / "results" / "v4" / "summary"
GEN = ROOT / "paper" / "generated"
FIG = ROOT / "paper" / "figures"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze as A  # noqa: E402

fmt = A.fmt
SHORT = {k: v.split(" ")[0] for k, v in A.SCEN_LABEL.items()}
SHORT["S99_mixed"] = "Mixed"
RNG_SEED = 20261104
N_BOOT = 10_000
ALPHA = 0.05

VM: dict[str, str] = {}
REPORT: dict = {"warnings": [], "exclusions": [], "deviations": []}


def M(k, v):
    if k in VM and VM[k] != str(v):
        raise SystemExit(f"macro {k} redefined: {VM[k]} vs {v}")
    VM[k] = str(v)


def fnum(v, nd=0):
    """fixed decimals with LaTeX thousands separators; '--' for missing"""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "--"
    t = f"{v:,.{nd}f}"
    if t in ("-0", "-0.0", "-0.00", "-0.000"):
        t = t[1:]
    if t.startswith("-"):
        t = "\\ensuremath{-}" + t[1:]
    return t.replace(",", "{,}")


DND = {"O1": 1, "O2": 1, "NLX": 0, "W": 3, "AV5": 3}

CLASS_CODE = {"identical": "id", "equivalent within margin": "eq",
              "equivalent within margin (significant difference)": "eq$^{s}$",
              "better beyond margin": "\\textbf{B}", "worse beyond margin": "\\textbf{W}",
              "different, within margin": "dw", "inconclusive": "inc"}
CLASS_LEGEND = ("Classes: id, identical in every seed; eq, equivalent within the margin (90\\% CI inside "
                "$\\pm$margin); eq$^{s}$, equivalent and significant after Holm correction; \\textbf{B}/\\textbf{W}, "
                "better/worse beyond the margin (Holm-adjusted $p<0.05$ and 95\\% CI beyond the margin); dw, different "
                "within the margin (significant, not equivalent); inc, inconclusive.")
GATE_ROWS = []  # rows of the table of comparisons that decide the A3 gates


def tnum(x):
    """compact number for comparison tables (3 significant digits, typographic minus)"""
    if x == 0:
        return "0"
    if abs(x) >= 100:
        return f"{x:,.0f}".replace(",", "{,}").replace("-", "$-$")
    s = f"{x:.1e}" if abs(x) < 1e-3 else f"{x:.3g}"
    if "e" in s:
        m_, e_ = s.split("e")
        s = f"{m_}\\cdot 10^{{{int(e_)}}}"
        return "$" + s + "$"
    return s.replace("-", "$-$")


def tp(p):
    return "$<$0.001" if p < 1e-3 else f"{p:.3f}"


def tci(ci):
    return f"[{tnum(ci[0])}, {tnum(ci[1])}]"


def warn(m):
    REPORT["warnings"].append(m)
    print("WARNING", m, file=sys.stderr)


# ============================================================================ outcomes (prereg Section 3)
def W_of(r):
    return r["tm_wh_rec_s"] / max(1, r["tm_reach"])


OUTCOMES = {  # code: (getter, preferred direction)
    "O1": (lambda r: r["nonlegit_auth"], "lower"),
    "O2": (lambda r: r["legit_missing"], "lower"),
    "NLX": (lambda r: r["tm_nl_rec_s"], "lower"),
    "W": (W_of, "lower"),
    "AV5": (lambda r: r["tm_avail_5s"], "higher"),
}
FIXED_MARGIN = {"O1": 1.0, "NLX": 60.0, "W": 0.6, "AV5": 0.01}


def margin(code, cell_rows):
    if code == "O2":
        return 0.01 * float(np.median([r["n_reachable"] for r in cell_rows]))
    return FIXED_MARGIN[code]


SECONDARY = {
    "AV1": lambda r: r["tm_avail_1s"], "AV30": lambda r: r["tm_avail_30s"], "AV60": lambda r: r["tm_avail_60s"],
    "KM50": lambda r: r.get("tm_first_km_p50_s"), "KM90": lambda r: r.get("tm_first_km_p90_s"),
    "KM99": lambda r: r.get("tm_first_km_p99_s"), "NEVER": lambda r: r["tm_never_avail"],
    "WDR": lambda r: r["tm_withdrawn"], "FMISS": lambda r: r["tm_fresh_missing_frac"],
    "FSTALE": lambda r: r["tm_fresh_stale_mean_s"], "CLAT": lambda r: r.get("tm_contain_lat_med_s"),
    "DWNL": lambda r: r.get("tm_dw_nl_s"), "DWLAT": lambda r: r.get("tm_dw_corr_lat_med_s"),
    "ALT": lambda r: r.get("tm_alert_true"), "ALF": lambda r: r.get("tm_alert_false"),
    "ALM": lambda r: r.get("tm_alert_missed"), "DEC": lambda r: r.get("review_decisions"),
    "DEF": lambda r: r.get("review_deferrals"), "HOLDS": lambda r: r.get("holds"),
    "SHH": lambda r: r.get("sh_holds"), "SHR": lambda r: r.get("sh_released"), "SHT": lambda r: r.get("sh_timeouts"),
    "RECP50": lambda r: (r.get("recovery_ms_p50") or 0) / 1000 if r.get("recovered_n") else None,
}


def mean(xs):
    xs = [x for x in xs if x is not None and not (isinstance(x, float) and math.isnan(x))]
    return float(np.mean(xs)) if xs else math.nan


def sd(xs):
    xs = [x for x in xs if x is not None]
    return float(np.std(xs, ddof=1)) if len(xs) > 1 else math.nan


# ============================================================================ loading
def load(path: Path):
    if not path.exists():
        warn(f"{path} missing")
        return [], []
    rows = [json.loads(x) for x in path.read_text().splitlines() if x.strip()]
    err = [r for r in rows if "error" in r]
    return [r for r in rows if "error" not in r], err


def cell_of(r):
    return r.get("point") if r.get("kind") == "sweep" else r["scenario"]


def index(rows, errs, campaign):
    """cell -> arm -> seed -> row, excluding every seed of a cell in which any run errored (prereg Section 9)."""
    by = defaultdict(lambda: defaultdict(dict))
    for r in rows:
        by[cell_of(r)][r["arm"]][r["seed"]] = r
    for e in errs:
        c = e.get("point") if e.get("kind") == "sweep" else e.get("scenario")
        REPORT["exclusions"].append({"campaign": campaign, "cell": c, "seed": e.get("seed"), "arm": e.get("arm"),
                                     "error": e.get("error", "")[:300]})
        for arm in by.get(c, {}):
            by[c][arm].pop(e.get("seed"), None)
    return by


# ============================================================================ statistics (prereg Section 4)
def boot(d, key="", levels=(95, 90)):
    """Percentile bootstrap of the mean; the generator is seeded per comparison (RNG_SEED, CRC32 of the key), so a
    result does not depend on the order in which comparisons are computed (independent re-computation)."""
    d = np.asarray(d, float)
    if np.all(d == d[0]):
        return {lv: (float(d[0]), float(d[0])) for lv in levels}
    rng = np.random.default_rng([RNG_SEED, zlib.crc32(key.encode())])
    idx = rng.integers(0, len(d), (N_BOOT, len(d)))
    b = d[idx].mean(axis=1)
    out = {}
    for lv in levels:
        a = (100 - lv) / 2
        out[lv] = (float(np.percentile(b, a)), float(np.percentile(b, 100 - a)))
    return out


def wilcoxon(d):
    d = np.asarray(d, float)
    if np.all(d == 0):
        return 1.0
    nz = d[d != 0]
    if len(nz) < 1:
        return 1.0
    try:
        return float(stats.wilcoxon(d, zero_method="wilcox", alternative="two-sided").pvalue)
    except ValueError:
        return 1.0


def holm(ps):
    ps = np.asarray(ps, float)
    m = len(ps)
    order = np.argsort(ps)
    adj = np.empty(m)
    run = 0.0
    for k, i in enumerate(order):
        run = max(run, (m - k) * ps[i])
        adj[i] = min(1.0, run)
    return adj


def classify(c):
    """Mechanical classification of one comparison (prereg Section 4). d = arm - reference."""
    d, D, pref = c["d"], c["margin"], c["direction"]
    if all(x == 0 for x in d):
        return "identical"
    lo95, hi95 = c["ci95"]
    lo90, hi90 = c["ci90"]
    sig = c["p_holm"] < ALPHA
    # sign convention: "better" means the arm is better than the reference
    if sig and pref == "lower" and hi95 < -D:
        return "better beyond margin"
    if sig and pref == "lower" and lo95 > D:
        return "worse beyond margin"
    if sig and pref == "higher" and lo95 > D:
        return "better beyond margin"
    if sig and pref == "higher" and hi95 < -D:
        return "worse beyond margin"
    if -D < lo90 and hi90 < D:
        return "equivalent within margin" + (" (significant difference)" if sig else "")
    if sig:
        return "different, within margin"
    return "inconclusive"


def compare_family(by, comps, code, campaign, hyp_of):
    """comps: list of (cell, arm, ref). One family = one campaign x one outcome; Holm across the family."""
    get, pref = OUTCOMES[code]
    res = []
    for cell, arm, ref in comps:
        a, b = by.get(cell, {}).get(arm, {}), by.get(cell, {}).get(ref, {})
        seeds = sorted(set(a) & set(b))
        if len(seeds) < 2:
            warn(f"{campaign} {code} {cell} {arm} vs {ref}: only {len(seeds)} paired seeds")
            continue
        d = [get(a[s]) - get(b[s]) for s in seeds]
        ci = boot(d, key=f"{campaign}|{code}|{cell}|{arm}|{ref}")
        res.append({"campaign": campaign, "outcome": code, "cell": cell, "arm": arm, "ref": ref,
                    "hypothesis": hyp_of(cell, arm, ref), "n": len(seeds), "d": d, "mean_d": float(np.mean(d)),
                    "mean_arm": mean([get(a[s]) for s in seeds]), "mean_ref": mean([get(b[s]) for s in seeds]),
                    "ci95": ci[95], "ci90": ci[90], "p": wilcoxon(d), "direction": pref,
                    "margin": margin(code, [b[s] for s in seeds])})
    if res:
        for r, pa in zip(res, holm([r["p"] for r in res])):
            r["p_holm"] = float(pa)
            r["m_family"] = len(res)
            r["class"] = classify(r)
    return res


# ============================================================================ cell summaries
def summarize(by, campaign):
    out = []
    for cell in sorted(by):
        for arm in sorted(by[cell]):
            rows = list(by[cell][arm].values())
            if not rows:
                continue
            rec = {"campaign": campaign, "cell": cell, "arm": arm, "n": len(rows)}
            for code, (get, _p) in OUTCOMES.items():
                v = [get(r) for r in rows]
                rec[code] = mean(v)
                rec[code + "_sd"] = sd(v)
            for code, get in SECONDARY.items():
                rec[code] = mean([get(r) for r in rows])
            rec["reach"] = mean([r["tm_reach"] for r in rows])
            rec["audits"] = sum(1 for r in rows if "audit_pass" in r)
            rec["audits_pass"] = sum(1 for r in rows if r.get("audit_pass") is True)
            rec["tracer_match"] = sum(1 for r in rows if r.get("tm_end_state_matches_authoritative") is True)
            out.append(rec)
    return out


def write_csv(name, recs, drop=("d",)):
    if not recs:
        return
    SUM4.mkdir(parents=True, exist_ok=True)
    keys = [k for k in recs[0] if k not in drop]
    with open(SUM4 / name, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for r in recs:
            w.writerow({k: (json.dumps(v) if isinstance(v, (list, tuple, dict)) else v) for k, v in r.items()})


def cellmap(summ):
    return {(s["cell"], s["arm"]): s for s in summ}


# ============================================================================ A0
def a0(path, cmp_path):
    rows, errs = load(path)
    by = index(rows, errs, "A0")
    summ = summarize(by, "A0")
    write_csv("A0_cells.csv", summ)
    M("AzeroRuns", len(rows))
    M("AzeroErrors", len(errs))
    M("AzeroAudits", sum(s["audits"] for s in summ))
    M("AzeroAuditsPass", sum(s["audits_pass"] for s in summ))
    M("AzeroTracerMatch", sum(s["tracer_match"] for s in summ))
    if cmp_path.exists():
        c = json.loads(cmp_path.read_text())
        M("AzeroCompared", c["compared"])
        M("AzeroIdentical", c["identical"])
        M("AzeroDifferent", len(c["differences"]))
        M("AzeroFieldComparisons", f"{c['n_field_comparisons_total']:,}".replace(",", "{,}"))
        REPORT["A0_comparison"] = {k: c[k] for k in ("compared", "identical", "missing_historical", "errors_new",
                                                     "n_field_comparisons_total", "skipped_fields")}
        REPORT["A0_comparison"]["n_differences"] = len(c["differences"])
    else:
        warn("A0 comparison missing")
    cm = cellmap(summ)
    # Table S: temporal outcomes per scenario and pipeline
    T = []
    T.append("% AUTO-GENERATED by analysis/analyze_v4.py -- do not edit by hand")
    T.append("\\begin{tabular}{@{}llrrrrrrr@{}}\\toprule")
    T.append("Scenario & Pipeline & O1 & O2 & NLX (rec-s) & $W$ (s) & AV5 & KM p90 (s) & Missing$_{fresh}$ \\\\ \\midrule")
    scen = sorted({s["cell"] for s in summ}, key=lambda c: (c == "S99_mixed", c))
    for sc in scen:
        first = True
        for arm in ("PBTI", "B4", "B5-hist", "B5S", "PBTI-R-hist"):
            s = cm.get((sc, arm))
            if not s:
                continue
            T.append(f"{SHORT.get(sc, sc) if first else ''} & {arm.replace('-hist', '')} & {fnum(s['O1'], 1)} & "
                     f"{fnum(s['O2'], 1)} & {fnum(s['NLX'], 0)} & {s['W']:.2f} & {s['AV5']:.3f} & {fnum(s['KM90'], 1)} & "
                     f"{s['FMISS']:.3f} \\\\")
            first = False
        T.append("\\addlinespace[2pt]")
    T.append("\\bottomrule\\end{tabular}")
    (GEN / "tabS_v4_temporal.tex").write_text("\n".join(T) + "\n")
    # key macros: E5 and mixed
    for sc, tag in (("S05_stolen_key", "Efive"), ("S99_mixed", "Mixed"), ("S08_seq_reuse_bug", "Eeight"),
                    ("S12_beyond_horizon", "Eelevenb"), ("S14_revocation", "Efourteen")):
        for arm, at in (("PBTI", "P"), ("B4", "Bfour"), ("B5-hist", "Bfive"), ("B5S", "BfiveS"),
                        ("PBTI-R-hist", "PR")):
            s = cm.get((sc, arm))
            if not s:
                continue
            M(f"Azero{tag}{at}W", fnum(s["W"], 2))
            M(f"Azero{tag}{at}AVfive", fnum(s["AV5"], 3))
            M(f"Azero{tag}{at}AVone", fnum(s["AV1"], 3))
            M(f"Azero{tag}{at}NLX", fnum(s["NLX"], 0))
            M(f"Azero{tag}{at}KMninety", fnum(s["KM90"], 1))
            M(f"Azero{tag}{at}Fmiss", fnum(s["FMISS"], 3))
            M(f"Azero{tag}{at}DWNL", fnum(s["DWNL"], 0))
            M(f"Azero{tag}{at}CLAT", fnum(s["CLAT"], 1))
            M(f"Azero{tag}{at}ALF", fnum(s["ALF"], 1))
            M(f"Azero{tag}{at}ALM", fnum(s["ALM"], 1))
            M(f"Azero{tag}{at}Oone", fnum(s["O1"], 1))
            M(f"Azero{tag}{at}Otwo", fnum(s["O2"], 1))
            M(f"Azero{tag}{at}WDR", fnum(s["WDR"], 1))
    # workloads in which PBTI and B5-hist (or B4) have identical cell means of every primary outcome
    def same(a, b, sc):
        x, y = cm.get((sc, a)), cm.get((sc, b))
        return bool(x and y) and all(abs(x[k] - y[k]) < 1e-9 for k in ("O1", "O2", "NLX", "W", "AV5"))
    sb5 = [sc for sc in scen if same("PBTI", "B5-hist", sc)]
    sb4 = [sc for sc in scen if same("PBTI", "B4", sc)]
    M("AzeroSameBfiveN", len(sb5))
    dl = [("the mixed workload" if sc == "S99_mixed" else SHORT.get(sc, sc)) for sc in scen if sc not in sb5]
    M("AzeroDiffBfiveScen", (", ".join(dl[:-1]) + " and " + dl[-1]) if len(dl) > 1 else (dl[0] if dl else "none"))
    M("AzeroSameBfourN", len(sb4))
    M("AzeroDiffBfourScen", ", ".join(SHORT.get(sc, sc) for sc in scen if sc not in sb4))
    M("AzeroScenN", len(scen))
    # scenarios where B5-hist's W exceeds PBTI's by more than the margin (descriptive, seeds 1-20)
    worse = [sc for sc in scen if cm.get((sc, "B5-hist")) and cm.get((sc, "PBTI"))
             and cm[(sc, "B5-hist")]["W"] - cm[(sc, "PBTI")]["W"] > FIXED_MARGIN["W"]]
    M("AzeroBfiveWorseWScen", ", ".join(SHORT.get(s, s) for s in worse) if worse else "none")
    M("AzeroBfiveWorseWN", len(worse))
    REPORT["A0_cells"] = len(summ)
    return summ


# ============================================================================ A1
A1_SETTINGS = ("hist", "d0c1", "d0c10", "d1c1", "d1c10", "d5c1", "d5c10", "d60c1", "d60c10", "event")
A1_SCEN = ("S05_stolen_key", "S08_seq_reuse_bug", "S12_beyond_horizon", "S99_mixed")


def a1_comparisons(cells, code):
    comps = []
    for sc in cells:
        comps.append((sc, "B5-hist", "PBTI"))                       # H1a
        comps.append((sc, "B5-event", "PBTI"))                      # H1b
        for x in A1_SETTINGS:                                       # H1c
            comps.append((sc, f"B5-{x}", f"PBTI-R-{x}"))
        if code in ("O1", "NLX"):                                   # H1d (prereg: O1 and NLX only)
            for x in A1_SETTINGS[1:]:
                comps.append((sc, f"B5-{x}", "B5-hist"))
    return comps


def a1_hyp(cell, arm, ref):
    if ref == "PBTI":
        return "H1a" if arm == "B5-hist" else "H1b"
    if ref.startswith("PBTI-R"):
        return "H1c"
    return "H1d"


def a1(path):
    rows, errs = load(path)
    by = index(rows, errs, "A1")
    summ = summarize(by, "A1")
    write_csv("A1_cells.csv", summ)
    cells = [c for c in A1_SCEN if c in by]
    allc = []
    fam_sizes = {}
    for code in OUTCOMES:
        comps = a1_comparisons(cells, code)
        fam_sizes[code] = len(comps)
        allc += compare_family(by, comps, code, "A1", a1_hyp)
    write_csv("A1_comparisons.csv", allc)
    M("AoneRuns", len(rows))
    M("AoneErrors", len(errs))
    M("AoneAudits", sum(s["audits"] for s in summ))
    M("AoneAuditsPass", sum(s["audits_pass"] for s in summ))
    M("AoneTracerMatch", sum(s["tracer_match"] for s in summ))
    M("AoneFamilySizeOone", fam_sizes.get("O1", 0))
    M("AoneFamilySizeW", fam_sizes.get("W", 0))
    REPORT["A1_family_sizes"] = fam_sizes
    cm = cellmap(summ)
    C = {(c["outcome"], c["cell"], c["arm"], c["ref"]): c for c in allc}
    # gate G1
    g1 = {sc: {code: C.get((code, sc, "B5-event", "PBTI"), {}).get("class") for code in ("W", "AV5")}
          for sc in ("S05_stolen_key", "S99_mixed")}
    G1 = all(v and (v.startswith("identical") or v.startswith("equivalent")) for d in g1.values() for v in d.values())
    # gate G2
    g2_ok, g2_exc = [], []
    for sc in cells:
        for x in A1_SETTINGS:
            cl = {code: C.get((code, sc, f"B5-{x}", f"PBTI-R-{x}"), {}).get("class") for code in ("O1", "O2")}
            ok = all(v and (v.startswith("identical") or v.startswith("equivalent")) for v in cl.values())
            (g2_ok if ok else g2_exc).append({"scenario": sc, "setting": x, **cl})
    gates = {"G1": {"holds": G1, "classes": g1}, "G2": {"equal": g2_ok, "exceptions": g2_exc}}
    M("AoneGOne", "holds" if G1 else "does not hold")
    M("AoneGTwoEqual", len(g2_ok))
    M("AoneGTwoTotal", len(g2_ok) + len(g2_exc))
    # macros for each scenario x arm (W, AV5, O1, O2, NLX, KM90, decisions, deferrals)
    stag = {"S05_stolen_key": "Efive", "S08_seq_reuse_bug": "Eeight", "S12_beyond_horizon": "Eelevenb",
            "S99_mixed": "Mixed"}
    for sc in cells:
        for arm in sorted({a for (c, a) in cm if c == sc}):
            s = cm[(sc, arm)]
            at = arm.replace("-", "").replace("PBTIR", "PR")
            t = f"Aone{stag[sc]}{at}"
            M(t + "W", fnum(s["W"], 2))
            M(t + "AVfive", fnum(s["AV5"], 3))
            M(t + "AVone", fnum(s["AV1"], 3))
            M(t + "Oone", fnum(s["O1"], 1))
            M(t + "Otwo", fnum(s["O2"], 1))
            M(t + "NLX", fnum(s["NLX"], 0))
            M(t + "KMninety", fnum(s["KM90"], 1))
            M(t + "KMfifty", fnum(s["KM50"], 2))
            M(t + "Dec", fnum(s["DEC"], 0))
            M(t + "Holds", fnum(s["HOLDS"], 0))
            M(t + "ALF", fnum(s["ALF"], 1))
            M(t + "ALM", fnum(s["ALM"], 1))
            M(t + "DWNL", fnum(s["DWNL"], 0))
    for (code, sc, arm, ref), c in C.items():
        if c["hypothesis"] in ("H1a", "H1b", "H1c", "H1d"):
            at = arm.replace("-", "").replace("PBTIR", "PR")
            rt = ref.replace("-", "").replace("PBTIR", "PR")
            t = f"Aone{stag[sc]}{at}vs{rt}{code}"
            M(t + "d", fnum(c["mean_d"], DND[code]))
            M(t + "dshort", fnum(c["mean_d"], 1))
            M(t + "lo", fnum(c["ci95"][0], DND[code]))
            M(t + "hi", fnum(c["ci95"][1], DND[code]))
            M(t + "class", c["class"])
    cntc = defaultdict(lambda: defaultdict(int))
    for c in allc:
        cntc[(c["hypothesis"], c["outcome"])][c["class"].split(" (")[0]] += 1
    REPORT["A1_class_counts"] = {"|".join(k): dict(v) for k, v in cntc.items()}
    for (h, code), v in cntc.items():
        t = f"Aone{h.replace('H1', 'H')}{code}"
        M(t + "N", sum(v.values()))
        M(t + "Same", v.get("identical", 0) + v.get("equivalent within margin", 0))
        M(t + "Identical", v.get("identical", 0))
        M(t + "Better", v.get("better beyond margin", 0))
        M(t + "Worse", v.get("worse beyond margin", 0))
    ev_ok = all(C[k]["class"].startswith(("identical", "equivalent")) for k in C if C[k]["hypothesis"] == "H1c"
                and k[2] == "B5-event")
    M("AoneEventAllSame", "all" if ev_ok else "not all")
    tab_a1(cm, C, cells)
    fig_delay(cm, by, cells)
    REPORT["A1_gates"] = gates
    return summ, allc, gates


def tab_a1(cm, C, cells):
    T = ["% AUTO-GENERATED by analysis/analyze_v4.py -- do not edit by hand",
         "\\begin{tabular}{@{}llrrrrrr@{}}\\toprule",
         "Scenario & Arm & O1 & O2 & NLX (rec-s) & $W$ (s) & AV1 & AV5 \\\\ \\midrule"]
    arms = ["PBTI", "B5-hist", "PBTI-R-hist", "B5-event", "PBTI-R-event"]     # all 22 arms: Data S1 (A1_cells.csv)
    for sc in cells:
        first = True
        for arm in arms:
            s = cm.get((sc, arm))
            if not s:
                continue
            T.append(f"{SHORT.get(sc, sc) if first else ''} & {arm} & {fnum(s['O1'], 1)} & {fnum(s['O2'], 1)} & "
                     f"{fnum(s['NLX'], 0)} & {s['W']:.2f} & {s['AV1']:.3f} & {s['AV5']:.3f} \\\\")
            first = False
        T.append("\\addlinespace[2pt]")
    T.append("\\bottomrule\\end{tabular}")
    (GEN / "tab_v4_a1.tex").write_text("\n".join(T) + "\n")
    # full comparison table (supplement)
    T = ["% AUTO-GENERATED by analysis/analyze_v4.py -- do not edit by hand",
         "\\setlength{\\tabcolsep}{2.6pt}",
         "\\begin{longtable}{@{}lllllrllrl@{}}",
         "\\caption{A1 (seeds 21--40): every preregistered comparison, $\\bar d$ = mean paired difference (arm $-$ "
         "reference) with 95\\% and 90\\% bootstrap CIs, Holm-adjusted Wilcoxon $p$ (within each outcome family) "
         "and the mechanical classification of the preregistration. Outcomes: O1, O2 (observations per run), NLX "
         "(record-s), $W$ (s per observation), AV5 (fraction). " + CLASS_LEGEND + "}\\label{tab:S-a1-tests}\\\\",
         "\\toprule",
         "Hyp. & Scen. & Arm & Reference & Out. & $\\bar d$ & 95\\% CI & 90\\% CI & $p_\\mathrm{Holm}$ & Class "
         "\\\\ \\midrule\\endfirsthead",
         "\\toprule",
         "Hyp. & Scen. & Arm & Reference & Out. & $\\bar d$ & 95\\% CI & 90\\% CI & $p_\\mathrm{Holm}$ & Class "
         "\\\\ \\midrule\\endhead"]
    for c in sorted(C.values(), key=lambda c: (c["hypothesis"], c["cell"], c["arm"], c["outcome"])):
        T.append(f"{c['hypothesis']} & {SHORT.get(c['cell'], c['cell'])} & {c['arm']} & {c['ref']} & {c['outcome']} & "
                 f"{tnum(c['mean_d'])} & {tci(c['ci95'])} & {tci(c['ci90'])} & {tp(c['p_holm'])} & "
                 f"{CLASS_CODE.get(c['class'], c['class'])} \\\\")
    T.append("\\bottomrule\\end{longtable}")
    (GEN / "tabS_v4_a1_tests.tex").write_text("\n".join(T) + "\n")


# ============================================================================ A3
def a3_points(by):
    return sorted(by)


def a3_comparisons(points):
    comps = []
    for p in points:
        comps.append((p, "PBTI-SH", "PBTI"))           # H3a
        comps.append((p, "PBTI-SH", "B5-hist"))        # H3b
        comps.append((p, "PBTI-SH", "B5-event"))       # H3b
        comps.append((p, "PBTI-SH", "B5S"))            # H3b
        comps.append((p, "PBTI-SH", "PBTI-R-hist"))    # H3b
        comps.append((p, "PBTI-SH-T30", "PBTI-SH"))    # H3c
    return comps


def a3_hyp(cell, arm, ref):
    return "H3c" if arm == "PBTI-SH-T30" else ("H3a" if ref == "PBTI" else "H3b")


def plabel(p):
    if not p:
        return p
    parts = dict(x.split("=") for x in p.split("+"))
    eq = float(parts.get("equivocation", 0)) * 100
    other = [(k, float(v) * 100) for k, v in parts.items() if k != "equivocation" and float(v) > 0]
    name = {"missing": "supp.", "delay": "delay", "missing_long": "long supp."}
    s = f"eq {eq:g}\\%"
    for k, v in other:
        s += f", {name.get(k, k)} {v:g}\\%"
    return s


def a3(path):
    rows, errs = load(path)
    by = index(rows, errs, "A3")
    summ = summarize(by, "A3")
    write_csv("A3_cells.csv", summ)
    points = a3_points(by)
    comps = a3_comparisons(points)
    allc = []
    for code in OUTCOMES:
        allc += compare_family(by, comps, code, "A3", a3_hyp)
    write_csv("A3_comparisons.csv", allc)
    M("AthreeRuns", len(rows))
    M("AthreeErrors", len(errs))
    M("AthreeAudits", sum(s["audits"] for s in summ))
    M("AthreeAuditsPass", sum(s["audits_pass"] for s in summ))
    M("AthreeTracerMatch", sum(s["tracer_match"] for s in summ))
    M("AthreePoints", len(points))
    M("AthreeFamilySize", len(comps))
    cm = cellmap(summ)
    C = {(c["outcome"], c["cell"], c["arm"], c["ref"]): c for c in allc}
    pos = [p for p in points if cm.get((p, "PBTI")) and cm[(p, "PBTI")]["O1"] > 0]
    better = [p for p in pos if any(C.get((code, p, "PBTI-SH", "PBTI"), {}).get("class") == "better beyond margin"
                                    for code in ("O1", "NLX"))]
    G3 = len(pos) > 0 and len(better) >= len(pos) / 2
    w_ok = [p for p in better if C.get(("W", p, "PBTI-SH", "B5-hist"), {}).get("class") != "worse beyond margin"]
    G4 = G3 and len(w_ok) == len(better)
    for p_ in pos:
        for code, ref in (("O1", "PBTI"), ("NLX", "PBTI"), ("W", "B5-hist")):
            c = C.get((code, p_, "PBTI-SH", ref))
            if c:
                GATE_ROWS.append(("A3", plabel(p_), ref, code, c))
    gates = {"G3": {"holds": G3, "points_with_pbti_O1_positive": pos, "points_better": better},
             "G4": {"holds": G4, "points_not_worse_W_than_B5hist": w_ok}}
    M("AthreeGThree", "holds" if G3 else "does not hold")
    M("AthreeGFour", "holds" if G4 else "does not hold")
    M("AthreePosPoints", len(pos))
    M("AthreeBetterPoints", len(better))
    # descriptive summaries of the grid for the text (no additional tests; classes as above)
    if pos:
        M("AthreeSHzeroPoints", sum(1 for p in pos if cm.get((p, "PBTI-SH")) and cm[(p, "PBTI-SH")]["O1"] == 0))
        M("AthreeSHmaxOone", fnum(max(cm[(p, "PBTI-SH")]["O1"] for p in pos if (p, "PBTI-SH") in cm), 2))
        M("AthreePmaxOone", fnum(max(cm[(p, "PBTI")]["O1"] for p in pos), 2))

        def beyond_margin(p):
            # mean reduction (PBTI-SH - PBTI) beyond the margin on O1 or NLX, whatever the class
            for code in ("O1", "NLX"):
                c = C.get((code, p, "PBTI-SH", "PBTI"))
                if c and c["mean_d"] < -c["margin"]:
                    return True
            return False
        rest = [p for p in pos if p not in better]
        holm_pts = [p for p in rest if beyond_margin(p)]
        M("AthreeHolmPoints", len(holm_pts))
        M("AthreeSmallPoints", len(rest) - len(holm_pts))
        gates["G3"]["points_reduction_beyond_margin_not_better"] = holm_pts
    eqpos = [p for p in points if "equivocation=0+" not in p and (p, "PBTI-SH") in cm and (p, "PBTI") in cm]
    if eqpos:
        dW = [cm[(p, "PBTI-SH")]["W"] - cm[(p, "PBTI")]["W"] for p in eqpos]
        dO2 = [cm[(p, "PBTI-SH")]["O2"] - cm[(p, "PBTI")]["O2"] for p in eqpos]
        M("AthreeWcostMin", fnum(min(dW), 2))
        M("AthreeWcostMax", fnum(max(dW), 2))
        M("AthreeOtwoCostMin", fnum(min(dO2), 1))
        M("AthreeOtwoCostMax", fnum(max(dO2), 1))
    M("AthreeSHTsameOonePoints", sum(1 for p in points if (p, "PBTI-SH-T30") in cm and (p, "PBTI") in cm
                                     and cm[(p, "PBTI-SH-T30")]["O1"] == cm[(p, "PBTI")]["O1"]))
    noeq = [p for p in points if "equivocation=0+" in p]
    M("AthreeNoEqPoints", len(noeq))
    M("AthreeNoEqIdentical", sum(1 for p in noeq if all(
        C.get((code, p, "PBTI-SH", "PBTI"), {}).get("class") == "identical" for code in OUTCOMES)))
    dly = [p for p in points if p.startswith("delay=")]
    if dly:
        M("AthreeDelayMaxOone", fnum(max(s["O1"] for (p, _a), s in cm.items() if p in dly), 2))
        dd = [cm[(p, "PBTI-SH")]["W"] - cm[(p, "PBTI")]["W"] for p in dly]
        M("AthreeDelayWcostMin", fnum(min(dd), 2))
        M("AthreeDelayWcostMax", fnum(max(dd), 2))
    # counts of classes per hypothesis/outcome
    cnt = defaultdict(lambda: defaultdict(int))
    for c in allc:
        cnt[(c["hypothesis"], c["ref"], c["outcome"])][c["class"].split(" (")[0]] += 1
    REPORT["A3_class_counts"] = {"|".join(k): dict(v) for k, v in cnt.items()}
    for (h, ref, code), v in cnt.items():
        t = f"Athree{h.replace('H3', 'H')}{ref.replace('-', '')}{code}"
        M(t + "Better", v.get("better beyond margin", 0))
        M(t + "Worse", v.get("worse beyond margin", 0))
        M(t + "Equiv", v.get("equivalent within margin", 0) + v.get("identical", 0))
    # grand means over the joint equivocation x suppression grid with equivocation > 0
    grid = [p for p in points if "missing=" in p and "equivocation=0+" not in p and "missing_long" not in p]
    for arm, at in (("PBTI", "P"), ("PBTI-SH", "SH"), ("PBTI-SH-T30", "SHT"), ("B5-hist", "Bfive"),
                    ("B5-event", "BfiveEv"), ("B5S", "BfiveS"), ("PBTI-R-hist", "PR")):
        vals = [cm[(p, arm)] for p in grid if (p, arm) in cm]
        if vals:
            M(f"Athree{at}GridOone", fnum(mean([v['O1'] for v in vals]), 2))
            M(f"Athree{at}GridW", fnum(mean([v['W'] for v in vals]), 2))
            M(f"Athree{at}GridOtwo", fnum(mean([v['O2'] for v in vals]), 1))
            M(f"Athree{at}GridNLX", fnum(mean([v['NLX'] for v in vals]), 0))
            M(f"Athree{at}GridAVfive", fnum(mean([v['AV5'] for v in vals]), 3))
    tab_a3(cm, points)
    fig_selective(cm, points)
    REPORT["A3_gates"] = gates
    return summ, allc, gates


def tab_gates():
    """comparisons of PBTI-SH that decide gates G3/G4 (grid points with PBTI O1 > 0) and G3F/G4F (FG cells)"""
    if not GATE_ROWS:
        return
    T = ["% AUTO-GENERATED by analysis/analyze_v4.py -- do not edit by hand",
         "\\setlength{\\tabcolsep}{2.6pt}",
         "\\begin{longtable}{@{}lllrrrllrl@{}}",
         "\\caption{Comparisons that decide the selective-hold gates: PBTI-SH versus the reference at the joint-grid "
         "points at which PBTI retained forgeries (G3: O1 or NLX better beyond the margin at half of these points; G4: "
         "G3 and $W$ not worse than B5-hist there) and in the factorial cells with equivocation and suppressed runs "
         "high (amendment 1; G3F: O1 or NLX better beyond the margin in at least two of the four cells; G4F: G3F and "
         "$W$ not worse than B5-hist). Means over seeds 21--40; $\\bar d$ = PBTI-SH $-$ reference; Holm within "
         "campaign and outcome. " + CLASS_LEGEND + " All comparisons: Data~S1.}\\label{tab:S-gates}\\\\",
         "\\toprule",
         "Campaign & Point or cell & Ref. & Out. & SH & Ref. & $\\bar d$ & 95\\% CI & $p_\\mathrm{Holm}$ & Class "
         "\\\\ \\midrule\\endfirsthead",
         "\\toprule",
         "Campaign & Point or cell & Ref. & Out. & SH & Ref. & $\\bar d$ & 95\\% CI & $p_\\mathrm{Holm}$ & Class "
         "\\\\ \\midrule\\endhead"]
    last = None
    for camp, lab, ref, code, c in GATE_ROWS:
        if last is not None and (camp, lab) != last:
            T.append("\\addlinespace[2pt]")
        first = (camp, lab) != last
        last = (camp, lab)
        nd = {"O1": 2, "O2": 1, "NLX": 0, "W": 2, "AV5": 3}[code]
        T.append(f"{camp if first else ''} & {lab if first else ''} & {ref} & {code} & {fnum(c['mean_arm'], nd)} & "
                 f"{fnum(c['mean_ref'], nd)} & {tnum(c['mean_d'])} & {tci(c['ci95'])} & {tp(c['p_holm'])} & "
                 f"{CLASS_CODE.get(c['class'], c['class'])} \\\\")
    T.append("\\bottomrule\\end{longtable}")
    (GEN / "tabS_v4_a3_gates.tex").write_text("\n".join(T) + "\n")


def tab_a3(cm, points):
    T = ["% AUTO-GENERATED by analysis/analyze_v4.py -- do not edit by hand",
         "\\begin{longtable}{@{}llrrrrr@{}}",
         "\\caption{A3 (seeds 21--40; 120~s production, about 2{,}880 legitimate observations per run): means per "
         "grid point and arm. eq: equivocation; supp.: suppressed messages; delay: long-delayed messages; long supp.: "
         "suppression runs of 20 messages.}\\label{tab:S-a3}\\\\",
         "\\toprule",
         "Point & Arm & O1 & O2 & NLX (rec-s) & $W$ (s) & AV5 \\\\ \\midrule\\endfirsthead",
         "\\toprule",
         "Point & Arm & O1 & O2 & NLX (rec-s) & $W$ (s) & AV5 \\\\ \\midrule\\endhead"]
    for p in points:
        first = True
        for arm in ("PBTI", "PBTI-SH", "PBTI-SH-T30", "B5-hist", "B5-event", "B5S", "PBTI-R-hist"):
            s = cm.get((p, arm))
            if not s:
                continue
            T.append(f"{plabel(p) if first else ''} & {arm} & {s['O1']:.2f} & {fnum(s['O2'], 1)} & {fnum(s['NLX'], 0)} & "
                     f"{s['W']:.2f} & {s['AV5']:.3f} \\\\")
            first = False
        T.append("\\addlinespace[2pt]")
    T.append("\\bottomrule\\end{longtable}")
    (GEN / "tabS_v4_a3.tex").write_text("\n".join(T) + "\n")



# ============================================================================ A3 amendment 1: factorial cells
FG_CELLS = ("run3", "run4", "run8", "run15")


def a3f(path):
    rows, errs = load(path)
    if not rows:
        warn("A3F (amendment 1) results missing")
        return None
    by = index(rows, errs, "A3F")
    summ = summarize(by, "A3F")
    write_csv("A3F_cells.csv", summ)
    points = sorted(by, key=lambda p: int(p[3:]))
    comps = a3_comparisons(points)
    allc = []
    for code in OUTCOMES:
        allc += compare_family(by, comps, code, "A3F", a3_hyp)
    write_csv("A3F_comparisons.csv", allc)
    M("AthreeFRuns", len(rows))
    M("AthreeFErrors", len(errs))
    M("AthreeFAudits", sum(s["audits"] for s in summ))
    M("AthreeFAuditsPass", sum(s["audits_pass"] for s in summ))
    M("AthreeFTracerMatch", sum(s["tracer_match"] for s in summ))
    cm = cellmap(summ)
    C = {(c["outcome"], c["cell"], c["arm"], c["ref"]): c for c in allc}
    fg = [p for p in FG_CELLS if p in by]
    better = [p for p in fg if any(C.get((code, p, "PBTI-SH", "PBTI"), {}).get("class") == "better beyond margin"
                                   for code in ("O1", "NLX"))]
    G3F = len(better) >= 2
    w_ok = [p for p in better if C.get(("W", p, "PBTI-SH", "B5-hist"), {}).get("class") != "worse beyond margin"]
    G4F = G3F and len(w_ok) == len(better)
    gates = {"G3F": {"holds": G3F, "fg_cells_better": better}, "G4F": {"holds": G4F, "not_worse_W": w_ok}}
    for p_ in fg:
        for code, ref in (("O1", "PBTI"), ("NLX", "PBTI"), ("W", "PBTI"), ("O2", "PBTI"), ("AV5", "PBTI"),
                          ("W", "B5-hist"), ("O2", "B5-hist")):
            c = C.get((code, p_, "PBTI-SH", ref))
            if c:
                GATE_ROWS.append(("A3F", p_ + "$^{FG}$", ref, code, c))
    M("AthreeFGThree", "holds" if G3F else "does not hold")
    M("AthreeFGFour", "holds" if G4F else "does not hold")
    M("AthreeFBetterFG", len(better))
    for arm, at in (("PBTI", "P"), ("PBTI-SH", "SH"), ("PBTI-SH-T30", "SHT"), ("B5-hist", "Bfive"),
                    ("B5-event", "BfiveEv"), ("B5S", "BfiveS"), ("PBTI-R-hist", "PR")):
        vals = [cm[(p, arm)] for p in fg if (p, arm) in cm]
        if vals:
            M(f"AthreeF{at}FGOone", fnum(mean([v['O1'] for v in vals]), 2))
            M(f"AthreeF{at}FGOtwo", fnum(mean([v['O2'] for v in vals]), 1))
            M(f"AthreeF{at}FGW", fnum(mean([v['W'] for v in vals]), 2))
            M(f"AthreeF{at}FGNLX", fnum(mean([v['NLX'] for v in vals]), 0))
            M(f"AthreeF{at}FGAVfive", fnum(mean([v['AV5'] for v in vals]), 3))
        allv = [cm[(p, arm)] for p in points if (p, arm) in cm]
        if allv:
            M(f"AthreeF{at}AllOone", fnum(mean([v['O1'] for v in allv]), 2))
            M(f"AthreeF{at}AllW", fnum(mean([v['W'] for v in allv]), 2))
    for code in ("O1", "W", "O2", "NLX"):
        for ref in ("PBTI", "B5-hist", "B5-event", "B5S", "PBTI-R-hist"):
            cl = [C.get((code, p, "PBTI-SH", ref), {}).get("class", "--") for p in fg]
            M(f"AthreeFSHvs{ref.replace('-', '')}{code}FGclasses", "; ".join(cl))
    for code in ("O1", "W", "O2", "NLX", "AV5"):
        for ref in ("PBTI", "B5-hist", "B5-event"):
            cl = [C.get((code, p, "PBTI-SH", ref), {}).get("class", "--").split(" (")[0] for p in fg]
            tag = f"AthreeFSHvs{ref.replace('-', '')}{code}FG"
            nw = "none one two three four five six seven eight".split()

            def ph(n, tot=len(cl)):  # "all four", "three of four", ... (followed by "cells" in the text)
                return f"all {nw[tot]}" if n == tot else f"{nw[n]} of {nw[tot]}"
            M(tag + "NBetter", ph(sum(c == "better beyond margin" for c in cl)))
            M(tag + "NWorse", ph(sum(c == "worse beyond margin" for c in cl)))
            M(tag + "NDiffWithin", ph(sum(c == "different, within margin" for c in cl)))
            M(tag + "NEquiv", ph(sum(c in ("equivalent within margin", "identical") for c in cl)))
            M(tag + "NInconcl", ph(sum(c == "inconclusive" for c in cl)))
    cnt = defaultdict(lambda: defaultdict(int))
    for c in allc:
        cnt[(c["hypothesis"], c["ref"], c["outcome"])][c["class"].split(" (")[0]] += 1
    REPORT["A3F_class_counts"] = {"|".join(k): dict(v) for k, v in cnt.items()}
    T = ["% AUTO-GENERATED by analysis/analyze_v4.py -- do not edit by hand",
         "\\begin{tabular}{@{}llrrrrr@{}}\\toprule",
         "Cell (high factors) & Arm & O1 & O2 & NLX (rec-s) & $W$ (s) & AV5 \\\\ \\midrule"]
    import sys as _s
    _s.path.insert(0, str(ROOT / "src"))
    from pbti.sweep import factorial_runs
    fname = {"dup": "duplicates", "reorder": "reordering", "delay": "long delay", "clock": "clock error",
             "missing": "suppressed runs"}
    hi = {f"run{r['run']}": ", ".join(fname.get(k, k) for k, v in r["levels"].items() if v > 0)
          for r in factorial_runs()}
    for p in points:
        first = True
        for arm in ("PBTI", "PBTI-SH", "PBTI-SH-T30", "B5-hist", "B5-event", "B5S", "PBTI-R-hist"):
            s_ = cm.get((p, arm))
            if not s_:
                continue
            lab = f"{p}{'$^{FG}$' if p in FG_CELLS else ''} ({hi.get(p, '')})" if first else ""
            T.append(f"{lab} & {arm} & {s_['O1']:.2f} & {fnum(s_['O2'], 1)} & {fnum(s_['NLX'], 0)} & {s_['W']:.2f} & "
                     f"{s_['AV5']:.3f} \\\\")
            first = False
        T.append("\\addlinespace[2pt]")
    T.append("\\bottomrule\\end{tabular}")
    (GEN / "tabS_v4_a3f.tex").write_text("\n".join(T) + "\n")
    fig_factorial(cm, points)
    REPORT["A3F_gates"] = gates
    return summ, allc, gates


def fig_factorial(cm, points):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    # PBTI-R-hist is identical to PBTI in every cell (no quarantine case to review): omitted, stated in the caption
    arms = (("PBTI", "o"), ("PBTI-SH", "D"), ("PBTI-SH-T30", "d"), ("B5-hist", "^"), ("B5-event", "v"), ("B5S", "s"))
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.6))
    x = np.arange(len(points))
    wdt = 0.13
    for ax, code, lab in ((axes[0], "O1", "retained forgeries O1 (per run)"), (axes[1], "W", "mean withheld time W (s/obs.)")):
        for k, (arm, mk) in enumerate(arms):
            ys = [cm.get((p, arm), {}).get(code, math.nan) for p in points]
            ax.bar(x + (k - 2.5) * wdt, ys, width=wdt * 0.9, color=COL[arm], label=arm, edgecolor="white", linewidth=0.4)
        top = max([v for p in points for a, _m in arms for v in [cm.get((p, a), {}).get(code, math.nan)]
                   if v == v] or [1.0])
        ax.set_ylim(0, top * 1.15 if top > 0 else 1.0)
        if code == "O1" and all(cm.get((p, "PBTI-SH"), {}).get("O1", 1) == 0 for p in points):
            ax.text(0.01, 0.97, "PBTI-SH: 0 in every cell", transform=ax.transAxes, fontsize=6.5, va="top",
                    color="#52514e")
        ax.set_xticks(x)
        ax.set_xticklabels([p.replace("run", "r") + ("*" if p in FG_CELLS else "") for p in points], fontsize=7)
        ax.set_xlabel("factorial cell with equivocation high (* also suppressed runs high)", fontsize=7, color="#52514e")
        ax.set_ylabel(lab, fontsize=7, color="#52514e")
        _style(ax)
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=6, fontsize=6.5, frameon=False, bbox_to_anchor=(0.5, -0.06))
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    fig.savefig(FIG / "fig_v4_factorial.pdf", bbox_inches="tight")
    (FIG / "png").mkdir(exist_ok=True)
    fig.savefig(FIG / "png" / "fig_v4_factorial.png", dpi=200, bbox_inches="tight")
    plt.close(fig)

# ============================================================================ A3 scenario controls
def a3s(path, a0_summ):
    rows, errs = load(path)
    by = index(rows, errs, "A3S")
    summ = summarize(by, "A3S")
    write_csv("A3S_cells.csv", summ)
    M("AthreeSRuns", len(rows))
    M("AthreeSErrors", len(errs))
    a0m = cellmap(a0_summ)
    cm = cellmap(summ)
    lines = []
    more_o1 = []
    for sc in sorted(by):
        p = a0m.get((sc, "PBTI"))
        s = cm.get((sc, "PBTI-SH"))
        if not (p and s):
            continue
        lines.append({"scenario": sc, "PBTI_O1": p["O1"], "SH_O1": s["O1"], "PBTI_O2": p["O2"], "SH_O2": s["O2"],
                      "PBTI_W": p["W"], "SH_W": s["W"], "PBTI_AV5": p["AV5"], "SH_AV5": s["AV5"],
                      "PBTI_NLX": p["NLX"], "SH_NLX": s["NLX"]})
        if s["O1"] > p["O1"] + 1e-9:
            more_o1.append(sc)
    write_csv("A3S_vs_A0_PBTI.csv", lines)
    # descriptive: workloads in which PBTI-SH has the same means as PBTI on every primary outcome
    same = [ln["scenario"] for ln in lines
            if all(abs(cm[(ln["scenario"], "PBTI-SH")][k] - a0m[(ln["scenario"], "PBTI")][k]) < 1e-12
                   for k in ("O1", "O2", "NLX", "W", "AV5"))]
    M("AthreeSN", len(lines))
    M("AthreeSSameN", len(same))
    diff = [("the mixed workload" if ln["scenario"] == "S99_mixed" else SHORT.get(ln["scenario"], ln["scenario"]))
            for ln in sorted(lines, key=lambda x: (x["scenario"] == "S99_mixed", x["scenario"]))
            if ln["scenario"] not in same]
    M("AthreeSDiffScen", (", ".join(diff[:-1]) + " and " + diff[-1]) if len(diff) > 1 else (diff[0] if diff else "none"))
    M("AthreeSMoreOoneN", len(more_o1))
    M("AthreeSMoreOoneScen", ", ".join(SHORT.get(s, s) for s in more_o1) if more_o1 else "none")
    for sc, tag in (("S05_stolen_key", "Efive"), ("S08_seq_reuse_bug", "Eeight"), ("S99_mixed", "Mixed"),
                    ("S14_revocation", "Efourteen"), ("S11_disconnect_recover", "Eeleven"),
                    ("S12_beyond_horizon", "Eelevenb")):
        for arm, at in (("PBTI-SH", "SH"), ("PBTI-SH-T30", "SHT")):
            s = cm.get((sc, arm))
            if s:
                M(f"AthreeS{tag}{at}Oone", fnum(s["O1"], 1))
                M(f"AthreeS{tag}{at}Otwo", fnum(s["O2"], 1))
                M(f"AthreeS{tag}{at}W", fnum(s["W"], 2))
                M(f"AthreeS{tag}{at}AVfive", fnum(s["AV5"], 3))
                M(f"AthreeS{tag}{at}NLX", fnum(s["NLX"], 0))
    REPORT["A3S_more_O1_than_PBTI"] = more_o1
    T = ["% AUTO-GENERATED by analysis/analyze_v4.py -- do not edit by hand",
         "\\begin{tabular}{@{}lrrrrrrrrrr@{}}\\toprule",
         " & \\multicolumn{2}{c}{O1} & \\multicolumn{2}{c}{O2} & \\multicolumn{2}{c}{NLX (rec-s)} & "
         "\\multicolumn{2}{c}{$W$ (s)} & \\multicolumn{2}{c}{AV5} \\\\ \\cmidrule(lr){2-3}\\cmidrule(lr){4-5}"
         "\\cmidrule(lr){6-7}\\cmidrule(lr){8-9}\\cmidrule(lr){10-11}",
         "Scenario & PBTI & SH & PBTI & SH & PBTI & SH & PBTI & SH & PBTI & SH \\\\ \\midrule"]

    def row(lab, pp, ss):
        return (f"{lab} & {fnum(pp['O1'], 1)} & {fnum(ss['O1'], 1)} & {fnum(pp['O2'], 1)} & {fnum(ss['O2'], 1)} & "
                f"{fnum(pp['NLX'], 0)} & {fnum(ss['NLX'], 0)} & {pp['W']:.2f} & {ss['W']:.2f} & {pp['AV5']:.3f} & "
                f"{ss['AV5']:.3f} \\\\")
    for ln in sorted(lines, key=lambda x: (x["scenario"] == "S99_mixed", x["scenario"])):
        sc = ln["scenario"]
        T.append(row(SHORT.get(sc, sc), a0m[(sc, "PBTI")], cm[(sc, "PBTI-SH")]))
    t30 = [sc for sc in sorted(by, key=lambda x: (x == "S99_mixed", x)) if (sc, "PBTI-SH-T30") in cm and (sc, "PBTI") in a0m]
    if t30:
        T.append("\\midrule")
        T.append("\\multicolumn{11}{@{}l}{SH = PBTI-SH-T30 (30~s timeout):} \\\\")
        for sc in t30:
            T.append(row(SHORT.get(sc, sc), a0m[(sc, "PBTI")], cm[(sc, "PBTI-SH-T30")]))
    T.append("\\bottomrule\\end{tabular}")
    (GEN / "tabS_v4_a3_scenarios.tex").write_text("\n".join(T) + "\n")
    return summ


# ============================================================================ A5 and A4
def a5():
    p = ROOT / "results" / "v4" / "summary" / "A5_lifecycle_matrix.json"
    if not p.exists():
        warn("A5 matrix missing")
        return
    rows = json.loads(p.read_text())
    M("AfiveRows", len(rows))
    T = ["% AUTO-GENERATED by analysis/analyze_v4.py -- do not edit by hand",
         "\\begin{tabularx}{\\linewidth}{@{}>{\\raggedright\\arraybackslash}p{4.3cm}"
         "*{3}{>{\\centering\\arraybackslash}X}@{}}\\toprule",
         "Case (PBTI; B5 identical) & none & discretionary (V3) & witness \\\\ \\midrule"]
    names = {"legit_buffered_witnessed": "Legitimate buffered record, witnessed before $t_c$",
             "backdated_forgery_witness_sees_late": "Backdated forgery, witness sees it after $t_c$",
             "backdated_forgery_not_witnessed": "Backdated forgery, never witnessed",
             "forgery_with_contradictory_successor": "Forgery contradicted by an admitted successor",
             "legit_buffered_witness_outage": "Legitimate record, witness outage",
             "stale_reviewer_snapshot": "Decision on a superseded snapshot",
             "revoked_reviewer": "Reviewer key revoked",
             "stale_ts_release_after_origin_revoked": "STALE\\_TS case, origin revoked before release",
             "release_then_later_taint": "Released, later revocation covers commit time",
             "full_sequence_revised_taint": "Released under revoked key, then earlier $t_{comp}$ revision"}

    def cellv(r):
        if r["malicious_authoritative"]:
            return "\\textbf{forgery authoritative}"
        if r["genuine_recovered"]:
            return "recovered" + (" (tainted)" if r["tainted_end"] else "")
        if r["legitimate"] and r["tainted_end"]:
            return "released, then tainted" + ("; window corrected" if r.get("window_corrected") else "")
        if r["legitimate"]:
            return "withheld (" + str(r["case_state"]).lower() + ")"
        return "excluded (" + str(r["case_state"]).lower() + ")"
    pb = {(r["case"], r["policy"]): r for r in rows if r["pipeline"] == "PBTI" and r["case"] in names}
    b5 = {(r["case"], r["policy"]): r for r in rows if r["pipeline"] == "B5" and r["case"] in names}
    same = all(cellv(pb[k]) == cellv(b5[k]) for k in pb if k in b5)
    M("AfivePBTIBfiveSame", "identical" if same else "different")
    for case, nm in names.items():
        T.append(nm + " & " + " & ".join(cellv(pb[(case, pol)]) for pol in ("none", "discretionary", "witness"))
                 + " \\\\")
    iv = [r for r in rows if r["case"] == "legit_buffered_witnessed_interval" and r["pipeline"] == "PBTI"]
    T.append("\\midrule")
    T.append("Interval width $t_{high}-t_{low}$ (witness policy) & \\multicolumn{3}{l}{" + "; ".join(
        f"{r['width_s']:g}\\,s: {'recovered' if r['genuine_recovered'] else 'withheld'}" for r in iv) + "} \\\\")
    T.append("\\bottomrule\\end{tabularx}")
    (GEN / "tabS_v4_a5.tex").write_text("\n".join(T) + "\n")
    rec = [r for r in iv if r["genuine_recovered"]]
    M("AfiveMaxRecoveredWidth", f"{max(r['width_s'] for r in rec):g}" if rec else "none")
    REPORT["A5"] = {"rows": len(rows), "pbti_b5_identical": same}


def a4():
    p = ROOT / "results" / "v4" / "formal" / "v4_locality_lifecycle_check.json"
    if not p.exists():
        warn("A4 check missing")
        return
    r = json.loads(p.read_text())
    M("AfourAllPass", "all pass" if r["all_pass"] else "violations")
    m = r.get("M", {})
    M("AfourMcases", f"{sum(v['cases'] for v in m.values()):,}".replace(",", "{,}"))
    L = r.get("L", {})
    if L:
        M("AfourLexhaustive", f"{L['exhaustive_U2_single']['cases']:,}".replace(",", "{,}"))
        M("AfourLrandom", f"{L['random_batches_2_3']['cases']:,}".replace(",", "{,}"))
    C = r.get("C", {})
    if C:
        M("AfourCexhaustive", f"{C['exhaustive']['sequences']:,}".replace(",", "{,}"))
        M("AfourCrandom", f"{C['random']['sequences']:,}".replace(",", "{,}"))
        M("AfourCops", f"{C['stats']['operations']:,}".replace(",", "{,}"))
        M("AfourCstale", C["stats"]["outcomes"].get("STALE_REVIEW", 0))
        M("AfourCreleased", C["stats"]["outcomes"].get("RELEASED", 0))
    REPORT["A4"] = {"all_pass": r["all_pass"], "source_unchanged": r.get("source_unchanged_during_run")}


# ============================================================================ figures
COL = {"PBTI": "#2a78d6", "B5": "#1baf7a", "PBTI-R": "#184f95", "PBTI-SH": "#6250d6", "PBTI-SH-T30": "#e87ba4",
       "B5-hist": "#1baf7a", "B5-event": "#008300", "B5S": "#eda100", "PBTI-R-hist": "#184f95"}


def _style(ax):
    ax.grid(axis="y", color="#e4e3df", linewidth=0.6)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(labelsize=7, colors="#52514e")


def fig_delay(cm, by, cells):
    if not cells:
        warn("A1 figure: no cells")
        return
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    Rs = [0, 1, 5, 60]
    xpos = {0: 0, 1: 1, 5: 2, 60: 3}
    fig, axes = plt.subplots(1, len(cells), figsize=(7.2, 2.3), sharey=False)
    axes = np.atleast_1d(axes)
    for ax, sc in zip(axes, cells):
        for fam, col, mk, cad, ls in (("B5", COL["B5"], "^", 1, "-"), ("B5", COL["B5"], "^", 10, ":"),
                                      ("PBTI-R", COL["PBTI-R"], "P", 1, "-"), ("PBTI-R", COL["PBTI-R"], "P", 10, ":")):
            ys, lo, hi = [], [], []
            for R in Rs:
                rows = list(by[sc].get(f"{fam}-d{R}c{cad}", {}).values())
                v = [W_of(r) for r in rows]
                m = mean(v)
                ci = boot(v, key=f"fig|{sc}|{fam}|{R}|{cad}")[95] if len(v) > 1 else (m, m)
                ys.append(m)
                lo.append(m - ci[0])
                hi.append(ci[1] - m)
            ax.errorbar([xpos[R] + (0.08 if cad == 10 else 0) for R in Rs], ys, yerr=[lo, hi], color=col,
                        marker=mk, markersize=4.5, linewidth=1.2, linestyle=ls, capsize=2,
                        markerfacecolor=col if cad == 1 else "white", label=f"{fam} defer, {cad} s cadence")
            if cad == 10:
                continue
            ev = cm.get((sc, f"{fam}-event"))
            if ev:
                ax.plot([-0.6], [ev["W"]], marker=mk, color=col, markersize=5.5, markerfacecolor="white",
                        linestyle="none", label=f"{fam} event-driven")
            hs = cm.get((sc, f"{fam}-hist"))
            if hs:
                ax.plot([3.6], [hs["W"]], marker=mk, color=col, markersize=5.5, markerfacecolor="#f0efec",
                        markeredgewidth=1.4, linestyle="none", label=f"{fam} V3 reviewer (60 s/10 s)")
        p = cm.get((sc, "PBTI"))
        if p:
            ax.axhline(p["W"], color=COL["PBTI"], linewidth=1.0, linestyle="--", label="PBTI (no reviewer)")
        ax.set_xticks([-0.6, 0, 1, 2, 3, 3.6])
        ax.set_xticklabels(["ev", "0", "1", "5", "60", "V3"], fontsize=7)
        ax.set_title(SHORT.get(sc, sc), fontsize=8, color="#0b0b0b")
        ax.set_xlabel("min. review age R (s)", fontsize=7, color="#52514e")
        _style(ax)
    axes[0].set_ylabel("mean withheld time W (s/obs.)", fontsize=7, color="#52514e")
    for ax in axes:
        for xv in (-0.3, 3.3):
            ax.axvline(xv, color="#e4e3df", linewidth=0.8, zorder=0)
    hd = {}
    for ax in axes:
        for h_, l_ in zip(*ax.get_legend_handles_labels()):
            hd.setdefault(l_, h_)
    order = ["B5 defer, 1 s cadence", "B5 defer, 10 s cadence", "B5 event-driven", "B5 V3 reviewer (60 s/10 s)",
             "PBTI-R defer, 1 s cadence", "PBTI-R defer, 10 s cadence", "PBTI-R event-driven",
             "PBTI-R V3 reviewer (60 s/10 s)", "PBTI (no reviewer)"]
    labs = [o for o in order if o in hd]
    fig.legend([hd[o] for o in labs], labs, loc="lower center", ncol=5, fontsize=6.5, frameon=False,
               bbox_to_anchor=(0.5, -0.1))
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / "fig_v4_delay.pdf", bbox_inches="tight")
    (FIG / "png").mkdir(exist_ok=True)
    fig.savefig(FIG / "png" / "fig_v4_delay.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def fig_selective(cm, points):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    sup = [0, 0.01, 0.05, 0.1]
    pts = [f"equivocation=0.05+missing={s:g}" for s in sup]
    if not any((p, "PBTI") in cm for p in pts):
        warn("A3 figure: grid points missing")
        return
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.4))
    arms = (("PBTI", "o", "-"), ("PBTI-SH", "D", "-"), ("PBTI-SH-T30", "d", "--"), ("B5-hist", "^", "-"),
            ("B5-event", "v", "--"), ("B5S", "s", ":"), ("PBTI-R-hist", "P", ":"))
    for ax, code, lab in ((axes[0], "O1", "retained forgeries O1 (per run)"), (axes[1], "W", "mean withheld time W (s/obs.)")):
        for arm, mk, ls in arms:
            ys = [cm.get((p, arm), {}).get(code, math.nan) for p in pts]
            ax.plot([s * 100 for s in sup], ys, marker=mk, linestyle=ls, color=COL[arm], linewidth=1.2,
                    markersize=4.5, label=arm)
        ax.set_xlabel("suppressed messages (%) at 5 % equivocation", fontsize=7, color="#52514e")
        ax.set_ylabel(lab, fontsize=7, color="#52514e")
        _style(ax)
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=7, fontsize=6.5, frameon=False, bbox_to_anchor=(0.5, -0.06))
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    fig.savefig(FIG / "fig_v4_selective.pdf", bbox_inches="tight")
    (FIG / "png").mkdir(exist_ok=True)
    fig.savefig(FIG / "png" / "fig_v4_selective.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


# ============================================================================ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-map", default="", help="A0=path,A1=path,A3=path,A3S=path (pilots); default results/v4/raw")
    ap.add_argument("--tag", default="", help="suffix for the report file (pilot runs)")
    a = ap.parse_args()
    paths = {"A0": RAW4 / "A0_core.jsonl", "A1": RAW4 / "A1_review.jsonl", "A3": RAW4 / "A3_selective.jsonl",
             "A3S": RAW4 / "A3_scenarios.jsonl", "A3F": RAW4 / "A3_factorial.jsonl",
             "A0cmp": SUM4 / "A0_comparison.json"}
    for kv in filter(None, a.raw_map.split(",")):
        k, v = kv.split("=", 1)
        paths[k] = Path(v)
    GEN.mkdir(parents=True, exist_ok=True)
    a0s = a0(paths["A0"], paths["A0cmp"])
    a1(paths["A1"])
    a3(paths["A3"])
    a3s(paths["A3S"], a0s)
    a3f(paths["A3F"])
    a5()
    a4()
    tab_gates()
    words = "Zero One Two Three Four Five Six Seven Eight Nine".split()
    seen = set()
    lines = ["% AUTO-GENERATED by analysis/analyze_v4.py from results/v4 -- do not edit by hand"]
    for k, v in sorted(VM.items()):
        safe = "".join(words[int(ch)] if ch.isdigit() else ch for ch in k if ch.isalnum())
        if safe in seen:
            raise SystemExit(f"macro collision {safe}")
        seen.add(safe)
        lines.append(f"\\newcommand{{\\W{safe}}}{{{v}}}")
    (GEN / "v4_macros.tex").write_text("\n".join(lines) + "\n")
    dv = ROOT / "research" / "V4" / "DEVIATIONS_V4.json"  # deviations from the preregistration (prereg Section 9)
    if dv.exists():
        REPORT["deviations"] = json.loads(dv.read_text())
    SUM4.mkdir(parents=True, exist_ok=True)
    (SUM4 / f"v4_analysis_report{a.tag}.json").write_text(json.dumps(REPORT, indent=1, default=str))
    print(f"wrote {len(VM)} V4 macros; warnings {len(REPORT['warnings'])}; exclusions {len(REPORT['exclusions'])}")


if __name__ == "__main__":
    main()
