# V3 candidate datasets for replaying sensor telemetry through the PBTI ingestion pipeline

Date of all checks: 3 November 2026. All URLs accessed on that date.

**Reachability.** "GitHub-only sandbox" means a shell that can reach GitHub (github.com, raw.githubusercontent.com, and possibly media.githubusercontent.com for Git LFS) and package registries, but nothing else.
- GitHub-hosted files were test-downloaded from this audit's shell using `raw.githubusercontent.com` (and `media.githubusercontent.com` for HAI LFS files).
- Other hosts are marked "not reachable from a GitHub-only sandbox" because of where they are hosted. This is not a test of that sandbox.
- The UCI `ucimlrepo` package is on PyPI, but it downloads the data from archive.ics.uci.edu, so installing it does not make UCI data reachable.

**Licence and terms** are quoted exactly from the official page or licence file.

## Recommendation (short)

1. **Primary, for a GitHub-only sandbox: SKAB** (waico/SKAB).
   - Real industrial-style testbed data: a water-circulation loop with pump, valves and 8 sensor channels, sampled at about 1 s, in small CSV files.
   - Licence: the repository's LICENSE file is the GNU GPL v3; the README badge says "License: GPL v3.0".
   - Reachable via GitHub raw. Citation requested.
   - Redistribution is allowed under GPL-3.0 terms. Safer still: do not vendor the files; download them at run time pinned to commit `b2c0d46c2971dcbfe71e26087b6d231998bb91c2` (HEAD on 3 Nov 2026).
2. **Secondary, for a GitHub-only sandbox: HAI 21.03 or 22.04** (icsdataset/hai).
   - ICS testbed (boiler, turbine and water-treatment processes with HIL simulation); 1 s sampling; 59-86 tags; includes attack periods.
   - Licence: "Creative Commons Attribution-ShareAlike License (CC BY-SA 4.0)".
   - Access: 20.07 and 21.03 via GitHub raw (gzip CSV); 22.04 and 23.05 via Git LFS (media.githubusercontent.com).
3. **Best real operational industrial data, but not GitHub-hosted: MetroPT-3** (UCI, CC BY 4.0). Air production unit of a metro train compressor, Feb-Aug 2020. Use only if UCI is reachable, or mirror it under CC BY 4.0 with attribution.
4. **Not recommended for an open, redistributable reproduction package:**
   - **TON_IoT**: academic use only; commercial use on request; no redistribution grant; SharePoint-hosted; telemetry mostly *simulated* via Node-RED.
   - **SWaT/WADI**: request form; the terms forbid sharing.

Either way, the manuscript's data-availability statement (main.tex l.326: "no third-party dataset was used") and the "synthetic telemetry" wording must change if any of these is used. Label any replay precisely, as BASELINE_CLAIMS_REGISTER C20 requires.

---

## 1. UNSW TON_IoT (telemetry datasets)

- **Official page.** https://research.unsw.edu.au/projects/toniot-datasets ("Last Updated: 02 June 2021"; key contact Assoc. Prof. Nour Moustafa, UNSW Canberra).
- **Access route.** The page links "The datasets can be downloaded from HERE" to UNSW SharePoint/OneDrive folders (`unsw-my.sharepoint.com/:f:/g/personal/z5025758_ad_unsw_edu_au/...`). WebFetch was refused (robots disallowed), so file names and sizes on SharePoint could **not** be verified.
  - **Not reachable from a GitHub-only sandbox.**
  - Third-party mirrors exist on Kaggle and GitHub, but the stated terms do not authorise redistribution, so their use is not covered.
- **Licence / terms (verbatim):** "Free use of the TON_IoT datasets for academic research purposes is hereby granted in perpetuity. Use for commercial purposes is allowable after asking the author, Dr Nour Moustafa, who has asserted his right under the Copyright."
  - No licence name (e.g. CC) is given.
  - **Redistribution: not granted** (not addressed). Treat it as not allowed without permission.
