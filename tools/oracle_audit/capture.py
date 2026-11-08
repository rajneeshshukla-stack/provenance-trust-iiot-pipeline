"""Oracle audit: run one campaign specification exactly as experiments/run_v4.py:job() does, while capturing
  (1) ground truth from the simulator itself: every gateway acceptance (World._gw_accept) and every honest gateway
      wrap (World._wrap: the (did, ep, seq) identity and the content of the wire the honest gateway produced);
  (2) the pipeline's authoritative-state history by an independent poller: mutation tracking on the registry slots
      (versions / implied / tainted / lost), on B5's `held` set and on PBTI-SH's `prov` dict, re-evaluating the
      pipeline's own is_authoritative() predicate for every touched identity after every ingest / _tick /
      apply_review / finalize call, with the content read from the stored raw/quarantine blob of the slot's
      single version (not from Slot.obs_first and not from the Tracer's cache); a full scan of all slots is
      repeated every FULL_EVERY polls and at the end to verify the incremental state;
  (3) the repository's own outputs on the same run (oracle.evaluate + temporal.temporal_metrics + job() extras),
      and the Tracer log.
Nothing in the repository is modified; all patches are applied in this process only.
"""
from __future__ import annotations

import json
import sys
import time

REPO = "/home/claude/PBTI_v7/scratch/oracle_audit/repo"
sys.path.insert(0, REPO + "/src")
sys.path.insert(0, REPO + "/experiments")
sys.path.insert(0, "/home/claude/PBTI_v7/tools/oracle_audit")

import pbti.registry as _registry  # noqa: E402
import pbti.sim as _sim  # noqa: E402
from refmetrics import content, intervals_from_transitions  # noqa: E402

FULL_EVERY = 1000


# ============================================================================ mutation tracking (process-local)
class _Track:
    dirty_slots: set = set()
    dirty_keys: set = set()
    untracked_new = 0


def _mark(slot):
    _Track.dirty_slots.add(slot)


class _VDict(dict):
    __slots__ = ("_owner",)

    def __setitem__(self, k, v):
        dict.__setitem__(self, k, v)
        _mark(self._owner)

    def __delitem__(self, k):
        dict.__delitem__(self, k)
        _mark(self._owner)

    def pop(self, *a):
        r = dict.pop(self, *a)
        _mark(self._owner)
        return r

    def popitem(self):
        r = dict.popitem(self)
        _mark(self._owner)
        return r

    def clear(self):
        dict.clear(self)
        _mark(self._owner)

    def update(self, *a, **kw):
        dict.update(self, *a, **kw)
        _mark(self._owner)

    def setdefault(self, k, d=None):
        r = dict.setdefault(self, k, d)
        _mark(self._owner)
        return r


class _ISet(set):
    __slots__ = ("_owner",)

    def add(self, x):
        set.add(self, x)
        _mark(self._owner)

    def discard(self, x):
        set.discard(self, x)
        _mark(self._owner)

    def remove(self, x):
        set.remove(self, x)
        _mark(self._owner)

    def update(self, *a):
        set.update(self, *a)
        _mark(self._owner)

    def clear(self):
        set.clear(self)
        _mark(self._owner)

    def pop(self):
        r = set.pop(self)
        _mark(self._owner)
        return r

    def __ior__(self, o):
        set.__ior__(self, o)
        _mark(self._owner)
        return self


_OrigSlot = _registry.Slot


class DirtySlot(_OrigSlot):
    """Behaviourally identical Slot that records every mutation of the state its authority depends on."""

    def __setattr__(self, name, value):
        if name == "versions" and type(value) is dict:
            v = _VDict(value)
            v._owner = self
            value = v
        elif name == "implied" and type(value) is set:
            v = _ISet(value)
            v._owner = self
            value = v
        object.__setattr__(self, name, value)
        if name in ("versions", "implied", "tainted", "lost", "obs_first"):
            _mark(self)


class _TrackSlots(dict):
    def __setitem__(self, key, slot):
        dict.__setitem__(self, key, slot)
        try:
            object.__setattr__(slot, "_key", key)
        except Exception:  # noqa: BLE001
            _Track.untracked_new += 1
        _mark(slot)


