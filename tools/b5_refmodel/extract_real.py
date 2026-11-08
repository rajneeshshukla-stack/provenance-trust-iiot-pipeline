"""Real scenario runs (src/pbti/scenarios.py, the paper's testbed) with B5 as implemented, instrumented from
outside: every receipt and every periodic review tick is logged in processing order with the real disposition;
the authority timeline is polled after every event.  The admitted-statement stream is then extracted and fed to
the reference model with exactly the same event order, and the two are compared.

usage: python3 extract_real.py S05_stolen_key 1 hist  [out.json]
"""
from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness as H  # noqa: E402  (sets sys.path to the scratch repository)
import refmodel as M  # noqa: E402
from pbti.canonical import canonical_bytes  # noqa: E402
from pbti.crypto import b64u, sha256, sha256_hex  # noqa: E402
from pbti.envelope import pbti_parse  # noqa: E402
from pbti.scenarios import build  # noqa: E402

ARMS = {  # world kwargs, model params
    "hist": ({}, M.Params.hist()),
    "B5S": ({}, M.Params.strict()),
    "event": ({"review_mode": "event", "review_delay_ms": 0, "review_rule": "defer"}, M.Params.event()),
    "d0c1": ({"review_delay_ms": 0, "review_every_ms": 1000, "review_rule": "defer"}, M.Params.defer(0, 1)),
}
PASS_DISP = ("ACCEPT", "CONFLICT", "DUPLICATE")
Q_RELEASABLE = ("STALE_TS", "STALE_SLOT", "STALE_EPOCH", "REVOKED_BUFFERED")


def run(scen, seed, arm):
    kw, P = ARMS[arm]
    system = "B5S" if arm == "B5S" else "B5"
    w = build(scen, system, seed, **kw)
    v = w.sys
    events, last, decisions, resumes = [], [None], [], []
    held_ever = set()

    hold_transitions = [0]

    class RecordingSet(set):
        def add(self, k):
            held_ever.add(k)
            if k not in self:
                hold_transitions[0] += 1          # slot goes from not-held to held
            super().add(k)
    v.held = RecordingSet()
    orig_ingest = v.ingest

    def ingest(wire, t, meta=None, waive=frozenset(), log=True):
        r = orig_ingest(wire, t, meta, waive=waive, log=log)
        if not waive:
            last[0] = r
        return r
    v.ingest = ingest
    orig_apply = v.apply_review

    def apply_review(d, t):
        out = orig_apply(d, t)
        c = v.qcases.get(d["case"])
        decisions.append((t, d["decision"], out["outcome"], c["reason"] if c else None,
                          tuple(c["eid"]) if c else None, d["snapshot"]["cd"]))
        dirty_feeds.add(tuple(c["eid"][:2]) if c else None)
        return out
    v.apply_review = apply_review
    orig_resume = v._maybe_resume

    def maybe_resume(feed, t):
        had = feed in v.fork
        orig_resume(feed, t)
        if had and feed not in v.fork:
            resumes.append((t, tuple(feed)))
    v._maybe_resume = maybe_resume

    # authority polling: per dirty feed (receipt feed, decided cases' feeds, feeds in new registry state events)
    cur, timeline = {}, []
    dirty_feeds = set()
    ev_n = [0]

    def feed_auth(feed):
        did, ep = feed
        out = set()
        for sq in v.feed_seqs.get(feed, ()):
            k = (did, ep, sq)
            s = v.reg.slots.get(k)
            if s is not None and s.obs_first is not None and v.is_authoritative(k, s):
                out.add((k, s.first_cd()))
        return out

    def poll(t, feeds):
        se = v.reg.state_events
        for x in se[ev_n[0]:]:
            if isinstance(x[1], tuple) and len(x[1]) == 3:
                feeds.add(x[1][:2])
        ev_n[0] = len(se)
        for f in feeds:
            if f is None:
                continue
            now = feed_auth(f)
            old = cur.get(f, set())
            for k in sorted(now - old):
                timeline.append((t, k[0], k[1], True, "real"))
            for k in sorted(old - now):
                timeline.append((t, k[0], k[1], False, "real"))
            cur[f] = now
        feeds.clear()

    def full_check():
        allf = set(v.feed_seqs)
        return sum(1 for f in allf if feed_auth(f) != cur.get(f, set()))

    orig_receive = w.receive

    def receive(wire, meta, label):
        last[0] = None
        orig_receive(wire, meta, label)
        r = last[0]
        try:
            obs = pbti_parse(wire)[0]
            feed = (obs["did"], obs["ep"])
        except Exception:  # noqa: BLE001
            obs, feed = None, None
        events.append(("A", w.now, wire, label, r.disp if r else None, r.why if r else None, obs))
        dirty_feeds.add(feed)
        poll(w.now, dirty_feeds)
    w.receive = receive
    if w.reviewer is not None and P.mode == "periodic":
        orig_run = w.reviewer.run

        def rrun(vv, t):
            out = orig_run(vv, t)
            events.append(("T", t))
            poll(t, dirty_feeds)
            return out
        w.reviewer.run = rrun
    t0 = time.perf_counter()
    w.run()
    wall = time.perf_counter() - t0
    t_end = w.cfg.duration_ms + w.cfg.drain_ms
    poll(t_end, set(v.feed_seqs))
    mism = full_check()
    v.hold_transitions = hold_transitions[0]
    return w, v, P, events, timeline, decisions, resumes, held_ever, t_end, wall, mism


