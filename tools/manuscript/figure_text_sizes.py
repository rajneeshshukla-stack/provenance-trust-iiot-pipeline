#!/usr/bin/env python3
"""Measure the printed size of text in figure PDFs (pdfminer character sizes times the placement scale).

Usage: python3 -I figure_text_sizes.py OUT.csv  FIG.pdf:PLACED_WIDTH_PT [FIG.pdf:PLACED_WIDTH_PT ...]
PLACED_WIDTH_PT is the width at which the figure is printed (e.g. 0.78 * 525.52 for 0.78\\linewidth in the MDPI full
width). The character size reported by pdfminer is the font size in the figure's own coordinates; multiplied by
placed width / natural width it gives the size on the printed page (rotated text: box width). Characters smaller than 1 pt (rules, artefacts)
are ignored; minimum, 5th percentile and maximum are reported.
"""
import csv
import sys
from pathlib import Path

from pdfminer.high_level import extract_pages
from pdfminer.layout import LTChar, LTTextContainer, LTFigure

out = Path(sys.argv[1])
rows = []


def chars(obj):
    if isinstance(obj, LTChar):
        yield obj
    elif hasattr(obj, "__iter__"):
        for o in obj:
            yield from chars(o)


for arg in sys.argv[2:]:
    path, placed = arg.rsplit(":", 1)
    placed = float(placed)
    page = next(extract_pages(path))
    nat = page.width
    scale = placed / nat
    def true_size(c):
        # pdfminer's size is the glyph-box height in page coordinates; for text rotated by about 90 degrees
        # (matplotlib y-axis labels) the font-size direction is the box width instead
        a, b = c.matrix[0], c.matrix[1]
        return c.width if abs(b) > abs(a) else c.height
    cs = [c for c in chars(page) if c.get_text().strip()]
    sizes = sorted(round(true_size(c) * scale, 2) for c in cs if true_size(c) * scale >= 1.0)
    small = sorted({c.get_text() for c in cs if true_size(c) * scale < 7.9})
    if not sizes:
        rows.append([Path(path).name, round(nat, 1), round(placed, 1), round(scale, 3), 0, "", "", "", "", 0, ""])
        continue
    p5 = sizes[max(0, int(0.05 * len(sizes)) - 1)]
    med = sizes[len(sizes) // 2]
    n_small = sum(1 for x in sizes if x < 7.9)
    rows.append([Path(path).name, round(nat, 1), round(placed, 1), round(scale, 3), len(sizes), sizes[0], p5, med,
                 sizes[-1], n_small, "".join(small)[:60]])
with out.open("w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["figure", "natural_width_pt", "placed_width_pt", "scale", "characters", "min_pt", "p5_pt", "median_pt",
                "max_pt", "chars_below_7.9pt", "glyphs_below_7.9pt"])
    w.writerows(rows)
for r in rows:
    print(r)
