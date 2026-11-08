#!/usr/bin/env python3
"""Statistical analysis, figures, and LaTeX artefacts generated directly from results/raw/*.jsonl.

Every number quoted in the manuscript is produced here and written to paper/generated/ as LaTeX
macros or tables, so the paper cannot drift from the measurements.

Statistics
  * per-cell mean, SD and 95% percentile-bootstrap CI (10,000 resamples, seed 12345) over seeds/reps;
  * paired comparisons PBTI vs each baseline per scenario (paired by seed, common random numbers):
    exact/normal-approximation Wilcoxon signed-rank (zero differences dropped, 'wilcox' method),
    Holm correction within each metric family, matched-pairs rank-biserial effect size;
  * independent comparisons for wall-clock metrics: Kruskal-Wallis across systems, pairwise
    Mann-Whitney U with Holm correction, Cliff's delta; Shapiro-Wilk reported to justify the
    non-parametric choice.
"""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, LogNorm, Normalize, TwoSlopeNorm
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results" / "raw"
SUM = ROOT / "results" / "summary"
FIG = ROOT / "paper" / "figures"
GEN = ROOT / "paper" / "generated"
for d in (SUM, FIG, GEN):
    d.mkdir(parents=True, exist_ok=True)

SYSTEMS = ["PBTI", "B1", "B2", "B3", "B4"]          # virtual-time campaigns (B4 added in revision 2)
WALL_SYSTEMS = ["PBTI", "B1", "B2", "B3"]           # wall-clock experiments (B4 not measured)
BASELINES = ("B1", "B2", "B3", "B4")
COLORS = {"PBTI": "#2a78d6", "B1": "#eb6834", "B2": "#1baf7a", "B3": "#eda100"}  # validated, fixed order
MARKERS = {"PBTI": "o", "B1": "s", "B2": "^", "B3": "D"}
INK, INK2, MUTED, GRID, BASE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
SEQ_BLUE = ["#fcfcfb", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
DIVERGING = ["#2a78d6", "#86b6ef", "#f0efec", "#f19a99", "#e34948"]
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7.5, "axes.edgecolor": BASE, "axes.labelcolor": INK2,
                     "xtick.color": INK2, "ytick.color": INK2, "axes.titlesize": 8, "axes.titleweight": "bold",
                     "axes.titlecolor": INK, "legend.frameon": False, "pdf.fonttype": 42, "savefig.dpi": 600})

SCEN_LABEL = {
    "S01_normal": "E1 Normal", "S02_payload_tamper": "E2 Payload tamper", "S03_metadata_tamper": "E3 Metadata tamper",
    "S04_unauthorized": "E4 Unauthorized/lateral", "S05_stolen_key": "E5 Stolen keys", "S06_replay": "E6 Replay",
    "S07_duplicates": "E7 Duplicates", "S08_seq_reuse_bug": "E8 Seq.-reuse bug", "S09_reorder": "E9 Reordering",
    "S10_delay_clock": "E10 Late + clock faults", "S11_disconnect_recover": "E11/12 Disconnect+restart",
    "S12_beyond_horizon": "E11b Beyond horizon", "S13_rotation": "E13 Key rotation",
    "S14_revocation": "E14 Revocation", "S15_edge_compromise": "E15 Edge compromise"}
ABL_LABEL = {"full": "PBTI (full)", "no_relay_sig": "A1 no relay signature", "static_policy": "A2 static policy",
             "no_obs_sig": "A3 no origin signature", "no_prev_link": "A4 no prev link",
             "edge_event_id": "A5 edge-assigned identity", "no_conflict": "A6 no conflict detection",
             "no_staleness": "A7 no horizon/epoch checks", "arrival_order": "A8 arrival-order state",
             "no_commitment": "A9 no evidence commitment", "no_quarantine": "A10 no quarantine",
             "no_revocation": "A11 no revocation/taint", "volatile_buffer": "A12 volatile edge buffer"}
RNG = np.random.default_rng(12345)


def load(name):
    files = sorted(RAW.glob(f"{name}.jsonl")) + sorted(RAW.glob(f"{name}_part*.jsonl"))
    if not files:
        return []
    rows = [json.loads(l) for p in files for l in open(p) if l.strip()]
    bad = [r for r in rows if "error" in r]
    if bad:
        print(f"WARNING {name}: {len(bad)} error rows excluded", file=sys.stderr)
    rows = [r for r in rows if "error" not in r]
    # guard against double counting when result files overlap (e.g., a full re-run next to an older *_part2 file)
    ident = [(r.get("scenario"), r.get("system"), r.get("seed"), r.get("ablation_name"), r.get("refresh_ms"), r.get("tamper"),
              r.get("rate"), r.get("rep"), r.get("n_devices")) for r in rows]
    if len(set(ident)) != len(ident):
        raise SystemExit(f"{name}: duplicate run identities across {[p.name for p in files]}; remove the stale file")
    return rows


def boot_ci(x, fn=np.mean, n=10_000):
    x = np.asarray(x, float)
    if len(x) == 0:
        return (math.nan, math.nan)
    if np.all(x == x[0]):
        return (float(x[0]), float(x[0]))
    idx = RNG.integers(0, len(x), (n, len(x)))
    b = fn(x[idx], axis=1)
    return (float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5)))


def holm(pvals):
    m = len(pvals)
    order = np.argsort(pvals)
    adj = np.empty(m)
    run = 0.0
    for k, i in enumerate(order):
        run = max(run, (m - k) * pvals[i])
        adj[i] = min(1.0, run)
    return adj


