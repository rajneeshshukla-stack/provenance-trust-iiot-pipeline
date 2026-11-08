#!/usr/bin/env python3
"""Bounded exhaustive check of PBTI Rule L (delivery-history classification) on the reference implementation.

Properties (definitions and the argument for what they imply are in README.md, Section 4):
  S0  conformance   after every arrival sequence the implementation's slot states equal Rule L
                    (PROTOCOL_SPECIFICATION.md 5.1) evaluated on the admitted evidence set
  S1  determinism   every permutation of the same admitted set yields identical final slot states
                    (and identical committed digests)
  S2  monotonicity  along every arrival sequence and over the inclusion lattice of admitted sets:
                    CONTESTED is absorbing, a slot with a version never returns to ABSENT, and a COMMITTED
                    slot never changes its committed digest
  S3  conflicts     (a) >= 2 distinct admitted contents for one slot  => CONTESTED
                    (b) gap-fill: an admitted alternative content whose genuine successor is admitted
                        => CONTESTED (checked with and without the genuine content itself)
                    (c) an alternative content is authoritative only if neither the genuine content nor the
                        genuine successor was admitted (characterises the known residual risk)
  S4  duplicates    re-delivering an already admitted statement is a DUPLICATE and leaves the registry
                    unchanged (checked after every prefix)

Bound: one device, one epoch, sequence numbers 0..N-1; per slot the genuine statement G_k and at most one
alternative statement F_k (<= 2 contents per slot); prev(G_k) = cd(G_{k-1}); prev(F_k) is cd(G_{k-1}) or
cd(F_{k-1}) ("standard"), or additionally null for k >= 1 ("extended", accepted by pbti_parse). A *feed* fixes
which alternatives exist; for a feed with universe U every subset of U is a candidate admitted set and every
permutation of it an arrival order. The prefix tree of U has exactly one node per (subset, permutation) pair,
so a depth-first walk of it enumerates all of them once.

Engines:
  mirror   a line-by-line re-implementation of PBTIVerifier._history (no ablations) operating on the real
           pbti.registry.Registry / Slot / EpochState objects and the real Slot.state(); cheap to clone,
           used for the exhaustive prefix-tree walks
  real     the unmodified pbti.verifier.PBTIVerifier fed with real Ed25519-signed wire messages built as in
           tests/test_evidence_and_envelope.py (X.509 certificates); every prefix of every permutation of the
           whole universe is compared with the mirror (registry snapshot and disposition) and with Rule L
  oracle   an independent evaluation of Rule L from the specification text on the admitted set
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import multiprocessing as mp
import os
import platform
import random
import sys
from pathlib import Path
import time
from collections import Counter

DEFAULT_SRC = str(Path(__file__).resolve().parents[1] / "src")  # V3: repository-relative


def _early_src() -> str:
    for i, a in enumerate(sys.argv):
        if a == "--src" and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
        if a.startswith("--src="):
            return a.split("=", 1)[1]
    return DEFAULT_SRC


SRC = os.path.abspath(_early_src())
sys.dont_write_bytecode = True        # never write .pyc files into the (read-only) source tree
sys.path.insert(0, SRC)

import cryptography  # noqa: E402

from pbti.crypto import b64u, keypair_from_seed, sha256_hex  # noqa: E402
from pbti.envelope import LogicalObs, pbti_content_digest, pbti_sign_obs, pbti_wire  # noqa: E402
from pbti.identity import TrustRegistry  # noqa: E402
from pbti.policy import DEFAULT_PARAMS, PolicyStore  # noqa: E402
from pbti.registry import ABSENT, COMMITTED, CONTESTED, EpochState, Registry, Slot, Stream  # noqa: E402
from pbti.verifier import ACCEPT, CONFLICT, DUPLICATE, QUARANTINE, REJECT, PBTIVerifier  # noqa: E402

SEED = b"pbti-rule-l-bounded-check"
DID, AID, SCH, EP = "d1", "a1", "telemetry.v1", 0
KID, WKID = "dk:d1:1", "wk:g1:1"
WID = "spiffe://plant-a.example/cell1/gw1/collector"
T0 = 20_000            # verifier time of the first receipt (ms); receipts are 1 ms apart
ALLOWED = {(ABSENT, ABSENT), (ABSENT, COMMITTED), (ABSENT, CONTESTED),
           (COMMITTED, COMMITTED), (COMMITTED, CONTESTED), (CONTESTED, CONTESTED)}
MAX_VIOL = 25          # violations stored verbatim per category (all are counted)
PREM_EQ = "premise:S3a-equivocation"
PREM_ALT = "premise:S3b-alt+genuine-successor"
PREM_GAP = "premise:S3b'-gap-fill(genuine withheld)+genuine-successor"


# =============================================================================================== logging
class Log:
    def __init__(self, path):
        self.f = open(path, "w", encoding="utf-8") if path else None

    def __call__(self, *a):
        s = " ".join(str(x) for x in a)
        print(s, flush=True)
        if self.f:
            self.f.write(s + "\n")
            self.f.flush()


def src_digests(src: str) -> dict:
    d = os.path.join(src, "pbti")
    out = {}
    for fn in sorted(os.listdir(d)):
        if fn.endswith(".py"):
            with open(os.path.join(d, fn), "rb") as f:
                out[fn] = hashlib.sha256(f.read()).hexdigest()
    return out


def tree_digest(dig: dict) -> str:
    return hashlib.sha256("".join(f"{k}:{v}\n" for k, v in sorted(dig.items())).encode()).hexdigest()


# =============================================================================================== messages
class Msg:
    __slots__ = ("label", "seq", "genuine", "cd", "prev", "obs", "osig", "wire", "wd", "ts")

    def __init__(self, label, seq, genuine, cd, prev, obs, osig, wire, ts):
        self.label, self.seq, self.genuine, self.cd, self.prev = label, seq, genuine, cd, prev
        self.obs, self.osig, self.wire, self.wd, self.ts = obs, osig, wire, sha256_hex(wire), ts

    def __repr__(self):
        return self.label


class World:
    """Identity plane, policy and keys as in tests/test_evidence_and_envelope.py (X.509 certificates)."""

    def __init__(self, params: dict | None = None, use_x509: bool = True):
        self.trust = TrustRegistry(SEED, use_x509=use_x509)
        self.dsk, dpk = keypair_from_seed(SEED, KID)
        self.wsk, wpk = keypair_from_seed(SEED, WKID)
        self.trust.issue(KID, "device", DID, dpk, -60_000, 10 ** 10)
        self.trust.issue(WKID, "workload", WID, wpk, -60_000, 10 ** 10)
        doc = {"devices": {DID: {"assets": [AID], "origin": "device", "schemas": [SCH]}},
               "workloads": {WID: {"relay": [DID]}}, "params": dict(params or {})}
        self.pol = PolicyStore(doc)
        self.params = self.pol.current().doc["params"]
        self.vkeys = keypair_from_seed(SEED, "verifier")
        self._cache: dict = {}

    def verifier(self) -> PBTIVerifier:
        return PBTIVerifier(self.trust, self.pol, self.vkeys)

    # -------------------------------------------------------------------------------- statements
    def _make(self, key, seq, x, prev, ts, label, genuine) -> Msg:
        m = self._cache.get(key)
        if m is None:
            o = LogicalObs(DID, AID, EP, seq, ts, SCH, {"x": x}, label, prev)
            obs, osig = pbti_sign_obs(o, self.dsk, KID)
            cd = b64u(pbti_content_digest(obs))
            wire = pbti_wire(obs, osig, WID, WKID, self.wsk, ts, "live")
            m = self._cache[key] = Msg(label, seq, genuine, cd, prev, obs, osig, wire, ts)
        return m

    def genuine(self, k: int) -> Msg:
        prev = None if k == 0 else self.genuine(k - 1).cd
        return self._make(("G", k), k, float(k), prev, 1_000 + 1_000 * k, f"G{k}", True)

    def alternative(self, k: int, parent: Msg | None) -> Msg:
        """F_k with prev = cd(parent) (parent None => prev null). Payload differs from G_k."""
        plabel = parent.label if parent is not None else "0"
        label = "F0" if k == 0 else f"F{k}<{plabel}"
        prev = parent.cd if parent is not None else None
        return self._make(("F", label), k, 100.0 + k, prev, 1_000 + 1_000 * k, label, False)

    def rerelayed(self, m: Msg) -> bytes:
        """Same (obs, osig) under a fresh relay statement (other rts and mode): different wire, same content."""
        w = self._cache.get(("RR", m.label))
        if w is None:
            w = self._cache[("RR", m.label)] = pbti_wire(m.obs, m.osig, WID, WKID, self.wsk, m.ts + 7, "buffered")
        return w


def enumerate_shapes(n: int, extended: bool):
    """Per slot: None (no alternative) | 'root' (F_0) | 'G' | 'F' | '0' (parent of F_k)."""
    def rec(k, prev_has_alt):
        if k == n:
            yield ()
            return
        opts = [None]
        if k == 0:
            opts.append("root")
        else:
            opts.append("G")
            if prev_has_alt:
                opts.append("F")
            if extended:
                opts.append("0")
        for o in opts:
            for rest in rec(k + 1, o is not None):
                yield (o,) + rest
    yield from rec(0, False)


def build_feed(world: World, n: int, shape) -> list[Msg]:
    gs = [world.genuine(k) for k in range(n)]
    msgs = list(gs)
    alt_prev = None
    for k, o in enumerate(shape):
        if o is None:
            alt_prev = None
            continue
        if o == "root":
            parent = None
        elif o == "G":
            parent = gs[k - 1]
        elif o == "F":
            parent = alt_prev
        else:
            parent = None
        a = world.alternative(k, parent)
        msgs.append(a)
        alt_prev = a
    return msgs


# =============================================================================================== engines
def mirror_deliver(reg: Registry, m: Msg, t: int, params: dict, wid=WID, kid=KID, wkid=WKID):
    """Re-implementation of PBTIVerifier._history (src/pbti/verifier.py) without ablations and without the
    V3 'waive' path, on the real Registry/Slot/EpochState classes. Returns (disposition, reason, admitted)."""
    did, ep, seq, cd = DID, EP, m.seq, m.cd
    key = (did, ep, seq)
    slot = reg.slots.get(key)
    if slot is not None and cd in slot.versions:
        if slot.state() == COMMITTED and slot.wid_first == wid and t - slot.t_first <= params["retry_window_ms"]:
            return DUPLICATE, "RETRY", False
        return DUPLICATE, "SUSPECTED_REPLAY", False
    stream = reg.stream(did)
    es = stream.epochs.get(ep)
    if es is not None and es.in_closed(seq) and (slot is None or not slot.versions):
        return QUARANTINE, "STALE_SLOT", False
    if ep < stream.max_ep and t - stream.epochs[stream.max_ep].t_open > params["epoch_drain_ms"]:
        return QUARANTINE, "STALE_EPOCH", False
    hw = es.hw if es is not None else -1
    if seq > hw + params["max_seq_jump"]:
        return QUARANTINE, "SEQ_JUMP", False
    slot = reg.slot(key, create=True)
    before = slot.state()
    slot.versions[cd] = m.wd
    if len(slot.versions) == 1:
        slot.t_first, slot.wid_first, slot.kid, slot.wkid = t, wid, kid, wkid
        slot.ts, slot.aid, slot.obs_first = m.obs["ts"], m.obs["aid"], m.obs
        reg.by_kid.setdefault(kid, []).append(key)
    changes = []
    if seq > 0 and m.prev is not None:
        pkey = (did, ep, seq - 1)
        ps = reg.slot(pkey, create=True)
        pb = ps.state()
        if ps.implied is None:
            ps.implied = set()
        ps.implied.add(m.prev)
        pa = ps.state()
        if pa != pb:
            changes.append((pkey, pb, pa))
    after = slot.state()
    if before == ABSENT:
        if es is None:
            es = stream.epochs[ep] = EpochState(t)
        if ep > stream.max_ep:
            stream.max_ep = ep
        es.note_seq(seq, t)
    if after == COMMITTED:
        res = (ACCEPT, "COMMITTED", True)
    else:
        why = "EQUIVOCATION" if before != ABSENT or len(slot.versions) > 1 else "LINK_MISMATCH"
        if before == COMMITTED:
            changes.append((key, COMMITTED, CONTESTED))
        res = (CONFLICT, why, True)
    for k, old, new in changes:
        reg.record_change(t, k, old, new, "EVIDENCE")
    return res


def clone_registry(reg: Registry) -> Registry:
    r = Registry()
    for k, s in reg.slots.items():
        c = Slot()
        c.versions = dict(s.versions)
        c.implied = set(s.implied) if s.implied is not None else None
        c.t_first, c.wid_first, c.kid, c.wkid, c.ts, c.aid = s.t_first, s.wid_first, s.kid, s.wkid, s.ts, s.aid
        c.tainted, c.lost, c.obs_first = s.tainted, s.lost, s.obs_first
        r.slots[k] = c
    for did, st in reg.streams.items():
        ns = Stream()
        ns.max_ep = st.max_ep
        for ep, es in st.epochs.items():
            e = EpochState(es.t_open)
            e.hw, e.gaps, e.closed = es.hw, [list(g) for g in es.gaps], list(es.closed)
            ns.epochs[ep] = e
        r.streams[did] = ns
    r.by_kid = {k: list(v) for k, v in reg.by_kid.items()}
    r.state_events = list(reg.state_events)
    return r


def snapshot(reg: Registry):
    """Everything Rule L and the admission checks of _history depend on (not the evidence log / derived data)."""
    slots = tuple(sorted(
        ((k, tuple(sorted(s.versions)), tuple(sorted(s.implied)) if s.implied else (), s.state(), s.lost,
          s.tainted, s.t_first, s.wid_first) for k, s in reg.slots.items()), key=repr))
    streams = tuple(sorted(
        (did, st.max_ep, tuple((ep, es.hw, es.t_open, tuple(tuple(g) for g in es.gaps), tuple(es.closed))
                               for ep, es in sorted(st.epochs.items())))
        for did, st in reg.streams.items()))
    return slots, streams


def fingerprint(reg: Registry):
    """Cheap change detector (every registry mutation grows one of these sizes or moves hw/gaps)."""
    return (len(reg.slots), sum(len(s.versions) + (len(s.implied) if s.implied else 0) for s in reg.slots.values()),
            tuple((ep, es.hw, len(es.gaps), len(es.closed)) for st in reg.streams.values()
                  for ep, es in st.epochs.items()), len(reg.state_events), len(reg.by_kid.get(KID, ())))


def state_vector(reg: Registry, n: int):
    st, cdig = [], []
    for k in range(n):
        s = reg.slots.get((DID, EP, k))
        if s is None:
            st.append(ABSENT)
            cdig.append(None)
        else:
            x = s.state()
            st.append(x)
            cdig.append(next(iter(s.versions)) if x == COMMITTED else None)
    return tuple(st), tuple(cdig)


def oracle(admitted, n: int):
    """Rule L from the specification text (PROTOCOL_SPECIFICATION.md 5.1 / STATE_MACHINE.md M2)."""
    vers = [set() for _ in range(n)]
    imp = [set() for _ in range(n)]
    for m in admitted:
        vers[m.seq].add(m.cd)
        if m.seq > 0 and m.prev is not None:
            imp[m.seq - 1].add(m.prev)
    st, cdig = [], []
    for k in range(n):
        if not vers[k]:
            st.append(ABSENT)
            cdig.append(None)
        elif len(vers[k] | imp[k]) == 1:
            st.append(COMMITTED)
            cdig.append(next(iter(vers[k])))
        else:
            st.append(CONTESTED)
            cdig.append(None)
    return tuple(st), tuple(cdig)


# =============================================================================================== checks
class Checker:
    """Accumulates counts and violations; check_node() applies S0-S3 to one (admitted set, order) node."""

    CATS = ("ADMIT", "S0", "S1", "S2", "S2-digest", "S3a", "S3b", "S3b'", "S3c", "S4-disp", "S4-state",
            "MIRROR-disp", "MIRROR-state", "EVENTS", "LOST")

    def __init__(self, n: int):
        self.n = n
        self.c = Counter()
        self.viol = {k: [] for k in self.CATS}
        self.sets: dict = {}          # frozenset(cd) -> (states, committed digests)

    def bad(self, cat, info):
        self.c["viol:" + cat] += 1
        if len(self.viol[cat]) < MAX_VIOL:
            self.viol[cat].append(info)

    def check_node(self, msgs, path, st, cdig, parent, gidx):
        n = self.n
        c = self.c
        c["nodes"] += 1
        admitted = [msgs[i] for i in path]
        labels = [m.label for m in admitted]
        # S0 conformance with the specification
        if (st, cdig) != oracle(admitted, n):
            self.bad("S0", (labels, st))
        # S1 one result per admitted set
        key = frozenset(m.cd for m in admitted)
        prev = self.sets.get(key)
        if prev is None:
            self.sets[key] = (st, cdig)
        elif prev != (st, cdig):
            self.bad("S1", (labels, st, prev[0]))
        # S2 monotonicity along the path
        if parent is not None:
            pst, pcd = parent
            for k in range(n):
                if (pst[k], st[k]) not in ALLOWED:
                    self.bad("S2", (labels, k, pst[k], st[k]))
                if pst[k] == COMMITTED and st[k] == COMMITTED and pcd[k] != cdig[k]:
                    self.bad("S2-digest", (labels, k))
        # S3 conflicts
        inset = set(path)
        for k in range(n):
            contents = {m.cd for m in admitted if m.seq == k}
            alt_in = any((not m.genuine) and m.seq == k for m in admitted)
            g_in = gidx[k] in inset
            succ_in = k + 1 < n and gidx[k + 1] in inset
            if len(contents) >= 2:
                c[PREM_EQ] += 1
                if st[k] != CONTESTED:
                    self.bad("S3a", (labels, k, st[k]))
            if alt_in and succ_in:
                c[PREM_ALT] += 1
                if st[k] != CONTESTED:
                    self.bad("S3b", (labels, k, st[k]))
                if not g_in:
                    c[PREM_GAP] += 1
                    if st[k] != CONTESTED:
                        self.bad("S3b'", (labels, k, st[k]))
            if st[k] == COMMITTED and cdig[k] != msgs[gidx[k]].cd:
                c["obs:alternative-authoritative(node)"] += 1
                if g_in or succ_in:
                    self.bad("S3c", (labels, k))
            if alt_in and st[k] == CONTESTED:
                c["obs:alternative-contested(node)"] += 1


def merge_sets(dst: dict, src: dict, chk: Checker):
    for k, v in src.items():
        p = dst.get(k)
        if p is None:
            dst[k] = v
        elif p != v:
            chk.bad("S1", ("cross-feed", sorted(k)[:3], v[0], p[0]))


def lattice_check(sets: dict, pool_cds, chk: Checker, n: int):
    """S2 over the inclusion lattice: for every admitted set A and content c with A u {c} also explored."""
    pairs = 0
    for a, (sta, cda) in sets.items():
        for cd in pool_cds:
            if cd in a:
                continue
            b = sets.get(a | {cd})
            if b is None:
                continue
            pairs += 1
            stb, cdb = b
            for k in range(n):
                if (sta[k], stb[k]) not in ALLOWED:
                    chk.bad("S2", ("lattice", k, sta[k], stb[k]))
                if sta[k] == COMMITTED and stb[k] == COMMITTED and cda[k] != cdb[k]:
                    chk.bad("S2-digest", ("lattice", k))
    return pairs


# =============================================================================================== part B: mirror walk
def mirror_walk_feed(msgs, n, params, chk: Checker, check_dups=True):
    """Depth-first walk of the prefix tree of the feed; each node = one (admitted set, arrival order)."""
    gidx = {m.seq: i for i, m in enumerate(msgs) if m.genuine}
    m_all = len(msgs)
    c = chk.c

    def rec(reg, path, used, parent, depth):
        st, cdig = state_vector(reg, n)
        chk.check_node(msgs, path, st, cdig, parent, gidx)
        if check_dups and path:
            snap0, fp0 = snapshot(reg), fingerprint(reg)
            for i in path:
                d, why, adm = mirror_deliver(reg, msgs[i], T0 + 1_000 + depth, params)
                c["dup_redeliveries"] += 1
                c["dup:" + why] += 1
                if d != DUPLICATE or adm:
                    chk.bad("S4-disp", ([msgs[j].label for j in path], msgs[i].label, d))
                if fingerprint(reg) != fp0:
                    chk.bad("S4-state", ([msgs[j].label for j in path], msgs[i].label))
            if snapshot(reg) != snap0:
                chk.bad("S4-state", ([msgs[j].label for j in path], "after all re-deliveries"))
        for i in range(m_all):
            if used >> i & 1:
                continue
            child = clone_registry(reg)
            d, why, adm = mirror_deliver(child, msgs[i], T0 + depth, params)
            c["disp:" + d + "/" + why] += 1
            if not adm:
                chk.bad("ADMIT", ([msgs[j].label for j in path], msgs[i].label, d, why))
                continue
            rec(child, path + [i], used | (1 << i), (st, cdig), depth + 1)

    rec(Registry(), [], 0, None, 0)


def mirror_feed_job(args):
    n, shape, check_dups = args
    world = World()
    msgs = build_feed(world, n, shape)
    sub = Checker(n)
    mirror_walk_feed(msgs, n, world.params, sub, check_dups)
    return len(msgs), [m.cd for m in msgs], dict(sub.c), sub.viol, sub.sets


def run_mirror(n, extended, log, check_dups=True, workers=1):
    world = World()
    shapes = list(enumerate_shapes(n, extended))
    chk = Checker(n)
    t0 = time.perf_counter()
    pool = {}
    sizes = Counter()
    jobs = sorted(((n, sh, check_dups) for sh in shapes), key=lambda j: -sum(x is not None for x in j[1]))
    if workers > 1:
        with mp.get_context("fork").Pool(workers) as pp:
            results = list(pp.imap_unordered(mirror_feed_job, jobs))
    else:
        results = [mirror_feed_job(j) for j in jobs]
    for size, cds, counts, viol, sets in results:
        sizes[size] += 1
        for cd in cds:
            pool[cd] = True
        chk.c.update(counts)
        for k, v in viol.items():
            chk.viol[k].extend(v[:MAX_VIOL - len(chk.viol[k])])
        merge_sets(chk.sets, sets, chk)
    pairs = lattice_check(chk.sets, list(pool), chk, n)
    dt = time.perf_counter() - t0
    distinct_pairs = sum(math.factorial(len(s)) for s in chk.sets)
    alt_auth_sets = sum(1 for s, (st, cd) in chk.sets.items()
                        if any(st[k] == COMMITTED and cd[k] != world.genuine(k).cd for k in range(n)))
    contested_sets = sum(1 for s, (st, cd) in chk.sets.items() if CONTESTED in st)
    summary = {
        "engine": "mirror", "N": n, "mode": "extended" if extended else "standard", "feeds": len(shapes),
        "feed_sizes": dict(sorted(sizes.items())), "distinct_contents": len(pool),
        "nodes_explored": chk.c["nodes"], "distinct_admitted_sets": len(chk.sets),
        "distinct_set_order_pairs": distinct_pairs, "lattice_pairs_checked": pairs,
        "dup_redeliveries": chk.c["dup_redeliveries"],
        "sets_with_alternative_authoritative": alt_auth_sets, "sets_with_contested_slot": contested_sets,
        "seconds": round(dt, 2),
        "counts": {k: v for k, v in sorted(chk.c.items()) if not k.startswith("viol:")},
        "violations": {k: chk.c.get("viol:" + k, 0) for k in Checker.CATS},
    }
    return summary, chk


# =============================================================================================== part C: real verifier
def real_sequence(world: World, order, n, chk: Checker, dup_mode: str, gidx, msgs, do_end_dups=True):
    """Feed one arrival order to a fresh PBTIVerifier and a fresh mirror; compare after every receipt."""
    c = chk.c
    params = world.params
    v = world.verifier()
    mreg = Registry()
    t = T0
    path = []
    parent = None
    pos = {id(m): i for i, m in enumerate(msgs)}
    st0, cd0 = state_vector(v.reg, n)
    chk.check_node(msgs, [], st0, cd0, None, gidx)          # empty admitted set (fresh verifier)
    parent = (st0, cd0)
    for m in order:
        r = v.ingest(m.wire, t)
        md, mwhy, madm = mirror_deliver(mreg, m, t, params)
        t += 1
        c["real_receipts"] += 1
        c["disp:" + r.disp + "/" + r.why.split(":")[0]] += 1
        if (r.disp, r.why) != (md, mwhy):
            chk.bad("MIRROR-disp", ([x.label for x in path], m.label, r.disp, r.why, md, mwhy))
        if r.disp not in (ACCEPT, CONFLICT):
            chk.bad("ADMIT", ([x.label for x in path], m.label, r.disp, r.why))
            continue
        path.append(m)
        if snapshot(v.reg) != snapshot(mreg):
            chk.bad("MIRROR-state", [x.label for x in path])
        st, cdig = state_vector(v.reg, n)
        chk.check_node(msgs, [pos[id(x)] for x in path], st, cdig, parent, gidx)
        parent = (st, cdig)
        if dup_mode == "every-prefix":
            snap0 = snapshot(v.reg)
            for d in path:
                r2 = v.ingest(d.wire, t)
                t += 1
                c["real_receipts"] += 1
                c["dup_redeliveries"] += 1
                c["dup:" + r2.why] += 1
                if r2.disp != DUPLICATE:
                    chk.bad("S4-disp", ([x.label for x in path], d.label, r2.disp, r2.why))
                if snapshot(v.reg) != snap0:
                    chk.bad("S4-state", ([x.label for x in path], d.label))
    if dup_mode == "every-prefix" or (dup_mode == "end" and do_end_dups):
        snap0 = snapshot(v.reg)
        for d in path:                    # byte-identical retransmission, then same content re-relayed
            for w in (d.wire, world.rerelayed(d)):
                r2 = v.ingest(w, t)
                t += 1
                c["real_receipts"] += 1
                c["dup_redeliveries"] += 1
                c["dup:" + r2.why] += 1
                if r2.disp != DUPLICATE:
                    chk.bad("S4-disp", ([x.label for x in path], d.label, r2.disp, r2.why))
                if snapshot(v.reg) != snap0:
                    chk.bad("S4-state", ([x.label for x in path], d.label))
    for (_, key, old, new, cause) in v.reg.state_events:
        c["state_event:" + old + "->" + new] += 1
        if (old, new) != (COMMITTED, CONTESTED):
            chk.bad("EVENTS", (key, old, new, cause))
    if v.lost_declared:
        chk.bad("LOST", v.lost_declared)


def real_feed_job(args):
    """Worker: all permutations of one feed's universe (or a random sample of them)."""
    n, extended, shape, dup_mode, sample, seed, dup_every = args
    world = World()
    msgs = build_feed(world, n, shape)
    gidx = {m.seq: i for i, m in enumerate(msgs) if m.genuine}
    chk = Checker(n)
    if sample is None:
        orders = itertools.permutations(msgs)
    else:
        rng = random.Random(seed)
        orders = [rng.sample(msgs, len(msgs)) for _ in range(sample)]
    nperm = 0
    prefixes = set()
    for order in orders:
        real_sequence(world, order, n, chk, dup_mode, gidx, msgs, do_end_dups=(nperm % dup_every == 0))
        nperm += 1
        if sample is None:
            idx = tuple(msgs.index(m) for m in order)
            for j in range(len(idx) + 1):
                prefixes.add(idx[:j])
    chk.c["permutations"] = nperm
    chk.c["distinct_prefix_nodes_covered"] = len(prefixes) if sample is None else 0
    return shape, len(msgs), dict(chk.c), chk.viol, chk.sets


