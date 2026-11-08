"""V3 attack/fault-rate sweep and fractional-factorial design (docs/V3_SWEEP_DESIGN.md).

Every factor is applied to the standard topology (4 gateways x 6 devices, 1 legacy per gateway, 1 Hz) with a
120 s production phase (instead of 300 s, to keep the 3,780 sweep and factorial runs feasible) and the usual 180 s drain. Each factor
takes a level r in {0, 0.01, 0.05, 0.10, 0.20}; time-valued factors map r to a time as stated per factor.
All randomness is drawn from per-world streams that do not depend on the pipeline, so runs of different
pipelines with the same seed and level see the same events (paired design).
"""
from __future__ import annotations

import random

from .attacks import DropHook, ReplayHook
from .scenarios import (EquivocationHook, ImpersonationHook, _rekey_gateway, _ts, forge_own, forge_own_legacy,
                        stolen_key_via_broker_rev)
from .sim import NetConfig, World, WorldConfig

DURATION_MS = 120_000
LEVELS = (0.0, 0.01, 0.05, 0.10, 0.20)
FACTORS = ("loss", "dup", "reorder", "delay", "burst", "clock", "revstale", "compromise", "equivocation",
           "missing", "relay")
TIME_SCALE_MS = 600_000   # time-valued factors: r -> r x 600 s (0, 6, 30, 60, 120 s)

DESCRIPTION = {
    "loss": "message lost in transit with probability r (gateway retransmits after the RTO)",
    "dup": "transport duplicate (redelivery) with probability r",
    "reorder": "extra delay U(0.2, 3) s with probability r (out-of-order delivery)",
    "delay": "long delay U(30, 90) s with probability r",
    "burst": "every gateway disconnected for r x 120 s from t = 24 s, then drains its backlog as a burst",
    "clock": "observation timestamp wrong with probability r: +U(6, 30) s (future) or -U(30, 90) s (past), 50/50",
    "revstale": "two devices of cell 4 and gateway 4 impersonated from 24 s (device+relay keys), revoked at 72 s with "
                "t_comp = 24 s; revocation status refreshed every r x 600 s (0, 6, 30, 60, 120 s)",
    "compromise": "same compromise from 24 s, revoked with t_comp = 24 s after a discovery delay of r x 600 s",
    "equivocation": "one signing device per cell equivocates with stolen device+relay keys with probability r per "
                    "message (cells 1-2 back-running, cells 3-4 front-running)",
    "missing": "a malicious broker drops (acks, then discards) a run of 5 consecutive messages of a device, starting "
               "with probability r/5 per message",
    "relay": "compromised gateway 2 (relay key only) forges r x 720 observations for its own devices and replays "
             "r of its traffic",
}


def _clock_hook(w: World, r: float):
    rng = random.Random(w.seed * 104729 + 17)
    for d in w.devices.values():
        base = d.clock

        def clock(t, base=base):
            ts = base(t)
            if rng.random() < r:
                if rng.random() < 0.5:
                    return ts + rng.randint(6_000, 30_000)
                return ts - rng.randint(30_000, 90_000)
            return ts
        d.clock = clock


def _missing_hook(w: World, r: float, run: int = 5, label: str = "missing-range"):
    rng = random.Random(w.seed * 7907 + 29 + (0 if run == 5 else 1000 * run))
    run_left: dict = {}

    def pred(ww, gw, e):
        o = e.item[1] if isinstance(e.item, tuple) else e.item
        if e.sends > 1:              # retransmissions of an already-dropped message are dropped too
            return getattr(e, "_dropped", False)
        n = run_left.get(o.did, 0)
        if n > 0:
            run_left[o.did] = n - 1
            e._dropped = True
            return True
        if rng.random() < r / run:
            run_left[o.did] = run - 1
            e._dropped = True
            return True
        return False
    w.hooks_deliver.append(DropHook(pred, label))


class _GatewayReplay(ReplayHook):
    """Replays captured traffic of one gateway only (malicious relay)."""

    def __init__(self, g: int, *a, **kw):
        super().__init__(*a, **kw)
        self.g = g

    def __call__(self, world, gw, e, wire, meta, label):
        if gw is None or gw.g != self.g:
            return None
        return super().__call__(world, gw, e, wire, meta, label)


