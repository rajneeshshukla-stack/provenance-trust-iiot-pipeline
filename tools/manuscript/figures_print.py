#!/usr/bin/env python3
"""Article and supplement figures, drawn at final print size from the stored rows and summaries of REPO_DIR.

Sources (unchanged):
  tools/v7/figures_v7.py  -> fig_review_delay (main text); fig_performance_costs, fig_selective_cells,
                             fig_selective_grid (supplement)
  analysis/analyze_v3.py  -> fig_sweep (function figure_sweep; written there as fig_v3_sweep)
What changed (presentation only):
  * each figure is exactly as wide as the text block it is placed in (main text with the MDPI \\extralength:
    525.52 TeX pt = 7.2716 in; supplement: 17.4 cm = 6.8504 in), so it is included at scale 1;
  * all text is 8-9 pt at that size (Liberation Sans, metrically equal to Arial);
  * one colour per pipeline in every figure: PBTI family blue #2a78d6, B5 family orange #eb6834, PBTI-SH aqua
    #1baf7a, the other baselines (B2, B4) grey #77766f; marker shape, line style, fill or hatching encodes the
    variant, so identity never rests on colour alone (the V6 sweep figure had B4 orange and B5 green);
  * count axes start at 0 (the V6 sweep figure showed negative ranges for all-zero panels);
  * the five all-zero sweep factors (former Figure S8) are not drawn; their values are written to the data table.
Values, bootstrap procedure, keys and seeds are unchanged (percentile bootstrap of the mean, 10,000 resamples,
generator seeded with 20261104 and CRC32 of the key). Every plotted value is written to OUT/data/<figure>.csv.

Usage: python3 -I figures_print.py REPO_DIR OUT_DIR   (REPO_DIR: the historical or the corrected-comparator tree)
"""
import csv
import json
import sys
import zlib
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

REPO, OUT = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "data").mkdir(exist_ok=True)
(OUT / "png600").mkdir(exist_ok=True)
RNG_SEED, N_BOOT = 20261104, 10_000
BLUE, ORANGE, AQUA, GREY = "#2a78d6", "#eb6834", "#1baf7a", "#77766f"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
W_MAIN = 525.52245 / 72.27      # main text, full width inside adjustwidth{-\extralength}{0cm}
W_SUPP = 17.4 / 2.54            # supplement text width (A4, 1.8 cm margins)
SHORT = {"S05_stolen_key": "E5 stolen keys", "S08_seq_reuse_bug": "E8 sequence-reuse fault",
         "S12_beyond_horizon": "E11b beyond-horizon backlog", "S99_mixed": "Mixed workload"}
plt.rcParams.update({
    "font.family": "Liberation Sans", "font.size": 8, "axes.titlesize": 8.5, "axes.labelsize": 8,
    "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 8, "figure.titlesize": 8.5,
    "axes.edgecolor": INK2, "axes.linewidth": 0.6, "xtick.color": INK2, "ytick.color": INK2,
    "xtick.labelcolor": INK, "ytick.labelcolor": INK, "axes.labelcolor": INK, "text.color": INK,
    "legend.frameon": False, "legend.handlelength": 2.2, "legend.columnspacing": 1.4,
    "pdf.fonttype": 42, "hatch.linewidth": 0.6,
    "figure.constrained_layout.h_pad": 0.02, "figure.constrained_layout.w_pad": 0.02,
})


def boot(d, key):
    d = np.asarray(d, float)
    if np.all(d == d[0]):
        return float(d[0]), float(d[0])
    rng = np.random.default_rng([RNG_SEED, zlib.crc32(key.encode())])
    b = d[rng.integers(0, len(d), (N_BOOT, len(d)))].mean(axis=1)
    return float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))


def W_of(r):
    return r["tm_wh_rec_s"] / max(1, r["tm_reach"])


def style(ax, grid_axis="y"):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis=grid_axis, color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.tick_params(length=2.5, width=0.6, pad=2)


