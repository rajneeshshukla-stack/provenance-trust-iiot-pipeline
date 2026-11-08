#!/usr/bin/env python3
"""Hand-computed oracle/temporal cases (oracle audit).

Each case drives the REAL, unmodified verifier of the repository (PBTI, B5 or PBTI-SH) through a micro world: one
signing device d1 (asset a1, epoch 0) behind gateway gw1, receipts at hand-chosen virtual times, the repository's
Tracer attached exactly as World._build attaches it, and hand-written ground truth (production time, first gateway
acceptance time, identity). Expected values are derived BY HAND in the comments (they are not computed by
src/pbti/oracle.py or src/pbti/temporal.py). Each case is evaluated three ways:
    expected (hand)  |  repository: oracle.evaluate + temporal.temporal_metrics  |  reference: refmetrics.compute on
    the independent poller's history (capture.Poller)
Notation: Gi = genuine observation with seq i, Fi = forged content under the same identity (stolen device key and
relay key, as EquivocationHook/GapFillHook do). ts = production time. T_end = duration + drain = 20 s + 10 s = 30 s
unless stated. All times in ms; durations reported in s.
"""
from __future__ import annotations

import json
import math
import sys
import types

sys.path.insert(0, "/home/claude/PBTI_v7/tools/oracle_audit")
import capture  # noqa: E402,F401  (installs the process-local slot instrumentation; adds the repo to sys.path)
from refmetrics import compute as ref_compute, content, intervals_from_transitions  # noqa: E402

from pbti.b5 import B5FeedLevel  # noqa: E402
from pbti.crypto import b64u, keypair_from_seed, sha256_hex  # noqa: E402
from pbti.envelope import LogicalObs, content_key, pbti_content_digest, pbti_sign_obs, pbti_wire  # noqa: E402
from pbti.identity import TrustRegistry  # noqa: E402
from pbti.oracle import evaluate  # noqa: E402
from pbti.policy import PolicyStore  # noqa: E402
from pbti.review import RELEASABLE, sign_decision  # noqa: E402
from pbti.selective import SelectiveHoldVerifier  # noqa: E402
from pbti.temporal import Tracer, temporal_metrics  # noqa: E402
from pbti.verifier import Ablation, PBTIVerifier, VerifierConfig  # noqa: E402

SEED = b"oracle-audit-hand-cases"
WID = "spiffe://plant-a.example/cell1/gw1/collector"
RID = "urn:pbti:reviewer:auto"


