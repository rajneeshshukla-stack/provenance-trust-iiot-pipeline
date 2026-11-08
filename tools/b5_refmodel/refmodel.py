"""Implementation-independent reference model of the B5 feed-level baseline.

Written from the specification only (phase 1): docs/BASELINES.md (B5, PBTI-R, V4 additions),
docs/STATE_MACHINE.md, docs/PROTOCOL_SPECIFICATION.md (prev links, Rule L, review release),
research/V3/PREREGISTRATION.md (B5 / B5-strict), research/V4/PREREGISTRATION_V4.md (review rules,
event-driven review), paper/main.tex (B5 paragraph, "Quarantine review and release"), plus the spec-level
notes research/V3/PREREGISTRATION_AMENDMENTS.md (A4), research/V4/DECISION_LOG.md (D03) and the caption of
the B5 table in paper/supplementary.tex ("an observation held again after a later fork is counted again").
src/pbti/b5.py, review.py and sim.py were NOT read when this model was written.

Scope. The model works on an abstract stream of statements that have already passed the shared
cryptographic / policy admission (signatures, relay binding, path-bound policy, credential status,
freshness).  Each statement is (arrival_time_ms, did, ep, seq, digest, prev_digest[, qreason]).
`qreason` is set when the shared admission quarantined the receipt for a *releasable* reason
(STALE_TS, STALE_SLOT, STALE_EPOCH, REVOKED_BUFFERED); such a receipt opens a review case and does not
enter the slot evidence until released.  Revocation/taint, gap closure, epoch drain, horizons and
non-releasable quarantine reasons are outside the model (they are shared with PBTI).

Behaviour (B5 = PBTI with Rule L replaced by a feed-level response, plus the automated reviewer):

* Slot evidence per identity e=(did,ep,seq): `versions` (admitted digests) and `implied` (digests named
  by the `prev` of admitted successors).  Held and rejected statements remain admitted evidence.
* Exact duplicate (digest already admitted for e): no state change, no case.
* Fork evidence on admitting digest cd with link p at e (one fork event per admission, fork point =
  minimum of the triggered points):
    F1  another digest already admitted for e                      -> fork point seq(e)
    F2  an admitted successor names another digest for e           -> fork point seq(e)
    F3  seq>0, the predecessor slot has admitted versions and p is
        none of them (successor contradicts known predecessor)     -> fork point seq(e)-1
* Fork event at point f in feed (did,ep): the feed is held (fork point = min(old, f)); every admitted,
  not-rejected observation of the feed with seq >= f becomes HELD (not authoritative), each opening a
  FEED_FORK_HOLD review case -- this includes observations that were released earlier (re-hold, counted
  again).  While the feed is held, every newly admitted observation with seq >= fork point is HELD.
* Authority: an admitted observation is authoritative iff its status is ACCEPTED (never held) or
  RELEASED.  (By construction an authoritative observation's slot has a single, uncontradicted digest.)
* Reviewer (B5 only; B5S has none): a case is
    corroborated  iff versions(e) <= {cd} and implied(e) <= {cd} and
                      (cd in implied(e)  or  (seq>0 and (e-1, prev) is authoritative))
    contradicted  iff some digest != cd is in versions(e) | implied(e), or
                      (seq>0 and K != {} and prev not in K), K = versions(e-1) | implied(e-1)
                      ("predecessor evidence" in Rule L's sense; for an admitted case its own prev is in
                      implied(e-1), so the second clause only matters for quarantine cases)
  Rule oneshot: RELEASE if corroborated else REJECT.  Rule defer: RELEASE if corroborated, REJECT if
  contradicted, else keep pending.
  RELEASE of a hold case makes the observation authoritative at once.  RELEASE of a quarantine case
  re-runs the B5 history step with the reason waived (duplicate / accepted / held / fork).
  REJECT is final.
* Periodic review: ticks at t = offset + k*C (k >= 1) up to t_end; at a tick, the pending cases with
  age t - t_open >= R (list taken at the start of the tick) are examined once each, oldest case first
  (creation order), every decision applied immediately so that later cases in the same tick see it.
  At equal times a tick runs before an arrival (Algorithm 1 "advance ticks to t" before admission).
* Event-driven review (mode="event", R=0, no ticks): after every non-duplicate admission, the pending
  cases at e-1, e, e+1 and every case opened by that admission are examined; each decided case adds its
  own neighbourhood (e'-1, e', e'+1) and the cases its decision opened to the next round; repeat until a
  round decides nothing.
* Resume: after every review tick / event cascade, a held feed without pending FEED_FORK_HOLD cases
  resumes (fork point cleared; later arrivals admitted normally; a later fork holds it again).
  B5S (recovery=False): no reviewer, no resume, quarantine cases stay pending.

The list AMBIGUITIES below records every interpretation choice.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field, replace
from typing import Iterable, Optional

ACCEPTED, HELD, RELEASED, REJECTED = "ACCEPTED", "HELD", "RELEASED", "REJECTED"
AUTH_STATES = (ACCEPTED, RELEASED)
HOLD = "FEED_FORK_HOLD"
RELEASABLE = ("STALE_TS", "STALE_SLOT", "STALE_EPOCH", "REVOKED_BUFFERED")

AMBIGUITIES = [
    ("A1", "Fork point of a link contradiction between e-1 and e",
     "seq(e)-1: the predecessor identity is the one with two candidate digests (admitted vs. implied); "
     "using seq(e) would leave a gap-fill forgery at e-1 authoritative"),
    ("A2", "Link contradiction when the successor arrives first",
     "symmetric: admitting a predecessor whose digest differs from a successor-implied digest is fork "
     "evidence (F2), fork point = predecessor"),
    ("A3", "Successor whose prev names one of several admitted predecessor versions",
     "not new fork evidence (F3 only if prev is none of the admitted predecessor versions)"),
    ("A4", "Further contradicting evidence on an already contradicted slot (third version, new "
           "contradicting link)", "every admission that triggers F1/F2/F3 is a new fork event (re-holds "
           "after a resume); a fork event inside an already held feed only lowers the fork point"),
    ("A5", "Which observations a (later) fork event holds",
     "every admitted, not-rejected observation with seq >= f, including previously released ones "
     "(supplementary caption: 'an observation held again after a later fork is counted again')"),
    ("A6", "Hold counter", "one hold event per observation each time it becomes held (on arrival in a "
           "held feed, retroactively at a fork, or re-held); feed-level hold transitions reported "
           "separately"),
    ("A7", "Resume condition and timing",
     "a held feed resumes when it has no pending FEED_FORK_HOLD case, checked after each review tick "
     "or event cascade; other quarantine cases do not block resume. Consequence: with R larger than "
     "the inter-arrival time a producing feed cannot resume until arrivals stop"),
    ("A8", "State after resume", "fork point cleared; arrivals admitted normally, even with seq >= "
           "old fork point; decided cases stay decided"),
    ("A9", "Review tick semantics",
     "eligible cases (age >= R, age from case opening) listed at the start of the tick, examined once, "
     "oldest first (case creation order), decisions applied immediately (visible within the tick); "
     "no fixpoint iteration inside a tick; cases opened during the tick wait for the next tick"),
    ("A10", "Tick schedule and ties", "ticks at k*C (k>=1, phase 0) up to t_end; tick before an "
            "arrival with the same time stamp"),
    ("A11", "Corroboration at seq 0 (prev = null)", "only a successor link can corroborate"),
    ("A12", "Which successors count as 'admitted'", "held and rejected successors count (stored "
            "evidence); a quarantined, unreleased successor does not"),
    ("A13", "Predecessor link corroboration", "the predecessor (e-1, prev) must be authoritative at "
            "decision time (held or rejected predecessor does not corroborate)"),
    ("A14", "'contradicted' (defer rule)", "frozen V4 prereg text: another digest in versions|implied of "
            "the slot, or prev absent from the predecessor's evidence (versions|implied, Rule L's term) "
            "when that evidence is non-empty; D03 gives only the first clause. For admitted (held) "
            "cases both texts then agree; reading 'evidence' as admitted versions only would reject "
            "the genuine successor of a gap-fill forgery at its first event-driven review"),
    ("A15", "Event-driven review scope", "rule defer, R=0, no periodic tick; reviewed: pending cases at "
            "e-1,e,e+1 of a non-duplicate admission plus all cases it opened; cascade over neighbours "
            "of decided cases until a round decides nothing"),
    ("A16", "'Single digest' for a quarantined (not admitted) case", "versions(e) <= {cd} (the case "
            "digest or nothing); its release re-runs the B5 history step and can end held, as a "
            "duplicate or in a fork"),
    ("A17", "B5S and non-hold quarantine cases", "B5S has no reviewer at all; STALE_TS etc. stay "
            "quarantined"),
    ("A18", "Rejected hold case", "final; the observation stays stored and non-authoritative and is "
            "not re-held by later forks"),
    ("A19", "Released observation and later contradiction", "it loses authority when a later fork "
            "event's point is <= its seq (A5), including a conflict on its own slot (amendment A4)"),
    ("A20", "Withheld-time window", "from first arrival (reachability at the verifier) to t_end; "
            "the paper measures from production"),
    ("A21", "Releasable quarantine reason inside a held feed", "the quarantine check precedes the "
            "history step, so the receipt is a quarantine case first and is held only when released"),
    ("A22", "Duplicates of held/rejected observations", "exact duplicates never change state and "
            "never open cases"),
    ("A23", "Release while the feed is still held", "a released observation is authoritative at once "
            "(it does not wait for the feed to resume)"),
    ("A24", "Rule for event-driven review", "defer (D03; event-driven one-shot would reject every "
            "case before its successor arrives); the model also accepts rule='oneshot' with "
            "mode='event'"),
]


# ----------------------------------------------------------------------------------------------------------
# Phase-2 switches.  They were added AFTER phase 1 (after reading src/pbti/b5.py, review.py, sim.py) only to
# attribute observed differences to individual interpretation choices.  Their defaults reproduce the
# phase-1 model exactly (phase1_snapshot/refmodel.py); setting them to the "impl" values re-states the
# choices the implementation makes at the points where the specification is silent or ambiguous:
#   order            "fifo" (phase 1: case creation order)  | "identity" (did, str(ep), seq, wire)
#   fork_rule        "evidence" (phase 1: F1-F3, new contradicting evidence only)
#                    | "state" (fork whenever the admitted slot or its predecessor slot is contested afterwards)
#   contested_cases  True (phase 1: every held version opens a case) | False (only single-digest slots do)
#   resume_timing    "pass" (phase 1: after each tick/cascade) | "decision" (after each hold-case decision)
#   wire_cases       False (phase 1: one case per receipt / per hold) | True (one case per wire digest, with the
#                    implementation's collision rules)
#   event_scope      "spec" (phase 1) | "impl" (sim.World._event_review candidate rules)
# ----------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Stmt:
    t: int                      # arrival time at the verifier, ms
    did: str
    ep: int
    seq: int
    digest: str
    prev: Optional[str]         # None iff seq == 0
    qreason: Optional[str] = None   # releasable quarantine reason from the shared admission, or None
    wire: Optional[str] = None  # wire identity (only used with wire_cases / identity order); default = digest


@dataclass
class Params:
    rule: str = "oneshot"       # "oneshot" | "defer"
    R_ms: int = 60_000          # minimum case age (periodic mode)
    C_ms: int = 10_000          # review cadence (periodic mode)
    mode: str = "periodic"      # "periodic" | "event"
    recovery: bool = True       # False -> B5S
    tick_offset_ms: int = 0
    tick_first: bool = True     # at equal time stamps the review tick precedes the arrival
    # phase-2 attribution switches (defaults = phase-1 model)
    order: str = "fifo"
    fork_rule: str = "evidence"
    contested_cases: bool = True
    resume_timing: str = "pass"
    wire_cases: bool = False
    event_scope: str = "spec"

    @staticmethod
    def hist():
        return Params("oneshot", 60_000, 10_000, "periodic", True)

    @staticmethod
    def defer(R_s, C_s):
        return Params("defer", int(R_s * 1000), int(C_s * 1000), "periodic", True)

    @staticmethod
    def event():
        return Params("defer", 0, 0, "event", True)

    @staticmethod
    def strict():
        return Params("oneshot", 60_000, 10_000, "periodic", False)

    def impl_choices(self, **only):
        """Copy with the implementation's choices at the ambiguous points (all, or only the named ones)."""
        impl = dict(order="identity", fork_rule="state", contested_cases=False, resume_timing="decision",
                    wire_cases=True, event_scope="impl")
        if only:
            impl = {k: v for k, v in only.items()}
        return replace(self, **impl)


