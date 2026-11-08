"""Identity plane: an X.509 certificate authority, credential lifecycle (rotation, revocation with
compromise time) and the verifier's cached view of key status.

Device certificates carry a URI SAN  urn:pbti:device:<did>; workload certificates carry an
X.509-SVID-style URI SAN spiffe://<trust-domain>/<path>. The prototype issues the certificates
itself (it does not run SPIRE); SPIRE would issue equivalent X.509-SVIDs after node/workload
attestation, which is outside the scope of the evaluated mechanism.

Time is an integer number of milliseconds since BASE (virtual or wall clock, injected by caller).
"""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Optional

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.x509.oid import NameOID

from .crypto import keypair_from_seed

BASE = _dt.datetime(2026, 1, 1, tzinfo=_dt.timezone.utc)
BASE_EPOCH_MS = int(BASE.timestamp() * 1000)


def ms_to_dt(ms: int) -> _dt.datetime:
    return BASE + _dt.timedelta(milliseconds=ms)


def dt_to_ms(d: _dt.datetime) -> int:
    if d.tzinfo is None:
        d = d.replace(tzinfo=_dt.timezone.utc)
    return int((d - BASE).total_seconds() * 1000)


@dataclass(frozen=True)
class KeyInfo:
    kid: str
    kind: str  # "device" | "workload" | "verifier"
    subject: str  # did for devices, SPIFFE ID for workloads
    pk: Ed25519PublicKey
    nbf_ms: int
    exp_ms: int


@dataclass(frozen=True)
class Revocation:
    kid: str
    t_rev_ms: int  # effective revocation time (publication by the identity authority)
    t_comp_ms: Optional[int]  # earliest suspected compromise time (may precede t_rev)
    reason: str


class TrustRegistry:
    """Authoritative identity store (the CA / registration authority)."""

    def __init__(self, seed: bytes, use_x509: bool = True, trust_domain: str = "plant-a.example"):
        self.use_x509 = use_x509
        self.trust_domain = trust_domain
        self.ca_sk, self.ca_pk = keypair_from_seed(seed, "plant-root-ca")
        self._certs: dict[str, bytes] = {}
        self._raw: dict[str, KeyInfo] = {}
        self._revocations: dict[str, Revocation] = {}
        self.history: list[tuple[int, str, str, dict]] = []  # append-only lifecycle log for audit
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "PBTI Plant Root CA")])
        self.ca_name = name
        if use_x509:
            self.ca_cert = (
                x509.CertificateBuilder()
                .subject_name(name).issuer_name(name)
                .public_key(self.ca_pk)
                .serial_number(1)
                .not_valid_before(ms_to_dt(-86_400_000))
                .not_valid_after(ms_to_dt(10 * 365 * 86_400_000))
                .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
                .sign(self.ca_sk, algorithm=None)
            )

    # ----------------------------------------------------------------- issuance
    def issue(self, kid: str, kind: str, subject: str, pk: Ed25519PublicKey, nbf_ms: int, exp_ms: int,
              now_ms: int = 0) -> None:
        if kid in self._certs or kid in self._raw:
            raise ValueError(f"duplicate key id {kid}")
        if self.use_x509:
            uri = f"urn:pbti:device:{subject}" if kind == "device" else subject
            cert = (
                x509.CertificateBuilder()
                .subject_name(x509.Name([
                    x509.NameAttribute(NameOID.COMMON_NAME, kid),
                    x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, kind),
                ]))
                .issuer_name(self.ca_name)
                .public_key(pk)
                .serial_number(x509.random_serial_number())
                .not_valid_before(ms_to_dt(nbf_ms))
                .not_valid_after(ms_to_dt(exp_ms))
                .add_extension(x509.SubjectAlternativeName([x509.UniformResourceIdentifier(uri)]), critical=False)
                .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
                .sign(self.ca_sk, algorithm=None)
            )
            self._certs[kid] = cert.public_bytes(serialization.Encoding.DER)
        else:
            self._raw[kid] = KeyInfo(kid, kind, subject, pk, nbf_ms, exp_ms)
        self.history.append((now_ms, "issue", kid, {"kind": kind, "subject": subject, "nbf": nbf_ms, "exp": exp_ms}))

    def revoke(self, kid: str, t_rev_ms: int, t_comp_ms: Optional[int] = None, reason: str = "") -> None:
        """V4 (decision D05): a key stays revoked from its first revocation, and a revised record can only make the
        suspected compromise time earlier (conservative merge); a revision never loosens taint or release rules."""
        old = self._revocations.get(kid)
        if old is not None:
            t_rev_ms = min(old.t_rev_ms, t_rev_ms)
            if old.t_comp_ms is not None and (t_comp_ms is None or old.t_comp_ms < t_comp_ms):
                t_comp_ms = old.t_comp_ms
            reason = f"{old.reason};{reason}" if reason else old.reason
        self._revocations[kid] = Revocation(kid, t_rev_ms, t_comp_ms, reason)
        self.history.append((t_rev_ms, "revoke", kid, {"t_comp": t_comp_ms, "reason": reason}))

    # ----------------------------------------------------------------- queries
    def credential(self, kid: str):
        if self.use_x509:
            return self._certs.get(kid)
        return self._raw.get(kid)

    def revocations_effective(self, now_ms: int) -> dict[str, Revocation]:
        return {k: r for k, r in self._revocations.items() if r.t_rev_ms <= now_ms}

    def all_revocations(self) -> dict[str, Revocation]:
        return dict(self._revocations)


