#!/usr/bin/env python3
"""Compare a re-execution of selected seeds with the stored results, field by field (prompt item 1.4).

For every re-executed run the stored run with the same campaign, arm, scenario/design point and seed is looked up in
STORED_REPO/results/v4/raw/<campaign>.jsonl. Every field is compared for exact equality except wall-clock timing
(fields containing "_us", and wall_s, audit_static_s, audit_replay_s), which depends on the machine. Virtual-time
outcomes (O1, O2, holds, all tm_* time-integrated outcomes, review counts, audit verdicts) are compared.
The deterministic lifecycle matrix and the bounded formal check are compared as whole documents (timing excluded).

Usage: python3 compare_reexec.py --stored-repo DIR --new DIR --out-json FILE --out-md FILE
"""
import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

CAMPAIGN_FILES = {          # re-executed file in --new  ->  stored file in results/v4/raw
    "A0_core_subset.jsonl": "A0_core.jsonl",
    "A1_review_subset.jsonl": "A1_review.jsonl",
    "A3_selective_subset.jsonl": "A3_selective.jsonl",
    "A3_scenarios_subset.jsonl": "A3_scenarios.jsonl",
    "A3_factorial_subset.jsonl": "A3_factorial.jsonl",
}
TIMING_EXACT = {"wall_s", "audit_static_s", "audit_replay_s"}


def timing(k: str) -> bool:
    return "_us" in k or k in TIMING_EXACT


def key(r):
    return (r.get("campaign"), r.get("arm"), r.get("scenario"), str(r.get("point", r.get("run", ""))), r.get("seed"))


def load_rows(p: Path):
    rows, errors = {}, []
    for line in p.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if "error" in r:
            errors.append(r)
            continue
        rows[key(r)] = r
    return rows, errors


def cmp_campaign(stored_p: Path, new_p: Path):
    stored, s_err = load_rows(stored_p)
    new, n_err = load_rows(new_p)
    res = {"stored_file": stored_p.name, "new_file": new_p.name, "compared": 0, "identical": 0, "different": 0,
           "missing_in_stored": [], "errors_in_new": len(n_err), "n_field_comparisons": 0,
           "timing_fields_excluded": set(), "differences": [], "by_arm": defaultdict(Counter)}
    seeds = sorted({k[4] for k in new})
    res["seeds"] = seeds
    for k, n in sorted(new.items(), key=lambda kv: str(kv[0])):
        s = stored.get(k)
        if s is None:
            res["missing_in_stored"].append(list(k))
            continue
        fields = sorted(set(s) | set(n))
        cmpf = [f for f in fields if not timing(f)]
        res["timing_fields_excluded"].update(f for f in fields if timing(f))
        res["n_field_comparisons"] += len(cmpf)
        diff = [f for f in cmpf if s.get(f) != n.get(f)]
        res["compared"] += 1
        res["by_arm"][k[1]]["compared"] += 1
        if diff:
            res["different"] += 1
            res["by_arm"][k[1]]["different"] += 1
            res["differences"].append({"key": list(k), "fields": {f: [s.get(f), n.get(f)] for f in diff[:15]}})
        else:
            res["identical"] += 1
            res["by_arm"][k[1]]["identical"] += 1
    # stored rows for the same seeds and design that were not re-executed (coverage check)
    arms_points = {(k[0], k[1], k[2], k[3]) for k in new}
    not_reexecuted = [list(k) for k in stored if k[4] in seeds and (k[0], k[1], k[2], k[3]) in arms_points
                      and k not in new]
    res["stored_rows_same_seeds_not_reexecuted"] = not_reexecuted
    res["timing_fields_excluded"] = sorted(res["timing_fields_excluded"])
    res["by_arm"] = {a: dict(c) for a, c in res["by_arm"].items()}
    return res


def strip_timing(x):
    if isinstance(x, dict):
        return {k: strip_timing(v) for k, v in x.items()
                if not (k in ("seconds_total", "log") or "seconds" in k or k.endswith("_s"))}
    if isinstance(x, list):
        return [strip_timing(v) for v in x]
    return x


def diff_paths(a, b, path="", out=None):
    out = [] if out is None else out
    if type(a) is not type(b):
        out.append(path or "/")
    elif isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append(f"{path}/{k}")
            else:
                diff_paths(a[k], b[k], f"{path}/{k}", out)
    elif isinstance(a, list):
        if len(a) != len(b):
            out.append(f"{path}[len]")
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                diff_paths(x, y, f"{path}[{i}]", out)
    elif a != b:
        out.append(path or "/")
    return out


