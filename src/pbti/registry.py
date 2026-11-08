"""Authoritative event registry for PBTI.

Event identity eid = (did, ep, seq) is chosen by the producer and covered by its signature.
For each eid the registry keeps a *slot*:
    versions : content digest -> blob ref     (validly signed + authorized statements for this eid)
    implied  : digests asserted for this eid by the `prev` link of the successor statement(s)
Slot state is a pure function of that evidence (Rule L, monotone in evidence):
    ABSENT     no version received (an implied digest may already be known)
    COMMITTED  exactly one distinct digest across versions and implied digests
    CONTESTED  two or more distinct digests  (equivocation / fork evidence)
    LOST       the gap containing eid was closed after the configured horizon
Because the state depends only on the *set* of admitted evidence, any delivery order of the same
evidence set yields the same final slot states (convergence invariant I9), and once CONTESTED a
slot can never return to COMMITTED (contest is absorbing).
TAINTED is an orthogonal flag on COMMITTED slots (retroactive credential-compromise containment).
"""
from __future__ import annotations

from typing import Optional

ABSENT, COMMITTED, CONTESTED, LOST = "ABSENT", "COMMITTED", "CONTESTED", "LOST"


class Slot:
    __slots__ = ("versions", "implied", "t_first", "wid_first", "kid", "wkid", "ts", "aid",
                 "tainted", "lost", "obs_first")

    def __init__(self):
        self.versions: dict[str, str] = {}
        self.implied: Optional[set] = None
        self.t_first = None
        self.wid_first = None
        self.kid = None
        self.wkid = None
        self.ts = None
        self.aid = None
        self.tainted = False
        self.lost = False
        self.obs_first = None

    def digests(self) -> set:
        s = set(self.versions)
        if self.implied:
            s |= self.implied
        return s

    def state(self) -> str:
        if self.lost and not self.versions:
            return LOST
        if not self.versions:
            return ABSENT
        return COMMITTED if len(self.digests()) == 1 else CONTESTED

    def first_cd(self) -> Optional[str]:
        return next(iter(self.versions)) if self.versions else None


class EpochState:
    __slots__ = ("hw", "t_open", "gaps", "closed")

    def __init__(self, t_open: int):
        self.hw = -1
        self.t_open = t_open
        self.gaps: list[list[int]] = []    # [lo, hi, t_opened], disjoint, sorted
        self.closed: list[tuple[int, int]] = []  # [lo, hi] declared LOST

    def note_seq(self, seq: int, t: int) -> str:
        """Update high-water mark / gap set for a newly admitted sequence number; return ordering annotation."""
        if seq == self.hw + 1:
            self.hw = seq
            return "IN_ORDER"
        if seq > self.hw + 1:
            self.gaps.append([self.hw + 1, seq - 1, t])
            self.hw = seq
            return "AHEAD"
        # seq <= hw: fills (part of) a gap
        for i, g in enumerate(self.gaps):
            lo, hi, t0 = g
            if lo <= seq <= hi:
                if lo == hi:
                    self.gaps.pop(i)
                elif seq == lo:
                    g[0] = lo + 1
                elif seq == hi:
                    g[1] = hi - 1
                else:
                    g[1] = seq - 1
                    self.gaps.insert(i + 1, [seq + 1, hi, t0])
                break
        return "LATE"

    def in_closed(self, seq: int) -> bool:
        return any(lo <= seq <= hi for lo, hi in self.closed)

    def close_old_gaps(self, now: int, horizon: int) -> int:
        n = 0
        keep = []
        for lo, hi, t0 in self.gaps:
            if now - t0 > horizon:
                self.closed.append((lo, hi))
                n += hi - lo + 1
            else:
                keep.append([lo, hi, t0])
        self.gaps = keep
        return n

    def open_gap_count(self) -> int:
        return sum(hi - lo + 1 for lo, hi, _ in self.gaps)


class Stream:
    __slots__ = ("epochs", "max_ep")

    def __init__(self):
        self.epochs: dict[int, EpochState] = {}
        self.max_ep = -1


class Registry:
    def __init__(self):
        self.slots: dict[tuple, Slot] = {}
        self.streams: dict[str, Stream] = {}
        self.by_kid: dict[str, list[tuple]] = {}
        self.state_events: list[tuple] = []  # append-only (t, eid, old, new, cause)

    def stream(self, did: str) -> Stream:
        s = self.streams.get(did)
        if s is None:
            s = self.streams[did] = Stream()
        return s

    def slot(self, key: tuple, create: bool = False) -> Optional[Slot]:
        s = self.slots.get(key)
        if s is None and create:
            s = self.slots[key] = Slot()
        return s

    def record_change(self, t: int, key: tuple, old: str, new: str, cause: str) -> None:
        self.state_events.append((t, key, old, new, cause))
