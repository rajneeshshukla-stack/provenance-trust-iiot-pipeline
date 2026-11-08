"""Unit tests of the B5 reference model.  Every expectation below was derived by hand from the
specification (see the comments), not by running the model."""
import itertools
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from refmodel import Params, Stmt, run  # noqa: E402

D = "d1"


def g(seq, t, ep=1, did=D, q=None):
    """Genuine statement: digest g<seq>, prev g<seq-1>."""
    return Stmt(t, did, ep, seq, f"{did}e{ep}g{seq}", None if seq == 0 else f"{did}e{ep}g{seq-1}", q)


def f(seq, t, prev_name, ep=1, did=D, tag="f"):
    """Forged/alternative statement with digest f<seq> and an explicit prev name (None for seq 0)."""
    prev = None if prev_name is None else f"{did}e{ep}{prev_name}"
    return Stmt(t, did, ep, seq, f"{did}e{ep}{tag}{seq}", prev)


def K(name, seq, ep=1, did=D):
    return ((did, ep, seq), f"{did}e{ep}{name}")


def auth_names(res):
    """Names (g3, f2, ...) of the authoritative statements of feed (d1, 1), ordered by sequence number."""
    out = [(e[2], cd.split("e1", 1)[1]) for (e, cd) in res["authoritative"] if cd.startswith(D + "e1")]
    return [n for _, n in sorted(out)]


# ---------------------------------------------------------------------------------------------------
def test_clean_chain_all_authoritative_no_holds():
    s = [g(i, 1000 * (i + 1)) for i in range(4)]
    r = run(s, Params.hist(), t_end=100_000)
    assert auth_names(r) == ["g0", "g1", "g2", "g3"]
    assert r["fork_events"] == [] and r["hold_events"] == [] and r["releases"] == []
    assert [x[0] for x in r["timeline"]] == [1000, 2000, 3000, 4000]


def test_exact_duplicate_changes_nothing():
    s = [g(0, 1000), g(1, 2000), g(1, 2500), g(2, 3000)]
    r = run(s, Params.hist(), t_end=100_000)
    assert [d[3] for d in r["dispositions"]] == ["ACCEPT", "ACCEPT", "DUPLICATE", "ACCEPT"]
    assert auth_names(r) == ["g0", "g1", "g2"] and r["pending"] == []


def test_equivocation_forged_second_hist():
    # f2 at 3.5 s: F1 -> fork at 2, g2 and f2 held; g3..g5 held on arrival.  First tick with all cases
    # older than 60 s is 70 s: g2,f2 rejected (two digests), g3,g4 successor-corroborated, g5
    # predecessor-corroborated by g4 released earlier in the same tick; feed resumes at 70 s.
    s = [g(0, 1000), g(1, 2000), g(2, 3000), f(2, 3500, "g1"), g(3, 4000), g(4, 5000), g(5, 6000)]
    legit = [K(f"g{i}", i) for i in range(6)]
    r = run(s, Params.hist(), t_end=100_000, legit=legit)
    assert auth_names(r) == ["g0", "g1", "g3", "g4", "g5"]
    assert [(t, fp) for t, _, fp, _ in r["fork_events"]] == [(3500, 2)]
    assert [(t, e[2]) for t, e, _ in r["hold_events"]] == [(3500, 2), (3500, 2), (4000, 3), (5000, 4), (6000, 5)]
    assert sorted((t, e[2]) for t, e, _, _ in r["releases"]) == [(70000, 3), (70000, 4), (70000, 5)]
    assert sorted((t, e[2]) for t, e, _, _ in r["rejections"]) == [(70000, 2), (70000, 2)]
    assert [t for t, _ in r["resumes"]] == [70000]
    assert r["W_ms_total"] == 96500 + 66000 + 65000 + 64000
    assert r["nlx_ms_total"] == 0
    assert r["legit_missing"] == [K("g2", 2)]


