"""Quarantine review and release workflow (added in V3).

Case states (one case per quarantined wire digest):
    QUARANTINED  -> REVIEW_PENDING -> RELEASED
                                   -> REJECTED
No quarantined observation becomes authoritative except through a RELEASED decision, and a release only
re-runs the normal admission pipeline with the single original quarantine reason waived; every other check
(signatures, key binding, credential status, policy, Rule L) applies again at release time.

A reviewer is an identity with a credential of kind "reviewer" in the trust registry and an entry in the
policy document:  doc["reviewers"][reviewer_id] = {"may_release": [reasons], "active": true}.
Decisions are signed by the reviewer (Ed25519, DOMAIN_REVIEW) over the canonical decision body; the verifier
checks signature, credential binding, revocation status and authorization, and that the evidence snapshot the
reviewer examined is still current (otherwise the decision is STALE and the case returns to QUARANTINED).
Every decision (including refused ones) is written to the evidence log as a REVIEW record, so the auditor can
replay it.

The AutoReviewer below is an operational policy, not part of the verifier: it releases a case only if the
observation is corroborated by at least one hash link (its predecessor is authoritative with exactly the digest
named by `prev`, or a successor's `prev` names exactly its digest) and no conflicting version is known.

V4 adds two operational options without changing the release predicate (`corroborated`):
  * rule="oneshot" (V3 behaviour, default): a reviewed case that is not corroborated is REJECTED for good.
  * rule="defer": a case is RELEASED if corroborated, REJECTED only if it is contradicted (`contradicted`: a different
    digest is known for its slot, or its `prev` contradicts the known predecessor digests), and otherwise left
    QUARANTINED, unopened, for a later review. This separates review timing from the rule's patience (decision D03).
  * run_on(): review a given candidate set (used by event-driven review in src/pbti/sim.py).
Hash-link corroboration is a consistency check, not independent evidence: a party holding the relevant signing keys
can produce mutually consistent records.
"""
from __future__ import annotations

from typing import Optional

from .canonical import canonical_bytes
from .crypto import DOMAIN_REVIEW, b64u, keypair_from_seed, sign

QUARANTINED, REVIEW_PENDING, RELEASED, REJECTED = "QUARANTINED", "REVIEW_PENDING", "RELEASED", "REJECTED"

# reasons an authorized reviewer may release; the others (SEQ_JUMP, KEY_EXPIRED, FUTURE_TS) are refused by policy
RELEASABLE = ("STALE_TS", "STALE_SLOT", "STALE_EPOCH", "REVOKED_BUFFERED", "FEED_FORK_HOLD")
DECISION_FIELDS = ("case", "reviewer", "rkid", "decision", "reason", "snapshot", "t")


def decision_body(d: dict) -> bytes:
    return canonical_bytes({k: d[k] for k in DECISION_FIELDS})


def sign_decision(d: dict, sk) -> dict:
    d = dict(d)
    d["sig"] = b64u(sign(sk, DOMAIN_REVIEW, decision_body(d)))
    return d


def contradicted(snap: dict) -> bool:
    """V4 (rule="defer"): the admitted evidence contradicts this exact content: another digest is known for its slot,
    or its prev link names a digest that the known predecessor evidence does not contain."""
    if snap.get("slot_digests") not in ([], [snap["cd"]]):
        return True
    pd = snap.get("pred_digests") or []
    return bool(snap.get("prev") is not None and pd and snap["prev"] not in pd)


def corroborated(snap: dict) -> bool:
    """At least one hash link vouches for exactly this content digest."""
    if snap.get("slot_digests") not in ([], [snap["cd"]]):
        return False                                 # a conflicting version or implied digest is known
    if snap.get("prev") is not None and snap.get("pred_digests") == [snap["prev"]] and snap.get("pred_authoritative"):
        return True
    if snap.get("succ_implied") == [snap["cd"]]:
        return True
    return False


class AutoReviewer:
    """Periodic automated reviewer used in the experiments (operator policy; see module docstring)."""

    def __init__(self, reviewer_id: str, kid: str, sk, min_age_ms: int = 60_000, reasons=RELEASABLE, rule: str = "oneshot"):
        if rule not in ("oneshot", "defer"):
            raise ValueError(rule)
        self.id, self.kid, self.sk = reviewer_id, kid, sk
        self.min_age_ms = min_age_ms
        self.reasons = tuple(reasons)
        self.rule = rule
        self.decisions = 0
        self.deferrals = 0

    @staticmethod
    def provision(trust, seedb: bytes, label: str = "rk:auto:1", subject: str = "urn:pbti:reviewer:auto",
                  nbf_ms: int = -60_000, exp_ms: int = 10 * 365 * 86_400_000):
        sk, pk = keypair_from_seed(seedb, label)
        trust.issue(label, "reviewer", subject, pk, nbf_ms, exp_ms)
        return subject, label, sk

    def eligible(self, v, t: int, wds=None) -> list[str]:
        """Eligible cases (all, or among `wds`) in deterministic identity order, so that a released predecessor can
        corroborate its successor in the same pass."""
        src = v.qcases.items() if wds is None else ((wd, v.qcases[wd]) for wd in set(wds) if wd in v.qcases)
        out = [wd for wd, c in src
               if c["state"] == QUARANTINED and c["reason"] in self.reasons and t - c["t_q"] >= self.min_age_ms]
        out.sort(key=lambda wd: (tuple(map(str, v.qcases[wd].get("eid") or ["", "", ""]))[:2],
                                 _seq(v.qcases[wd].get("eid")), wd))
        return out

    def run(self, v, t: int) -> list[dict]:
        """Review every eligible case once (periodic review)."""
        return self.run_on(v, t, None)

    def run_on(self, v, t: int, wds) -> list[dict]:
        out = []
        if self.rule == "defer":
            v.advance(t)                         # peek at the same evidence state that open_review would see
        for wd in self.eligible(v, t, wds):
            if self.rule == "defer":
                peek = v.review_snapshot(wd)
                if peek is None:
                    continue
                if not corroborated(peek) and not contradicted(peek):
                    self.deferrals += 1
                    continue                     # leave the case QUARANTINED (unopened) for a later review
            snap = v.open_review(wd, self.id, t)
            if snap is None:
                continue
            dec = "RELEASE" if corroborated(snap) else "REJECT"
            d = sign_decision({"case": wd, "reviewer": self.id, "rkid": self.kid, "decision": dec,
                               "reason": "CORROBORATED_BY_HASH_LINK" if dec == "RELEASE" else "UNCORROBORATED_OR_CONFLICTING",
                               "snapshot": snap, "t": t}, self.sk)
            out.append(v.apply_review(d, t))
            self.decisions += 1
        return out


def _seq(eid: Optional[list]) -> int:
    try:
        return int(eid[2])
    except Exception:  # noqa: BLE001
        return -1
