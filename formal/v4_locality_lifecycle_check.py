#!/usr/bin/env python3
"""V4 (memo R07/A4): locality lemma checks and bounded lifecycle combinations for Rule L.

Three parts, kept separate from the proof (formal/LOCALITY_PROOF.md), which does not depend on them:

  M  model, exhaustive: a mathematical transition model of the evidence maps V (admitted versions) and I (implied
     digests), independent of the implementation. For every base set B of a statement universe and every batch S of
     one or two further statements: the slots whose class changes are contained in A(S) = {e(s)} U {pred(e(s))}
     (prev present, seq > 0), |A(S)| <= 2|S|, CONTESTED is absorbing, and both application orders give equal maps.
     Universes: U1 = one epoch, seq 0..2, contents {G, F}, prev in {G, F, null} (14 statements);
                U2 = two epochs, seq 0..1, contents {G, F}, prev in {G, F} (12 statements).
  L  implementation locality: the unmodified PBTIVerifier with real Ed25519 signatures on U2 (every base set B,
     delivered in sorted order, and every single further statement) and a seeded random sample of batches of two or
     three statements over U1 and U2; per slot (Rule L class, authoritative, present in derived processing) before
     and after the batch; changes must lie in A(S') where S' are the batch statements the verifier admitted
     (disposition ACCEPT or CONFLICT). Statements it did not admit are counted as admission-set differences.
  C  bounded lifecycle combinations on the unmodified verifier: every operation sequence of length <= 4 over a
     13-symbol alphabet (7 deliveries over two epochs including a forged alternative and a rotated-key statement,
     gap closure, revocation with early or late compromise time, reviewed release with a fresh or a stale snapshot,
     rejection), plus a seeded random sample of longer sequences (length 5..8). Invariants after every operation:
       C1 evidence conformance: registry V/I equal the evidence of the statements the verifier admitted
          (receipt ACCEPT or CONFLICT, including re-runs of admission inside a release), and Rule L classes equal
          the specification evaluated on that evidence (LOST only for slots without versions after gap closure)
       C2 contest is absorbing across all operations
       C3 authority: authoritative <=> COMMITTED and not TAINTED; derived processing holds exactly the
          authoritative slots
       C4 taint exactness: after a revocation (kid, t_comp) is processed, a slot is TAINTED iff its origin key is
          revoked and its commit time is >= t_comp and it was COMMITTED when the revocation was processed
       C5 ordinary admission under a revoked key never happens; a revoked-key statement is admitted only by a
          RELEASED review decision
       C6 release: RELEASED implies the re-run admission returned ACCEPT; a failed release leaves no authority
       C7 stale snapshot: a decision on a superseded snapshot is refused (STALE_REVIEW), the case returns to
          QUARANTINED and the registry is unchanged by the decision
       C8 locality of every delivery operation (as in part L)
       C9 rotation: a statement under an expired key is admitted only within the rotation grace period

Bounds and exclusions are reported in the JSON summary. These are bounded checks, not proofs.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import platform
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "src"))

from pbti.crypto import b64u, keypair_from_seed, sha256_hex  # noqa: E402
from pbti.envelope import LogicalObs, pbti_content_digest, pbti_sign_obs, pbti_wire  # noqa: E402
from pbti.identity import TrustRegistry  # noqa: E402
from pbti.policy import PolicyStore  # noqa: E402
from pbti.registry import ABSENT, COMMITTED, CONTESTED, LOST  # noqa: E402
from pbti.review import RELEASABLE, sign_decision  # noqa: E402
from pbti.verifier import ACCEPT, CONFLICT, PBTIVerifier  # noqa: E402

SEED = b"v4-locality-lifecycle"
DID, AID, SCH = "d1", "a1", "s"
WID = "spiffe://plant-a.example/cell1/gw1/collector"
RID = "urn:pbti:reviewer:auto"


# ============================================================================ part M: the mathematical model
def model_universe(epochs, seqs, prevs_null: bool):
    """Abstract statements (ep, seq, content, prev) with prev = (content of seq-1) or None."""
    U = []
    for ep in epochs:
        for q in seqs:
            for c in ("G", "F"):
                if q == 0:
                    U.append((ep, q, c, None))
                else:
                    for p in ("G", "F") + ((None,) if prevs_null else ()):
                        U.append((ep, q, c, p))
    return U


def digest_of(ep, q, c, p):
    return (ep, q, c, p)            # the statement itself is its digest in the model


def ref_statement(ep, q, c):
    """The statement a prev link names: content c of slot (ep, q) whose own prev names G (as in impl_universe)."""
    return (ep, q, c, None) if q == 0 else (ep, q, c, "G")


def model_apply(V, I, s):
    """One admission: V(e) gains the statement's digest; I(pred e) gains the digest its prev link names."""
    ep, q, c, p = s
    V = dict(V)
    I = dict(I)
    V[(ep, q)] = V.get((ep, q), frozenset()) | {digest_of(*s)}
    if q > 0 and p is not None:
        I[(ep, q - 1)] = I.get((ep, q - 1), frozenset()) | {digest_of(*ref_statement(ep, q - 1, p))}
    return V, I


