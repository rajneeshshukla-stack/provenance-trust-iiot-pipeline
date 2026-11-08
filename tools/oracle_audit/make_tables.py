#!/usr/bin/env python3
"""Render the markdown tables of the oracle-audit report from the result files (no hand transcription)."""
import glob
import json
from collections import OrderedDict

R = "/home/claude/PBTI_v7/results/oracle_audit"


def fmt(v, nd=3):
    if v is None:
        return "None"
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, float):
        if abs(v - round(v)) < 1e-12 and abs(v) >= 1:
            return f"{v:.1f}"
        return f"{v:.{nd}f}".rstrip("0").rstrip(".") if abs(v) < 1e6 else f"{v:.0f}"
    if isinstance(v, list):
        return "[" + ", ".join(map(str, v)) + "]"
    return str(v)


def hand_table():
    rows = json.load(open(f"{R}/hand_cases.json"))
    by = OrderedDict()
    for r in rows:
        by.setdefault(r["case"], []).append(r)
    out = ["| Case | Expected by hand (selected fields) | Oracle/temporal result (same fields) | Match repo (n/N) | Match reference (n/N) |",
           "|---|---|---|---|---|"]
    key_fields = ("nonlegit_auth", "legit_missing", "tm_nl_rec_s", "tm_wh_rec_s", "W", "tm_avail_1s", "tm_avail_5s",
                  "tm_avail_30s", "tm_first_km_p50_s", "tm_first_km_p90_s", "tm_never_avail", "tm_withdrawn",
                  "tm_zero_flips", "legit_quarantined", "holds", "held_distinct_ever", "taint_events", "dup_auth",
                  "tm_alert_missed", "win_corrupt", "win_incomplete")
    short = {"nonlegit_auth": "O1", "legit_missing": "O2", "tm_nl_rec_s": "NLX", "tm_wh_rec_s": "WH", "W": "W",
             "tm_avail_1s": "AV1", "tm_avail_5s": "AV5", "tm_avail_30s": "AV30", "tm_first_km_p50_s": "KM50",
             "tm_first_km_p90_s": "KM90", "tm_never_avail": "never", "tm_withdrawn": "wdr", "tm_zero_flips": "zero",
             "legit_quarantined": "quar", "holds": "holds", "held_distinct_ever": "heldDist", "taint_events": "taint",
             "dup_auth": "dup", "tm_alert_missed": "ALM", "win_corrupt": "winCorr", "win_incomplete": "winInc"}
    tot = [0, 0, 0, 0]
    for case, rr in by.items():
        sel = [r for r in rr if r["field"] in key_fields]
        e = "; ".join(f"{short[r['field']]}={fmt(r['expected'])}" for r in sel)
        g = "; ".join(f"{short[r['field']]}={fmt(r['repo'])}" + ("" if r["match_repo"] else " **≠**") for r in sel)
        mr = [r["match_repo"] for r in rr if r["match_repo"] is not None]
        mf = [r["match_ref"] for r in rr if r["match_ref"] is not None]
        tot[0] += sum(mr); tot[1] += len(mr); tot[2] += sum(mf); tot[3] += len(mf)
        name = case.replace("case_", "")
        out.append(f"| {name} | {e} | {g} | {sum(mr)}/{len(mr)} | {sum(mf)}/{len(mf)} |")
    out.append(f"| **Total** | | | **{tot[0]}/{tot[1]}** | **{tot[2]}/{tot[3]}** |")
    return "\n".join(out)


