"""Canonical JSON serialization following RFC 8785 (JSON Canonicalization Scheme, JCS).

Scope and stated restrictions (documented in docs/PROTOCOL_SPECIFICATION.md):
  * object keys must be strings; keys are sorted by UTF-16 code units as required by JCS;
  * numbers are serialized with the ECMAScript Number-to-String algorithm that JCS mandates
    (shortest round-trip digits, fixed notation for exponents in [-6, 21));
  * integers must lie inside the IEEE-754 exactly-representable range |x| <= 2**53;
  * NaN / Infinity are rejected (they are not valid JSON).

Signatures in PBTI are computed over these canonical bytes, so a benign re-encoding of the same
logical statement (key order, whitespace, number spelling such as 5.0 vs 5) produces identical
bytes and therefore identical content digests.
"""
from __future__ import annotations

import json
import math
from typing import Any

_MAX_SAFE_INT = 2 ** 53


def _number(x: float | int) -> str:
    if isinstance(x, bool):  # bool is a subclass of int; handled by caller
        raise TypeError("bool is not a number")
    if isinstance(x, int):
        if abs(x) > _MAX_SAFE_INT:
            raise ValueError("integer outside IEEE-754 safe range")
        return str(x)
    if not math.isfinite(x):
        raise ValueError("non-finite numbers are not valid JSON")
    if x == 0:
        return "0"  # also maps -0.0 to "0" as JCS requires
    r = repr(x)  # Python repr yields the shortest round-trip digit string
    sign = ""
    if r[0] == "-":
        sign, r = "-", r[1:]
    if "e" in r:
        mant, e = r.split("e")
        exp = int(e)
    else:
        mant, exp = r, 0
    if "." in mant:
        ip, fp = mant.split(".")
    else:
        ip, fp = mant, ""
    full = ip + fp
    lead = len(full) - len(full.lstrip("0"))
    n = len(ip) - lead + exp  # value = 0.<digits> * 10**n
    digits = full.lstrip("0").rstrip("0") or "0"
    k = len(digits)
    if k <= n <= 21:
        s = digits + "0" * (n - k)
    elif 0 < n <= 21:
        s = digits[:n] + "." + digits[n:]
    elif -6 < n <= 0:
        s = "0." + "0" * (-n) + digits
    else:
        e2 = n - 1
        s = digits[0] + ("." + digits[1:] if k > 1 else "") + "e" + ("+" if e2 >= 0 else "-") + str(abs(e2))
    return sign + s


def canonical_str(o: Any) -> str:
    if o is None:
        return "null"
    if o is True:
        return "true"
    if o is False:
        return "false"
    if isinstance(o, str):
        return json.dumps(o, ensure_ascii=False)
    if isinstance(o, (int, float)):
        return _number(o)
    if isinstance(o, (list, tuple)):
        return "[" + ",".join(canonical_str(v) for v in o) + "]"
    if isinstance(o, dict):
        for k in o:
            if not isinstance(k, str):
                raise TypeError("object keys must be strings")
        items = sorted(o.items(), key=lambda kv: kv[0].encode("utf-16-be"))
        return "{" + ",".join(json.dumps(k, ensure_ascii=False) + ":" + canonical_str(v) for k, v in items) + "}"
    raise TypeError(f"type {type(o).__name__} cannot be canonicalized")


def canonical_bytes(o: Any) -> bytes:
    return canonical_str(o).encode("utf-8")
