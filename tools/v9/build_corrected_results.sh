#!/bin/bash
# V9: from the stored raw results to every number, table and figure of the article and Document S1.
#   1. corrected-comparator tree: copy of the repository with the B5/B5S rows replaced by the corrected reruns
#   2. the unchanged analysis scripts, run in that tree (macros \R \V \W \X, generated tables, summaries)
#   3. print-size figures from that tree
#   4. V9 analysis (\Y macros, Document S1 tables of the correction and robustness checks, Data S1 additions)
#   5. generated files copied into the manuscript directory; presentation-only layout and class wording
# usage: tools/v9/build_corrected_results.sh PAPER_DIR [TREE_DIR]
set -e
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
PAPER="$(cd "$1" && pwd)"
TREE="${2:-$REPO/../corrected_tree}"
export PYTHONDONTWRITEBYTECODE=1 MPLBACKEND=Agg
python3 "$REPO/tools/v9/build_corrected_tree.py" "$TREE"
"$REPO/tools/v9/regenerate_analysis.sh" "$TREE"
python3 -I "$REPO/tools/manuscript/figures_print.py" "$TREE" "$PAPER/figures" > "$TREE/logs_v9_figures_print.txt" 2>&1
python3 "$REPO/tools/v9/analysis_v9.py" "$REPO" "$TREE" "$TREE/paper_v7/generated" "$REPO/results/v9/summary"
python3 -I "$REPO/tools/manuscript/import_generated.py" "$TREE/paper_v7/generated" "$PAPER"
python3 -I "$REPO/tools/manuscript/table_layout.py" "$PAPER"
python3 -I "$REPO/tools/manuscript/relabel_classes.py" "$PAPER"
python3 -I "$REPO/tools/manuscript/relabel_rows.py" "$PAPER"
python3 -I "$REPO/tools/manuscript/prune_generated.py" "$PAPER"
echo "generated files and figures written to $PAPER (tree: $TREE)"
