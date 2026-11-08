#!/bin/bash
# Regenerate every summary, macro file, generated table and figure of the article and the supplement from the raw
# results of TREE (a repository tree: the historical tree, or the corrected tree written by build_corrected_tree.py).
# The frozen analysis scripts are run unchanged, in the order of the V7 reproduction instructions.
# usage: tools/v9/regenerate_analysis.sh TREE
set -e
cd "$1"
export PYTHONDONTWRITEBYTECODE=1 MPLBACKEND=Agg
mkdir -p paper/generated paper/figures/png600 paper/figures/png     # output directories of the frozen scripts
date -u +"start %FT%TZ"
python3 analysis/analyze.py              > logs_v9_analyze.txt 2>&1        # revision-2 macros (\R...)
python3 analysis/analyze_v3.py           > logs_v9_analyze_v3.txt 2>&1     # V3 macros (\V...), tables, summaries
python3 analysis/analyze_v4.py           > logs_v9_analyze_v4.txt 2>&1     # V4 macros (\W...), tables, gates
# the article's generated/ directory is composed as in the frozen V7 build: every file written by the three analysis
# scripts, then the label-neutral versions of ten tables, then the \X macros and tables
mkdir -p paper_v7/generated
cp paper/generated/*.tex paper_v7/generated/
python3 -B tools/v7/neutralize_tables.py paper/generated paper_v7/generated > logs_v9_neutralize.txt 2>&1
python3 -B tools/v7/analysis_v7.py . . paper_v7/generated > logs_v9_analysis_v7.txt 2>&1   # V7 macros (\X...)
python3 -B tools/v7/figures_v7.py . paper_v7/figures > logs_v9_figures_v7.txt 2>&1
date -u +"end %FT%TZ"
