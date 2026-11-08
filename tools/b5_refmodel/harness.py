"""Phase-2 differential harness: the same logical stream through (a) the real B5 implementation (real signed
statements, real B5FeedLevel verifier, real AutoReviewer, real event-driven review code of sim.World, simulated
time) and (b) the reference model (refmodel.py), and a field-by-field comparison.

The repository copy used is /home/claude/PBTI_v7/scratch/b5_refmodel/repo (never the read-only original).
"""
from __future__ import annotations

import os
import sys
import types
from dataclasses import dataclass

REPO = os.environ.get("B5_REPO", "/home/claude/PBTI_v7/scratch/b5_refmodel/repo")
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pbti.b5 import B5FeedLevel                                    # noqa: E402
from pbti.crypto import b64u, keypair_from_seed, sha256, sha256_hex  # noqa: E402
from pbti.envelope import LogicalObs, pbti_content_digest, pbti_sign_obs, pbti_wire  # noqa: E402
from pbti.identity import TrustRegistry                            # noqa: E402
from pbti.policy import PolicyStore                                # noqa: E402
from pbti.review import RELEASABLE, AutoReviewer                   # noqa: E402
from pbti.sim import World                                         # noqa: E402

import refmodel as M                                               # noqa: E402

SEED = b"b5-refmodel-diff"
WID = "spiffe://plant-a.example/cell1/gw1/collector"
WKID = "wk:g1:1"
RID, RKID = "urn:pbti:reviewer:auto", "rk:auto:1"


class Env:
    """Keys and policy for a set of devices (one relay workload, one automated reviewer)."""
    _cache: dict = {}

    def __init__(self, devices, h_max_ms=20_000):
        self.devices = list(devices)
        self.h_max_ms = h_max_ms
        self.trust = TrustRegistry(SEED, use_x509=False)
        self.dsk = {}
        for did in self.devices:
            sk, pk = keypair_from_seed(SEED, f"dk:{did}:1")
            self.trust.issue(f"dk:{did}:1", "device", did, pk, -60_000, 10 ** 12)
            self.dsk[did] = sk
        self.wsk, wpk = keypair_from_seed(SEED, WKID)
        self.trust.issue(WKID, "workload", WID, wpk, -60_000, 10 ** 12)
        self.rsk, rpk = keypair_from_seed(SEED, RKID)
        self.trust.issue(RKID, "reviewer", RID, rpk, -60_000, 10 ** 12)
        self.doc = {"devices": {d: {"assets": [f"a-{d}"], "origin": "device", "schemas": ["s"]} for d in self.devices},
                    "workloads": {WID: {"relay": list(self.devices)}},
                    "params": {"h_max_ms": h_max_ms},
                    "reviewers": {RID: {"may_release": list(RELEASABLE), "active": True}}}
        self.vkeys = keypair_from_seed(SEED, "verifier")


def fake_digest(tag: str) -> str:
    return b64u(sha256(("ext:" + tag).encode()))


@dataclass
class Built:
    env: Env
    wires: dict          # (name, wrap) -> wire bytes
    cd: dict             # name -> content digest
    prev_cd: dict        # name -> prev digest
    stmt: dict           # name -> statement spec
    model_stmts: list    # M.Stmt in arrival order (stable)
    wire_of_arrival: list
    legit: list          # (e, cd) of legitimate statements
    t_end: int