@dataclass
class Slot:
    versions: dict = field(default_factory=dict)    # digest -> admission time (insertion ordered)
    implied: set = field(default_factory=set)

    def digests(self):
        return set(self.versions) | self.implied


@dataclass
class Case:
    cid: int
    kind: str                   # FEED_FORK_HOLD or a releasable quarantine reason
    e: tuple
    cd: str
    prev: Optional[str]
    t_open: int
    wire: Optional[str] = None
    state: str = "PENDING"      # PENDING | RELEASED | REJECTED
    t_decided: Optional[int] = None


@dataclass
class Feed:
    held: bool = False
    fork_point: Optional[int] = None


def pred(e):
    return (e[0], e[1], e[2] - 1)


def succ(e):
    return (e[0], e[1], e[2] + 1)


class B5Model:
    def __init__(self, params: Params):
        self.p = params
        self.slots: dict[tuple, Slot] = {}
        self.status: dict[tuple, str] = {}           # (e, cd) -> ACCEPTED/HELD/RELEASED/REJECTED
        self.prev_of: dict[tuple, Optional[str]] = {}
        self.wire_of: dict[tuple, Optional[str]] = {}
        self.feeds: dict[tuple, Feed] = defaultdict(Feed)
        self.feed_slots: dict[tuple, set] = defaultdict(set)   # (did, ep) -> set of seq with versions
        self.cases: list[Case] = []
        self.pending_by_id: dict[tuple, list] = defaultdict(list)  # e -> [Case] (pending only)
        self.case_by_wire: dict = {}                # wire -> latest case (wire_cases)
        # outputs
        self.timeline: list = []        # (t, e, cd, authoritative, cause)
        self.fork_events: list = []     # (t, (did, ep), fork_point, triggers)
        self.fork_new_point: list = []  # per fork event: fork point created or lowered (implementation counter)
        self.hold_events: list = []     # (t, e, cd)
        self.feed_holds: list = []      # (t, (did, ep), fork_point)   feed not-held -> held
        self.releases: list = []        # (t, e, cd, kind)   reviewer decided RELEASE
        self.release_failed: list = []  # (t, e, cd, kind)   wire_cases: re-run did not end in ACCEPT
        self.rejections: list = []      # (t, e, cd, kind)
        self.resumes: list = []         # (t, (did, ep))
        self.dispositions: list = []    # per arrival: (t, e, cd, disposition)
        self.state_events: list = []    # identities newly held by a fork (implementation's record_change)
        self.c_holds_impl = 0           # implementation-style counters (meaningful with impl switches)
        self.c_forks_impl = 0

    # ------------------------------------------------------------------ helpers
    def _slot(self, e) -> Slot:
        s = self.slots.get(e)
        if s is None:
            s = self.slots[e] = Slot()
        return s

    def is_auth(self, e, cd) -> bool:
        return self.status.get((e, cd)) in AUTH_STATES

    def _set_status(self, e, cd, new, t, cause):
        old = self.status.get((e, cd))
        self.status[(e, cd)] = new
        was, now = old in AUTH_STATES, new in AUTH_STATES
        if was != now:
            self.timeline.append((t, e, cd, now, cause))

    def _open_case(self, kind, e, cd, prev, t, wire=None) -> Case:
        c = Case(len(self.cases), kind, e, cd, prev, t, wire)
        self.cases.append(c)
        self.pending_by_id[e].append(c)
        if wire is not None:
            self.case_by_wire[wire] = c
        return c

    def _close_case(self, c: Case, state, t):
        c.state, c.t_decided = state, t
        self.pending_by_id[c.e].remove(c)

    def _single(self, e) -> bool:
        return len(self._slot(e).digests()) == 1

    def _hold(self, e, cd, t, path):
        """Hold (e, cd); path = "fork" (retroactive / by a fork) or "arrival" (admitted into a held feed)."""
        self._set_status(e, cd, HELD, t, "HOLD")
        self.hold_events.append((t, e, cd))
        if not self.p.contested_cases and not self._single(e):
            return                                   # implementation: no case for a contested slot
        wire = self.wire_of.get((e, cd))
        if self.p.wire_cases:
            c = self.case_by_wire.get(wire)
            if path == "fork" and not (c is None or c.state == "RELEASED"):
                return                               # b5._fork: existing non-released case for this wire
            if path == "arrival" and c is not None:
                return                               # verifier._finish: one case per wire digest
        self._open_case(HOLD, e, cd, self.prev_of[(e, cd)], t, wire)

    # ------------------------------------------------------------------ admission
    def arrive(self, s: Stmt):
        e = (s.did, s.ep, s.seq)
        wire = s.wire if s.wire is not None else s.digest
        if s.qreason is not None:
            if self.p.wire_cases and wire in self.case_by_wire:
                disp = "QUARANTINE_NO_CASE:" + s.qreason
            else:
                self._open_case(s.qreason, e, s.digest, s.prev, s.t, wire)
                disp = "QUARANTINE:" + s.qreason
        else:
            disp = self._history(e, s.digest, s.prev, s.t, wire)
        self.dispositions.append((s.t, e, s.digest, disp))
        return disp

    def _history(self, e, cd, prev, t, wire=None) -> str:
        slot = self._slot(e)
        if cd in slot.versions:
            return "DUPLICATE"
        did, ep, seq = e
        points, triggers = [], []
        if self.p.fork_rule == "evidence":
            if any(d != cd for d in slot.versions):
                points.append(seq); triggers.append("F1")
            if any(d != cd for d in slot.implied):
                points.append(seq); triggers.append("F2")
        slot.versions[cd] = t
        self.prev_of[(e, cd)] = prev
        self.wire_of[(e, cd)] = wire if wire is not None else cd
        self.feed_slots[(did, ep)].add(seq)
        if seq > 0:
            ps = self._slot(pred(e))
            if self.p.fork_rule == "evidence" and ps.versions and prev not in ps.versions:
                points.append(seq - 1); triggers.append("F3")
            if prev is not None:
                ps.implied.add(prev)
        if self.p.fork_rule == "state":
            if len(slot.digests()) > 1:
                points.append(seq); triggers.append("S0")
            ps = self.slots.get(pred(e))
            if seq > 0 and ps is not None and ps.versions and len(ps.digests()) > 1:
                points.append(seq - 1); triggers.append("S1")
        feed = self.feeds[(did, ep)]
        self.status[(e, cd)] = None              # admitted, not yet classified
        if points:
            self._fork((did, ep), min(points), t, tuple(triggers))
        if self.status[(e, cd)] == HELD:         # held by the fork just detected
            if self.p.fork_rule == "state" and self._single(e) and feed.held and seq >= feed.fork_point:
                self.c_holds_impl += 1           # b5._history counts the hold a second time
            return "HELD_FORK"
        if feed.held and seq >= feed.fork_point:
            self.c_holds_impl += 1
            self._hold(e, cd, t, "arrival")
            return "HELD"
        self._set_status(e, cd, ACCEPTED, t, "ACCEPT")
        return "ACCEPT"

    def _fork(self, fk, f, t, triggers):
        feed = self.feeds[fk]
        new_point = (not feed.held) or f < feed.fork_point
        if new_point:
            self.c_forks_impl += 1
        self.fork_events.append((t, fk, f, triggers))
        self.fork_new_point.append(new_point)
        if not feed.held:
            feed.held, feed.fork_point = True, f
            self.feed_holds.append((t, fk, f))
        else:
            feed.fork_point = min(feed.fork_point, f)
        did, ep = fk
        for seq in sorted(q for q in self.feed_slots[fk] if q >= f):
            e = (did, ep, seq)
            vers = list(self.slots[e].versions)
            slot_was_held = any(self.status.get((e, cd)) in (HELD, REJECTED) for cd in vers)   # impl: key in held
            newly = False
            for cd in vers:
                if self.status.get((e, cd)) in (ACCEPTED, RELEASED, None):
                    self._hold(e, cd, t, "fork")
                    newly = True
            if newly and not slot_was_held:
                self.c_holds_impl += 1
                self.state_events.append(e)

    # ------------------------------------------------------------------ review
    def corroborated(self, c: Case) -> bool:
        s = self._slot(c.e)
        if any(d != c.cd for d in s.versions) or any(d != c.cd for d in s.implied):
            return False
        if c.cd in s.implied:
            return True
        return c.e[2] > 0 and self.is_auth(pred(c.e), c.prev)

    def contradicted(self, c: Case) -> bool:
        s = self._slot(c.e)
        if any(d != c.cd for d in s.versions) or any(d != c.cd for d in s.implied):
            return True
        if c.e[2] > 0:
            ps = self.slots.get(pred(c.e))
            known = (set(ps.versions) | ps.implied) if ps is not None else set()
            if known and c.prev not in known:
                return True
        return False

    def _decide(self, c: Case, t) -> str:
        if self.corroborated(c):
            self.releases.append((t, c.e, c.cd, c.kind))
            if c.kind == HOLD:
                self._close_case(c, "RELEASED", t)
                self._set_status(c.e, c.cd, RELEASED, t, "RELEASE")
            else:
                self._close_case(c, "REVIEWING", t)          # (case is under review while admission re-runs)
                r = self._history(c.e, c.cd, c.prev, t, c.wire)   # re-run with the quarantine reason waived
                c.state = "RELEASED"
                if self.p.wire_cases and r != "ACCEPT":
                    c.state = "REJECTED"                     # verifier._release: RELEASE_FAILED
                    self.release_failed.append((t, c.e, c.cd, c.kind, r))
                    return "RELEASE_FAILED"
            out = "RELEASE"
        elif self.p.rule == "oneshot" or self.contradicted(c):
            self._close_case(c, "REJECTED", t)
            self.rejections.append((t, c.e, c.cd, c.kind))
            if c.kind == HOLD:
                self._set_status(c.e, c.cd, REJECTED, t, "REJECT")
            out = "REJECT"
        else:
            return "DEFER"
        if self.p.resume_timing == "decision" and c.kind == HOLD:
            self._maybe_resume((c.e[0], c.e[1]), t)
        return out

    def _feed_pending(self, fk) -> bool:
        did, ep = fk
        return any(c.kind == HOLD for seq in self.feed_slots[fk]
                   for c in self.pending_by_id.get((did, ep, seq), ()))

    def _maybe_resume(self, fk, t):
        feed = self.feeds[fk]
        if feed.held and not self._feed_pending(fk):
            feed.held, feed.fork_point = False, None
            self.resumes.append((t, fk))

    def _check_resume(self, t):
        if self.p.resume_timing != "pass":
            return
        for fk in list(self.feeds):
            self._maybe_resume(fk, t)

    def _order(self, cases):
        if self.p.order == "identity":
            return sorted(cases, key=lambda c: ((str(c.e[0]), str(c.e[1])), c.e[2], str(c.wire or c.cd)))
        return cases

    def review_tick(self, t):
        eligible = [c for c in self.cases if c.state == "PENDING" and t - c.t_open >= self.p.R_ms]
        for c in self._order(eligible):
            if c.state == "PENDING":
                self._decide(c, t)
        self._check_resume(t)

    def event_review(self, e, first_new_cid, t, first_state_event=0):
        if self.p.event_scope == "impl":
            return self._event_review_impl(e, first_new_cid, t, first_state_event)
        work = {pred(e), e, succ(e)} | {c.e for c in self.cases[first_new_cid:]}
        while work:
            nxt = set()
            for ident in sorted(work, key=lambda x: (x[0], x[1], x[2])):
                for c in list(self.pending_by_id.get(ident, ())):
                    if c.state != "PENDING":
                        continue
                    before = len(self.cases)
                    if self._decide(c, t) != "DEFER":
                        nxt |= {pred(c.e), c.e, succ(c.e)} | {x.e for x in self.cases[before:]}
            work = nxt
        self._check_resume(t)

    def _event_review_impl(self, e, ci, t, si):
        """Mirror of sim.World._event_review: candidates = receipt identity +-1, identities of newly opened cases,
        identities newly held by a fork +-1; a round reviews each candidate case once in identity order; releases
        add their neighbours; repeat while candidates or new cases/holds exist."""
        cand = {pred(e), e, succ(e)}
        while True:
            for c in self.cases[ci:]:
                cand.add(c.e)
            ci = len(self.cases)
            for x in self.state_events[si:]:
                cand |= {pred(x), x, succ(x)}
            si = len(self.state_events)
            todo = [c for x in cand for c in self.pending_by_id.get(x, ())]
            if not todo:
                break
            cand = set()
            for c in self._order(todo):
                if c.state == "PENDING" and self._decide(c, t) == "RELEASE":
                    cand |= {pred(c.e), succ(c.e)}
            if not cand and ci == len(self.cases) and si == len(self.state_events):
                break
        self._check_resume(t)

    # ------------------------------------------------------------------ results
    def authoritative_set(self):
        return {k for k, v in self.status.items() if v in AUTH_STATES}

    def pending_cases(self):
        return [c for c in self.cases if c.state == "PENDING"]


