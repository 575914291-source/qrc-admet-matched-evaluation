from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.text.paragraph import Paragraph

from src.config import PROJECT_ROOT


OUTPUT_ROOT = PROJECT_ROOT / "outputs"
TEMPLATE_ROOT = PROJECT_ROOT / "templates"
EN_SOURCE = TEMPLATE_ROOT / "bilingual_source_EN.docx"
ZH_SOURCE = TEMPLATE_ROOT / "bilingual_source_ZH.docx"
FINAL_EN = OUTPUT_ROOT / "Final_Manuscript_EN.docx"
FINAL_ZH = OUTPUT_ROOT / "Final_Manuscript_ZH.docx"
CHANGES_JSON = OUTPUT_ROOT / "Bilingual_Revision_Changes.json"


@dataclass
class ChangeLog:
    document: str
    location: str
    before: str
    after: str
    reason: str

    def as_dict(self) -> dict[str, str]:
        return {
            "document": self.document,
            "location": self.location,
            "before": self.before,
            "after": self.after,
            "reason": self.reason,
        }


def _find_unique(document: Document, prefix: str) -> Paragraph:
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


def _set_text(paragraph: Paragraph, text: str) -> None:
    runs = [run for run in paragraph.runs if run.text]
    if runs:
        runs[0].text = text
        for run in runs[1:]:
            run._r.getparent().remove(run._r)
    else:
        paragraph.add_run(text)
    if paragraph.style.name == "Normal":
        paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY


def _new_paragraph_after(
    anchor: Paragraph,
    text: str,
    *,
    style: str | None = None,
) -> Paragraph:
    element = OxmlElement("w:p")
    anchor._p.addnext(element)
    paragraph = Paragraph(element, anchor._parent)
    if anchor._p.pPr is not None:
        element.insert(0, copy.deepcopy(anchor._p.pPr))
    paragraph.style = style or anchor.style
    if anchor.runs and anchor.runs[0]._r.rPr is not None:
        run = paragraph.add_run(text)
        run._r.insert(0, copy.deepcopy(anchor.runs[0]._r.rPr))
    else:
        paragraph.add_run(text)
    if paragraph.style.name == "Normal":
        paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    else:
        paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    if paragraph.style.name.startswith("Heading"):
        paragraph.paragraph_format.keep_with_next = True
    return paragraph


def _new_paragraph_before(
    marker: Paragraph,
    text: str,
    *,
    style: str,
) -> Paragraph:
    paragraph = marker.insert_paragraph_before("", style=style)
    if marker.runs and marker.runs[0]._r.rPr is not None:
        run = paragraph.add_run(text)
        run._r.insert(0, copy.deepcopy(marker.runs[0]._r.rPr))
    else:
        paragraph.add_run(text)
    paragraph.alignment = (
        WD_ALIGN_PARAGRAPH.JUSTIFY
        if style == "Normal"
        else WD_ALIGN_PARAGRAPH.LEFT
    )
    paragraph.paragraph_format.keep_with_next = style.startswith("Heading")
    return paragraph


def _replace(
    document: Document,
    document_name: str,
    location: str,
    prefix: str,
    after: str,
    reason: str,
    changes: list[ChangeLog],
) -> Paragraph:
    paragraph = _find_unique(document, prefix)
    before = paragraph.text
    _set_text(paragraph, after)
    changes.append(
        ChangeLog(
            document=document_name,
            location=location,
            before=before,
            after=after,
            reason=reason,
        )
    )
    return paragraph


def _replace_substring(paragraph: Paragraph, old: str, new: str) -> None:
    if old not in paragraph.text:
        raise RuntimeError(f"Expected substring not found: {old!r}")
    _set_text(paragraph, paragraph.text.replace(old, new))


def _split_after(
    paragraph: Paragraph,
    marker: str,
    *,
    second_text: str | None = None,
) -> Paragraph:
    text = paragraph.text
    if marker not in text:
        raise RuntimeError(f"Split marker not found: {marker!r}")
    first, remainder = text.split(marker, 1)
    first = first + marker
    second = (remainder.lstrip() if second_text is None else second_text)
    _set_text(paragraph, first)
    return _new_paragraph_after(paragraph, second)


def _replace_cell(cell, old: str, new: str) -> None:
    if cell.text != old:
        return
    paragraph = cell.paragraphs[0]
    for extra in cell.paragraphs[1:]:
        extra._p.getparent().remove(extra._p)
    _set_text(paragraph, new)


def _remove_unverified_power_values(document: Document) -> None:
    """Remove ad hoc diagnostic constants not present in the study outputs."""
    for paragraph in document.paragraphs:
        text = paragraph.text
        text = text.replace(
            "For unit-scaled endpoint metrics, the median sample standard "
            "deviation of the five QRC-minus-control seed effects was 0.0205. "
            "Using the design approximation of Knopov and Shvai [40] and "
            "ignoring the item-level variance term, 80% power to certify a "
            "+/-0.01 margin requires approximately 72 independent split seeds. ",
            "",
        )
        text = text.replace(
            "对于单位尺度端点指标，五个 QRC 减对照 seed 效应的样本标准差"
            "中位数为 0.0205。按照 Knopov 和 Shvai [40] 的设计近似并忽略 "
            "item 级方差项，若要在 +/-0.01 边界内达到 80% 功效，约需 72 "
            "个独立划分种子。",
            "",
        )
        if text != paragraph.text:
            _set_text(paragraph, text)


def _normalize_connectors(document: Document) -> None:
    replacements = {
        "The value of quantum features therefore cannot be inferred":
            "A comparison with a single weak base model cannot isolate the value "
            "of quantum features",
        "The main five-split analysis therefore estimates":
            "The main five-split analysis estimates",
        "Gated results therefore indicate":
            "The gating results indicate",
        "and was therefore excluded":
            "and was excluded",
        "primary difference therefore contains":
            "primary difference contains",
        "and therefore tests sensitivity":
            "and tests sensitivity",
        "orthogonal family therefore had":
            "orthogonal family had",
        "Circuit errors therefore mainly contracted":
            "Circuit errors mainly contracted",
        "we describe the real-orthogonal family as":
            "the real-orthogonal family is described as",
        "We therefore describe the real-orthogonal family as":
            "The real-orthogonal family is described as",
        "The hERG result should therefore be read":
            "The hERG result is",
        "The two cohorts therefore differ":
            "The two cohorts differ",
        "The present comparison therefore applies":
            "The present comparison applies",
        "因此，不能通过与单一弱基线模型比较来推断量子特征的价值。":
            "仅与单一弱基线模型比较，无法分离量子特征的增量。",
        "因此，主分析的五划分足以估计平均效应":
            "主分析的五划分足以估计平均效应",
        "因此，门控结果表示风险控制":
            "门控结果表示风险控制",
        "因此被排除":
            "被排除",
        "因此 +0.0402 的主差异":
            "+0.0402 的主差异",
        "因此仅检验":
            "仅检验",
        "因此，QRC 和正交族":
            "QRC 和正交族",
        "因此，线路误差":
            "线路误差",
        "因此，hERG 结果":
            "hERG 结果",
        "因此，两个队列":
            "两个队列",
        "因此，当前比较":
            "当前比较",
    }
    for paragraph in document.paragraphs:
        text = paragraph.text
        updated = text
        for old, new in replacements.items():
            updated = updated.replace(old, new)
        if updated != text:
            _set_text(paragraph, updated)


def _normalize_english_spelling(document: Document) -> None:
    replacements = {
        "labelled": "labeled",
        "behaviour": "behavior",
        "favour": "favor",
        "Favour": "Favor",
        "favours": "favors",
        "favoured": "favored",
        "favouring": "favoring",
        "neighbour": "neighbor",
        "neighbouring": "neighboring",
        "中心核对齐": "中心核对齐",
    }
    references_started = False
    for paragraph in document.paragraphs:
        if paragraph.text.strip() == "References":
            references_started = True
        if references_started:
            continue
        updated = paragraph.text.replace("，", ", ")
        for old, new in replacements.items():
            updated = updated.replace(old, new)
        updated = re.sub(r" {2,}", " ", updated)
        if updated != paragraph.text:
            _set_text(paragraph, updated)


