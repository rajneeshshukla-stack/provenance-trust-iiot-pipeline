"""RFC 8785 conformance of the canonicalizer (vectors copied from RFC 8785, Appendix B, Table 1)."""
import struct

import pytest

from pbti.canonical import canonical_str

RFC8785_TABLE1 = [
    ("0000000000000000", "0"),
    ("8000000000000000", "0"),
    ("0000000000000001", "5e-324"),
    ("8000000000000001", "-5e-324"),
    ("7fefffffffffffff", "1.7976931348623157e+308"),
    ("ffefffffffffffff", "-1.7976931348623157e+308"),
    ("4340000000000000", "9007199254740992"),
    ("c340000000000000", "-9007199254740992"),
    ("4430000000000000", "295147905179352830000"),
    ("44b52d02c7e14af5", "9.999999999999997e+22"),
    ("44b52d02c7e14af6", "1e+23"),
    ("44b52d02c7e14af7", "1.0000000000000001e+23"),
    ("444b1ae4d6e2ef4e", "999999999999999700000"),
    ("444b1ae4d6e2ef4f", "999999999999999900000"),
    ("444b1ae4d6e2ef50", "1e+21"),
    ("3eb0c6f7a0b5ed8c", "9.999999999999997e-7"),
    ("3eb0c6f7a0b5ed8d", "0.000001"),
    ("41b3de4355555553", "333333333.3333332"),
    ("41b3de4355555554", "333333333.33333325"),
    ("41b3de4355555555", "333333333.3333333"),
    ("41b3de4355555556", "333333333.3333334"),
    ("41b3de4355555557", "333333333.33333343"),
    ("becbf647612f3696", "-0.0000033333333333333333"),
    ("43143ff3c1cb0959", "1424953923781206.2"),
]


@pytest.mark.parametrize("hexv,expected", RFC8785_TABLE1)
def test_rfc8785_number_vectors(hexv, expected):
    x = struct.unpack(">d", bytes.fromhex(hexv))[0]
    assert canonical_str(x) == expected


@pytest.mark.parametrize("hexv", ["7fffffffffffffff", "7ff0000000000000"])
def test_non_finite_rejected(hexv):
    with pytest.raises(ValueError):
        canonical_str(struct.unpack(">d", bytes.fromhex(hexv))[0])


def test_key_order_and_whitespace():
    assert canonical_str({"b": 1, "a": [True, None, "x"], "c": {"z": 0.5, "y": 5.0}}) == \
        '{"a":[true,null,"x"],"b":1,"c":{"y":5,"z":0.5}}'


def test_benign_reencoding_is_identical():
    import json
    a = {"temp_c": 71.25, "flow": 12.0, "id": "pa-c1-d02"}
    b = json.loads('{ "id" : "pa-c1-d02", "flow": 12.000, "temp_c": 7.125e1 }')
    assert canonical_str(a) == canonical_str(b)


def test_string_escaping():
    assert canonical_str("a\"b\\c\n\u0001€") == '"a\\"b\\\\c\\n\\u0001€"'
