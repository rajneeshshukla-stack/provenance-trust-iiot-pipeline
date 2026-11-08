"""V3 regression guard: existing pipelines must reproduce the stored revision-2 outcomes exactly.

Written before any V3 change to src/. Each case re-runs one stored specification (scenario, system, seed) and
compares every outcome field of the stored raw row (timing fields excluded) with the new run.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pbti.oracle import evaluate  # noqa: E402
from pbti.scenarios import build  # noqa: E402

SKIP = ("_us", "_s", "wall", "ingest", "wrap", "devsign", "replay_s", "static_s")

CASES = [  # (raw file, scenario, system, seed)
    ("scenarios.jsonl", "S05_stolen_key", "PBTI", 3),
    ("scenarios.jsonl", "S08_seq_reuse_bug", "PBTI", 2),
    ("scenarios_part2.jsonl", "S12_beyond_horizon", "PBTI", 12),
    ("scenarios_part2.jsonl", "S14_revocation", "B3", 15),
    ("scenarios_part3_b4.jsonl", "S05_stolen_key", "B4", 7),
    ("scenarios_part3_b4.jsonl", "S14_revocation", "B4", 4),
    ("scenarios.jsonl", "S07_duplicates", "B2", 5),
]


def _stored(fname, scenario, system, seed):
    for line in open(ROOT / "results" / "raw" / fname):
        r = json.loads(line)
        if r.get("scenario") == scenario and r.get("system") == system and r.get("seed") == seed and "error" not in r:
            return r
    raise LookupError((fname, scenario, system, seed))


@pytest.mark.parametrize("fname,scenario,system,seed", CASES)
def test_stored_outcomes_reproduced(fname, scenario, system, seed):
    stored = _stored(fname, scenario, system, seed)
    w = build(scenario, system, seed)
    w.run()
    new = evaluate(w)
    diff = {k: (stored[k], new.get(k)) for k in stored
            if k in new and not any(t in k for t in SKIP) and not k.startswith("audit") and stored[k] != new[k]}
    assert not diff, diff