- **Citation required (verbatim):** "To whom intend the use of the TON_IoT datasets have to cite the above eight papers." The eight papers listed include:
  - Moustafa, *Sustainable Cities and Society* 72 (2021) 102994, DOI 10.1016/j.scs.2021.102994;
  - Booij et al., *IEEE IoT-J* 9(1):485-496 (2022), DOI 10.1109/JIOT.2021.3085194;
  - Alsaedi et al., *IEEE Access* 8:165130-165150 (2020), DOI 10.1109/ACCESS.2020.3022862;
  - two TrustCom 2020 papers, an eResearch Australasia 2019 paper, an arXiv preprint (1906.01055) and Ashraf et al., SCS 2021.
  - The three DOIs above were verified in Crossref.
- **Content.**
  - Official page: "IoT/IIoT datasets were logged in log and CSV files, where more than 10 IoT and IIoT sensors such as weather and Modbus sensors were used". The folders are Raw, Processed, Train_Test, Description_stats and SecurityEvents_GroundTruth.
  - Alsaedi et al. 2020 (FULL TEXT of a figshare-hosted copy of the paper; the IEEE VoR was blocked):
    - seven telemetry CSV sets: "Fridge, GPS Tracker, Motion Light, Garage Door, Modbus, Thermostat and Weather";
    - "Each IoT device has its own CSV file such as 'Train_Test_IoT_device_name.csv'";
    - "The testbed has a combination of physical and simulated IoT/IIoT services ... physical ESP8266 weather sensors ... The testbed also has six simulated IoT services ... developed using Javascript in the Node-RED API and linked to the public MQTT broker";
    - the fridge script emits `fridge_temperature` and `temp_condition`; the thermostat script uses `currentTemperature` and `sensorState`.
- **Columns, units, sampling, sizes.** The per-dataset feature tables (Tables 2-8 of Alsaedi et al.) are images and could not be text-extracted. Sampling rate and file sizes are not documented on the official page. **Not verified.**
- **Suitability.** Low for PBTI:
  - most telemetry is generated by Node-RED scripts, so it is still synthetic;
  - the terms bar redistribution and commercial use without asking;
  - it is not reachable from a GitHub-only sandbox.
  - It is useful only as "labelled IoT telemetry with attack periods" for an academic-only, non-redistributed experiment.

## 2. iTrust SWaT and WADI (SUTD)

- **Official pages.** https://itrust.sutd.edu.sg/itrust-labs_datasets/ (terms; via WebFetch) ; https://www.sutd.edu.sg/itrust/itrust-labs/datasets/dataset-characteristics/swat/ and .../wadi/ (characteristics; via WebFetch). The shell could not connect to itrust.sutd.edu.sg (timeout).
- **Access route.** A request form: "Requests for datasets and details of the dataset characteristics can be obtained here"; "we may take up to three working days to process your request". "Earlier releases were shared through download links sent to requesters" (WebFetch summary of the SWaT page). **Not reachable from a GitHub-only sandbox.**
- **Terms (as returned via WebFetch; numbered as on the page).** By requesting and receiving a dataset, the requester agrees to:
  1. have their and their organisation's name and the request date published on iTrust's site;
  2. give explicit credit to "iTrust, Centre for Research in Cyber Security, Singapore University of Technology and Design";
  3. notify iTrust when such works are published;
  4. not share the dataset with others, privately or publicly ("all additional requests for the same dataset needs to go through the request form").
  - Data are provided "on a good faith and 'as is' basis"; no follow-up support since 1 Jul 2022.
  - **Redistribution: not allowed.** Commercial use: not addressed.
- **Content (as returned via WebFetch).**
  - SWaT.A1 (Dec 2015): "11 days of continuous operation: 7 under normal operation and 4 days with attack scenarios"; 41 attacks; "51 sensors and actuators".
  - Later SWaT releases: A2-A7 (2015-2020) and A9 (Dec 2023, 105 h, no attacks).
  - WaDi.A1: "16 days of continuous operation: 14 under normal operation & 2 days with attack scenarios", "123 sensors and actuators", 15 attacks. WaDi.A2 (19 Dec 2019): "WADI_14days_new.csv" plus a labels file. WaDi.A3 (Dec 2023, 100 h).
  - Sampling interval: **not stated** on the characteristics pages; it is commonly reported as 1 s in the literature, not verified here.
