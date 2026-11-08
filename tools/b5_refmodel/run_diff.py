"""Differential test driver: generate streams, run the real B5 and the reference model (phase-1 interpretation
and implementation-choice switches), compare, write JSONL rows and a summary.

usage: python3 run_diff.py --family rand_small --seeds 0:100 --settings all --out results.jsonl
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness as H  # noqa: E402
import refmodel as M  # noqa: E402
from gen import FAMILIES  # noqa: E402

SETTINGS = {
    "hist": M.Params.hist(),
    "B5S": M.Params.strict(),
    "d0c1": M.Params.defer(0, 1), "d1c1": M.Params.defer(1, 1), "d5c1": M.Params.defer(5, 1),
    "d60c1": M.Params.defer(60, 1), "d0c10": M.Params.defer(0, 10), "d1c10": M.Params.defer(1, 10),
    "d5c10": M.Params.defer(5, 10), "d60c10": M.Params.defer(60, 10),
    "event": M.Params.event(),
    "oneshot_d0c10": M.Params("oneshot", 0, 10_000, "periodic", True),
}
SWITCHES = ("order", "fork_rule", "contested_cases", "resume_timing", "wire_cases", "event_scope")
IMPL_VALUES = dict(order="identity", fork_rule="state", contested_cases=False, resume_timing="decision",
                   wire_cases=True, event_scope="impl")


def summary_of(res):
    return {"W": res["W_ms_total"], "NLX": res["nlx_ms_total"], "missing": len(res["legit_missing"]),
            "nonlegit": len(res["nonlegit_auth"]), "n_auth": len(res["authoritative"]),
            "resumes": len(res["resumes"]), "held_ids": len(res["held_identities"])}


def attribute(b, P, real, events):
    """For a stream where the phase-1 model and the implementation differ: which single switches (set to the
    implementation's value on top of the phase-1 model) remove the difference, and which are needed in the
    full implementation-choice model (leave-one-out)."""
    out = {"single_fixes": [], "needed": []}
    for sw in SWITCHES:
        m = H.run_model(b, M.replace(P, **{sw: IMPL_VALUES[sw]}), events)
        if H.compare(m, real)["all_core"]:
            out["single_fixes"].append(sw)
    for sw in SWITCHES:
        vals = dict(IMPL_VALUES)
        vals.pop(sw)
        m = H.run_model(b, M.replace(P, **vals), events)
        if not H.compare(m, real)["all_core"]:
            out["needed"].append(sw)
    return out


def run_one(spec, settings):
    b = H.build(spec)
    rows = []
    for name in settings:
        P = SETTINGS[name]
        t0 = time.perf_counter()
        events = M.schedule(b.model_stmts, P, b.t_end)
        real = H.run_real(b, P, events)
        t_real = time.perf_counter() - t0
        spec_m = H.run_model(b, P, events)
        impl_m = H.run_model(b, P.impl_choices(), events)
        c_spec = H.compare(spec_m, real)
        c_impl = H.compare(impl_m, real)
        row = {"family": spec["family"], "seed": spec["seed"], "setting": name,
               "n_stmts": len(spec["stmts"]), "n_arrivals": len(spec["arrivals"]), "kinds": spec["kinds"],
               "real": summary_of(real), "spec_model": summary_of(spec_m), "impl_model": summary_of(impl_m),
               "cmp_spec": c_spec, "cmp_impl": c_impl,
               "counters_real": real["counters"], "counters_impl_model": impl_m["impl_counters"],
               "counters_match_impl": H.counters_match(impl_m, real),
               "review_outcomes": real["review_outcomes"], "t_real_s": round(t_real, 3)}
        if not c_spec["all_core"]:
            row["attribution"] = attribute(b, P, real, events)
        rows.append(row)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", required=True)
    ap.add_argument("--seeds", default="0:10")
    ap.add_argument("--settings", default="all")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    lo, hi = map(int, a.seeds.split(":"))
    settings = list(SETTINGS) if a.settings == "all" else a.settings.split(",")
    gen = FAMILIES[a.family]
    n = 0
    t0 = time.time()
    with open(a.out, "a") as fh:
        for seed in range(lo, hi):
            try:
                rows = run_one(gen(seed), settings)
            except Exception:  # noqa: BLE001
                rows = [{"family": a.family, "seed": seed, "error": traceback.format_exc()}]
            for r in rows:
                fh.write(json.dumps(r, default=str) + "\n")
            n += 1
    print(f"{a.family} seeds {lo}:{hi} settings {len(settings)}: {n} streams in {time.time() - t0:.1f} s")


if __name__ == "__main__":
    main()