def build(spec: dict) -> Built:
    """spec = {devices, h_max_ms, stmts:[{name,did,ep,seq,ts,prev,val,legit}], arrivals:[(t,name,wrap,mode)], t_end}"""
    env = Env(spec["devices"], spec.get("h_max_ms", 20_000))
    cd, prev_cd, obs_of, stmt = {}, {}, {}, {}
    for s in spec["stmts"]:
        p = s["prev"]
        if p is None:
            pd = None
        elif isinstance(p, dict):
            pd = fake_digest(p["ext"])
        else:
            pd = cd[p]
        o = LogicalObs(s["did"], f"a-{s['did']}", s["ep"], s["seq"], s["ts"], "s", {"x": s["val"]}, s["name"], pd)
        obs, osig = pbti_sign_obs(o, env.dsk[s["did"]], f"dk:{s['did']}:1")
        cd[s["name"]] = b64u(pbti_content_digest(obs))
        prev_cd[s["name"]] = pd
        obs_of[s["name"]] = (obs, osig)
        stmt[s["name"]] = s
    wires, model_stmts, woa = {}, [], []
    arr = sorted(enumerate(spec["arrivals"]), key=lambda x: (x[1][0], x[0]))
    for _, (t, name, wrap, mode) in arr:
        if stmt[name]["seq"] == 0 and prev_cd[name] is not None:
            continue          # the shared parser rejects it (MALFORMED: prev at epoch start): never admitted
        key = (name, wrap)
        if key not in wires:
            obs, osig = obs_of[name]
            rts = stmt[name]["ts"] + 10 * wrap
            wires[key] = pbti_wire(obs, osig, WID, WKID, env.wsk, rts, mode)
        s = stmt[name]
        q = "STALE_TS" if t - s["ts"] > env.h_max_ms else None
        model_stmts.append(M.Stmt(int(t), s["did"], s["ep"], s["seq"], cd[name], prev_cd[name], q,
                                  sha256_hex(wires[key])))
        woa.append(wires[key])
    legit = [((s["did"], s["ep"], s["seq"]), cd[s["name"]]) for s in spec["stmts"] if s.get("legit")]
    return Built(env, wires, cd, prev_cd, stmt, model_stmts, woa, legit, int(spec["t_end"]))


# ------------------------------------------------------------------------------------------- real B5
def _auth_set(v):
    out = set()
    for key, s in v.reg.slots.items():
        if s.obs_first is not None and v.is_authoritative(key, s):
            out.add((key, s.first_cd()))
    return out


def run_real(b: Built, P: M.Params, events=None):
    env = b.env
    v = B5FeedLevel(env.trust, PolicyStore(env.doc), env.vkeys, recovery=P.recovery)
    rv = None
    if P.recovery:
        rv = AutoReviewer(RID, RKID, env.rsk, min_age_ms=P.R_ms, rule=P.rule)
    decisions, resumes = [], []
    ever_held = set()

    class RecordingSet(set):
        def add(self, k):
            ever_held.add(k)
            super().add(k)
    v.held = RecordingSet()
    orig_apply = v.apply_review

    def apply_review(d, t):
        out = orig_apply(d, t)
        c = v.qcases.get(d["case"])
        decisions.append((t, d["decision"], out["outcome"], c["reason"] if c else None,
                          tuple(c["eid"]) if c else None, d["snapshot"]["cd"]))
        return out
    v.apply_review = apply_review
    orig_resume = v._maybe_resume

    def maybe_resume(feed, t):
        had = feed in v.fork
        orig_resume(feed, t)
        if had and feed not in v.fork:
            resumes.append((t, tuple(feed)))
    v._maybe_resume = maybe_resume
    drv = None
    if P.recovery and P.mode == "event":
        drv = types.SimpleNamespace(sys=v, reviewer=rv, now=0, _ci_n=0, _case_idx={}, _ev_n=0, event_review_rounds=0)
        drv._event_touched = types.MethodType(World._event_touched, drv)
        drv._event_pending = types.MethodType(World._event_pending, drv)
    wire_by_stmt = {id(s): w for s, w in zip(b.model_stmts, b.wire_of_arrival)}
    if events is None:
        events = M.schedule(b.model_stmts, P, b.t_end)
    timeline, cur, disps = [], set(), []
    first_arrival = {}
    for kind, x in events:
        if kind == "T":
            t = x
            if rv is not None and P.mode == "periodic":
                rv.run(v, t)
        else:
            t = x.t
            first_arrival.setdefault(((x.did, x.ep, x.seq), x.digest), t)
            w = wire_by_stmt[id(x)]
            r = v.ingest(w, t, {"tid": WID})
            disps.append((t, (x.did, x.ep, x.seq), x.digest, r.disp + "/" + r.why.split(":")[0]))
            if drv is not None:
                drv.now = t
                World._event_review(drv, w)
        now = _auth_set(v)
        for k in sorted(now - cur):
            timeline.append((t, k[0], k[1], True, "real"))
        for k in sorted(cur - now):
            timeline.append((t, k[0], k[1], False, "real"))
        cur = now
    v.advance(b.t_end)
    now = _auth_set(v)
    for k in sorted(now - cur):
        timeline.append((b.t_end, k[0], k[1], True, "real"))
    for k in sorted(cur - now):
        timeline.append((b.t_end, k[0], k[1], False, "real"))
    iv = M.authority_intervals(timeline, b.t_end)
    res = {"t_end": b.t_end, "authoritative": sorted(now), "timeline": timeline, "intervals": iv,
           "held_identities": sorted(ever_held), "decisions": decisions, "resumes": resumes,
           "dispositions": disps, "first_arrival": first_arrival,
           "counters": {"holds": v.holds, "fork_events": v.fork_events, "resumed_feeds": v.resumed_feeds},
           "pending": sorted((c["reason"], tuple(c["eid"])) for c in v.qcases.values()
                             if c["state"] not in ("RELEASED", "REJECTED")),
           "review_outcomes": dict(v.review_outcomes)}
    _add_legit_metrics(res, b)
    return res


