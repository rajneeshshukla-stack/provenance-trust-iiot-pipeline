"""V3 regression test (found by the bounded-check work): a captured message whose numbers lie outside the I-JSON range
(|integer| > 2^53, NaN, infinity) must be rejected with an evidence record, not raise out of ingest (no keys needed)."""
import json

import pytest

from pbti.b5 import B5FeedLevel
from pbti.realtime import EdgeEncoder, Topology, build_identity, make_system
from pbti.store import MemoryStore
from pbti.verifier import REJECT, VerifierConfig

BAD = [("pl-nan", lambda m: m["obs"]["pl"].__setitem__("temp_c", "NaN")),
       ("pl-inf", lambda m: m["obs"]["pl"].__setitem__("temp_c", "1e400")),
       ("pl-bigint", lambda m: m["obs"]["pl"].__setitem__("temp_c", str(2 ** 60))),
       ("seq-bigint", lambda m: m["obs"].__setitem__("seq", str(2 ** 60))),
       ("rts-bigint", lambda m: m["rel"].__setitem__("rts", str(2 ** 60)))]


def _raw(m: dict) -> bytes:
    """JSON with unquoted special numbers, as an attacker on the broker could send them."""
    s = json.dumps(m)
    for tok in ("NaN", "1e400", str(2 ** 60)):
        s = s.replace(f'"{tok}"', tok)
    return s.encode()


def _system(name, topo):
    trust, policy, keys, vkeys = build_identity(topo)
    if name == "B5":
        return B5FeedLevel(trust, policy, vkeys, store=MemoryStore(), cfg=VerifierConfig()), keys
    return make_system(name, trust, policy, vkeys, store=MemoryStore()), keys


@pytest.mark.parametrize("name", ["PBTI", "B5", "B4"])
@pytest.mark.parametrize("label,mut", BAD)
def test_pbti_wire_out_of_range_numbers_rejected(name, label, mut):
    if name == "B4" and label.startswith("rts"):
        pytest.skip("B4 does not use the relay statement")
    topo = Topology(1, 1, 3)
    v, keys = _system(name, topo)
    enc = EdgeEncoder("PBTI", topo, keys)
    m = json.loads(enc.encode(1, 2, 10_000, {"temp_c": 60.0}))
    mut(m)
    n0 = v.n_receipts
    ev0 = getattr(getattr(v, "evidence", None), "bytes", None)
    r = v.ingest(_raw(m), 10_005, {"tid": topo.wid(1), "tkid": "wk:gw1:1", "new_session": True})
    assert r.disp == REJECT
    assert v.n_receipts == n0 + 1
    if ev0 is not None:
        assert v.evidence.bytes > ev0          # one evidence record was written for the receipt


@pytest.mark.parametrize("name", ["B1", "B2", "B3"])
@pytest.mark.parametrize("val", ["NaN", "1e400", str(2 ** 60)])
def test_baseline_out_of_range_payload_rejected(name, val):
    topo = Topology(1, 1, 3)
    v, keys = _system(name, topo)
    enc = EdgeEncoder(name, topo, keys)
    m = json.loads(enc.encode(1, 2, 10_000, {"temp_c": 60.0}))
    body = m["rec"] if name == "B3" else m
    body["pl"]["temp_c"] = val
    r = v.ingest(_raw(m), 10_005, {"tid": topo.wid(1), "tkid": "wk:gw1:1", "new_session": True})
    assert r.disp == REJECT
