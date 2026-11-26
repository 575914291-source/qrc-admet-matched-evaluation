from __future__ import annotations

import shutil
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt

from src.config import PROJECT_ROOT


OUTPUT_ROOT = PROJECT_ROOT / "outputs"
VARIANT_ROOT = OUTPUT_ROOT / "Submission_Variants"
JCAMD_ROOT = VARIANT_ROOT / "JCAMD_Master"
JCIM_ROOT = VARIANT_ROOT / "JCIM"
QMI_ROOT = VARIANT_ROOT / "QMI"

JCAMD_EN = OUTPUT_ROOT / "Final_Manuscript_EN.docx"
JCAMD_ZH = OUTPUT_ROOT / "Final_Manuscript_ZH.docx"


def _find(document: Document, prefix: str):
    matches = [
        paragraph
        for paragraph in document.paragraphs
        if paragraph.text.strip().startswith(prefix)
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected one paragraph starting with {prefix!r}, found {len(matches)}"
        )
    return matches[0]


def _set_text(paragraph, text: str) -> None:
    runs = [run for run in paragraph.runs if run.text]
    if runs:
        runs[0].text = text
        for run in runs[1:]:
            run._r.getparent().remove(run._r)
    else:
        paragraph.add_run(text)


def _append_sentence(
    document: Document,
    prefix: str,
    sentence: str,
    joiner: str = " ",
) -> None:
    paragraph = _find(document, prefix)
    if sentence not in paragraph.text:
        _set_text(paragraph, paragraph.text.rstrip() + joiner + sentence)


def _archive_jcand_master() -> None:
    JCAMD_ROOT.mkdir(parents=True, exist_ok=True)
    shutil.copy2(JCAMD_EN, JCAMD_ROOT / "JCAMD_Master_EN.docx")
    shutil.copy2(JCAMD_ZH, JCAMD_ROOT / "JCAMD_Master_ZH.docx")
    (JCAMD_ROOT / "README.md").write_text(
        "# JCAMD master\n\n"
        "This folder preserves the complete JCAMD-oriented manuscript used as the "
        "experimental and textual master for target-specific submission versions. "
        "The English and Chinese files are identical in scientific content. Do not "
        "submit this version concurrently with the JCIM or QMI versions.\n",
        encoding="utf-8",
    )


def _build_jcim_manuscripts() -> tuple[Path, Path]:
    JCIM_ROOT.mkdir(parents=True, exist_ok=True)
    en = Document(JCAMD_EN)
    zh = Document(JCAMD_ZH)

    _set_text(
        en.paragraphs[0],
        "Matched Evaluation of Fixed Quantum Reservoir Features for TDC ADMET Prediction",
    )
    _set_text(
        en.paragraphs[1],
        "A Signal-Calibrated Benchmark with Random Realizations and Strong Baselines",
    )
    _set_text(
        _find(en, "Keywords:"),
        "Keywords: ADMET; QSAR; cheminformatics; TDC; stateless quantum feature map; "
        "matched classical controls; external transfer",
    )
    _append_sentence(
        en,
        "ADMET prediction includes binary",
        "These features make benchmark evidence directly relevant to QSAR and "
        "chemical information workflows, where predictive gains must survive strong "
        "classical representations, held-out chemistry, and source change.",
        joiner=" ",
    )
    _set_text(
        _find(en, "6.5 Interpretation and Reuse"),
        "6.5 Interpretation and Reuse in Molecular Property Modeling",
    )

    _set_text(
        zh.paragraphs[0],
        "固定量子储层特征用于 TDC ADMET 预测的匹配评估",
    )
    _set_text(
        zh.paragraphs[1],
        "基于随机实现与强基线的信号校准基准",
    )
    _set_text(
        _find(zh, "关键词："),
        "关键词：ADMET；QSAR；化学信息学；TDC；无状态量子特征映射；"
        "匹配经典对照；外部迁移",
    )
    _append_sentence(
        zh,
        "ADMET 预测包含",
        "这些特征使基准证据直接关系到 QSAR 和化学信息学工作流："
        "模型增益必须经受强经典表示、留出化学空间和来源变化的检验。",
        joiner="",
    )
    _set_text(
        _find(zh, "6.5 解释与复用"),
        "6.5 分子性质建模中的解释与复用",
    )

    for document, language, comment in (
        (
            en,
            "en-US",
            "JCIM-targeted manuscript variant; same study results as the JCAMD master.",
        ),
        (
            zh,
            "zh-CN",
            "JCIM 目标版本；科学结果与 JCAMD 母稿一致。",
        ),
    ):
        document.core_properties.title = document.paragraphs[0].text
        document.core_properties.subject = document.paragraphs[1].text
        document.core_properties.author = ""
        document.core_properties.language = language
        document.core_properties.comments = comment

    en_path = JCIM_ROOT / "JCIM_Manuscript_EN.docx"
    zh_path = JCIM_ROOT / "JCIM_Manuscript_ZH.docx"
    en.save(en_path)
    zh.save(zh_path)
    return en_path, zh_path


