"""V4 (memo R09/A5): a time-stamping witness for exact-content pre-compromise evidence (testbed component).

A witness outside the verifier's control signs (statement digest, witness time) for digests submitted to it, e.g.
by a gateway when it accepts an observation into its buffer. A token is evidence that this exact signed statement
existed at the witness time; it is not evidence that the measurement is physically true, and a statement that the
witness first sees after a compromise cannot be certified as pre-compromise. The trust model is explicit: the
witness key and clock are trusted; its clock uncertainty `eps_ms` is subtracted from the evidence margin.

The verifier's REVOKED_BUFFERED release waiver (src/pbti/verifier.py, `release_evidence`) then has three policies:
  * "none":          no observation under a revoked key is ever released;
  * "discretionary": V3 behaviour: released if the observation's own (device-asserted) timestamp precedes t_comp;
                     a key holder can backdate, so this is a release-policy condition, not evidence;
  * "witness":       released only if a valid witness token for the exact statement digest has a witness time
                     t_w with t_w + eps_ms < t_low, where t_low is the earliest plausible compromise time (the
                     revocation's t_comp; with an uncertainty interval [t_low, t_high] the caller supplies t_low).
"""
from __future__ import annotations

from typing import Optional

from .canonical import canonical_bytes
from .crypto import b64u, keypair_from_seed, sign, ub64u, verify

DOMAIN_WITNESS = b"PBTI-v1/time-witness\x00"


class TimeWitness:
    def __init__(self, seedb: bytes, wid: str = "urn:pbti:witness:tsa", eps_ms: int = 1_000):
        self.wid = wid
        self.eps_ms = eps_ms
        self.sk, self.pk = keypair_from_seed(seedb, "witness-key:" + wid)
        self.up = True
        self.tokens: dict[str, dict] = {}       # cd -> earliest token
        self.submissions = 0
        self.refused = 0

    def stamp(self, cd: str, t: int) -> Optional[dict]:
        """Record that the exact statement with digest cd was presented at witness time t (None during an outage)."""
        self.submissions += 1
        if not self.up:
            self.refused += 1
            return None
        if cd in self.tokens:
            return self.tokens[cd]
        body = {"cd": cd, "t": int(t), "wit": self.wid}
        tok = dict(body, sig=b64u(sign(self.sk, DOMAIN_WITNESS, canonical_bytes(body))))
        self.tokens[cd] = tok
        return tok

    def token_for(self, cd: str) -> Optional[dict]:
        return self.tokens.get(cd)

    def valid(self, tok: dict) -> bool:
        try:
            body = {"cd": tok["cd"], "t": tok["t"], "wit": tok["wit"]}
            return tok["wit"] == self.wid and verify(self.pk, DOMAIN_WITNESS, canonical_bytes(body), ub64u(tok["sig"]))
        except Exception:  # noqa: BLE001
            return False

    def proves_before(self, cd: str, t_low: int) -> bool:
        tok = self.token_for(cd)
        return tok is not None and self.valid(tok) and tok["t"] + self.eps_ms < t_low
