#!/usr/bin/env python3
"""Build the corrected-comparator analysis tree and compare corrected with historical rows.

A copy of the repository is made in OUT (sources, configurations, analysis scripts and all raw results).  In the
copy, and only there, each raw result file that the frozen analysis scripts read has its B5 and B5S rows replaced by
the corrected-B5 rerun rows of the same specification (results/v9/raw/*); every other row (PBTI, PBTI-R, PBTI-SH, B4,
...) is kept byte-identical.  The frozen analysis scripts can then be run unchanged in the copy.  The historical
tree is never modified.

Row-level comparison (written to results/v9/summary/b5c_row_comparison.json of the ORIGINAL tree):
  * for every replaced row, the outcome fields that differ (timing fields such as wall_s, ingest_us_* excluded);
  * invariance check: a historical row without fork evidence (fork_events == 0 and holds == 0) must be reproduced
    exactly by the corrected implementation in every outcome field (the corrected code paths require fork evidence).

usage: python3 tools/v9/build_corrected_tree.py OUT_DIR
"""
from __future__ import annotations

import json
import shutil
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V9RAW = ROOT / "results" / "v9" / "raw"
TIMING = ("_us", "wall", "ingest", "wrap", "devsign", "audit_static_s", "audit_replay_s", "_ns")
V9_ONLY = ("b5_impl", "b5_corrected_sha256", "b5_historical_sha256", "source_sha256", "held_distinct_ever_v9",
           "recovered_distinct", "fork_evidence_receipts", "forked_feeds_distinct", "deferred_releases",
           "hold_case_conversions", "hold_case_replacements", "held_without_case_end", "wd_", "W_delay", "W_loss")
COUNTERS = ("holds", "fork_events", "held_distinct_ever", "recovered_n", "review[", "slots_HELD", "held_end",
            "resumed_feeds", "rx[", "legit_rx_", "review_decisions", "review_deferrals", "event_review_rounds",
            "tm_transitions", "derived_versions", "derived_corrections", "store_bytes", "audit_findings")

# original raw file -> (key fields, {system: corrected file})
PLAN = {
    "results/raw/v3_scenarios_b5.jsonl": (("scenario", "seed"), {"B5": "v3_scenarios_B5c.jsonl",
                                                                 "B5S": "v3_scenarios_B5Sc.jsonl"}),
    "results/raw/v3_mixed_b5.jsonl": (("scenario", "seed"), {"B5": "v3_mixed_B5c.jsonl", "B5S": "v3_mixed_B5Sc.jsonl"}),
    "results/raw/v3_sweep.jsonl": (("factor", "level", "seed"), {"B5": "v3_sweep_B5c.jsonl"}),
    "results/raw/v3_factorial.jsonl": (("run", "seed"), {"B5": "v3_factorial_B5c.jsonl"}),
    "results/raw/v3_replay_skab.jsonl": (("scenario", "seed"), {"B5": "v3_replay_skab_B5c.jsonl"}),
    "results/v4/raw/A0_core.jsonl": (("arm", "scenario", "point", "seed"), {"B5": "A0_core_B5c.jsonl",
                                                                         "B5S": "A0_core_B5c.jsonl"}),
    "results/v4/raw/A1_review.jsonl": (("arm", "scenario", "point", "seed"), {"B5": "A1_review_B5c.jsonl"}),
    "results/v4/raw/A3_selective.jsonl": (("arm", "scenario", "point", "seed"), {"B5": "A3_selective_B5c.jsonl",
                                                                              "B5S": "A3_selective_B5c.jsonl"}),
    "results/v4/raw/A3_factorial.jsonl": (("arm", "scenario", "point", "seed"), {"B5": "A3_factorial_B5c.jsonl",
                                                                              "B5S": "A3_factorial_B5c.jsonl"}),
}


def rows(p):
    return [json.loads(l) for l in open(p) if l.strip()]