def _ticks(params: Params, t_end: int):
    ticks = []
    if params.recovery and params.mode == "periodic":
        if params.C_ms <= 0:
            raise ValueError("periodic review needs C_ms > 0")
        k = 1
        while params.tick_offset_ms + k * params.C_ms <= t_end:
            ticks.append(params.tick_offset_ms + k * params.C_ms)
            k += 1
    return ticks


def schedule(stmts, params: Params, t_end: int):
    """Merged event list [("A", stmt) | ("T", t)] in processing order (stable for equal arrival times)."""
    arrivals = [s for _, s in sorted(enumerate(stmts), key=lambda x: (x[1].t, x[0]))]
    events = [(s.t, 1 if params.tick_first else 0, i, "A", s) for i, s in enumerate(arrivals)]
    events += [(tt, 0 if params.tick_first else 1, i, "T", tt) for i, tt in enumerate(_ticks(params, t_end))]
    events.sort(key=lambda x: (x[0], x[1], x[2]))
    return [(k, x) for _, _, _, k, x in events]


def run(stmts: Iterable[Stmt], params: Params, t_end: Optional[int] = None, legit=None, events=None):
    """Run the model over the arrival list (stable order for equal times) and return a result dict.
    `events` (optional) gives an explicit processing order [("A", Stmt) | ("T", t)] instead of the schedule."""
    stmts = list(stmts)
    if t_end is None:
        last = max((s.t for s in stmts), default=0)
        t_end = last + params.R_ms + 2 * max(params.C_ms, 1)
    if events is None:
        events = schedule(stmts, params, t_end)
    m = B5Model(params)
    arrivals = []
    for kind, x in events:
        if kind == "T":
            if params.recovery and params.mode == "periodic":
                m.review_tick(x)
        else:
            arrivals.append(x)
            ci, si = len(m.cases), len(m.state_events)
            disp = m.arrive(x)
            if params.recovery and params.mode == "event" and (disp != "DUPLICATE" or params.event_scope == "impl"):
                m.event_review((x.did, x.ep, x.seq), ci, x.t, si)
    return summarize(m, arrivals, t_end, legit)


