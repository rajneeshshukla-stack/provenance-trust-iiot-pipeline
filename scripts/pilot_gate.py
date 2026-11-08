#!/usr/bin/env python3
"""Gate before freezing the preregistration: pilot rows have no errors, audited rows pass, the temporal tracer's end
state matches the pipeline in every row, and the A0 pilot comparison found no difference. Exit status 1 otherwise."""
import json
import sys
from pathlib import Path

bad = []
for f in sys.argv[1:]:
    p = Path(f)
    if p.name.endswith("comparison.json"):
        d = json.loads(p.read_text())
        if d["differences"] or d["missing_historical"] or d["errors_new"] or d["compared"] == 0:
            bad.append(f"{p.name}: {len(d['differences'])} differences, {len(d['missing_historical'])} missing")
        continue
    rows = [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
    if not rows:
        bad.append(f"{p.name}: no rows")
    for r in rows:
        tag = f"{p.name}:{r.get('arm')}:{r.get('scenario') or r.get('point')}:{r.get('seed')}"
        if "error" in r:
            bad.append(tag + " error " + r["error"][:200])
        elif r.get("audit_pass") is False:
            bad.append(tag + " audit failed")
        elif r.get("tm_end_state_matches_authoritative") is not True:
            bad.append(tag + " tracer end state mismatch")
    print(f"{p.name}: {len(rows)} rows checked")
print("GATE", "FAILED" if bad else "PASSED")
for b in bad[:50]:
    print(" ", b)
sys.exit(1 if bad else 0)
