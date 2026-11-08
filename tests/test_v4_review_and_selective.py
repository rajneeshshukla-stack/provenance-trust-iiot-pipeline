"""V4: reviewer decision rules (one-shot vs deferring), event-driven review completeness, and the PBTI-SH selective
evidence-gated hold rule (src/pbti/selective.py). Expected outcomes are written out by hand from the rule text."""
from pbti.audit import audit_pbti
from pbti.b5 import B5FeedLevel
from pbti.registry import COMMITTED, CONTESTED
from pbti.review import AutoReviewer, contradicted, corroborated
from pbti.selective import SelectiveHoldVerifier
from pbti.verifier import ACCEPT, CONFLICT, QUARANTINE

from test_v3_review_b5 import RID, chain, env, msg, wd_of


def auth(v):
    return {k for k, _ in v.authoritative()}


def reviewer(rsk, rule, age=0):
    return AutoReviewer(RID, "rk:auto:1", rsk, min_age_ms=age, rule=rule)


# ------------------------------------------------------------------ decision rules
def _b5_with_held_tail():
    """B5: fork at seq 1 (two contents); seq 2 then arrives and is held; its successor has not arrived yet."""
    v, trust, dsk, wsk, rsk, _ = env(cls=B5FeedLevel)
    c = chain(dsk, wsk, 4)
    v.ingest(c[0][0], 1_000)
    v.ingest(c[1][0], 2_000)
    alt, _ = msg(dsk, wsk, 1, c[0][1], 2_000, val=9.0)
    assert v.ingest(alt, 2_050).disp == CONFLICT                 # fork at seq 1
    assert v.ingest(c[2][0], 3_000).disp == QUARANTINE           # FEED_FORK_HOLD
    return v, dsk, wsk, rsk, c


def test_oneshot_rejects_uncorroborated_case_for_good():
    v, dsk, wsk, rsk, c = _b5_with_held_tail()
    wd = wd_of(c[2][0])
    reviewer(rsk, "oneshot").run(v, 3_100)                       # successor of seq 2 has not arrived
    assert v.qcases[wd]["state"] == "REJECTED"
    v.ingest(c[3][0], 4_000)                                     # it arrives later: too late for the one-shot rule
    reviewer(rsk, "oneshot").run(v, 4_100)
    assert ("d1", 0, 2) not in auth(v)


def test_defer_waits_for_corroboration_then_releases():
    v, dsk, wsk, rsk, c = _b5_with_held_tail()
    wd = wd_of(c[2][0])
    rv = reviewer(rsk, "defer")
    rv.run(v, 3_100)
    assert v.qcases[wd]["state"] == "QUARANTINED" and rv.deferrals == 1   # neither corroborated nor contradicted
    v.ingest(c[3][0], 4_000)                                     # successor names seq 2's digest: corroboration
    rv.run(v, 4_100)
    assert v.qcases[wd]["state"] == "RELEASED" and ("d1", 0, 2) in auth(v)


def test_defer_rejects_contradicted_case():
    v, dsk, wsk, rsk, c = _b5_with_held_tail()
    wd = wd_of(c[2][0])
    snap = v.review_snapshot(wd)
    assert not corroborated(snap) and not contradicted(snap)
    other, _ = msg(dsk, wsk, 2, c[1][1], 3_000, val=7.0)         # a second content for seq 2
    v.ingest(other, 3_200)
    assert contradicted(v.review_snapshot(wd))
    reviewer(rsk, "defer").run(v, 3_300)
    assert v.qcases[wd]["state"] == "REJECTED"


def test_event_review_leaves_no_corroborated_case_pending():
    """World-level completeness check: in event mode, after every receipt no eligible case is corroborated."""
    from pbti.scenarios import build
    w = build("S08_seq_reuse_bug", "B5", 1, review_mode="event", review_delay_ms=0, review_rule="defer",
              duration_ms=90_000, drain_ms=30_000)
    orig = w.receive
    bad = []

    def receive(wire, meta, label):
        orig(wire, meta, label)
        for wd in w.reviewer.eligible(w.sys, w.now):
            snap = w.sys.review_snapshot(wd)
            if snap is not None and corroborated(snap):
                bad.append((w.now, wd))
    w.receive = receive
    w.run()
    assert w.sys.holds > 0 and bad == []
    assert audit_pbti(w.sys, replay=True)["pass"]


def test_event_mode_requires_zero_minimum_age():
    import pytest
    from pbti.scenarios import build
    with pytest.raises(ValueError):
        build("S01_normal", "B5", 1, review_mode="event", review_delay_ms=60_000)


# ------------------------------------------------------------------ PBTI-SH
def sh(**kw):
    return env(cls=SelectiveHoldVerifier, **kw)


def test_sh_without_fork_evidence_behaves_like_pbti():
    v, trust, dsk, wsk, rsk, _ = sh()
    c = chain(dsk, wsk, 4)
    for i, (w, _) in enumerate(c):
        assert v.ingest(w, 1_000 * (i + 1)).disp == ACCEPT
    assert auth(v) == {("d1", 0, i) for i in range(4)} and not v.suspect and not v.prov


