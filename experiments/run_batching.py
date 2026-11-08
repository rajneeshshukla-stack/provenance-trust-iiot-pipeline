#!/usr/bin/env python3
"""V3 performance study (P7): group-commit batch size x signature-verification workers, wall clock, in-process.

Design
  * N pre-encoded messages (4 gateways x 6 devices, one legacy device per gateway; same generator, payloads and
    event-time rate as experiments/run_throughput.py) are fed to the verifier in batches of `batch` messages. The
    durable SQLite store commits once per batch (group commit), as in the V2 throughput experiment.
  * workers = 1: the verifier runs exactly as in the paper: every check in one process.
  * workers > 1 (PBTI, B5 only; B2 has no signatures): a process pool verifies the two Ed25519 signatures of each
    message ahead of the verifier. This is stateless work (a signature over canonical bytes under the public key the
    statement names). The verifier process still performs every check, in arrival order; its signature calls are
    answered from the pool's results, keyed by SHA-256(public key || domain || message || signature), and fall back
    to a real verification on a miss. A cached answer is therefore always the answer the verifier would have
    computed for the same key and bytes. As a check, every run records a digest of the full disposition sequence
    and the script compares it across worker counts.
  * Dispatch window: at most max(1, workers) batches are in flight. Latency of a message = time from the dispatch
    of its batch to the durable commit of that batch (saturation latency; with an open-loop arrival rate
    lambda the batch-fill wait, (b-1)/(2 lambda) on average, comes on top). Queue depth = batches already verified by
    the pool but not yet admitted when a batch is admitted.
  * The host has 2 vCPUs; worker counts above 1 compete with the verifier process for the same cores, so results
    for 4 and 8 workers show oversubscription, not scaling.
"""
from __future__ import annotations

import argparse
import collections
import gc
import hashlib
import json
import math
import multiprocessing as mp
import os
import random
import sys
import tempfile
import time
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import pbti.verifier as V  # noqa: E402
from pbti.b5 import B5FeedLevel  # noqa: E402
from pbti.canonical import canonical_bytes  # noqa: E402
from pbti.crypto import DOMAIN_OBS, DOMAIN_REL, pub_raw, ub64u  # noqa: E402
from pbti.crypto import verify as real_verify  # noqa: E402
from pbti.identity import TrustView  # noqa: E402
from pbti.realtime import EdgeEncoder, Topology, build_identity, make_system  # noqa: E402
from pbti.store import SQLiteStore  # noqa: E402
from pbti.verifier import VerifierConfig  # noqa: E402

sys.path.insert(0, str(ROOT / "experiments"))
from run_campaign import manifest  # noqa: E402

CACHE: dict = {}
STATS = {"hit": 0, "miss": 0}


def _key(pkraw: bytes, domain: bytes, msg: bytes, sig: bytes) -> bytes:
    return hashlib.sha256(pkraw + domain + msg + sig).digest()


def cached_verify(pk, domain, msg, sig):
    r = CACHE.pop(_key(pub_raw(pk), domain, msg, sig), None)
    if r is None:
        STATS["miss"] += 1
        return real_verify(pk, domain, msg, sig)
    STATS["hit"] += 1
    return r


_W_KEYS: dict = {}


def _winit(keys_raw: dict):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    _W_KEYS.update({k: (raw, Ed25519PublicKey.from_public_bytes(raw)) for k, raw in keys_raw.items()})


def _wverify(wires: list) -> list:
    out = []
    for w in wires:
        try:
            m = json.loads(w)
            obs, rel = m["obs"], m["rel"]
            osig, rsig = ub64u(m["osig"]), ub64u(m["rsig"])
            for kid, dom, msg, sig in ((rel["wkid"], DOMAIN_REL, canonical_bytes(rel), rsig),
                                       (obs["kid"], DOMAIN_OBS, canonical_bytes(obs), osig)):
                kk = _W_KEYS.get(kid)
                if kk is not None:
                    out.append((_key(kk[0], dom, msg, sig), real_verify(kk[1], dom, msg, sig)))
        except Exception:  # noqa: BLE001  (malformed input: the verifier will reject it itself)
            continue
    return out


