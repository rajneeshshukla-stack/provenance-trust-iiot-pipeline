"""Independent offline auditor and insider-tampering injector (experiment E16).

PBTI audit checks (each maps to an invariant):
  A-RAW   every COMMITTED slot's raw object exists, hashes to its content address, carries valid
          observation and relay signatures, and its content digest equals the slot digest   (I1, I6)
  A-EVID  evidence records hash to their Merkle leaves, every batch root matches its signed
          checkpoint, checkpoints are chained, contiguous, and identical to the witness copies (I6)
  A-REG   every COMMITTED slot is backed by an ACCEPT evidence record for the same digest     (I2)
  A-DET   replaying the receipt log through a fresh verifier reproduces every disposition and
          the final registry state (decision determinism / re-verifiability)                  (I10)
  A-LIN   every latest derived version references only authoritative raw objects, its inputs
          root and aggregates recompute, and it includes every authoritative input of its window (I5)
B3 audit: ledger hash chain, signed heads, ledger blob digests, record signatures.
B1/B2: no integrity anchors exist; nothing can be verified (reported as "no mechanism").
"""
from __future__ import annotations

import copy
import json
import math
import time
from collections import Counter

from .canonical import canonical_bytes
from .crypto import DOMAIN_B3, DOMAIN_B3LEDGER, DOMAIN_CKPT, DOMAIN_OBS, DOMAIN_REL, b64u, sha256, sha256_hex, sign, ub64u, verify
from .evidence import EvidenceLog, leaf_hash, merkle_root
from .identity import TrustView
from .registry import COMMITTED
from .verifier import PBTIVerifier


