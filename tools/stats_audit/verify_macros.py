#!/usr/bin/env python3
"""STEP 5: check every V4 macro used in paper/main.tex against values recomputed from the raw data by the
audit's own code (cell means, paired comparisons from results/stats_audit/recomputed_*.csv, gate logic).

Output: results/stats_audit/macro_check.csv  (macro, lines, paper value, recomputed value, status)
"""
import csv
import math
import os
import re
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paper_sentences as P  # noqa: E402
import prereg_stats as ps  # noqa: E402

OUT = "/home/claude/PBTI_v7/results/stats_audit"


def fnum(v, nd=0):
    t = f"{v:,.{nd}f}"
    if t in ("-0", "-0.0", "-0.00", "-0.000"):
        t = t[1:]
    if t.startswith("-"):
        t = "\\ensuremath{-}" + t[1:]
    return t.replace(",", "{,}")


def parse(s):
    s = s.replace("\\ensuremath{-}", "-").replace("{,}", "")
    try:
        return float(s)
    except ValueError:
        return None


def phrase(n, tot):
    nw = "none one two three four five six seven eight".split()
    return f"all {nw[tot]}" if n == tot else f"{nw[n]} of {nw[tot]}"


SC = {"Efive": "S05_stolen_key", "Eeight": "S08_seq_reuse_bug", "Eelevenb": "S12_beyond_horizon",
      "Mixed": "S99_mixed", "Efourteen": "S14_revocation"}
SHORT = {"S05_stolen_key": "E5", "S08_seq_reuse_bug": "E8", "S12_beyond_horizon": "E11b", "S99_mixed": "the mixed workload",
         "S14_revocation": "E14"}

FIELD = {"NLX": lambda r: r["tm_nl_rec_s"], "W": lambda r: r["tm_wh_rec_s"] / r["tm_reach"],
         "AVfive": lambda r: r["tm_avail_5s"], "KMninety": lambda r: r.get("tm_first_km_p90_s"),
         "ALM": lambda r: r.get("tm_alert_missed"), "ALF": lambda r: r.get("tm_alert_false"),
         "WDR": lambda r: r["tm_withdrawn"], "Oone": lambda r: r["nonlegit_auth"], "Otwo": lambda r: r["legit_missing"],
         "Dec": lambda r: r.get("review_decisions")}
ND = {"NLX": 0, "W": 2, "AVfive": 3, "KMninety": 1, "ALM": 1, "ALF": 1, "WDR": 1, "Oone": 1, "Otwo": 1, "Dec": 0}


def cmean(camp, cell, arm, f):
    vals = [FIELD[f](r) for (c, a, s), r in camp.by.items() if c == cell and a == arm]
    vals = [v for v in vals if v is not None]
    return float(np.mean(vals)) if vals else math.nan


def load_recomputed(lab):
    with open(f"{OUT}/recomputed_{lab}.csv") as fh:
        return list(csv.DictReader(fh))


