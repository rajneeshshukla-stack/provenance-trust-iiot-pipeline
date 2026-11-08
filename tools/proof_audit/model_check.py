#!/usr/bin/env python3
"""Independent exhaustive checker of the Rule L locality lemma on the PURE MATHEMATICAL MODEL.

Written from the statement in formal/LOCALITY_PROOF.md (Sections 1-3) and paper/main.tex (Proposition 1) only.
It does not import, copy or adapt formal/v4_locality_lifecycle_check.py or formal/rule_l_bounded_check.py.

Model (as stated in the proof):
  identity e = (d, p, q); pred(d, p, q) = (d, p, q-1) for q > 0, none for q = 0
  statement s = (e, c, r): cd(s) = c, prev(s) = r (a digest label, or None for "bottom")
  evidence E = (V, I), V, I : identities -> finite sets of digests
  adm(E, s): V(e) := V(e) u {c};  I(pred e) := I(pred e) u {r}  if q(e) > 0 and r is not None
  cls: ABSENT if V(e) = {} ; else COMMITTED if |V(e) u I(e)| = 1 ; else CONTESTED   (ordered case distinction)
  auth: cls = COMMITTED and not tau(e); tau is not changed by admissions (revocation processing is excluded)
  A(S) = { e(s_i) } u { pred(e(s_i)) : q(e(s_i)) > 0 and prev(s_i) != None }

Encoding for exhaustive enumeration: every identity has a two-letter digest alphabet {0, 1}; its evidence is one
nibble (bit0/bit1: digest 0/1 in V, bit2/bit3: digest 0/1 in I). ALL 16^n nibble vectors are enumerated, i.e. every
evidence state, including states that no delivery history can produce (the lemma quantifies over any E).
For q = 0 the alphabet of prev is also {None, 0, 1}: a non-null prev at q = 0 is the boundary case the lemma says
is ignored (the implementation's parser rejects it; see impl_check.py).

Checks for every (E, S):
  M1 lemma (a): V'(x) = V(x) and I'(x) = I(x) for every x outside A(S)
  M2 lemma (b): |A(S)| <= k + m <= 2k; and |A(S)| = 2k  <=>  the attainment condition stated in the proof
  M3 corollary 1: class and authority (tau = false everywhere, the worst case) unchanged outside A(S);
     number of identities whose evidence / class / authority changes <= |A(S)| <= 2k
  M4 corollary 2: every permutation of S gives the same E' (ordered sequences are enumerated, with repetition)
  M5 absorption: CONTESTED stays CONTESTED; COMMITTED never becomes ABSENT; a version never disappears
Counts: per k, histograms of the number of identities whose evidence, class or authority changed; how often 2k is
attained; how often |A(S)| = 2k (pairwise distinct identities) but fewer than 2k classes change.
A scalar reference engine (Python frozensets, literal transcription of the definitions) cross-validates the
vectorised engine on random samples.
"""
from __future__ import annotations

import argparse
import itertools
import json
import platform
import random
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np

ABSENT, COMMITTED, CONTESTED = 0, 1, 2
CLS_NAME = {ABSENT: "ABSENT", COMMITTED: "COMMITTED", CONTESTED: "CONTESTED"}


# ----------------------------------------------------------------------------------------------- the model
class Universe:
    def __init__(self, name: str, devices: int, epochs: int, qmax: int):
        self.name = name
        self.ids = [(d, p, q) for d in range(devices) for p in range(epochs) for q in range(qmax + 1)]
        self.index = {e: i for i, e in enumerate(self.ids)}
        self.n = len(self.ids)
        self.bounds = {"devices": devices, "epochs": epochs, "q": [0, qmax], "digests_per_identity": 2}

    @staticmethod
    def pred(e):
        d, p, q = e
        return (d, p, q - 1) if q > 0 else None

    def statements(self):
        """Every statement over the universe: identity x cd in {0,1} x prev in {None, 0, 1}."""
        return [(e, c, r) for e in self.ids for c in (0, 1) for r in (None, 0, 1)]


def affected(S, U: Universe) -> set:
    """A(S) exactly as defined in the lemma."""
    out = set()
    for (e, _c, r) in S:
        out.add(e)
        if e[2] > 0 and r is not None:
            out.add(U.pred(e))
    return out


