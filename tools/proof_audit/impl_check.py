#!/usr/bin/env python3
"""Independent check of Proposition 1 (locality of Rule L) on the REAL implementation.

Drives the unmodified PBTIVerifier (and, for contrast, B5FeedLevel and SelectiveHoldVerifier) from a private working
copy of the repository (never the read-only original), with real Ed25519-signed statements built here from the
library's public constructors (as in tests/test_v4_oracle_traces.py). Written from the lemma statement; it does not
import or adapt formal/v4_locality_lifecycle_check.py.

Part R (random small histories, main configuration, no lifecycle transitions in between):
  statement universe: 2 devices x 2 epochs x q in 0..3; per identity q > 0 contents {G, F} x prev in
  {genuine predecessor digest, forged predecessor digest, null, a digest that names nothing}; q = 0: {G, F}, prev null.
  Each history: a random base delivered in random order, then a batch of k in {1,2,3} statements.
  Per identity in the universe: (V, I, class, authority, presence in derived processing, taint, lost) before/after.
  S' = batch statements the verifier admitted (receipt ACCEPT or CONFLICT, as the proof identifies admissions).
    R1 V and I change only on A(S')                     R2 class, authority, derived presence change only on A(S')
    R3 |A(S')| <= 2|S'| and #changed identities <= 2|S'|
    R4 registry V/I equal adm (written here) applied to every admitted statement; class equals Rule L on it
    R5 authority == COMMITTED and not tainted; derived presence == authority; authoritative() agrees
    R6 a receipt is ACCEPT/CONFLICT  <=>  the statement's digest was newly written into V(e)
    R7 no slot outside the universe is created
Part X (targeted scenarios): q = 0 with non-null prev; an ACCEPT receipt that contests its predecessor; the bound
  attained (k equivocations); distinct identities without 2k changes; reviewed release / failed release / reject /
  LOST release; and, expected to fall OUTSIDE the proposition because its hypothesis is violated, gap closure and
  revocation processing triggered inside ingest(); B5 and PBTI-SH authority (stated exclusions).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import random
import sys
import time
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True
REPO = Path("/home/claude/PBTI_v7/scratch/proof_audit/repo")   # private working copy
sys.path.insert(0, str(REPO / "src"))

from pbti.b5 import B5FeedLevel  # noqa: E402
from pbti.canonical import canonical_bytes  # noqa: E402
from pbti.crypto import b64u, keypair_from_seed, sha256, sha256_hex  # noqa: E402
from pbti.envelope import LogicalObs, pbti_sign_obs, pbti_wire  # noqa: E402
from pbti.identity import TrustRegistry  # noqa: E402
from pbti.policy import PolicyStore  # noqa: E402
from pbti.review import RELEASABLE, sign_decision  # noqa: E402
from pbti.selective import SelectiveHoldVerifier  # noqa: E402
from pbti.verifier import PBTIVerifier  # noqa: E402

SEED = b"proof-audit-independent-2026-11-05"
DEVS = ("devA", "devB")
EPOCHS = (0, 1)
QMAX = 3
FEEDS = [(d, p) for d in DEVS for p in EPOCHS]
IDS = [(d, p, q) for (d, p) in FEEDS for q in range(QMAX + 1)]
WID = "spiffe://plant-z.example/cellZ/gwZ/collector"
RID = "urn:pbti:reviewer:audit"
RAND_PREV = b64u(sha256(b"a digest that names no statement"))
ADMIT = ("ACCEPT", "CONFLICT")


class Stmt:
    __slots__ = ("wire", "wd", "cd", "e", "prev", "label")

    def __init__(self, wire, cd, e, prev, label):
        self.wire, self.cd, self.e, self.prev, self.label = wire, cd, e, prev, label
        self.wd = sha256_hex(wire)


class World:
    def __init__(self, params=None):
        self.dk = {d: keypair_from_seed(SEED, "device:" + d) for d in DEVS}
        self.wk = keypair_from_seed(SEED, "workload:Z")
        self.rk = keypair_from_seed(SEED, "reviewer:audit")
        self.vkeys = keypair_from_seed(SEED, "verifier-evidence")
        self.params = dict(params or {})
        self.U, self.at, self.G, self.F = [], {}, {}, {}
        for (d, p) in FEEDS:
            for q in range(QMAX + 1):
                e = (d, p, q)
                self.at[e] = []
                if q == 0:
                    for c in ("G", "F"):
                        s = self.sign(d, p, q, c, None, label=f"{d}/{p}/{q}/{c}/null")
                        self.at[e].append(s)
                        (self.G if c == "G" else self.F)[e] = s
                    continue
                links = {"gen": self.G[(d, p, q - 1)].cd, "alt": self.F[(d, p, q - 1)].cd, "null": None,
                         "rand": RAND_PREV}
                for c in ("G", "F"):
                    for name, pv in links.items():
                        s = self.sign(d, p, q, c, pv, label=f"{d}/{p}/{q}/{c}/{name}")
                        self.at[e].append(s)
                        if name == "gen":
                            (self.G if c == "G" else self.F)[e] = s
                self.U.extend(self.at[e])
            self.U.extend(self.at[(d, p, 0)])

    def sign(self, d, p, q, content, prev, ts=None, mode="live", label=""):
        ts = 100 + 10 * q + 5 * p if ts is None else ts
        val = {"G": 20.0, "F": 80.0}[content] + q + 0.5 * p
        o = LogicalObs(d, "asset-" + d, p, q, ts, "sch1", {"temp_c": val}, f"{d}/{p}/{q}/{content}", prev)
        obs, osig = pbti_sign_obs(o, self.dk[d][0], "kid:" + d)
        wire = pbti_wire(obs, osig, WID, "kid:wl", self.wk[0], ts, mode)
        cd = b64u(sha256(canonical_bytes(obs)))      # content digest recomputed from the canonical observation
        return Stmt(wire, cd, (d, p, q), prev, label)

    def verifier(self, kind="PBTI", params=None):
        tr = TrustRegistry(SEED, use_x509=False)
        for d in DEVS:
            tr.issue("kid:" + d, "device", d, self.dk[d][1], -10 ** 7, 10 ** 13)
        tr.issue("kid:wl", "workload", WID, self.wk[1], -10 ** 7, 10 ** 13)
        tr.issue("kid:rev", "reviewer", RID, self.rk[1], -10 ** 7, 10 ** 13)
        doc = {"devices": {d: {"assets": ["asset-" + d], "origin": "device", "schemas": ["sch1"]} for d in DEVS},
               "workloads": {WID: {"relay": list(DEVS)}}, "params": dict(self.params if params is None else params),
               "reviewers": {RID: {"may_release": list(RELEASABLE), "active": True}}}
        cls = {"PBTI": PBTIVerifier, "B5": B5FeedLevel, "PBTI-SH": SelectiveHoldVerifier}[kind]
        return tr, cls(tr, PolicyStore(doc), self.vkeys)


# --------------------------------------------------------------------------- independent model (lemma definitions)
def pred(e):
    return (e[0], e[1], e[2] - 1) if e[2] > 0 else None


def affected(stmts) -> set:
    a = set()
    for s in stmts:
        a.add(s.e)
        if s.e[2] > 0 and s.prev is not None:
            a.add(pred(s.e))
    return a


def model_evidence(stmts):
    V, I = {}, {}
    for s in stmts:
        V.setdefault(s.e, set()).add(s.cd)
        if s.e[2] > 0 and s.prev is not None:
            I.setdefault(pred(s.e), set()).add(s.prev)
    return V, I


def model_class(V, I, e):
    v = V.get(e, set())
    if not v:
        return "ABSENT"
    return "COMMITTED" if len(v | I.get(e, set())) == 1 else "CONTESTED"


# --------------------------------------------------------------------------- observation of the implementation
FIELDS = ("V", "I", "class", "auth", "derived", "tainted", "lost")


def snapshot(v, ids=IDS):
    out = {}
    for key in ids:
        s = v.reg.slots.get(key)
        if s is None:
            out[key] = (frozenset(), frozenset(), "ABSENT", False, key in v.proc.where, False, False)
        else:
            out[key] = (frozenset(s.versions), frozenset(s.implied or ()), s.state(), bool(v.is_authoritative(key, s)),
                        key in v.proc.where, bool(s.tainted), bool(s.lost))
    return out


def diff(before, after):
    """identity -> set of changed field names"""
    ch = {}
    for key in set(before) | set(after):
        a, b = before[key], after[key]
        f = {FIELDS[i] for i in range(len(FIELDS)) if a[i] != b[i]}
        if f:
            ch[key] = f
    return ch


def v_of(v, e):
    s = v.reg.slots.get(e)
    return frozenset(s.versions) if s is not None else frozenset()


def deliver(v, s, t):
    """ingest and report whether the statement's digest was newly written into V(e) (admission in the model sense)"""
    vb = v_of(v, s.e)
    r = v.ingest(s.wire, t)
    va = v_of(v, s.e)
    return r, (s.cd in va and s.cd not in vb)


