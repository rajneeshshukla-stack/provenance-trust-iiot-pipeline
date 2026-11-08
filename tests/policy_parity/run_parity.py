#!/usr/bin/env python3
"""Decision-parity harness: policies/admission.rego (Rego v1) versus the Python PDP (src/pbti/policy.py).

Usage
  python3 tests/policy_parity/run_parity.py [--repo PATH] [--backend regopy|opa] [--out parity_results.json]
                         [--opa-bin PATH] [--opa-per-case] [--opa-dry-run DIR]

Rego back ends
  regopy  Microsoft rego-cpp Python bindings (`pip install --break-system-packages regopy`). One interpreter
          per policy version; one input document + one query per case.
  opa     `opa eval`, ONLY if an `opa` binary is already installed (PATH or --opa-bin). This harness never
          downloads or installs OPA. Batch mode (default) evaluates every case of one policy version in a single
          `opa eval` process with `with input as`; --opa-per-case runs one process per case.
          --opa-dry-run DIR writes the data/input files and the exact commands without running anything.
          NOTE: the OPA path was NOT executed in the validation run documented in README.md.

What is compared
  Python : PDP(PolicyStore).evaluate(did, aid, wid, sch, origin_kind, t_ms) -> (permit, reason, policy_version)
           (default check_origin=True, i.e. the call made by the PBTI verifier, verifier.py line 209).
  Rego   : data.pbti.admission.allow and data.pbti.admission.reason with data.pbti = the policy-version document
           and input = {"did", "aid", "wid", "sch", "origin_kind"}.
  Input convention: every case is one JSON object; a field absent from the object is passed to Python as None
  (Python's signature has no notion of "absent"); Rego sees it as undefined. Policy versions: Python selects the
  version itself from t_ms (PDP.active_version); Rego has no time input, so the harness loads the document of the
  version that is in force at t_ms (independently computed) and also checks the version Python reports.

The policy layer decides only (permit, reason) from (version, did, aid, wid, sch, origin kind). Credential
validity, expiry/rotation grace, revocation, freshness (skew/horizon), quarantine and delivery history are
verifier checks outside the PDP (src/pbti/verifier.py) and are deliberately NOT simulated here; see the
"scope" section of the results file.
"""
from __future__ import annotations

import argparse
import collections
import copy
import datetime as dt
import hashlib
import itertools
import json
import os
import platform
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HARNESS_VERSION = "1.0"
FIELDS = ("did", "aid", "wid", "sch", "origin_kind")
QUERY = "x := [data.pbti.admission.allow, data.pbti.admission.reason]"
QUERY_ALLOW = "x := data.pbti.admission.allow"
QUERY_REASON = "x := data.pbti.admission.reason"
OPA_BATCH_QUERY = ("x := {i: [a, r] | some i; c := data.parity_cases[i]; "
                   "a := data.pbti.admission.allow with input as c; "
                   "r := data.pbti.admission.reason with input as c}")

# Policy history built on top of the standard S01 world (all changes made through World.policy_update, i.e. the
# repository's own deep-copy + mutate + PolicyStore.update path):
T_MOVE, T_DEV_OFF, T_WL_OFF, T_RECOVER = 150_000, 200_000, 250_000, 280_000
INACTIVE_DEV = "pa-c2-d03"
INACTIVE_WL = "spiffe://plant-a.example/cell4/gw4/collector"

