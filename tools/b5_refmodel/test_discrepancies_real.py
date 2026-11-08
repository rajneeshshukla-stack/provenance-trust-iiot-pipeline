"""Minimal reproducing streams for every discrepancy between the phase-1 reference model and the real B5
implementation (run against the scratch copy of the repository).  Each test asserts what the real implementation
does and what the phase-1 model (specification reading) does, so the difference is pinned down exactly."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness as H  # noqa: E402
import refmodel as M  # noqa: E402
from gen import SpecBuilder  # noqa: E402


def chain(b, did, n, t_prod=lambda i: 1_000 * (i + 1), ep=0, val0=50):
    names, prev = [], None
    for i in range(n):
        nm = b.stmt(f"{did}/{ep}/{i}/g{i}", did, ep, i, t_prod(i), prev, val0 + i, True)
        names.append(nm)
        prev = nm
    return names


def forge(b, did, seq, ts, prev, ep=0, tag="f"):
    return b.stmt(f"{did}/{ep}/{seq}/{tag}{seq}", did, ep, seq, ts, prev, 900 + seq, False)


def both(b, t_end, P):
    built = H.build(b.spec(t_end, "repro", 0))
    ev = M.schedule(built.model_stmts, P, t_end)
    real = H.run_real(built, P, ev)
    model = H.run_model(built, P, ev)
    return built, real, model


def iv(res, built, name):
    k = (tuple(built.stmt[name][x] for x in ("did", "ep", "seq")), built.cd[name])
    return res["intervals"].get(k, [])


# --------------------------------------------------------------------------------------------- D-ORDER
def test_review_order_identity_vs_creation():
    """Two stale backlog entries arrive 4 ms out of order (g3 before g2), nothing after them is admitted.
    Implementation (identity order): g2 then g3 released in the same tick (90 s: first tick with both cases
    older than 60 s).  Phase-1 model (creation order):
    g3 is reviewed first, its predecessor is not yet authoritative -> one-shot REJECT; g2 released."""
    b = SpecBuilder(["d"], h_max_ms=10_000)
    g = chain(b, "d", 4)
    for nm in g[:2]:
        b.arrive(b.stmts[g.index(nm)]["ts"] + 20, nm)
    b.arrive(20_004, g[3], 0, "buffered")
    b.arrive(20_008, g[2], 0, "buffered")
    built, real, model = both(b, 100_000, M.Params.hist())
    assert iv(real, built, g[3]) == [(90_000, 100_000)] and iv(real, built, g[2]) == [(90_000, 100_000)]
    assert iv(model, built, g[3]) == [] and iv(model, built, g[2]) == [(90_000, 100_000)]
    m2 = H.run_model(built, M.replace(M.Params.hist(), order="identity"))
    assert H.compare(m2, real)["all_core"]


# --------------------------------------------------------------------------------------------- D-REFORK
def test_state_based_refork_reholds_released_observations():
    """Equivocation at seq 1; g2 delayed until after the review released g3, g4 and the feed resumed.
    Implementation: g2's predecessor slot is contested -> new fork at 1 -> g3, g4 re-held (released again
    at 140 s) and g2 held.  Phase-1 model: g2's prev names one of the admitted versions of seq 1 -> no new
    fork evidence -> g2 accepted, g3/g4 stay authoritative."""
    b = SpecBuilder(["d"], h_max_ms=3_600_000)
    g = chain(b, "d", 5)
    f1 = forge(b, "d", 1, 2_000, g[0])
    b.arrive(1_020, g[0]); b.arrive(2_020, g[1]); b.arrive(2_070, f1)
    b.arrive(75_000, g[2]); b.arrive(4_020, g[3]); b.arrive(5_020, g[4])
    built, real, model = both(b, 200_000, M.Params.hist())
    assert iv(real, built, g[3]) == [(70_000, 75_000), (140_000, 200_000)]
    assert iv(real, built, g[2]) == [(140_000, 200_000)]
    assert iv(model, built, g[3]) == [(70_000, 200_000)] and iv(model, built, g[2]) == [(75_000, 200_000)]
    assert real["counters"]["fork_events"] == 2 and len(model["feed_holds"]) == 1
    m2 = H.run_model(built, M.replace(M.Params.hist(), fork_rule="state"))
    assert H.compare(m2, real)["all_core"]


# --------------------------------------------------------------------------------------------- D-NOCASE
def test_contested_slot_without_case_feed_never_resumes():
    """Equivocation at the newest seq 2 (nothing above it): the implementation opens no review case for the
    contested slot, so no decision ever triggers a resume; g4 (seq 4, not adjacent to the contested slot,
    g3 suppressed) arrives much later and is held, then rejected (one-shot, uncorroborated).  Phase-1 model:
    the contested versions are cases, rejected at 70 s, the feed resumes and g4 is accepted at once.
    (The implementation resumes only at 170 s, after rejecting g4.)"""
    b = SpecBuilder(["d"], h_max_ms=3_600_000)
    g = chain(b, "d", 5, t_prod=lambda i: 1_000 * (i + 1) if i < 4 else 100_000)
    f2 = forge(b, "d", 2, 3_000, g[1])
    b.arrive(1_020, g[0]); b.arrive(2_020, g[1]); b.arrive(3_020, g[2]); b.arrive(3_070, f2)
    b.arrive(100_020, g[4])
    built, real, model = both(b, 200_000, M.Params.hist())
    assert real["resumes"] == [(170_000, ("d", 0))] and iv(real, built, g[4]) == []
    assert model["resumes"] == [(70_000, ("d", 0))] and iv(model, built, g[4]) == [(100_020, 200_000)]
    m2 = H.run_model(built, M.replace(M.Params.hist(), contested_cases=False, resume_timing="decision"))
    assert H.compare(m2, real)["all_core"]


# --------------------------------------------------------------------------------------------- D-WIRE (defect)
def test_stale_release_into_held_feed_is_lost():
    """Fork at seq 1; g4 arrives beyond the horizon (STALE_TS case) while the feed is held; g5 names it, g6
    keeps the feed held.  At 80 s the reviewer releases g4: the re-run puts it on FEED_FORK_HOLD, but the hold
    case would have the same wire digest as the STALE_TS case, so none is opened and the STALE_TS case is
    closed RELEASE_FAILED:QUARANTINE/FEED_FORK_HOLD.  g4 stays held with no case: never authoritative.
    Phase-1 model: g4 becomes a FEED_FORK_HOLD case and is released at 140 s."""
    b = SpecBuilder(["d"], h_max_ms=10_000)
    g = chain(b, "d", 7, t_prod=lambda i: 1_000 * (i + 1) if i < 6 else 50_000)
    f1 = forge(b, "d", 1, 2_000, g[0])
    b.arrive(1_020, g[0]); b.arrive(2_020, g[1]); b.arrive(2_070, f1); b.arrive(3_020, g[2])
    b.arrive(4_020, g[3]); b.arrive(20_000, g[4], 0, "buffered"); b.arrive(6_020, g[5]); b.arrive(50_020, g[6])
    built, real, model = both(b, 200_000, M.Params.hist())
    assert real["review_outcomes"].get("RELEASE_FAILED:QUARANTINE/FEED_FORK_HOLD") == 1
    assert iv(real, built, g[4]) == [] and built.legit and len(real["legit_missing"]) == len(model["legit_missing"]) + 1
    assert iv(model, built, g[4]) == [(140_000, 200_000)]
    m2 = H.run_model(built, M.replace(M.Params.hist(), wire_cases=True))
    assert H.compare(m2, real)["all_core"]


def test_stale_duplicate_of_admitted_wire_blocks_hold_case():
    """A byte-identical retransmission of an admitted wire arrives beyond the horizon: it opens a STALE_TS
    case keyed by the same wire digest.  A fork then holds the slot, but b5._fork finds the pending STALE_TS
    case for that wire and opens no FEED_FORK_HOLD case; the STALE_TS release re-run is a DUPLICATE
    (RELEASE_FAILED), so g3 stays held for good.  Phase-1 model: g3 gets a hold case and is released."""
    b = SpecBuilder(["d"], h_max_ms=10_000)
    g = chain(b, "d", 6)
    f1 = forge(b, "d", 1, 15_500, g[0])
    for i, nm in enumerate(g):
        b.arrive(1_000 * (i + 1) + 20, nm)
    b.arrive(15_000, g[3])                                   # stale retransmission of an admitted wire
    b.arrive(16_000, f1)                                     # fresh forgery: fork at 1 holds seq 1.. (g3 too)
    built, real, model = both(b, 200_000, M.Params.hist())
    assert iv(real, built, g[3]) == [(4_020, 16_000)]
    assert iv(model, built, g[3]) == [(4_020, 16_000), (80_000, 200_000)]
    m2 = H.run_model(built, M.replace(M.Params.hist(), wire_cases=True))
    assert H.compare(m2, real)["all_core"]


# --------------------------------------------------------------------------------------------- D-EVENT
def test_event_mode_failed_release_not_reexamined():
    """Event-driven review: fork at 1; g2 and g4 held and pending (no corroboration yet); g3 arrives beyond the
    horizon, its STALE_TS case is corroborated by g4's link and released, but the re-run puts it on hold without
    a case (RELEASE_FAILED, as above).  Its admission added g2's successor link, yet sim.World._event_review
    re-examines only neighbours of RELEASED outcomes, so g2 stays pending for good (no later receipt touches
    seq 1-3); g4 is released only when g5 arrives.  With every other implementation choice kept, a cascade that
    also re-examines the neighbours of the failed release (event_scope="spec") releases g2 at 20 s.  (The
    phase-1 model resumes the feed right after rejecting the contested versions, so g2 and g4 are accepted on
    arrival there.)"""
    b = SpecBuilder(["d"], h_max_ms=10_000)
    g = chain(b, "d", 6, t_prod=lambda i: 1_000 * (i + 1) if i < 5 else 60_000)
    f1 = forge(b, "d", 1, 2_000, g[0])
    b.arrive(1_020, g[0]); b.arrive(2_020, g[1]); b.arrive(2_070, f1); b.arrive(3_020, g[2])
    b.arrive(5_020, g[4]); b.arrive(20_000, g[3], 0, "buffered"); b.arrive(60_020, g[5])
    built, real, model = both(b, 100_000, M.Params.event())
    assert iv(real, built, g[2]) == [] and iv(real, built, g[3]) == [] and iv(real, built, g[4]) == [(60_020, 100_000)]
    assert real["review_outcomes"].get("RELEASE_FAILED:QUARANTINE/FEED_FORK_HOLD") == 1
    m_impl = H.run_model(built, M.Params.event().impl_choices())
    assert H.compare(m_impl, real)["all_core"]
    m_casc = H.run_model(built, M.replace(M.Params.event().impl_choices(), event_scope="spec"))
    assert iv(m_casc, built, g[2]) == [(20_000, 100_000)]
    assert iv(model, built, g[2]) == [(3_020, 100_000)] and iv(model, built, g[4]) == [(5_020, 100_000)]
    assert iv(model, built, g[3]) == [(20_000, 100_000)]


# --------------------------------------------------------------------------------------------- D-COUNT (counter)
def test_hold_counter_counts_an_observation_twice():
    """g2 (prev contradicts the admitted g1') arrives: b5._fork holds g2 (holds += 1) and b5._history counts the
    same hold again (holds += 1): 3 holds for 2 held slots (f1-contested slot 1 and g2)."""
    b = SpecBuilder(["d"], h_max_ms=3_600_000)
    g = chain(b, "d", 3)
    f1 = forge(b, "d", 1, 2_000, g[0])
    b.arrive(1_020, g[0]); b.arrive(2_020, f1); b.arrive(3_020, g[2])
    built, real, model = both(b, 100_000, M.Params.strict())
    assert real["counters"]["holds"] == 3 and len(real["held_identities"]) == 2
    assert len(model["hold_events"]) == 2