def _add_legit_metrics(res, b: Built):
    legit = set(b.legit)
    fa = res["first_arrival"]
    iv = res["intervals"]
    t_end = b.t_end
    reach = [k for k in legit if k in fa]
    res["withheld_ms"] = {k: M.withheld_ms(iv.get(k, []), fa[k], t_end) for k in reach}
    res["W_ms_total"] = sum(res["withheld_ms"].values())
    res["reachable"] = len(reach)
    nl = [k for k in fa if k not in legit]
    res["nlx_ms_total"] = sum(sum(max(0, min(bb, t_end) - a) for a, bb in iv.get(k, [])) for k in nl)
    auth = set(res["authoritative"])
    res["legit_missing"] = sorted(k for k in reach if k not in auth)
    res["nonlegit_auth"] = sorted(k for k in nl if k in auth)


def run_model(b: Built, P: M.Params, events=None):
    return M.run(b.model_stmts, P, t_end=b.t_end, legit=b.legit, events=events)


# ------------------------------------------------------------------------------------------- comparison
def _real_releases(real):
    return sorted((t, e, cd) for t, dec, out, reason, e, cd in real["decisions"] if dec == "RELEASE")


def _real_rejections(real):
    return sorted((t, e, cd) for t, dec, out, reason, e, cd in real["decisions"] if dec == "REJECT")


def compare(model, real) -> dict:
    """Field-by-field comparison; True means equal."""
    mi, ri = model["intervals"], real["intervals"]
    keys = set(mi) | set(ri)
    iv_diff = sorted(k for k in keys if mi.get(k, []) != ri.get(k, []))
    m_rel = sorted((t, e, cd) for t, e, cd, _ in model["releases"])
    m_rej = sorted((t, e, cd) for t, e, cd, _ in model["rejections"])
    out = {
        "final": set(model["authoritative"]) == set(real["authoritative"]),
        "intervals": not iv_diff,
        "W": model["W_ms_total"] == real["W_ms_total"],
        "NLX": model["nlx_ms_total"] == real["nlx_ms_total"],
        "held_ids": set(model["held_identities"]) == set(real["held_identities"]),
        "releases": m_rel == _real_releases(real),
        "rejections": m_rej == _real_rejections(real),
        "resumes": sorted(model["resumes"]) == sorted(real["resumes"]),
    }
    out["all_core"] = out["final"] and out["intervals"]
    out["n_iv_diff"] = len(iv_diff)
    out["iv_diff_sample"] = [(list(k[0]), k[1][:8], mi.get(k, []), ri.get(k, [])) for k in iv_diff[:3]]
    out["dW_ms"] = model["W_ms_total"] - real["W_ms_total"]
    out["dNLX_ms"] = model["nlx_ms_total"] - real["nlx_ms_total"]
    out["d_missing"] = len(model["legit_missing"]) - len(real["legit_missing"])
    out["d_nonlegit"] = len(model["nonlegit_auth"]) - len(real["nonlegit_auth"])
    return out


def counters_match(model, real) -> bool:
    return model["impl_counters"] == real["counters"]
