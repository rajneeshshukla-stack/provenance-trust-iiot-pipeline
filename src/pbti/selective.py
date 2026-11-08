"""PBTI-SH: selective evidence-gated holds (V4 research extension, memo R08/A3). A separate code path: the historical
PBTI verifier (src/pbti/verifier.py) is unchanged; this subclass only adds an authority gate.

Rule (frozen in research/V4/PREREGISTRATION_V4.md before the confirmatory runs):
  * Admission, Rule L, credential lifecycle, taint, evidence and lineage are exactly PBTI's.
  * Fork evidence: a feed f = (did, ep) becomes SUSPECT at the first time any slot of f is CONTESTED (two digests
    known for one identity, from admitted versions or successor-implied digests). Suspicion lasts for the epoch.
  * Eligibility: in a suspect feed, an observation whose slot is COMMITTED but NOT CORROBORATED is PROVISIONAL:
    stored and committed in the registry (its receipt is ACCEPT/COMMITTED with annotation PROVISIONAL), but not
    authoritative and not visible to derived processing. When a feed becomes suspect, every already committed and
    uncorroborated observation of the feed becomes provisional at that moment (targeted retroactive hold);
    corroborated observations stay available.
  * Release evidence: CORROBORATED means that an admitted successor's prev link names exactly the slot's digest
    (I(e) = V(e) = {cd}). A matching predecessor link is NOT sufficient, because whoever forges an observation
    can copy the known predecessor digest. A provisional observation is released (becomes authoritative and enters
    derived processing) as soon as it is corroborated, by the admission that supplies the successor link.
  * Timeout: timeout_ms = 0 (default arm): no timeout; an uncorroborated provisional observation stays withheld.
    timeout_ms > 0 (sensitivity arm): a provisional observation still COMMITTED, untainted and uncorroborated after
    timeout_ms is released at the next verifier tick (cause SH_TIMEOUT).
  * Contradiction: a provisional slot that becomes CONTESTED is contested as in PBTI and never released.
  * Revocation: taint applies to provisional slots exactly as to committed ones; a tainted slot is never released.
  * Audit: holds and releases are registry state events (SH_HOLD / SH_CORROBORATED / SH_TIMEOUT); the gate is a
    deterministic function of the admitted evidence and verifier time, so the auditor's decision replay (A-DET)
    reproduces it; A-REG/A-LIN use is_authoritative().
Limits: hash-link corroboration is a consistency check under the signer's keys, not independent evidence; an attacker
holding the device and relay keys can forge a consistent successor (negative control: full impersonation). The rule
adds no evidence source, so comparators receive exactly the same evidence.
"""
from __future__ import annotations

from .envelope import content_key
from .registry import COMMITTED, CONTESTED
from .verifier import ACCEPT, PBTIVerifier