def model_class(V, I, e):
    """Rule L (lifecycle-free): ABSENT without a version, else COMMITTED iff |V(e) u I(e)| = 1, else CONTESTED."""
    v = V.get(e, frozenset())
    if not v:
        return ABSENT
    return COMMITTED if len(v | I.get(e, frozenset())) == 1 else CONTESTED


def affected(S):
    a = set()
    for (ep, q, c, p) in S:
        a.add((ep, q))
        if q > 0 and p is not None:
            a.add((ep, q - 1))
    return a


def part_m(log):
    out = {}
    for name, U in (("U1_one_epoch_seq0-2_prev_null", model_universe((0,), (0, 1, 2), True)),
                    ("U2_two_epochs_seq0-1", model_universe((0, 1), (0, 1), False))):
        t0 = time.time()
        slots = sorted({(s[0], s[1]) for s in U})
        n_cases = n_bound_tight = n_changed = 0
        viol = []
        for mask in range(1 << len(U)):
            B = [U[i] for i in range(len(U)) if mask >> i & 1]
            V, I = {}, {}
            for s in B:
                V, I = model_apply(V, I, s)
            before = {e: model_class(V, I, e) for e in slots}
            rest = [U[i] for i in range(len(U)) if not mask >> i & 1]
            for k in (1, 2):
                for S in itertools.combinations(rest, k):
                    n_cases += 1
                    V1, I1 = V, I
                    for s in S:
                        V1, I1 = model_apply(V1, I1, s)
                    V2, I2 = V, I
                    for s in reversed(S):
                        V2, I2 = model_apply(V2, I2, s)
                    after = {e: model_class(V1, I1, e) for e in slots}
                    ch = {e for e in slots if after[e] != before[e]}
                    A = affected(S)
                    n_changed += bool(ch)
                    if len(ch) == 2 * k:
                        n_bound_tight += 1
                    bad = []
                    if not ch <= A:
                        bad.append("locality")
                    if len(A) > 2 * k:
                        bad.append("bound")
                    if (V1, I1) != (V2, I2):
                        bad.append("order")
                    if any(before[e] == CONTESTED and after[e] != CONTESTED for e in slots):
                        bad.append("absorbing")
                    if bad and len(viol) < 5:
                        viol.append({"B": B, "S": list(S), "bad": bad})
        out[name] = {"statements": len(U), "base_sets": 1 << len(U), "cases": n_cases,
                     "cases_with_class_change": n_changed, "cases_bound_attained": n_bound_tight,
                     "violations": viol, "seconds": round(time.time() - t0, 1)}
        log(f"[M] {name}: {n_cases} cases, {n_changed} with a class change, bound 2|S| attained in {n_bound_tight}, "
            f"violations {len(viol)}")
    return out


