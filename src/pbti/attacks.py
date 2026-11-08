"""Attack injectors. Each attack is defined by attacker POSITION and CAPABILITY (keys held), and is
rendered into the wire format of the system under test using only those capabilities. An attacker
without a key produces a random 64-byte value in place of the corresponding signature.

Positions:  BROKER  on-path at the messaging layer (read/modify/inject/drop/replay; can claim any
                    publisher identity towards the subscriber, as a compromised broker can)
            GATEWAY a compromised edge workload (holds its workload key and transport credential)
Capabilities: K_dev(d) stolen device key, K_gw(g) compromised workload key.
"""
from __future__ import annotations

import json
import os
import random
from typing import Optional

from .canonical import canonical_bytes
from .crypto import DOMAIN_B3, DOMAIN_OBS, DOMAIN_REL, b64u, sha256, sign
from .envelope import PBTI_WIRE, LogicalObs, b1_wire, b2_wire, b3_record, pbti_content_digest, pbti_obs_dict

RAND_SIG = lambda rng: bytes(rng.getrandbits(8) for _ in range(64))  # noqa: E731


def craft(world, o: LogicalObs, origin: Optional[tuple], relay_gw, relay_key: Optional[tuple],
          mode: str = "live", origin_kid: Optional[str] = None) -> tuple[bytes, dict]:
    """origin/relay_key = (sk, kid) if the attacker holds the key, else None (forged signature)."""
    s = world.cfg.system
    rng = world.mrng
    meta = {"tid": relay_gw.wid, "tkid": relay_gw.kid, "new_session": False}
    if s == "B1":
        return b1_wire(o, relay_gw.wid), meta
    if s == "B2":
        return b2_wire(o, relay_gw.wid), meta
    if s == "B3":
        kid = origin[1] if origin else origin_kid
        rec = b3_record(o, kid)
        sig = sign(origin[0], DOMAIN_B3, canonical_bytes(rec)) if origin else RAND_SIG(rng)
        return canonical_bytes({"rec": rec, "sig": b64u(sig)}), meta
    kid = origin[1] if origin else origin_kid
    obs = pbti_obs_dict(o, kid)
    osig = sign(origin[0], DOMAIN_OBS, canonical_bytes(obs)) if origin else RAND_SIG(rng)
    wkid = relay_key[1] if relay_key else relay_gw.kid
    rel = {"v": 1, "typ": "pbti.relay", "wid": relay_gw.wid, "wkid": wkid,
           "odig": b64u(sha256(canonical_bytes(obs) + osig)), "rts": world.now, "mode": mode}
    rsig = sign(relay_key[0], DOMAIN_REL, canonical_bytes(rel)) if relay_key else RAND_SIG(rng)
    return canonical_bytes({"obs": obs, "osig": b64u(osig), "rel": rel, "rsig": b64u(rsig)}), meta


def mutate(world, wire: bytes, what: str, rng: random.Random) -> bytes:
    """Modify a captured message WITHOUT re-signing (attacker lacks keys)."""
    m = json.loads(wire)
    s = world.cfg.system
    body = m["obs"] if s in PBTI_WIRE else (m["rec"] if s == "B3" else m)
    if what == "payload":
        body["pl"]["temp_c"] = round(body["pl"]["temp_c"] + rng.choice([-1, 1]) * rng.uniform(3, 8), 2)
    elif what == "asset":
        body["aid"] = body["aid"][:-2] + f"{(int(body['aid'][-2:]) % 6) + 1:02d}"
    elif what == "ts":
        body["ts"] = body["ts"] + rng.choice([-1, 1]) * rng.randint(2_000, 20_000)
    elif what == "seq":
        if s in PBTI_WIRE:
            body["seq"] = body["seq"] + rng.randint(1, 3)
        else:
            body["mid"] = f"{rng.getrandbits(64):016x}"
            body["ts"] = body["ts"] + 1
    elif what == "refresh":  # replay with refreshed timestamp (and fresh message id) to evade de-dup
        body["ts"] = world.now
        if "mid" in body:
            body["mid"] = f"{rng.getrandbits(64):016x}"
    else:
        raise ValueError(what)
    return canonical_bytes(m)


# ----------------------------------------------------------------------------- hooks
class TamperHook:
    """BROKER modifies a fraction of legitimate messages in transit."""

    def __init__(self, p: float, what: str, gws: Optional[set] = None, t0: int = 0, t1: int = 10 ** 12):
        self.p, self.what, self.gws, self.t0, self.t1 = p, what, gws, t0, t1

    def __call__(self, world, gw, e, wire, meta, label):
        if label != "legit" or gw is None or not (self.t0 <= world.now < self.t1):
            return None
        if self.gws and gw.g not in self.gws:
            return None
        if world.arng.random() >= self.p:
            return None
        new = mutate(world, wire, self.what, world.mrng)
        world.attack_log.append({"t": world.now, "type": "tamper-" + self.what})
        return new, meta, "tamper-" + self.what


class ReplayHook:
    """BROKER records legitimate messages and re-injects them later (exact or timestamp-refreshed)."""

    def __init__(self, p_capture: float, delay_ms: tuple, refresh: bool, t0: int = 0, t1: int = 10 ** 12):
        self.p, self.delay, self.refresh, self.t0, self.t1 = p_capture, delay_ms, refresh, t0, t1

    def __call__(self, world, gw, e, wire, meta, label):
        if label != "legit" or not (self.t0 <= world.now < self.t1):
            return None
        if world.arng.random() < self.p:
            d = world.arng.uniform(*self.delay)
            lab = "replay-refresh" if self.refresh else "replay-exact"
            def fire(w=wire, m=dict(meta, new_session=False)):
                ww = mutate(world, w, "refresh", world.mrng) if self.refresh else w
                world.attack_log.append({"t": world.now, "type": lab})
                world.receive(ww, m, lab)
            world.at(world.now + d, fire)
        return None


class DropHook:
    """BROKER or compromised gateway silently suppresses selected legitimate messages."""

    def __init__(self, pred, label="suppressed"):
        self.pred, self.label = pred, label

    def __call__(self, world, gw, e, wire, meta, label):
        if label != "legit" or e is None:
            return None
        if self.pred(world, gw, e):
            world.attack_log.append({"t": world.now, "type": self.label})
            return "DROP"
        return None


def obs_from_item(item) -> LogicalObs:
    return item[1] if isinstance(item, tuple) else item


def fake_obs(world, d, ts: int, ep: int, seq: int, prev: Optional[str], delta: float = 6.0) -> LogicalObs:
    pl = d.sample(world.arng, ts)
    pl["temp_c"] = round(pl["temp_c"] + delta, 2)
    return LogicalObs(d.did, d.aid, ep, seq, ts, "telemetry.v1", pl, f"{world.arng.getrandbits(64):016x}", prev)


def schedule_injections(world, times: list[int], make):
    """make(world) -> (wire, meta, label) or None; injected after a small network delay."""
    def fire():
        r = make(world)
        if r is None:
            return
        wire, meta, label = r
        world.attack_log.append({"t": world.now, "type": label})
        world.receive(wire, meta, label)
    for t in times:
        world.at(t, fire)
