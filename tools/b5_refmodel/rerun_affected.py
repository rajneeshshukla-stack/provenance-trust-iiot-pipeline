"""Recompute the rand_small rows of the seeds whose stream contains a statement the shared parser rejects
(seq 0 with a non-null prev, produced by the generator's sequence-reuse fault at seq 0).  These rows were first
computed before the harness filtered such statements out of the model input (harness.build); the original rows
are kept in rand_small.before_seq0_fix.jsonl."""
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen import rand_small  # noqa: E402
from run_diff import SETTINGS, run_one  # noqa: E402

D = "/home/claude/PBTI_v7/results/b5_refmodel/campaign"
src = os.path.join(D, "rand_small.jsonl")
bak = os.path.join(D, "superseded", "rand_small.before_seq0_fix.jsonl")
aff = set(json.loads(open("/home/claude/PBTI_v7/results/b5_refmodel/rand_small_seq0_affected_seeds.json").read()))
if not os.path.exists(bak):
    shutil.copy(src, bak)
rows = [json.loads(line) for line in open(bak)]
keep = [r for r in rows if r["seed"] not in aff]
new = []
for seed in sorted(aff):
    new += run_one(rand_small(seed), list(SETTINGS))
out = sorted(keep + new, key=lambda r: (r["seed"], list(SETTINGS).index(r["setting"]) if "setting" in r else 0))
with open(src, "w") as fh:
    for r in out:
        fh.write(json.dumps(r, default=str) + "\n")
print(f"replaced {len(rows) - len(keep)} rows of {len(aff)} seeds with {len(new)} recomputed rows")
