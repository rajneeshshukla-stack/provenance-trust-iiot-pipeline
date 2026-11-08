"""Tamper-evident evidence log: Merkle batches (RFC 9162 tree hashing) + signed, chained checkpoints.

leaf hash  = SHA-256(0x00 || canonical(record))
node hash  = SHA-256(0x01 || left || right)
checkpoint = {n, first, count, root, prev, t} signed by the verifier's evidence key; `prev` is the
SHA-256 of the previous checkpoint's canonical bytes, so deleting or reordering batches breaks the
chain. Each checkpoint is copied to an external witness (models anchoring outside the verifier's
administrative domain); a verifier-key holder who rewrites history after anchoring is detected by
comparing against the witness copies.
"""
from __future__ import annotations

from typing import Optional

from .canonical import canonical_bytes
from .crypto import DOMAIN_CKPT, b64u, sha256, sign, verify


def leaf_hash(data: bytes) -> bytes:
    return sha256(b"\x00" + data)


def node_hash(l: bytes, r: bytes) -> bytes:
    return sha256(b"\x01" + l + r)


def _split(n: int) -> int:
    k = 1
    while k << 1 < n:
        k <<= 1
    return k


def merkle_root(leaves: list[bytes]) -> bytes:
    n = len(leaves)
    if n == 0:
        return sha256(b"")
    if n == 1:
        return leaves[0]
    k = _split(n)
    return node_hash(merkle_root(leaves[:k]), merkle_root(leaves[k:]))


def inclusion_proof(m: int, leaves: list[bytes]) -> list[bytes]:
    n = len(leaves)
    if n <= 1:
        return []
    k = _split(n)
    if m < k:
        return inclusion_proof(m, leaves[:k]) + [merkle_root(leaves[k:])]
    return inclusion_proof(m - k, leaves[k:]) + [merkle_root(leaves[:k])]


def verify_inclusion(leaf: bytes, index: int, size: int, proof: list[bytes], root: bytes) -> bool:
    """RFC 9162, Section 2.1.3.2."""
    if index >= size:
        return False
    fn, sn, r = index, size - 1, leaf
    for p in proof:
        if sn == 0:
            return False
        if fn & 1 or fn == sn:
            r = node_hash(p, r)
            if not fn & 1:
                while not fn & 1 and fn != 0:
                    fn >>= 1
                    sn >>= 1
        else:
            r = node_hash(r, p)
        fn >>= 1
        sn >>= 1
    return sn == 0 and r == root


class EvidenceLog:
    def __init__(self, sk, pk, batch: int = 512, enabled: bool = True):
        self.sk, self.pk = sk, pk
        self.batch = batch
        self.enabled = enabled
        self.records: list[bytes] = []
        self.leaves: list[bytes] = []
        self.checkpoints: list[dict] = []
        self.witness: list[dict] = []  # external anchor copies
        self._next = 0
        self.bytes = 0

    def append(self, rec: dict) -> Optional[int]:
        if not self.enabled:
            return None
        b = canonical_bytes(rec)
        self.records.append(b)
        self.leaves.append(leaf_hash(b))
        self.bytes += len(b) + 32
        return len(self.records) - 1

    def checkpoint(self, t_ms: int, force: bool = False) -> Optional[dict]:
        if not self.enabled:
            return None
        pending = len(self.leaves) - self._next
        if pending == 0 or (pending < self.batch and not force):
            return None
        first, count = self._next, pending
        root = merkle_root(self.leaves[first:first + count])
        prev = b64u(sha256(canonical_bytes(self.checkpoints[-1]))) if self.checkpoints else None
        body = {"n": len(self.checkpoints), "first": first, "count": count, "root": b64u(root), "prev": prev, "t": t_ms}
        ck = dict(body, sig=b64u(sign(self.sk, DOMAIN_CKPT, canonical_bytes(body))))
        self.checkpoints.append(ck)
        self.witness.append(dict(ck))
        self._next = first + count
        self.bytes += len(canonical_bytes(ck))
        return ck

    def proof_for(self, idx: int) -> tuple[dict, list[bytes]]:
        for ck in self.checkpoints:
            if ck["first"] <= idx < ck["first"] + ck["count"]:
                leaves = self.leaves[ck["first"]:ck["first"] + ck["count"]]
                return ck, inclusion_proof(idx - ck["first"], leaves)
        raise KeyError("record not yet checkpointed")

    @staticmethod
    def verify_checkpoint_sig(pk, ck: dict) -> bool:
        body = {k: ck[k] for k in ("n", "first", "count", "root", "prev", "t")}
        from .crypto import ub64u
        return verify(pk, DOMAIN_CKPT, canonical_bytes(body), ub64u(ck["sig"]))
