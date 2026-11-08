"""V9 regression tests for the corrected B5 comparator (src/pbti/b5_corrected.py).

Each defect is first reproduced on the historical implementation (src/pbti/b5.py, unchanged), then the corrected
implementation is run on the same stream and compared with the reference model of tools/b5_refmodel with the
corrected choices (new fork evidence only; one case per held observation) and the kept implementation choices
(identity order, no case for contested identities, resume checked after hold-case decisions, sim.World event rule).
The minimal streams are those of tools/b5_refmodel/test_discrepancies_real.py.
"""
import contextlib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ["B5_REPO"] = ROOT          # the V7 harness imports pbti from $B5_REPO/src (default: a V7 scratch path)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "tools", "b5_refmodel"))

import harness as H  # noqa: E402
import refmodel as M  # noqa: E402
from gen import FAMILIES, SpecBuilder  # noqa: E402
from pbti.b5 import B5FeedLevel  # noqa: E402
from pbti.b5_corrected import B5Corrected  # noqa: E402

assert all(os.path.realpath(m.__file__).startswith(os.path.realpath(ROOT))
           for m in (H, M, sys.modules["pbti.b5"], sys.modules["pbti.sim"], sys.modules["pbti.verifier"]))

CORRECTED_CHOICES = dict(order="identity", fork_rule="evidence", contested_cases=False, resume_timing="decision",
                         wire_cases=False, event_scope="impl")


@contextlib.contextmanager
def _impl(cls):
    old = H.B5FeedLevel
    H.B5FeedLevel = cls
    try:
        yield
    finally:
        H.B5FeedLevel = old


def bound(cls, P):
    """The harness constructs the class without a review mode; bind the stream's mode for the corrected class."""
    if not issubclass(cls, B5Corrected):
        return cls

    class Bound(cls):
        def __init__(self, *a, **kw):
            kw.setdefault("review_mode", P.mode)
            super().__init__(*a, **kw)
    return Bound


def run_cls(cls, built, P, events=None):
    with _impl(bound(cls, P)):
        return H.run_real(built, P, events)


def corrected_model(P):
    return M.replace(P, **CORRECTED_CHOICES)


def chain(b, did, n, t_prod=lambda i: 1_000 * (i + 1), ep=0, val0=50):
    names, prev = [], None
    for i in range(n):
        nm = b.stmt(f"{did}/{ep}/{i}/g{i}", did, ep, i, t_prod(i), prev, val0 + i, True)
        names.append(nm)
        prev = nm
    return names


def forge(b, did, seq, ts, prev, ep=0, tag="f"):
    return b.stmt(f"{did}/{ep}/{seq}/{tag}{seq}", did, ep, seq, ts, prev, 900 + seq, False)


def iv(res, built, name):
    k = (tuple(built.stmt[name][x] for x in ("did", "ep", "seq")), built.cd[name])
    return res["intervals"].get(k, [])


def three(b, t_end, P):
    built = H.build(b.spec(t_end, "repro", 0))
    ev = M.schedule(built.model_stmts, P, t_end)
    old = run_cls(B5FeedLevel, built, P, ev)
    new = run_cls(B5Corrected, built, P, ev)
    model = H.run_model(built, corrected_model(P), ev)
    return built, old, new, model


def _corrected_invariant(built, P, events=None):
    """Run the corrected B5 and return the verifier, so that internal invariants can be checked."""
    holder = {}

    class Capture(B5Corrected):
        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            holder["v"] = self

    res = run_cls(Capture, built, P, events)
    return res, holder["v"]


