#!/bin/bash
# Real scenario runs (instrumented B5 in the paper's testbed) + reference-model comparison. Single process, niced.
cd /home/claude/PBTI_v7/tools/b5_refmodel
OUT=/home/claude/PBTI_v7/results/b5_refmodel/real/real_runs.jsonl
date -u +"start %FT%TZ"
for scen in S05_stolen_key S08_seq_reuse_bug S99_mixed; do
  for seed in 1 2; do
    for arm in hist B5S event d0c1; do
      nice -n 10 timeout 1800 python3 extract_real.py $scen $seed $arm $OUT > /dev/null && echo "$scen $seed $arm done" || echo "$scen $seed $arm FAILED"
    done
  done
done
for arm in hist event; do
  nice -n 10 timeout 1800 python3 extract_real.py S12_beyond_horizon 1 $arm $OUT > /dev/null && echo "S12 1 $arm done" || echo "S12 1 $arm FAILED"
done
date -u +"end %FT%TZ"