SCOPE = [
    {"category": "valid/invalid credentials", "status": "not a PDP decision (only its origin-kind outcome is)",
     "where": "verifier.py ingest stages 2-3: UNKNOWN_KEY, KEY_SUBJECT_MISMATCH, KEY_KIND_INVALID, INTEGRITY_RELAY, "
              "BINDING_MISMATCH, INTEGRITY_OBS (identity.py TrustView/TrustRegistry; crypto.verify)",
     "covered_here": "The PDP only receives origin_kind, derived from the verified key kind ('device'|'workload'). "
                     "Origin-kind combinations are tested (category origin_kind_mismatch and the grid)."},
    {"category": "expired credentials", "status": "not a PDP decision",
     "where": "verifier.py ingest stage 4: KEY_NOT_YET_VALID, KEY_EXPIRED (quarantine), KEY_IN_GRACE annotation "
              "(params.rotation_grace_ms is read from the policy document but applied by the verifier)",
     "covered_here": "nothing (no PDP input carries validity times)"},
    {"category": "revocation", "status": "not a PDP decision",
     "where": "verifier.py ingest stage 4 and _apply_taints: REVOKED, REVOKED_BUFFERED (quarantine), taint propagation "
              "(identity.py TrustView.status)",
     "covered_here": "nothing. Deactivating a device/workload in the policy document ('active': false) IS a PDP "
                     "decision and is tested (inactive_device, inactive_workload), but it is not credential revocation."},
    {"category": "legacy data", "status": "partially a PDP decision",
     "where": "PDP: legacy devices carry origin requirement 'gateway' (the edge workload may sign for them). "
              "Aged/buffered legacy data is a freshness decision in verifier.py (STALE_TS, FUTURE_TS, STALE_EPOCH).",
     "covered_here": "gateway-origin (legacy) devices with every origin kind (grid + origin_kind_mismatch); "
                     "data age is out of scope"},
    {"category": "path violations", "status": "PDP decision", "where": "policy.py PDP._decide: ASSET_NOT_ASSIGNED, "
     "WORKLOAD_NOT_REGISTERED, PATH_NOT_AUTHORIZED", "covered_here": "grid (all versions), asset_not_assigned, "
     "unknown_workload, device_moved"},
    {"category": "missing fields", "status": "PDP-level only; unreachable through the PBTI verifier",
     "where": "envelope.pbti_parse rejects missing/empty/non-string did, aid, sch, wid as MALFORMED before the PDP; "
              "origin_kind is computed by the verifier",
     "covered_here": "missing_fields (each field absent, all absent)"},
    {"category": "malformed input", "status": "PDP-level only; unreachable through the PBTI verifier",
     "where": "envelope.pbti_parse (type/length checks) before the PDP", "covered_here":
     "wrong_types, empty_strings; plus malformed_policy_document (both evaluators validate the policy document: the "
     "Python PolicyStore refuses a schema-violating document at load time, the Rego policy denies with "
     "POLICY_DOCUMENT_INVALID)"},
    {"category": "quarantine and recovery", "status": "not a PDP decision",
     "where": "verifier.py: QUARANTINE dispositions (FUTURE_TS, STALE_TS, KEY_EXPIRED, REVOKED_BUFFERED, STALE_SLOT, "
              "STALE_EPOCH, SEQ_JUMP) and later re-delivery; the PDP returns only permit/deny",
     "covered_here": "only policy-level recovery: version v5 re-activates the device and workload deactivated in "
                     "v3/v4; decisions under v5 are compared with v2"},
    {"category": "unknown identity", "status": "partially a PDP decision",
     "where": "PDP: unknown did -> DEVICE_NOT_REGISTERED, unknown wid -> WORKLOAD_NOT_REGISTERED. Unknown keys "
              "(UNKNOWN_KEY) are rejected by the verifier before the PDP.",
     "covered_here": "unknown_device, unknown_workload"},
    {"category": "clock-boundary conditions", "status": "partially a PDP decision",
     "where": "PDP: the only time dependence is policy-version selection (PDP.active_version: latest version with "
              "t_ms <= t; earliest version if none). Skew (skew_max_ms), horizon (h_max_ms), retry window, epoch "
              "drain and rotation grace are verifier checks.",
     "covered_here": "version_selection_clock_boundary (t_k-1, t_k, t_k+1 for every version change; t<0; far "
                     "future). Rego has no time input: version selection is the integrator's job, so only the Python "
                     "selection is tested and Rego is evaluated on the version in force."},
]


# ===================================================================================== helpers
def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def jround(x):
    """JSON round trip: guarantees every case is JSON-representable and both sides see the same values."""
    return json.loads(json.dumps(x))


def classify(py: dict, rg: dict) -> str | None:
    pe, re_ = "error" in py, "error" in rg
    if pe and re_:
        return "BOTH_ERROR"
    if pe:
        return "PY_ERROR"
    if re_:
        return "REGO_ERROR"
    if py["allow"] != rg["allow"]:
        return "ALLOW_MISMATCH"
    if py["reason"] != rg["reason"]:
        return "REASON_MISMATCH"
    return None


# ===================================================================================== Python side
class PySide:
    def __init__(self, repo: Path):
        sys.dont_write_bytecode = True  # never write __pycache__ into the (read-only) repository
        sys.path.insert(0, str(repo / "src"))
        from pbti.policy import PDP, PolicyStore  # noqa: E402
        from pbti.scenarios import build, move_device  # noqa: E402
        self.PDP, self.PolicyStore = PDP, PolicyStore
        w = build("S01_normal", "PBTI", 1)
        self.world = w
        self.s01_doc = copy.deepcopy(w.policy_doc)
        self.moved_did = w.gateways[2].devices[5].did  # the device S99_mixed moves cell3 -> cell2 at t=150 s
        self.move_from = f"spiffe://plant-a.example/cell{w.devices[self.moved_did].g}/gw{w.devices[self.moved_did].g}/collector"
        self.move_to = "spiffe://plant-a.example/cell2/gw2/collector"
        move_device(w, self.moved_did, 2, T_MOVE)                       # repository helper (policy part used)
        w.policy_update(T_DEV_OFF, lambda d: d["devices"][INACTIVE_DEV].__setitem__("active", False))
        w.policy_update(T_WL_OFF, lambda d: d["workloads"][INACTIVE_WL].__setitem__("active", False))

        def recover(d):
            d["devices"][INACTIVE_DEV]["active"] = True
            d["workloads"][INACTIVE_WL]["active"] = True
        w.policy_update(T_RECOVER, recover)
        # fire ONLY the scheduled policy-update events (the simulation itself is not run)
        fired = []
        for (t, _, fn, args) in sorted(w.q, key=lambda e: (e[0], e[1])):
            if fn.__qualname__.endswith("policy_update.<locals>.up"):
                w.now = t
                fn(*args)
                fired.append(t)
        self.store = w.policy
        assert [v.t_ms for v in self.store.versions] == [0, T_MOVE, T_DEV_OFF, T_WL_OFF, T_RECOVER], fired
        self.pdp = PDP(self.store)
        self.version_notes = {1: "S01_normal world policy (build('S01_normal','PBTI',1).policy_doc)",
                              2: f"{self.moved_did} moved cell3 -> cell2 via scenarios.move_device (as in S99_mixed)",
                              3: f"v2 + device {INACTIVE_DEV} active=false",
                              4: f"v3 + workload {INACTIVE_WL} active=false",
                              5: f"v4 + {INACTIVE_DEV} and {INACTIVE_WL} re-activated (should decide like v2)"}
        self.extra = {}  # malformed-document stores: key -> (PolicyStore|None, PDP|None, store_error)

    def version_doc(self, v: int) -> dict:
        return self.store.get(v).doc

    def expected_version(self, t: int) -> int:
        """Independent statement of the documented rule: latest version with t_ms <= t, else the first one."""
        cands = [v.version for v in self.store.versions if v.t_ms <= t]
        return max(cands) if cands else 1

    def add_store(self, key: str, doc: dict) -> None:
        try:
            st = self.PolicyStore(doc, 0)
            self.extra[key] = (st, self.PDP(st), None)
        except Exception as e:  # noqa: BLE001
            self.extra[key] = (None, None, f"{type(e).__name__}: {e}")

    def evaluate(self, key, inp: dict, t: int) -> dict:
        args = tuple(inp.get(k) for k in FIELDS)  # absent field -> None
        if key == "main":
            pdp = self.pdp
        else:
            st, pdp, err = self.extra[key]
            if pdp is None:
                return {"error": "PolicyStore construction failed: " + err}
        try:
            permit, why, pv = pdp.evaluate(*args, t)
            res = {"allow": permit, "reason": why, "version": pv}
        except Exception as e:  # noqa: BLE001
            res = {"error": f"{type(e).__name__}: {e}"}
        # uncached decision core on the same version: separates memo-cache artefacts from policy logic
        try:
            a, r = self.PDP._decide(pdp.active_version(t).doc, *args)
            res["uncached"] = {"allow": a, "reason": r}
        except Exception as e:  # noqa: BLE001
            res["uncached"] = {"error": f"{type(e).__name__}: {e}"}
        return res