class Micro:
    def __init__(self, system="PBTI", params=None, duration_ms=20_000, drain_ms=10_000, nominal=None):
        self.trust = TrustRegistry(SEED, use_x509=False)
        self.dsk, dpk = keypair_from_seed(SEED, "dk:d1:1")
        self.wsk, wpk = keypair_from_seed(SEED, "wk:gw1:1")
        self.rsk, rpk = keypair_from_seed(SEED, "rk:auto:1")
        self.trust.issue("dk:d1:1", "device", "d1", dpk, -60_000, 10 ** 12)
        self.trust.issue("wk:gw1:1", "workload", WID, wpk, -60_000, 10 ** 12)
        self.trust.issue("rk:auto:1", "reviewer", RID, rpk, -60_000, 10 ** 12)
        doc = {"devices": {"d1": {"assets": ["a1"], "origin": "device", "schemas": ["telemetry.v1"]}},
               "workloads": {WID: {"relay": ["d1"]}}, "params": dict(params or {}),
               "reviewers": {RID: {"may_release": list(RELEASABLE), "active": True}}}
        vk = keypair_from_seed(SEED, "verifier")
        if system == "PBTI":
            self.sys = PBTIVerifier(self.trust, PolicyStore(doc), vk)
        elif system == "B5":
            self.sys = B5FeedLevel(self.trust, PolicyStore(doc), vk)
        elif system == "PBTI-SH":
            self.sys = SelectiveHoldVerifier(self.trust, PolicyStore(doc), vk, timeout_ms=0)
        else:
            raise ValueError(system)
        self.cfg = types.SimpleNamespace(system=system, ablation=Ablation(), seed=0, vcfg=VerifierConfig(),
                                         duration_ms=duration_ms, drain_ms=drain_ms)
        self.t_end = duration_ms + drain_ms
        self.now = 0
        self.truth, self.revocations = [], []
        self.devices = {"d1": types.SimpleNamespace(aid="a1", base_t=nominal)} if nominal is not None else {}
        self.ingest_ns, self.wrap_ns, self.sign_dev_ns, self.wire_bytes = [], [], [], []
        self.cv_samples = self.cv_wrong = 0
        self.receipts_by_label = {}
        self.tracer = Tracer(self)                 # as World._build does when cfg.temporal is set
        self.poller = capture.Poller(self)         # independent history (outer wrapper)
        self.ref_legit = []
        self.cd = {}

    # ------------------------------------------------------------------ statements
    def stmt(self, seq, ts, temp, prev, tag):
        o = LogicalObs("d1", "a1", 0, seq, ts, "telemetry.v1", {"temp_c": temp}, f"m-{tag}", prev)
        obs, osig = pbti_sign_obs(o, self.dsk, "dk:d1:1")
        self.cd[tag] = b64u(pbti_content_digest(obs))
        return o, obs, osig

    def genuine(self, tag, seq, t_prod, temp, prev_tag=None, accepted=True, t_acc=None):
        """Ground truth of one legitimate observation (as World._produce/_gw_accept/_wrap record it)."""
        prev = self.cd[prev_tag] if prev_tag else None
        o, obs, osig = self.stmt(seq, t_prod, temp, prev, tag)
        o.meta = {"t_prod": t_prod, "gw": "gw1"}
        if accepted:
            o.meta.update(gw_accepted=True, t_acc=t_prod if t_acc is None else t_acc, eids=[("d1", 0, seq)])
        self.truth.append({"did": "d1", "aid": "a1", "ts": t_prod, "t": t_prod, "pl": o.pl, "o": o,
                           "ck": content_key("d1", "a1", t_prod, "telemetry.v1", o.pl)})
        c = content("d1", "a1", t_prod, "telemetry.v1", o.pl)
        self.ref_legit.append({"t_prod": t_prod, "t_acc": (o.meta.get("t_acc") if accepted else None),
                               "content": c, "pairs": {(("d1", 0, seq), c)} if accepted else set()})
        return pbti_wire(obs, osig, WID, "wk:gw1:1", self.wsk, t_prod, "live")

    def forged(self, tag, seq, ts, temp, prev_tag=None, prev=None):
        p = self.cd[prev_tag] if prev_tag else prev
        o, obs, osig = self.stmt(seq, ts, temp, p, tag)
        return pbti_wire(obs, osig, WID, "wk:gw1:1", self.wsk, ts, "live")

    # ------------------------------------------------------------------ pipeline calls (as World.receive does)
    def rx(self, wire, t, label="legit"):
        self.now = t
        r = self.sys.ingest(wire, t, {"tid": WID, "tkid": "wk:gw1:1"})
        k = r.disp + "/" + r.why.split(":")[0]
        d = self.receipts_by_label.setdefault(label, {})
        d[k] = d.get(k, 0) + 1
        self.tracer.note_receipt(t, wire, label)
        return k

    def review(self, wire, t, decision):
        self.now = t
        wd = sha256_hex(wire)
        snap = self.sys.open_review(wd, RID, t)
        assert snap is not None, "case not open"
        d = sign_decision({"case": wd, "reviewer": RID, "rkid": "rk:auto:1", "decision": decision,
                           "reason": "HAND", "snapshot": snap, "t": t}, self.rsk)
        return self.sys.apply_review(d, t)["outcome"]

    def revoke(self, t_rev, t_comp):
        self.trust.revoke("dk:d1:1", t_rev, t_comp, "hand-case")
        self.revocations.append((t_rev, "dk:d1:1", t_comp))

    def finish(self):
        self.now = self.t_end
        self.sys.finalize(self.t_end)
        o = evaluate(self)
        m = temporal_metrics(self)
        repo = dict(o)
        repo.update(m)
        repo["W"] = repo["tm_wh_rec_s"] / max(1, repo["tm_reach"])
        if hasattr(self.sys, "held"):          # the two extra B5 fields exactly as experiments/run_v4.py:job() computes them
            repo["held_end"] = len(self.sys.held)
            repo["held_distinct_ever"] = len({e[1] for e in self.sys.reg.state_events if e[3] == "HELD"})
        iv, zero, endp = intervals_from_transitions(self.poller.trans_call, self.t_end)
        ref = ref_compute(self.ref_legit, iv, set(self.poller.cur.items()), self.t_end)
        ref["zero"] = zero
        return repo, ref


# repository field -> reference field
RMAP = {"nonlegit_auth": "O1_content", "legit_missing": "O2_content", "tm_nl_rec_s": "NLX_s",
        "tm_wh_rec_s": "withheld_s", "W": "W_s", "tm_avail_1s": "AV1", "tm_avail_5s": "AV5",
        "tm_avail_30s": "AV30", "tm_avail_60s": "AV60", "tm_never_avail": "never", "tm_withdrawn": "withdrawn",
        "tm_withdrawn_end": "withdrawn_end", "tm_first_km_p50_s": "KM50_s", "tm_first_km_p90_s": "KM90_s",
        "tm_first_km_p99_s": "KM99_s", "tm_zero_flips": "zero", "tm_nl_pairs_ever": "nl_pairs_ever",
        "tm_nl_auth_end": "nl_auth_end"}


def _eq(a, b):
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)
    return a == b