def _normalize_chinese_terms(document: Document) -> None:
    replacements = {
        "正交界分支": "正交界分支",
        "量子极端学习机": "量子极限学习机",
        "量子极端学习": "量子极限学习",
        "联合校正": "联合 QRC-正交残差",
        "有限 shots": "有限测量采样",
        "固定 4,096 shots": "固定 4,096 次测量采样",
        "4,096 shots": "4,096 次测量采样",
        " shots 下": " 次测量采样下",
        "shots 预算": "测量采样预算",
        "shots": "测量采样",
        "seed 级": "随机种子级",
        "独立划分种子": "独立划分随机种子",
        "seed 效应": "随机种子效应",
        "item 级": "条目级",
        "Hermiticity": "厄米性",
        "强基座": "强基线",
        "基座模型": "基线模型",
        "两种经典基座": "两种经典基线",
        "同一基座内": "同一基线内",
        "每个基座": "每个基线",
        "任一基座": "任一基线",
        "两个基座": "两个基线",
        "两种基座": "两种基线",
        "更强基座": "更强基线",
        "更强基座上": "更强基线上",
        "基座配置": "基线配置",
        "基座预测": "基线预测",
        "相对无残差基座": "相对无残差基线",
        "无残差基座": "无残差基线",
        "减 CatBoost 基座": "减 CatBoost 基线",
        "相对基座": "相对基线",
        "两种强经典基座": "两种强经典基线",
        "QRC − 基座": "QRC − 基线",
        "基座": "基线",
        "PIC50": "pIC50",
        "log-loss": "对数损失",
        "Brier 和 对数损失": "Brier 分数和对数损失",
        "Brier 与 对数损失": "Brier 分数与对数损失",
        "Brier 分数和对数损失 改善": "Brier 分数和对数损失改善",
        "Brier 分数与对数损失 差异": "Brier 分数与对数损失差异",
        "有限测量采样（测量采样）": "有限测量采样",
        "解释hERG": "解释 hERG",
        "合成的QRC": "合成的 QRC",
        "来源 开发集": "来源开发集",
        "来源 测试集": "来源测试集",
        "Dev 集": "开发集（Dev）",
        "Test 集": "测试集",
        "CYP2C9 substrate": "CYP2C9 底物",
        "CYP2D6 inhibition": "CYP2D6 抑制",
        "Half-life": "半衰期",
        "baseline 配置": "baseline（基线）配置",
    }
    for paragraph in document.paragraphs:
        updated = paragraph.text
        for _ in range(2):
            for old, new in replacements.items():
                updated = updated.replace(old, new)
        updated = re.sub(r" {2,}", " ", updated)
        if updated != paragraph.text:
            _set_text(paragraph, updated)
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    updated = paragraph.text
                    for _ in range(2):
                        for old, new in replacements.items():
                            updated = updated.replace(old, new)
                    if updated != paragraph.text:
                        _set_text(paragraph, updated)


