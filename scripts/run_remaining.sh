#!/bin/sh
# waits for the running campaign chain, then runs the remaining measurements sequentially
while pgrep -f "run_campaign.py (revocation|audit|scenarios|ablations) --seeds" >/dev/null || pgrep -f "sh -c python3 experiments/run_campaign.py scenarios" >/dev/null; do sleep 10; done
python3 experiments/run_campaign.py scenarios --seeds 10 --seed-start 11 --workers 2 --out results/raw/scenarios_part2.jsonl > logs/scenarios_part2.log 2>&1
python3 experiments/run_campaign.py ablations --seeds 10 --workers 2 --only-errors-of results/raw/ablations.jsonl > logs/ablations_rerun.log 2>&1
python3 experiments/run_throughput.py --reps 10 --n 20000 > logs/throughput.log 2>&1
python3 experiments/run_throughput.py --reps 3 --n 20000 --scaling > logs/scaling.log 2>&1
python3 experiments/run_mqtt_e2e.py --rates 200 500 1000 1500 --reps 5 --warm 3 --measure 12 --drain 4 > logs/e2e.log 2>&1
echo ALLDONE > logs/remaining.done
