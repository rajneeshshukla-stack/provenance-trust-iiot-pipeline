#!/usr/bin/env python3
"""Exploratory check (evidence level B): how much of B5's lower exposure in the mixed workload comes from
inconsistencies of the simulated impersonation attacker?

The registered mixed workload (S99) uses scenarios.ImpersonationHook, whose docstring promises an internally
consistent forged stream. The simulated reviewer A found three leaks: (i) it acts only on deliveries labelled "legit",
so transport duplicates ("legit-dup") of the suppressed genuine messages reach the verifier; (ii) on a retransmission
it forges a new content (fresh random nonce) for the same identity, with `prev` set to its own previous forgery;
(iii) it chains `prev` in delivery order, not sequence order. Each leak gives both pipelines contradictory evidence.

This script re-runs selected registered specifications unchanged (experiments/run_v4.py:expand on the frozen
configuration A1_review.json) twice: once with the registered hook and once with a consistent impersonator of the
same capability (same victims, window, keys and payload change) that chains `prev` by sequence number, re-sends one
cached forgery per identity and also drops transport duplicates in the impersonated range (adapted from the
reviewer's probe, `reports/13_reviewer_simulation/scratch_review_A/probe_mixed2.py`). The repository is not modified:
the hook is replaced in this process only. Outcomes are computed with the repository's own oracle and tracer.

Usage: python3 -B consistent_impersonator_check.py REPO_COPY OUT_JSONL [SEED ...]
"""
import json
import sys
import time
from pathlib import Path

REPO = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2])
SEEDS = [int(s) for s in sys.argv[3:]] or [21, 22, 23, 24, 25]
ARMS = ["PBTI", "B5-hist", "B5-event", "PBTI-R-event"]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "experiments"))
import run_v4  # noqa: E402
from pbti import scenarios as S  # noqa: E402
from pbti.attacks import craft  # noqa: E402
from pbti.crypto import b64u, keypair_from_seed  # noqa: E402
from pbti.envelope import LogicalObs, pbti_content_digest, pbti_obs_dict  # noqa: E402
from pbti.oracle import evaluate  # noqa: E402
from pbti.temporal import temporal_metrics  # noqa: E402

REGISTERED = S.ImpersonationHook


class ConsistentImpersonation:
    """Same victims, window, keys and payload change as the registered hook; one forgery per identity, chained by
    sequence number to the genuine predecessor at the start of the window; transport duplicates dropped."""

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


def spec_for(arm, seed):
    conf = json.loads((REPO / "experiments/v4_configs/A1_review.json").read_text())
    for s in run_v4.expand(conf, [seed]):
        if s["arm"] == arm and s.get("scenario") == "S99_mixed":
            return s
    raise KeyError((arm, seed))


def one(arm, seed, variant):
    S.ImpersonationHook = REGISTERED if variant == "registered" else ConsistentImpersonation
    spec = spec_for(arm, seed)
    kw = {k: v for k, v in spec["cfg"].items() if k in run_v4.CFG_KEYS}
    w = S.build("S99_mixed", spec["system"], seed, **kw)
    w.run()
    r = evaluate(w)
    r.update(temporal_metrics(w))
    return {"arm": arm, "seed": seed, "variant": variant, "O1": r["nonlegit_auth"], "O2": r["legit_missing"],
            "NLX": r["tm_nl_rec_s"], "W": r["tm_wh_rec_s"] / max(1, r["tm_reach"]), "AV5": r["tm_avail_5s"],
            "impersonation_receipts": dict(w.receipts_by_label.get("impersonation", {}))}


if __name__ == "__main__":
    done = set()
    if OUT.exists():
        done = {(json.loads(l)["arm"], json.loads(l)["seed"], json.loads(l)["variant"]) for l in open(OUT)}
    stored = {}
    for line in open(REPO / "results/v4/raw/A1_review.jsonl"):
        x = json.loads(line)
        if x.get("scenario") == "S99_mixed":
            stored[(x["arm"], x["seed"])] = x
    with open(OUT, "a") as f:
        for seed in SEEDS:
            for arm in ARMS:
                for variant in ("registered", "consistent"):
                    if (arm, seed, variant) in done:
                        continue
                    t0 = time.time()
                    rec = one(arm, seed, variant)
                    if variant == "registered":        # the unchanged run must reproduce the stored row
                        st = stored[(arm, seed)]
                        rec["matches_stored"] = (rec["O1"] == st["nonlegit_auth"] and rec["O2"] == st["legit_missing"]
                                                 and abs(rec["NLX"] - st["tm_nl_rec_s"]) < 1e-6)
                    rec["run_s"] = round(time.time() - t0, 1)
                    f.write(json.dumps(rec) + "\n")
                    f.flush()
                    print(json.dumps(rec), flush=True)