def _build_jcim_cover_letter() -> tuple[Path, Path]:
    markdown_path = JCIM_ROOT / "JCIM_Cover_Letter.md"
    paragraphs = [
        "Dear Editor,",
        (
            "We submit our manuscript, \"Matched Evaluation of Fixed Quantum "
            "Reservoir Features for TDC ADMET Prediction: A Signal-Calibrated "
            "Benchmark with Random Realizations and Strong Baselines,\" for "
            "consideration as a research article in the Journal of Chemical "
            "Information and Modeling."
        ),
        (
            "Quantum reservoir features are often presented as compact nonlinear "
            "molecular representations, but their incremental value relative to "
            "strong classical representations and matched nonlinear controls has "
            "not been evaluated consistently across public ADMET endpoints. The "
            "manuscript treats this as a chemical-information problem rather than "
            "a quantum-advantage demonstration."
        ),
        (
            "The study makes three contributions. First, it positions the fixed "
            "five-qubit molecular feature map as the stateless QRC/QELM limit and "
            "shows that its Pauli readouts form a constrained real-quadratic "
            "family. Second, it compares this family with controls matched in "
            "input dimension, nominal readout dimension, fitted-parameter count, "
            "random-map budget, and tuning budget across all 22 official TDC ADMET "
            "endpoints, two classical bases, five scaffold splits, and multiple "
            "random maps. Third, it uses low-data, finite-shot, simulated-noise, "
            "bounded-family, external-transfer, continuous-label, independent "
            "pIC50, calibration, and chemical-space analyses to delimit the "
            "result."
        ),
        (
            "No endpoint remained significantly better than its matched "
            "real-orthogonal control after Holm correction. Apparent gains on the "
            "weaker ExtraTrees base did not persist on MapLight-CatBoost. External "
            "transfer produced a source-local hERG candidate signal but significant "
            "negative transfer on B3DB BBB. Known-signal calibration recovered "
            "QRC-derived and classical targets in 150/150 and 149/150 simulations, "
            "respectively, while null false-positive rates were 4.7% and 2.0%."
        ),
        (
            "These results are useful to JCIM readers because they provide a "
            "reusable matched-evaluation protocol for claims about quantum-derived "
            "molecular descriptors. The conclusion is explicitly limited to the "
            "tested five-qubit amplitude encoding, fixed Hamiltonian reservoir, 15 "
            "Pauli readouts, linear residual head, and exact simulation. The work "
            "does not claim that other encodings, trainable circuits, larger "
            "reservoirs, or physical hardware are ineffective."
        ),
        (
            "The submission includes public-data provenance, split-level "
            "predictions, model configurations, audit scripts, and an open "
            "reproduction package. The versioned code and result index are "
            "available at https://github.com/575914291-source/"
            "qrc-admet-matched-evaluation."
        ),
        "Sincerely,",
        "[Author names, affiliations, and corresponding author]",
    ]
    markdown_path.write_text(
        "# JCIM Cover Letter\n\n" + "\n\n".join(paragraphs) + "\n",
        encoding="utf-8",
    )

    document = Document()
    section = document.sections[0]
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)
    normal = document.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(11)
    normal.paragraph_format.line_spacing = 1.15
    normal.paragraph_format.space_after = Pt(8)
    for text in paragraphs:
        paragraph = document.add_paragraph()
        run = paragraph.add_run(text)
        if text == "Dear Editor,":
            run.bold = True
        paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT

    docx_path = JCIM_ROOT / "JCIM_Cover_Letter.docx"
    document.core_properties.title = "Cover Letter for JCIM Submission"
    document.core_properties.subject = (
        "Matched evaluation of fixed quantum reservoir features for TDC ADMET"
    )
    document.core_properties.author = ""
    document.core_properties.language = "en-US"
    document.save(docx_path)
    return markdown_path, docx_path


