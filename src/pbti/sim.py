"""Deterministic virtual-time testbed for security/correctness experiments.

All randomness derives from one seed; the same seed yields the same production schedule, network
schedule and attack schedule for every evaluated system (paired design / common random numbers).
Virtual time drives protocol semantics (horizons, windows, revocation times); processing cost is
measured separately in wall-clock nanoseconds around every ingest call.

Topology: one plant, G gateways (one per production cell), D devices per gateway, one asset per
device. A fraction of devices are "legacy" (cannot sign; the edge workload is their origin signer).
"""
from __future__ import annotations

import heapq
import math
import random
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from .b5 import B5FeedLevel
from .baselines import B1Conventional, B2ZeroTrust, B3Provenance, B4Combined
from .envelope import PBTI_WIRE
from .canonical import canonical_bytes
from .crypto import b64u, keypair_from_seed, sha256
from .envelope import (LogicalObs, b1_wire, b2_wire, b3_record, b3_wire_from_record, content_key,
                       pbti_content_digest, pbti_sign_obs, pbti_wire)
from .identity import TrustRegistry
from .policy import PolicyStore
from .review import RELEASABLE, AutoReviewer
from .verifier import Ablation, PBTIVerifier, VerifierConfig

FAR = 10 * 365 * 86_400_000


# =============================================================================== configuration
@dataclass
class NetConfig:
    base_ms: float = 20.0
    jitter_mean_ms: float = 10.0
    p_reorder: float = 0.0       # extra delay U(200, reorder_max_ms)
    reorder_max_ms: int = 3_000
    p_delay: float = 0.0         # long delay U(delay_min_ms, delay_max_ms)
    delay_min_ms: int = 30_000
    delay_max_ms: int = 90_000
    p_dup: float = 0.0           # transport duplicate (redelivery)
    p_loss: float = 0.0          # message lost in transit (no ack -> retransmission)
    p_ackloss: float = 0.0       # delivered but acknowledgement lost (-> retransmission)
    ack_ms: float = 20.0


@dataclass
class WorldConfig:
    seed: int = 1
    system: str = "PBTI"           # PBTI | B1 | B2 | B3
    ablation: Ablation = field(default_factory=Ablation)
    n_gw: int = 4
    dev_per_gw: int = 6
    legacy_per_gw: int = 1
    rate_hz: float = 1.0
    duration_ms: int = 300_000
    drain_ms: int = 180_000        # extra time after production stops for buffers to drain
    rto_ms: int = 2_000
    drain_rate_per_s: float = 60.0  # per-gateway send rate limit while a backlog exists
    net: NetConfig = field(default_factory=NetConfig)
    vcfg: VerifierConfig = field(default_factory=VerifierConfig)
    params: dict = field(default_factory=dict)     # policy parameter overrides
    use_x509: bool = True
    wl_validity_ms: int = FAR      # workload credential lifetime (short-lived SVID if small)
    wl_renew_ms: int = 0           # renewal period (0 = no rotation)
    dev_cert_exp: dict = field(default_factory=dict)  # did -> expiry of the first device certificate
    measure: bool = True
    review_every_ms: int = 0       # V3: periodic automated quarantine review (0 = off; on for B5 and PBTI-R)
    review_delay_ms: int = 60_000  # V3: minimum case age before review (review delay R)
    review_mode: str = "periodic"  # V4: "periodic" (cadence review_every_ms) | "event" (after every admission; R = 0)
    review_rule: str = "oneshot"   # V4: "oneshot" (V3: uncorroborated -> REJECT) | "defer" (see src/pbti/review.py)
    temporal: bool = False         # V4: record authoritative-state transitions (src/pbti/temporal.py)
    sh_timeout_ms: int = 0         # V4: PBTI-SH hold timeout (0 = none: held until corroborated)
    release_evidence: str = "discretionary"  # V4 (A5): REVOKED_BUFFERED waiver policy: discretionary | none | witness


