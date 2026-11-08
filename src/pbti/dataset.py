"""V3 external-validity replay of public industrial telemetry (SKAB) through the PBTI simulator (docs/V3_DATASET_REPLAY.md).

Dataset: Skoltech Anomaly Benchmark (SKAB), Katser and Kozitsin, DOI 10.34740/KAGGLE/DSV/1693952, GPL-3.0, read from a local
clone of https://github.com/waico/SKAB (the files are not redistributed with this repository). Each SKAB file is one run of a
water-circulation test bed (pump, valves, tank) with eight sensor channels written about once per second.

Replay model
  * Each of the 24 devices of the standard topology replays one SKAB file (fixed assignment, FILES below). A device's
    observation carries the eight channel values of one row; `temp_c` is the motor-body temperature channel (the field the
    attack library manipulates), the other seven keep their SKAB meaning.
  * Native timing: the gap between two consecutive observations of a device is the gap between the two SKAB rows
    (1 s for 94.6 % of rows, 2 s for 5.3 %, rarely longer), divided by the speed-up factor (1, 5 or 10).
  * A window of ROWS rows is replayed per file, starting at row min(400, len - ROWS), so that it contains the onset of the
    file's labelled process anomaly. SKAB's own anomaly labels are kept outside the payload, in `world.row_label`, and are
    only used to check that admission does not depend on process anomalies.
  * Injected stressors are scheduled in dataset rows and converted to simulated time with the speed-up factor (STRESS);
    they are labelled by the simulator's ground truth exactly as in the synthetic scenarios.
"""
from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path

from .scenarios import EquivocationHook, ImpersonationHook, _rekey_gateway, _ts, forge_own, forge_own_legacy, \
    stolen_key_via_broker_rev
from .sim import NetConfig, World, WorldConfig

SOURCE = {"name": "Skoltech Anomaly Benchmark (SKAB) v0.9", "doi": "10.34740/KAGGLE/DSV/1693952",
          "url": "https://github.com/waico/SKAB", "license": "GPL-3.0",
          "citation": "I. D. Katser and V. O. Kozitsin, Skoltech Anomaly Benchmark (SKAB), Kaggle, 2020"}

COLUMNS = {  # SKAB column -> payload field (unit)
    "Accelerometer1RMS": "acc1_rms_g", "Accelerometer2RMS": "acc2_rms_g", "Current": "current_a",
    "Pressure": "press_bar", "Temperature": "temp_c", "Thermocouple": "fluid_temp_c", "Voltage": "voltage_v",
    "Volume Flow RateRMS": "flow_l_min",
}
FILES = ([f"valve1/{i}.csv" for i in range(16)] + [f"valve2/{i}.csv" for i in range(4)]
         + [f"other/{i}.csv" for i in range(1, 5)])          # 24 files -> devices (g, j) in order
ROWS = 600
SPEEDS = (1, 5, 10)

# stressors in dataset rows (row r of the replay window is produced at about r x 1 s / speed)
STRESS = {"p_loss": 0.02, "p_dup": 0.02, "p_reorder": 0.05,
          "outage_gw": 1, "outage_rows": (100, 160),
          "equivocation_p": 0.05, "equivocation_rows": (30, ROWS - 30),
          "compromise_rows": (200, 260),      # compromise of 2 cell-4 devices + gateway 4 at row 200, revoked at row 260
          "relay_forgeries": 72}              # gateway 2 (relay key only) forges 72 observations over the run


@dataclass
class Row:
    dt_ms: int        # time since the first row of the window (dataset time, ms)
    pl: dict
    label: int        # SKAB anomaly label (process anomaly, not an attack)
    src_row: int


def file_sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_file(path: Path, rows: int = ROWS) -> tuple[list[Row], int]:
    import datetime as dt
    with open(path, newline="") as fh:
        r = list(csv.reader(fh, delimiter=";"))
    head, body = r[0], r[1:]
    ci = {c: head.index(c) for c in COLUMNS}
    ai = head.index("anomaly") if "anomaly" in head else None
    start = max(0, min(400, len(body) - rows))
    win = body[start:start + rows]
    t0 = dt.datetime.fromisoformat(win[0][0])
    out = []
    for k, row in enumerate(win):
        t = dt.datetime.fromisoformat(row[0])
        pl = {COLUMNS[c]: round(float(row[i]), 6) for c, i in ci.items()}
        lab = int(float(row[ai])) if ai is not None and row[ai] != "" else 0
        out.append(Row(int((t - t0).total_seconds() * 1000), pl, lab, start + k))
    return out, start