def save(fig, name, rows, header):
    fig.savefig(OUT / f"{name}.pdf")
    fig.savefig(OUT / "png600" / f"{name}.png", dpi=600)
    plt.close(fig)
    with open(OUT / "data" / f"{name}.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    print("written", name, f"({len(rows)} plotted values)")


# ====================================================================== Figure 2: review delay (main text)
by = defaultdict(lambda: defaultdict(list))
for line in (REPO / "results/v4/raw/A1_review.jsonl").read_text().splitlines():
    r = json.loads(line)
    if "error" in r:
        continue
    by[r["scenario"]][r["arm"]].append(r)
cells = ["S05_stolen_key", "S08_seq_reuse_bug", "S12_beyond_horizon", "S99_mixed"]
Rs = [0, 1, 5, 60]
xpos = {0: 0, 1: 1, 5: 2, 60: 3}
rows = []
fig, axes = plt.subplots(1, 4, figsize=(W_MAIN, 2.62), layout="constrained")
for ax, sc in zip(axes, cells):
    for fam, col, mk in (("B5", ORANGE, "^"), ("PBTI-R", BLUE, "o")):
        for cad, ls in ((1, "-"), (10, ":")):
            ys, lo, hi = [], [], []
            for R in Rs:
                v = [W_of(r) for r in by[sc][f"{fam}-d{R}c{cad}"]]
                m = float(np.mean(v))
                c = boot(v, f"fig|{sc}|{fam}|{R}|{cad}")
                ys.append(m)
                lo.append(m - c[0])
                hi.append(c[1] - m)
                rows.append([SHORT[sc], f"{fam} deferring", cad, R, len(v), m, c[0], c[1]])
            ax.errorbar([xpos[R] + (0.1 if cad == 10 else 0) for R in Rs], ys, yerr=[lo, hi], color=col, marker=mk,
                        markersize=4.5, linewidth=1.2, linestyle=ls, capsize=2, elinewidth=0.8,
                        markerfacecolor=col if cad == 1 else "white", markeredgewidth=1.0,
                        label=f"{fam}, deferring, cadence {cad} s")
        ev = [W_of(r) for r in by[sc][f"{fam}-event"]]
        rows.append([SHORT[sc], f"{fam} event-driven", "", "", len(ev), float(np.mean(ev)), "", ""])
        ax.plot([-0.75], [np.mean(ev)], marker=mk, color=col, markersize=5.5, markerfacecolor="white",
                markeredgewidth=1.3, linestyle="none", label=f"{fam}, event-driven")
        hs = [W_of(r) for r in by[sc][f"{fam}-hist"]]
        rows.append([SHORT[sc], f"{fam} one-shot 60/10", 10, 60, len(hs), float(np.mean(hs)), "", ""])
        ax.plot([3.75], [np.mean(hs)], marker=mk, color=col, markersize=5.5, markerfacecolor=col, alpha=0.55,
                markeredgewidth=0.0, linestyle="none", label=f"{fam}, one-shot (R = 60 s, C = 10 s)")
    p = [W_of(r) for r in by[sc]["PBTI"]]
    rows.append([SHORT[sc], "PBTI without reviewer", "", "", len(p), float(np.mean(p)), "", ""])
    ax.axhline(np.mean(p), color=INK2, linewidth=1.0, linestyle="--", label="PBTI without reviewer")
    for xv in (-0.38, 3.42):
        ax.axvline(xv, color=GRID, linewidth=0.8, zorder=0)
    ax.set_xticks([-0.75, 0, 1, 2, 3, 3.75])
    ax.set_xticklabels(["event", "0", "1", "5", "60", "one-\nshot"])
    ax.set_xlim(-1.2, 4.2)
    ax.set_title(SHORT[sc])
    ax.set_ylim(0, ax.get_ylim()[1] * 1.05)
    style(ax)
axes[0].set_ylabel("withheld time W\n(s per observation)")
fig.supxlabel("minimum review age R (s)", fontsize=8)
hd = {}
for ax in axes:
    for h_, l_ in zip(*ax.get_legend_handles_labels()):
        hd.setdefault(l_, h_)
order = ["B5, deferring, cadence 1 s", "B5, deferring, cadence 10 s", "B5, event-driven",
         "B5, one-shot (R = 60 s, C = 10 s)", "PBTI-R, deferring, cadence 1 s", "PBTI-R, deferring, cadence 10 s",
         "PBTI-R, event-driven", "PBTI-R, one-shot (R = 60 s, C = 10 s)", "PBTI without reviewer"]
fig.legend([hd[o] for o in order], order, loc="outside upper center", ncol=3)
fig.get_layout_engine().set(h_pad=0.05)
save(fig, "fig_review_delay", rows, ["workload", "arm", "cadence_s", "R_s", "n_seeds", "W_mean", "ci_lo", "ci_hi"])

# ====================================================================== Figure S-perf: performance (supplement; Figure 3 of V7)
PC = {"PBTI": BLUE, "B5": ORANGE, "B2": GREY}
PM = {"PBTI": "o", "B5": "^", "B2": "v"}
bt = pd.read_csv(REPO / "results" / "summary" / "v3_batching_summary.csv")
ee = pd.read_csv(REPO / "results" / "summary" / "v3_e2e_summary.csv")
tp = [json.loads(l) for l in open(REPO / "results" / "raw" / "throughput.jsonl")]
rows = []
fig, axes = plt.subplots(1, 4, figsize=(W_SUPP, 2.35), layout="constrained",
                         gridspec_kw={"width_ratios": [1.2, 0.9, 1.3, 1.15]})
ax = axes[0]
for s in ("B2", "B5", "PBTI"):
    d = bt[(bt.system == s) & (bt.workers == 1)].sort_values("batch")
    ax.errorbar(d.batch, d.throughput, yerr=[d.throughput - d.tp_lo, d.tp_hi - d.throughput], marker=PM[s], ms=4,
                lw=1.2, capsize=1.8, color=PC[s], label=s)
    rows += [["a", s, int(b), 1, t, lo_, hi_] for b, t, lo_, hi_ in zip(d.batch, d.throughput, d.tp_lo, d.tp_hi)]
ax.set_xscale("log", base=2)
ax.set_xticks([1, 8, 32, 128, 512])
ax.set_xticklabels(["1", "8", "32", "128", "512"])
ax.set_xlabel("commit batch (messages)")
ax.set_ylabel("messages/s")
ax.set_ylim(0, ax.get_ylim()[1])
ax.set_title("(a) batch size, 1 worker", loc="left")
ax = axes[1]
for s in ("B5", "PBTI"):
    d = bt[(bt.system == s) & (bt.batch == 128)].sort_values("workers")
    ax.errorbar(d.workers, d.throughput, yerr=[d.throughput - d.tp_lo, d.tp_hi - d.throughput], marker=PM[s], ms=4,
                lw=1.2, capsize=1.8, color=PC[s], label=s)
    rows += [["b", s, 128, int(w_), t, lo_, hi_] for w_, t, lo_, hi_ in zip(d.workers, d.throughput, d.tp_lo,
                                                                          d.tp_hi)]
ax.set_xscale("log", base=2)
ax.set_xticks([1, 2, 4, 8])
ax.set_xticklabels(["1", "2", "4", "8"])
ax.set_xlabel("verification workers")
ax.set_ylim(0, ax.get_ylim()[1])
ax.set_title("(b) workers, batch 128", loc="left")
ax = axes[2]
pb = [r for r in tp if r["system"] == "PBTI"]
mean_ = lambda k: float(np.mean([r.get(k, 0) for r in pb]))  # noqa: E731
stages = [("signatures", mean_("stage_us_crypto")), ("evidence + commit", mean_("stage_us_commit")),
          ("Rule L + lineage", mean_("stage_us_history") - mean_("stage_us_commit")),
          ("credential status", mean_("stage_us_lifecycle")), ("policy", mean_("stage_us_policy")),
          ("parse", mean_("stage_us_parse"))]
ax.barh(range(len(stages)), [v for _, v in stages], color=BLUE, height=0.62)
for i, (_, v) in enumerate(stages):
    ax.text(v + 8, i, f"{v:.0f}", va="center", fontsize=8, color=INK)
rows += [["c", "PBTI", lab_, "", v, "", ""] for lab_, v in stages]
ax.set_yticks(range(len(stages)))
ax.set_yticklabels([l_ for l_, _ in stages])
ax.tick_params(axis="y", length=0)
ax.invert_yaxis()
ax.set_xlim(0, max(v for _, v in stages) * 1.3)
ax.set_xlabel("µs per message (sum %.0f)" % sum(v for _, v in stages))
ax.set_title("(c) PBTI cost by stage", loc="left")
ax = axes[3]
for s in ("B2", "PBTI"):
    d = ee[ee.system == s].sort_values("rate")
    ax.errorbar(d.rate, d.lat_ms_p50, yerr=[d.lat_ms_p50 - d.lat_ms_p50_lo, d.lat_ms_p50_hi - d.lat_ms_p50],
                marker=PM[s], ms=4, lw=1.2, capsize=1.8, color=PC[s])
    ax.errorbar(d.rate, d.lat_ms_p99, yerr=[d.lat_ms_p99 - d.lat_ms_p99_lo, d.lat_ms_p99_hi - d.lat_ms_p99],
                marker=PM[s], ms=4, lw=1.2, ls="--", capsize=1.8, color=PC[s], mfc="white")
    rows += [["d", s, "p50", int(r_), v, lo_, hi_] for r_, v, lo_, hi_ in zip(d.rate, d.lat_ms_p50, d.lat_ms_p50_lo,
                                                                           d.lat_ms_p50_hi)]
    rows += [["d", s, "p99", int(r_), v, lo_, hi_] for r_, v, lo_, hi_ in zip(d.rate, d.lat_ms_p99, d.lat_ms_p99_lo,
                                                                           d.lat_ms_p99_hi)]
ax.set_yscale("log")
rates = sorted(ee.rate.unique())
ax.set_xticks(rates)
ax.set_xticklabels([f"{r_:g}" for r_ in rates], rotation=0)
ax.set_xlabel("offered load (messages/s)")
ax.set_ylabel("latency (ms)")
ax.set_title("(d) MQTT/TLS latency", loc="left")
ax.set_ylim(4, 2e4)
ax.legend([Line2D([], [], color=INK2, lw=1.2, marker="o", ms=4), Line2D([], [], color=INK2, lw=1.2, ls="--",
                                                                     marker="o", ms=4, mfc="white")],
          ["p50", "p99"], loc="upper left", ncol=2, handlelength=2.0, columnspacing=1.0, borderaxespad=0.2)
for ax in axes:
    style(ax, "x" if ax is axes[2] else "y")
fig.legend([Line2D([], [], color=PC[s], marker=PM[s], ms=4.5, lw=1.2) for s in ("PBTI", "B5", "B2")],
           ["PBTI", "B5", "B2"], loc="outside upper center", ncol=3)
save(fig, "fig_performance_costs", rows, ["panel", "system", "batch_or_stage_or_quantile", "workers_or_rate",
                                          "value", "ci_lo", "ci_hi"])
print("  stage sum (us):", round(sum(v for _, v in stages), 1))

# ====================================================================== Figure S-a3: selective-hold grid (supplement)
g = pd.read_csv(REPO / "results/v4/summary/A3_cells.csv").set_index(["cell", "arm"])
sup = [0, 0.01, 0.05, 0.1]
pts = [f"equivocation=0.05+missing={s:g}" for s in sup]
arms_g = [("PBTI", "PBTI", BLUE, "o", "-"), ("PBTI-R-hist", "PBTI-R, one-shot", BLUE, "P", ":"),
          ("B5-hist", "B5, one-shot", ORANGE, "^", "-"), ("B5-event", "B5, event-driven", ORANGE, "v", "--"),
          ("B5S", "B5s (no recovery)", ORANGE, "s", ":"), ("PBTI-SH", "PBTI-SH", AQUA, "D", "-"),
          ("PBTI-SH-T30", "PBTI-SH, 30 s timeout", AQUA, "d", "--")]
rows = []
fig, axes = plt.subplots(1, 2, figsize=(W_SUPP, 2.75), layout="constrained")
for ax, code, lab in ((axes[0], "O1", "retained forgeries O1 (per run)"),
                      (axes[1], "W", "withheld time W (s per observation)")):
    for arm, name, col, mk, ls in arms_g:
        ys = [float(g.loc[(p_, arm), code]) for p_ in pts]
        rows += [[code, name, s_ * 100, y_] for s_, y_ in zip(sup, ys)]
        ax.plot([s_ * 100 for s_ in sup], ys, marker=mk, linestyle=ls, color=col, linewidth=1.2, markersize=4.5,
                markerfacecolor=col if ls == "-" else "white", markeredgewidth=1.0, label=name)
    ax.set_ylabel(lab)
    ax.set_xticks([0, 1, 5, 10])
    ax.set_ylim(0, ax.get_ylim()[1])
    style(ax)
fig.supxlabel("suppressed messages (%) at 5% equivocation", fontsize=8)
h, l_ = axes[0].get_legend_handles_labels()
fig.legend(h, l_, loc="outside upper center", ncol=4)
save(fig, "fig_selective_grid", rows, ["outcome", "arm", "suppressed_pct", "mean"])

# ====================================================================== Figure S-factorial: factorial cells (supplement)
cm = pd.read_csv(REPO / "results/v4/summary/A3F_cells.csv").set_index(["cell", "arm"])
points = ["run2", "run3", "run4", "run5", "run8", "run9", "run14", "run15"]
FG = {"run3", "run4", "run8", "run15"}
arms = [("PBTI", "PBTI", BLUE, None), ("B5-hist", "B5, one-shot", ORANGE, None),
        ("B5-event", "B5, event-driven", ORANGE, "////"), ("B5S", "B5s (no recovery)", ORANGE, "...."),
        ("PBTI-SH", "PBTI-SH", AQUA, None), ("PBTI-SH-T30", "PBTI-SH, 30 s timeout", AQUA, "////")]
rows = []
fig, axes = plt.subplots(1, 2, figsize=(W_SUPP, 2.85), layout="constrained")
x = np.arange(len(points))
w = 0.13
for ax, code, lab in ((axes[0], "O1", "retained forgeries O1 (per run)"),
                      (axes[1], "W", "withheld time W (s per observation)")):
    for k, (arm, name, col, hatch) in enumerate(arms):
        ys = [float(cm.loc[(p_, arm), code]) for p_ in points]
        rows += [[code, name, p_.replace("run", ""), y_] for p_, y_ in zip(points, ys)]
        ax.bar(x + (k - 2.5) * w, ys, width=w * 0.86, color=col if hatch is None else "white",
               edgecolor=col, hatch=hatch, linewidth=0.8, label=name)
    ax.set_xticks(x)
    ax.set_xticklabels([p_.replace("run", "") + ("*" if p_ in FG else "") for p_ in points])
    ax.set_ylabel(lab)
    style(ax)
axes[0].text(0.99, 0.98, "PBTI-SH: 0 in every cell", transform=axes[0].transAxes, fontsize=8, va="top",
             ha="right", color=INK2)
fig.supxlabel("factorial cell with equivocation high (*: suppressed runs also high)", fontsize=8)
h, l_ = axes[0].get_legend_handles_labels()
fig.legend(h, l_, loc="outside upper center", ncol=3)
save(fig, "fig_selective_cells", rows, ["outcome", "arm", "cell", "mean"])

# ====================================================================== Figure S-sweep: stressor sweep (supplement)
sw = pd.read_csv(REPO / "results" / "summary" / "v3_sweep_summary.csv")
LEVELS = (0.0, 0.01, 0.05, 0.10, 0.20)
FACT_LABEL = {"equivocation": "Equivocation", "relay": "Relay forgery", "compromise": "Discovery\ndelay",
              "revstale": "Revocation\nstaleness", "missing": "Suppressed\nruns", "clock": "Clock error"}
main_sel = ["equivocation", "relay", "compromise", "revstale", "missing", "clock"]
rest = ["loss", "dup", "reorder", "delay", "burst"]
SYS = (("B4", GREY, "s", "-", 1.2, 4.0, None), ("PBTI", BLUE, "o", "-", 1.6, 4.5, None),
       ("B5", ORANGE, "^", "--", 1.1, 4.5, "white"))
rows = []
fig, axes = plt.subplots(2, 6, figsize=(W_SUPP, 3.25), layout="constrained", sharex=True)
for j, f in enumerate(main_sel):
    for i, (metric, ylab) in enumerate((("nonlegit_auth", "O1 per run"), ("legit_missing", "O2 per run"))):
        ax = axes[i, j]
        for s, col, mk, ls, lw, ms, mfc in SYS:
            d = sw[(sw.factor == f) & (sw.system == s)].set_index("level")
            xs = [lv * 100 for lv in LEVELS if lv in d.index]
            ys = [float(d.loc[lv, metric]) for lv in LEVELS if lv in d.index]
            lo = [float(d.loc[lv, metric + "_lo"]) for lv in LEVELS if lv in d.index]
            hi = [float(d.loc[lv, metric + "_hi"]) for lv in LEVELS if lv in d.index]
            rows += [[f, metric, s, x_, y_, a_, b_] for x_, y_, a_, b_ in zip(xs, ys, lo, hi)]
            ax.fill_between(xs, lo, hi, color=col, alpha=0.16, lw=0)
            ax.plot(xs, ys, marker=mk, ms=ms, lw=lw, ls=ls, color=col, mfc=mfc or col, mew=1.0, label=s,
                    zorder=4 if s == "B5" else 3)
        top = max(1.0, ax.get_ylim()[1])
        ax.set_ylim(0, top)
        if top == 1.0:   # every value of this panel is zero
            ax.set_yticks([0, 1])
        ax.set_xticks([0, 10, 20])
        style(ax, "both")
        if i == 0:
            ax.set_title(FACT_LABEL[f])
        if j == 0:
            ax.set_ylabel(ylab)
for f in rest:   # not drawn: every value is zero; written to the data table for checking
    for metric in ("nonlegit_auth", "legit_missing"):
        for s in ("B4", "PBTI", "B5"):
            d = sw[(sw.factor == f) & (sw.system == s)].set_index("level")
            rows += [[f, metric, s, lv * 100, float(d.loc[lv, metric]), float(d.loc[lv, metric + "_lo"]),
                      float(d.loc[lv, metric + "_hi"])] for lv in LEVELS]
fig.supxlabel("stressor level (%)", fontsize=8)
h, l_ = axes[0, 0].get_legend_handles_labels()
order = [l_.index(n) for n in ("PBTI", "B5", "B4")]
fig.legend([h[k] for k in order], ["PBTI", "B5", "B4"], loc="outside upper center", ncol=3)
save(fig, "fig_sweep", rows, ["factor", "outcome", "system", "level_pct", "mean", "ci_lo", "ci_hi"])
zero = [r for r in rows if r[0] in rest]
print("  remaining factors all zero:", all(r[4] == 0 and r[5] == 0 and r[6] == 0 for r in zero), len(zero), "values")