# =============================================================================== edge entities
class Device:
    def __init__(self, world: "World", g: int, j: int, legacy: bool):
        self.g, self.j = g, j
        self.did = f"pa-c{g}-d{j:02d}"
        self.aid = f"pa-c{g}-a{j:02d}"
        self.legacy = legacy
        self.ep, self.seq = 0, 0
        self.prev: Optional[str] = None
        self.key_gen = 1
        self.kid = f"dk:{self.did}:{self.key_gen}"
        self.sk = None
        self.clock_offset = 0
        self.freeze_until = -1
        self.freeze_ts = 0
        self.seq_bug = False
        self.history: deque = deque()  # recently produced items (device-side retransmission buffer)
        rng = random.Random(world.seed * 7919 + g * 101 + j)
        self.phase = rng.random() * 2 * math.pi
        self.base_t = 55 + 20 * rng.random()
        self.offset_ms = int(rng.random() * 1000)

    def clock(self, t: int) -> int:
        if t < self.freeze_until:
            return self.freeze_ts
        return t + self.clock_offset

    def sample(self, rng: random.Random, t: int) -> dict:
        s = t / 1000.0
        return {
            "temp_c": round(self.base_t + 3 * math.sin(2 * math.pi * s / 120 + self.phase) + rng.gauss(0, 0.2), 2),
            "vib_mm_s": round(2.0 + 0.5 * math.sin(2 * math.pi * s / 30 + self.phase) + rng.gauss(0, 0.05), 3),
            "press_bar": round(5.0 + 0.2 * math.sin(2 * math.pi * s / 60) + rng.gauss(0, 0.02), 3),
            "flow_m3h": round(12.0 + 1.5 * math.sin(2 * math.pi * s / 90 + self.phase) + rng.gauss(0, 0.1), 2),
        }


@dataclass
class Entry:
    wire: bytes
    item: Any
    t_buf: int
    acked: bool = False
    ack_persisted: bool = False
    last_send: int = -10 ** 12
    sends: int = 0


class Gateway:
    def __init__(self, world: "World", g: int):
        self.w = world
        self.g = g
        self.gid = f"gw{g}"
        self.wid = f"spiffe://plant-a.example/cell{g}/gw{g}/collector"
        self.key_gen = 1
        self.kid = f"wk:gw{g}:{self.key_gen}"
        self.sk = None
        self.devices: list[Device] = []
        self.buffer: deque[Entry] = deque()
        self.unacked: dict[int, Entry] = {}
        self.link_up = True
        self.alive = True
        self.new_session = True
        self.legacy_ep = 0
        self.legacy_seq: dict[str, int] = {}
        self.legacy_prev: dict[str, Optional[str]] = {}
        self.next_send_slot = 0
        self.sent_total = 0
        self.tokens = 0.0
        self.tok_t = 0
        self.pump_scheduled = False

    def meta(self) -> dict:
        m = {"tid": self.wid, "tkid": self.kid, "new_session": self.new_session}
        self.new_session = False
        return m


