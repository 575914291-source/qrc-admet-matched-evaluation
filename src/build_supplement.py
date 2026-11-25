from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
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
TABLE_ROOT = RESULTS_ROOT / "manuscript" / "tables"
DOMAIN_ROOT = RESULTS_ROOT / "domain_audit"
DIAGNOSTIC_ROOT = RESULTS_ROOT / "external_diagnostics"
REPORT_ROOT = RESULTS_ROOT / "report"
REGRESSION_ROOT = RESULTS_ROOT / "external_regression"


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
    font_size: float = 7.4,
) -> None:
    table = document.add_table(rows=len(rows), cols=len(rows[0]))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    for index, width in enumerate(widths):
        table.columns[index].width = Inches(width)
        table._tbl.tblGrid.gridCol_lst[index].set(
            qn("w:w"),
            str(round(width * 1440)),
        )
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
    if text.startswith("Table S") and document.tables:
        paragraph.paragraph_format.keep_with_next = True
        document.tables[-1]._tbl.addprevious(paragraph._p)


def _paragraph(document: Document, text: str) -> None:
    paragraph = document.add_paragraph(text)
    paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    for run in paragraph.runs:
        _set_run_font(run, 10.5)


def _figure(document: Document, path: Path, width: float, alt_text: str) -> None:
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    shape = paragraph.add_run().add_picture(str(path), width=Inches(width))
    shape._inline.docPr.set("descr", alt_text)
    shape._inline.docPr.set("title", alt_text)


def _fmt_rate(value: float) -> str:
    return f"{100 * value:.1f}%"


def _fmt_effect(row, metric: str) -> str:
    value = float(row.effect_better_positive)
    if np.isfinite(row.ci_low) and np.isfinite(row.ci_high):
        interval = f"[{row.ci_low:+.3f}, {row.ci_high:+.3f}]"
    else:
        interval = "point estimate"
    return f"{value:+.4f} {interval}"


def _build_hash_manifest() -> pd.DataFrame:
    paths = [
        ("TDC ADMET archive", PROJECT_ROOT / "data/archives/admet_group_4426004.zip"),
        ("hERG source", PROJECT_ROOT / "data/external/hERG_Dataset.csv"),
        ("B3DB source", PROJECT_ROOT / "data/external/B3DB_classification.tsv"),
        ("MapLight cache metadata", PROJECT_ROOT / "data/cache/maplight_complete.json"),
        ("Official split manifest", PROJECT_ROOT / "data/cache/source_manifest.json"),
        (
            "Chemical-space descriptors",
            TABLE_ROOT / "chemical_space_descriptors.csv",
        ),
        (
            "Chemical-space projection",
            TABLE_ROOT / "chemical_space_projection.csv",
        ),
        ("Endpoint characteristics", TABLE_ROOT / "endpoint_characteristics.csv"),
        ("Analysis hierarchy", TABLE_ROOT / "analysis_hierarchy.csv"),
        ("Prior-study comparison", TABLE_ROOT / "prior_qml_comparison.csv"),
        ("External validation table", TABLE_ROOT / "external_validation_table.csv"),
        (
            "Independent regression table",
            TABLE_ROOT / "external_regression_table.csv",
        ),
        (
            "External diagnostic decomposition",
            DIAGNOSTIC_ROOT / "summary.csv",
        ),
        ("Calibration metrics", DIAGNOSTIC_ROOT / "calibration_metrics.csv"),
        ("TOST sensitivity", REPORT_ROOT / "tost_sensitivity.csv"),
        (
            "Independent hERG regression",
            REGRESSION_ROOT / "comparisons.csv",
        ),
        ("Study-design figure", FIGURE_ROOT / "figure1_design.pdf"),
        ("Chemical-space figure", FIGURE_ROOT / "figure2_chemical_space.pdf"),
        (
            "External-diagnostics figure",
            FIGURE_ROOT / "figure3_external_diagnostics.pdf",
        ),
        (
            "Primary-effect figure",
            FIGURE_ROOT / "figure4_primary_effects.pdf",
        ),
        (
            "Independent-regression figure",
            FIGURE_ROOT / "figureS4_external_regression.pdf",
        ),
    ]
    rows = [
        {
            "asset": name,
            "path": path.relative_to(PROJECT_ROOT).as_posix(),
            "sha256": _sha256(path),
        }
        for name, path in paths
    ]
    frame = pd.DataFrame(rows)
    frame.to_csv(
        OUTPUT_ROOT / "Supplementary_File_Hashes.csv",
        index=False,
        encoding="utf-8-sig",
    )
    return frame


