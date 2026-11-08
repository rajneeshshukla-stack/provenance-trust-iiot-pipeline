#!/bin/sh
# revision 2: strongest-combination baseline B4 on all scenarios (seeds 1-20) and on the mixed workload (seeds 1-20)
python3 experiments/run_campaign.py scenarios --systems B4 --seeds 20 --workers 2 --out results/raw/scenarios_part3_b4.jsonl > logs/scenarios_b4.log 2>&1
python3 experiments/run_campaign.py ablations --systems B4 --seeds 20 --workers 2 --out results/raw/ablations_part3_b4.jsonl > logs/ablations_b4.log 2>&1
echo DONE > logs/b4.done
