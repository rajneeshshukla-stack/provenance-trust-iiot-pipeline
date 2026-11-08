#!/usr/bin/env python3
"""E1/E17/E18 (in-process part): verifier service time, per-stage cost, saturation throughput,
resource and storage overhead with durable SQLite group commit.

For each system and repetition: pre-encode N messages (edge cost measured separately), then feed
them through the verifier as fast as possible (closed loop). The store flushes (durable commit)
every `batch` messages. Reported per run: throughput, per-message service time distribution
(ingest + amortized flush), process CPU time per message, peak RSS delta, database bytes per event,
wire bytes per event, and (PBTI) per-stage breakdown.
Device-count scaling (E18) varies the number of devices at constant N.
"""
from __future__ import annotations

import argparse
import gc
import json
import math
import os
import random
import sys
import tempfile
import time
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from pbti.realtime import EdgeEncoder, Topology, build_identity, make_system  # noqa: E402
from pbti.store import SQLiteStore  # noqa: E402

sys.path.insert(0, str(ROOT / "experiments"))
from run_campaign import manifest  # noqa: E402


def payload(rng, t):
    s = t / 1000
    return {"temp_c": round(60 + 3 * math.sin(s / 20) + rng.gauss(0, 0.2), 2),
            "vib_mm_s": round(2 + rng.gauss(0, 0.05), 3), "press_bar": round(5 + rng.gauss(0, 0.02), 3),
            "flow_m3h": round(12 + rng.gauss(0, 0.1), 2)}


def one_run(system: str, n_gw: int, dev_per_gw: int, n_msgs: int, batch: int, seed: int, tmpdir: str) -> dict:
    topo = Topology(seed, n_gw, dev_per_gw)
    trust, policy, keys, vkeys = build_identity(topo, use_x509=True)
    enc = EdgeEncoder(system, topo, keys)
    rng = random.Random(seed)
    devs = [(g, j) for g in range(1, n_gw + 1) for j in range(1, dev_per_gw + 1)]
    n_dev = len(devs)
    rate_per_dev_ms = max(1, int(1000 * n_dev / 2000))  # aggregate 2000 msg/s of event time
    msgs = []
    t_enc0 = time.process_time()
    for i in range(n_msgs):
        g, j = devs[i % n_dev]
        t_ms = 10_000 + (i // n_dev) * rate_per_dev_ms
        msgs.append((t_ms, g, enc.encode(g, j, t_ms, payload(rng, t_ms))))
    edge_cpu_us = (time.process_time() - t_enc0) / n_msgs * 1e6
    wire_bytes = sum(len(m[2]) for m in msgs) / n_msgs
    db = os.path.join(tmpdir, f"{system}-{seed}.db")
    store = SQLiteStore(db)
    sysobj = make_system(system, trust, policy, vkeys, store=store, profile=(system == "PBTI"))
    proc = psutil.Process()
    gc.collect()
    rss0 = proc.memory_info().rss
    svc = []
    cpu0 = time.process_time()
    w0 = time.perf_counter()
    for i, (t_ms, g, wire) in enumerate(msgs):
        a = time.perf_counter_ns()
        sysobj.ingest(wire, t_ms, {"tid": topo.wid(g), "tkid": f"wk:gw{g}:1", "new_session": i < n_gw})
        if (i + 1) % batch == 0:
            store.flush()
        svc.append(time.perf_counter_ns() - a)
    sysobj.finalize(msgs[-1][0] + 1_000)
    store.flush()
    wall = time.perf_counter() - w0
    cpu = time.process_time() - cpu0
    rss1 = proc.memory_info().rss
    dbb = store.db_bytes()
    store.close()
    os.remove(db)
    for suf in ("-wal", "-shm"):
        if os.path.exists(db + suf):
            os.remove(db + suf)
    svc_sorted = sorted(svc)
    q = lambda p: svc_sorted[min(len(svc_sorted) - 1, int(p / 100 * len(svc_sorted)))] / 1e3  # noqa: E731
    r = {"system": system, "seed": seed, "n_gw": n_gw, "dev_per_gw": dev_per_gw, "n_devices": n_dev,
         "n_msgs": n_msgs, "batch": batch, "throughput_msg_s": n_msgs / wall, "cpu_us_per_msg": cpu / n_msgs * 1e6,
         "svc_us_mean": sum(svc) / len(svc) / 1e3, "svc_us_p50": q(50), "svc_us_p95": q(95), "svc_us_p99": q(99),
         "rss_delta_mb": (rss1 - rss0) / 2 ** 20, "db_bytes_per_msg": dbb / n_msgs, "wire_bytes": wire_bytes,
         "edge_cpu_us_per_msg": edge_cpu_us}
    if system == "PBTI":
        for k, v in sysobj.stage_ns.items():
            r[f"stage_us_{k}"] = v / n_msgs / 1e3
        r["evidence_bytes_per_msg"] = sysobj.evidence.bytes / n_msgs
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=10)
    ap.add_argument("--n", type=int, default=20_000)
    ap.add_argument("--batch", type=int, default=200)
    ap.add_argument("--scaling", action="store_true", help="E18: vary device count")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    name = "throughput_scaling" if args.scaling else "throughput"
    out = Path(args.out or ROOT / "results" / "raw" / f"{name}.jsonl")
    out.with_suffix(".manifest.json").write_text(json.dumps(manifest(name, args), indent=1))
    configs = [(4, 6)] if not args.scaling else [(1, 10), (4, 25), (10, 50), (20, 100)]
    tmp = tempfile.mkdtemp(prefix="pbti-tp-")
    with open(out, "w") as fh:
        for rep in range(1, args.reps + 1):
            for (g, d) in configs:
                order = ["B1", "B2", "B3", "PBTI"]
                random.Random(rep).shuffle(order)  # randomized run order controls drift
                for s in order:
                    r = one_run(s, g, d, args.n, args.batch, rep, tmp)
                    r["rep"] = rep
                    fh.write(json.dumps(r) + "\n")
                    fh.flush()
                    print(f"rep {rep} {s} dev={g*d}: {r['throughput_msg_s']:.0f} msg/s, p50 {r['svc_us_p50']:.0f}us, "
                          f"p99 {r['svc_us_p99']:.0f}us", flush=True)


if __name__ == "__main__":
    main()