def _write_submission_notes() -> Path:
    path = JCIM_ROOT / "JCIM_Submission_Notes.md"
    path.write_text(
        """# JCIM submission notes

## Current decision

Use the JCIM variant as the primary submission. Keep the JCAMD master
unchanged and do not submit another journal version while JCIM is under review.

## What differs from the JCAMD master

- Title changes from "Matched Evaluation of Fixed Quantum Reservoir Residuals
  on TDC ADMET with Random Realizations and Strong Baselines" to "Matched
  Evaluation of Fixed Quantum Reservoir Features for TDC ADMET Prediction."
- Subtitle changes to "A Signal-Calibrated Benchmark with Random Realizations
  and Strong Baselines."
- Keywords add QSAR and cheminformatics.
- The first Introduction paragraph adds: "These features make benchmark
  evidence directly relevant to QSAR and chemical information workflows,
  where predictive gains must survive strong classical representations,
  held-out chemistry, and source change."
- Section 6.5 changes from "Interpretation and Reuse" to "Interpretation and
  Reuse in Molecular Property Modeling."
- All experiments, numbers, tables, figures, equations, references, and
  scientific boundaries are unchanged.

## Before submitting

1. Add author names, affiliations, ORCID identifiers, corresponding author,
   funding, author contributions, and conflict-of-interest statement.
2. Apply the current ACS article template and check the journal's current
   abstract and reference requirements.
3. Confirm the subscription publishing route to avoid a mandatory APC.
4. Upload the main manuscript, cover letter, figures, and supplementary file.
5. Confirm that no JCAMD or QMI version is under consideration elsewhere.

## Recommended positioning

The contribution is a TDC-wide, signal-calibrated matched audit of a fixed
quantum-derived molecular feature family. Do not present the paper as a failed
attempt to improve ADMET accuracy.
""",
        encoding="utf-8",
    )
    return path


def _write_qmi_plan() -> Path:
    path = QMI_ROOT / "QMI_Migration_Plan.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """# QMI submission migration plan

Status: prepare only. Submit only after the JCIM decision and only after a
substantive QML-oriented rewrite.

## 1. Target identity

### Working title

Matched Benchmarking of Fixed Quantum Reservoir Features Against Classical
Quadratic Controls for Molecular Property Prediction

### Primary claim

Under a common numerical budget, a fixed five-qubit stateless quantum feature
map does not show a stable increment over matched real-quadratic controls on 22
ADMET endpoints, two classical bases, multiple random maps, and independent
molecular-source cohorts.

## 2. Section migration from the JCIM version