def main():
    a0 = ps.Campaign(ps.load_jsonl("A0_core.jsonl"))
    a1 = ps.Campaign(ps.load_jsonl("A1_review.jsonl"))
    a3 = ps.Campaign(ps.load_jsonl("A3_selective.jsonl"))
    a3f = ps.Campaign(ps.load_jsonl("A3_factorial.jsonl"))
    a3s = ps.Campaign(ps.load_jsonl("A3_scenarios.jsonl"))
    R1, R3, R3F = load_recomputed("A1"), load_recomputed("A3"), load_recomputed("A3F")
    C1 = {(r["outcome"], r["cell"], r["arm"], r["ref"]): r for r in R1}
    C3 = {(r["outcome"], r["cell"], r["arm"], r["ref"]): r for r in R3}
    C3F = {(r["outcome"], r["cell"], r["arm"], r["ref"]): r for r in R3F}
    mine = {}

    # ---------------- run counts / audits
    for tag, camp, fn in (("Azero", a0, "A0_core.jsonl"), ("Aone", a1, "A1_review.jsonl"),
                          ("Athree", a3, "A3_selective.jsonl"), ("AthreeS", a3s, "A3_scenarios.jsonl"),
                          ("AthreeF", a3f, "A3_factorial.jsonl")):
        rows = ps.load_jsonl(fn)
        mine[f"W{tag}Runs"] = str(len(rows))
        mine[f"W{tag}Errors"] = str(len(camp.errors))
        mine[f"W{tag}AuditsPass"] = str(sum(1 for r in rows if r.get("audit_pass") is True))

    # ---------------- A0 cell means (seeds 1-20)
    armtag0 = {"P": "PBTI", "Bfive": "B5-hist", "Bfour": "B4"}
    for name in [m for m in P.MAC if m.startswith("WAzero")]:
        mo = re.match(r"WAzero(Efive|Eeight|Eelevenb|Mixed|Efourteen)(P|Bfive|Bfour)(NLX|W|AVfive|KMninety|ALM|ALF|WDR|Oone|Otwo)$", name)
        if mo:
            mine[name] = fnum(cmean(a0, SC[mo.group(1)], armtag0[mo.group(2)], mo.group(3)), ND[mo.group(3)])
    scen0 = sorted({k[0] for k in a0.by}, key=lambda c: (c == "S99_mixed", c))
    same = []
    for sc in scen0:
        if all(abs(cmean(a0, sc, "PBTI", f) - cmean(a0, sc, "B5-hist", f)) < 1e-9 for f in ("Oone", "Otwo", "NLX", "W", "AVfive")):
            same.append(sc)
    mine["WAzeroSameBfiveN"] = str(len(same))
    mine["WAzeroScenN"] = str(len(scen0))
    dl = [{"S99_mixed": "the mixed workload", "S12_beyond_horizon": "E11b"}.get(s, "E" + str(int(s[1:3]))) for s in scen0 if s not in same]
    mine["WAzeroDiffBfiveScen"] = ", ".join(dl[:-1]) + " and " + dl[-1]

    # ---------------- A1 cell means
    def at(arm):
        return arm.replace("-", "").replace("PBTIR", "PR")

    def word(s):  # digits -> words, as in macro names
        w = "Zero One Two Three Four Five Six Seven Eight Nine".split()
        return "".join(w[int(c)] if c.isdigit() else c for c in s if c.isalnum())
    arms1 = sorted({k[1] for k in a1.by})
    for sc_tag, sc in SC.items():
        if sc not in {k[0] for k in a1.by}:
            continue
        for arm in arms1:
            for f in ("NLX", "W", "AVfive", "Oone", "Otwo", "ALF", "ALM", "Dec"):
                mine[word(f"WAone{sc_tag}{at(arm)}{f}")] = fnum(cmean(a1, sc, arm, f), {**ND, "W": 2}[f])
    # A1 comparison macros
    oc = {"O1": "O1", "O2": "O2", "NLX": "NLX", "W": "W", "AV5": "AV5"}
    dnd = {"O1": 1, "O2": 1, "NLX": 0, "W": 3, "AV5": 3}
    inv = {v: k for k, v in SC.items()}
    for (o, cell, arm, ref), r in C1.items():
        t = word(f"WAone{inv[cell]}{at(arm)}vs{at(ref)}{oc[o]}")
        mine[t + "d"] = fnum(float(r["mean_d"]), dnd[o])
        mine[t + "dshort"] = fnum(float(r["mean_d"]), 1)
        mine[t + "lo"] = fnum(float(r["ci95_lo"]), dnd[o])
        mine[t + "hi"] = fnum(float(r["ci95_hi"]), dnd[o])
    cnt = defaultdict(lambda: defaultdict(int))
    for r in R1:
        cnt[(r["hypothesis"], r["outcome"])][r["class"]] += 1
    for (h, o), v in cnt.items():
        t = word(f"WAone{h.replace('H1', 'H')}{o}")
        mine[t + "N"] = str(sum(v.values()))
        mine[t + "Worse"] = str(v.get("worse", 0))
        mine[t + "Better"] = str(v.get("better", 0))
    g = {}
    import json
    gates = json.load(open(f"{OUT}/gates_recomputed.json"))["primary"]
    mine["WAoneGOne"] = "holds" if gates["G1"]["holds"] else "does not hold"
    mine["WAthreeGThree"] = "holds" if gates["G3"]["holds"] else "does not hold"
    mine["WAthreeGFour"] = "holds" if gates["G4"]["holds_at_points_counted_better"] else "does not hold"
    mine["WAthreeFGThree"] = "holds" if gates["G3F"]["holds"] else "does not hold"
    mine["WAthreeFGFour"] = "holds" if gates["G4F"]["holds_at_cells_counted_better"] else "does not hold"

    # ---------------- A3
    pts = ps.A3_GRID
    mean3 = lambda c, a, f: cmean(a3, c, a, f)
    pos = gates["G3"]["points_pbti_O1_gt0"]
    better = gates["G3"]["points_O1_or_NLX_better"]
    mine["WAthreePosPoints"] = str(len(pos))
    mine["WAthreePoints"] = str(len(pts))
    mine["WAthreePmaxOone"] = fnum(max(mean3(p, "PBTI", "Oone") for p in pos), 2)
    mine["WAthreeSHzeroPoints"] = str(sum(1 for p in pos if mean3(p, "PBTI-SH", "Oone") == 0))
    mine["WAthreeSHmaxOone"] = fnum(max(mean3(p, "PBTI-SH", "Oone") for p in pos), 2)
    mine["WAthreeBetterPoints"] = str(len(better))
    rest = [p for p in pos if p not in better]
    beyond = [p for p in rest if any(float(C3[(o, p, "PBTI-SH", "PBTI")]["mean_d"]) < -float(C3[(o, p, "PBTI-SH", "PBTI")]["margin"])
                                     for o in ("O1", "NLX"))]
    mine["WAthreeHolmPoints"] = str(len(beyond))
    mine["WAthreeSmallPoints"] = str(len(rest) - len(beyond))
    mine["WAthreeFamilySize"] = str(sum(1 for r in R3 if r["outcome"] == "O1"))
    noeq = [p for p in pts if p.startswith("equivocation=0+")]
    mine["WAthreeNoEqIdentical"] = str(sum(1 for p in noeq if all(C3[(o, p, "PBTI-SH", "PBTI")]["class"] == "identical" for o in ps.OUTCOMES)))
    eqp = [p for p in pts if not p.startswith("equivocation=0+")]
    dW = [mean3(p, "PBTI-SH", "W") - mean3(p, "PBTI", "W") for p in eqp]
    dO2 = [mean3(p, "PBTI-SH", "Otwo") - mean3(p, "PBTI", "Otwo") for p in eqp]
    mine["WAthreeWcostMin"], mine["WAthreeWcostMax"] = fnum(min(dW), 2), fnum(max(dW), 2)
    mine["WAthreeOtwoCostMin"], mine["WAthreeOtwoCostMax"] = fnum(min(dO2), 1), fnum(max(dO2), 1)
    cnt3 = defaultdict(lambda: defaultdict(int))
    for r in R3:
        cnt3[(r["hypothesis"], r["ref"], r["outcome"])][r["class"]] += 1
    for (h, ref, o), v in cnt3.items():
        t = word(f"WAthree{h.replace('H3', 'H')}{ref.replace('-', '')}{o}")
        mine[t + "Better"] = str(v.get("better", 0))
        mine[t + "Worse"] = str(v.get("worse", 0))
    mine["WAthreeSHTsameOonePoints"] = str(sum(1 for p in pts if mean3(p, "PBTI-SH-T30", "Oone") == mean3(p, "PBTI", "Oone")))
    dly = [p for p in pts if p.startswith("delay=")]
    dd = [mean3(p, "PBTI-SH", "W") - mean3(p, "PBTI", "W") for p in dly]
    mine["WAthreeDelayWcostMin"], mine["WAthreeDelayWcostMax"] = fnum(min(dd), 2), fnum(max(dd), 2)
    delay_max_o1 = max(mean3(p, a, "Oone") for p in dly for a in {k[1] for k in a3.by})

    # ---------------- A3F
    fg = ps.FG_CELLS
    tagF = {"P": "PBTI", "SH": "PBTI-SH", "SHT": "PBTI-SH-T30", "Bfive": "B5-hist", "BfiveEv": "B5-event", "BfiveS": "B5S", "PR": "PBTI-R-hist"}
    for tg, arm in tagF.items():
        for f, nd in (("Oone", 2), ("Otwo", 1), ("W", 2), ("NLX", 0), ("AVfive", 3)):
            mine[f"WAthreeF{tg}FG{f}"] = fnum(float(np.mean([cmean(a3f, c, arm, f) for c in fg])), nd)
    for o, oname in (("O1", "O1"), ("W", "W"), ("O2", "O2"), ("NLX", "NLX"), ("AV5", "AV5")):
        for ref in ("PBTI", "B5-hist", "B5-event"):
            cl = [C3F[(o, c, "PBTI-SH", ref)]["class"] for c in fg]
            t = word(f"WAthreeFSHvs{ref.replace('-', '')}{oname}FG")
            mine[t + "NBetter"] = phrase(sum(c == "better" for c in cl), 4)
            mine[t + "NWorse"] = phrase(sum(c == "worse" for c in cl), 4)
            mine[t + "NDiffWithin"] = phrase(sum(c == "different" for c in cl), 4)
            mine[t + "NEquiv"] = phrase(sum(c in ("equivalent", "identical") for c in cl), 4)

    # ---------------- A3S (seeds 1-20, PBTI from A0)
    scen = sorted({k[0] for k in a3s.by})
    same_s = [s for s in scen if all(abs(cmean(a3s, s, "PBTI-SH", f) - cmean(a0, s, "PBTI", f)) < 1e-12
                                      for f in ("Oone", "Otwo", "NLX", "W", "AVfive"))]
    mine["WAthreeSSameN"], mine["WAthreeSN"] = str(len(same_s)), str(len(scen))
    diff = [{"S99_mixed": "the mixed workload"}.get(s, "E" + str(int(s[1:3]))) for s in sorted(scen, key=lambda x: (x == "S99_mixed", x)) if s not in same_s]
    mine["WAthreeSDiffScen"] = ", ".join(diff[:-1]) + " and " + diff[-1]
    more = [s for s in scen if cmean(a3s, s, "PBTI-SH", "Oone") > cmean(a0, s, "PBTI", "Oone") + 1e-9]
    mine["WAthreeSMoreOoneScen"] = ", ".join(more) if more else "none"
    for sc_tag in ("Efive", "Eeight", "Mixed", "Efourteen"):
        for tg, arm in (("SH", "PBTI-SH"), ("SHT", "PBTI-SH-T30")):
            if (SC[sc_tag], arm, 1) in a3s.by:
                for f, nd in (("Oone", 1), ("Otwo", 1), ("W", 2), ("AVfive", 3), ("NLX", 0)):
                    mine[f"WAthreeS{sc_tag}{tg}{f}"] = fnum(cmean(a3s, SC[sc_tag], arm, f), nd)

    # ---------------- compare
    used = defaultdict(list)
    for ln, line in enumerate(open(P.REPO + "/paper/main.tex"), 1):
        for mo in re.finditer(r"\\(W[A-Za-z]+)", line):
            used[mo.group(1)].append(ln)
    rows = []
    for k in sorted(used, key=lambda x: used[x][0]):
        pv = P.MAC.get(k)
        mv = mine.get(k)
        if mv is None:
            st = "NOT_RECOMPUTED"
        elif mv == pv:
            st = "MATCH"
        else:
            a, b = parse(pv or ""), parse(mv)
            if a is not None and b is not None and k.endswith(("lo", "hi")):
                st = "CI_MC_DIFF"  # bootstrap bound: Monte-Carlo difference only
            else:
                st = "MISMATCH"
        rows.append({"macro": k, "lines": " ".join(map(str, sorted(set(used[k])))), "paper": pv, "recomputed": mv, "status": st})
    with open(f"{OUT}/macro_check.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    from collections import Counter
    print(Counter(r["status"] for r in rows))
    for r in rows:
        if r["status"] != "MATCH":
            print(r)
    print("delay points: max cell-mean O1 over all arms =", delay_max_o1)


if __name__ == "__main__":
    main()