def attainment_condition(S) -> bool:
    """The proof's stated condition for |A(S)| = 2k, transcribed literally:
    no statement has q = 0 or prev = bottom, no two statements share an identity or a predecessor, and no
    statement's identity is another's predecessor."""
    if any(e[2] == 0 or r is None for (e, _c, r) in S):
        return False
    ids = [e for (e, _c, _r) in S]
    preds = [Universe.pred(e) for e in ids]
    if len(set(ids)) != len(ids) or len(set(preds)) != len(preds):
        return False
    for i, e in enumerate(ids):
        for j, pe in enumerate(preds):
            if i != j and e == pe:
                return False
    return True


# scalar reference engine (literal transcription of the definitions, frozensets)
def s_adm(V: dict, I: dict, s, U: Universe):
    e, c, r = s
    V = dict(V)
    V[e] = V.get(e, frozenset()) | {c}
    if e[2] > 0 and r is not None:
        I = dict(I)
        pe = U.pred(e)
        I[pe] = I.get(pe, frozenset()) | {r}
    return V, I


def s_cls(V: dict, I: dict, e) -> int:
    v = V.get(e, frozenset())
    if not v:
        return ABSENT
    return COMMITTED if len(v | I.get(e, frozenset())) == 1 else CONTESTED


def nibble_to_sets(nib: int):
    v = frozenset(x for x in (0, 1) if nib >> x & 1)
    i = frozenset(x for x in (0, 1) if nib >> (2 + x) & 1)
    return v, i


# vectorised engine
LUT_CLS = np.zeros(16, dtype=np.uint8)
for _nib in range(16):
    _v, _i = _nib & 3, (_nib >> 2) & 3
    LUT_CLS[_nib] = ABSENT if _v == 0 else (COMMITTED if bin(_v | _i).count("1") == 1 else CONTESTED)
# the proof's class definition read literally (without an ordered case distinction) is ambiguous when V = {} and
# I != {}: both "ABSENT if V = {}" and "COMMITTED/CONTESTED if |V u I| = 1 / >= 2" apply
LUT_LITERAL_AMBIGUOUS = np.array([(n & 3) == 0 and ((n >> 2) & 3) != 0 for n in range(16)])


def all_states(n: int) -> np.ndarray:
    N = 16 ** n
    idx = np.arange(N, dtype=np.uint64)
    st = np.empty((N, n), dtype=np.uint8)
    for j in range(n):
        st[:, j] = ((idx >> np.uint64(4 * j)) & np.uint64(15)).astype(np.uint8)
    return st


def apply_vec(st: np.ndarray, S, U: Universe) -> np.ndarray:
    out = st.copy()
    for (e, c, r) in S:                              # statements applied one after the other, in sequence order
        out[:, U.index[e]] |= np.uint8(1 << c)
        if e[2] > 0 and r is not None:
            out[:, U.index[U.pred(e)]] |= np.uint8(4 << r)
    return out


class Tally:
    def __init__(self, n: int):
        self.n = n
        self.by_k: dict = {}
        self.violations: list = []
        self.n_violations = 0
        self.examples: dict = {}

    def k(self, k):
        if k not in self.by_k:
            z = lambda: np.zeros(self.n + 1, dtype=np.int64)  # noqa: E731
            self.by_k[k] = {"cases": 0, "sequences": 0, "hist_A": Counter(), "hist_evidence": z(), "hist_class": z(),
                            "hist_authority": z(), "hist_class_or_authority": z(), "attained_class_2k": 0,
                            "attained_authority_2k": 0, "attained_evidence_2k": 0, "A_eq_2k_cases": 0,
                            "A_eq_2k_but_class_lt_2k": 0, "A_eq_2k_but_evidence_lt_2k": 0, "max_class": 0,
                            "max_evidence": 0, "max_authority": 0}
        return self.by_k[k]

    def violation(self, kind, U, S, st_row=None):
        self.n_violations += 1
        if len(self.violations) < 20:
            self.violations.append({"kind": kind, "S": [list(map(str, s)) for s in S],
                                    "E": None if st_row is None else [int(x) for x in st_row]})

    def as_json(self):
        out = {}
        for k, t in sorted(self.by_k.items()):
            out[str(k)] = {kk: (vv.tolist() if isinstance(vv, np.ndarray) else
                                ({str(a): b for a, b in sorted(vv.items())} if isinstance(vv, Counter) else vv))
                           for kk, vv in t.items()}
        return out


