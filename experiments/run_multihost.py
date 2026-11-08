#!/usr/bin/env python3
"""V3 multi-host MQTT/TLS deployment harness (protocol: docs/V3_HARDWARE_PROTOCOLS.md, section 2). NOT PERFORMED in
the study: only a functional test with all roles on one host was run, which is not a multi-host experiment.

Roles (run each on its own host; hosts share a PKI directory copied once, and agree on a start time):
  pki        --pki DIR --broker-names NAME[,IP...]      create CA, broker, verifier and gateway certificates + ACL
  broker     --pki DIR                                   run Mosquitto (mTLS, per-gateway identity, per-topic ACL)
  verifier   --pki DIR --broker HOST --system S --start-at T --out FILE
  publisher  --pki DIR --broker HOST --system S --rate R --start-at T --out FILE
  hostinfo   --out FILE                                  CPU, cores, memory, OS, kernel, Python, library versions,
                                                         clock synchronisation state (chrony/timedatectl)
Latency = verifier durable-commit time - publisher send time, both on CLOCK_REALTIME. The two hosts' clocks must be
synchronised (PTP or NTP); record the offset with `chronyc tracking` before and after each run, and treat
|offset| + its uncertainty as the latency error bound. RTT and bandwidth: `ping -c 100 HOST`, `iperf3 -c HOST -t 20`.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import queue
import random
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))
PORT = 8883
TOPO = dict(n_gw=4, dev_per_gw=6)


def role_pki(a):
    import datetime as dt
    import ipaddress
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID
    d = Path(a.pki)
    d.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now(dt.timezone.utc)
    name = lambda cn: x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])  # noqa: E731
    ca_key = ec.generate_private_key(ec.SECP256R1())
    ca = (x509.CertificateBuilder().subject_name(name("pbti-tls-ca")).issuer_name(name("pbti-tls-ca"))
          .public_key(ca_key.public_key()).serial_number(1).not_valid_before(now - dt.timedelta(days=1))
          .not_valid_after(now + dt.timedelta(days=30)).add_extension(x509.BasicConstraints(ca=True, path_length=None), True)
          .sign(ca_key, hashes.SHA256()))
    (d / "ca.crt").write_bytes(ca.public_bytes(serialization.Encoding.PEM))
    sans = []
    for n in a.broker_names.split(","):
        try:
            sans.append(x509.IPAddress(ipaddress.ip_address(n)))
        except ValueError:
            sans.append(x509.DNSName(n))

    def leaf(cn, san=None):
        k = ec.generate_private_key(ec.SECP256R1())
        b = (x509.CertificateBuilder().subject_name(name(cn)).issuer_name(ca.subject).public_key(k.public_key())
             .serial_number(x509.random_serial_number()).not_valid_before(now - dt.timedelta(days=1))
             .not_valid_after(now + dt.timedelta(days=30)))
        if san:
            b = b.add_extension(x509.SubjectAlternativeName(san), False)
        (d / f"{cn}.crt").write_bytes(b.sign(ca_key, hashes.SHA256()).public_bytes(serialization.Encoding.PEM))
        (d / f"{cn}.key").write_bytes(k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                                      serialization.NoEncryption()))
    leaf("server", sans)
    leaf("verifier")
    for g in range(1, TOPO["n_gw"] + 1):
        leaf(f"gw{g}")
    acl = ["user verifier", "topic read pbti/#", ""] + sum([[f"user gw{g}", f"topic write pbti/gw{g}/#", ""]
                                                           for g in range(1, TOPO["n_gw"] + 1)], [])
    (d / "acl").write_text("\n".join(acl))
    (d / "mosquitto.conf").write_text(f"""per_listener_settings true
