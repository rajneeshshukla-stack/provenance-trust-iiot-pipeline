#!/usr/bin/env python3
"""V9 verification record: what was actually run to check the package, and its outcome.

Checks (each recorded with command, start/end time, exit status and summary):
  1. test suite (pytest, junit report)                      6. regeneration of the historical summaries from raw rows
  2. frozen files unchanged (freeze lists)                  7. spot reruns from a clean copy reproduce stored rows
  3. every V9 run file complete and without error rows      8. from a clean copy: corrected tree, analysis and figures
  4. corrected rows carry one implementation and source        reproduce the manuscript's generated files, figure
  5. corrected tree complete; no-fork rows invariant           data and the V9 summaries; the article's
                                                               qualitative statements hold on the corrected data
                                                               (claims_check.py); corrected A0 rows
                                                               consistent with corrected V3 rows
Passing software tests or reproducing stored rows shows determinism and internal consistency; it does not prove the
scientific claims, validate the proof, or establish human verification.

usage: python3 tools/v9/verify_v9.py CLEAN_DIR      (CLEAN_DIR: empty scratch directory for steps 7-8)
"""
from __future__ import annotations

import filecmp
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLEAN = Path(sys.argv[1]).resolve()
REC = {"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "steps": []}
EXPECTED = {"A1_review_B5c.jsonl": 880, "v3_scenarios_B5c.jsonl": 300, "v3_mixed_B5c.jsonl": 20,
            "v3_scenarios_B5Sc.jsonl": 300, "v3_mixed_B5Sc.jsonl": 20, "A0_core_B5c.jsonl": 640,
            "A3_selective_B5c.jsonl": 1260, "A3_factorial_B5c.jsonl": 480, "v3_sweep_B5c.jsonl": 940,
            "v3_factorial_B5c.jsonl": 320, "v3_replay_skab_B5c.jsonl": 69, "attacker_consistent_impersonator.jsonl": 148}


def run(name, cmd, cwd=ROOT, timeout=7200):
    t0 = time.time()
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, shell=isinstance(cmd, str))
    step = {"name": name, "command": cmd if isinstance(cmd, str) else " ".join(cmd), "cwd": str(cwd),
            "exit": p.returncode, "seconds": round(time.time() - t0, 1),
            "stdout_tail": p.stdout[-1500:], "stderr_tail": p.stderr[-800:]}
    REC["steps"].append(step)
    print(f"[{name}] exit {p.returncode} in {step['seconds']} s", flush=True)
    return p


def note(name, ok, detail):
    REC["steps"].append({"name": name, "ok": bool(ok), "detail": detail})
    print(f"[{name}] {'ok' if ok else 'FAILED'}: {json.dumps(detail)[:300]}", flush=True)


# 1-2 -------------------------------------------------------------------------------------------------------------
run("pytest", [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests",
               "--junitxml=results/v9/summary/pytest_v9.xml"])
run("frozen_files", [sys.executable, "scripts/verify_prereg_hashes.py"])
# 3-4 -------------------------------------------------------------------------------------------------------------
files, impl = {}, set()
for f, n in EXPECTED.items():
    p = ROOT / "results/v9/raw" / f
    rows = [json.loads(l) for l in open(p)] if p.exists() else []
    err = sum(1 for r in rows if "error" in r)
    files[f] = {"rows": len(rows), "expected": n, "errors": err}
    for r in rows:
        if "b5_impl" in r and r.get("b5_impl"):
            impl.add((r["b5_impl"], r.get("b5_corrected_sha256"), r.get("source_sha256")))
note("v9_runs_complete", all(v["rows"] == v["expected"] and v["errors"] == 0 for v in files.values()), files)
note("v9_single_implementation", len({(a, b, c) for a, b, c in impl if a == "b5_corrected_v9"}) == 1,
     sorted(map(list, impl)))
