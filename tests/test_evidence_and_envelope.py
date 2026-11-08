"""Merkle inclusion proofs (RFC 9162 algorithm) and per-field integrity coverage of the envelope (I1)."""
import json
import random

import pytest

from pbti.canonical import canonical_bytes
from pbti.crypto import keypair_from_seed, sha256
from pbti.envelope import LogicalObs, pbti_sign_obs, pbti_wire
from pbti.evidence import inclusion_proof, leaf_hash, merkle_root, verify_inclusion
from pbti.identity import TrustRegistry
from pbti.policy import PolicyStore
from pbti.verifier import ACCEPT, REJECT, PBTIVerifier


@pytest.mark.parametrize("n", [1, 2, 3, 5, 8, 13, 100, 257])
def test_inclusion_proofs(n):
    leaves = [leaf_hash(f"rec-{i}".encode()) for i in range(n)]
    root = merkle_root(leaves)
    for m in range(n):
        p = inclusion_proof(m, leaves)
        assert verify_inclusion(leaves[m], m, n, p, root)
        bad = leaf_hash(b"forged")
        assert not verify_inclusion(bad, m, n, p, root)


def _setup():
    seed = b"unit"
    trust = TrustRegistry(seed)
    dsk, dpk = keypair_from_seed(seed, "dk:d1:1")
    wsk, wpk = keypair_from_seed(seed, "wk:g1:1")
    wid = "spiffe://plant-a.example/cell1/gw1/collector"
    trust.issue("dk:d1:1", "device", "d1", dpk, -60_000, 10 ** 10)
    trust.issue("wk:g1:1", "workload", wid, wpk, -60_000, 10 ** 10)
    doc = {"devices": {"d1": {"assets": ["a1", "a2"], "origin": "device", "schemas": ["telemetry.v1"]}},
           "workloads": {wid: {"relay": ["d1"]}}, "params": {}}
    v = PBTIVerifier(trust, PolicyStore(doc), keypair_from_seed(seed, "verifier"))
    o = LogicalObs("d1", "a1", 0, 0, 1_000, "telemetry.v1", {"temp_c": 70.5, "vib": 2.0}, "m1")
    obs, osig = pbti_sign_obs(o, dsk, "dk:d1:1")
    wire = pbti_wire(obs, osig, wid, "wk:g1:1", wsk, 1_000, "live")
    return v, wire


def test_valid_envelope_accepted():
    v, wire = _setup()
    assert v.ingest(wire, 1_100).disp == ACCEPT


FIELD_MUTATIONS = [
    ("obs", "did", "d2"), ("obs", "aid", "a2"), ("obs", "ep", 1), ("obs", "seq", 1), ("obs", "ts", 999),
    ("obs", "sch", "telemetry.v2"), ("obs", "pl", {"temp_c": 70.6, "vib": 2.0}), ("obs", "kid", "dk:d1:2"),
    ("rel", "wid", "spiffe://plant-a.example/cell2/gw2/collector"), ("rel", "wkid", "wk:g1:2"),
    ("rel", "odig", "A" * 43), ("rel", "rts", 1_001), ("rel", "mode", "buffered"),
    # version, statement type and predecessor link (added in revision 2 so that all 18 protected fields are covered)
    ("obs", "v", 2), ("obs", "typ", "pbti.relay"), ("obs", "prev", "A" * 43), ("rel", "v", 2), ("rel", "typ", "pbti.obs"),
]


@pytest.mark.parametrize("part,field,value", FIELD_MUTATIONS)
def test_every_protected_field_is_covered(part, field, value):
    """Integrity invariant I1: modifying any protected field without re-signing is rejected."""
    v, wire = _setup()
    m = json.loads(wire)
    m[part][field] = value
    r = v.ingest(canonical_bytes(m), 1_100)
    assert r.disp == REJECT, (field, r)
    assert not v.reg.slots, "a rejected receipt must not create registry state"
