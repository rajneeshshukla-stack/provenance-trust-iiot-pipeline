"""Rule L properties: convergence under arbitrary delivery order (I9), contest absorption, idempotency (I3)."""
import itertools
import random

from pbti.canonical import canonical_bytes
from pbti.crypto import b64u, keypair_from_seed, sha256
from pbti.envelope import LogicalObs, pbti_content_digest, pbti_sign_obs, pbti_wire
from pbti.identity import TrustRegistry
from pbti.policy import PolicyStore
from pbti.registry import COMMITTED, CONTESTED
from pbti.verifier import PBTIVerifier

SEED = b"rule-l"
WID = "spiffe://plant-a.example/cell1/gw1/collector"


def world():
    trust = TrustRegistry(SEED, use_x509=False)
    dsk, dpk = keypair_from_seed(SEED, "dk:d1:1")
    wsk, wpk = keypair_from_seed(SEED, "wk:g1:1")
    trust.issue("dk:d1:1", "device", "d1", dpk, -60_000, 10 ** 10)
    trust.issue("wk:g1:1", "workload", WID, wpk, -60_000, 10 ** 10)
    doc = {"devices": {"d1": {"assets": ["a1"], "origin": "device", "schemas": ["s"]}},
           "workloads": {WID: {"relay": ["d1"]}}, "params": {}}
    return trust, PolicyStore(doc), dsk, wsk


def chain(dsk, wsk, n, forge_at=None, forged_prev_ok=True):
    """Legit chain of n statements; optionally a forged alternative for slot forge_at."""
    wires, prev = [], None
    digests = []
    for i in range(n):
        o = LogicalObs("d1", "a1", 0, i, 1_000 + i * 1_000, "s", {"x": float(i)}, f"m{i}", prev)
        obs, osig = pbti_sign_obs(o, dsk, "dk:d1:1")
        wires.append(pbti_wire(obs, osig, WID, "wk:g1:1", wsk, 1_000 + i * 1_000, "live"))
        digests.append(prev)
        prev = b64u(pbti_content_digest(obs))
    extra = []
    if forge_at is not None:
        o = LogicalObs("d1", "a1", 0, forge_at, 1_000 + forge_at * 1_000, "s", {"x": -1.0}, "mf",
                       digests[forge_at] if forged_prev_ok else None)
        obs, osig = pbti_sign_obs(o, dsk, "dk:d1:1")
        extra.append(pbti_wire(obs, osig, WID, "wk:g1:1", wsk, 1_000, "live"))
    return wires, extra


def final_states(order):
    trust, pol, dsk, wsk = world()
    v = PBTIVerifier(trust, pol, keypair_from_seed(SEED, "v"))
    for i, w in enumerate(order):
        v.ingest(w, 20_000 + i)
    return {k: s.state() for k, s in v.reg.slots.items()}, sorted(k for k, _ in v.authoritative())


def test_convergence_under_permutations_duplicates_and_forgery():
    trust, pol, dsk, wsk = world()
    legit, forged = chain(dsk, wsk, 6, forge_at=3)
    base = legit + forged
    rng = random.Random(42)
    ref = None
    for _ in range(60):
        order = base + [rng.choice(base) for _ in range(4)]  # duplicates
        rng.shuffle(order)
        st = final_states(order)
        if ref is None:
            ref = st
        assert st == ref
    states, auth = ref
    assert states[("d1", 0, 3)] == CONTESTED
    assert ("d1", 0, 3) not in auth and len(auth) == 5


def test_gap_fill_rejected_when_successor_known():
    trust, pol, dsk, wsk = world()
    legit, forged = chain(dsk, wsk, 5, forge_at=2)
    # successor (seq 3) arrives first, legit seq 2 is withheld, forged seq 2 then arrives
    states, auth = final_states([legit[0], legit[1], legit[3], forged[0], legit[4]])
    assert states[("d1", 0, 2)] == CONTESTED
    assert ("d1", 0, 2) not in auth


def test_idempotent_retries():
    trust, pol, dsk, wsk = world()
    legit, _ = chain(dsk, wsk, 4)
    states, auth = final_states(legit * 3)
    assert len(auth) == 4 and all(s == COMMITTED for s in states.values())
