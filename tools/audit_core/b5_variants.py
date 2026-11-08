"""Audit-only B5 variants (never used to change the repository).

B5Instr  : the repository's B5 unchanged, plus counters:
           rehold_noev_calls   _fork calls made by a receipt that added no new fork evidence (no digest set of the
                               receipt's slot or of its predecessor slot changed while having >= 2 digests)
           rehold_released     slots re-held (case was RELEASED) by such calls
           rehold_released_ev  slots re-held (case was RELEASED) by calls that did bring new fork evidence
           stuck_reingest      non-FEED_FORK_HOLD releases whose re-run admission was turned into a feed hold
                               (case closed REJECTED, slot left in `held` without a pending case)
B5NoReHold: identical, except that fork handling (_fork) is invoked only when the receipt adds new fork evidence.
B5NoStuck : identical to the repository's B5 except that a released non-fork case whose re-run admission lands in a
            held feed keeps a pending FEED_FORK_HOLD case instead of being closed REJECTED.
"""
from pbti.b5 import B5FeedLevel
from pbti.review import QUARANTINED, RELEASED, REJECTED
from pbti.verifier import QUARANTINE


def _digs(reg, key):
    s = reg.slots.get(key)
    return (frozenset(s.digests()) if s is not None else frozenset()), (bool(s.versions) if s is not None else False)


class B5Instr(B5FeedLevel):
    fix_rehold = False
    fix_stuck = False

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.c = {"rehold_noev_calls": 0, "rehold_released": 0, "rehold_released_ev": 0, "stuck_reingest": 0,
                  "fork_calls": 0, "noev_held_other": 0}
        self._newev = None

    def _history(self, ev, wire, obs, rel, cb_obs, wid, kid, wkid, t, params, ann, waive=frozenset()):
        did, ep, seq = obs["did"], obs["ep"], obs["seq"]
        ks, kp = (did, ep, seq), (did, ep, seq - 1)
        b_s, _ = _digs(self.reg, ks)
        b_p, _ = _digs(self.reg, kp)
        self._pending_ev = (ks, kp, b_s, b_p)
        try:
            return super()._history(ev, wire, obs, rel, cb_obs, wid, kid, wkid, t, params, ann, waive)
        finally:
            self._pending_ev = None

    def _is_new_evidence(self):
        pe = getattr(self, "_pending_ev", None)
        if pe is None:
            return True                       # not called from _history: treat as new
        ks, kp, b_s, b_p = pe
        a_s, _ = _digs(self.reg, ks)
        a_p, pv = _digs(self.reg, kp)
        return (len(a_s) > 1 and a_s != b_s) or (pv and len(a_p) > 1 and a_p != b_p)

    def _fork(self, feed, f, t):
        self.c["fork_calls"] += 1
        new = self._is_new_evidence()
        if not new and self.fix_rehold:
            return
        did, ep = feed
        rel_before = {sq for sq in self.feed_seqs.get(feed, ()) if sq >= f and (did, ep, sq) not in self.held
                      and self.reg.slots.get((did, ep, sq)) is not None and self.reg.slots[(did, ep, sq)].versions
                      and (self.qcases.get(next(iter(self.reg.slots[(did, ep, sq)].versions.values()))) or {}).get("state") == RELEASED}
        if not new:
            self.c["rehold_noev_calls"] += 1
            self.c["rehold_released"] += len(rel_before)
            own = self._pending_ev[0] if getattr(self, "_pending_ev", None) else None
            self.c["noev_held_other"] += sum(
                1 for sq in self.feed_seqs.get(feed, ()) if sq >= f and (did, ep, sq) != own
                and (did, ep, sq) not in self.held and self.reg.slots.get((did, ep, sq)) is not None
                and self.reg.slots[(did, ep, sq)].versions)
        else:
            self.c["rehold_released_ev"] += len(rel_before)
        return super()._fork(feed, f, t)

    def _release(self, wd, case, t):
        if case["reason"] == "FEED_FORK_HOLD":
            return super()._release(wd, case, t)
        out = super()._release(wd, case, t)
        if out == "RELEASE_FAILED:QUARANTINE/FEED_FORK_HOLD":
            self.c["stuck_reingest"] += 1
            if self.fix_stuck:
                case["state"] = QUARANTINED
                case["reason"] = "FEED_FORK_HOLD"
                case["t_q"] = t
                return "DEFERRED_TO_FEED_HOLD"
        return out


class B5NoReHold(B5Instr):
    fix_rehold = True


class B5NoStuck(B5Instr):
    fix_stuck = True
