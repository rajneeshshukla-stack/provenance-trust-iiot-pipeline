#!/bin/bash
R=/home/claude/PBTI_v7/scratch/audit_core/repo
S=/home/claude/PBTI_v7/tools/audit_core/stuck_survey.py
OUT=/home/claude/PBTI_v7/results/audit_core/s99_counters_A1seeds.jsonl
: > $OUT
cd $R
nice -n 10 python3 $S $R S99_mixed '{"review_delay_ms": 1000, "review_every_ms": 10000, "review_rule": "defer"}' $(seq 21 40) >> $OUT
nice -n 10 python3 $S $R S99_mixed '{"review_delay_ms": 5000, "review_every_ms": 1000, "review_rule": "defer"}' $(seq 21 40) >> $OUT
echo done
