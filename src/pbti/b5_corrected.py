"""B5 with the V9 corrections (corrected comparator).  The historical implementation, src/pbti/b5.py, is unchanged:
it produced every frozen result and stays the reference for them.  This module is used only by the V9 runners
(experiments/v9/), which store their rows separately and label them with the source digest of this file.

Corrections, each pinned by a regression test in tests/test_b5_corrected.py (audit findings F1-F3 and F8 of
results/v7/audit_core; reference-model discrepancies D2, D4, D5, D6 and D7 of results/v7/b5_refmodel):

  C1  Fork response only on NEW fork evidence (F1 / D2).  The historical B5 re-ran fork detection from slot
      state, so any admission at an already contested identity, or right after one, held again observations
      that review had released and, after a resume, started a new feed hold.  Here the feed-level response is
      triggered only by a receipt that adds one of
        E1  another admitted version of the same identity exists (two signed contents for one identity);
        E2  an admitted successor's `prev` names a different digest for this identity;
        E3  the receipt's `prev` names a digest that is not among the admitted versions of its predecessor
            (fork point: the predecessor).
      A successor whose `prev` names one of the admitted versions of a contested predecessor is not new evidence.
      New evidence at a later point of an already forked feed still holds again the observations from that point
      on, including released ones (historical V3 rule, unchanged).

  C2  No held observation without an open review case (F2 / D4).  Review cases are keyed by wire digest; the
      historical B5 therefore left an identity held with no pending case (never authoritative again) when
        (a) a reviewed release of another reason (e.g. STALE_TS) re-ran admission inside a held feed: the
            re-run was a feed hold, no hold case could be opened for the same wire, and the case was closed
            RELEASE_FAILED:QUARANTINE/FEED_FORK_HOLD;
        (b) a fork held a committed identity whose wire already had a pending case of another reason (e.g. a
            byte-identical stale retransmission) or a closed one.
      Here (a) leaves the case pending as a FEED_FORK_HOLD case from the time of the hold (review outcome
      DEFERRED_TO_FEED_HOLD), and in (b) the pending case of another reason becomes the FEED_FORK_HOLD case
      (a closed one is replaced by a new FEED_FORK_HOLD case).  A hold case opened or converted while a review
      decision is applied behaves like a case opened at that moment: periodic review does not decide it in the
      same pass (the reviewer selected that pass's cases before the decision), only from the next pass on,
      once its minimum age has passed; event-driven review may decide it in a later round of the same cascade.
      Every hold transition is recorded as a HELD state event, so event-driven review re-examines the held
      identity and its hash-link neighbours (the documented candidate rule of sim.World._event_review:
      "identities whose slot state changed").

  C3  Counters (F3 / D5, F8 / D7).  `holds` counts hold transitions: an identity entering the held set is
      counted once (the historical counter counted an identity held by the fork its own receipt revealed twice).
      `fork_events` keeps its definition (a feed's fork point is set or lowered) but is now driven by new
      evidence only.  Added: held_distinct_ever, recovered_distinct (identities released at least once, whereas
      recovered_n counts release events), fork_evidence_receipts, forked_feeds_distinct, deferred_releases,
      hold_case_conversions, hold_case_replacements.

  C4  Label (D6).  Releasing a held identity whose slot is tainted is reported as RELEASE_FAILED:TAINTED (the
      historical label was RELEASE_FAILED:CONFLICT).  Labels after the colon do not enter any result column.

Implementation choices that are kept and are now stated in docs/BASELINES.md (they apply to the historical and the
corrected B5 alike): identity order within a review pass (D1, shared with PBTI-R); contested identities get no
review case, and a feed's resume is checked after each hold-case decision (D3); the event-driven candidate rule of
sim.World._event_review (event scope).
"""
from __future__ import annotations

from .b5 import B5FeedLevel
from .crypto import b64u, sha256
from .envelope import content_key
from .registry import COMMITTED, EpochState
from .review import QUARANTINED, REJECTED, RELEASED
from .verifier import ACCEPT, CONFLICT, DUPLICATE, QUARANTINE, PBTIVerifier

