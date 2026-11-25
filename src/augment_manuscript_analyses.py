from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt

from src.config import PROJECT_ROOT, RESULTS_ROOT


OUTPUT_ROOT = PROJECT_ROOT / "outputs"
CHINESE = OUTPUT_ROOT / "论文修订稿_v2_TDC完整实验.docx"
ENGLISH = OUTPUT_ROOT / "Matched_Evaluation_Fixed_Quantum_Reservoir_TDC_ADMET.docx"
CALIBRATION = RESULTS_ROOT / "calibration" / "summary.csv"
DECOMPOSITION = RESULTS_ROOT / "effect_decomposition" / "summary.json"
SELECTION = RESULTS_ROOT / "map_selection" / "summary.json"
CAPACITY = RESULTS_ROOT / "capacity_diagnostics" / "feature_summary.csv"


def _font(run, east_asia: str = "Times New Roman") -> None:
    run.font.name = "Arial"
    run.font.size = Pt(10.5)
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), east_asia)


def _insert_block(
    document: Document,
    marker_text: str,
    heading: str,
    paragraphs: list[str],
    east_asia: str,
) -> None:
    if any(paragraph.text.strip() == heading for paragraph in document.paragraphs):
        return
    marker = next(
        (
            paragraph
            for paragraph in document.paragraphs
            if paragraph.text.strip() == marker_text
        ),
        None,
    )
    if marker is None:
        raise RuntimeError(f"Cannot find manuscript marker: {marker_text}")
    heading_paragraph = marker.insert_paragraph_before(heading, style="Heading 2")
    for run in heading_paragraph.runs:
        run.font.name = "Arial"
        run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), east_asia)
    for text in paragraphs:
        paragraph = marker.insert_paragraph_before(text, style="Normal")
        paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        paragraph.paragraph_format.space_after = Pt(4)
        paragraph.paragraph_format.line_spacing = 1.2
        for run in paragraph.runs:
            _font(run, east_asia=east_asia)


def _load_values() -> dict[str, object]:
    calibration = pd.read_csv(
        CALIBRATION,
        encoding="utf-8-sig",
        keep_default_na=False,
        na_values=[""],
    )
    decomposition = json.loads(DECOMPOSITION.read_text(encoding="utf-8"))
    selection = json.loads(SELECTION.read_text(encoding="utf-8"))
    capacity = pd.read_csv(CAPACITY, encoding="utf-8-sig")
    index = calibration.set_index(["scenario", "base"])
    capacity_index = capacity.set_index(["base", "family"])
    return {
        "qrc_signal_et": float(
            index.loc[("qrc_signal", "extra_trees"), "qrc_minus_orthogonal_mean"]
        ),
        "qrc_signal_cb": float(
            index.loc[("qrc_signal", "catboost"), "qrc_minus_orthogonal_mean"]
        ),
        "classical_signal_et": float(
            index.loc[
                ("classical_signal", "extra_trees"),
                "qrc_minus_orthogonal_mean",
            ]
        ),
        "classical_signal_cb": float(
            index.loc[
                ("classical_signal", "catboost"),
                "qrc_minus_orthogonal_mean",
            ]
        ),
        "null_fpr_et": float(
            index.loc[
                ("null", "extra_trees"), "null_false_positive_rate"
            ]
        ),
        "null_fpr_cb": float(
            index.loc[
                ("null", "catboost"), "null_false_positive_rate"
            ]
        ),
        "qrc_selection_rate_et": float(
            index.loc[
                ("qrc_signal", "extra_trees"), "correct_selection_rate"
            ]
        ),
        "qrc_selection_rate_cb": float(
            index.loc[
                ("qrc_signal", "catboost"), "correct_selection_rate"
            ]
        ),
        "classical_selection_rate_et": float(
            index.loc[
                ("classical_signal", "extra_trees"), "correct_selection_rate"
            ]
        ),
        "classical_selection_rate_cb": float(
            index.loc[
                ("classical_signal", "catboost"), "correct_selection_rate"
            ]
        ),
        "neutralized_et": int(
            decomposition["bases"]["extra_trees"][
                "apparent_gains_neutralized_by_control"
            ]
        ),
        "positive_et": int(
            decomposition["bases"]["extra_trees"][
                "positive_qrc_vs_base_endpoints"
            ]
        ),
        "neutralized_cb": int(
            decomposition["bases"]["catboost"][
                "apparent_gains_neutralized_by_control"
            ]
        ),
        "positive_cb": int(
            decomposition["bases"]["catboost"][
                "positive_qrc_vs_base_endpoints"
            ]
        ),
        "selected_vs_orth_et": int(
            selection["endpoint_counts"]["extra_trees"][
                "qrc_selected_better_than_orth"
            ]
        ),
        "selected_vs_orth_cb": int(
            selection["endpoint_counts"]["catboost"][
                "qrc_selected_better_than_orth"
            ]
        ),
        "rank_et_qrc": float(
            capacity_index.loc[
                ("extra_trees", "qrc"), "test_effective_rank_mean"
            ]
        ),
        "rank_et_orth": float(
            capacity_index.loc[
                ("extra_trees", "real_orthogonal"),
                "test_effective_rank_mean",
            ]
        ),
        "rank_cb_qrc": float(
            capacity_index.loc[
                ("catboost", "qrc"), "test_effective_rank_mean"
            ]
        ),
        "rank_cb_orth": float(
            capacity_index.loc[
                ("catboost", "real_orthogonal"),
                "test_effective_rank_mean",
            ]
        ),
    }


