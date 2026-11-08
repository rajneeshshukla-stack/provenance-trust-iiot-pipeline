"""V3 tests: quarantine review workflow (release/reject, authorization, staleness, duplicates, missing and conflicting
evidence, later revocation), LOST state and gap closure, B5/B5-strict feed-level handling, and the separation of
admission determinism from state determinism."""
import itertools

from pbti.b5 import B5FeedLevel
from pbti.crypto import b64u, keypair_from_seed
from pbti.envelope import LogicalObs, pbti_content_digest, pbti_sign_obs, pbti_wire
from pbti.identity import TrustRegistry
from pbti.policy import PolicyStore
from pbti.registry import COMMITTED, CONTESTED, LOST
from pbti.review import RELEASABLE, AutoReviewer, corroborated, sign_decision
from pbti.verifier import ACCEPT, QUARANTINE, PBTIVerifier

SEED = b"v3-review"
WID = "spiffe://plant-a.example/cell1/gw1/collector"
RID = "urn:pbti:reviewer:auto"


def env(params=None, cls=PBTIVerifier, reviewers=True, **kw):
    trust = TrustRegistry(SEED, use_x509=False)
    dsk, dpk = keypair_from_seed(SEED, "dk:d1:1")
    wsk, wpk = keypair_from_seed(SEED, "wk:g1:1")
    trust.issue("dk:d1:1", "device", "d1", dpk, -60_000, 10 ** 10)
    trust.issue("wk:g1:1", "workload", WID, wpk, -60_000, 10 ** 10)
    rsk, rpk = keypair_from_seed(SEED, "rk:auto:1")
    trust.issue("rk:auto:1", "reviewer", RID, rpk, -60_000, 10 ** 10)
    xsk, xpk = keypair_from_seed(SEED, "rk:other:1")
    trust.issue("rk:other:1", "reviewer", "urn:pbti:reviewer:other", xpk, -60_000, 10 ** 10)
    doc = {"devices": {"d1": {"assets": ["a1"], "origin": "device", "schemas": ["s"]}},
           "workloads": {WID: {"relay": ["d1"]}}, "params": dict(params or {})}
    if reviewers:
        doc["reviewers"] = {RID: {"may_release": list(RELEASABLE), "active": True}}
    v = cls(trust, PolicyStore(doc), keypair_from_seed(SEED, "verifier"), **kw)
    return v, trust, dsk, wsk, rsk, xsk


def msg(dsk, wsk, seq, prev, ts, val=1.0, ep=0, mode="buffered"):
    o = LogicalObs("d1", "a1", ep, seq, ts, "s", {"x": val}, f"m{seq}-{val}", prev)
    obs, osig = pbti_sign_obs(o, dsk, "dk:d1:1")
    return pbti_wire(obs, osig, WID, "wk:g1:1", wsk, ts, mode), b64u(pbti_content_digest(obs))


def chain(dsk, wsk, n, ts0=0, step=1_000, ep=0):
    out, prev = [], None
    for i in range(n):
        w, cd = msg(dsk, wsk, i, prev, ts0 + i * step, ep=ep)
        out.append((w, cd))
        prev = cd
    return out


def decide(v, wd, sk, t, decision="RELEASE", reviewer=RID, rkid="rk:auto:1", snap=None):
    if snap is None:
        snap = v.open_review(wd, reviewer, t)
    return sign_decision({"case": wd, "reviewer": reviewer, "rkid": rkid, "decision": decision,
                          "reason": "TEST", "snapshot": snap, "t": t}, sk)


def wd_of(wire):
    from pbti.crypto import sha256_hex
    return sha256_hex(wire)


# ------------------------------------------------------------------ release workflow
def test_stale_quarantine_released_by_authorized_reviewer_and_logged():
    v, trust, dsk, wsk, rsk, _ = env({"h_max_ms": 5_000})
    c = chain(dsk, wsk, 3)
    assert v.ingest(c[0][0], 1_000).disp == ACCEPT
    late = c[1][0]
    assert v.ingest(late, 20_000).disp == QUARANTINE          # older than the horizon
    fresh, _ = msg(dsk, wsk, 2, c[1][1], 19_900)                 # its successor arrives fresh
    assert v.ingest(fresh, 20_100).disp == ACCEPT
    wd = wd_of(late)
    assert v.qcases[wd]["state"] == "QUARANTINED"
    out = v.apply_review(decide(v, wd, rsk, 30_000), 30_000)
    assert out["outcome"] == "RELEASED"
    assert v.reg.slots[("d1", 0, 1)].state() == COMMITTED
    assert ("d1", 0, 1) in {k for k, _ in v.authoritative()}
    rev = [r for r in v.evidence.records if b'"type":"REVIEW"' in r]
    assert rev and b'"outcome":"RELEASED"' in rev[-1] and b'"rsig"' in rev[-1]
    assert v.recovery_latencies and v.recovery_latencies[0][0] == 30_000 - 1_000