class TrustView:
    """The verifier's cached view of the identity plane.

    * certificates are chain-validated once (first use) and cached by key id;
    * revocation status is refreshed at most every `refresh_ms` (0 = consult on every event),
      which models CRL/OCSP-style status propagation delay.
    """

    def __init__(self, registry: TrustRegistry, refresh_ms: int = 0):
        self.reg = registry
        self.refresh_ms = refresh_ms
        self._keys: dict[str, Optional[KeyInfo]] = {}
        self._status: dict[str, Revocation] = {}
        self._last_refresh: Optional[int] = None
        self.chain_validations = 0
        self.pending_new: list = []

    def key(self, kid: str) -> Optional[KeyInfo]:
        if kid in self._keys:
            return self._keys[kid]
        cred = self.reg.credential(kid)
        info: Optional[KeyInfo] = None
        if cred is not None:
            if self.reg.use_x509:
                info = self._validate(kid, cred)
            else:
                info = cred
        self._keys[kid] = info
        return info

    def _validate(self, kid: str, der: bytes) -> Optional[KeyInfo]:
        self.chain_validations += 1
        try:
            cert = x509.load_der_x509_certificate(der)
            if cert.issuer != self.reg.ca_name:
                return None
            self.reg.ca_pk.verify(cert.signature, cert.tbs_certificate_bytes)
            cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
            kind = cert.subject.get_attributes_for_oid(NameOID.ORGANIZATIONAL_UNIT_NAME)[0].value
            if cn != kid:
                return None
            uri = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value.get_values_for_type(
                x509.UniformResourceIdentifier)[0]
            subject = uri[len("urn:pbti:device:"):] if kind == "device" else uri
            pk = cert.public_key()
            if not isinstance(pk, Ed25519PublicKey):
                return None
            return KeyInfo(kid, kind, subject, pk, dt_to_ms(cert.not_valid_before_utc), dt_to_ms(cert.not_valid_after_utc))
        except Exception:
            return None

    def status(self, kid: str, now_ms: int) -> Optional[Revocation]:
        if self._last_refresh is None or now_ms - self._last_refresh >= self.refresh_ms:
            snap = self.reg.revocations_effective(now_ms)
            for k, r in snap.items():
                if self._status.get(k) != r:
                    # first time this verifier learns of it, or (V4, D05) a revised record for an already revoked
                    # key, e.g. an earlier compromise time: the taint selector runs again with the revised record
                    self.pending_new.append((now_ms, r))
            self._status = snap
            self._last_refresh = now_ms
        return self._status.get(kid)

    def drain_new(self) -> list:
        out, self.pending_new = self.pending_new, []
        return out
