#!/usr/bin/env python3
"""Verify a local SKAB clone against the provenance record of the replay campaign
(results/raw/v3_replay_skab_dataset.json: commit and per-file SHA-256).  The dataset is not redistributed.
Acquire it with:  git clone https://github.com/waico/SKAB && git -C SKAB checkout b2c0d46c2971dcbfe71e26087b6d231998bb91c2
usage: python3 -I tools/v9/check_skab.py SKAB_DIR        (exit code 0 if every file matches)"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
skab = Path(sys.argv[1]).resolve()
rec = json.loads((ROOT / "results/raw/v3_replay_skab_dataset.json").read_text())
try:
    head = subprocess.run(["git", "-C", str(skab), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
except Exception:  # noqa: BLE001
    head = None
bad = []
for f in rec["files"]:
    p = skab / "data" / f["file"]
    if not p.exists():
        bad.append((f["file"], "missing"))
    elif hashlib.sha256(p.read_bytes()).hexdigest() != f["sha256"]:
        bad.append((f["file"], "sha256 differs"))
out = {"recorded_commit": rec["commit"], "local_commit": head, "files": len(rec["files"]), "mismatches": bad,
       "license": rec.get("license"), "url": rec.get("url")}
print(json.dumps(out, indent=1))
sys.exit(1 if bad else 0)