# --------------------------------------------------------------------------- part R
class Stats:
    def __init__(self):
        self.batches = 0
        self.by_k = {}
        self.viol = Counter()
        self.examples = []
        self.disp = Counter()

    def k(self, k):
        if k not in self.by_k:
            self.by_k[k] = {"batches": 0, "hist_class_or_auth": Counter(), "hist_class": Counter(),
                            "hist_auth": Counter(), "hist_evidence": Counter(), "hist_A": Counter(),
                            "attained_2k_class_or_auth": 0, "max_class_or_auth": 0}
        return self.by_k[k]

    def bad(self, kind, info):
        self.viol[kind] += 1
        if len(self.examples) < 15:
            self.examples.append({"kind": kind, **info})

    def as_json(self):
        return {"batches": self.batches, "violations": dict(self.viol), "violation_examples": self.examples,
                "dispositions_in_batches": dict(self.disp),
                "by_k_admitted": {str(k): {kk: (dict(sorted(vv.items())) if isinstance(vv, Counter) else vv)
                                           for kk, vv in t.items()} for k, t in sorted(self.by_k.items())}}


def random_history(world: World, rng: random.Random):
    feeds = rng.sample(FEEDS, rng.randint(1, len(FEEDS)))
    base = []
    for (d, p) in feeds:
        for q in range(QMAX + 1):
            e = (d, p, q)
            x = rng.random()
            if x < 0.55:
                base.append(world.G[e])
            elif x < 0.75:
                base.append(rng.choice(world.at[e]))
            if rng.random() < 0.12:
                base.append(rng.choice(world.at[e]))
    rng.shuffle(base)
    pool = [s for (d, p) in feeds for q in range(QMAX + 1) for s in world.at[(d, p, q)]]
    k = rng.choice((1, 2, 3))
    batch = [rng.choice(pool) if rng.random() < 0.85 else rng.choice(world.U) for _ in range(k)]
    return base, batch


