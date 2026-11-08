#!/usr/bin/env python3
"""List the slots newly held by B5 _fork calls whose triggering receipt added no new fork evidence."""
import json, sys
REPO = sys.argv[1]
sys.path.insert(0, REPO + "/src"); sys.path.insert(0, "/home/claude/PBTI_v7/tools/audit_core")
import pbti.sim as sim
import b5_variants as bv

class B5Inspect(bv.B5Instr):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.log = []
    def _fork(self, feed, f, t):
        new = self._is_new_evidence()
        did, ep = feed
        before = {}
        for sq in self.feed_seqs.get(feed, ()):
            k = (did, ep, sq)
            s = self.reg.slots.get(k)
            if sq >= f and s is not None and s.versions and k not in self.held:
                wd = next(iter(s.versions.values()))
                before[sq] = (s.state(), self.is_authoritative(k, s), (self.qcases.get(wd) or {}).get("state"))
        fk_before = dict(self.fork.get(feed) or {})
        r = super()._fork(feed, f, t)
        if not new and before:
            self.log.append({"t": t, "feed": feed, "f": f, "fork_before": fk_before, "newly_held": before,
                             "receipt": getattr(self, "_pending_ev", None) and self._pending_ev[0]})
        return r

sim.B5FeedLevel = B5Inspect
from pbti.sweep import build_sweep
from pbti.scenarios import build
where, seed = sys.argv[2], int(sys.argv[3])
cfg = json.loads(sys.argv[4]) if len(sys.argv) > 4 else {}
w = build_sweep(json.loads(where), "B5", seed, **cfg) if where.startswith("{") else build(where, "B5", seed, **cfg)
w.run()
for e in w.sys.log[:12]:
    print(e)
print("calls with newly held slots:", len(w.sys.log), "slots:", sum(len(e["newly_held"]) for e in w.sys.log))
