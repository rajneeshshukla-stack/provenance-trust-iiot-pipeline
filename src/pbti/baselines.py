"""Baseline ingestion pipelines. All baselines share storage, the downstream processor and the
policy document with PBTI, so measured differences are attributable to admission semantics.

B1  Conventional authenticated pipeline (common practice approximation)
    * transport-session authentication of gateways (TLS client certificate); credential status is
      checked when a session is (re)established, not per message;
    * coarse publish authorization: any registered gateway may publish plant telemetry;
    * idempotent consumer: message-id de-duplication within a TTL window;
    * bronze (append-only landing) + silver (upsert by business key (did, ts), last arrival wins).
B2  Zero-Trust access-controlled pipeline (NIST SP 800-207 style PEP/PDP at the ingestion boundary)
    * per-message continuous verification of the session's workload credential (short-lived SVID);
    * per-message path-bound authorization with the SAME policy document as PBTI
      (device -> asset -> schema, workload -> relay scope) on the claimed message metadata;
    * freshness checks; message-id TTL de-duplication; bronze + silver as B1.
    * no message-level signatures: identity terminates at the session (broker) boundary.
B3  Provenance-focused pipeline (approximation of signature/hash-chain IoT provenance schemes)
    * origin signature on every record (device key; gateway key for legacy devices);
    * key status (revocation, validity window) checked at verification time, no rotation grace;
    * content-hash uniqueness and an append-only hash-chained provenance ledger with signed heads;
    * no path binding, no deterministic producer event identity, no delivery-history semantics,
      no retroactive taint; silver as B1.
B3 is NOT a re-implementation of any specific published system; deviations are listed in
docs/BASELINES.md.
B4  Strongest reasonable combination of existing techniques (added in revision 2 to test whether existing
    practice already reproduces PBTI's outcomes); it uses the PBTI observation statement on the wire but
    none of the PBTI-specific mechanisms:
    * per-message continuous verification of the session workload credential and per-message path-bound
      authorization with the SAME policy as PBTI, including the origin requirement (as B2);
    * origin signature on every observation (device key; gateway key for legacy devices, whose subject
      must equal the session workload) with the SAME rotation grace as PBTI (B3 has none);
    * freshness checks (skew, horizon) as B2 (reject, no quarantine);
    * idempotent admission keyed by the producer-assigned event identity (did, ep, seq), as in Kafka's
      idempotent producer: exact duplicates are suppressed, a different content for an admitted identity
      is rejected and logged (first writer wins);
    * hash-chained ledger with signed heads over admitted records (as B3); current value ordered by
      (ep, seq) as in PBTI.
    Not included: relay statement through the broker, predecessor-link contest (Rule L), recoverable
    quarantine, decision-replay evidence log, retroactive taint.
"""
from __future__ import annotations

from typing import Optional

from .canonical import canonical_bytes
from .crypto import DOMAIN_B3, DOMAIN_B3LEDGER, b64u, sha256, sha256_hex, sign, verify
from .crypto import DOMAIN_OBS
from .envelope import B1_KEYS, B2_KEYS, MalformedMessage, b3_parse, content_key, pbti_parse, plain_parse
from .identity import TrustRegistry, TrustView
from .policy import PDP, PolicyStore
from .processor import Processor
from .store import MemoryStore
from .verifier import ACCEPT, DUPLICATE, QUARANTINE, REJECT, Receipt, VerifierConfig


