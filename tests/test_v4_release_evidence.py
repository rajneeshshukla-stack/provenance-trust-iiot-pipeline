"""V4 (memo R09, A5): release-evidence policies for the REVOKED_BUFFERED waiver and the lifecycle matrix cases.

The lifecycle cases are defined once in scripts/a5_lifecycle_matrix.py; these tests pin their outcomes for both the
per-identity (PBTI) and feed-level (B5) verifier classes, plus unit checks of the witness token itself.
"""
import importlib.util
from pathlib import Path

import pytest

from pbti.b5 import B5FeedLevel
from pbti.timewitness import TimeWitness
from pbti.verifier import PBTIVerifier

_SPEC = importlib.util.spec_from_file_location(
    "a5_lifecycle_matrix", Path(__file__).resolve().parents[1] / "scripts" / "a5_lifecycle_matrix.py")
A5 = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(A5)

CLASSES = (PBTIVerifier, B5FeedLevel)


def run(case, cls, policy, width_ms=0):
    params = {"h_max_ms": 10_000} if case in A5.H10_CASES else {}
    e = A5.Env(cls, policy, params, width_ms=width_ms)
    return A5.CASES[case](e)


# --------------------------------------------------------------------------- witness token
def test_witness_token_binds_exact_digest_and_time():
    w = TimeWitness(b"t", eps_ms=1_000)
    tok = w.stamp("digestA", 5_000)
    assert w.valid(tok)
    assert w.proves_before("digestA", 6_001) and not w.proves_before("digestA", 6_000)   # eps margin
    assert not w.proves_before("digestB", 10 ** 9)                                        # other content
    forged = dict(tok, cd="digestB")
    assert not w.valid(forged)
    assert w.stamp("digestA", 1_000)["t"] == 5_000          # the earliest token is kept; cannot be re-dated earlier


def test_witness_outage_issues_no_token():
    w = TimeWitness(b"t")
    w.up = False
    assert w.stamp("d", 1) is None and w.refused == 1 and w.token_for("d") is None


def test_unknown_release_policy_raises():
    e = A5.Env(PBTIVerifier, "bogus")
    with pytest.raises(ValueError):
        A5.case_legit_buffered_witnessed(e)


# --------------------------------------------------------------------------- lifecycle matrix
@pytest.mark.parametrize("cls", CLASSES)
def test_legitimate_buffered_record_released_unless_policy_none(cls):
    assert run("legit_buffered_witnessed", cls, "none")["genuine_withheld"]
    for pol in ("discretionary", "witness"):
        r = run("legit_buffered_witnessed", cls, pol)
        assert r["case_state"] == "RELEASED" and r["genuine_recovered"]
        assert not r["tainted_end"]           # released after the revocation was processed: not re-tainted by it


@pytest.mark.parametrize("cls", CLASSES)
@pytest.mark.parametrize("case", ["backdated_forgery_witness_sees_late", "backdated_forgery_not_witnessed"])
def test_backdated_forgery_released_only_by_discretionary_policy(cls, case):
    assert run(case, cls, "discretionary")["malicious_authoritative"]        # V3 behaviour: demonstrated exposure
    for pol in ("none", "witness"):
        r = run(case, cls, pol)
        assert not r["malicious_authoritative"] and r["case_state"] == "REJECTED"


@pytest.mark.parametrize("cls", CLASSES)
@pytest.mark.parametrize("pol", A5.POLICIES)
def test_contradicted_forgery_never_released(cls, pol):
    r = run("forgery_with_contradictory_successor", cls, pol)
    assert not r["malicious_authoritative"]


@pytest.mark.parametrize("cls", CLASSES)
def test_witness_outage_costs_availability_under_witness_policy(cls):
    assert run("legit_buffered_witness_outage", cls, "witness")["genuine_withheld"]
    assert run("legit_buffered_witness_outage", cls, "discretionary")["genuine_recovered"]


@pytest.mark.parametrize("cls", CLASSES)
def test_stale_snapshot_refused_then_fresh_review_decides(cls):
    r = run("stale_reviewer_snapshot", cls, "witness")
    assert r["first_decision"] == "STALE_REVIEW" and r["state_after_first_decision"] == "QUARANTINED"
    assert r["case_state"] == "RELEASED" and r["genuine_recovered"]