def classify_outside(before, after, ch, A):
    """Cause of each change outside A(S): gap closure (ABSENT -> LOST), revocation processing (taint), or none."""
    causes = Counter()
    for e, f in ch.items():
        if e in A:
            continue
        b, a = before[e], after[e]
        if f <= {"class", "lost"} and b[2] == "ABSENT" and a[2] == "LOST":
            causes["gap_closure"] += 1
        elif f <= {"tainted", "auth", "derived"} and a[5] and not b[5]:
            causes["revocation_taint"] += 1
        else:
            causes["unexplained"] += 1
    return causes


def r6(st, kind, h, s, r, wrote):
    """R6: the proof identifies admission with an ACCEPT/CONFLICT receipt. A mismatch is a defect of that
    identification; for B5 it is a known finding (FEED_FORK_HOLD receipts are issued after V and I were written)."""
    info = {"history": h, "stmt": s.label, "disp": f"{r.disp}/{r.why}", "wrote_V": wrote}
    if kind == "PBTI":
        st.bad("R6-disposition-vs-V-write", info)
    else:
        st.viol[f"(finding) receipts {r.disp}/{r.why.split(':')[0]} with V written={wrote}"] += 1
        if not any(x["kind"] == "disposition-vs-V-write" for x in st.examples):
            st.examples.append({"kind": "disposition-vs-V-write", **info})


