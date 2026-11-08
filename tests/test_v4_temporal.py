"""V4: exact checks of the temporal metrics (src/pbti/temporal.py) on hand-crafted transition traces whose integrals
were derived by hand (memo A2: zero-duration changes, repeated holds, taint to the end, records never released,
forged and genuine contents sharing an identity, censoring), plus tracer and end-to-end consistency checks."""
import types

import pytest

from pbti.envelope import content_key
from pbti.temporal import Tracer, compute, intervals_from_log, kaplan_meier_quantiles

T = 10_000


def L(pairs, t_prod=0, t_acc=None, aid="a", temp=None):
    return {"pairs": set(pairs), "t_prod": t_prod, "t_acc": t_prod if t_acc is None else t_acc, "aid": aid, "temp": temp}


def test_single_observation_available_after_100ms():
    r = compute([(100, "e1", None, "c1", "d1", "k")], [L([("e1", "c1")])], T)
    assert r["tm_wh_rec_s"] == pytest.approx(0.1)
    assert r["tm_nl_rec_s"] == 0
    assert r["tm_avail_1s"] == 1.0 and r["tm_never_avail"] == 0 and r["tm_withdrawn"] == 0
    assert r["tm_first_km_p50_s"] == pytest.approx(0.1)


def test_forged_and_genuine_share_identity():
    log = [(100, "e1", None, "cF", "dF", "k"), (600, "e1", "cF", "c1", "d1", "k")]
    rec = {"e1": [(100, "dF", None, "equivocation"), (600, "d1", None, "legit")]}
    r = compute(log, [L([("e1", "c1")])], T, receipts=rec)
    assert r["tm_nl_rec_s"] == pytest.approx(0.5)       # the forgery was authoritative 100-600 ms
    assert r["tm_nl_pairs_ever"] == 1 and r["tm_nl_auth_end"] == 0
    assert r["tm_wh_rec_s"] == pytest.approx(0.6)       # the forged value never counts as the genuine one
    assert r["tm_avail_1s"] == 1.0
    assert r["tm_nl_contained"] == 1 and r["tm_contain_lat_max_s"] == 0.0


def test_zero_duration_change_is_not_availability():
    log = [(500, "e2", None, "c2", "d", "k"), (500, "e2", "c2", None, "d", "k")]
    r = compute(log, [L([("e2", "c2")], t_prod=400)], T)
    assert r["tm_zero_flips"] == 1
    assert r["tm_never_avail"] == 1
    assert r["tm_wh_rec_s"] == pytest.approx(9.6)


def test_repeated_hold_and_release():
    log = [(0, "e3", None, "c3", "d", "k"), (1000, "e3", "c3", None, "d", "k"), (3000, "e3", None, "c3", "d", "k")]
    r = compute(log, [L([("e3", "c3")])], T)
    assert r["tm_wh_rec_s"] == pytest.approx(2.0)
    assert r["tm_withdrawn"] == 1 and r["tm_withdrawn_end"] == 0


def test_taint_withdraws_until_end():
    log = [(200, "e4", None, "c4", "d", "k"), (5000, "e4", "c4", None, "d", "k")]
    r = compute(log, [L([("e4", "c4")])], T)
    assert r["tm_wh_rec_s"] == pytest.approx(5.2)
    assert r["tm_withdrawn"] == 1 and r["tm_withdrawn_end"] == 1


def test_never_released_counts_from_gateway_acceptance():
    r = compute([], [L([("e5", "c5")], t_prod=1000, t_acc=2000)], T)
    assert r["tm_wh_rec_s"] == pytest.approx(8.0)
    assert r["tm_never_avail"] == 1 and r["tm_first_km_p50_s"] is None


def test_kaplan_meier_with_censoring():
    q = kaplan_meier_quantiles([100, 200, 300, 400], [1, 1, 0, 1])
    assert q[0.5] == 200 and q[0.9] == 400 and q[0.99] == 400
    assert kaplan_meier_quantiles([5, 6], [0, 0])[0.5] is None


def test_observation_with_two_honest_identities():
    log = [(100, "e6a", None, "c6", "d", "k"), (3000, "e6b", None, "c6", "d", "k"), (4000, "e6a", "c6", None, "d", "k")]
    r = compute(log, [L([("e6a", "c6"), ("e6b", "c6")])], T)
    assert r["tm_wh_rec_s"] == pytest.approx(0.1) and r["tm_withdrawn"] == 0


