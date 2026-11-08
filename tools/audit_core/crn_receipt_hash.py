#!/usr/bin/env python3
"""Hash the exact sequence of receipts (virtual time, SHA-256 of wire bytes, label) that the World delivers to the
pipeline; identical hashes across arms mean identical workload, network and attack schedules (common random numbers)."""
import hashlib, json, sys
REPO = sys.argv[1]
sys.path.insert(0, REPO + "/src")
from pbti.scenarios import build
from pbti.sweep import build_sweep
where, seed = sys.argv[2], int(sys.argv[3])
arms = json.loads(sys.argv[4])
out = {}
for name, (system, cfg) in arms.items():
    w = build_sweep(json.loads(where), system, seed, temporal=False, **cfg) if where.startswith("{") else \
        build(where, system, seed, temporal=False, **cfg)
    h = hashlib.sha256(); n = [0]
    orig = w.receive
    def rec(wire, meta, label, orig=orig):
        h.update(f"{w.now}|{hashlib.sha256(wire).hexdigest()}|{label}|{meta.get('tid')}\n".encode()); n[0] += 1
        return orig(wire, meta, label)
    w.receive = rec
    w.run()
    out[name] = (n[0], h.hexdigest()[:16])
    print(name, out[name], flush=True)
print("IDENTICAL" if len({v for v in out.values()}) == 1 else "DIFFERENT", json.dumps(out))
