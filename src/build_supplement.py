from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

from src.config import PROJECT_ROOT, RESULTS_ROOT


OUTPUT_ROOT = PROJECT_ROOT / "outputs"
OUTPUT = OUTPUT_ROOT / "Supplementary_Material_JCAMD.docx"
FIGURE_ROOT = RESULTS_ROOT / "manuscript" / "figures"
DOMAIN_ROOT = RESULTS_ROOT / "domain_audit"
REPORT_ROOT = RESULTS_ROOT / "report"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _set_run_font(run, size: float, bold: bool = False) -> None:
    run.font.name = "Times New Roman"
    run.font.size = Pt(size)
    run.bold = bold
    run.font.color.rgb = RGBColor(0, 0, 0)
    run._element.get_or_add_rPr().rFonts.set(
        qn("w:eastAsia"),
        "Times New Roman",
    )


def _shade(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shading = tc_pr.find(qn("w:shd"))
    if shading is None:
        shading = OxmlElement("w:shd")
        tc_pr.append(shading)
    shading.set(qn("w:fill"), fill)


def _set_cell_border(cell, color: str = "D9D9D9", size: str = "4") -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = tc_pr.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = f"w:{edge}"
        element = borders.find(qn(tag))
        if element is None:
            element = OxmlElement(tag)
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), size)
        element.set(qn("w:color"), color)


def _repeat_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    if tr_pr.find(qn("w:tblHeader")) is None:
        tr_pr.append(OxmlElement("w:tblHeader"))