def test_equivocation_forged_first_hist():
    # f2 accepted at 2.5 s, g2 at 3 s -> fork at 2 (f2 loses authority).  Exposure of f2 = 0.5 s.
    s = [g(0, 1000), g(1, 2000), f(2, 2500, "g1"), g(2, 3000), g(3, 4000), g(4, 5000)]
    legit = [K(f"g{i}", i) for i in range(5)]
    r = run(s, Params.hist(), t_end=100_000, legit=legit)
    assert auth_names(r) == ["g0", "g1", "g3", "g4"]
    assert r["nlx_ms_total"] == 500
    assert r["W_ms_total"] == 97000 + 66000 + 65000
    assert [t for t, _ in r["resumes"]] == [70000]


def test_gap_fill_forgery_predecessor_suppressed():
    # g2 never delivered; f2 (prev g1) accepted at 3 s; g3 (prev g2) at 4 s contradicts the known
    # predecessor -> F3, fork point 2: f2 and g3 held.  At 70 s f2 rejected (successor-implied g2),
    # g3 released (g4 names it), g4 released (predecessor g3 released just before).
    s = [g(0, 1000), g(1, 2000), f(2, 3000, "g1"), g(3, 4000), g(4, 5000)]
    r = run(s, Params.hist(), t_end=100_000, legit=[K(f"g{i}", i) for i in (0, 1, 3, 4)])
    assert [(t, fp, tr) for t, _, fp, tr in r["fork_events"]] == [(4000, 2, ("F3",))]
    assert auth_names(r) == ["g0", "g1", "g3", "g4"]
    assert r["nlx_ms_total"] == 1000
    assert sorted(e[2] for _, e, _, _ in r["rejections"]) == [2]


def test_successor_first_then_gap_fill():
    # g3 accepted at 4 s (predecessor unknown); f2 at 4.5 s contradicts implied g2 -> F2, fork at 2,
    # g3 retroactively held (authoritative [4.0, 4.5) s and again from 70 s).
    s = [g(0, 1000), g(1, 2000), g(3, 4000), f(2, 4500, "g1"), g(4, 5000)]
    r = run(s, Params.hist(), t_end=100_000)
    assert [(t, fp, tr) for t, _, fp, tr in r["fork_events"]] == [(4500, 2, ("F2",))]
    assert auth_names(r) == ["g0", "g1", "g3", "g4"]
    assert r["intervals"][K("g3", 3)] == [(4000, 4500), (70000, 100000)]
    assert [(t, e[2]) for t, e, _ in r["hold_events"]] == [(4500, 2), (4500, 3), (5000, 4)]


def test_b5_strict_freezes_feed():
    s = [g(0, 1000), g(1, 2000), g(2, 3000), f(2, 3500, "g1"), g(3, 4000), g(4, 5000), g(5, 6000)]
    r = run(s, Params.strict(), t_end=100_000)
    assert auth_names(r) == ["g0", "g1"]
    assert r["releases"] == [] and r["resumes"] == [] and len(r["pending"]) == 5
    assert len(r["held_at_end"]) == 5


def test_b5_strict_new_epoch_is_a_new_feed():
    s = [g(0, 1000), g(1, 2000), f(1, 2500, "g0"), g(2, 3000),
         g(0, 4000, ep=2), g(1, 5000, ep=2)]
    r = run(s, Params.strict(), t_end=100_000)
    assert sorted(k for k in r["authoritative"]) == sorted([K("g0", 0), ((D, 2, 0), f"{D}e2g0"),
                                                            ((D, 2, 1), f"{D}e2g1")])


def test_defer_r0_c1_resume_within_tick():
    # Tick at 3 s: g2,f2 contradicted -> rejected; g3 released (g4 names it); g4 released through its
    # predecessor g3 (same tick, decided earlier); no pending case -> resume at 3 s.
    s = [g(0, 100), g(1, 1100), g(2, 2100), f(2, 2200, "g1"), g(3, 2300), g(4, 2400)]
    r = run(s, Params.defer(0, 1), t_end=10_000)
    assert auth_names(r) == ["g0", "g1", "g3", "g4"]
    assert [t for t, _ in r["resumes"]] == [3000]
    assert sorted((t, e[2]) for t, e, _, _ in r["releases"]) == [(3000, 3), (3000, 4)]


