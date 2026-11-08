"""Experiment scenarios (docs/EXPERIMENT_PLAN.md, Table "Experimental scenarios").

Each scenario returns (WorldConfig overrides, setup(world)). Virtual duration 300 s, 4 gateways,
6 devices per gateway (1 legacy per gateway), 1 Hz per device unless overridden.
"""
from __future__ import annotations

import copy
from dataclasses import replace
from typing import Callable

from .attacks import (DropHook, ReplayHook, TamperHook, craft, fake_obs, obs_from_item, schedule_injections)
from .canonical import canonical_bytes
from .crypto import b64u, keypair_from_seed
from .envelope import PBTI_WIRE, LogicalObs, pbti_content_digest, pbti_obs_dict
from .sim import FAR, NetConfig, World, WorldConfig


# ----------------------------------------------------------------------------- stateful attackers
class EquivocationHook:
    """K_dev(d)+K_gw(g): after a victim's legitimate message passes, inject a conflicting version
    with the SAME identity (PBTI: did,ep,seq,prev; baselines: did,ts with a fresh message id)."""

    def __init__(self, victims: set, p: float, t0: int, t1: int, label: str = "equivocation", front: bool = False):
        self.victims, self.p, self.t0, self.t1, self.label, self.front = victims, p, t0, t1, label, front

    def __call__(self, world, gw, e, wire, meta, label):
        if label != "legit" or e is None or not (self.t0 <= world.now < self.t1):
            return None
        o = obs_from_item(e.item)
        if o.did not in self.victims or world.arng.random() >= self.p:
            return None
        d = world.devices[o.did]
        g = world.gateways[d.g - 1]
        f = LogicalObs(o.did, o.aid, o.ep, o.seq, o.ts, o.sch, dict(o.pl, temp_c=round(o.pl["temp_c"] + 7.5, 2)),
                       f"{world.arng.getrandbits(64):016x}", o.prev)
        w2, m2 = craft(world, f, (d.sk, d.kid), g, (g.sk, g.kid))
        world.attack_log.append({"t": world.now, "type": self.label})
        if self.front:  # front-running: the forged version reaches the verifier first
            world.receive(w2, m2, self.label)
            return None
        world.at(world.now + 50, lambda: world.receive(w2, m2, self.label))
        return None


class GapFillHook:
    """K_dev(d)+K_gw(g): suppress a victim's legitimate message and deliver a forged one with the
    same identity and a correct predecessor link in its place."""

    def __init__(self, victims: set, p: float, t0: int, t1: int):
        self.victims, self.p, self.t0, self.t1 = victims, p, t0, t1

    def __call__(self, world, gw, e, wire, meta, label):
        if label != "legit" or e is None or not (self.t0 <= world.now < self.t1):
            return None
        o = obs_from_item(e.item)
        if o.did not in self.victims or world.arng.random() >= self.p:
            return None
        d = world.devices[o.did]
        g = world.gateways[d.g - 1]
        f = LogicalObs(o.did, o.aid, o.ep, o.seq, o.ts, o.sch, dict(o.pl, temp_c=round(o.pl["temp_c"] - 6.5, 2)),
                       f"{world.arng.getrandbits(64):016x}", o.prev)
        w2, m2 = craft(world, f, (d.sk, d.kid), g, (g.sk, g.kid))
        world.attack_log.append({"t": world.now, "type": "gapfill"})
        return w2, m2, "gapfill"