# --------------------------------------------------------------------------------------------- C1 (F1 / D2)
def test_c1_no_rehold_without_new_fork_evidence():
    """f1 forks the feed at seq 1; g2 arrives late but adds no fork evidence (its prev names g1, an admitted
    version of the contested slot).  Historical B5: g2's receipt re-runs fork detection from slot state, holds
    again g3 that review had released at 70 s, and counts a second fork.  Corrected B5: no second hold."""
    b = SpecBuilder(["d"], h_max_ms=3_600_000)
    g = chain(b, "d", 5)
    f1 = forge(b, "d", 1, 2_000, g[0])
    b.arrive(1_020, g[0]); b.arrive(2_020, g[1]); b.arrive(2_070, f1)
    b.arrive(75_000, g[2]); b.arrive(4_020, g[3]); b.arrive(5_020, g[4])
    built, old, new, model = three(b, 200_000, M.Params.hist())
    assert iv(old, built, g[3]) == [(70_000, 75_000), (140_000, 200_000)]          # defect reproduced
    assert old["counters"]["fork_events"] == 2
    assert iv(new, built, g[3]) == [(70_000, 200_000)]
    assert iv(new, built, g[2]) == [(75_000, 200_000)]
    assert new["counters"]["fork_events"] == 1
    assert H.compare(model, new)["all_core"]
    assert H.counters_match(model, new)


def test_c1_successor_of_contested_slot_after_resume_is_live():
    """Fork at seq 1 (g1 and f1); g3's hold case is rejected at 70 s (one-shot, uncorroborated) and the feed resumes.
    g2 arrives at 150 s; its prev names g1, one of the admitted versions of the contested slot, so it adds no fork
    evidence.  Historical B5: g2's receipt starts a new feed hold (g2 authoritative only from 210 s).  Corrected
    B5: g2 is admitted live."""
    b = SpecBuilder(["d"], h_max_ms=3_600_000)
    g = chain(b, "d", 5)
    f1 = forge(b, "d", 1, 2_000, g[0])
    b.arrive(1_020, g[0]); b.arrive(2_020, g[1]); b.arrive(2_070, f1); b.arrive(4_020, g[3])
    b.arrive(150_000, g[2])
    built, old, new, model = three(b, 300_000, M.Params.hist())
    assert old["resumes"][0] == (70_000, ("d", 0)) and new["resumes"][0] == (70_000, ("d", 0))
    assert iv(old, built, g[2]) == [(210_000, 300_000)] and old["counters"]["fork_events"] == 2   # historical
    assert iv(new, built, g[2]) == [(150_000, 300_000)] and new["counters"]["fork_events"] == 1
    assert H.compare(model, new)["all_core"]


# --------------------------------------------------------------------------------------------- C2 (F2 / D4)
def test_c2a_stale_release_into_held_feed_gets_a_hold_case():
    b = SpecBuilder(["d"], h_max_ms=10_000)
    g = chain(b, "d", 7, t_prod=lambda i: 1_000 * (i + 1) if i < 6 else 50_000)
    f1 = forge(b, "d", 1, 2_000, g[0])
    b.arrive(1_020, g[0]); b.arrive(2_020, g[1]); b.arrive(2_070, f1); b.arrive(3_020, g[2])
    b.arrive(4_020, g[3]); b.arrive(20_000, g[4], 0, "buffered"); b.arrive(6_020, g[5]); b.arrive(50_020, g[6])
    P = M.Params.hist()
    built, old, new, model = three(b, 200_000, P)
    assert old["review_outcomes"].get("RELEASE_FAILED:QUARANTINE/FEED_FORK_HOLD") == 1    # defect reproduced
    assert iv(old, built, g[4]) == []
    assert "RELEASE_FAILED:QUARANTINE/FEED_FORK_HOLD" not in new["review_outcomes"]
    assert new["review_outcomes"].get("DEFERRED_TO_FEED_HOLD") == 1
    assert iv(new, built, g[4]) == [(140_000, 200_000)]
    assert H.compare(model, new)["all_core"]
    _, v = _corrected_invariant(built, P)
    assert v.held_without_case() == []


def test_c2b_stale_duplicate_of_admitted_wire_gets_a_hold_case():
    b = SpecBuilder(["d"], h_max_ms=10_000)
    g = chain(b, "d", 6)
    f1 = forge(b, "d", 1, 15_500, g[0])
    for i, nm in enumerate(g):
        b.arrive(1_000 * (i + 1) + 20, nm)
    b.arrive(15_000, g[3])                                   # stale retransmission of an admitted wire
    b.arrive(16_000, f1)                                     # fork at 1 holds seq 1.. (g3 too)
    P = M.Params.hist()
    built, old, new, model = three(b, 200_000, P)
    assert iv(old, built, g[3]) == [(4_020, 16_000)]                                 # defect reproduced
    assert iv(new, built, g[3]) == [(4_020, 16_000), (80_000, 200_000)]
    assert H.compare(model, new)["all_core"]
    res, v = _corrected_invariant(built, P)
    assert v.held_without_case() == [] and v.hold_case_conversions == 1


