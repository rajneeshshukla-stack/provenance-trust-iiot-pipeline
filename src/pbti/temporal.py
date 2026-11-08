"""V4 time-dependent outcomes (memo R06/A2): authoritative-state transition trace and temporal metrics.

Unit of analysis. A(t) is the set of authoritative pairs (event identity, content key) at time t; the content key
(device, asset, timestamp, schema, canonical payload) is the oracle's content identity (src/pbti/envelope.py). A
legitimate observation (one ground-truth record) is AVAILABLE at t if some pair under which an honest gateway wrapped
it is in A(t); a forged content under the same identity is a different pair, so it never counts as availability of
the genuine observation. A pair in A(t) that no honest gateway produced is NON-LEGITIMATE.

Population and interval. L(t) is the set of legitimate observations accepted by a gateway at or before t (first
acceptance time `t_acc`). All integrals are taken over the fixed interval [0, T_end], T_end = production phase +
drain, in simulated (virtual) time; normalised values divide by T_end. Each run yields one value per metric: the run,
not the timestamp or the observation, is the experimental unit.

Zero-duration changes (a pair that enters and leaves A at the same timestamp) contribute nothing to integrals and do
not count as availability, first availability or withdrawal; they are counted separately (`tm_zero_flips`).

The Tracer observes the pipeline from outside: it wraps `ingest`, `_tick`, `apply_review` and `finalize` and, after
each call, re-evaluates authority only for identities the call can have touched (the receipt's identity and its
predecessor, identities in new registry state events, the decided review case). It never changes pipeline state;
attack labels stay outside the pipeline (the oracle side uses the World's ground truth).
"""
from __future__ import annotations

import bisect
import math
from collections import defaultdict
from typing import Optional

from .canonical import canonical_bytes
from .crypto import b64u, sha256
from .envelope import content_key, pbti_parse

DEADLINES_S = (1, 5, 30, 60)          # predeclared deadlines for first availability (PREREGISTRATION_V4)
ALERT_DELTA_C = 2.5                   # monitoring workload: alert when temp_c > nominal + 2.5 degC
ALERT_DEADLINE_S = 5                  # a true alert is missed if not raised within 5 s of production
FRESH_STEP_S = 1                      # freshness sampling step


