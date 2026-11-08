#!/usr/bin/env python3
"""V9 differential check of the corrected B5 (src/pbti/b5_corrected.py) against the reference model of
tools/b5_refmodel with the corrected choices (fork_rule="evidence", wire_cases=False) and the kept implementation
choices (order="identity", contested_cases=False, resume_timing="decision", event_scope="impl").

For every stream and review setting it runs the historical B5, the corrected B5 and the model on the same event
order and records whether the corrected B5 equals the model (final authoritative set and every authority interval,
"all_core"; also W, NLX, held identities, releases, rejections, resumes and the hold/fork/resume counters) and
whether it differs from the historical B5.

usage: python3 tools/v9/b5c_refmodel_diff.py --family rand_small --seeds 0:100 --out results/v9/b5c_refmodel/x.jsonl
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
import time
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["B5_REPO"] = ROOT          # the V7 harness imports pbti from $B5_REPO/src (default: a V7 scratch path)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "tools", "b5_refmodel"))
import harness as H  # noqa: E402
import refmodel as M  # noqa: E402
from gen import FAMILIES  # noqa: E402
from run_diff import SETTINGS  # noqa: E402
from pbti.b5 import B5FeedLevel  # noqa: E402
from pbti.b5_corrected import B5Corrected  # noqa: E402

assert all(os.path.realpath(m.__file__).startswith(os.path.realpath(ROOT)) for m in (H, M, B5FeedLevel and sys.modules["pbti.b5"], sys.modules["pbti.sim"], sys.modules["pbti.verifier"])), "modules loaded from outside the repository"

CORRECTED_CHOICES = dict(order="identity", fork_rule="evidence", contested_cases=False, resume_timing="decision",
                         wire_cases=False, event_scope="impl")


def corrected_for(mode):
    class B5CorrectedBound(B5Corrected):
        def __init__(self, *a, **kw):
            kw.setdefault("review_mode", mode)
            super().__init__(*a, **kw)
    return B5CorrectedBound


@contextlib.contextmanager
def _impl(cls):
    old = H.B5FeedLevel
    H.B5FeedLevel = cls
    try:
        yield
    finally:
        H.B5FeedLevel = old


def summary_of(res):
    return {"W": res["W_ms_total"], "NLX": res["nlx_ms_total"], "missing": len(res["legit_missing"]),
            "nonlegit": len(res["nonlegit_auth"]), "n_auth": len(res["authoritative"]),
            "resumes": len(res["resumes"]), "held_ids": len(res["held_identities"])}


def run_one(spec, settings):
    b = H.build(spec)
    rows = []
    for name in settings:
        P = SETTINGS[name]
        events = M.schedule(b.model_stmts, P, b.t_end)
        with _impl(B5FeedLevel):
            old = H.run_real(b, P, events)
        t0 = time.perf_counter()
        with _impl(corrected_for(P.mode)):
            new = H.run_real(b, P, events)
        t_new = time.perf_counter() - t0
        model = H.run_model(b, M.replace(P, **CORRECTED_CHOICES), events)
        c = H.compare(model, new)
        c_hist = H.compare(model, old)
        same_as_hist = (old["intervals"] == new["intervals"] and set(old["authoritative"]) == set(new["authoritative"]))
        rows.append({"family": spec["family"], "seed": spec["seed"], "setting": name,
                     "n_stmts": len(spec["stmts"]), "n_arrivals": len(spec["arrivals"]), "kinds": spec["kinds"],
                     "corrected": summary_of(new), "model": summary_of(model), "historical": summary_of(old),
                     "cmp": c, "cmp_model_vs_historical_all_core": c_hist["all_core"],
                     "counters_corrected": new["counters"], "counters_model": model["impl_counters"],
                     "counters_historical": old["counters"],
                     "counters_match": H.counters_match(model, new),
                     "corrected_equals_historical": same_as_hist,
                     "review_outcomes_corrected": new["review_outcomes"],
                     "review_outcomes_historical": old["review_outcomes"],
                     "t_corrected_s": round(t_new, 3)})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", required=True, choices=sorted(FAMILIES))
    ap.add_argument("--seeds", required=True, help="lo:hi")
    ap.add_argument("--settings", default="all")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    lo, hi = map(int, a.seeds.split(":"))
    settings = list(SETTINGS) if a.settings == "all" else a.settings.split(",")
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    n = bad = 0
    t0 = time.time()
    with open(a.out, "a") as fh:
        for seed in range(lo, hi):
            try:
                rows = run_one(FAMILIES[a.family](seed), settings)
            except Exception as e:  # noqa: BLE001
                rows = [{"family": a.family, "seed": seed, "error": repr(e), "trace": traceback.format_exc()}]
            for r in rows:
                fh.write(json.dumps(r, default=str) + "\n")
                n += 1
                bad += int("error" in r or not r["cmp"]["all_core"])
    print(f"{a.family} {lo}:{hi}: {n} rows, {bad} not equal to the model, {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