def test_unauthorized_reviewer_and_bad_signature_refused():
    v, trust, dsk, wsk, rsk, xsk = env({"h_max_ms": 5_000})
    c = chain(dsk, wsk, 2)
    v.ingest(c[0][0], 1_000)
    v.ingest(c[1][0], 20_000)
    wd = wd_of(c[1][0])
    d = decide(v, wd, xsk, 30_000, reviewer="urn:pbti:reviewer:other", rkid="rk:other:1")
    assert v.apply_review(d, 30_000)["outcome"] == "UNAUTHORIZED_REVIEWER"
    assert v.qcases[wd]["state"] == "QUARANTINED"
    d = decide(v, wd, rsk, 31_000)
    d["decision"] = "RELEASE"
    d["reason"] = "tampered after signing"
    assert v.apply_review(d, 31_000)["outcome"] == "INVALID_REVIEWER_CREDENTIAL"
    assert ("d1", 0, 1) not in {k for k, _ in v.authoritative()}


def test_duplicate_and_unknown_case_and_revoked_reviewer():
    v, trust, dsk, wsk, rsk, _ = env({"h_max_ms": 5_000})
    c = chain(dsk, wsk, 2)
    v.ingest(c[0][0], 1_000)
    v.ingest(c[1][0], 20_000)
    wd = wd_of(c[1][0])
    d = decide(v, wd, rsk, 30_000)
    assert v.apply_review(d, 30_000)["outcome"] == "RELEASED"
    assert v.apply_review(d, 30_500)["outcome"] == "ALREADY_DECIDED"     # duplicate release is idempotent
    assert sum(1 for k, _ in v.authoritative() if k == ("d1", 0, 1)) == 1
    bogus = dict(d, case="0" * 64)
    assert v.apply_review(bogus, 31_000)["outcome"] in ("MISSING_EVIDENCE", "INVALID_REVIEWER_CREDENTIAL")
    trust.revoke("rk:auto:1", 32_000)
    v2, trust2, dsk2, wsk2, rsk2, _ = env({"h_max_ms": 5_000})
    c2 = chain(dsk2, wsk2, 2)
    v2.ingest(c2[0][0], 1_000)
    v2.ingest(c2[1][0], 20_000)
    trust2.revoke("rk:auto:1", 25_000)
    wd2 = wd_of(c2[1][0])
    assert v2.apply_review(decide(v2, wd2, rsk2, 30_000), 30_000)["outcome"] == "REVIEWER_REVOKED"


def test_stale_review_and_conflicting_evidence():
    v, trust, dsk, wsk, rsk, _ = env({"h_max_ms": 5_000})
    c = chain(dsk, wsk, 2)
    v.ingest(c[0][0], 1_000)
    v.ingest(c[1][0], 20_000)                                   # quarantined (stale)
    wd = wd_of(c[1][0])
    snap = v.open_review(wd, RID, 21_000)
    forged, _ = msg(dsk, wsk, 1, c[0][1], 19_500, val=99.0)     # a second content for the same identity arrives fresh
    v.ingest(forged, 22_000)
    d = decide(v, wd, rsk, 23_000, snap=snap)
    assert v.apply_review(d, 23_000)["outcome"] == "STALE_REVIEW"
    d2 = decide(v, wd, rsk, 24_000)                              # fresh review of the current evidence
    out = v.apply_review(d2, 24_000)
    assert out["outcome"].startswith("RELEASE_FAILED:CONFLICT")
    assert v.reg.slots[("d1", 0, 1)].state() == CONTESTED
    assert ("d1", 0, 1) not in {k for k, _ in v.authoritative()}