class _SilverMixin:
    """bronze append + silver upsert by business key (did, ts), last-arrival-wins."""

    def _land(self, t: int, m: dict, wire: bytes, ref: str, extra: dict | None = None) -> Receipt:
        try:   # V3: a payload number outside the I-JSON range cannot be canonicalised -> REJECT (no crash)
            ck = content_key(m["did"], m["aid"], m["ts"], m["sch"], m["pl"])
        except (ValueError, TypeError):
            return Receipt(REJECT, "MALFORMED:non-canonical-number")
        self.store.append("bronze", {"t": t, "ref": ref}, len(wire) + 16)
        bk = (m["did"], m["ts"])
        old = self.silver.get(bk)
        self.silver[bk] = (ck, m, ref)
        self.store.put("silver", bk, ref, 48)
        if old is not None:
            if old[0] == ck:
                return Receipt(ACCEPT, "UPSERT_SAME")
            self.proc.remove(bk, "REPLACE_CORRECTION")
            self.replacements += 1
        self.proc.add(bk, m["aid"], m["ts"], m["pl"], ref, ck, m["ts"])
        return Receipt(ACCEPT, "UPSERT_REPLACE" if old is not None else "INSERT")

    def authoritative(self):
        for bk, (ck, m, ref) in self.silver.items():
            yield bk, ck

    def _count(self, r: Receipt) -> Receipt:
        k = r.disp + "/" + r.why.split(":")[0]
        self.counts[k] = self.counts.get(k, 0) + 1
        return r

    def advance(self, t: int) -> None:
        while self.next_tick <= t:
            if self.next_tick % self.cfg.emit_ms == 0:
                self.proc.emit(self.next_tick)
            self._tick(self.next_tick)
            self.next_tick += self.cfg.tick_ms

    def _tick(self, t: int) -> None:
        pass

    def finalize(self, t: int) -> None:
        self.advance(t)
        self.proc.emit(t)
        self.store.flush()


class B1Conventional(_SilverMixin):
    name = "B1"

    def __init__(self, trust: TrustRegistry, policy: PolicyStore, store: Optional[MemoryStore] = None,
                 cfg: Optional[VerifierConfig] = None, dedup_ttl_ms: int = 300_000):
        self.cfg = cfg or VerifierConfig()
        self.trust = TrustView(trust, self.cfg.status_refresh_ms)
        self.policy = policy
        self.store = store or MemoryStore()
        self.proc = Processor(self.cfg.window_ms, order="ts")
        self.silver: dict = {}
        self.seen: dict[str, int] = {}
        self.ttl = dedup_ttl_ms
        self.sessions: dict[str, bool] = {}
        self.next_tick = 0
        self.counts: dict[str, int] = {}
        self.replacements = 0
        self.n_receipts = 0

    def _session_ok(self, t: int, meta: dict) -> bool:
        tid, tkid = meta.get("tid"), meta.get("tkid")
        if meta.get("new_session") or tid not in self.sessions:
            info = self.trust.key(tkid) if tkid else None
            ok = (info is not None and info.subject == tid and info.nbf_ms <= t <= info.exp_ms
                  and self.trust.status(tkid, t) is None)
            self.sessions[tid] = ok
        return self.sessions[tid]

    def _tick(self, t: int) -> None:
        if t % 10_000 == 0:  # bounded de-dup memory
            lim = t - self.ttl
            self.seen = {k: v for k, v in self.seen.items() if v >= lim}

    def ingest(self, wire: bytes, t: int, meta: Optional[dict] = None) -> Receipt:
        self.advance(t)
        self.n_receipts += 1
        meta = meta or {}
        if not self._session_ok(t, meta):
            return self._count(Receipt(REJECT, "SESSION_UNAUTHENTICATED"))
        try:
            m = plain_parse(wire, B1_KEYS)
        except MalformedMessage as e:
            return self._count(Receipt(REJECT, "MALFORMED:" + str(e)))
        if m["mid"] in self.seen:
            return self._count(Receipt(DUPLICATE, "MID_SEEN"))
        self.seen[m["mid"]] = t
        ref = sha256_hex(wire)
        self.store.put_blob("bronze", ref, wire)
        return self._count(self._land(t, m, wire, ref))