def test_defer_r0_after_resume_later_arrivals_accepted():
    s = [g(0, 100), g(1, 1100), g(2, 2100), f(2, 2300, "g1"), g(3, 3100), g(4, 4100)]
    r = run(s, Params.defer(0, 1), t_end=10_000)
    assert [t for t, _ in r["resumes"]] == [3000]
    assert [d[3] for d in r["dispositions"]][-2:] == ["ACCEPT", "ACCEPT"]
    assert auth_names(r) == ["g0", "g1", "g3", "g4"]


def test_oneshot_rejects_uncorroborated_last_observation():
    # fork at 1; g2 has no successor and its predecessor g1 is rejected -> one-shot rejects g2.
    s = [g(0, 1000), g(1, 2000), f(1, 2500, "g0"), g(2, 3000)]
    r = run(s, Params.hist(), t_end=100_000)
    assert auth_names(r) == ["g0"]
    assert sorted(e[2] for _, e, _, _ in r["rejections"]) == [1, 1, 2]
    assert [t for t, _ in r["resumes"]] == [70000]


def test_defer_keeps_uncorroborated_case_pending_then_releases():
    s = [g(0, 1000), g(1, 2000), f(1, 2500, "g0"), g(2, 3000)]
    r = run(s, Params.defer(60, 10), t_end=100_000)
    assert auth_names(r) == ["g0"] and r["resumes"] == []
    assert [(k, e[2]) for k, e, _, _ in r["pending"]] == [("FEED_FORK_HOLD", 2)]
    # a successor arriving later corroborates g2 (released at the next tick, 90 s); g3 (opened 80 s)
    # is released at 140 s through its released predecessor g2
    r2 = run(s + [g(3, 80_000)], Params.defer(60, 10), t_end=200_000)
    assert sorted((t, e[2]) for t, e, _, _ in r2["releases"]) == [(90000, 2), (140000, 3)]
    assert auth_names(r2) == ["g0", "g2", "g3"]
    assert [t for t, _ in r2["resumes"]] == [140000]


def test_defer_release_time_of_late_corroborated_case():
    # Pinpoint the previous test: g2 (opened 3 s) is reviewed at 70 s (deferred) and released at the
    # first tick after g3's admission at 80 s, i.e. 80 s if the tick precedes the arrival -> 90 s.
    s = [g(0, 1000), g(1, 2000), f(1, 2500, "g0"), g(2, 3000), g(3, 80_000)]
    r = run(s, Params.defer(60, 10), t_end=200_000)
    rel = sorted((t, e[2]) for t, e, _, _ in r["releases"])
    assert rel == [(90000, 2), (140000, 3)]


def test_event_mode_equivocation_resumes_immediately():
    s = [g(0, 1000), g(1, 2000), g(2, 3000), f(2, 3500, "g1"), g(3, 4000), g(4, 5000)]
    r = run(s, Params.event(), t_end=10_000)
    assert auth_names(r) == ["g0", "g1", "g3", "g4"]
    assert [t for t, _ in r["resumes"]] == [3500]
    assert len(r["hold_events"]) == 2
    assert [d[3] for d in r["dispositions"]][-2:] == ["ACCEPT", "ACCEPT"]


def test_event_mode_gap_fill_successor_deferred_then_released():
    # g3 contradicts f2 (fork at 2); f2 rejected at once (implied g2); g3 is neither corroborated nor
    # contradicted (its own prev is predecessor evidence) -> pending; g4 at 5 s corroborates g3, g4
    # is released through g3 in the cascade; resume at 5 s.
    s = [g(0, 1000), g(1, 2000), f(2, 3000, "g1"), g(3, 4000), g(4, 5000)]
    r = run(s, Params.event(), t_end=10_000)
    assert auth_names(r) == ["g0", "g1", "g3", "g4"]
    assert sorted((t, e[2]) for t, e, _, _ in r["releases"]) == [(5000, 3), (5000, 4)]
    assert [(t, e[2]) for t, e, _, _ in r["rejections"]] == [(4000, 2)]
    assert [t for t, _ in r["resumes"]] == [5000]


