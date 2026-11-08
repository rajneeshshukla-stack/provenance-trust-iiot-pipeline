#!/usr/bin/env python3
"""Independent reference for two reported secondary outcomes, from the captured histories (no simulation):
  freshness (Table S22): per asset at 1 s steps, missing = no correct value available; stale = age of the latest
             available correct value behind the latest produced one;
  alerts    (Table S22): alert when temp_c > nominal + 2.5 degC; true / missed (not raised within 5 s of production) /
             retracted; false alerts = non-legitimate authoritative pairs above the threshold, retracted or open.
Nominal temperatures are regenerated from the simulator's device construction (src/pbti/sim.py Device.__init__:
random.Random(seed*7919 + g*101 + j); phase, then base_t = 55 + 20*U), i.e. ground truth, not the oracle.
Compared with the stored row of the same run."""
import glob
import gzip
import json
import math
import pickle
import random
import sys

sys.path.insert(0, "/home/claude/PBTI_v7/tools/oracle_audit")
from refmetrics import _union  # noqa: E402

RUNS = "/home/claude/PBTI_v7/results/oracle_audit/runs"
REPO = "/home/claude/PBTI_v7/scratch/oracle_audit/repo"


def nominal_for(seed, n_gw=4, dev_per_gw=6):
    out = {}
    for g in range(1, n_gw + 1):
        for j in range(1, dev_per_gw + 1):
            rng = random.Random(seed * 7919 + g * 101 + j)
            rng.random()                       # phase
            out[f"pa-c{g}-a{j:02d}"] = 55 + 20 * rng.random()
    return out


def avail_at(u, t):
    for a, b in u:
        if a <= t < b:
            return True
        if a > t:
            return False
    return False


def temp_of(c):
    pl = dict(c[4][1])          # content payload: ("d", ((key, ("n", value)), ...))
    v = pl.get("temp_c")
    return v[1] if v and v[0] == "n" else None


def secondary(legit, iv, t_end, nominal):
    L = [o for o in legit if o["t_acc"] is not None]
    honest = set()
    for o in L:
        honest |= o["pairs"]
    av = [_union([x for p in o["pairs"] for x in iv.get(p, ())]) for o in L]
    # freshness
    by_asset = {}
    for o, u in zip(L, av):
        by_asset.setdefault(o["content"][1], []).append((o["t_prod"], u))
    samples = missing = 0
    stale = []
    for aid, items in by_asset.items():
        items.sort(key=lambda x: x[0])
        for tau in range(1000, t_end, 1000):
            produced = [x for x in items if x[0] <= tau]
            if not produced:
                continue
            samples += 1
            latest = produced[-1][0]
            avail = [tp for tp, u in produced if avail_at(u, tau)]
            if not avail:
                missing += 1
            else:
                stale.append(latest - max(avail))
    res = {"tm_fresh_samples": samples, "tm_fresh_missing_frac": missing / samples if samples else 0.0,
           "tm_fresh_stale_mean_s": (sum(stale) / len(stale) / 1000) if stale else 0.0,
           "tm_fresh_stale_frac": (sum(1 for s in stale if s > 0) / samples) if samples else 0.0}
    # alerts
    true_a = missed = retr_true = 0
    for o, u in zip(L, av):
        th = nominal.get(o["content"][1])
        tv = temp_of(o["content"])
        if th is None or tv is None or not tv > th + 2.5:
            continue
        true_a += 1
        if not u or u[0][0] - o["t_prod"] > 5000:
            missed += 1
        if u and (len(u) > 1 or u[-1][1] < t_end):
            retr_true += 1
    false_a = false_retr = false_open = 0
    for p, v in iv.items():
        if p in honest:
            continue
        th = nominal.get(p[1][1])
        tv = temp_of(p[1])
        if th is None or tv is None or not tv > th + 2.5:
            continue
        false_a += 1
        if max(b for _, b in v) < t_end:
            false_retr += 1
        else:
            false_open += 1
    res.update({"tm_alert_true": true_a, "tm_alert_missed": missed, "tm_alert_retract_true": retr_true,
                "tm_alert_false": false_a, "tm_alert_false_retracted": false_retr, "tm_alert_false_open_end": false_open})
    return res


def main():
    stored = {}
    for camp in ("A0_core", "A1_review", "A3_factorial"):
        for line in open(f"{REPO}/results/v4/raw/{camp}.jsonl"):
            r = json.loads(line)
            loc = r.get("point") if r.get("kind") == "sweep" else r.get("scenario")
            stored[f"{camp}__{r['arm']}__{loc}__{r['seed']}"] = r
    out, n_ok, n_all = {}, 0, 0
    for f in sorted(glob.glob(RUNS + "/*.pkl.gz")):
        tag = f.split("/")[-1][:-7]
        d = pickle.load(gzip.open(f))
        seed = int(tag.split("__")[-1])
        res = secondary(d["legit"], d["hist"]["poll_call"][0], d["t_end"], nominal_for(seed))
        st = stored[tag]
        cmp = {}
        for k, v in res.items():
            sv = st.get(k)
            ok = sv is not None and math.isclose(v, sv, rel_tol=1e-9, abs_tol=1e-12)
            cmp[k] = {"ref": v, "stored": sv, "match": ok}
            n_all += 1
            n_ok += ok
        out[tag] = cmp
        bad = {k: (c["ref"], c["stored"]) for k, c in cmp.items() if not c["match"]}
        print(f"{tag:46s} fresh_missing={res['tm_fresh_missing_frac']:.5f} stale={res['tm_fresh_stale_mean_s']:.4f} "
              f"alerts T/M/F={res['tm_alert_true']}/{res['tm_alert_missed']}/{res['tm_alert_false']} "
              f"mismatch={bad}")
    json.dump(out, open("/home/claude/PBTI_v7/results/oracle_audit/ref_secondary.json", "w"), indent=1)
    print(f"\n{n_ok}/{n_all} secondary values match the stored rows")


if __name__ == "__main__":
    main()