| JCIM section | QMI treatment |
|---|---|
| Title and abstract | Rebuild around QML benchmarking, matched controls, and readout limitations. Keep the same result numbers. |
| Introduction | Lead with QRC/QELM expressivity, data encodings, readout decodability, and matched evaluation. Move QSAR framing to the motivation. |
| Related work | Expand QRC/QELM, Pauli-transfer, readout orientation, equivalence testing, and QML reporting. Compress ADMET model history. |
| Data and splits | Keep TDC, scaffold splits, and leakage controls, but move endpoint-by-endpoint chemistry detail to supplementary material. |
| Quantum feature section | Move earlier and expand the finite-shot, fixed-Hamiltonian, 15-readout, and stateless-QELM definition. |
| Classical controls | Keep Morgan-ExtraTrees and MapLight-CatBoost, but present them as strong prediction pipelines attached to matched feature families. |
| Primary results | Lead with QRC versus matched quadratic maps across endpoints and bases. Summarize the 22-endpoint table in one figure and keep full tables in supplement. |
| Gating and extra analyses | Retain as robustness tests, not as the main narrative. |
| External cohorts | Present as distribution-shift probes; reduce chemical-space description in the main text. |
| Discussion | Center on feature geometry, effective rank, readout access, and simulation boundaries. Move detailed chemistry interpretation to supplement. |
| Limitations | Keep five-qubit/exact-simulation/readout boundaries prominent. Do not claim general failure of QRC or QML. |
| Conclusion | Frame the contribution as a QML benchmark and reproducible evaluation protocol for molecular tasks. |

## 3. Abstract blueprint

1. One-sentence problem: QRC gains are sensitive to classical tuning,
   randomness, readout choice, and task structure.
2. Design: fixed stateless five-qubit feature map, matched quadratic and
   Fourier controls, two bases, five scaffold splits, five maps.
3. Main result: no stable quantum increment across 22 ADMET endpoints.
4. Robustness: gating, low data, finite shots, noise, family search, and
   external transfer.
5. Interpretation: source-local hERG signal and negative BBB transfer do not
   support a general advantage.
6. Contribution and boundary: quantum benchmark and evaluation protocol, limited
   to the tested amplitude encoding, Pauli readout, and simulation.

## 4. Material to retain

- All 45 references and the verified citation scope.
- The exact 22-endpoint counts and all effect sizes.
- The Proposition 1 quadratic representation.
- The distinction between nominal readout dimension and task-relevant
  decodability.
- Five-map and five-split randomness controls.
- Known-signal calibration and null false-positive results.
- Qiskit/Aer readout-fidelity results and finite-shot analyses.

## 5. Material to move or compress

- Long TDC endpoint descriptions: keep only enough to interpret the 22-task
  scope; move the rest to supplement.
- Detailed chemical-space summary: retain one compact paragraph and cite the
  supplementary audit.
- QSAR-practice guidance: condense into the final Discussion paragraph.

## 6. Recommended strengthening without rerunning the full benchmark

Priority 1: an interaction-free or product-state Hamiltonian ablation on the
eight representative endpoints, keeping the same PCA input, five random maps,
15 Pauli readouts, and linear head. This distinguishes entanglement or
interaction effects from generic nonlinear feature expansion.

Priority 2: a readout-orientation sensitivity analysis on a small endpoint
subset. Reuse existing feature generation where possible and state clearly that
the full readout search was not performed.

If neither analysis is possible, keep the present readout limitation and do not
claim that the Hamiltonian or entanglement was isolated.

## 7. Reuse and compliance

Figures, tables, and predictions may be reused because they describe the same
study. Text, title, abstract, and discussion must be substantially rewritten for
the QMI readership. Do not submit while JCIM is under review and disclose prior
review history where the submission system requests it.
""",
        encoding="utf-8",
    )
    return path


def build_variants() -> dict[str, str]:
    VARIANT_ROOT.mkdir(parents=True, exist_ok=True)
    _archive_jcand_master()
    jcim_en, jcim_zh = _build_jcim_manuscripts()
    cover_md, cover_docx = _build_jcim_cover_letter()
    notes = _write_submission_notes()
    qmi_plan = _write_qmi_plan()
    return {
        "jcim_en": str(jcim_en),
        "jcim_zh": str(jcim_zh),
        "jcim_cover_md": str(cover_md),
        "jcim_cover_docx": str(cover_docx),
        "jcim_notes": str(notes),
        "qmi_plan": str(qmi_plan),
        "jcamd_master_en": str(JCAMD_ROOT / "JCAMD_Master_EN.docx"),
        "jcamd_master_zh": str(JCAMD_ROOT / "JCAMD_Master_ZH.docx"),
    }


if __name__ == "__main__":
    import json

    print(json.dumps(build_variants(), ensure_ascii=False, indent=2))