# ============================================================================ PBTI
def audit_pbti(v: PBTIVerifier, replay: bool = True) -> dict:
    t0 = time.perf_counter()
    f = Counter()
    tv = TrustView(v.trust_registry, 0)
    # A-RAW
    held = getattr(v, "held", set())
    for key, s in v.reg.slots.items():
        if s.state() != COMMITTED or key in held:   # V3: B5 holds are not authoritative raw objects
            continue
        for cd, wd in list(s.versions.items())[:1]:
            blob = v.store.get_blob("raw", wd)
            if blob is None:
                f["A-RAW:missing"] += 1
                continue
            if sha256_hex(blob) != wd:
                f["A-RAW:digest"] += 1
                continue
            try:
                m = json.loads(blob)
                obs, rel = m["obs"], m["rel"]
                osig, rsig = ub64u(m["osig"]), ub64u(m["rsig"])
                kd, kw = tv.key(obs["kid"]), tv.key(rel["wkid"])
                cb = canonical_bytes(obs)
                ok = (kd is not None and kw is not None and verify(kd.pk, DOMAIN_OBS, cb, osig)
                      and verify(kw.pk, DOMAIN_REL, canonical_bytes(rel), rsig)
                      and rel["odig"] == b64u(sha256(cb + osig)) and b64u(sha256(cb)) == cd)
                if not ok:
                    f["A-RAW:signature"] += 1
            except Exception:  # noqa: BLE001
                f["A-RAW:unparseable"] += 1
    # A-EVID
    ev = v.evidence
    leaves = [leaf_hash(r) for r in ev.records]
    nxt = 0
    prev = None
    for i, ck in enumerate(ev.checkpoints):
        if not EvidenceLog.verify_checkpoint_sig(ev.pk, ck):
            f["A-EVID:checkpoint-signature"] += 1
        if ck["first"] != nxt:
            f["A-EVID:checkpoint-gap"] += 1
        if ck["prev"] != prev:
            f["A-EVID:checkpoint-chain"] += 1
        root = b64u(merkle_root(leaves[ck["first"]:ck["first"] + ck["count"]]))
        if root != ck["root"]:
            f["A-EVID:root-mismatch"] += 1
        w = ev.witness[i] if i < len(ev.witness) else None
        if w != ck:
            f["A-EVID:witness-mismatch"] += 1
        nxt = ck["first"] + ck["count"]
        prev = b64u(sha256(canonical_bytes(ck)))
    if len(ev.witness) != len(ev.checkpoints):
        f["A-EVID:witness-count"] += 1
    if nxt != len(ev.records):
        f["A-EVID:uncovered-records"] += len(ev.records) - nxt
    # A-REG
    accepted = {}
    for r in ev.records:
        try:
            d = json.loads(r)
        except Exception:  # noqa: BLE001
            continue
        if d.get("disp") == "ACCEPT":
            accepted[d["w"]] = d.get("cd")
        elif d.get("type") == "REVIEW" and d.get("outcome") == "RELEASED_HOLD":  # V3: B5 hold released by review
            accepted[d["case"]] = (d.get("evidence") or {}).get("cd")
    for key, s in v.reg.slots.items():
        if v.is_authoritative(key, s):
            cd, wd = next(iter(s.versions.items()))
            if accepted.get(wd) != cd:
                f["A-REG:slot-without-evidence"] += 1
    # A-LIN
    authoritative = {wd_of(s): k for k, s in v.reg.slots.items() if v.is_authoritative(k, s)}
    per_window: dict = {}
    for k, s in v.reg.slots.items():
        if v.is_authoritative(k, s) and s.obs_first is not None:
            o = s.obs_first
            wk = (o["aid"], o["ts"] - o["ts"] % v.cfg.window_ms)
            per_window.setdefault(wk, set()).add(wd_of(s))
    for wk, vers in v.proc.versions.items():
        rec = vers[-1]
        refs = rec.get("inputs", [])
        if rec.get("inputs_root") != b64u(merkle_root([leaf_hash(r.encode()) for r in refs])):
            f["A-LIN:inputs-root"] += 1
        if any(r not in authoritative for r in refs):
            f["A-LIN:non-authoritative-input"] += 1
        if set(refs) != per_window.get(wk, set()):
            f["A-LIN:incomplete"] += 1
        # recompute aggregates from raw objects. V3: the processor sums in arrival order and the auditor in sorted
        # order, so a mean that lies on a rounding tie of the 6th decimal may round differently; the auditor therefore
        # sums exactly (math.fsum) and accepts the recorded mean within one unit of that decimal (min/max exact).
        agg = {}
        for r in refs:
            blob = v.store.get_blob("raw", r)
            if blob is None:
                continue
            try:
                pl = json.loads(blob)["obs"]["pl"]
            except Exception:  # noqa: BLE001
                continue
            for m, x in pl.items():
                a = agg.setdefault(m, [0, [], x, x])
                a[0] += 1; a[1].append(x); a[2] = min(a[2], x); a[3] = max(a[3], x)
        got = rec["agg"]
        bad = set(agg) != set(got) if refs else False
        for m, a in agg.items():
            g = got.get(m)
            if g is None or g[1] != a[2] or g[2] != a[3] or abs(math.fsum(a[1]) / a[0] - g[0]) > 1.000001e-6:
                bad = True
        if refs and bad:
            f["A-LIN:aggregate-mismatch"] += 1
    t_static = time.perf_counter() - t0
    # A-DET
    det = {}
    if replay:
        t1 = time.perf_counter()
        v2 = type(v)(v.trust_registry, v.pdp.store, (ev.sk, ev.pk), cfg=copy.deepcopy(v.cfg), ablation=v.ab,
                     **getattr(v, "init_kw", {}))
        # V4: the release-evidence policy and its trust anchors are part of the verifier configuration
        v2.release_evidence = getattr(v, "release_evidence", "discretionary")
        v2.witness = getattr(v, "witness", None)
        v2.compromise_low = dict(getattr(v, "compromise_low", {}))

        def _disp(records):
            out = []
            for r in records:
                try:
                    d = json.loads(r)
                    out.append((d.get("disp"), d.get("why")))
                except Exception:  # noqa: BLE001
                    out.append(None)
            return out
        for i, (t, wd, tid) in enumerate(v.receipt_log):
            if isinstance(tid, (tuple, list)) and tid and tid[0] == "REVIEW_OPEN":   # V3 review workflow
                v2.open_review(wd, tid[1], t)
                continue
            if isinstance(tid, (tuple, list)) and tid and tid[0] == "REVIEW":
                v2.apply_review(tid[1], t)
                continue
            blob = v.store.get_blob("raw", wd) or v.store.get_blob("q", wd)
            if blob is None:
                f["A-DET:missing-input"] += 1
                continue
            v2.ingest(blob, t, {"tid": tid})
        d1, d2 = _disp(ev.records), _disp(v2.evidence.records)
        mism = sum(1 for a, b in zip(d1, d2) if a != b) + abs(len(d1) - len(d2))
        v2.finalize(v.next_tick - v.cfg.tick_ms if v.next_tick else 0)
        if mism:
            f["A-DET:disposition-mismatch"] += mism
        s1 = {k: (s.state(), s.tainted, tuple(sorted(s.versions)), v.is_authoritative(k, s)) for k, s in v.reg.slots.items()}
        s2 = {k: (s.state(), s.tainted, tuple(sorted(s.versions)), v2.is_authoritative(k, s)) for k, s in v2.reg.slots.items()}
        if s1 != s2:
            f["A-DET:registry-mismatch"] += sum(1 for k in set(s1) | set(s2) if s1.get(k) != s2.get(k))
        det["replay_s"] = time.perf_counter() - t1
    return {"findings": dict(f), "pass": not f, "static_s": t_static, **det,
            "n_records": len(ev.records), "n_slots": len(v.reg.slots)}