def _no_split(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    if tr_pr.find(qn("w:cantSplit")) is None:
        tr_pr.append(OxmlElement("w:cantSplit"))


def _add_table(
    document: Document,
    rows: list[list[str]],
    widths: list[float],
    font_size: float = 8.0,
) -> None:
    table = document.add_table(rows=len(rows), cols=len(rows[0]))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    for index, width in enumerate(widths):
        table.columns[index].width = Inches(width)
        grid_column = table._tbl.tblGrid.gridCol_lst[index]
        grid_column.set(qn("w:w"), str(round(width * 1440)))
    for row_index, values in enumerate(rows):
        row = table.rows[row_index]
        _no_split(row)
        for column_index, value in enumerate(values):
            cell = row.cells[column_index]
            cell.width = Inches(widths[column_index])
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            cell.text = ""
            paragraph = cell.paragraphs[0]
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = paragraph.add_run(str(value))
            _set_run_font(run, font_size, bold=row_index == 0)
            _set_cell_border(cell)
            if row_index == 0:
                _shade(cell, "D9E2F3")
            elif row_index % 2 == 0:
                _shade(cell, "F5F7FA")
    _repeat_header(table.rows[0])


def _caption(document: Document, text: str) -> None:
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    paragraph.paragraph_format.space_before = Pt(4)
    paragraph.paragraph_format.space_after = Pt(8)
    run = paragraph.add_run(text)
    _set_run_font(run, 8.5, bold=True)


def _paragraph(document: Document, text: str) -> None:
    paragraph = document.add_paragraph(text)
    paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    for run in paragraph.runs:
        _set_run_font(run, 10.5)


def _figure(document: Document, path: Path, width: float = 6.6) -> None:
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run()
    run.add_picture(str(path), width=Inches(width))


def _fmt_rate(value: float) -> str:
    return f"{100 * value:.1f}%"


def build_supplement() -> Path:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    summary = pd.read_csv(DOMAIN_ROOT / "domain_summary.csv", encoding="utf-8-sig")
    subgroups = pd.read_csv(
        DOMAIN_ROOT / "model_subgroups.csv",
        encoding="utf-8-sig",
    )
    metrics_rows = len(
        pd.read_csv(REPORT_ROOT / "metrics_by_seed.csv", encoding="utf-8-sig")
    )

    document = Document()
    section = document.sections[0]
    section.top_margin = Inches(0.7)
    section.bottom_margin = Inches(0.7)
    section.left_margin = Inches(0.75)
    section.right_margin = Inches(0.75)

    normal = document.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(10.5)
    normal.paragraph_format.line_spacing = 1.12
    normal.paragraph_format.space_after = Pt(5)
    for style_name, size in (("Heading 1", 14), ("Heading 2", 12)):
        style = document.styles[style_name]
        style.font.name = "Times New Roman"
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.paragraph_format.space_before = Pt(10)
        style.paragraph_format.space_after = Pt(5)

    title = document.add_paragraph(style="Title")
    title.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = title.add_run("Supplementary Material")
    _set_run_font(run, 20, bold=True)
    subtitle = document.add_paragraph()
    run = subtitle.add_run(
        "Matched evaluation of fixed quantum reservoir residuals on TDC ADMET"
    )
    _set_run_font(run, 12)

    _paragraph(
        document,
        "This supplement documents data provenance, reproduction assets, "
        "chemical-space audits, sensitivity analyses, and the interpretation of "
        "equivalence tests for the associated manuscript. It does not introduce "
        "new model-selection decisions or additional training experiments.",
    )

    document.add_heading("S1 Data and environment", level=1)
    _paragraph(
        document,
        "All primary models use the official TDC ADMET archive. The competition-"
        "cleaned table is not used as a source of labels or evaluation rows. "
        "External cohorts are deduplicated after canonical non-isomeric SMILES "
        "normalization and exact identities present in the corresponding TDC "
        "archive are removed before evaluation.",
    )
    paths = {
        "TDC ADMET archive": (
            PROJECT_ROOT / "data" / "archives" / "admet_group_4426004.zip"
        ),
        "hERG source": PROJECT_ROOT / "data" / "external" / "hERG_Dataset.csv",
        "B3DB source": (
            PROJECT_ROOT / "data" / "external" / "B3DB_classification.tsv"
        ),
        "Corrected MapLight cache metadata": (
            PROJECT_ROOT / "data" / "cache" / "maplight_complete.json"
        ),
        "Official split index": (
            PROJECT_ROOT / "data" / "cache" / "source_manifest.json"
        ),
    }
    data_rows = [["Asset", "Records / role", "SHA-256 (short)"]]
    roles = {
        "TDC ADMET archive": "22 official endpoints",
        "hERG source": "External hERG test",
        "B3DB source": "External BBB cohort",
        "Corrected MapLight cache metadata": "Feature provenance",
        "Official split index": "Split manifest",
    }
    hash_rows = []
    for name, path in paths.items():
        full_hash = _sha256(path)
        hash_rows.append(
            {
                "asset": name,
                "path": path.relative_to(PROJECT_ROOT).as_posix(),
                "sha256": full_hash,
            }
        )
        data_rows.append(
            [
                name,
                roles[name],
                f"{full_hash[:12]}...{full_hash[-12:]}",
            ]
        )
    pd.DataFrame(hash_rows).to_csv(
        OUTPUT_ROOT / "Supplementary_File_Hashes.csv",
        index=False,
        encoding="utf-8-sig",
    )
    _add_table(document, data_rows, [2.6, 1.9, 2.3], font_size=7.5)
    _caption(
        document,
        "Table S1. Data and feature-cache provenance used for the released "
        "evaluation. Full SHA-256 values are provided in "
        "Supplementary_File_Hashes.csv and in the source metadata.",
    )

    document.add_heading("S2 Chemical-space and source audit", level=1)
    _paragraph(
        document,
        "The audit asks whether the external hERG and B3DB cohorts differ from "
        "their corresponding TDC sources in exact identity, Bemis-Murcko scaffold "
        "overlap, nearest-neighbour similarity, and label prevalence. These are "
        "descriptive diagnostics; they do not identify a causal chemical mechanism.",
    )
    chem_rows = [[
        "Cohort",
        "N",
        "Positives",
        "TDC positives",
        "Shared train/validation scaffolds",
        "NN Tanimoto median",
        "NN Tanimoto q90",
    ]]
    labels = {"herg": "hERG", "bbb_martins": "B3DB BBB"}
    for row in summary.itertuples(index=False):
        chem_rows.append(
            [
                labels[row.task],
                f"{int(row.n_external):,}",
                _fmt_rate(row.positive_rate),
                _fmt_rate(row.tdc_positive_rate_all),
                f"{int(row.n_scaffold_overlap_tdc_trainval)} "
                f"({row.pct_scaffold_overlap_tdc_trainval:.1f}%)",
                f"{row.nearest_tanimoto_median:.3f}",
                f"{row.nearest_tanimoto_q90:.3f}",
            ]
        )
    _add_table(document, chem_rows, [1.0, 0.55, 0.75, 0.85, 1.45, 1.05, 1.05])
    _caption(
        document,
        "Table S2. External-cohort source-proximity audit. No exact canonical "
        "identities remained. Morgan radius-2 2048-bit Tanimoto similarities were "
        "calculated against the TDC train/validation molecules for the same endpoint.",
    )

    selected = subgroups[
        (subgroups.task == "herg")
        & (subgroups.base == "catboost")
        & subgroups.subgroup.isin(
            [
                "all",
                "shared_scaffold",
                "novel_scaffold",
                "nearest_similarity_top_quartile",
                "nearest_similarity_lower_three_quartiles",
            ]
        )
    ].copy()
    subgroup_labels = {
        "all": "All",
        "shared_scaffold": "Shared scaffold",
        "novel_scaffold": "Novel scaffold",
        "nearest_similarity_top_quartile": "NN top quartile",
        "nearest_similarity_lower_three_quartiles": "NN lower 3 quartiles",
    }
    subgroup_rows = [[
        "Chemical stratum",
        "N (positive)",
        "Base AUROC",
        "Gated QRC",
        "Gated orth.",
        "QRC - orth. [seed range]",
        "Positive seeds",
    ]]
    for row in selected.itertuples(index=False):
        subgroup_rows.append(
            [
                subgroup_labels[row.subgroup],
                f"{int(row.n)} ({int(row.n_positive)})",
                f"{row.base_mean_auroc:.3f}",
                f"{row.qrc_gated_mean_auroc:.3f}",
                f"{row.orth_gated_mean_auroc:.3f}",
                f"{row.qrc_minus_orth_mean:+.4f} "
                f"[{row.qrc_minus_orth_min:+.4f}, "
                f"{row.qrc_minus_orth_max:+.4f}]",
                f"{int(row.positive_splits)}/{int(row.defined_splits)}",
            ]
        )
    _add_table(document, subgroup_rows, [1.2, 0.9, 0.85, 0.85, 0.9, 1.65, 0.8])
    _caption(
        document,
        "Table S3. Exploratory hERG CatBoost stratification of the already fitted "
        "external predictions. The positive overall point estimate is not concentrated "
        "in molecules with a shared TDC train/validation scaffold. Stratification is "
        "descriptive and was not used for model selection.",
    )
    _paragraph(
        document,
        "The corresponding BBB audit is negative across shared-scaffold, novel-"
        "scaffold, and similarity strata. Because hERG is not enriched for shared "
        "scaffolds yet has a positive CatBoost effect, and B3DB has more overlap yet "
        "a negative effect, the current data do not support a simple scaffold-overlap "
        "explanation. Assay context, endpoint construction, label prevalence, source "
        "batch, and other distribution shifts remain plausible contributors and "
        "cannot be separated by the existing pairs of external cohorts.",
    )

    document.add_heading("S3 Supplementary figures", level=1)
    _figure(document, FIGURE_ROOT / "low_data_counts.png", 6.45)
    _caption(
        document,
        "Figure S1. Low-data direction counts for gated QRC versus the matching "
        "gated orthogonal branch across eight representative endpoints.",
    )
    _figure(document, FIGURE_ROOT / "external_validation_effects.png", 6.45)
    _caption(
        document,
        "Figure S2. External hERG and B3DB BBB effects with paired scaffold-"
        "bootstrap 95% intervals and Holm-adjusted permutation p values.",
    )
    _figure(document, FIGURE_ROOT / "noise_counts.png", 6.45)
    _caption(
        document,
        "Figure S3. Simulated depolarizing-noise sensitivity for the eight "
        "representative endpoints.",
    )

    document.add_heading("S4 Release inventory and statistical interpretation", level=1)
    _paragraph(
        document,
        "The machine-readable release contains every split-level prediction and "
        "metric table. The primary result directory includes metrics_by_seed.csv, "
        "comparisons.csv, gate_weights.csv, map sensitivity, equivalence results, "
        "and report_manifest.json. External results include summary.csv and "
        "effects_by_seed.csv. Domain_audit contains the per-molecule overlap and "
        "similarity table plus model_subgroups.csv. The versioned repository is "
        "https://github.com/575914291-source/qrc-admet-matched-evaluation.",
    )
    inventory = [
        ["Artefact", "Unit", "Count"],
        ["Primary endpoint runs", "base x endpoint x split", "220"],
        ["Finite-shot files", "result files", "80"],
        ["Finite-shot results", "shot settings", "240"],
        ["Low-data files", "result files", "80"],
        ["Low-data fractions", "fraction results", "400"],
        ["External validation runs", "base x cohort x split", "20"],
        ["Noise files", "result files", "80"],
        ["Noise results", "noise settings", "240"],
        ["Bounded-family search runs", "result files", "80"],
        ["Primary report rows", "metrics_by_seed.csv", f"{metrics_rows:,}"],
    ]
    _add_table(document, inventory, [3.0, 2.2, 1.1], font_size=8.5)
    _caption(
        document,
        "Table S4. Released result inventory. Full records are supplied as CSV or "
        "NPZ files in the reproduction repository and the submission archive.",
    )
    _paragraph(
        document,
        "Significance, equivalence, and unresolved outcomes are reported as three "
        "separate states. A Holm-significant negative effect indicates significantly "
        "lower performance; a Holm-significant positive effect indicates significant "
        "improvement; a significant TOST result indicates practical equivalence within "
        "the prespecified benchmark margin. Equivalence is not evidence of identical "
        "mechanisms or molecule-level predictions. All margins are benchmark "
        "interpretation thresholds, not clinical or regulatory limits.",
    )

    document.add_heading("S5 Reproduction commands and verification", level=1)
    commands = [
        "python -m unittest discover -s tests -v",
        "python -m src.audit_runs",
        "python -m src.audit_finite_shot",
        "python -m src.audit_low_data",
        "python -m src.audit_external",
        "python -m src.audit_noise",
        "python -m src.audit_tuned_qrc",
        "python -m src.domain_audit",
    ]
    for command in commands:
        paragraph = document.add_paragraph()
        paragraph.paragraph_format.left_indent = Inches(0.2)
        paragraph.paragraph_format.space_after = Pt(1)
        run = paragraph.add_run(command)
        run.font.name = "Consolas"
        run.font.size = Pt(8.5)
    _paragraph(
        document,
        "The dense 473 MB MapLight feature cache is not distributed through Git. "
        "It can be rebuilt with python -m src.build_features --workers 4. The "
        "released split-level predictions allow all reported scores and audits to "
        "be checked without retraining.",
    )
    _paragraph(
        document,
        "Exact state-vector simulation is a controlled experimental choice. It "
        "separates the function class of the fixed circuit and readout from physical "
        "hardware error. Finite-shot and depolarizing analyses are sensitivity tests "
        "and are not claims of hardware execution.",
    )

    document.save(OUTPUT)
    print(OUTPUT)
    return OUTPUT


if __name__ == "__main__":
    build_supplement()