# =============================================================================== world
class World:
    def __init__(self, cfg: WorldConfig):
        self.cfg = cfg
        self.seed = cfg.seed
        self.rng = random.Random(cfg.seed)          # production / payload randomness
        self.nrng = random.Random(cfg.seed * 31 + 7)  # network randomness
        self.arng = random.Random(cfg.seed * 57 + 3)  # attacker decisions (identical across systems)
        self.mrng = random.Random(cfg.seed * 91 + 5)  # system-specific attack rendering (mutations, forged sig bytes)
        self.grng = random.Random(cfg.seed * 13 + 11)  # gateway-assigned message ids on re-wrap (B1/B2 only)
        self.seedb = f"pbti-seed-{cfg.seed}".encode()
        self.trust = TrustRegistry(self.seedb, use_x509=cfg.use_x509)
        self.gateways: list[Gateway] = []
        self.devices: dict[str, Device] = {}
        self.q: list = []
        self._qn = 0
        self.now = 0
        # ground truth
        self.truth: list[dict] = []           # every legitimately produced observation
        self.attack_log: list[dict] = []
        self.ingest_ns: list[int] = []
        self.wrap_ns: list[int] = []
        self.sign_dev_ns: list[int] = []
        self.wire_bytes: list[int] = []
        self.dispositions: dict[str, int] = {}
        self.receipts_by_label: dict[str, dict[str, int]] = {}
        self.captured: list[tuple] = []
        self.hooks_deliver: list[Callable] = []
        self.recovery_marks: dict[str, Any] = {}
        self._build()

    # --------------------------------------------------------------- setup
    def _build(self) -> None:
        cfg = self.cfg
        devices_doc, workloads_doc = {}, {}
        for g in range(1, cfg.n_gw + 1):
            gw = Gateway(self, g)
            gw.sk, pk = keypair_from_seed(self.seedb, gw.kid)
            self.trust.issue(gw.kid, "workload", gw.wid, pk, -60_000, min(FAR, cfg.wl_validity_ms))
            for j in range(1, cfg.dev_per_gw + 1):
                d = Device(self, g, j, legacy=(j <= cfg.legacy_per_gw))
                if not d.legacy:
                    d.sk, dpk = keypair_from_seed(self.seedb, d.kid)
                    self.trust.issue(d.kid, "device", d.did, dpk, -60_000, cfg.dev_cert_exp.get(d.did, FAR))
                gw.devices.append(d)
                self.devices[d.did] = d
                devices_doc[d.did] = {"assets": [d.aid], "origin": "gateway" if d.legacy else "device",
                                      "schemas": ["telemetry.v1"], "active": True}
            workloads_doc[gw.wid] = {"relay": [d.did for d in gw.devices], "active": True}
            self.gateways.append(gw)
        self.policy_doc = {"devices": devices_doc, "workloads": workloads_doc, "params": dict(cfg.params)}
        s = cfg.system
        if s in ("B5", "PBTI-R") and not cfg.review_every_ms and cfg.review_mode == "periodic":
            cfg.review_every_ms = 10_000
        if cfg.review_mode not in ("periodic", "event"):
            raise ValueError(cfg.review_mode)
        if cfg.review_mode == "event" and cfg.review_delay_ms != 0:
            raise ValueError("event-driven review is defined for a minimum case age of 0 (decision D03)")
        self.reviewer = None
        if cfg.review_every_ms or cfg.review_mode == "event":
            rid, rkid, rsk = AutoReviewer.provision(self.trust, self.seedb)
            self.policy_doc["reviewers"] = {rid: {"may_release": list(RELEASABLE), "active": True}}
            self.reviewer = AutoReviewer(rid, rkid, rsk, min_age_ms=cfg.review_delay_ms, rule=cfg.review_rule)
        self.policy = PolicyStore(self.policy_doc, 0)
        vsk, vpk = keypair_from_seed(self.seedb, "verifier-evidence-key")
        self.vkeys = (vsk, vpk)
        if s in ("PBTI", "PBTI-R"):
            self.sys = PBTIVerifier(self.trust, self.policy, self.vkeys, cfg=cfg.vcfg, ablation=cfg.ablation)
        elif s == "PBTI-SH":
            from .selective import SelectiveHoldVerifier
            self.sys = SelectiveHoldVerifier(self.trust, self.policy, self.vkeys, cfg=cfg.vcfg, ablation=cfg.ablation,
                                             timeout_ms=cfg.sh_timeout_ms)
        elif s in ("B5", "B5S"):
            self.sys = B5FeedLevel(self.trust, self.policy, self.vkeys, cfg=cfg.vcfg, recovery=(s == "B5"))
        elif s == "B1":
            self.sys = B1Conventional(self.trust, self.policy, cfg=cfg.vcfg)
        elif s == "B2":
            self.sys = B2ZeroTrust(self.trust, self.policy, cfg=cfg.vcfg)
        elif s == "B3":
            self.sys = B3Provenance(self.trust, self.policy, self.vkeys, cfg=cfg.vcfg)
        elif s == "B4":
            self.sys = B4Combined(self.trust, self.policy, self.vkeys, cfg=cfg.vcfg)
        else:
            raise ValueError(s)
        # production schedule
        period = int(1000 / cfg.rate_hz)
        for gw in self.gateways:
            for d in gw.devices:
                self.at(d.offset_ms, self._produce, d, gw, period)
        if cfg.wl_renew_ms:
            for gw in self.gateways:
                self.at(cfg.wl_renew_ms, self._renew_workload, gw)
        for gw in self.gateways:
            self.at(0, self._send_tick, gw)
        self.cv_samples = 0
        self.cv_wrong = 0
        self.at(5_000, self._cv_sample)
        if self.reviewer is not None and cfg.review_mode == "periodic":
            self.at(cfg.review_every_ms, self._review_tick)
        self._ci_n, self._case_idx, self._ev_n = 0, {}, 0   # V4: event-driven review bookkeeping
        self.event_review_rounds = 0
        if getattr(self.sys, "release_evidence", None) is not None:
            self.sys.release_evidence = cfg.release_evidence
        self.revocations: list[tuple] = []     # V4: (t_rev, kid, t_comp) as executed
        self.tracer = None
        if cfg.temporal:
            from .temporal import Tracer
            self.tracer = Tracer(self)

    def _event_review(self, wire: bytes) -> None:
        """V4: event-driven review (review_mode="event", minimum case age 0). After an admission, review the open cases
        whose identity or hash-link neighbourhood the admission touched (the receipt's identity and its neighbours,
        identities whose slot state changed, newly opened cases); a release re-examines its neighbours. Cases are
        processed in identity order; every case is decided at most once per round, so the cascade terminates."""
        v = self.sys
        cand: set = set()
        try:
            from .envelope import pbti_parse
            o = pbti_parse(wire)[0]
            cand |= {(o["did"], o["ep"], o["seq"] + d) for d in (-1, 0, 1)}
        except Exception:  # noqa: BLE001  (malformed receipts touch no identity)
            pass
        rounds = 0
        while True:
            cand |= self._event_touched()
            wds = {wd for e in cand for wd in self._case_idx.get(e, ())}
            if not wds:
                return
            res = self.reviewer.run_on(v, self.now, wds)
            rounds += 1
            self.event_review_rounds += 1
            cand = set()
            for r in res:
                if str(r.get("outcome", "")).startswith("RELEASED"):
                    c = v.qcases.get(r["case"])
                    if c and c.get("eid"):
                        did, ep, sq = c["eid"]
                        cand |= {(did, ep, sq - 1), (did, ep, sq + 1)}
            if not cand and not self._event_pending():
                return
            if rounds > 100_000:
                raise RuntimeError("event-driven review did not terminate")

    def _event_pending(self) -> bool:
        return len(self.sys.qcases) != self._ci_n or len(getattr(self.sys, "reg", None).state_events) != self._ev_n

    def _event_touched(self) -> set:
        """Index newly opened cases by identity and return the identities touched since the last call."""
        import itertools
        v = self.sys
        out: set = set()
        if len(v.qcases) != self._ci_n:
            for wd in itertools.islice(v.qcases, self._ci_n, None):
                e = v.qcases[wd].get("eid")
                if e:
                    k = tuple(e)
                    self._case_idx.setdefault(k, set()).add(wd)
                    out.add(k)
            self._ci_n = len(v.qcases)
        ev = v.reg.state_events
        if len(ev) != self._ev_n:
            for (_t, key, _o, _n, _c) in ev[self._ev_n:]:
                if isinstance(key, tuple) and len(key) == 3 and isinstance(key[2], int):
                    out |= {(key[0], key[1], key[2] + d) for d in (-1, 0, 1)}
            self._ev_n = len(ev)
        return out

    def _review_tick(self) -> None:
        """V3: periodic automated review of quarantine/hold cases (operator policy, src/pbti/review.py)."""
        if self.now + self.cfg.review_every_ms <= self.cfg.duration_ms + self.cfg.drain_ms:
            self.at(self.now + self.cfg.review_every_ms, self._review_tick)
        self.reviewer.run(self.sys, self.now)

    # --------------------------------------------------------------- event queue
    def at(self, t: int, fn: Callable, *args) -> None:
        self._qn += 1
        heapq.heappush(self.q, (int(t), self._qn, fn, args))

    def run(self) -> None:
        end = self.cfg.duration_ms + self.cfg.drain_ms
        while self.q:
            t, _, fn, args = heapq.heappop(self.q)
            if t > end:
                break
            self.now = t
            fn(*args)
        self.now = end
        self.sys.finalize(end)

    def _cv_sample(self) -> None:
        """Order correctness of the current-value table: at each sample the system's current value for
        an asset must be the observation with the highest TRUE production order among the asset's
        authoritative observations held by the system at that instant."""
        if self.now + 5_000 <= self.cfg.duration_ms + self.cfg.drain_ms:
            self.at(self.now + 5_000, self._cv_sample)
        self.sys.advance(self.now)
        proc = self.sys.proc
        tprod = self._tprod_index()
        for aid, members in proc.cur.items():
            if not members:
                continue
            got = max(members.values(), key=lambda x: x[0])[1]
            best = max((tprod.get(ck, -1), ck) for _, ck in members.values())[1]
            self.cv_samples += 1
            if got != best:
                self.cv_wrong += 1

    def _tprod_index(self) -> dict:
        n = len(self.truth)
        if getattr(self, "_tp_n", 0) != n:
            self._tp = {tr["ck"]: tr["t"] for tr in self.truth}
            self._tp_n = n
        return self._tp

    # --------------------------------------------------------------- production
    def _produce(self, d: Device, gw: Gateway, period: int) -> None:
        t = self.now
        if t >= self.cfg.duration_ms:
            return
        gw = self.gateways[d.g - 1]  # current cell (devices may be re-assigned)
        self.at(t + period, self._produce, d, gw, period)
        pl = d.sample(self.rng, t)
        ts = d.clock(t)
        mid = f"{self.rng.getrandbits(64):016x}"
        if d.legacy:
            o = LogicalObs(d.did, d.aid, -1, -1, ts, "telemetry.v1", pl, mid)
        else:
            o = LogicalObs(d.did, d.aid, d.ep, d.seq, ts, "telemetry.v1", pl, mid)
            if not d.seq_bug:
                d.seq += 1
            else:
                d.seq_bug = False  # bug: sequence counter not advanced once (seq reuse)
        o.meta = {"t_prod": t, "gw": gw.gid}
        item = self._device_side(d, o)
        self.truth.append({"did": d.did, "aid": d.aid, "ts": ts, "t": t, "pl": pl, "o": o,
                           "ck": content_key(d.did, d.aid, ts, "telemetry.v1", pl)})
        d.history.append((t, item))
        while d.history and d.history[0][0] < t - 60_000:
            d.history.popleft()
        if gw.alive:
            self._gw_accept(gw, d, item)

    def _device_side(self, d: Device, o: LogicalObs):
        s = self.cfg.system
        if d.legacy or s in ("B1", "B2"):
            return o
        t0 = time.perf_counter_ns()
        if s in PBTI_WIRE:
            o.prev = d.prev
            obs, osig = pbti_sign_obs(o, d.sk, d.kid)
            d.prev = b64u(pbti_content_digest(obs))
            item = ("pbti", o, obs, osig)
        else:  # B3
            rec = b3_record(o, d.kid)
            item = ("b3", o, b3_wire_from_record(rec, d.sk))
        self.sign_dev_ns.append(time.perf_counter_ns() - t0)
        return item

    def _gw_accept(self, gw: Gateway, d: Device, item, mode: Optional[str] = None) -> None:
        t = self.now
        if mode is None:
            mode = "live" if gw.link_up else "buffered"
        t0 = time.perf_counter_ns()
        wire = self._wrap(gw, d, item, mode, t)
        self.wrap_ns.append(time.perf_counter_ns() - t0)
        self.wire_bytes.append(len(wire))
        e = Entry(wire, item, t)
        _obs_of(item).meta["gw_accepted"] = True
        _obs_of(item).meta.setdefault("t_acc", t)     # V4: first acceptance by a gateway (temporal population)
        gw.buffer.append(e)
        gw.unacked[id(e)] = e
        self._try_send(gw)

    def _wrap(self, gw: Gateway, d: Device, item, mode: str, t: int) -> bytes:
        s = self.cfg.system
        if s == "B1":
            return b1_wire(_with_gw_mid(self, item), gw.wid)
        if s == "B2":
            return b2_wire(_with_gw_mid(self, item), gw.wid)
        if s == "B3":
            if d.legacy:
                rec = b3_record(item, gw.kid)
                return b3_wire_from_record(rec, gw.sk)
            return item[2]
        # PBTI
        if d.legacy:
            o: LogicalObs = item
            seq = gw.legacy_seq.get(d.did, 0)
            o.ep, o.seq = gw.g * 1000 + gw.legacy_ep, seq  # epoch namespace per attesting gateway
            o.prev = gw.legacy_prev.get(d.did) if seq > 0 else None
            obs, osig = pbti_sign_obs(o, gw.sk, gw.kid)
            gw.legacy_seq[d.did] = seq + 1
            gw.legacy_prev[d.did] = b64u(pbti_content_digest(obs))
        else:
            _, o, obs, osig = item
        eids = o.meta.setdefault("eids", [])        # V4: every identity under which an honest gateway wrapped it
        eid = (obs["did"], obs["ep"], obs["seq"])
        if eid not in eids:
            eids.append(eid)
        return pbti_wire(obs, osig, gw.wid, gw.kid, gw.sk, t, mode)

    # --------------------------------------------------------------- sending
    def _try_send(self, gw: Gateway) -> None:
        if not (gw.alive and gw.link_up):
            return
        self._pump(gw)

    def _send_tick(self, gw: Gateway) -> None:
        if self.now <= self.cfg.duration_ms + self.cfg.drain_ms:
            self.at(self.now + 250, self._send_tick, gw)
        if gw.alive and gw.link_up:
            self._pump(gw)

    def _pump(self, gw: Gateway) -> None:
        """Send due entries. While a backlog exists the gateway is limited by a token bucket
        (drain_rate_per_s, burst of one second) that models uplink bandwidth."""
        t = self.now
        rate = self.cfg.drain_rate_per_s
        gw.tokens = min(rate, gw.tokens + (t - gw.tok_t) * rate / 1000.0)
        gw.tok_t = t
        backlog = 0
        for e in gw.buffer:
            if not e.acked and e.sends == 0:
                backlog += 1
                if backlog > 20:
                    break
        limited = backlog > 20
        for e in list(gw.buffer):
            if e.acked:
                continue
            due = e.sends == 0 or (t - e.last_send >= self.cfg.rto_ms)
            if not due:
                continue
            if limited:
                if gw.tokens < 1.0:
                    if not gw.pump_scheduled:
                        gw.pump_scheduled = True
                        self.at(t + int(1000.0 / rate) + 1, self._pump_cb, gw)
                    break
                gw.tokens -= 1.0
            e.sends += 1
            e.last_send = t
            gw.sent_total += 1
            self._transmit(gw, e, t)
        while gw.buffer and gw.buffer[0].acked:
            gw.buffer.popleft()

    def _pump_cb(self, gw: Gateway) -> None:
        gw.pump_scheduled = False
        if gw.alive and gw.link_up:
            self._pump(gw)

    def _transmit(self, gw: Gateway, e: Entry, t: int) -> None:
        n = self.cfg.net
        r = self.nrng
        if r.random() < n.p_loss:
            return
        delay = n.base_ms + r.expovariate(1.0 / n.jitter_mean_ms)
        if r.random() < n.p_reorder:
            delay += r.uniform(200, n.reorder_max_ms)
        if r.random() < n.p_delay:
            delay += r.uniform(n.delay_min_ms, n.delay_max_ms)
        meta = gw.meta()
        self.at(t + delay, self._deliver, gw, e, e.wire, meta, "legit")
        if r.random() < n.p_dup:
            self.at(t + delay + r.uniform(1, 500), self._deliver, gw, None, e.wire, dict(meta, new_session=False), "legit-dup")

    def _deliver(self, gw: Optional[Gateway], e: Optional[Entry], wire: bytes, meta: dict, label: str) -> None:
        for h in self.hooks_deliver:
            res = h(self, gw, e, wire, meta, label)
            if res is None:
                continue
            if res == "DROP":
                if gw is not None and e is not None:
                    self.at(self.now + self.cfg.net.ack_ms, self._ack, gw, e)  # broker acks, then drops
                return
            wire, meta, label = res
        self.receive(wire, meta, label)
        if gw is not None and e is not None:
            if self.nrng.random() >= self.cfg.net.p_ackloss:
                self.at(self.now + self.cfg.net.ack_ms, self._ack, gw, e)

    def receive(self, wire: bytes, meta: dict, label: str) -> None:
        t = self.now
        if self.cfg.measure:
            t0 = time.perf_counter_ns()
            r = self.sys.ingest(wire, t, meta)
            self.ingest_ns.append(time.perf_counter_ns() - t0)
        else:
            r = self.sys.ingest(wire, t, meta)
        k = r.disp + "/" + r.why.split(":")[0]
        d = self.receipts_by_label.setdefault(label, {})
        d[k] = d.get(k, 0) + 1
        if self.tracer is not None:
            self.tracer.note_receipt(t, wire, label)
        if self.reviewer is not None and self.cfg.review_mode == "event":
            self._event_review(wire)

    def _ack(self, gw: Gateway, e: Entry) -> None:
        if not gw.alive:
            return
        if not e.acked:
            e.acked = True
            gw.unacked.pop(id(e), None)
            # ack marks are persisted lazily (every 2 s) -> restart may resend delivered entries
            self.at(self.now + 2_000, _persist_ack, e)

    # --------------------------------------------------------------- control events
    def partition(self, g: int, t0: int, t1: int) -> None:
        gw = self.gateways[g - 1]
        def down():
            gw.link_up = False
        def up():
            gw.link_up = True
            gw.new_session = True
            self.recovery_marks.setdefault("reconnect", []).append((gw.gid, self.now))
            self._try_send(gw)
        self.at(t0, down)
        self.at(t1, up)

    def gateway_restart(self, g: int, t: int, down_ms: int = 5_000, reread_ms: int = 10_000) -> None:
        gw = self.gateways[g - 1]
        def crash():
            gw.alive = False
            if self.cfg.ablation.volatile_buffer:
                lost = [e for e in gw.buffer if not e.acked]
                self.recovery_marks["volatile_lost"] = self.recovery_marks.get("volatile_lost", 0) + len(lost)
                gw.buffer.clear()
                gw.unacked.clear()
            else:
                # durable buffer survives; acknowledgements not yet persisted are forgotten
                for e in gw.buffer:
                    if e.acked and not e.ack_persisted:
                        e.acked = False
                        gw.unacked[id(e)] = e
                    e.sends = 0
        def boot():
            gw.alive = True
            gw.new_session = True
            gw.legacy_ep += 1
            gw.legacy_seq.clear()
            gw.legacy_prev.clear()
            # OT-side at-least-once: signing devices resend their recent history to the gateway
            for d in gw.devices:
                if d.legacy:
                    continue
                for (tp, item) in list(d.history):
                    if tp >= self.now - down_ms - reread_ms:
                        self._gw_accept(gw, d, _rewrap_item(self, d, item), mode="buffered")
            self._try_send(gw)
        self.at(t, crash)
        self.at(t + down_ms, boot)

    def device_reboot(self, did: str, t: int) -> None:
        d = self.devices[did]
        def reboot():
            d.ep += 1
            d.seq = 0
            d.prev = None
        self.at(t, reboot)

    def device_seq_bug(self, did: str, t: int) -> None:
        d = self.devices[did]
        self.at(t, lambda: setattr(d, "seq_bug", True))

    def clock_freeze(self, did: str, t: int, dur: int) -> None:
        d = self.devices[did]
        def f():
            d.freeze_ts = d.clock(self.now)
            d.freeze_until = self.now + dur
        self.at(t, f)

    def clock_step(self, did: str, t: int, delta: int) -> None:
        d = self.devices[did]
        self.at(t, lambda: setattr(d, "clock_offset", d.clock_offset + delta))

    def rotate_device_key(self, did: str, t: int) -> None:
        """Planned rotation: the device switches to a new key at t; the old certificate's validity
        (set at build time through cfg.dev_cert_exp) ends shortly after (overlap)."""
        d = self.devices[did]
        def rot():
            d.key_gen += 1
            d.kid = f"dk:{d.did}:{d.key_gen}"
            d.sk, pk = keypair_from_seed(self.seedb, d.kid)
            self.trust.issue(d.kid, "device", d.did, pk, self.now - 1_000, FAR, self.now)
        self.at(t, rot)

    def _renew_workload(self, gw: Gateway) -> None:
        if self.now > self.cfg.duration_ms + self.cfg.drain_ms:
            return
        self.at(self.now + self.cfg.wl_renew_ms, self._renew_workload, gw)
        gw.key_gen += 1
        gw.kid = f"wk:gw{gw.g}:{gw.key_gen}"
        gw.sk, pk = keypair_from_seed(self.seedb, gw.kid)
        self.trust.issue(gw.kid, "workload", gw.wid, pk, self.now - 1_000, self.now + self.cfg.wl_validity_ms, self.now)
        gw.new_session = True

    def revoke(self, kid_fn: Callable[[], str], t_rev: int, t_comp: Optional[int]) -> None:
        def rv():
            kid = kid_fn()
            self.trust.revoke(kid, t_rev, t_comp, "incident-response")
            self.revocations.append((t_rev, kid, t_comp))
        self.at(t_rev, rv)

    def policy_update(self, t: int, mutate: Callable[[dict], None]) -> None:
        def up():
            import copy
            doc = copy.deepcopy(self.policy.current().doc)
            mutate(doc)
            self.policy.update(doc, self.now)
        self.at(t, up)


# =============================================================================== helpers
def _obs_of(item) -> LogicalObs:
    return item[1] if isinstance(item, tuple) else item


def _persist_ack(e: Entry) -> None:
    if e.acked:
        e.ack_persisted = True


def _with_gw_mid(world: World, o: LogicalObs) -> LogicalObs:
    """Baselines B1/B2: the gateway assigns the message id when it wraps the observation."""
    if o.meta.get("rewrap"):
        o2 = LogicalObs(o.did, o.aid, o.ep, o.seq, o.ts, o.sch, o.pl, f"{world.grng.getrandbits(64):016x}", o.prev, dict(o.meta))
        return o2
    return o


def _rewrap_item(world: World, d: Device, item):
    s = world.cfg.system
    if s in ("B1", "B2"):
        item.meta["gw_accepted"] = True  # the original observation reaches the gateway again
        o = LogicalObs(item.did, item.aid, item.ep, item.seq, item.ts, item.sch, item.pl, item.mid, item.prev,
                       dict(item.meta, rewrap=True))
        return o
    return item