def _finalize_english() -> tuple[Document, list[ChangeLog]]:
    document = Document(EN_SOURCE)
    changes: list[ChangeLog] = []

    abstract = _find_unique(
        document,
        "Reported quantum-reservoir gains are difficult to interpret",
    )
    _replace_substring(abstract, "Gating, joint correction", "Joint gating")
    _replace_substring(
        abstract,
        "The main contribution is a TDC-wide audit with a reusable "
        "matched-evaluation protocol.",
        "We contribute a signal-calibrated TDC audit and an open "
        "matched-evaluation protocol for this quantum feature family.",
    )
    _replace_substring(
        abstract,
        "A Qiskit/Aer readout-fidelity audit preserved rank under errors but "
        "attenuated amplitudes without downstream retraining.",
        "A Qiskit/Aer readout audit preserved rank under errors but attenuated "
        "amplitudes without retraining.",
    )
    _replace_substring(
        abstract,
        "Five scaffold splits and five averaged maps per family control randomness.",
        "Five scaffold splits and five maps per family control randomness.",
    )
    changes.append(
        ChangeLog(
            document="English",
            location="Abstract",
            before="Gating, joint correction ... main contribution is a TDC-wide audit ...",
            after=abstract.text,
            reason=(
                "Corrected joint gating terminology and narrowed the claimed "
                "method contribution to this benchmark and protocol."
            ),
        )
    )

    intro = _find_unique(document, "ADMET prediction includes binary")
    _replace_substring(
        intro,
        "The value of quantum features therefore cannot be inferred from a "
        "comparison with a single weak base model.",
        "A comparison with a single weak base model cannot isolate the value "
        "of quantum features.",
    )
    changes.append(
        ChangeLog(
            document="English",
            location="1 Introduction, paragraph 1",
            before=(
                "The value of quantum features therefore cannot be inferred "
                "from a comparison with a single weak base model."
            ),
            after=(
                "A comparison with a single weak base model cannot isolate the "
                "value of quantum features."
            ),
            reason="Replaced a repeated connector with a direct comparison claim.",
        )
    )

    related = _find_unique(document, "Beaulieu et al. studied fixed reservoirs")
    split_marker = "do not support a single-score ranking."
    first_text = related.text.split(split_marker, 1)[0] + split_marker
    second_text = related.text.split(split_marker, 1)[1].strip()
    _set_text(related, first_text)
    _new_paragraph_after(related, second_text)
    changes.append(
        ChangeLog(
            document="English",
            location="2.2 Quantum Molecular Features and Structural Controls",
            before=related.text,
            after=f"{first_text} [paragraph break] {second_text}",
            reason=(
                "Separated the reviewed molecular studies from the newer "
                "reservoir and hardware comparisons."
            ),
        )
    )

    t0st = _find_unique(document, "The primary effect was computed")
    first_end = "followed by Holm correction across the 22 endpoints [18-20]."
    second_end = "Equivalence does not imply identical mechanisms or identical per-molecule predictions."
    t0st_text = t0st.text
    first_part = t0st_text.split(first_end, 1)[0] + first_end
    remainder = t0st_text.split(first_end, 1)[1].strip()
    second_part = remainder.split(second_end, 1)[0] + second_end
    third_part = (
        "A post hoc seed-level power diagnostic showed that five split seeds "
        "cannot provide a high-power equivalence certificate for individual "
        "endpoints at the +/-0.01 metric margin. These TOST results remain "
        "exploratory and are reported as counts rather than as confirmatory "
        "claims."
    )
    _set_text(t0st, first_part)
    second_paragraph = _new_paragraph_after(t0st, second_part)
    _new_paragraph_after(second_paragraph, third_part)
    changes.append(
        ChangeLog(
            document="English",
            location="3 Data, Splits, and Statistical Evaluation",
            before=t0st_text,
            after=f"{first_part} [paragraph break] {second_part} [paragraph break] {third_part}",
            reason=(
                "Separated effect estimation, TOST interpretation, and the "
                "power boundary. Removed ad hoc constants that were not part "
                "of the archived analysis outputs."
            ),
        )
    )
    _replace(
        document,
        "English",
        "3 Data, Splits, and Statistical Evaluation",
        "3 Data and Official Evaluation",
        "3 Data, Splits, and Statistical Evaluation",
        "Made the section title match its data, split, and statistical contents.",
        changes,
    )

    proposition = _find_unique(document, "Proposition 1.")
    proposition_after = (
        "Proposition 1. For any fixed set of 15 diagonal Pauli observables D_j "
        "and any fixed unitary U, the readouts of a normalized 32-dimensional "
        "real input a satisfy q_j(a)=a^T A_j a, where A_j=Re(U^dagger D_j U). "
        "Any affine readout of these 15 features has the form a^T M a+b, with "
        "the intercept absorbed into b. A fixed five-qubit reservoir feature "
        "map with a linear residual head is an instance of this model family, "
        "constrained by at most 15 real quadratic forms. The proof follows by "
        "expanding (Ua)^dagger D_j (Ua). This does not make QRC equivalent to "
        "a particular real-orthogonal map; it defines the function class "
        "available under the current encoding and readout. This proposition "
        "defines the nominal function family and does not imply equal "
        "decodability. Pauli-transfer and readout-orientation analyses show "
        "that equal rank or observable count can leave different task-relevant "
        "information accessible [37-39]. The real-orthogonal family is "
        "described as matched in input dimension, nominal readout dimension, "
        "fitted-parameter count, random-map budget, and tuning budget, not as "
        "having identical capacity. The primary analysis also fixes the "
        "readout family at five Z and all ten ZZ observables; optimized "
        "measurement operators and interaction ablations are outside the "
        "primary comparison."
    )
    _replace(
        document,
        "English",
        "4.2 Five-Qubit Stateless Feature Map and Matched Classical Features, Proposition 1",
        "Proposition 1.",
        proposition_after,
        "Removed the contradictory 'intercept-free' description and separated nominal function class from decodability.",
        changes,
    )

    gating = _find_unique(document, "Validation gating set the QRC weight")
    _replace_substring(
        gating,
        "CatBoost favoured QRC at 4, the orthogonal branch at 17, and tied at "
        "1 on CatBoost.",
        "CatBoost favoured QRC at 4, the orthogonal branch at 17, and tied at 1.",
    )

    bounded = _find_unique(
        document,
        "Across the eight representative endpoints, the validation-selected",
    )
    bounded_after = (
        "Across the eight representative endpoints, ExtraTrees selected the "
        "QRC search for 4 endpoints and the matched orthogonal search for 4. "
        "CatBoost selected the QRC search for 2, the orthogonal search for 5, "
        "and a tie for 1. No endpoint was Holm-significantly positive. The "
        "baseline reservoir family remained the most frequently selected QRC "
        "setting (15/40 on ExtraTrees and 25/40 on CatBoost), indicating that "
        "the broader family did not reveal a new stable signal. Against the "
        "residual-free base, the corresponding counts remained 4/4 and 2/5/1; "
        "VDss was significantly worse on both bases. This narrows the "
        "possibility that under-tuning explains the null result."
    )
    _replace(
        document,
        "English",
        "5.7 Bounded Reservoir-Family Search, paragraph 2",
        "Across the eight representative endpoints",
        bounded_after,
        "Rewrote a circular selection sentence and clarified the counted objects without changing any count.",
        changes,
    )

    _replace(
        document,
        "English",
        "5.8 Independent Continuous hERG Regression",
        "5.8 Independent Continuous pIC50 Regression and Circuit-Level Audit",
        "5.8 Independent Continuous hERG Regression",
        "Separated the independent regression from the circuit-audit result.",
        changes,
    )
    combined_result = _find_unique(document, "Five model seeds did not show")
    split_at = "Supplementary Table S10."
    first_part, remainder = combined_result.text.split(split_at, 1)
    _set_text(combined_result, first_part + split_at)
    circuit_heading = _new_paragraph_after(
        combined_result,
        "5.9 Circuit-Level Aer Audit",
        style="Heading 2",
    )
    circuit_text = remainder.strip()
    if circuit_text.startswith("We also audited"):
        circuit_text = circuit_text.replace(
            "We also audited readout fidelity",
            "The circuit-level audit examined readout fidelity",
            1,
        )
    _new_paragraph_after(circuit_heading, circuit_text, style="Normal")
    _replace(
        document,
        "English",
        "5.10 Benchmark Calibration and Source Diagnostics",
        "5.9 Benchmark Calibration and Source Diagnostics",
        "5.10 Benchmark Calibration and Source Diagnostics",
        "Renumbered the calibration section after the split.",
        changes,
    )
    calibration = _find_unique(
        document,
        "The known-signal calibration recovered",
    )
    calibration_after = (
        "The known-signal calibration separated the three feature families. "
        "For QRC-derived targets, QRC minus orthogonal test performance was "
        "+0.302 on ExtraTrees and +0.190 on CatBoost, and the expected QRC "
        "family ranked first in 150/150 simulations (100.0%) for both bases. "
        "For orthogonal-derived targets, the same contrast reversed to -0.332 "
        "and -0.238, and the expected orthogonal family ranked first in 149/150 "
        "simulations (99.3%) for ExtraTrees and 149/150 (99.3%) for CatBoost. "
        "For null targets, two-sided paired permutation tests were significant "
        "in 7/150 simulations (4.7%) on ExtraTrees and 3/150 (2.0%) on "
        "CatBoost."
    )
    _set_text(calibration, calibration_after)
    changes.append(
        ChangeLog(
            document="English",
            location="5.10 Benchmark Calibration and Source Diagnostics",
            before="The known-signal calibration recovered the intended geometry.",
            after=calibration_after,
            reason="Reported simulation denominators so the percentages can be audited.",
        )
    )

    quadratic = _find_unique(
        document,
        "With real amplitude inputs, every Z or ZZ expectation",
    )
    quadratic_after = (
        "With real amplitude inputs, every Z or ZZ expectation after fixed "
        "evolution is a real symmetric quadratic form. Training-side "
        "standardization is affine, so the linear readout combines these "
        "forms and adds a fixed offset. Given the fitted parameters, the QRC "
        "residual can be reproduced by a real quadratic form and a constant "
        "on the normalized 32-dimensional latent input. This statement applies "
        "to that latent space, not to the raw molecular graph. All five QRC "
        "readout matrices had rank 15 and a median condition number of 1.210; "
        "the real-orthogonal readout matrices had rank 15 and condition number "
        "1.000. On held-out molecular features, effective rank was 14.10 "
        "versus 14.62 on ExtraTrees and 12.82 versus 14.25 on CatBoost, with "
        "linear centered-kernel alignments of 0.20 and 0.30. The branches had "
        "the same output dimension and fitted-parameter count, different geometry, and "
        "comparable but not identical effective feature capacity."
    )
    _replace(
        document,
        "English",
        "6.1 What the Constrained Quadratic Map Explains, paragraph 1",
        "With real amplitude inputs",
        quadratic_after,
        "Kept readout-matrix rank distinct from held-out effective rank and CKA, and removed equal-capacity language.",
        changes,
    )

    strong_base = _find_unique(
        document,
        "The strong-base experiment is the main difference",
    )
    strong_after = (
        "The strong-base comparison provides a direct stress test. "
        "MapLight-CatBoost outperformed Morgan-ExtraTrees on 21/22 endpoints, "
        "but QRC's relative advantage did not persist on the stronger base. "
        "Joint gating, finite shots, low-data scaling, and simulated noise did "
        "not reveal a transferable quantum correction. The circuit audit "
        "likewise showed readout attenuation without new advantage evidence."
    )
    _set_text(strong_base, strong_after)
    external_after = (
        "The external results support only a source-specific candidate on "
        "hERG. The same direction appeared in pIC50 rank transfer and "
        "independent regression, but neither survived the joint multiplicity "
        "correction. B3DB logBB was near zero and B3DB BBB classification "
        "degraded significantly, so the hERG result cannot be generalized "
        "across sources. These findings support testing future quantum "
        "encodings on a strong classical base with matched input, nominal "
        "readout dimension, fitted-parameter count, and candidate budget. They "
        "do not establish a general ADMET descriptor. The two cohorts probe "
        "different chemistry and label regimes rather than a single deployment "
        "scenario [44]."
    )
    _new_paragraph_after(strong_base, external_after)
    changes.append(
        ChangeLog(
            document="English",
            location="6.3 What the Strong Base and External Cohorts Reveal",
            before=strong_base.text,
            after=f"{strong_after} [paragraph break] {external_after}",
            reason="Separated the strong-base stress test from the external transfer interpretation.",
        )
    )

    chemical_1 = (
        "A descriptive chemical-space audit tested whether cohort differences "
        "could reflect source proximity. Both cohorts were free of exact "
        "canonical identities from the corresponding TDC archive. For hERG, "
        "23 of 293 molecules (7.8%) retained a Bemis-Murcko scaffold present "
        "in TDC train/validation data; the median nearest Morgan Tanimoto "
        "similarity (radius 2, 2048 bits) was 0.234 and the 90th percentile was "
        "0.423. For B3DB BBB, 562 of 2,317 molecules (24.3%) shared a TDC "
        "train/validation scaffold, with a median nearest similarity of 0.346 "
        "and a 90th percentile of 0.722. B3DB had 48.9% positives versus "
        "76.4% in the full TDC BBB archive, whereas hERG contained 76.4% "
        "versus 68.9% in TDC. The two cohorts differed from their TDC sources "
        "in both chemical proximity and label composition."
    )
    _replace(
        document,
        "English",
        "6.4 Chemical-Space and Source Dependence, paragraph 1",
        "We added a descriptive chemical-space audit",
        chemical_1,
        "Turned the background facts into a direct source-proximity audit statement.",
        changes,
    )
    chemical_2 = (
        "Stratifying the held-out predictions did not support a simple "
        "scaffold-overlap or similarity explanation for the hERG signal. For "
        "CatBoost, the hERG gated-QRC minus gated-orthogonal effect was -0.0026 "
        "AUROC among the 23 molecules with a shared train/validation scaffold "
        "and +0.0452 among the 270 molecules with a novel scaffold. The earlier "
        "top-quartile split gave +0.0196 in the highest-similarity group and "
        "+0.0494 in the other three quartiles. The finer quartile analysis was "
        "non-monotonic: CatBoost and ExtraTrees were positive in Q3 but not in "
        "every adjacent quartile. B3DB effects were negative across "
        "shared-scaffold, novel-scaffold, and most similarity strata. Full "
        "source audits are reported in Supplementary Tables S5, S6, and S16. "
        "These descriptive strata locate where an effect appears; they do not "
        "control source, assay batch, or label definition and cannot establish "
        "a causal chemical mechanism."
    )
    _replace(
        document,
        "English",
        "6.4 Chemical-Space and Source Dependence, paragraph 2",
        "Re-scoring the existing held-out predictions",
        chemical_2,
        "Connected the similarity strata to the non-monotonic QRC-specific effect without claiming a chemical mechanism.",
        changes,
    )

    interpret_1 = _find_unique(
        document,
        "A low-dimensional fixed quantum reservoir has its clearest",
    )
    _new_paragraph_before(interpret_1, "6.5 Interpretation and Reuse", style="Heading 2")
    interpret_1_after = (
        "A low-dimensional fixed quantum reservoir has its clearest theoretical "
        "rationale for tasks with limited training data, strong local nonlinear "
        "interactions, and classical kernels that do not adequately cover the "
        "chemical distribution. The global TDC ADMET endpoints generally "
        "contain larger and more heterogeneous label collections, the regime "
        "in which the present design showed no stable gain. The low-data curves "
        "likewise did not show a synchronized positive shift across bases. "
        "This observation does not rule out angle encodings, task-conditioned "
        "amplitude encodings, trainable circuits, larger reservoirs, or "
        "different readout strategies; each must be reassessed against strong "
        "bases and independent source cohorts."
    )
    _set_text(interpret_1, interpret_1_after)
    interpret_2_before = _find_unique(
        document,
        "The hERG point improvement is a candidate signal",
    )
    interpret_2_after = (
        "Neither the hERG candidate nor the B3DB negative transfer establishes "
        "a mechanistic or general quantum effect. The reviewed QML-ADMET "
        "studies use different fixed reservoirs, Hamiltonian-derived features, "
        "quantum-inspired preprocessing, circuit search, or jointly trained "
        "residuals. Their task counts, controls, and external transfer settings "
        "do not support like-for-like equivalence. Table 1 summarizes the "
        "design differences, and Supplementary Table S4 provides the expanded "
        "comparison. The empirical contribution is a TDC-wide, "
        "signal-calibrated audit of one fixed stateless quantum feature-map "
        "family. The methodological contribution is a reusable minimum "
        "evaluation protocol: prespecify the primary comparator, match "
        "candidate and map budgets, infer with scaffold clusters, correct "
        "across endpoints, interpret equivalence separately from superiority, "
        "and report both cross-base and cross-source results."
    )
    _set_text(interpret_2_before, interpret_2_after)
    changes.append(
        ChangeLog(
            document="English",
            location="6.5 Interpretation and Reuse",
            before="The hERG point improvement is a candidate signal ... The contribution is a reusable minimum ... The contribution is a TDC-wide ...",
            after=interpret_2_after,
            reason="Removed repeated contribution statements and separated the empirical from the methodological contribution.",
        )
    )

    limitations_1 = _find_unique(
        document,
        "The fixed official test set supports reproducible comparisons",
    )
    limitations_1_after = (
        "Three evaluation limits constrain generalization. The public TDC test "
        "sets may have been reused by earlier studies and are not prospective "
        "cohorts; scaffold splits reduce, but do not eliminate, near analogues "
        "across laboratories, time, and chemical series. The low-data analysis "
        "covers eight endpoints, and its 96-record minimum changes the "
        "effective fraction for the smallest endpoints. The primary external "
        "comparison contains two classification cohorts that differ in assay "
        "source and label construction [3-5]."
    )
    _set_text(limitations_1, limitations_1_after)
    limitations_2 = _find_unique(
        document,
        "We evaluate independent per-molecule inputs",
    )
    limitations_2_after = (
        "The execution boundary is equally explicit. Exact state-vector "
        "calculation isolates the fixed circuit's expressive behavior but does "
        "not evaluate physical gate error, readout crosstalk, connectivity, or "
        "scheduling. Finite-shot analysis samples each Pauli expectation "
        "independently. The simplified depolarizing model omits gate-specific "
        "error, leakage, crosstalk, and physical scheduling. The Qiskit/Aer "
        "audit adds transpiled gate depolarization and readout flips, but uses "
        "fixed synthetic error parameters and does not retrain the full "
        "predictor on circuit-noisy features. Trainable circuits, "
        "task-conditioned amplitude encoding, and other PCA dimensions were not "
        "evaluated."
    )
    _set_text(limitations_2, limitations_2_after)
    limitations_3 = (
        "The auxiliary analyses have narrower scope. Continuous-label transfer "
        "ranks outputs from binary-trained models and is not an independently "
        "trained regression. The separate pIC50 regression uses 214 test "
        "molecules in 155 scaffolds under a fixed protocol and has limited "
        "statistical power. B3DB logBB was available for only 613/2,317 "
        "non-overlapping molecules and was strongly class-enriched. The "
        "chemical-space figure uses a linear fingerprint projection and three "
        "basic descriptors, not a complete applicability-domain model, and "
        "TOST margins are exploratory benchmark thresholds rather than "
        "clinical or regulatory limits [21]. Random-map sensitivity covers "
        "five realizations per family. The known-signal calibration uses "
        "synthetic targets drawn from the tested feature families; it "
        "establishes detectability for those designs, not coverage of every "
        "possible nonlinear signal. The reported comparison applies to "
        "five-qubit amplitude encoding, a fixed Hamiltonian reservoir, 15 Pauli "
        "readouts, a linear residual head, and exact simulation; other "
        "encodings, trainable circuits, larger reservoirs, and physical "
        "hardware require independent evaluation."
    )
    _new_paragraph_after(limitations_2, limitations_3)
    changes.append(
        ChangeLog(
            document="English",
            location="7 Limitations",
            before="Two long paragraphs mixed evaluation, execution, and auxiliary-analysis limits.",
            after=f"{limitations_1_after} [paragraph break] {limitations_2_after} [paragraph break] {limitations_3}",
            reason="Grouped necessary limitations by the type of inference they constrain.",
        )
    )

    conclusion = _find_unique(
        document,
        "Across 22 official TDC ADMET endpoints",
    )
    conclusion_1 = (
        "Across 22 official TDC ADMET endpoints, fixed five-qubit stateless "
        "reservoir residuals showed no stable increment over real-orthogonal "
        "quadratic maps matched in input dimension, nominal readout dimension, "
        "fitted-parameter count, random-map budget, and tuning budget. This "
        "result held on both Morgan-ExtraTrees and the stronger "
        "MapLight-CatBoost base. Validation gating pushed some harmful "
        "residuals back to the classical base but did not produce a stable "
        "advantage over the gated classical control. Joint gating, low-data "
        "scaling, finite shots, and simulated decoherence did not reverse this "
        "conclusion. External hERG transfer provided a CatBoost-specific "
        "candidate signal, whereas B3DB BBB showed significant negative "
        "transfer. Continuous-label rank transfer and the scaffold-disjoint "
        "pIC50 sensitivity analysis showed only uncorrected weak "
        "CatBoost/hERG directions, with no Holm-significant comparison and no "
        "corresponding BBB signal. The circuit-level audit showed high rank "
        "preservation under low and medium errors but marked readout "
        "attenuation and no new advantage evidence. Known-signal calibration "
        "recovered the synthetic QRC and classical targets, with null "
        "false-positive rates at or below 5%."
    )
    conclusion_2 = (
        "The empirical contribution is a signal-calibrated, TDC-wide audit of "
        "one fixed stateless quantum feature-map family; the methodological "
        "contribution is an open matched-evaluation protocol. The hERG signal "
        "is a bounded candidate rather than a demonstrated mechanism of "
        "cardiotoxicity, and the B3DB result does not show that quantum methods "
        "are universally ineffective. These conclusions apply to the tested "
        "five-qubit amplitude-encoded, fixed-Hamiltonian reservoir with 15 "
        "Pauli readouts, a linear residual head, and exact simulation; other "
        "encodings, trainable circuits, larger reservoirs, and physical "
        "hardware require independent evaluation."
    )
    _set_text(conclusion, conclusion_1)
    _new_paragraph_after(conclusion, conclusion_2)
    changes.append(
        ChangeLog(
            document="English",
            location="8 Conclusion",
            before=conclusion_1,
            after=f"{conclusion_1} [paragraph break] {conclusion_2}",
            reason="Separated the empirical finding from the methodological contribution and final scope.",
        )
    )

    availability = _find_unique(
        document,
        "The official TDC archive is available",
    )
    availability_1 = (
        "The official TDC archive is available as Harvard Dataverse file "
        "4426004 with SHA-256 "
        "bd0005246cb6f1672333c28ad202112a8bf071ab65d847848715030308faf1f1. "
        "External hERG data are from Zenodo 5807719 and BBB data from B3DB. "
        "Source, label rules, deduplication, and overlap audits are included in "
        "the reproduction package. The MapLight reference and MIT license are "
        "retained, and upstream data licenses are listed with the archived "
        "materials."
    )
    _set_text(availability, availability_1)
    availability_2 = (
        "The reproduction package contains processing scripts, five scaffold "
        "splits, five random maps per family, base configurations, all "
        "split-level predictions, gating, finite-shot, low-data, external "
        "decomposition and calibration, continuous-label transfer, independent "
        "pIC50 regression, simplified and circuit-level noise, bounded-family, "
        "TOST-sensitivity, effect-decomposition, capacity, and source-gradient "
        "results, statistical scripts, figure-generation code, and environment "
        "locks. The versioned code and result index are at "
        "https://github.com/575914291-source/qrc-admet-matched-evaluation. "
        "Official test labels were used only for scoring after configuration "
        "lock and were not used for training, map generation, joint weights, or "
        "gating."
    )
    references_heading = _find_unique(document, "References")
    _new_paragraph_before(references_heading, availability_2, style="Normal")
    changes.append(
        ChangeLog(
            document="English",
            location="Data and Code Availability",
            before="One paragraph combined source provenance and the software inventory.",
            after=f"{availability_1} [paragraph break] {availability_2}",
            reason="Separated source provenance from software and result availability.",
        )
    )

    table_updates = {
        "Methods 3; Figure 4; Table 5":
            "Section 3; Figure 4; Table 5",
        "Figure 3; Tables S7-S10":
            "Figure 3; Tables S7-S10, S16",
        "Tables 3-5; Figures S1-S5":
            "Tables 3-5, S12-S16; Figures S1-S10",
        "Methods 4.2; Limitations; Figure S5":
            "Methods 4.2, 4.4; Limitations; Figures S5-S10",
    }
    for row in document.tables[-1].rows:
        for cell in row.cells:
            for old, new in table_updates.items():
                _replace_cell(cell, old, new)

    _remove_unverified_power_values(document)
    _normalize_connectors(document)
    _normalize_english_spelling(document)
    document.core_properties.title = document.paragraphs[0].text
    document.core_properties.subject = document.paragraphs[1].text
    document.core_properties.author = ""
    document.core_properties.language = "en-US"
    document.core_properties.comments = (
        "Final English manuscript; bilingual and matched-evaluation revisions "
        "integrated; author metadata pending."
    )
    document.save(FINAL_EN)
    return document, changes