def test_c2c_event_mode_deferred_release_reexamines_neighbours():
    """Event-driven review: g3's stale case is corroborated and released into the held feed.  Historical B5: the
    release fails without a case and g2 stays pending for good.  Corrected B5: g3 becomes a held identity with a
    hold case; its HELD transition makes event review re-examine g2, g3 and g4 at once."""
    b = SpecBuilder(["d"], h_max_ms=10_000)
    g = chain(b, "d", 6, t_prod=lambda i: 1_000 * (i + 1) if i < 5 else 60_000)
    f1 = forge(b, "d", 1, 2_000, g[0])
    b.arrive(1_020, g[0]); b.arrive(2_020, g[1]); b.arrive(2_070, f1); b.arrive(3_020, g[2])
    b.arrive(5_020, g[4]); b.arrive(20_000, g[3], 0, "buffered"); b.arrive(60_020, g[5])
    P = M.Params.event()
    built, old, new, model = three(b, 100_000, P)
    assert iv(old, built, g[2]) == [] and iv(old, built, g[3]) == []                 # defect reproduced
    assert iv(new, built, g[2]) == [(20_000, 100_000)]
    assert iv(new, built, g[3]) == [(20_000, 100_000)]
    assert iv(new, built, g[4]) == [(20_000, 100_000)]
    assert H.compare(model, new)["all_core"]


def test_c2d_hold_case_opened_during_a_pass_waits_for_the_next_pass():
    """Stress stream (generator family stale_into_held, seed 250; one-shot review, R = 0, C = 10 s): at 40 s the
    release of g17's stale case re-runs admission, which forks the feed at 16 and holds g18, whose wire also has a
    pending stale case (a byte-identical retransmission) in the same pass.  That case becomes g18's hold case; it
    was opened during the pass, so it is decided at the next pass (50 s, released), not in the pass that opened it
    (where its predecessor was still held and the one-shot rule would have rejected it for good)."""
    from run_diff import SETTINGS
    spec = FAMILIES["stale_into_held"](250)
    built = H.build(spec)
    P = SETTINGS["oneshot_d0c10"]
    ev = M.schedule(built.model_stmts, P, built.t_end)
    new = run_cls(B5Corrected, built, P, ev)
    model = H.run_model(built, corrected_model(P), ev)
    assert iv(new, built, "s1/0/18/g18") == [(18_022, 40_000), (50_000, 150_000)]
    assert H.compare(model, new)["all_core"] and H.counters_match(model, new)


# --------------------------------------------------------------------------------------------- C3 (F3 / D5)
def test_c3_hold_counted_once():
    b = SpecBuilder(["d"], h_max_ms=3_600_000)
    g = chain(b, "d", 3)
    f1 = forge(b, "d", 1, 2_000, g[0])
    b.arrive(1_020, g[0]); b.arrive(2_020, f1); b.arrive(3_020, g[2])
    P = M.Params.strict()
    built, old, new, model = three(b, 100_000, P)
    assert old["counters"]["holds"] == 3 and len(old["held_identities"]) == 2         # defect reproduced
    assert new["counters"]["holds"] == 2 == len(new["held_identities"])
    assert H.counters_match(model, new)
    _, v = _corrected_invariant(built, P)
    assert v.v9_counters()["held_distinct_ever"] == 2


