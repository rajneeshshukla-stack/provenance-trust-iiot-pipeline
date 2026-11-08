#!/usr/bin/env python3
"""Check the qualitative statements of the article that are not printed through a generated macro.

Every statement below is worded in the article without a number (for example "all with R >= 5 s or the 10 s
cadence"); this script evaluates it on the analysis outputs and raw rows of TREE, so that a statement cannot stay in
the text when the data no longer support it. Run it on the corrected tree (the article's data) and, as a control of
the encoding, on the historical repository.

Usage: python3 -I claims_check.py TREE OUT_JSON [V9_SUMMARY_DIR]
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

T, OUT = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
V9S = Path(sys.argv[3]).resolve() if len(sys.argv) > 3 else None
S4 = T / "results/v4/summary"
c1 = pd.read_csv(S4 / "A1_comparisons.csv")
c3f = pd.read_csv(S4 / "A3F_comparisons.csv")
EQ = ("identical", "equivalent within margin", "equivalent within margin (significant difference)")
CELLS = ["S05_stolen_key", "S08_seq_reuse_bug", "S12_beyond_horizon", "S99_mixed"]
FG = ["run3", "run4", "run8", "run15"]
res = {}


def claim(key, text, ok, detail):
    res[key] = {"statement": text, "holds": bool(ok), "detail": detail}


def cls(df, **kw):
    q = df
    for k, v in kw.items():
        q = q[q[k] == v]
    if len(q) != 1:
        raise SystemExit(f"expected one comparison for {kw}, found {len(q)}")
    return q.iloc[0]


def sched(arm):
    """(R in s, C in s, kind) of a review arm."""
    if arm.endswith("-hist"):
        return (60, 10, "oneshot")
    if arm.endswith("-event"):
        return (None, None, "event")
    m = re.search(r"oneshot-d(\d+)c(\d+)$", arm)
    if m:
        return (int(m.group(1)), int(m.group(2)), "oneshot")
    m = re.search(r"-d(\d+)c(\d+)$", arm)
    return (int(m.group(1)), int(m.group(2)), "deferring")


# raw A1 rows: B5 O1 equals PBTI O1 in every seed, workload and schedule
raw = [json.loads(l) for l in open(T / "results/v4/raw/A1_review.jsonl")]
by = {(r["scenario"], r["arm"], r["seed"]): r for r in raw}
bad = [k for k, r in by.items() if r["arm"].startswith("B5") and
       r["nonlegit_auth"] != by[(k[0], "PBTI", k[2])]["nonlegit_auth"]]
claim("A1_O1_equal_every_seed", "review-schedule evaluation: B5 retained exactly as many forged observations as PBTI "
      "in every seed of every workload under every schedule (Section 6.1, 6.3)", not bad, {"violations": bad[:10]})

# matched event-driven review: every primary outcome identical or equivalent in all four workloads
rows = c1[(c1.arm == "B5-event") & (c1.ref == "PBTI-R-event")]
nonq = rows[~rows["class"].isin(EQ)][["cell", "outcome", "class"]].values.tolist()
claim("A1_matched_event_all_equiv", "B5ev vs PBTI-Rev: every primary outcome identical or equivalent within the margins "
      "in the four workloads (abstract, Sections 6.1, 6.3, 10)", len(rows) == 20 and not nonq,
      {"n": len(rows), "not_identical_or_equivalent": nonq})

# only event-driven review gives all-equivalent among the matched schedules
per = defaultdict(list)
for _, r in c1[c1.hypothesis == "H1c"].iterrows():
    per[r.arm].append(r["class"] in EQ)
all_eq = sorted(a for a, v in per.items() if all(v))
claim("A1_only_event_all_equiv", "only with event-driven review was every primary outcome identical or equivalent in "
      "all four workloads (Section 6.3)", all_eq == ["B5-event"], {"schedules_all_equivalent": all_eq})

# B5 vs PBTI-R beyond-margin W and AV5 cells are all with R >= 5 s or the 10 s cadence
wv = c1[(c1.hypothesis == "H1c") & (c1.outcome == "W") & (c1["class"] == "worse beyond margin")]
av = c1[(c1.hypothesis == "H1c") & (c1.outcome == "AV5") & (c1["class"] == "worse beyond margin")]


def slow(arm):
    R, C, kind = sched(arm)
    return kind != "event" and (R >= 5 or C == 10)


offend = [(r.arm, r.cell, r.outcome) for _, r in pd.concat([wv, av]).iterrows() if not slow(r.arm)]
claim("A1_worse_cells_slow_schedules", "B5 withheld more than PBTI-R beyond the margin, and made fewer observations "
      "available within 5 s, only with R >= 5 s or the 10 s cadence (Section 6.3)", not offend,
      {"W_worse": len(wv), "AV5_worse": len(av), "offending": offend})

# R = 0, C = 1 s, mixed workload, NLX: significant but interval crosses the -60 boundary
r = cls(c1, hypothesis="H1c", arm="B5-d0c1", ref="PBTI-R-d0c1", cell="S99_mixed", outcome="NLX")
lo, hi = (float(x) for x in re.findall(r"-?[\d.]+(?:e-?\d+)?", r.ci95)[:2])
claim("A1_d0c1_mixed_NLX_unresolved", "B5 minus PBTI-R exposure at R = 0, C = 1 s (mixed): significant, interval "
      "crosses the -60 record-second boundary (Section 6.3)",
      r["class"] == "different, within margin" and lo < -60 < hi,
      {"class": r["class"], "mean_d": r.mean_d, "ci95": [lo, hi], "p_holm": r.p_holm})

# H1d: schedules whose mixed-workload exposure is worse than the one-shot schedule beyond the margin
h1d = c1[(c1.hypothesis == "H1d") & (c1.cell == "S99_mixed") & (c1.outcome == "NLX")]
worse = sorted(h1d[h1d["class"] == "worse beyond margin"].arm)
expect = sorted(a for a in h1d.arm if sched(a)[2] == "event" or (sched(a)[0] is not None and sched(a)[0] <= 5))
claim("A1_H1d_fast_review_raises_exposure", "every schedule with R <= 5 s, and event-driven review, raised B5's "
      "mixed-workload exposure relative to the one-shot schedule beyond the margin (Section 6.3)", worse == expect,
      {"worse": worse, "expected": expect})

# H1a / H1b statements
h1a = {(r.cell, r.outcome): r["class"] for _, r in c1[c1.hypothesis == "H1a"].iterrows()}
ok = (all(h1a[(c, "O1")] == "identical" for c in CELLS)
      and all(h1a[(c, "W")] == "worse beyond margin" for c in ("S05_stolen_key", "S08_seq_reuse_bug", "S99_mixed"))
      and h1a[("S99_mixed", "NLX")] == "better beyond margin")
claim("A1_H1a_pattern", "one-shot B5 vs PBTI: identical O1 in all four workloads, W worse beyond the margin in E5, E8 "
      "and the mixed workload, exposure better beyond the margin in the mixed workload (Section 6.3)", ok,
      {k[0] + "/" + k[1]: v for k, v in h1a.items()})
h1b = {(r.cell, r.outcome): r["class"] for _, r in c1[c1.hypothesis == "H1b"].iterrows()}
ok = (h1b[("S05_stolen_key", "W")] in EQ and h1b[("S08_seq_reuse_bug", "W")] in EQ
      and h1b[("S12_beyond_horizon", "W")] == "better beyond margin" and h1b[("S99_mixed", "W")] == "better beyond margin")
claim("A1_H1b_pattern", "event-driven B5 vs PBTI: W equivalent in E5 and E8, B5 withheld less (better beyond the "
      "margin) in E11b and the mixed workload (Sections 6.1, 6.3)", ok, {k[0] + "/" + k[1]: v for k, v in h1b.items()})

# selective holds: PBTI-SH withheld more than event-driven B5 in all four FG cells
q = c3f[(c3f.outcome == "W") & (c3f.cell.isin(FG)) & (((c3f.arm == "PBTI-SH") & (c3f.ref == "B5-event")) |
                                                     ((c3f.arm == "B5-event") & (c3f.ref == "PBTI-SH")))]
sgn = [(r.cell, r.arm, r.ref, r.mean_d, r["class"]) for _, r in q.iterrows()]
more = [((r.arm == "PBTI-SH") and r.mean_d > 0) or ((r.arm == "B5-event") and r.mean_d < 0) for _, r in q.iterrows()]
claim("A3F_SH_withholds_more_than_Bev", "PBTI-SH withheld more than event-driven B5 in all four factorial cells "
      "(Section 6.1)", len(q) == 4 and all(more), {"comparisons": sgn})

# sweep: B5 differed significantly from PBTI in no sweep cell
sw = pd.read_csv(T / "results/summary/v3_sweep_tests.csv")
b5 = sw[sw.comp == "B5"]
sig = b5[b5.sig.astype(str).str.lower() == "true"][["factor", "level", "outcome"]].values.tolist()
claim("sweep_B5_no_significant_cell", "B5 differed significantly from PBTI in no sweep cell (Section 6.7)",
      len(b5) > 0 and not sig, {"tests": len(b5), "significant": sig})

# design ordering: B5's authoritative set never larger than PBTI-R's (same reviewer and schedule)
n = v = 0
for (sc, arm, seed), x in by.items():
    if not arm.startswith("B5-"):
        continue
    y = by.get((sc, "PBTI-R-" + arm.split("-", 1)[1], seed))
    if y is None:
        continue
    n += 1
    Wx, Wy = x["tm_wh_rec_s"] / x["tm_reach"], y["tm_wh_rec_s"] / y["tm_reach"]
    v += int(x["nonlegit_auth"] > y["nonlegit_auth"] or x["tm_nl_rec_s"] > y["tm_nl_rec_s"] + 1e-6
             or x["legit_missing"] < y["legit_missing"] or Wx < Wy - 1e-9 or x["tm_avail_5s"] > y["tm_avail_5s"] + 1e-12)
claim("A1_subset_ordering", "no matched run violated the ordering B5 <= PBTI-R (Section 5.2)", n > 0 and v == 0,
      {"runs": n, "violations": v})

# main evaluation: O2 differs from PBTI only in E11b, where PBTI-R with the same reviewer matches B5
x1 = pd.read_csv(T / "results/summary/v3_x1_preregistered_tests.csv")
o2 = x1[(x1.outcome.str.contains("O2|legit_missing", regex=True)) & (x1.comp == "B5")]
nonid = sorted(o2[o2.kind != "identical"].scenario)
claim("main_O2_differs_only_E11b", "main evaluation: B5's end-of-run losses identical to PBTI's in every scenario but "
      "E11b (Sections 6.2, 10)", nonid == ["S12_beyond_horizon"], {"not_identical": nonid})

# attacker-model campaign (optional, from the V9 summaries)
if V9S is not None and (V9S / "V9_attacker_comparisons.csv").exists():
    e = pd.read_csv(V9S / "V9_attacker_comparisons.csv")
    def g(att, a, b, k):
        q = e[(e.attacker == att) & (e.arm == a) & (e.ref == b) & (e.outcome == k)]
        return q.iloc[0] if len(q) == 1 else None
    hist_vs = g("consistent", "B5c-hist", "PBTI", "NLX")
    ev_vs = g("consistent", "B5c-event", "PBTI-R-event", "NLX")
    cells = pd.read_csv(V9S / "V9_attacker_cells.csv")
    con = cells[cells.attacker == "consistent"]
    claim("attacker_all_retain", "consistent impersonator: every pipeline retained forgeries at the end (limitations table)",
          bool((con.O1 > 0).all()), {r.arm: r.O1 for _, r in con.iterrows()})
    claim("attacker_oneshot_exposes_less", "consistent impersonator: one-shot B5 had less exposure than PBTI "
          "(limitations table; Section 6.5)", hist_vs is not None and hist_vs.mean_d < 0,
          {"mean_d": None if hist_vs is None else hist_vs.mean_d, "class": None if hist_vs is None else hist_vs["class"]})
    claim("attacker_event_close", "consistent impersonator: event-driven B5 and PBTI-R stay within the registered exposure "
          "margin of each other (limitations table)", ev_vs is not None and ev_vs["class"] in EQ,
          {"mean_d": None if ev_vs is None else ev_vs.mean_d, "class": None if ev_vs is None else ev_vs["class"]})

if V9S is not None and (V9S / "V9_runs_corrected_minus_original.csv").exists():
    rr = pd.read_csv(V9S / "V9_runs_corrected_minus_original.csv")
    b5s = rr[rr.system == "B5S"]
    claim("B5S_identical_to_historical", "B5s (no recovery): every primary outcome of every rerun equals the historical "
          "run (docs/BASELINES.md)", len(b5s) > 0 and int(b5s.runs_outcome_changed.sum()) == 0
          and bool((b5s.rerun == b5s.runs).all()),
          {r.stage: {"runs": int(r.runs), "rerun": int(r.rerun), "changed": int(r.runs_outcome_changed)}
           for _, r in b5s.iterrows()})
    allr = rr
    claim("all_specifications_rerun", "every B5/B5s specification of every stage was rerun (Sections 5.6, S3)",
          bool((allr.rerun == allr.runs).all()), {f"{r.stage}/{r.system}": [int(r.rerun), int(r.runs)]
                                                  for _, r in allr.iterrows()})

OUT.write_text(json.dumps({"tree": str(T), "claims": res,
                           "all_hold": all(v["holds"] for v in res.values())}, indent=1, default=str))
for k, v in res.items():
    print(("ok   " if v["holds"] else "FAIL ") + k)