# ============================================================================ tracer (attached to a World)
class Tracer:
    def __init__(self, world):
        self.w = world
        self.sys = sys_ = world.sys
        self.status: dict = {}            # key -> (ck, cd, kid) while authoritative
        self.log: list[tuple] = []        # (t, key, old_ck, new_ck, cd, kid)
        self.receipts: dict = defaultdict(list)   # eid -> [(t, cd, prev, label)]
        self._ev = 0
        self._ck_cache: dict = {}
        if hasattr(sys_, "reg"):
            self._auth = self._auth_pbti_family
        elif hasattr(sys_, "silver") and hasattr(sys_, "digest"):
            self._auth = self._auth_b4
        else:
            raise ValueError(f"temporal tracing is not defined for pipeline {type(sys_).__name__}")
        for name in ("ingest", "_tick", "apply_review", "finalize"):
            if hasattr(sys_, name):
                setattr(sys_, name, self._wrap(name, getattr(sys_, name)))

    # -- authority adapters
    def _auth_pbti_family(self, key):
        s = self.sys.reg.slots.get(key)
        if s is None or s.obs_first is None or not self.sys.is_authoritative(key, s):
            return None
        ck = self._ck_cache.get(key)
        if ck is None:
            o = s.obs_first
            ck = self._ck_cache[key] = content_key(o["did"], o["aid"], o["ts"], o["sch"], o["pl"])
        return ck, s.first_cd(), s.kid

    def _auth_b4(self, key):
        v = self.sys.silver.get(key)
        if v is None:
            return None
        ck, obs, _ref = v
        return ck, self.sys.digest.get(key), obs.get("kid")

    # -- wrappers
    def _wrap(self, name, fn):
        def wrapped(*a, **kw):
            r = fn(*a, **kw)
            t = a[1] if name in ("ingest", "apply_review") else (a[0] if a else kw.get("t"))
            cand = set()
            if name == "ingest":
                cand |= _eid_and_pred(a[0])
            elif name == "apply_review":
                case = self.sys.qcases.get(a[0].get("case")) if hasattr(self.sys, "qcases") else None
                if case and case.get("eid"):
                    did, ep, sq = case["eid"]
                    cand |= {(did, ep, sq), (did, ep, sq - 1)}
            self.flush(int(t), cand)
            return r
        return wrapped

    def note_receipt(self, t: int, wire: bytes, label: str) -> None:
        try:
            obs = pbti_parse(wire)[0]
            cd = b64u(sha256(canonical_bytes(obs)))
        except Exception:  # noqa: BLE001
            return
        self.receipts[(obs["did"], obs["ep"], obs["seq"])].append((t, cd, obs.get("prev"), label))

    def flush(self, t: int, cand: set) -> None:
        reg = getattr(self.sys, "reg", None)
        if reg is not None and len(reg.state_events) != self._ev:
            for ev in reg.state_events[self._ev:]:
                cand.add(ev[1])
            self._ev = len(reg.state_events)
        for key in cand:
            new = self._auth(key)
            old = self.status.get(key)
            if (new and new[0]) != (old and old[0]):
                self.log.append((t, key, old[0] if old else None, new[0] if new else None,
                                 (new or old)[1], (new or old)[2]))
                if new is None:
                    self.status.pop(key, None)
                else:
                    self.status[key] = new

    def end_state(self) -> set:
        return {(k, v[0]) for k, v in self.status.items()}


def _eid_and_pred(wire) -> set:
    try:
        o = pbti_parse(wire)[0]
    except Exception:  # noqa: BLE001
        return set()
    return {(o["did"], o["ep"], o["seq"]), (o["did"], o["ep"], o["seq"] - 1)}


# ============================================================================ metric computation (pure functions)
def intervals_from_log(log: list[tuple], t_end: int) -> dict:
    """pair (key, ck) -> list of [start, end) intervals with end > start (zero-length intervals dropped and counted)."""
    cur: dict = {}
    out: dict = defaultdict(list)
    zero = 0
    for (t, key, old, new, *_rest) in log:
        if old is not None:
            t0 = cur.pop(key, None)
            if t0 is not None:
                if t > t0[0]:
                    out[(key, old)].append((t0[0], t))
                else:
                    zero += 1
        if new is not None:
            cur[key] = (t, new)
    for key, (t0, ck) in cur.items():
        if t_end > t0:
            out[(key, ck)].append((t0, t_end))
        else:
            zero += 1
    return {"iv": dict(out), "zero": zero}


def _union(ivs: list) -> list:
    out = []
    for a, b in sorted(ivs):
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def _measure(ivs: list, lo: int, hi: int) -> int:
    return sum(max(0, min(b, hi) - max(a, lo)) for a, b in ivs)


def _available_at(ivs: list, t: int) -> bool:
    i = bisect.bisect_right([a for a, _ in ivs], t) - 1
    return i >= 0 and ivs[i][0] <= t < ivs[i][1]


def kaplan_meier_quantiles(times: list, events: list, qs=(0.5, 0.9, 0.99)) -> dict:
    """Product-limit estimate of the distribution of time to first availability with right censoring.
    times: observed time (event time or censoring time); events: 1 = became available, 0 = censored.
    Returns q -> smallest t with F(t) >= q, or None if the estimate never reaches q (censored tail)."""
    pts = sorted(zip(times, events))
    n = len(pts)
    surv = 1.0
    out = {q: None for q in qs}
    i = 0
    while i < n:
        t = pts[i][0]
        d = c = 0
        while i < n and pts[i][0] == t:
            if pts[i][1]:
                d += 1
            else:
                c += 1
            i += 1
        at_risk = n - (i - d - c)
        if d:
            surv *= 1 - d / at_risk
        for q in qs:
            if out[q] is None and 1 - surv >= q - 1e-12:
                out[q] = t
    return out


