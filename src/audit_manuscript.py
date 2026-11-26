from __future__ import annotations

import json
import re
from pathlib import Path

from docx import Document

from src.config import PROJECT_ROOT


OUTPUT_ROOT = PROJECT_ROOT / "outputs"
ORIGINAL = (
    OUTPUT_ROOT
    / "Matched_Evaluation_Fixed_Quantum_Reservoir_TDC_ADMET.docx"
)
REVISED = (
    OUTPUT_ROOT
    / "Matched_Evaluation_Fixed_Quantum_Reservoir_TDC_ADMET_REVISED.docx"
)
FINAL = OUTPUT_ROOT / "Final_Manuscript_EN.docx"
MANUSCRIPT = FINAL if FINAL.exists() else (
    REVISED if REVISED.exists() else ORIGINAL
)
SUPPLEMENT = OUTPUT_ROOT / "Supplementary_Material_JCAMD.docx"


def _all_text(document: Document) -> str:
    blocks = [paragraph.text for paragraph in document.paragraphs]
    for table in document.tables:
        blocks.extend(cell.text for row in table.rows for cell in row.cells)
    return "\n".join(blocks)


def _citation_numbers(text: str) -> set[int]:
    values: set[int] = set()
    for group in re.findall(r"\[([0-9,\s\-]+)\]", text):
        for token in re.split(r",\s*", group):
            token = token.strip()
            if not token:
                continue
            if "-" in token:
                low, high = (int(value) for value in token.split("-", 1))
                values.update(range(low, high + 1))
            else:
                values.add(int(token))
    return values


def audit_manuscript() -> dict[str, object]:
    document = Document(MANUSCRIPT)
    supplement = Document(SUPPLEMENT)
    main_text = _all_text(document)
    english_text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    abstract_words = len(document.paragraphs[3].text.split())
    citation_numbers = _citation_numbers(english_text)
    reference_numbers = {
        int(match.group(1))
        for paragraph in document.paragraphs
        if (match := re.match(r"^(\d+)\.\s", paragraph.text.strip()))
    }
    missing_references = sorted(citation_numbers - reference_numbers)
    uncited_references = sorted(reference_numbers - citation_numbers)
    captions = [paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()]
    figure_captions = {
        number: any(
            text.startswith(f"Figure {number}.")
            for text in captions
        )
        for number in range(1, 5)
    }
    table_captions = {
        number: any(
            text.startswith(f"Table {number}.")
            for text in captions
        )
        for number in range(1, 7)
    }
    image_alts = [
        shape._inline.docPr.get("descr", "").strip()
        for shape in document.inline_shapes
    ]
    banned_phrases = (
        "QRC performs worse",
        "QRC is inferior",
        "negative result",
        "quantum hardware validation",
    )
    placeholders = re.findall(r"\b(?:TODO|TBD|XXXX+|PLACEHOLDER)\b", main_text)
    failures = []
    if re.search(r"[\u3400-\u9fff]", english_text):
        failures.append("English manuscript contains CJK text")
    if not 180 <= abstract_words <= 250:
        failures.append(f"Abstract has {abstract_words} words")
    if len(document.tables) != 6:
        failures.append(f"Expected 6 main tables, found {len(document.tables)}")
    if len(document.inline_shapes) != 4:
        failures.append(f"Expected 4 main figures, found {len(document.inline_shapes)}")
    if not all(figure_captions.values()):
        failures.append(f"Missing main figure captions: {figure_captions}")
    if not all(table_captions.values()):
        failures.append(f"Missing main table captions: {table_captions}")
    if missing_references:
        failures.append(f"Citations without reference entries: {missing_references}")
    if uncited_references:
        failures.append(f"Reference entries not cited: {uncited_references}")
    if reference_numbers != set(range(1, len(reference_numbers) + 1)):
        failures.append("Reference numbering is not contiguous from 1")
    if any(not value for value in image_alts):
        failures.append("One or more main images lack alt text")
    if placeholders:
        failures.append(f"Placeholders found: {placeholders}")
    present_banned = [
        phrase for phrase in banned_phrases if phrase.lower() in main_text.lower()
    ]
    if present_banned:
        failures.append(f"Potentially biased phrases found: {present_banned}")
    if "  " in english_text:
        failures.append("Double spaces found in English paragraph text")
    result = {
        "status": "passed" if not failures else "failed",
        "failures": failures,
        "main": {
            "paragraphs": len(document.paragraphs),
            "tables": len(document.tables),
            "figures": len(document.inline_shapes),
            "abstract_words": abstract_words,
            "citation_range": [
                min(citation_numbers) if citation_numbers else None,
                max(citation_numbers) if citation_numbers else None,
            ],
            "reference_count": len(reference_numbers),
            "missing_references": missing_references,
            "uncited_references": uncited_references,
            "figure_captions": figure_captions,
            "table_captions": table_captions,
            "image_alt_texts": image_alts,
        },
        "supplement": {
            "paragraphs": len(supplement.paragraphs),
            "tables": len(supplement.tables),
            "figures": len(supplement.inline_shapes),
        },
        "checks": [
            "English manuscript contains no CJK text",
            "abstract is within 250 words",
            "all main figure and table captions are present",
            "all cited reference numbers fall within the reference list",
            "all main images have alt text",
            "no placeholder or explicitly biased wording remains",
            "no doubled spaces remain in English paragraph text",
        ],
    }
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    (OUTPUT_ROOT / "MANUSCRIPT_QA.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if failures:
        raise RuntimeError("Manuscript audit failed:\n" + "\n".join(failures))
    return result


if __name__ == "__main__":
    print(json.dumps(audit_manuscript(), ensure_ascii=False, indent=2))