class B2ZeroTrust(_SilverMixin):
    name = "B2"

    def __init__(self, trust: TrustRegistry, policy: PolicyStore, store: Optional[MemoryStore] = None,
                 cfg: Optional[VerifierConfig] = None, dedup_ttl_ms: int = 300_000):
        self.cfg = cfg or VerifierConfig()
        self.trust = TrustView(trust, self.cfg.status_refresh_ms)
        self.pdp = PDP(policy)
        self.store = store or MemoryStore()
        self.proc = Processor(self.cfg.window_ms, order="ts")
        self.silver: dict = {}
        self.seen: dict[str, int] = {}
        self.ttl = dedup_ttl_ms
        self.next_tick = 0
        self.counts: dict[str, int] = {}
        self.replacements = 0
        self.n_receipts = 0

    def _tick(self, t: int) -> None:
        if t % 10_000 == 0:
            lim = t - self.ttl
            self.seen = {k: v for k, v in self.seen.items() if v >= lim}

    def ingest(self, wire: bytes, t: int, meta: Optional[dict] = None) -> Receipt:
        self.advance(t)
        self.n_receipts += 1
        meta = meta or {}
        tid, tkid = meta.get("tid"), meta.get("tkid")
        info = self.trust.key(tkid) if tkid else None
        # continuous verification of the session credential on every request
        if info is None or info.kind != "workload" or info.subject != tid:
            return self._count(Receipt(REJECT, "SESSION_UNAUTHENTICATED"))
        if self.trust.status(tkid, t) is not None:
            return self._count(Receipt(REJECT, "REVOKED:workload"))
        if not (info.nbf_ms <= t <= info.exp_ms):
            return self._count(Receipt(REJECT, "SESSION_CREDENTIAL_EXPIRED"))
        try:
            m = plain_parse(wire, B2_KEYS)
        except MalformedMessage as e:
            return self._count(Receipt(REJECT, "MALFORMED:" + str(e)))
        if m["wid"] != tid:
            return self._count(Receipt(REJECT, "WORKLOAD_CLAIM_MISMATCH"))
        permit, why, pv = self.pdp.evaluate(m["did"], m["aid"], tid, m["sch"], "workload", t, check_origin=False)
        if not permit:
            return self._count(Receipt(REJECT, "UNAUTHORIZED:" + why))
        params = self.pdp.params(t)
        if m["ts"] > t + params["skew_max_ms"] or t - m["ts"] > params["h_max_ms"]:
            return self._count(Receipt(REJECT, "STALE_OR_FUTURE"))
        if m["mid"] in self.seen:
            return self._count(Receipt(DUPLICATE, "MID_SEEN"))
        self.seen[m["mid"]] = t
        ref = sha256_hex(wire)
        self.store.put_blob("bronze", ref, wire)
        return self._count(self._land(t, m, wire, ref))