listener {PORT} 0.0.0.0
cafile {d.resolve()}/ca.crt
certfile {d.resolve()}/server.crt
keyfile {d.resolve()}/server.key
require_certificate true
use_identity_as_username true
allow_anonymous false
acl_file {d.resolve()}/acl
max_inflight_messages 0
max_queued_messages 0
persistence false
log_dest none
""")
    print("PKI written to", d, "- copy the directory to every host (keys are test keys for this experiment only)")


def client(d: Path, cn: str, cid: str):
    import paho.mqtt.client as mqtt
    c = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, client_id=cid, protocol=mqtt.MQTTv5)
    c.tls_set(ca_certs=str(d / "ca.crt"), certfile=str(d / f"{cn}.crt"), keyfile=str(d / f"{cn}.key"))
    c.max_inflight_messages_set(0)
    c.max_queued_messages_set(0)
    return c


def hostinfo():
    import cryptography
    info = {"host": platform.node(), "os": platform.platform(), "kernel": platform.release(), "python": sys.version.split()[0],
            "cryptography": cryptography.__version__, "cores": os.cpu_count(), "time": time.time()}
    try:
        info["cpu"] = [l for l in open("/proc/cpuinfo") if l.lower().startswith("model name")][0].split(":")[1].strip()
        info["mem_mb"] = int(open("/proc/meminfo").readline().split()[1]) // 1024
    except Exception:  # noqa: BLE001
        pass
    for k, cmd in (("chrony", ["chronyc", "tracking"]), ("timedatectl", ["timedatectl", "show"]),
                   ("mosquitto", ["mosquitto", "-h"])):
        try:
            info[k] = subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout.strip().splitlines()[:12]
        except Exception:  # noqa: BLE001
            info[k] = None
    return info


def vtime(a) -> int:
    """Protocol time (ms) shared by publisher and verifier: CLOCK_REALTIME relative to the agreed start, + 10 s."""
    return 10_000 + time.time_ns() // 1_000_000 - int(a.start_at * 1000)


def wait_until(t):
    while True:
        dt_s = t - time.time()
        if dt_s <= 0:
            return
        time.sleep(min(0.05, dt_s))


def role_verifier(a):
    import psutil
    from pbti.realtime import Topology, build_identity, make_system
    from pbti.store import SQLiteStore
    d = Path(a.pki)
    topo = Topology(a.seed, **TOPO)
    trust, policy, keys, vkeys = build_identity(topo)
    db = f"{a.db}-{a.system}-{a.rate}-{a.rep}"
    for suf in ("", "-wal", "-shm"):          # fresh database per run
        if os.path.exists(db + suf):
            os.remove(db + suf)
    store = SQLiteStore(db)
    sysobj = make_system(a.system, trust, policy, vkeys, store=store)
    q: queue.SimpleQueue = queue.SimpleQueue()

    def on_message(cl, ud, msg):
        ts = next((int(v) for k, v in (msg.properties.UserProperty or []) if k == "ts"), 0)
        q.put((msg.topic, msg.payload, ts))
    c = client(d, "verifier", f"verifier-{a.system}-{a.rep}")
    c.on_message = on_message
    c.on_connect = lambda cl, ud, fl, rc, pr: cl.subscribe("pbti/#", qos=1)
    c.connect(a.broker, PORT, keepalive=60)
    c.loop_start()
    t0, t1 = a.start_at + a.warm, a.start_at + a.warm + a.measure
    end = t1 + a.drain
    proc = psutil.Process()
    lat, pending, seen, qd = [], [], set(), []
    last = time.time()
    cpu0 = None
    while time.time() < end:
        try:
            topic, payload, ts = q.get(timeout=0.002)
        except queue.Empty:
            if pending and time.time() - last > 0.010:
                store.flush()
                now = time.time_ns()
                lat += [now - t for t in pending if t0 * 1e9 <= t <= t1 * 1e9]
                pending.clear()
                last = time.time()
            continue
        qd.append(q.qsize() + 1)
        if cpu0 is None and time.time() >= t0:
            cpu0 = proc.cpu_times()
        g = int(topic.split("/")[1][2:])
        sysobj.ingest(payload, vtime(a), {"tid": topo.wid(g), "tkid": f"wk:gw{g}:1", "new_session": g not in seen})
        seen.add(g)
        pending.append(ts)
        if len(pending) >= a.batch or time.time() - last > 0.010:
            store.flush()
            now = time.time_ns()
            lat += [now - t for t in pending if t0 * 1e9 <= t <= t1 * 1e9]
            pending.clear()
            last = time.time()
    cpu1 = proc.cpu_times()
    c.loop_stop()
    lat.sort()
    qq = lambda p: lat[min(len(lat) - 1, int(p / 100 * len(lat)))] / 1e6 if lat else None  # noqa: E731
    out = {"role": "verifier", "system": a.system, "rep": a.rep, "rate": a.rate, "n_measured": len(lat),
           "lat_ms_p50": qq(50), "lat_ms_p95": qq(95), "lat_ms_p99": qq(99),
           "verifier_cpu_s": (cpu1.user + cpu1.system - cpu0.user - cpu0.system) if cpu0 else None,
           "queue_depth_max": max(qd) if qd else 0, "rss_mb": proc.memory_info().rss / 2 ** 20,
           "dispositions": dict(sysobj.counts), "db_bytes": store.db_bytes(), "host": hostinfo()}
    store.close()
    with open(a.out, "a") as fh:
        fh.write(json.dumps(out) + "\n")


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
        c.connect(a.broker, PORT, keepalive=60)
        c.loop_start()
        cls.append(c)
    rng = random.Random(a.seed)
    devs = [(g, j) for g in range(1, topo.n_gw + 1) for j in range(1, topo.dev_per_gw + 1)]
    wait_until(a.start_at)
    t_start = time.time()
    t_end = t_start + a.warm + a.measure
    proc = psutil.Process()
    cpu0 = proc.cpu_times()
    i = 0
    while time.time() < t_end:
        dt_s = t_start + i / a.rate - time.time()
        if dt_s > 0:
            time.sleep(min(dt_s, 0.002))
            continue
        g, j = devs[i % len(devs)]
        pl = {"temp_c": round(60 + rng.gauss(0, 0.5), 2), "vib_mm_s": round(2 + rng.gauss(0, 0.05), 3),
              "press_bar": round(5 + rng.gauss(0, 0.02), 3), "flow_m3h": round(12 + rng.gauss(0, 0.1), 2)}
        wire = enc.encode(g, j, vtime(a), pl)
        props = Properties(PacketTypes.PUBLISH)
        props.UserProperty = ("ts", str(time.time_ns()))
        cls[g - 1].publish(f"pbti/gw{g}/{topo.dids(g)[j - 1]}", wire, qos=1, properties=props)
        i += 1
    cpu1 = proc.cpu_times()
    time.sleep(a.drain)
    for c in cls:
        c.loop_stop()
        c.disconnect()
    with open(a.out, "a") as fh:
        fh.write(json.dumps({"role": "publisher", "system": a.system, "rep": a.rep, "rate": a.rate, "sent": i,
                             "achieved_rate": i / (a.warm + a.measure),
                             "publisher_cpu_us_per_msg": (cpu1.user + cpu1.system - cpu0.user - cpu0.system) / max(1, i) * 1e6,
                             "host": hostinfo()}) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("role", choices=["pki", "broker", "verifier", "publisher", "hostinfo"])
    ap.add_argument("--pki", default="pki")
    ap.add_argument("--broker-names", default="localhost,127.0.0.1")
    ap.add_argument("--broker", default="127.0.0.1")
    ap.add_argument("--system", default="PBTI")
    ap.add_argument("--rate", type=int, default=500)
    ap.add_argument("--rep", type=int, default=1)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--start-at", type=float, default=0.0, help="agreed CLOCK_REALTIME start (epoch seconds)")
    ap.add_argument("--warm", type=float, default=3)
    ap.add_argument("--measure", type=float, default=30)
    ap.add_argument("--drain", type=float, default=5)
    ap.add_argument("--batch", type=int, default=200)
    ap.add_argument("--db", default="/tmp/pbti-multihost", help="database path prefix (one fresh file per run)")
    ap.add_argument("--out", default="multihost.jsonl")
    a = ap.parse_args()
    if a.role == "pki":
        role_pki(a)
    elif a.role == "broker":
        os.execvp("mosquitto", ["mosquitto", "-c", str(Path(a.pki) / "mosquitto.conf")])
    elif a.role == "verifier":
        role_verifier(a)
    elif a.role == "publisher":
        role_publisher(a)
    else:
        with open(a.out, "a") as fh:
            fh.write(json.dumps({"role": "hostinfo", **hostinfo()}) + "\n")


if __name__ == "__main__":
    main()