# ===================================================================================== Rego back ends
class RegopyBackend:
    name = "regopy"

    def __init__(self, rego_src: str):
        import regopy
        from regopy import Interpreter
        self.Interpreter = Interpreter
        self.src = rego_src
        self.interp = {}
        self.info = {"regopy_version": getattr(regopy, "__version__", None),
                     "rego_cpp_build_info": regopy.build_info() if callable(regopy.build_info) else str(regopy.build_info),
                     "input_mode": "set_input_term(json.dumps(case)) (JSON text, as OPA would receive it)",
                     "query": QUERY}

    def load(self, key, doc: dict) -> None:
        r = self.Interpreter()
        r.add_module("admission.rego", self.src)
        r.add_data({"pbti": doc})
        self.interp[key] = r

    def _q(self, r, q):
        out = r.query(q)
        if not out.ok():
            return None, "rego error: " + str(out).replace("\n", " ")[:500]
        s = str(out)
        if s == "undefined" or not out.results or "x" not in out.results[0].bindings:
            return None, "undefined"
        return out.results[0].bindings["x"], None

    def evaluate_one(self, key, inp: dict, as_python_value: bool = False) -> dict:
        r = self.interp[key]
        if as_python_value:
            r.set_input(inp)
        else:
            r.set_input_term(json.dumps(inp))
        val, err = self._q(r, QUERY)
        if err is None:
            return {"allow": val[0], "reason": val[1]}
        a, ea = self._q(r, QUERY_ALLOW)        # diagnose which rule failed
        rs, er = self._q(r, QUERY_REASON)
        res = {"error": err}
        if ea is None:
            res["allow_alone"] = a
        if er is None:
            res["reason_alone"] = rs
        return res

    def evaluate_many(self, key, inputs: list) -> list:
        return [self.evaluate_one(key, i) for i in inputs]


class OpaBackend:
    """`opa eval` back end. Only usable when an opa binary is ALREADY installed; never downloads anything."""
    name = "opa"

    def __init__(self, rego_path: Path, opa_bin: str | None, per_case: bool = False, dry_run_dir: str | None = None):
        self.rego_path, self.per_case, self.dry = rego_path, per_case, dry_run_dir
        self.opa = opa_bin or shutil.which("opa")
        if not self.opa and not self.dry:
            raise RuntimeError("BLOCKED: no 'opa' binary on PATH (and --opa-bin not given); this harness does not "
                               "download OPA. Install OPA by an approved route, or use --backend regopy.")
        self.docs = {}
        self.work = Path(dry_run_dir) if dry_run_dir else Path(tempfile.mkdtemp(prefix="parity-opa-"))
        self.work.mkdir(parents=True, exist_ok=True)
        self.commands = []
        ver = None
        if self.opa and not self.dry:
            ver = subprocess.run([self.opa, "version"], capture_output=True, text=True).stdout.strip()
        self.info = {"opa_bin": self.opa, "opa_version": ver, "mode": "per-case" if per_case else "batch",
                     "batch_query": OPA_BATCH_QUERY, "query": QUERY, "dry_run_dir": dry_run_dir}

    def load(self, key, doc):
        self.docs[key] = doc

    def _run(self, args, stdin=None):
        self.commands.append(shlex.join(args) + (" < input.json" if stdin is not None else ""))
        if self.dry:
            return None
        p = subprocess.run(args, input=stdin, capture_output=True, text=True, timeout=600)
        return p

    @staticmethod
    def _safe(key) -> str:
        if isinstance(key, tuple):
            return f"{key[0]}_v{key[1]}"
        return str(key).replace(":", "_").replace("/", "_")

    def evaluate_many(self, key, inputs: list) -> list:
        safe = self._safe(key)
        if self.per_case:
            return self._per_case(safe, key, inputs)
        data = self.work / f"data_{safe}.json"
        data.write_text(json.dumps({"pbti": self.docs[key], "parity_cases": inputs}))
        p = self._run([self.opa or "opa", "eval", "--format=json", "--data", str(self.rego_path), "--data", str(data),
                       OPA_BATCH_QUERY])
        if p is None:
            return [{"error": "dry-run (not executed)"} for _ in inputs]
        if p.returncode != 0:  # e.g. a conflict error in one case aborts the batch: fall back to per-case
            return self._per_case(safe, key, inputs)
        x = json.loads(p.stdout)["result"][0]["bindings"]["x"]
        out = []
        for i in range(len(inputs)):
            v = x.get(str(i), x.get(i)) if isinstance(x, dict) else None
            out.append({"allow": v[0], "reason": v[1]} if v is not None else {"error": "undefined"})
        return out

    def _per_case(self, safe, key, inputs):
        data = self.work / f"data_{safe}_only.json"
        data.write_text(json.dumps({"pbti": self.docs[key]}))
        out = []
        for inp in inputs:
            p = self._run([self.opa or "opa", "eval", "--format=json", "--data", str(self.rego_path), "--data",
                           str(data), "--stdin-input", QUERY], stdin=json.dumps(inp))
            if p is None:
                out.append({"error": "dry-run (not executed)"})
            elif p.returncode != 0:
                out.append({"error": "opa error: " + (p.stdout + p.stderr)[:500]})
            else:
                res = json.loads(p.stdout).get("result")
                if not res:
                    out.append({"error": "undefined"})
                else:
                    v = res[0]["bindings"]["x"]
                    out.append({"allow": v[0], "reason": v[1]})
        return out


