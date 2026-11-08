"""B5 and B5-strict (added in V3): literature-informed strong baselines with FEED-LEVEL conflict handling.

What each part comes from (and what is glue written for this testbed):
  * origin-signed observation statement, (did, ep, seq, prev) chain ............ PBTI statement format; hash-linked
    single-writer feeds as in Secure Scuttlebutt (Tarr et al. 2019) and Global Data Plane DataCapsules (Mor et al.)
  * relay countersignature binding the exact signed origin statement (odig)  .... RFC 9338 countersignature style
    (as in PBTI's relay statement); the countersignature does not itself carry a policy version - the admission
    record does, as in SCITT registration (RFC 9943)
  * versioned path-bound admission, credential lifecycle, revocation ........... shared with PBTI (inherited)
  * idempotency on (did, ep, seq) instead of timestamps ....................... CloudEvents-style de-duplication on
                                                                                  a Kafka-like (producer, epoch, sequence)
                                                                                  key; unlike Kafka's broker (KIP-98),
                                                                                  gaps and reordering are accepted
  * append-only decision/evidence log with signed Merkle checkpoints .......... SCITT-style registration evidence
                                                                                  (shared with PBTI)
  * fork evidence: two signed contents for one identity, or a successor whose
    prev contradicts a known predecessor .......................................... PeerReview authenticators /
                                                                                  SSB backlinks / GDP branches
  * FEED-LEVEL response: from the fork point onwards every observation of the feed (did, ep) is held
    (not authoritative) ......................................................... Secure Scuttlebutt ("messages from
                                                                                  the point of the fork onwards are
                                                                                  ignored")
  * taint of commits since t_comp when a key is revoked ....................... shared with PBTI; the revocation
                                                                                  trigger is PBTI's own (Taser, Retro and
                                                                                  Warp start repair from detector,
                                                                                  administrator or patch inputs)
  * recovery (B5 only): held observations become review cases (reason FEED_FORK_HOLD); after the review delay
    an authorized reviewer releases those whose slot has a single digest and at least one corroborating hash
    link (src/pbti/review.py); a reviewed feed resumes ............................ GLUE (operator practice)
B5-strict has no recovery: a forked feed stays frozen from the fork point (a new epoch starts a new feed).

The per-slot evidence (versions, successor-implied digests) is the same information PBTI uses; the difference
under test is the response to it: feed-level hold plus review (B5) or permanent freeze (B5-strict) versus
PBTI's per-identity contest (Rule L) without review.
"""
from __future__ import annotations

from .canonical import canonical_bytes
from .crypto import b64u, sha256
from .envelope import content_key
from .registry import COMMITTED, EpochState
from .review import QUARANTINED, REJECTED, RELEASED
from .verifier import ACCEPT, CONFLICT, DUPLICATE, QUARANTINE, PBTIVerifier