def wilcoxon_paired(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = a - b
    nz = d[d != 0]
    if len(nz) == 0:
        return 1.0, 0.0, "identical"
    try:
        res = stats.wilcoxon(a, b, zero_method="wilcox", alternative="two-sided")
        p = float(res.pvalue)
    except ValueError:
        p = 1.0
    r = stats.rankdata(np.abs(nz))
    rb = (r[nz > 0].sum() - r[nz < 0].sum()) / r.sum()  # matched-pairs rank-biserial
    return p, float(rb), "tested"


def cliffs_delta(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    gt = sum((x > b).sum() for x in a)
    lt = sum((x < b).sum() for x in a)
    return (gt - lt) / (len(a) * len(b))


def fmt(x, nd=1):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "--"
    if x == 0:
        return "0"
    if abs(x - round(x)) < 1e-9 and abs(x) >= 1:
        return f"{int(round(x)):,}".replace(",", "{,}")
    return f"{x:.{nd}f}"


def ptex(p):
    """p-value for LaTeX (valid in text and math mode): two significant digits, scientific notation below 0.001."""
    if p != p:
        return "--"
    if p >= 0.001:
        return f"{p:.2g}"
    m, e = f"{p:.1e}".split("e")
    return f"\\ensuremath{{{m}\\times10^{{{int(e)}}}}}"


macros: dict[str, str] = {}


def M(name, value):
    macros[name] = value


# ============================================================================ scenarios
def analyze_scenarios():
    rows = load("scenarios")
    if not rows:
        return
    by = defaultdict(list)
    for r in rows:
        by[(r["scenario"], r["system"])].append(r)
    metrics = ["nonlegit_auth", "legit_missing", "legit_quarantined", "dup_auth", "win_corrupt", "win_incomplete",
               "cv_wrong_rate"]
    table = []
    for sc in SCEN_LABEL:
        for s in SYSTEMS:
            rs = sorted(by.get((sc, s), []), key=lambda r: r["seed"])
            if not rs:
                continue
            row = {"scenario": sc, "system": s, "n": len(rs), "reach": np.mean([r["n_reachable"] for r in rs])}
            for m in metrics:
                v = [r.get(m, 0) for r in rs]
                row[m] = float(np.mean(v)); row[m + "_sd"] = float(np.std(v, ddof=1)) if len(v) > 1 else 0.0
                row[m + "_ci"] = boot_ci(v)
            table.append(row)
    json.dump(table, open(SUM / "scenarios_summary.json", "w"), indent=1, default=float)
    # headline extremes used in the abstract (computed, never typed)
    base = [t for t in table if t["system"] != "PBTI"]
    mx = max(base, key=lambda t: t["nonlegit_auth"])
    M("MaxBaseNonlegit", fmt(mx["nonlegit_auth"])); M("MaxBaseNonlegitWhere", f"{SCEN_LABEL[mx['scenario']].split(' ')[0]} {mx['system']}")
    pb = [t for t in table if t["system"] == "PBTI"]
    M("PBTIScenariosZeroNonlegit", fmt(sum(1 for t in pb if t["nonlegit_auth"] == 0)))
    # scenarios (excluding normal operation) in which the strongest-combination baseline B4 and PBTI give identical
    # outcomes in every seed on all three tested metrics
    same, diff = [], []
    for sc in SCEN_LABEL:
        if sc == "S01_normal":
            continue
        a = {r["seed"]: r for r in by.get((sc, "PBTI"), [])}
        b = {r["seed"]: r for r in by.get((sc, "B4"), [])}
        if not a or not b:
            continue
        ok = all(a[k].get(m, 0) == b[k].get(m, 0) for k in set(a) & set(b) for m in ("nonlegit_auth", "legit_missing", "cv_wrong"))
        (same if ok else diff).append(SCEN_LABEL[sc].split(" ")[0])
    if same or diff:
        M("BFourMatches", fmt(len(same))); M("BFourDiffers", fmt(len(diff)))
        M("BFourMatchList", ", ".join(same)); M("BFourDiffList", ", ".join(diff))
        M("ScenariosNonNormal", fmt(len(same) + len(diff)))
    # paired tests PBTI vs baselines on nonlegit_auth and legit_missing
    tests = []
    for metric in ("nonlegit_auth", "legit_missing", "cv_wrong"):
        fam = []
        for sc in SCEN_LABEL:
            p_rs = {r["seed"]: r for r in by.get((sc, "PBTI"), [])}
            for b in BASELINES:
                b_rs = {r["seed"]: r for r in by.get((sc, b), [])}
                seeds = sorted(set(p_rs) & set(b_rs))
                if not seeds:
                    continue
                a = [p_rs[k].get(metric, 0) for k in seeds]
                c = [b_rs[k].get(metric, 0) for k in seeds]
                p, rb, kind = wilcoxon_paired(a, c)
                n_nz = int(sum(1 for x, y in zip(a, c) if x != y))
                fam.append({"metric": metric, "scenario": sc, "baseline": b, "n": len(seeds), "n_nonzero": n_nz, "p": p, "rb": rb,
                            "kind": kind, "mean_pbti": float(np.mean(a)), "mean_base": float(np.mean(c))})
        if fam:
            adj = holm(np.array([t["p"] for t in fam]))            # global family: all scenarios x baselines
            for t, pa in zip(fam, adj):
                t["p_holm"] = float(pa)
            for sc in SCEN_LABEL:                                    # per-scenario family: three baselines
                sub = [t for t in fam if t["scenario"] == sc]
                if sub:
                    for t, pa in zip(sub, holm(np.array([t["p"] for t in sub]))):
                        t["p_holm_scen"] = float(pa)
        tests += fam
    json.dump(tests, open(SUM / "scenarios_paired_tests.json", "w"), indent=1)
    # audit pass rate (I5, I6, I10)
    prs = [r for r in rows if r["system"] == "PBTI"]
    n_aud = sum(1 for r in prs if "audit_pass" in r)
    n_pass = sum(1 for r in prs if r.get("audit_pass"))
    M("AuditRuns", fmt(n_aud)); M("AuditPass", fmt(n_pass))
    M("ScenarioRuns", fmt(len(rows))); M("ScenarioSeeds", fmt(len({r["seed"] for r in rows})))
    M("ScenarioSeedMax", fmt(max(r["seed"] for r in rows)))
    n_s = len({r["seed"] for r in rows})
    M("WilcoxonMinP", ptex(2.0 / 2 ** n_s))
    replay_s = [r["audit_replay_s"] for r in prs if r.get("audit_replay_s")]
    rec = [r["n_receipts"] for r in prs if r.get("audit_replay_s")]
    if replay_s:
        M("AuditReplayUsPerReceipt", fmt(np.mean(np.array(replay_s) / np.array(rec)) * 1e6, 0))
        static_s = [r["audit_static_s"] for r in prs if r.get("audit_replay_s")]
        M("AuditStaticUsPerReceipt", fmt(np.mean(np.array(static_s) / np.array(rec)) * 1e6, 0))
        M("AuditTotalUsPerReceipt", fmt(np.mean((np.array(static_s) + np.array(replay_s)) / np.array(rec)) * 1e6, 0))
    # replay/retry labelling quality for PBTI (labels carry no authority; reported for transparency)
    def rxmean(sc, sysname, keys):
        rs = by.get((sc, sysname), [])
        return float(np.mean([sum(r.get(k, 0) for k in keys) for r in rs])) if rs else math.nan
    fa = ["rx[legit]DUPLICATE/SUSPECTED_REPLAY", "rx[legit-dup]DUPLICATE/SUSPECTED_REPLAY"]
    for sc in ("S07_duplicates", "S09_reorder", "S10_delay_clock", "S11_disconnect_recover"):
        tag = sc.split("_")[0]
        M(f"{tag}PBTIreplayfalsealarms", fmt(rxmean(sc, "PBTI", fa)))
        M(f"{tag}PBTIlegitduplicates", fmt(rxmean(sc, "PBTI", fa + ["rx[legit]DUPLICATE/RETRY", "rx[legit-dup]DUPLICATE/RETRY"])))
    M("SZeroSixPBTIreplaydetected", fmt(rxmean("S06_replay", "PBTI", ["rx[replay-exact]DUPLICATE/SUSPECTED_REPLAY"])))
    M("SZeroSixPBTIreplaymissed", fmt(rxmean("S06_replay", "PBTI", ["rx[replay-exact]DUPLICATE/RETRY"])))
    # headline macros
    def cell(sc, s, m):
        for row in table:
            if row["scenario"] == sc and row["system"] == s:
                return row[m]
        return math.nan
    for sc in SCEN_LABEL:
        tag = sc.split("_")[0]
        for s in SYSTEMS:
            for m in ("nonlegit_auth", "legit_missing", "legit_quarantined", "dup_auth", "win_corrupt"):
                M(f"{tag}{s}{m.replace('_', '')}", fmt(cell(sc, s, m)))
            M(f"{tag}{s}cvwrong", fmt(100 * cell(sc, s, "cv_wrong_rate"), 1))
    # LaTeX: main outcome table (compact)
    lines = [r"\begin{tabular}{lrrrrrrrrrr}", r"\toprule",
             r"& \multicolumn{5}{c}{\textbf{Non-legitimate authoritative obs.} (mean/run)} & \multicolumn{5}{c}{\textbf{Legitimate obs.\ missing} (mean/run)}\\",
             r"\cmidrule(lr){2-6}\cmidrule(lr){7-11}",
             r"\textbf{Scenario} & B1 & B2 & B3 & B4 & PBTI & B1 & B2 & B3 & B4 & PBTI\\", r"\midrule"]
    for sc, lab in SCEN_LABEL.items():
        if sc == "S01_normal":
            continue
        vals = [cell(sc, s, "nonlegit_auth") for s in ("B1", "B2", "B3", "B4", "PBTI")]
        miss = [cell(sc, s, "legit_missing") for s in ("B1", "B2", "B3", "B4", "PBTI")]
        q = cell(sc, "PBTI", "legit_quarantined")
        pm = fmt(miss[4]) + (f"$^{{\\dagger}}$" if q and q > 0 else "")
        lines.append(lab.replace("&", r"\&") + " & " + " & ".join(fmt(v) for v in vals) + " & " +
                     " & ".join(fmt(v) for v in miss[:4]) + " & " + pm + r"\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (GEN / "tab_outcomes.tex").write_text("\n".join(lines))
    # full supplementary table with SD and CI
    sl = [r"\begin{tabular}{llrrrrrrr}", r"\toprule",
          r"Scenario & Sys. & Reach. & Non-legit.\ (95\% CI) & Missing (95\% CI) & Quar. & Dup. & Corrupt win. & CV wrong \%\\",
          r"\midrule"]
    for sc, lab in SCEN_LABEL.items():
        for s in ("B1", "B2", "B3", "B4", "PBTI"):
            row = next((x for x in table if x["scenario"] == sc and x["system"] == s), None)
            if row is None:
                continue
            ci1, ci2 = row["nonlegit_auth_ci"], row["legit_missing_ci"]
            sl.append(f"{lab if s == 'B1' else ''} & {s} & {fmt(row['reach'])} & {fmt(row['nonlegit_auth'])} [{fmt(ci1[0])}, {fmt(ci1[1])}]"
                      f" & {fmt(row['legit_missing'])} [{fmt(ci2[0])}, {fmt(ci2[1])}] & {fmt(row['legit_quarantined'])}"
                      f" & {fmt(row['dup_auth'])} & {fmt(row['win_corrupt'])} & {fmt(100 * row['cv_wrong_rate'], 1)}\\\\")
        sl.append(r"\midrule" if sc != list(SCEN_LABEL)[-1] else r"\bottomrule")
    sl.append(r"\end{tabular}")
    (GEN / "tabS_outcomes_full.tex").write_text("\n".join(sl))
    # tests table (supplementary)
    tl = [r"\begin{tabular}{llrrrrrr}", r"\toprule",
          r"Metric & Scenario & Base. & Mean PBTI & Mean base. & $p_\mathrm{Holm}^\mathrm{global}$ & $p_\mathrm{Holm}^\mathrm{scen.}$ & $r_\mathrm{rb}$\\", r"\midrule"]
    for t in tests:
        if t["kind"] == "identical":
            continue
        tl.append(f"{t['metric'].replace('_', r'\_')} & {SCEN_LABEL[t['scenario']].split(' ')[0]} & {t['baseline']} & {fmt(t['mean_pbti'])}"
                  f" & {fmt(t['mean_base'])} & {ptex(t['p_holm'])} & {ptex(t['p_holm_scen'])} & {t['rb']:+.2f}\\\\")
    tl += [r"\bottomrule", r"\end{tabular}"]
    (GEN / "tabS_tests.tex").write_text("\n".join(tl))
    n_id = sum(1 for t in tests if t["kind"] == "identical")
    M("PairedTestsTotal", fmt(len(tests))); M("PairedTestsIdentical", fmt(n_id))
    tested = [t for t in tests if t["kind"] == "tested"]
    sig = [t for t in tested if t["p_holm"] < 0.05]
    sig_s = [t for t in tested if t["p_holm_scen"] < 0.05]
    M("PairedTestsTested", fmt(len(tested)))
    M("PairedTestsSignificant", fmt(len(sig)))
    M("PairedTestsSignificantScen", fmt(len(sig_s)))
    cons = [t for t in tested if abs(t["rb"]) == 1.0]
    M("PairedTestsConsistent", fmt(len(cons)))
    M("PairedTestsAllSeeds", fmt(sum(1 for t in cons if t["n_nonzero"] == t["n"])))
    ps = [t["p_holm"] for t in tests if t["kind"] == "tested"]
    if ps:
        M("PairedTestsMinP", ptex(min(ps)))
    figure_outcomes(table)


def figure_outcomes(table):
    scen = [s for s in SCEN_LABEL if s != "S01_normal"]
    cols = ["B1", "B2", "B3", "B4", "PBTI"]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.15), constrained_layout=True, gridspec_kw={"wspace": 0.08})
    cmap = LinearSegmentedColormap.from_list("seqblue", SEQ_BLUE)
    for ax, metric, title in zip(axes, ("nonlegit_auth", "legit_missing"),
                                 ("(a) Non-legitimate authoritative observations", "(b) Legitimate observations missing")):
        M_ = np.array([[next((r[metric] for r in table if r["scenario"] == sc and r["system"] == s), np.nan)
                        for s in cols] for sc in scen])
        im = ax.imshow(np.log10(1 + M_), cmap=cmap, vmin=0, vmax=np.log10(1001), aspect="auto")
        for i in range(M_.shape[0]):
            for j in range(M_.shape[1]):
                v = M_[i, j]
                txt = "0" if v == 0 else (f"{v:.0f}" if v >= 10 else f"{v:.1f}")
                ax.text(j, i, txt, ha="center", va="center", fontsize=6.5,
                        color="#ffffff" if np.log10(1 + v) > 1.7 else INK)
        ax.set_xticks(range(len(cols)), cols)
        ax.set_yticks(range(len(scen)), [SCEN_LABEL[s] for s in scen] if ax is axes[0] else [""] * len(scen))
        ax.tick_params(length=0)
        for sp in ax.spines.values():
            sp.set_visible(False)
        ax.set_title(title, loc="center", fontsize=7.5)
        ax.set_xticks(np.arange(-.5, len(cols), 1), minor=True)
        ax.set_yticks(np.arange(-.5, len(scen), 1), minor=True)
        ax.grid(which="minor", color="#fcfcfb", linewidth=1.5)
        ax.tick_params(which="minor", length=0)
    cb = fig.colorbar(im, ax=axes, shrink=0.75, pad=0.01)
    cb.set_ticks(list(np.log10(1 + np.array([0, 10, 100, 1000]))), labels=["0", "10", "100", "1,000"])
    cb.set_label("count per run (log scale, mean of seeds)", color=INK2)
    cb.outline.set_visible(False)
    fig.savefig(FIG / "fig_outcomes.pdf")
    plt.close(fig)


# ============================================================================ ablations
def analyze_ablations():
    rows = load("ablations")
    if not rows:
        return
    by = defaultdict(list)
    for r in rows:
        key = r["ablation_name"] if r["system"] == "PBTI" else r["system"]
        by[key].append(r)
    metrics = ["nonlegit_auth", "legit_missing", "legit_quarantined", "dup_auth", "win_corrupt", "cv_wrong_rate", "ingest_us_mean"]
    summ = {}
    for k, rs in by.items():
        rs = sorted(rs, key=lambda r: r["seed"])
        summ[k] = {m: float(np.mean([r.get(m, 0) for r in rs])) for m in metrics}
        summ[k]["n"] = len(rs)
        summ[k]["seeds"] = [r["seed"] for r in rs]
        for m in metrics:
            summ[k][m + "_vals"] = [r.get(m, 0) for r in rs]
    json.dump(summ, open(SUM / "ablations_summary.json", "w"), indent=1)
    full = summ.get("full")
    if not full:
        return
    # paired differences vs full with Wilcoxon (Holm within metric)
    order = [k for k in ABL_LABEL if k != "full" and k in summ]
    tests = {}
    for m in ("nonlegit_auth", "legit_missing", "legit_quarantined", "dup_auth", "cv_wrong_rate", "ingest_us_mean"):
        ps = []
        for k in order:
            p, rb, kind = wilcoxon_paired(summ[k][m + "_vals"], full[m + "_vals"])
            ps.append(p)
            tests[(k, m)] = {"p": p, "rb": rb, "kind": kind}
        adj = holm(np.array(ps))
        for k, pa in zip(order, adj):
            tests[(k, m)]["p_holm"] = float(pa)
    lines = [r"\begin{tabular}{lrrrrrr}", r"\toprule",
             r"\textbf{Configuration} & \textbf{Non-legit.} & \textbf{Missing} & \textbf{Quar.} & \textbf{Dup.} & \textbf{CV wrong \%} & \textbf{$\mu$s/msg}\\",
             r"\midrule"]
    def star(k, m):
        t = tests.get((k, m))
        return "$^{*}$" if t and t["kind"] == "tested" and t["p_holm"] < 0.05 else ""
    for k in ["B1", "B2", "B3", "B4"]:
        if k in summ:
            s = summ[k]
            lines.append(f"{k} (baseline) & {fmt(s['nonlegit_auth'])} & {fmt(s['legit_missing'])} & {fmt(s['legit_quarantined'])} & {fmt(s['dup_auth'])} & {fmt(100*s['cv_wrong_rate'],1)} & {fmt(s['ingest_us_mean'],0)}\\\\")
    lines.append(r"\midrule")
    for k in ["full"] + order:
        s = summ[k]
        lines.append(f"{ABL_LABEL[k]} & {fmt(s['nonlegit_auth'])}{star(k,'nonlegit_auth')} & {fmt(s['legit_missing'])}{star(k,'legit_missing')}"
                     f" & {fmt(s['legit_quarantined'])}{star(k,'legit_quarantined')} & {fmt(s['dup_auth'])}{star(k,'dup_auth')} & {fmt(100*s['cv_wrong_rate'],1)}{star(k,'cv_wrong_rate')}"
                     f" & {fmt(s['ingest_us_mean'],0)}{star(k,'ingest_us_mean')}\\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (GEN / "tab_ablations.tex").write_text("\n".join(lines))
    for k in ["full"] + order + ["B1", "B2", "B3", "B4"]:
        if k in summ:
            tag = "Abl" + k.replace("_", "").replace("B", "Base")
            for m in ("nonlegit_auth", "legit_missing", "dup_auth", "legit_quarantined"):
                M(tag + m.replace("_", ""), fmt(summ[k][m]))
            M(tag + "cvwrong", fmt(100 * summ[k]["cv_wrong_rate"], 1))
            M(tag + "us", fmt(summ[k]["ingest_us_mean"], 0))
    M("AblSeeds", fmt(full["n"]))
    if "no_commitment" in summ:
        M("AblEvidenceCostUs", fmt(full["ingest_us_mean"] - summ["no_commitment"]["ingest_us_mean"], 0))
    if "no_relay_sig" in summ:
        M("AblRelayCostUs", fmt(full["ingest_us_mean"] - summ["no_relay_sig"]["ingest_us_mean"], 0))
    figure_ablation(summ, order)


def figure_ablation(summ, order):
    full = summ["full"]
    cols = [("nonlegit_auth", "Non-legit.\nadmitted"), ("legit_missing", "Legit.\nmissing"), ("dup_auth", "Duplicate\nauthoritative"),
            ("cv_wrong_rate", "Current-value\nwrong (pp)"), ("ingest_us_mean", "Verifier cost\n(µs/msg)")]
    D = np.array([[(summ[k][m] - full[m]) * (100 if m == "cv_wrong_rate" else 1) for m, _ in cols] for k in order])
    fig, ax = plt.subplots(figsize=(5.6, 3.3), constrained_layout=True)
    cmap = LinearSegmentedColormap.from_list("div", DIVERGING)
    # per-column symmetric scaling so each metric uses the full colour range (values are annotated)
    S = np.where(np.abs(D).max(axis=0) > 0, D / np.abs(D).max(axis=0), 0)
    ax.imshow(S, cmap=cmap, vmin=-1, vmax=1, aspect="auto")
    for i in range(D.shape[0]):
        for j in range(D.shape[1]):
            v = D[i, j]
            txt = f"{v:.0f}" if abs(v) >= 10 else (f"{v:.1f}" if abs(v) >= 0.05 or v == 0 else f"{v:.2f}")
            ax.text(j, i, ("+" if v > 0 else "") + txt, ha="center", va="center",
                    fontsize=6.5, color="#ffffff" if abs(S[i, j]) > 0.65 else INK)
    ax.set_xticks(range(len(cols)), [c for _, c in cols])
    ax.set_yticks(range(len(order)), [ABL_LABEL[k] for k in order])
    ax.xaxis.tick_top()
    ax.tick_params(length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.set_xticks(np.arange(-.5, len(cols), 1), minor=True)
    ax.set_yticks(np.arange(-.5, len(order), 1), minor=True)
    ax.grid(which="minor", color="#fcfcfb", linewidth=1.5)
    ax.tick_params(which="minor", length=0)
    fig.suptitle("Change relative to full PBTI (mixed workload, mean of seeds); red = worse, blue = better",
                 x=0.01, ha="left", fontsize=7, color=INK2, fontweight="normal")
    fig.savefig(FIG / "fig_ablation.pdf")
    plt.close(fig)


# ============================================================================ revocation sweep
def analyze_revocation():
    rows = load("revocation")
    if not rows:
        return
    by = defaultdict(list)
    for r in rows:
        by[(r["refresh_ms"], r["system"])].append(r)
    refreshes = sorted({r["refresh_ms"] for r in rows})
    M("RevSeeds", fmt(len({r["seed"] for r in rows})))
    lines = [r"\begin{tabular}{r" + "rr" * 4 + "}", r"\toprule",
             r"& \multicolumn{2}{c}{B1} & \multicolumn{2}{c}{B2} & \multicolumn{2}{c}{B3} & \multicolumn{2}{c}{PBTI}\\",
             r"\cmidrule(lr){2-3}\cmidrule(lr){4-5}\cmidrule(lr){6-7}\cmidrule(lr){8-9}",
             r"Status refresh $\Delta$ & post-rev. & non-legit. & post-rev. & non-legit. & post-rev. & non-legit. & post-rev. & non-legit.\\",
             r"\midrule"]
    out = {}
    for f in refreshes:
        cells = []
        for s in ("B1", "B2", "B3", "PBTI"):
            rs = by.get((f, s), [])
            post = np.mean([sum(v for k, v in r.items() if k.startswith("rx[postrevocation-stolen]ACCEPT")) for r in rs]) if rs else math.nan
            nl = np.mean([r["nonlegit_auth"] for r in rs]) if rs else math.nan
            miss = np.mean([r["legit_missing"] for r in rs]) if rs else math.nan
            out[(f, s)] = {"post": float(post), "nonlegit": float(nl), "missing": float(miss),
                           "taint": float(np.mean([r.get("taint_events", 0) for r in rs])) if rs else 0}
            cells += [fmt(post), fmt(nl)]
            M(f"Rev{s}{f // 1000}spost", fmt(post)); M(f"Rev{s}{f // 1000}snonlegit", fmt(nl)); M(f"Rev{s}{f // 1000}smissing", fmt(miss))
        lines.append(f"{f / 1000:g} s & " + " & ".join(cells) + r"\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (GEN / "tab_revocation.tex").write_text("\n".join(lines))
    json.dump({f"{k[0]}|{k[1]}": v for k, v in out.items()}, open(SUM / "revocation_summary.json", "w"), indent=1)
    M("RevPBTItaint", fmt(out.get((0, "PBTI"), {}).get("taint", math.nan)))


# ============================================================================ audit / insider tampering
def analyze_audit():
    rows = load("audit")
    if not rows:
        return
    names = {"T1_raw_modify": "T1 raw object modified", "T2_raw_delete": "T2 raw object deleted",
             "T3_evidence_modify": "T3 evidence record modified", "T4_checkpoint_delete": "T4 checkpoint deleted",
             "T5_rewrite_with_key": "T5 log rewritten + re-signed (key holder)", "T6_derived_modify": "T6 derived record modified",
             "T7_registry_modify": "T7 registry state modified"}
    lines = [r"\begin{tabular}{lrrl}", r"\toprule",
             r"\textbf{Insider action} & \textbf{B3 detected} & \textbf{PBTI detected} & \textbf{PBTI checks that fired}\\", r"\midrule"]
    for cls, lab in names.items():
        res = {}
        for s in ("B3", "PBTI"):
            rs = [r for r in rows if r["tamper"] == cls and r["system"] == s and r.get("tampered", 0) > 0]
            det = sum(1 for r in rs if not r["audit_pass"])
            res[s] = (det, len(rs))
        fired = defaultdict(int)
        for r in rows:
            if r["tamper"] == cls and r["system"] == "PBTI":
                for k in r["audit_findings"]:
                    fired[k.split(":")[0]] += 1
        lines.append(f"{lab} & {res['B3'][0]}/{res['B3'][1]} & {res['PBTI'][0]}/{res['PBTI'][1]} & {', '.join(sorted(fired))}\\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (GEN / "tab_audit.tex").write_text("\n".join(lines))
    M("AuditTamperSeeds", fmt(max(r["seed"] for r in rows)))


# ============================================================================ throughput (in-process)
def analyze_throughput():
    rows = [r for r in load("throughput")]
    if not rows:
        return
    by = defaultdict(list)
    for r in rows:
        by[r["system"]].append(r)
    out = {}
    for s in SYSTEMS:
        rs = by.get(s, [])
        if not rs:
            continue
        d = {}
        for m in ("throughput_msg_s", "cpu_us_per_msg", "svc_us_p50", "svc_us_p99", "db_bytes_per_msg", "wire_bytes",
                  "edge_cpu_us_per_msg", "rss_delta_mb"):
            v = [r[m] for r in rs]
            d[m] = float(np.mean(v)); d[m + "_ci"] = boot_ci(v)
        if s == "PBTI":
            for k in ("parse", "crypto", "lifecycle", "policy", "history", "commit"):
                d["stage_" + k] = float(np.mean([r.get(f"stage_us_{k}", 0) for r in rs]))
            # The verifier's "history" timer encloses the commit step (_finish is called inside _history), and in
            # this experiment every receipt is an accept, so every commit happens inside that timer. Report the
            # history stage exclusive of commit so that the stages partition the per-message cost.
            d["stage_history"] = float(np.mean([r.get("stage_us_history", 0) - r.get("stage_us_commit", 0) for r in rs]))
            d["evidence_bytes"] = float(np.mean([r.get("evidence_bytes_per_msg", 0) for r in rs]))
        d["n"] = len(rs)
        out[s] = d
    # Kruskal-Wallis + pairwise Mann-Whitney on throughput
    groups = [np.array([r["throughput_msg_s"] for r in by[s]]) for s in SYSTEMS if s in by]
    kw = stats.kruskal(*groups) if len(groups) > 1 else None
    pw = []
    for b in ("B1", "B2", "B3"):
        if b in by and "PBTI" in by:
            a = [r["throughput_msg_s"] for r in by["PBTI"]]; c = [r["throughput_msg_s"] for r in by[b]]
            u = stats.mannwhitneyu(a, c, alternative="two-sided")
            pw.append((b, float(u.pvalue), cliffs_delta(a, c)))
    adj = holm(np.array([p for _, p, _ in pw])) if pw else []
    sw = {s: float(stats.shapiro([r["throughput_msg_s"] for r in by[s]]).pvalue) for s in SYSTEMS if s in by and len(by[s]) >= 3}
    json.dump({"systems": out, "kruskal": [float(kw.statistic), float(kw.pvalue)] if kw else None,
               "pairwise": [(b, p, d, float(a)) for (b, p, d), a in zip(pw, adj)], "shapiro_p": sw},
              open(SUM / "throughput_summary.json", "w"), indent=1)
    for s, d in out.items():
        M(f"Tp{s}", fmt(d["throughput_msg_s"], 0)); M(f"Cpu{s}", fmt(d["cpu_us_per_msg"], 0))
        M(f"SvcP50{s}", fmt(d["svc_us_p50"], 0)); M(f"SvcP99{s}", fmt(d["svc_us_p99"], 0))
        M(f"Db{s}", fmt(d["db_bytes_per_msg"], 0)); M(f"Wire{s}", fmt(d["wire_bytes"], 0)); M(f"Edge{s}", fmt(d["edge_cpu_us_per_msg"], 0))
        lo, hi = d["throughput_msg_s_ci"]; M(f"Tp{s}lo", fmt(lo, 0)); M(f"Tp{s}hi", fmt(hi, 0))
    if "PBTI" in out:
        for k in ("parse", "crypto", "lifecycle", "policy", "history", "commit"):
            M("Stage" + k.capitalize(), fmt(out["PBTI"]["stage_" + k], 0))
        M("EvidenceBytes", fmt(out["PBTI"]["evidence_bytes"], 0))
        for b in ("B1", "B2", "B3"):
            if b in out:
                M(f"TpRatio{b}", fmt(out["PBTI"]["throughput_msg_s"] / out[b]["throughput_msg_s"], 2))
                M(f"WireRatio{b}", fmt(out["PBTI"]["wire_bytes"] / out[b]["wire_bytes"], 2))
                M(f"DbRatio{b}", fmt(out["PBTI"]["db_bytes_per_msg"] / out[b]["db_bytes_per_msg"], 2))
    M("TpReps", fmt(out.get("PBTI", {}).get("n", 0)))
    if kw:
        M("TpKWp", ptex(kw.pvalue))
    if len(adj):
        M("TpPairPmax", ptex(max(adj)))
        M("TpCliffMin", f"{min(abs(d) for _, _, d in pw):.2f}")
    rows_s = load("throughput_scaling")
    sc = defaultdict(list)
    for r in rows_s:
        sc[(r["system"], r["n_devices"])].append(r)
    out["scaling"] = {f"{k[0]}|{k[1]}": {"tp": float(np.mean([r["throughput_msg_s"] for r in v])),
                                          "p99": float(np.mean([r["svc_us_p99"] for r in v])),
                                          "rss": float(np.mean([r["rss_delta_mb"] for r in v]))} for k, v in sc.items()}
    json.dump(out["scaling"], open(SUM / "scaling_summary.json", "w"), indent=1)
    if sc:
        M("ScaleReps", fmt(min(len(v) for v in sc.values())))
        devs = sorted({k[1] for k in sc})
        M("ScaleDevMin", fmt(devs[0])); M("ScaleDevMax", fmt(devs[-1]))
        for s_ in SYSTEMS:
            tps = [out["scaling"][f"{s_}|{n}"]["tp"] for n in devs if f"{s_}|{n}" in out["scaling"]]
            if tps:
                M(f"Scale{s_}min", fmt(min(tps), 0)); M(f"Scale{s_}max", fmt(max(tps), 0))
                M(f"Scale{s_}drop", fmt(100 * (tps[0] - tps[-1]) / tps[0], 0))
    return out


# ============================================================================ MQTT end-to-end
def analyze_e2e():
    rows = [r for r in load("mqtt_e2e") if "lat_ms_p50" in r]
    if not rows:
        return None
    by = defaultdict(list)
    for r in rows:
        by[(r["system"], r["rate"])].append(r)
    rates = sorted({r["rate"] for r in rows})
    out = {}
    for (s, rate), rs in by.items():
        d = {}
        for m in ("lat_ms_p50", "lat_ms_p95", "lat_ms_p99", "throughput_msg_s", "verifier_cpu_us_per_msg",
                  "publisher_cpu_us_per_msg", "broker_cpu_us_per_msg"):
            v = [r[m] for r in rs if r.get(m) == r.get(m)]
            d[m] = float(np.mean(v)) if v else math.nan
            d[m + "_ci"] = boot_ci(v) if v else (math.nan, math.nan)
        d["n"] = len(rs)
        out[f"{s}|{rate}"] = d
        M(f"Ee{s}r{rate}pfifty", fmt(d["lat_ms_p50"], 1)); M(f"Ee{s}r{rate}pninetynine", fmt(d["lat_ms_p99"], 1))
        M(f"Ee{s}r{rate}tp", fmt(d["throughput_msg_s"], 0)); M(f"Ee{s}r{rate}pub", fmt(d["publisher_cpu_us_per_msg"], 0))
    tests = []
    for rate in rates:
        groups = {s: [r["lat_ms_p99"] for r in by.get((s, rate), [])] for s in WALL_SYSTEMS}
        if all(len(v) >= 2 for v in groups.values()):
            kw = stats.kruskal(*groups.values())
            for b in ("B1", "B2", "B3"):
                u = stats.mannwhitneyu(groups["PBTI"], groups[b], alternative="two-sided")
                tests.append({"rate": rate, "baseline": b, "p": float(u.pvalue), "delta": cliffs_delta(groups["PBTI"], groups[b]),
                              "kw_p": float(kw.pvalue)})
    if tests:
        adj = holm(np.array([t["p"] for t in tests]))
        for t, a in zip(tests, adj):
            t["p_holm"] = float(a)
    # validity check: in the end-to-end runs every message is legitimate, so every disposition must be an accept
    acc = tot = 0
    for r in rows:
        for k, n in (r.get("dispositions") or {}).items():
            tot += n
            acc += n if k.startswith("ACCEPT") else 0
    if tot:
        if acc != tot:
            print(f"WARNING: end-to-end runs contain {tot - acc} non-accept dispositions out of {tot}")
        M("EeAcceptPct", fmt(100.0 * acc / tot, 2))
        M("EeDispTotal", f"{tot:,}".replace(",", "{,}"))
    json.dump({"cells": out, "tests_p99": tests, "accepted": acc, "dispositions_total": tot},
              open(SUM / "mqtt_e2e_summary.json", "w"), indent=1)
    M("EeReps", fmt(max(d["n"] for d in out.values())))
    for rate in rates:
        bp = [out[f"{b}|{rate}"]["lat_ms_p99"] for b in ("B1", "B2", "B3") if f"{b}|{rate}" in out]
        if bp:
            M(f"EeBaser{rate}pninetyninemin", fmt(min(bp), 1)); M(f"EeBaser{rate}pninetyninemax", fmt(max(bp), 1))
    low = [d["lat_ms_p50"] for k, d in out.items() if int(k.split("|")[1]) <= 1000]
    if low:
        M("EeLowPFiftyMin", fmt(min(low), 1)); M("EeLowPFiftyMax", fmt(max(low), 1))
    if tests:
        M("EePNinetyNineHolmMin", ptex(min(t["p_holm"] for t in tests)))
        n_r = min(len(v) for v in by.values())
        M("EeMinAttainP", ptex(2.0 / math.comb(2 * n_r, n_r)))
        M("EeNTests", fmt(len(tests)))
        M("EeDeltaMaxRate", fmt(min(t["delta"] for t in tests if t["rate"] == max(rates)), 2))
    M("EeRates", ", ".join(str(r) for r in rates))
    return out, rates


def figure_performance(tp, e2e):
    fig = plt.figure(figsize=(7.0, 2.6), constrained_layout=True)
    gs = fig.add_gridspec(1, 3, width_ratios=[1.0, 1.35, 1.1])
    # (a) in-process throughput
    ax = fig.add_subplot(gs[0])
    if tp:
        xs = [s for s in WALL_SYSTEMS if s in tp]
        vals = [tp[s]["throughput_msg_s"] for s in xs]
        err = np.array([[tp[s]["throughput_msg_s"] - tp[s]["throughput_msg_s_ci"][0], tp[s]["throughput_msg_s_ci"][1] - tp[s]["throughput_msg_s"]] for s in xs]).T
        ax.bar(range(len(xs)), vals, color=[COLORS[s] for s in xs], width=0.62, edgecolor="#fcfcfb", linewidth=1.0)
        ax.errorbar(range(len(xs)), vals, yerr=err, fmt="none", ecolor=INK2, elinewidth=0.8, capsize=2)
        for i, v in enumerate(vals):
            ax.text(i, v * 1.02, f"{v:,.0f}", ha="center", va="bottom", fontsize=6.5, color=INK)
        ax.set_xticks(range(len(xs)), xs)
        ax.set_ylabel("messages / s (single core)")
        ax.set_ylim(0, max(vals) * 1.18)
        ax.grid(axis="y", color=GRID, linewidth=0.5); ax.set_axisbelow(True)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
    ax.set_title("(a) Saturation throughput", loc="left")
    # (b) e2e latency vs rate
    ax = fig.add_subplot(gs[1])
    if e2e:
        cells, rates = e2e
        for s in WALL_SYSTEMS:
            ys = [cells.get(f"{s}|{r}", {}).get("lat_ms_p99", np.nan) for r in rates]
            y50 = [cells.get(f"{s}|{r}", {}).get("lat_ms_p50", np.nan) for r in rates]
            ax.plot(rates, ys, color=COLORS[s], marker=MARKERS[s], markersize=4, linewidth=1.6, label=f"{s} p99")
            ax.plot(rates, y50, color=COLORS[s], marker=MARKERS[s], markersize=3, linewidth=1.0, linestyle=(0, (3, 2)), alpha=0.9)
        ax.set_xlabel("offered load (messages / s)")
        ax.set_ylabel("end-to-end latency (ms)")
        ax.set_yscale("log")
        ax.grid(color=GRID, linewidth=0.5); ax.set_axisbelow(True)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        ax.legend(fontsize=6.3, loc="upper left", handlelength=1.6, ncol=2)
        ax.text(0.99, 0.02, "solid: p99, dashed: p50", transform=ax.transAxes, ha="right", va="bottom", fontsize=6, color=MUTED)
    ax.set_title("(b) End-to-end latency, MQTT/TLS", loc="left")
    # (c) PBTI stage breakdown
    ax = fig.add_subplot(gs[2])
    if tp and "PBTI" in tp:
        st = ["parse", "crypto", "lifecycle", "policy", "history", "commit"]
        lab = {"parse": "parse", "crypto": "2× Ed25519 verify", "lifecycle": "credential status",
               "policy": "policy + freshness", "history": "history + lineage", "commit": "evidence + commit"}
        v = [tp["PBTI"]["stage_" + k] for k in st]
        ax.barh(range(len(st)), v, color=COLORS["PBTI"], height=0.6, edgecolor="#fcfcfb")
        for i, x in enumerate(v):
            ax.text(x + max(v) * 0.02, i, f"{x:.0f}", va="center", fontsize=6.5, color=INK)
        ax.set_yticks(range(len(st)), [lab[k] for k in st])
        ax.invert_yaxis()
        ax.set_xlabel("µs per message (mean)")
        ax.set_xlim(0, max(v) * 1.22)
        ax.grid(axis="x", color=GRID, linewidth=0.5); ax.set_axisbelow(True)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
    ax.set_title("(c) PBTI cost by stage", loc="left")
    fig.savefig(FIG / "fig_performance.pdf")
    plt.close(fig)


def supplementary_tables(tp, e2e):
    # Table S8: end-to-end latency per rate and system
    if e2e:
        cells, rates = e2e
        L = [r"\begin{tabular}{rlrrrrrr}", r"\toprule",
             r"\makecell[r]{Load\\(msg/s)} & Pipeline & \makecell[r]{p50\\(ms)} & \makecell[r]{p95\\(ms)} & \makecell[r]{p99 (ms)\\{[95\% CI]}} & \makecell[r]{Achieved\\(msg/s)} & \makecell[r]{Verifier CPU\\($\mu$s/msg)} & \makecell[r]{Publisher CPU\\($\mu$s/msg)}\\", r"\midrule"]
        for r in rates:
            for sname in ("B1", "B2", "B3", "PBTI"):
                d = cells.get(f"{sname}|{r}")
                if not d:
                    continue
                lo, hi = d["lat_ms_p99_ci"]
                L.append(f"{r if sname == 'B1' else ''} & {sname} & {fmt(d['lat_ms_p50'], 2)} & {fmt(d['lat_ms_p95'], 2)} & {fmt(d['lat_ms_p99'], 2)} [{fmt(lo, 1)}, {fmt(hi, 1)}]"
                         f" & {fmt(d['throughput_msg_s'], 0)} & {fmt(d['verifier_cpu_us_per_msg'], 0)} & {fmt(d['publisher_cpu_us_per_msg'], 0)}\\\\")
            L.append(r"\midrule" if r != rates[-1] else r"\bottomrule")
        L.append(r"\end{tabular}")
        (GEN / "tabS_e2e.tex").write_text("\n".join(L))
    # in-process throughput table (supplementary)
    if tp:
        L = [r"\begin{tabular}{lrrrrrrr}", r"\toprule",
             r"Pipeline & \makecell[r]{Throughput (msg/s)\\{[95\% CI]}} & \makecell[r]{CPU\\($\mu$s/msg)} & \makecell[r]{Service\\p50 ($\mu$s)} & \makecell[r]{Service\\p99 ($\mu$s)} & \makecell[r]{Wire\\(B/msg)} & \makecell[r]{Stored\\(B/msg)} & \makecell[r]{Edge CPU\\($\mu$s/msg)}\\", r"\midrule"]
        for sname in ("B1", "B2", "B3", "PBTI"):
            d = tp.get(sname)
            if not d:
                continue
            lo, hi = d["throughput_msg_s_ci"]
            L.append(f"{sname} & {fmt(d['throughput_msg_s'], 0)} [{fmt(lo, 0)}, {fmt(hi, 0)}] & {fmt(d['cpu_us_per_msg'], 0)} & {fmt(d['svc_us_p50'], 0)} & {fmt(d['svc_us_p99'], 0)}"
                     f" & {fmt(d['wire_bytes'], 0)} & {fmt(d['db_bytes_per_msg'], 0)} & {fmt(d['edge_cpu_us_per_msg'], 0)}\\\\")
        L += [r"\bottomrule", r"\end{tabular}"]
        (GEN / "tabS_throughput.tex").write_text("\n".join(L))
        sc = tp.get("scaling") or {}
        if sc:
            devs = sorted({int(k.split("|")[1]) for k in sc})
            L = [r"\begin{tabular}{l" + "r" * len(devs) + "}", r"\toprule",
                 "Pipeline & " + " & ".join(f"{d} devices" for d in devs) + r"\\", r"\midrule"]
            for sname in ("B1", "B2", "B3", "PBTI"):
                vals = [sc.get(f"{sname}|{d}", {}).get("tp", math.nan) for d in devs]
                L.append(sname + " & " + " & ".join(fmt(v, 0) for v in vals) + r"\\")
            L += [r"\bottomrule", r"\end{tabular}"]
            (GEN / "tabS_scaling.tex").write_text("\n".join(L))
    # environment table from manifests
    man = {}
    for name in ("scenarios", "throughput", "mqtt_e2e"):
        f = RAW / f"{name}.manifest.json"
        if f.exists():
            man[name] = json.loads(f.read_text())
    # V3: "current" is the digest of the source tree as it is now (same algorithm as experiments/run_campaign.py)
    import hashlib
    hh = hashlib.sha256()
    for sp in sorted((ROOT / "src").rglob("*.py")):
        hh.update(sp.relative_to(ROOT).as_posix().encode())
        hh.update(sp.read_bytes())
    cur = hh.hexdigest()
    fr3, fr = SUM / "regression_check_v3.json", SUM / "regression_check.json"
    if fr3.exists():
        reg = json.loads(fr3.read_text())
        n3 = sum(1 for c in reg["checked"] if c["file"].startswith("v3_"))
        reg_txt = (f"{len(reg['checked'])} stored specifications ({len(reg['checked']) - n3} revision-2, {n3} V3) re-run under the "
                   f"current source: {reg['differences']} differences (results/summary/regression_check_v3.json)")
    else:
        reg = json.loads(fr.read_text()) if fr.exists() else {"checked": [], "differences": "n/a"}
        reg_txt = (f"{len(reg['checked'])} stored B1--B3/PBTI specifications re-run under the current revision: "
                   f"{reg['differences']} differences (results/summary/regression_check.json)")
    if man:
        m = man.get("scenarios") or next(iter(man.values()))
        rows = [("CPU", m.get("cpu", "?")), ("Logical CPUs / RAM", f"{m.get('logical_cpus')} / {m.get('ram_gb')} GB"),
                ("Python", m.get("python", "?").split()[0]),
                ("cryptography / NumPy / SciPy / pandas", " / ".join(m.get("versions", {}).get(k, "?") for k in ("cryptography", "numpy", "scipy", "pandas")))]
        # source digest and platform per campaign, from every manifest (merged V3 manifests: per source run)
        label = {"scenarios": "scenarios (seeds 1--10)", "scenarios_part2": "scenarios (seeds 11--20)", "scenarios_part3_b4": "B4 scenarios (seeds 1--20)",
                 "ablations": "ablations (seeds 1--10)", "ablations_part2": "ablations (seeds 11--20)", "ablations_part3_b4": "B4 mixed workload (seeds 1--20)",
                 "revocation": "revocation (seeds 1--10)", "revocation_part2": "revocation (seeds 11--20)", "audit": "audit",
                 "throughput": "throughput", "throughput_scaling": "scaling", "mqtt_e2e": "end-to-end"}
        by_dig, by_plat = {}, {}

        def add(mm, lab):
            by_dig.setdefault(mm.get("source_sha256", "?"), []).append(lab)
            by_plat.setdefault(mm.get("platform", "?"), []).append(lab)

        for f in sorted(RAW.glob("*.manifest.json")):
            mm = json.loads(f.read_text())
            name = f.name.replace(".manifest.json", "")
            if "source_sha256" in mm:
                add(mm, label.get(name, name))
                continue
            covered = set()
            for sname, sm in mm.get("sources", {}).items():
                sy = (sm.get("args") or {}).get("systems") or []
                covered |= set(sy)
                add(sm, f"{name} ({'/'.join(sy)} rows)")
            orig = mm.get("original_run_manifest")
            fj = RAW / f"{name}.jsonl"
            rest = sorted({json.loads(ln)["system"] for ln in fj.read_text().splitlines() if ln.strip()} - covered) if fj.exists() else []
            if orig and rest:
                add(orig, f"{name} ({'/'.join(rest)} rows)")
        for pl, camps in by_plat.items():
            rows.append(("Platform", pl + " (" + "; ".join(camps) + ")" if len(by_plat) > 1 else pl))
        for dg in sorted(by_dig, key=lambda d: (d != cur, d)):
            tag = "Source digest " + dg[:12] + "\\ldots" + (" (final)" if dg == cur else "")
            rows.append((tag, "; ".join(by_dig[dg])))
        rows.append(("Regression check", reg_txt))
        if "mqtt_e2e" in man:
            rows.append(("Broker / MQTT client", f"{man['mqtt_e2e'].get('mosquitto', '?')} / paho-mqtt {man['mqtt_e2e'].get('paho', '?')}"))
        L = [r"\begin{tabular}{p{4.1cm}p{11.4cm}}", r"\toprule", r"Item & Value\\", r"\midrule"]
        for k, v in rows:
            L.append(f"{k} & \\texttt{{{str(v).replace('_', chr(92) + '_')}}}\\\\")
        L += [r"\bottomrule", r"\end{tabular}"]
        (GEN / "tabS_env.tex").write_text("\n".join(L))
    # Shapiro-Wilk statement for the supplementary text
    f = SUM / "throughput_summary.json"
    if f.exists():
        sw = json.loads(f.read_text()).get("shapiro_p", {})
        if sw:
            M("ShapiroMinP", ptex(min(sw.values())))


def analyze_attribution():
    """Macros from scripts/attribute_nonlegit.py (per-label attribution of non-legitimate authoritative observations)."""
    for name in ("nonlegit_attribution.json", "nonlegit_attribution_mixed.json", "nonlegit_attribution_b4.json"):
        f = SUM / name
        if not f.exists():
            print(f"WARNING: {f} missing; run scripts/attribute_nonlegit.py (make attribution)", file=sys.stderr)
            continue
        for key, d in json.loads(f.read_text()).items():
            sc, sysname = key.split("|")
            tag = "Attr" + (SCEN_LABEL.get(sc, "Mixed").split(" ")[0] if sc != "S99_mixed" else "Mixed") + sysname
            labels = d["per_run_mean_by_label"]
            M(tag + "Seeds", fmt(d["seeds"]))
            M(tag + "Labels", fmt(len(labels)))
            for lab, v in labels.items():
                M(tag + lab.replace("-", "").replace("_", ""), fmt(v, 2 if v < 1 else 1))


def main():
    analyze_attribution()
    analyze_scenarios()
    analyze_ablations()
    analyze_revocation()
    analyze_audit()
    tp = analyze_throughput()
    e2e = analyze_e2e()
    figure_performance(tp, e2e)
    supplementary_tables(tp, e2e)
    with open(GEN / "results_macros.tex", "w") as fh:
        fh.write("% AUTO-GENERATED by analysis/analyze.py from results/raw/*.jsonl -- do not edit by hand\n")
        words = "Zero One Two Three Four Five Six Seven Eight Nine".split()
        seen = set()
        for k, v in sorted(macros.items()):
            safe = "".join(words[int(ch)] if ch.isdigit() else ch for ch in k if ch.isalnum())
            assert safe not in seen, safe
            seen.add(safe)
            fh.write(f"\\newcommand{{\\R{safe}}}{{{v}}}\n")
    print(f"wrote {len(macros)} macros")


if __name__ == "__main__":
    main()