def test_auto_reviewer_refuses_uncorroborated_forgery():
    v, trust, dsk, wsk, rsk, _ = env({"h_max_ms": 5_000})
    c = chain(dsk, wsk, 2)
    v.ingest(c[0][0], 1_000)
    v.ingest(c[1][0], 2_000)
    fake, _ = msg(dsk, wsk, 5_000, None, 1_500, val=42.0)        # back-dated, far-ahead identity, no hash link
    assert v.ingest(fake, 40_000).disp == QUARANTINE
    rv = AutoReviewer(RID, "rk:auto:1", rsk, min_age_ms=0)
    res = rv.run(v, 50_000)
    assert [r["outcome"] for r in res] == ["REJECTED"]
    assert ("d1", 0, 5_000) not in {k for k, _ in v.authoritative()}


def test_later_revocation_retaints_released_record():
    v, trust, dsk, wsk, rsk, _ = env({"h_max_ms": 5_000})
    c = chain(dsk, wsk, 3)
    v.ingest(c[0][0], 1_000)
    v.ingest(c[1][0], 20_000)
    v.ingest(c[2][0], 20_100)
    wd = wd_of(c[1][0])
    assert v.apply_review(decide(v, wd, rsk, 30_000), 30_000)["outcome"] == "RELEASED"
    trust.revoke("dk:d1:1", 40_000, t_comp_ms=25_000)            # compromise window covers the release commit
    v.advance(41_000)
    s = v.reg.slots[("d1", 0, 1)]
    assert s.tainted and ("d1", 0, 1) not in {k for k, _ in v.authoritative()}
    assert v.proc.current_value("a1") != c[1][1]


def test_recovery_after_long_gap_lost_state_and_release():
    v, trust, dsk, wsk, rsk, _ = env({"gap_close_ms": 5_000})
    c = chain(dsk, wsk, 4)
    v.ingest(c[0][0], 1_000)
    v.ingest(c[3][0], 1_200)                                    # opens gap [1, 2]; seq 2 has an implied digest
    v.advance(10_000)                                           # gap older than gap_close_ms -> LOST
    es = v.reg.streams["d1"].epochs[0]
    assert es.in_closed(1) and es.in_closed(2) and v.lost_declared == 2
    assert v.reg.slots[("d1", 0, 2)].state() == LOST
    r1 = v.ingest(c[1][0], 12_000)
    r2 = v.ingest(c[2][0], 12_100)
    assert (r1.disp, r1.why) == (QUARANTINE, "STALE_SLOT") and (r2.disp, r2.why) == (QUARANTINE, "STALE_SLOT")
    rv = AutoReviewer(RID, "rk:auto:1", rsk, min_age_ms=0)
    outs = [r["outcome"] for r in rv.run(v, 20_000)]
    assert outs == ["RELEASED", "RELEASED"]                     # seq 1 via its predecessor, seq 2 via both links
    assert {("d1", 0, 1), ("d1", 0, 2)} <= {k for k, _ in v.authoritative()}


# ------------------------------------------------------------------ B5 / B5-strict
def _fork_feed(cls_kw):
    v, trust, dsk, wsk, rsk, _ = env(cls=B5FeedLevel, **cls_kw)
    c = chain(dsk, wsk, 6)
    for i, (w, _) in enumerate(c[:3]):
        assert v.ingest(w, 1_000 * (i + 1)).disp == ACCEPT
    forged, _ = msg(dsk, wsk, 2, c[1][1], 2_500, val=77.0)      # equivocation at seq 2
    v.ingest(forged, 3_500)
    for i, (w, _) in enumerate(c[3:]):
        assert v.ingest(w, 4_000 + 1_000 * i).disp == QUARANTINE   # feed held from the fork point
    return v, rsk


def test_b5_feed_hold_and_review_recovery():
    v, rsk = _fork_feed({"recovery": True})
    auth = {k for k, _ in v.authoritative()}
    assert ("d1", 0, 1) in auth and not any(k[2] >= 2 for k in auth)
    rv = AutoReviewer(RID, "rk:auto:1", rsk, min_age_ms=0)
    outs = [r["outcome"] for r in rv.run(v, 70_000)]
    assert outs.count("RELEASED_HOLD") == 3 and "REJECTED" in outs or outs.count("RELEASED_HOLD") == 3
    auth = {k for k, _ in v.authoritative()}
    assert {("d1", 0, 3), ("d1", 0, 4), ("d1", 0, 5)} <= auth and ("d1", 0, 2) not in auth
    assert ("d1", 0) not in v.fork                               # reviewed feed resumed