- **Suitability.** Good industrial realism, but the no-sharing term means it cannot appear in an open artifact. Use only for a private, non-redistributed replication, with the credit and notification obligations.

## 3. SKAB: Skoltech Anomaly Benchmark (GitHub waico/SKAB)

- **URL.** https://github.com/waico/SKAB (HEAD `b2c0d46c2971dcbfe71e26087b6d231998bb91c2` on 3 Nov 2026). Version: README "SKAB (v0.9) contains 34 datasets"; later in the same README "The SKAB v0.9 corpus contains 35 individual data files". The README announces a future v1.0 with 300+ files.
- **Access route.** **Via GitHub raw**, e.g. `https://raw.githubusercontent.com/waico/SKAB/master/data/valve1/1.csv`. Tested from this shell: HTTP 200 for README.md, LICENSE, data/README.md, data/anomaly-free/anomaly-free.csv, data/valve1/1.csv and data/other/1.csv. Also on Kaggle (DOI 10.34740/KAGGLE/DSV/1693952, verified in DataCite: "SKAB - Skoltech Anomaly Benchmark", Iurii D. Katser, Vyacheslav O. Kozitsin, Kaggle, 2020; rightsList empty). The Kaggle page did not expose its licence to WebFetch.
- **Licence (exact).**
  - The repository LICENSE file is "GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007"; the README badge reads "License: GPL v3.0".
  - No separate data licence was found, so the GPL-3.0 applies to the repository contents, data included. A software licence applied to data is unusual; attribution and licence-notice obligations apply when redistributing.
  - **Redistribution: allowed under GPL-3.0** (keep the licence text; modified versions under GPL-3.0).
- **Citation (README, verbatim):** "Please cite our project in your publications if it helps your research." The BibTeX is a @misc: Katser, Iurii D. and Kozitsin, Vyacheslav O., *Skoltech Anomaly Benchmark (SKAB)*, Kaggle, 2020, DOI 10.34740/KAGGLE/DSV/1693952. The README says a position paper is "currently submitted for publication".
- **Columns and units (README).**
  - `datetime` "(YYYY-MM-DD hh:mm:ss)"
  - `Accelerometer1RMS`, `Accelerometer2RMS` "(Amount of g units)"
  - `Current` "(Ampere)"
  - `Pressure` "(Bar)"
  - `Temperature` "temperature of the engine body (The degree Celsius)"
  - `Thermocouple` "temperature of the fluid in the circulation loop (The degree Celsius)"
  - `Voltage` "(Volt)"
  - `RateRMS` "circulation flow rate ... (Liter per minute)"
  - `anomaly`, `changepoint` (0/1)
  - The actual CSV header uses `Volume Flow RateRMS`; the separator is `;`; anomaly-free.csv has no label columns.
- **Sampling (measured here, not documented).** Timestamp deltas in three files are mostly 1 s, with about 6% at 2 s:
  - anomaly-free.csv: 9,405 rows, 2020-02-08 13:30:47 to 16:16:47;
  - valve1/1.csv: 1,145 rows;
  - other/1.csv: 745 rows.
- **Layout (data/README.md).**
  - `anomaly-free/anomaly-free.csv`
  - `valve1/1-16.csv` ("closing the valve at the flow inlet to the pump")
  - `valve2/1-4.csv` ("closing the valve at the outlet")
  - `other/1-14.csv`: leaks, rotor imbalance, cavitation, temperature, etc.
  - Sizes are about 70 KB to 815 KB per file.
- **Suitability.** High for a GitHub-only sandbox.
  - Real sensor data from a physical testbed, multi-channel, at about 1 Hz, small, labelled.
  - It maps naturally to one device (or several, one per experiment) emitting 4-8 channel observations.
  - The 2 s gaps exercise PBTI's gap and timestamp handling.
  - Limitation: a single testbed and short runs (12 min to 2.8 h).

## 4. HAI: HIL-based Augmented ICS security dataset (GitHub icsdataset/hai)