def run_random(world: World, kind: str, n: int, seed: int, log, lifecycle: bool = False) -> dict:
    """lifecycle=False: main configuration, no lifecycle transition can occur (the proposition's hypothesis holds).
    lifecycle=True: gap_close_ms = 300 and, in 30% of histories, a revocation of devA's key (t_comp = 0) published
    just before the batch, which is delivered 2 s later: ingest() then runs gap closure / revocation processing
    inside the batch, i.e. the hypothesis is deliberately violated; every change outside A(S') is classified."""
    rng = random.Random(seed)
    st = Stats()
    t_start = time.time()
    n_ingest = 0
    causes_total = Counter()
    for h in range(n):
        base, batch = random_history(world, rng)
        tr, v = world.verifier(kind, params={"gap_close_ms": 300} if lifecycle else None)
        t = 1_000
        admitted_v = []                      # statements whose digest was newly written into V (model admission)
        admitted_d = []                      # statements with receipt ACCEPT or CONFLICT (proof's identification)
        for s in base:
            r, wrote = deliver(v, s, t)
            n_ingest += 1
            t += 37
            if wrote:
                admitted_v.append(s)
            if r.disp in ADMIT:
                admitted_d.append(s)
            if wrote != (r.disp in ADMIT):
                r6(st, kind, h, s, r, wrote)
        v.advance(t)
        before = snapshot(v)
        if lifecycle:
            if rng.random() < 0.3:
                tr.revoke("kid:devA", t + 1, 0, "audit")
            t += 2_000
        bv, bd, disps = [], [], []
        for s in batch:
            r, wrote = deliver(v, s, t)
            n_ingest += 1
            t += 37
            st.disp[f"{r.disp}/{r.why.split(':')[0]}"] += 1
            disps.append(f"{s.label}->{r.disp}/{r.why.split(':')[0]}")
            if wrote:
                bv.append(s)
            if r.disp in ADMIT:
                bd.append(s)
            if wrote != (r.disp in ADMIT):
                r6(st, kind, h, s, r, wrote)
        after = snapshot(v)
        ch = diff(before, after)
        # the proof identifies admissions by disposition for PBTI; for B5/PBTI-SH the model notion (V write) is used
        Sx = bd if kind == "PBTI" else bv
        A = affected(Sx)
        k = len(Sx)
        info = {"history": h, "base": [s.label for s in base], "batch": disps,
                "changed": {str(e): sorted(f) for e, f in ch.items()}, "A": sorted(map(str, A))}
        ev_out = [e for e, f in ch.items() if f & {"V", "I"} and e not in A]
        cl_out = [e for e, f in ch.items() if "class" in f and e not in A]
        au_out = [e for e, f in ch.items() if f & {"auth", "derived"} and e not in A]
        n_ca = sum(1 for f in ch.values() if f & {"class", "auth"})
        n_c = sum(1 for f in ch.values() if "class" in f)
        if ev_out:
            st.bad("R1-evidence-outside-A", info)
        if lifecycle:
            causes = classify_outside(before, after, ch, A)
            causes_total.update(causes)
            if causes.get("unexplained"):
                st.bad("R2-unexplained-change-outside-A", info)
            if causes:
                st.viol["(hypothesis violated) batches_with_lifecycle_change_outside_A"] += 1
        else:
            if cl_out:
                st.bad("R2-class-outside-A", info)
            if au_out:
                if kind == "PBTI":
                    st.bad("R2-authority-or-derived-outside-A", info)
                else:
                    st.viol["(expected, stated exclusion) batches_with_authority_change_outside_A"] += 1
                    st.viol["(expected, stated exclusion) identities_with_authority_change_outside_A"] += len(au_out)
                    if len(st.examples) < 15 and not any(x["kind"] == "expected-authority" for x in st.examples):
                        st.examples.append({"kind": "expected-authority", **info})
            if len(A) > 2 * k or (n_ca if kind == "PBTI" else n_c) > 2 * k:
                st.bad("R3-bound", info)
        # R4 conformance with the model over everything admitted so far
        V, I = model_evidence((admitted_d if kind == "PBTI" else admitted_v) + Sx)
        for e in IDS:
            Vi, Ii, cl = after[e][0], after[e][1], after[e][2]
            if Vi != frozenset(V.get(e, ())) or Ii != frozenset(I.get(e, ())):
                st.bad("R4-evidence-conformance", {**info, "identity": str(e)})
                break
            if cl != model_class(V, I, e) and not (cl == "LOST" and after[e][6] and model_class(V, I, e) == "ABSENT"):
                st.bad("R4-class-conformance", {**info, "identity": str(e)})
                break
        # R5 authority definition (PBTI only; B5/SH deliberately add holds)
        if kind == "PBTI":
            auth_set = {key for key, _ in v.authoritative()}
            for e in IDS:
                cl, au, de, ta = after[e][2], after[e][3], after[e][4], after[e][5]
                if au != (cl == "COMMITTED" and not ta) or de != au or (e in auth_set) != au:
                    st.bad("R5-authority-definition", {**info, "identity": str(e)})
                    break
        extra = set(v.reg.slots) - set(IDS)
        if extra:
            st.bad("R7-slot-outside-universe", {**info, "extra": sorted(map(str, extra))})
        st.batches += 1
        t_k = st.k(k)
        t_k["batches"] += 1
        t_k["hist_class_or_auth"][n_ca] += 1
        t_k["hist_class"][sum(1 for f in ch.values() if "class" in f)] += 1
        t_k["hist_auth"][sum(1 for f in ch.values() if "auth" in f)] += 1
        t_k["hist_evidence"][sum(1 for f in ch.values() if f & {"V", "I"})] += 1
        t_k["hist_A"][len(A)] += 1
        t_k["max_class_or_auth"] = max(t_k["max_class_or_auth"], n_ca)
        if k > 0 and n_ca == 2 * k:
            t_k["attained_2k_class_or_auth"] += 1
    out = st.as_json()
    out.update({"verifier": kind, "histories": n, "seed": seed, "ingests": n_ingest, "lifecycle_active": lifecycle,
                "causes_of_changes_outside_A": dict(causes_total), "seconds": round(time.time() - t_start, 1)})
    log(f"[R:{kind}] {n} histories, {n_ingest} ingests, {out['seconds']} s; violations {dict(st.viol)}; "
        + "; ".join(f"k'={k}: n={t['batches']}, max changed={t['max_class_or_auth']}, 2k' attained="
                    f"{t['attained_2k_class_or_auth']}" for k, t in sorted(st.by_k.items())))
    return out