def cmp_a5(stored_p: Path, new_p: Path):
    s = json.loads(stored_p.read_text())
    n = json.loads(new_p.read_text())
    k = lambda r: (r.get("pipeline"), r.get("case"), r.get("policy"), float(r.get("width_s") or 0))
    si, ni = {k(r): r for r in s}, {k(r): r for r in n}
    diffs = [list(x) for x in sorted(set(si) | set(ni), key=str) if si.get(x) != ni.get(x)]
    return {"stored_rows": len(s), "new_rows": len(n), "identical_rows": sum(1 for x in ni if si.get(x) == ni[x]),
            "different_or_missing": diffs}


def cmp_formal(stored_p: Path, new_p: Path):
    s = strip_timing(json.loads(stored_p.read_text()))
    n = strip_timing(json.loads(new_p.read_text()))
    d = diff_paths(s, n)
    return {"all_pass_stored": s.get("all_pass"), "all_pass_new": n.get("all_pass"), "identical_excluding_timing": not d,
            "differing_paths": d[:50]}


def parse_pytest(log: Path):
    if not log.exists():
        return None
    txt = log.read_text(errors="replace")
    m = re.findall(r"(\d+) (passed|failed|skipped|error|errors|xfailed|xpassed)", txt.splitlines()[-1] if txt else "")
    counts = {w: int(n) for n, w in m}
    return {"summary_line": txt.strip().splitlines()[-1] if txt.strip() else "", "counts": counts}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stored-repo", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--out-md", required=True)
    a = ap.parse_args()
    S = Path(a.stored_repo)
    N = Path(a.new)
    out = {"campaigns": {}, "a5_lifecycle_matrix": None, "formal_check": None, "pytest": None, "steps": [],
           "environment": None}
    for nf, sf in CAMPAIGN_FILES.items():
        if (N / nf).exists():
            out["campaigns"][nf] = cmp_campaign(S / "results" / "v4" / "raw" / sf, N / nf)
    if (N / "A5_lifecycle_matrix.json").exists():
        out["a5_lifecycle_matrix"] = cmp_a5(S / "results/v4/summary/A5_lifecycle_matrix.json",
                                            N / "A5_lifecycle_matrix.json")
    if (N / "v4_locality_lifecycle_check.json").exists():
        out["formal_check"] = cmp_formal(S / "results/v4/formal/v4_locality_lifecycle_check.json",
                                         N / "v4_locality_lifecycle_check.json")
    out["pytest"] = parse_pytest(N / "pytest.log")
    if (N / "steps.tsv").exists():
        for line in (N / "steps.tsv").read_text().splitlines():
            parts = line.split("\t")
            if len(parts) >= 5:
                out["steps"].append({"step": parts[0], "exit_code": int(parts[1]), "start_utc": parts[2],
                                     "end_utc": parts[3], "command": parts[4]})
    out["digests"] = {}
    for nf, sf in CAMPAIGN_FILES.items():
        nm, sm = N / nf.replace(".jsonl", ".manifest.json"), S / "results" / "v4" / "raw" / sf.replace(".jsonl", ".manifest.json")
        if nm.exists() and sm.exists():
            a_, b_ = json.loads(nm.read_text()), json.loads(sm.read_text())
            out["digests"][nf] = {k: {"stored": b_.get(k), "new": a_.get(k), "equal": b_.get(k) == a_.get(k)}
                                  for k in ("source_sha256", "config_sha256")}
    if (N / "environment.json").exists():
        env = json.loads((N / "environment.json").read_text())
        env.pop("code_files_sha256", None)
        out["environment"] = env
    tot = Counter()
    for c in out["campaigns"].values():
        for f in ("compared", "identical", "different", "errors_in_new", "n_field_comparisons"):
            tot[f] += c[f]
        tot["missing_in_stored"] += len(c["missing_in_stored"])
        tot["not_reexecuted"] += len(c["stored_rows_same_seeds_not_reexecuted"])
    out["totals"] = dict(tot)
    ok = (tot["different"] == 0 and tot["errors_in_new"] == 0 and tot["missing_in_stored"] == 0
          and all(s["exit_code"] == 0 for s in out["steps"])
          and (out["a5_lifecycle_matrix"] is None or not out["a5_lifecycle_matrix"]["different_or_missing"])
          and (out["formal_check"] is None or out["formal_check"]["identical_excluding_timing"])
          and all(v["equal"] for d in out["digests"].values() for v in d.values()))
    out["verdict"] = "ALL RE-EXECUTED OUTPUTS IDENTICAL TO STORED OUTPUTS (timing excluded)" if ok else \
        "DIFFERENCES OR FAILURES FOUND - see details"
    Path(a.out_json).write_text(json.dumps(out, indent=1, default=str))

    L = ["# Re-execution of selected seeds: comparison with the stored results", ""]
    e = out["environment"] or {}
    L += [f"**Verdict:** {out['verdict']}", "",
          f"* Label: {e.get('label', '')}",
          f"* Time (UTC): {e.get('time_utc')}; local: {e.get('time_local')}",
          f"* CPU: {e.get('cpu_model')} ({e.get('logical_cpus')} logical CPUs), memory {e.get('memory_gib')} GiB",
          f"* OS: {e.get('os')} (kernel {e.get('kernel')}, {e.get('machine')}); Python {e.get('python')}",
          f"* Packages: " + ", ".join(f"{k} {v}" for k, v in (e.get('packages') or {}).items()),
          f"* Git commit: {e.get('git_commit') or 'not a git checkout'}",
          f"* Source SHA-256 (src/pbti aggregate): `{e.get('source_sha256_src_pbti_aggregate')}`",
          f"* Code SHA-256 (src, experiments, analysis, formal, scripts aggregate): `{e.get('code_sha256_aggregate')}`",
          "", "## Steps", "", "| Step | Exit code | Start (UTC) | End (UTC) | Command |", "|---|---|---|---|---|"]
    for s in out["steps"]:
        L.append(f"| {s['step']} | {s['exit_code']} | {s['start_utc']} | {s['end_utc']} | `{s['command']}` |")
    if out["pytest"]:
        L += ["", f"Test suite: {out['pytest']['summary_line']}"]
    L += ["", "## Campaign runs", "", "| Re-executed file | Seeds | Runs compared | Identical | Different | Errors | "
          "Field comparisons |", "|---|---|---|---|---|---|---|"]
    for nf, c in out["campaigns"].items():
        L.append(f"| {nf} | {', '.join(map(str, c['seeds']))} | {c['compared']} | {c['identical']} | {c['different']} | "
                 f"{c['errors_in_new']} | {c['n_field_comparisons']} |")
    if out["digests"]:
        L += ["", "Source and configuration digests as recorded by the runner (repository definition), stored campaign "
              "versus re-execution:", "", "| Re-executed file | source_sha256 | config_sha256 | equal |", "|---|---|---|---|"]
        for nf, d in out["digests"].items():
            L.append(f"| {nf} | `{str(d['source_sha256']['new'])[:16]}…` | `{str(d['config_sha256']['new'])[:16]}…` | "
                     f"{'yes' if all(v['equal'] for v in d.values()) else 'NO'} |")
    L += ["", f"Totals: {json.dumps(out['totals'])}", "",
          "Excluded (machine-dependent wall-clock timing): fields containing `_us`, and `wall_s`, `audit_static_s`, "
          "`audit_replay_s`."]
    if out["a5_lifecycle_matrix"]:
        m = out["a5_lifecycle_matrix"]
        L += ["", f"Lifecycle matrix: {m['identical_rows']} of {m['stored_rows']} rows identical; "
              f"different or missing: {len(m['different_or_missing'])}"]
    if out["formal_check"]:
        f = out["formal_check"]
        L += ["", f"Bounded formal check: all_pass stored={f['all_pass_stored']}, new={f['all_pass_new']}; identical "
              f"excluding timing: {f['identical_excluding_timing']}"]
    diffs = [d for c in out["campaigns"].values() for d in c["differences"]]
    if diffs:
        L += ["", "## Differences (first 20)", ""] + [f"* {d['key']}: {json.dumps(d['fields'])[:400]}" for d in diffs[:20]]
    L += ["", "Scope: this compares the listed seeds only. It is not a full reproduction of every campaign, and a "
          "re-execution on the same code shows determinism and portability of the stored results, not the validity "
          "of the modelling assumptions."]
    Path(a.out_md).write_text("\n".join(L) + "\n")
    print(out["verdict"])
    print(json.dumps(out["totals"]))


if __name__ == "__main__":
    main()
