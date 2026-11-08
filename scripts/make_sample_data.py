#!/usr/bin/env python3
"""Write small, human-readable samples of the synthetic workload and of every pipeline's wire format
(data/sample/*.jsonl) plus a W3C PROV-JSON lineage example for one derived record."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from pbti.sim import World, WorldConfig  # noqa: E402

OUT = ROOT / "data" / "sample"
OUT.mkdir(parents=True, exist_ok=True)

for system in ("B1", "B2", "B3", "PBTI"):
    w = World(WorldConfig(seed=1, system=system, duration_ms=20_000, drain_ms=10_000))
    captured = []
    w.hooks_deliver.append(lambda world, gw, e, wire, meta, label, c=captured:
                           (c.append({"t_ms": world.now, "label": label, "transport_identity": meta.get("tid"),
                                      "wire": json.loads(wire)}) if len(c) < 12 else None) and None)
    w.run()
    with open(OUT / f"wire_{system}.jsonl", "w") as fh:
        for row in captured:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
    if system == "PBTI":
        with open(OUT / "truth_observations.jsonl", "w") as fh:
            for tr in w.truth[:48]:
                fh.write(json.dumps({"did": tr["did"], "aid": tr["aid"], "ts_ms": tr["ts"], "t_prod_ms": tr["t"],
                                     "payload": tr["pl"]}, sort_keys=True) + "\n")
        # PROV-JSON export of one derived window and its inputs
        wk, vers = next(iter(w.sys.proc.versions.items()))
        rec = vers[-1]
        prov = {"prefix": {"pbti": "urn:pbti:", "prov": "http://www.w3.org/ns/prov#"},
                "entity": {f"pbti:derived/{wk[0]}/{wk[1]}/v{rec['v']}": {"pbti:inputs_root": rec["inputs_root"],
                                                                        "pbti:cause": rec["cause"], "pbti:count": rec["n"]}},
                "activity": {f"pbti:aggregate/{wk[0]}/{wk[1]}": {"prov:type": "pbti:windowAggregation"}},
                "wasDerivedFrom": {}, "wasGeneratedBy": {}, "agent": {}, "wasAttributedTo": {}}
        for i, ref in enumerate(rec["inputs"]):
            prov["entity"][f"pbti:raw/{ref}"] = {"prov:type": "pbti:RawObservation"}
            prov["wasDerivedFrom"][f"_:d{i}"] = {"prov:generatedEntity": f"pbti:derived/{wk[0]}/{wk[1]}/v{rec['v']}",
                                                  "prov:usedEntity": f"pbti:raw/{ref}"}
        json.dump(prov, open(OUT / "lineage_prov_example.json", "w"), indent=1)
print("samples written to", OUT)
