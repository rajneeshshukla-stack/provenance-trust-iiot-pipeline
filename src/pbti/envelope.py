"""Wire formats (codecs) for the proposed mechanism (PBTI) and the three baselines.

PBTI wire message = canonical JSON object
    { "obs": <observation statement>,  "osig": b64u(Ed25519 over DOMAIN_OBS||canon(obs)),
      "rel": <relay statement>,        "rsig": b64u(Ed25519 over DOMAIN_REL||canon(rel)) }

Observation statement (signed by the device, or by the edge workload for legacy devices):
    v, typ, did, aid, ep, seq, ts, sch, pl, prev, kid
Relay statement (signed by the relaying edge workload):
    v, typ, wid, wkid, odig, rts, mode
    odig = b64u(SHA-256(canon(obs) || osig)) binds exactly one signed observation statement.

Baselines:
    B1 conventional : {mid, did, aid, ts, sch, pl, gw}       (no message-level protection)
    B2 zero-trust   : {mid, did, aid, ts, sch, pl, wid}      (no message-level protection)
    B3 provenance   : {rec:{mid,did,aid,ts,sch,pl,kid}, sig} (origin signature, no relay binding)
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Optional

from .canonical import canonical_bytes
from .crypto import (DOMAIN_B3, DOMAIN_OBS, DOMAIN_REL, b64u, sha256, sign, ub64u)

MAX_WIRE_BYTES = 4096
OBS_KEYS = frozenset({"v", "typ", "did", "aid", "ep", "seq", "ts", "sch", "pl", "prev", "kid"})
REL_KEYS = frozenset({"v", "typ", "wid", "wkid", "odig", "rts", "mode"})
WIRE_KEYS = frozenset({"obs", "osig", "rel", "rsig"})


@dataclass
class LogicalObs:
    """A logical industrial observation as produced at the source."""
    did: str
    aid: str
    ep: int
    seq: int
    ts: int
    sch: str
    pl: dict
    mid: str                       # message id used by the baselines (assigned at the source/edge)
    prev: Optional[str] = None     # PBTI: b64u content digest of the previous observation (same epoch)
    meta: dict = field(default_factory=dict)  # simulation bookkeeping only (never serialized)


PBTI_WIRE = ("PBTI", "B4", "B5", "B5S", "PBTI-R", "PBTI-SH")  # V4: PBTI-SH (selective evidence-gated holds)  # pipelines whose edge side emits PBTI observation and relay statements


def content_key(did: str, aid: str, ts: int, sch: str, pl: dict) -> tuple:
    """System-independent identity of an observation's content, used by the oracle."""
    return (did, aid, int(ts), sch, canonical_bytes(pl))


# --------------------------------------------------------------------------- PBTI
def pbti_obs_dict(o: LogicalObs, kid: str) -> dict:
    return {"v": 1, "typ": "pbti.obs", "did": o.did, "aid": o.aid, "ep": o.ep, "seq": o.seq,
            "ts": o.ts, "sch": o.sch, "pl": o.pl, "prev": o.prev, "kid": kid}


def pbti_content_digest(obs: dict) -> bytes:
    return sha256(canonical_bytes(obs))


def pbti_sign_obs(o: LogicalObs, sk, kid: str) -> tuple[dict, bytes]:
    obs = pbti_obs_dict(o, kid)
    return obs, sign(sk, DOMAIN_OBS, canonical_bytes(obs))


def pbti_wire(obs: dict, osig: bytes, wid: str, wkid: str, wsk, rts: int, mode: str) -> bytes:
    odig = b64u(sha256(canonical_bytes(obs) + osig))
    rel = {"v": 1, "typ": "pbti.relay", "wid": wid, "wkid": wkid, "odig": odig, "rts": rts, "mode": mode}
    rsig = sign(wsk, DOMAIN_REL, canonical_bytes(rel))
    return canonical_bytes({"obs": obs, "osig": b64u(osig), "rel": rel, "rsig": b64u(rsig)})


class MalformedMessage(ValueError):
    pass


def _req(cond: bool, what: str):
    if not cond:
        raise MalformedMessage(what)