class ImpersonationHook:
    """K_dev(d)+K_gw(g): from t0, suppress ALL legitimate messages of the victim and emit a forged,
    internally consistent stream (same identities, re-chained predecessor links)."""

    def __init__(self, victims: set, t0: int, t1: int):
        self.victims, self.t0, self.t1 = victims, t0, t1
        self.chain: dict[str, str] = {}

    def __call__(self, world, gw, e, wire, meta, label):
        if label != "legit" or e is None:
            return None
        o = obs_from_item(e.item)
        if o.did not in self.victims:
            return None
        d = world.devices[o.did]
        if not (self.t0 <= world.now < self.t1):
            if world.cfg.system in PBTI_WIRE and world.now < self.t0:
                self.chain[o.did] = _cd_of(world, o, d)
            return None
        if world.trust.all_revocations().get(_kid_used(o, d, e)) is not None:
            return None
        g = world.gateways[d.g - 1]
        prev = self.chain.get(o.did) if o.seq > 0 else None
        f = LogicalObs(o.did, o.aid, o.ep, o.seq, o.ts, o.sch, dict(o.pl, temp_c=round(o.pl["temp_c"] + 9.0, 2)),
                       f"{world.arng.getrandbits(64):016x}", prev)
        kid_used = _kid_used(o, d, e)
        sk_used = keypair_from_seed(world.seedb, kid_used)[0]
        w2, m2 = craft(world, f, (sk_used, kid_used), g, (g.sk, g.kid))
        if world.cfg.system in PBTI_WIRE:
            self.chain[o.did] = b64u(pbti_content_digest(pbti_obs_dict(f, kid_used)))
        world.attack_log.append({"t": world.now, "type": "impersonation"})
        return w2, m2, "impersonation"


def _kid_used(o, d, e):
    item = e.item
    if isinstance(item, tuple) and item[0] == "pbti":
        return item[2]["kid"]
    return d.kid


def _cd_of(world, o, d):
    if world.cfg.system not in PBTI_WIRE:
        return ""
    return b64u(pbti_content_digest(pbti_obs_dict(o, d.kid)))


def lateral_forgery(world: World, src_g: int, dst_g: int, times: list[int], label="lateral"):
    """K_gw(src): forge NEW observations for devices of another cell, relayed through src."""
    src = world.gateways[src_g - 1]
    dst = world.gateways[dst_g - 1]

    def make(w):
        d = dst.devices[w.arng.randrange(len(dst.devices))]
        es = 10_000 + w.arng.randrange(10_000)
        f = fake_obs(w, d, w.now - 500, 0 if not d.legacy else 0, es, None)
        if d.legacy:
            return (*craft(w, f, (src.sk, src.kid), src, (src.sk, src.kid)), label + "-legacy")
        return (*craft(w, f, None, src, (src.sk, src.kid), origin_kid=d.kid), label + "-signing")
    schedule_injections(world, times, make)


def forge_own(world: World, g: int, times: list[int]):
    """K_gw(g) only: forge observations for the gateway's own devices (legacy and signing)."""
    gw = world.gateways[g - 1]

    def make(w):
        d = gw.devices[w.arng.randrange(len(gw.devices))]
        f = fake_obs(w, d, w.now - 300, 0, 50_000 + w.arng.randrange(10_000), None)
        if d.legacy:
            return (*craft(w, f, (gw.sk, gw.kid), gw, (gw.sk, gw.kid)), "gwforge-legacy")
        return (*craft(w, f, None, gw, (gw.sk, gw.kid), origin_kid=d.kid), "gwforge-signing")
    schedule_injections(world, times, make)


def stolen_key_via_broker(world: World, victims: list[str], times: list[int]):
    """K_dev(d) without any workload key, injected at the broker claiming the victim's gateway."""

    def make(w):
        d = w.devices[victims[w.arng.randrange(len(victims))]]
        g = w.gateways[d.g - 1]
        f = fake_obs(w, d, w.now - 200, d.ep, d.seq + 5 + w.arng.randrange(50), None)
        return (*craft(w, f, (d.sk, d.kid), g, None), "stolenkey-broker")
    schedule_injections(world, times, make)


