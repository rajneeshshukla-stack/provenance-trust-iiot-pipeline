#!/usr/bin/env python3
"""Quantify, on real B5 runs, (1) the `holds` counter versus true hold episodes (an identity entering B5's held set),
(2) `held_distinct_ever` (run_v4.py: identities with a HELD state event) versus identities ever held, and (3) what the
oracle's `legit_quarantined` ("still held at the end", Table S14 "Quar.") contains at the end of the run."""
import json
import sys

REPO = "/home/claude/PBTI_v7/scratch/oracle_audit/repo"
sys.path.insert(0, REPO + "/src")
sys.path.insert(0, REPO + "/experiments")

import run_v4  # noqa: E402
from pbti.envelope import content_key  # noqa: E402
from pbti.oracle import evaluate  # noqa: E402
from pbti.scenarios import build  # noqa: E402

CONF = {"A0_core": REPO + "/experiments/v4_configs/A0_core.json",
        "A1_review": REPO + "/experiments/v4_configs/A1_review.json"}


class CountingSet(set):
    def __init__(self):
        super().__init__()
        self.episodes = 0
        self.ever = set()

    def add(self, k):
        if k not in self:
            self.episodes += 1
        self.ever.add(k)
        set.add(self, k)


def one(camp, arm, scen, seed, stored):
    conf = json.load(open(CONF[camp]))
    spec = next(s for s in run_v4.expand(conf, [seed]) if s["arm"] == arm and s["scenario"] == scen)
    kw = {k: v for k, v in spec["cfg"].items() if k in run_v4.CFG_KEYS}
    w = build(scen, spec["system"], seed, **kw)
    cs = CountingSet()
    w.sys.held = cs
    w.run()
    r = evaluate(w)
    v = w.sys
    # composition of legit_quarantined (same loop as src/pbti/oracle.py:100-118)
    reach = set(tr["ck"] for tr in w.truth if tr["o"].meta.get("gw_accepted"))
    auth = set(ck for _, ck in v.authoritative())
    comp = {}
    seen = set()
    for (ns, dg), blob in v.store.blobs.items():
        if ns != "q" or dg not in v.quarantined_wires:
            continue
        ob = json.loads(blob)["obs"]
        ck = content_key(ob["did"], ob["aid"], ob["ts"], ob["sch"], ob["pl"])
        if ck not in reach or ck in auth or ck in seen:
            continue
        seen.add(ck)
        key = (ob["did"], ob["ep"], ob["seq"])
        s = v.reg.slots.get(key)
        case = v.qcases.get(dg, {})
        if s is None or not s.versions:
            cls = "no-slot (quarantined before admission), case " + str(case.get("state"))
        elif s.state() == "CONTESTED":
            cls = "slot CONTESTED (absorbing: never releasable)"
        elif s.tainted:
            cls = "slot TAINTED"
        elif key in v.held:
            cls = "held, case " + str(case.get("state"))
        else:
            cls = "other"
        comp[cls] = comp.get(cls, 0) + 1
    hev = len({e[1] for e in v.reg.state_events if e[3] == "HELD"})
    out = {"run": f"{camp}/{arm}/{scen}/{seed}", "holds_counter": v.holds, "true_hold_episodes": cs.episodes,
           "distinct_identities_ever_held": len(cs.ever), "held_distinct_ever_(run_v4)": hev,
           "held_end": len(v.held), "legit_quarantined": r["legit_quarantined"], "legit_quarantined_composition": comp,
           "legit_missing": r["legit_missing"], "recovered_n": r.get("recovered_n"),
           "stored_holds": stored.get("holds"), "stored_legit_quarantined": stored.get("legit_quarantined"),
           "stored_held_distinct_ever": stored.get("held_distinct_ever")}
    return out


def main():
    stored = {}
    for camp in CONF:
        for line in open(f"{REPO}/results/v4/raw/{camp}.jsonl"):
            x = json.loads(line)
            stored[(camp, x["arm"], x["scenario"], x["seed"])] = x
    res = []
    for (camp, arm, scen, seed) in [("A0_core", "B5-hist", "S05_stolen_key", 1),
                                    ("A1_review", "B5-hist", "S99_mixed", 21)]:
        o = one(camp, arm, scen, seed, stored[(camp, arm, scen, seed)])
        print(json.dumps(o, indent=1))
        res.append(o)
    json.dump(res, open("/home/claude/PBTI_v7/results/oracle_audit/b5_counters.json", "w"), indent=1)


if __name__ == "__main__":
    main()
