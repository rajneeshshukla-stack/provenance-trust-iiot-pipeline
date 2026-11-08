#!/usr/bin/env python3
"""Freeze research/V4/PREREGISTRATION_V4.md: write the SHA-256 of the document and of the source and configuration
files the confirmatory campaigns depend on, with the UTC freezing time (self-recorded; not an external registry)."""
import datetime as dt
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEPS = (["research/V4/PREREGISTRATION_V4.md", "experiments/run_v4.py"]
        + sorted(str(p.relative_to(ROOT)) for p in (ROOT / "experiments" / "v4_configs").glob("*.json"))
        + sorted(str(p.relative_to(ROOT)) for p in (ROOT / "src" / "pbti").glob("*.py")))


def main():
    out = ROOT / "research" / "V4" / ("PREREGISTRATION_V4.sha256" if len(sys.argv) < 2 else sys.argv[1])
    lines = [f"# frozen_utc {dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}"]
    for rel in DEPS:
        lines.append(f"{hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()}  {rel}")
    out.write_text("\n".join(lines) + "\n")
    print(out.read_text())


if __name__ == "__main__":
    main()
