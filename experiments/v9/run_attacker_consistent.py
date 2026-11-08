#!/usr/bin/env python3
"""V9 robustness campaign E04 (exploratory, not preregistered): the mixed workload (S99) of the review-timing
comparison A1 with the consistent impersonation attacker (experiments/v9/consistent_impersonator.py) instead of the
registered one, for PBTI, PBTI-R (one-shot 60 s / 10 s and event-driven), the historical B5 and the corrected B5
(same two review settings), on all 20 A1 seeds (21-40), so that every comparison is paired by seed and attacker.

Registered-attacker rows are not re-run here: they are the frozen A1 rows (PBTI, PBTI-R, historical B5) and the
corrected-B5 A1 rerun (results/v9/raw/A1_review_B5c.jsonl).  For seeds 21 and 22 the registered attacker is also
re-run for PBTI, PBTI-R-hist and both B5 implementations as a check that this runner reproduces those rows.

usage: python3 experiments/v9/run_attacker_consistent.py --out results/v9/raw/attacker_consistent_impersonator.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v9_common as C  # noqa: E402

import run_v4  # noqa: E402
from consistent_impersonator import ConsistentImpersonation  # noqa: E402
from pbti import scenarios as S  # noqa: E402
from pbti import sim  # noqa: E402
from pbti.b5 import B5FeedLevel as B5Historical  # noqa: E402
from pbti.oracle import evaluate  # noqa: E402
from pbti.temporal import temporal_metrics  # noqa: E402

REGISTERED = S.ImpersonationHook
CONF = C.ROOT / "experiments/v4_configs/A1_review.json"
# (label, A1 arm whose configuration is used, B5 implementation)
ARMS = [("PBTI", "PBTI", None), ("PBTI-R-hist", "PBTI-R-hist", None), ("PBTI-R-event", "PBTI-R-event", None),
        ("B5-hist", "B5-hist", "historical"), ("B5-event", "B5-event", "historical"),
        ("B5c-hist", "B5-hist", "corrected"), ("B5c-event", "B5-event", "corrected")]
SEEDS = list(range(21, 41))
CHECK_SEEDS = (21, 22)
CHECK_ARMS = ("PBTI", "PBTI-R-hist", "B5-hist", "B5c-hist")


def _spec(arm, seed):
    for s in run_v4.expand(json.loads(CONF.read_text()), [seed]):
        if s["arm"] == arm and s.get("scenario") == "S99_mixed":
            return s
    raise KeyError((arm, seed))


def job(t):
    t0 = time.perf_counter()
    try:
        label, a1_arm, impl = t["label"], t["a1_arm"], t["impl"]
        S.ImpersonationHook = REGISTERED if t["variant"] == "registered" else ConsistentImpersonation
        B5C = C.install_corrected_b5()
        sim.B5FeedLevel = B5C if impl == "corrected" else B5Historical
        spec = _spec(a1_arm, t["seed"])
        kw = {k: v for k, v in spec["cfg"].items() if k in run_v4.CFG_KEYS}
        w = S.build("S99_mixed", spec["system"], t["seed"], **kw)
        w.run()
        r = evaluate(w)
        r.update(temporal_metrics(w))
        r.update(C.w_split(w))
        if hasattr(w.sys, "v9_counters"):
            r.update(w.sys.v9_counters())
        r.update({"label": label, "arm": a1_arm, "b5_impl": impl, "variant": t["variant"], "seed": t["seed"],
                  "scenario": "S99_mixed", "campaign": "E04_consistent_impersonator", "cfg": spec["cfg"],
                  "impersonation_receipts": dict(w.receipts_by_label.get("impersonation", {})),
                  "review_decisions": getattr(w.reviewer, "decisions", None)})
        r["wall_s"] = time.perf_counter() - t0
        return r
    except Exception as e:  # noqa: BLE001
        return {"error": repr(e), "trace": traceback.format_exc(), **t}
    finally:
        S.ImpersonationHook = REGISTERED


def key_of(r):
    return (r["label"], r["variant"], r["seed"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=2)
    a = ap.parse_args()
    todo = [{"label": l, "a1_arm": arm, "impl": impl, "variant": "consistent", "seed": s}
            for s in SEEDS for (l, arm, impl) in ARMS]
    todo += [{"label": l, "a1_arm": arm, "impl": impl, "variant": "registered", "seed": s}
             for s in CHECK_SEEDS for (l, arm, impl) in ARMS if l in CHECK_ARMS]
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    man = C.manifest("v9_E04_consistent_impersonator", vars(a),
                     {"workload": "S99_mixed of experiments/v4_configs/A1_review.json", "seeds": SEEDS,
                      "arms": ARMS, "attacker_module": "experiments/v9/consistent_impersonator.py",
                      "attacker_sha256": C.sha256_file(C.ROOT / "experiments/v9/consistent_impersonator.py"),
                      "n_specs": len(todo), "evidence_level": "exploratory (not preregistered)"})
    mpath = out.with_suffix(".manifest.json")
    if mpath.exists():
        old = json.loads(mpath.read_text())
        old.setdefault("resumed", []).append(man["started"])
        man = old
    mpath.write_text(json.dumps(man, indent=1, default=str))
    errors = C.run_pool(todo, job, out, key_of, a.workers, "E04")
    print("written", out, "errors", errors)


if __name__ == "__main__":
    main()