def test_deadline_boundary_is_inclusive():
    r = compute([(1000, "e", None, "c", "d", "k")], [L([("e", "c")])], T)
    assert r["tm_avail_1s"] == 1.0


def test_freshness_staleness_and_missing():
    log = [(50, "e0", None, "c0", "d", "k"), (1500, "e1", None, "c1", "d", "k")]
    legit = [L([("e0", "c0")], 0, aid="f"), L([("e1", "c1")], 1000, aid="f"), L([("e2", "c2")], 2000, aid="f")]
    r = compute(log, legit, 3000)
    # samples at 1 s and 2 s (the end of the interval is excluded): stale 1.0 s at both
    assert r["tm_fresh_samples"] == 2
    assert r["tm_fresh_stale_mean_s"] == pytest.approx(1.0) and r["tm_fresh_missing_frac"] == 0.0
    r2 = compute([], [L([("e0", "c0")], 0, aid="g")], 3000)
    assert r2["tm_fresh_missing_frac"] == 1.0


def test_monitoring_workload_false_missed_and_retracted_alerts():
    hot1 = content_key("d", "a", 0, "s", {"temp_c": 53.0})
    hot2 = content_key("d", "a", 1, "s", {"temp_c": 54.0})
    forged = content_key("d", "a", 2, "s", {"temp_c": 60.0})
    log = [(6000, "h1", None, hot1, "x", "k"), (100, "h2", None, hot2, "x", "k"),
           (200, "f", None, forged, "y", "k"), (700, "f", forged, None, "y", "k")]
    log.sort(key=lambda x: x[0])
    legit = [L([("h1", hot1)], 0, aid="a", temp=53.0), L([("h2", hot2)], 0, aid="a", temp=54.0)]
    r = compute(log, legit, T, nominal={"a": 50.0})
    assert r["tm_alert_true"] == 2 and r["tm_alert_missed"] == 1          # h1 only after 6 s > 5 s deadline
    assert r["tm_alert_false"] == 1 and r["tm_alert_false_retracted"] == 1 and r["tm_alert_false_open_end"] == 0


def test_derived_output_exposure_and_correction_latency():
    log = [(900, "e", None, "cF", "d", "k"), (2500, "e", "cF", None, "d", "k")]
    windows = {("a", 0): [{"t": 1000, "ckeys": ("cF",)}, {"t": 3000, "ckeys": ()}]}
    r = compute(log, [], T, windows=windows)
    assert r["tm_dw_nl_s"] == pytest.approx(2.0)
    assert r["tm_dw_corr_n"] == 1 and r["tm_dw_corr_lat_max_s"] == pytest.approx(0.5)


def test_intervals_drop_zero_length_and_close_at_end():
    out = intervals_from_log([(10, "k", None, "c", 0, 0), (10, "k", "c", None, 0, 0), (20, "k", None, "c", 0, 0)], 50)
    assert out["iv"] == {("k", "c"): [(20, 50)]} and out["zero"] == 1


# ------------------------------------------------------------------ tracer on the real verifier
def test_tracer_logs_each_change_once():
    from test_v3_review_b5 import chain, env
    v, trust, dsk, wsk, rsk, _ = env()
    tr = Tracer(types.SimpleNamespace(sys=v))
    c = chain(dsk, wsk, 3)
    for i, (w, _) in enumerate(c):
        v.ingest(w, 1000 * (i + 1))
    n = len(tr.log)
    assert n == 3 and all(x[3] is not None for x in tr.log)
    v.ingest(c[1][0], 5_000)                      # exact duplicate: no change
    tr.flush(6_000, {("d1", 0, 0), ("d1", 0, 1)})  # re-evaluation without change
    assert len(tr.log) == n
    assert tr.end_state() == {(k, ck) for k, ck in v.authoritative()}


def test_end_to_end_normal_run_is_fully_available():
    from pbti.oracle import evaluate
    from pbti.scenarios import build
    from pbti.temporal import temporal_metrics
    w = build("S01_normal", "PBTI", 1, temporal=True, duration_ms=60_000, drain_ms=30_000)
    w.run()
    r = evaluate(w)
    m = temporal_metrics(w)
    assert m["tm_end_state_matches_authoritative"]
    assert m["tm_nl_rec_s"] == 0 and m["tm_never_avail"] == 0 and m["tm_avail_60s"] == 1.0
    assert r["legit_missing"] == 0
