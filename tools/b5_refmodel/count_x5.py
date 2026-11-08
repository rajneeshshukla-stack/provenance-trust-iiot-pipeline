"""Check the paper's S99 traces (the only campaign workload that combines feed holds with releasable quarantine
reasons) for the wire-keyed case collision (X5): count review outcomes by subtype and, at the end of each run, the
held, single-digest, untainted slots that have no FEED_FORK_HOLD case for their wire (permanently held without a
case).  World-only runs, no model.  usage: python3 count_x5.py OUT.jsonl SCEN ARM SEED [SEED ...]"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness  # noqa: F401,E402  (sys.path to the scratch repository)
from pbti.envelope import content_key  # noqa: E402
from pbti.registry import COMMITTED  # noqa: E402
from pbti.scenarios import build  # noqa: E402

ARMS = {"B5-hist": {}, "B5-d60c1": {"review_delay_ms": 60_000, "review_every_ms": 1000, "review_rule": "defer"},
        "B5-d60c10": {"review_delay_ms": 60_000, "review_every_ms": 10_000, "review_rule": "defer"},
        "B5-d0c1": {"review_delay_ms": 0, "review_every_ms": 1000, "review_rule": "defer"},
        "B5-event": {"review_mode": "event", "review_delay_ms": 0, "review_rule": "defer"}}


def main(out, scen, arm, *seeds):
    for seed in map(int, seeds):
        t0 = time.perf_counter()
        w = build(scen, "B5", seed, **ARMS[arm])
        w.run()
        v = w.sys
        legit_ck = {tr["ck"] for tr in w.truth}
        victims, legit_victims = [], 0
        for k in v.held:
            s = v.reg.slots.get(k)
            if s is None or s.state() != COMMITTED or s.tainted or not s.versions:
                continue
            wd = next(iter(s.versions.values()))
            c = v.qcases.get(wd)
            if c is None or c["reason"] != "FEED_FORK_HOLD":
                victims.append((list(k), c["reason"] if c else None, c["state"] if c else None))
                o = s.obs_first
                legit_victims += content_key(o["did"], o["aid"], o["ts"], o["sch"], o["pl"]) in legit_ck
        row = {"scenario": scen, "arm": arm, "seed": seed, "review_outcomes": dict(v.review_outcomes),
               "holds": v.holds, "fork_events": v.fork_events, "resumed_feeds": v.resumed_feeds,
               "held_without_hold_case": len(victims), "legit_held_without_hold_case": legit_victims,
               "victims": victims[:20], "wall_s": round(time.perf_counter() - t0, 1)}
        with open(out, "a") as fh:
            fh.write(json.dumps(row) + "\n")
        print(scen, arm, seed, row["held_without_hold_case"], row["legit_held_without_hold_case"],
              {k: x for k, x in row["review_outcomes"].items() if k.startswith("RELEASE_FAILED")}, row["wall_s"])


if __name__ == "__main__":
    main(*sys.argv[1:])
