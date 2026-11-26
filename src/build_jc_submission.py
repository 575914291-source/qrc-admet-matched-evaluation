from __future__ import annotations

import shutil
from pathlib import Path

from docx import Document
from docx.enum.text import WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt

from src.config import PROJECT_ROOT


OUTPUT_ROOT = PROJECT_ROOT / "outputs"
SOURCE = OUTPUT_ROOT / "Matched_Evaluation_Fixed_Quantum_Reservoir_TDC_ADMET.docx"
REVISED_SOURCE = (
    OUTPUT_ROOT
    / "Matched_Evaluation_Fixed_Quantum_Reservoir_TDC_ADMET_REVISED.docx"
)
FINAL_SOURCE = OUTPUT_ROOT / "Final_Manuscript_EN.docx"
SOURCE = FINAL_SOURCE if FINAL_SOURCE.exists() else (
    REVISED_SOURCE if REVISED_SOURCE.exists() else SOURCE
)
SUPPLEMENT = OUTPUT_ROOT / "Supplementary_Material_JCAMD.pdf"
SUBMISSION_ROOT = OUTPUT_ROOT / "JCAMD_Submission"
MANUSCRIPT = SUBMISSION_ROOT / "Manuscript.docx"

FIGURES = {
    "Figure_1.pdf": OUTPUT_ROOT / "Figure1_Study_Design.pdf",
    "Figure_2.pdf": OUTPUT_ROOT / "Figure2_Chemical_Space.pdf",
    "Figure_3.pdf": OUTPUT_ROOT / "Figure3_External_Validation.pdf",
    "Figure_4.pdf": OUTPUT_ROOT / "Figure4_Primary_Effects.pdf",
}


def _remove_page_breaks(document: Document) -> None:
    for paragraph in document.paragraphs:
        paragraph.paragraph_format.page_break_before = False
        for page_break in paragraph._p.xpath('.//w:br[@w:type="page"]'):
            page_break.getparent().remove(page_break)


def _remove_table_shading(document: Document) -> None:
    for table in document.tables:
        for cell in table._tbl.xpath(".//w:tc"):
            properties = cell.find(qn("w:tcPr"))
            if properties is None:
                continue
            for shading in list(properties.findall(qn("w:shd"))):
                properties.remove(shading)


def _add_continuous_line_numbers(document: Document) -> None:
    for section in document.sections:
        section_properties = section._sectPr
        line_numbering = section_properties.find(qn("w:lnNumType"))
        if line_numbering is None:
            line_numbering = OxmlElement("w:lnNumType")
            section_properties.append(line_numbering)
        line_numbering.set(qn("w:countBy"), "1")
        line_numbering.set(qn("w:restart"), "continuous")
        line_numbering.set(qn("w:distance"), "360")


def _apply_submission_spacing(document: Document) -> None:
    normal = document.styles["Normal"]
    normal.paragraph_format.line_spacing_rule = WD_LINE_SPACING.DOUBLE
    normal.paragraph_format.space_after = Pt(0)
    normal.paragraph_format.space_before = Pt(0)

    for style_name in ("Heading 1", "Heading 2"):
        style = document.styles[style_name]
        style.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        style.paragraph_format.space_before = Pt(12)
        style.paragraph_format.space_after = Pt(6)

    for style_name in ("Title", "Subtitle"):
        style = document.styles[style_name]
        style.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE

    for paragraph in document.paragraphs:
        if paragraph.style.name in {"Title", "Subtitle", "Heading 1", "Heading 2"}:
            continue
        paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.DOUBLE
        paragraph.paragraph_format.space_before = Pt(0)
        paragraph.paragraph_format.space_after = Pt(0)

    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
                    paragraph.paragraph_format.space_before = Pt(0)
                    paragraph.paragraph_format.space_after = Pt(0)


def _normalize_fonts(document: Document) -> None:
    paragraphs = list(document.paragraphs)
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                paragraphs.extend(cell.paragraphs)
    for section in document.sections:
        paragraphs.extend(section.footer.paragraphs)
        paragraphs.extend(section.header.paragraphs)
    for paragraph in paragraphs:
        for run in paragraph.runs:
            run.font.name = "Times New Roman"
            run_properties = run._element.get_or_add_rPr()
            fonts = run_properties.rFonts
            fonts.set(qn("w:ascii"), "Times New Roman")
            fonts.set(qn("w:hAnsi"), "Times New Roman")
            fonts.set(qn("w:eastAsia"), "Times New Roman")
            fonts.set(qn("w:cs"), "Times New Roman")


def _apply_jc_specific_labels(document: Document) -> None:
    for paragraph in document.paragraphs:
        if paragraph.text.strip() == "Data and Code Availability":
            paragraph.text = "Availability of data and materials"
        elif paragraph.text.startswith(
            "The official TDC archive is available as Harvard Dataverse"
        ):
            paragraph.text = (
                paragraph.text.rstrip()
                + " Additional file 1 contains the supplementary methods, "
                "extended tables, robustness figures, and independent "
                "continuous-regression results."
            )


def _write_cover_letter() -> Path:
    source = PROJECT_ROOT / "COVER_LETTER.md"
    text = source.read_text(encoding="utf-8").strip().splitlines()
    document = Document()
    normal = document.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(11)
    normal.paragraph_format.line_spacing = 1.15
    normal.paragraph_format.space_after = Pt(8)
    for line in text:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("Dear Editor"):
            paragraph = document.add_paragraph()
            run = paragraph.add_run(stripped)
            run.bold = True
        elif stripped.startswith("[Author") or stripped == "Sincerely,":
            document.add_paragraph(stripped)
        else:
            document.add_paragraph(stripped)
    destination = SUBMISSION_ROOT / "Cover_Letter_Draft.docx"
    document.save(destination)
    return destination


def build_submission_package() -> dict[str, object]:
    required = [SOURCE, SUPPLEMENT, *FIGURES.values()]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing submission assets: {missing}")

    SUBMISSION_ROOT.mkdir(parents=True, exist_ok=True)
    document = Document(SOURCE)
    _remove_page_breaks(document)
    _remove_table_shading(document)
    _add_continuous_line_numbers(document)
    _apply_submission_spacing(document)
    _apply_jc_specific_labels(document)
    _normalize_fonts(document)
    document.save(MANUSCRIPT)

    shutil.copy2(SUPPLEMENT, SUBMISSION_ROOT / "Additional_file_1.pdf")
    for name, source in FIGURES.items():
        shutil.copy2(source, SUBMISSION_ROOT / name)
    cover = _write_cover_letter()

    return {
        "manuscript": str(MANUSCRIPT),
        "additional_file": str(SUBMISSION_ROOT / "Additional_file_1.pdf"),
        "figures": {
            name: str(SUBMISSION_ROOT / name) for name in FIGURES
        },
        "cover_letter_draft": str(cover),
        "shaded_cells_after": sum(
            1
            for table in document.tables
            for row in table.rows
            for cell in row.cells
            if cell._tc.xpath("./w:tcPr/w:shd")
        ),
        "line_numbering": bool(
            document.sections[0]._sectPr.xpath("./w:lnNumType")
        ),
    }


if __name__ == "__main__":
    import json

    print(json.dumps(build_submission_package(), indent=2))