def key(r, fields):
    return tuple(json.dumps(r.get(f), sort_keys=True) for f in fields)


def outcome_fields(a, b):
    out = []
    for f in sorted(set(a) | set(b)):
        if any(t in f for t in TIMING) or any(f.startswith(v) for v in V9_ONLY) or f in ("cfg", "trace"):
            continue
        if f not in a:                       # recorded only by the V9 runners (e.g. the counters of the V3 rows)
            continue
        if a.get(f) != b.get(f):
            out.append(f)
    return out


def main(out_dir: Path):
    if out_dir.exists():
        shutil.rmtree(out_dir)
    ignore = shutil.ignore_patterns("__pycache__", ".pytest_cache", "*.pyc", ".git")
    shutil.copytree(ROOT, out_dir, ignore=ignore, symlinks=True)
    report, missing = {}, []
    for rel, (fields, sysmap) in PLAN.items():
        orig = rows(ROOT / rel)
        corr_by_sys = defaultdict(dict)
        for system, fname in sysmap.items():
            p = V9RAW / fname
            if not p.exists():
                missing.append(fname)
                continue
            for r in rows(p):
                if "error" in r or r.get("system") != system:
                    continue
                corr_by_sys[system][key(r, fields)] = r
        merged, rep = [], defaultdict(lambda: {"rows": 0, "replaced": 0, "missing_corrected": 0,
                                                "rows_with_outcome_change": 0, "changed_fields": defaultdict(int),
                                                "nofork_rows": 0, "nofork_rows_identical": 0, "nofork_mismatch": []})
        for r in orig:
            s = r.get("system")
            if s in sysmap and "error" not in r:
                st = rep[s]
                st["rows"] += 1
                c = corr_by_sys.get(s, {}).get(key(r, fields))
                if c is None:
                    st["missing_corrected"] += 1
                    merged.append(r)
                    continue
                st["replaced"] += 1
                d = outcome_fields(r, c)
                core = [f for f in d if not any(f.startswith(x) for x in COUNTERS)]
                if core:
                    st["rows_with_outcome_change"] += 1
                for f in d:
                    st["changed_fields"][f] += 1
                if r.get("fork_events", 0) == 0 and r.get("holds", 0) == 0:
                    st["nofork_rows"] += 1
                    if not d:
                        st["nofork_rows_identical"] += 1
                    elif len(st["nofork_mismatch"]) < 5:
                        st["nofork_mismatch"].append({"key": key(r, fields), "fields": d[:10]})
                merged.append(c)
            else:
                merged.append(r)
        extra = {s: len(m) - rep[s]["replaced"] for s, m in corr_by_sys.items()}
        with open(out_dir / rel, "w") as fh:
            for r in merged:
                fh.write(json.dumps(r, default=str) + "\n")
        report[rel] = {s: dict(v, changed_fields=dict(v["changed_fields"])) for s, v in rep.items()}
        report[rel]["unused_corrected_rows"] = extra
    summ = ROOT / "results" / "v9" / "summary"
    summ.mkdir(parents=True, exist_ok=True)
    (summ / "b5c_row_comparison.json").write_text(json.dumps({"missing_corrected_files": missing, "files": report},
                                                             indent=1))
    ok = all(v.get("missing_corrected", 0) == 0 and v.get("nofork_rows", 0) == v.get("nofork_rows_identical", 0)
             for f in report.values() for s, v in f.items() if isinstance(v, dict) and "rows" in v)
    print(json.dumps({"tree": str(out_dir), "missing_files": missing, "complete_and_invariant": ok}, indent=1))
    for rel, f in report.items():
        for s, v in f.items():
            if isinstance(v, dict) and "rows" in v:
                print(f"{rel} {s}: rows {v['rows']} replaced {v['replaced']} missing {v['missing_corrected']} "
                      f"outcome-changed {v['rows_with_outcome_change']} no-fork {v['nofork_rows_identical']}/{v['nofork_rows']}")


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve())