class B3Provenance(_SilverMixin):
    name = "B3"

    def __init__(self, trust: TrustRegistry, policy: PolicyStore, vkeys, store: Optional[MemoryStore] = None,
                 cfg: Optional[VerifierConfig] = None, head_every: int = 512):
        self.cfg = cfg or VerifierConfig()
        self.trust = TrustView(trust, self.cfg.status_refresh_ms)
        self.store = store or MemoryStore()
        self.proc = Processor(self.cfg.window_ms, order="ts")
        self.silver: dict = {}
        self.sessions: dict[str, bool] = {}
        self.ledger: list[dict] = []
        self.ledger_index: set[str] = set()
        self.heads: list[dict] = []
        self.vsk, self.vpk = vkeys
        self.head_every = head_every
        self.next_tick = 0
        self.counts: dict[str, int] = {}
        self.replacements = 0
        self.n_receipts = 0

    _session_ok = B1Conventional._session_ok

    def _sign_head(self, t: int) -> None:
        if not self.ledger or (self.heads and self.heads[-1]["size"] == len(self.ledger)):
            return
        body = {"size": len(self.ledger), "head": self.ledger[-1]["h"], "t": t}
        self.heads.append(dict(body, sig=b64u(sign(self.vsk, DOMAIN_B3LEDGER, canonical_bytes(body)))))

    def _tick(self, t: int) -> None:
        if t % 5_000 == 0:
            self._sign_head(t)

    def finalize(self, t: int) -> None:
        super().finalize(t)
        self._sign_head(t)

    def ingest(self, wire: bytes, t: int, meta: Optional[dict] = None) -> Receipt:
        self.advance(t)
        self.n_receipts += 1
        meta = meta or {}
        if not self._session_ok(t, meta):
            return self._count(Receipt(REJECT, "SESSION_UNAUTHENTICATED"))
        try:
            rec, sig = b3_parse(wire)
        except MalformedMessage as e:
            return self._count(Receipt(REJECT, "MALFORMED:" + str(e)))
        info = self.trust.key(rec["kid"])
        if info is None:
            return self._count(Receipt(REJECT, "UNKNOWN_KEY"))
        if info.kind == "device" and info.subject != rec["did"]:
            return self._count(Receipt(REJECT, "KEY_SUBJECT_MISMATCH"))
        try:
            cb = canonical_bytes(rec)
        except (ValueError, TypeError):
            return self._count(Receipt(REJECT, "MALFORMED:non-canonical-number"))
        if not verify(info.pk, DOMAIN_B3, cb, sig):
            return self._count(Receipt(REJECT, "INTEGRITY"))
        if self.trust.status(rec["kid"], t) is not None:
            return self._count(Receipt(REJECT, "REVOKED"))
        if not (info.nbf_ms <= t <= info.exp_ms):
            return self._count(Receipt(REJECT, "KEY_EXPIRED"))
        h = b64u(sha256(cb))
        if h in self.ledger_index:
            return self._count(Receipt(DUPLICATE, "CONTENT_HASH_SEEN"))
        prev = self.ledger[-1]["h"] if self.ledger else None
        ref = sha256_hex(wire)
        entry = {"i": len(self.ledger), "rec": h, "ref": ref, "t": t, "prev": prev}
        entry["h"] = b64u(sha256(canonical_bytes({k: entry[k] for k in ("i", "rec", "ref", "t", "prev")})))
        self.ledger.append(entry)
        self.ledger_index.add(h)
        self.store.put_blob("ledger", ref, wire)
        self.store.append("ledger", entry, 160)
        if len(self.ledger) % self.head_every == 0:
            self._sign_head(t)
        return self._count(self._land(t, rec, wire, ref))


