"""Cryptographic primitives used by PBTI. No new primitives are introduced.

* Ed25519 signatures (RFC 8032) via the `cryptography` package (OpenSSL backend).
* SHA-256 digests.
* Domain separation: every signature is computed over DOMAIN || 0x00 || canonical-bytes so that a
  signature produced for one statement type can never be accepted as another statement type.
* Deterministic key derivation from an experiment seed is used ONLY for reproducible experiments;
  production deployments must generate keys inside secure elements / TPMs (see THREAT_MODEL.md).
"""
from __future__ import annotations

import base64
import hashlib

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

DOMAIN_OBS = b"PBTI-v1/observation\x00"
DOMAIN_REL = b"PBTI-v1/relay\x00"
DOMAIN_CKPT = b"PBTI-v1/checkpoint\x00"
DOMAIN_REVIEW = b"PBTI-v1/quarantine-review\x00"  # V3: signed reviewer decisions
DOMAIN_B3 = b"B3-v1/provenance-record\x00"
DOMAIN_B3LEDGER = b"B3-v1/ledger-checkpoint\x00"


def b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")


def ub64u(s: str) -> bytes:
    if not isinstance(s, str):
        raise TypeError("base64url field must be a string")
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def sha256(b: bytes) -> bytes:
    return hashlib.sha256(b).digest()


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def keypair_from_seed(seed: bytes, label: str) -> tuple[Ed25519PrivateKey, Ed25519PublicKey]:
    """Reproducible key derivation for experiments (NOT for production)."""
    sk = Ed25519PrivateKey.from_private_bytes(hashlib.sha256(seed + b"|" + label.encode()).digest())
    return sk, sk.public_key()


def sign(sk: Ed25519PrivateKey, domain: bytes, msg: bytes) -> bytes:
    return sk.sign(domain + msg)


def verify(pk: Ed25519PublicKey, domain: bytes, msg: bytes, sig: bytes) -> bool:
    try:
        pk.verify(sig, domain + msg)
        return True
    except (InvalidSignature, ValueError):
        return False


def pub_raw(pk: Ed25519PublicKey) -> bytes:
    return pk.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
