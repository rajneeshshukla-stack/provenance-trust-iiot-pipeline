#!/usr/bin/env python3
"""Log fork and resume times of B5 feeds, and the held-at-arrival share, for one run."""
import json, sys
REPO = sys.argv[1]
sys.path.insert(0, REPO + "/src")
import pbti.sim as sim
from pbti.b5 import B5FeedLevel

class B5Log(B5FeedLevel):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.ev = []
    def _fork(self, feed, f, t):
        new = feed not in self.fork
        r = super()._fork(feed, f, t)
        if new:
            self.ev.append(("fork", feed, f, t))
        return r
    def _maybe_resume(self, feed, t):
        was = feed in self.fork
        r = super()._maybe_resume(feed, t)
        if was and feed not in self.fork:
            self.ev.append(("resume", feed, None, t))
        return r

sim.B5FeedLevel = B5Log
from pbti.scenarios import build
sc, seed = sys.argv[2], int(sys.argv[3]); cfg = json.loads(sys.argv[4]) if len(sys.argv) > 4 else {}
w = build(sc, "B5", seed, temporal=False, **cfg)
w.run()
evs = w.sys.ev
print(json.dumps({"scenario": sc, "seed": seed, "cfg": cfg, "n_fork": sum(e[0] == "fork" for e in evs),
                  "n_resume": sum(e[0] == "resume" for e in evs), "first_events": evs[:8],
                  "resume_times_s": sorted(e[3] / 1000 for e in evs if e[0] == "resume")[:10]}, default=str))
