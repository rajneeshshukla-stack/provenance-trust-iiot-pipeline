#!/usr/bin/env python3
"""A5 (memo R09): deterministic lifecycle matrix for revocation, quarantine, reviewed release and later taint.

Each case is a hand-specified timeline on the real verifier (PBTI and B5 classes) with a device key d1 and relay key
g1, true compromise of both keys at t_c = 10 s, revocation observed at 20 s with the supplied compromise time t_comp,
reviewer decisions at 30 s (signed by an authorized reviewer key), and ticks until 60 s. Policies of the
REVOKED_BUFFERED waiver: none | discretionary (V3: device timestamp before t_comp) | witness (exact-content token from a
TimeWitness before t_low, src/pbti/timewitness.py). The ground-truth label of every record (legitimate or forged)
is known to this script only, not to the verifier.

Output: results/v4/summary/A5_lifecycle_matrix.json and .csv (one row per case x policy x pipeline).
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pbti.b5 import B5FeedLevel  # noqa: E402
from pbti.crypto import b64u, keypair_from_seed, sha256_hex  # noqa: E402
from pbti.envelope import LogicalObs, pbti_content_digest, pbti_sign_obs, pbti_wire  # noqa: E402
from pbti.identity import TrustRegistry  # noqa: E402
from pbti.policy import PolicyStore  # noqa: E402
from pbti.review import RELEASABLE, AutoReviewer, sign_decision  # noqa: E402
from pbti.timewitness import TimeWitness  # noqa: E402
from pbti.verifier import PBTIVerifier  # noqa: E402

SEED = b"v4-a5"
WID = "spiffe://plant-a.example/cell1/gw1/collector"
RID = "urn:pbti:reviewer:auto"
T_C, T_REV, T_REVIEW, T_END = 10_000, 20_000, 30_000, 60_000
POLICIES = ("none", "discretionary", "witness")
H10_CASES = {"stale_reviewer_snapshot", "stale_ts_release_after_origin_revoked", "release_then_later_taint"}


class Env:
    def __init__(self, cls, policy, params=None, width_ms=0):
        self.trust = TrustRegistry(SEED, use_x509=False)
        self.dsk, dpk = keypair_from_seed(SEED, "dk:d1:1")
        self.wsk, wpk = keypair_from_seed(SEED, "wk:g1:1")
        self.rsk, rpk = keypair_from_seed(SEED, "rk:auto:1")
        self.trust.issue("dk:d1:1", "device", "d1", dpk, -60_000, 10 ** 10)
        self.trust.issue("wk:g1:1", "workload", WID, wpk, -60_000, 10 ** 10)
        self.trust.issue("rk:auto:1", "reviewer", RID, rpk, -60_000, 10 ** 10)
        doc = {"devices": {"d1": {"assets": ["a1"], "origin": "device", "schemas": ["s"]}},
               "workloads": {WID: {"relay": ["d1"]}}, "params": dict(params or {}),
               "reviewers": {RID: {"may_release": list(RELEASABLE), "active": True}}}
        self.v = cls(self.trust, PolicyStore(doc), keypair_from_seed(SEED, "verifier"))
        self.v.release_evidence = policy
        self.witness = TimeWitness(SEED, eps_ms=1_000)
        self.v.witness = self.witness
        if width_ms:
            for k in ("dk:d1:1", "wk:g1:1"):
                self.v.compromise_low[k] = T_C - width_ms // 2
        self.rv = AutoReviewer(RID, "rk:auto:1", self.rsk, min_age_ms=0, rule="oneshot")

    def msg(self, seq, prev, ts, val, mode):
        o = LogicalObs("d1", "a1", 0, seq, ts, "s", {"x": val}, f"m{seq}-{val}", prev)
        obs, osig = pbti_sign_obs(o, self.dsk, "dk:d1:1")
        return pbti_wire(obs, osig, WID, "wk:g1:1", self.wsk, ts, mode), b64u(pbti_content_digest(obs))

    def revoke(self, t_comp=T_C):
        for k in ("dk:d1:1", "wk:g1:1"):
            self.trust.revoke(k, T_REV, t_comp, "incident-response")

    def auth(self):
        return {k for k, _ in self.v.authoritative()}


def _prefix(e):
    """Genuine G0, G1 admitted live before the compromise."""
    g0, c0 = e.msg(0, None, 1_000, 1.0, "live")
    g1, c1 = e.msg(1, c0, 2_000, 2.0, "live")
    e.v.ingest(g0, 1_100)
    e.v.ingest(g1, 2_100)
    return c1


def _finish(e, wire, legit, extra=None):
    wd = sha256_hex(wire)
    for t in range(T_REVIEW + 1_000, T_END + 1, 1_000):
        e.v.advance(t)
    s = e.v.reg.slots.get(("d1", 0, 2))
    out = {"legitimate": legit, "case_state": (e.v.qcases.get(wd) or {}).get("state"),
           "authoritative_end": ("d1", 0, 2) in e.auth(), "tainted_end": bool(s and s.tainted),
           "review_outcomes": dict(e.v.review_outcomes)}
    out["malicious_authoritative"] = out["authoritative_end"] and not legit
    out["genuine_recovered"] = out["authoritative_end"] and legit
    out["genuine_withheld"] = legit and not out["authoritative_end"]
    out.update(extra or {})
    return out


def case_legit_buffered_witnessed(e):
    c1 = _prefix(e)
    g2, c2 = e.msg(2, c1, 5_000, 3.0, "buffered")
    e.witness.stamp(c2, 5_000)                         # gateway presented it to the witness before the compromise
    e.revoke()
    e.v.ingest(g2, 25_000)                             # delivered after the revocation: QUARANTINE REVOKED_BUFFERED
    e.rv.run(e.v, T_REVIEW)
    return _finish(e, g2, True)


def case_backdated_forgery(e, attacker_stamps=True):
    c1 = _prefix(e)
    f2, cf = e.msg(2, c1, 6_000, 99.0, "buffered")     # forged at 15 s with a timestamp before the compromise
    if attacker_stamps:
        e.witness.stamp(cf, 15_000)                    # the witness first sees it after the compromise
    e.revoke()
    e.v.ingest(f2, 25_000)
    e.rv.run(e.v, T_REVIEW)                            # corroborated: predecessor G1 is authoritative and named by prev
    return _finish(e, f2, False)


def case_contradictory_successor(e):
    c1 = _prefix(e)
    f2, cf = e.msg(2, c1, 6_000, 99.0, "buffered")
    g2, c2 = e.msg(2, c1, 5_000, 3.0, "buffered")
    g3, _ = e.msg(3, c2, 7_000, 4.0, "live")
    e.v.ingest(g3, 7_100)                              # genuine successor admitted before the compromise
    e.revoke()
    e.v.ingest(f2, 25_000)
    e.rv.run(e.v, T_REVIEW)
    return _finish(e, f2, False)


def case_witness_outage(e):
    c1 = _prefix(e)
    g2, c2 = e.msg(2, c1, 5_000, 3.0, "buffered")
    e.witness.up = False
    e.witness.stamp(c2, 5_000)                         # refused: witness unreachable
    e.witness.up = True
    e.revoke()
    e.v.ingest(g2, 25_000)
    e.rv.run(e.v, T_REVIEW)
    return _finish(e, g2, True)


def case_stale_snapshot(e):
    """A decision bound to a snapshot that new admitted evidence has superseded is refused (STALE_REVIEW) and the case
    returns to QUARANTINED; a fresh review of the current evidence then decides it. No revocation in this case."""
    c1 = _prefix(e)
    g2, c2 = e.msg(2, c1, 5_000, 3.0, "buffered")
    e.v.ingest(g2, 18_000)                             # beyond the 10 s horizon: QUARANTINE STALE_TS
    wd = sha256_hex(g2)
    snap = e.v.open_review(wd, RID, 19_000)
    g3, _ = e.msg(3, c2, 19_200, 4.0, "live")          # genuine successor admitted after the snapshot was taken
    e.v.ingest(g3, 19_300)
    d = sign_decision({"case": wd, "reviewer": RID, "rkid": "rk:auto:1", "decision": "RELEASE", "reason": "TEST",
                       "snapshot": snap, "t": 19_500}, e.rsk)
    out1 = e.v.apply_review(d, 19_500)["outcome"]
    state_after_stale = e.v.qcases[wd]["state"]
    e.rv.run(e.v, T_REVIEW)                            # fresh snapshot: corroborated by the successor link
    return _finish(e, g2, True, {"first_decision": out1, "state_after_first_decision": state_after_stale})


def case_revoked_reviewer(e):
    c1 = _prefix(e)
    g2, c2 = e.msg(2, c1, 5_000, 3.0, "buffered")
    e.witness.stamp(c2, 5_000)
    e.revoke()
    e.trust.revoke("rk:auto:1", 28_000, None, "reviewer-key-loss")
    e.v.ingest(g2, 25_000)
    e.rv.run(e.v, T_REVIEW)
    return _finish(e, g2, True)


def case_stale_ts_then_revoked_origin(e):
    c1 = _prefix(e)
    g2, c2 = e.msg(2, c1, 5_000, 3.0, "buffered")
    e.witness.stamp(c2, 5_000)
    e.v.ingest(g2, 18_000)                             # beyond the 10 s horizon: QUARANTINE STALE_TS (not yet revoked)
    e.revoke()
    e.rv.run(e.v, T_REVIEW)                            # release waives STALE_TS only; the revoked keys still apply
    return _finish(e, g2, True)


def case_release_then_taint(e):
    c1 = _prefix(e)
    g2, c2 = e.msg(2, c1, 5_000, 3.0, "buffered")
    e.v.ingest(g2, 18_000)                             # STALE_TS
    e.rv.run(e.v, 19_000)                              # released at 19 s, before any revocation
    rel = ("d1", 0, 2) in e.auth()
    for k in ("dk:d1:1", "wk:g1:1"):
        e.trust.revoke(k, T_REV, 12_000, "late-discovery")   # compromise from 12 s: the release (commit 19 s) is tainted
    return _finish(e, g2, True, {"authoritative_after_release": rel})


def case_full_sequence_revised_taint(e):
    """R09 complete sequence: revocation -> REVOKED_BUFFERED quarantine -> authorized review -> release -> revised
    revocation record (earlier compromise time, D05) -> taint -> derived-window correction."""
    c1 = _prefix(e)
    g2, c2 = e.msg(2, c1, 5_000, 3.0, "buffered")
    e.witness.stamp(c2, 5_000)
    e.revoke()                                         # t_comp = 10 s
    e.v.ingest(g2, 25_000)
    e.rv.run(e.v, T_REVIEW)
    for t in range(T_REVIEW + 1_000, 40_001, 1_000):
        e.v.advance(t)
    key = ("d1", 0, 2)
    rel = key in e.auth()
    wk = ("a1", 5_000 - 5_000 % e.v.cfg.window_ms)
    n_before = len(e.v.proc.versions.get(wk, []))
    in_window_after_release = bool(e.v.proc.versions.get(wk)) and any(
        c[2] == 5_000 for c in e.v.proc.versions[wk][-1]["ckeys"])
    for k in ("dk:d1:1", "wk:g1:1"):
        e.trust.revoke(k, 40_000, 4_000, "forensic-revision")   # compromise now believed to start at 4 s
    out = _finish(e, g2, True)
    vers = e.v.proc.versions.get(wk, [])
    out.update({"authoritative_after_release": rel, "in_window_after_release": in_window_after_release,
                "window_versions_added": len(vers) - n_before,
                "window_corrected": bool(vers) and all(c[2] != 5_000 for c in vers[-1]["ckeys"])
                and vers[-1]["cause"] == "TAINT_CORRECTION"})
    return out


CASES = {"legit_buffered_witnessed": case_legit_buffered_witnessed,
         "backdated_forgery_witness_sees_late": case_backdated_forgery,
         "backdated_forgery_not_witnessed": lambda e: case_backdated_forgery(e, attacker_stamps=False),
         "forgery_with_contradictory_successor": case_contradictory_successor,
         "legit_buffered_witness_outage": case_witness_outage,
         "stale_reviewer_snapshot": case_stale_snapshot,
         "revoked_reviewer": case_revoked_reviewer,
         "stale_ts_release_after_origin_revoked": case_stale_ts_then_revoked_origin,
         "release_then_later_taint": case_release_then_taint,
         "full_sequence_revised_taint": case_full_sequence_revised_taint}


def run_all():
    rows = []
    for cls in (PBTIVerifier, B5FeedLevel):
        for case, fn in CASES.items():
            for pol in POLICIES:
                params = {"h_max_ms": 10_000} if case in H10_CASES else {}
                e = Env(cls, pol, params)
                r = fn(e)
                rows.append({"pipeline": cls.name, "case": case, "policy": pol, "width_s": 0, **r})
        # uncertainty interval of the compromise time (witness policy only; t_low = t_c - width/2)
        for w in (0, 5_000, 30_000, 120_000):
            e = Env(cls, "witness", {}, width_ms=w)
            r = case_legit_buffered_witnessed(e)
            rows.append({"pipeline": cls.name, "case": "legit_buffered_witnessed_interval", "policy": "witness",
                         "width_s": w / 1000, **r})
    return rows


def main():
    rows = run_all()
    out = ROOT / "results" / "v4" / "summary"
    out.mkdir(parents=True, exist_ok=True)
    (out / "A5_lifecycle_matrix.json").write_text(json.dumps(rows, indent=1, default=str))
    keys = ["pipeline", "case", "policy", "width_s", "legitimate", "case_state", "authoritative_end", "tainted_end",
            "malicious_authoritative", "genuine_recovered", "genuine_withheld", "first_decision",
            "state_after_first_decision", "authoritative_after_release", "in_window_after_release",
            "window_versions_added", "window_corrected"]
    with open(out / "A5_lifecycle_matrix.csv", "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        wr.writeheader()
        wr.writerows(rows)
    for r in rows:
        if True:
            print(f"{r['pipeline']:5s} ", end="")
            print(f"{r['case']:42s} {r['policy']:13s} w={r['width_s']:>5} state={str(r['case_state']):9s} "
                  f"auth={r['authoritative_end']!s:5s} taint={r['tainted_end']!s:5s} legit={r['legitimate']!s:5s} "
                  f"{r.get('first_decision', '')}")


if __name__ == "__main__":
    main()