def authority_intervals(timeline, t_end):
    """(e, cd) -> list of [start, end) intervals of authority (zero-length intervals dropped, adjacent merged)."""
    out, open_ = defaultdict(list), {}
    for t, e, cd, now, _ in timeline:
        k = (e, cd)
        if now:
            open_.setdefault(k, t)
        elif k in open_:
            a = open_.pop(k)
            if t > a:
                if out[k] and out[k][-1][1] == a:
                    out[k][-1] = (out[k][-1][0], t)
                else:
                    out[k].append((a, t))
    for k, a in open_.items():
        if t_end > a:
            if out[k] and out[k][-1][1] == a:
                out[k][-1] = (out[k][-1][0], t_end)
            else:
                out[k].append((a, t_end))
    return {k: v for k, v in out.items() if v}


def withheld_ms(intervals, first_arrival, t_end):
    """Time in [first_arrival, t_end] during which the pair was not authoritative."""
    span = max(0, t_end - first_arrival)
    auth = sum(max(0, min(b, t_end) - max(a, first_arrival)) for a, b in intervals)
    return span - auth


def summarize(m: B5Model, arrivals, t_end, legit=None):
    first_arrival = {}
    for s in arrivals:
        first_arrival.setdefault(((s.did, s.ep, s.seq), s.digest), s.t)
    iv = authority_intervals(m.timeline, t_end)
    res = {
        "t_end": t_end,
        "authoritative": sorted(m.authoritative_set()),
        "timeline": m.timeline,
        "fork_events": m.fork_events,
        "hold_events": m.hold_events,
        "held_identities": sorted({e for _, e, _ in m.hold_events}),
        "feed_holds": m.feed_holds,
        "releases": m.releases,
        "release_failed": m.release_failed,
        "rejections": m.rejections,
        "resumes": m.resumes,
        "pending": [(c.kind, c.e, c.cd, c.t_open) for c in m.pending_cases()],
        "held_at_end": sorted(k for k, v in m.status.items() if v == HELD),
        "dispositions": m.dispositions,
        "intervals": dict(iv),
        "first_arrival": first_arrival,
        "impl_counters": {"holds": m.c_holds_impl, "fork_events": m.c_forks_impl, "resumed_feeds": len(m.resumes)},
    }
    if legit is not None:
        legit = set(legit)
        reach = [k for k in legit if k in first_arrival]
        w = {k: withheld_ms(iv.get(k, []), first_arrival[k], t_end) for k in reach}
        nl = [k for k in first_arrival if k not in legit]
        auth = m.authoritative_set()
        res["withheld_ms"] = w
        res["W_ms_total"] = sum(w.values())
        res["reachable"] = len(reach)
        res["nlx_ms_total"] = sum(sum(max(0, min(b, t_end) - a) for a, b in iv.get(k, [])) for k in nl)
        res["legit_missing"] = sorted(k for k in reach if k not in auth)
        res["nonlegit_auth"] = sorted(k for k in nl if k in auth)
    return res