def unknown_producer(world: World, times: list[int]):
    rogue_sk, _ = keypair_from_seed(b"rogue", "rogue-key")

    class _Rogue:
        wid = "spiffe://plant-a.example/rogue/collector"
        kid = "wk:rogue:1"
        sk = rogue_sk

    def make(w):
        d = w.gateways[0].devices[1]
        f = fake_obs(w, d, w.now - 100, 0, 70_000 + w.arng.randrange(1000), None)
        return (*craft(w, f, (rogue_sk, "dk:rogue:1"), _Rogue, (rogue_sk, "wk:rogue:1")), "unknown-producer")
    schedule_injections(world, times, make)


def move_device(world: World, did: str, new_g: int, t: int):
    """Physical re-assignment of a device to another cell + matching policy update at t."""
    d = world.devices[did]
    old_g = d.g

    def mv():
        old = world.gateways[d.g - 1]
        new = world.gateways[new_g - 1]
        old.devices.remove(d)
        new.devices.append(d)
        d.g = new_g
        world._move_period = getattr(world, "_move_period", {})
    world.at(t, mv)

    def mut(doc):
        old_wid = f"spiffe://plant-a.example/cell{old_g}/gw{old_g}/collector"
        new_wid = f"spiffe://plant-a.example/cell{new_g}/gw{new_g}/collector"
        doc["workloads"][old_wid]["relay"] = [x for x in doc["workloads"][old_wid]["relay"] if x != did]
        doc["workloads"][new_wid]["relay"].append(did)
    world.policy_update(t, mut)


# ----------------------------------------------------------------------------- scenario catalogue
def _ts(a, b, n, rng=None):
    step = (b - a) / max(1, n)
    return [int(a + i * step) for i in range(n)]


def S01_normal():
    return {}, lambda w: None


def S02_payload_tamper():
    return {}, lambda w: w.hooks_deliver.append(TamperHook(0.05, "payload"))


def S03_metadata_tamper():
    def setup(w):
        w.hooks_deliver += [TamperHook(0.02, "asset"), TamperHook(0.02, "ts"), TamperHook(0.02, "seq")]
    return {}, setup


def S04_unauthorized():
    def setup(w):
        unknown_producer(w, _ts(20_000, 280_000, 100))
        lateral_forgery(w, 2, 3, _ts(30_000, 270_000, 100))
    return {}, setup


def S05_stolen_key():
    def setup(w):
        g1 = w.gateways[0]
        victims = [d.did for d in g1.devices if not d.legacy][:2]
        stolen_key_via_broker(w, victims, _ts(40_000, 260_000, 100))
        g4 = w.gateways[3]
        v4 = [d.did for d in g4.devices if not d.legacy]
        w.hooks_deliver.append(EquivocationHook({v4[0]}, 0.10, 30_000, 270_000, "equivocation-back"))
        w.hooks_deliver.append(EquivocationHook({v4[3]}, 0.10, 30_000, 270_000, "equivocation-front", front=True))
        w.hooks_deliver.append(GapFillHook({v4[1]}, 0.10, 30_000, 270_000))
        w.hooks_deliver.append(ImpersonationHook({v4[2]}, 150_000, 10 ** 12))
    return {}, setup


def S06_replay():
    def setup(w):
        w.hooks_deliver.append(ReplayHook(0.05, (5_000, 150_000), refresh=False))
        w.hooks_deliver.append(ReplayHook(0.03, (5_000, 150_000), refresh=True))
    return {}, setup


def S07_duplicates():
    return {"net": NetConfig(p_dup=0.10, p_ackloss=0.10, p_loss=0.02)}, lambda w: None


def S08_seq_reuse_bug():
    def setup(w):
        for i, d in enumerate([w.gateways[0].devices[2], w.gateways[2].devices[3]]):
            for t in (80_000 + 40_000 * i, 200_000 + 30_000 * i):
                w.device_seq_bug(d.did, t)
    return {}, setup


def S09_reorder():
    return {"net": NetConfig(p_reorder=0.30, reorder_max_ms=3_000)}, lambda w: None