- **URL.** https://github.com/icsdataset/hai (HEAD `2a814cebc9a66b06c9e5cd545e2d72e65d383737` on 3 Nov 2026). Also on Kaggle (https://www.kaggle.com/datasets/icsdataset/hai-security-dataset).
- **Versions (README).**
  - HAI 20.07 (bug-fixed HAI 1.0, Feb/Aug 2020)
  - HAI 21.03
  - HAI 22.04
  - HAI 23.05, plus HAIEnd 23.05 (internal boiler DCS logic tags)
  - "The version numbering follows a date-based scheme".
- **Access route.**
  - **Via GitHub raw** for 20.07 and 21.03, e.g. `hai-21.03/train1.csv.gz` (tested: HTTP 206 on a range request; gzip content).
  - For 22.04 and 23.05 the raw files are **Git LFS pointers** ("From HAI 22.04, use git lfs pull"). Their contents are served by `https://media.githubusercontent.com/media/icsdataset/hai/master/...`, which was tested (HTTP 206; CSV header `timestamp,P1_B2004,...`). This needs GitHub LFS media access in the sandbox.
- **Licence (README, exact):** "This work is licensed under a Creative Commons Attribution-ShareAlike License (CC BY-SA 4.0)". **Redistribution: allowed** with attribution, and adaptations under the same licence.
- **Citation.** The README asks users to "please cite the sources below", including:
  - Shin, Lee, Yun, Min, "Two ICS Security Datasets and Anomaly Detection Contest on the HIL-based Augmented ICS Testbed", CSET '21, ACM, pp. 36-40, DOI 10.1145/3474718.3474719 (verified in Crossref);
  - Shin et al., "HAI 1.0: HIL-Based Augmented ICS Security Dataset", CSET '20;
  - a "HAI security datasets" (2023) entry.
- **Columns and sampling.**
  - "The first column represents the observed time in the 'yyyy-MM-dd hh:mm:ss' format, while the rest of the columns provide the recorded SCADA data points". The last columns are attack labels (from 22.04 only the global `attack` label).
  - The example rows are at 1 s intervals. "Data Points" per version: 59 (20.07), 78 (21.03), 86 (22.04, 23.05), 225 (HAIEnd 23.05).
  - Units are per the technical manual (not checked).
- **Sizes (README table).**
  - 21.03: normal 352 h / 471 MB; attack 112 h / 205 MB (50 attacks).
  - 22.04: normal 279 h / 534.4 MB; attack 100.3 h / 195.6 MB (58 attacks).
  - 23.05: normal 249 h / 494.8 MB; attack 79 h / 156.6 MB (52 attacks).
- **Processes (README).**
  - P1 Boiler (Emerson Ovation DCS)
  - P2 Turbine (GE Mark VIe DCS)
  - P3 Water treatment (Siemens S7-300 PLC)
  - P4 HIL simulation (dSPACE SCALEXIO)
  - "interconnected with the real-world processes through a Siemens S7-1500 PLC and ET200 remote IO devices ... based on the OPC gateway".
- **Suitability.** High.
  - Genuine ICS process telemetry at 1 Hz with many tags. It can be partitioned into devices by process or controller.
  - The open licence permits redistribution.
  - Includes labelled attack periods. These are process attacks, which are out of PBTI's detection scope (AP5), but they are useful for showing that authenticated data is not necessarily physically correct.

## 5. MetroPT-3 (UCI Machine Learning Repository, id 791)

