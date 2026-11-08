"""V4 (memo A0): independently, manually derived expected traces on the unmodified verifier.

Each trace lists, written down by hand from the protocol specification (docs/PROTOCOL_SPECIFICATION.md) and not
computed by the implementation, the expected disposition of every receipt and the expected final Rule L classes and
authority. Covered: retry, replay outside the retry window, equivocation, gap-fill contest in both successor orders,
missing successor (the known residual risk), rotation grace and expiry, revocation and taint, stale review snapshot,
LOST release and release-then-taint with derived-window correction.
"""
from pbti.crypto import b64u, keypair_from_seed, sha256_hex
from pbti.envelope import LogicalObs, pbti_content_digest, pbti_sign_obs, pbti_wire
from pbti.identity import TrustRegistry
from pbti.policy import PolicyStore
from pbti.review import RELEASABLE, sign_decision
from pbti.verifier import PBTIVerifier

SEED = b"v4-oracle-traces"
WID = "spiffe://plant-a.example/cell1/gw1/collector"
RID = "urn:pbti:reviewer:auto"


class T:
    def __init__(self, params=None, k1_exp=10 ** 12):
        self.tr = TrustRegistry(SEED, use_x509=False)
        self.d1, p1 = keypair_from_seed(SEED, "dk:d1:1")
        self.d2, p2 = keypair_from_seed(SEED, "dk:d1:2")
        self.w, pw = keypair_from_seed(SEED, "wk:g1:1")
        self.r, pr = keypair_from_seed(SEED, "rk:auto:1")
        self.tr.issue("dk:d1:1", "device", "d1", p1, -60_000, k1_exp)
        self.tr.issue("dk:d1:2", "device", "d1", p2, -60_000, 10 ** 12)
        self.tr.issue("wk:g1:1", "workload", WID, pw, -60_000, 10 ** 12)
        self.tr.issue("rk:auto:1", "reviewer", RID, pr, -60_000, 10 ** 12)
        doc = {"devices": {"d1": {"assets": ["a1"], "origin": "device", "schemas": ["s"]}},
               "workloads": {WID: {"relay": ["d1"]}}, "params": dict(params or {}),
               "reviewers": {RID: {"may_release": list(RELEASABLE), "active": True}}}
        self.v = PBTIVerifier(self.tr, PolicyStore(doc), keypair_from_seed(SEED, "verifier"))

    def st(self, seq, prev, ts, val, mode="live", key=1):
        o = LogicalObs("d1", "a1", 0, seq, ts, "s", {"x": val}, f"m{seq}-{val}-{key}", prev)
        sk, kid = (self.d1, "dk:d1:1") if key == 1 else (self.d2, "dk:d1:2")
        obs, osig = pbti_sign_obs(o, sk, kid)
        return pbti_wire(obs, osig, WID, "wk:g1:1", self.w, ts, mode), b64u(pbti_content_digest(obs))

    def rx(self, wire, t):
        r = self.v.ingest(wire, t)
        return f"{r.disp}/{r.why.split(':')[0]}"

    def cls(self, seq):
        s = self.v.reg.slots.get(("d1", 0, seq))
        return "ABSENT" if s is None else s.state()

    def auth(self, seq):
        return ("d1", 0, seq) in {k for k, _ in self.v.authoritative()}


def test_retry_and_replay():
    t = T()
    g0, _ = t.st(0, None, 1_000, 1.0)
    assert [t.rx(g0, 1_100), t.rx(g0, 2_000), t.rx(g0, 40_000)] == \
        ["ACCEPT/COMMITTED", "DUPLICATE/RETRY", "DUPLICATE/SUSPECTED_REPLAY"]
    assert t.cls(0) == "COMMITTED" and t.auth(0)


def test_equivocation_contests_and_withdraws():
    t = T()
    g0, c0 = t.st(0, None, 1_000, 1.0)
    g1, _ = t.st(1, c0, 2_000, 2.0)
    f1, _ = t.st(1, c0, 2_000, 99.0)
    assert [t.rx(g0, 1_100), t.rx(g1, 2_100), t.rx(f1, 2_200)] == \
        ["ACCEPT/COMMITTED", "ACCEPT/COMMITTED", "CONFLICT/EQUIVOCATION"]
    assert (t.cls(1), t.auth(1), t.cls(0), t.auth(0)) == ("CONTESTED", False, "COMMITTED", True)


def test_gap_fill_contested_in_both_successor_orders():
    expected = {0: "COMMITTED", 1: "CONTESTED", 2: "COMMITTED"}
    for order in ("forgery_first", "successor_first"):
        t = T()
        g0, c0 = t.st(0, None, 1_000, 1.0)
        g1, c1 = t.st(1, c0, 2_000, 2.0)          # genuine G1 is never delivered (suppressed)
        f1, _ = t.st(1, c0, 2_000, 99.0)           # gap-fill forgery copies the predecessor link
        g2, _ = t.st(2, c1, 3_000, 3.0)            # genuine successor names G1
        t.rx(g0, 1_100)
        if order == "forgery_first":
            assert [t.rx(f1, 2_100), t.rx(g2, 3_100)] == ["ACCEPT/COMMITTED", "ACCEPT/COMMITTED"]
        else:
            assert [t.rx(g2, 3_100), t.rx(f1, 3_200)] == ["ACCEPT/COMMITTED", "CONFLICT/LINK_MISMATCH"]
        assert {q: t.cls(q) for q in (0, 1, 2)} == expected and not t.auth(1) and t.auth(2)


