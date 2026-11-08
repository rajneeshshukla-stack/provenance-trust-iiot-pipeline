"""Independent reference implementation (oracle audit) of O1, O2, NLX, withheld record-seconds / W, AVd and
Kaplan-Meier first availability.

Written from the metric definitions in paper/main.tex ("Metrics", "Time-dependent outcomes (V4)") and the
supplementary definitions table (Table S22), NOT from src/pbti/oracle.py or src/pbti/temporal.py. This module
imports nothing from the pbti package.

Inputs
  legit   : list of ground-truth observations, one dict each:
              t_prod  production time (ms, virtual)
              t_acc   first gateway acceptance time (ms) or None if no gateway ever accepted it
              content content identity (did, aid, ts, sch, normalised payload) -- see `content()`
              pairs   set of (identity, content) under which an honest gateway wrapped it
  history : intervals per authoritative (identity, content) pair: {(key, content): [(a, b), ...]}, b > a,
            zero-length episodes already removed (they are counted separately by the capture tool)
  end_auth: set of (key, content) pairs authoritative at T_end (pipeline state after finalize)
  t_end   : end of the observation interval (production + drain), ms
"""
from __future__ import annotations

from collections import Counter


def content(did, aid, ts, sch, pl) -> tuple:
    """Content identity independent of the repository's canonical encoder: numbers are compared as floats
    (5 and 5.0 are the same value, as in RFC 8785), keys in sorted order."""
    def norm(v):
        if isinstance(v, bool):
            return ("b", v)
        if isinstance(v, (int, float)):
            return ("n", float(v))
        if isinstance(v, dict):
            return ("d", tuple(sorted((k, norm(x)) for k, x in v.items())))
        if isinstance(v, (list, tuple)):
            return ("l", tuple(norm(x) for x in v))
        return ("s", v)
    return (did, aid, int(ts), sch, norm(pl))


def _union(ivs):
    out = []
    for a, b in sorted(ivs):
        if out and a <= out[-1][1]:
            if b > out[-1][1]:
                out[-1][1] = b
        else:
            out.append([a, b])
    return out


def _len_within(ivs, lo, hi):
    tot = 0
    for a, b in ivs:
        a2, b2 = max(a, lo), min(b, hi)
        if b2 > a2:
            tot += b2 - a2
    return tot


def km_quantile(times, events, q):
    """Product-limit estimator. S(t) = prod_{t_i <= t} (1 - d_i / n_i), with n_i the number at risk just before
    t_i (censored at t_i still at risk at t_i: events precede censorings at tied times). Returns the smallest
    observed event time t with 1 - S(t) >= q, or None when the curve never reaches q."""
    distinct = sorted(set(times))
    n_at_risk = len(times)
    by_t = {}
    for t, e in zip(times, events):
        d, c = by_t.get(t, (0, 0))
        by_t[t] = (d + (1 if e else 0), c + (0 if e else 1))
    s = 1.0
    for t in distinct:
        d, c = by_t[t]
        if d:
            s *= (1.0 - d / n_at_risk)
            if 1.0 - s >= q - 1e-12:
                return t
        n_at_risk -= d + c
    return None


def compute(legit, history, end_auth, t_end, all_produced_contents=None):
    """Returns a dict of reference metrics; keys mirror the repository's names where a counterpart exists."""
    res = {}
    L = [o for o in legit if o["t_acc"] is not None]          # population: accepted by a gateway
    honest_pairs = set()
    for o in L:
        honest_pairs |= o["pairs"]
    produced = all_produced_contents if all_produced_contents is not None else {o["content"] for o in legit}
    # ------------------------------------------------------------------ final-state outcomes
    end_contents = Counter(c for (_k, c) in end_auth)
    res["O1_content"] = sum(n for c, n in end_contents.items() if c not in produced)     # oracle definition
    res["O1_pair"] = sum(1 for p in end_auth if p not in honest_pairs)                    # pair-based variant
    reach = Counter(o["content"] for o in L)
    present = sum(min(end_contents.get(c, 0), n) for c, n in reach.items())
    res["O2_content"] = len(L) - present                                                  # oracle definition
    res["O2_pair"] = sum(1 for o in L if not (o["pairs"] & end_auth))                     # pair-based variant
    res["n_reachable"] = len(L)
    res["n_produced"] = len(legit)
    # ------------------------------------------------------------------ non-legitimate exposure
    nl = {p: v for p, v in history.items() if p not in honest_pairs}
    res["NLX_s"] = sum(_len_within(v, 0, t_end) for v in nl.values()) / 1000.0
    res["nl_pairs_ever"] = len(nl)
    res["nl_auth_end"] = sum(1 for p in end_auth if p not in honest_pairs)
    # ------------------------------------------------------------------ withheld time and first availability
    wh = 0
    dl = {1: 0, 5: 0, 30: 0, 60: 0}
    never = withdrawn = withdrawn_end = 0
    km_t, km_e = [], []
    for o in L:
        u = _union([iv for p in o["pairs"] for iv in history.get(p, ())])
        avail = _len_within(u, o["t_acc"], t_end)
        wh += (t_end - o["t_acc"]) - avail
        if u:
            ft = u[0][0] - o["t_prod"]
            km_t.append(ft)
            km_e.append(1)
            for d in dl:
                if ft <= d * 1000:
                    dl[d] += 1
            ends_before = u[-1][1] < t_end
            if len(u) > 1 or ends_before:
                withdrawn += 1
            if ends_before:
                withdrawn_end += 1
        else:
            never += 1
            km_t.append(t_end - o["t_prod"])
            km_e.append(0)
    n = max(1, len(L))
    res["withheld_s"] = wh / 1000.0
    res["W_s"] = res["withheld_s"] / n
    for d in dl:
        res[f"AV{d}"] = dl[d] / n
    res["never"] = never
    res["withdrawn"] = withdrawn
    res["withdrawn_end"] = withdrawn_end
    for q, name in ((0.5, "KM50_s"), (0.9, "KM90_s"), (0.99, "KM99_s")):
        v = km_quantile(km_t, km_e, q)
        res[name] = None if v is None else v / 1000.0
    return res


def intervals_from_transitions(trans, t_end):
    """trans: [(t, key, old_content, new_content)] in non-decreasing t (old/new None = absent).
    Returns ({pair: [(a, b)]}, zero_count, end_pairs)."""
    open_ = {}
    out = {}
    zero = 0
    for (t, key, old, new) in trans:
        if old is not None:
            t0 = open_.pop((key, old), None)
            if t0 is not None:
                if t > t0:
                    out.setdefault((key, old), []).append((t0, t))
                else:
                    zero += 1
        if new is not None:
            open_[(key, new)] = t
    for p, t0 in open_.items():
        if t_end > t0:
            out.setdefault(p, []).append((t0, t_end))
        else:
            zero += 1
    return out, zero, set(open_)