def compute(log, legit: list, t_end: int, receipts: Optional[dict] = None, revocations=(), windows=None,
            nominal: Optional[dict] = None) -> dict:
    """legit: one dict per reachable legitimate observation with keys
         pairs (set of (eid, ck)), t_prod, t_acc, aid, temp (float or None)
       receipts: eid -> [(t, cd, prev, label)]; revocations: [(t_rev, kid, t_comp)];
       windows: {wk: [version dicts with "t" and "ckeys"]} from the processor; nominal: aid -> nominal temperature.
    All times in ms; durations reported in seconds."""
    res: dict = {}
    ivr = intervals_from_log(log, t_end)
    iv, res["tm_zero_flips"] = ivr["iv"], ivr["zero"]
    legit_pairs = set()
    for o in legit:
        legit_pairs |= o["pairs"]
    legit_cks = {ck for _, ck in legit_pairs}
    T = t_end / 1000.0
    # ---------------------------------------------------------------- non-legitimate exposure
    nl = {p: v for p, v in iv.items() if p not in legit_pairs}
    nl_ms = sum(_measure(v, 0, t_end) for v in nl.values())
    res["tm_nl_rec_s"] = nl_ms / 1000.0
    res["tm_nl_rec_norm"] = res["tm_nl_rec_s"] / T
    res["tm_nl_pairs_ever"] = len(nl)
    res["tm_nl_auth_end"] = sum(1 for v in nl.values() if v[-1][1] == t_end)
    # ---------------------------------------------------------------- legitimate availability
    wh_ms = 0
    first = []
    km_t, km_e = [], []
    dl = {d: 0 for d in DEADLINES_S}
    never = withdrawn = withdrawn_end = 0
    avail_of = []
    for o in legit:
        u = _union([x for p in o["pairs"] for x in iv.get(p, ())])
        avail_of.append(u)
        t_acc = o["t_acc"]
        wh_ms += (t_end - t_acc) - _measure(u, t_acc, t_end)
        if u:
            ft = u[0][0] - o["t_prod"]
            first.append(ft)
            km_t.append(ft)
            km_e.append(1)
            for d in DEADLINES_S:
                if ft <= d * 1000:
                    dl[d] += 1
            if len(u) > 1 or u[-1][1] < t_end:
                withdrawn += 1
            if u[-1][1] < t_end:
                withdrawn_end += 1
        else:
            never += 1
            km_t.append(t_end - o["t_prod"])
            km_e.append(0)
    n = max(1, len(legit))
    res["tm_reach"] = len(legit)
    res["tm_wh_rec_s"] = wh_ms / 1000.0
    res["tm_wh_rec_norm"] = res["tm_wh_rec_s"] / T
    for d in DEADLINES_S:
        res[f"tm_avail_{d}s"] = dl[d] / n
    res["tm_never_avail"] = never
    res["tm_withdrawn"] = withdrawn
    res["tm_withdrawn_end"] = withdrawn_end
    km = kaplan_meier_quantiles(km_t, km_e)
    for q, v in km.items():
        res[f"tm_first_km_p{int(round(q * 1000)) / 10:g}_s".replace(".", "_")] = (v / 1000.0) if v is not None else None
    # ---------------------------------------------------------------- correct-data freshness (per asset, 1 s samples)
    by_asset = defaultdict(list)
    for o, u in zip(legit, avail_of):
        by_asset[o["aid"]].append((o["t_prod"], u))
    stale, missing, samples = [], 0, 0
    for aid, items in by_asset.items():
        items.sort(key=lambda x: x[0])
        prods = [x[0] for x in items]
        for tau in range(FRESH_STEP_S * 1000, t_end, FRESH_STEP_S * 1000):   # [step, T_end): intervals are half-open
            j = bisect.bisect_right(prods, tau) - 1
            if j < 0:
                continue
            samples += 1
            latest = prods[j]
            k = j
            while k >= 0 and not _available_at(items[k][1], tau):
                k -= 1
            if k < 0:
                missing += 1
            else:
                stale.append(latest - prods[k])
    res["tm_fresh_samples"] = samples
    res["tm_fresh_missing_frac"] = missing / samples if samples else 0.0
    res["tm_fresh_stale_mean_s"] = (sum(stale) / len(stale) / 1000.0) if stale else 0.0
    res["tm_fresh_stale_p95_s"] = (sorted(stale)[min(len(stale) - 1, int(0.95 * len(stale)))] / 1000.0) if stale else 0.0
    res["tm_fresh_stale_frac"] = (sum(1 for s in stale if s > 0) / samples) if samples else 0.0
    # ---------------------------------------------------------------- containment of non-legitimate episodes
    rev_by_kid = defaultdict(list)
    for (t_rev, kid, t_comp) in revocations:
        rev_by_kid[kid].append((t_rev, t_comp))
    cd_of = {}
    kid_of = {}
    for (t, key, old, new, cd, kid) in log:
        if new is not None:
            cd_of[(key, new)] = cd
            kid_of[(key, new)] = kid
    lat, undirected = [], 0
    contained = 0
    for p, v in nl.items():
        key, ck = p
        for a, b in v:
            if b >= t_end:
                continue
            contained += 1
            tx = None
            cdp = cd_of.get(p)
            if receipts is not None:
                for (tr, cd, prev, _l) in receipts.get(key, ()):        # another content for the same identity
                    if tr >= a and cd != cdp:
                        tx = tr if tx is None else min(tx, tr)
                        break
                if isinstance(key, tuple) and len(key) == 3:            # a successor whose prev contradicts it
                    for (tr, cd, prev, _l) in receipts.get((key[0], key[1], key[2] + 1), ()):
                        if tr >= a and prev is not None and prev != cdp:
                            tx = tr if tx is None else min(tx, tr)
                            break
            for (t_rev, t_comp) in rev_by_kid.get(kid_of.get(p), ()):
                if t_comp is not None and t_rev >= a:
                    tx = t_rev if tx is None else min(tx, t_rev)
            if tx is None or tx > b:
                undirected += 1
            else:
                lat.append(b - tx)
    res["tm_nl_contained"] = contained
    res["tm_nl_contained_undirected"] = undirected
    res["tm_contain_lat_med_s"] = (sorted(lat)[len(lat) // 2] / 1000.0) if lat else None
    res["tm_contain_lat_max_s"] = (max(lat) / 1000.0) if lat else None
    # ---------------------------------------------------------------- derived outputs (processor window versions)
    if windows is not None:
        dw_ms = 0
        for wk, vers in windows.items():
            for i, ver in enumerate(vers):
                t0 = ver["t"]
                t1 = vers[i + 1]["t"] if i + 1 < len(vers) else t_end
                if any(c not in legit_cks for c in ver["ckeys"]):
                    dw_ms += max(0, min(t1, t_end) - t0)
        # time from containment of a non-legitimate input to the first derived version without it, for windows whose
        # latest version at containment time contained it (censored if no later version is emitted before T_end)
        win_of_ck = defaultdict(set)
        for wk, vers in windows.items():
            for ver in vers:
                for c in ver["ckeys"]:
                    if c not in legit_cks:
                        win_of_ck[c].add(wk)
        corr, cens = [], 0
        for p, v in nl.items():
            c = p[1]
            for a, b in v:
                if b >= t_end:
                    continue
                for wk in win_of_ck.get(c, ()):
                    vers = windows[wk]
                    ts_ = [x["t"] for x in vers]
                    i = bisect.bisect_left(ts_, b) - 1      # latest version emitted strictly before containment
                    if i < 0 or c not in vers[i]["ckeys"]:
                        continue
                    nxt = next((x["t"] for x in vers[i + 1:] if c not in x["ckeys"]), None)
                    if nxt is None:
                        cens += 1
                    else:
                        corr.append(nxt - b)
        res["tm_dw_nl_s"] = dw_ms / 1000.0
        res["tm_dw_corr_n"] = len(corr)
        res["tm_dw_corr_censored"] = cens
        res["tm_dw_corr_lat_med_s"] = (sorted(corr)[len(corr) // 2] / 1000.0) if corr else None
        res["tm_dw_corr_lat_max_s"] = (max(corr) / 1000.0) if corr else None
    # ---------------------------------------------------------------- monitoring workload (temperature alerts)
    if nominal is not None:
        true_alerts = missed = retract_true = 0
        for o, u in zip(legit, avail_of):
            th = nominal.get(o["aid"])
            if th is None or o.get("temp") is None or o["temp"] <= th + ALERT_DELTA_C:
                continue
            true_alerts += 1
            if not u or u[0][0] - o["t_prod"] > ALERT_DEADLINE_S * 1000:
                missed += 1
            if u and (len(u) > 1 or u[-1][1] < t_end):
                retract_true += 1
        false_alerts = retract_false = false_open = 0
        for p, v in nl.items():
            key, ck = p
            temp = _temp_of_ck(ck)
            aid = ck[1]
            th = nominal.get(aid)
            if th is None or temp is None or temp <= th + ALERT_DELTA_C:
                continue
            false_alerts += 1
            if v[-1][1] < t_end:
                retract_false += 1
            else:
                false_open += 1
        res["tm_alert_true"] = true_alerts
        res["tm_alert_missed"] = missed
        res["tm_alert_retract_true"] = retract_true
        res["tm_alert_false"] = false_alerts
        res["tm_alert_false_retracted"] = retract_false
        res["tm_alert_false_open_end"] = false_open
    return res


def _temp_of_ck(ck) -> Optional[float]:
    """content key = (did, aid, ts, sch, canonical payload bytes)."""
    import json
    try:
        pl = json.loads(ck[4])
        v = pl.get("temp_c")
        return float(v) if isinstance(v, (int, float)) else None
    except Exception:  # noqa: BLE001
        return None


# ============================================================================ glue: metrics for a finished World
def temporal_metrics(world) -> dict:
    tr = world.tracer
    if tr is None:
        return {}
    t_end = world.cfg.duration_ms + world.cfg.drain_ms
    legit = []
    for rec in world.truth:
        o = rec["o"]
        if not o.meta.get("gw_accepted"):
            continue
        eids = o.meta.get("eids") or []
        legit.append({"pairs": {(tuple(e), rec["ck"]) for e in eids}, "t_prod": rec["t"],
                      "t_acc": o.meta.get("t_acc", rec["t"]), "aid": rec["aid"],
                      "temp": rec["pl"].get("temp_c") if isinstance(rec["pl"], dict) else None})
    nominal = {d.aid: d.base_t for d in world.devices.values()} if world.devices else None
    if nominal and not all(isinstance(r["pl"], dict) and "temp_c" in r["pl"] for r in world.truth[:50]):
        nominal = None                       # monitoring workload defined for the synthetic temperature channel only
    res = compute(tr.log, legit, t_end, receipts=tr.receipts, revocations=world.revocations,
                  windows=world.sys.proc.versions, nominal=nominal)
    # consistency with the oracle's end state (pairs vs content keys)
    end = tr.end_state()
    auth = set(world.sys.authoritative())
    res["tm_end_state_matches_authoritative"] = end == {(k, ck) for k, ck in auth}
    res["tm_transitions"] = len(tr.log)
    return res
