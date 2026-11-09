# HW1 report

- Final English PDF: `../output/pdf/report.pdf` (4 pages).
- Submission copy: `../report.pdf` (automatically synchronized by the builder).
- Editable Word copy: `../report.docx`; export with `python report/build_docx.py`.
- Text/figure export for review: `report.md`.
- PDF content and layout source: `build_report.py`.
- Figure rendering: `prepare_figures.py`; reads saved measurements and trajectories only.
- Input provenance: `sources.json` (SHA-256 hashes).

The PDF includes both phases, interventions, verification plots, the three required
questions, and the optional custom ICP comparison. Historical missing runtimes are
marked NR. The manual capture's missing severe-zone coverage and RANSAC/rerun
differences are explicitly reported. It does not claim a complete map or causal
improvements from single trials.

To revise the PDF, edit the text/layout in `build_report.py` and rebuild.
`report.md` is an exported review copy; editing it does not automatically change
the PDF. The builder regenerates it together with the PDF.

The layout uses black text, unfilled tables with thin black rules, and section
titles without page headers, footers, page numbers, or decorative subtitles.
Figures retain their original colors to distinguish experimental results.

The Word exporter reuses the content in `build_report.py` and creates native
paragraphs, headings and tables, with embedded figure images. Word edits are
independent of the Python/PDF source; export a PDF from Word to retain those edits.
Running the Word exporter again replaces the Word copy.

From hw1, render data figures with the habitat environment:

```bash
MPLCONFIGDIR=/tmp/hw1_report_mpl .pixi/envs/habitat/bin/python report/prepare_figures.py
```

Build with a Python environment containing ReportLab and Pillow:

```bash
python report/build_report.py
```

This task used the bundled PDF runtime. DejaVu fonts are loaded from the system,
with the existing matplotlib font directory as an italic-font fallback.
The builder checks page bounds and uses explicit page breaks. Render the PDF with
Poppler and inspect every page after content/layout changes.

For submission, copy the final PDF as `report.pdf` at the ZIP root. No submission
ZIP was created in this task; do not include experiment diagnostics, capture data
or Replica assets. The handout's required source/ontology/README files must be
packaged separately alongside the PDF.