def _methods_english(values: dict[str, object]) -> list[str]:
    return [
        (
            "To test whether the evaluation can recover a known reservoir-specific "
            "signal and reject a known classical signal, we added a feature-stage "
            "calibration on hERG, B3DB BBB, and AqSolDB solubility. Real molecular "
            "inputs were projected to 32 dimensions and passed through the same five "
            "QRC, orthogonal, and Fourier map draws. We generated QRC-derived, "
            "orthogonal-derived, and independent null targets, trained the same "
            "15-dimensional heads on the fixed training splits, averaged the five "
            "map predictions, and evaluated held-out recovery. The calibration "
            "isolates the feature comparison and intentionally omits the classical "
            "base offset."
        ),
        (
            "We also decomposed every QRC-versus-base endpoint effect into a matched "
            "classical nonlinearity term and a QRC-specific term, evaluated "
            "validation-selected maps to quantify selection optimism, measured "
            "effective rank condition and centered kernel alignment for all 220 "
            "task-base-split combinations, and stratified external QRC-specific "
            "effects by nearest-TDC similarity quartiles. These analyses are "
            "reported in Supplementary Tables S12-S16 and Figures S6-S10."
        ),
        (
            "The calibration targets test the sensitivity and specificity of the "
            "evaluation. They are not biological endpoints and are not used to infer "
            "new ADMET mechanisms."
        ),
    ]


def _methods_chinese(values: dict[str, object]) -> list[str]:
    return [
        (
            "为了检验评估流程能否恢复已知的储层特异信号，并拒绝已知的经典二次"
            "信号，我们在 hERG、B3DB BBB 与 AqSolDB 溶解度上增加了特征层校准。"
            "真实分子输入仍投影到 32 维，并使用相同的五个 QRC、实正交和 Fourier"
            " 映射。分别生成 QRC 来源、实正交来源和无信号来源的合成目标，在固定"
            "训练划分上训练相同的 15 维读出，并平均五个映射的测试预测。该实验"
            "只校准特征比较阶段，故意不加入经典基座偏移。"
        ),
        (
            "此外，我们将每个 QRC 相对基座的端点效应分解为经典非线性项和 QRC "
            "特异项；利用验证集选择最佳映射并评价选择乐观；在全部 220 个"
            "任务-基座-split 组合上计算有效秩、条件数与中心核对齐；最后按"
            "外部样本到 TDC 的最近邻相似度四分位分层。相关结果见补充表 S12 至"
            " S16 与补充图 S6 至 S10。"
        ),
        (
            "这些质量校准目标用于检验评估的检出能力和特异性。它们不是生物"
            "终点，也不用于推断新的 ADMET 机制。"
        ),
    ]


def _results_english(values: dict[str, object]) -> list[str]:
    return [
        (
            "The known-signal calibration recovered the intended geometry. For a "
            "QRC-derived target, QRC minus orthogonal test performance was "
            f"{values['qrc_signal_et']:+.3f} on ExtraTrees and "
            f"{values['qrc_signal_cb']:+.3f} on CatBoost, and the correct source "
            f"family ranked first in {100 * values['qrc_selection_rate_et']:.1f}% "
            f"and {100 * values['qrc_selection_rate_cb']:.1f}% of simulations. "
            "For an orthogonal-derived target, the same contrast reversed to "
            f"{values['classical_signal_et']:+.3f} and "
            f"{values['classical_signal_cb']:+.3f}; the correct classical family "
            f"ranked first in {100 * values['classical_selection_rate_et']:.1f}% "
            f"and {100 * values['classical_selection_rate_cb']:.1f}% of simulations. "
            f"Null false-positive rates were {100 * values['null_fpr_et']:.1f}% "
            f"and {100 * values['null_fpr_cb']:.1f}%, respectively."
        ),
        (
            "Effect decomposition showed why matched controls change interpretation. "
            f"Among the {values['positive_et']} ExtraTrees endpoints with a positive "
            f"QRC-versus-base point estimate, {values['neutralized_et']} had a "
            "non-positive QRC-specific effect after subtracting the matched "
            f"orthogonal contribution. For CatBoost, {values['neutralized_cb']} of "
            f"{values['positive_cb']} such endpoints were neutralized. "
            "Validation-selected QRC beat validation-selected orthogonal features on "
            f"{values['selected_vs_orth_et']}/22 ExtraTrees and "
            f"{values['selected_vs_orth_cb']}/22 CatBoost endpoints, a near-balanced "
            "pattern rather than a cross-base advantage."
        ),
        (
            "Capacity diagnostics showed that the fixed QRC maps were not "
            "artificially underparameterized: mean test effective rank was "
            f"{values['rank_et_qrc']:.2f} versus {values['rank_et_orth']:.2f} on "
            f"ExtraTrees and {values['rank_cb_qrc']:.2f} versus "
            f"{values['rank_cb_orth']:.2f} on CatBoost across 15 features. "
            "External source stratification retained a local hERG direction in "
            "middle similarity quartiles but not across adjacent quartiles or B3DB "
            "BBB. Together, these controls support a bounded evaluation finding "
            "rather than a model-ranking claim."
        ),
    ]


