"""Summarize the differential campaign (JSONL rows from run_diff.py) into a JSON summary and Markdown tables."""
import collections
import glob
import json
import os
import sys

OUT = "/home/claude/PBTI_v7/results/b5_refmodel"


def load(pattern):
    rows, errors = [], []
    for f in sorted(glob.glob(pattern)):
        for line in open(f):
            r = json.loads(line)
            (errors if "error" in r else rows).append(r)
    return rows, errors


def main(pattern=os.path.join(OUT, "campaign", "*.jsonl")):
    rows, errors = load(pattern)
    streams = collections.defaultdict(set)
    kinds = collections.Counter()
    seen = set()
    for r in rows:
        streams[r["family"]].add(r["seed"])
        if (r["family"], r["seed"]) not in seen:
            seen.add((r["family"], r["seed"]))
            kinds.update(r["kinds"])
    by = collections.defaultdict(lambda: collections.Counter())
    dW = collections.defaultdict(list)
    single = collections.defaultdict(collections.Counter)
    needed = collections.defaultdict(collections.Counter)
    O = collections.defaultdict(collections.Counter)
    for r in rows:
        key = (r["family"], r["setting"])
        c = by[key]
        c["rows"] += 1
        c["spec_core_equal"] += r["cmp_spec"]["all_core"]
        c["spec_final_equal"] += r["cmp_spec"]["final"]
        c["impl_core_equal"] += r["cmp_impl"]["all_core"]
        c["impl_all_fields_equal"] += all(r["cmp_impl"][k] for k in ("final", "intervals", "W", "NLX", "held_ids",
                                                                      "releases", "rejections", "resumes"))
        c["impl_counters_equal"] += r["counters_match_impl"]
        c["real_release_failed_hold"] += r["review_outcomes"].get("RELEASE_FAILED:QUARANTINE/FEED_FORK_HOLD", 0)
        c["rows_with_release_failed_hold"] += r["review_outcomes"].get("RELEASE_FAILED:QUARANTINE/FEED_FORK_HOLD", 0) > 0
        if not r["cmp_spec"]["all_core"]:
            dW[key].append(r["cmp_spec"]["dW_ms"])
            att = r.get("attribution", {})
            for s in att.get("single_fixes", []):
                single[key][s] += 1
            for s in att.get("needed", []):
                needed[key][s] += 1
            if not att.get("single_fixes"):
                single[key]["(none alone)"] += 1
        O[key]["spec_missing_minus_real"] += r["cmp_spec"]["d_missing"]
        O[key]["spec_nonlegit_minus_real"] += r["cmp_spec"]["d_nonlegit"]
        O[key]["W_spec_ms"] += r["spec_model"]["W"]
        O[key]["W_real_ms"] += r["real"]["W"]
        O[key]["NLX_spec_ms"] += r["spec_model"]["NLX"]
        O[key]["NLX_real_ms"] += r["real"]["NLX"]
        O[key]["missing_real"] += r["real"]["missing"]
        O[key]["missing_spec"] += r["spec_model"]["missing"]
        O[key]["nonlegit_real"] += r["real"]["nonlegit"]
        O[key]["nonlegit_spec"] += r["spec_model"]["nonlegit"]
        O[key]["reachable"] += 0
    summary = {"n_rows": len(rows), "n_errors": len(errors), "streams": {k: len(v) for k, v in streams.items()},
               "n_streams": sum(len(v) for v in streams.values()), "stream_kinds": dict(kinds), "cells": {}}
    for key in sorted(by):
        d = dict(by[key])
        d.update({"dW_spec_minus_real_ms": {"n": len(dW[key]), "neg": sum(x < 0 for x in dW[key]),
                                            "pos": sum(x > 0 for x in dW[key]), "zero": sum(x == 0 for x in dW[key]),
                                            "sum": sum(dW[key])},
                  "single_switch_fixes": dict(single[key]), "needed_switches": dict(needed[key]),
                  "outcomes": dict(O[key])})
        summary["cells"]["|".join(key)] = d
    tot = collections.Counter()
    for key, c in by.items():
        tot.update(c)
    summary["totals"] = dict(tot)
    tot_single, tot_needed = collections.Counter(), collections.Counter()
    for key in single:
        tot_single.update(single[key])
        tot_needed.update(needed[key])
    summary["totals"]["single_switch_fixes"] = dict(tot_single)
    summary["totals"]["needed_switches"] = dict(tot_needed)
    with open(os.path.join(OUT, "campaign_summary.json"), "w") as fh:
        json.dump(summary, fh, indent=1, default=str)
    # markdown
    lines = ["| family | setting | rows | phase-1 model = real (final & timeline) | final set equal | impl-choice model = real | all fields | counters | W spec-real (s, sum) | missing spec-real | non-legit spec-real | RELEASE_FAILED hold |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for key in sorted(by):
        c = by[key]
        o = O[key]
        lines.append(f"| {key[0]} | {key[1]} | {c['rows']} | {c['spec_core_equal']} | {c['spec_final_equal']} | "
                     f"{c['impl_core_equal']} | {c['impl_all_fields_equal']} | {c['impl_counters_equal']} | "
                     f"{(o['W_spec_ms'] - o['W_real_ms']) / 1000:.0f} | {o['spec_missing_minus_real']} | "
                     f"{o['spec_nonlegit_minus_real']} | {c['real_release_failed_hold']} |")
    with open(os.path.join(OUT, "campaign_table.md"), "w") as fh:
        fh.write("\n".join(lines) + "\n")
    print(json.dumps({k: summary[k] for k in ("n_rows", "n_errors", "streams", "n_streams", "totals")}, indent=1))
    return summary


if __name__ == "__main__":
    main(*sys.argv[1:])
