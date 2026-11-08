#!/usr/bin/env python3
"""Export editing copies of the manuscript (V4): research/V4/manuscript/<NAME>.md and <NAME>.docx.

The MDPI LaTeX source (paper/main.tex) is authoritative. This script expands generated macros and tables, maps
MDPI-specific commands to plain structure, converts figures to PNG, and runs pandoc.
Citations are numbered exactly as in the compiled PDF: numbers come from paper/main.aux and the reference list
from paper/main.bbl, so run `make paper` first.
"""
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "paper"
OUT = ROOT / "research" / "V4" / "manuscript"
OUT.mkdir(parents=True, exist_ok=True)
NAME = "Provenance-Bound_Trust-Aware_Ingestion_V5_Manuscript"
TMP = ROOT / "build" / "export"
TMP.mkdir(parents=True, exist_ok=True)

src = (P / "main.tex").read_text()
macros = dict(re.findall(r"\\newcommand\{\\(R[A-Za-z]+)\}\{(.*)\}", (P / "generated" / "results_macros.tex").read_text()))
if (P / "generated" / "v3_macros.tex").exists():   # V3 macros (analysis/analyze_v3.py)
    macros.update(re.findall(r"\\newcommand\{\\(V[A-Z][A-Za-z]+)\}\{(.*)\}", (P / "generated" / "v3_macros.tex").read_text()))
if (P / "generated" / "v4_macros.tex").exists():   # V4 macros (analysis/analyze_v4.py)
    macros.update(re.findall(r"\\newcommand\{\\(W[A-Z][A-Za-z]+)\}\{(.*)\}", (P / "generated" / "v4_macros.tex").read_text()))


def expand_inputs(t):
    def rep(m):
        f = P / (m.group(1) if m.group(1).endswith(".tex") else m.group(1) + ".tex")
        return f.read_text() if f.exists() else ""
    return re.sub(r"\\input\{(generated/[^}]+)\}", rep, t)


def braced(t, start):
    """return (content, end_index) of the balanced {...} beginning at t[start] == '{'"""
    depth = 0
    for i in range(start, len(t)):
        if t[i] == "{":
            depth += 1
        elif t[i] == "}":
            depth -= 1
            if depth == 0:
                return t[start + 1:i], i + 1
    raise ValueError("unbalanced")


def take_cmd(t, name):
    i = t.find("\\" + name + "{")
    if i < 0:
        return None, t
    content, end = braced(t, i + len(name) + 1)
    return content, t[:i] + t[end:]


body = src
title, body = take_cmd(body, "Title")
abstract, body = take_cmd(body, "abstract")
keywords, body = take_cmd(body, "keyword")
back = {}
for cmd, label in [("supplementary", "Supplementary Materials"), ("authorcontributions", "Author Contributions"),
                   ("funding", "Funding"), ("institutionalreview", "Institutional Review Board Statement"),
                   ("informedconsent", "Informed Consent Statement"), ("dataavailability", "Data Availability Statement"),
                   ("acknowledgments", "Acknowledgments"), ("conflictsofinterest", "Conflicts of Interest")]:
    c, body = take_cmd(body, cmd)
    back[label] = c
# keep only the document body
body = body[body.index("\\begin{document}") + len("\\begin{document}"):body.index("\\end{document}")]
# remove abbreviations block and bibliography wrapper
body = re.sub(r"\\abbreviations\{Abbreviations\}\{.*?\\end\{tabular\}\s*\}", "", body, flags=re.S)
body = re.sub(r"\\begin\{adjustwidth\}\{-\\extralength\}\{0cm\}\s*\\reftitle\{References\}.*?\\end\{adjustwidth\}", "", body, flags=re.S)
body = body.replace("\\begin{adjustwidth}{-\\extralength}{0cm}", "").replace("\\end{adjustwidth}", "")
body = body.replace("\\vspace{6pt}", "")
# algorithm -> plain-text block; keep in sync with Algorithm 1 in paper/main.tex (checked below by caption)
ALG_CAPTION = "PBTI admission of one received message m at verifier time t"
ALG_LINES = [
    "    // a reviewed release re-runs this algorithm with only the case's quarantine reason waived",
    " 1  (obs, sig_o, rel, sig_w) <- parse(m)                   // else REJECT malformed",
    " 2  K_o <- key(obs.kid); K_w <- key(rel.wkid)",
    "    require subject(K_w) = rel.wid, and subject(K_o) = obs.did (device)",
    "    or subject(K_o) = rel.wid (legacy)",
    " 3  verify sig_w; check rel.odig = H(JCS(obs) || sig_o); verify sig_o",
    "                                                           // else REJECT integrity",
    " 4  for each K in {K_o, K_w}:",
    " 5      if K revoked at t, unless a REVOKED_BUFFERED waiver meets the release-evidence policy:",
    "             return QUARANTINE if rel.mode = buffered (policy), else REJECT",
    " 6      if t > K.exp + grace: return QUARANTINE expired    // within grace: annotate",
    " 7  (permit, pv) <- PDP(did, aid, wid, sch, origin, t)",
    "    if not permit: return REJECT unauthorized",
    " 8  if ts > t + skew or t - ts > h_max: return QUARANTINE future/stale",
    " 9  s <- slot(e); if cd in s.versions: return DUPLICATE",
    "        (RETRY if same relay and within window, else SUSPECTED_REPLAY)",
    "10  if e is in a closed gap, a stale epoch or a sequence jump: return QUARANTINE",
    "11  add cd to s.versions; add obs.prev to slot(did, ep, seq - 1).implied",
    "12  if |s.versions U s.implied| = 1: commit raw m under H(m); return ACCEPT",
    "13  mark affected slots CONTESTED, remove them from derived data; return CONFLICT",
]