# --------------------------------------------------------------------------- part X: targeted scenarios
def scen_q0_prev(world, log):
    tr, v = world.verifier()
    s = world.sign("devA", 0, 0, "G", RAND_PREV, label="devA/0/0/G/rand")
    b = snapshot(v)
    r = v.ingest(s.wire, 1_000)
    ch = diff(b, snapshot(v))
    res = {"receipt": f"{r.disp}/{r.why}", "changed": {str(e): sorted(f) for e, f in ch.items()}}
    log(f"[X1] q=0 with non-null prev: {res}")
    return res


def scen_accept_contests_pred(world, log):
    tr, v = world.verifier()
    g0 = world.G[("devA", 0, 0)]
    f1 = next(s for s in world.at[("devA", 0, 1)] if s.label.endswith("/F/rand"))
    v.ingest(g0.wire, 1_000)
    b = snapshot(v)
    r = v.ingest(f1.wire, 1_100)
    a = snapshot(v)
    res = {"receipt": f"{r.disp}/{r.why}", "slot1": a[("devA", 0, 1)][2:5], "slot0_before": b[("devA", 0, 0)][2:5],
           "slot0_after": a[("devA", 0, 0)][2:5],
           "changed": {str(e): sorted(f) for e, f in diff(b, a).items()}, "A": sorted(map(str, affected([f1])))}
    log(f"[X2] ACCEPT receipt that contests its predecessor: {res}")
    return res


