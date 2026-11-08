"""Ground-truth oracle. Computes, per run, the invariant-oriented correctness metrics.

Definitions (docs/EXPERIMENT_PLAN.md, Table "Metric definitions"):
  reachable legit observation : produced by an honest device AND accepted by an edge gateway
  legit_auth        reachable legit observations present exactly in the authoritative set
  legit_missing     reachable legit observations absent from the authoritative set
  dup_auth          extra authoritative copies of a legit observation (idempotency violations, I3)
  nonlegit_auth     authoritative observations whose content matches no legit observation
                    (forged / tampered / replay-with-modification; integrity violations, I1/I2/I4)
  windows           derived records classified EXACT | INCOMPLETE | CORRUPT against the ideal
                    derived state computed from all reachable legit observations
  cv_correct        assets whose final current value equals the latest legit observation
"""
from __future__ import annotations

from collections import Counter
from statistics import mean
from typing import Any

import numpy as np


def _pct(a, q):
    return float(np.percentile(a, q)) if len(a) else float("nan")


def evaluate(world) -> dict[str, Any]:
    sys = world.sys
    W = world.cfg.vcfg.window_ms
    legit = Counter()
    reach = Counter()
    last_by_aid: dict[str, tuple] = {}
    ideal_w: dict[tuple, Counter] = {}
    for tr in world.truth:
        ck = tr["ck"]
        legit[ck] += 1
        if tr["o"].meta.get("gw_accepted"):
            reach[ck] += 1
            wk = (tr["aid"], tr["ts"] - tr["ts"] % W)
            ideal_w.setdefault(wk, Counter())[ck] += 1
            prev = last_by_aid.get(tr["aid"])
            if prev is None or tr["t"] >= prev[0]:
                last_by_aid[tr["aid"]] = (tr["t"], ck)
    auth = Counter(ck for _, ck in sys.authoritative())
    legit_auth = sum(min(auth[ck], reach[ck]) for ck in reach)
    dup_auth = sum(max(0, auth[ck] - legit[ck]) for ck in auth if ck in legit)
    nonlegit_auth = sum(c for ck, c in auth.items() if ck not in legit)
    n_reach = sum(reach.values())
    # derived windows
    final = sys.proc.final_windows()
    exact = incomplete = corrupt = 0
    for wk, ideal in ideal_w.items():
        rec = final.get(wk)
        if rec is None:
            incomplete += 1
            continue
        got = Counter(rec["ckeys"])
        if any(ck not in legit or got[ck] > ideal.get(ck, 0) for ck in got):
            corrupt += 1
        elif got == ideal:
            exact += 1
        else:
            incomplete += 1
    extra_windows = sum(1 for wk, rec in final.items() if wk not in ideal_w and rec["n"] > 0)
    corrupt += extra_windows
    cv_ok = sum(1 for aid, (_, ck) in last_by_aid.items() if sys.proc.current_value(aid) == ck)
    ing = world.ingest_ns
    res = {
        "system": world.cfg.system,
        "ablation": world.cfg.ablation.label(),
        "seed": world.cfg.seed,
        "n_produced": sum(legit.values()),
        "n_reachable": n_reach,
        "n_receipts": len(ing),
        "legit_auth": legit_auth,
        "legit_missing": n_reach - legit_auth,
        "dup_auth": dup_auth,
        "nonlegit_auth": nonlegit_auth,
        "win_total": len(ideal_w) + extra_windows,
        "win_exact": exact,
        "win_incomplete": incomplete,
        "win_corrupt": corrupt,
        "cv_assets": len(last_by_aid),
        "cv_correct": cv_ok,
        "cv_samples": world.cv_samples,
        "cv_wrong": world.cv_wrong,
        "cv_wrong_rate": world.cv_wrong / max(1, world.cv_samples),
        "derived_versions": sys.proc.n_versions,
        "derived_corrections": sys.proc.n_corrections,
        "ingest_us_mean": mean(ing) / 1e3 if ing else float("nan"),
        "ingest_us_p50": _pct(ing, 50) / 1e3,
        "ingest_us_p95": _pct(ing, 95) / 1e3,
        "ingest_us_p99": _pct(ing, 99) / 1e3,
        "wrap_us_mean": mean(world.wrap_ns) / 1e3 if world.wrap_ns else float("nan"),
        "devsign_us_mean": mean(world.sign_dev_ns) / 1e3 if world.sign_dev_ns else 0.0,
        "wire_bytes_mean": mean(world.wire_bytes) if world.wire_bytes else float("nan"),
        "store_bytes": getattr(sys.store, "bytes_written", 0) + getattr(getattr(sys, "evidence", None), "bytes", 0),
    }
    res["store_bytes_per_reach"] = res["store_bytes"] / max(1, n_reach)
    if hasattr(sys, "reg") and hasattr(sys, "store"):
        # legit observations retained in quarantine (recoverable by explicit release), not authoritative
        import json as _json
        rec = set()
        for (ns, dg), blob in sys.store.blobs.items():
            if ns != "q" or dg not in sys.quarantined_wires:
                continue
            try:
                ob = _json.loads(blob)["obs"]
            except Exception:  # noqa: BLE001
                continue
            from .envelope import content_key as _ck
            ck = _ck(ob["did"], ob["aid"], ob["ts"], ob["sch"], ob["pl"])
            if ck in reach and auth.get(ck, 0) == 0:
                rec.add(ck)
        res_q = len(rec)
    else:
        res_q = 0
    res["legit_quarantined"] = res_q
    res["legit_lost_unrecoverable"] = res["legit_missing"] - res_q
    if hasattr(sys, "reg"):
        res["gaps_open"] = sum(es.open_gap_count() for st in sys.reg.streams.values() for es in st.epochs.values())
        res["gaps_closed"] = sum(hi - lo + 1 for st in sys.reg.streams.values() for es in st.epochs.values()
                                 for lo, hi in es.closed)
    if hasattr(sys, "recovery_latencies"):   # V3: quarantine review / feed-hold recovery
        lat = sorted(x[0] for x in sys.recovery_latencies)
        res["recovered_n"] = len(lat)
        res["recovery_ms_p50"] = _pct(lat, 50) if lat else 0.0
        res["recovery_ms_p95"] = _pct(lat, 95) if lat else 0.0
        res["recovery_ms_max"] = float(lat[-1]) if lat else 0.0
        for k, v in getattr(sys, "review_outcomes", {}).items():
            res["review[" + k.split(":")[0] + "]"] = res.get("review[" + k.split(":")[0] + "]", 0) + v
        res["holds"] = getattr(sys, "holds", 0)
        res["fork_events"] = getattr(sys, "fork_events", 0)
    legit_rx = {k: v for lab, d in world.receipts_by_label.items() if lab == "legit" for k, v in d.items()}
    res["legit_rx_rejected"] = sum(v for k, v in legit_rx.items() if k.startswith("REJECT"))
    res["legit_rx_conflict"] = sum(v for k, v in legit_rx.items() if k.startswith("CONFLICT"))
    res["legit_rx_quarantined"] = sum(v for k, v in legit_rx.items() if k.startswith("QUARANTINE"))
    if hasattr(sys, "slot_summary"):
        for k, v in sys.slot_summary().items():
            res["slots_" + k] = v
        res["taint_events"] = sys.taint_events
    for label, d in world.receipts_by_label.items():
        for k, v in d.items():
            res[f"rx[{label}]{k}"] = v
    return res
