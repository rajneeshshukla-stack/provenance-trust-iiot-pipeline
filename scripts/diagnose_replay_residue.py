#!/usr/bin/env python3
"""V3 diagnostic: which attack classes make up the non-legitimate observations that remain authoritative at the end
of a stressed SKAB replay run, and why legitimate losses grow with the replay speed-up.

Re-runs selected replay specifications exactly as experiments/run_campaign.py does (same builder, seeds and speeds;
the replay counterpart of scripts/attribute_nonlegit.py), records the attack label of every received non-legitimate wire message by its content key, and attributes each
authoritative non-legitimate content key at the end of the run to the label(s) that delivered it. The run's
nonlegit_auth and legit_missing are recomputed with the oracle and compared with the stored campaign row, so the
diagnostic is checked against the raw data it explains.

Usage: python3 scripts/diagnose_replay_residue.py --skab-dir DIR [--systems PBTI B5 B4] [--speeds 1 10] [--seeds 1 2 3]
Writes results/summary/v3_replay_residue.json.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pbti.dataset import build_replay, load_skab  # noqa: E402
from pbti.envelope import content_key  # noqa: E402
from pbti.oracle import evaluate  # noqa: E402


def _find_obs(d):
    """Return the dict that carries the observation fields, wherever the wire format nests it (as in
    scripts/attribute_nonlegit.py)."""
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


def _ck_of(wire: bytes):
    """Content key of the observation carried by a wire message (None if unparsable)."""
    try:
        o = _find_obs(json.loads(wire))
        if o is not None:
            return content_key(o["did"], o["aid"], o["ts"], o.get("sch", "telemetry.v1"), o["pl"])
    except Exception:  # noqa: BLE001  (malformed wires are part of some attacks)
        pass
    return None


def one(data, system, seed, speed):
    w = build_replay(data, system, seed, speed, True)
    labels_by_ck: dict = defaultdict(Counter)
    orig = w.receive

    def receive(wire, meta, label):
        if label not in ("legit", "legit-dup"):
            ck = _ck_of(wire)
            if ck is not None:
                labels_by_ck[ck][label] += 1
        return orig(wire, meta, label)

    w.receive = receive
    w.run()
    r = evaluate(w)
    legit = {tr["ck"] for tr in w.truth}
    auth = Counter(ck for _, ck in w.sys.authoritative())
    by_label = Counter()
    by_cell = Counter()   # device id pa-c<g>-d<j>: cell g is the cell of gateway g
    for ck, c in auth.items():
        if ck in legit:
            continue
        labs = labels_by_ck.get(ck)
        key = "+".join(sorted(labs)) if labs else "unattributed"
        by_label[key] += c
        by_cell[f"{key}@{ck[0].rsplit('-', 1)[0]}"] += c
    legit_rx = {k: v for k, v in w.receipts_by_label.get("legit", {}).items()}
    return {"system": system, "seed": seed, "speed": speed, "nonlegit_auth": r["nonlegit_auth"],
            "legit_missing": r["legit_missing"], "residue_by_label": dict(by_label), "residue_by_label_and_cell": dict(by_cell),
            "legit_rx_not_committed": {k: v for k, v in legit_rx.items() if k != "ACCEPT/COMMITTED"}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skab-dir", required=True)
    ap.add_argument("--systems", nargs="+", default=["PBTI", "B5", "B4"])
    ap.add_argument("--speeds", nargs="+", type=float, default=[1, 10])
    ap.add_argument("--seeds", nargs="+", type=int, default=[1, 2, 3])
    ap.add_argument("--out", default=str(ROOT / "results" / "summary" / "v3_replay_residue.json"))
    a = ap.parse_args()
    data = load_skab(a.skab_dir)
    stored = {}
    raw = ROOT / "results" / "raw" / "v3_replay_skab.jsonl"
    for line in raw.read_text().splitlines():
        s = json.loads(line)
        if s.get("stress"):
            stored[(s["system"], s["seed"], float(s["speed"]))] = s
    out = []
    for system in a.systems:
        for speed in a.speeds:
            for seed in a.seeds:
                res = one(data, system, seed, speed)
                ref = stored.get((system, seed, float(speed)))
                res["matches_campaign_row"] = bool(ref) and all(res[k] == ref[k] for k in ("nonlegit_auth", "legit_missing"))
                out.append(res)
                print(json.dumps(res, sort_keys=True), flush=True)
    agg = defaultdict(Counter)
    agg_cell = defaultdict(Counter)
    for res in out:
        for k, v in res["residue_by_label"].items():
            agg[(res["system"], res["speed"])][k] += v
        for k, v in res["residue_by_label_and_cell"].items():
            agg_cell[(res["system"], res["speed"])][k] += v
    summary = {"runs": out, "all_match_campaign": all(r["matches_campaign_row"] for r in out),
               "residue_by_label_total": {f"{s}@{sp:g}x": dict(c) for (s, sp), c in agg.items()},
               "residue_by_label_and_cell_total": {f"{s}@{sp:g}x": dict(c) for (s, sp), c in agg_cell.items()},
               "seeds": a.seeds, "speeds": a.speeds, "systems": a.systems,
               "note": "Labels are the injector labels of src/pbti/scenarios.py and src/pbti/dataset.py; a content key "
                       "delivered under several labels is reported with the labels joined by '+'."}
    Path(a.out).write_text(json.dumps(summary, indent=1, sort_keys=True))
    print("all_match_campaign", summary["all_match_campaign"])


if __name__ == "__main__":
    main()