# ===================================================================================== cases
def grid_cases(doc: dict) -> tuple[list, dict]:
    dids = sorted(doc["devices"])
    aids = sorted({a for d in doc["devices"].values() for a in d["assets"]})
    wids = sorted(doc["workloads"])
    schs = sorted({s for d in doc["devices"].values() for s in d.get("schemas", [])})
    origins = sorted({"device", "workload"} | {d.get("origin", "device") for d in doc["devices"].values()})
    dom = {"did": dids, "aid": aids, "wid": wids, "sch": schs, "origin_kind": origins}
    cases = [dict(zip(FIELDS, c)) for c in itertools.product(dids, aids, wids, schs, origins)]
    return cases, dom


def boundary_cases(py: PySide) -> list:
    """Each case: (category, label, store_key, t_ms, expected_version or None, input)."""
    W = lambda g: f"spiffe://plant-a.example/cell{g}/gw{g}/collector"  # noqa: E731
    dev_ok = {"did": "pa-c1-d02", "aid": "pa-c1-a02", "wid": W(1), "sch": "telemetry.v1", "origin_kind": "device"}
    leg_ok = {"did": "pa-c1-d01", "aid": "pa-c1-a01", "wid": W(1), "sch": "telemetry.v1", "origin_kind": "workload"}
    C = []

    def add(cat, label, inp, key="main", t=0, ev=None):
        C.append({"category": cat, "label": label, "store": key, "t": t, "expected_version": ev, "input": jround(inp)})

    add("baseline_permit", "signing device, own asset, own gateway", dev_ok, ev=1)
    add("baseline_permit", "legacy device signed by its gateway workload", leg_ok, ev=1)
    add("baseline_permit", "legacy device, origin_kind device (allowed for origin=gateway)", {**leg_ok, "origin_kind": "device"}, ev=1)
    # unknown device
    for v in ["pa-c9-d99", "PA-C1-D02", "pa-c1-d02 ", " pa-c1-d02", "pa-c1-d2", "pa-c1-a02", W(1)]:
        add("unknown_device", f"did={v!r}", {**dev_ok, "did": v}, ev=1)
        add("unknown_device", f"did={v!r}, origin_kind workload", {**dev_ok, "did": v, "origin_kind": "workload"}, ev=1)
    # unknown workload
    for v in [W(9), W(1) + "/", W(1).upper(), "spiffe://plant-b.example/cell1/gw1/collector",
              "spiffe://plant-a.example/cell1/gw1/collectorX", "pa-c1-d02"]:
        add("unknown_workload", f"wid={v!r} (signing device)", {**dev_ok, "wid": v}, ev=1)
        add("unknown_workload", f"wid={v!r} (legacy device)", {**leg_ok, "wid": v}, ev=1)
        add("unknown_workload", f"wid={v!r} + schema not allowed", {**dev_ok, "wid": v, "sch": "telemetry.v2"}, ev=1)
    # asset not assigned
    for v in ["pa-c1-a03", "pa-c2-a02", "pa-c9-a99", "pa-c1-d02", "PA-C1-A02"]:
        add("asset_not_assigned", f"aid={v!r} (signing device)", {**dev_ok, "aid": v}, ev=1)
        add("asset_not_assigned", f"aid={v!r} (legacy device)", {**leg_ok, "aid": v}, ev=1)
        add("asset_not_assigned", f"aid={v!r} + foreign gateway", {**dev_ok, "aid": v, "wid": W(2)}, ev=1)
    # schema not allowed
    for v in ["telemetry.v2", "TELEMETRY.V1", "telemetry.v1 ", "alarm.v1", "telemetry"]:
        add("schema_not_allowed", f"sch={v!r} (signing device)", {**dev_ok, "sch": v}, ev=1)
        add("schema_not_allowed", f"sch={v!r} (legacy device)", {**leg_ok, "sch": v}, ev=1)
        add("schema_not_allowed", f"sch={v!r} + foreign gateway", {**dev_ok, "sch": v, "wid": W(2)}, ev=1)
        add("schema_not_allowed", f"sch={v!r} + weak origin", {**dev_ok, "sch": v, "origin_kind": "workload"}, ev=1)
    # origin-kind mismatch (device vs gateway/legacy)
    for v in ["workload", "gateway", "legacy", "Device", "device "]:
        add("origin_kind_mismatch", f"origin=device device, origin_kind={v!r}", {**dev_ok, "origin_kind": v}, ev=1)
    for v in ["device", "workload", "gateway", "legacy", "Workload"]:
        add("origin_kind_mismatch", f"origin=gateway (legacy) device, origin_kind={v!r}", {**leg_ok, "origin_kind": v}, ev=1)
    # inactive device (v3) and inactive workload (v4), with the same inputs on v2 and v5 for contrast
    g_off = int(INACTIVE_DEV.split("-c")[1][0])
    for ver, t in [(2, T_MOVE), (3, T_DEV_OFF), (5, T_RECOVER)]:
        for ok in ["device", "workload"]:
            add("inactive_device", f"v{ver}: {INACTIVE_DEV} own path, origin_kind={ok}",
                {"did": INACTIVE_DEV, "aid": INACTIVE_DEV.replace("-d", "-a"), "wid": W(g_off), "sch": "telemetry.v1",
                 "origin_kind": ok}, t=t, ev=ver)
        add("inactive_device", f"v{ver}: {INACTIVE_DEV} + wrong asset", {"did": INACTIVE_DEV, "aid": "pa-c2-a04",
            "wid": W(g_off), "sch": "telemetry.v1", "origin_kind": "device"}, t=t, ev=ver)
        add("inactive_device", f"v{ver}: {INACTIVE_DEV} + foreign gateway", {"did": INACTIVE_DEV,
            "aid": INACTIVE_DEV.replace("-d", "-a"), "wid": W(1), "sch": "telemetry.v1", "origin_kind": "device"}, t=t, ev=ver)
    for ver, t in [(3, T_DEV_OFF), (4, T_WL_OFF), (5, T_RECOVER)]:
        for did, ok in [("pa-c4-d02", "device"), ("pa-c4-d01", "workload"), ("pa-c4-d01", "device")]:
            add("inactive_workload", f"v{ver}: {did} via cell4 workload, origin_kind={ok}",
                {"did": did, "aid": did.replace("-d", "-a"), "wid": INACTIVE_WL, "sch": "telemetry.v1", "origin_kind": ok},
                t=t, ev=ver)
        add("inactive_workload", f"v{ver}: pa-c1-d02 (not relayed by cell4) via cell4 workload",
            {**dev_ok, "wid": INACTIVE_WL}, t=t, ev=ver)
        add("inactive_workload", f"v{ver}: pa-c4-d02 via cell4 workload + bad schema",
            {"did": "pa-c4-d02", "aid": "pa-c4-a02", "wid": INACTIVE_WL, "sch": "x", "origin_kind": "device"}, t=t, ev=ver)
    # device moved to another cell (v1 -> v2)
    mv = py.moved_did
    for ver, t in [(1, 0), (2, T_MOVE)]:
        for wid in [py.move_from, py.move_to, W(1)]:
            for ok in ["device", "workload", "gateway"]:
                add("device_moved", f"v{ver}: {mv} via {wid.split('/')[3]}, origin_kind={ok}",
                    {"did": mv, "aid": mv.replace("-d", "-a"), "wid": wid, "sch": "telemetry.v1", "origin_kind": ok},
                    t=t, ev=ver)
    # clock boundary of policy-version selection
    probes = [("moved device via old cell", {"did": mv, "aid": mv.replace("-d", "-a"), "wid": py.move_from,
                                             "sch": "telemetry.v1", "origin_kind": "device"}),
              ("moved device via new cell", {"did": mv, "aid": mv.replace("-d", "-a"), "wid": py.move_to,
                                             "sch": "telemetry.v1", "origin_kind": "device"}),
              ("deactivated device", {"did": INACTIVE_DEV, "aid": INACTIVE_DEV.replace("-d", "-a"), "wid": W(g_off),
                                      "sch": "telemetry.v1", "origin_kind": "device"}),
              ("deactivated workload", {"did": "pa-c4-d02", "aid": "pa-c4-a02", "wid": INACTIVE_WL,
                                        "sch": "telemetry.v1", "origin_kind": "device"})]
    times = [-1, 0, 1] + [x for tk in (T_MOVE, T_DEV_OFF, T_WL_OFF, T_RECOVER) for x in (tk - 1, tk, tk + 1)] + [10 ** 12]
    for t in times:
        for lab, inp in probes:
            add("version_selection_clock_boundary", f"t={t}: {lab}", inp, t=t, ev=py.expected_version(t))
    # missing fields (absent key -> Python None)
    for base_lab, base in [("signing device", dev_ok), ("legacy device", leg_ok)]:
        for f in FIELDS:
            add("missing_fields", f"{base_lab}: '{f}' absent", {k: v for k, v in base.items() if k != f}, ev=1)
        add("missing_fields", f"{base_lab}: only 'did'", {"did": base["did"]}, ev=1)
    add("missing_fields", "empty input object {}", {}, ev=1)
    # wrong types / malformed values (JSON-representable)
    bad_values = [("int", 123), ("float", 1.5), ("true", True), ("false", False), ("null", None),
                  ("list[valid]", "__LIST__"), ("object{valid}", "__OBJ__"), ("empty list", []), ("empty object", {})]
    for base_lab, base in [("signing device", dev_ok), ("legacy device", leg_ok)]:
        for f in FIELDS:
            for tlab, bv in bad_values:
                val = [base[f]] if bv == "__LIST__" else ({"v": base[f]} if bv == "__OBJ__" else bv)
                add("wrong_types", f"{base_lab}: {f} = {tlab}", {**base, f: val}, ev=1)
    # empty strings
    for base_lab, base in [("signing device", dev_ok), ("legacy device", leg_ok)]:
        for f in FIELDS:
            add("empty_strings", f"{base_lab}: {f} = ''", {**base, f: ""}, ev=1)
        add("empty_strings", f"{base_lab}: all fields ''", {k: "" for k in FIELDS}, ev=1)
    return C