# --------------------------------------------------------------------------------------------- C4 (D6)
def test_c4_tainted_hold_release_label():
    b = SpecBuilder(["d"], h_max_ms=3_600_000)
    g = chain(b, "d", 4)
    f1 = forge(b, "d", 1, 2_050, g[0])
    b.arrive(1_020, g[0]); b.arrive(2_020, g[1]); b.arrive(2_070, f1); b.arrive(3_020, g[2]); b.arrive(4_020, g[3])
    built = H.build(b.spec(100_000, "repro", 0))
    P = M.Params.hist()
    ev = M.schedule(built.model_stmts, P, built.t_end)
    holder = {}

    class Taint(B5Corrected):
        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            holder["v"] = self

        def _release(self, wd, case, t):
            if case["reason"] == "FEED_FORK_HOLD":
                self.reg.slots[tuple(case["eid"])].tainted = True     # white-box: taint before the decision
            return super()._release(wd, case, t)

    res = run_cls(Taint, built, P, ev)
    outs = res["review_outcomes"]
    assert outs.get("RELEASE_FAILED:TAINTED", 0) >= 1 and "RELEASE_FAILED:CONFLICT" not in outs


# --------------------------------------------------------------------------------------------- kept choices
def test_kept_choice_identity_review_order():
    """D1 (kept, documented): a review pass works in identity order, as in the historical B5 and PBTI-R."""
    b = SpecBuilder(["d"], h_max_ms=10_000)
    g = chain(b, "d", 4)
    for nm in g[:2]:
        b.arrive(b.stmts[g.index(nm)]["ts"] + 20, nm)
    b.arrive(20_004, g[3], 0, "buffered")
    b.arrive(20_008, g[2], 0, "buffered")
    built, old, new, model = three(b, 100_000, M.Params.hist())
    assert iv(new, built, g[3]) == [(90_000, 100_000)] and iv(new, built, g[2]) == [(90_000, 100_000)]
    assert old["intervals"] == new["intervals"]
    assert H.compare(model, new)["all_core"]


def test_kept_choice_contested_identity_has_no_case():
    """D3 (kept, documented): a contested identity gets no review case and a feed resume is checked after each
    hold-case decision, so this feed resumes only after g4's hold case is decided (170 s)."""
    b = SpecBuilder(["d"], h_max_ms=3_600_000)
    g = chain(b, "d", 5, t_prod=lambda i: 1_000 * (i + 1) if i < 4 else 100_000)
    f2 = forge(b, "d", 2, 3_000, g[1])
    b.arrive(1_020, g[0]); b.arrive(2_020, g[1]); b.arrive(3_020, g[2]); b.arrive(3_070, f2)
    b.arrive(100_020, g[4])
    built, old, new, model = three(b, 200_000, M.Params.hist())
    assert new["resumes"] == [(170_000, ("d", 0))] and iv(new, built, g[4]) == []
    assert H.compare(model, new)["all_core"]


# --------------------------------------------------------------------------------------------- invariants
def _family_specs(fam, seeds):
    return [FAMILIES[fam](s) for s in seeds]


def test_no_held_identity_without_case_on_stress_streams():
    for fam in ("stale_into_held", "rand_small"):
        for spec in _family_specs(fam, range(12)):
            built = H.build(spec)
            for P in (M.Params.hist(), M.Params.event(), M.Params.defer(1, 1), M.Params.strict()):
                _, v = _corrected_invariant(built, P)
                assert v.held_without_case() == [], (fam, spec["seed"], P)


def test_identical_to_historical_without_fork_evidence():
    """Streams without any fork evidence: the corrected and the historical B5 behave identically."""
    b = SpecBuilder(["d", "e"], h_max_ms=10_000)
    gd = chain(b, "d", 8)
    ge = chain(b, "e", 8, val0=70)
    for i in range(8):
        b.arrive(1_000 * (i + 1) + 20, gd[i])
        b.arrive(1_000 * (i + 1) + 40 if i != 5 else 30_000, ge[i], 0, "live" if i != 5 else "buffered")
    b.arrive(9_500, gd[3])                                   # retransmission
    for P in (M.Params.hist(), M.Params.event(), M.Params.strict()):
        built = H.build(b.spec(120_000, "repro", 0))
        ev = M.schedule(built.model_stmts, P, built.t_end)
        old = run_cls(B5FeedLevel, built, P, ev)
        new = run_cls(B5Corrected, built, P, ev)
        for k in ("intervals", "authoritative", "decisions", "resumes", "counters", "review_outcomes"):
            assert old[k] == new[k], (k, P)