def alg(m):
    t = m.group(0)
    assert "admission of one received message" in t, "Algorithm 1 changed: update ALG_LINES in export_manuscript.py"
    return ("\n\n\\noindent\\textbf{Algorithm 1.} " + ALG_CAPTION + "\n\n\\begin{verbatim}\n" + "\n".join(ALG_LINES)
            + "\n\\end{verbatim}\n\n")


body = re.sub(r"\\begin\{algorithm\}.*?\\end\{algorithm\}", alg, body, flags=re.S)
body = re.sub(r"\\begin\{Proposition\}\[([^\]]*)\]\\label\{prop:locality\}", r"\\noindent\\textbf{Proposition 1 (\1).} \\emph{", body)
body = body.replace("\\end{Proposition}", "}")
body = body.replace("Proposition~\\ref{prop:locality}", "Proposition 1")
body = body.replace("Algorithm~\\ref{alg:admit}", "Algorithm~1").replace("Algorithm \\ref{alg:admit}", "Algorithm 1")
body = expand_inputs(body)
body = re.sub(r"\\cmidrule(\([a-z]*\))?\{[0-9-]+\}", "", body)
# superscript-only math ($^{*}$, $^{\dagger}$) has no base in OMML and shows a placeholder box: use text superscripts
body = re.sub(r"\$\^\{([^${}]*)\}\$", lambda m: "\\textsuperscript{" + m.group(1).replace("\\dagger", "\u2020").replace("\\ast", "*") + "}", body)
body = body.replace("$\\dagger$", "\u2020")
# numbered citations exactly as in the compiled PDF
aux = (P / "main.aux").read_text()
NUM = {k: int(n) for k, n in re.findall(r"\\bibcite\{([^}]+)\}\{\{(\d+)\}", aux)}


def cite_numbers(keys):
    ns = sorted(NUM[k.strip()] for k in keys.split(","))
    out, i = [], 0
    while i < len(ns):
        j = i
        while j + 1 < len(ns) and ns[j + 1] == ns[j] + 1:
            j += 1
        out.append(f"{ns[i]}\u2013{ns[j]}" if j - i >= 2 else ",".join(str(x) for x in ns[i:j + 1]))
        i = j + 1
    return "[" + ",".join(out) + "]"


def cites(t):
    return re.sub(r"\\cite\{([^}]+)\}", lambda m: cite_numbers(m.group(1)), t)


body = cites(body)
bbl = (P / "main.bbl").read_text()
items = []
for m in re.finditer(r"\\bibitem(?:\[(?:[^\[\]]|\[[^\]]*\])*\])?\{([^}]+)\}(.*?)(?=\\bibitem|\\end\{thebibliography\})", bbl, re.S):
    txt = " ".join(m.group(2).replace("\\newblock", " ").split())
    items.append((NUM[m.group(1)], txt))
items.sort()
assert [n for n, _ in items] == list(range(1, len(items) + 1)), "reference numbering gap"
REFS = "\n\\section*{References}\n\\begin{enumerate}\n" + "\n".join("\\item " + t for _, t in items) + "\n\\end{enumerate}\n"
for k in sorted(macros, key=len, reverse=True):
    body = body.replace("\\" + k + "\\ ", macros[k] + " ").replace("\\" + k, macros[k])
    abstract = abstract.replace("\\" + k + "\\ ", macros[k] + " ").replace("\\" + k, macros[k])
    for lab in back:
        if back[lab]:
            back[lab] = back[lab].replace("\\" + k, macros[k])