def build_supplement() -> Path:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    endpoint = pd.read_csv(
        TABLE_ROOT / "endpoint_characteristics.csv",
        encoding="utf-8-sig",
    )
    hierarchy = pd.read_csv(
        TABLE_ROOT / "analysis_hierarchy.csv",
        encoding="utf-8-sig",
    )
    prior = pd.read_csv(
        TABLE_ROOT / "prior_qml_comparison.csv",
        encoding="utf-8-sig",
    )
    domain = pd.read_csv(
        DOMAIN_ROOT / "domain_summary.csv",
        encoding="utf-8-sig",
    )
    subgroups = pd.read_csv(
        DOMAIN_ROOT / "model_subgroups.csv",
        encoding="utf-8-sig",
    )
    external = pd.read_csv(
        DIAGNOSTIC_ROOT / "summary.csv",
        encoding="utf-8-sig",
    )
    calibration = pd.read_csv(
        DIAGNOSTIC_ROOT / "calibration_metrics.csv",
        encoding="utf-8-sig",
    )
    tost_summary = pd.read_csv(
        REPORT_ROOT / "tost_sensitivity_summary.csv",
        encoding="utf-8-sig",
    )
    regression = pd.read_csv(
        REGRESSION_ROOT / "comparisons.csv",
        encoding="utf-8-sig",
    )
    hashes = _build_hash_manifest()

    document = Document()
    section = document.sections[0]
    section.top_margin = Inches(0.65)
    section.bottom_margin = Inches(0.65)
    section.left_margin = Inches(0.65)
    section.right_margin = Inches(0.65)

    normal = document.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(10.5)
    normal.paragraph_format.line_spacing = 1.08
    normal.paragraph_format.space_after = Pt(4)
    for style_name, size in (("Heading 1", 14), ("Heading 2", 11.5)):
        style = document.styles[style_name]
        style.font.name = "Times New Roman"
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.paragraph_format.space_before = Pt(9)
        style.paragraph_format.space_after = Pt(4)

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
        "This supplement contains endpoint composition, analysis hierarchy, "
        "prior-study comparison, chemical-space audits, external effect decomposition "
        "and calibration, multiplicity sensitivity, independent continuous regression, "
        "data provenance, and reproduction assets. It uses the same locked predictions "
        "and does not introduce label-based model selection.",
    )
    _paragraph(
        document,
        "Code repository: https://github.com/575914291-source/"
        "qrc-admet-matched-evaluation. Frozen submission release: "
        "https://github.com/575914291-source/"
        "qrc-admet-matched-evaluation/releases/tag/v1.1.0.",
    )

    document.add_heading("S1 Endpoint composition and analysis hierarchy", level=1)
    endpoint_rows = [["Endpoint", "Type", "Metric", "TV n", "Test n", "TV label", "Test label"]]
    for row in endpoint.itertuples(index=False):
        endpoint_rows.append(
            [
                row.endpoint,
                "Class." if row.task_type == "classification" else "Regr.",
                row.metric,
                f"{row.n_train_valid:,}",
                f"{row.n_test:,}",
                row.train_valid_label_summary,
                row.test_label_summary,
            ]
        )
    _add_table(
        document,
        endpoint_rows,
        [1.35, 0.55, 0.55, 0.60, 0.60, 1.55, 1.55],
        font_size=6.9,
    )
    _caption(
        document,
        "Table S1. Endpoint sample counts, official metrics, and label summaries. "
        "TV denotes the official TDC training/validation archive before the five "
        "scaffold re-splits.",
    )

    hierarchy_rows = [["Tier", "Question", "Scope", "Inference"]]
    for row in hierarchy.itertuples(index=False):
        hierarchy_rows.append(
            [
                row.analysis_tier,
                row.question,
                row.scope,
                row.inference,
            ]
        )
    _add_table(
        document,
        hierarchy_rows,
        [1.0, 2.05, 1.55, 2.4],
        font_size=7.1,
    )
    _caption(
        document,
        "Table S2. Analysis hierarchy. Primary, secondary, sensitivity, external, and "
        "exploratory analyses are separated so that multiplicity is not inferred across "
        "an undefined set of comparisons.",
    )

    hash_rows = [["Asset", "Path", "SHA-256 (short)"]]
    for row in hashes.itertuples(index=False):
        value = row.sha256
        hash_rows.append(
            [
                row.asset,
                row.path,
                f"{value[:12]}...{value[-12:]}",
            ]
        )
    _add_table(
        document,
        hash_rows,
        [1.8, 2.7, 2.2],
        font_size=6.8,
    )
    _caption(
        document,
        "Table S3. Data and analysis asset hashes. Full SHA-256 values are in "
        "Supplementary_File_Hashes.csv.",
    )

    document.add_heading("S2 Relation to prior QML-ADMET studies", level=1)
    _paragraph(
        document,
        "The studies below differ in molecular task, quantum or hybrid feature family, "
        "learning protocol, controls, and external validation. The table therefore "
        "positions the present benchmark and does not claim numerical equivalence across "
        "architectures.",
    )
    prior_rows = [["Study", "Setting", "Quantum/hybrid component", "Reported focus", "Relation to this study"]]
    for row in prior.itertuples(index=False):
        prior_rows.append(
            [
                row.study,
                row.molecular_setting,
                row.quantum_or_hybrid_component,
                row.reporting_focus,
                row.relation_to_present_work,
            ]
        )
    _add_table(
        document,
        prior_rows,
        [1.05, 1.2, 1.35, 1.7, 1.7],
        font_size=6.7,
    )
    _caption(
        document,
        "Table S4. Prior QML molecular-prediction studies and their relation to the "
        "present matched evaluation.",
    )

    document.add_heading("S3 Chemical-space and source audit", level=1)
    _paragraph(
        document,
        "Figure 2 in the main manuscript shows Morgan fingerprint projection and "
        "molecular-weight, cLogP, and TPSA distributions. TDC contains 43,203 unique "
        "molecules in this descriptor audit; hERG contributes 293 and B3DB contributes "
        "2,317. The projection randomly uses 3,000 unique TDC molecules, 500 B3DB "
        "molecules, and all 293 hERG molecules.",
    )
    chemical_rows = [["Cohort", "N", "Positives", "TDC positives", "Shared TV scaffolds", "NN median", "NN q90"]]
    labels = {"herg": "hERG", "bbb_martins": "B3DB BBB"}
    for row in domain.itertuples(index=False):
        chemical_rows.append(
            [
                labels[row.task],
                f"{row.n_external:,}",
                _fmt_rate(row.positive_rate),
                _fmt_rate(row.tdc_positive_rate_all),
                f"{row.n_scaffold_overlap_tdc_trainval} "
                f"({row.pct_scaffold_overlap_tdc_trainval:.1f}%)",
                f"{row.nearest_tanimoto_median:.3f}",
                f"{row.nearest_tanimoto_q90:.3f}",
            ]
        )
    _add_table(
        document,
        chemical_rows,
        [0.9, 0.55, 0.65, 0.8, 1.35, 0.75, 0.75],
        font_size=7.2,
    )
    _caption(
        document,
        "Table S5. Chemical-source audit. Exact canonical identities were removed before "
        "evaluation. Similarity uses Morgan radius-2 2048-bit Tanimoto values against "
        "the same endpoint's TDC train/validation molecules.",
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
    subgroup_rows = [["Stratum", "N (+)", "Base", "QRC", "Orth.", "QRC - orth. [range]", "Seeds +"]]
    for row in selected.itertuples(index=False):
        subgroup_rows.append(
            [
                subgroup_labels[row.subgroup],
                f"{row.n} ({row.n_positive})",
                f"{row.base_mean_auroc:.3f}",
                f"{row.qrc_gated_mean_auroc:.3f}",
                f"{row.orth_gated_mean_auroc:.3f}",
                f"{row.qrc_minus_orth_mean:+.4f} "
                f"[{row.qrc_minus_orth_min:+.4f}, {row.qrc_minus_orth_max:+.4f}]",
                f"{row.positive_splits}/{row.defined_splits}",
            ]
        )
    _add_table(
        document,
        subgroup_rows,
        [1.3, 0.75, 0.7, 0.7, 0.7, 1.8, 0.65],
        font_size=7.2,
    )
    _caption(
        document,
        "Table S6. Exploratory hERG CatBoost stratification. The positive overall "
        "CatBoost effect is not concentrated in molecules with a shared TDC "
        "train/validation scaffold.",
    )

    document.add_heading("S4 External classification diagnostics", level=1)
    external_rows = [["Cohort", "Base", "Contrast", "Metric", "Effect [95% CI]", "Seeds +"]]
    for row in external.itertuples(index=False):
        if row.metric == "AUROC":
            keep = True
        elif row.method == "qrc_gated" and row.reference == "orthogonal_gated":
            keep = True
        else:
            keep = False
        if not keep:
            continue
        cohort = "hERG" if row.task == "herg" else "B3DB"
        contrast = {
            ("qrc_gated", "base"): "QRC - base",
            ("orthogonal_gated", "base"): "Orth. - base",
            ("qrc_gated", "orthogonal_gated"): "QRC - orth.",
        }[(row.method, row.reference)]
        external_rows.append(
            [
                cohort,
                "ET" if row.base == "extra_trees" else "CB",
                contrast,
                row.metric,
                _fmt_effect(row, row.metric),
                f"{row.positive_seeds}/5",
            ]
        )
    _add_table(
        document,
        external_rows,
        [0.7, 0.45, 0.95, 0.75, 2.45, 0.65],
        font_size=6.9,
    )
    _caption(
        document,
        "Table S7. External AUROC decomposition and QRC-versus-orthogonal AUPRC, Brier, "
        "and log-loss diagnostics. For AUROC/AUPRC, positive values favour the first "
        "method; for Brier/log loss, positive values indicate lower error for the first "
        "method. Confidence intervals are shown for AUROC/AUPRC.",
    )

    document.add_page_break()
    calibration_rows = [["Cohort", "Base", "Method", "Mean p", "Observed", "AUROC", "AUPRC", "Brier", "Slope", "Intercept"]]
    for row in calibration.itertuples(index=False):
        calibration_rows.append(
            [
                "hERG" if row.task == "herg" else "B3DB",
                "ET" if row.base == "extra_trees" else "CB",
                "QRC" if row.method == "qrc_gated" else "Orth.",
                f"{row.mean_prediction:.3f}",
                f"{row.observed_rate:.3f}",
                f"{row.auroc:.3f}",
                f"{row.auprc:.3f}",
                f"{row.brier:.3f}",
                f"{row.calibration_slope:.3f}",
                f"{row.calibration_intercept:.3f}",
            ]
        )
    _add_table(
        document,
        calibration_rows,
        [0.6, 0.4, 0.5, 0.55, 0.65, 0.55, 0.55, 0.55, 0.55, 0.7],
        font_size=6.8,
    )
    _caption(
        document,
        "Table S8. Calibration and discrimination metrics based on the five-seed mean "
        "probability. Calibration slope and intercept come from logistic recalibration "
        "of the mean prediction and are descriptive, not model-selection criteria.",
    )

    document.add_heading("S5 Robustness figures and multiplicity sensitivity", level=1)
    _figure(
        document,
        FIGURE_ROOT / "low_data_counts.png",
        5.7,
        "Supplementary Figure S1. Low-data direction counts for gated QRC and the matching orthogonal branch.",
    )
    _caption(
        document,
        "Figure S1. Low-data direction counts for gated QRC versus the matching gated "
        "orthogonal branch across eight representative endpoints.",
    )
    _figure(
        document,
        FIGURE_ROOT / "external_validation_effects.png",
        5.7,
        "Supplementary Figure S2. External endpoint AUROC intervals for gated QRC versus gated orthogonal features.",
    )
    _caption(
        document,
        "Figure S2. Full external endpoint AUROC intervals and Holm-adjusted "
        "permutation tests for gated QRC versus the matched gated orthogonal branch.",
    )
    _figure(
        document,
        FIGURE_ROOT / "noise_counts.png",
        5.5,
        "Supplementary Figure S3. Simulated depolarizing-noise direction counts.",
    )
    _caption(
        document,
        "Figure S3. Simulated depolarizing-noise sensitivity at 4,096 shots across "
        "eight representative endpoints.",
    )

    tost_rows = [["Base", "Margin", "Equivalent endpoints / 22"]]
    for row in tost_summary.itertuples(index=False):
        tost_rows.append(
            [
                "ExtraTrees" if row.base == "extra_trees" else "CatBoost",
                row.margin_label,
                f"{row.equivalent_endpoints}/{row.endpoints}",
            ]
        )
    _add_table(
        document,
        tost_rows,
        [1.3, 1.1, 2.0],
        font_size=8.0,
    )
    _caption(
        document,
        "Table S9. TOST sensitivity for the ungated QRC-versus-orthogonal primary "
        "comparison. Absolute margins are 0.005, 0.01, and 0.02 for AUROC/AUPRC/"
        "Spearman; MAE margins are 1%, 2%, and 4% of the base MAE. Counts are after "
        "Holm correction across the 22 endpoints within each base and margin.",
    )

    document.add_heading("S6 Independent continuous pIC50 regression", level=1)
    _paragraph(
        document,
        "The external ToxTree hERG Dev-set was split by Bemis-Murcko scaffold into 6,895 "
        "training and 985 validation molecules after removal of TDC overlaps. The source "
        "Test-set was filtered against both TDC and external Dev-set scaffolds, leaving "
        "214 molecules in 155 scaffolds. Five model seeds were fitted for each classical "
        "base with the TDC feature, PCA, residual-head, and gating settings held fixed.",
    )
    regression_rows = [["Base", "Metric", "Contrast", "Effect [95% CI]", "Raw p", "Holm p", "Seeds +"]]
    for row in regression.itertuples(index=False):
        if row.method != "qrc":
            continue
        contrast = (
            "QRC - orth."
            if row.reference == "real_orthogonal"
            else "QRC - base"
            if row.reference == "base"
            else "QRC - Fourier"
        )
        regression_rows.append(
            [
                "ExtraTrees" if row.base == "extra_trees" else "CatBoost",
                row.metric,
                contrast,
                f"{row.effect_better_positive:+.4f} "
                f"[{row.ci_low:+.4f}, {row.ci_high:+.4f}]",
                f"{row.permutation_p:.3f}",
                f"{row.holm_p:.3f}",
                f"{row.positive_seeds}/5",
            ]
        )
    _add_table(
        document,
        regression_rows,
        [0.8, 0.65, 1.0, 1.75, 0.55, 0.55, 0.55],
        font_size=7.2,
    )
    _caption(
        document,
        "Table S10. Independent ToxTree hERG pIC50 regression. Spearman and MAE effects "
        "are direction-normalized so positive values favour QRC; Holm correction spans "
        "all 12 metric, base, and contrast tests.",
    )
    _figure(
        document,
        FIGURE_ROOT / "figureS4_external_regression.png",
        6.2,
        "Supplementary Figure S4. Independent hERG pIC50 regression effects with scaffold-bootstrap intervals.",
    )
    _caption(
        document,
        "Figure S4. Independent ToxTree hERG pIC50 regression effects for QRC versus "
        "the matched orthogonal and residual-free base branches.",
    )

    document.add_heading("S7 Release inventory and reproduction", level=1)
    inventory_rows = [
        ["Artefact", "Unit", "Count"],
        ["Primary endpoint runs", "base x endpoint x split", "220"],
        ["Finite-shot files", "result files", "80"],
        ["Finite-shot results", "shot settings", "240"],
        ["Low-data files", "result files", "80"],
        ["Low-data fractions", "fraction results", "400"],
        ["External classification runs", "base x cohort x split", "20"],
        ["Noise files", "result files", "80"],
        ["Noise results", "noise settings", "240"],
        ["Bounded-family search runs", "result files", "80"],
        ["Independent regression runs", "base x model seed", "10"],
        ["Primary report rows", "metrics_by_seed.csv", "1,760"],
    ]
    _add_table(
        document,
        inventory_rows,
        [2.55, 2.15, 0.95],
        font_size=8.2,
    )
    _caption(
        document,
        "Table S11. Released result inventory. Full split-level records are supplied as "
        "CSV or NPZ files in the GitHub release and submission archive.",
    )
    commands = [
        "python -m unittest discover -s tests -v",
        "python -m src.audit_runs",
        "python -m src.audit_finite_shot",
        "python -m src.audit_low_data",
        "python -m src.audit_external",
        "python -m src.analyze_continuous_transfer",
        "python -m src.audit_noise",
        "python -m src.audit_tuned_qrc",
        "python -m src.domain_audit",
        "python -m src.analyze_chemical_space",
        "python -m src.analyze_external_diagnostics",
        "python -m src.analyze_tost_sensitivity",
        "python -m src.report_external_regression",
        "python -m src.audit_external_regression",
        "python -m src.build_extended_tables",
        "python -m src.build_extended_figures",
    ]
    for command in commands:
        paragraph = document.add_paragraph()
        paragraph.paragraph_format.left_indent = Inches(0.15)
        paragraph.paragraph_format.space_after = Pt(0)
        run = paragraph.add_run(command)
        run.font.name = "Consolas"
        run.font.size = Pt(8.0)
    _paragraph(
        document,
        "The dense 473 MB MapLight feature cache is excluded from Git and can be "
        "rebuilt with python -m src.build_features --workers 4. Exact simulation is a "
        "controlled design choice; finite-shot and depolarizing analyses are not "
        "physical-hardware validation.",
    )

    document.save(OUTPUT)
    print(OUTPUT)
    return OUTPUT


if __name__ == "__main__":
    build_supplement()