def test_sh_holds_uncorroborated_until_successor_link():
    v, trust, dsk, wsk, rsk, _ = sh()
    c = chain(dsk, wsk, 5)
    v.ingest(c[0][0], 1_000)
    v.ingest(c[1][0], 2_000)
    alt, _ = msg(dsk, wsk, 1, c[0][1], 2_000, val=9.0)
    assert v.ingest(alt, 2_050).disp == CONFLICT                 # fork evidence: feed (d1, 0) becomes suspect
    assert ("d1", 0) in v.suspect
    assert ("d1", 0, 0) in auth(v)                               # corroborated by seq 1's prev link: stays available
    r = v.ingest(c[2][0], 3_000)
    assert r.disp == ACCEPT and "PROVISIONAL" in r.ann           # committed, but withheld
    assert ("d1", 0, 2) not in auth(v)
    v.ingest(c[3][0], 4_000)                                     # successor names seq 2: released
    assert ("d1", 0, 2) in auth(v) and ("d1", 0, 3) not in auth(v)
    assert v.sh_released == 1


def test_sh_predecessor_match_is_not_enough_and_forgery_stays_withheld():
    """A forged version whose genuine version and successors are suppressed: Rule L alone would commit it."""
    v, trust, dsk, wsk, rsk, _ = sh()
    c = chain(dsk, wsk, 6)
    for i in range(3):
        v.ingest(c[i][0], 1_000 * (i + 1))
    alt, _ = msg(dsk, wsk, 1, c[0][1], 2_000, val=9.0)
    v.ingest(alt, 3_100)                                         # fork at seq 1 -> suspect
    forged, _ = msg(dsk, wsk, 3, c[2][1], 4_000, val=20.0)       # prev copies the genuine predecessor digest
    assert v.ingest(forged, 4_000).disp == ACCEPT                # genuine seq 3, 4 suppressed: no contradiction
    for t in range(5_000, 60_000, 1_000):
        v.advance(t)
    assert ("d1", 0, 3) not in auth(v) and ("d1", 0, 3) in v.prov


def test_sh_retroactive_gate_only_touches_uncorroborated_observations():
    v, trust, dsk, wsk, rsk, _ = sh()
    c = chain(dsk, wsk, 4)
    for i in range(4):
        v.ingest(c[i][0], 1_000 * (i + 1))
    assert auth(v) == {("d1", 0, i) for i in range(4)}
    alt, _ = msg(dsk, wsk, 1, c[0][1], 2_000, val=9.0)
    v.ingest(alt, 5_000)                                         # fork at seq 1 after seq 0-3 were committed
    # seq 1 contested; seq 0 and 2 corroborated by successors; seq 3 (latest, no successor yet) becomes provisional
    assert v.reg.slots[("d1", 0, 1)].state() == CONTESTED
    assert auth(v) == {("d1", 0, 0), ("d1", 0, 2)}
    assert set(v.prov) == {("d1", 0, 3)}


def test_sh_contest_of_provisional_slot_and_timeout_arm():
    v, trust, dsk, wsk, rsk, _ = sh(timeout_ms=5_000)
    c = chain(dsk, wsk, 4)
    v.ingest(c[0][0], 1_000)
    v.ingest(c[1][0], 2_000)
    v.ingest(msg(dsk, wsk, 1, c[0][1], 2_000, val=9.0)[0], 2_050)
    v.ingest(c[2][0], 3_000)                                     # provisional
    assert ("d1", 0, 2) in v.prov
    v.advance(9_000)                                             # timeout arm: released after 5 s if uncontested
    assert ("d1", 0, 2) in auth(v) and v.sh_timeouts == 1
    v2, trust2, dsk2, wsk2, _, _ = sh(timeout_ms=5_000)
    c2 = chain(dsk2, wsk2, 3)
    v2.ingest(c2[0][0], 1_000)
    v2.ingest(c2[1][0], 2_000)
    v2.ingest(msg(dsk2, wsk2, 1, c2[0][1], 2_000, val=9.0)[0], 2_050)
    v2.ingest(c2[2][0], 3_000)
    v2.ingest(msg(dsk2, wsk2, 2, c2[1][1], 3_000, val=8.0)[0], 3_500)   # second content: contested, never released
    v2.advance(20_000)
    assert ("d1", 0, 2) not in auth(v2) and ("d1", 0, 2) not in v2.prov


def test_sh_tainted_provisional_is_never_released():
    v, trust, dsk, wsk, rsk, _ = sh()
    c = chain(dsk, wsk, 4)
    v.ingest(c[0][0], 1_000)
    v.ingest(c[1][0], 2_000)
    v.ingest(msg(dsk, wsk, 1, c[0][1], 2_000, val=9.0)[0], 2_050)
    v.ingest(c[2][0], 3_000)                                     # provisional
    trust.revoke("dk:d1:1", 3_500, 2_500, "test")                # compromise from 2.5 s: seq 2 committed at 3 s
    v.advance(4_000)
    assert v.reg.slots[("d1", 0, 2)].tainted
    v.ingest(c[3][0], 4_100)                                     # successor (revoked key) is refused; nothing released
    assert ("d1", 0, 2) not in auth(v)


def test_sh_derived_data_and_audit_replay():
    v, trust, dsk, wsk, rsk, _ = sh()
    c = chain(dsk, wsk, 5)
    for i in range(3):
        v.ingest(c[i][0], 1_000 * (i + 1))
    v.ingest(msg(dsk, wsk, 1, c[0][1], 2_000, val=9.0)[0], 3_100)
    v.ingest(c[3][0], 4_000)
    v.finalize(10_000)
    members = {k for wk, m in v.proc.win.items() for k in m}
    assert members == auth(v)                                    # provisional observations are not in derived data
    assert audit_pbti(v, replay=True)["pass"]