# ============================================================================ cases
def case_A_forged_and_genuine_share_identity():
    """Back-running equivocation. G0@1.1s, G1@2.1s commit; F1 (same identity, forged payload)@2.6s contests slot 1;
    G2@3.1s commits. A(t) never holds (seq1, F1): the forgery is not authoritative for any positive time, and the
    genuine G1 is available only [2100, 2600)."""
    w = Micro()
    g0 = w.genuine("G0", 0, 1000, 50.0)
    g1 = w.genuine("G1", 1, 2000, 51.0, "G0")
    f1 = w.forged("F1", 1, 2000, 99.0, "G0")
    g2 = w.genuine("G2", 2, 3000, 52.0, "G1")
    rx = [w.rx(g0, 1100), w.rx(g1, 2100), w.rx(f1, 2600, "equivocation"), w.rx(g2, 3100)]
    exp = {
        "nonlegit_auth": 0,                 # F1 never authoritative at the end (slot 1 CONTESTED)
        "legit_missing": 1,                 # G1 (contested); G0, G2 authoritative
        "tm_nl_rec_s": 0.0,                 # F1 never in A(t)
        "tm_nl_pairs_ever": 0,
        # withheld: G0 (30000-1000)-28900 = 100; G1 (30000-2000)-(2600-2100) = 27500; G2 100  -> 27700 ms
        "tm_wh_rec_s": 27.7,
        "W": 27.7 / 3,                      # 9.2333 s per observation
        "tm_avail_1s": 1.0,                 # first availability 100 ms for all three (G1 counts though withdrawn)
        "tm_avail_5s": 1.0,
        "tm_never_avail": 0,
        "tm_withdrawn": 1, "tm_withdrawn_end": 1,   # G1
        "tm_first_km_p50_s": 0.1,           # three events at 100 ms
        "tm_zero_flips": 0,
        "tm_transitions": 4,                # G0 in, G1 in, G1 out, G2 in
        "tm_end_state_matches_authoritative": True,
        # derived window (a1, [0,10 s)): ideal {G0,G1,G2}, final version {G0,G2} -> incomplete; current value = G2
        "win_total": 1, "win_exact": 0, "win_incomplete": 1, "win_corrupt": 0, "cv_assets": 1, "cv_correct": 1,
    }
    return w, rx, exp, ["ACCEPT/COMMITTED", "ACCEPT/COMMITTED", "CONFLICT/EQUIVOCATION", "ACCEPT/COMMITTED"]


def case_B_front_running_same_ms_zero_flip_of_forgery():
    """Front-running at the same millisecond: F1@2100 commits, genuine G1@2100 contests it at once. The forged pair
    is authoritative for zero time: no NLX, counted as a zero flip; G1 is never available (censored)."""
    w = Micro()
    g0 = w.genuine("G0", 0, 1000, 50.0)
    g1 = w.genuine("G1", 1, 2000, 51.0, "G0")
    f1 = w.forged("F1", 1, 2000, 99.0, "G0")
    g2 = w.genuine("G2", 2, 3000, 52.0, "G1")
    rx = [w.rx(g0, 1100), w.rx(f1, 2100, "equivocation"), w.rx(g1, 2100), w.rx(g2, 3100)]
    exp = {
        "nonlegit_auth": 0, "legit_missing": 1,
        "tm_nl_rec_s": 0.0, "tm_nl_pairs_ever": 0,
        "tm_zero_flips": 1,                 # (seq1,F1) enters and leaves at 2100
        # withheld: G0 100; G1 never: 30000-2000 = 28000; G2 100 -> 28200 ms
        "tm_wh_rec_s": 28.2, "W": 9.4,
        "tm_avail_5s": 2 / 3, "tm_never_avail": 1, "tm_withdrawn": 0,
        # KM: (100,e),(100,e),(28000,c): S(100)=1-2/3 -> F=2/3>=0.5 -> p50=0.1 s; F never reaches 0.9 -> None
        "tm_first_km_p50_s": 0.1, "tm_first_km_p90_s": None,
        "tm_transitions": 4,                # G0 in, F1 in, F1 out, G2 in
    }
    return w, rx, exp, ["ACCEPT/COMMITTED", "ACCEPT/COMMITTED", "CONFLICT/EQUIVOCATION", "ACCEPT/COMMITTED"]