# 5-6 -------------------------------------------------------------------------------------------------------------
cmp = json.loads((ROOT / "results/v9/summary/b5c_row_comparison.json").read_text())
ok = not cmp["missing_corrected_files"] and all(
    v.get("missing_corrected", 0) == 0 and v.get("nofork_rows", 0) == v.get("nofork_rows_identical", 0)
    for f in cmp["files"].values() for s, v in f.items() if isinstance(v, dict) and "rows" in v)
note("corrected_tree_complete_and_invariant", ok, {"missing_files": cmp["missing_corrected_files"]})
# 7 ---------------------------------------------------------------------------------------------------------------
if CLEAN.exists():
    shutil.rmtree(CLEAN)
CLEAN.mkdir(parents=True)
hist = CLEAN / "historical_tree"
shutil.copytree(ROOT, hist, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "v9"), symlinks=True)
stored = {d: {p.name: p.read_bytes() for p in (ROOT / d).glob("*") if p.is_file()}
          for d in ("paper/generated", "paper_v7/generated", "results/summary", "results/v4/summary")
          if (ROOT / d).is_dir()}
t_regen = time.time()
p_regen = run("regenerate_historical", ["bash", str(ROOT / "tools/v9/regenerate_analysis.sh"), str(hist)])
diffs, regenerated, not_written = {}, {}, {}
for d, files_ in stored.items():
    diffs[d] = [n for n, b in files_.items() if (hist / d / n).exists() and (hist / d / n).read_bytes() != b]
    regenerated[d] = sum(1 for n in files_ if (hist / d / n).exists() and (hist / d / n).stat().st_mtime >= t_regen)
    not_written[d] = sorted(n for n in files_ if not ((hist / d / n).exists() and (hist / d / n).stat().st_mtime >= t_regen))
expected_diff = {"tabS_env.tex"}     # marks the current source digest, which includes the added V9 module
# every per-cell table and comparison that Data S1 publishes must have been rewritten by this regeneration
ds1 = {"results/summary": ["v2_paired_tests.csv", "v3_outcomes_full.csv", "v3_x1_preregistered_tests.csv",
                           "v3_x2_mixed.csv", "v3_sweep_summary.csv", "v3_sweep_tests.csv", "v3_factorial_effects.csv",
                           "v3_replay_summary.csv", "v3_replay_tests.csv"],
       "results/v4/summary": ["A0_cells.csv", "A1_cells.csv", "A1_comparisons.csv", "A3_cells.csv",
                              "A3_comparisons.csv", "A3F_cells.csv", "A3F_comparisons.csv", "A3S_cells.csv",
                              "A3S_vs_A0_PBTI.csv"]}
missing_regen = [f"{d}/{n}" for d, ns in ds1.items() for n in ns if n in not_written.get(d, [])]
note("regenerated_equals_stored", p_regen.returncode == 0 and not missing_regen
     and all(set(v) <= expected_diff for v in diffs.values()),
     {"exit": p_regen.returncode, "differ": diffs, "rewritten": regenerated, "data_s1_sources_not_rewritten": missing_regen,
      "stored_files_not_written_by_the_analysis": {d: len(v) for d, v in not_written.items()}})
