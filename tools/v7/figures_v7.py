#!/usr/bin/env python3
"""V7 figures with neutral labels (no internal stage names), redrawn from the stored raw rows and cell summaries.

fig_review_delay.pdf : withheld time W versus minimum review age R (review-schedule evaluation, seeds 21-40)
fig_selective_cells.pdf : retained forgeries O1 and withheld time W in the eight factorial cells with equivocation
                          high (amendment-informed analysis, seeds 21-40)
Colour encodes the pipeline family (PBTI family blue, B5 family orange, PBTI-SH family aqua: dataviz reference
palette slots 1-3, validated all-pairs in light mode); line style, marker fill or hatching encodes the variant, so
identity never rests on colour alone. Bootstrap intervals use the same procedure and keys as the stored analysis
(percentile bootstrap of the mean, 10,000 resamples, generator seeded with 20261104 and CRC32 of the key).

Usage: python3 -B figures_v7.py REPO_DIR OUT_FIG_DIR
"""
import json
import math
import sys
import zlib
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

REPO, OUT = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
OUT.mkdir(parents=True, exist_ok=True)
RNG_SEED, N_BOOT = 20261104, 10_000
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SHORT = {"S05_stolen_key": "E5 stolen keys", "S08_seq_reuse_bug": "E8 sequence-reuse fault",
         "S12_beyond_horizon": "E11b beyond-horizon backlog", "S99_mixed": "Mixed workload"}
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7, "axes.edgecolor": INK2, "axes.linewidth": 0.6,
                     "xtick.color": INK2, "ytick.color": INK2, "pdf.fonttype": 42})


def boot(d, key):
    d = np.asarray(d, float)
    if np.all(d == d[0]):
        return float(d[0]), float(d[0])
    rng = np.random.default_rng([RNG_SEED, zlib.crc32(key.encode())])
    b = d[rng.integers(0, len(d), (N_BOOT, len(d)))].mean(axis=1)
    return float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))


def W_of(r):
    return r["tm_wh_rec_s"] / max(1, r["tm_reach"])