def test_b5_strict_feed_stays_frozen_new_epoch_not_held():
    v, rsk = _fork_feed({"recovery": False})
    auth = {k for k, _ in v.authoritative()}
    assert not any(k[1] == 0 and k[2] >= 2 for k in auth)
    trust_dsk = keypair_from_seed(SEED, "dk:d1:1")[0]
    wsk = keypair_from_seed(SEED, "wk:g1:1")[0]
    w, _ = msg(trust_dsk, wsk, 0, None, 9_000, ep=1)
    assert v.ingest(w, 9_100).disp == ACCEPT                     # a new epoch is a new feed


def test_b5_released_slot_contested_later_leaves_derived_data():
    """V3 regression (found by audit A-LIN on the mixed workload): a held observation released by review and contested
    by a later conflicting version, while its feed is still forked, must leave derived data and authority."""
    from pbti.audit import audit_pbti
    v, trust, dsk, wsk, rsk, _ = env(cls=B5FeedLevel, recovery=True)
    c = chain(dsk, wsk, 6)
    for i, (w, _) in enumerate(c[:3]):
        assert v.ingest(w, 1_000 * (i + 1)).disp == ACCEPT
    forged, _ = msg(dsk, wsk, 2, c[1][1], 2_500, val=77.0)      # equivocation at seq 2 -> fork, hold from seq 2
    v.ingest(forged, 3_500)
    assert v.ingest(c[3][0], 4_000).disp == QUARANTINE
    assert v.ingest(c[4][0], 5_000).disp == QUARANTINE
    assert v.ingest(c[5][0], 30_000).disp == QUARANTINE          # arrives late: its case is not yet eligible at 66 s
    rv = AutoReviewer(RID, "rk:auto:1", rsk, min_age_ms=60_000)
    rv.run(v, 66_000)                                           # seq 3 and 4 released; seq 5 pending -> feed stays forked
    auth = {k for k, _ in v.authoritative()}
    assert ("d1", 0, 3) in auth and ("d1", 0) in v.fork
    late_fork, _ = msg(dsk, wsk, 3, c[2][1], 3_000, val=55.0)    # conflicting version of the RELEASED seq 3
    v.ingest(late_fork, 67_000)
    assert v.reg.slots[("d1", 0, 3)].state() == CONTESTED
    assert ("d1", 0, 3) not in {k for k, _ in v.authoritative()}
    v.finalize(400_000)
    a = audit_pbti(v, replay=True)
    assert a["pass"], a["findings"]


# ------------------------------------------------------------------ admission vs state determinism
def test_state_determinism_for_fixed_admitted_set_pbti_and_b5_strict():
    for cls, kw in ((PBTIVerifier, {}), (B5FeedLevel, {"recovery": False})):
        finals = set()
        _, _, dsk, wsk, _, _ = env()
        c = chain(dsk, wsk, 4)
        forged, _ = msg(dsk, wsk, 2, c[1][1], 2_500, val=5.0)
        wires = [w for w, _ in c] + [forged]
        for perm in itertools.permutations(range(len(wires))):
            v = env(cls=cls, **kw)[0]
            for j, i in enumerate(perm):
                v.ingest(wires[i], 10_000 + j)
            finals.add(tuple(sorted((k, s.state(), v.is_authoritative(k, s)) for k, s in v.reg.slots.items())))
        assert len(finals) == 1, cls


def test_admission_depends_on_arrival_time():
    v1, _, dsk, wsk, _, _ = env({"h_max_ms": 5_000})
    v2 = env({"h_max_ms": 5_000})[0]
    w, _ = msg(dsk, wsk, 0, None, 1_000)
    assert v1.ingest(w, 2_000).disp == ACCEPT                    # fresh -> admitted
    assert v2.ingest(w, 9_000).disp == QUARANTINE                # same statement, later -> not admitted
    assert ({k for k, _ in v1.authoritative()} != {k for k, _ in v2.authoritative()})


def test_corroboration_rule():
    assert corroborated({"cd": "a", "prev": "p", "slot_digests": ["a"], "pred_digests": ["p"],
                         "pred_authoritative": True, "succ_implied": []})
    assert corroborated({"cd": "a", "prev": None, "slot_digests": ["a"], "pred_digests": [],
                         "pred_authoritative": False, "succ_implied": ["a"]})
    assert not corroborated({"cd": "a", "prev": "p", "slot_digests": ["a", "b"], "pred_digests": ["p"],
                             "pred_authoritative": True, "succ_implied": []})
    assert not corroborated({"cd": "a", "prev": None, "slot_digests": ["a"], "pred_digests": [],
                             "pred_authoritative": False, "succ_implied": []})