def case_C_brief_forgery_withdrawn_by_successor():
    """Gap-fill: genuine G1 accepted by the gateway at 2.0 s but suppressed; F1 (copies G0's link)@2.1s commits;
    genuine successor G2@5.1s names G1's digest -> slot 1 CONTESTED, F1 withdrawn at 5.1 s."""
    w = Micro()
    g0 = w.genuine("G0", 0, 1000, 50.0)
    w.genuine("G1", 1, 2000, 51.0, "G0")          # suppressed: never delivered
    f1 = w.forged("F1", 1, 2000, 99.0, "G0")
    g2 = w.genuine("G2", 2, 5000, 52.0, "G1")
    rx = [w.rx(g0, 1100), w.rx(f1, 2100, "gapfill"), w.rx(g2, 5100)]
    exp = {
        "nonlegit_auth": 0, "legit_missing": 1,       # G1
        "tm_nl_rec_s": 3.0,                           # F1 authoritative [2100, 5100)
        "tm_nl_pairs_ever": 1, "tm_nl_auth_end": 0,
        "tm_wh_rec_s": 28.2, "W": 9.4,                # 100 + 28000 + 100
        "tm_avail_5s": 2 / 3, "tm_never_avail": 1, "tm_withdrawn": 0,
        "tm_nl_contained": 1, "tm_nl_contained_undirected": 0,
        "tm_contain_lat_max_s": 0.0,                  # successor receipt at 5100 contradicts F1, contained at 5100
        "legit_quarantined": 0, "legit_lost_unrecoverable": 1,
    }
    return w, rx, exp, ["ACCEPT/COMMITTED", "ACCEPT/COMMITTED", "ACCEPT/COMMITTED"]


def case_D_quarantine_then_release():
    """PBTI, horizon 10 s: G1 (ts 2.0 s) arrives buffered at 15 s -> QUARANTINE/STALE_TS; released by an authorized
    review at 16 s."""
    w = Micro(params={"h_max_ms": 10_000})
    g0 = w.genuine("G0", 0, 1000, 50.0)
    g1 = w.genuine("G1", 1, 2000, 51.0, "G0")
    rx = [w.rx(g0, 1100), w.rx(g1, 15_000)]
    rx.append(w.review(g1, 16_000, "RELEASE"))
    exp = {
        "nonlegit_auth": 0, "legit_missing": 0, "legit_quarantined": 0,
        "tm_wh_rec_s": 14.1, "W": 7.05,               # G0 100; G1 16000-2000 = 14000
        "tm_avail_1s": 0.5, "tm_avail_5s": 0.5, "tm_avail_30s": 1.0, "tm_avail_60s": 1.0,
        "tm_never_avail": 0, "tm_withdrawn": 0,
        # KM: events 100 and 14000: F(100)=0.5 -> p50 = 0.1 s; F(14000)=1 -> p90 = p99 = 14 s
        "tm_first_km_p50_s": 0.1, "tm_first_km_p90_s": 14.0, "tm_first_km_p99_s": 14.0,
        "recovered_n": 1,
        # window (a1, 0): ideal {G0,G1}; after the release the final version is {G0,G1} -> exact; current value G1
        "win_total": 1, "win_exact": 1, "win_incomplete": 0, "win_corrupt": 0, "cv_correct": 1,
    }
    return w, rx, exp, ["ACCEPT/COMMITTED", "QUARANTINE/STALE_TS", "RELEASED"]


def _b5_fork_prefix(w):
    g0 = w.genuine("G0", 0, 1000, 50.0)
    g1 = w.genuine("G1", 1, 2000, 51.0, "G0")
    f1 = w.forged("F1", 1, 2000, 99.0, "G0")
    g2 = w.genuine("G2", 2, 3000, 52.0, "G1")
    g3 = w.genuine("G3", 3, 4000, 53.0, "G2")
    rx = [w.rx(g0, 1100), w.rx(g1, 2100), w.rx(f1, 2600, "equivocation"), w.rx(g2, 3100), w.rx(g3, 4100)]
    rx.append(w.review(g2, 10_000, "RELEASE"))       # corroborated by G3's link
    rx.append(w.review(g3, 10_000, "RELEASE"))       # corroborated by authoritative predecessor G2
    return rx, (g0, g1, f1, g2, g3)


def case_E_b5_hold_then_release():
    """B5: F1@2.6s forks feed (d1,0) at seq 1 -> slot 1 held (contested; G1 withdrawn at 2.6 s); G2@3.1s and G3@4.1s
    held at admission; reviewer releases G2 then G3 at 10 s."""
    w = Micro(system="B5")
    rx, _ = _b5_fork_prefix(w)
    exp = {
        "nonlegit_auth": 0, "legit_missing": 1,       # G1
        "tm_nl_rec_s": 0.0,
        # withheld: G0 100; G1 28000-500 = 27500; G2 10000-3000 = 7000; G3 10000-4000 = 6000 -> 40600 ms
        "tm_wh_rec_s": 40.6, "W": 10.15,
        "tm_avail_1s": 0.5, "tm_avail_5s": 0.5, "tm_avail_30s": 1.0,
        "tm_withdrawn": 1, "tm_withdrawn_end": 1, "tm_never_avail": 0,
        # KM events 100,100,6000,7000: F(100)=0.5 -> p50 0.1 s; F(6000)=0.75, F(7000)=1 -> p90 7 s
        "tm_first_km_p50_s": 0.1, "tm_first_km_p90_s": 7.0,
        "tm_transitions": 5,                          # G0 in, G1 in, G1 out, G2 in, G3 in
        "recovered_n": 2,
        "legit_quarantined": 0, "legit_lost_unrecoverable": 1,
        "holds": 3,                                   # three distinct slots were held (1, 2, 3)
        "held_distinct_ever": 3,
    }
    return w, rx, exp, ["ACCEPT/COMMITTED", "ACCEPT/COMMITTED", "CONFLICT/EQUIVOCATION", "QUARANTINE/FEED_FORK_HOLD",
                        "QUARANTINE/FEED_FORK_HOLD", "RELEASED_HOLD", "RELEASED_HOLD"]


