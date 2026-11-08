#!/usr/bin/env python3
"""Amendment A4: replace the B5 and B5s rows of the X1 and X2 result files by the re-runs under the fixed B5 code, keep
the superseded rows under results/raw/superseded/, and compare old and new rows (results/summary/v3_b5_fix_comparison.json).
PBTI-R rows (PBTIVerifier, unaffected by the fix) are kept. Idempotent: originals are read from results/raw/superseded/."""
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results" / "raw"
SUP = RAW / "superseded"
SKIP = ("_us", "_s", "wall", "ingest", "wrap", "devsign", "audit")
PLAN = {"v3_scenarios_b5.jsonl": {"B5": "v3_scenarios_b5_fixedB5.jsonl", "B5S": "v3_scenarios_b5s_fixed.jsonl"},
        "v3_mixed_b5.jsonl": {"B5": "v3_mixed_b5_fixedB5.jsonl", "B5S": "v3_mixed_b5s_fixed.jsonl"}}


def rows(p):
    return [json.loads(l) for l in open(p) if l.strip()]


def main():
    SUP.mkdir(exist_ok=True)
    report = {}
    for orig, fixed in PLAN.items():
        o_path = RAW / orig
        keep = SUP / orig.replace(".jsonl", "_before_B5_fix.jsonl")
        if not keep.exists():
            shutil.copy2(o_path, keep)
            mf = o_path.with_suffix(".manifest.json")
            if mf.exists():
                shutil.copy2(mf, SUP / mf.name.replace(".manifest.json", "_before_B5_fix.manifest.json"))
        old = rows(keep)
        merged = [r for r in old if r["system"] not in fixed]
        for system, fname in fixed.items():
            new = {(r["scenario"], r["seed"]): r for r in rows(RAW / fname) if r["system"] == system and "error" not in r}
            prev = {(r["scenario"], r["seed"]): r for r in old if r["system"] == system}
            assert set(new) == set(prev), (orig, system, len(new), len(prev))
            diffs, same_o = {}, 0
            for k in sorted(prev):
                a, b = prev[k], new[k]
                d = [f for f in a if not any(t in f for t in SKIP) and a.get(f) != b.get(f)]
                same_o += a["nonlegit_auth"] == b["nonlegit_auth"] and a["legit_missing"] == b["legit_missing"]
                if d:
                    diffs[f"{k[0]}|{k[1]}"] = {f: [a.get(f), b.get(f)] for f in d[:12]}
            merged += [new[k] for k in sorted(new)]
            report[f"{orig}|{system}"] = {"runs": len(new), "same_O1_O2": same_o, "runs_with_any_difference": len(diffs),
                                         "audits_new": {"run": sum("audit_pass" in r for r in new.values()),
                                                        "pass": sum(bool(r.get("audit_pass")) for r in new.values())},
                                         "differences": diffs}
        with open(o_path, "w") as fh:
            for r in merged:
                fh.write(json.dumps(r, default=str) + "\n")
    (ROOT / "results" / "summary" / "v3_b5_fix_comparison.json").write_text(json.dumps(report, indent=1))
    for k, v in report.items():
        print(k, {x: y for x, y in v.items() if x != "differences"})


if __name__ == "__main__":
    main()
