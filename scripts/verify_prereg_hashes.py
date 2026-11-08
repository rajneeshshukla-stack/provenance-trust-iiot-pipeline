#!/usr/bin/env python3
"""Verify the preregistration freeze files: every listed file must still have the recorded SHA-256."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
res = {}
for hf in ("research/V4/PREREGISTRATION_V4.sha256", "research/V4/PREREGISTRATION_V4_AMENDMENT_1.sha256"):
    lines = [l for l in (ROOT / hf).read_text().splitlines() if l and not l.startswith("#")]
    bad = [p for h, p in (l.split(None, 1) for l in lines) if hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != h]
    res[hf] = {"files": len(lines), "changed": bad}
print(json.dumps(res, indent=1))
sys.exit(1 if any(v["changed"] for v in res.values()) else 0)