def S10_delay_clock():
    def setup(w):
        ds = [d for g in w.gateways for d in g.devices if not d.legacy]
        w.clock_freeze(ds[0].did, 100_000, 5_000)
        w.clock_freeze(ds[5].did, 140_000, 5_000)
        w.clock_step(ds[9].did, 150_000, -30_000)
        w.clock_step(ds[13].did, 160_000, -30_000)
    return {"net": NetConfig(p_delay=0.02)}, setup


def S11_disconnect_recover():
    def setup(w):
        w.partition(1, 60_000, 180_000)
        w.device_reboot(w.gateways[0].devices[3].did, 100_000)
        w.gateway_restart(1, 190_000, down_ms=5_000, reread_ms=10_000)
    return {"net": NetConfig(p_ackloss=0.05)}, setup


def S12_beyond_horizon():
    def setup(w):
        w.partition(2, 60_000, 210_000)
    return {"params": {"h_max_ms": 120_000}}, setup


def S13_rotation():
    def setup(w):
        g3 = w.gateways[2]
        for d in [x for x in g3.devices if not x.legacy][:3]:
            w.rotate_device_key(d.did, 150_000)
        w.partition(3, 100_000, 220_000)
    def cfg_fix(c: WorldConfig):
        c.wl_validity_ms, c.wl_renew_ms = 90_000, 60_000
        exp = {}
        for j in range(2, 5):
            exp[f"pa-c3-d{j:02d}"] = 155_000
        c.dev_cert_exp = exp
    return {"_fix": cfg_fix}, setup


def S14_revocation(refresh_ms: int = 0):
    def setup(w):
        g4 = w.gateways[3]
        victims = [d for d in g4.devices if not d.legacy][:2]
        w.hooks_deliver.append(ImpersonationHook({v.did for v in victims}, 120_000, 200_000))
        forge_own_legacy(w, 4, _ts(120_000, 200_000, 40))
        for v in victims:
            w.revoke(lambda v=v: v.kid, 200_000, 120_000)
        w.revoke(lambda: g4.kid, 200_000, 120_000)
        for v in victims:
            w.rotate_device_key(v.did, 205_000)
        w.at(205_000, lambda: _rekey_gateway(w, g4))
        # after incident response the attacker keeps trying with the stolen (now revoked) keys
        stolen_key_via_broker_rev(w, [v.did for v in victims], g4, _ts(206_000, 280_000, 40))
    return {"vcfg_refresh": refresh_ms}, setup


def forge_own_legacy(w: World, g: int, times):
    gw = w.gateways[g - 1]
    leg = [d for d in gw.devices if d.legacy]

    def make(ww):
        d = leg[0]
        f = fake_obs(ww, d, ww.now - 300, 0, 0, None, delta=8.0)
        if ww.cfg.system in PBTI_WIRE:
            seq = gw.legacy_seq.get(d.did, 0)
            f.ep, f.seq = gw.g * 1000 + gw.legacy_ep, seq
            f.prev = gw.legacy_prev.get(d.did)
            gw.legacy_seq[d.did] = seq + 1
            gw.legacy_prev[d.did] = b64u(pbti_content_digest(pbti_obs_dict(f, gw.kid)))
        return (*craft(ww, f, (gw.sk, gw.kid), gw, (gw.sk, gw.kid)), "gwforge-legacy")
    schedule_injections(w, times, make)


def stolen_key_via_broker_rev(w: World, victims: list[str], gw, times):
    old = {did: (keypair_from_seed(w.seedb, f"dk:{did}:1")[0], f"dk:{did}:1") for did in victims}
    old_g = (keypair_from_seed(w.seedb, f"wk:gw{gw.g}:1")[0], f"wk:gw{gw.g}:1")

    class _G:
        wid = gw.wid
        kid = f"wk:gw{gw.g}:1"

    def make(ww):
        did = victims[ww.arng.randrange(len(victims))]
        d = ww.devices[did]
        f = fake_obs(ww, d, ww.now - 200, d.ep, d.seq + 3 + ww.arng.randrange(20), None, delta=9.0)
        return (*craft(ww, f, old[did], _G, old_g), "postrevocation-stolen")
    schedule_injections(w, times, make)


