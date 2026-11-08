# V3 hardware experiments: multi-host deployment and constrained-device signing

**Status: NOT PERFORMED.** The study environment was one virtual machine (2 vCPUs, 7.8 GB RAM) with no second host and
no constrained device. Both experiments below are prepared (scripts, configuration, instrumentation, protocol) and
were only smoke-tested on that single host, which is neither a multi-host experiment nor a device measurement. No
number from these smoke tests appears in the manuscript.

| Item | Script | Smoke test on the study host |
|---|---|---|
| Multi-host MQTT/TLS deployment | `experiments/run_multihost.py` | all roles on one host, 200 msg/s, 4 s: 800/800 accepted (functional only) |
| Constrained-device micro-benchmark | `experiments/run_device_bench.py` | label `server-smoke`, 300 iterations (functional only) |

## 1. Why these experiments matter

The manuscript's performance results come from one shared 2-vCPU host on which publisher, broker and verifier compete
for the same cores, and its edge-signing cost was measured on a server CPU. Neither says how the pipeline behaves when
the three roles run on separate machines connected by a real network, or what signing costs on a device of the class
that would sign observations. These results must not be extrapolated from the server measurements.

## 2. Multi-host deployment protocol

### 2.1 Hosts

Three distinct physical hosts or VMs on distinct physical machines (containers on one machine do not qualify):

| Host | Role | Minimum |
|---|---|---|
| H1 | edge publisher (4 emulated gateways, real-time device and relay signing) | 2 cores |
| H2 | MQTT broker (Mosquitto, mutual TLS, per-gateway identity, per-topic ACL) | 2 cores |
| H3 | verifier with durable SQLite group commit and evidence log | 2 cores, SSD |

### 2.2 Preparation (once)

1. Install the repository and `pip install -r requirements.txt` (or `deploy/requirements.lock.txt` with
   `--require-hashes`) on H1 and H3; install Mosquitto 2.0.x on H2.
2. Synchronise all clocks with PTP if available, otherwise chrony against the same local NTP server. Require
   `chronyc tracking` to report |offset| < 0.5 ms on H1 and H3 before every session.
3. On any host: `python3 experiments/run_multihost.py pki --pki pki --broker-names <H2 DNS name>,<H2 IP>`; copy the
   `pki` directory to all three hosts (test keys for this experiment only).
4. Record per host: `python3 experiments/run_multihost.py hostinfo --out hosts.jsonl` (CPU model, cores, memory, OS,
   kernel, Python and `cryptography` versions, chrony state, Mosquitto version).
5. Network: `ping -c 100 <peer>` (RTT distribution) and `iperf3 -c <peer> -t 20` (bandwidth) for H1-H2 and H2-H3;
   record both directions.

### 2.3 One repetition

1. H2: `python3 experiments/run_multihost.py broker --pki pki` (fresh broker per repetition).
2. Agree a start time `T` (epoch seconds, about 20 s in the future) and pass it to both sides.
3. H3: `python3 experiments/run_multihost.py verifier --pki pki --broker <H2> --system S --rate R --rep k --start-at T --warm 3 --measure 30 --drain 5 --out ver.jsonl`
4. H1: `python3 experiments/run_multihost.py publisher --pki pki --broker <H2> --system S --rate R --rep k --start-at T --warm 3 --measure 30 --drain 5 --out pub.jsonl`
5. Record `chronyc tracking` on H1 and H3 immediately after the repetition.
6. On H2, sample broker CPU and memory during the run (`pidstat -u -r -p $(pidof mosquitto) 1`).

### 2.4 Design

* Pipelines: B1, B2, B3, PBTI (B4 and B5 are accepted by the verifier role as well).
* Offered loads: 200, 500, 1000, 1500, 2000 messages/s, plus a step search for the saturation point of each pipeline
  (load at which the achieved rate falls below 98 % of the offered rate or p50 latency exceeds 100 ms).
* 30 repetitions per (pipeline, load) cell, in randomised order, broker restarted for each repetition.
* Record per repetition: achieved rate, p50/p95/p99 latency (CLOCK_REALTIME commit minus send), verifier CPU,
  verifier RSS, verifier input-queue depth, broker CPU/RSS, losses (sent minus committed), dispositions, database bytes.
* Latency error bound: |clock offset| + offset uncertainty from chrony, reported with every latency.

### 2.5 Analysis

Same as the single-host end-to-end analysis (`analysis/analyze_v3.py`, function `e2e`): per-cell means and bootstrap
CIs over repetitions, Mann-Whitney U per load with Holm correction, Cliff's delta. Report the saturation point per
pipeline and compare it with the single-host result, without pooling the two.

## 3. Constrained-device protocol

### 3.1 Devices

At least one Raspberry-Pi-class device (for example Raspberry Pi 4 Model B, 4 GB, Cortex-A72) and, if available, one
smaller device (for example Raspberry Pi Zero 2 W, Cortex-A53). Record board revision, SoC, RAM, storage medium, OS
image and kernel, power supply, cooling (heat sink, fan), and ambient temperature.

### 3.2 Procedure

1. Fresh OS image, no other workload; CPU governor fixed (`performance` and, separately, the default `ondemand`).
2. Install Python 3.11+ and the pinned `cryptography` wheel (record the wheel and its OpenSSL version).
3. Store the device key as it would be stored in deployment (file, TPM or secure element) and record the storage in
   `--key-storage`; this benchmark uses an in-memory key unless modified.
4. Let the device idle 5 minutes; record temperature and throttling (`vcgencmd measure_temp`, `vcgencmd get_throttled`).
5. Run `python3 experiments/run_device_bench.py --label <device> --n 5000 --power-mode "<supply>"` five times with
   2 minutes of idle between runs; the script records platform, thermal state before and after, payload, statement
   and message sizes, and per-operation CPU and wall time (mean, p50, p95, p99).
6. Energy (optional): with a USB power meter or a shunt and data logger, record energy over each run and pass it with
   `--energy-j-before` / `--energy-j-after`; subtract the idle energy over the same duration.
7. Repeat steps 4-6 under sustained load (run 30 minutes continuously) to observe thermal throttling.

### 3.3 Reported quantities

Per device and governor: Ed25519 sign and verify time, JCS canonicalisation time, device-role statement signing time,
gateway-role full-message encoding time (observation and relay signatures), CPU time per operation, message and
payload sizes, maximum sustainable signing rate (1 / mean device-role time), temperature and throttling flags, and
energy per signed observation where measured. These values replace, for the device class tested, the server-CPU edge
cost reported in the manuscript; they must not be used to predict other device classes.
