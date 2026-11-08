#!/usr/bin/env python3
"""Shared-assumption sensitivity on the captured histories of the audited runs (no new simulation).

For every run (results/oracle_audit/runs/*.pkl.gz, independent poller history) compute:
  * W, AV5, NLX and end-of-interval loss for truncated intervals [0, T'] (T' = end of production, +60 s, +120 s,
    full drain). The simulation is causal and the drain only stops the event loop, so the history restricted to
    [0, T'] is the history of the same run with a drain of T' - production (the final finalize() at T' adds only
    zero-length changes).
  * W split into the delay of observations available at T_end and the withheld time of observations lost at T_end.
  * AV5 as defined (first availability within 5 s, even if withdrawn later) versus AV5_stable (available within 5 s
    of production and continuously from then on to T_end).
  * non-legitimate pairs whose content equals a legitimate content (relabelled genuine content).
Then paired arm differences for the same campaign / scenario / seed.
"""
import glob
import gzip
import json
import pickle
from collections import defaultdict

import sys
sys.path.insert(0, "/home/claude/PBTI_v7/tools/oracle_audit")
from refmetrics import _len_within, _union  # noqa: E402

RUNS = "/home/claude/PBTI_v7/results/oracle_audit/runs"


def metrics_at(legit, iv, T):
    L = [o for o in legit if o["t_acc"] is not None and o["t_acc"] <= T]
    honest = set()
    for o in [o for o in legit if o["t_acc"] is not None]:
        honest |= o["pairs"]
    wh = wh_loss = 0
    av5 = av5_stable = lost = 0
    for o in L:
        u = _union([(a, min(b, T)) for p in o["pairs"] for (a, b) in iv.get(p, ()) if a < T])
        avail = _len_within(u, o["t_acc"], T)
        w_o = (T - o["t_acc"]) - avail
        wh += w_o
        at_end = bool(u) and u[-1][1] >= T
        if not at_end:
            lost += 1
            wh_loss += w_o
        if u and u[0][0] - o["t_prod"] <= 5000:
            av5 += 1
        if at_end and u[-1][0] - o["t_prod"] <= 5000:
            av5_stable += 1
    n = max(1, len(L))
    nlx = sum(_len_within([(a, min(b, T)) for a, b in v if a < T], 0, T) for p, v in iv.items() if p not in honest)
    return {"n": len(L), "W": wh / 1000 / n, "W_loss": wh_loss / 1000 / n, "W_delay": (wh - wh_loss) / 1000 / n,
            "AV5": av5 / n, "AV5_stable": av5_stable / n, "NLX": nlx / 1000, "lost": lost}


def main():
    out = {}
    for f in sorted(glob.glob(RUNS + "/*.pkl.gz")):
        tag = f.split("/")[-1][:-7]
        d = pickle.load(gzip.open(f))
        legit, (iv, _z, _e), t_end = d["legit"], d["hist"]["poll_call"], d["t_end"]
        prod = d["repo_row"].get("levels") is not None and 120_000 or 300_000
        produced = {o["content"] for o in legit}
        honest = set()
        for o in legit:
            if o["t_acc"] is not None:
                honest |= o["pairs"]
        relabel = sum(1 for p in iv if p not in honest and p[1] in produced)
        res = {"relabelled_nl_pairs": relabel, "t_end": t_end}
        for name, T in (("prod_end", prod), ("drain60", prod + 60_000), ("drain120", prod + 120_000),
                        ("full", t_end)):
            res[name] = metrics_at(legit, iv, min(T, t_end))
        out[tag] = res
    json.dump(out, open("/home/claude/PBTI_v7/results/oracle_audit/sensitivity.json", "w"), indent=1)
    # ----------------------------------------------------------------- per-run table
    print(f"{'run':46s} {'relab':>5s} | {'W(full)':>8s} {'Wdelay':>7s} {'Wloss':>7s} | {'AV5':>6s} {'AV5st':>6s} | "
          f"{'W(+60s)':>8s} {'W(+120s)':>8s}")
    for tag, r in out.items():
        fu = r["full"]
        print(f"{tag:46s} {r['relabelled_nl_pairs']:5d} | {fu['W']:8.3f} {fu['W_delay']:7.3f} {fu['W_loss']:7.3f} | "
              f"{fu['AV5']:6.4f} {fu['AV5_stable']:6.4f} | {r['drain60']['W']:8.3f} {r['drain120']['W']:8.3f}")
    # ----------------------------------------------------------------- paired arm differences
    groups = defaultdict(dict)
    for tag, r in out.items():
        camp, arm, loc, seed = tag.split("__")
        groups[(camp, loc, seed)][arm] = r
    print("\npaired differences (other arm minus PBTI), W in s/obs, NLX in record-s:")
    rows = []
    for (camp, loc, seed), arms in sorted(groups.items()):
        if "PBTI" not in arms and "PBTI-SH" not in arms:
            continue
        base_name = "PBTI" if "PBTI" in arms else "PBTI-SH"
        base = arms[base_name]
        for arm, r in arms.items():
            if arm == base_name:
                continue
            row = {"campaign": camp, "scenario": loc, "seed": seed, "arm": arm, "base": base_name}
            for T in ("prod_end", "drain60", "drain120", "full"):
                row[f"dW_{T}"] = r[T]["W"] - base[T]["W"]
                row[f"dNLX_{T}"] = r[T]["NLX"] - base[T]["NLX"]
            row["dAV5"] = r["full"]["AV5"] - base["full"]["AV5"]
            row["dAV5_stable"] = r["full"]["AV5_stable"] - base["full"]["AV5_stable"]
            row["dW_delay"] = r["full"]["W_delay"] - base["full"]["W_delay"]
            row["dW_loss"] = r["full"]["W_loss"] - base["full"]["W_loss"]
            rows.append(row)
            print(f"{camp:12s} {loc:20s} s{seed:>2s} {arm:12s}-{base_name:7s} dW: end-prod {row['dW_prod_end']:+7.3f} "
                  f"+60s {row['dW_drain60']:+7.3f} +120s {row['dW_drain120']:+7.3f} full {row['dW_full']:+7.3f} "
                  f"(delay {row['dW_delay']:+7.3f} loss {row['dW_loss']:+7.3f}) | dAV5 {row['dAV5']:+.4f} "
                  f"dAV5_stable {row['dAV5_stable']:+.4f} | dNLX full {row['dNLX_full']:+9.1f}")
    json.dump(rows, open("/home/claude/PBTI_v7/results/oracle_audit/sensitivity_paired.json", "w"), indent=1)


if __name__ == "__main__":
    main()
