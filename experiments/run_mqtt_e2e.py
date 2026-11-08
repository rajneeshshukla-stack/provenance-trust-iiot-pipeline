#!/usr/bin/env python3
"""E1/E17 end-to-end: real Mosquitto broker, mutual TLS (per-gateway client certificates, identity
used as username, per-topic ACL), MQTT v5 QoS 1, one publisher process emulating G gateways
(edge signing performed in real time), one verifier process with durable SQLite group commit.

End-to-end latency = verifier durable-commit time - publisher send time (same host, CLOCK_MONOTONIC).
Usage: python experiments/run_mqtt_e2e.py --rates 200 500 1000 1500 --reps 5 --measure 20
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import random
import signal
import subprocess
import sys
import tempfile
import threading
import time
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

PORT = 8883
TOPO = dict(n_gw=4, dev_per_gw=6)


# ----------------------------------------------------------------------------- PKI for TLS
def make_pki(d: Path, n_gw: int) -> None:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID
    import ipaddress

    def name(cn):
        return x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])

    now = dt.datetime.now(dt.timezone.utc)
    ca_key = ec.generate_private_key(ec.SECP256R1())
    ca = (x509.CertificateBuilder().subject_name(name("pbti-tls-ca")).issuer_name(name("pbti-tls-ca"))
          .public_key(ca_key.public_key()).serial_number(1).not_valid_before(now - dt.timedelta(days=1))
          .not_valid_after(now + dt.timedelta(days=30))
          .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
          .sign(ca_key, hashes.SHA256()))

    def leaf(cn, server=False):
        k = ec.generate_private_key(ec.SECP256R1())
        b = (x509.CertificateBuilder().subject_name(name(cn)).issuer_name(ca.subject).public_key(k.public_key())
             .serial_number(x509.random_serial_number()).not_valid_before(now - dt.timedelta(days=1))
             .not_valid_after(now + dt.timedelta(days=30)))
        if server:
            b = b.add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost"),
                                                             x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]), False)
        c = b.sign(ca_key, hashes.SHA256())
        (d / f"{cn}.crt").write_bytes(c.public_bytes(serialization.Encoding.PEM))
        (d / f"{cn}.key").write_bytes(k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                                      serialization.NoEncryption()))

    (d / "ca.crt").write_bytes(ca.public_bytes(serialization.Encoding.PEM))
    leaf("server", server=True)
    leaf("verifier")
    for g in range(1, n_gw + 1):
        leaf(f"gw{g}")
    acl = ["user verifier", "topic read pbti/#", ""]
    for g in range(1, n_gw + 1):
        acl += [f"user gw{g}", f"topic write pbti/gw{g}/#", ""]
    (d / "acl").write_text("\n".join(acl))
    (d / "mosquitto.conf").write_text(f"""per_listener_settings true