def scen_tightness(world, log):
    rows = []
    targets = [(d, p, q) for (d, p) in FEEDS for q in (1, 3)]
    for k in range(1, len(targets) + 1):
        tr, v = world.verifier()
        t = 1_000
        for e in IDS:
            v.ingest(world.G[e].wire, t)
            t += 20
        v.advance(t)
        b = snapshot(v)
        S = [next(s for s in world.at[e] if s.label.endswith("/F/alt")) for e in targets[:k]]
        disp = []
        for s in S:
            disp.append(v.ingest(s.wire, t).disp)
            t += 20
        a = snapshot(v)
        ch = diff(b, a)
        rows.append({"k": k, "A": len(affected(S)), "receipts": dict(Counter(disp)),
                     "class_or_auth_changed": sum(1 for f in ch.values() if f & {"class", "auth"}),
                     "authority_withdrawn": sum(1 for e in ch if b[e][3] and not a[e][3]),
                     "outside_A": sum(1 for e in ch if e not in affected(S))})
    log("[X3] bound attained (k equivocations, prev = forged predecessor, non-adjacent q): "
        + ", ".join(f"k={r['k']}: A={r['A']} changed={r['class_or_auth_changed']} withdrawn={r['authority_withdrawn']}"
                    for r in rows))
    return rows


def scen_distinct_not_sufficient(world, log):
    tr, v = world.verifier()
    b = snapshot(v)
    S = [world.G[("devA", 0, 1)], world.G[("devA", 0, 3)]]
    disp = [v.ingest(s.wire, 1_000 + 10 * i).disp for i, s in enumerate(S)]
    a = snapshot(v)
    ch = diff(b, a)
    res = {"receipts": disp, "A": len(affected(S)), "class_changed": sum(1 for f in ch.values() if "class" in f),
           "evidence_changed": sum(1 for f in ch.values() if f & {"V", "I"}),
           "changed": {str(e): sorted(f) for e, f in ch.items()}}
    log(f"[X4] pairwise distinct A(S) but fewer than 2k class changes: {res}")
    return res


def review(v, wd, t, decision, world):
    snap = v.open_review(wd, RID, t)
    d = sign_decision({"case": wd, "reviewer": RID, "rkid": "kid:rev", "decision": decision, "reason": "AUDIT",
                       "snapshot": snap, "t": t}, world.rk[0])
    return v.apply_review(d, t)["outcome"]