def malformed_documents(s01: dict) -> list:
    """(label, doc, [(case label, input)]) -- the policy document itself is patched; most patches violate the schema
    that both sides validate (Python: PolicyStore refuses the document; Rego: POLICY_DOCUMENT_INVALID), a few remain
    valid through schema defaults and are evaluated normally by both."""
    W1 = "spiffe://plant-a.example/cell1/gw1/collector"
    dev_ok = {"did": "pa-c1-d02", "aid": "pa-c1-a02", "wid": W1, "sch": "telemetry.v1", "origin_kind": "device"}
    leg_ok = {"did": "pa-c1-d01", "aid": "pa-c1-a01", "wid": W1, "sch": "telemetry.v1", "origin_kind": "workload"}
    out = []

    def mut(label, f, cases):
        d = copy.deepcopy(s01)
        f(d)
        out.append((label, d, cases))

    std = [("valid request", dev_ok)]
    for val in [None, 0, "", [], {}, "false", "no", 1]:
        mut(f"device.active = {json.dumps(val)}", lambda d, v=val: d["devices"]["pa-c1-d02"].__setitem__("active", v), std)
    for val in [None, 0, ""]:
        mut(f"workload.active = {json.dumps(val)}", lambda d, v=val: d["workloads"][W1].__setitem__("active", v), std)
    mut("device.assets is a string 'pa-c1-a02'", lambda d: d["devices"]["pa-c1-d02"].__setitem__("assets", "pa-c1-a02"),
        [("aid equal to the string", dev_ok), ("aid = substring 'a02'", {**dev_ok, "aid": "a02"}),
         ("aid = substring 'pa-c1'", {**dev_ok, "aid": "pa-c1"})])
    mut("device.schemas is a string 'telemetry.v1'", lambda d: d["devices"]["pa-c1-d02"].__setitem__("schemas", "telemetry.v1"),
        [("sch equal to the string", dev_ok), ("sch = substring 'telemetry'", {**dev_ok, "sch": "telemetry"}),
         ("sch = substring 'v1'", {**dev_ok, "sch": "v1"})])
    mut("workload.relay is a string 'pa-c1-d02 pa-c1-d03'", lambda d: d["workloads"][W1].__setitem__("relay", "pa-c1-d02 pa-c1-d03"),
        [("did contained in the string", dev_ok), ("did = substring 'pa-c1-d0'", {**dev_ok, "did": "pa-c1-d0"})])
    mut("device without 'assets' key", lambda d: d["devices"]["pa-c1-d02"].pop("assets"), std)
    mut("device without 'schemas' key", lambda d: d["devices"]["pa-c1-d02"].pop("schemas"), std)
    mut("device without 'origin' key (default 'device')", lambda d: d["devices"]["pa-c1-d02"].pop("origin"),
        [("origin_kind device", dev_ok), ("origin_kind workload", {**dev_ok, "origin_kind": "workload"})])
    mut("device without 'active' key (default true)", lambda d: d["devices"]["pa-c1-d02"].pop("active"), std)
    mut("workload without 'relay' key", lambda d: d["workloads"][W1].pop("relay"), std)
    for val in ["legacy", "Gateway", "none", ""]:
        mut(f"device.origin = {val!r} (not in {{device, gateway}})",
            lambda d, v=val: d["devices"]["pa-c1-d02"].__setitem__("origin", v),
            [("origin_kind device", dev_ok), ("origin_kind workload", {**dev_ok, "origin_kind": "workload"}),
             ("origin_kind 'garbage'", {**dev_ok, "origin_kind": "garbage"})])
    for lab, val in [("a string", "garbage"), ("null", None), ("a list", ["pa-c1-a02"])]:
        mut(f"device entry is {lab}", lambda d, v=val: d["devices"].__setitem__("pa-c1-d02", v), std)
        mut(f"workload entry is {lab}", lambda d, v=val: d["workloads"].__setitem__(W1, v), std + [("legacy", leg_ok)])
    mut("legacy device entry has origin 'gateway' but no schemas", lambda d: d["devices"]["pa-c1-d01"].pop("schemas"),
        [("legacy", leg_ok)])
    return out