def _finalize_chinese() -> tuple[Document, list[ChangeLog]]:
    document = Document(ZH_SOURCE)
    changes: list[ChangeLog] = []

    abstract = _find_unique(document, "量子储层研究报告的增益")
    _replace_substring(
        abstract,
        "量子储层研究报告的增益难以解释",
        "文献报告的量子储层性能增益难以比较",
    )
    _replace_substring(
        abstract,
        "本文在无状态量子极端学习机（QELM）极限下，对固定的五比特幅度编码特征映射开展覆盖 TDC 全端点的信号校准评价",
        "本文将模型定位为无状态量子极限学习机（QELM），评价一项覆盖 TDC 全端点的固定五比特幅度编码特征映射",
    )
    _replace_substring(
        abstract,
        "五个骨架划分和每族五个平均映射控制随机性",
        "研究使用五个骨架划分，并对每族五个映射取平均以控制随机性",
    )
    _replace_substring(abstract, "联合校正", "联合 QRC-正交残差")
    _replace_substring(abstract, "正交界分支", "正交界分支")
    _replace_substring(
        abstract,
        "hERG 差异还包含正交界分支的下降",
        "hERG 差异还包含正交界分支的性能下降",
    )
    _replace_substring(
        abstract,
        "有限 shots",
        "有限测量采样",
    )
    _replace_substring(
        abstract,
        "且未对下游模型重新训练",
        "且未在误差特征上重新训练下游模型",
    )
    _replace_substring(
        abstract,
        "主要贡献是对一个固定量子特征映射族开展 TDC 全端点审计，并给出可复用的匹配评价流程。",
        "本文的贡献是针对这一特征映射族开展信号校准的 TDC 审计，并提供开放的匹配评价流程。",
    )
    changes.append(
        ChangeLog(
            document="中文",
            location="摘要",
            before="联合校正、正交界分支、量子极端学习机、有限 shots ...",
            after=abstract.text,
            reason="统一术语、删除重复的门控表述，并使贡献表述与最终英文稿一致。",
        )
    )

    intro = _find_unique(document, "ADMET 预测包含")
    _replace_substring(
        intro,
        "因此，不能通过与单一弱基座模型比较来推断量子特征的价值。",
        "仅与单一弱基线模型比较，无法分离量子特征的增量。",
    )
    changes.append(
        ChangeLog(
            document="中文",
            location="1 引言，第 1 段",
            before="因此，不能通过与单一弱基座模型比较来推断量子特征的价值。",
            after="仅与单一弱基线模型比较，无法分离量子特征的增量。",
            reason="直接写出比较条件与推断范围，减少机械衔接。",
        )
    )

    related = _find_unique(document, "Beaulieu 等研究了固定储层")
    split_marker = "不能支持单一分数排名。"
    first, remainder = related.text.split(split_marker, 1)
    first = first + split_marker
    second = remainder.lstrip()
    _set_text(related, first)
    _new_paragraph_after(related, second)
    changes.append(
        ChangeLog(
            document="中文",
            location="2.2 量子分子特征与结构对照",
            before=first,
            after=f"{first} [paragraph break] {second}",
            reason="把早期分子性质研究与新增的储层、硬件比较分开，降低单段负担。",
        )
    )

    tost = _find_unique(document, "主要效应由未舍入预测计算")
    first_end = "并在每个基座内对 22 个端点进行 Holm 校正 [18-20]。"
    second_end = "等价不意味着机制相同或逐分子预测相同。"
    text = tost.text
    part_1 = text.split(first_end, 1)[0] + first_end
    rem = text.split(first_end, 1)[1].strip()
    part_2 = rem.split(second_end, 1)[0] + second_end
    part_3 = (
        "事后随机种子级功效诊断表明，五个划分随机种子不足以在 "
        "+/-0.01 的指标边界内为单个端点提供高功效等价证明。"
        "TOST 结果仍属探索性，按等价计数报告，不作为确证性主张。"
    )
    _set_text(tost, part_1)
    p2 = _new_paragraph_after(tost, part_2)
    _new_paragraph_after(p2, part_3)
    changes.append(
        ChangeLog(
            document="中文",
            location="3 数据、划分与统计评价",
            before=text,
            after=f"{part_1} [paragraph break] {part_2} [paragraph break] {part_3}",
            reason="分开效应估计、TOST 判定与功效边界，并删除未进入归档分析的事后常数。",
        )
    )
    _replace(
        document,
        "中文",
        "3 数据、划分与统计评价",
        "3 数据与官方评价",
        "3 数据、划分与统计评价",
        "使节标题覆盖数据、划分和统计评价三项内容。",
        changes,
    )

    proposition = _find_unique(document, "命题 1")
    proposition_after = (
        "命题 1。对于任意固定的一组 15 个对角 Pauli 可观测量 D_j 和任意"
        "固定酉矩阵 U，归一化 32 维实输入 a 的读出满足 "
        "q_j(a)=a^T A_j a，其中 A_j=Re(U^dagger D_j U)。这些 15 个特征的"
        "任意仿射读出均可写成 a^T M a+b，其中截距并入 b。使用线性残差头的"
        "固定五比特储层特征映射属于这一模型族，并受至多 15 个实二次型约束。"
        "证明可由展开 (Ua)^dagger D_j (Ua) 得到。该命题并不表示 QRC 与某个"
        "特定真实正交映射等价，而是界定当前编码和读出可用的函数类。它只定义"
        "名义函数族，不表示可解码性相同。Pauli 转移和读出方向分析表明，"
        "相同秩或观测量数量仍可能使不同任务相关信息具有不同的可访问性 "
        "[37-39]。本文将真实正交族描述为在输入维数、名义读出维数、拟合参数"
        "数量、随机映射预算和调参预算上匹配，而不称其具有完全相同的容量。"
        "主分析还将读出固定在五个 Z 和全部十个 ZZ 观测量；优化测量算子和"
        "相互作用消融不属于主比较。"
    )
    _replace(
        document,
        "中文",
        "4.2 五比特无状态特征映射与匹配经典特征，命题 1",
        "命题 1",
        proposition_after,
        "删除“无截距却含 b”的自相矛盾，并区分名义函数族与可解码性。",
        changes,
    )

    bounded = _find_unique(
        document,
        "在八个代表端点上，ExtraTrees 中有 4 个端点选择 QRC 搜索",
    )
    bounded_after = (
        "在八个代表端点上，ExtraTrees 有 4 个端点选择 QRC 搜索、4 个端点"
        "选择匹配正交搜索；CatBoost 有 2 个端点选择 QRC 搜索、5 个端点"
        "选择正交搜索、1 个端点持平。没有 Holm 显著正向端点。baseline"
        "（基线）配置仍是最常被选择的 QRC 设置（ExtraTrees 15/40，"
        "CatBoost 25/40），说明扩大特征族没有揭示新的稳定信号。相对无残差"
        "基线，相应计数仍为 ExtraTrees 4/4、CatBoost 2/5/1；VDss 在两种"
        "基线上均显著更差。这降低了“调参不足导致零结果”的可能。"
    )
    _replace(
        document,
        "中文",
        "5.7 有限储层族搜索，第 2 段",
        "在八个代表端点上，ExtraTrees 中有 4 个端点选择 QRC 搜索",
        bounded_after,
        "修正循环表述并明确计数对象，未改动任何计数。",
        changes,
    )

    _replace(
        document,
        "中文",
        "5.8 独立连续 hERG 回归",
        "5.8 独立连续 pIC50 回归与电路级审计",
        "5.8 独立连续 hERG 回归",
        "把独立回归与电路级审计分开。",
        changes,
    )
    combined = _find_unique(document, "五个模型种子均未显示")
    split_at = "补充表 S10。"
    first, remainder = combined.text.split(split_at, 1)
    _set_text(combined, first + split_at)
    circuit_heading = _new_paragraph_after(
        combined,
        "5.9 电路级 Aer 审计",
        style="Heading 2",
    )
    circuit = remainder.strip()
    circuit = circuit.replace(
        "本文还在显式生成的 Qiskit 线路上审计读出保真度",
        "电路级审计在显式生成的 Qiskit 线路上考察读出保真度",
        1,
    )
    _new_paragraph_after(circuit_heading, circuit, style="Normal")
    _replace(
        document,
        "中文",
        "5.10 基准校准与来源诊断",
        "5.9 基准校准与来源诊断",
        "5.10 基准校准与来源诊断",
        "电路审计拆分后的章节重新编号。",
        changes,
    )
    calibration = _find_unique(
        document,
        "已知信号校准恢复了预期几何",
    )
    calibration_after = (
        "已知信号校准区分了三类特征来源。对 QRC 派生目标，QRC 减正交的"
        "测试表现中，ExtraTrees 为 +0.302、CatBoost 为 +0.190；两个基线"
        "中，预期 QRC 族均在 150/150 次模拟中排名第一（100.0%）。对正交派生"
        "目标，同一比较反转为 -0.332 和 -0.238，预期正交族在 ExtraTrees "
        "和 CatBoost 上均为 149/150 次模拟排名第一（99.3%）。对零信号"
        "目标，双侧配对置换检验在 ExtraTrees 的 7/150 次模拟（4.7%）和 "
        "CatBoost 的 3/150 次模拟（2.0%）中显著。"
    )
    _set_text(calibration, calibration_after)
    changes.append(
        ChangeLog(
            document="中文",
            location="5.10 基准校准与来源诊断",
            before="已知信号校准恢复了预期几何。",
            after=calibration_after,
            reason="补充模拟分母，使正文百分比和假阳性率可核查。",
        )
    )

    quadratic = _find_unique(
        document,
        "对于实幅度输入，固定演化后的每个 Z 或 ZZ 期望",
    )
    quadratic_after = (
        "对于实幅度输入，固定演化后的每个 Z 或 ZZ 期望都是实对称二次型。"
        "训练侧标准化是仿射特征变换，因此线性读出只组合这些二次型并加入"
        "固定偏移。给定拟合参数后，量子残差可由归一化 32 维潜变量输入上的"
        "一个实二次型和常数复现。该结构作用于潜变量空间，而不作用于原始"
        "分子图。五个 QRC 读出矩阵的秩均为 15，条件数中位数为 1.210；"
        "真实正交读出矩阵的秩为 15，条件数为 1.000。在留出分子特征上，"
        "有效秩在 ExtraTrees 上为 14.10 对 14.62，在 CatBoost 上为 12.82 "
        "对 14.25；线性中心核对齐分别为 0.20 和 0.30。两类分支具有相同的"
        "输出维数和拟合参数数量、不同的几何，以及相近但不完全相同的有效"
        "特征容量。"
    )
    _replace(
        document,
        "中文",
        "6.1 受限二次映射解释了什么，第 1 段",
        "对于实幅度输入",
        quadratic_after,
        "区分读出矩阵秩、留出特征有效秩和中心核对齐，并避免把名义匹配写成容量相等。",
        changes,
    )

    strong = _find_unique(document, "强基座实验是本文相对早期试点")
    strong_after = (
        "强基线比较提供了直接压力测试。MapLight-CatBoost 在 21/22 个端点上"
        "优于 Morgan-ExtraTrees，但 QRC 的相对优势没有在更强基线上保留。"
        "联合门控、有限测量采样、低数据缩放和模拟噪声均未揭示可迁移的量子"
        "修正。电路级审计同样显示读出幅度衰减，未增加优势证据。"
    )
    _set_text(strong, strong_after)
    external_after = (
        "外部结果仅支持 hERG 上的来源特异候选。同一方向也出现在 pIC50 "
        "排序迁移和独立回归中，但两者均未通过联合多重校正。B3DB logBB "
        "迁移接近零，B3DB BBB 分类又出现显著退化，因此 hERG 结果不能跨"
        "来源推广。未来量子编码应在强基线上测试，并匹配输入维数、名义读出"
        "维数、拟合参数数量和候选预算；现有结果不支持将其视为通用 ADMET "
        "描述符。两个队列用于考察不同化学空间与标签机制，并不对应单一"
        "部署场景 [44]。"
    )
    _new_paragraph_after(strong, external_after)
    changes.append(
        ChangeLog(
            document="中文",
            location="6.3 强基线与外部队列揭示了什么",
            before=strong_after,
            after=f"{strong_after} [paragraph break] {external_after}",
            reason="把强基线压力测试与外部队列解释分成两段。",
        )
    )

    chemical_1 = (
        "描述性化学空间审计用于判断队列差异是否反映来源邻近性。两个队列"
        "均已删除各自 TDC 归档中的精确规范身份。hERG 的 293 个分子中有 "
        "23 个（7.8%）保留了出现在 TDC 训练/验证集中的 Bemis-Murcko 骨架；"
        "到 TDC 训练/验证分子的最近 Morgan Tanimoto 相似度（半径 2，"
        "2048 位）中位数为 "
        "0.234，第 90 百分位为 0.423。B3DB BBB 的 2,317 个分子中有 562 个"
        "（24.3%）共享 TDC 训练/验证骨架，最近相似度中位数为 0.346，"
        "第 90 百分位为 0.722。B3DB 阳性率为 48.9%，完整 TDC BBB 归档"
        "为 76.4%；hERG 阳性率为 76.4%，TDC 为 68.9%。两个队列在化学"
        "邻近性和标签组成上都不同于其 TDC 来源。"
    )
    _replace(
        document,
        "中文",
        "6.4 化学空间与来源依赖，第 1 段",
        "本文增加描述性化学空间审计",
        chemical_1,
        "把背景数据改为直接的来源邻近性审计陈述。",
        changes,
    )
    chemical_2 = (
        "按化学分层重新评分现有留出预测，未支持用简单骨架重叠或相似度解释"
        "hERG 信号。对 CatBoost，在 23 个共享训练/验证骨架的分子中，"
        "hERG 门控 QRC 减门控正交的 AUROC 效应为 -0.0026；在 270 个"
        "新骨架分子中为 +0.0452。早期按最高相似度四分位分组时，最高组"
        "为 +0.0196，其余三组为 +0.0494。更细的四分位分析并不单调："
        "CatBoost 和 ExtraTrees 在 Q3 均为正，但该方向未在每个相邻分组"
        "中保持。BBB 效应在共享骨架、新骨架和多数相似度分组中均为负。"
        "完整来源审计见补充表 S5、S6 和 S16。这些描述性分层只定位效应"
        "出现的位置，不能控制来源、实验批次或标签定义，也不能建立因果"
        "化学机制。"
    )
    _replace(
        document,
        "中文",
        "6.4 化学空间与来源依赖，第 2 段",
        "按上述化学分层重新评分",
        chemical_2,
        "补充非单调分层结果，并把结论限定为效应位置而非化学机制。",
        changes,
    )

    interpret_1 = _find_unique(
        document,
        "低维固定量子储层最清晰的理论动机",
    )
    _new_paragraph_before(interpret_1, "6.5 解释与复用", style="Heading 2")
    interpret_1_after = (
        "低维固定量子储层最清晰的理论动机，是处理训练数据有限、局部非线性"
        "强，且经典核不能充分覆盖化学分布的任务。全局 TDC ADMET 端点通常"
        "包含更大、更异构的标签集合，当前设计在该情境中没有显示稳定增益。"
        "低数据曲线也未在两种基线间出现同步正向变化。该观察并不排除角度"
        "编码、任务条件幅度编码、可训练线路、更大储层或不同读出策略；这些"
        "方案仍需在强基线和独立来源队列上重新评价。"
    )
    _set_text(interpret_1, interpret_1_after)
    interpret_2 = _find_unique(
        document,
        "hERG 点估计改善是候选信号",
    )
    interpret_2_after = (
        "hERG 候选信号和 B3DB 负迁移都不能单独建立机制性或普遍的量子效应。"
        "本文综述的 QML-ADMET 研究使用不同的固定储层、Hamiltonian 派生"
        "特征、量子启发预处理、线路搜索或联合训练残差；其任务数、对照和"
        "外部迁移设置不支持同类等效比较。表 1 汇总设计差异，补充表 S4 "
        "给出扩展比较。本文的经验贡献是对一个固定无状态量子特征映射族"
        "开展信号校准的 TDC 全端点审计；方法贡献是提供可复用的最低评价"
        "流程：预设主要对照，匹配候选与映射预算，按骨架簇推断，跨端点"
        "校正，分别解释等价与优越性，并同时报告跨基线与跨来源结果。"
    )
    _set_text(interpret_2, interpret_2_after)
    changes.append(
        ChangeLog(
            document="中文",
            location="6.5 解释与复用",
            before="hERG 点估计改善是候选信号 ... 本文贡献是 ...",
            after=interpret_2_after,
            reason="删除重复的贡献句，并区分经验贡献与方法贡献。",
        )
    )

    limitations_1 = _find_unique(
        document,
        "固定官方测试集支持可重复比较",
    )
    limitations_1_after = (
        "三类评价限制界定了结果的泛化范围。公开 TDC 测试集可能已被早期研究"
        "重复使用，并非前瞻性队列；骨架划分减少了实验室、时间和化学系列"
        "之间的近邻泄漏，但不能将其完全消除。低数据分析覆盖八个端点，"
        "96 条记录下限会改变最小端点的有效比例。主要外部比较包含两个分类"
        "队列，其来源和标签构造不同 [3-5]。"
    )
    _set_text(limitations_1, limitations_1_after)
    limitations_2 = _find_unique(
        document,
        "本文评价独立分子输入和一次固定五比特演化",
    )
    limitations_2_after = (
        "执行边界同样明确。精确态矢量计算用于隔离固定线路的表达行为，"
        "但不评价物理门误差、读出串扰、连接性或调度。有限测量采样分析"
        "对每个 Pauli 期望独立采样；简化去极化模型省略门专用误差、泄漏、"
        "串扰和物理调度。Qiskit/Aer 审计增加了转译门去极化和读出翻转，"
        "但仍使用固定合成误差参数，且未在电路含噪特征上重新训练完整"
        "预测器。本文未测试可训练线路、任务条件幅度编码或其他 PCA 维数。"
    )
    _set_text(limitations_2, limitations_2_after)
    limitations_3 = (
        "辅助分析的适用范围更窄。连续标签迁移对二分类模型输出排序，"
        "不是独立训练的回归评价。单独 pIC50 回归在固定协议下使用 214 个"
        "测试分子和 155 个骨架，统计功效有限。B3DB logBB 仅有 613/2,317 "
        "个非重叠分子可用，且类别比例高度不平衡。化学空间图使用线性指纹投影和"
        "三个基本描述符，不是完整适用域模型；TOST 边界是探索性基准阈值，"
        "而非临床或监管限值 [21]。随机映射敏感性为每族五个实现。已知信号"
        "校准使用由受测特征族生成的合成目标，只能说明这些设计的可检测性，"
        "并不覆盖所有可能的非线性信号。当前比较适用于五比特幅度编码、"
        "固定 Hamiltonian 储层、15 个 Pauli 读出、线性残差头和精确模拟；"
        "其他编码、可训练线路、更大储层和物理硬件需要独立评价。"
    )
    _new_paragraph_after(limitations_2, limitations_3)
    changes.append(
        ChangeLog(
            document="中文",
            location="7 局限性",
            before="两个长段混合了评价、执行和辅助分析限制。",
            after=f"{limitations_1_after} [paragraph break] {limitations_2_after} [paragraph break] {limitations_3}",
            reason="按限制所约束的推断类型分成评价、执行和辅助分析三段。",
        )
    )

    conclusion = _find_unique(
        document,
        "在 22 个官方 TDC ADMET 端点上",
    )
    conclusion_1 = (
        "在 22 个官方 TDC ADMET 端点上，固定五比特无状态储层残差相对在"
        "输入维数、名义读出维数、拟合参数数量、随机映射预算和调参预算上"
        "匹配的真实正交二次映射，没有显示稳定增量。该结果在 "
        "Morgan-ExtraTrees 和更强的 MapLight-CatBoost 基线上均成立。"
        "验证门控把部分有害残差退回经典基线，却未产生相对门控经典对照的"
        "稳定优势。联合门控、低数据缩放、有限测量采样和模拟退相干均未"
        "推翻该结论。外部 hERG 迁移提供了 CatBoost 特异候选信号，而 "
        "B3DB BBB 显示显著负迁移。连续标签排序迁移和骨架不相交的 pIC50 "
        "敏感性分析只显示未校正的弱 CatBoost/hERG 方向，既无 Holm 显著"
        "比较，也没有相应 BBB 信号。电路级审计在低、中误差下保持较高秩，"
        "但读出幅度明显衰减，且未增加优势证据。已知信号校准恢复了合成的"
        "QRC 与经典目标，零信号假阳性率不超过 5%。"
    )
    conclusion_2 = (
        "本文的经验贡献是对一个固定无状态量子特征映射族开展信号校准的 "
        "TDC 全端点审计；方法贡献是提供开放的匹配评价流程。hERG 信号是"
        "有边界的候选，而不是已建立的心脏毒性机制；B3DB 结果也不表示量子"
        "方法在 ADMET 中普遍无效。结论适用于所测试的五比特幅度编码、固定 "
        "Hamiltonian 储层、15 个 Pauli 读出、线性残差头和精确模拟；其他"
        "编码、可训练线路、更大储层和物理硬件需要独立评价。"
    )
    _set_text(conclusion, conclusion_1)
    _new_paragraph_after(conclusion, conclusion_2)
    changes.append(
        ChangeLog(
            document="中文",
            location="8 结论",
            before=conclusion_1,
            after=f"{conclusion_1} [paragraph break] {conclusion_2}",
            reason="拆开经验结果与方法贡献，并集中保留一次适用边界。",
        )
    )

    availability = _find_unique(
        document,
        "官方 TDC 归档可由 Harvard Dataverse",
    )
    availability_1 = (
        "官方 TDC 归档可由 Harvard Dataverse 文件 4426004 获取，SHA-256 为 "
        "bd0005246cb6f1672333c28ad202112a8bf071ab65d847848715030308faf1f1。"
        "外部 hERG 数据来自 Zenodo 5807719，BBB 数据来自 B3DB。数据来源、标签"
        "规则、去重和重叠审计包含在复现包中。MapLight 参照实现和 MIT "
        "许可证被保留，上游数据许可证随归档材料一并列出。"
    )
    _set_text(availability, availability_1)
    availability_2 = (
        "复现包包含处理脚本、五个骨架划分、每族五个随机映射、基线配置、"
        "全部逐划分预测、门控、有限测量采样、低数据、外部效应分解与校准、"
        "连续标签迁移、独立 pIC50 回归、简化和电路级噪声、有限特征族、"
        "TOST 敏感性、效应分解、容量和来源梯度结果，以及统计脚本、绘图"
        "代码和环境锁文件。版本化代码和结果索引见 "
        "https://github.com/575914291-source/qrc-admet-matched-evaluation。"
        "官方测试标签仅在配置锁定后用于评分，未用于训练、映射生成、联合"
        "权重或门控。"
    )
    references_heading = _find_unique(document, "参考文献")
    _new_paragraph_before(references_heading, availability_2, style="Normal")
    changes.append(
        ChangeLog(
            document="中文",
            location="数据与代码可用性",
            before="一段同时说明数据来源和软件清单。",
            after=f"{availability_1} [paragraph break] {availability_2}",
            reason="把数据来源与软件、结果清单分开。",
        )
    )

    table_updates = {
        "方法 3；图 4；表 5": "第 3 节；图 4；表 5",
        "图 3；补充表 S7-S10": "图 3；补充表 S7-S10、S16",
        "表 3-5；补充图 S1-S5": "表 3-5、S12-S16；补充图 S1-S10",
        "方法 4.2；局限性；补充图 S5": "方法 4.2、4.4；局限性；补充图 S5-S10",
        "报告全部端点效应、门控选择、低数据、shots、噪声和特征族搜索":
            "报告全部端点效应、门控选择、低数据、测量采样、噪声和特征族搜索",
        "两种强经典基座：Morgan-ExtraTrees 与 MapLight-CatBoost":
            "两种强经典基线：Morgan-ExtraTrees 与 MapLight-CatBoost",
    }
    for row in document.tables[-1].rows:
        for cell in row.cells:
            for old, new in table_updates.items():
                _replace_cell(cell, old, new)

    _remove_unverified_power_values(document)
    _normalize_connectors(document)
    _normalize_chinese_terms(document)
    document.core_properties.title = document.paragraphs[0].text
    document.core_properties.subject = document.paragraphs[1].text
    document.core_properties.author = ""
    document.core_properties.language = "zh-CN"
    document.core_properties.comments = (
        "中文参考稿；与最终英文稿逐段对应；作者信息待补。"
    )
    document.save(FINAL_ZH)
    return document, changes


def finalize() -> dict[str, object]:
    missing = [str(path) for path in (EN_SOURCE, ZH_SOURCE) if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing bilingual source documents: {missing}")

    _, english_changes = _finalize_english()
    _, chinese_changes = _finalize_chinese()
    changes = [change.as_dict() for change in english_changes + chinese_changes]
    payload = {
        "english": str(FINAL_EN),
        "chinese": str(FINAL_ZH),
        "change_count": len(changes),
        "changes": changes,
    }
    CHANGES_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


if __name__ == "__main__":
    print(json.dumps(finalize(), ensure_ascii=False, indent=2))