def style(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.tick_params(length=2.5, width=0.6, labelsize=6.5)


# ------------------------------------------------------------------ review delay figure
by = defaultdict(lambda: defaultdict(list))
for line in (REPO / "results/v4/raw/A1_review.jsonl").read_text().splitlines():
    r = json.loads(line)
    if "error" in r:
        continue
    by[r["scenario"]][r["arm"]].append(r)
cells = ["S05_stolen_key", "S08_seq_reuse_bug", "S12_beyond_horizon", "S99_mixed"]
Rs = [0, 1, 5, 60]
xpos = {0: 0, 1: 1, 5: 2, 60: 3}
fig, axes = plt.subplots(1, 4, figsize=(7.2, 2.35))
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
            ax.errorbar([xpos[R] + (0.1 if cad == 10 else 0) for R in Rs], ys, yerr=[lo, hi], color=col, marker=mk,
                        markersize=4, linewidth=1.1, linestyle=ls, capsize=1.8, elinewidth=0.8,
                        markerfacecolor=col if cad == 1 else "white", markeredgewidth=0.9,
                        label=f"{fam}, deferring rule, cadence {cad} s")
        ev = [W_of(r) for r in by[sc][f"{fam}-event"]]
        ax.plot([-0.75], [np.mean(ev)], marker=mk, color=col, markersize=5, markerfacecolor="white",
                markeredgewidth=1.2, linestyle="none", label=f"{fam}, event-driven review")
        hs = [W_of(r) for r in by[sc][f"{fam}-hist"]]
        ax.plot([3.75], [np.mean(hs)], marker=mk, color=col, markersize=5, markerfacecolor=col, alpha=0.55,
                markeredgewidth=0.0, linestyle="none", label=f"{fam}, one-shot rule (R = 60 s, cadence 10 s)")
    p = [W_of(r) for r in by[sc]["PBTI"]]
    ax.axhline(np.mean(p), color=INK2, linewidth=0.9, linestyle="--", label="PBTI without reviewer")
    for xv in (-0.38, 3.42):
        ax.axvline(xv, color=GRID, linewidth=0.8, zorder=0)
    ax.set_xticks([-0.75, 0, 1, 2, 3, 3.75])
    ax.set_xticklabels(["event", "0", "1", "5", "60", "one-\nshot"], fontsize=6.3)
    ax.set_xlim(-1.15, 4.15)
    ax.set_title(SHORT[sc], fontsize=7.5, color=INK)
    ax.set_xlabel("minimum review age R (s)", fontsize=6.8, color=INK2)
    lo_y, hi_y = ax.get_ylim()
    ax.set_ylim(0, hi_y * 1.05)
    style(ax)
axes[0].set_ylabel("withheld time W (s per observation)", fontsize=6.8, color=INK2)
hd = {}
for ax in axes:
    for h_, l_ in zip(*ax.get_legend_handles_labels()):
        hd.setdefault(l_, h_)
order = ["B5, deferring rule, cadence 1 s", "B5, deferring rule, cadence 10 s", "B5, event-driven review",
         "B5, one-shot rule (R = 60 s, cadence 10 s)", "PBTI-R, deferring rule, cadence 1 s",
         "PBTI-R, deferring rule, cadence 10 s", "PBTI-R, event-driven review",
         "PBTI-R, one-shot rule (R = 60 s, cadence 10 s)", "PBTI without reviewer"]
fig.legend([hd[o] for o in order], order, loc="lower center", ncol=3, fontsize=6.2, frameon=False,
           bbox_to_anchor=(0.5, -0.14), labelcolor=INK)
fig.tight_layout(rect=(0, 0.13, 1, 1), w_pad=0.6)
fig.savefig(OUT / "fig_review_delay.pdf", bbox_inches="tight")
fig.savefig(OUT / "fig_review_delay.png", dpi=220, bbox_inches="tight")
plt.close(fig)

# ------------------------------------------------------------------ selective holds on the factorial cells
cm = pd.read_csv(REPO / "results/v4/summary/A3F_cells.csv").set_index(["cell", "arm"])
points = ["run2", "run3", "run4", "run5", "run8", "run9", "run14", "run15"]
FG = {"run3", "run4", "run8", "run15"}
arms = [("PBTI", "PBTI", BLUE, None), ("B5-hist", "B5, one-shot 60/10 s", ORANGE, None),
        ("B5-event", "B5, event-driven", ORANGE, "////"), ("B5S", "B5s (no recovery)", ORANGE, "...."),
        ("PBTI-SH", "PBTI-SH", AQUA, None), ("PBTI-SH-T30", "PBTI-SH, 30 s timeout", AQUA, "////")]
fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.55))
x = np.arange(len(points))
w = 0.128
plt.rcParams["hatch.linewidth"] = 0.6
for ax, code, lab in ((axes[0], "O1", "retained forgeries O1 (per run)"),
                      (axes[1], "W", "withheld time W (s per observation)")):
    for k, (arm, name, col, hatch) in enumerate(arms):
        ys = [float(cm.loc[(p, arm), code]) for p in points]
        ax.bar(x + (k - 2.5) * w, ys, width=w * 0.86, color=col if hatch is None else "white",
               edgecolor=col, hatch=hatch, linewidth=0.7, label=name)
    ax.set_xticks(x)
    ax.set_xticklabels([("cell " if i == 0 else "") + p.replace("run", "") + ("*" if p in FG else "")
                        for i, p in enumerate(points)], fontsize=6.5)
    ax.set_xlabel("factorial cell with equivocation high (* suppressed runs also high)", fontsize=6.8, color=INK2)
    ax.set_ylabel(lab, fontsize=6.8, color=INK2)
    style(ax)
axes[0].text(0.99, 0.97, "PBTI-SH: 0 in every cell", transform=axes[0].transAxes, fontsize=6.3, va="top",
             ha="right", color=INK2)
h, l = axes[0].get_legend_handles_labels()
fig.legend(h, l, loc="lower center", ncol=6, fontsize=6.2, frameon=False, bbox_to_anchor=(0.5, -0.05),
           labelcolor=INK)