# expand the manuscript's own macros (\\sys, \\Sobs, \\Srel, \\pubsub, ...) defined in the preamble
for name, val in re.findall(r"^\\newcommand\{\\(\w+)\}\{(.*)\}\s*(?:%.*)?$", src.split("\\begin{document}")[0], flags=re.M):
    if name.startswith("orcid"):
        continue
    val = val.replace("\\allowbreak{}", "").replace("\\allowbreak", "")
    for t in ("body", "abstract"):
        v = globals()[t]
        v = re.sub(r"\\" + name + r"\\ ", lambda m: val + " ", v)
        v = re.sub(r"\\" + name + r"(?![A-Za-z])", lambda m: val, v)
        globals()[t] = v
    for lab in back:
        if back[lab]:
            back[lab] = re.sub(r"\\" + name + r"(?![A-Za-z])", lambda m: val, back[lab])
body = body.replace("\\sys\\", "PBTI").replace("\\sys", "PBTI").replace("\\Sobs", "\\textsf{obs}").replace("\\Srel", "\\textsf{rel}")
abstract = abstract.replace("\\sys", "PBTI")
body = re.sub(r"\\begin\{tabularx\}\{\\fulllength\}\{([^}]*)\}", lambda m: "\\begin{tabular}{" + m.group(1).replace("X", "l") + "}", body)
body = body.replace("\\end{tabularx}", "\\end{tabular}")
# figures -> PNG
figdir = TMP / "figures"
figdir.mkdir(exist_ok=True)
for pdf in re.findall(r"\\includegraphics\[[^\]]*\]\{figures/([^}]+)\.pdf\}", body):
    if (P / "figures" / f"{pdf}.pdf").exists():
        subprocess.run(["pdftoppm", "-r", "200", "-png", "-singlefile", str(P / "figures" / f"{pdf}.pdf"), str(figdir / pdf)], check=True)
body = re.sub(r"\\includegraphics\[[^\]]*\]\{figures/([^}]+)\.pdf\}", lambda m: "\\includegraphics{" + str(figdir / m.group(1)) + ".png}", body)
front = ("\\documentclass{article}\n\\usepackage{graphicx,booktabs,amsmath}\n\\title{" + title + "}\n"
         "\\author{Rajneesh Shukla\\textsuperscript{1,\u2020,*} and Punit Gupta\\textsuperscript{2,\u2020}\\\\ \\small \\textsuperscript{\u2020}These authors contributed equally to this work [AUTHORS TO CONFIRM]. \\textsuperscript{*}Correspondence: rajneeshshukla@gmail.com\\\\ \\small \\textsuperscript{1,2}[Affiliations: AUTHORS TO COMPLETE]}\n\\begin{document}\n\\maketitle\n"
         "\\section*{Abstract}\n" + abstract + "\n\n\\noindent\\textbf{Keywords:} " + keywords + "\n")
if back.get("Supplementary Materials"):
    back["Supplementary Materials"] = back["Supplementary Materials"].replace("\\linksupplementary{s1}", "www.mdpi.com/xxx/s1")
tail = "".join(f"\n\\noindent\\textbf{{{lab}:}} {cites(txt)}\n" for lab, txt in back.items() if txt)
doc = front + body + tail + REFS + "\\end{document}\n"
# lone signs as math have no operand in OMML (shown as a placeholder by some renderers): use plain characters
doc = doc.replace("\\ensuremath{-}", "\u2212").replace("$+$", "+").replace("$-$", "\u2212")
tex = TMP / "manuscript_export.tex"
tex.write_text(doc)
common = ["pandoc", str(tex), "--from=latex", "--number-sections", f"--resource-path={TMP}"]
subprocess.run(common + ["--to=gfm", "-o", str(OUT / (NAME + ".md")), "--wrap=none"], check=True)
subprocess.run(common + ["--to=docx", "-o", str(OUT / (NAME + ".docx"))], check=True)


def _small_runs(block, half_points=16):
    """give every text run in block an explicit size (appended to its rPr)"""
    sz = f'<w:sz w:val="{half_points}" /><w:szCs w:val="{half_points}" />'
    block = re.sub(r"<w:r>(?!<w:rPr>)", "<w:r><w:rPr>" + sz + "</w:rPr>", block)
    return re.sub(r"<w:rPr>((?:(?!</w:rPr>).)*?)</w:rPr>", lambda m: m.group(0) if "<w:sz " in m.group(1)
                  else "<w:rPr>" + m.group(1) + sz + "</w:rPr>", block, flags=re.S)