def pbti_parse(wire: bytes) -> tuple[dict, bytes, dict, bytes]:
    _req(len(wire) <= MAX_WIRE_BYTES, "oversize")
    try:
        m = json.loads(wire)
    except Exception as e:  # noqa: BLE001
        raise MalformedMessage("json") from e
    _req(isinstance(m, dict) and set(m) == WIRE_KEYS, "wire-keys")
    obs, rel = m["obs"], m["rel"]
    _req(isinstance(obs, dict) and set(obs) == OBS_KEYS, "obs-keys")
    _req(isinstance(rel, dict) and set(rel) == REL_KEYS, "rel-keys")
    _req(obs["v"] == 1 and obs["typ"] == "pbti.obs", "obs-version")
    _req(rel["v"] == 1 and rel["typ"] == "pbti.relay", "rel-version")
    for k in ("did", "aid", "sch", "kid"):
        _req(isinstance(obs[k], str) and 0 < len(obs[k]) <= 256, f"obs-{k}")
    for k in ("ep", "seq", "ts"):
        _req(isinstance(obs[k], int) and not isinstance(obs[k], bool) and obs[k] >= 0, f"obs-{k}")
    _req(isinstance(obs["pl"], dict), "obs-pl")
    _req(obs["prev"] is None or (isinstance(obs["prev"], str) and len(obs["prev"]) == 43), "obs-prev")
    _req(obs["seq"] > 0 or obs["prev"] is None, "obs-prev-at-epoch-start")
    for k in ("wid", "wkid", "odig", "mode"):
        _req(isinstance(rel[k], str) and 0 < len(rel[k]) <= 256, f"rel-{k}")
    _req(rel["mode"] in ("live", "buffered"), "rel-mode")
    _req(isinstance(rel["rts"], int) and not isinstance(rel["rts"], bool), "rel-rts")
    try:
        osig, rsig = ub64u(m["osig"]), ub64u(m["rsig"])
    except Exception as e:  # noqa: BLE001
        raise MalformedMessage("sig-encoding") from e
    _req(len(osig) == 64 and len(rsig) == 64, "sig-length")
    return obs, osig, rel, rsig


# --------------------------------------------------------------------------- baselines
def b1_wire(o: LogicalObs, gw: str) -> bytes:
    return canonical_bytes({"mid": o.mid, "did": o.did, "aid": o.aid, "ts": o.ts, "sch": o.sch, "pl": o.pl, "gw": gw})


def b2_wire(o: LogicalObs, wid: str) -> bytes:
    return canonical_bytes({"mid": o.mid, "did": o.did, "aid": o.aid, "ts": o.ts, "sch": o.sch, "pl": o.pl, "wid": wid})


def b3_record(o: LogicalObs, kid: str) -> dict:
    return {"mid": o.mid, "did": o.did, "aid": o.aid, "ts": o.ts, "sch": o.sch, "pl": o.pl, "kid": kid}


def b3_wire_from_record(rec: dict, sk) -> bytes:
    sig = sign(sk, DOMAIN_B3, canonical_bytes(rec))
    return canonical_bytes({"rec": rec, "sig": b64u(sig)})


def plain_parse(wire: bytes, keys: frozenset) -> dict:
    _req(len(wire) <= MAX_WIRE_BYTES, "oversize")
    try:
        m = json.loads(wire)
    except Exception as e:  # noqa: BLE001
        raise MalformedMessage("json") from e
    _req(isinstance(m, dict) and set(m) == keys, "keys")
    for k in ("mid", "did", "aid", "sch"):
        _req(isinstance(m.get(k), str), k)
    _req(isinstance(m.get("ts"), int), "ts")
    _req(isinstance(m.get("pl"), dict), "pl")
    return m


B1_KEYS = frozenset({"mid", "did", "aid", "ts", "sch", "pl", "gw"})
B2_KEYS = frozenset({"mid", "did", "aid", "ts", "sch", "pl", "wid"})
B3_REC_KEYS = frozenset({"mid", "did", "aid", "ts", "sch", "pl", "kid"})


def b3_parse(wire: bytes) -> tuple[dict, bytes]:
    _req(len(wire) <= MAX_WIRE_BYTES, "oversize")
    try:
        m = json.loads(wire)
    except Exception as e:  # noqa: BLE001
        raise MalformedMessage("json") from e
    _req(isinstance(m, dict) and set(m) == {"rec", "sig"}, "keys")
    rec = m["rec"]
    _req(isinstance(rec, dict) and set(rec) == B3_REC_KEYS, "rec-keys")
    _req(isinstance(rec["ts"], int) and isinstance(rec["pl"], dict), "rec-types")
    try:
        sig = ub64u(m["sig"])
    except Exception as e:  # noqa: BLE001
        raise MalformedMessage("sig") from e
    _req(len(sig) == 64, "sig-length")
    return rec, sig