- **URL.** https://archive.ics.uci.edu/dataset/791 ; DOI 10.24432/C5VW3R (DataCite: "MetroPT-3 Dataset", UCI Machine Learning Repository, 2021).
- **Access route.** UCI download (zip 208.3 MB; file "MetroPT3(AirCompressor).csv" 208.2 MB plus "Data Description_Metro.pdf"). **Not reachable from a GitHub-only sandbox.** A related **MetroPT2** is on Zenodo (DOI 10.5281/zenodo.7766691, CC BY 4.0, about 1.2 GB plus 1.6 GB), also not GitHub.
- **Licence (UCI, exact):** "This dataset is licensed under a Creative Commons Attribution 4.0 International (CC BY 4.0) license. This allows for the sharing and adaptation of the datasets for any purpose, provided that the appropriate credit is given." **Redistribution: allowed** with attribution.
- **Citation (UCI):** "Davari, N., Veloso, B., Ribeiro, R., & Gama, J. (2021). MetroPT-3 Dataset [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5VW3R". Introductory paper: Davari et al., IEEE DSAA 2021 (DOI not verified here).
- **Content.**
  - "multivariate time series data obtained from several analogue and digital sensors installed on the compressor of a train. The data span between February and August 2020 and includes 15 signals".
  - 1,516,948 instances.
  - Analogue variables (UCI variables table): `timestamp`, TP2, TP3, H1, DV_pressure, Reservoirs (bar), Oil_temperature (°C), Motor_current (A).
  - Digital signals, as named in UCI's attribute description: COMP, DV electric, TOWERS, MPG, LPS, Pressure Switch, Oil Level, Caudal Impulse.
  - The exact CSV header spellings were not verified (the file was not downloaded).
  - Four documented air-leak failures with time windows.
  - **Sampling is inconsistently documented** on the UCI page: "The data were logged at 1Hz by an onboard embedded device", but also "1516948 data points collected at 0.1Hz". Check the timestamps before use.
- **Suitability.** High realism (in-service industrial asset) and an open licence. The size and host make it unsuitable for a GitHub-only sandbox unless a CC BY 4.0 mirror or subset is prepared with attribution.

## 6. Other candidates checked (lower priority)

| Dataset | URL / ID | Licence (exact) | Redistribution | Access | Notes |
|---|---|---|---|---|---|
| Condition monitoring of hydraulic systems (UCI 447) | https://archive.ics.uci.edu/dataset/447 ; DOI 10.24432/C5CW21 | "Creative Commons Attribution 4.0 International (CC BY 4.0)" | yes, with credit | UCI only (zip 73.1 MB); not GitHub | Real test rig; 2,205 load cycles of 60 s; sensors PS1-6 and EPS1 at 100 Hz, FS1-2 at 10 Hz, TS1-4, VS1, CE, CP, SE at 1 Hz. Files are "matrices (tab-delimited) with the rows representing the cycles and the columns the data points within a cycle". There are **no absolute timestamps**, so replay needs synthetic time. Citation: Helwig, Pignanelli, Schütze (2015), UCI. |
| Numenta Anomaly Benchmark (NAB) | https://github.com/numenta/NAB (HEAD `ea702d75cc2258d9d7dd35ca8e5e2539d71f3140`); Zenodo DOI 10.5281/zenodo.1040335 (README badge; not verified) | LICENSE.txt: "Copyright 2014-2024 Numenta Inc. Permission is hereby granted, free of charge, ..." (MIT License text) | yes, with notice | **via GitHub raw** (tested) | Mostly non-industrial series. `realKnownCause/machine_temperature_system_failure.csv` is "Temperature sensor data of an internal component of a large, industrial mahcine" [sic]: 22,695 rows at 5-min intervals (measured), with one backwards timestamp step of 3,300 s (measured), which is useful for clock-step tests. Single-valued. Citation: Ahmad, Lavin, Purdy, Agha, *Neurocomputing* 262:134-147 (2017), DOI 10.1016/j.neucom.2017.04.070 (verified in Crossref). |

## 7. Notes for use in V3

- Replaying any dataset changes the claim from "synthetic telemetry" to "replayed recorded telemetry (dataset, version, commit)". The data-availability statement (main.tex l.326) and the Generative-AI/methods text must then name the dataset, licence and citation.
- PBTI's security results do not depend on payload realism. Replay mainly tests:
  - encoding and canonicalization of real numeric values (number spelling under RFC 8785);
  - irregular sampling (SKAB's 2 s gaps; NAB's backward step);
  - realistic payload sizes for throughput and wire bytes.
  State this to avoid over-claiming "real-data validation".
- For share-alike licences (HAI CC BY-SA 4.0; SKAB GPL-3.0), do not commit transformed data into the paper's repository under a different licence. Download at run time, pinned by commit, and record SHA-256 digests in the manifests.