# 8 ---------------------------------------------------------------------------------------------------------------
clean_repo = CLEAN / "repo"
shutil.copytree(ROOT, clean_repo, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"), symlinks=True)
spot = CLEAN / "spot.jsonl"
run("clean_tests_corrected_b5", [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                                 "tests/test_b5_corrected.py"], cwd=clean_repo)
run("clean_spot_rerun", [sys.executable, "experiments/v9/run_v4_b5c.py", "experiments/v4_configs/A1_review.json",
                         "--arms", "B5-d0c1", "--out", str(spot), "--workers", "2"], cwd=clean_repo)
stored_rows = {}
for l in open(ROOT / "results/v9/raw/A1_review_B5c.jsonl"):
    r = json.loads(l)
    stored_rows[(r["arm"], r["scenario"], r["seed"])] = r
skip = ("_us", "wall", "ingest", "wrap", "devsign", "audit_static_s", "audit_replay_s")
mism = 0
n = 0
for l in open(spot):
    r = json.loads(l)
    s = stored_rows[(r["arm"], r["scenario"], r["seed"])]
    n += 1
    mism += any(r.get(k) != s.get(k) for k in s if not any(t in k for t in skip))
note("clean_spot_rerun_matches_stored", mism == 0 and n == 80, {"runs": n, "mismatching_runs": mism})
# 9 ---------------------------------------------------------------------------------------------------------------
man_stored = ROOT / "manuscript"
if man_stored.is_dir():
    man = CLEAN / "manuscript_check"
    shutil.copytree(man_stored, man)
    for p in list((man / "generated").glob("*.tex")) + list((man / "figures" / "data").glob("*.csv")):
        p.unlink()                                   # must be rewritten by the build, not carried over
    ctree = CLEAN / "corrected_tree"
    t_build = time.time()
    p_build = run("clean_corrected_build", ["bash", str(clean_repo / "tools/v9/build_corrected_results.sh"), str(man),
                                            str(ctree)], cwd=clean_repo)
    gen_diff, gen_missing = [], []
    for p in sorted((man_stored / "generated").glob("*.tex")):
        q = man / "generated" / p.name
        if not q.exists():
            gen_missing.append(p.name)
        elif q.read_bytes() != p.read_bytes():
            gen_diff.append(p.name)
    fig_diff = [p.name for p in sorted((man_stored / "figures" / "data").glob("*.csv"))
                if not (man / "figures" / "data" / p.name).exists()
                or (man / "figures" / "data" / p.name).read_bytes() != p.read_bytes()]
    # generated by xref_maps.py from the compiled documents, not by the analysis
    xref = {"main_xref.tex", "supp_xref.tex"}
    note("clean_build_reproduces_generated_files",
         p_build.returncode == 0 and not gen_diff and set(gen_missing) <= xref and not fig_diff,
         {"generated_compared": len(list((man_stored / "generated").glob("*.tex"))), "differ": gen_diff,
          "not_written_by_analysis": gen_missing, "figure_data_differ": fig_diff})
    sum_diff = [p.name for p in sorted((ROOT / "results/v9/summary").glob("V9_*"))
                if not (clean_repo / "results/v9/summary" / p.name).exists()
                or (clean_repo / "results/v9/summary" / p.name).stat().st_mtime < t_build
                or (clean_repo / "results/v9/summary" / p.name).read_bytes() != p.read_bytes()]
    note("clean_build_reproduces_v9_summaries", not sum_diff, {"differ": sum_diff})
    claims_out = CLEAN / "claims_corrected.json"
    p_cl = run("claims_check_corrected", [sys.executable, "-I", str(clean_repo / "tools/v9/claims_check.py"), str(ctree),
                                          str(claims_out), str(clean_repo / "results/v9/summary")], cwd=clean_repo)
    if claims_out.exists():
        cl = json.loads(claims_out.read_text())
        note("article_statements_hold_on_corrected_data", p_cl.returncode == 0 and all(
            v["holds"] for v in cl["claims"].values()),
            {k: v["holds"] for k, v in cl["claims"].items()})
    run("A0_consistency_corrected", [sys.executable, "scripts/compare_a0.py", "results/v4/raw/A0_core.jsonl",
                                     "--out", str(CLEAN / "A0_corrected_consistency.json")], cwd=ctree)
    shutil.copy2(CLEAN / "A0_corrected_consistency.json", ROOT / "results/v9/summary/A0_corrected_consistency.json")
REC["ended"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
REC["scope_note"] = ("All checks were run by the automated research process in its own workspace; none is an external, "
                     "independent reproduction or a human verification.")
out = ROOT / "results/v9/summary/verification_record.json"
out.write_text(json.dumps(REC, indent=1))
print("written", out)
