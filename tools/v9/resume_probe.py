#!/usr/bin/env python3
"""V9: fork and resume times of the corrected B5 with one-shot review (R = 60 s, C = 10 s) in E5 (stolen keys),
A1 seeds 21-23, as quoted in the article's description of B5's resume rule.
Output: results/v9/summary/resume_probe.json.  usage: python3 tools/v9/resume_probe.py"""
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "experiments" / "v9")); sys.path.insert(0, str(ROOT / "experiments")); sys.path.insert(0, str(ROOT / "src"))
import v9_common as C
import run_v4
from pbti.scenarios import build
B5C = C.install_corrected_b5()
conf = json.load(open(ROOT / 'experiments/v4_configs/A1_review.json'))
out = {}
for seed in (21, 22, 23):
    spec = [s for s in run_v4.expand(conf, [seed]) if s['arm'] == 'B5-hist' and s.get('scenario') == 'S05_stolen_key'][0]
    kw = {k: v for k, v in spec['cfg'].items() if k in run_v4.CFG_KEYS}
    w = build('S05_stolen_key', 'B5', seed, **kw)
    forks, resumes = {}, {}
    orig_fork = w.sys._fork
    def fk(feed, f, t, _o=orig_fork):
        forks.setdefault(feed, t); return _o(feed, f, t)
    w.sys._fork = fk
    orig_res = w.sys._maybe_resume
    def mr(feed, t, _o=orig_res):
        had = feed in w.sys.fork; _o(feed, t)
        if had and feed not in w.sys.fork: resumes.setdefault(feed, t)
    w.sys._maybe_resume = mr
    w.run()
    out[seed] = {"forks_s": sorted(v/1000 for v in forks.values()), "resumes_s": sorted(v/1000 for v in resumes.values()),
                 "production_end_s": w.cfg.duration_ms/1000, "run_end_s": (w.cfg.duration_ms + w.cfg.drain_ms)/1000}
(ROOT / 'results/v9/summary/resume_probe.json').write_text(json.dumps(out, indent=1))
print(json.dumps(out))
