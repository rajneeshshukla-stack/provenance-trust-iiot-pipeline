# Data

All data in this study are generated synthetically by the testbed; no third-party dataset is redistributed.

* Telemetry model (`src/pbti/sim.py`, `Device.sample`): per device, temperature (°C), vibration (mm/s), pressure (bar)
  and flow (m³/h) as seeded sinusoids plus Gaussian noise, sampled at 1 Hz, rounded to 2–3 decimals.
* `data/sample/truth_observations.jsonl`: first 48 legitimate observations of seed 1 (did, aid, source time, production
  time, payload).
* `data/sample/wire_<SYSTEM>.jsonl`: the first messages delivered to each pipeline (B1, B2, B3, PBTI) for seed 1,
  showing each wire format.
* `data/sample/lineage_prov_example.json`: W3C PROV-JSON-style lineage of one derived window.
* Regenerate with `make sample-data`. Full raw experiment results: `results/raw/*.jsonl` (one JSON object per run).

Public industrial datasets (e.g., HAI, CC BY-SA 4.0) were evaluated as candidates but not used; see
`research/OPEN_RESEARCH_ITEMS.md` item 10.
