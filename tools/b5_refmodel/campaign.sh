#!/bin/bash
# Differential-test campaign (single process, niced: shares 2 vCPUs with another long job).
cd /home/claude/PBTI_v7/tools/b5_refmodel
OUT=/home/claude/PBTI_v7/results/b5_refmodel/campaign
run() { fam=$1; lo=$2; hi=$3; step=$4
  for ((s=lo; s<hi; s+=step)); do e=$((s+step)); [ $e -gt $hi ] && e=$hi
    nice -n 10 python3 run_diff.py --family $fam --seeds $s:$e --out $OUT/$fam.jsonl
  done; }
date -u +"start %FT%TZ"
run stale_into_held 0 400 100
run rand_small 0 2500 250
run s08_like 0 100 25
run s12_like 0 100 25
run s05_like 0 100 25
run s99_like 0 100 25
date -u +"end %FT%TZ"