def run_real(n, extended, dup_mode, log, workers=1, sample=None, seed=1, dup_every=1):
    shapes = list(enumerate_shapes(n, extended))
    jobs = [(n, extended, s, dup_mode, sample, seed + i, dup_every) for i, s in enumerate(shapes)]
    jobs.sort(key=lambda j: -sum(x is not None for x in j[2]))   # largest feeds first
    chk = Checker(n)
    t0 = time.perf_counter()
    done = 0
    sizes = Counter()
    if workers > 1:
        ctx = mp.get_context("fork")
        with ctx.Pool(workers) as pool:
            it = pool.imap_unordered(real_feed_job, jobs)
            results = []
            for r in it:
                results.append(r)
                done += 1
                if done % max(1, len(jobs) // 8) == 0 or done == len(jobs):
                    log(f"    ... {done}/{len(jobs)} feeds, {time.perf_counter() - t0:.0f} s")
    else:
        results = []
        for j in jobs:
            results.append(real_feed_job(j))
            done += 1
            if done % max(1, len(jobs) // 8) == 0 or done == len(jobs):
                log(f"    ... {done}/{len(jobs)} feeds, {time.perf_counter() - t0:.0f} s")
    for shape, size, counts, viol, sets in results:
        sizes[size] += 1
        chk.c.update(counts)
        for k, v in viol.items():
            chk.viol[k].extend(v[:MAX_VIOL - len(chk.viol[k])])
        merge_sets(chk.sets, sets, chk)
    dt = time.perf_counter() - t0
    summary = {
        "engine": "real PBTIVerifier", "N": n, "mode": "extended" if extended else "standard",
        "feeds": len(shapes), "feed_sizes": dict(sorted(sizes.items())),
        "orders": "all permutations of each universe" if sample is None else f"{sample} random permutations per feed",
        "duplicate_mode": dup_mode if dup_mode != "end" else f"end of every {dup_every}th permutation",
        "permutations_run": chk.c["permutations"],
        "real_receipts": chk.c["real_receipts"], "prefix_nodes_checked": chk.c["nodes"],
        "distinct_prefix_nodes_covered": chk.c["distinct_prefix_nodes_covered"],
        "distinct_admitted_sets": len(chk.sets), "dup_redeliveries": chk.c["dup_redeliveries"],
        "seconds": round(dt, 2),
        "counts": {k: v for k, v in sorted(chk.c.items()) if not k.startswith("viol:")},
        "violations": {k: chk.c.get("viol:" + k, 0) for k in Checker.CATS},
    }
    return summary, chk


# =============================================================================================== part D: admission
def final_states(v: PBTIVerifier, n: int):
    st, cd = state_vector(v.reg, n)
    return st, cd


def show(st, cd, world: World, n: int):
    out = []
    for k in range(n):
        if st[k] == COMMITTED:
            who = "G" if cd[k] == world.genuine(k).cd else "alternative"
            out.append(f"{k}:COMMITTED[{who}]")
        else:
            out.append(f"{k}:{st[k]}")
    return " ".join(out)


def deliver_schedule(world: World, schedule, n):
    v = world.verifier()
    rec = []
    admitted = []
    for m, t in schedule:
        r = v.ingest(m.wire, t)
        rec.append((m.label, t, r.disp, r.why.split(":")[0]))
        if r.disp in (ACCEPT, CONFLICT):
            admitted.append(m)
    return v, rec, admitted


def admission_examples(log):
    res = {}
    n = 3
    # --------------------------------------------------------------------------- D1: time (h_max)
    log("D1  freshness horizon: policy params h_max_ms = 10000 (all other parameters default)")
    w = World({"h_max_ms": 10_000})
    G0, G1, G2 = (w.genuine(k) for k in range(3))
    F1 = w.alternative(1, G0)          # equivocating alternative for seq 1 (prev = cd(G0))
    log(f"    statements: G0(ts={G0.ts}) G1(ts={G1.ts}, prev=cd(G0)) F1(ts={F1.ts}, prev=cd(G0), other payload)"
        f" G2(ts={G2.ts}, prev=cd(G1))")
    scheds = {
        "a  all prompt":                     [(G0, 5_000), (G1, 5_001), (F1, 5_002), (G2, 5_003)],
        "b  same order, F1 late":            [(G0, 5_000), (G1, 5_001), (F1, 12_001), (G2, 12_002)],
        "c  G1,G2 late (F1 prompt)":         [(G0, 5_000), (F1, 5_001), (G1, 12_500), (G2, 13_500)],
    }
    d1 = {}
    for name, sch in scheds.items():
        v, rec, adm = deliver_schedule(w, sch, n)
        st, cd = final_states(v, n)
        ok_oracle = (st, cd) == oracle(adm, n)
        # replay every permutation of the admitted set promptly on fresh verifiers
        perm_states = set()
        for perm in itertools.permutations(adm):
            v2, _, adm2 = deliver_schedule(w, [(m, 5_000 + i) for i, m in enumerate(perm)], n)
            perm_states.add(final_states(v2, n))
            assert {m.label for m in adm2} == {m.label for m in adm}
        log(f"    schedule {name}:")
        for lab, t, disp, why in rec:
            log(f"        t={t:>6}  {lab:8s} -> {disp}/{why}")
        log(f"        admitted set {{{', '.join(m.label for m in adm)}}}  final: {show(st, cd, w, n)}"
            f"   Rule-L(admitted set) matches: {ok_oracle};"
            f" all {math.factorial(len(adm))} permutations of the admitted set -> {len(perm_states)} distinct final state(s)")
        d1[name] = {"receipts": rec, "admitted": [m.label for m in adm], "final": show(st, cd, w, n),
                    "matches_rule_l": ok_oracle, "permutations_of_admitted_set": math.factorial(len(adm)),
                    "distinct_final_states_over_those_permutations": len(perm_states)}
    res["D1_time_h_max"] = d1
    # --------------------------------------------------------------------------- D2: order (max_seq_jump)
    log("D2  sequence-jump guard: policy params max_seq_jump = 1 (all receipts within 5 ms, far inside h_max)")
    w = World({"max_seq_jump": 1})
    G0, G1, G2 = (w.genuine(k) for k in range(3))
    F2 = w.alternative(2, G1)
    msgs = [G0, G1, F2, G2]
    outcomes = Counter()
    examples = {}
    all_ok = True
    for perm in itertools.permutations(msgs):
        v, rec, adm = deliver_schedule(w, [(m, 5_000 + i) for i, m in enumerate(perm)], n)
        st, cd = final_states(v, n)
        all_ok &= (st, cd) == oracle(adm, n)
        key = (tuple(sorted(m.label for m in adm)), show(st, cd, w, n))
        outcomes[key] += 1
        examples.setdefault(key, (perm, rec))
    log(f"    statements: G0 G1 G2 (genuine chain) and F2 (alternative for seq 2, prev = cd(G1))")
    log(f"    all 24 arrival orders of the same 4 statements -> {len(outcomes)} distinct (admitted set, final state)"
        f" outcomes; final state equals Rule L on the admitted set in every order: {all_ok}")
    d2 = []
    for (adm, fin), cnt in sorted(outcomes.items(), key=lambda kv: -kv[1]):
        perm, rec = examples[(adm, fin)]
        log(f"      {cnt:2d} orders: admitted {{{', '.join(adm)}}} -> {fin};  e.g. order "
            f"{' '.join(m.label for m in perm)}: " + ", ".join(f"{l}:{d}/{y}" for l, _, d, y in rec))
        d2.append({"orders": cnt, "admitted": list(adm), "final": fin,
                   "example_order": [m.label for m in perm], "example_receipts": rec})
    # byte-identical retransmission of a quarantined statement is not a no-op
    v, rec, adm = deliver_schedule(w, [(G0, 5_000), (F2, 5_001), (G1, 5_002), (G2, 5_003), (F2, 5_004)], n)
    st, cd = final_states(v, n)
    log("    retransmission of a QUARANTINED statement: G0, F2, G1, G2, F2(byte-identical again) -> "
        + ", ".join(f"{l}:{d}/{y}" for l, _, d, y in rec) + f"  final: {show(st, cd, w, n)}")
    res["D2_order_max_seq_jump"] = {"outcomes": d2, "all_orders_match_rule_l_on_admitted_set": all_ok,
                                    "retransmitted_quarantined": {"receipts": rec, "final": show(st, cd, w, n)}}
    return res


# =============================================================================================== part A
def validate_clone(log, trials=400, seed=7):
    """clone_registry must be indistinguishable from copy.deepcopy for every state the walk can reach."""
    import copy
    world = World()
    rng = random.Random(seed)
    shapes = list(enumerate_shapes(4, True))
    bad = 0
    for _ in range(trials):
        msgs = build_feed(world, 4, rng.choice(shapes))
        reg = Registry()
        for m in rng.sample(msgs, rng.randint(0, len(msgs))):
            mirror_deliver(reg, m, T0, world.params)
        a, b = clone_registry(reg), copy.deepcopy(reg)
        if snapshot(a) != snapshot(b) or a.state_events != b.state_events or a.by_kid != b.by_kid:
            bad += 1
        nxt = rng.choice(msgs)
        r1, r2 = mirror_deliver(a, nxt, T0 + 1, world.params), mirror_deliver(b, nxt, T0 + 1, world.params)
        if r1 != r2 or snapshot(a) != snapshot(b):
            bad += 1
        if snapshot(reg) != snapshot(copy.deepcopy(reg)):
            bad += 1
    log(f"A   clone_registry vs copy.deepcopy on {trials} random reachable registries: {bad} mismatches")
    return bad


# =============================================================================================== main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", default=DEFAULT_SRC, help="path to the PBTI src/ directory (read-only)")
    ap.add_argument("--n", type=int, default=4, help="number of sequence numbers (slots) for the mirror walk")
    ap.add_argument("--n-ext", type=int, default=4, help="slots for the mirror walk in extended mode (0 = skip)")
    ap.add_argument("--real-n", type=int, default=3, help="slots for the real verifier, every-prefix duplicates")
    ap.add_argument("--real-n-full", type=int, default=4,
                    help="slots for the real verifier, all permutations, duplicates at the end (0 = skip)")
    ap.add_argument("--real-sample", type=int, default=0,
                    help="if > 0: instead of all permutations at --real-n-full, this many random ones per feed")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--dup-every", type=int, default=16,
                    help="in the all-permutations real run, re-deliver duplicates after every k-th permutation")
    ap.add_argument("--log", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "rule_l_bounded_check.log"))
    args = ap.parse_args()

    log = Log(args.log)
    t_start = time.time()
    dig0 = src_digests(SRC)
    log("PBTI Rule L -- bounded exhaustive check against the reference implementation")
    log(f"date (UTC)      : {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")
    log(f"host            : {platform.platform()}, {os.cpu_count()} CPUs, Python {platform.python_version()},"
        f" cryptography {cryptography.__version__}")
    log(f"source          : {SRC}/pbti  (tree digest {tree_digest(dig0)})")
    for fn in ("registry.py", "verifier.py", "envelope.py", "crypto.py", "canonical.py", "identity.py", "policy.py"):
        log(f"                  sha256 {dig0.get(fn)}  {fn}")
    log(f"command         : {' '.join(sys.argv)}")
    log(f"policy params   : defaults {json.dumps(DEFAULT_PARAMS, sort_keys=True)}")
    log(f"identities      : did={DID} ep={EP} kid={KID} wid={WID} wkid={WKID}; receipts at t = {T0} + i ms;"
        f" ts(G_k) = ts(F_k) = 1000 + 1000k ms")
    log("bound           : one device, one epoch, seq 0..N-1, per slot G_k plus at most one alternative F_k;")
    log("                  prev(G_k)=cd(G_{k-1}); standard: prev(F_k) in {cd(G_{k-1}), cd(F_{k-1})};"
        " extended: also null (k>=1)")
    log("")
    summary = {"source_tree_digest": tree_digest(dig0), "source_digests": dig0, "argv": sys.argv}

    summary["A_clone_validation_mismatches"] = validate_clone(log)
    log("")

    runs = []
    log(f"B   mirror engine, exhaustive prefix-tree walk, S4 re-delivery of every admitted statement at every node")
    for n, ext in ((args.n, False), (args.n_ext, True)):
        if n <= 0:
            continue
        s, chk = run_mirror(n, ext, log, workers=args.workers)
        runs.append(s)
        log(f"  B[{s['mode']}, N={n}] feeds={s['feeds']} (sizes {s['feed_sizes']}), distinct contents={s['distinct_contents']}")
        log(f"      nodes explored (set, order pairs incl. repeats across feeds) = {s['nodes_explored']:,}")
        log(f"      distinct admitted sets = {s['distinct_admitted_sets']:,}; distinct (set, order) pairs ="
            f" {s['distinct_set_order_pairs']:,}; lattice pairs (A, A+c) checked = {s['lattice_pairs_checked']:,}")
        log(f"      duplicate re-deliveries checked = {s['dup_redeliveries']:,}; time = {s['seconds']} s")
        cnt = s["counts"]
        p_eq = cnt.get(PREM_EQ, 0)
        p_alt = cnt.get(PREM_ALT, 0)
        p_gap = cnt.get(PREM_GAP, 0)
        log(f"      premises (nodes x slots): equivocation = {p_eq:,}, alternative + genuine successor = {p_alt:,},"
            f" gap-fill (genuine withheld) + genuine successor = {p_gap:,}")
        log(f"      admitted sets with an alternative content authoritative = {s['sets_with_alternative_authoritative']:,}"
            f" (all with genuine content and genuine successor absent, see S3c);"
            f" sets with a CONTESTED slot = {s['sets_with_contested_slot']:,}")
        log(f"      violations: {s['violations']}")
        for k, v in chk.viol.items():
            for x in v[:5]:
                log(f"        {k}: {x}")
    log("")

    log("C   unmodified PBTIVerifier with real Ed25519-signed messages (X.509 identities), compared after every"
        " receipt with the mirror (registry snapshot + disposition) and with Rule L")
    plan = []
    if args.real_n > 0:
        plan += [(args.real_n, False, "every-prefix", None, 1), (args.real_n, True, "every-prefix", None, 1)]
    if args.real_n_full > 0:
        plan += [(args.real_n_full, False, "end", args.real_sample or None, args.dup_every)]
    for n, ext, dup_mode, sample, dup_every in plan:
        log(f"  C[{'extended' if ext else 'standard'}, N={n}, duplicates={dup_mode}"
            + (f" (every {dup_every}th permutation)" if dup_mode == "end" else "")
            + f", {'all permutations' if sample is None else f'{sample} random permutations per feed'}] running ...")
        s, chk = run_real(n, ext, dup_mode, log, workers=args.workers, sample=sample, dup_every=dup_every)
        runs.append(s)
        log(f"      feeds={s['feeds']} (sizes {s['feed_sizes']}); permutations run = {s['permutations_run']:,};"
            f" receipts ingested = {s['real_receipts']:,}")
        log(f"      prefix nodes checked = {s['prefix_nodes_checked']:,} (distinct (set, order) nodes covered ="
            f" {s['distinct_prefix_nodes_covered']:,}); distinct admitted sets = {s['distinct_admitted_sets']:,}")
        log(f"      duplicate re-deliveries checked = {s['dup_redeliveries']:,}"
            f" (RETRY {s['counts'].get('dup:RETRY', 0):,}, SUSPECTED_REPLAY {s['counts'].get('dup:SUSPECTED_REPLAY', 0):,});"
            f" time = {s['seconds']} s")
        disp = {k[5:]: v for k, v in s["counts"].items() if k.startswith("disp:")}
        ev = {k[12:]: v for k, v in s["counts"].items() if k.startswith("state_event:")}
        log(f"      dispositions of first deliveries: {disp}; recorded state events: {ev}")
        log(f"      violations: {s['violations']}")
        for k, v in chk.viol.items():
            for x in v[:5]:
                log(f"        {k}: {x}")
    log("")

    log("D   admission non-determinism (unmodified PBTIVerifier, real signatures)")
    summary["D_admission_examples"] = admission_examples(log)
    log("")

    dig1 = src_digests(SRC)
    changed = sorted(k for k in set(dig0) | set(dig1) if dig0.get(k) != dig1.get(k))
    log(f"source digests unchanged during the run: {not changed}" + (f" (changed: {changed})" if changed else ""))
    total_viol = sum(sum(r["violations"].values()) for r in runs) + summary["A_clone_validation_mismatches"]
    log(f"TOTAL violations over all runs: {total_viol}")
    log(f"total wall time: {time.time() - t_start:.1f} s")
    summary["runs"] = runs
    summary["source_changed_during_run"] = changed
    summary["total_violations"] = total_viol
    log("")
    log("JSON summary:")
    log(json.dumps(summary, indent=1, sort_keys=True, default=str))
    return 0 if total_viol == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
