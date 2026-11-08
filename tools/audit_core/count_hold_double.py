#!/usr/bin/env python3
"""Count B5 hold events that are counted twice (the arriving observation is held by _fork's loop and again by the
arrival branch of _history), and held-at-arrival observations missing from the HELD state events."""
import json, sys
REPO = sys.argv[1]
sys.path.insert(0, REPO + "/src")
import pbti.sim as sim
from pbti.b5 import B5FeedLevel
from pbti.verifier import QUARANTINE

class B5Count(B5FeedLevel):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.double = 0
        self.arrival_holds = 0
    def _finish(self, ev, wire, disp, why, t_prev=0, ann=(), ns="q"):
        if disp == QUARANTINE and why == "FEED_FORK_HOLD":
            self.arrival_holds += 1
            if self._pre_held:
                self.double += 1
        return super()._finish(ev, wire, disp, why, t_prev, ann, ns)
    def _history(self, ev, wire, obs, rel, cb_obs, wid, kid, wkid, t, params, ann, waive=frozenset()):
        key = (obs["did"], obs["ep"], obs["seq"])
        n0 = len(self.reg.state_events)
        self._pre_held = False
        orig_fork = self._fork
        def fork(feed, f, tt):
            r = orig_fork(feed, f, tt)
            if key in self.held:
                self._pre_held = True
            return r
        self._fork = fork
        try:
            return super()._history(ev, wire, obs, rel, cb_obs, wid, kid, wkid, t, params, ann, waive)
        finally:
            del self._fork

sim.B5FeedLevel = B5Count
from pbti.scenarios import build
w = build(sys.argv[2], "B5", int(sys.argv[3]), temporal=False)
w.run()
v = w.sys
held_ev = {e[1] for e in v.reg.state_events if e[3] == "HELD"}
print(json.dumps({"scenario": sys.argv[2], "seed": int(sys.argv[3]), "holds": v.holds, "double_counted": v.double,
                  "arrival_holds": v.arrival_holds, "held_distinct_ever(state events)": len(held_ev),
                  "distinct ever held (true)": len(held_ev | {tuple(c['eid']) for c in v.qcases.values() if c['reason']=='FEED_FORK_HOLD'})}))