fig.tight_layout(rect=(0, 0.07, 1, 1))
fig.savefig(OUT / "fig_selective_cells.pdf", bbox_inches="tight")
fig.savefig(OUT / "fig_selective_cells.png", dpi=220, bbox_inches="tight")
plt.close(fig)
print("written:", sorted(p.name for p in OUT.glob("fig_*")))

# ------------------------------------------------------------------ supplementary: selective-hold grid at 5 % equivocation
g = pd.read_csv(REPO / "results/v4/summary/A3_cells.csv").set_index(["cell", "arm"])
sup = [0, 0.01, 0.05, 0.1]
pts = [f"equivocation=0.05+missing={s:g}" for s in sup]
arms_g = [("PBTI", "PBTI", BLUE, "o", "-"), ("PBTI-R-hist", "PBTI-R, one-shot 60/10 s", BLUE, "P", ":"),
          ("B5-hist", "B5, one-shot 60/10 s", ORANGE, "^", "-"), ("B5-event", "B5, event-driven", ORANGE, "v", "--"),
          ("B5S", "B5s (no recovery)", ORANGE, "s", ":"), ("PBTI-SH", "PBTI-SH", AQUA, "D", "-"),
          ("PBTI-SH-T30", "PBTI-SH, 30 s timeout", AQUA, "d", "--")]
fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.45))
for ax, code, lab in ((axes[0], "O1", "retained forgeries O1 (per run)"),
                      (axes[1], "W", "withheld time W (s per observation)")):
    for arm, name, col, mk, ls in arms_g:
        ys = [float(g.loc[(p, arm), code]) for p in pts]
        ax.plot([s * 100 for s in sup], ys, marker=mk, linestyle=ls, color=col, linewidth=1.1, markersize=4,
                markerfacecolor=col if ls == "-" else "white", markeredgewidth=0.9, label=name)
    ax.set_xlabel("suppressed messages (%) at 5 % equivocation", fontsize=6.8, color=INK2)
    ax.set_ylabel(lab, fontsize=6.8, color=INK2)
    ax.set_xticks([0, 1, 5, 10])
    style(ax)
h, l = axes[0].get_legend_handles_labels()
fig.legend(h, l, loc="lower center", ncol=4, fontsize=6.2, frameon=False, bbox_to_anchor=(0.5, -0.1),
           labelcolor=INK)
fig.tight_layout(rect=(0, 0.11, 1, 1))
fig.savefig(OUT / "fig_selective_grid.pdf", bbox_inches="tight")
fig.savefig(OUT / "fig_selective_grid.png", dpi=220, bbox_inches="tight")
plt.close(fig)
print("written fig_selective_grid")


# ------------------------------------------------------------------ performance figure (Figure 5)
# Redrawn from the stored summaries with the V7 colours (PBTI blue, B5 orange as in Figures 3-4; the Zero-Trust
# baseline B2 in neutral grey). Panel (c) shows Rule L + lineage WITHOUT the nested evidence-commit time, so that the
# stages add up to the per-message total reported in the text (the V6 figure plotted the nested timer, which
# included commit and double-counted it).
GREY = INK2
PC = {"PBTI": BLUE, "B5": ORANGE, "B2": GREY}
PM = {"PBTI": "o", "B5": "^", "B2": "v"}
bt = pd.read_csv(REPO / "results" / "summary" / "v3_batching_summary.csv")
ee = pd.read_csv(REPO / "results" / "summary" / "v3_e2e_summary.csv")
tp = [json.loads(l) for l in open(REPO / "results" / "raw" / "throughput.jsonl")]
fig, axes = plt.subplots(1, 4, figsize=(7.3, 2.05))
ax = axes[0]
for s in ("B2", "B5", "PBTI"):
    d = bt[(bt.system == s) & (bt.workers == 1)].sort_values("batch")
    ax.errorbar(d.batch, d.throughput, yerr=[d.throughput - d.tp_lo, d.tp_hi - d.throughput], marker=PM[s], ms=3,
                lw=1.0, capsize=1.5, color=PC[s], label=s)
