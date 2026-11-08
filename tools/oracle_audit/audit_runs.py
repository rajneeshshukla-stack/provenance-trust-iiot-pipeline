#!/usr/bin/env python3
"""Oracle audit driver: re-run selected campaign specifications with independent capture (capture.py), compute the
reference metrics (refmetrics.py) and compare them with (a) the repository's oracle/temporal outputs on the same run
and (b) the stored rows in results/v4/raw/*.jsonl.

Usage: python3 audit_runs.py [--only N ...] [--out DIR]
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import pickle
import sys
import time
from pathlib import Path

sys.path.insert(0, "/home/claude/PBTI_v7/tools/oracle_audit")
import capture  # noqa: E402  (installs the process-local instrumentation)
from refmetrics import compute  # noqa: E402

REPO = Path(capture.REPO)
CONF = {"A0_core": REPO / "experiments/v4_configs/A0_core.json",
        "A1_review": REPO / "experiments/v4_configs/A1_review.json",
        "A3_factorial": REPO / "experiments/v4_configs/amendment1/A3_factorial.json"}

# (campaign, arm, scenario or factorial point, seed)
SELECT = [
    ("A1_review", "PBTI", "S05_stolen_key", 21), ("A1_review", "PBTI-R-hist", "S05_stolen_key", 21),
    ("A1_review", "B5-hist", "S05_stolen_key", 21),
    ("A1_review", "PBTI", "S08_seq_reuse_bug", 21), ("A1_review", "PBTI-R-hist", "S08_seq_reuse_bug", 21),
    ("A1_review", "B5-hist", "S08_seq_reuse_bug", 21),
    ("A1_review", "PBTI", "S12_beyond_horizon", 21), ("A1_review", "PBTI-R-hist", "S12_beyond_horizon", 21),
    ("A1_review", "B5-hist", "S12_beyond_horizon", 21),
    ("A1_review", "PBTI", "S99_mixed", 21), ("A1_review", "PBTI-R-hist", "S99_mixed", 21),
    ("A1_review", "B5-hist", "S99_mixed", 21),
    ("A1_review", "B5-event", "S05_stolen_key", 22),
    ("A0_core", "PBTI", "S05_stolen_key", 1), ("A0_core", "B5-hist", "S05_stolen_key", 1),
    ("A0_core", "PBTI", "S14_revocation", 1), ("A0_core", "B5-hist", "S14_revocation", 1),
    ("A0_core", "PBTI-R-hist", "S99_mixed", 2),
    ("A3_factorial", "PBTI-SH", "run3", 21), ("A3_factorial", "PBTI-SH-T30", "run3", 21),
]

# reference metric -> repository field (W derived as in analysis/analyze_v4.py:W_of)
MAP = [("O1_content", "nonlegit_auth"), ("O2_content", "legit_missing"), ("n_reachable", "n_reachable"),
       ("n_reachable", "tm_reach"), ("n_produced", "n_produced"), ("NLX_s", "tm_nl_rec_s"),
       ("nl_pairs_ever", "tm_nl_pairs_ever"), ("nl_auth_end", "tm_nl_auth_end"), ("withheld_s", "tm_wh_rec_s"),
       ("W_s", "W"), ("AV1", "tm_avail_1s"), ("AV5", "tm_avail_5s"), ("AV30", "tm_avail_30s"),
       ("AV60", "tm_avail_60s"), ("never", "tm_never_avail"), ("withdrawn", "tm_withdrawn"),
       ("withdrawn_end", "tm_withdrawn_end"), ("KM50_s", "tm_first_km_p50_s"), ("KM90_s", "tm_first_km_p90_s"),
       ("KM99_s", "tm_first_km_p99_s"), ("zero", "tm_zero_flips")]
TIMING = set(capture.TIMING) | {"store_bytes", "store_bytes_per_reach", "wire_bytes_mean"}


def same(a, b, tol=1e-9):
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if isinstance(a, float) and math.isnan(a):
            return isinstance(b, float) and math.isnan(b)
        return abs(a - b) <= tol * max(1.0, abs(a), abs(b))
    return a == b


def stored_rows():
    out = {}
    for camp in ("A0_core", "A1_review", "A3_factorial"):
        for line in open(REPO / f"results/v4/raw/{camp}.jsonl"):
            r = json.loads(line)
            loc = r.get("point") if r.get("kind") == "sweep" else r.get("scenario")
            out[(camp, r["arm"], loc, r["seed"])] = r
    return out


def find_spec(camp, arm, loc, seed):
    import run_v4
    conf = json.loads(CONF[camp].read_text())
    for s in run_v4.expand(conf, [seed]):
        sloc = s.get("point") if s["kind"] == "sweep" else s["scenario"]
        if s["arm"] == arm and sloc == loc:
            return s
    raise KeyError((camp, arm, loc, seed))


def with_W(row):
    row = dict(row)
    row["W"] = row["tm_wh_rec_s"] / max(1, row["tm_reach"])
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=int, nargs="*")
    ap.add_argument("--out", default="/home/claude/PBTI_v7/results/oracle_audit")
    a = ap.parse_args()
    outdir = Path(a.out)
    (outdir / "runs").mkdir(parents=True, exist_ok=True)
    stored = stored_rows()
    sel = [SELECT[i] for i in a.only] if a.only else SELECT
    for (camp, arm, loc, seed) in sel:
        tag = f"{camp}__{arm}__{loc}__{seed}"
        dst = outdir / "runs" / f"{tag}.json"
        if dst.exists():
            print("skip (done)", tag, flush=True)
            continue
        spec = find_spec(camp, arm, loc, seed)
        t0 = time.time()
        cap = capture.run_spec(spec)
        repo = with_W(cap["repo_row"])
        st = with_W(stored[(camp, arm, loc, seed)])
        # (1) fidelity of the re-run: every deterministic field of the stored row
        fid = {"compared": 0, "diff": []}
        for k, v in st.items():
            if k in TIMING or k.startswith("audit"):
                continue
            fid["compared"] += 1
            if not same(v, repo.get(k)):
                fid["diff"].append((k, v, repo.get(k)))
        # (2) reference metrics on three histories
        ref = {}
        for h in ("poll_call", "poll_world", "tracer"):
            iv, zero, endp = cap["_hist"][h]
            m = compute(cap["_legit"], iv, cap["_end_poll"] if h != "tracer" else endp, cap["t_end"],
                        all_produced_contents=cap["_produced"])
            m["zero"] = zero
            ref[h] = m
        # O1/O2 also on the oracle's own end set (sys.authoritative()) with the reference definitions
        m_end = compute(cap["_legit"], {}, cap["_end_oracle"], cap["t_end"], all_produced_contents=cap["_produced"])
        ref["oracle_endset"] = {k: m_end[k] for k in ("O1_content", "O1_pair", "O2_content", "O2_pair")}
        cmp_rows = []
        for rk, fk in MAP:
            cmp_rows.append({"metric": rk, "field": fk, "ref_poll": ref["poll_call"].get(rk),
                             "ref_poll_world": ref["poll_world"].get(rk), "ref_tracer": ref["tracer"].get(rk),
                             "repo_rerun": repo.get(fk), "stored": st.get(fk),
                             "match_ref_repo": same(ref["poll_call"].get(rk), repo.get(fk)),
                             "match_repo_stored": same(repo.get(fk), st.get(fk))})
        # (3) history agreement poller vs tracer, pair by pair
        ivp, ivt = cap["_hist"]["poll_call"][0], cap["_hist"]["tracer"][0]
        hist_diff = [str(p) for p in set(ivp) | set(ivt) if ivp.get(p) != ivt.get(p)]
        res = {"tag": tag, "spec": cap["spec"], "t_end": cap["t_end"], "run_s": cap["run_s"],
               "wall_s": time.time() - t0, "poller": cap["poller"], "gt_issues": cap["gt_issues"],
               "end_state": cap["end_state"], "fidelity": fid, "ref": ref, "compare": cmp_rows,
               "hist_pairs": {"poll": len(ivp), "tracer": len(ivt), "differ": len(hist_diff),
                              "examples": hist_diff[:5]},
               "repo_selected": {k: repo.get(k) for k in ("nonlegit_auth", "legit_missing", "legit_quarantined",
                                                           "legit_lost_unrecoverable", "dup_auth", "holds",
                                                           "held_end", "held_distinct_ever", "sh_provisional_end",
                                                           "taint_events", "tm_transitions",
                                                           "tm_end_state_matches_authoritative", "recovered_n")}}
        dst.write_text(json.dumps(res, indent=1, default=str))
        with gzip.open(outdir / "runs" / f"{tag}.pkl.gz", "wb") as fh:
            pickle.dump({"legit": cap["_legit"], "hist": cap["_hist"], "end_oracle": cap["_end_oracle"],
                         "end_poll": cap["_end_poll"], "t_end": cap["t_end"], "repo_row": cap["repo_row"]}, fh)
        bad = [c["metric"] + "/" + c["field"] for c in cmp_rows if not (c["match_ref_repo"] and c["match_repo_stored"])]
        print(f"{tag}: {res['wall_s']:.0f}s fidelity_diff={len(fid['diff'])} hist_differ={len(hist_diff)} "
              f"leaks={cap['poller']['leaks']} fullmis={len(cap['poller']['full_mismatch'])} "
              f"metric_mismatch={bad}", flush=True)


if __name__ == "__main__":
    main()
