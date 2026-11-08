#!/usr/bin/env python3
"""V3 analysis: preregistered B5 comparison (X1), mixed workload (X2), sweep (X3), factorial (X4), SKAB replay (X5),
release workflow, batching/worker benchmark, 30-repetition end-to-end latency, SKAB end-to-end replay, policy parity.

Reads results/raw/*.jsonl (revision-2 files and the v3_* files) and writes
  paper/generated/v3_macros.tex           LaTeX macros \\V...  (every V3 number quoted in the manuscript)
  paper/generated/tab*_v3_*.tex           tables
  paper/figures/fig_v3_*.pdf              figures
  results/summary/v3_*.csv|json           machine-readable summaries (Data S1)
Statistics follow research/V3/PREREGISTRATION.md: two-sided Wilcoxon signed-rank on paired seeds (zero differences
dropped), pairs identical in every seed reported as identical and entered with p = 1, Holm over the 30 tests of an
outcome; percentile-bootstrap 95 % CIs (10,000 resamples); wall-clock metrics: Mann-Whitney U, Holm, Cliff's delta.
"""
from __future__ import annotations

import csv
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze as A  # noqa: E402  (helpers, plotting style, revision-2 loaders)
from scipy import stats  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

RAW, GEN, FIG, SUM, ROOT = A.RAW, A.GEN, A.FIG, A.SUM, A.ROOT
fmt, ptex, boot_ci, holm = A.fmt, A.ptex, A.boot_ci, A.holm
VM: dict[str, str] = {}
REPORT: dict = {}
WARN: list[str] = []
SCEN = list(A.SCEN_LABEL)
SHORT = {k: v.split(" ")[0] for k, v in A.SCEN_LABEL.items()}
OUT = {"O1": "nonlegit_auth", "O2": "legit_missing"}
THR = {"O1": 1.0, "O2": 72.0}
COL = {"PBTI": "#2a78d6", "B4": "#eb6834", "B5": "#1baf7a", "B5S": "#eda100", "B2": "#7a52c7", "PBTI-R": "#184f95"}
MRK = {"PBTI": "o", "B4": "s", "B5": "^", "B5S": "D", "B2": "v", "PBTI-R": "P"}


def M(k, v):
    VM[k] = str(v)


def warn(msg):
    WARN.append(msg)
    print("WARNING", msg, file=sys.stderr)


def rows_of(fname):
    p = RAW / fname
    if not p.exists():
        warn(f"{fname} missing")
        return []
    rows = [json.loads(l) for l in open(p) if l.strip()]
    bad = [r for r in rows if "error" in r]
    if bad:
        warn(f"{fname}: {len(bad)} error rows excluded")
    return [r for r in rows if "error" not in r]


def mean(x):
    x = [v for v in x if v is not None and not (isinstance(v, float) and math.isnan(v))]
    return float(np.mean(x)) if x else math.nan


def f1(x):
    return fmt(x, 1)