class SelectiveHoldVerifier(PBTIVerifier):
    name = "PBTI-SH"

    def __init__(self, *args, timeout_ms: int = 0, **kw):
        super().__init__(*args, **kw)
        self.timeout_ms = int(timeout_ms)
        self.init_kw = {"timeout_ms": self.timeout_ms}
        self.suspect: dict[tuple, int] = {}      # (did, ep) -> time of first fork evidence
        self.prov: dict[tuple, int] = {}         # slot key -> time it became provisional
        self.feed_seqs: dict[tuple, set] = {}
        self.sh_holds = 0
        self.sh_released = 0
        self.sh_timeouts = 0
        self._wrap_proc_add()

    # ------------------------------------------------------------------ authority
    def is_authoritative(self, key, s) -> bool:
        return s.state() == COMMITTED and not s.tainted and key not in self.prov

    @staticmethod
    def corroborated(s) -> bool:
        return s.state() == COMMITTED and bool(s.implied)     # COMMITTED: V u I = {cd}; I non-empty => I = {cd}

    def _wrap_proc_add(self):
        orig = self.proc.add

        def add(obs_id, aid, ts, pl, ref, ckey, order_key):
            if isinstance(obs_id, tuple) and len(obs_id) == 3 and self._gate_now(obs_id):
                self._make_provisional(obs_id, self._t_now, "SH_HOLD", remove=False)
                return
            orig(obs_id, aid, ts, pl, ref, ckey, order_key)
        self._proc_add_orig = orig
        self.proc.add = add

    def _gate_now(self, key) -> bool:
        """Called when PBTI is about to make `key` authoritative (it is COMMITTED)."""
        did, ep, sq = key
        s = self.reg.slots.get(key)
        if s is None or self.corroborated(s):
            return False
        if (did, ep) in self.suspect:
            return True
        ps = self.reg.slots.get((did, ep, sq - 1))   # fork evidence created by this very admission (its prev link)
        return ps is not None and ps.state() == CONTESTED

    def _make_provisional(self, key, t, cause, remove=True):
        if key in self.prov:
            return
        self.prov[key] = t
        self.sh_holds += 1
        if remove:
            self.proc.remove(key, "CONTEST_CORRECTION")
        self.reg.record_change(t, key, COMMITTED, "PROVISIONAL", cause)

    def _release_prov(self, key, t, cause):
        s = self.reg.slots.get(key)
        if key not in self.prov or s is None or s.state() != COMMITTED or s.tainted:
            return False
        del self.prov[key]
        o = s.obs_first
        cd, wd = next(iter(s.versions.items()))
        self._proc_add_orig(key, o["aid"], o["ts"], o["pl"], wd,
                            content_key(o["did"], o["aid"], o["ts"], o["sch"], o["pl"]), (o["ep"], o["seq"]))
        self.reg.record_change(t, key, "PROVISIONAL", COMMITTED, cause)
        if cause == "SH_TIMEOUT":
            self.sh_timeouts += 1
        else:
            self.sh_released += 1
        return True

    # ------------------------------------------------------------------ admission
    def _history(self, ev, wire, obs, rel, cb_obs, wid, kid, wkid, t, params, ann, waive=frozenset()):
        self._t_now = t
        n_ev = len(self.reg.state_events)
        rec = super()._history(ev, wire, obs, rel, cb_obs, wid, kid, wkid, t, params, ann, waive)
        did, ep, sq = obs["did"], obs["ep"], obs["seq"]
        feed = (did, ep)
        key = (did, ep, sq)
        s = self.reg.slots.get(key)
        if s is not None and s.versions:
            self.feed_seqs.setdefault(feed, set()).add(sq)
        if key in self.prov and s is not None and s.state() == COMMITTED and rec.disp == ACCEPT:
            rec = rec._replace(ann=tuple(rec.ann) + ("PROVISIONAL",))
        # fork evidence created by this admission: make the feed suspect and gate its uncorroborated observations
        contested = any(e[3] == CONTESTED and isinstance(e[1], tuple) and e[1][:2] == feed
                        for e in self.reg.state_events[n_ev:])
        if s is not None and s.state() == CONTESTED:
            contested = True
        ps = self.reg.slots.get((did, ep, sq - 1))
        if ps is not None and ps.state() == CONTESTED:
            contested = True
        if contested and feed not in self.suspect:
            self.suspect[feed] = t
            for q in sorted(self.feed_seqs.get(feed, ())):
                k = (did, ep, q)
                sl = self.reg.slots.get(k)
                if sl is not None and sl.state() == COMMITTED and not sl.tainted and not self.corroborated(sl):
                    self._make_provisional(k, t, "SH_FORK")
        # corroboration supplied by this admission: its prev link may corroborate a provisional predecessor
        if ps is not None and (did, ep, sq - 1) in self.prov and self.corroborated(ps):
            self._release_prov((did, ep, sq - 1), t, "SH_CORROBORATED")
        if key in self.prov and s is not None and s.state() == CONTESTED:
            del self.prov[key]                      # contested: never released (Rule L)
        return rec

    # ------------------------------------------------------------------ time
    def _tick(self, t: int) -> None:
        super()._tick(t)
        for k in [k for k in self.prov if self.reg.slots[k].state() == CONTESTED]:
            del self.prov[k]                        # contested: never released (Rule L)
        if self.timeout_ms > 0:
            due = sorted(k for k, t0 in self.prov.items() if t - t0 >= self.timeout_ms)
            for k in due:
                self._release_prov(k, t, "SH_TIMEOUT")

    @property
    def holds(self) -> int:                         # reported by the oracle like B5's hold events
        return self.sh_holds

    @property
    def fork_events(self) -> int:
        return len(self.suspect)

    def slot_summary(self) -> dict:
        c = super().slot_summary()
        c["PROVISIONAL"] = len(self.prov)
        return c
