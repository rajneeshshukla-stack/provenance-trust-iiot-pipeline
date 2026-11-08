# Local LaTeX build stub

The official MDPI class (v6.5d, 19 Oct 2026) loads `bbm`, which Debian/Ubuntu ship only in the 1.7 GB
`texlive-fonts-extra` package. The manuscript does not use `\mathbbm`, so the stub `bbm.sty` here is layout-neutral.

Build with the stub (the Makefile does this):

```bash
cd paper && TEXINPUTS=$(cd ../tools/texstubs && pwd)//: latexmk -pdf main.tex
```

Do **not** copy this folder into the journal submission; MDPI compiles with a full TeX Live installation.
`verse.sty` (also required by the class) is in `texlive-humanities`.
