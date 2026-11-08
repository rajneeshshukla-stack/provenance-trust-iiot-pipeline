#!/usr/bin/env python3
"""V9 E04 negative controls: small deterministic traces on the real verifiers (signed origin and relay statements,
real Rule L / feed-level admission, real automated reviewer) that isolate the failure modes behind the attacker-model
sensitivity.  They are controls, not a campaign: one device, one relay, ten 1 Hz observations, simulated time.

Pipelines: PBTI (no review), PBTI-R (one-shot review, R = 60 s, C = 10 s), historical B5 and corrected B5 (same
review).  The attacker holds the device key (and relays through the honest gateway); ground truth is known only here.

Traces
  T1 contradiction admitted     g5 suppressed, forged f5 (prev = g4) admitted; genuine g6..g9 (g6.prev = g5) arrive.
  T2 contradiction absent       as T1, but g6..g9 are suppressed as well (no successor names g5).
  T3 consistent takeover        g5..g9 suppressed and replaced by forgeries f5..f9 chained to each other (f5.prev = g4).
  T4 fresh identities           genuine g0..g9; forgeries at identities the device does not use in the run
                                (seq 12..14, after a gap), never contradicted.
  T5 fresh identities, later    as T4, but the genuine device later reaches seq 12..14 (g12..g14 arrive afterwards).
  T6 epoch advance              forgeries open epoch 1 (seq 0..4) while the device continues in epoch 0; with
                                epoch_drain_ms = 20 s, later epoch-0 statements are quarantined as STALE_EPOCH.
Output: results/v9/raw/attacker_controls.json (per trace and pipeline: final authority and exposure of forged statements,
final authority and withheld time of genuine statements, review outcomes).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
os.environ["B5_REPO"] = str(ROOT)
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools" / "b5_refmodel"))
import harness as H  # noqa: E402
import refmodel as M  # noqa: E402
from gen import SpecBuilder  # noqa: E402
from pbti.b5 import B5FeedLevel  # noqa: E402
from pbti.b5_corrected import B5Corrected  # noqa: E402
from pbti.policy import PolicyStore  # noqa: E402
from pbti.review import AutoReviewer  # noqa: E402
from pbti.verifier import PBTIVerifier  # noqa: E402

T_END = 200_000
P = M.Params.hist()


def chain(b, n, did="d", ep=0, t0=1_000, val0=50, start=0, prev=None, tag="g"):
    names = []
    for i in range(start, start + n):
        nm = b.stmt(f"{did}/{ep}/{i}/{tag}{i}", did, ep, i, t0 + 1_000 * i, prev, val0 + i, tag == "g")
        names.append(nm)
        prev = nm
    return names


def forge(b, seq, prev, ep=0, ts=None):
    return b.stmt(f"d/{ep}/{seq}/f{seq}", "d", ep, seq, ts if ts is not None else 1_000 + 1_000 * seq, prev,
                  900 + seq, False)


def traces():
    out = {}
    # T1 / T2
    for name, deliver_after in (("T1_contradiction_admitted", True), ("T2_contradiction_absent", False)):
        b = SpecBuilder(["d"], h_max_ms=3_600_000)
        g = chain(b, 10)
        f5 = forge(b, 5, g[4])
        for i, nm in enumerate(g):
            if i == 5 or (i > 5 and not deliver_after):
                continue
            b.arrive(1_020 + 1_000 * i, nm)
        b.arrive(6_020, f5)
        out[name] = b
    # T3
    b = SpecBuilder(["d"], h_max_ms=3_600_000)
    g = chain(b, 10)
    prev = g[4]
    for i in range(5, 10):
        prev = forge(b, i, prev)
    for i in range(5):
        b.arrive(1_020 + 1_000 * i, g[i])
    for i in range(5, 10):
        b.arrive(1_020 + 1_000 * i, f"d/0/{i}/f{i}")
    out["T3_consistent_takeover"] = b
    # T4 / T5
    for name, later in (("T4_fresh_identities", False), ("T5_fresh_identities_later_contradicted", True)):
        b = SpecBuilder(["d"], h_max_ms=3_600_000)
        g = chain(b, 15 if later else 10)
        for i in range(10):
            b.arrive(1_020 + 1_000 * i, g[i])
        prev = {"ext": "attacker-chain"}
        for i in (12, 13, 14):
            prev = forge(b, i, prev, ts=10_500 + 100 * i)
            b.arrive(10_600 + 100 * i, prev)
        if later:
            for i in range(10, 15):
                b.arrive(30_020 + 1_000 * i, g[i])          # the device resumes later (buffered backlog)
        out[name] = b
    # T6
    b = SpecBuilder(["d"], h_max_ms=3_600_000)
    g = chain(b, 10, t0=1_000)
    prev = None
    for i in range(5):
        prev = b.stmt(f"d/1/{i}/f{i}", "d", 1, i, 3_000 + 1_000 * i, prev, 900 + i, False)
        b.arrive(3_020 + 1_000 * i, prev)
    for i in range(10):
        b.arrive(1_020 + 1_000 * i if i < 5 else 30_000 + 1_000 * i, g[i])   # g5..g9 arrive after the drain
    out["T6_epoch_advance"] = b
    return out


def run(built, pipeline, epoch_drain_ms=None):
    env = built.env
    doc = json.loads(json.dumps(env.doc))
    if epoch_drain_ms is not None:
        doc["params"]["epoch_drain_ms"] = epoch_drain_ms
    pol = PolicyStore(doc)
    if pipeline in ("PBTI", "PBTI-R"):
        v = PBTIVerifier(env.trust, pol, env.vkeys)
    elif pipeline == "B5":
        v = B5FeedLevel(env.trust, pol, env.vkeys, recovery=True)
    else:
        v = B5Corrected(env.trust, pol, env.vkeys, recovery=True, review_mode="periodic")
    rv = None if pipeline == "PBTI" else AutoReviewer(H.RID, H.RKID, env.rsk, min_age_ms=P.R_ms, rule=P.rule)
    events = M.schedule(built.model_stmts, P, built.t_end)
    wire_by_stmt = {id(s): w for s, w in zip(built.model_stmts, built.wire_of_arrival)}
    timeline, cur, disp = [], set(), []
    first = {}
    for kind, x in events:
        if kind == "T":
            t = x
            if rv is not None:
                rv.run(v, t)
        else:
            t = x.t
            first.setdefault(((x.did, x.ep, x.seq), x.digest), t)
            r = v.ingest(wire_by_stmt[id(x)], t, {"tid": H.WID})
            disp.append(((x.did, x.ep, x.seq), r.disp + "/" + r.why.split(":")[0]))
        now = H._auth_set(v)
        for k in sorted(now - cur):
            timeline.append((t, k[0], k[1], True, "real"))
        for k in sorted(cur - now):
            timeline.append((t, k[0], k[1], False, "real"))
        cur = now
    v.advance(built.t_end)
    iv = M.authority_intervals(timeline, built.t_end)
    legit = set(built.legit)
    forged = [k for k in first if k not in legit]
    genuine = [k for k in first if k in legit]
    expo = sum(max(0, min(bb, built.t_end) - a) for k in forged for a, bb in iv.get(k, []))
    withheld = sum(M.withheld_ms(iv.get(k, []), first[k], built.t_end) for k in genuine)
    return {"pipeline": pipeline, "forged_admitted_arrivals": len(forged),
            "forged_authoritative_end": sum(1 for k in forged if k in cur),
            "forged_exposure_record_s": expo / 1000.0,
            "genuine_arrived": len(genuine), "genuine_authoritative_end": sum(1 for k in genuine if k in cur),
            "genuine_withheld_record_s": withheld / 1000.0,
            "dispositions": sorted({d for _, d in disp}),
            "review_outcomes": dict(getattr(v, "review_outcomes", {}))}


def main():
    res = []
    for name, b in traces().items():
        built = H.build(b.spec(T_END, name, 0))
        for pipe in ("PBTI", "PBTI-R", "B5", "B5c"):
            r = run(built, pipe, epoch_drain_ms=20_000 if name.startswith("T6") else None)
            r["trace"] = name
            res.append(r)
            print(f"{name:42s} {pipe:6s} forged auth end {r['forged_authoritative_end']}/{r['forged_admitted_arrivals']}"
                  f"  exposure {r['forged_exposure_record_s']:8.1f} rs  genuine auth end "
                  f"{r['genuine_authoritative_end']}/{r['genuine_arrived']}  withheld {r['genuine_withheld_record_s']:8.1f} rs")
    p = ROOT / "results" / "v9" / "raw" / "attacker_controls.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"t_end_ms": T_END, "review": "one-shot, R = 60 s, C = 10 s (PBTI-R, B5, B5c)",
                             "rows": res}, indent=1, default=str))


if __name__ == "__main__":
    main()