# ============================================================================ implementation harness
class Harness:
    """Prebuilt, signed wires for a small feed; a fresh verifier per schedule."""

    def __init__(self, params=None, k1_exp_ms=10 ** 12):
        self.params = dict(params or {})
        self.dsk1, self.dpk1 = keypair_from_seed(SEED, "dk:d1:1")
        self.dsk2, self.dpk2 = keypair_from_seed(SEED, "dk:d1:2")
        self.wsk, self.wpk = keypair_from_seed(SEED, "wk:g1:1")
        self.rsk, self.rpk = keypair_from_seed(SEED, "rk:auto:1")
        self.vkey = keypair_from_seed(SEED, "verifier")
        self.k1_exp_ms = k1_exp_ms
        self.cd_cache = {}

    def verifier(self):
        tr = TrustRegistry(SEED, use_x509=False)
        tr.issue("dk:d1:1", "device", DID, self.dpk1, -60_000, self.k1_exp_ms)
        tr.issue("dk:d1:2", "device", DID, self.dpk2, -60_000, 10 ** 12)
        tr.issue("wk:g1:1", "workload", WID, self.wpk, -60_000, 10 ** 12)
        tr.issue("rk:auto:1", "reviewer", RID, self.rpk, -60_000, 10 ** 12)
        doc = {"devices": {DID: {"assets": [AID], "origin": "device", "schemas": [SCH]}},
               "workloads": {WID: {"relay": [DID]}}, "params": dict(self.params),
               "reviewers": {RID: {"may_release": list(RELEASABLE), "active": True}}}
        return tr, PBTIVerifier(tr, PolicyStore(doc), self.vkey)

    def statement(self, ep, seq, content, prev_cd, key=1, ts=None):
        val = {"G": 1.0, "F": 99.0}[content] + seq
        o = LogicalObs(DID, AID, ep, seq, 100 * seq + 10 * ep if ts is None else ts, SCH, {"x": val},
                       f"m{ep}-{seq}-{content}", prev_cd)
        sk, kid = (self.dsk1, "dk:d1:1") if key == 1 else (self.dsk2, "dk:d1:2")
        obs, osig = pbti_sign_obs(o, sk, kid)
        wire = pbti_wire(obs, osig, WID, "wk:g1:1", self.wsk, o.ts, "buffered")
        cd = b64u(pbti_content_digest(obs))
        return {"wire": wire, "cd": cd, "eid": (DID, ep, seq), "prev": prev_cd, "kid": kid, "wd": sha256_hex(wire)}


def slot_view(v):
    auth = {k for k, _ in v.authoritative()}
    proc = set(v.proc.where)
    return {k: (s.state(), k in auth, k in proc, s.tainted) for k, s in v.reg.slots.items()}


def changed_slots(a, b):
    keys = set(a) | set(b)
    none = (ABSENT, False, False, False)
    return {k for k in keys if a.get(k, none)[:3] != b.get(k, none)[:3]}


def affected_impl(stmts):
    a = set()
    for s in stmts:
        a.add(s["eid"])
        if s["eid"][2] > 0 and s["prev"] is not None:
            a.add((s["eid"][0], s["eid"][1], s["eid"][2] - 1))
    return a


def impl_universe(h, epochs, seqs, prevs_null):
    """Real signed statements mirroring the model universe: G chain and F alternatives; prev names the G or F
    statement of the predecessor whose own prev is G (a fixed reference statement per content)."""
    ref = {}
    U = []
    for ep in epochs:
        for q in seqs:
            for c in ("G", "F"):
                if q == 0:
                    s = h.statement(ep, q, c, None)
                    U.append(s)
                    ref[(ep, q, c)] = s["cd"]
                else:
                    for p in ("G", "F") + ((None,) if prevs_null else ()):
                        s = h.statement(ep, q, c, ref[(ep, q - 1, p)] if p else None)
                        U.append(s)
                        if p == "G":
                            ref[(ep, q, c)] = s["cd"]
    return U


