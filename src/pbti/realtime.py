"""Shared set-up for the wall-clock experiments (in-process throughput and MQTT end-to-end).

Both the publisher (edge) and the verifier (cloud) processes rebuild the same identities and policy
deterministically from the experiment seed; private keys are only used on the edge side.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

from .baselines import B1Conventional, B2ZeroTrust, B3Provenance
from .crypto import b64u, keypair_from_seed
from .envelope import (LogicalObs, b1_wire, b2_wire, b3_record, b3_wire_from_record, pbti_content_digest,
                       pbti_sign_obs, pbti_wire)
from .identity import TrustRegistry
from .policy import PolicyStore
from .store import MemoryStore, SQLiteStore
from .verifier import PBTIVerifier, VerifierConfig

FAR = 10 * 365 * 86_400_000


@dataclass
class Topology:
    seed: int
    n_gw: int
    dev_per_gw: int
    legacy_per_gw: int = 1

    def dids(self, g):
        return [f"pa-c{g}-d{j:02d}" for j in range(1, self.dev_per_gw + 1)]

    def wid(self, g):
        return f"spiffe://plant-a.example/cell{g}/gw{g}/collector"

    def legacy(self, j):
        return j <= self.legacy_per_gw


def build_identity(topo: Topology, use_x509: bool = True):
    seedb = f"pbti-seed-{topo.seed}".encode()
    trust = TrustRegistry(seedb, use_x509=use_x509)
    devices, workloads, keys = {}, {}, {}
    for g in range(1, topo.n_gw + 1):
        kid = f"wk:gw{g}:1"
        sk, pk = keypair_from_seed(seedb, kid)
        trust.issue(kid, "workload", topo.wid(g), pk, -60_000, FAR)
        keys[topo.wid(g)] = (sk, kid)
        for j, did in enumerate(topo.dids(g), start=1):
            leg = topo.legacy(j)
            if not leg:
                dk = f"dk:{did}:1"
                dsk, dpk = keypair_from_seed(seedb, dk)
                trust.issue(dk, "device", did, dpk, -60_000, FAR)
                keys[did] = (dsk, dk)
            devices[did] = {"assets": [did.replace("-d", "-a")], "origin": "gateway" if leg else "device",
                            "schemas": ["telemetry.v1"], "active": True}
        workloads[topo.wid(g)] = {"relay": topo.dids(g), "active": True}
    policy = PolicyStore({"devices": devices, "workloads": workloads, "params": {}}, 0)
    vkeys = keypair_from_seed(seedb, "verifier-evidence-key")
    return trust, policy, keys, vkeys


def make_system(name: str, trust, policy, vkeys, store=None, profile=False):
    cfg = VerifierConfig(profile=profile)
    if name == "PBTI":
        return PBTIVerifier(trust, policy, vkeys, store=store, cfg=cfg)
    if name == "B1":
        return B1Conventional(trust, policy, store=store, cfg=cfg)
    if name == "B2":
        return B2ZeroTrust(trust, policy, store=store, cfg=cfg)
    if name == "B3":
        return B3Provenance(trust, policy, vkeys, store=store, cfg=cfg)
    if name == "B4":    # V3: wall-clock runs of the revision-2 strongest combination (PBTI wire format)
        from .baselines import B4Combined
        return B4Combined(trust, policy, vkeys, store=store, cfg=cfg)
    if name in ("B5", "B5S"):   # V3: feed-level baseline (PBTI wire format; no reviewer in wall-clock runs)
        from .b5 import B5FeedLevel
        return B5FeedLevel(trust, policy, vkeys, store=store, cfg=cfg, recovery=(name == "B5"))
    raise ValueError(name)


class EdgeEncoder:
    """Real-time edge side: produces the wire bytes a gateway would publish for one observation,
    including device-side signing (signing devices) and relay signing (PBTI)."""

    def __init__(self, system: str, topo: Topology, keys: dict):
        self.system, self.topo, self.keys = system, topo, keys
        self.state: dict[str, list] = {}  # did -> [ep, seq, prev]
        self.n = 0

    def encode(self, g: int, j: int, t_ms: int, pl: dict) -> bytes:
        did = self.topo.dids(g)[j - 1]
        aid = did.replace("-d", "-a")
        wid = self.topo.wid(g)
        st = self.state.setdefault(did, [g * 1000 if self.topo.legacy(j) else 0, 0, None])
        self.n += 1
        mid = f"{self.n:016x}"
        o = LogicalObs(did, aid, st[0], st[1], t_ms, "telemetry.v1", pl, mid, st[2])
        st[1] += 1
        s = self.system
        if s == "B1":
            return b1_wire(o, wid)
        if s == "B2":
            return b2_wire(o, wid)
        if s == "B3":
            sk, kid = self.keys[wid] if self.topo.legacy(j) else self.keys[did]
            return b3_wire_from_record(b3_record(o, kid), sk)
        sk, kid = self.keys[wid] if self.topo.legacy(j) else self.keys[did]
        obs, osig = pbti_sign_obs(o, sk, kid)
        st[2] = b64u(pbti_content_digest(obs))
        wsk, wkid = self.keys[wid]
        return pbti_wire(obs, osig, wid, wkid, wsk, t_ms, "live")