def _compromise(w: World, t_rev: int, refresh_ms: int = 0):
    """Device+relay keys of two cell-4 devices and gateway 4 compromised from 24 s; the attacker impersonates them
    and forges legacy data until incident response at t_rev (revocation with t_comp = 24 s, re-keying 5 s later),
    then keeps trying with the stolen, now revoked keys."""
    g4 = w.gateways[3]
    victims = [d for d in g4.devices if not d.legacy][:2]
    if t_rev > 24_000:
        w.hooks_deliver.append(ImpersonationHook({v.did for v in victims}, 24_000, t_rev))
        forge_own_legacy(w, 4, _ts(24_000, t_rev, max(1, (t_rev - 24_000) // 3_000)))
    for v in victims:
        w.revoke(lambda v=v: v.kid, t_rev, 24_000)
    w.revoke(lambda: g4.kid, t_rev, 24_000)
    for v in victims:
        w.rotate_device_key(v.did, t_rev + 5_000)
    w.at(t_rev + 5_000, lambda: _rekey_gateway(w, g4))
    if t_rev + 6_000 < DURATION_MS + 60_000:
        stolen_key_via_broker_rev(w, [v.did for v in victims], g4, _ts(t_rev + 6_000, DURATION_MS + 60_000, 30))
    if refresh_ms and hasattr(w.sys, "trust"):
        w.sys.trust.refresh_ms = refresh_ms


def build_sweep(levels: dict, system: str, seed: int, **kw) -> World:
    """levels: factor -> r (missing factors are 0). kw (V4): WorldConfig overrides (review timing/mode/rule, temporal
    tracing, PBTI-SH timeout), applied before the World is built."""
    lv = {f: float(levels.get(f, 0.0)) for f in FACTORS}
    net = NetConfig(p_loss=lv["loss"], p_dup=lv["dup"], p_reorder=lv["reorder"], p_delay=lv["delay"])
    cfg = WorldConfig(seed=seed, system=system, duration_ms=DURATION_MS, net=net)
    for k, v in kw.items():
        setattr(cfg, k, v)
    w = World(cfg)
    if lv["burst"] > 0:
        for g in range(1, cfg.n_gw + 1):
            w.partition(g, 24_000, 24_000 + int(lv["burst"] * DURATION_MS))
    if lv["clock"] > 0:
        _clock_hook(w, lv["clock"])
    if lv["equivocation"] > 0:
        for gi, gw in enumerate(w.gateways):
            v = [d for d in gw.devices if not d.legacy][0]
            w.hooks_deliver.append(EquivocationHook({v.did}, lv["equivocation"], 6_000, DURATION_MS - 6_000,
                                                    "equivocation-front" if gi >= 2 else "equivocation-back",
                                                    front=gi >= 2))
    if lv["missing"] > 0:
        _missing_hook(w, lv["missing"])
    if float(levels.get("missing_long", 0.0)) > 0:       # V4 (A3): runs of 20 consecutive messages instead of 5
        _missing_hook(w, float(levels["missing_long"]), run=20, label="missing-long")
    if lv["relay"] > 0:
        n = round(lv["relay"] * 6 * DURATION_MS / 1000)
        forge_own(w, 2, _ts(3_000, DURATION_MS - 3_000, n))
        w.hooks_deliver.append(_GatewayReplay(2, lv["relay"], (2_000, 30_000), refresh=False, t0=0, t1=10 ** 12))
    # time-valued factors: every level (including 0) contains the compromise; level 0 = immediate status / discovery
    if "revstale" in levels:
        _compromise(w, 72_000, refresh_ms=int(lv["revstale"] * TIME_SCALE_MS))
    elif "compromise" in levels:
        _compromise(w, 24_000 + int(lv["compromise"] * TIME_SCALE_MS))
    return w


# ------------------------------------------------------------------ 2^(7-3) resolution IV fractional factorial
FACT7 = ("loss", "dup", "reorder", "delay", "clock", "equivocation", "missing")   # A B C D E F G


def factorial_runs(high: float = 0.10) -> list[dict]:
    """Standard 2^(7-3)_IV design: A, B, C, D full factorial; E = ABC, F = BCD, G = ACD."""
    runs = []
    for i in range(16):
        a, b, c, d = [(1 if (i >> k) & 1 else -1) for k in range(4)]
        e, f, g = a * b * c, b * c * d, a * c * d
        signs = dict(zip(FACT7, (a, b, c, d, e, f, g)))
        runs.append({"run": i, "signs": signs, "levels": {k: (high if s > 0 else 0.0) for k, s in signs.items()}})
    return runs