@pytest.mark.parametrize("cls", CLASSES)
def test_revoked_reviewer_cannot_decide(cls):
    r = run("revoked_reviewer", cls, "discretionary")
    assert r["case_state"] == "QUARANTINED" and r["review_outcomes"].get("REVIEWER_REVOKED", 0) >= 1


@pytest.mark.parametrize("cls", CLASSES)
@pytest.mark.parametrize("pol", A5.POLICIES)
def test_stale_ts_release_fails_closed_after_origin_revocation(cls, pol):
    """Only the case's own reason (STALE_TS) is waived; the revocation that arrived meanwhile still applies, so the
    release fails and the case closes (documented behaviour; a genuine record is withheld)."""
    r = run("stale_ts_release_after_origin_revoked", cls, pol)
    assert r["case_state"] == "REJECTED" and r["genuine_withheld"]
    assert any(k.startswith("RELEASE_FAILED") for k in r["review_outcomes"])


@pytest.mark.parametrize("cls", CLASSES)
def test_release_then_later_revocation_taints(cls):
    r = run("release_then_later_taint", cls, "discretionary")
    assert r["authoritative_after_release"] and r["tainted_end"] and not r["authoritative_end"]


@pytest.mark.parametrize("cls", CLASSES)
def test_compromise_interval_width_trades_recovery(cls):
    got = {w: run("legit_buffered_witnessed", cls, "witness", width_ms=w)["genuine_recovered"]
           for w in (0, 5_000, 30_000, 120_000)}
    assert got == {0: True, 5_000: True, 30_000: False, 120_000: False}


# --------------------------------------------------------------------------- D05: revised revocation records
def _committed_env():
    e = A5.Env(PBTIVerifier, "discretionary")
    g0, c0 = e.msg(0, None, 1_000, 1.0, "live")
    e.v.ingest(g0, 2_000)
    return e


def test_revised_earlier_compromise_time_taints_retroactively():
    e = _committed_env()
    e.trust.revoke("dk:d1:1", 3_000, 3_000, "first")        # commit at 2 s precedes t_comp: not tainted
    e.v.advance(4_000)
    assert not e.v.reg.slots[("d1", 0, 0)].tainted
    e.trust.revoke("dk:d1:1", 5_000, 0, "revised")          # forensic revision: compromise since 0
    e.v.advance(6_000)
    assert e.v.reg.slots[("d1", 0, 0)].tainted
    r = e.trust.all_revocations()["dk:d1:1"]
    assert (r.t_rev_ms, r.t_comp_ms) == (3_000, 0)


def test_revision_cannot_move_compromise_time_later():
    e = _committed_env()
    e.trust.revoke("dk:d1:1", 3_000, 1_000, "first")
    e.trust.revoke("dk:d1:1", 4_000, 50_000, "later")
    assert e.trust.all_revocations()["dk:d1:1"].t_comp_ms == 1_000
    e.v.advance(5_000)
    assert e.v.reg.slots[("d1", 0, 0)].tainted               # 2 s >= 1 s


def test_reannounced_revocation_keeps_valid_pre_compromise_release():
    e = A5.Env(PBTIVerifier, "discretionary")
    r = A5.case_legit_buffered_witnessed(e)                  # released at 30 s under ts 5 s < t_comp 10 s
    assert r["genuine_recovered"]
    for k in ("dk:d1:1", "wk:g1:1"):
        e.trust.revoke(k, 70_000, 10_000, "re-announced")    # same compromise time: release condition still holds
    e.v.advance(72_000)
    assert ("d1", 0, 2) in e.auth() and not e.v.reg.slots[("d1", 0, 2)].tainted
    for k in ("dk:d1:1", "wk:g1:1"):
        e.trust.revoke(k, 80_000, 4_000, "revised-earlier")  # now ts 5 s >= t_comp 4 s: the condition fails
    e.v.advance(82_000)
    assert e.v.reg.slots[("d1", 0, 2)].tainted and ("d1", 0, 2) not in e.auth()


@pytest.mark.parametrize("cls", CLASSES)
@pytest.mark.parametrize("pol", ("discretionary", "witness"))
def test_full_sequence_release_then_revised_taint_corrects_derived_window(cls, pol):
    """R09: revocation -> quarantine -> authorized review -> release -> revised record -> taint -> correction."""
    r = run("full_sequence_revised_taint", cls, pol)
    assert r["case_state"] == "RELEASED" and r["authoritative_after_release"] and r["in_window_after_release"]
    assert r["tainted_end"] and not r["authoritative_end"] and r["window_corrected"]