def wd_of(s) -> str:
    return next(iter(s.versions.values()))


# ============================================================================ B3
def audit_b3(b) -> dict:
    f = Counter()
    tv = TrustView(b.trust.reg, 0)
    prev = None
    for i, e in enumerate(b.ledger):
        h = b64u(sha256(canonical_bytes({k: e[k] for k in ("i", "rec", "ref", "t", "prev")})))
        if h != e["h"] or e["prev"] != prev or e["i"] != i:
            f["B3:chain"] += 1
        prev = e["h"]
        blob = b.store.get_blob("ledger", e["ref"])
        if blob is None:
            f["B3:blob-missing"] += 1
            continue
        if sha256_hex(blob) != e["ref"]:
            f["B3:blob-digest"] += 1
            continue
        try:
            m = json.loads(blob)
            rec, sig = m["rec"], ub64u(m["sig"])
            info = tv.key(rec["kid"])
            cb = canonical_bytes(rec)
            if info is None or not verify(info.pk, DOMAIN_B3, cb, sig) or b64u(sha256(cb)) != e["rec"]:
                f["B3:signature"] += 1
        except Exception:  # noqa: BLE001
            f["B3:unparseable"] += 1
    for hd in b.heads:
        body = {k: hd[k] for k in ("size", "head", "t")}
        if not verify(b.vpk, DOMAIN_B3LEDGER, canonical_bytes(body), ub64u(hd["sig"])):
            f["B3:head-signature"] += 1
        if hd["size"] > len(b.ledger) or b.ledger[hd["size"] - 1]["h"] != hd["head"]:
            f["B3:head-mismatch"] += 1
    return {"findings": dict(f), "pass": not f}


# ============================================================================ insider tampering
TAMPER_CLASSES = ["T1_raw_modify", "T2_raw_delete", "T3_evidence_modify", "T4_checkpoint_delete",
                  "T5_rewrite_with_key", "T6_derived_modify", "T7_registry_modify"]