def write_csv(name, rows):
    if not rows:
        return
    keys = list(rows[0].keys())
    with open(SUM / name, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow(r)


# ============================================================================ X1 preregistered comparison
def x1():
    v2 = A.load("scenarios")
    v3 = rows_of("v3_scenarios_b5.jsonl") + rows_of("v3_scenarios_pbtir.jsonl")
    by = defaultdict(dict)
    for r in v2 + v3:
        key = (r["scenario"], r["system"])
        if r["seed"] in by[key]:
            raise SystemExit(f"duplicate {key} seed {r['seed']}")
        by[key][r["seed"]] = r
    REPORT["x1_cells"] = {f"{k[0]}|{k[1]}": len(v) for k, v in sorted(by.items())}
    M("XOneRuns", fmt(len(v3)))
    aud = [r for r in v3 if "audit_pass" in r]
    REPORT["x1_audits"] = {"runs": len(aud), "pass": sum(bool(r["audit_pass"]) for r in aud),
                           "failed": [(r["scenario"], r["system"], r["seed"], r.get("audit_findings")) for r in aud if not r["audit_pass"]]}
    ms = {sc: mean([r["legit_missing"] for r in by.get((sc, "B5S"), {}).values()]) for sc in SCEN if by.get((sc, "B5S"))}
    if ms:
        top = max(ms, key=lambda k: ms[k])
        M("BFiveSMaxMissing", f1(ms[top]))
        M("BFiveSMaxMissingScen", SHORT[top])
    tests = []
    for o, metric in OUT.items():
        fam = []
        for sc in SCEN:
            for comp in ("B5", "B5S"):
                a, b = by.get((sc, "PBTI"), {}), by.get((sc, comp), {})
                seeds = sorted(set(a) & set(b))
                pb = np.array([a[s][metric] for s in seeds], float)
                cb = np.array([b[s][metric] for s in seeds], float)
                if len(seeds) == 0:
                    fam.append(dict(outcome=o, scenario=sc, comp=comp, n=0, mean_pbti=math.nan, mean_comp=math.nan,
                                    mean_diff=math.nan, ci_lo=math.nan, ci_hi=math.nan, p=1.0, rb=0.0, kind="missing",
                                    n_identical=0, practical=False))
                    continue
                d = cb - pb
                p, rb, kind = A.wilcoxon_paired(cb, pb)
                lo, hi = boot_ci(d)
                fam.append(dict(outcome=o, scenario=sc, comp=comp, n=len(seeds), mean_pbti=float(pb.mean()),
                                mean_comp=float(cb.mean()), mean_diff=float(d.mean()), ci_lo=lo, ci_hi=hi, p=p, rb=rb,
                                kind=kind, n_identical=int((d == 0).sum()), practical=bool(abs(d.mean()) >= THR[o])))
        adj = holm(np.array([t["p"] for t in fam]))
        for t, q in zip(fam, adj):
            t["p_holm"] = float(q)
            t["sig"] = bool(q < 0.05)
        tests += fam
    complete = all(t["n"] == 20 for t in tests)
    M("XOneComplete", "yes" if complete else "no")
    if not complete:
        warn("X1 incomplete: " + ", ".join(f"{t['scenario']}/{t['comp']}:{t['n']}" for t in tests if t["n"] != 20 and t["outcome"] == "O1"))
    write_csv("v3_x1_preregistered_tests.csv", tests)
    T = {(t["outcome"], t["scenario"], t["comp"]): t for t in tests}
    # ---- predictions
    p1_ident = [sc for sc in SCEN if T[("O1", sc, "B5")]["kind"] == "identical"]
    p1_fail = [sc for sc in SCEN if T[("O1", sc, "B5")]["sig"] or T[("O1", sc, "B5")]["practical"]]
    P1 = len(p1_fail) == 0
    p2 = {sc: (T[("O2", sc, "B5S")]["mean_diff"] >= THR["O2"] and T[("O2", sc, "B5S")]["sig"]) for sc in ("S05_stolen_key", "S08_seq_reuse_bug")}
    P2 = all(p2.values())
    p3_exc = [sc for sc in SCEN if abs(T[("O2", sc, "B5")]["mean_diff"]) >= THR["O2"]]
    b5rows = [r for (sc, s), d in by.items() if s == "B5" for r in d.values()]
    rec = [r for r in b5rows if r.get("recovered_n", 0) > 0]
    p50min = min((r["recovery_ms_p50"] for r in rec), default=math.nan)
    lat_ok = all(r["recovery_ms_p50"] >= 60_000 for r in rec)
    P3 = len(p3_exc) == 0 and lat_ok
    # P4: B4 vs PBTI on O1 in E5 and E14 (Holm over the two tests)
    p4 = {}
    for sc in ("S05_stolen_key", "S14_revocation"):
        a, b = by.get((sc, "PBTI"), {}), by.get((sc, "B4"), {})
        seeds = sorted(set(a) & set(b))
        x = np.array([b[s]["nonlegit_auth"] for s in seeds], float)
        y = np.array([a[s]["nonlegit_auth"] for s in seeds], float)
        p, rb, kind = A.wilcoxon_paired(x, y)
        p4[sc] = dict(mean_diff=float((x - y).mean()) if seeds else math.nan, p=p, rb=rb, n=len(seeds))
    adj = holm(np.array([v["p"] for v in p4.values()]))
    for (k, v), q in zip(p4.items(), adj):
        v["p_holm"] = float(q)
        v["holds"] = bool(v["mean_diff"] >= THR["O1"] and q < 0.05)
    P4 = all(v["holds"] for v in p4.values())
    # ---- decision rules
    d2 = [(t["scenario"], t["comp"], t["outcome"], t["mean_diff"]) for t in tests
          if t["n"] and t["mean_diff"] < 0 and (t["sig"] or t["practical"])]
    d3 = [(t["scenario"], t["mean_diff"]) for t in tests if t["outcome"] == "O1" and t["comp"] == "B5" and t["n"]
          and t["mean_diff"] > 0 and (t["sig"] or t["practical"])]
    REPORT["predictions"] = {"P1": {"holds": P1, "identical_in_every_seed": len(p1_ident), "failing": p1_fail},
                             "P2": {"holds": P2, "per_scenario": p2},
                             "P3": {"holds": P3, "exceptions_O2": [(sc, T[("O2", sc, "B5")]["mean_diff"]) for sc in p3_exc],
                                    "recovery_p50_min_ms": p50min, "all_recovered_after_R": lat_ok, "runs_with_recovery": len(rec)},
                             "P4": {"holds": P4, "per_scenario": p4},
                             "D1_condition_met": bool(P1 and P3), "D2_cases": d2, "D3_cases": d3}
    M("POneHolds", "held" if P1 else "did not hold")
    M("POneIdentical", fmt(len(p1_ident)))
    M("PTwoHolds", "held" if P2 else "did not hold")
    M("PThreeHolds", "held" if P3 else "did not hold")
    M("PThreeExceptions", ", ".join(SHORT[sc] for sc in p3_exc) if p3_exc else "none")
    M("PFourHolds", "held" if P4 else "did not hold")
    M("DOneMet", "met" if P1 and P3 else "not met")
    M("RecoveryPFiftyMinS", fmt(p50min / 1000, 1) if p50min == p50min else "--")
    for o in OUT:
        for comp in ("B5", "B5S"):
            fam = [t for t in tests if t["outcome"] == o and t["comp"] == comp]
            M(f"{o}{comp}Identical", fmt(sum(t["kind"] == "identical" for t in fam)))
            M(f"{o}{comp}Sig", fmt(sum(t["sig"] for t in fam)))
            M(f"{o}{comp}Practical", fmt(sum(t["practical"] for t in fam)))
    # per-scenario macros for the text
    for sc in SCEN:
        code = sc[:3]
        for s in ("PBTI", "B4", "B5", "B5S", "PBTI-R"):
            d = by.get((sc, s))
            if not d:
                continue
            rr = list(d.values())
            tag = s.replace("-", "")
            for k in ("nonlegit_auth", "legit_missing", "legit_quarantined", "recovered_n", "holds", "cv_wrong_rate",
                      "store_bytes_per_reach", "fork_events"):
                v = mean([r.get(k, 0) for r in rr])
                M(f"{code}{tag}{k.replace('_', '')}", f1(v * 100) if k == "cv_wrong_rate" else f1(v))
            p50 = [r["recovery_ms_p50"] / 1000 for r in rr if r.get("recovered_n", 0) > 0]
            p95 = [r["recovery_ms_p95"] / 1000 for r in rr if r.get("recovered_n", 0) > 0]
            M(f"{code}{tag}recpfifty", f1(mean(p50)) if p50 else "--")
            M(f"{code}{tag}recpninetyfive", f1(mean(p95)) if p95 else "--")
            M(f"{code}{tag}reviewrejected", f1(mean([r.get("review[REJECTED]", 0) for r in rr])))
            M(f"{code}{tag}lostunrecoverable", f1(mean([r.get("legit_lost_unrecoverable", 0) for r in rr])))
    # held-observation totals for B5 across X1
    held = {sc: mean([r.get("holds", 0) for r in by.get((sc, "B5"), {}).values()]) for sc in SCEN}
    M("BFiveHeldScenarios", fmt(sum(1 for v in held.values() if v and v > 0)))
    outcomes_full_csv(by)
    tab_outcomes_v3(by, T)
    tabS_b5(by, T)
    tabS_tests(tests)
    return by, T


def outcomes_full_csv(by):
    """Data S1 (replaces the printed Table S6): per scenario and pipeline, means and 95 % bootstrap CIs."""
    out = []
    metrics = ("n_reachable", "nonlegit_auth", "legit_missing", "legit_quarantined", "dup_auth", "win_corrupt",
               "win_incomplete", "cv_wrong_rate", "holds", "recovered_n", "store_bytes_per_reach")
    for sc in SCEN:
        for s in ("PBTI", "B1", "B2", "B3", "B4", "B5", "B5S", "PBTI-R"):
            d = by.get((sc, s))
            if not d:
                continue
            row = {"scenario": sc, "label": A.SCEN_LABEL[sc], "pipeline": s, "seeds": len(d)}
            for m in metrics:
                x = [r.get(m, 0) or 0 for r in d.values()]
                lo, hi = boot_ci(x)
                row[m] = mean(x)
                row[m + "_ci_lo"], row[m + "_ci_hi"] = lo, hi
            out.append(row)
    write_csv("v3_outcomes_full.csv", out)
    pt = SUM / "scenarios_paired_tests.json"
    if pt.exists():
        write_csv("v2_paired_tests.csv", json.loads(pt.read_text()))


def tab_outcomes_v3(by, T):
    systems = ["B1", "B2", "B3", "B4", "B5", "B5S", "PBTI"]
    lines = [r"\begin{tabular}{l" + "r" * 14 + "}", r"\toprule",
             r"& \multicolumn{7}{c}{\textbf{Non-legitimate authoritative} (mean/run)} & \multicolumn{7}{c}{\textbf{Legitimate missing} (mean/run)}\\",
             r"\cmidrule(lr){2-8}\cmidrule(lr){9-15}",
             r"\textbf{Scen.} & " + " & ".join(s.replace("B5S", "B5s") for s in systems) + " & "
             + " & ".join(s.replace("B5S", "B5s") for s in systems) + r"\\", r"\midrule"]
    for sc in SCEN:
        if sc == "S01_normal":
            continue
        cells = []
        for metric, o in (("nonlegit_auth", "O1"), ("legit_missing", "O2")):
            for s in systems:
                d = by.get((sc, s))
                if not d:
                    cells.append("--")
                    continue
                v = mean([r[metric] for r in d.values()])
                txt = fmt(v)
                if s in ("B5", "B5S"):
                    t = T.get((o, sc, s))
                    if t and t["sig"]:
                        txt += "$^{*}$"
                if metric == "legit_missing" and s == "PBTI" and mean([r.get("legit_quarantined", 0) for r in d.values()]) > 0:
                    txt += r"$^{\dagger}$"
                cells.append(txt)
        lines.append(SHORT[sc] + " & " + " & ".join(cells) + r"\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (GEN / "tab_outcomes_v3.tex").write_text("\n".join(lines))


def tabS_b5(by, T):
    """B5 secondary outcomes: held observations, release latency, quarantine, current-value error, storage."""
    lines = [r"\begin{tabular}{lrrrrrrrr}", r"\toprule",
             r"\textbf{Scen.} & \textbf{Forks} & \textbf{Held} & \textbf{Released} & \textbf{Lat.\ p50 (s)} & \textbf{Lat.\ p95 (s)} & \textbf{Quar.} & \textbf{CV wrong \%} & \textbf{B/obs.}\\",
             r"\midrule"]
    for sc in SCEN:
        for s in ("PBTI", "B5", "B5S", "PBTI-R"):
            d = by.get((sc, s))
            if not d:
                continue
            rr = list(d.values())
            if s != "PBTI" and all(r.get("holds", 0) == 0 and r.get("recovered_n", 0) == 0 and r.get("legit_quarantined", 0) == 0 for r in rr) \
                    and s != "PBTI-R":
                continue
            if s == "PBTI" and not any(r.get("legit_quarantined", 0) for r in rr) and not any(
                    any(x.get("holds", 0) or x.get("recovered_n", 0) for x in by.get((sc, b), {}).values()) for b in ("B5", "B5S")):
                continue
            p50 = [r["recovery_ms_p50"] / 1000 for r in rr if r.get("recovered_n", 0) > 0]
            p95 = [r["recovery_ms_p95"] / 1000 for r in rr if r.get("recovered_n", 0) > 0]
            lines.append(f"{SHORT[sc]} {s.replace('B5S', 'B5s')} & {f1(mean([r.get('fork_events', 0) for r in rr]))} & "
                         f"{f1(mean([r.get('holds', 0) for r in rr]))} & {f1(mean([r.get('recovered_n', 0) for r in rr]))} & "
                         f"{f1(mean(p50)) if p50 else '--'} & {f1(mean(p95)) if p95 else '--'} & "
                         f"{f1(mean([r.get('legit_quarantined', 0) for r in rr]))} & {fmt(mean([r.get('cv_wrong_rate', 0) for r in rr]) * 100, 2)} & "
                         f"{fmt(mean([r.get('store_bytes_per_reach', 0) for r in rr]), 0)}\\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (GEN / "tabS_v3_b5.tex").write_text("\n".join(lines))


def tabS_tests(tests):
    lines = [r"\begin{tabular}{llrrrrrl}", r"\toprule",
             r"\textbf{Outcome} & \textbf{Scen.} & \textbf{PBTI} & \textbf{Comp.} & \textbf{Diff.\ [95\% CI]} & \textbf{$r_\mathrm{rb}$} & \textbf{$p_\mathrm{Holm}$} & \textbf{Practical}\\",
             r"\midrule"]
    for t in tests:
        if t["kind"] != "tested":
            continue
        lines.append(f"{t['outcome']} & {SHORT[t['scenario']]} vs {t['comp'].replace('B5S', 'B5s')} & {f1(t['mean_pbti'])} & {f1(t['mean_comp'])} & "
                     f"{f1(t['mean_diff'])} [{f1(t['ci_lo'])}, {f1(t['ci_hi'])}] & {t['rb']:.2f} & {ptex(t['p_holm'])} & "
                     f"{'yes' if t['practical'] else 'no'}\\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (GEN / "tabS_v3_tests.tex").write_text("\n".join(lines))
    M("XOneTested", fmt(sum(t["kind"] == "tested" for t in tests)))
    M("XOneIdentical", fmt(sum(t["kind"] == "identical" for t in tests)))
    M("XOneTotal", fmt(len(tests)))


# ============================================================================ X2 mixed workload
def x2():
    v2 = [r for r in A.load("ablations") if (r["system"] == "PBTI" and r.get("ablation_name") == "full") or
          (r["system"] in ("B1", "B2", "B3", "B4") and r.get("ablation_name") == "baseline")]
    v3 = rows_of("v3_mixed_b5.jsonl")
    M("MixRuns", fmt(len(v3)))
    REPORT["x2_audits"] = {"runs": sum("audit_pass" in r for r in v3), "pass": sum(bool(r.get("audit_pass")) for r in v3)}
    by = defaultdict(dict)
    for r in v2 + v3:
        by[r["system"]][r["seed"]] = r
    out = []
    for s in ("PBTI", "B4", "B5", "B5S", "PBTI-R"):
        d = by.get(s)
        if not d:
            continue
        rr = list(d.values())
        tag = s.replace("-", "")
        row = {"system": s, "n": len(rr)}
        for k in ("nonlegit_auth", "legit_missing", "legit_quarantined", "recovered_n", "holds", "cv_wrong_rate", "fork_events"):
            row[k] = mean([r.get(k, 0) for r in rr])
            M(f"Mix{tag}{k.replace('_', '')}", f1(row[k] * 100) if k == "cv_wrong_rate" else f1(row[k]))
        p50 = [r["recovery_ms_p50"] / 1000 for r in rr if r.get("recovered_n", 0) > 0]
        row["rec_p50_s"] = mean(p50) if p50 else math.nan
        M(f"Mix{tag}recpfifty", f1(row["rec_p50_s"]) if p50 else "--")
        out.append(row)
    # exploratory paired tests vs PBTI (Holm over comparisons x outcomes)
    tests = []
    for s in ("B5", "B5S", "PBTI-R"):
        for o, metric in OUT.items():
            a, b = by.get("PBTI", {}), by.get(s, {})
            seeds = sorted(set(a) & set(b))
            if not seeds:
                continue
            x = np.array([b[k][metric] for k in seeds], float)
            y = np.array([a[k][metric] for k in seeds], float)
            p, rb, kind = A.wilcoxon_paired(x, y)
            tests.append({"comp": s, "outcome": o, "n": len(seeds), "mean_diff": float((x - y).mean()), "p": p, "rb": rb, "kind": kind})
    if tests:
        adj = holm(np.array([t["p"] for t in tests]))
        for t, q in zip(tests, adj):
            t["p_holm"] = float(q)
            M(f"Mix{t['comp'].replace('-', '')}{t['outcome']}pholm", ptex(q) if t["kind"] == "tested" else "identical")
    REPORT["x2"] = {"summary": out, "tests": tests}
    write_csv("v3_x2_mixed.csv", out)
    # Table S14: append the mixed workload (X2) below the X1 scenarios
    tp = GEN / "tabS_v3_b5.tex"
    if tp.exists():
        rows_tex = [r"\midrule"]
        for s in ("PBTI", "B5", "B5S", "PBTI-R"):
            rr = list(by.get(s, {}).values())
            if not rr:
                continue
            p50 = [r["recovery_ms_p50"] / 1000 for r in rr if r.get("recovered_n", 0) > 0]
            p95 = [r["recovery_ms_p95"] / 1000 for r in rr if r.get("recovered_n", 0) > 0]
            rows_tex.append(f"Mixed {s.replace('B5S', 'B5s')} & {f1(mean([r.get('fork_events', 0) for r in rr]))} & "
                            f"{f1(mean([r.get('holds', 0) for r in rr]))} & {f1(mean([r.get('recovered_n', 0) for r in rr]))} & "
                            f"{f1(mean(p50)) if p50 else '--'} & {f1(mean(p95)) if p95 else '--'} & "
                            f"{f1(mean([r.get('legit_quarantined', 0) for r in rr]))} & {fmt(mean([r.get('cv_wrong_rate', 0) for r in rr]) * 100, 2)} & "
                            f"{fmt(mean([r.get('store_bytes_per_reach', 0) for r in rr]), 0)}\\\\")
        txt = tp.read_text()
        assert txt.count(r"\bottomrule") == 1
        tp.write_text(txt.replace(r"\bottomrule", "\n".join(rows_tex) + "\n" + r"\bottomrule"))


# ============================================================================ X3 sweep
FACT_LABEL = {"loss": "Loss", "dup": "Duplicates", "reorder": "Reordering", "delay": "Long delay", "burst": "Outage (burst)",
              "clock": "Clock error", "revstale": "Revocation staleness", "compromise": "Discovery delay",
              "equivocation": "Equivocation", "missing": "Suppressed runs", "relay": "Relay forgery"}
LEVELS = (0.0, 0.01, 0.05, 0.10, 0.20)
TIME_F = ("revstale", "compromise")


def sweep():
    rows = rows_of("v3_sweep.jsonl")
    if not rows:
        return None
    cell = defaultdict(dict)   # (factor, level, system) -> seed -> row
    for r in rows:
        cell[(r["factor"], float(r["level"]), r["system"])][r["seed"]] = r
    factors = [f for f in FACT_LABEL if any(k[0] == f for k in cell)]

    def get(f, lv, s):
        if lv == 0.0 and f not in TIME_F:
            return cell.get(("none", 0.0, s), {})
        return cell.get((f, lv, s), {})
    summ = []
    for f in factors:
        for lv in LEVELS:
            for s in ("PBTI", "B4", "B5"):
                d = get(f, lv, s)
                if not d:
                    continue
                rr = list(d.values())
                row = {"factor": f, "level": lv, "system": s, "n": len(rr)}
                for k in ("nonlegit_auth", "legit_missing", "legit_quarantined", "recovered_n", "holds", "cv_wrong_rate"):
                    x = [r.get(k, 0) for r in rr]
                    row[k] = mean(x)
                    if k in ("nonlegit_auth", "legit_missing"):
                        row[k + "_lo"], row[k + "_hi"] = boot_ci(x)
                summ.append(row)
    write_csv("v3_sweep_summary.csv", summ)
    # exploratory paired tests: B4 vs PBTI and B5 vs PBTI per cell, Holm per outcome x comparison
    tests = []
    for comp in ("B4", "B5"):
        for o, metric in OUT.items():
            fam = []
            for f in factors:
                for lv in LEVELS:
                    a, b = get(f, lv, "PBTI"), get(f, lv, comp)
                    seeds = sorted(set(a) & set(b))
                    if not seeds or (lv == 0.0 and f not in TIME_F and f != factors[0]):
                        continue   # shared zero point tested once
                    x = np.array([b[k][metric] for k in seeds], float)
                    y = np.array([a[k][metric] for k in seeds], float)
                    p, rb, kind = A.wilcoxon_paired(x, y)
                    fam.append({"comp": comp, "outcome": o, "factor": f if lv or f in TIME_F else "none", "level": lv,
                                "n": len(seeds), "mean_pbti": float(y.mean()), "mean_comp": float(x.mean()),
                                "mean_diff": float((x - y).mean()), "p": p, "rb": rb, "kind": kind})
            if fam:
                adj = holm(np.array([t["p"] for t in fam]))
                for t, q in zip(fam, adj):
                    t["p_holm"] = float(q)
                    t["sig"] = bool(q < 0.05)
            tests += fam
    write_csv("v3_sweep_tests.csv", tests)
    for comp in ("B4", "B5"):
        for o in OUT:
            fam = [t for t in tests if t["comp"] == comp and t["outcome"] == o]
            tag = f"Sw{comp}{o}"
            M(tag + "cells", fmt(len(fam)))
            M(tag + "identical", fmt(sum(t["kind"] == "identical" for t in fam)))
            M(tag + "sig", fmt(sum(t.get("sig", False) for t in fam)))
            M(tag + "worse", fmt(sum(t.get("sig", False) and t["mean_diff"] > 0 for t in fam)))
            M(tag + "better", fmt(sum(t.get("sig", False) and t["mean_diff"] < 0 for t in fam)))
    REPORT["sweep_runs"] = len(rows)
    M("SweepRuns", fmt(len(rows)))
    # selected numbers at 20 %
    S = {(r["factor"], r["level"], r["system"]): r for r in summ}
    for f in factors:
        for s in ("PBTI", "B4", "B5"):
            r = S.get((f, 0.20, s))
            if r:
                M(f"Sw{f}{s}OneTwenty", f1(r["nonlegit_auth"]))
                M(f"Sw{f}{s}TwoTwenty", f1(r["legit_missing"]))
                M(f"Sw{f}{s}HoldsTwenty", f1(r["holds"]))
                M(f"Sw{f}{s}RecTwenty", f1(r["recovered_n"]))
            r0 = S.get((f, 0.0, s))
            if r0:   # level 0 (for the time-valued factors it still contains the compromise)
                M(f"Sw{f}{s}OneZero", f1(r0["nonlegit_auth"]))
                M(f"Sw{f}{s}TwoZero", f1(r0["legit_missing"]))
    figure_sweep(summ, factors)
    return summ


def figure_sweep(summ, factors):
    S = defaultdict(dict)
    for r in summ:
        S[(r["factor"], r["system"])][r["level"]] = r
    main_sel = [f for f in ("equivocation", "relay", "compromise", "revstale", "missing", "clock") if f in factors]
    rest = [f for f in factors if f not in main_sel]
    for name, sel in (("fig_v3_sweep.pdf", main_sel), ("fig_v3_sweep_rest.pdf", rest)):
        if not sel:
            continue
        n = len(sel)
        fig, axes = plt.subplots(2, n, figsize=(7.3 if n > 4 else 1.25 * n + 1.2, 2.45), sharex=True)
        if n == 1:
            axes = np.array(axes).reshape(2, 1)
        for j, f in enumerate(sel):
            for i, (metric, ylab) in enumerate((("nonlegit_auth", "Non-legit. auth./run"), ("legit_missing", "Legit. missing/run"))):
                ax = axes[i, j]
                for s in ("B4", "B5", "PBTI"):
                    d = S.get((f, s), {})
                    xs = [lv * 100 for lv in LEVELS if lv in d]
                    ys = [d[lv][metric] for lv in LEVELS if lv in d]
                    lo = [d[lv][metric + "_lo"] for lv in LEVELS if lv in d]
                    hi = [d[lv][metric + "_hi"] for lv in LEVELS if lv in d]
                    if not xs:
                        continue
                    ax.plot(xs, ys, marker=MRK[s], ms=2.6, lw=1.0, color=COL[s], label=s, zorder=3 if s == "PBTI" else 2)
                    ax.fill_between(xs, lo, hi, color=COL[s], alpha=0.15, lw=0)
                ax.grid(True, color=A.GRID, lw=0.4)
                ax.tick_params(labelsize=5.2, length=1.5, pad=1)
                for sp in ("top", "right"):
                    ax.spines[sp].set_visible(False)
                if i == 0:
                    ax.set_title(FACT_LABEL[f], fontsize=5.6, pad=2)
                if j == 0:
                    ax.set_ylabel(ylab, fontsize=5.6)
                if i == 1:
                    ax.set_xticks([0, 10, 20])
                    ax.set_xlabel("level (%)", fontsize=5.2, labelpad=1)
        h, l = axes[0, 0].get_legend_handles_labels()
        fig.legend(h, l, loc="upper center", ncol=3, fontsize=6, bbox_to_anchor=(0.5, 1.02))
        fig.tight_layout(rect=(0, 0, 1, 0.95), w_pad=0.25, h_pad=0.4)
        fig.savefig(FIG / name)
        fig.savefig(FIG / "png600" / name.replace(".pdf", ".png"), dpi=600)
        plt.close(fig)


# ============================================================================ X4 factorial
FACT7 = ("loss", "dup", "reorder", "delay", "clock", "equivocation", "missing")
LET = dict(zip(FACT7, "ABCDEFG"))
CHAINS = {"AB": ("AB", "CE", "FG"), "AC": ("AC", "BE", "DG"), "AD": ("AD", "EF", "CG"), "AE": ("AE", "BC", "DF"),
          "AF": ("AF", "DE", "BG"), "AG": ("AG", "CD", "BF"), "BD": ("BD", "CF", "EG")}


def factorial():
    rows = rows_of("v3_factorial.jsonl")
    if not rows:
        return
    inv = {v: k for k, v in LET.items()}
    res = []
    for s in ("PBTI", "B4", "B5"):
        for o, metric in OUT.items():
            per_seed = defaultdict(dict)   # seed -> run -> value
            signs = {}
            for r in rows:
                if r["system"] != s:
                    continue
                per_seed[r["seed"]][r["run"]] = r[metric]
                signs[r["run"]] = {LET[k]: v for k, v in r["signs"].items()}
            if not per_seed:
                continue
            effects = [(LET[f], (LET[f],)) for f in FACT7] + [(c, tuple(c)) for c in CHAINS]
            for name, letters in effects:
                est = []
                for seed, runs in per_seed.items():
                    if len(runs) != 16:
                        continue
                    hi = [v for run, v in runs.items() if np.prod([signs[run][L] for L in letters]) > 0]
                    lo = [v for run, v in runs.items() if np.prod([signs[run][L] for L in letters]) < 0]
                    est.append(np.mean(hi) - np.mean(lo))
                est = np.array(est, float)
                if len(est) < 2:
                    continue
                m = float(est.mean())
                se = float(est.std(ddof=1) / math.sqrt(len(est)))
                tq = stats.t.ppf(0.975, len(est) - 1)
                label = inv[name] if name in inv else " = ".join(CHAINS[name])
                res.append({"system": s, "outcome": o, "effect": name, "label": label, "n_seeds": len(est), "estimate": m,
                            "ci_lo": m - tq * se, "ci_hi": m + tq * se})
    write_csv("v3_factorial_effects.csv", res)
    E = {(r["system"], r["outcome"], r["effect"]): r for r in res}
    lines = [r"\begin{tabular}{l" + "r" * 6 + "}", r"\toprule",
             r"& \multicolumn{2}{c}{\textbf{PBTI}} & \multicolumn{2}{c}{\textbf{B4}} & \multicolumn{2}{c}{\textbf{B5}}\\",
             r"\cmidrule(lr){2-3}\cmidrule(lr){4-5}\cmidrule(lr){6-7}",
             r"\textbf{Effect} & O1 & O2 & O1 & O2 & O1 & O2\\", r"\midrule"]
    for name in [LET[f] for f in FACT7] + list(CHAINS):
        label = (f"{name} ({inv[name]})" if name in inv else " = ".join(CHAINS[name]))
        cells = []
        for s in ("PBTI", "B4", "B5"):
            for o in ("O1", "O2"):
                r = E.get((s, o, name))
                if not r:
                    cells.append("--")
                    continue
                sig = r["ci_lo"] > 0 or r["ci_hi"] < 0
                cells.append(f"{f1(r['estimate'])}" + ("$^{*}$" if sig else ""))
        lines.append(label + " & " + " & ".join(cells) + r"\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (GEN / "tabS_v3_factorial.tex").write_text("\n".join(lines))
    M("FactRuns", fmt(len(rows)))
    # equivocation combined with suppressed runs (F+ and G+): gap-fills whose genuine successor never arrives
    fg = defaultdict(list)
    for r in rows:
        if r["signs"]["equivocation"] > 0 and r["signs"]["missing"] > 0:
            fg[r["system"]].append(r["nonlegit_auth"])
    for s_, v in fg.items():
        M(f"Fact{s_}OneFG", f1(mean(v)))
    byk = {(r["system"], r["run"], r["seed"]): r["nonlegit_auth"] for r in rows}
    pairs = [(byk[("B5", ru, se)], byk[("PBTI", ru, se)]) for (s_, ru, se) in byk if s_ == "PBTI" and ("B5", ru, se) in byk]
    M("FactPairs", fmt(len(pairs)))
    M("FactBFiveBetterPairs", fmt(sum(a < b for a, b in pairs)))
    M("FactBFiveWorsePairs", fmt(sum(a > b for a, b in pairs)))
    if pairs:
        x = np.array([a for a, _ in pairs], float)
        y = np.array([b for _, b in pairs], float)
        p, rb, kind = A.wilcoxon_paired(x, y)
        M("FactBFiveVsPBTIOOnep", ptex(p))
        REPORT["factorial_b5_vs_pbti_O1"] = {"pairs": len(pairs), "b5_lower": int((x < y).sum()), "b5_higher": int((x > y).sum()), "p": p, "rb": rb}
    for s in ("PBTI", "B4", "B5"):
        for o in OUT:
            big = sorted([r for r in res if r["system"] == s and r["outcome"] == o], key=lambda r: -abs(r["estimate"]))
            if big:
                M(f"Fact{s}{o}top", f"{big[0]['label']} ({f1(big[0]['estimate'])})")
    REPORT["factorial"] = res


# ============================================================================ X5 SKAB replay (virtual time)
def replay():
    rows = rows_of("v3_replay_skab.jsonl")
    meta_p = RAW / "v3_replay_skab_dataset.json"
    if meta_p.exists():
        meta = json.loads(meta_p.read_text())
        M("SkabCommit", meta.get("commit", "")[:8])
        M("SkabFiles", fmt(len(meta.get("files", []))))
        M("SkabRows", fmt(meta.get("rows_per_file")))
        M("SkabAccessed", meta.get("accessed", ""))
        M("SkabAnomRows", fmt(sum(f["anomalous_rows"] for f in meta.get("files", []))))
        REPORT["skab_dataset"] = meta
    if not rows:
        return
    cell = defaultdict(dict)
    for r in rows:
        cell[(r["speed"], r["stress"], r["system"])][r["seed"]] = r
    summ = []
    for (speed, stress, s), d in sorted(cell.items()):
        rr = list(d.values())
        row = {"speed": speed, "stress": stress, "system": s, "n": len(rr)}
        for k in ("n_reachable", "nonlegit_auth", "legit_missing", "legit_quarantined", "recovered_n", "holds", "cv_wrong_rate",
                  "label0_reach", "label0_auth", "label1_reach", "label1_auth", "store_bytes_per_reach"):
            row[k] = mean([r.get(k, 0) for r in rr])
        # legitimate receipts rejected because their relay or origin key was already revoked (the gateway re-key is
        # scheduled 5 s after revocation in simulated time, not in dataset rows, so this count scales with the speed-up)
        row["legit_rx_revoked"] = mean([r.get("rx[legit]REJECT/REVOKED", 0) for r in rr])
        p50 = [r["recovery_ms_p50"] / 1000 for r in rr if r.get("recovered_n", 0) > 0]
        row["rec_p50_s"] = mean(p50) if p50 else math.nan
        row["avail_label0"] = row["label0_auth"] / row["label0_reach"] if row["label0_reach"] else math.nan
        row["avail_label1"] = row["label1_auth"] / row["label1_reach"] if row["label1_reach"] else math.nan
        lo, hi = boot_ci([r["nonlegit_auth"] for r in rr])
        row["O1_lo"], row["O1_hi"] = lo, hi
        lo, hi = boot_ci([r["legit_missing"] for r in rr])
        row["O2_lo"], row["O2_hi"] = lo, hi
        summ.append(row)
        sp = {1: "One", 5: "Five", 10: "Ten"}.get(int(speed), str(speed))
        tag = f"Rp{sp}{'' if stress else 'clean'}{s}"
        for k in ("nonlegit_auth", "legit_missing", "legit_quarantined", "recovered_n", "holds"):
            M(tag + k.replace("_", ""), f1(row[k]))
        M(tag + "recpfifty", f1(row["rec_p50_s"]) if p50 else "--")
        M(tag + "revokedrej", f1(row["legit_rx_revoked"]))
        M(tag + "availnormal", fmt(row["avail_label0"] * 100, 1))
        M(tag + "availanom", fmt(row["avail_label1"] * 100, 1))
        M(tag + "reach", f1(row["n_reachable"]))
    write_csv("v3_replay_summary.csv", summ)
    tests = []
    for o, metric in OUT.items():
        fam = []
        for speed in sorted({k[0] for k in cell}):
            for comp in ("B4", "B5"):
                a, b = cell.get((speed, True, "PBTI"), {}), cell.get((speed, True, comp), {})
                seeds = sorted(set(a) & set(b))
                if not seeds:
                    continue
                x = np.array([b[k][metric] for k in seeds], float)
                y = np.array([a[k][metric] for k in seeds], float)
                p, rb, kind = A.wilcoxon_paired(x, y)
                fam.append({"outcome": o, "speed": speed, "comp": comp, "n": len(seeds), "mean_diff": float((x - y).mean()),
                            "p": p, "rb": rb, "kind": kind})
        if fam:
            adj = holm(np.array([t["p"] for t in fam]))
            for t, q in zip(fam, adj):
                t["p_holm"] = float(q)
                sp = {1: "One", 5: "Five", 10: "Ten"}.get(int(t["speed"]), "")
                M(f"Rp{sp}{t['comp']}{o}pholm", ptex(q) if t["kind"] == "tested" else "identical")
        tests += fam
    write_csv("v3_replay_tests.csv", tests)
    clean_rows = [r for r in rows if not r["stress"]]
    M("RpCleanRuns", fmt(len(clean_rows)))
    M("RpCleanMissingTotal", fmt(sum(r["legit_missing"] for r in clean_rows)))
    M("RpCleanNonlegitTotal", fmt(sum(r["nonlegit_auth"] for r in clean_rows)))
    M("RpCleanQuarTotal", fmt(sum(r.get("legit_quarantined", 0) + r.get("holds", 0) for r in clean_rows)))
    aud = [r for r in rows if "audit_pass" in r]
    REPORT["x5_audits"] = {"runs": len(aud), "pass": sum(bool(r["audit_pass"]) for r in aud)}
    M("RpRuns", fmt(len(rows)))
    # attack-label attribution of the end-of-run residue (scripts/diagnose_replay_residue.py re-runs seeds exactly)
    rp = SUM / "v3_replay_residue.json"
    if rp.exists():
        res = json.loads(rp.read_text())
        seeds = sorted(res.get("seeds", []))
        M("RpResSeeds", f"{seeds[0]}--{seeds[-1]}" if seeds else "--")
        M("RpResAllMatch", "identical to" if res.get("all_match_campaign") else "NOT identical to")
        sp = sorted(float(x) for x in res.get("speeds", []))
        M("RpResSpeeds", " and ".join(f"{x:g}" for x in sp))
        M("RpResRunsPerSystem", fmt(sum(1 for run in res["runs"] if run["system"] == "PBTI")))
        tot = defaultdict(Counter)
        for run in res["runs"]:
            for k, c in run["residue_by_label_and_cell"].items():
                tot[run["system"]][k] += c
        for s, tag in (("PBTI", "PBTI"), ("B5", "BFive"), ("B4", "BFour")):
            c = tot.get(s, Counter())
            M(f"RpRes{tag}total", fmt(sum(c.values())))
            M(f"RpRes{tag}gw", fmt(sum(v for k, v in c.items() if k.startswith("gwforge-legacy@pa-c2"))))   # never-revoked forging gateway
            M(f"RpRes{tag}imp", fmt(sum(v for k, v in c.items() if k.startswith("impersonation"))))
            M(f"RpRes{tag}eqv", fmt(sum(v for k, v in c.items() if k.startswith("equivocation"))))
        REPORT["x5_residue"] = {s: dict(c) for s, c in tot.items()}
    lines = [r"\begin{tabular}{rlrrrrrrrr}", r"\toprule",
             r"\textbf{Speed} & \textbf{Pipeline} & \textbf{Reach.} & \textbf{Non-legit.} & \textbf{Missing} & \textbf{Quar.} & \textbf{Held} & \textbf{Released (p50 s)} & \textbf{Avail.\ normal \%} & \textbf{Avail.\ anomaly \%}\\",
             r"\midrule"]
    for r in summ:
        if not r["stress"]:
            continue
        rel = f"{f1(r['recovered_n'])} ({f1(r['rec_p50_s'])})" if r["recovered_n"] else "0"
        lines.append(f"{int(r['speed'])}$\\times$ & {r['system']} & {f1(r['n_reachable'])} & {f1(r['nonlegit_auth'])} & "
                     f"{f1(r['legit_missing'])} & {f1(r['legit_quarantined'])} & {f1(r['holds'])} & {rel} & "
                     f"{fmt(r['avail_label0'] * 100, 1)} & {fmt(r['avail_label1'] * 100, 1)}\\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (GEN / "tabS_v3_replay.tex").write_text("\n".join(lines))
    REPORT["replay"] = {"summary": summ, "tests": tests}


# ============================================================================ wall clock: batching / workers
def batching():
    rows = rows_of("v3_batching.jsonl")
    if not rows:
        return None
    cell = defaultdict(list)
    for r in rows:
        cell[(r["system"], r["batch"], r["workers"])].append(r)
    digests = defaultdict(set)
    for r in rows:
        digests[(r["system"], r["rep"])].add(r["dispositions_digest"])
    same = all(len(v) == 1 for v in digests.values())
    M("BatchSemanticsIdentical", "identical" if same else "NOT identical")
    summ = []
    for (s, b, w), rr in sorted(cell.items()):
        tp = [r["throughput_msg_s"] for r in rr]
        lo, hi = boot_ci(tp)
        row = {"system": s, "batch": b, "workers": w, "n": len(rr), "throughput": mean(tp), "tp_lo": lo, "tp_hi": hi}
        for k in ("lat_ms_p50", "lat_ms_p95", "lat_ms_p99", "cpu_util_cores", "cpu_us_per_msg", "queue_depth_max",
                  "db_bytes_per_msg", "evidence_bytes_per_msg", "wire_bytes", "rss_main_mb", "rss_workers_mb", "drops", "timeouts"):
            row[k] = mean([r.get(k, 0) for r in rr])
        summ.append(row)
        tag = f"Bt{s}b{fmt(b)}w{w}".replace("{,}", "")
        M(tag + "tp", fmt(row["throughput"], 0))
        M(tag + "pninetynine", f1(row["lat_ms_p99"]))
        M(tag + "pfifty", f1(row["lat_ms_p50"]))
        M(tag + "cpu", fmt(row["cpu_us_per_msg"], 0))
    write_csv("v3_batching_summary.csv", summ)
    S = {(r["system"], r["batch"], r["workers"]): r for r in summ}
    for s in ("PBTI", "B5", "B2"):
        cand = [r for r in summ if r["system"] == s]
        if cand:
            best = max(cand, key=lambda r: r["throughput"])
            M(f"Bt{s}best", fmt(best["throughput"], 0))
            M(f"Bt{s}bestbatch", fmt(best["batch"]))
            M(f"Bt{s}bestworkers", fmt(best["workers"]))
            if (s, 1, 1) in {(r["system"], r["batch"], r["workers"]) for r in cand}:
                base = next(r for r in cand if r["batch"] == 1 and r["workers"] == 1)
                M(f"Bt{s}bestgain", fmt(best["throughput"] / base["throughput"], 2))  # best cell vs batch 1, 1 process
    if ("PBTI", 1, 1) in S and ("PBTI", 128, 1) in S:
        M("BtPBTIgainbatch", fmt(S[("PBTI", 128, 1)]["throughput"] / S[("PBTI", 1, 1)]["throughput"], 2))
    if ("PBTI", 128, 1) in S and ("PBTI", 128, 2) in S:
        M("BtPBTIgainworkers", fmt(S[("PBTI", 128, 2)]["throughput"] / S[("PBTI", 128, 1)]["throughput"], 2))
    for w, word in ((4, "four"), (8, "eight")):
        if ("PBTI", 128, 1) in S and ("PBTI", 128, w) in S:
            M("BtPBTIgainworkers" + word, fmt(S[("PBTI", 128, w)]["throughput"] / S[("PBTI", 128, 1)]["throughput"], 2))
    if ("PBTI", 1, 1) in S and ("PBTI", 1, 2) in S:
        M("BtPBTIlossworkersbatchone", fmt(S[("PBTI", 1, 2)]["throughput"] / S[("PBTI", 1, 1)]["throughput"], 2))
    if ("PBTI", 128, 1) in S and ("B2", 128, 1) in S:
        M("BtRatioBTwo", fmt(S[("PBTI", 128, 1)]["throughput"] / S[("B2", 128, 1)]["throughput"], 2))
    if ("B5", 128, 1) in S and ("PBTI", 128, 1) in S:
        M("BtRatioBFive", fmt(S[("B5", 128, 1)]["throughput"] / S[("PBTI", 128, 1)]["throughput"], 2))
    M("BtReps", fmt(max(r["n"] for r in summ)))
    M("BtN", fmt(rows[0]["n_msgs"]))
    lines = [r"\begin{tabular}{lrrrrrrrr}", r"\toprule",
             r"\textbf{Pipeline} & \textbf{Batch} & \textbf{Workers} & \textbf{msg/s [95\% CI]} & \textbf{p50 (ms)} & \textbf{p99 (ms)} & \textbf{CPU cores} & \textbf{CPU $\mu$s/msg} & \textbf{DB B/msg}\\",
             r"\midrule"]
    for r in summ:
        if r["system"] != "PBTI" and r["workers"] != 1 and r["batch"] != 128:
            continue   # table: full PBTI grid; B5 batch sweep (1 worker) and worker sweep (batch 128); full grid in Data S1
        lines.append(f"{r['system']} & {fmt(r['batch'])} & {r['workers']} & {fmt(r['throughput'], 0)} [{fmt(r['tp_lo'], 0)}, {fmt(r['tp_hi'], 0)}] & "
                     f"{f1(r['lat_ms_p50'])} & {f1(r['lat_ms_p99'])} & {fmt(r['cpu_util_cores'], 2)} & {fmt(r['cpu_us_per_msg'], 0)} & {fmt(r['db_bytes_per_msg'], 0)}\\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (GEN / "tabS_v3_batching.tex").write_text("\n".join(lines))
    REPORT["batching"] = summ
    return summ


# ============================================================================ wall clock: 30-rep end-to-end
def e2e():
    rows = rows_of("v3_mqtt_e2e.jsonl")
    if not rows:
        return None
    cell = defaultdict(list)
    for r in rows:
        cell[(r["system"], r["rate"])].append(r)
    summ = []
    for (s, rate), rr in sorted(cell.items()):
        row = {"system": s, "rate": rate, "n": len(rr)}
        for k in ("lat_ms_p50", "lat_ms_p95", "lat_ms_p99", "throughput_msg_s", "achieved_rate", "verifier_cpu_us_per_msg", "queue_depth_max", "lost"):
            x = [r.get(k) for r in rr if r.get(k) is not None]
            row[k] = mean(x)
            row[k + "_median"] = float(np.median(x)) if x else math.nan
            if k in ("lat_ms_p50", "lat_ms_p99"):
                row[k + "_lo"], row[k + "_hi"] = boot_ci(x)
        summ.append(row)
        tag = f"Ee{s}r{fmt(rate)}".replace("{,}", "")
        M(tag + "pfifty", f1(row["lat_ms_p50"]))
        M(tag + "pfiftymed", f1(row["lat_ms_p50_median"]))
        M(tag + "pninetynine", f1(row["lat_ms_p99"]))
        M(tag + "tp", fmt(row["throughput_msg_s"], 0))
        M(tag + "sent", fmt(row["achieved_rate"], 0))   # publisher send rate (signs in real time on the same host)
        M(tag + "lost", fmt(row["lost"], 0))
        M(tag + "n", fmt(row["n"]))
    write_csv("v3_e2e_summary.csv", summ)
    tests = []
    for rate in sorted({k[1] for k in cell}):
        a, b = cell.get(("PBTI", rate), []), cell.get(("B2", rate), [])
        if not a or not b:
            continue
        for k in ("lat_ms_p50", "lat_ms_p99"):
            x = [r[k] for r in a]
            y = [r[k] for r in b]
            p = float(stats.mannwhitneyu(x, y, alternative="two-sided").pvalue)
            tests.append({"rate": rate, "metric": k, "p": p, "delta": float(A.cliffs_delta(x, y)), "n_pbti": len(x), "n_b2": len(y)})
    if tests:
        adj = holm(np.array([t["p"] for t in tests]))
        for t, q in zip(tests, adj):
            t["p_holm"] = float(q)
            M(f"Eer{fmt(t['rate'])}{t['metric'].replace('lat_ms_', '').replace('p50', 'pfifty').replace('p99', 'pninetynine')}".replace("{,}", "") + "pholm", ptex(q))
            M(f"Eer{fmt(t['rate'])}{t['metric'].replace('lat_ms_', '').replace('p50', 'pfifty').replace('p99', 'pninetynine')}".replace("{,}", "") + "delta", fmt(t["delta"], 2))
    write_csv("v3_e2e_tests.csv", tests)
    M("EeReps", fmt(min(r["n"] for r in summ)))
    M("EeLostTotal", fmt(sum(r.get("lost", 0) or 0 for r in rows), 0))   # sent minus durably committed, all runs
    M("EeRates", ", ".join(fmt(r) for r in sorted({k[1] for k in cell})).replace("{,}", ","))
    M("EeNTests", fmt(len(tests)))
    lines = [r"\begin{tabular}{lrrrrrrrr}", r"\toprule",
             r"\textbf{Pipeline} & \textbf{Offered} & \textbf{Reps} & \textbf{Sent msg/s} & \textbf{Committed msg/s} & \textbf{p50 ms [95\% CI]} & \textbf{p99 ms [95\% CI]} & \textbf{CPU $\mu$s/msg} & \textbf{Max queue}\\",
             r"\midrule"]
    for r in summ:
        lines.append(f"{r['system']} & {fmt(r['rate'])} & {r['n']} & {fmt(r['achieved_rate'], 0)} & {fmt(r['throughput_msg_s'], 0)} & {f1(r['lat_ms_p50'])} [{f1(r['lat_ms_p50_lo'])}, {f1(r['lat_ms_p50_hi'])}] & "
                     f"{f1(r['lat_ms_p99'])} [{f1(r['lat_ms_p99_lo'])}, {f1(r['lat_ms_p99_hi'])}] & {fmt(r['verifier_cpu_us_per_msg'], 0)} & {fmt(r['queue_depth_max'], 0)}\\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (GEN / "tabS_v3_e2e.tex").write_text("\n".join(lines))
    REPORT["e2e"] = {"summary": summ, "tests": tests}
    return summ


def e2e_skab():
    rows = rows_of("v3_mqtt_e2e_skab.jsonl")
    if not rows:
        return None
    cell = defaultdict(list)
    for r in rows:
        cell[(r["speed"], r["system"])].append(r)
    summ = []
    for (sp, s), rr in sorted(cell.items()):
        row = {"speed": sp, "system": s, "n": len(rr)}
        for k in ("rate", "throughput_msg_s", "lat_ms_p50", "lat_ms_p95", "lat_ms_p99", "verifier_cpu_us_per_msg", "queue_depth_max",
                  "verifier_rss_peak_mb", "db_bytes_per_msg", "lost", "sent"):
            row[k] = mean([r.get(k) for r in rr])
        ev = [r["evidence_bytes"] / max(1, r["n_commit_total"]) for r in rr if r.get("evidence_bytes")]
        row["evidence_bytes_per_msg"] = mean(ev) if ev else math.nan
        lo, hi = boot_ci([r["lat_ms_p99"] for r in rr])
        row["p99_lo"], row["p99_hi"] = lo, hi
        summ.append(row)
        spn = {1: "One", 5: "Five", 10: "Ten"}.get(int(sp), "")
        tag = f"Es{spn}{s}"
        M(tag + "pfifty", f1(row["lat_ms_p50"]))
        M(tag + "pninetynine", f1(row["lat_ms_p99"]))
        M(tag + "lost", fmt(row["lost"], 0))
        M(tag + "cpu", fmt(row["verifier_cpu_us_per_msg"], 0))
        M(tag + "dbbytes", fmt(row["db_bytes_per_msg"], 0))
        M(tag + "tp", fmt(row["throughput_msg_s"], 0))
    write_csv("v3_e2e_skab_summary.csv", summ)
    M("EsReps", fmt(min(r["n"] for r in summ)))
    M("EsLostTotal", fmt(sum(r.get("lost", 0) for r in rows), 0))
    lines = [r"\begin{tabular}{rlrrrrrrrr}", r"\toprule",
             r"\textbf{Speed} & \textbf{Pipeline} & \textbf{msg/s} & \textbf{p50 ms} & \textbf{p99 ms [95\% CI]} & \textbf{CPU $\mu$s/msg} & \textbf{Max queue} & \textbf{RSS MB} & \textbf{DB B/msg} & \textbf{Lost}\\",
             r"\midrule"]
    for r in summ:
        lines.append(f"{int(r['speed'])}$\\times$ & {r['system']} & {fmt(r['throughput_msg_s'], 0)} & {f1(r['lat_ms_p50'])} & {f1(r['lat_ms_p99'])} [{f1(r['p99_lo'])}, {f1(r['p99_hi'])}] & "
                     f"{fmt(r['verifier_cpu_us_per_msg'], 0)} & {fmt(r['queue_depth_max'], 0)} & {fmt(r['verifier_rss_peak_mb'], 0)} & {fmt(r['db_bytes_per_msg'], 0)} & {fmt(r['lost'], 0)}\\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (GEN / "tabS_v3_e2e_skab.tex").write_text("\n".join(lines))
    REPORT["e2e_skab"] = summ
    return summ


def figure_performance_v3(bt, ee):
    tp_rows = A.load("throughput")
    fig, axes = plt.subplots(1, 4, figsize=(7.3, 1.95))
    ax = axes[0]
    if bt:
        for s in ("B2", "B5", "PBTI"):
            d = sorted([r for r in bt if r["system"] == s and r["workers"] == 1], key=lambda r: r["batch"])
            if d:
                ax.errorbar([r["batch"] for r in d], [r["throughput"] for r in d],
                            yerr=[[r["throughput"] - r["tp_lo"] for r in d], [r["tp_hi"] - r["throughput"] for r in d]],
                            marker=MRK[s], ms=2.8, lw=1.0, capsize=1.5, color=COL[s], label=s)
        ax.set_xscale("log", base=2)
        ax.set_xlabel("group-commit batch (messages)")
        ax.set_ylabel("messages/s")
        ax.set_title("(a) Batch size, 1 worker", loc="left")
        ax.legend(fontsize=5.5)
    ax = axes[1]
    if bt:
        for s in ("B5", "PBTI"):
            d = sorted([r for r in bt if r["system"] == s and r["batch"] == 128], key=lambda r: r["workers"])
            if d:
                ax.errorbar([r["workers"] for r in d], [r["throughput"] for r in d],
                            yerr=[[r["throughput"] - r["tp_lo"] for r in d], [r["tp_hi"] - r["throughput"] for r in d]],
                            marker=MRK[s], ms=2.8, lw=1.0, capsize=1.5, color=COL[s], label=s)
        ax.set_xscale("log", base=2)
        ax.set_xticks([1, 2, 4, 8])
        ax.set_xticklabels(["1", "2", "4", "8"])
        ax.set_xlabel("signature workers (2 vCPUs)")
        ax.set_title("(b) Workers, batch 128", loc="left")
    ax = axes[2]
    pb = [r for r in tp_rows if r["system"] == "PBTI"]
    if pb:
        stages = [("crypto", "signatures"), ("commit", "evidence+commit"), ("history", "Rule L+lineage"),
                  ("lifecycle", "credential status"), ("policy", "policy"), ("parse", "parse")]
        vals = [mean([r.get(f"stage_us_{k}", 0) for r in pb]) for k, _ in stages]
        ax.barh(range(len(stages)), vals, color=COL["PBTI"], height=0.6)
        ax.set_yticks(range(len(stages)))
        ax.set_yticklabels([l for _, l in stages], fontsize=5.5)
        ax.invert_yaxis()
        ax.set_xlabel("$\\mu$s per message")
        ax.set_title("(c) PBTI cost by stage", loc="left")
    ax = axes[3]
    if ee:
        for s in ("B2", "PBTI"):
            d = sorted([r for r in ee if r["system"] == s], key=lambda r: r["rate"])
            if d:
                ax.errorbar([r["rate"] for r in d], [r["lat_ms_p50"] for r in d],
                            yerr=[[r["lat_ms_p50"] - r["lat_ms_p50_lo"] for r in d], [r["lat_ms_p50_hi"] - r["lat_ms_p50"] for r in d]],
                            marker=MRK[s], ms=2.8, lw=1.0, capsize=1.5, color=COL[s], label=f"{s} p50")
                ax.errorbar([r["rate"] for r in d], [r["lat_ms_p99"] for r in d],
                            yerr=[[r["lat_ms_p99"] - r["lat_ms_p99_lo"] for r in d], [r["lat_ms_p99_hi"] - r["lat_ms_p99"] for r in d]],
                            marker=MRK[s], ms=2.8, lw=1.0, ls="--", capsize=1.5, color=COL[s], mfc="white", label=f"{s} p99")
        ax.set_yscale("log")
        ax.set_xticks(sorted({r["rate"] for r in ee}))
        ax.set_xlabel("offered load (msg/s)")
        ax.set_ylabel("latency (ms)")
        ax.set_title("(d) MQTT/TLS latency", loc="left")
        ax.set_ylim(4, 4e4)   # head room so that the legend sits above the data
        ax.legend(fontsize=4.6, ncol=2, loc="upper left", frameon=False, handlelength=1.8, columnspacing=0.8)
    for ax in axes:
        ax.grid(True, color=A.GRID, lw=0.4)
        ax.tick_params(labelsize=5.5)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
    fig.tight_layout(w_pad=0.6)
    fig.savefig(FIG / "fig_performance_v3.pdf", bbox_inches="tight", pad_inches=0.02)   # nothing clipped at the right edge
    fig.savefig(FIG / "png600" / "fig_performance_v3.png", dpi=600, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)


# ============================================================================ other V3 evidence
def parity():
    p = ROOT / "results" / "policy_parity" / "parity_results.json"
    if not p.exists():
        warn("policy parity results missing")
        return
    d = json.loads(p.read_text())
    h = d.get("headline", {})
    wf = h.get("well_formed_requests_on_well_formed_policy", {})
    mr = h.get("malformed_requests (missing_fields, wrong_types, empty_strings)", {})
    md = h.get("malformed_policy_document", {})
    M("ParityWellFormedN", fmt(wf.get("n", 0)))
    M("ParityWellFormedExact", fmt(wf.get("exact_match", 0)))
    M("ParityMalformedReqN", fmt(mr.get("n", 0)))
    M("ParityMalformedReqExact", fmt(mr.get("exact_match", 0)))
    M("ParityMalformedDocN", fmt(md.get("n", 0)))              # requests evaluated under patched policy documents
    M("ParityMalformedDocPyRejected", fmt(md.get("python_error", 0)))   # ... of which the Python store refused the document
    # per patched document: the Python store either refuses the document at load time (schema violation) or loads it
    # (patch valid by the schema defaults); count documents and the requests under each group
    recs = [r for r in d.get("boundary_cases", []) if r.get("category") == "malformed_policy_document"]
    per_doc = defaultdict(list)
    for r in recs:
        per_doc[r.get("doc_patch")].append(r)
    refused = {k: v for k, v in per_doc.items() if all("error" in r["python"] for r in v)}
    loaded = {k: v for k, v in per_doc.items() if k not in refused}
    M("ParityPatchedDocs", fmt(len(per_doc)))
    M("ParityPatchedDocsRefused", fmt(len(refused)))
    M("ParityPatchedDocsLoaded", fmt(len(loaded)))
    M("ParityRefusedReqRegoDenied", fmt(sum(1 for v in refused.values() for r in v
                                            if r["rego"].get("allow") is False and r["rego"].get("reason") == "POLICY_DOCUMENT_INVALID")))
    M("ParityRefusedReqN", fmt(sum(len(v) for v in refused.values())))
    M("ParityLoadedReqN", fmt(sum(len(v) for v in loaded.values())))
    M("ParityLoadedReqExact", fmt(sum(1 for v in loaded.values() for r in v
                                      if "error" not in r["python"] and (r["python"].get("allow"), r["python"].get("reason"))
                                      == (r["rego"].get("allow"), r["rego"].get("reason")))))
    M("ParityOneSide", fmt(h.get("all_cases", {}).get("permit_by_one_side_only", 0)))
    M("ParityBackend", d.get("meta", {}).get("rego_backend_info", d.get("rego_backend_info", "regopy")).split(";")[0] if isinstance(d.get("meta", {}).get("rego_backend_info", ""), str) else "regopy")
    REPORT["parity"] = h


def tamper_rerun():
    """Insider-tampering audits (E16) re-run with the final auditor (results/raw/v3_audit_rerun.jsonl) versus the stored
    revision-2 runs (results/raw/audit.jsonl): same detection outcome and same set of checks that fired, per run."""
    new = rows_of("v3_audit_rerun.jsonl")
    old_p = RAW / "audit.jsonl"
    if not new or not old_p.exists():
        warn("tamper re-run or revision-2 audit file missing")
        return
    key = lambda r: (r["system"], r["tamper"], r["seed"])  # noqa: E731
    old = {key(r): r for r in (json.loads(x) for x in old_p.read_text().splitlines() if x.strip())}
    same_det = same_checks = same_n = 0
    detected_new = 0
    pbti_new = [r for r in new if r["system"] == "PBTI"]
    for r in new:
        o = old.get(key(r))
        if o is None:
            continue
        same_det += (bool(r["audit_pass"]) == bool(o["audit_pass"]))
        same_checks += (set(r.get("audit_findings") or {}) == set(o.get("audit_findings") or {}))
        same_n += (r.get("tampered") == o.get("tampered"))
    detected_new = sum(not r["audit_pass"] for r in pbti_new)
    M("TamperRerunRuns", fmt(len(new)))
    M("TamperRerunSameDetection", fmt(same_det))
    M("TamperRerunSameChecks", fmt(same_checks))
    M("TamperRerunPBTIDetected", fmt(detected_new))
    M("TamperRerunPBTIRuns", fmt(len(pbti_new)))
    REPORT["tamper_rerun"] = {"runs": len(new), "same_detection": same_det, "same_checks": same_checks,
                              "same_tampered_count": same_n, "pbti_detected": detected_new, "pbti_runs": len(pbti_new)}


def regression():
    p = SUM / "regression_check_v3.json"
    if not p.exists():
        warn("regression_check_v3.json missing")
        return
    d = json.loads(p.read_text())
    M("RegChecked", fmt(len(d["checked"])))
    M("RegDiff", fmt(d["differences"]))
    v3n = sum(1 for c in d["checked"] if c["file"].startswith("v3_"))
    M("RegCheckedVthree", fmt(v3n))
    M("RegCheckedVtwo", fmt(len(d["checked"]) - v3n))
    M("RegFiles", fmt(len({c["file"] for c in d["checked"]})))
    REPORT["regression"] = {"checked": len(d["checked"]), "differences": d["differences"], "source": d["source_sha256"]}


def formal():
    p = ROOT / "results" / "formal" / "formal_summary.json"
    if not p.exists():
        warn("results/formal/formal_summary.json missing")
        return
    d = json.loads(p.read_text())
    M("FormalSummary", d["summary_tex"])
    M("FormalSymbolic", d["symbolic_tex"])
    M("FormalSummarySupp", d["supp_tex"])
    REPORT["formal"] = d


def tests_report():
    p = SUM / "pytest_v3.xml"
    if not p.exists():
        warn("results/summary/pytest_v3.xml missing")
        return
    import xml.etree.ElementTree as ET
    root = ET.parse(p).getroot()
    suites = [root] if root.tag == "testsuite" else list(root)
    n = sum(int(x.get("tests", 0)) for x in suites)
    bad = sum(int(x.get("failures", 0)) + int(x.get("errors", 0)) for x in suites)
    M("TestCount", fmt(n))
    M("TestFailures", fmt(bad))
    REPORT["tests"] = {"tests": n, "failures_or_errors": bad}


def audits_total():
    tot = runs = 0
    for k in ("x1_audits", "x2_audits", "x5_audits"):
        a = REPORT.get(k, {})
        runs += a.get("runs", 0)
        tot += a.get("pass", 0)
    M("AuditRuns", fmt(runs))
    M("AuditPass", fmt(tot))


def main():
    x1()
    x2()
    sweep()
    factorial()
    replay()
    bt = batching()
    ee = e2e()
    e2e_skab()
    figure_performance_v3(bt, ee)
    parity()
    regression()
    tamper_rerun()
    formal()
    tests_report()
    audits_total()
    words = "Zero One Two Three Four Five Six Seven Eight Nine".split()
    seen = set()
    with open(GEN / "v3_macros.tex", "w") as fh:
        fh.write("% AUTO-GENERATED by analysis/analyze_v3.py from results/raw/*.jsonl -- do not edit by hand\n")
        for k, v in sorted(VM.items()):
            safe = "".join(words[int(ch)] if ch.isdigit() else ch for ch in k if ch.isalpha() or ch.isdigit())
            if safe in seen:
                raise SystemExit(f"macro collision {safe}")
            seen.add(safe)
            fh.write(f"\\newcommand{{\\V{safe}}}{{{v}}}\n")
    REPORT["warnings"] = WARN
    (SUM / "v3_analysis_report.json").write_text(json.dumps(REPORT, indent=1, default=str))
    print(f"wrote {len(VM)} V3 macros; warnings: {len(WARN)}")


if __name__ == "__main__":
    main()
