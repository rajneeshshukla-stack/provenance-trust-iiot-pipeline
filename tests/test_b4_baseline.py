"""Revision 2: strongest-combination baseline B4 (origin signatures + rotation grace + per-message path policy +
producer-sequence idempotency + signed ledger, without relay statement, Rule L, quarantine or taint)."""
from pbti.oracle import evaluate
from pbti.scenarios import build


def _run(sc, seed=1):
    w = build(sc, "B4", seed)
    w.run()
    return w, evaluate(w)


def test_b4_normal_operation_accepts_everything():
    w, r = _run("S01_normal")
    assert r["nonlegit_auth"] == 0 and r["legit_missing"] == 0 and r["dup_auth"] == 0
    assert set(w.sys.counts) == {"ACCEPT/INSERT"}


def test_b4_rejects_tampering_like_signature_schemes():
    _, r = _run("S02_payload_tamper")
    assert r["nonlegit_auth"] == 0


def test_b4_first_writer_wins_on_conflicting_versions():
    w, r = _run("S08_seq_reuse_bug")
    assert w.sys.counts.get("REJECT/CONFLICTING_VERSION", 0) >= 1
    assert r["nonlegit_auth"] == 0 and r["dup_auth"] == 0


def test_b4_has_no_retroactive_taint():
    _, r = _run("S14_revocation")
    assert r["nonlegit_auth"] > 0   # forgeries committed before revocation stay authoritative without taint