def _rekey_gateway(w: World, gw):
    gw.key_gen += 1
    gw.kid = f"wk:gw{gw.g}:{gw.key_gen}"
    gw.sk, pk = keypair_from_seed(w.seedb, gw.kid)
    w.trust.issue(gw.kid, "workload", gw.wid, pk, w.now - 1_000, FAR, w.now)
    gw.new_session = True


def S15_edge_compromise():
    def setup(w):
        forge_own(w, 2, _ts(30_000, 270_000, 100))
        g2 = w.gateways[1]
        w.hooks_deliver.append(DropHook(lambda ww, gw, e: gw is not None and gw.g == 2 and ww.arng.random() < 0.05,
                                        "suppressed"))
        w.hooks_deliver.append(ReplayHook(0.05, (2_000, 60_000), refresh=False, t0=0, t1=10 ** 12))
    return {}, setup


def S99_mixed():
    """Combined adversarial + failure workload used for the ablation study."""
    def setup(w):
        ds = [d for g in w.gateways for d in g.devices if not d.legacy]
        w.hooks_deliver.append(TamperHook(0.01, "payload"))
        w.hooks_deliver.append(TamperHook(0.005, "ts"))
        w.hooks_deliver.append(TamperHook(0.005, "seq"))
        w.hooks_deliver.append(ReplayHook(0.02, (5_000, 120_000), refresh=False))
        w.hooks_deliver.append(ReplayHook(0.01, (5_000, 120_000), refresh=True))
        g4 = w.gateways[3]
        v4 = [d for d in g4.devices if not d.legacy]
        w.hooks_deliver.append(EquivocationHook({v4[0].did}, 0.10, 30_000, 270_000, "equivocation-back"))
        w.hooks_deliver.append(EquivocationHook({v4[3].did}, 0.10, 30_000, 270_000, "equivocation-front", front=True))
        forge_own(w, 2, _ts(30_000, 270_000, 30))
        w.hooks_deliver.append(GapFillHook({v4[1].did}, 0.05, 30_000, 270_000))
        w.hooks_deliver.append(ImpersonationHook({v4[2].did}, 120_000, 200_000))
        w.revoke(lambda: v4[2].kid, 200_000, 120_000)
        w.rotate_device_key(v4[2].did, 205_000)
        stolen_key_via_broker(w, [ds[0].did], _ts(40_000, 260_000, 30))
        lateral_forgery(w, 2, 3, _ts(30_000, 270_000, 30))
        w.device_seq_bug(ds[3].did, 90_000)
        w.clock_freeze(ds[6].did, 100_000, 5_000)
        w.clock_step(ds[7].did, 150_000, -30_000)
        w.partition(1, 60_000, 190_000)
        w.device_reboot(w.gateways[0].devices[4].did, 100_000)
        w.gateway_restart(1, 200_000, down_ms=5_000, reread_ms=10_000)
        time_forgery(w, v4[4].did, _ts(40_000, 260_000, 30))
        moved = w.gateways[2].devices[5].did
        move_device(w, moved, 2, 150_000)
        # after the move, an attacker holding gw3's workload key and the device key tries the old path
        lateral_old_path(w, 3, moved, _ts(160_000, 280_000, 30))
    return {"net": NetConfig(p_dup=0.05, p_ackloss=0.05, p_reorder=0.10, p_delay=0.01),
            "params": {"h_max_ms": 120_000}}, setup