def case_E2_b5_rehold_after_release():
    """Continuation of E: after the feed resumed, F2 (forged copy of identity seq 2) @12 s forks the feed again ->
    released G2 (now contested) and G3 are held again (withdrawn at 12 s); review at 20 s rejects G3 (not
    corroborated: its predecessor is contested)."""
    w = Micro(system="B5")
    rx, (g0, g1, f1, g2, g3) = _b5_fork_prefix(w)
    f2 = w.forged("F2", 2, 3000, 98.0, "G1")
    rx.append(w.rx(f2, 12_000, "equivocation"))
    rx.append(w.review(g3, 20_000, "REJECT"))
    exp = {
        "nonlegit_auth": 0, "legit_missing": 3,       # G1, G2 (contested), G3 (held, rejected)
        "tm_nl_rec_s": 0.0,
        # withheld: G0 100; G1 27500; G2 (30000-3000)-(12000-10000) = 25000; G3 (30000-4000)-2000 = 24000
        "tm_wh_rec_s": 76.6, "W": 19.15,
        "tm_withdrawn": 3, "tm_withdrawn_end": 3, "tm_never_avail": 0,
        "tm_avail_5s": 0.5, "tm_avail_30s": 1.0,
        "tm_transitions": 7,                          # + G2 out, G3 out at 12 s
        # "still quarantined or held" (paper, Metrics): G3 is still held (case rejected, slot COMMITTED); G2's slot is
        # CONTESTED like G1's (absorbing, never releasable), so G2 is lost exactly as G1 is -> 1 held, 2 lost
        "legit_quarantined": 1, "legit_lost_unrecoverable": 2,
        "holds": 5,                                   # hold episodes: slot1@2.6, slot2@3.1, slot3@4.1, slot2@12, slot3@12
    }
    return w, rx, exp, ["ACCEPT/COMMITTED", "ACCEPT/COMMITTED", "CONFLICT/EQUIVOCATION", "QUARANTINE/FEED_FORK_HOLD",
                        "QUARANTINE/FEED_FORK_HOLD", "RELEASED_HOLD", "RELEASED_HOLD", "CONFLICT/EQUIVOCATION",
                        "REJECTED"]


def case_F_never_released_censoring():
    """PBTI, horizon 10 s, no reviewer: G1 (ts 2 s) and G2 (ts 3 s) both arrive at 15 s -> STALE_TS quarantine to the
    end. Never-available observations stay in every denominator and are censored at T_end."""
    w = Micro(params={"h_max_ms": 10_000})
    g0 = w.genuine("G0", 0, 1000, 50.0)
    g1 = w.genuine("G1", 1, 2000, 51.0, "G0")
    g2 = w.genuine("G2", 2, 3000, 52.0, "G1")
    rx = [w.rx(g0, 1100), w.rx(g1, 15_000), w.rx(g2, 15_000)]
    exp = {
        "legit_missing": 2, "legit_quarantined": 2, "legit_lost_unrecoverable": 0,
        "tm_wh_rec_s": 55.1, "W": 55.1 / 3,           # 100 + 28000 + 27000
        "tm_avail_5s": 1 / 3, "tm_avail_60s": 1 / 3, "tm_never_avail": 2,
        # KM: (100,e),(27000,c),(28000,c): F(100)=1/3 < 0.5 and no later event -> p50 None
        # (if the censored observations were dropped, p50 would be 0.1 s and AV5 1.0)
        "tm_first_km_p50_s": None, "tm_first_km_p90_s": None,
        "nonlegit_auth": 0, "tm_nl_rec_s": 0.0,
    }
    return w, rx, exp, ["ACCEPT/COMMITTED", "QUARANTINE/STALE_TS", "QUARANTINE/STALE_TS"]


def case_G_duplicate_and_replay():
    """Transport duplicate (same statement, new relay statement) within the retry window and an exact replay outside
    it (retry window 5 s): no change of A(t)."""
    w = Micro(params={"retry_window_ms": 5_000})
    g0 = w.genuine("G0", 0, 1000, 50.0)
    g1 = w.genuine("G1", 1, 2000, 51.0, "G0")
    m = json.loads(g0)
    from pbti.envelope import pbti_wire as _pw
    from pbti.crypto import ub64u
    dup = _pw(m["obs"], ub64u(m["osig"]), WID, "wk:gw1:1", w.wsk, 1400, "live")
    rx = [w.rx(g0, 1100), w.rx(dup, 1500, "legit-dup"), w.rx(g1, 2100), w.rx(g0, 20_000, "replay-exact")]
    exp = {
        "nonlegit_auth": 0, "legit_missing": 0, "dup_auth": 0,
        "tm_wh_rec_s": 0.2, "W": 0.1, "tm_avail_1s": 1.0, "tm_transitions": 2,
        "tm_nl_rec_s": 0.0, "tm_zero_flips": 0,
    }
    return w, rx, exp, ["ACCEPT/COMMITTED", "DUPLICATE/RETRY", "ACCEPT/COMMITTED", "DUPLICATE/SUSPECTED_REPLAY"]