def run_batch(h, B, S, t0=1_000):
    _, v = h.verifier()
    t = t0
    for s in B:
        v.ingest(s["wire"], t)
        t += 10
    v.advance(t)
    before = slot_view(v)
    admitted = []
    for s in S:
        r = v.ingest(s["wire"], t)
        if r.disp in (ACCEPT, CONFLICT):
            admitted.append(s)
        t += 10
    after = slot_view(v)
    return changed_slots(before, after), admitted


def part_l(log, n_random=4000, seed=1):
    h = Harness()
    U1 = impl_universe(h, (0,), (0, 1, 2), True)
    U2 = impl_universe(h, (0, 1), (0, 1), False)
    t0 = time.time()
    res = {"exhaustive_U2_single": {"cases": 0, "violations": 0, "not_admitted": 0, "changed": 0}}
    ex = res["exhaustive_U2_single"]
    viol = []
    for mask in range(1 << len(U2)):
        B = [U2[i] for i in range(len(U2)) if mask >> i & 1]
        for i in range(len(U2)):
            if mask >> i & 1:
                continue
            ch, adm = run_batch(h, B, [U2[i]])
            ex["cases"] += 1
            ex["not_admitted"] += not adm
            ex["changed"] += bool(ch)
            if not ch <= affected_impl(adm):
                ex["violations"] += 1
                if len(viol) < 5:
                    viol.append({"B": [s["eid"] for s in B], "S": [U2[i]["eid"]], "changed": sorted(ch)})
    ex["seconds"] = round(time.time() - t0, 1)
    log(f"[L] exhaustive U2 single statements: {ex['cases']} cases, {ex['changed']} with a change, "
        f"{ex['not_admitted']} not admitted, violations {ex['violations']}")
    rng = random.Random(seed)
    rs = {"cases": 0, "violations": 0, "not_admitted_statements": 0, "changed": 0, "bound_attained": 0}
    t1 = time.time()
    for _ in range(n_random):
        U = U1 if rng.random() < 0.5 else U2
        k = rng.choice((2, 3))
        idx = list(range(len(U)))
        rng.shuffle(idx)
        S = [U[i] for i in idx[:k]]
        B = [U[i] for i in idx[k:] if rng.random() < 0.5]
        rng.shuffle(B)
        ch, adm = run_batch(h, B, S)
        rs["cases"] += 1
        rs["not_admitted_statements"] += k - len(adm)
        rs["changed"] += bool(ch)
        rs["bound_attained"] += len(ch) == 2 * len(adm) and bool(adm)
        if not ch <= affected_impl(adm) or len(affected_impl(adm)) > 2 * len(adm):
            rs["violations"] += 1
            if len(viol) < 10:
                viol.append({"B": [s["eid"] for s in B], "S": [s["eid"] for s in S], "changed": sorted(ch)})
    rs["seconds"] = round(time.time() - t1, 1)
    res["random_batches_2_3"] = rs
    res["violation_examples"] = viol
    log(f"[L] random batches of 2-3 (seed {seed}): {rs['cases']} cases, {rs['changed']} with a change, "
        f"bound attained {rs['bound_attained']}, violations {rs['violations']}")
    return res


# ============================================================================ part C: lifecycle combinations
GAP_CLOSE_MS = 3_000
GRACE_MS = 3_000
K1_EXP_MS = 4_000
OPS = ("dG0", "dG1", "dF1", "dG2", "dR2", "dH0", "dH1", "CLOSE", "REV_EARLY", "REV_LATE", "REL", "REL_STALE", "REJ")