def run_table():
    out = ["| Run (campaign / arm / scenario or cell / seed) | Fidelity: stored fields reproduced | O1 | O2 | NLX (rec-s) | Withheld (rec-s) | W (s/obs) | AV5 | KM p50 (s) | KM p90 (s) | Never | Withdrawn | Zero flips | Transitions | Poller = Tracer (pairs) | 21 metrics: ref = re-run = stored |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    allok = 0
    files = sorted(glob.glob(f"{R}/runs/*.json"))
    for f in files:
        r = json.load(open(f))
        c = {x["metric"] + "|" + x["field"]: x for x in r["compare"]}
        v = lambda k: c[k]["ref_poll"]  # noqa: E731
        ok = all(x["match_ref_repo"] and x["match_repo_stored"] and
                 x["ref_tracer"] == x["ref_poll"] for x in r["compare"])
        allok += ok
        n_m = sum(1 for x in r["compare"] if x["match_ref_repo"] and x["match_repo_stored"])
        tag = r["tag"].replace("__", " / ")
        out.append(f"| {tag} | {r['fidelity']['compared'] - len(r['fidelity']['diff'])}/{r['fidelity']['compared']} | "
                   f"{v('O1_content|nonlegit_auth')} | {v('O2_content|legit_missing')} | {v('NLX_s|tm_nl_rec_s'):.3f} | "
                   f"{v('withheld_s|tm_wh_rec_s'):.3f} | {v('W_s|W'):.4f} | {v('AV5|tm_avail_5s'):.4f} | "
                   f"{fmt(v('KM50_s|tm_first_km_p50_s'))} | {fmt(v('KM90_s|tm_first_km_p90_s'))} | "
                   f"{v('never|tm_never_avail')} | {v('withdrawn|tm_withdrawn')} | {v('zero|tm_zero_flips')} | "
                   f"{r['poller']['transitions']} | {r['hist_pairs']['poll'] - r['hist_pairs']['differ']}/{r['hist_pairs']['poll']} | "
                   f"{n_m}/{len(r['compare'])} |")
    return "\n".join(out), allok, len(files)


def sens_table():
    rows = json.load(open(f"{R}/sensitivity_paired.json"))
    out = ["| Campaign / scenario / seed | Arm − base | ΔW end of production | ΔW +60 s drain | ΔW +120 s | ΔW full drain (published) | ΔW delay part | ΔW loss part | ΔAV5 (published) | ΔAV5_stable | ΔNLX (rec-s) |",
           "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        out.append(f"| {r['campaign']} / {r['scenario']} / {r['seed']} | {r['arm']} − {r['base']} | {r['dW_prod_end']:+.3f} | "
                   f"{r['dW_drain60']:+.3f} | {r['dW_drain120']:+.3f} | {r['dW_full']:+.3f} | {r['dW_delay']:+.3f} | "
                   f"{r['dW_loss']:+.3f} | {r['dAV5']:+.4f} | {r['dAV5_stable']:+.4f} | {r['dNLX_full']:+.1f} |")
    return "\n".join(out)


def wdecomp_table():
    s = json.load(open(f"{R}/sensitivity.json"))
    out = ["| Run | W (s/obs) | delay part | permanent-loss part | loss share | AV5 | AV5_stable | relabelled NL pairs |",
           "|---|---|---|---|---|---|---|---|"]
    for tag, r in s.items():
        fu = r["full"]
        share = fu["W_loss"] / fu["W"] if fu["W"] else 0.0
        out.append(f"| {tag.replace('__', ' / ')} | {fu['W']:.3f} | {fu['W_delay']:.3f} | {fu['W_loss']:.3f} | {share:.1%} | "
                   f"{fu['AV5']:.4f} | {fu['AV5_stable']:.4f} | {r['relabelled_nl_pairs']} |")
    return "\n".join(out)


if __name__ == "__main__":
    t1 = hand_table()
    t2, ok, n = run_table()
    t3 = sens_table()
    t4 = wdecomp_table()
    open(f"{R}/tables.md", "w").write("## hand\n\n" + t1 + "\n\n## runs\n\n" + t2 + f"\n\nall-match runs: {ok}/{n}\n\n## sens\n\n" + t3 + "\n\n## wdecomp\n\n" + t4 + "\n")
    print(t1)
    print()
    print(t2)
    print(f"\nall-match runs: {ok}/{n}")
    print()
    print(t3)
    print()
    print(t4)