def _size_columns(tbl_xml, text_width=9360):
    """fixed column widths proportional to content (min: longest word), so narrow label columns do not wrap mid-word"""
    from lxml import etree as ET
    WNS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    q = lambda t: "{%s}%s" % (WNS, t)
    wrapped = ('<root xmlns:w="%s" xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" '
               'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
               'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
               'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
               'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">' % WNS) + tbl_xml + "</root>"
    root = ET.fromstring(wrapped.encode("utf-8"))
    tbl = root[0]
    grid = tbl.find(q("tblGrid"))
    if grid is None:
        return tbl_xml
    ncol = len(grid)
    need = [4.0] * ncol
    for tr in tbl.findall(q("tr")):
        j = 0
        for tc in tr.findall(q("tc")):
            span = tc.find(q("tcPr") + "/" + q("gridSpan"))
            k = int(span.get(q("val"))) if span is not None else 1
            text = "".join(t.text or "" for t in tc.iter(q("t"), "{http://schemas.openxmlformats.org/officeDocument/2006/math}t"))
            if k == 1 and j < ncol:
                longest = max((len(w) for w in text.split()), default=0)
                need[j] = max(need[j], float(longest) + 1, min(len(text), 34) * 0.9)
            j += k
    total = sum(need)
    widths = [max(500, int(text_width * n / total)) for n in need]
    for gc, wv in zip(grid, widths):
        gc.set(q("w"), str(wv))
    tblPr = tbl.find(q("tblPr"))
    tblW = tblPr.find(q("tblW"))
    if tblW is None:
        tblW = ET.SubElement(tblPr, q("tblW"))
    tblW.set(q("type"), "dxa")
    tblW.set(q("w"), str(sum(widths)))
    if tblPr.find(q("tblLayout")) is None:
        ET.SubElement(tblPr, q("tblLayout")).set(q("type"), "fixed")
    for tr in tbl.findall(q("tr")):
        j = 0
        for tc in tr.findall(q("tc")):
            tcPr = tc.find(q("tcPr"))
            if tcPr is None:
                tcPr = ET.Element(q("tcPr"))
                tc.insert(0, tcPr)
            span = tcPr.find(q("gridSpan"))
            k = int(span.get(q("val"))) if span is not None else 1
            tcW = tcPr.find(q("tcW"))
            if tcW is None:
                tcW = ET.Element(q("tcW"))
                tcPr.insert(0, tcW)
            tcW.set(q("type"), "dxa")
            tcW.set(q("w"), str(sum(widths[j:j + k])))
            j += k
    out = ET.tostring(tbl, encoding="unicode")
    # drop the namespace declarations lxml repeats on the extracted element
    return re.sub(r' xmlns:(w|m|r|wp|a|pic)="[^"]+"', "", out)


def postprocess_docx(path):
    """8-pt text in tables and in the algorithm block so wide tables and code lines fit the page"""
    import zipfile
    with zipfile.ZipFile(path) as z:
        items = [(i, z.read(i.filename)) for i in z.infolist()]
    out = []
    for info, data in items:
        if info.filename == "word/document.xml":
            d = data.decode("utf-8")
            d = re.sub(r"<w:tbl>.*?</w:tbl>", lambda m: _size_columns(_small_runs(m.group(0))), d, flags=re.S)
            d = re.sub(r"<w:p>(?:(?!</w:p>).)*?<w:pStyle w:val=\"SourceCode\" />.*?</w:p>", lambda m: _small_runs(m.group(0)), d, flags=re.S)
            data = d.encode("utf-8")
        out.append((info, data))
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for info, data in out:
            z.writestr(info, data)


postprocess_docx(OUT / (NAME + ".docx"))
subprocess.run(["python3", str(ROOT / "scripts" / "docx_normalize.py"), str(OUT / (NAME + ".docx"))], check=True)
# make figure paths in the Markdown repository-relative
md = (OUT / (NAME + ".md")).read_text().replace(str(figdir), "../../../paper/figures/png")
(OUT / (NAME + ".md")).write_text(
    "> Editing copy generated from `paper/main.tex` by `scripts/export_manuscript_v4.py`. The MDPI LaTeX/PDF is authoritative; "
    "citation numbers and the reference list are taken from the compiled PDF.\n\n" + md)
(P / "figures" / "png").mkdir(exist_ok=True)
for f in figdir.glob("*.png"):
    shutil.copy(f, P / "figures" / "png" / f.name)
print("exported", OUT / (NAME + ".md"), OUT / (NAME + ".docx"))
