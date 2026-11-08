"""Estimate the page extent of every numbered heading in an MDPI PDF.

Usage: python3 -I section_pages.py PDF [--level 1|2]
Reads word boxes from `pdftotext -bbox`, rebuilds lines, finds headings of the form
'N. Title' or 'N.M. Title' and prints start page + fraction and length in pages.
"""
import re, subprocess, sys, html
from collections import defaultdict

pdf = sys.argv[1]
level = int(sys.argv[sys.argv.index("--level") + 1]) if "--level" in sys.argv else 2
out = subprocess.run(["pdftotext", "-bbox", pdf, "-"], capture_output=True, text=True, check=True).stdout
pages = re.split(r"<page ", out)[1:]
lines = []  # (page, y, text, xmin)
for pi, pg in enumerate(pages, 1):
    m = re.match(r'width="([\d.]+)" height="([\d.]+)"', pg)
    H = float(m.group(2))
    words = re.findall(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>', pg)
    rows = defaultdict(list)
    for x0, y0, x1, y1, w in words:
        rows[round(float(y0) / 3)].append((float(x0), html.unescape(w), float(y0)))
    for k in sorted(rows):
        ws = sorted(rows[k])
        lines.append((pi, ws[0][2] / H, " ".join(w for _, w, _ in ws), ws[0][0]))
pat1 = re.compile(r"^(\d{1,2})\.\s+([A-Z][A-Za-z,\-–: ]{3,80})$")
pat2 = re.compile(r"^(\d{1,2})\.(\d{1,2})\.\s+([A-Z][^.]{3,90})$")
heads = []
for p, y, t, x in lines:
    t2 = re.sub(r"\s+\d{1,4}$", "", t.strip())  # drop trailing line number
    t2 = re.sub(r"^\d{1,4}\s+", "", t2) if not pat1.match(t2) and not pat2.match(t2) else t2
    m1, m2 = pat1.match(t2), pat2.match(t2)
    if m1 and int(m1.group(1)) <= 12:
        heads.append((p + y, p, 1, m1.group(1), m1.group(2)))
    elif m2 and level >= 2:
        heads.append((p + y, p, 2, m2.group(1) + "." + m2.group(2), m2.group(3)))
# references / back matter markers
for p, y, t, x in lines:
    for marker in ("References", "Supplementary Materials:", "Author Contributions:"):
        if t.strip().startswith(marker) and (marker != "References" or t.strip() == "References"):
            heads.append((p + y, p, 0, "--", marker.rstrip(":")))
heads.sort()
npages = len(pages)
for i, (pos, p, lv, num, title) in enumerate(heads):
    end = heads[i + 1][0] if i + 1 < len(heads) else npages + 1.0
    print(f"{num:6s} {'  ' * (lv - 1 if lv > 0 else 0)}{title[:60]:62s} p{p:2d}  {end - pos:5.2f} pages")