listener {PORT} 127.0.0.1
cafile {d}/ca.crt
certfile {d}/server.crt
keyfile {d}/server.key
require_certificate true
use_identity_as_username true
allow_anonymous false
acl_file {d}/acl
max_inflight_messages 0
max_queued_messages 0
persistence false
log_dest none
""")
    # the broker drops privileges to the 'mosquitto' user: make the test PKI readable (sandbox only)
    os.chmod(d, 0o755)
    for f in d.iterdir():
        os.chmod(f, 0o644)


def client(d: Path, cn: str, cid: str):
    import paho.mqtt.client as mqtt
    c = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, client_id=cid, protocol=mqtt.MQTTv5)
    c.tls_set(ca_certs=str(d / "ca.crt"), certfile=str(d / f"{cn}.crt"), keyfile=str(d / f"{cn}.key"))
    c.max_inflight_messages_set(0)
    c.max_queued_messages_set(0)
    return c


# ----------------------------------------------------------------------------- verifier role
def role_verifier(a):
    import psutil
    from paho.mqtt.packettypes import PacketTypes  # noqa: F401
    from pbti.realtime import Topology, build_identity, make_system
    from pbti.store import SQLiteStore
    d = Path(a.pki)
    topo = Topology(a.seed, **TOPO)
    trust, policy, keys, vkeys = build_identity(topo)
    dbp = Path(a.tmp) / f"e2e-{a.system}-{a.rate}-{a.rep}.db"  # fresh database per run (no growth carried across runs)
    store = SQLiteStore(str(dbp))
    sysobj = make_system(a.system, trust, policy, vkeys, store=store)
    import queue as _queue
    q: _queue.SimpleQueue = _queue.SimpleQueue()
    ev = threading.Event()

    def on_message(cl, ud, msg):
        ts = 0
        for k, v in (msg.properties.UserProperty or []):
            if k == "ts":
                ts = int(v)
        q.put((msg.topic, msg.payload, ts))

    c = client(d, "verifier", f"verifier-{a.system}")
    c.on_message = on_message
    c.on_connect = lambda cl, ud, fl, rc, pr: (cl.subscribe("pbti/#", qos=1), ev.set())
    c.connect("127.0.0.1", PORT, keepalive=60)
    c.loop_start()
    ev.wait(10)
    Path(a.ready).write_text("ready")
    proc = psutil.Process()
    seen_gw = set()
    lat, pending = [], []
    qd_max, qd_sum, qd_n = 0, 0, 0   # V3: verifier input-queue depth (messages received, not yet ingested)
    n_commit = 0
    last_flush = time.monotonic_ns()
    deadline = time.monotonic() + a.warm + a.measure + a.drain + 30
    cpu0 = None
    t_meas0 = t_meas1 = None
    window = (None, None)
    winfile = Path(a.window)
    while time.monotonic() < deadline:
        if window[0] is None and winfile.exists():
            try:
                w = json.loads(winfile.read_text())
                window = (w["t0"], w["t1"])
            except (ValueError, KeyError):   # V3: never act on a partially written file
                pass
        try:
            topic, payload, ts = q.get(timeout=0.002)  # blocking wait, no busy polling
        except _queue.Empty:
            if pending and time.monotonic_ns() - last_flush > 10_000_000:
                store.flush(); tnow = time.monotonic_ns()
                if window[0] is not None:
                    for t in pending:
                        if window[0] <= t <= window[1]:
                            lat.append(tnow - t)
                            t_meas1 = tnow
                n_commit += len(pending); pending.clear(); last_flush = tnow
            if Path(a.stop).exists() and q.empty():
                break
            continue
        qd = q.qsize() + 1
        qd_max = max(qd_max, qd); qd_sum += qd; qd_n += 1
        g = int(topic.split("/")[1][2:])
        tid = topo.wid(g)
        # verifier clock = its own receipt time on the host-wide CLOCK_MONOTONIC (shared with the publisher,
        # which stamps observations on the same clock), so the freshness checks see the real end-to-end delay
        sysobj.ingest(payload, 10_000 + time.monotonic_ns() // 1_000_000, {"tid": tid, "tkid": f"wk:gw{g}:1",
                                                                           "new_session": g not in seen_gw})
        seen_gw.add(g)
        pending.append(ts)
        if len(pending) >= a.batch or time.monotonic_ns() - last_flush > 10_000_000:
            store.flush(); tnow = time.monotonic_ns()
            if window[0] is not None:
                for t in pending:
                    if window[0] <= t <= window[1]:
                        lat.append(tnow - t)
                        if cpu0 is None:
                            cpu0 = proc.cpu_times(); t_meas0 = tnow
                        t_meas1 = tnow
            n_commit += len(pending); pending.clear(); last_flush = tnow
    cpu1 = proc.cpu_times()
    c.loop_stop()
    lat.sort()
    q_ = lambda p: lat[min(len(lat) - 1, int(p / 100 * len(lat)))] / 1e6 if lat else float("nan")  # noqa: E731
    span = (t_meas1 - t_meas0) / 1e9 if t_meas0 and t_meas1 and t_meas1 > t_meas0 else float("nan")
    out = {"system": a.system, "rate": a.rate, "rep": a.rep, "n_measured": len(lat),
           "lat_ms_p50": q_(50), "lat_ms_p95": q_(95), "lat_ms_p99": q_(99),
           "lat_ms_mean": (sum(lat) / len(lat) / 1e6) if lat else float("nan"),
           "throughput_msg_s": len(lat) / span if span == span and span > 0 else float("nan"),
           "verifier_cpu_s": (cpu1.user + cpu1.system - cpu0.user - cpu0.system) if cpu0 else float("nan"),
           "verifier_cpu_us_per_msg": ((cpu1.user + cpu1.system - cpu0.user - cpu0.system) / max(1, len(lat)) * 1e6) if cpu0 else float("nan"),
           "n_commit_total": n_commit, "dispositions": dict(sorted(sysobj.counts.items())),
           "queue_depth_max": qd_max, "queue_depth_mean": (qd_sum / qd_n) if qd_n else 0.0,
           "verifier_rss_peak_mb": __import__("resource").getrusage(__import__("resource").RUSAGE_SELF).ru_maxrss / 1024,
           "evidence_bytes": getattr(getattr(sysobj, "evidence", None), "bytes", None)}
    store.flush()
    out["db_bytes"] = store.db_bytes()
    out["db_bytes_per_msg"] = out["db_bytes"] / max(1, n_commit)
    store.close()
    for f in (dbp, Path(str(dbp) + "-wal"), Path(str(dbp) + "-shm")):
        if f.exists():
            f.unlink()
    Path(a.result).write_text(json.dumps(out))


# ----------------------------------------------------------------------------- publisher role
def role_publisher(a):
    import psutil
    from paho.mqtt.packettypes import PacketTypes
    from paho.mqtt.properties import Properties
    from pbti.realtime import EdgeEncoder, Topology, build_identity
    d = Path(a.pki)
    topo = Topology(a.seed, **TOPO)
    _, _, keys, _ = build_identity(topo)
    enc = EdgeEncoder(a.system, topo, keys)
    cls = []
    for g in range(1, topo.n_gw + 1):
        c = client(d, f"gw{g}", f"gw{g}-{a.system}-{a.rep}")
        c.connect("127.0.0.1", PORT, keepalive=60)
        c.loop_start()
        cls.append(c)
    time.sleep(1.0)
    rng = random.Random(a.seed)
    devs = [(g, j) for g in range(1, topo.n_gw + 1) for j in range(1, topo.dev_per_gw + 1)]
    period = 1.0 / a.rate
    sched = None
    if a.payload == "skab":   # V3: replay SKAB rows with their native timing divided by the speed-up factor
        import heapq
        from pbti.dataset import load_skab
        feeds = load_skab(a.skab_dir)["feeds"]
        sched = [(r.dt_ms / 1000.0 / a.speed, k, ri) for k, f in enumerate(feeds) for ri, r in enumerate(f)]
        heapq.heapify(sched)
        sched = [heapq.heappop(sched) for _ in range(len(sched))]
    t_start = time.monotonic()
    t_end = t_start + a.warm + a.measure
    win = {"t0": int((t_start + a.warm) * 1e9), "t1": int(t_end * 1e9)}
    tmpw = Path(a.window + ".tmp")          # V3: atomic publish of the measurement window (the verifier polls for it)
    tmpw.write_text(json.dumps(win))
    os.replace(tmpw, a.window)
    proc = psutil.Process()
    cpu0 = proc.cpu_times()
    i = 0
    while True:
        if sched is not None:
            if i >= len(sched):
                break
            target = t_start + sched[i][0]
        else:
            target = t_start + i * period
        now = time.monotonic()
        if now >= t_end:
            break
        if target > now:
            time.sleep(min(target - now, 0.002))
            continue
        if sched is not None:
            k, ri = sched[i][1], sched[i][2]
            g, j = devs[k]
            pl = dict(feeds[k][ri].pl)
        else:
            g, j = devs[i % len(devs)]
        t_ms = 10_000 + time.monotonic_ns() // 1_000_000  # observation time on the shared monotonic clock
        if sched is None:
            pl = {"temp_c": round(60 + rng.gauss(0, 0.5), 2), "vib_mm_s": round(2 + rng.gauss(0, 0.05), 3),
                  "press_bar": round(5 + rng.gauss(0, 0.02), 3), "flow_m3h": round(12 + rng.gauss(0, 0.1), 2)}
        wire = enc.encode(g, j, t_ms, pl)
        props = Properties(PacketTypes.PUBLISH)
        props.UserProperty = ("ts", str(time.monotonic_ns()))
        cls[g - 1].publish(f"pbti/gw{g}/{topo.dids(g)[j - 1]}", wire, qos=1, properties=props)
        i += 1
    cpu1 = proc.cpu_times()
    time.sleep(a.drain)
    for c in cls:
        c.loop_stop()
        c.disconnect()
    Path(a.pubresult).write_text(json.dumps({"sent": i, "achieved_rate": i / (a.warm + a.measure),
                                             "publisher_cpu_us_per_msg": (cpu1.user + cpu1.system - cpu0.user - cpu0.system) / max(1, i) * 1e6}))


# ----------------------------------------------------------------------------- orchestrator
def orchestrate(a):
    import psutil
    sys.path.insert(0, str(ROOT / "experiments"))
    from run_campaign import manifest
    out = Path(a.out or ROOT / "results" / "raw" / "mqtt_e2e.jsonl")
    out.with_suffix(".manifest.json").write_text(json.dumps(
        dict(manifest("mqtt_e2e", a), mosquitto=subprocess.run(["mosquitto", "-h"], capture_output=True, text=True).stdout.splitlines()[0],
             paho=__import__("paho.mqtt").mqtt.__version__), indent=1))
    tmp = Path(tempfile.mkdtemp(prefix="pbti-e2e-"))
    make_pki(tmp, TOPO["n_gw"])
    cells = [(r, 0.0) for r in a.rates] if a.payload == "synthetic" else [(int(24 * sp), sp) for sp in a.speeds]
    with open(out, "w") as fh:
        for rep in range(1, a.reps + 1):
            for rate, speed in cells:
                order = list(a.systems)
                random.Random(rep * 1000 + rate).shuffle(order)
                for s in order:
                    broker = subprocess.Popen(["mosquitto", "-c", str(tmp / "mosquitto.conf")])
                    time.sleep(0.5)
                    files = {k: tmp / f"{k}-{s}-{rate}-{rep}" for k in ("ready", "stop", "window", "result", "pubresult")}
                    for f in files.values():
                        if f.exists():
                            f.unlink()
                    common = ["--pki", str(tmp), "--tmp", str(tmp), "--system", s, "--rate", str(rate), "--rep", str(rep),
                              "--warm", str(a.warm), "--measure", str(a.measure), "--drain", str(a.drain),
                              "--batch", str(a.batch), "--seed", str(rep), "--payload", a.payload, "--speed", str(speed)] \
                        + (["--skab-dir", a.skab_dir] if a.skab_dir else []) + sum([[f"--{k}", str(v)] for k, v in files.items()], [])
                    ver = subprocess.Popen([sys.executable, __file__, "--role", "verifier"] + common)
                    t0 = time.time()
                    while not files["ready"].exists() and time.time() - t0 < 30:
                        time.sleep(0.05)
                    bproc = psutil.Process(broker.pid)
                    bcpu0 = bproc.cpu_times()
                    pub = subprocess.run([sys.executable, __file__, "--role", "publisher"] + common)
                    bcpu1 = bproc.cpu_times()
                    files["stop"].write_text("stop")
                    ver.wait(timeout=a.warm + a.measure + a.drain + 120)
                    broker.send_signal(signal.SIGTERM)
                    broker.wait(timeout=10)
                    try:
                        r = json.loads(files["result"].read_text())
                        r.update(json.loads(files["pubresult"].read_text()))
                        r.update({"payload": a.payload, "speed": speed, "lost": r["sent"] - r["n_commit_total"]})
                        r["broker_cpu_us_per_msg"] = (bcpu1.user + bcpu1.system - bcpu0.user - bcpu0.system) / max(1, r["sent"]) * 1e6
                    except Exception as e:  # noqa: BLE001
                        r = {"system": s, "rate": rate, "rep": rep, "error": repr(e)}
                    fh.write(json.dumps(r) + "\n")
                    fh.flush()
                    print(f"rep {rep} rate {rate} {s}: p50 {r.get('lat_ms_p50', float('nan')):.2f} ms p99 "
                          f"{r.get('lat_ms_p99', float('nan')):.2f} ms thr {r.get('throughput_msg_s', float('nan')):.0f}/s", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--role", default="orchestrator")
    ap.add_argument("--rates", type=int, nargs="+", default=[200, 500, 1000, 1500])
    ap.add_argument("--reps", type=int, default=5)
    ap.add_argument("--warm", type=float, default=3)
    ap.add_argument("--measure", type=float, default=20)
    ap.add_argument("--drain", type=float, default=5)
    ap.add_argument("--batch", type=int, default=200)
    ap.add_argument("--out", default=None)
    for k in ("pki", "tmp", "system", "ready", "stop", "window", "result", "pubresult"):
        ap.add_argument(f"--{k}", default=None)
    ap.add_argument("--rate", type=int, default=0)
    ap.add_argument("--rep", type=int, default=0)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--systems", nargs="+", default=["B1", "B2", "B3", "PBTI"], help="V3: pipelines to run")
    ap.add_argument("--payload", choices=["synthetic", "skab"], default="synthetic", help="V3: SKAB dataset replay")
    ap.add_argument("--skab-dir", default=None)
    ap.add_argument("--speeds", type=float, nargs="+", default=[1, 5, 10], help="V3: SKAB replay speed-up factors")
    ap.add_argument("--speed", type=float, default=1.0)
    a = ap.parse_args()
    if a.role == "verifier":
        role_verifier(a)
    elif a.role == "publisher":
        role_publisher(a)
    else:
        orchestrate(a)


if __name__ == "__main__":
    main()