class Lifecycle:
    def __init__(self):
        self.h = Harness({"gap_close_ms": GAP_CLOSE_MS, "rotation_grace_ms": GRACE_MS}, k1_exp_ms=K1_EXP_MS)
        h = self.h
        g0 = h.statement(0, 0, "G", None)
        g1 = h.statement(0, 1, "G", g0["cd"])
        f1 = h.statement(0, 1, "F", g0["cd"])            # equivocation / gap-fill alternative under the same key
        g2 = h.statement(0, 2, "G", g1["cd"])
        r2 = h.statement(0, 2, "G", g1["cd"], key=2)     # same reading signed with the rotated key
        h0 = h.statement(1, 0, "G", None)
        h1 = h.statement(1, 1, "G", h0["cd"])
        self.st = {"dG0": g0, "dG1": g1, "dF1": f1, "dG2": g2, "dR2": r2, "dH0": h0, "dH1": h1}
        self.order = ["dG0", "dG1", "dF1", "dG2", "dR2", "dH0", "dH1"]
        self.stats = {"sequences": 0, "operations": 0, "violations": 0, "outcomes": {}, "dispositions": {},
                      "failed_release_admitted_evidence": 0}
        self.examples = []

    # ---------------------------------------------------------------- one schedule
    def run(self, seq):
        tr, v = self.h.verifier()
        t = 1_000
        admitted = []                    # statements admitted (ACCEPT/CONFLICT receipts, incl. inside releases)
        revs = []                        # (t_rev, t_comp, processed_at, committed_untainted_at_processing)
        contested_ever = set()
        k1_revoked_at = None
        released = set()
        delivered = []
        bad = []

        def check(tag):
            vw = slot_view(v)
            # C1 evidence conformance
            V, I = {}, {}
            for s in admitted:
                V.setdefault(s["eid"], set()).add(s["cd"])
                if s["eid"][2] > 0 and s["prev"] is not None:
                    I.setdefault((s["eid"][0], s["eid"][1], s["eid"][2] - 1), set()).add(s["prev"])
            for k, sl in v.reg.slots.items():
                if set(sl.versions) != V.get(k, set()) or set(sl.implied or ()) != I.get(k, set()):
                    bad.append((tag, "C1-evidence", k))
                d = set(sl.versions) | set(sl.implied or ())
                spec = (LOST if sl.lost and not sl.versions else ABSENT if not sl.versions
                        else COMMITTED if len(d) == 1 else CONTESTED)
                if sl.state() != spec:
                    bad.append((tag, "C1-class", k))
                if sl.lost and sl.versions and sl.state() == LOST:
                    bad.append((tag, "C1-lost", k))
            for k in set(V) - set(v.reg.slots):
                bad.append((tag, "C1-missing-slot", k))
            # C2 absorbing contest
            for k, (st, *_r) in vw.items():
                if st == CONTESTED:
                    contested_ever.add(k)
                elif k in contested_ever:
                    bad.append((tag, "C2-absorbing", k))
            # C3 authority and derived processing
            for k, (st, au, pr, ta) in vw.items():
                if au != (st == COMMITTED and not ta):
                    bad.append((tag, "C3-authority", k))
                if pr != au:
                    bad.append((tag, "C3-derived", k))
            # C4 taint exactness
            for k, sl in v.reg.slots.items():
                if sl.tainted:
                    ok = sl.kid == "dk:d1:1" and any(sl.t_first >= tc and k in cu for (_tr, tc, _p, cu) in revs)
                    if not ok:
                        bad.append((tag, "C4-taint-unexpected", k))
            for (_tr, tc, _p, cu) in revs:
                for k in cu:
                    if not v.reg.slots[k].tainted:
                        bad.append((tag, "C4-taint-missing", k))
            return vw

        check("init")
        for op in seq:
            t += 1_000
            v.advance(t)
            if op in self.st:
                s = self.st[op]
                before = slot_view(v)
                r = v.ingest(s["wire"], t)
                delivered.append(op)
                self.stats["dispositions"][r.disp + "/" + r.why.split(":")[0]] = \
                    self.stats["dispositions"].get(r.disp + "/" + r.why.split(":")[0], 0) + 1
                adm = r.disp in (ACCEPT, CONFLICT)
                if adm:
                    admitted.append(s)
                    # C5 ordinary admission under a revoked key
                    if s["kid"] == "dk:d1:1" and k1_revoked_at is not None and t >= k1_revoked_at:
                        bad.append((op, "C5-revoked-admitted", s["eid"]))
                    # C9 rotation
                    if s["kid"] == "dk:d1:1" and t > K1_EXP_MS + GRACE_MS:
                        bad.append((op, "C9-expired-admitted", s["eid"]))
                if s["kid"] == "dk:d1:1" and K1_EXP_MS < t <= K1_EXP_MS + GRACE_MS and adm \
                        and "KEY_IN_GRACE:device" not in (r.ann or ()):
                    bad.append((op, "C9-grace-annotation", s["eid"]))
                after = check(op)
                ch = changed_slots(before, after)
                if not ch <= affected_impl([s] if adm else []):
                    bad.append((op, "C8-locality", sorted(ch)))
            elif op == "CLOSE":
                t += GAP_CLOSE_MS + 1_000
                v.advance(t)
                check(op)
            elif op in ("REV_EARLY", "REV_LATE"):
                tr.revoke("dk:d1:1", t, 0 if op == "REV_EARLY" else t, "check")
                tc = tr.all_revocations()["dk:d1:1"].t_comp_ms      # merged record: earliest compromise time (D05)
                k1_revoked_at = t if k1_revoked_at is None else k1_revoked_at
                # expected taint: COMMITTED, origin key revoked, commit time >= t_comp, except a reviewed
                # pre-compromise release whose condition (discretionary: ts < t_comp) still holds
                cu = {k for k, sl in v.reg.slots.items()
                      if sl.kid == "dk:d1:1" and sl.state() == COMMITTED and sl.t_first >= tc
                      and not (k in v.pre_comp_released and sl.ts < tc)}
                v.advance(t + 1_000)          # process the revocation now (taint selector)
                t += 1_000
                revs.append((t, tc, t, cu))
                check(op)
            elif op in ("REL", "REL_STALE", "REJ"):
                cases = sorted((c["t_q"], wd) for wd, c in v.qcases.items() if c["state"] == "QUARANTINED")
                if not cases:
                    check(op)
                    continue
                wd = cases[0][1]
                snap = v.open_review(wd, RID, t)
                if op == "REL_STALE":
                    # prefer an undelivered statement for the case's identity or a hash-link neighbour, so that the
                    # snapshot is actually superseded when that statement is admitted
                    ce = tuple(v.qcases[wd]["eid"]) if v.qcases[wd].get("eid") else None
                    near = [o for o in self.order if o not in delivered and ce is not None
                            and self.st[o]["eid"][:2] == ce[:2] and abs(self.st[o]["eid"][2] - ce[2]) <= 1]
                    nxt = near[0] if near else next((o for o in self.order if o not in delivered), None)
                    if nxt is not None:
                        s = self.st[nxt]
                        r = v.ingest(s["wire"], t)
                        delivered.append(nxt)
                        if r.disp in (ACCEPT, CONFLICT):
                            admitted.append(s)
                cur = v.review_snapshot(wd)
                reg_before = {k: (frozenset(sl.versions), frozenset(sl.implied or ()), sl.tainted)
                              for k, sl in v.reg.slots.items()}
                d = sign_decision({"case": wd, "reviewer": RID, "rkid": "rk:auto:1",
                                   "decision": "REJECT" if op == "REJ" else "RELEASE", "reason": "CHECK",
                                   "snapshot": snap, "t": t}, self.h.rsk)
                blob_stmt = next((s for s in self.st.values() if s["wd"] == wd), None)
                n_adm = len(admitted)
                out = v.apply_review(d, t)["outcome"]
                self.stats["outcomes"][out.split("/")[0]] = self.stats["outcomes"].get(out.split("/")[0], 0) + 1
                if snap != cur:
                    # C7 stale snapshot: the decision is refused (STALE_REVIEW, or an earlier refusal such as
                    # UNAUTHORIZED_REVIEWER for a reason the reviewer may not release) and the case is QUARANTINED
                    if out in ("RELEASED", "REJECTED") or out.startswith("RELEASE_FAILED") \
                            or v.qcases[wd]["state"] != "QUARANTINED":
                        bad.append((op, "C7-stale-accepted", out))
                    reg_after = {k: (frozenset(sl.versions), frozenset(sl.implied or ()), sl.tainted)
                                 for k, sl in v.reg.slots.items()}
                    if reg_after != reg_before:
                        bad.append((op, "C7-registry-changed", out))
                if out == "RELEASED":
                    admitted.append(blob_stmt)
                    released.add(wd)
                    if v.reg.slots[blob_stmt["eid"]].state() != COMMITTED:
                        bad.append((op, "C6-release-not-committed", blob_stmt["eid"]))
                elif out.startswith("RELEASE_FAILED:CONFLICT"):
                    admitted.append(blob_stmt)      # the re-run admission recorded contradictory evidence
                    self.stats["failed_release_admitted_evidence"] += 1
                    if blob_stmt["eid"] in {k for k, _ in v.authoritative()}:
                        bad.append((op, "C6-failed-release-authoritative", blob_stmt["eid"]))
                check(op)
                assert len(admitted) >= n_adm
        self.stats["sequences"] += 1
        self.stats["operations"] += len(seq)
        if bad:
            self.stats["violations"] += 1
            if len(self.examples) < 10:
                self.examples.append({"sequence": list(seq), "violations": [list(map(str, b)) for b in bad[:5]]})


