# Figure index

All main figures are embedded in the manuscript and copied to `outputs/` as
standalone vector PDFs.

| Figure | Topic | Source script | Standalone PDF |
|---|---|---|---|
| Figure 1 | Matched evaluation design | `src/build_design_figure.py` | `outputs/Figure1_Study_Design.pdf` |
| Figure 2 | Chemical space and physicochemical context | `src/analyze_chemical_space.py`, `src/build_extended_figures.py` | `outputs/Figure2_Chemical_Space.pdf` |
| Figure 3 | External effect decomposition and calibration | `src/analyze_external_diagnostics.py`, `src/build_extended_figures.py` | `outputs/Figure3_External_Validation.pdf` |
| Figure 4 | Endpoint-level primary effects | `src/make_manuscript_assets.py` | `outputs/Figure4_Primary_Effects.pdf` |
| Figure S4 | Independent hERG pIC50 regression | `src/report_external_regression.py`, `src/build_extended_figures.py` | `outputs/Supplementary_FigureS4_External_Regression.pdf` |

Alt text is stored in the inline shapes of the DOCX manuscripts. Figure 1 was
initially laid out with the `academic-figures` workflow from Scientific Agent
Skills and is regenerated locally by the script above.