def evaluate_block(U: Universe, st0: np.ndarray, cls0: np.ndarray, S, perms, tally: Tally, collect_examples=True):
    """Evaluate one batch S (and its permutations) against a block of evidence states."""
    k = len(S)
    t = tally.k(k)
    st1 = apply_vec(st0, S, U)
    # M4: every permutation gives the same E'
    for P in perms:
        if P is S:
            continue
        if not np.array_equal(apply_vec(st0, P, U), st1):
            tally.violation("M4-order", U, P)
    cls1 = LUT_CLS[st1]
    A = affected(S, U)
    m = sum(1 for (e, _c, r) in S if e[2] > 0 and r is not None)
    # M2 (state independent)
    if not (len(A) <= k + m <= 2 * k):
        tally.violation("M2-bound", U, S)
    if (len(A) == 2 * k) != attainment_condition(S):
        tally.violation("M2-attainment-condition", U, S)
    inside = np.zeros(U.n, dtype=bool)
    for e in A:
        inside[U.index[e]] = True
    outside = ~inside
    evch = st1 != st0
    clch = cls1 != cls0
    auch = (cls1 == COMMITTED) != (cls0 == COMMITTED)          # authority with tau = false everywhere
    caud = clch | auch
    if outside.any():
        bad_ev = evch[:, outside].any(axis=1)
        bad_cl = (clch[:, outside] | auch[:, outside]).any(axis=1)
        if bad_ev.any():
            r = int(np.flatnonzero(bad_ev)[0])
            tally.violation("M1-evidence-outside-A", U, S, st0[r])
        if bad_cl.any():
            r = int(np.flatnonzero(bad_cl)[0])
            tally.violation("M3-class-or-authority-outside-A", U, S, st0[r])
    # M5 absorption / monotonicity
    bad_abs = ((cls0 == CONTESTED) & (cls1 != CONTESTED)).any(axis=1) | \
              ((cls0 == COMMITTED) & (cls1 == ABSENT)).any(axis=1) | ((st0 & ~st1) != 0).any(axis=1)
    if bad_abs.any():
        r = int(np.flatnonzero(bad_abs)[0])
        tally.violation("M5-absorption", U, S, st0[r])
    ne, nc, na, nca = evch.sum(1), clch.sum(1), auch.sum(1), caud.sum(1)
    if (nca > len(A)).any() or (ne > len(A)).any():
        tally.violation("M3-count-exceeds-A", U, S)
    t["cases"] += st0.shape[0] * len(perms)
    t["sequences"] += len(perms)
    t["hist_A"][len(A)] += st0.shape[0] * len(perms)
    w = len(perms)
    t["hist_evidence"] += np.bincount(ne, minlength=U.n + 1)[:U.n + 1] * w
    t["hist_class"] += np.bincount(nc, minlength=U.n + 1)[:U.n + 1] * w
    t["hist_authority"] += np.bincount(na, minlength=U.n + 1)[:U.n + 1] * w
    t["hist_class_or_authority"] += np.bincount(nca, minlength=U.n + 1)[:U.n + 1] * w
    t["max_class"] = max(t["max_class"], int(nc.max()))
    t["max_evidence"] = max(t["max_evidence"], int(ne.max()))
    t["max_authority"] = max(t["max_authority"], int(na.max()))
    att_c = nc == 2 * k
    t["attained_class_2k"] += int(att_c.sum()) * w
    t["attained_authority_2k"] += int((na == 2 * k).sum()) * w
    t["attained_evidence_2k"] += int((ne == 2 * k).sum()) * w
    if len(A) == 2 * k:
        t["A_eq_2k_cases"] += st0.shape[0] * w
        t["A_eq_2k_but_class_lt_2k"] += int((nc < 2 * k).sum()) * w
        t["A_eq_2k_but_evidence_lt_2k"] += int((ne < 2 * k).sum()) * w
        if collect_examples and f"A2k_class_lt_2k_k{k}" not in tally.examples and (nc < 2 * k).any():
            r = int(np.flatnonzero(nc < 2 * k)[0])
            tally.examples[f"A2k_class_lt_2k_k{k}"] = describe(U, st0[r], S, cls0[r], cls1[r])
    if collect_examples and att_c.any() and f"attained_k{k}" not in tally.examples:
        r = int(np.flatnonzero(att_c)[0])
        tally.examples[f"attained_k{k}"] = describe(U, st0[r], S, cls0[r], cls1[r])


