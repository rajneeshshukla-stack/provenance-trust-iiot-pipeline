#!/usr/bin/env python3
"""Attribute non-legitimate authoritative observations to the injection that produced them.

The campaign records only aggregate counts (oracle.nonlegit_auth). This script re-runs selected scenarios (virtual time,
deterministic per seed and source digest) with a receive-side tap that remembers under which delivery label each content
key arrived, and reports, per scenario and pipeline, how many non-legitimate authoritative observations stem from each
attack label. It substantiates statements such as "the only non-legitimate observations PBTI retained in E5 came from
impersonation with both keys".

Usage: python3 scripts/attribute_nonlegit.py --scenarios S05_stolen_key S15_gateway_forgery --systems PBTI B3 --seeds 1 20
Output: results/summary/nonlegit_attribution.json
"""
import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from pbti.envelope import content_key  # noqa: E402
from pbti.scenarios import SCENARIOS, build  # noqa: E402


def _find_obs(d):
    """Return the dict that carries the observation fields, wherever the wire format nests it."""
    if isinstance(d, dict):
        if {"did", "aid", "ts", "pl"} <= set(d):
            return d
        for v in d.values():
            r = _find_obs(v)
            if r is not None:
                return r
    elif isinstance(d, list):
        for v in d:
            r = _find_obs(v)
            if r is not None:
                return r
    return None


def run_one(scenario, system, seed):
    w = build(scenario, system, seed)
    labels = defaultdict(Counter)
    orig = w.receive

    def tap(wire, meta, label):
        try:
            o = _find_obs(json.loads(wire))
            if o is not None:
                labels[content_key(o["did"], o["aid"], o["ts"], o.get("sch", "telemetry.v1"), o["pl"])][label] += 1
        except Exception:  # noqa: BLE001  (malformed wires are part of some attacks)
            pass
        return orig(wire, meta, label)

    w.receive = tap
    w.run()
    legit = {tr["ck"] for tr in w.truth}
    out = Counter()
    for _, ck in w.sys.authoritative():
        if ck in legit:
            continue
        ls = labels.get(ck)
        out["+".join(sorted(ls)) if ls else "unknown"] += 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenarios", nargs="+", default=["S05_stolen_key", "S15_gateway_forgery"])
    ap.add_argument("--systems", nargs="+", default=["PBTI"])
    ap.add_argument("--seeds", nargs=2, type=int, default=[1, 20])
    ap.add_argument("--out", default=str(ROOT / "results" / "summary" / "nonlegit_attribution.json"))
    a = ap.parse_args()
    res = {}
    for sc in a.scenarios:
        if sc not in SCENARIOS:
            raise SystemExit(f"unknown scenario {sc}; known: {', '.join(SCENARIOS)}")
        for s in a.systems:
            tot = Counter()
            for seed in range(a.seeds[0], a.seeds[1] + 1):
                tot.update(run_one(sc, s, seed))
            n = a.seeds[1] - a.seeds[0] + 1
            res[f"{sc}|{s}"] = {"seeds": n, "per_run_mean_by_label": {k: v / n for k, v in sorted(tot.items())}}
            print(sc, s, {k: round(v / n, 2) for k, v in sorted(tot.items())}, flush=True)
    Path(a.out).write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