def scen_release(world, log):
    res = {}
    # (a) STALE_TS quarantine, then RELEASE: re-run admission
    w = World({"h_max_ms": 10_000})
    tr, v = w.verifier()
    g0, g1 = w.G[("devA", 0, 0)], w.G[("devA", 0, 1)]
    v.ingest(g0.wire, 1_000)
    r = v.ingest(g1.wire, 20_000)
    b = snapshot(v)
    out = review(v, g1.wd, 20_500, "RELEASE", w)
    a = snapshot(v)
    ch = diff(b, a)
    res["release_stale_ts"] = {"quarantine": f"{r.disp}/{r.why}", "outcome": out,
                               "changed": {str(e): sorted(f) for e, f in ch.items()},
                               "outside_A": [str(e) for e in ch if e not in affected([g1])]}
    # (b) failed release: the released version conflicts with a committed one
    tr, v = w.verifier()
    f1 = w.F[("devA", 0, 1)]
    v.ingest(g0.wire, 1_000)
    v.ingest(g1.wire, 1_100)
    r = v.ingest(f1.wire, 20_000)
    b = snapshot(v)
    out = review(v, f1.wd, 20_500, "RELEASE", w)
    a = snapshot(v)
    ch = diff(b, a)
    res["release_conflict"] = {"quarantine": f"{r.disp}/{r.why}", "outcome": out,
                               "changed": {str(e): sorted(f) for e, f in ch.items()},
                               "outside_A": [str(e) for e in ch if e not in affected([f1])]}
    # (c) REJECT decision: an operation on the case only
    tr, v = w.verifier()
    v.ingest(g0.wire, 1_000)
    v.ingest(g1.wire, 20_000)
    b = snapshot(v)
    out = review(v, g1.wd, 20_500, "REJECT", w)
    res["reject"] = {"outcome": out, "changed": {str(e): sorted(f) for e, f in diff(b, snapshot(v)).items()}}
    # (c') STALE_REVIEW: new successor evidence after the snapshot; the decision is refused, registry untouched
    tr, v = w.verifier()
    g2 = w.sign("devA", 0, 2, "G", g1.cd, ts=20_000, label="devA/0/2/G/gen-fresh")
    v.ingest(g0.wire, 1_000)
    v.ingest(g1.wire, 20_000)
    snap = v.open_review(g1.wd, RID, 20_100)
    r2 = v.ingest(g2.wire, 20_200)
    b = snapshot(v)
    d = sign_decision({"case": g1.wd, "reviewer": RID, "rkid": "kid:rev", "decision": "RELEASE", "reason": "AUDIT",
                       "snapshot": snap, "t": 20_300}, w.rk[0])
    out = v.apply_review(d, 20_300)["outcome"]
    res["stale_review"] = {"successor": f"{r2.disp}/{r2.why}", "outcome": out, "case_state": v.qcases[g1.wd]["state"],
                           "changed": {str(e): sorted(f) for e, f in diff(b, snapshot(v)).items()}}
    # (d) LOST slot released (STALE_SLOT waived)
    w2 = World({"gap_close_ms": 2_000})
    tr, v = w2.verifier()
    g0, g1, g2 = (w2.G[("devA", 0, q)] for q in (0, 1, 2))
    v.ingest(g0.wire, 1_000)
    v.ingest(g2.wire, 1_100)
    v.advance(5_000)
    lost_cls = snapshot(v)[("devA", 0, 1)][2]
    r = v.ingest(g1.wire, 5_100)
    b = snapshot(v)
    out = review(v, g1.wd, 5_200, "RELEASE", w2)
    a = snapshot(v)
    ch = diff(b, a)
    res["release_lost"] = {"class_after_gap_closure": lost_cls, "arrival": f"{r.disp}/{r.why}", "outcome": out,
                           "changed": {str(e): sorted(f) for e, f in ch.items()},
                           "outside_A": [str(e) for e in ch if e not in affected([g1])]}
    log(f"[X5] reviewed release paths: {json.dumps(res)}")
    return res


def scen_gap_closure_inside_ingest(world, log):
    """Hypothesis violated on purpose: a delivery whose ingest() runs a tick that closes an old gap."""
    w = World({"gap_close_ms": 2_000})
    tr, v = w.verifier()
    v.ingest(w.G[("devA", 0, 0)].wire, 1_000)
    v.ingest(w.G[("devA", 0, 3)].wire, 1_100)            # opens the gap [1, 2]; creates slot (devA,0,2) via prev
    v.advance(1_200)
    b = snapshot(v)
    s = w.G[("devB", 0, 0)]
    r = v.ingest(s.wire, 6_000)                           # ingest() first advances time: tick closes the gap
    a = snapshot(v)
    ch = diff(b, a)
    res = {"receipt": f"{r.disp}/{r.why}", "A": sorted(map(str, affected([s]))),
           "changed": {str(e): sorted(f) for e, f in ch.items()},
           "outside_A": {str(e): (b[e][2], a[e][2]) for e in ch if e not in affected([s])},
           "lost_declared_counter": v.lost_declared,
           "slots_in_closed_range": {q: (("devA", 0, q) in v.reg.slots) for q in (1, 2)}}
    log(f"[X6] gap closure inside ingest (expected outside the proposition): {res}")
    return res


def scen_revocation_inside_ingest(world, log):
    """Hypothesis violated on purpose: a revocation becomes visible and is processed inside ingest()."""
    tr, v = world.verifier()
    t = 1_000
    for q in range(QMAX + 1):
        v.ingest(world.G[("devA", 0, q)].wire, t)
        t += 50
    v.advance(2_000)
    b = snapshot(v)
    tr.revoke("kid:devA", 2_500, 0, "audit")              # compromise since 0
    s = world.G[("devB", 0, 0)]
    r = v.ingest(s.wire, 3_000)
    a = snapshot(v)
    ch = diff(b, a)
    res = {"receipt": f"{r.disp}/{r.why}", "A": sorted(map(str, affected([s]))),
           "outside_A": {str(e): sorted(f) for e, f in ch.items() if e not in affected([s])}}
    log(f"[X7] revocation processing inside ingest (expected outside the proposition): {res}")
    return res


