"""Versioned admission policy and Policy Decision Point (PDP).

The policy is a vendor-neutral JSON document (see policies/admission_policy.example.json).
An equivalent Rego formulation is provided in policies/admission.rego; V3 tests decision and reason parity
with a Rego interpreter (tests/policy_parity/).

Decision inputs  : device id, asset id, relaying workload id, schema id, origin-signer kind.
Decision output  : (permit, reason, policy_version).
Every admission record stores policy_version, so an auditor can re-evaluate any decision
against the exact policy that was in force (policy history is append-only).
"""
from __future__ import annotations

import copy
from dataclasses import dataclass

from .canonical import canonical_bytes
from .crypto import sha256_hex

DEFAULT_PARAMS = {
    "skew_max_ms": 5_000,          # max tolerated source-clock lead over verifier clock
    "h_max_ms": 3_600_000,         # max permitted buffering horizon (age at arrival)
    "retry_window_ms": 30_000,     # duplicate within window via same path => RETRY, else SUSPECTED_REPLAY
    "rotation_grace_ms": 3_600_000,  # expired (not revoked) keys accepted this long after expiry
    "max_seq_jump": 100_000,       # sequence jump above high-water mark that is quarantined
    "epoch_drain_ms": 3_600_000,   # older epoch accepted this long after a newer epoch opened
    "on_revoked_buffered": "quarantine",  # or "reject"
    "gap_close_ms": 3_600_000,     # open sequence gaps are declared LOST after this long
}


class PolicyDocumentError(ValueError):
    """V3: a policy document that does not match the schema below is rejected before it can take effect (fail closed)."""


_ORIGINS = ("device", "gateway")


def _str_list(x) -> bool:
    return isinstance(x, list) and all(isinstance(e, str) for e in x)


def validate_policy_doc(doc) -> None:
    """Schema of a policy document (V3). Defaults: schemas = [], origin = "device", active = true.
    Raises PolicyDocumentError; the same rules are checked by `doc_ok` in policies/admission.rego."""
    def bad(msg):
        raise PolicyDocumentError(msg)
    if not isinstance(doc, dict):
        bad("policy document is not an object")
    for k in ("devices", "workloads"):
        if not isinstance(doc.get(k), dict):
            bad(f"'{k}' is missing or not an object")
    if not isinstance(doc.get("params", {}), dict):
        bad("'params' is not an object")
    for did, d in doc["devices"].items():
        if not isinstance(d, dict):
            bad(f"device {did!r}: entry is not an object")
        if not _str_list(d.get("assets")):
            bad(f"device {did!r}: 'assets' must be a list of strings")
        if "schemas" in d and not _str_list(d["schemas"]):
            bad(f"device {did!r}: 'schemas' must be a list of strings")
        if d.get("origin", "device") not in _ORIGINS:
            bad(f"device {did!r}: 'origin' must be one of {_ORIGINS}")
        if not isinstance(d.get("active", True), bool):
            bad(f"device {did!r}: 'active' must be a boolean")
    for wid, w in doc["workloads"].items():
        if not isinstance(w, dict):
            bad(f"workload {wid!r}: entry is not an object")
        if not _str_list(w.get("relay")):
            bad(f"workload {wid!r}: 'relay' must be a list of strings")
        if not isinstance(w.get("active", True), bool):
            bad(f"workload {wid!r}: 'active' must be a boolean")
    if "reviewers" in doc:
        if not isinstance(doc["reviewers"], dict):
            bad("'reviewers' is not an object")
        for rid, r in doc["reviewers"].items():
            if not isinstance(r, dict) or not _str_list(r.get("may_release", [])) or not isinstance(r.get("active", True), bool):
                bad(f"reviewer {rid!r}: needs 'may_release' (list of strings) and a boolean 'active'")
    for k, v in doc.get("params", {}).items():
        if k == "on_revoked_buffered":
            if v not in ("quarantine", "reject"):
                bad("params.on_revoked_buffered must be 'quarantine' or 'reject'")
        elif k in DEFAULT_PARAMS and (not isinstance(v, int) or isinstance(v, bool) or v < 0):
            bad(f"params.{k} must be a non-negative integer")