IMPL_ID = "b5_corrected_v9"


class B5Corrected(B5FeedLevel):
    impl_id = IMPL_ID

    def __init__(self, *args, recovery: bool = True, review_mode: str = "periodic", **kw):
        super().__init__(*args, recovery=recovery, **kw)
        self.review_mode = review_mode            # "periodic" | "event" (set by the runner from the world config)
        self.init_kw = {"recovery": recovery, "review_mode": review_mode}   # the audit replay re-creates the class
        self._in_review = 0
        self._t_now = None
        self.held_ever: set = set()
        self.recovered_ids: set = set()
        self.forked_feeds_ever: set = set()
        self.fork_evidence_receipts = 0
        self.deferred_releases = 0
        self.hold_case_conversions = 0
        self.hold_case_replacements = 0

    def set_review_mode(self, mode: str) -> None:
        if mode not in ("periodic", "event"):
            raise ValueError(mode)
        self.review_mode = mode
        self.init_kw["review_mode"] = mode

    # ------------------------------------------------------------------ review pass bookkeeping
    def advance(self, t: int) -> None:
        self._t_now = t
        super().advance(t)

    def _opened_this_pass(self, case: dict, t) -> bool:
        return self.review_mode == "periodic" and t is not None and case.get("opened_in_review_t") == t

    def open_review(self, wd: str, reviewer: str, t: int):
        case = self.qcases.get(wd)
        if case is not None and self._opened_this_pass(case, t):
            self.advance(t)
            return None                           # opened during this pass: decided from the next pass on
        return super().open_review(wd, reviewer, t)

    def review_snapshot(self, wd: str):
        case = self.qcases.get(wd)
        if case is not None and self._opened_this_pass(case, self._t_now):
            return None                           # (the deferring reviewer peeks before opening)
        return super().review_snapshot(wd)

    def _apply_review(self, d: dict, t: int) -> dict:
        self._in_review += 1
        try:
            return super()._apply_review(d, t)
        finally:
            self._in_review -= 1

    # ------------------------------------------------------------------ held identities and their cases
    def _mark_held(self, key: tuple, t: int, old: str, cause: str) -> None:
        if key in self.held:
            return
        self.held.add(key)
        self.holds += 1
        self.held_ever.add(key)
        self.reg.record_change(t, key, old, "HELD", cause)

    def _ensure_hold_case(self, key: tuple, wd: str, t: int, tid) -> None:
        """C2: a held committed identity has a pending FEED_FORK_HOLD case for its committed wire."""
        c = self.qcases.get(wd)
        if c is None or c["state"] in (RELEASED, REJECTED):
            if c is not None:
                self.hold_case_replacements += 1
            c = self.qcases[wd] = {"state": QUARANTINED, "reason": "FEED_FORK_HOLD", "t_q": t, "tid": tid,
                                   "eid": list(key)}
        elif c["state"] == QUARANTINED and c["reason"] != "FEED_FORK_HOLD":
            c["reason"], c["t_q"], c["eid"] = "FEED_FORK_HOLD", t, list(key)
            self.hold_case_conversions += 1
        else:
            return
        if self._in_review:
            c["opened_in_review_t"] = t
        # REVIEW_PENDING: this wire's case is being decided right now (its release re-runs admission); the
        # outcome is handled in _release.  A pending FEED_FORK_HOLD case needs nothing.

    # ------------------------------------------------------------------ delivery history (feed-level)
    def _history(self, ev, wire, obs, rel, cb_obs, wid, kid, wkid, t, params, ann, waive=frozenset()):
        # Same steps as B5FeedLevel._history (src/pbti/b5.py) except where marked C1-C3.
        did, ep, seq = obs["did"], obs["ep"], obs["seq"]
        cd = b64u(sha256(cb_obs))
        ev["cd"] = cd
        key = (did, ep, seq)
        reg = self.reg
        slot = reg.slots.get(key)
        if slot is not None and cd in slot.versions:
            if slot.state() == COMMITTED and slot.wid_first == wid and t - slot.t_first <= params["retry_window_ms"]:
                return self._finish(ev, wire, DUPLICATE, "RETRY", ann=ann)
            return self._finish(ev, wire, DUPLICATE, "SUSPECTED_REPLAY", ann=ann)
        stream = reg.stream(did)
        es = stream.epochs.get(ep)
        if es is not None and es.in_closed(seq) and (slot is None or not slot.versions) and "STALE_SLOT" not in waive:
            return self._q(ev, wire, "STALE_SLOT")
        if (ep < stream.max_ep and t - stream.epochs[stream.max_ep].t_open > params["epoch_drain_ms"]
                and "STALE_EPOCH" not in waive):
            return self._q(ev, wire, "STALE_EPOCH")
        hw = es.hw if es is not None else -1
        if seq > hw + params["max_seq_jump"]:
            return self._q(ev, wire, "SEQ_JUMP")
        # C1: fork evidence this receipt adds, evaluated against the evidence admitted before it
        prev = obs["prev"]
        points = []
        if slot is not None:
            if any(d != cd for d in slot.versions):                         # E1
                points.append(seq)
            if slot.implied and any(d != cd for d in slot.implied):         # E2
                points.append(seq)
        if seq > 0 and prev is not None:
            ps0 = reg.slots.get((did, ep, seq - 1))
            if ps0 is not None and ps0.versions and prev not in ps0.versions:   # E3
                points.append(seq - 1)
        slot = reg.slot(key, create=True)
        before = slot.state()
        slot.versions[cd] = ev["w"]
        if len(slot.versions) == 1:
            slot.t_first, slot.wid_first, slot.kid, slot.wkid = t, wid, kid, wkid
            slot.ts, slot.aid, slot.obs_first = obs["ts"], obs["aid"], obs
            reg.by_kid.setdefault(kid, []).append(key)
        if seq > 0 and prev is not None:
            ps = reg.slot((did, ep, seq - 1), create=True)
            if ps.implied is None:
                ps.implied = set()
            ps.implied.add(prev)
        if before == "ABSENT":
            if es is None:
                es = stream.epochs[ep] = EpochState(t)
            if ep > stream.max_ep:
                stream.max_ep = ep
            order = es.note_seq(seq, t)
        else:
            order = "-"
        feed = (did, ep)
        self.feed_seqs.setdefault(feed, set()).add(seq)
        if points:
            self._fork(feed, min(points), t)
        fk = self.fork.get(feed)
        if slot.state() != COMMITTED:
            why = "EQUIVOCATION" if before != "ABSENT" or len(slot.versions) > 1 else "LINK_MISMATCH"
            return self._finish(ev, wire, CONFLICT, why, ann=ann)
        if fk is not None and seq >= fk["seq"]:
            self._mark_held(key, t, before, "FEED_FORK_ARRIVAL")             # C3: counted once
            rec = self._finish(ev, wire, QUARANTINE, "FEED_FORK_HOLD", ann=ann)
            self._ensure_hold_case(key, ev["w"], t, ev.get("tid"))          # C2
            return rec
        ann = ann + [order, "RECOVERED" if rel["mode"] == "buffered" else "LIVE"]
        rec = self._finish(ev, wire, ACCEPT, "COMMITTED", ann=ann, ns="raw")
        self.proc.add(key, obs["aid"], obs["ts"], obs["pl"], ev["w"],
                      content_key(did, obs["aid"], obs["ts"], obs["sch"], obs["pl"]), (ep, seq))
        return rec

    def _fork(self, feed: tuple, f: int, t: int) -> None:
        """Called only for a receipt that adds new fork evidence (C1).  Holds every observation of the feed from the
        evidence point f onwards, including observations released earlier (historical V3 rule)."""
        self.fork_evidence_receipts += 1
        self.forked_feeds_ever.add(feed)
        fk = self.fork.get(feed)
        if fk is None or f < fk["seq"]:
            self.fork_events += 1
            self.fork[feed] = {"seq": f, "t": t if fk is None else fk["t"]}
        did, ep = feed
        for sq in sorted(self.feed_seqs.get(feed, ())):
            if sq < f:
                continue
            k = (did, ep, sq)
            s = self.reg.slots.get(k)
            if s is None or k in self.held or not s.versions:
                continue
            self._mark_held(k, t, s.state(), "FEED_FORK")
            self.proc.remove(k, "CONTEST_CORRECTION")
            if s.state() == COMMITTED:
                wd = next(iter(s.versions.values()))
                blob = self.store.get_blob("raw", wd) or self.store.get_blob("q", wd)
                if blob is not None and self.store.get_blob("q", wd) is None:
                    self.store.put_blob("q", wd, blob)
                self.quarantined_wires.add(wd)
                self._ensure_hold_case(k, wd, t, s.wid_first)               # C2 (b)

    # ------------------------------------------------------------------ recovery through review
    def _release(self, wd: str, case: dict, t: int) -> str:
        if case["reason"] == "FEED_FORK_HOLD":
            did, ep, sq = case["eid"]
            k = (did, ep, sq)
            s = self.reg.slots.get(k)
            if s is None or s.state() != COMMITTED:
                case["state"] = REJECTED
                return "RELEASE_FAILED:CONFLICT"
            if s.tainted:                                                    # C4
                case["state"] = REJECTED
                return "RELEASE_FAILED:TAINTED"
            out = super()._release(wd, case, t)                              # historical release of a hold
            if out == "RELEASED_HOLD":
                self.recovered_ids.add(k)
            return out
        out = PBTIVerifier._release(self, wd, case, t)                       # re-run admission, reason waived
        if out == "RELEASED":
            self.recovered_ids.add(tuple(case["eid"]))
        elif out == "RELEASE_FAILED:QUARANTINE/FEED_FORK_HOLD":
            # C2 (a): the re-run admitted the observation into a held feed: it is a held identity now, and this
            # case (the only one its wire digest can have) continues as its FEED_FORK_HOLD case from now on.
            case["state"], case["reason"], case["t_q"] = QUARANTINED, "FEED_FORK_HOLD", t
            case["opened_in_review_t"] = t
            self.deferred_releases += 1
            return "DEFERRED_TO_FEED_HOLD"
        return out

    # ------------------------------------------------------------------ result fields
    def v9_counters(self) -> dict:
        return {"b5_impl": IMPL_ID,
                "held_distinct_ever": len(self.held_ever),
                "recovered_distinct": len(self.recovered_ids),
                "fork_evidence_receipts": self.fork_evidence_receipts,
                "forked_feeds_distinct": len(self.forked_feeds_ever),
                "deferred_releases": self.deferred_releases,
                "hold_case_conversions": self.hold_case_conversions,
                "hold_case_replacements": self.hold_case_replacements,
                "held_without_case_end": len(self.held_without_case())}

    def held_without_case(self) -> list:
        """Held committed, untainted identities whose committed wire has no FEED_FORK_HOLD case (pending or decided).
        Must be empty for the corrected B5 with recovery (invariant checked by the tests and recorded per run)."""
        out = []
        for k in self.held:
            s = self.reg.slots.get(k)
            if s is None or not s.versions or s.state() != COMMITTED or s.tainted:
                continue
            wd = next(iter(s.versions.values()))
            c = self.qcases.get(wd)
            if c is None or c.get("reason") != "FEED_FORK_HOLD":
                out.append(k)
        return sorted(out, key=lambda x: (str(x[0]), str(x[1]), x[2]))


def make_b5_corrected(trust, policy, vkeys, cfg=None, recovery: bool = True, review_mode: str = "periodic"):
    return B5Corrected(trust, policy, vkeys, cfg=cfg, recovery=recovery, review_mode=review_mode)