def case_H_suppressed_message():
    """G1 accepted by the gateway at 2 s and dropped by the broker (acked, discarded); G2 still commits."""
    w = Micro()
    g0 = w.genuine("G0", 0, 1000, 50.0)
    w.genuine("G1", 1, 2000, 51.0, "G0")
    g2 = w.genuine("G2", 2, 3000, 52.0, "G1")
    rx = [w.rx(g0, 1100), w.rx(g2, 3100)]
    exp = {
        "legit_missing": 1, "legit_quarantined": 0, "legit_lost_unrecoverable": 1,
        "tm_wh_rec_s": 28.2, "W": 9.4, "tm_never_avail": 1, "tm_avail_5s": 2 / 3,
        "tm_first_km_p50_s": 0.1, "tm_first_km_p90_s": None, "tm_nl_rec_s": 0.0, "nonlegit_auth": 0,
    }
    return w, rx, exp, ["ACCEPT/COMMITTED", "ACCEPT/COMMITTED"]


def case_I_taint_after_revocation():
    """G0@1.1s, G1@2.1s, G2@3.1s commit; F3 (stolen key, valid links)@4.1s commits; revocation of dk:d1:1 at
    t_rev = 8 s with t_comp = 2 s taints every commit at or after 2 s (G1, G2, F3) at the 8 s tick."""
    w = Micro()
    g0 = w.genuine("G0", 0, 1000, 50.0)
    g1 = w.genuine("G1", 1, 2000, 51.0, "G0")
    g2 = w.genuine("G2", 2, 3000, 52.0, "G1")
    f3 = w.forged("F3", 3, 4000, 99.0, "G2")
    w.revoke(8_000, 2_000)
    rx = [w.rx(g0, 1100), w.rx(g1, 2100), w.rx(g2, 3100), w.rx(f3, 4100, "stolenkey")]
    exp = {
        "nonlegit_auth": 0, "legit_missing": 2, "taint_events": 3,
        # withheld: G0 100; G1 (28000)-(8000-2100) = 22100; G2 (27000)-(8000-3100) = 22100 -> 44300 ms
        "tm_wh_rec_s": 44.3, "W": 44.3 / 3,
        "tm_nl_rec_s": 3.9,                           # F3 [4100, 8000)
        "tm_nl_pairs_ever": 1, "tm_nl_auth_end": 0,
        "tm_avail_1s": 1.0, "tm_never_avail": 0, "tm_withdrawn": 2, "tm_withdrawn_end": 2,
        "tm_nl_contained": 1, "tm_nl_contained_undirected": 0, "tm_contain_lat_max_s": 0.0,
        "tm_transitions": 7,
    }
    return w, rx, exp, ["ACCEPT/COMMITTED"] * 4


def case_J_deadline_boundaries():
    """First availability exactly 1000, 1001, 5000 and 5001 ms after production (and the 5 s alert deadline:
    nominal 50 degC, all four observations 53.x degC > 52.5)."""
    w = Micro(nominal=50.0)
    g0 = w.genuine("G0", 0, 1000, 53.0)
    g1 = w.genuine("G1", 1, 2000, 53.1, "G0")
    g2 = w.genuine("G2", 2, 3000, 53.2, "G1")
    g3 = w.genuine("G3", 3, 4000, 53.3, "G2")
    rx = [w.rx(g0, 2000), w.rx(g1, 3001), w.rx(g2, 8000), w.rx(g3, 9001)]
    exp = {
        "tm_avail_1s": 0.25,                          # only ft = 1000 (inclusive); 1001 excluded
        "tm_avail_5s": 0.75,                          # 1000, 1001, 5000 (inclusive); 5001 excluded
        "tm_avail_30s": 1.0, "tm_avail_60s": 1.0,
        "tm_wh_rec_s": 12.002, "W": 12.002 / 4,       # 1000 + 1001 + 5000 + 5001
        # KM events 1000,1001,5000,5001: F = .25,.5,.75,1 -> p50 1.001 s, p90 = p99 = 5.001 s
        "tm_first_km_p50_s": 1.001, "tm_first_km_p90_s": 5.001, "tm_first_km_p99_s": 5.001,
        "tm_alert_true": 4, "tm_alert_missed": 1,     # 5001 ms > 5 s deadline; 5000 ms is in time
    }
    return w, rx, exp, ["ACCEPT/COMMITTED"] * 4