def describe(U, row, S, c0, c1):
    ev = {}
    for j, e in enumerate(U.ids):
        v, i = nibble_to_sets(int(row[j]))
        if v or i:
            ev[str(e)] = {"V": sorted(v), "I": sorted(i)}
    return {"E": ev, "S": [{"e": str(e), "cd": c, "prev": r} for (e, c, r) in S],
            "class_before": {str(e): CLS_NAME[int(c0[j])] for j, e in enumerate(U.ids)},
            "class_after": {str(e): CLS_NAME[int(c1[j])] for j, e in enumerate(U.ids)}}


def multisets(stmts, k):
    return itertools.combinations_with_replacement(range(len(stmts)), k)


def distinct_perms(seq):
    """Distinct orderings of seq; the first one is seq itself (itertools yields the identity permutation first)."""
    return list(dict.fromkeys(tuple(p) for p in itertools.permutations(seq)))


# ----------------------------------------------------------------------------------------------- runs
def run_exhaustive(U: Universe, kmax: int, log) -> dict:
    """ALL 16^n evidence states x ALL ordered sequences (with repetition) of k <= kmax statements."""
    t0 = time.time()
    st0 = all_states(U.n)
    cls0 = LUT_CLS[st0]
    stmts = U.statements()
    tally = Tally(U.n)
    for k in range(1, kmax + 1):
        tk = time.time()
        for ms in multisets(stmts, k):
            S = tuple(stmts[i] for i in ms)
            perms = distinct_perms(S)
            evaluate_block(U, st0, cls0, perms[0], perms, tally)
        log(f"[A:{U.name}] k={k}: {tally.by_k[k]['sequences']} sequences x {st0.shape[0]} states = "
            f"{tally.by_k[k]['cases']} cases, max class changes {tally.by_k[k]['max_class']}, "
            f"2k attained {tally.by_k[k]['attained_class_2k']}, violations so far {tally.n_violations} "
            f"({time.time() - tk:.1f}s)")
    amb = int(LUT_LITERAL_AMBIGUOUS[st0].any(axis=1).sum())
    return {"universe": U.name, "bounds": U.bounds, "identities": U.n, "states": int(st0.shape[0]),
            "statements": len(stmts), "kmax": kmax, "exhaustive": True, "by_k": tally.as_json(),
            "violations": tally.violations, "n_violations": tally.n_violations, "examples": tally.examples,
            "states_where_literal_class_definition_is_ambiguous": amb, "seconds": round(time.time() - t0, 1)}


