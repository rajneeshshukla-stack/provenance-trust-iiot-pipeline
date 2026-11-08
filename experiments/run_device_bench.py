#!/usr/bin/env python3
"""V3 constrained-device micro-benchmark (protocol: docs/V3_HARDWARE_PROTOCOLS.md, section 3).

Run ON the device (Raspberry-Pi-class or comparable). Measures, with the same code paths the edge uses:
  * Ed25519 signing and verification of a PBTI observation statement (device role),
  * the complete edge encoding of one message: observation statement, its signature, relay statement and relay
    signature (gateway role, as for a legacy device), and JCS canonicalisation alone,
  * payload and message sizes.
It records the platform (CPU model, cores, memory, OS, kernel, Python, cryptography/OpenSSL versions), the CPU
frequency governor, and on a Raspberry Pi the SoC temperature and throttling flags before and after the run.
Energy is NOT measured by this script; if a power meter is used, enter its readings with --energy-j-before/after.

Usage:  python3 experiments/run_device_bench.py --label rpi4-1 --n 2000 --out results/raw/v3_device_bench.jsonl
In the study environment this script was only smoke-tested on the server host (label "server-smoke"); no device
measurement was performed. Server results must never be presented as device results.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from pbti.canonical import canonical_bytes  # noqa: E402
from pbti.crypto import DOMAIN_OBS, keypair_from_seed, sign, verify  # noqa: E402
from pbti.envelope import LogicalObs, pbti_obs_dict, pbti_sign_obs, pbti_wire  # noqa: E402


def sh(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:  # noqa: BLE001
        return None


def platform_info():
    import cryptography
    from cryptography.hazmat.backends.openssl import backend
    cpu = None
    try:
        for line in open("/proc/cpuinfo"):
            if line.lower().startswith(("model name", "hardware", "model")):
                cpu = line.split(":", 1)[1].strip()
                break
    except OSError:
        pass
    mem = None
    try:
        mem = int(open("/proc/meminfo").readline().split()[1]) // 1024
    except Exception:  # noqa: BLE001
        pass
    gov = None
    try:
        gov = open("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor").read().strip()
    except OSError:
        pass
    return {"cpu": cpu or platform.processor(), "machine": platform.machine(), "cores": os.cpu_count(), "mem_mb": mem,
            "os": platform.platform(), "kernel": platform.release(), "python": sys.version.split()[0],
            "cryptography": cryptography.__version__, "openssl": backend.openssl_version_text(), "governor": gov}


def thermal():
    t = sh(["vcgencmd", "measure_temp"])
    thr = sh(["vcgencmd", "get_throttled"])
    if t is None:
        try:
            t = str(int(open("/sys/class/thermal/thermal_zone0/temp").read()) / 1000) + "C"
        except Exception:  # noqa: BLE001
            t = None
    return {"temp": t, "throttled": thr}


def timeit(fn, n):
    cpu, wall = [], []
    for _ in range(n):
        c0, w0 = time.process_time_ns(), time.perf_counter_ns()
        fn()
        cpu.append(time.process_time_ns() - c0)
        wall.append(time.perf_counter_ns() - w0)
    q = sorted(wall)
    return {"n": n, "cpu_us_mean": statistics.fmean(cpu) / 1e3, "wall_us_mean": statistics.fmean(wall) / 1e3,
            "wall_us_p50": q[n // 2] / 1e3, "wall_us_p95": q[int(0.95 * n)] / 1e3, "wall_us_p99": q[int(0.99 * n)] / 1e3}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True, help="device label, e.g. rpi4-1 (use 'server-smoke' for a host test)")
    ap.add_argument("--n", type=int, default=2000)
    ap.add_argument("--warmup", type=int, default=200)
    ap.add_argument("--energy-j-before", type=float, default=None)
    ap.add_argument("--energy-j-after", type=float, default=None)
    ap.add_argument("--key-storage", default="file (PKCS8, unencrypted) -- record the real storage on the device")
    ap.add_argument("--power-mode", default=None, help="e.g. 'official 5V/3A PSU, no USB load'")
    ap.add_argument("--out", default=str(ROOT / "results" / "raw" / "v3_device_bench.jsonl"))
    a = ap.parse_args()
    seed = b"pbti-device-bench"
    dsk, dpk = keypair_from_seed(seed, "dk:bench:1")
    wsk, wpk = keypair_from_seed(seed, "wk:bench:1")
    pl = {"temp_c": 61.23, "vib_mm_s": 2.031, "press_bar": 5.012, "flow_m3h": 12.07}
    state = {"seq": 0, "prev": None}

    def obs():
        state["seq"] += 1
        return LogicalObs("pa-c1-d02", "pa-c1-a02", 0, state["seq"], 1_700_000_000_000 + state["seq"] * 1000,
                          "telemetry.v1", pl, f"{state['seq']:016x}", state["prev"])
    o = obs()
    d = pbti_obs_dict(o, "dk:bench:1")
    cb = canonical_bytes(d)
    sig = sign(dsk, DOMAIN_OBS, cb)
    for _ in range(a.warmup):
        sign(dsk, DOMAIN_OBS, cb)
        verify(dpk, DOMAIN_OBS, cb, sig)
    th0 = thermal()
    res = {
        "jcs_canonicalize": timeit(lambda: canonical_bytes(d), a.n),
        "ed25519_sign_obs": timeit(lambda: sign(dsk, DOMAIN_OBS, cb), a.n),
        "ed25519_verify_obs": timeit(lambda: verify(dpk, DOMAIN_OBS, cb, sig), a.n),
        "device_role_sign_statement": timeit(lambda: pbti_sign_obs(obs(), dsk, "dk:bench:1"), a.n),
        "gateway_role_full_message": timeit(lambda: pbti_wire(*pbti_sign_obs(obs(), wsk, "wk:bench:1"),
                                                             "spiffe://plant-a.example/cell1/gw1/collector", "wk:bench:1",
                                                             wsk, 1_700_000_000_000, "live"), a.n),
    }
    th1 = thermal()
    obs_d, osig = pbti_sign_obs(obs(), dsk, "dk:bench:1")
    wire = pbti_wire(obs_d, osig, "spiffe://plant-a.example/cell1/gw1/collector", "wk:bench:1", wsk, 1, "live")
    row = {"label": a.label, "time": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "platform": platform_info(),
           "thermal_before": th0, "thermal_after": th1, "power_mode": a.power_mode, "key_storage": a.key_storage,
           "payload_bytes": len(canonical_bytes(pl)), "statement_bytes": len(canonical_bytes(obs_d)), "message_bytes": len(wire),
           "energy_j": (a.energy_j_after - a.energy_j_before) if a.energy_j_before is not None and a.energy_j_after is not None else None,
           "results": res,
           "note": "device measurement" if not a.label.startswith("server") else "SERVER SMOKE TEST - not a device measurement"}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "a") as fh:
        fh.write(json.dumps(row) + "\n")
    for k, v in res.items():
        print(f"{k:28s} mean {v['wall_us_mean']:8.1f} us  p99 {v['wall_us_p99']:8.1f} us  cpu {v['cpu_us_mean']:8.1f} us")
    print("message bytes", len(wire), "->", a.out)


if __name__ == "__main__":
    main()