class B4Combined(_SilverMixin):
    name = "B4"

    def __init__(self, trust: TrustRegistry, policy: PolicyStore, vkeys, store: Optional[MemoryStore] = None,
                 cfg: Optional[VerifierConfig] = None, head_every: int = 512):
        self.cfg = cfg or VerifierConfig()
        self.trust = TrustView(trust, self.cfg.status_refresh_ms)
        self.pdp = PDP(policy)
        self.store = store or MemoryStore()
        self.proc = Processor(self.cfg.window_ms, order="seq")
        self.silver: dict = {}          # (did, ep, seq) -> (content key, observation, ref)
        self.digest: dict = {}          # (did, ep, seq) -> content digest of the admitted version
        self.ledger: list[dict] = []
        self.heads: list[dict] = []
        self.vsk, self.vpk = vkeys
        self.head_every = head_every
        self.next_tick = 0
        self.counts: dict[str, int] = {}
        self.replacements = 0
        self.conflicts_logged = 0
        self.n_receipts = 0

    _sign_head = B3Provenance._sign_head
    _tick = B3Provenance._tick

    def finalize(self, t: int) -> None:
        super().finalize(t)
        self._sign_head(t)

    def ingest(self, wire: bytes, t: int, meta: Optional[dict] = None) -> Receipt:
        self.advance(t)
        self.n_receipts += 1
        meta = meta or {}
        tid, tkid = meta.get("tid"), meta.get("tkid")
        sess = self.trust.key(tkid) if tkid else None
        # continuous verification of the session credential on every request (as B2)
        if sess is None or sess.kind != "workload" or sess.subject != tid:
            return self._count(Receipt(REJECT, "SESSION_UNAUTHENTICATED"))
        if self.trust.status(tkid, t) is not None:
            return self._count(Receipt(REJECT, "REVOKED:workload"))
        if not (sess.nbf_ms <= t <= sess.exp_ms):
            return self._count(Receipt(REJECT, "SESSION_CREDENTIAL_EXPIRED"))
        try:
            obs, osig, _rel, _rsig = pbti_parse(wire)   # relay statement present on the wire but not used
        except MalformedMessage as e:
            return self._count(Receipt(REJECT, "MALFORMED:" + str(e)))
        did = obs["did"]
        kd = self.trust.key(obs["kid"])
        if kd is None:
            return self._count(Receipt(REJECT, "UNKNOWN_KEY"))
        if kd.kind == "device":
            if kd.subject != did:
                return self._count(Receipt(REJECT, "KEY_SUBJECT_MISMATCH"))
            origin = "device"
        elif kd.kind == "workload":
            if kd.subject != tid:   # gateway-attested data must come from the attesting gateway's session
                return self._count(Receipt(REJECT, "KEY_SUBJECT_MISMATCH"))
            origin = "workload"
        else:
            return self._count(Receipt(REJECT, "KEY_KIND_INVALID"))
        try:
            cb = canonical_bytes(obs)
        except (ValueError, TypeError):
            return self._count(Receipt(REJECT, "MALFORMED:non-canonical-number"))
        if not verify(kd.pk, DOMAIN_OBS, cb, osig):
            return self._count(Receipt(REJECT, "INTEGRITY"))
        params = self.pdp.params(t)
        if self.trust.status(obs["kid"], t) is not None:
            return self._count(Receipt(REJECT, "REVOKED:" + kd.kind))
        if t < kd.nbf_ms:
            return self._count(Receipt(REJECT, "KEY_NOT_YET_VALID"))
        if t > kd.exp_ms and t - kd.exp_ms > params["rotation_grace_ms"]:
            return self._count(Receipt(REJECT, "KEY_EXPIRED"))
        permit, why, pv = self.pdp.evaluate(did, obs["aid"], tid, obs["sch"], origin, t)
        if not permit:
            return self._count(Receipt(REJECT, "UNAUTHORIZED:" + why))
        if obs["ts"] > t + params["skew_max_ms"] or t - obs["ts"] > params["h_max_ms"]:
            return self._count(Receipt(REJECT, "STALE_OR_FUTURE"))
        eid = (did, obs["ep"], obs["seq"])
        cd = b64u(sha256(cb))
        if eid in self.digest:
            if self.digest[eid] == cd:
                return self._count(Receipt(DUPLICATE, "SEQ_SEEN"))
            self.conflicts_logged += 1
            return self._count(Receipt(REJECT, "CONFLICTING_VERSION"))   # first writer wins
        self.digest[eid] = cd
        prev = self.ledger[-1]["h"] if self.ledger else None
        ref = sha256_hex(wire)
        entry = {"i": len(self.ledger), "rec": cd, "ref": ref, "t": t, "prev": prev}
        entry["h"] = b64u(sha256(canonical_bytes({k: entry[k] for k in ("i", "rec", "ref", "t", "prev")})))
        self.ledger.append(entry)
        self.store.put_blob("ledger", ref, wire)
        self.store.append("ledger", entry, 160)
        if len(self.ledger) % self.head_every == 0:
            self._sign_head(t)
        ck = content_key(did, obs["aid"], obs["ts"], obs["sch"], obs["pl"])
        self.silver[eid] = (ck, obs, ref)
        self.store.put("silver", eid, ref, 48)
        self.store.append("bronze", {"t": t, "ref": ref}, len(wire) + 16)
        self.proc.add(eid, obs["aid"], obs["ts"], obs["pl"], ref, ck, (obs["ep"], obs["seq"]))
        return self._count(Receipt(ACCEPT, "INSERT"))
