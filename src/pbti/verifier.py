"""PBTI trust-aware ingestion verifier (cloud-side Policy Enforcement Point for data objects).

Admission pipeline for every receipt (see docs/PROTOCOL_SPECIFICATION.md, Algorithm 1):
  1 parse + structural validation            -> REJECT/MALFORMED
  2 resolve keys, bind keys to subjects       -> REJECT/UNKNOWN_KEY | KEY_SUBJECT_MISMATCH
  3 verify relay signature, odig binding,
    observation signature                     -> REJECT/INTEGRITY_RELAY | BINDING_MISMATCH | INTEGRITY_OBS
  4 credential lifecycle (revocation, validity, rotation grace)
                                              -> REJECT/REVOKED | QUARANTINE/REVOKED_BUFFERED | KEY_EXPIRED
  5 path-bound admission policy + freshness   -> REJECT/UNAUTHORIZED:* | QUARANTINE/FUTURE_TS | STALE_TS
  6 delivery-history classification on the event registry (Rule L)
                                              -> ACCEPT | DUPLICATE/RETRY|SUSPECTED_REPLAY | CONFLICT
                                                 | QUARANTINE/STALE_EPOCH|STALE_SLOT|SEQ_JUMP
  7 commit: content-addressed raw blob, registry update, evidence record, derived processing.
Every receipt (including rejects) produces one evidence record.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import NamedTuple, Optional

from .canonical import canonical_bytes
from .crypto import DOMAIN_OBS, DOMAIN_REL, DOMAIN_REVIEW, b64u, sha256, sha256_hex, ub64u, verify
from .envelope import MalformedMessage, content_key, pbti_parse
from .evidence import EvidenceLog
from .identity import TrustRegistry, TrustView
from .policy import PDP, PolicyStore
from .processor import Processor
from .review import QUARANTINED, REJECTED, RELEASED, REVIEW_PENDING, decision_body
from .registry import ABSENT, COMMITTED, CONTESTED, EpochState, Registry
from .store import MemoryStore

ACCEPT, DUPLICATE, CONFLICT, QUARANTINE, REJECT = "ACCEPT", "DUPLICATE", "CONFLICT", "QUARANTINE", "REJECT"


class Receipt(NamedTuple):
    disp: str
    why: str
    ann: tuple = ()


@dataclass
class Ablation:
    no_relay_sig: bool = False      # A1  workload identity not bound to the data object
    static_policy: bool = False     # A2  policy frozen at deployment time
    no_obs_sig: bool = False        # A3  no origin (device) signature verification
    no_prev_link: bool = False      # A4  no hash link to predecessor
    edge_event_id: bool = False     # A5  identity assigned at the edge (relay digest) instead of (did,ep,seq)
    no_conflict: bool = False       # A6  first-write-wins, later versions silently ignored
    no_staleness: bool = False      # A7  no horizon / epoch / sequence-jump checks
    arrival_order: bool = False     # A8  current value by arrival order
    no_commitment: bool = False     # A9  no evidence log / checkpoints / lineage commitments
    no_quarantine: bool = False     # A10 quarantine reasons become rejects
    no_revocation: bool = False     # A11 no revocation status / no taint propagation
    volatile_buffer: bool = False   # A12 edge buffer not durable (consumed by the gateway)

    def label(self) -> str:
        on = [k for k, v in self.__dict__.items() if v]
        return "+".join(on) if on else "full"


@dataclass
class VerifierConfig:
    tick_ms: int = 1_000
    emit_ms: int = 1_000
    checkpoint_batch: int = 512
    status_refresh_ms: int = 0
    window_ms: int = 10_000
    profile: bool = False


class PBTIVerifier:
    name = "PBTI"

    def __init__(self, trust: TrustRegistry, policy: PolicyStore, vkeys, store: Optional[MemoryStore] = None,
                 cfg: Optional[VerifierConfig] = None, ablation: Optional[Ablation] = None):
        self.cfg = cfg or VerifierConfig()
        self.ab = ablation or Ablation()
        self.trust = TrustView(trust, self.cfg.status_refresh_ms)
        self.trust_registry = trust
        self.pdp = PDP(policy, static=self.ab.static_policy)
        self.store = store or MemoryStore()
        self.reg = Registry()
        self.evidence = EvidenceLog(vkeys[0], vkeys[1], batch=self.cfg.checkpoint_batch, enabled=not self.ab.no_commitment)
        self.proc = Processor(self.cfg.window_ms, order="arrival" if self.ab.arrival_order else "seq",
                              lineage=not self.ab.no_commitment)
        self.next_tick = 0
        self.n_receipts = 0
        self.counts: dict[str, int] = {}
        self.receipt_log: list[tuple] = []  # (t, wire_digest, tid) — replayable input log for the auditor
        self.stage_ns = {"parse": 0, "crypto": 0, "lifecycle": 0, "policy": 0, "history": 0, "commit": 0}
        self.taint_events = 0
        self.lost_declared = 0
        self.quarantined_wires: set = set()
        # V4 (memo R09/A5): policy of the REVOKED_BUFFERED release waiver: "discretionary" (V3 behaviour, default:
        # device-asserted timestamp before t_comp), "none" (never), "witness" (exact-content pre-compromise evidence
        # from a TimeWitness, src/pbti/timewitness.py); compromise_low maps a kid to t_low of an uncertainty interval
        self.release_evidence = "discretionary"
        self.witness = None
        self.compromise_low: dict[str, int] = {}
        # V3 quarantine review workflow (src/pbti/review.py); unused unless a reviewer acts
        self.qcases: dict[str, dict] = {}
        self.review_outcomes: dict[str, int] = {}
        self.recovery_latencies: list[tuple[int, int]] = []  # (t_release - ts, t_release - t_quarantine)
        self.pre_comp_released: dict = {}     # V4 (D05): key -> (obs, canonical bytes) of REVOKED_BUFFERED releases

    # ----------------------------------------------------------------- time
    def advance(self, t: int) -> None:
        while self.next_tick <= t:
            self._tick(self.next_tick)
            self.next_tick += self.cfg.tick_ms

    def _tick(self, t: int) -> None:
        params = self.pdp.params(t)
        if not self.ab.no_revocation:
            self.trust.status("", t)
            self._apply_taints(t)
        if not self.ab.no_staleness:
            for did, st in self.reg.streams.items():
                for ep, es in st.epochs.items():
                    if es.gaps:
                        nb = len(es.closed)
                        n = es.close_old_gaps(t, params["gap_close_ms"])
                        self.lost_declared += n
                        for lo, hi in es.closed[nb:]:      # V3: reflect gap closure in the slot state (LOST)
                            for sq in range(lo, hi + 1):
                                sl = self.reg.slots.get((did, ep, sq))
                                if sl is not None and not sl.versions and not sl.lost:
                                    sl.lost = True
                                    self.reg.record_change(t, (did, ep, sq), "ABSENT", "LOST", "GAP_CLOSED")
        if t % self.cfg.emit_ms == 0:
            self.proc.emit(t)
        if t % 5_000 == 0:
            self.evidence.checkpoint(t, force=True)
        else:
            self.evidence.checkpoint(t)

    def finalize(self, t: int) -> None:
        self.advance(t)
        self._apply_taints(t)
        self.proc.emit(t)
        self.evidence.checkpoint(t, force=True)
        self.store.flush()

    def _apply_taints(self, t: int) -> None:
        for (t_seen, rev) in self.trust.drain_new():
            if self.ab.no_revocation or rev.t_comp_ms is None:
                continue
            for key in self.reg.by_kid.get(rev.kid, []):
                s = self.reg.slots[key]
                if s.state() == COMMITTED and not s.tainted and s.t_first >= rev.t_comp_ms:
                    pc = self.pre_comp_released.get(key)
                    if pc is not None and self._pre_compromise_ok(pc[0], pc[1], rev.kid, rev):
                        continue      # V4 (D05): the release condition still holds under this revocation record
                    s.tainted = True
                    self.taint_events += 1
                    self.reg.record_change(t, key, COMMITTED, "COMMITTED+TAINTED", "REVOCATION:" + rev.kid)
                    self.proc.remove(key, "TAINT_CORRECTION")

    # ----------------------------------------------------------------- ingest
    def ingest(self, wire: bytes, t: int, meta: Optional[dict] = None, waive: frozenset = frozenset(),
               log: bool = True) -> Receipt:
        """`waive` (V3) is used only by an authorized release decision: it waives the one quarantine reason that
        the reviewer released; `log=False` because the release itself is logged as a REVIEW entry."""
        self.advance(t)
        prof = self.cfg.profile
        t0 = time.perf_counter_ns() if prof else 0
        meta = meta or {}
        wd = sha256_hex(wire)
        if log:
            self.receipt_log.append((t, wd, meta.get("tid")))
        ev = {"rid": self.n_receipts, "t": t, "w": wd, "tid": meta.get("tid")}
        self.n_receipts += 1
        try:
            obs, osig, rel, rsig = pbti_parse(wire)
        except MalformedMessage as e:
            return self._finish(ev, wire, REJECT, "MALFORMED:" + str(e))
        t1 = time.perf_counter_ns() if prof else 0
        if prof:
            self.stage_ns["parse"] += t1 - t0
        try:   # V3: numbers outside the I-JSON range (|int| > 2^53, NaN, infinity) cannot be canonicalised -> REJECT
            cb_obs = canonical_bytes(obs)
            cb_rel = None if self.ab.no_relay_sig else canonical_bytes(rel)
        except (ValueError, TypeError):
            return self._finish(ev, wire, REJECT, "MALFORMED:non-canonical-number", t1)
        did, kid, wkid = obs["did"], obs["kid"], rel["wkid"]
        ev.update(kid=kid, wkid=wkid, eid=[did, obs["ep"], obs["seq"]])
        kd = self.trust.key(kid)
        kw = None if self.ab.no_relay_sig else self.trust.key(wkid)
        if kd is None or (kw is None and not self.ab.no_relay_sig):
            return self._finish(ev, wire, REJECT, "UNKNOWN_KEY")
        if self.ab.no_relay_sig:
            wid = meta.get("tid") or rel["wid"]
        else:
            wid = rel["wid"]
            if kw.kind != "workload" or kw.subject != wid:
                return self._finish(ev, wire, REJECT, "KEY_SUBJECT_MISMATCH")
        if kd.kind == "device":
            if kd.subject != did:
                return self._finish(ev, wire, REJECT, "KEY_SUBJECT_MISMATCH")
            origin = "device"
        elif kd.kind == "workload":
            if kd.subject != wid:
                return self._finish(ev, wire, REJECT, "KEY_SUBJECT_MISMATCH")
            origin = "workload"
        else:
            return self._finish(ev, wire, REJECT, "KEY_KIND_INVALID")
        if not self.ab.no_relay_sig:
            if not verify(kw.pk, DOMAIN_REL, cb_rel, rsig):
                return self._finish(ev, wire, REJECT, "INTEGRITY_RELAY", t1)
            if rel["odig"] != b64u(sha256(cb_obs + osig)):
                return self._finish(ev, wire, REJECT, "BINDING_MISMATCH", t1)
        if not self.ab.no_obs_sig:
            if not verify(kd.pk, DOMAIN_OBS, cb_obs, osig):
                return self._finish(ev, wire, REJECT, "INTEGRITY_OBS", t1)
        t2 = time.perf_counter_ns() if prof else 0
        if prof:
            self.stage_ns["crypto"] += t2 - t1
        params = self.pdp.params(t)
        ann: list[str] = []
        if not self.ab.no_revocation:
            for info in ((kd,) if self.ab.no_relay_sig else (kd, kw)):
                rev = self.trust.status(info.kid, t)
                if rev is not None:
                    if "REVOKED_BUFFERED" in waive and self._pre_compromise_ok(obs, cb_obs, info.kid, rev):
                        ann.append("RELEASED_PRE_COMPROMISE:" + info.kind)
                        continue
                    if rel["mode"] == "buffered" and params["on_revoked_buffered"] == "quarantine" and not self.ab.no_quarantine:
                        return self._finish(ev, wire, QUARANTINE, "REVOKED_BUFFERED:" + info.kind)
                    return self._finish(ev, wire, REJECT, "REVOKED:" + info.kind)
        for info in ((kd,) if self.ab.no_relay_sig else (kd, kw)):
            if t < info.nbf_ms:
                return self._finish(ev, wire, REJECT, "KEY_NOT_YET_VALID:" + info.kind)
            if t > info.exp_ms:
                if t - info.exp_ms <= params["rotation_grace_ms"]:
                    ann.append("KEY_IN_GRACE:" + info.kind)
                else:
                    return self._q(ev, wire, "KEY_EXPIRED:" + info.kind)
        t3 = time.perf_counter_ns() if prof else 0
        if prof:
            self.stage_ns["lifecycle"] += t3 - t2
        permit, why, pv = self.pdp.evaluate(did, obs["aid"], wid, obs["sch"], origin, t)
        ev["pv"] = pv
        if not permit:
            return self._finish(ev, wire, REJECT, "UNAUTHORIZED:" + why)
        if not self.ab.no_staleness:
            if obs["ts"] > t + params["skew_max_ms"]:
                return self._q(ev, wire, "FUTURE_TS")
            if t - obs["ts"] > params["h_max_ms"] and "STALE_TS" not in waive:
                return self._q(ev, wire, "STALE_TS")
        t4 = time.perf_counter_ns() if prof else 0
        if prof:
            self.stage_ns["policy"] += t4 - t3
        r = self._history(ev, wire, obs, rel, cb_obs, wid, kid, wkid, t, params, ann, waive)
        if r.disp == ACCEPT and not self.ab.edge_event_id and any(a.startswith("RELEASED_PRE_COMPROMISE") for a in ann):
            # V4 (D05): remember a reviewed pre-compromise release, so that a revised revocation record re-checks
            # its release condition instead of tainting it by commit time alone
            self.pre_comp_released[(did, obs["ep"], obs["seq"])] = (obs, cb_obs)
        if prof:
            t5 = time.perf_counter_ns()
            self.stage_ns["history"] += t5 - t4
        return r

    def _pre_compromise_ok(self, obs, cb_obs, kid, rev) -> bool:
        """V4: may an observation under revoked key `kid` be released by an authorized REVOKED_BUFFERED waiver?"""
        if rev.t_comp_ms is None or self.release_evidence == "none":
            return False
        if self.release_evidence == "discretionary":
            return obs["ts"] < rev.t_comp_ms                 # V3 rule: self-asserted timestamp (policy, not proof)
        if self.release_evidence == "witness":
            t_low = min(rev.t_comp_ms, self.compromise_low.get(kid, rev.t_comp_ms))
            return self.witness is not None and self.witness.proves_before(b64u(sha256(cb_obs)), t_low)
        raise ValueError(self.release_evidence)

    def _q(self, ev, wire, why):
        if self.ab.no_quarantine:
            return self._finish(ev, wire, REJECT, why)
        return self._finish(ev, wire, QUARANTINE, why)

    def _history(self, ev, wire, obs, rel, cb_obs, wid, kid, wkid, t, params, ann, waive=frozenset()) -> Receipt:
        did, ep, seq = obs["did"], obs["ep"], obs["seq"]
        cd = b64u(sha256(cb_obs))
        ev["cd"] = cd
        if self.ab.edge_event_id:
            key = (did, "edge", b64u(sha256(canonical_bytes(rel))))
        else:
            key = (did, ep, seq)
        reg = self.reg
        slot = reg.slots.get(key)
        if slot is not None and cd in slot.versions:
            if slot.state() == COMMITTED and slot.wid_first == wid and t - slot.t_first <= params["retry_window_ms"]:
                return self._finish(ev, wire, DUPLICATE, "RETRY", ann=ann)
            return self._finish(ev, wire, DUPLICATE, "SUSPECTED_REPLAY", ann=ann)
        if self.ab.no_conflict and slot is not None and slot.versions:
            return self._finish(ev, wire, DUPLICATE, "IGNORED_VERSION", ann=ann)
        use_seq = not self.ab.edge_event_id
        stream = reg.stream(did)
        es = stream.epochs.get(ep) if use_seq else None
        if use_seq and not self.ab.no_staleness:
            if es is not None and es.in_closed(seq) and (slot is None or not slot.versions) and "STALE_SLOT" not in waive:
                return self._q(ev, wire, "STALE_SLOT")
            if (ep < stream.max_ep and t - stream.epochs[stream.max_ep].t_open > params["epoch_drain_ms"]
                    and "STALE_EPOCH" not in waive):
                return self._q(ev, wire, "STALE_EPOCH")
            hw = es.hw if es is not None else -1
            if seq > hw + params["max_seq_jump"]:
                return self._q(ev, wire, "SEQ_JUMP")
        slot = reg.slot(key, create=True)
        before = slot.state()
        slot.versions[cd] = wd = ev["w"]
        first = len(slot.versions) == 1
        if first:
            slot.t_first, slot.wid_first, slot.kid, slot.wkid = t, wid, kid, wkid
            slot.ts, slot.aid, slot.obs_first = obs["ts"], obs["aid"], obs
            reg.by_kid.setdefault(kid, []).append(key)
        changes = []
        if use_seq and not self.ab.no_prev_link and not self.ab.no_conflict and seq > 0 and obs["prev"] is not None:
            pkey = (did, ep, seq - 1)
            ps = reg.slot(pkey, create=True)
            pb = ps.state()
            if ps.implied is None:
                ps.implied = set()
            ps.implied.add(obs["prev"])
            pa = ps.state()
            if pa != pb:
                changes.append((pkey, pb, pa))
        after = slot.state()
        order = "-"
        if use_seq and before == "ABSENT":
            if es is None:
                es = stream.epochs[ep] = EpochState(t)
            if ep > stream.max_ep:
                stream.max_ep = ep
            order = es.note_seq(seq, t)
        if after == COMMITTED:
            ann = ann + [order, "RECOVERED" if rel["mode"] == "buffered" else "LIVE"]
            rec = self._finish(ev, wire, ACCEPT, "COMMITTED", ann=ann, ns="raw")
            pl = obs["pl"]
            self.proc.add(key, obs["aid"], obs["ts"], pl, wd,
                          content_key(did, obs["aid"], obs["ts"], obs["sch"], pl), (ep, seq))
        else:
            why = "EQUIVOCATION" if before != "ABSENT" or len(slot.versions) > 1 else "LINK_MISMATCH"
            if before == COMMITTED:
                changes.append((key, COMMITTED, CONTESTED))
            rec = self._finish(ev, wire, CONFLICT, why, ann=ann)
        for k, old, new in changes:
            reg.record_change(t, k, old, new, "EVIDENCE")
            if old == COMMITTED and new == CONTESTED:
                self.proc.remove(k, "CONTEST_CORRECTION")
        return rec

    def _finish(self, ev: dict, wire: bytes, disp: str, why: str, t_prev: int = 0, ann=(), ns: str = "q") -> Receipt:
        prof = self.cfg.profile
        tc = time.perf_counter_ns() if prof else 0
        ev["disp"], ev["why"] = disp, why
        if disp == QUARANTINE:
            self.quarantined_wires.add(ev["w"])
            if ev["w"] not in self.qcases:
                self.qcases[ev["w"]] = {"state": QUARANTINED, "reason": why.split(":")[0], "t_q": ev["t"],
                                        "tid": ev.get("tid"), "eid": ev.get("eid")}
        if ann:
            ev["ann"] = list(ann)
        if not self.ab.no_commitment:
            if ns == "raw" or self.store.get_blob("raw", ev["w"]) is None:
                self.store.put_blob(ns, ev["w"], wire)
                ev["ns"] = ns
            else:
                ev["ns"] = "raw"  # byte-identical to an already committed raw object
            self.evidence.append(ev)
        else:
            if ns == "raw":
                self.store.append("raw_rows", wire, len(wire))
        self.counts[disp + "/" + why.split(":")[0]] = self.counts.get(disp + "/" + why.split(":")[0], 0) + 1
        if prof:
            self.stage_ns["commit"] += time.perf_counter_ns() - tc
        return Receipt(disp, why, tuple(ann))

    # ----------------------------------------------------------------- oracle views
    def is_authoritative(self, key, s) -> bool:
        return s.state() == COMMITTED and not s.tainted

    def authoritative(self):
        """Yield (obs_id, content_key) for every authoritative observation (COMMITTED, untainted)."""
        for key, s in self.reg.slots.items():
            if self.is_authoritative(key, s) and s.obs_first is not None:
                o = s.obs_first
                yield key, content_key(o["did"], o["aid"], o["ts"], o["sch"], o["pl"])

    def slot_summary(self) -> dict:
        c: dict[str, int] = {}
        for s in self.reg.slots.values():
            st = s.state() + ("+T" if s.tainted else "")
            c[st] = c.get(st, 0) + 1
        return c

    # ----------------------------------------------------------------- V3: quarantine review workflow
    def review_snapshot(self, wd: str) -> Optional[dict]:
        """Evidence a reviewer examines for one case: the quarantined statement's digests and the hash-link
        neighbourhood of its event identity. Deterministic, so a decision can be checked for staleness."""
        case = self.qcases.get(wd)
        blob = self.store.get_blob("q", wd) or self.store.get_blob("raw", wd)
        if case is None or blob is None:
            return None
        try:
            obs, _, _, _ = pbti_parse(blob)
        except MalformedMessage:
            return None
        did, ep, seq = obs["did"], obs["ep"], obs["seq"]
        cd = b64u(sha256(canonical_bytes(obs)))
        slot = self.reg.slots.get((did, ep, seq))
        pred = self.reg.slots.get((did, ep, seq - 1))
        return {"case": wd, "reason": case["reason"], "eid": [did, ep, seq], "cd": cd, "prev": obs["prev"],
                "slot_digests": sorted(slot.digests()) if slot else [],
                "pred_digests": sorted(pred.digests()) if pred else [],
                "pred_authoritative": bool(pred is not None and self.is_authoritative((did, ep, seq - 1), pred)),
                # digests that admitted successor statements assert for THIS identity via their prev link
                "succ_implied": sorted(slot.implied) if slot is not None and slot.implied else []}

    def open_review(self, wd: str, reviewer: str, t: int) -> Optional[dict]:
        """QUARANTINED -> REVIEW_PENDING; returns the evidence snapshot for the reviewer."""
        self.advance(t)
        case = self.qcases.get(wd)
        if case is None or case["state"] != QUARANTINED:
            return None
        self.receipt_log.append((t, wd, ("REVIEW_OPEN", reviewer)))
        case["state"] = REVIEW_PENDING
        case["reviewer"] = reviewer
        return self.review_snapshot(wd)

    def _reviewer_authorized(self, reviewer: str, reason: str, t: int) -> bool:
        doc = self.pdp.active_version(t).doc
        r = doc.get("reviewers", {}).get(reviewer)
        return bool(r and r.get("active", True) and reason in r.get("may_release", []))

    def apply_review(self, decision: dict, t: int) -> dict:
        self.advance(t)
        self.receipt_log.append((t, decision.get("case"), ("REVIEW", decision)))
        return self._apply_review(decision, t)

    def _apply_review(self, d: dict, t: int) -> dict:
        wd = d.get("case")
        case = self.qcases.get(wd)
        info = self.trust.key(d.get("rkid", ""))
        outcome = None
        try:
            sig_ok = info is not None and verify(info.pk, DOMAIN_REVIEW, decision_body(d), ub64u(d["sig"]))
        except Exception:  # noqa: BLE001
            sig_ok = False
        if not sig_ok or info.kind != "reviewer" or info.subject != d.get("reviewer"):
            outcome = "INVALID_REVIEWER_CREDENTIAL"
        elif self.trust.status(info.kid, t) is not None:
            outcome = "REVIEWER_REVOKED"
        elif case is None:
            outcome = "MISSING_EVIDENCE"
        elif case["state"] in (RELEASED, REJECTED):
            outcome = "ALREADY_DECIDED"
        elif case["state"] != REVIEW_PENDING:
            outcome = "NOT_PENDING"
        elif not self._reviewer_authorized(d["reviewer"], case["reason"], t):
            outcome = "UNAUTHORIZED_REVIEWER"
        elif self.store.get_blob("q", wd) is None and self.store.get_blob("raw", wd) is None:
            outcome = "MISSING_EVIDENCE"
        elif d.get("snapshot") != self.review_snapshot(wd):
            outcome = "STALE_REVIEW"
            case["state"] = QUARANTINED          # needs a fresh review of the current evidence
        elif d["decision"] == "REJECT":
            outcome = "REJECTED"
            case["state"] = REJECTED
        elif d["decision"] == "RELEASE":
            outcome = self._release(wd, case, t)
        else:
            outcome = "INVALID_DECISION"
        if outcome in ("UNAUTHORIZED_REVIEWER", "INVALID_REVIEWER_CREDENTIAL", "REVIEWER_REVOKED") and case is not None \
                and case["state"] == REVIEW_PENDING:
            case["state"] = QUARANTINED
        rec = {"type": "REVIEW", "t": t, "case": wd, "reviewer": d.get("reviewer"), "rkid": d.get("rkid"),
               "decision": d.get("decision"), "release_reason": d.get("reason"), "rsig": d.get("sig"),
               "orig_reason": case["reason"] if case else None, "evidence": d.get("snapshot"),
               "pv": self.pdp.active_version(t).version, "outcome": outcome,
               "affected": case.get("affected") if case else None, "disp": "REVIEW", "why": outcome}
        if not self.ab.no_commitment:
            self.evidence.append(rec)
        self.review_outcomes[outcome] = self.review_outcomes.get(outcome, 0) + 1
        return {"case": wd, "outcome": outcome}

    def _release(self, wd: str, case: dict, t: int) -> str:
        blob = self.store.get_blob("q", wd) or self.store.get_blob("raw", wd)
        r = self.ingest(blob, t, {"tid": case.get("tid")}, waive=frozenset({case["reason"]}), log=False)
        if r.disp == ACCEPT:
            case["state"] = RELEASED
            obs = pbti_parse(blob)[0]
            case["affected"] = [obs["aid"], obs["ts"] - obs["ts"] % self.cfg.window_ms]
            self.recovery_latencies.append((t - obs["ts"], t - case["t_q"]))
            return "RELEASED"
        case["state"] = REJECTED
        return "RELEASE_FAILED:" + r.disp + "/" + r.why.split(":")[0]
