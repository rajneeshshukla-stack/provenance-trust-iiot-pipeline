#!/usr/bin/env python3
"""V9 checks on the deterministic lifecycle matrix (scripts/a5_lifecycle_matrix.py, unchanged):
  1. regeneration: the matrix is re-run with the historical classes and compared with the stored
     results/v4/summary/A5_lifecycle_matrix.json (must be identical);
  2. corrected comparator: the B5 rows are re-run with the corrected B5 (src/pbti/b5_corrected.py);
  3. E09: the superseded-snapshot case is traced (review openings, decisions, outcomes and times) for every policy and
     pipeline, to establish whether recovery follows a refused decision through a later fresh decision;
  4. E10: the witness-policy uncertainty widths that were actually evaluated and their outcomes.
Outputs: results/v9/summary/a5_e09_e10.json
"""
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
spec = importlib.util.spec_from_file_location("a5", ROOT / "scripts" / "a5_lifecycle_matrix.py")
a5 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a5)
from pbti.b5 import B5FeedLevel  # noqa: E402
from pbti.b5_corrected import B5Corrected  # noqa: E402
from pbti.verifier import PBTIVerifier  # noqa: E402

FIELDS = ["pipeline", "case", "policy", "width_s", "legitimate", "case_state", "authoritative_end", "tainted_end",
          "malicious_authoritative", "genuine_recovered", "genuine_withheld", "first_decision",
          "state_after_first_decision", "authoritative_after_release", "in_window_after_release",
          "window_versions_added", "window_corrected"]


def norm(rows):
    return [{k: r.get(k) for k in FIELDS} for r in rows]


def trace_stale(cls, pol):
    e = a5.Env(cls, pol, {"h_max_ms": 10_000})
    r = a5.case_stale_snapshot(e)
    log = []
    for t, wd, tid in e.v.receipt_log:
        if isinstance(tid, (tuple, list)) and tid and tid[0] in ("REVIEW_OPEN", "REVIEW"):
            if tid[0] == "REVIEW_OPEN":
                log.append({"t_ms": t, "event": "REVIEW_OPEN", "case": wd[:12]})
            else:
                d = tid[1]
                log.append({"t_ms": t, "event": "REVIEW", "case": (d.get("case") or "")[:12],
                            "decision": d.get("decision"), "snapshot_taken_at_ms": None})
    outcomes = [{"t_ms": rec["t"], "outcome": rec["outcome"], "decision": rec["decision"],
                 "snapshot_succ_implied": bool((rec.get("evidence") or {}).get("succ_implied"))}
                for rec in (json.loads(x) for x in e.v.evidence.records) if rec.get("type") == "REVIEW"]
    return {"pipeline": cls.name, "policy": pol, "first_decision": r.get("first_decision"),
            "state_after_first_decision": r.get("state_after_first_decision"), "case_state_end": r.get("case_state"),
            "genuine_recovered": r.get("genuine_recovered"), "review_log": log, "review_records": outcomes}


def main():
    stored = json.loads((ROOT / "results/v4/summary/A5_lifecycle_matrix.json").read_text())
    regen = a5.run_all()
    same = norm(regen) == norm(stored)
    a5.B5FeedLevel = B5Corrected
    corr = a5.run_all()
    a5.B5FeedLevel = B5FeedLevel
    diffs = []
    for o, c in zip(norm(regen), norm(corr)):
        if o != c:
            diffs.append({"case": o["case"], "policy": o["policy"], "pipeline": o["pipeline"], "width_s": o["width_s"],
                          "fields": {k: [o[k], c[k]] for k in FIELDS if o[k] != c[k]}})
    e09 = [trace_stale(cls, pol) for cls in (PBTIVerifier, B5FeedLevel, B5Corrected) for pol in a5.POLICIES]
    e10 = [{"pipeline": r["pipeline"], "width_s": r["width_s"], "genuine_recovered": r.get("genuine_recovered"),
            "genuine_withheld": r.get("genuine_withheld"), "case_state": r.get("case_state")}
           for r in regen if r["case"] == "legit_buffered_witnessed_interval"]
    out = {"a5_regenerated_equals_stored": same, "rows": len(regen),
           "corrected_b5_differences": diffs, "e09_superseded_snapshot": e09, "e10_widths": e10}
    p = ROOT / "results" / "v9" / "summary" / "a5_e09_e10.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps({"a5_regenerated_equals_stored": same, "corrected_b5_differences": len(diffs)}, indent=1))
    for x in e09:
        print(x["pipeline"], x["policy"], x["first_decision"], x["state_after_first_decision"], x["case_state_end"],
              x["genuine_recovered"], [(y["t_ms"], y["outcome"]) for y in x["review_records"]])
    for x in e10:
        print("E10", x)
    for d in diffs:
        print("B5c diff", d)


if __name__ == "__main__":
    main()