def payload(rng, t):
    s = t / 1000
    return {"temp_c": round(60 + 3 * math.sin(s / 20) + rng.gauss(0, 0.2), 2),
            "vib_mm_s": round(2 + rng.gauss(0, 0.05), 3), "press_bar": round(5 + rng.gauss(0, 0.02), 3),
            "flow_m3h": round(12 + rng.gauss(0, 0.1), 2)}


def encode(system, n_msgs, seed, n_gw=4, dev_per_gw=6):
    topo = Topology(seed, n_gw, dev_per_gw)
    trust, policy, keys, vkeys = build_identity(topo, use_x509=True)
    enc = EdgeEncoder("PBTI" if system in ("PBTI", "B5") else system, topo, keys)
    rng = random.Random(seed)
    devs = [(g, j) for g in range(1, n_gw + 1) for j in range(1, dev_per_gw + 1)]
    step = max(1, int(1000 * len(devs) / 2000))  # aggregate 2000 msg/s of event time, as in run_throughput.py
    msgs = []
    for i in range(n_msgs):
        g, j = devs[i % len(devs)]
        t_ms = 10_000 + (i // len(devs)) * step
        msgs.append((t_ms, g, enc.encode(g, j, t_ms, payload(rng, t_ms))))
    return topo, trust, policy, vkeys, msgs


def keys_raw(trust, msgs) -> dict:
    tv = TrustView(trust, 0)
    kids = set()
    for _, _, w in msgs[:5000]:
        m = json.loads(w)
        kids.add(m["obs"]["kid"])
        kids.add(m["rel"]["wkid"])
    return {k: pub_raw(tv.key(k).pk) for k in kids if tv.key(k) is not None}


def one_run(system, batch, workers, enc, tmpdir, rep):
    topo, trust, policy, vkeys, msgs = enc
    n_gw = topo.n_gw
    use_pool = workers > 1 and system in ("PBTI", "B5")
    pool = None
    if use_pool:
        pool = mp.get_context("fork").Pool(workers, initializer=_winit, initargs=(keys_raw(trust, msgs),))
        pool.map(abs, range(4 * workers))  # warm-up: workers started and initialised before timing
    db = os.path.join(tmpdir, f"{system}-{batch}-{workers}-{rep}.db")
    store = SQLiteStore(db)
    if system == "B5":
        sysobj = B5FeedLevel(trust, policy, vkeys, store=store, cfg=VerifierConfig(), recovery=False)
    else:
        sysobj = make_system(system, trust, policy, vkeys, store=store, profile=False)
    batches = [msgs[i:i + batch] for i in range(0, len(msgs), batch)]
    proc = psutil.Process()
    gc.collect()
    rss0 = proc.memory_info().rss
    disp, lat, qdepth = [], [], []
    CACHE.clear()
    STATS.update(hit=0, miss=0)
    rss_children = 0.0
    if use_pool:
        V.verify = cached_verify
    kids0 = {c.pid: c.cpu_times() for c in proc.children()} if use_pool else {}
    cpu0 = proc.cpu_times()
    w0 = time.perf_counter()
    try:
        idx = 0
        window = max(1, workers)
        inflight = collections.deque()
        nxt = 0

        def dispatch():
            nonlocal nxt
            if nxt < len(batches):
                t = time.perf_counter()
                fut = pool.apply_async(_wverify, ([w for _, _, w in batches[nxt]],)) if use_pool else None
                inflight.append((nxt, t, fut))
                nxt += 1

        for _ in range(window):
            dispatch()
        while inflight:
            bi, t_disp, fut = inflight.popleft()
            if fut is not None:
                for k, ok in fut.get():
                    CACHE[k] = ok
                qdepth.append(sum(1 for _, _, f in inflight if f.ready()))
            for t_ms, g, wire in batches[bi]:
                r = sysobj.ingest(wire, t_ms, {"tid": topo.wid(g), "tkid": f"wk:gw{g}:1", "new_session": idx < n_gw})
                disp.append(r.disp + "/" + r.why)
                idx += 1
            store.flush()
            lat.extend([time.perf_counter() - t_disp] * len(batches[bi]))
            dispatch()
        sysobj.finalize(msgs[-1][0] + 1_000)
        store.flush()
        wall = time.perf_counter() - w0
        kids_cpu = 0.0
        if use_pool:
            kids = proc.children()
            rss_children = sum(c.memory_info().rss for c in kids) / 2 ** 20
            for c in kids:
                t1 = c.cpu_times()
                t0 = kids0.get(c.pid)
                kids_cpu += (t1.user + t1.system) - ((t0.user + t0.system) if t0 else 0.0)
        cpu1 = proc.cpu_times()
    finally:
        V.verify = real_verify
        if pool is not None:
            pool.close()
            pool.join()
    cpu = (cpu1.user - cpu0.user) + (cpu1.system - cpu0.system) + kids_cpu  # verifier process + live pool workers
    rss1 = proc.memory_info().rss
    dbb = store.db_bytes()
    ev_bytes = getattr(getattr(sysobj, "evidence", None), "bytes", 0)
    store.close()
    for suf in ("", "-wal", "-shm"):
        if os.path.exists(db + suf):
            os.remove(db + suf)
    lat_ms = sorted(x * 1e3 for x in lat)
    q = lambda p: lat_ms[min(len(lat_ms) - 1, int(p / 100 * len(lat_ms)))]  # noqa: E731
    return {"system": system, "batch": batch, "workers": workers, "rep": rep, "n_msgs": len(msgs),
            "logical_cpus": os.cpu_count(), "throughput_msg_s": len(msgs) / wall, "wall_s": wall, "cpu_s": cpu,
            "cpu_util_cores": cpu / wall, "cpu_us_per_msg": cpu / len(msgs) * 1e6,
            "lat_ms_p50": q(50), "lat_ms_p95": q(95), "lat_ms_p99": q(99),
            "queue_depth_max": max(qdepth) if qdepth else 0,
            "queue_depth_mean": (sum(qdepth) / len(qdepth)) if qdepth else 0.0,
            "drops": 0, "timeouts": 0, "db_bytes_per_msg": dbb / len(msgs), "evidence_bytes_per_msg": ev_bytes / len(msgs),
            "wire_bytes": sum(len(m[2]) for m in msgs) / len(msgs),
            "sig_cache_hit": STATS["hit"], "sig_cache_miss": STATS["miss"],
            "rss_main_mb": rss1 / 2 ** 20, "rss_delta_mb": (rss1 - rss0) / 2 ** 20, "rss_workers_mb": rss_children,
            "dispositions_digest": hashlib.sha256("|".join(disp).encode()).hexdigest()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10_000)
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--batches", type=int, nargs="+", default=[1, 8, 32, 128, 512])
    ap.add_argument("--workers", type=int, nargs="+", default=[1, 2, 4, 8])
    ap.add_argument("--systems", nargs="+", default=["PBTI", "B5", "B2"])
    ap.add_argument("--out", default=str(ROOT / "results" / "raw" / "v3_batching.jsonl"))
    a = ap.parse_args()
    out = Path(a.out)
    out.with_suffix(".manifest.json").write_text(json.dumps(manifest("v3_batching", a), indent=1))
    tmp = tempfile.mkdtemp(prefix="pbti-batch-")
    all_same = True
    with open(out, "w") as fh:
        for rep in range(1, a.reps + 1):
            encs = {s: encode(s, a.n, rep) for s in a.systems}
            cells = [(s, b, w) for s in a.systems for b in a.batches for w in (a.workers if s in ("PBTI", "B5") else [1])]
            random.Random(rep).shuffle(cells)  # randomised run order controls drift
            ref: dict = {}
            for s, b, w in cells:
                r = one_run(s, b, w, encs[s], tmp, rep)
                ref.setdefault(s, set()).add(r["dispositions_digest"])
                fh.write(json.dumps(r) + "\n")
                fh.flush()
                print(f"rep {rep} {s:4s} batch={b:3d} workers={w}: {r['throughput_msg_s']:7.0f} msg/s "
                      f"p50 {r['lat_ms_p50']:8.1f} ms p99 {r['lat_ms_p99']:8.1f} ms cpu {r['cpu_util_cores']:.2f} "
                      f"hits {r['sig_cache_hit']}", flush=True)
            same = all(len(d) == 1 for d in ref.values())
            all_same &= same
            print(f"rep {rep}: dispositions identical across batch sizes and worker counts: {same}", flush=True)
    print("ALL_DISPOSITIONS_IDENTICAL", all_same)


if __name__ == "__main__":
    main()
