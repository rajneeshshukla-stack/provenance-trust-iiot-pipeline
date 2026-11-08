"""Consistent impersonation attacker for the mixed workload (S99), used by the V9 robustness campaign (E04).

Same capability as the registered attacker (scenarios.ImpersonationHook: same victims, window, device and relay
keys, same payload change); it differs only where the registered hook leaks contradictory evidence:
  * one forged statement per identity, cached and re-sent unchanged on retransmission (the registered hook forges a
    new content, with a fresh nonce, for every retransmission of the same identity);
  * `prev` is chained by sequence number to the attacker's own forged predecessor, and at the start of the window to
    the genuine predecessor (the registered hook chains in delivery order);
  * transport duplicates ("legit-dup") of suppressed genuine messages in the impersonated range are dropped (the
    registered hook acts only on deliveries labelled "legit").
The logic is that of tools/v7/consistent_impersonator_check.py (V7 exploratory check, five seeds), moved into an
importable module without change.
"""
from __future__ import annotations

import json

from pbti.attacks import craft
from pbti.crypto import b64u, keypair_from_seed
from pbti.envelope import LogicalObs, pbti_content_digest, pbti_obs_dict


class ConsistentImpersonation:
    def __init__(self, victims, t0, t1):
        self.victims, self.t0, self.t1 = victims, t0, t1
        self.F, self.rng = {}, {}

    def _range(self, world, did):
        a = [tr["o"].seq for tr in world.truth if tr["did"] == did and tr["t"] >= self.t0]
        b = [tr["o"].seq for tr in world.truth if tr["did"] == did and tr["t"] >= self.t1]
        return (min(a) if a else None), (min(b) if b else 10 ** 9)

    @staticmethod
    def _genuine(world, did, ep, seq):
        for tr in world.truth:
            o = tr["o"]
            if tr["did"] == did and o.ep == ep and o.seq == seq:
                return o
        return None

    def _forge(self, world, d, g, ep, seq, s0, kid):
        key = (d.did, ep, seq)
        if key not in self.F:
            G = self._genuine(world, d.did, ep, seq)
            if seq == s0:
                Gp = self._genuine(world, d.did, ep, seq - 1)
                prev = b64u(pbti_content_digest(pbti_obs_dict(Gp, kid))) if Gp is not None and seq > 0 else None
            else:
                prev = self._forge(world, d, g, ep, seq - 1, s0, kid)[2]
            f = LogicalObs(d.did, G.aid, ep, seq, G.ts, G.sch, dict(G.pl, temp_c=round(G.pl["temp_c"] + 9.0, 2)),
                           "0" * 16, prev)
            sk = keypair_from_seed(world.seedb, kid)[0]
            w2, m2 = craft(world, f, (sk, kid), g, (g.sk, g.kid))
            self.F[key] = (w2, m2, b64u(pbti_content_digest(pbti_obs_dict(f, kid))))
        return self.F[key]

    def __call__(self, world, gw, e, wire, meta, label):
        if label not in ("legit", "legit-dup") or world.now < self.t0:
            return None
        try:
            o = json.loads(wire)["obs"]
        except Exception:  # noqa: BLE001
            return None
        did = o["did"]
        if did not in self.victims:
            return None
        if did not in self.rng:
            self.rng[did] = self._range(world, did)
        s0, s1 = self.rng[did]
        if s0 is None or not (s0 <= o["seq"] < s1):
            return None
        if label == "legit-dup":
            return "DROP"
        d = world.devices[did]
        g = world.gateways[d.g - 1]
        w2, m2, _ = self._forge(world, d, g, o["ep"], o["seq"], s0, o["kid"])
        world.attack_log.append({"t": world.now, "type": "impersonation"})
        return w2, dict(m2), "impersonation"