# ===================================================================================== main
def main():
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=str(Path(__file__).resolve().parents[2]))  # V3: this repository
    ap.add_argument("--backend", choices=["regopy", "opa"], default="regopy")
    ap.add_argument("--opa-bin", default=None)
    ap.add_argument("--opa-per-case", action="store_true")
    ap.add_argument("--opa-dry-run", default=None, metavar="DIR")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parents[2] / "results" / "policy_parity" / "parity_results.json"))
    ap.add_argument("--max-grid", type=int, default=0, help="debug: limit grid cases per version (0 = all)")
    a = ap.parse_args()
    repo = Path(a.repo).resolve()
    rego_path = repo / "policies" / "admission.rego"
    t_start = time.time()

    py = PySide(repo)
    if a.backend == "regopy":
        rg = RegopyBackend(rego_path.read_text())
    else:
        rg = OpaBackend(rego_path, a.opa_bin, per_case=a.opa_per_case, dry_run_dir=a.opa_dry_run)

    versions = [v.version for v in py.store.versions]
    for v in versions:
        rg.load(("main", v), py.version_doc(v))

    records = []         # every evaluated case (grid cases are summarised, not stored, unless mismatching)
    stats = collections.defaultdict(collections.Counter)
    confusion = collections.Counter()
    mismatches = []
    boundary_records = []
    grid_decisions = {}  # (version, input-tuple) -> (py allow, py reason, rego allow, rego reason)
    grid_domains = {}
    input_mode_check = collections.Counter()

    def account(cat, rec, primary=True):
        """primary=False: aggregate-only accounting (no mismatch entry, no confusion count)."""
        s = stats[cat]
        s["n"] += 1
        py_r, rg_r = rec["python"], rec["rego"]
        kind = classify(py_r, rg_r)
        if rec.get("expected_version") is not None and "error" not in py_r and py_r["version"] != rec["expected_version"]:
            s["version_selection_error"] += 1
            if primary:
                mismatches.append({**rec, "kind": "VERSION_SELECTION"})
        if kind is None:
            s["exact_match"] += 1
        else:
            s[kind.lower()] += 1
            if primary:
                mismatches.append({**rec, "kind": kind})
                if kind == "REASON_MISMATCH":
                    confusion[(py_r["reason"], rg_r["reason"])] += 1
        if "error" not in py_r and "error" not in rg_r and py_r["allow"] == rg_r["allow"]:
            s["allow_match"] += 1
        fc_py = False if "error" in py_r else py_r["allow"]
        fc_rg = False if "error" in rg_r else rg_r["allow"]
        if fc_py == fc_rg:
            s["fail_closed_allow_match"] += 1
        else:
            s["fail_closed_allow_mismatch"] += 1
        if (fc_py or fc_rg) and not (fc_py and fc_rg):
            s["permit_by_one_side_only"] += 1
        unc = py_r.get("uncached", {})
        if "error" not in py_r and "error" not in unc and (unc["allow"], unc["reason"]) != (py_r["allow"], py_r["reason"]):
            s["python_cache_divergence"] += 1
        if "error" in py_r and "error" not in unc:
            s["python_error_only_in_memo_cache"] += 1

    # ---- grid on every version
    for v in versions:
        cases, dom = grid_cases(py.version_doc(v))
        if a.max_grid:
            cases = cases[:a.max_grid]
        grid_domains[v] = {k: len(x) for k, x in dom.items()} | {"n": len(cases), "origin_kind_values": dom["origin_kind"]}
        t = py.store.get(v).t_ms
        rres = rg.evaluate_many(("main", v), [jround(c) for c in cases])
        for c, rr in zip(cases, rres):
            pr = py.evaluate("main", c, t)
            rec = {"category": f"grid_v{v}", "label": "grid", "store": "main", "t": t, "expected_version": v,
                   "input": c, "python": pr, "rego": rr}
            account(f"grid_v{v}", rec)
            account("grid_all_versions", rec, primary=False)
            grid_decisions[(v, tuple(c[k] for k in FIELDS))] = (pr.get("allow"), pr.get("reason"), rr.get("allow"), rr.get("reason"))

    # ---- boundary cases
    bcases = boundary_cases(py)
    by_key = collections.defaultdict(list)
    for c in bcases:
        ver = c["expected_version"] if c["expected_version"] is not None else py.expected_version(c["t"])
        c["rego_version"] = ver
        by_key[("main", ver)].append(c)
    for key, cs in by_key.items():
        rres = rg.evaluate_many(key, [c["input"] for c in cs])
        for c, rr in zip(cs, rres):
            pr = py.evaluate("main", c["input"], c["t"])
            rec = {**c, "python": pr, "rego": rr}
            if isinstance(rg, RegopyBackend):  # cross-check: Python-value input conversion gives the same answer
                alt = rg.evaluate_one(key, c["input"], as_python_value=True)
                rec["rego_input_mode_consistent"] = (alt == rr)
                input_mode_check[alt == rr] += 1
            account(c["category"], rec)
            account("boundary_all", rec, primary=False)
            boundary_records.append(rec)

    # ---- malformed policy documents (separate single-version stores)
    mal = malformed_documents(py.s01_doc)
    for i, (label, doc, cases) in enumerate(mal):
        key = f"malformed:{i}"
        py.add_store(key, doc)
        rg.load(key, doc)
        rres = rg.evaluate_many(key, [jround(inp) for _, inp in cases])
        for (clab, inp), rr in zip(cases, rres):
            pr = py.evaluate(key, jround(inp), 0)
            rec = {"category": "malformed_policy_document", "label": f"{label} | {clab}", "store": key, "t": 0,
                   "expected_version": None, "input": jround(inp), "python": pr, "rego": rr,
                   "doc_patch": label}
            account("malformed_policy_document", rec)
            boundary_records.append(rec)

    # ---- cross-version consistency properties (number of grid inputs whose decision differs between versions)
    def same_decisions(v_a, v_b, side):
        sl = slice(0, 2) if side == "python" else slice(2, 4)
        diff = 0
        for (v, key), d in grid_decisions.items():
            if v != v_a:
                continue
            o = grid_decisions.get((v_b, key))
            if o is not None and d[sl] != o[sl]:
                diff += 1
        return diff
    props = {"v5_vs_v2_decision_differences": {"python": same_decisions(5, 2, "python"), "rego": same_decisions(5, 2, "rego")},
             "v2_vs_v1_decision_differences": {"python": same_decisions(2, 1, "python"), "rego": same_decisions(2, 1, "rego")},
             "v3_vs_v2_decision_differences": {"python": same_decisions(3, 2, "python"), "rego": same_decisions(3, 2, "rego")},
             "v4_vs_v3_decision_differences": {"python": same_decisions(4, 3, "python"), "rego": same_decisions(4, 3, "rego")}}

    # ---- example document equivalence
    ex = json.loads((repo / "policies" / "admission_policy.example.json").read_text())
    s01 = py.s01_doc
    meta = {
        "harness": HARNESS_VERSION, "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "wall_s": None, "python": sys.version.split()[0], "platform": platform.platform(),
        "repo": str(repo), "rego_backend": rg.name, "rego_backend_info": rg.info,
        "sha256": {p: sha256_file(repo / p) for p in ["policies/admission.rego", "src/pbti/policy.py",
                                                       "src/pbti/scenarios.py", "src/pbti/sim.py",
                                                       "policies/admission_policy.example.json"]},
        "world": "pbti.scenarios.build('S01_normal', 'PBTI', 1).policy_doc",
        "s01_doc_equals_example_json": {"devices": s01["devices"] == ex["devices"], "workloads": s01["workloads"] == ex["workloads"]},
        "policy_versions": [{"version": v.version, "t_ms": v.t_ms, "digest": v.digest, "note": py.version_notes[v.version]}
                            for v in py.store.versions],
        "python_call": "PDP(store).evaluate(did, aid, wid, sch, origin_kind, t_ms)  [check_origin=True]",
        "rego_eval": "data.pbti.admission.{allow, reason}; data.pbti = PolicyVersion.doc; input = case object",
        "input_convention": "absent JSON field -> Python None; Rego undefined",
        "grid_domains": grid_domains,
        "regopy_input_mode_crosscheck": {"consistent": input_mode_check[True], "inconsistent": input_mode_check[False],
                                         "note": "boundary cases re-evaluated with set_input(python value) instead of "
                                                 "set_input_term(JSON text)"},
        "n_cases_total": stats["grid_all_versions"]["n"] + stats["boundary_all"]["n"] + stats["malformed_policy_document"]["n"],
    }
    meta["harness_sha256"] = sha256_file(Path(__file__).resolve())

    def agg(cats):
        t = collections.Counter()
        for c in cats:
            t.update(stats[c])
        return {"n": t["n"], "allow_match": t["allow_match"], "exact_match": t["exact_match"],
                "reason_mismatch": t["reason_mismatch"], "allow_mismatch": t["allow_mismatch"],
                "python_error": t["py_error"], "rego_error": t["rego_error"],
                "permit_by_one_side_only": t["permit_by_one_side_only"]}
    well_formed = [f"grid_v{v}" for v in versions] + ["baseline_permit", "unknown_device", "unknown_workload",
                                                      "asset_not_assigned", "schema_not_allowed", "origin_kind_mismatch",
                                                      "inactive_device", "inactive_workload", "device_moved",
                                                      "version_selection_clock_boundary"]
    headline = {"well_formed_requests_on_well_formed_policy": agg(well_formed),
                "malformed_requests (missing_fields, wrong_types, empty_strings)": agg(["missing_fields", "wrong_types", "empty_strings"]),
                "malformed_policy_document": agg(["malformed_policy_document"]),
                "all_cases": agg(well_formed + ["missing_fields", "wrong_types", "empty_strings", "malformed_policy_document"])}
    out = {
        "meta": meta,
        "headline": headline,
        "summary": {cat: dict(sorted(c.items())) for cat, c in sorted(stats.items())},
        "reason_confusion_py_to_rego": [{"python": k[0], "rego": k[1], "count": n} for k, n in confusion.most_common()],
        "cross_version_properties": props,
        "scope": SCOPE,
        "mismatches": mismatches,
        "boundary_cases": boundary_records,
    }
    if isinstance(rg, OpaBackend):
        out["meta"]["opa_commands"] = rg.commands[:50]
    meta["wall_s"] = round(time.time() - t_start, 1)
    Path(a.out).write_text(json.dumps(out, indent=1, default=str))
    # console summary
    print(f"backend={rg.name} wall={meta['wall_s']}s versions={len(versions)} -> {a.out}")
    for cat in ["grid_all_versions"] + [f"grid_v{v}" for v in versions] + ["boundary_all"] + sorted(
            c for c in stats if not c.startswith("grid") and c != "boundary_all"):
        s = stats[cat]
        print(f"  {cat:34s} n={s['n']:6d} exact={s['exact_match']:6d} allow_match={s['allow_match']:6d} "
              f"reason_mm={s['reason_mismatch']:4d} allow_mm={s['allow_mismatch']:3d} py_err={s['py_error']:3d} "
              f"rego_err={s['rego_error']:3d} both_err={s['both_error']:3d} permit_one_side={s['permit_by_one_side_only']:3d} "
              f"ver_sel_err={s['version_selection_error']}")
    print("  reason confusion:", dict(confusion))
    print("  properties:", props)
    for k, v in headline.items():
        print(f"  HEADLINE {k}: {v}")


if __name__ == "__main__":
    main()