class B5FeedLevel(PBTIVerifier):
    name = "B5"

    def __init__(self, *args, recovery: bool = True, **kw):
        super().__init__(*args, **kw)
        self.recovery = recovery
        self.init_kw = {"recovery": recovery}
        self.fork: dict[tuple, dict] = {}      # (did, ep) -> {"seq": fork point, "t": first detection}
        self.held: set = set()                  # slot keys currently held (not authoritative)
        self.feed_seqs: dict[tuple, set] = {}
        self.fork_events = 0
        self.holds = 0
        self.resumed_feeds = 0
        if not recovery:
            self.name = "B5S"

    # ------------------------------------------------------------------ authority
    def is_authoritative(self, key, s) -> bool:
        return s.state() == COMMITTED and not s.tainted and key not in self.held

    # ------------------------------------------------------------------ delivery history (feed-level)
    def _history(self, ev, wire, obs, rel, cb_obs, wid, kid, wkid, t, params, ann, waive=frozenset()):
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
        slot = reg.slot(key, create=True)
        before = slot.state()
        slot.versions[cd] = ev["w"]
        if len(slot.versions) == 1:
            slot.t_first, slot.wid_first, slot.kid, slot.wkid = t, wid, kid, wkid
            slot.ts, slot.aid, slot.obs_first = obs["ts"], obs["aid"], obs
            reg.by_kid.setdefault(kid, []).append(key)
        if seq > 0 and obs["prev"] is not None:
            ps = reg.slot((did, ep, seq - 1), create=True)
            if ps.implied is None:
                ps.implied = set()
            ps.implied.add(obs["prev"])
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
        # fork evidence for this feed
        forks = []
        if len(slot.digests()) > 1:
            forks.append(seq)
        ps = reg.slots.get((did, ep, seq - 1))
        if ps is not None and ps.versions and len(ps.digests()) > 1:
            forks.append(seq - 1)
        if forks:
            self._fork(feed, min(forks), t)
        fk = self.fork.get(feed)
        if slot.state() != COMMITTED:
            why = "EQUIVOCATION" if before != "ABSENT" or len(slot.versions) > 1 else "LINK_MISMATCH"
            return self._finish(ev, wire, CONFLICT, why, ann=ann)
        if fk is not None and seq >= fk["seq"]:
            self.held.add(key)
            self.holds += 1
            return self._finish(ev, wire, QUARANTINE, "FEED_FORK_HOLD", ann=ann)
        ann = ann + [order, "RECOVERED" if rel["mode"] == "buffered" else "LIVE"]
        rec = self._finish(ev, wire, ACCEPT, "COMMITTED", ann=ann, ns="raw")
        self.proc.add(key, obs["aid"], obs["ts"], obs["pl"], ev["w"],
                      content_key(did, obs["aid"], obs["ts"], obs["sch"], obs["pl"]), (ep, seq))
        return rec

    def _fork(self, feed: tuple, f: int, t: int) -> None:
        """Hold every observation of the feed from the fork point f onwards (V3 fix: also when the feed is already
        forked at an earlier point, so that a slot released by review and contested later leaves derived data)."""
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
            self.held.add(k)
            self.holds += 1
            self.reg.record_change(t, k, s.state(), "HELD", "FEED_FORK")
            self.proc.remove(k, "CONTEST_CORRECTION")
            if s.state() == COMMITTED:
                wd = next(iter(s.versions.values()))
                blob = self.store.get_blob("raw", wd) or self.store.get_blob("q", wd)
                if blob is not None and self.store.get_blob("q", wd) is None:
                    self.store.put_blob("q", wd, blob)
                self.quarantined_wires.add(wd)
                c = self.qcases.get(wd)
                if c is None or c["state"] in (RELEASED,):
                    self.qcases[wd] = {"state": QUARANTINED, "reason": "FEED_FORK_HOLD", "t_q": t,
                                       "tid": s.wid_first, "eid": [did, ep, sq]}

    # ------------------------------------------------------------------ recovery through review
    def _release(self, wd: str, case: dict, t: int) -> str:
        if case["reason"] != "FEED_FORK_HOLD":
            return super()._release(wd, case, t)
        did, ep, sq = case["eid"]
        k = (did, ep, sq)
        s = self.reg.slots.get(k)
        if s is None or s.state() != COMMITTED or s.tainted:
            case["state"] = REJECTED
            return "RELEASE_FAILED:CONFLICT"
        self.held.discard(k)
        if self.store.get_blob("raw", wd) is None:          # arrived during the hold: commit its raw object now
            blob = self.store.get_blob("q", wd)
            if blob is not None:
                self.store.put_blob("raw", wd, blob)
        o = s.obs_first
        self.proc.add(k, o["aid"], o["ts"], o["pl"], wd, content_key(did, o["aid"], o["ts"], o["sch"], o["pl"]), (ep, sq))
        case["state"] = RELEASED
        case["affected"] = [o["aid"], o["ts"] - o["ts"] % self.cfg.window_ms]
        self.recovery_latencies.append((t - o["ts"], t - case["t_q"]))
        self._maybe_resume((did, ep), t)
        return "RELEASED_HOLD"

    def _apply_review(self, d: dict, t: int) -> dict:
        out = super()._apply_review(d, t)
        case = self.qcases.get(d.get("case"))
        if case is not None and case.get("reason") == "FEED_FORK_HOLD" and case["state"] == REJECTED:
            self._maybe_resume(tuple(case["eid"][:2]), t)
        return out

    def _maybe_resume(self, feed: tuple, t: int) -> None:
        """A reviewed feed resumes when none of its held observations is still awaiting review."""
        if feed not in self.fork:
            return
        did, ep = feed
        for wd, c in self.qcases.items():
            if c["reason"] == "FEED_FORK_HOLD" and c["state"] not in (RELEASED, REJECTED) and c.get("eid") \
                    and (c["eid"][0], c["eid"][1]) == feed:
                return
        del self.fork[feed]
        self.resumed_feeds += 1
        # held slots that were rejected by review stay excluded (they remain in self.held)

    def slot_summary(self) -> dict:
        c = super().slot_summary()
        c["HELD"] = len(self.held)
        return c


def make_b5(trust, policy, vkeys, cfg=None, recovery: bool = True):
    return B5FeedLevel(trust, policy, vkeys, cfg=cfg, recovery=recovery)