@dataclass(frozen=True)
class PolicyVersion:
    version: int
    t_ms: int
    doc: dict
    digest: str


class PolicyStore:
    def __init__(self, doc: dict, t_ms: int = 0):
        self.versions: list[PolicyVersion] = []
        self.update(doc, t_ms)

    def update(self, doc: dict, t_ms: int) -> PolicyVersion:
        validate_policy_doc(doc)          # V3: malformed documents never become a policy version
        d = copy.deepcopy(doc)
        params = dict(DEFAULT_PARAMS)
        params.update(d.get("params", {}))
        d["params"] = params
        v = PolicyVersion(len(self.versions) + 1, t_ms, d, sha256_hex(canonical_bytes(d)))
        self.versions.append(v)
        return v

    def current(self) -> PolicyVersion:
        return self.versions[-1]

    def get(self, version: int) -> PolicyVersion:
        return self.versions[version - 1]


class PDP:
    """Path-bound admission policy: device -> asset -> schema, and workload -> relay scope."""

    def __init__(self, store: PolicyStore, static: bool = False):
        self.store = store
        self.static = static  # ablation A2: freeze the first policy version
        self._cache: dict[tuple, tuple[bool, str]] = {}
        self.evaluations = 0

    def active_version(self, t_ms: int) -> PolicyVersion:
        if self.static:
            return self.store.get(1)
        vs = self.store.versions
        for v in reversed(vs):  # policy history is short; latest version in force at t_ms
            if v.t_ms <= t_ms:
                return v
        return vs[0]

    def params(self, t_ms: int) -> dict:
        return self.active_version(t_ms).doc["params"]

    def evaluate(self, did: str, aid: str, wid: str, sch: str, origin_kind: str, t_ms: int,
                 check_origin: bool = True) -> tuple[bool, str, int]:
        pv = self.active_version(t_ms)
        if not all(type(x) is str for x in (did, aid, wid, sch, origin_kind)):   # V3: fail closed on malformed input
            return False, "INPUT_INVALID", pv.version
        key = (pv.version, did, aid, wid, sch, origin_kind, check_origin)
        hit = self._cache.get(key)
        if hit is None:
            self.evaluations += 1
            hit = self._decide(pv.doc, did, aid, wid, sch, origin_kind, check_origin)
            self._cache[key] = hit
        return hit[0], hit[1], pv.version

    @staticmethod
    def _decide(doc: dict, did: str, aid: str, wid: str, sch: str, origin_kind: str,
                check_origin: bool = True) -> tuple[bool, str]:
        if not all(type(x) is str for x in (did, aid, wid, sch, origin_kind)):
            return False, "INPUT_INVALID"
        dev = doc["devices"].get(did)
        if dev is None or not dev.get("active", True):
            return False, "DEVICE_NOT_REGISTERED"
        if aid not in dev["assets"]:
            return False, "ASSET_NOT_ASSIGNED"
        if sch not in dev.get("schemas", []):
            return False, "SCHEMA_NOT_ALLOWED"
        wl = doc["workloads"].get(wid)
        if wl is None or not wl.get("active", True):
            return False, "WORKLOAD_NOT_REGISTERED"
        if did not in wl["relay"]:
            return False, "PATH_NOT_AUTHORIZED"
        if not check_origin:
            return True, "PERMIT"
        required = dev.get("origin", "device")
        if required == "device" and origin_kind != "device":
            return False, "ORIGIN_SIGNER_TOO_WEAK"
        if required == "gateway" and origin_kind not in ("workload", "device"):
            return False, "ORIGIN_SIGNER_INVALID"
        return True, "PERMIT"
