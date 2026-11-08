"""Downstream stream processing shared by all pipelines: event-time tumbling-window aggregates,
a current-value table (last known state per asset) and raw-to-derived lineage.

Each emitted derived record version carries:
    inputs        sorted list of raw references (blob digests / ledger or bronze row ids)
    inputs_root   Merkle root over the input references (compact lineage commitment)
    cause         NEW | LATE_CORRECTION | CONTEST_CORRECTION | TAINT_CORRECTION | REPLACE_CORRECTION
Removing an input (contested, tainted, or replaced by last-write-wins in the baselines) marks
the window dirty, and the next emission produces a correction version; earlier versions are kept
(append-only), so the history of every analytical value remains reconstructible.
"""
from __future__ import annotations

from typing import Any

from .crypto import b64u
from .evidence import leaf_hash, merkle_root

_PRIO = {"NEW": 0, "LATE_CORRECTION": 1, "REPLACE_CORRECTION": 2, "CONTEST_CORRECTION": 3, "TAINT_CORRECTION": 3}


class Processor:
    def __init__(self, window_ms: int = 10_000, order: str = "seq", lineage: bool = True):
        self.window_ms = window_ms
        self.order = order  # "seq" (PBTI), "ts" (baselines), "arrival" (ablation A8)
        self.lineage_enabled = lineage
        self.win: dict[tuple, dict[Any, tuple]] = {}
        self.where: dict[Any, tuple] = {}
        self.dirty: dict[tuple, str] = {}
        self.versions: dict[tuple, list[dict]] = {}
        self.cur: dict[str, dict[Any, tuple]] = {}
        self._arrival = 0
        self.n_versions = 0
        self.n_corrections = 0

    def _wkey(self, aid: str, ts: int) -> tuple:
        return (aid, ts - ts % self.window_ms)

    def add(self, obs_id: Any, aid: str, ts: int, pl: dict, ref: str, ckey: tuple, order_key: Any) -> None:
        wk = self._wkey(aid, ts)
        self.win.setdefault(wk, {})[obs_id] = (ckey, pl, ref)
        self.where[obs_id] = wk
        cause = "LATE_CORRECTION" if wk in self.versions else "NEW"
        if _PRIO[cause] >= _PRIO.get(self.dirty.get(wk, "NEW"), 0):
            self.dirty[wk] = cause
        self._arrival += 1
        ok = self._arrival if self.order == "arrival" else order_key
        self.cur.setdefault(aid, {})[obs_id] = (ok, ckey)

    def remove(self, obs_id: Any, cause: str) -> None:
        wk = self.where.pop(obs_id, None)
        if wk is None:
            return
        self.win[wk].pop(obs_id, None)
        if _PRIO[cause] >= _PRIO.get(self.dirty.get(wk, "NEW"), 0):
            self.dirty[wk] = cause
        self.cur.get(wk[0], {}).pop(obs_id, None)

    def emit(self, t: int) -> int:
        n = 0
        for wk, cause in self.dirty.items():
            members = self.win.get(wk, {})
            agg: dict[str, list] = {}
            for ckey, pl, ref in members.values():
                for m, v in pl.items():
                    if isinstance(v, (int, float)):
                        a = agg.setdefault(m, [0, 0.0, v, v])
                        a[0] += 1; a[1] += v; a[2] = min(a[2], v); a[3] = max(a[3], v)
            vers = self.versions.setdefault(wk, [])
            rec = {"aid": wk[0], "w": wk[1], "v": len(vers) + 1, "t": t, "n": len(members), "cause": cause,
                   "agg": {m: [round(a[1] / a[0], 6), a[2], a[3]] for m, a in agg.items()}}
            if self.lineage_enabled:
                refs = sorted(r for _, _, r in members.values())
                rec["inputs"] = refs
                rec["inputs_root"] = b64u(merkle_root([leaf_hash(r.encode()) for r in refs]))
            rec["ckeys"] = tuple(sorted(c for c, _, _ in members.values()))
            vers.append(rec)
            n += 1
            if cause != "NEW":
                self.n_corrections += 1
        self.n_versions += n
        self.dirty.clear()
        return n

    def current_value(self, aid: str):
        d = self.cur.get(aid)
        if not d:
            return None
        return max(d.values(), key=lambda x: x[0])[1]

    def final_windows(self) -> dict[tuple, dict]:
        return {wk: v[-1] for wk, v in self.versions.items()}