def random_state_pool(U: Universe, size: int, rng: np.random.Generator) -> np.ndarray:
    """Mixture: uniform nibbles (any evidence state), sparse states, and 'mostly consistent' chains."""
    a = rng.integers(0, 16, size=(size // 3, U.n), dtype=np.uint8)
    b = rng.integers(0, 16, size=(size // 3, U.n), dtype=np.uint8)
    b[rng.random(b.shape) < 0.6] = 0
    c = np.zeros((size - 2 * (size // 3), U.n), dtype=np.uint8)
    # a consistent genuine chain (V = {0}, successor link names 0) with random perturbations
    for j, e in enumerate(U.ids):
        succ = (e[0], e[1], e[2] + 1)
        has_v = rng.random(c.shape[0]) < 0.7
        c[has_v, j] |= 1
        if succ in U.index:
            c[rng.random(c.shape[0]) < 0.6, j] |= 4
    pert = rng.random(c.shape) < 0.1
    c[pert] = rng.integers(0, 16, size=int(pert.sum()), dtype=np.uint8)
    return np.concatenate([a, b, c])


def run_sampled(U: Universe, pool_size: int, n_seq_k3: int, seed: int, log) -> dict:
    """Large universe: a pool of random evidence states; all sequences for k <= 2, a random sample for k = 3."""
    t0 = time.time()
    rng = np.random.default_rng(seed)
    st0 = random_state_pool(U, pool_size, rng)
    cls0 = LUT_CLS[st0]
    stmts = U.statements()
    tally = Tally(U.n)
    for k in (1, 2):
        for ms in multisets(stmts, k):
            S = tuple(stmts[i] for i in ms)
            perms = distinct_perms(S)
            evaluate_block(U, st0, cls0, perms[0], perms, tally)
        log(f"[B:{U.name}] k={k} (all sequences, {pool_size} random states): {tally.by_k[k]['cases']} cases, "
            f"max class changes {tally.by_k[k]['max_class']}, violations so far {tally.n_violations}")
    prng = random.Random(seed)
    sub = st0[: max(1, pool_size // 4)]
    subc = cls0[: sub.shape[0]]
    for _ in range(n_seq_k3):
        S = tuple(prng.choice(stmts) for _ in range(3))
        perms = distinct_perms(S)
        evaluate_block(U, sub, subc, S, [S] + [p for p in perms if p != S], tally)
    log(f"[B:{U.name}] k=3 ({n_seq_k3} random sequences incl. all their permutations, {sub.shape[0]} states): "
        f"{tally.by_k[3]['cases']} cases, max class changes {tally.by_k[3]['max_class']}, "
        f"violations so far {tally.n_violations}")
    return {"universe": U.name, "bounds": U.bounds, "identities": U.n, "state_pool": pool_size,
            "statements": len(stmts), "exhaustive": False, "seed": seed, "by_k": tally.as_json(),
            "violations": tally.violations, "n_violations": tally.n_violations, "examples": tally.examples,
            "seconds": round(time.time() - t0, 1)}


def run_six_identity_attainment(log, chunk: int = 1 << 20) -> dict:
    """One feed, q in 0..5 (6 identities), ALL 16^6 evidence states, for every batch of k = 3 statements with
    |A(S)| = 6 (statements at q = 1, 3, 5 with non-null prev): how often are all 2k = 6 classes changed?"""
    t0 = time.time()
    U = Universe("1dev_1ep_q0-5", 1, 1, 5)
    batches = []
    for c1, r1, c3, r3, c5, r5 in itertools.product((0, 1), repeat=6):
        batches.append(((((0, 0, 1), c1, r1)), ((0, 0, 3), c3, r3), ((0, 0, 5), c5, r5)))
    tally = Tally(U.n)
    N = 16 ** U.n
    for lo in range(0, N, chunk):
        idx = np.arange(lo, min(N, lo + chunk), dtype=np.uint64)
        st0 = np.empty((idx.shape[0], U.n), dtype=np.uint8)
        for j in range(U.n):
            st0[:, j] = ((idx >> np.uint64(4 * j)) & np.uint64(15)).astype(np.uint8)
        cls0 = LUT_CLS[st0]
        for S in batches:
            evaluate_block(U, st0, cls0, S, [S], tally, collect_examples=(lo == 0))
    t = tally.by_k[3]
    log(f"[C:{U.name}] k=3, {len(batches)} batches with |A(S)|=6 x {N} states = {t['cases']} cases: "
        f"6 classes changed in {t['attained_class_2k']}, fewer in {t['A_eq_2k_but_class_lt_2k']}, "
        f"violations {tally.n_violations} ({time.time() - t0:.1f}s)")
    return {"universe": U.name, "bounds": U.bounds, "states": N, "batches": len(batches), "by_k": tally.as_json(),
            "violations": tally.violations, "n_violations": tally.n_violations, "examples": tally.examples,
            "seconds": round(time.time() - t0, 1)}


def cross_validate(U: Universe, n: int, seed: int) -> dict:
    """Scalar (frozenset) engine vs vectorised engine on random (state, sequence) pairs."""
    rng = random.Random(seed)
    stmts = U.statements()
    mism = 0
    for _ in range(n):
        row = np.array([rng.randrange(16) for _ in range(U.n)], dtype=np.uint8)
        S = tuple(rng.choice(stmts) for _ in range(rng.randint(1, 3)))
        V, I = {}, {}
        for j, e in enumerate(U.ids):
            v, i = nibble_to_sets(int(row[j]))
            if v:
                V[e] = v
            if i:
                I[e] = i
        V1, I1 = V, I
        for s in S:
            V1, I1 = s_adm(V1, I1, s, U)
        out = apply_vec(row[None, :], S, U)[0]
        for j, e in enumerate(U.ids):
            v, i = nibble_to_sets(int(out[j]))
            if v != V1.get(e, frozenset()) or i != I1.get(e, frozenset()) or LUT_CLS[out[j]] != s_cls(V1, I1, e):
                mism += 1
                break
    return {"universe": U.name, "pairs": n, "mismatches": mism}


def tightness_construction(log) -> dict:
    """The proof's tightness example, made concrete in 2 devices x 2 epochs x q 0..3 (scalar engine).
    Base: genuine chain in every feed (V(e) = {0}, successor link names 0). Batch: k equivocations (cd 1, prev 1)
    at pairwise non-adjacent q (q in {1, 3} of each feed). Also the gap-fill variant (no genuine version at q)."""
    U = Universe("2dev_2ep_q0-3", 2, 2, 3)
    res = {}
    for variant in ("equivocation", "gap_fill_no_successor", "gap_fill_with_successor_link"):
        rows = []
        targets = [(d, p, q) for d in (0, 1) for p in (0, 1) for q in (1, 3)]
        for k in range(1, len(targets) + 1):
            V, I = {}, {}
            for e in U.ids:
                V[e] = frozenset({0})
                if e[2] < 3:
                    I[e] = frozenset({0})
            for e in targets[:k]:
                if variant != "equivocation":
                    V.pop(e)                      # genuine version suppressed
                if variant == "gap_fill_no_successor":
                    I.pop(e, None)                # and no successor link for it
            S = [(e, 1, 1) for e in targets[:k]]
            V1, I1 = V, I
            for s in S:
                V1, I1 = s_adm(V1, I1, s, U)
            ch_cls = [e for e in U.ids if s_cls(V, I, e) != s_cls(V1, I1, e)]
            contested_new = [e for e in U.ids if s_cls(V1, I1, e) == CONTESTED and s_cls(V, I, e) != CONTESTED]
            lost_auth = [e for e in U.ids if s_cls(V, I, e) == COMMITTED and s_cls(V1, I1, e) != COMMITTED]
            gained_auth = [e for e in U.ids if s_cls(V, I, e) != COMMITTED and s_cls(V1, I1, e) == COMMITTED]
            rows.append({"k": k, "A": len(affected(S, U)), "class_changes": len(ch_cls),
                         "newly_contested": len(contested_new), "authority_lost": len(lost_auth),
                         "authority_gained": len(gained_auth)})
        res[variant] = rows
        log(f"[T] {variant}: " + ", ".join(f"k={r['k']}: A={r['A']} cls={r['class_changes']} "
                                           f"contested={r['newly_contested']}" for r in rows))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "results" / "model_check.json"))
    ap.add_argument("--kmax", type=int, default=3)
    ap.add_argument("--pool", type=int, default=4096)
    ap.add_argument("--k3-sample", type=int, default=20000)
    ap.add_argument("--skip-six", action="store_true")
    a = ap.parse_args()
    lines = []

    def log(m):
        print(m, flush=True)
        lines.append(m)

    t0 = time.time()
    res = {"python": platform.python_version(), "numpy": np.__version__, "script": str(Path(__file__).resolve()),
           "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    res["cross_validation"] = [cross_validate(Universe("1dev_1ep_q0-3", 1, 1, 3), 20000, 11),
                               cross_validate(Universe("2dev_2ep_q0-3", 2, 2, 3), 20000, 12)]
    log(f"[X] cross-validation scalar vs vectorised: {res['cross_validation']}")
    res["exhaustive"] = [run_exhaustive(Universe("1dev_1ep_q0-3", 1, 1, 3), a.kmax, log),
                         run_exhaustive(Universe("1dev_2ep_q0-1", 1, 2, 1), a.kmax, log),
                         run_exhaustive(Universe("2dev_1ep_q0-1", 2, 1, 1), a.kmax, log)]
    res["sampled"] = [run_sampled(Universe("2dev_2ep_q0-3", 2, 2, 3), a.pool, a.k3_sample, 7, log)]
    if not a.skip_six:
        res["six_identity_attainment"] = run_six_identity_attainment(log)
    res["tightness_construction"] = tightness_construction(log)
    total_v = sum(r["n_violations"] for r in res["exhaustive"] + res["sampled"]) + \
        (res["six_identity_attainment"]["n_violations"] if "six_identity_attainment" in res else 0) + \
        sum(c["mismatches"] for c in res["cross_validation"])
    res["total_violations"] = total_v
    res["seconds_total"] = round(time.time() - t0, 1)
    res["log"] = lines
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=1, default=str))
    log(f"total violations {total_v}; {res['seconds_total']} s -> {a.out}")
    return 0 if total_v == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