def test_rehold_after_resume_counts_new_feed_hold():
    s = [g(0, 1000), g(1, 2000), g(2, 3000), f(2, 3500, "g1"), g(3, 4000), g(4, 5000),
         f(4, 6000, "g3")]
    r = run(s, Params.event(), t_end=10_000)
    assert [t for t, _, _ in r["feed_holds"]] == [3500, 6000]
    assert [t for t, _ in r["resumes"]] == [3500, 6000]
    assert len(r["hold_events"]) == 4
    assert auth_names(r) == ["g0", "g1", "g3"]


def test_fork_point_moves_down_and_rehold_counts():
    s = [g(i, 1000 * (i + 1)) for i in range(10)]
    s += [f(5, 10_500, "g4"), g(10, 11_000), f(3, 12_000, "g2")]
    r = run(s, Params.hist(), t_end=100_000)
    assert [(t, fp) for t, _, fp, _ in r["fork_events"]] == [(10500, 5), (12000, 3)]
    assert len(r["feed_holds"]) == 1 and len(r["hold_events"]) == 10
    assert auth_names(r) == ["g0", "g1", "g2", "g4", "g6", "g7", "g8", "g9", "g10"]
    assert all(t == 80000 for t, _, _, _ in r["releases"]) and len(r["releases"]) == 6
    assert [t for t, _ in r["resumes"]] == [80000]


def test_released_observation_loses_authority_on_later_conflict():
    s = [g(0, 1000), g(1, 2000), f(1, 2500, "g0"), g(2, 3000), g(3, 4000), g(4, 65_000),
         f(2, 75_000, "g1")]
    r = run(s, Params.hist(), t_end=200_000)
    assert r["intervals"][K("g2", 2)] == [(70000, 75000)]
    assert r["intervals"][K("g3", 3)] == [(70000, 75000), (140000, 200000)]
    rej = sorted((t, e[2]) for t, e, _, _ in r["rejections"])
    assert rej == [(70000, 1), (70000, 1), (130000, 4), (140000, 2), (140000, 2)]
    assert auth_names(r) == ["g0", "g3"]
    assert [t for t, _ in r["resumes"]] == [140000]
    # re-hold counted again: g1,f1,g2,g3,g4 (5) + g2,f2,g3 (3)
    assert len(r["hold_events"]) == 8


def test_stale_backlog_released_in_order():
    s = [g(0, 1000), g(1, 2000), g(2, 3000),
         g(3, 10_000, q="STALE_TS"), g(4, 10_001, q="STALE_TS"), g(5, 10_002, q="STALE_TS"),
         g(6, 10_003)]
    r = run(s, Params.hist(), t_end=100_000)
    assert sorted((t, e[2]) for t, e, _, _ in r["releases"]) == [(70000, 3), (80000, 4), (80000, 5)]
    assert auth_names(r) == ["g0", "g1", "g2", "g3", "g4", "g5", "g6"]
    assert r["fork_events"] == []


def test_stale_seq0_needs_successor():
    r = run([g(0, 1000, q="STALE_TS")], Params.hist(), t_end=100_000)
    assert r["authoritative"] == [] and [e[2] for _, e, _, _ in r["rejections"]] == [0]
    r = run([g(0, 1000, q="STALE_TS")], Params.defer(60, 10), t_end=100_000)
    assert r["authoritative"] == [] and len(r["pending"]) == 1
    r = run([g(0, 1000, q="STALE_TS"), g(1, 2000)], Params.hist(), t_end=100_000)
    assert auth_names(r) == ["g0", "g1"]


