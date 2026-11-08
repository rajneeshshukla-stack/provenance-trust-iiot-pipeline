#!/usr/bin/env python3
"""Message-size breakdown of the PBTI wire format versus the baselines (prompt item 2.3).

Encodes the same logical observations with the repository's real-time edge encoder (the encoder used by the
in-process throughput benchmark: 4 gateways x 6 devices, the benchmark's payload function, seed 1) for B1, B2, B3 and
PBTI, and attributes every byte of the canonical-JSON PBTI message to a field by marginal removal (size of the
message minus size of the message without that field). Byte counts do not depend on the machine.

It also reports an *engineering estimate* (not implemented in the prototype) of the same content in a binary
encoding: a minimal CBOR encoder (RFC 8949) written here, with signatures and digests as raw bytes, once with text
keys and once with small integer keys as COSE header labels use; payload floats encoded as float64 (conservative).

Usage: python3 -B message_breakdown.py REPO_DIR OUT_JSON
"""
import json
import random
import struct
import sys
from pathlib import Path

REPO = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2])
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "experiments"))
from pbti.canonical import canonical_bytes  # noqa: E402
from pbti.crypto import ub64u  # noqa: E402
from pbti.realtime import EdgeEncoder, Topology, build_identity  # noqa: E402
from run_throughput import payload  # noqa: E402

N = 2000


# ------------------------------------------------------------------ minimal CBOR (RFC 8949) for the estimate
def _head(major, n):
    if n < 24:
        return bytes([major << 5 | n])
    for ai, fmt, lim in ((24, ">B", 1 << 8), (25, ">H", 1 << 16), (26, ">I", 1 << 32), (27, ">Q", 1 << 64)):
        if n < lim:
            return bytes([major << 5 | ai]) + struct.pack(fmt, n)
    raise ValueError(n)


def cbor(x):
    if x is None:
        return b"\xf6"
    if isinstance(x, bool):
        return b"\xf5" if x else b"\xf4"
    if isinstance(x, int):
        return _head(0, x) if x >= 0 else _head(1, -1 - x)
    if isinstance(x, float):
        return b"\xfb" + struct.pack(">d", x)
    if isinstance(x, bytes):
        return _head(2, len(x)) + x
    if isinstance(x, str):
        b = x.encode()
        return _head(3, len(b)) + b
    if isinstance(x, (list, tuple)):
        return _head(4, len(x)) + b"".join(cbor(v) for v in x)
    if isinstance(x, dict):
        return _head(5, len(x)) + b"".join(cbor(k) + cbor(v) for k, v in x.items())
    raise TypeError(type(x))


B64_FIELDS = {("osig",), ("rsig",), ("rel", "odig"), ("obs", "prev")}


def to_binary(msg, int_keys=False):
    """Same content; base64url signatures/digests as raw bytes; optionally integer keys (per-object label maps)."""
    def conv(obj, path=()):
        if isinstance(obj, dict):
            out = {}
            for i, (k, v) in enumerate(sorted(obj.items())):
                key = i if int_keys and path != ("obs", "pl") else k
                out[key] = conv(v, path + (k,))
            return out
        if path in B64_FIELDS and isinstance(obj, str):
            return ub64u(obj)
        return obj
    return cbor(conv(msg))


def marginal(msg: dict, path: tuple) -> int:
    full = len(canonical_bytes(msg))
    m = json.loads(canonical_bytes(msg))
    d = m
    for p in path[:-1]:
        d = d[p]
    del d[path[-1]]
    return full - len(canonical_bytes(m))