def time_forgery(w: World, did: str, times, label_back="backdated-forgery", label_fut="futuredated-forgery"):
    """K_dev(d)+K_gw(g): forge observations with back-dated (rewrite finalized history) or future-dated
    (pin the current value) timestamps, using fresh sequence numbers far ahead of the device."""
    d0 = w.devices[did]
    gw = w.gateways[d0.g - 1]
    k = {"n": 0}

    def make(ww):
        d = ww.devices[did]
        k["n"] += 1
        back = k["n"] % 2 == 0 and ww.now >= 160_000
        ts = ww.now - 150_000 if back else ww.now + 3_600_000   # back-dated beyond the 120 s horizon
        f = fake_obs(ww, d, ts, d.ep, 20_000 + k["n"], None, delta=4.0)
        return (*craft(ww, f, (d.sk, d.kid), gw, (gw.sk, gw.kid)), label_back if back else label_fut)
    schedule_injections(w, times, make)


def lateral_old_path(w: World, g: int, did: str, times):
    gw = w.gateways[g - 1]

    def make(ww):
        d = ww.devices[did]
        f = fake_obs(ww, d, ww.now - 300, d.ep, d.seq + 400 + ww.arng.randrange(100), None, delta=5.0)
        return (*craft(ww, f, (d.sk, d.kid), gw, (gw.sk, gw.kid)), "oldpath-forgery")
    schedule_injections(w, times, make)


SCENARIOS: dict[str, tuple[str, str, Callable]] = {
    "S01_normal": ("E1", "Normal operation", S01_normal),
    "S02_payload_tamper": ("E2", "Payload tampering in transit (5%)", S02_payload_tamper),
    "S03_metadata_tamper": ("E3", "Metadata tampering: asset, timestamp, sequence (2% each)", S03_metadata_tamper),
    "S04_unauthorized": ("E4", "Unknown producer + lateral forgery through another cell's gateway", S04_unauthorized),
    "S05_stolen_key": ("E5", "Stolen device keys: via broker; with gateway: equivocation, gap-fill, impersonation", S05_stolen_key),
    "S06_replay": ("E6", "Malicious replay: exact (5%) and timestamp-refreshed (3%)", S06_replay),
    "S07_duplicates": ("E7", "Transport duplicates 10%, ack loss 10%, loss 2%", S07_duplicates),
    "S08_seq_reuse_bug": ("E8", "Benign conflicting duplicates: device sequence-reuse bug", S08_seq_reuse_bug),
    "S09_reorder": ("E9", "Out-of-order delivery (30% delayed up to 3 s)", S09_reorder),
    "S10_delay_clock": ("E10", "Late events (2% delayed 30-90 s) + clock freeze and backward step", S10_delay_clock),
    "S11_disconnect_recover": ("E11/E12", "120 s disconnection, device reboot, gateway restart during drain, ack loss", S11_disconnect_recover),
    "S12_beyond_horizon": ("E11b", "150 s disconnection with a 120 s admission horizon", S12_beyond_horizon),
    "S13_rotation": ("E13", "Short-lived workload SVIDs + device key rotation during a disconnection", S13_rotation),
    "S14_revocation": ("E14", "Device+gateway compromise, revocation with compromise window, re-keying", S14_revocation),
    "S15_edge_compromise": ("E15", "Compromised edge workload: forgery, suppression, replay", S15_edge_compromise),
    "S99_mixed": ("ABL", "Mixed adversarial and failure workload (ablation study)", S99_mixed),
}


def build(scenario: str, system: str, seed: int, ablation=None, **kw) -> World:
    _, _, fn = SCENARIOS[scenario]
    over, setup = fn() if scenario != "S14_revocation" else fn(kw.pop("refresh_ms", 0))
    cfg = WorldConfig(seed=seed, system=system)
    if ablation is not None:
        cfg.ablation = ablation
    for k, v in over.items():
        if k == "_fix":
            v(cfg)
        elif k == "vcfg_refresh":
            cfg.vcfg = replace(cfg.vcfg, status_refresh_ms=v)
        else:
            setattr(cfg, k, v)
    for k, v in kw.items():
        setattr(cfg, k, v)
    w = World(cfg)
    setup(w)
    return w