ax.set_xscale("log", base=2)
ax.set_xlabel("group-commit batch (messages)")
ax.set_ylabel("messages/s")
ax.set_title("(a) Batch size, 1 worker", loc="left", fontsize=7)
ax.legend(fontsize=5.5, frameon=False)
ax = axes[1]
for s in ("B5", "PBTI"):
    d = bt[(bt.system == s) & (bt.batch == 128)].sort_values("workers")
    ax.errorbar(d.workers, d.throughput, yerr=[d.throughput - d.tp_lo, d.tp_hi - d.throughput], marker=PM[s], ms=3,
                lw=1.0, capsize=1.5, color=PC[s], label=s)
ax.set_xscale("log", base=2)
ax.set_xticks([1, 2, 4, 8])
ax.set_xticklabels(["1", "2", "4", "8"])
ax.set_xlabel("signature workers (2 vCPUs)")
ax.set_title("(b) Workers, batch 128", loc="left", fontsize=7)
ax.legend(fontsize=5.5, frameon=False)
ax = axes[2]
pb = [r for r in tp if r["system"] == "PBTI"]
mean_ = lambda k: float(np.mean([r.get(k, 0) for r in pb]))
stages = [("signatures", mean_("stage_us_crypto")), ("evidence + commit", mean_("stage_us_commit")),
          ("Rule L + lineage", mean_("stage_us_history") - mean_("stage_us_commit")),
          ("credential status", mean_("stage_us_lifecycle")), ("policy", mean_("stage_us_policy")),
          ("parse", mean_("stage_us_parse"))]
ax.barh(range(len(stages)), [v for _, v in stages], color=BLUE, height=0.6)
for i, (_, v) in enumerate(stages):
    ax.text(v + 6, i, f"{v:.0f}", va="center", fontsize=5.5, color=INK)
ax.set_yticks(range(len(stages)))
ax.set_yticklabels([l for l, _ in stages], fontsize=5.5)
ax.invert_yaxis()
ax.set_xlim(0, max(v for _, v in stages) * 1.18)
ax.set_xlabel("$\\mu$s per message (sum %.0f)" % sum(v for _, v in stages))
ax.set_title("(c) PBTI cost by stage", loc="left", fontsize=7)
ax = axes[3]
for s in ("B2", "PBTI"):
    d = ee[ee.system == s].sort_values("rate")
    ax.errorbar(d.rate, d.lat_ms_p50, yerr=[d.lat_ms_p50 - d.lat_ms_p50_lo, d.lat_ms_p50_hi - d.lat_ms_p50],
                marker=PM[s], ms=3, lw=1.0, capsize=1.5, color=PC[s], label=f"{s} p50")
    ax.errorbar(d.rate, d.lat_ms_p99, yerr=[d.lat_ms_p99 - d.lat_ms_p99_lo, d.lat_ms_p99_hi - d.lat_ms_p99],
                marker=PM[s], ms=3, lw=1.0, ls="--", capsize=1.5, color=PC[s], mfc="white", label=f"{s} p99")
ax.set_yscale("log")
ax.set_xticks(sorted(ee.rate.unique()))
ax.set_xlabel("offered load (msg/s)")
ax.set_ylabel("latency (ms)")
ax.set_title("(d) MQTT/TLS latency, one host", loc="left", fontsize=7)
ax.set_ylim(4, 4e4)
ax.legend(fontsize=4.8, ncol=2, loc="upper left", frameon=False, handlelength=1.8, columnspacing=0.8)
for ax in axes:
    style(ax)
    ax.tick_params(labelsize=5.5)
fig.tight_layout(w_pad=0.6)
fig.savefig(OUT / "fig_performance_costs.pdf", bbox_inches="tight", pad_inches=0.02)
fig.savefig(OUT / "fig_performance_costs.png", dpi=220, bbox_inches="tight", pad_inches=0.02)
plt.close(fig)
print("written", OUT / "fig_performance_costs.pdf", "stage sum", round(sum(v for _, v in stages), 1))