def scen_b5_hold_receipt(world, log):
    tr, v = world.verifier("B5")
    t = 1_000
    for q in range(3):
        v.ingest(world.G[("devA", 0, q)].wire, t)
        t += 50
    f1 = world.F[("devA", 0, 1)]
    r1 = v.ingest(f1.wire, t)
    b = snapshot(v)
    g3 = world.G[("devA", 0, 3)]
    vb = v_of(v, g3.e)
    r = v.ingest(g3.wire, t + 50)
    a = snapshot(v)
    res = {"fork_receipt": f"{r1.disp}/{r1.why}", "receipt": f"{r.disp}/{r.why}",
           "V_written": g3.cd in v_of(v, g3.e) and g3.cd not in vb,
           "I_pred_after": len(a[("devA", 0, 2)][1]),
           "changed": {str(e): sorted(f) for e, f in diff(b, a).items()}}
    log(f"[X8] B5: QUARANTINE/FEED_FORK_HOLD receipt that writes V and I: {res}")
    return res


def sources():
    h = {}
    for p in sorted((REPO / "src" / "pbti").glob("*.py")):
        h[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
    return h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "results" / "impl_check.json"))
    ap.add_argument("--n", type=int, default=600, help="random histories for PBTIVerifier")
    ap.add_argument("--n-contrast", type=int, default=200, help="random histories for B5 and PBTI-SH")
    ap.add_argument("--seed", type=int, default=20261105)
    a = ap.parse_args()
    lines = []

    def log(m):
        print(m, flush=True)
        lines.append(m)

    t0 = time.time()
    src0 = sources()
    world = World()
    log(f"universe: {len(world.U)} signed statements over {len(IDS)} identities ({time.time() - t0:.1f}s)")
    res = {"python": platform.python_version(), "repo_copy": str(REPO), "source_sha256": src0,
           "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "statements": len(world.U)}
    res["R_PBTI"] = run_random(world, "PBTI", a.n, a.seed, log)
    res["R_B5"] = run_random(world, "B5", a.n_contrast, a.seed + 1, log)
    res["R_PBTI_SH"] = run_random(world, "PBTI-SH", a.n_contrast, a.seed + 2, log)
    res["R_PBTI_lifecycle_active"] = run_random(world, "PBTI", a.n_contrast, a.seed + 3, log, lifecycle=True)
    res["X1_q0_nonnull_prev"] = scen_q0_prev(world, log)
    res["X2_accept_contests_predecessor"] = scen_accept_contests_pred(world, log)
    res["X3_bound_attained"] = scen_tightness(world, log)
    res["X4_distinct_not_sufficient"] = scen_distinct_not_sufficient(world, log)
    res["X5_release_paths"] = scen_release(world, log)
    res["X6_gap_closure_inside_ingest"] = scen_gap_closure_inside_ingest(world, log)
    res["X7_revocation_inside_ingest"] = scen_revocation_inside_ingest(world, log)
    res["X8_b5_hold_receipt_writes_evidence"] = scen_b5_hold_receipt(world, log)
    res["source_unchanged_during_run"] = sources() == src0
    res["seconds_total"] = round(time.time() - t0, 1)
    def real(r):          # counters whose name starts with "(" are labelled expected effects or findings
        return sum(v for k, v in r["violations"].items() if not k.startswith("("))
    pbti_viol = real(res["R_PBTI"]) + real(res["R_PBTI_lifecycle_active"])
    res["unexpected_violations"] = {k: real(res[k]) for k in ("R_PBTI", "R_PBTI_lifecycle_active", "R_B5",
                                                              "R_PBTI_SH")}
    res["pbti_violations"] = pbti_viol
    res["log"] = lines
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=1, default=str))
    log(f"PBTI violations {pbti_viol}; total {res['seconds_total']} s -> {a.out}")
    return 0 if pbti_viol == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