def extract(events, P):
    """Admitted-statement stream for the model, in the real processing order."""
    model_events, n_in, skipped = [], 0, {}
    receipts = []
    for e in events:
        if e[0] == "T":
            model_events.append(("T", e[1]))
            continue
        _, t, wire, label, disp, why, obs = e
        if obs is None or disp is None:
            skipped["MALFORMED"] = skipped.get("MALFORMED", 0) + 1
            continue
        reason = (why or "").split(":")[0]
        if disp in PASS_DISP or (disp == "QUARANTINE" and reason == "FEED_FORK_HOLD"):
            q = None
        elif disp == "QUARANTINE" and reason in Q_RELEASABLE:
            q = reason
        else:
            skipped[disp + "/" + reason] = skipped.get(disp + "/" + reason, 0) + 1
            continue
        cd = b64u(sha256(canonical_bytes(obs)))
        s = M.Stmt(int(t), obs["did"], obs["ep"], obs["seq"], cd, obs["prev"], q, sha256_hex(wire))
        model_events.append(("A", s))
        receipts.append((s, label))
        n_in += 1
    return model_events, receipts, n_in, skipped


def compare_real(scen, seed, arm, out_path=None):
    w, v, P, events, timeline, decisions, resumes, held_ever, t_end, wall, mism = run(scen, seed, arm)
    model_events, receipts, n_in, skipped = extract(events, P)
    tainted_feeds = {tuple(x[1][:2]) for x in v.reg.state_events if str(x[4]).startswith("REVOCATION")}
    legit = {((s.did, s.ep, s.seq), s.digest) for s, label in receipts if label in ("legit", "legit-dup")}
    stmts = [x for k, x in model_events if k == "A"]
    real = {"t_end": t_end, "intervals": M.authority_intervals(timeline, t_end), "timeline": timeline,
            "decisions": decisions, "resumes": resumes, "held_identities": sorted(held_ever),
            "authoritative": sorted({k for f in v.feed_seqs for k in _auth(v, f)}),
            "counters": {"holds": v.holds, "fork_events": v.fork_events, "resumed_feeds": v.resumed_feeds}}
    res = {"scenario": scen, "seed": seed, "arm": arm, "receipts": sum(1 for e in events if e[0] == "A"),
           "model_stmts": n_in, "skipped": skipped, "ticks": sum(1 for e in events if e[0] == "T"),
           "world_wall_s": round(wall, 1), "incremental_poll_mismatch_feeds": mism,
           "tainted_feeds_excluded": sorted(map(list, tainted_feeds)), "review_outcomes": dict(v.review_outcomes),
           "counters_real": real["counters"], "hold_transitions_real": v.hold_transitions,
           "distinct_held_slots_real": len(held_ever)}
    IMPL = dict(order="identity", fork_rule="state", contested_cases=False, resume_timing="decision",
                wire_cases=True, event_scope="impl")
    variants = [("spec", P), ("impl", P.impl_choices())]
    for sw, val in IMPL.items():
        variants.append(("spec+" + sw, M.replace(P, **{sw: val})))
        rest = dict(IMPL)
        rest.pop(sw)
        variants.append(("impl-" + sw, M.replace(P, **rest)))
    for variant, PP in variants:
        m = M.run(stmts, PP, t_end=t_end, legit=legit, events=model_events)
        res[variant] = _cmp(m, real, legit, tainted_feeds, t_end, receipts)
        if variant == "impl":
            res["counters_impl_model"] = m["impl_counters"]
            res["release_failed_impl_model"] = [(t, list(e), k, r) for t, e, cd, k, r in m["release_failed"]][:50]
    res["n_legit_reachable"] = sum(1 for k in legit if tuple(k[0][:2]) not in tainted_feeds)
    if out_path:
        with open(out_path, "a") as fh:
            fh.write(json.dumps(res, default=str) + "\n")
    return res