class _KeySet(set):
    def add(self, k):
        set.add(self, k)
        _Track.dirty_keys.add(k)

    def discard(self, k):
        set.discard(self, k)
        _Track.dirty_keys.add(k)

    def remove(self, k):
        set.remove(self, k)
        _Track.dirty_keys.add(k)


class _KeyDict(dict):
    def __setitem__(self, k, v):
        dict.__setitem__(self, k, v)
        _Track.dirty_keys.add(k)

    def __delitem__(self, k):
        dict.__delitem__(self, k)
        _Track.dirty_keys.add(k)

    def pop(self, k, *d):
        r = dict.pop(self, k, *d)
        _Track.dirty_keys.add(k)
        return r


_registry.Slot = DirtySlot


# ============================================================================ ground-truth capture
class _GT:
    acc: dict = {}      # id(LogicalObs) -> [world.now at each gateway acceptance]
    wraps: dict = {}    # id(LogicalObs) -> [(eid, content, t, gid)]


_orig_accept = _sim.World._gw_accept
_orig_wrap = _sim.World._wrap


def _gw_accept(self, gw, d, item, mode=None):
    o = item[1] if isinstance(item, tuple) else item
    _GT.acc.setdefault(id(o), []).append(self.now)
    return _orig_accept(self, gw, d, item, mode)


def _wrap(self, gw, d, item, mode, t):
    wire = _orig_wrap(self, gw, d, item, mode, t)
    o = item[1] if isinstance(item, tuple) else item
    try:
        obs = json.loads(wire)["obs"]
        eid = (obs["did"], obs["ep"], obs["seq"])
        c = content(obs["did"], obs["aid"], obs["ts"], obs["sch"], obs["pl"])
    except Exception:  # noqa: BLE001  (non-PBTI wire formats: B1-B3 are not traced)
        eid, c = None, None
    _GT.wraps.setdefault(id(o), []).append((eid, c, t, gw.gid))
    return wire


_sim.World._gw_accept = _gw_accept
_sim.World._wrap = _wrap


# ============================================================================ independent poller
class Poller:
    def __init__(self, world):
        self.w = world
        self.sys = world.sys
        self.cur: dict = {}                 # key -> content (authoritative now)
        self.trans_call: list = []          # (t_call, key, old, new)
        self.trans_world: list = []         # (world.now, key, old, new)
        self.polls = 0
        self.full_checks = 0
        self.full_mismatch: list = []
        self.leaks = 0
        self.blob_missing = 0
        self.obs_first_disagree = 0
        self._cache: dict = {}
        self._depth = 0
        reg = self.sys.reg
        assert not reg.slots, "poller must be attached before the run"
        reg.slots = _TrackSlots()
        if hasattr(self.sys, "held"):
            assert not self.sys.held
            self.sys.held = _KeySet()
        if hasattr(self.sys, "prov"):
            assert not self.sys.prov
            self.sys.prov = _KeyDict()
        _Track.dirty_slots = set()
        _Track.dirty_keys = set()
        for name in ("ingest", "_tick", "apply_review", "finalize"):
            if hasattr(self.sys, name):
                setattr(self.sys, name, self._wrapfn(name, getattr(self.sys, name)))

    def _wrapfn(self, name, fn):
        def wrapped(*a, **kw):
            if self._depth == 0 and (_Track.dirty_slots or _Track.dirty_keys):
                self.leaks += 1                       # mutation outside any wrapped call
                self.poll(self.w.now)
            self._depth += 1
            try:
                r = fn(*a, **kw)
            finally:
                self._depth -= 1
            if name in ("ingest", "apply_review"):
                t = a[1] if len(a) > 1 else kw["t"]
            else:
                t = a[0] if a else kw["t"]
            self.poll(int(t))
            return r
        return wrapped

    def _content(self, key, s):
        wd = next(iter(s.versions.values()))
        c = self._cache.get((key, wd))
        if c is None:
            st = self.sys.store
            blob = st.get_blob("raw", wd) or st.get_blob("q", wd)
            if blob is None:
                self.blob_missing += 1
                o = s.obs_first
            else:
                o = json.loads(blob)["obs"]
            c = content(o["did"], o["aid"], o["ts"], o["sch"], o["pl"])
            of = s.obs_first
            if of is not None and content(of["did"], of["aid"], of["ts"], of["sch"], of["pl"]) != c:
                self.obs_first_disagree += 1
            self._cache[(key, wd)] = c
        return c

    def _eval(self, key):
        s = self.sys.reg.slots.get(key)
        if s is None or not s.versions or not self.sys.is_authoritative(key, s):
            return None
        return self._content(key, s)

    def poll(self, t):
        self.polls += 1
        keys = set(_Track.dirty_keys)
        for sl in _Track.dirty_slots:
            k = getattr(sl, "_key", None)
            if k is not None:
                keys.add(k)
        _Track.dirty_slots = set()
        _Track.dirty_keys = set()
        for key in keys:
            new = self._eval(key)
            old = self.cur.get(key)
            if new != old:
                self.trans_call.append((t, key, old, new))
                self.trans_world.append((self.w.now, key, old, new))
                if new is None:
                    del self.cur[key]
                else:
                    self.cur[key] = new
        if self.polls % FULL_EVERY == 0:
            self.full_check(t)

    def full_check(self, t):
        self.full_checks += 1
        full = {}
        for key, s in self.sys.reg.slots.items():
            if s.versions and self.sys.is_authoritative(key, s):
                full[key] = self._content(key, s)
        if full != self.cur:
            diff = {k for k in set(full) | set(self.cur) if full.get(k) != self.cur.get(k)}
            self.full_mismatch.append((t, len(diff), sorted(map(str, diff))[:5]))


