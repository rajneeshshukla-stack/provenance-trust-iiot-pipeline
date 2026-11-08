#!/bin/sh
# extends the revocation sweep and the ablation study from 10 to 20 seeds, then re-attributes the mixed workload
python3 experiments/run_campaign.py revocation --seeds 10 --seed-start 11 --workers 2 --out results/raw/revocation_part2.jsonl > logs/revocation_part2.log 2>&1
python3 experiments/run_campaign.py ablations --seeds 10 --seed-start 11 --workers 2 --out results/raw/ablations_part2.jsonl > logs/ablations_part2.log 2>&1
python3 scripts/attribute_nonlegit.py --scenarios S99_mixed --systems PBTI --seeds 1 20 --out results/summary/nonlegit_attribution_mixed.json > logs/attribution_mixed.log 2>&1
echo DONE > logs/extension.done