def case_K_genuine_zero_duration():
    """G1@2100 commits and F1@2100 (same millisecond) contests it: zero-duration availability is neither
    availability nor a withdrawal."""
    w = Micro()
    g0 = w.genuine("G0", 0, 1000, 50.0)
    g1 = w.genuine("G1", 1, 2000, 51.0, "G0")
    f1 = w.forged("F1", 1, 2000, 99.0, "G0")
    g2 = w.genuine("G2", 2, 3000, 52.0, "G1")
    rx = [w.rx(g0, 1100), w.rx(g1, 2100), w.rx(f1, 2100, "equivocation"), w.rx(g2, 3100)]
    exp = {
        "tm_zero_flips": 1, "tm_never_avail": 1, "tm_withdrawn": 0, "tm_avail_5s": 2 / 3,
        "tm_wh_rec_s": 28.2, "W": 9.4, "legit_missing": 1, "tm_nl_rec_s": 0.0,
    }
    return w, rx, exp, ["ACCEPT/COMMITTED", "ACCEPT/COMMITTED", "CONFLICT/EQUIVOCATION", "ACCEPT/COMMITTED"]


def case_L_drain_phase():
    """Production 0-20 s, drain 20-30 s. G1 (prod 19 s) commits in the drain at 25 s; G2 (prod 19.5 s) commits
    exactly at T_end; G3 (prod 19.8 s, accepted) is still in transit at T_end; forged F4 (seq 4, links to G3)
    commits at 28 s and is still authoritative at T_end."""
    w = Micro()
    g0 = w.genuine("G0", 0, 1000, 50.0)
    g1 = w.genuine("G1", 1, 19_000, 51.0, "G0")
    g2 = w.genuine("G2", 2, 19_500, 52.0, "G1")
    w.genuine("G3", 3, 19_800, 53.0, "G2")
    f4 = w.forged("F4", 4, 19_900, 99.0, "G3")
    rx = [w.rx(g0, 1100), w.rx(g1, 25_000), w.rx(f4, 28_000, "forgery"), w.rx(g2, 30_000)]
    exp = {
        "nonlegit_auth": 1,                           # F4 authoritative at the end
        "legit_missing": 1,                           # G3; G2 IS authoritative at T_end (final state)
        "tm_nl_rec_s": 2.0, "tm_nl_auth_end": 1,      # F4 [28000, 30000)
        # withheld: G0 100; G1 25000-19000 = 6000; G2 zero-length at T_end -> 30000-19500 = 10500; G3 10200
        "tm_wh_rec_s": 26.8, "W": 6.7,
        "tm_avail_5s": 0.25, "tm_avail_30s": 0.5,
        "tm_never_avail": 2,                          # G2 (zero-length availability at T_end) and G3
        "tm_zero_flips": 1,
        # KM: (100,e),(6000,e),(10200,c),(10500,c): F(100)=.25, F(6000)=1-(3/4)(2/3)=.5 -> p50 = 6 s
        "tm_first_km_p50_s": 6.0, "tm_first_km_p90_s": None,
        # windows: (a1,0) ideal {G0} = final -> exact; (a1,10 s) ideal {G1,G2,G3}, final {G1,G2,F4} -> corrupt (F4);
        # current value: highest (ep,seq) authoritative = F4, latest legitimate = G3 -> wrong
        "win_total": 2, "win_exact": 1, "win_corrupt": 1, "win_incomplete": 0, "cv_correct": 0,
    }
    return w, rx, exp, ["ACCEPT/COMMITTED"] * 4


def case_M_forgery_under_genuine_identity_retained():
    """Gap-fill forgery F1 with no successor ever: F1 stays authoritative under G1's identity to the end. It must
    count as non-legitimate (O1, NLX) and never as availability of G1."""
    w = Micro()
    g0 = w.genuine("G0", 0, 1000, 50.0)
    w.genuine("G1", 1, 2000, 51.0, "G0")            # suppressed
    f1 = w.forged("F1", 1, 2000, 99.0, "G0")
    rx = [w.rx(g0, 1100), w.rx(f1, 2100, "gapfill")]
    exp = {
        "nonlegit_auth": 1, "legit_missing": 1,
        "tm_nl_rec_s": 27.9, "tm_nl_auth_end": 1,     # 30000 - 2100
        "tm_wh_rec_s": 28.1, "W": 14.05, "tm_never_avail": 1, "tm_avail_5s": 0.5,
        # window (a1,0): ideal {G0,G1}, final {G0,F1} -> corrupt; current value F1 (seq 1) instead of G1 -> wrong
        "win_total": 1, "win_corrupt": 1, "win_exact": 0, "cv_correct": 0,
    }
    return w, rx, exp, ["ACCEPT/COMMITTED", "ACCEPT/COMMITTED"]