def _results_chinese(values: dict[str, object]) -> list[str]:
    return [
        (
            "已知信号校准能够恢复预设的表示来源。对于由 QRC 构造的目标，QRC "
            "相对实正交控制的测试表现差值在 ExtraTrees 上为 "
            f"{values['qrc_signal_et']:+.3f}，在 CatBoost 上为 "
            f"{values['qrc_signal_cb']:+.3f}；正确来源族排名第一的比例分别为 "
            f"{100 * values['qrc_selection_rate_et']:.1f}% 和 "
            f"{100 * values['qrc_selection_rate_cb']:.1f}%。当目标由实正交二次"
            f"特征生成时，该差值反转为 {values['classical_signal_et']:+.3f} 和 "
            f"{values['classical_signal_cb']:+.3f}，正确经典族排名第一的比例分别"
            f"为 {100 * values['classical_selection_rate_et']:.1f}% 和 "
            f"{100 * values['classical_selection_rate_cb']:.1f}%。无信号对照的"
            f"错误阳性率分别为 {100 * values['null_fpr_et']:.1f}% 和 "
            f"{100 * values['null_fpr_cb']:.1f}%。"
        ),
        (
            "效应分解进一步说明匹配控制为什么会改变解释。在 ExtraTrees 的 "
            f"{values['positive_et']} 个 QRC 相对基座点估计为正的端点中，"
            f"{values['neutralized_et']} 个在扣除实正交贡献后并不存在正向的 "
            f"QRC 特异效应；CatBoost 中相应为 {values['neutralized_cb']}/"
            f"{values['positive_cb']}。验证集选中的 QRC 仅在 "
            f"{values['selected_vs_orth_et']}/22 个 ExtraTrees 和 "
            f"{values['selected_vs_orth_cb']}/22 个 CatBoost 端点上优于同样经过"
            "验证集选择的实正交映射，没有形成跨基座优势。"
        ),
        (
            "容量诊断表明固定 QRC 映射并不是人为低容量对照：在 15 维读出中，"
            f"平均测试有效秩在 ExtraTrees 上为 {values['rank_et_qrc']:.2f}"
            f"（QRC）与 {values['rank_et_orth']:.2f}（实正交），在 CatBoost 上为 "
            f"{values['rank_cb_qrc']:.2f} 与 {values['rank_cb_orth']:.2f}。"
            "外部来源分层只保留了中部相似度区域的局部 hERG 方向，而在相邻"
            "四分位和 B3DB BBB 中不稳定。这些结果把论文支持的主张限定为"
            "评估层结论，而不是模型精度排名。"
        ),
    ]


def augment(path: Path, language: str, values: dict[str, object]) -> None:
    document = Document(path)
    if language == "en":
        _insert_block(
            document,
            "5 Results",
            "4.4 Benchmark Calibration and Attribution",
            _methods_english(values),
            "Times New Roman",
        )
        _insert_block(
            document,
            "6 Discussion",
            "5.9 Benchmark Calibration and Source Diagnostics",
            _results_english(values),
            "Times New Roman",
        )
    else:
        _insert_block(
            document,
            "5 结果",
            "4.4 基准校准与效应归因",
            _methods_chinese(values),
            "宋体",
        )
        _insert_block(
            document,
            "6 讨论",
            "5.9 基准校准与来源诊断",
            _results_chinese(values),
            "宋体",
        )
    document.save(path)


def main() -> None:
    values = _load_values()
    augment(ENGLISH, "en", values)
    augment(CHINESE, "zh", values)
    print(
        json.dumps(
            {
                "english": str(ENGLISH),
                "chinese": str(CHINESE),
                "calibration_rows": 3,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