def part_c(log, max_len=4, n_random=20000, seed=2):
    lc = Lifecycle()
    t0 = time.time()
    n = 0
    for L in range(1, max_len + 1):
        for seq in itertools.product(OPS, repeat=L):
            lc.run(seq)
            n += 1
    ex = {"exhaustive_max_len": max_len, "sequences": n, "seconds": round(time.time() - t0, 1)}
    log(f"[C] exhaustive sequences of length <= {max_len}: {n} sequences, violations {lc.stats['violations']}")
    rng = random.Random(seed)
    t1 = time.time()
    for _ in range(n_random):
        lc.run([rng.choice(OPS) for _ in range(rng.randint(max_len + 1, 8))])
    log(f"[C] random sequences of length {max_len + 1}..8 (seed {seed}): {n_random}; "
        f"total violations {lc.stats['violations']}")
    return {"exhaustive": ex, "random": {"sequences": n_random, "seed": seed, "seconds": round(time.time() - t1, 1)},
            "alphabet": list(OPS), "stats": lc.stats, "violation_examples": lc.examples,
            "constants": {"gap_close_ms": GAP_CLOSE_MS, "rotation_grace_ms": GRACE_MS, "k1_exp_ms": K1_EXP_MS}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "results" / "v4" / "formal" / "v4_locality_lifecycle_check.json"))
    ap.add_argument("--l-random", type=int, default=4000)
    ap.add_argument("--c-max-len", type=int, default=4)
    ap.add_argument("--c-random", type=int, default=20000)
    ap.add_argument("--parts", default="MLC")
    a = ap.parse_args()
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = []

    def log(m):
        print(m, flush=True)
        lines.append(m)

    src = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT / "src" / "pbti").glob("*.py"))}
    res = {"python": platform.python_version(), "source_sha256": src,
           "this_file_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    t0 = time.time()
    if "M" in a.parts:
        res["M"] = part_m(log)
    if "L" in a.parts:
        res["L"] = part_l(log, n_random=a.l_random)
    if "C" in a.parts:
        res["C"] = part_c(log, max_len=a.c_max_len, n_random=a.c_random)
    src_end = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT / "src" / "pbti").glob("*.py"))}
    res["source_unchanged_during_run"] = src == src_end
    res["seconds_total"] = round(time.time() - t0, 1)
    res["log"] = lines
    res["all_pass"] = (all(not x["violations"] for x in res.get("M", {}).values())
                       and res.get("L", {}).get("exhaustive_U2_single", {}).get("violations", 0) == 0
                       and res.get("L", {}).get("random_batches_2_3", {}).get("violations", 0) == 0
                       and res.get("C", {}).get("stats", {}).get("violations", 0) == 0)
    out.write_text(json.dumps(res, indent=1, default=str))
    log(f"all_pass={res['all_pass']} -> {out}")


if __name__ == "__main__":
    main()