def test_stale_release_into_held_feed_is_held():
    # Feed forked at 2.  Tick 70 s (creation order g2,f2,g3,g4,q(g5),g6,g7): g2,f2 rejected; g3
    # released (g4 names it); g4 released through g3; stale g5 corroborated by g6's link -> released,
    # history re-run puts it on hold (new case opened at 70 s); g6 corroborated by g7; g7 through g6.
    # The new hold case of g5 is released at 130 s (g6 names it); then the feed resumes.
    s = [g(0, 1000), g(1, 2000), g(2, 3000), f(2, 3500, "g1"), g(3, 4000), g(4, 5000),
         g(5, 6000, q="STALE_TS"), g(6, 7000), g(7, 8000)]
    r = run(s, Params.hist(), t_end=200_000)
    assert [(t, e[2]) for t, e, _ in r["hold_events"]] == [(3500, 2), (3500, 2), (4000, 3), (5000, 4),
                                                          (7000, 6), (8000, 7), (70000, 5)]
    rel = sorted((t, e[2], k) for t, e, _, k in r["releases"])
    assert rel == [(70000, 3, "FEED_FORK_HOLD"), (70000, 4, "FEED_FORK_HOLD"), (70000, 5, "STALE_TS"),
                   (70000, 6, "FEED_FORK_HOLD"), (70000, 7, "FEED_FORK_HOLD"),
                   (130000, 5, "FEED_FORK_HOLD")]
    assert [t for t, _ in r["resumes"]] == [130000]
    assert auth_names(r) == ["g0", "g1", "g3", "g4", "g5", "g6", "g7"]


def test_oneshot_rejects_successor_of_quarantined_observation():
    # Same fork, but the stale g4 is the last observation: at 70 s g3 has no admitted successor
    # (g4 is only a quarantine case) and its predecessor g2 is rejected -> g3 rejected; then the
    # quarantine case g4 has no authoritative predecessor -> rejected.
    s = [g(0, 1000), g(1, 2000), g(2, 3000), f(2, 3500, "g1"), g(3, 4000), g(4, 5000, q="STALE_TS")]
    r = run(s, Params.hist(), t_end=200_000)
    assert sorted((t, e[2], k) for t, e, _, k in r["rejections"]) == [
        (70000, 2, "FEED_FORK_HOLD"), (70000, 2, "FEED_FORK_HOLD"), (70000, 3, "FEED_FORK_HOLD"),
        (70000, 4, "STALE_TS")]
    assert auth_names(r) == ["g0", "g1"]


def test_duplicates_of_held_and_rejected_change_nothing():
    s = [g(0, 1000), g(1, 2000), g(2, 3000), f(2, 3500, "g1"), g(3, 4000), g(3, 4500),
         g(4, 5000), g(2, 80_000)]
    r = run(s, Params.hist(), t_end=100_000)
    assert [d[3] for d in r["dispositions"]] == ["ACCEPT", "ACCEPT", "ACCEPT", "HELD_FORK", "HELD",
                                                 "DUPLICATE", "HELD", "DUPLICATE"]
    assert len(r["hold_events"]) == 4 and auth_names(r) == ["g0", "g1", "g3", "g4"]
    assert len([c for c in r["pending"]]) == 0


def test_multi_device_isolation():
    s = [g(0, 1000), g(1, 2000), f(1, 2500, "g0"), g(2, 3000),
         g(0, 1000, did="d2"), g(1, 2000, did="d2"), g(2, 3000, did="d2")]
    r = run(s, Params.strict(), t_end=100_000)
    assert sorted(cd for _, cd in r["authoritative"]) == ["d1e1g0", "d2e1g0", "d2e1g1", "d2e1g2"]


def test_tick_before_arrival_at_equal_time():
    # f2 arrives exactly at the 2 s tick: the tick runs first, so the cases are reviewed at 3 s.
    s = [g(0, 100), g(1, 1100), g(2, 1500), f(2, 2000, "g1")]
    r = run(s, Params.defer(0, 1), t_end=5_000)
    assert sorted(t for t, _, _, _ in r["rejections"]) == [3000, 3000]


def test_b5s_final_state_independent_of_delivery_order():
    base = [g(0, 0), g(1, 0), g(2, 0), f(2, 0, "g1"), g(3, 0), f(4, 0, "g3x"), g(4, 0)]
    results = set()
    for perm in itertools.permutations(base):
        s = [Stmt(1000 * (i + 1), x.did, x.ep, x.seq, x.digest, x.prev) for i, x in enumerate(perm)]
        r = run(s, Params.strict(), t_end=100_000)
        results.add(tuple(r["authoritative"]))
    assert results == {(K("g0", 0), K("g1", 1))}