def test_missing_successor_leaves_forgery_committed():
    """The documented residual risk: no contradictory evidence, so Rule L cannot contest the forgery."""
    t = T()
    g0, c0 = t.st(0, None, 1_000, 1.0)
    f1, _ = t.st(1, c0, 2_000, 99.0)
    assert [t.rx(g0, 1_100), t.rx(f1, 2_100)] == ["ACCEPT/COMMITTED", "ACCEPT/COMMITTED"]
    assert t.cls(1) == "COMMITTED" and t.auth(1)


def test_rotation_grace_then_expiry():
    t = T({"rotation_grace_ms": 3_000}, k1_exp=4_000)
    g0, c0 = t.st(0, None, 5_500, 1.0)
    g1, _ = t.st(1, c0, 8_500, 2.0)
    r = t.v.ingest(g0, 6_000)                                   # 2 s after expiry: within grace
    assert (r.disp, "KEY_IN_GRACE:device" in r.ann) == ("ACCEPT", True)
    assert t.rx(g1, 9_000) == "QUARANTINE/KEY_EXPIRED"          # 5 s after expiry: beyond grace


def test_revocation_rejects_quarantines_and_taints():
    t = T()
    g0, c0 = t.st(0, None, 1_000, 1.0)
    g1, c1 = t.st(1, c0, 6_000, 2.0)
    g2, _ = t.st(2, c1, 6_500, 3.0, mode="buffered")
    assert t.rx(g0, 2_000) == "ACCEPT/COMMITTED"
    t.tr.revoke("dk:d1:1", 5_000, 0, "test")                    # compromise since 0: commit at 2 s is tainted
    assert [t.rx(g1, 6_100), t.rx(g2, 6_600)] == ["REJECT/REVOKED", "QUARANTINE/REVOKED_BUFFERED"]
    t.v.advance(8_000)
    assert t.v.reg.slots[("d1", 0, 0)].tainted and not t.auth(0)


def test_stale_snapshot_refused():
    t = T({"h_max_ms": 10_000})
    g0, c0 = t.st(0, None, 1_000, 1.0)
    g1, c1 = t.st(1, c0, 2_000, 2.0, mode="buffered")
    g2, _ = t.st(2, c1, 16_000, 3.0)
    t.rx(g0, 1_100)
    assert t.rx(g1, 15_000) == "QUARANTINE/STALE_TS"
    wd = sha256_hex(g1)
    snap = t.v.open_review(wd, RID, 15_500)
    assert t.rx(g2, 16_100) == "ACCEPT/COMMITTED"                # new successor evidence after the snapshot
    d = sign_decision({"case": wd, "reviewer": RID, "rkid": "rk:auto:1", "decision": "RELEASE", "reason": "T",
                       "snapshot": snap, "t": 16_500}, t.r)
    assert t.v.apply_review(d, 16_500)["outcome"] == "STALE_REVIEW"
    assert t.v.qcases[wd]["state"] == "QUARANTINED" and t.cls(1) == "ABSENT"


def test_lost_slot_released_by_review():
    t = T({"gap_close_ms": 3_000})
    g0, c0 = t.st(0, None, 1_000, 1.0)
    g1, c1 = t.st(1, c0, 1_500, 2.0, mode="buffered")
    g2, _ = t.st(2, c1, 2_000, 3.0)
    t.rx(g0, 1_100)
    t.rx(g2, 2_100)                                             # opens the gap at sequence 1
    t.v.advance(7_000)                                          # gap older than 3 s: closed
    assert t.cls(1) == "LOST"
    assert t.rx(g1, 7_500) == "QUARANTINE/STALE_SLOT"
    wd = sha256_hex(g1)
    snap = t.v.open_review(wd, RID, 8_000)
    d = sign_decision({"case": wd, "reviewer": RID, "rkid": "rk:auto:1", "decision": "RELEASE", "reason": "T",
                       "snapshot": snap, "t": 8_000}, t.r)
    assert t.v.apply_review(d, 8_000)["outcome"] == "RELEASED"
    assert t.cls(1) == "COMMITTED" and t.auth(1)


def test_release_then_taint_corrects_derived_window():
    t = T({"h_max_ms": 10_000})
    g0, c0 = t.st(0, None, 1_000, 1.0)
    g1, _ = t.st(1, c0, 2_000, 2.0, mode="buffered")
    t.rx(g0, 1_100)
    assert t.rx(g1, 15_000) == "QUARANTINE/STALE_TS"
    wd = sha256_hex(g1)
    snap = t.v.open_review(wd, RID, 16_000)
    d = sign_decision({"case": wd, "reviewer": RID, "rkid": "rk:auto:1", "decision": "RELEASE", "reason": "T",
                       "snapshot": snap, "t": 16_000}, t.r)
    assert t.v.apply_review(d, 16_000)["outcome"] == "RELEASED" and t.auth(1)
    t.v.advance(17_000)
    wk = ("a1", 0)
    assert any(c[2] == 2_000 for c in t.v.proc.versions[wk][-1]["ckeys"])
    t.tr.revoke("dk:d1:1", 18_000, 10_000, "late discovery")    # commit at 16 s >= 10 s: tainted
    t.v.advance(20_000)
    last = t.v.proc.versions[wk][-1]
    assert t.v.reg.slots[("d1", 0, 1)].tainted and not t.auth(1)
    assert last["cause"] == "TAINT_CORRECTION" and all(c[2] != 2_000 for c in last["ckeys"])
    assert t.auth(0)                                            # commit at 1.1 s < t_comp: not tainted