def main():
    topo = Topology(1, 4, 6)
    trust, policy, keys, vkeys = build_identity(topo, use_x509=True)
    rng = random.Random(1)
    devs = [(g, j) for g in range(1, 5) for j in range(1, 7)]
    pls = [payload(rng, 10_000 + (i // 24) * 12) for i in range(N)]
    sizes, msgs = {}, {}
    for s in ("B1", "B2", "B3", "PBTI"):
        enc = EdgeEncoder(s, topo, keys)
        ws = []
        for i in range(N):
            g, j = devs[i % len(devs)]
            ws.append(enc.encode(g, j, 10_000 + (i // 24) * 12, pls[i]))
        msgs[s] = ws
        sizes[s] = sum(len(w) for w in ws) / N
    # field attribution for PBTI (mean over messages)
    fields = [("obs", "pl"), ("obs", "did"), ("obs", "aid"), ("obs", "ts"), ("obs", "sch"),
              ("obs", "v"), ("obs", "typ"), ("obs", "ep"), ("obs", "seq"), ("obs", "prev"), ("obs", "kid"),
              ("osig",), ("rel", "v"), ("rel", "typ"), ("rel", "wid"), ("rel", "wkid"), ("rel", "odig"),
              ("rel", "rts"), ("rel", "mode"), ("rsig",)]
    acc = {"/".join(f): 0.0 for f in fields}
    for w in msgs["PBTI"]:
        m = json.loads(w)
        for f in fields:
            acc["/".join(f)] += marginal(m, f)
    acc = {k: v / N for k, v in acc.items()}
    groups = {
        "content and identifiers also carried by B2 (pl, did, aid, ts, sch)":
            ["obs/pl", "obs/did", "obs/aid", "obs/ts", "obs/sch"],
        "observation-statement additions (v, typ, ep, seq, prev, kid)":
            ["obs/v", "obs/typ", "obs/ep", "obs/seq", "obs/prev", "obs/kid"],
        "origin signature (osig, base64url)": ["osig"],
        "relay statement (v, typ, wid, wkid, odig, rts, mode)":
            ["rel/v", "rel/typ", "rel/wid", "rel/wkid", "rel/odig", "rel/rts", "rel/mode"],
        "relay signature (rsig, base64url)": ["rsig"],
    }
    g_sum = {g: sum(acc[k] for k in ks) for g, ks in groups.items()}
    struct_rest = sizes["PBTI"] - sum(g_sum.values())
    # binary estimates (mean)
    bin_txt = {s: sum(len(to_binary(json.loads(w))) for w in msgs[s]) / N for s in ("B2", "PBTI")}
    bin_int = {s: sum(len(to_binary(json.loads(w), int_keys=True)) for w in msgs[s]) / N for s in ("B2", "PBTI")}
    sample = json.loads(msgs["PBTI"][30])
    res = {
        "n_messages": N, "topology": "4 gateways x 6 devices (1 legacy per gateway), seed 1",
        "mean_wire_bytes_json": sizes, "ratio_PBTI_to_B2_json": sizes["PBTI"] / sizes["B2"],
        "pbti_field_bytes_mean": acc, "pbti_group_bytes_mean": g_sum,
        "pbti_json_structure_and_key_overhead_bytes": struct_rest,
        "pbti_only_bytes_vs_B2": sizes["PBTI"] - sizes["B2"],
        "binary_estimate_text_keys": bin_txt, "binary_estimate_int_keys": bin_int,
        "ratio_PBTI_to_B2_binary_text_keys": bin_txt["PBTI"] / bin_txt["B2"],
        "ratio_PBTI_to_B2_binary_int_keys": bin_int["PBTI"] / bin_int["B2"],
        "sample_pbti_message": sample,
        "sample_b2_message": json.loads(msgs["B2"][30]),
        "note": ("Byte counts are exact for the prototype's canonical JSON; the binary sizes are an engineering estimate "
                 "of the same fields in CBOR, not an implemented or measured format."),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=1))
    print(json.dumps({k: res[k] for k in ("mean_wire_bytes_json", "ratio_PBTI_to_B2_json", "pbti_group_bytes_mean",
                                          "pbti_json_structure_and_key_overhead_bytes", "binary_estimate_text_keys",
                                          "binary_estimate_int_keys", "ratio_PBTI_to_B2_binary_text_keys",
                                          "ratio_PBTI_to_B2_binary_int_keys")}, indent=1))


if __name__ == "__main__":
    main()
