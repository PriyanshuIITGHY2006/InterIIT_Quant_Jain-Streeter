# Technical report

`jain_streeter_technical_report.pdf` is the compiled report. The source is `report.tex` (with `quarters.tex` and the figures in `fig/`).

Build with XeLaTeX, run three times so the contents page and long tables settle:

```
xelatex report.tex
xelatex report.tex
xelatex report.tex
```

On Overleaf, set Menu > Compiler to XeLaTeX. The fonts are CMU (cm-unicode), which ship with TeX Live.