def case_N_relabelled_genuine_content():
    """Definitional probe: the genuine content of G1 re-signed with the stolen key under another identity (seq 5).
    Content-based O1 calls it legitimate (a duplicate); pair-based NLX calls it non-legitimate."""
    w = Micro()
    g0 = w.genuine("G0", 0, 1000, 50.0)
    g1 = w.genuine("G1", 1, 2000, 51.0, "G0")
    x = w.forged("X", 5, 2000, 51.0, None)           # same (did, aid, ts, sch, payload) as G1, identity seq 5
    rx = [w.rx(g0, 1100), w.rx(g1, 2100), w.rx(x, 3100, "relabel")]
    exp = {
        "nonlegit_auth": 0,                           # content matches a legitimate observation
        "dup_auth": 1,                                # two authoritative copies of G1's content
        "legit_missing": 0,
        "tm_nl_rec_s": 26.9, "tm_nl_auth_end": 1,     # pair (seq5, ck(G1)) authoritative [3100, 30000)
    }
    return w, rx, exp, ["ACCEPT/COMMITTED"] * 3


def case_O_pbti_sh_provisional_to_end():
    """PBTI-SH (no timeout): F1 contests slot 1 -> feed suspect; G2 is committed but uncorroborated -> provisional
    (withheld) to the end. Oracle classification of the withheld-but-retained G2."""
    w = Micro(system="PBTI-SH")
    g0 = w.genuine("G0", 0, 1000, 50.0)
    g1 = w.genuine("G1", 1, 2000, 51.0, "G0")
    f1 = w.forged("F1", 1, 2000, 99.0, "G0")
    g2 = w.genuine("G2", 2, 3000, 52.0, "G1")
    rx = [w.rx(g0, 1100), w.rx(g1, 2100), w.rx(f1, 2600, "equivocation"), w.rx(g2, 3100)]
    exp = {
        "nonlegit_auth": 0, "legit_missing": 2,       # G1 contested, G2 provisional
        "tm_wh_rec_s": 54.6, "W": 18.2,               # 100 + 27500 + 27000
        "tm_never_avail": 1, "tm_withdrawn": 1,
        # by the stated definition G2 is retained and recoverable (a corroborating successor releases it)
        "legit_quarantined": 1, "legit_lost_unrecoverable": 1,
    }
    return w, rx, exp, ["ACCEPT/COMMITTED", "ACCEPT/COMMITTED", "CONFLICT/EQUIVOCATION", "ACCEPT/COMMITTED"]


CASES = [case_A_forged_and_genuine_share_identity, case_B_front_running_same_ms_zero_flip_of_forgery,
         case_C_brief_forgery_withdrawn_by_successor, case_D_quarantine_then_release, case_E_b5_hold_then_release,
         case_E2_b5_rehold_after_release, case_F_never_released_censoring, case_G_duplicate_and_replay,
         case_H_suppressed_message, case_I_taint_after_revocation, case_J_deadline_boundaries,
         case_K_genuine_zero_duration, case_L_drain_phase, case_M_forgery_under_genuine_identity_retained,
         case_N_relabelled_genuine_content, case_O_pbti_sh_provisional_to_end]


def run_all():
    rows = []
    for fn in CASES:
        w, rx, exp, exp_rx = fn()
        repo, ref = w.finish()
        rows.append({"case": fn.__name__, "field": "receipts", "expected": exp_rx, "repo": rx, "ref": None,
                     "match_repo": rx == exp_rx, "match_ref": None})
        for f, e in exp.items():
            got = repo.get(f)
            rk = RMAP.get(f)
            if f == "tm_transitions":
                rv = len(w.poller.trans_call)
            elif f == "tm_end_state_matches_authoritative":
                rv = None
            else:
                rv = ref.get(rk) if rk else None
            rows.append({"case": fn.__name__, "field": f, "expected": e, "repo": got, "ref": rv,
                         "match_repo": _eq(e, got), "match_ref": (None if rk is None and f != "tm_transitions"
                                                                  else _eq(e, rv))})
        # reference pair-based variants, for the report
        rows.append({"case": fn.__name__, "field": "ref:O1_pair/O2_pair", "expected": None, "repo": None,
                     "ref": (ref["O1_pair"], ref["O2_pair"]), "match_repo": None, "match_ref": None})
    return rows


if __name__ == "__main__":
    rows = run_all()
    out = "/home/claude/PBTI_v7/results/oracle_audit/hand_cases.json"
    json.dump(rows, open(out, "w"), indent=1, default=str)
    for r in rows:
        flag = "" if r["match_repo"] in (True, None) and r["match_ref"] in (True, None) else "   <== MISMATCH"
        print(f"{r['case'][:44]:44s} {r['field']:34s} exp={r['expected']!s:24.24s} repo={r['repo']!s:24.24s} "
              f"ref={r['ref']!s:20.20s}{flag}")
    bad = [r for r in rows if r["match_repo"] is False or r["match_ref"] is False]
    print(f"\n{len(rows)} checks, {len(bad)} mismatches")