def tamper_pbti(v: PBTIVerifier, cls: str, k: int, rng) -> int:
    """Apply insider tampering to a finished PBTI run; return the number of objects altered."""
    slots = [(key, s) for key, s in v.reg.slots.items() if s.state() == COMMITTED and not s.tainted]
    rng.shuffle(slots)
    n = 0
    if cls == "T1_raw_modify":
        for key, s in slots[:k]:
            wd = wd_of(s)
            blob = v.store.blobs.get(("raw", wd))
            if blob is None:
                continue
            m = json.loads(blob)
            m["obs"]["pl"]["temp_c"] = round(m["obs"]["pl"]["temp_c"] + 1.0, 2)
            v.store.blobs[("raw", wd)] = canonical_bytes(m)
            n += 1
    elif cls == "T2_raw_delete":
        for key, s in slots[:k]:
            if v.store.blobs.pop(("raw", wd_of(s)), None) is not None:
                n += 1
    elif cls == "T3_evidence_modify":
        idx = rng.sample(range(len(v.evidence.records)), min(k, len(v.evidence.records)))
        for i in idx:
            d = json.loads(v.evidence.records[i])
            d["disp"] = "ACCEPT" if d.get("disp") != "ACCEPT" else "REJECT"
            v.evidence.records[i] = canonical_bytes(d)
            n += 1
    elif cls == "T4_checkpoint_delete":
        if len(v.evidence.checkpoints) > 2:
            j = rng.randrange(1, len(v.evidence.checkpoints) - 1)
            v.evidence.checkpoints.pop(j)
            n = 1
    elif cls == "T5_rewrite_with_key":
        # insider holding the verifier evidence key rewrites records and re-signs every checkpoint;
        # only the externally held witness copies are out of reach
        ev = v.evidence
        idx = rng.sample(range(len(ev.records)), min(k, len(ev.records)))
        for i in idx:
            d = json.loads(ev.records[i])
            d["disp"] = "ACCEPT" if d.get("disp") != "ACCEPT" else "REJECT"
            ev.records[i] = canonical_bytes(d)
            n += 1
        ev.leaves = [leaf_hash(r) for r in ev.records]
        prev = None
        new = []
        for ck in ev.checkpoints:
            body = {"n": ck["n"], "first": ck["first"], "count": ck["count"],
                    "root": b64u(merkle_root(ev.leaves[ck["first"]:ck["first"] + ck["count"]])), "prev": prev, "t": ck["t"]}
            c2 = dict(body, sig=b64u(sign(ev.sk, DOMAIN_CKPT, canonical_bytes(body))))
            new.append(c2)
            prev = b64u(sha256(canonical_bytes(c2)))
        ev.checkpoints = new
    elif cls == "T6_derived_modify":
        wks = list(v.proc.versions)
        rng.shuffle(wks)
        for wk in wks[:k]:
            rec = v.proc.versions[wk][-1]
            if rec.get("agg") and "temp_c" in rec["agg"]:
                rec["agg"]["temp_c"][0] = round(rec["agg"]["temp_c"][0] + 0.5, 6)
                n += 1
    elif cls == "T7_registry_modify":
        for key, s in slots[:k]:
            s.tainted = True  # silently retire authoritative observations
            n += 1
    return n


def tamper_b3(b, cls: str, k: int, rng) -> int:
    n = 0
    idx = list(range(len(b.ledger)))
    rng.shuffle(idx)
    if cls == "T1_raw_modify":
        for i in idx[:k]:
            ref = b.ledger[i]["ref"]
            blob = b.store.blobs.get(("ledger", ref))
            if blob is None:
                continue
            m = json.loads(blob)
            m["rec"]["pl"]["temp_c"] = round(m["rec"]["pl"]["temp_c"] + 1.0, 2)
            b.store.blobs[("ledger", ref)] = canonical_bytes(m)
            n += 1
    elif cls == "T2_raw_delete":
        for i in idx[:k]:
            if b.store.blobs.pop(("ledger", b.ledger[i]["ref"]), None) is not None:
                n += 1
    elif cls == "T3_evidence_modify":
        for i in idx[:k]:
            b.ledger[i]["t"] += 1
            n += 1
    elif cls == "T4_checkpoint_delete":
        if len(b.heads) > 2:
            b.heads.pop(rng.randrange(1, len(b.heads) - 1))
            n = 1
    elif cls == "T5_rewrite_with_key":
        for i in idx[:k]:
            b.ledger[i]["t"] += 1
            n += 1
        prev = None
        for e in b.ledger:
            e["prev"] = prev
            e["h"] = b64u(sha256(canonical_bytes({kk: e[kk] for kk in ("i", "rec", "ref", "t", "prev")})))
            prev = e["h"]
        for hd in b.heads:
            hd["head"] = b.ledger[hd["size"] - 1]["h"]
            body = {kk: hd[kk] for kk in ("size", "head", "t")}
            hd["sig"] = b64u(sign(b.vsk, DOMAIN_B3LEDGER, canonical_bytes(body)))
    elif cls == "T6_derived_modify":
        wks = list(b.proc.versions)
        rng.shuffle(wks)
        for wk in wks[:k]:
            rec = b.proc.versions[wk][-1]
            if rec.get("agg") and "temp_c" in rec["agg"]:
                rec["agg"]["temp_c"][0] += 0.5
                n += 1
    elif cls == "T7_registry_modify":
        keys = list(b.silver)
        rng.shuffle(keys)
        for bk in keys[:k]:
            b.silver.pop(bk)
            n += 1
    return n