# ============================================================================ one run
TIMING = ("ingest_us_mean", "ingest_us_p50", "ingest_us_p95", "ingest_us_p99", "wrap_us_mean", "devsign_us_mean",
          "wall_s", "audit_pass", "audit_findings", "audit_static_s", "audit_replay_s")


def run_spec(spec: dict) -> dict:
    """Mirror of experiments/run_v4.py:job() (audit skipped: it does not change any outcome) plus capture."""
    import run_v4
    from pbti.oracle import evaluate
    from pbti.scenarios import build
    from pbti.sweep import build_sweep
    from pbti.temporal import temporal_metrics
    _GT.acc, _GT.wraps = {}, {}
    t0 = time.perf_counter()
    kw = {k: v for k, v in spec["cfg"].items() if k in run_v4.CFG_KEYS}
    if spec["kind"] == "scenario":
        w = build(spec["scenario"], spec["system"], spec["seed"], **kw)
    else:
        w = build_sweep(spec["levels"], spec["system"], spec["seed"], **kw)
    poller = Poller(w)
    w.run()
    poller.full_check(w.cfg.duration_ms + w.cfg.drain_ms)
    t_run = time.perf_counter() - t0
    # ---------------------------------------------------------------- repository outputs (as job() writes them)
    r = evaluate(w)
    r.update(temporal_metrics(w))
    r.update({k: spec[k] for k in ("campaign", "arm", "kind", "scenario", "seed", "point", "run", "levels") if k in spec})
    r["cfg"] = spec["cfg"]
    rv = w.reviewer
    if rv is not None:
        r["review_decisions"] = rv.decisions
        r["review_deferrals"] = getattr(rv, "deferrals", 0)
        r["review_mode"] = w.cfg.review_mode
        r["review_rule"] = rv.rule
        r["review_delay_ms"] = w.cfg.review_delay_ms
        r["review_every_ms"] = w.cfg.review_every_ms
        r["event_review_rounds"] = w.event_review_rounds
    for k in ("sh_holds", "sh_released", "sh_timeouts", "resumed_feeds"):
        if hasattr(w.sys, k):
            r[k] = getattr(w.sys, k)
    if hasattr(w.sys, "prov"):
        r["sh_provisional_end"] = len(w.sys.prov)
        r["sh_suspect_feeds"] = len(w.sys.suspect)
    if hasattr(w.sys, "held"):
        r["held_end"] = len(w.sys.held)
        r["held_distinct_ever"] = len({e[1] for e in w.sys.reg.state_events if e[3] == "HELD"})
    # ---------------------------------------------------------------- ground truth
    t_end = w.cfg.duration_ms + w.cfg.drain_ms
    legit, produced, gt_issues = [], set(), {"wrap_content_ne_truth": 0, "wrap_eid_ne_obs": 0, "acc_without_wrap": 0,
                                             "meta_tacc_ne_capture": 0, "meta_eids_ne_capture": 0,
                                             "multi_identity": 0, "multi_accept": 0}
    for rec in w.truth:
        o = rec["o"]
        c_truth = content(rec["did"], rec["aid"], rec["ts"], o.sch, rec["pl"])
        produced.add(c_truth)
        acc = _GT.acc.get(id(o))
        wr = _GT.wraps.get(id(o), [])
        pairs = set()
        for (eid, c, _t, _g) in wr:
            if c != c_truth:
                gt_issues["wrap_content_ne_truth"] += 1
            if eid != (o.did, o.ep, o.seq):
                gt_issues["wrap_eid_ne_obs"] += 1
            pairs.add((eid, c))
        if acc and not wr:
            gt_issues["acc_without_wrap"] += 1
        if acc and len(acc) > 1:
            gt_issues["multi_accept"] += 1
        if len({p[0] for p in pairs}) > 1:
            gt_issues["multi_identity"] += 1
        t_acc = min(acc) if acc else None
        if acc and o.meta.get("t_acc") != t_acc:
            gt_issues["meta_tacc_ne_capture"] += 1
        if acc and {tuple(e) for e in (o.meta.get("eids") or [])} != {p[0] for p in pairs}:
            gt_issues["meta_eids_ne_capture"] += 1
        legit.append({"t_prod": rec["t"], "t_acc": t_acc, "content": c_truth, "pairs": pairs,
                      "label": f"{rec['did']}/{o.ep}/{o.seq}"})
    # ---------------------------------------------------------------- end state, three ways
    end_poll = {(k, c) for k, c in poller.cur.items()}
    end_oracle = set()
    for k, ck in w.sys.authoritative():
        end_oracle.add((k, content(ck[0], ck[1], ck[2], ck[3], json.loads(ck[4]))))
    tr = w.tracer
    tracer_trans = [(t, k, None if a is None else content(a[0], a[1], a[2], a[3], json.loads(a[4])),
                     None if b is None else content(b[0], b[1], b[2], b[3], json.loads(b[4])))
                    for (t, k, a, b, _cd, _kid) in tr.log]
    out = {"spec": {k: v for k, v in spec.items() if k != "levels"} | ({"levels": spec["levels"]} if "levels" in spec else {}),
           "t_end": t_end, "repo_row": r, "run_s": t_run,
           "poller": {"polls": poller.polls, "full_checks": poller.full_checks, "full_mismatch": poller.full_mismatch,
                      "leaks": poller.leaks, "blob_missing": poller.blob_missing,
                      "obs_first_disagree": poller.obs_first_disagree, "untracked_new": _Track.untracked_new,
                      "transitions": len(poller.trans_call)},
           "gt_issues": gt_issues,
           "end_state": {"poll_eq_oracle": end_poll == end_oracle, "n_poll": len(end_poll), "n_oracle": len(end_oracle),
                         "poll_minus_oracle": len(end_poll - end_oracle), "oracle_minus_poll": len(end_oracle - end_poll)}}
    hist = {}
    for name, trans in (("poll_call", poller.trans_call), ("poll_world", poller.trans_world), ("tracer", tracer_trans)):
        iv, zero, endp = intervals_from_transitions(trans, t_end)
        hist[name] = (iv, zero, endp)
    out["_legit"] = legit
    out["_produced"] = produced
    out["_hist"] = hist
    out["_end_oracle"] = end_oracle
    out["_end_poll"] = end_poll
    return out