def _auth(v, feed):
    did, ep = feed
    for sq in v.feed_seqs.get(feed, ()):
        k = (did, ep, sq)
        s = v.reg.slots.get(k)
        if s is not None and s.obs_first is not None and v.is_authoritative(k, s):
            yield (k, s.first_cd())


def _cmp(m, real, legit, excl, t_end, receipts):
    def keep(k):
        return tuple(k[0][:2]) not in excl
    fa = {}
    for s, _ in receipts:
        fa.setdefault(((s.did, s.ep, s.seq), s.digest), s.t)
    mi = {k: x for k, x in m["intervals"].items() if keep(k)}
    ri = {k: x for k, x in real["intervals"].items() if keep(k)}
    diff = sorted(k for k in set(mi) | set(ri) if mi.get(k, []) != ri.get(k, []))

    def W(iv):
        return sum(M.withheld_ms(iv.get(k, []), fa[k], t_end) for k in legit if k in fa and keep(k))

    def AV5(iv):
        ks = [k for k in legit if k in fa and keep(k)]
        ok = sum(1 for k in ks if iv.get(k) and iv[k][0][0] - fa[k] <= 5_000)
        return round(ok / max(1, len(ks)), 5)

    def NLX(iv):
        return sum(sum(b - a for a, b in iv.get(k, [])) for k in fa if k not in legit and keep(k))
    m_rel = sorted((t, e, cd) for t, e, cd, _ in m["releases"] if tuple(e[:2]) not in excl)
    r_rel = sorted((t, e, cd) for t, d, o, r, e, cd in real["decisions"] if d == "RELEASE" and tuple(e[:2]) not in excl)
    fin_m = {k for k in m["authoritative"] if keep(k)}
    fin_r = {tuple((tuple(k[0]), k[1])) for k in real["authoritative"] if keep(k)}
    feeds_diff = sorted({tuple(k[0][:2]) for k in diff})
    return {"final_equal": fin_m == fin_r, "final_model_only": len(fin_m - fin_r), "final_real_only": len(fin_r - fin_m),
            "intervals_equal": not diff, "n_pairs_diff": len(diff), "feeds_diff": [list(f) for f in feeds_diff],
            "W_model_s": round(W(mi) / 1000, 1), "W_real_s": round(W(ri) / 1000, 1),
            "NLX_model_s": round(NLX(mi) / 1000, 1), "NLX_real_s": round(NLX(ri) / 1000, 1),
            "AV5_model": AV5(mi), "AV5_real": AV5(ri),
            "nonlegit_final_model": sum(1 for k in fin_m if k not in legit),
            "nonlegit_final_real": sum(1 for k in fin_r if k not in legit),
            "releases_equal": m_rel == r_rel, "n_rel_model": len(m_rel), "n_rel_real": len(r_rel),
            "resumes_model": len([x for x in m["resumes"] if tuple(x[1]) not in excl]),
            "resumes_real": len([x for x in real["resumes"] if tuple(x[1]) not in excl]),
            "legit_missing_model": sum(1 for k in legit if k in fa and keep(k) and k not in fin_m),
            "legit_missing_real": sum(1 for k in legit if k in fa and keep(k) and k not in fin_r)}


if __name__ == "__main__":
    scen, seed, arm = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    out = sys.argv[4] if len(sys.argv) > 4 else None
    r = compare_real(scen, seed, arm, out)
    print(json.dumps({k: r[k] for k in r if k not in ("skipped",)}, default=str))
