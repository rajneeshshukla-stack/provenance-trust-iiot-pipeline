"""End-to-end invariant checks on short simulated runs (fast versions of the experiment scenarios)."""
import pytest

from pbti.audit import audit_pbti
from pbti.oracle import evaluate
from pbti.scenarios import build

SHORT = dict(duration_ms=300_000, drain_ms=120_000)


def run(sc, system="PBTI", seed=3):
    w = build(sc, system, seed)
    w.run()
    return w, evaluate(w)


def test_I3_idempotency_under_duplicates():
    _, r = run("S07_duplicates")
    assert r["dup_auth"] == 0 and r["legit_missing"] == 0


def test_I1_I2_no_forged_or_tampered_admission():
    for sc in ("S02_payload_tamper", "S03_metadata_tamper", "S04_unauthorized", "S06_replay"):
        _, r = run(sc)
        assert r["nonlegit_auth"] == 0, sc


def test_I4_equivocation_and_gapfill_never_authoritative():
    _, r = run("S05_stolen_key")
    imp = r.get("rx[impersonation]ACCEPT/COMMITTED", 0)
    # the only admitted forgeries are the full impersonation stream (out of detection scope)
    assert r["nonlegit_auth"] <= imp


def test_I7_revocation_containment():
    _, r = run("S14_revocation")
    assert r["nonlegit_auth"] == 0
    assert r.get("rx[postrevocation-stolen]ACCEPT/COMMITTED", 0) == 0


def test_I8_recovery_complete():
    _, r = run("S11_disconnect_recover")
    assert r["legit_missing"] == 0 and r["dup_auth"] == 0
    # the SUSPECTED_REPLAY label is context-based and non-authoritative; it is a reported metric, not an invariant


def test_I9_order_independence_reorder():
    _, r = run("S09_reorder")
    assert r["win_exact"] == r["win_total"] and r["cv_wrong"] == 0


def test_I5_I6_I10_audit_passes():
    w, _ = run("S05_stolen_key")
    a = audit_pbti(w.sys, replay=True)
    assert a["pass"], a["findings"]