def load_skab(skab_dir: str | Path, rows: int = ROWS) -> dict:
    d = Path(skab_dir) / "data"
    feeds, meta = [], []
    for f in FILES:
        p = d / f
        rws, start = load_file(p, rows)
        feeds.append(rws)
        meta.append({"file": f, "sha256": file_sha256(p), "start_row": start, "rows": len(rws),
                     "anomalous_rows": sum(r.label for r in rws), "span_s": rws[-1].dt_ms / 1000})
    return {"feeds": feeds, "meta": meta}


class ReplayWorld(World):
    """World whose devices produce the rows of a dataset feed at the feed's own timing / speed."""

    def __init__(self, cfg: WorldConfig, feeds: list[list[Row]], speed: float):
        self._feeds_list, self.speed = feeds, speed
        self.feeds: dict[str, list[Row]] = {}
        self.ridx: dict[str, int] = {}
        self.cur: dict[str, Row] = {}
        self.row_label: dict[tuple, int] = {}
        super().__init__(cfg)

    def _build(self) -> None:
        super()._build()
        devs = [d for gw in self.gateways for d in gw.devices]
        assert len(devs) == len(self._feeds_list)
        for d, feed in zip(devs, self._feeds_list):
            self.feeds[d.did] = feed
            self.ridx[d.did] = 0
            self.cur[d.did] = feed[0]
            d.sample = (lambda did: (lambda rng, t: dict(self.cur[did].pl)))(d.did)  # fresh copy: attacks mutate it

    def _produce(self, d, gw, period) -> None:
        feed, i = self.feeds[d.did], self.ridx[d.did]
        if i >= len(feed):
            return
        self.ridx[d.did] = i + 1
        self.cur[d.did] = feed[i]
        self.row_label[(d.did, self.now)] = feed[i].label
        nxt = (feed[i + 1].dt_ms - feed[i].dt_ms) / self.speed if i + 1 < len(feed) else 10 ** 12
        super()._produce(d, gw, max(1, int(round(nxt))))


def label_breakdown(world: ReplayWorld) -> dict:
    """Reachable legitimate observations and how many are authoritative, split by SKAB process-anomaly label."""
    from collections import Counter
    auth = Counter(ck for _, ck in world.sys.authoritative())
    out = {}
    for lab in (0, 1):
        n = a = 0
        for tr in world.truth:
            if world.row_label.get((tr["did"], tr["t"])) != lab or not tr["o"].meta.get("gw_accepted"):
                continue
            n += 1
            if auth[tr["ck"]] > 0:
                a += 1
        out[f"label{lab}_reach"] = n
        out[f"label{lab}_auth"] = a
    return out


def _compromise(w: World, t0: int, t_rev: int, end: int) -> None:
    g4 = w.gateways[3]
    victims = [d for d in g4.devices if not d.legacy][:2]
    w.hooks_deliver.append(ImpersonationHook({v.did for v in victims}, t0, t_rev))
    forge_own_legacy(w, 4, _ts(t0, t_rev, max(1, (t_rev - t0) // 3_000)))
    for v in victims:
        w.revoke(lambda v=v: v.kid, t_rev, t0)
    w.revoke(lambda: g4.kid, t_rev, t0)
    for v in victims:
        w.rotate_device_key(v.did, t_rev + 5_000)
    w.at(t_rev + 5_000, lambda: _rekey_gateway(w, g4))
    if t_rev + 6_000 < end:
        stolen_key_via_broker_rev(w, [v.did for v in victims], g4, _ts(t_rev + 6_000, end, 30))


def build_replay(data: dict, system: str, seed: int, speed: float, stress: bool = True) -> ReplayWorld:
    feeds = data["feeds"]
    span = max(f[-1].dt_ms for f in feeds)
    dur = int(span / speed) + 1_000
    rt = lambda r: int(r * 1000 / speed)  # noqa: E731  dataset row -> simulated time (nominal 1 row/s)
    net = NetConfig(p_loss=STRESS["p_loss"], p_dup=STRESS["p_dup"], p_reorder=STRESS["p_reorder"]) if stress else NetConfig()
    cfg = WorldConfig(seed=seed, system=system, duration_ms=dur, net=net, rate_hz=float(speed))
    w = ReplayWorld(cfg, feeds, speed)
    if not stress:
        return w
    a, b = STRESS["outage_rows"]
    w.partition(STRESS["outage_gw"], rt(a), rt(b))
    e0, e1 = STRESS["equivocation_rows"]
    for gi, gw in enumerate(w.gateways):
        v = [d for d in gw.devices if not d.legacy][0]
        w.hooks_deliver.append(EquivocationHook({v.did}, STRESS["equivocation_p"], rt(e0), rt(e1),
                                                "equivocation-front" if gi >= 2 else "equivocation-back", front=gi >= 2))
    c0, c1 = STRESS["compromise_rows"]
    _compromise(w, rt(c0), rt(c1), dur + 60_000)
    forge_own(w, 2, _ts(rt(3), dur - rt(3), STRESS["relay_forgeries"]))
    return w
